"""PC-only continuation with software VA aliases; never enable a real MMU.

The existing entry model checks actual XNU-created page tables first. This
continuation validates every aliased 16K page with that walker and executes
real instructions using copied aliases. Register/barrier effects are modeled.
No CPU translation, TLB/cache correctness, hardware handoff or C initialization
success is implied by reaching a C entry/call boundary.
"""
from collections import Counter,deque
import struct

PAGE=0x4000


def continue_entry(*,uc,md,state,stop,symbols,physical_image,rounded,arguments,
                   boot_args,virtual_ram,ram_base,walk,code_hook,write_hook,
                   banked_sp,sp_select,fault=None):
    from unicorn import UC_HOOK_CODE,UC_HOOK_MEM_WRITE,UC_HOOK_MEM_READ
    from unicorn import arm64_const as regs
    if fault not in (None,'argument','mapping'):raise ValueError('Unknown PC fault injection')
    uc.hook_del(code_hook);uc.hook_del(write_hook)
    delta=virtual_ram-ram_base
    mappings=[(physical_image,rounded),(arguments,0x10000)]
    if fault=='mapping':
        # Corrupt the actual emulated L2 descriptor, rather than substituting
        # a guessed walker result. The already-checked bootstrap uses L1/L2
        # tables and 32MiB blocks for this linked 16K kernel.
        virtual=physical_image+delta
        bits=64-((state['tcr_el1']>>16)&63)
        root=state['ttbr1_el1']&0x0000ffffffffc000
        slot=(virtual>>36)&((1<<(bits-36))-1)
        table_desc=struct.unpack('<Q',uc.mem_read(root+slot*8,8))[0]
        if table_desc&3!=3:raise ValueError('Fault fixture requires a real L1 table')
        table=table_desc&0x0000ffffffffc000
        leaf=table+((virtual>>25)&2047)*8
        descriptor=struct.unpack('<Q',uc.mem_read(leaf,8))[0]
        if descriptor&3!=1:raise ValueError('Fault fixture requires a real L2 block')
        uc.mem_write(leaf,struct.pack('<Q',descriptor^(1<<25)))
    pages=0
    for physical,size in mappings:
        virtual=physical+delta
        for offset in range(0,size,PAGE):
            for last in (0,PAGE-1):
                address=virtual+offset+last
                actual=walk(address,True)
                if actual!=physical+offset+last:raise ValueError('VA alias differs from bootstrap translation')
            pages+=1
        uc.mem_map(virtual,size)
        uc.mem_write(virtual,bytes(uc.mem_read(physical,size)))
    target=symbols['_arm_init']
    if not physical_image+delta<=target<physical_image+delta+rounded:
        raise ValueError('C entry outside linked kernel')
    expected_args=arguments+delta
    expected_stack=symbols['_intstack_top']
    expected_exception_stack=symbols['_excepstack_top']
    if banked_sp[1]!=expected_exception_stack or uc.reg_read(regs.UC_ARM64_REG_SP)!=expected_stack:
        raise ValueError('XNU did not establish virtual bootstrap stacks')
    if sp_select!=0:raise ValueError('Unexpected bootstrap SP selection')
    if fault=='argument':uc.reg_write(regs.UC_ARM64_REG_X20,arguments+PAGE)
    # Keep Unicorn's MMU state untouched. The SCTLR write and its effect are
    # modeled explicitly; only the subsequent linked instructions execute.
    state=dict(state);state['sctlr_el1']=int(stop['sctlr_value'],16)
    start=int(stop['address'],16)+4
    operations=Counter();recent=deque(maxlen=20);count=0;entry=None;boundary=None
    stores=[];reads=0;fetches=0
    def translate(address,size):
        high=address>=virtual_ram
        physical=address-delta if high else address
        if not any(first<=physical and physical+size<=first+length for first,length in mappings):
            raise ValueError('Access left declared model buffers')
        for last in (0,size-1):
            if walk(address+last,high)!=physical+last:
                raise ValueError('Access differs from actual bootstrap translation')
        return physical
    def gpr(name):
        if name=='xzr':return None
        return getattr(regs,'UC_ARM64_REG_'+name.upper())
    def read(name):
        if name.startswith('#'):return int(name[1:],0)
        register=gpr(name)
        return uc.reg_read(register) if register is not None else 0
    def instruction(engine,address,size,_):
        nonlocal count,entry,boundary,fetches
        count+=1
        translate(address,4);fetches+=1
        ins=next(md.disasm(bytes(engine.mem_read(address,4)),address))
        recent.append(hex(address)+' '+ins.mnemonic+' '+ins.op_str)
        if address==target:
            if engine.reg_read(regs.UC_ARM64_REG_X0)!=expected_args:
                raise ValueError('C entry received wrong virtual boot_args')
            if bytes(engine.mem_read(expected_args,len(boot_args)))!=bytes(boot_args):
                raise ValueError('Virtual boot_args contents changed')
            entry={'symbol':'_arm_init','virtual_address':hex(address),
                   'x0':hex(expected_args),'stack_pointer':hex(engine.reg_read(regs.UC_ARM64_REG_SP))}
        if entry is not None and ins.mnemonic in ('bl','blr'):
            if ins.mnemonic!='bl':raise ValueError('Unexpected indirect first C call')
            destination=int(ins.op_str.lstrip('#'),0)
            names=[name for name,value in symbols.items() if value==destination]
            if not names:raise ValueError('First C call target has no linked symbol')
            boundary={'reason':'before_first_arm_init_call','address':hex(address),
                      'target_address':hex(destination),'target_symbols':sorted(names)}
            engine.emu_stop();return
        operands=[part.strip().lower() for part in ins.op_str.split(',')]
        if ins.mnemonic=='mrs':
            dst,reg=operands
            if reg not in state:raise ValueError('Unmodeled post-MMU register read: '+reg)
            engine.reg_write(gpr(dst),state[reg]);operations['modeled_mrs']+=1
        elif ins.mnemonic=='msr':
            reg,src=operands
            if reg not in ('cpacr_el1','tpidr_el1'):raise ValueError('Unexpected post-MMU register write: '+reg)
            state[reg]=read(src);operations['modeled_msr']+=1
        elif ins.mnemonic in ('dc','ic','tlbi','dsb','dmb','isb'):
            operations['modeled_'+ins.mnemonic]+=1
        else:return
        engine.reg_write(regs.UC_ARM64_REG_PC,address+4)
    def write(engine,access,address,size,value,_):
        physical=translate(address,size)
        if address<virtual_ram:raise ValueError('Post-MMU store used physical alias')
        if not physical_image<=physical or physical+size>physical_image+rounded:
            raise ValueError('Post-MMU store left virtual kernel RAM')
        if size>8:raise ValueError('Unsupported post-MMU store size')
        # Mirror pre-write hook values into the physical view. This is a
        # software alias model, not a hardware coherence/cache test.
        engine.mem_write(physical,(value&((1<<(size*8))-1)).to_bytes(size,'little'))
        stores.append((address,size))
    def load(engine,access,address,size,value,_):
        nonlocal reads
        translate(address,size);reads+=1
    hook=uc.hook_add(UC_HOOK_CODE,instruction);memory_hook=uc.hook_add(UC_HOOK_MEM_WRITE,write)
    read_hook=uc.hook_add(UC_HOOK_MEM_READ,load)
    try:uc.emu_start(start,physical_image+rounded,count=10000)
    except Exception as error:raise ValueError(str(error)+'\n'+'\n'.join(recent)) from error
    finally:uc.hook_del(hook);uc.hook_del(memory_hook);uc.hook_del(read_hook)
    if entry is None or boundary is None:raise ValueError('Did not reach the C first-call boundary')
    if bytes(uc.mem_read(arguments,len(boot_args)))!=bytes(boot_args):
        raise ValueError('Physical boot_args changed')
    for address,size in stores:
        if bytes(uc.mem_read(address,size))!=bytes(uc.mem_read(address-delta,size)):
            raise ValueError('Software physical/virtual store mirrors disagree')
    return {'passed':True,'instructions':count,'arm_init_entry':entry,'stop':boundary,
            'aliased_pages_checked':pages,'virtual_kernel_store_count':len(stores),
            'translated_instruction_fetches':fetches,'translated_data_reads':reads,
            'modeled_system_operations':dict(operations),'exception_stack':hex(expected_exception_stack),
            'mmu_enable_executed':False,'hardware_verified':False,'c_initialization_completed':False,
            'stage1_permission_faults_modeled':False,'cache_tlb_coherence_tested':False,
            'scope':'Linked instructions with page-table-checked software VA aliases; modeled SCTLR/register/barriers'}
