"""PC-only continuation with software VA aliases; never enable a real MMU.

The existing entry model checks actual XNU-created page tables first. This
continuation validates every aliased 16K page with that walker and executes
real instructions using copied aliases. Register/barrier effects are modeled.
No CPU translation, TLB/cache correctness, hardware handoff or C initialization
success is implied by reaching a C entry/call boundary.
"""
from collections import Counter,deque
import struct
from stage1_access import check_access

PAGE=0x4000


class ModelPanic(ValueError):
    def __init__(self,report):
        self.report=report
        super().__init__('Actual XNU panic path: '+report['format'])


class ModelExecutionError(ValueError):
    def __init__(self,report):
        self.report=report
        super().__init__(report['error']+'\n'+'\n'.join(report['recent']))


def continue_entry(*,uc,md,state,stop,symbols,physical_image,rounded,arguments,
                   boot_args,virtual_ram,ram_base,walk,code_hook,write_hook,
                   banked_sp,sp_select,kernel_raw,kernel_segments,fault=None,c_phase='first-call',register_inputs=None,
                   expected_timebase=None,cache_inputs=None):
    from unicorn import UC_HOOK_CODE,UC_HOOK_MEM_WRITE,UC_HOOK_MEM_READ
    from unicorn import arm64_const as regs
    if c_phase not in ('first-call','platform','platform-return','topology','topology-return','thread','thread-return','startup','startup-return','vm'):
        raise ValueError('Unknown C continuation boundary')
    descriptor_faults=('mapping','af','pxn','readonly','table-pxn','table-readonly','el0-writable')
    if fault not in (None,'argument','wxn','epd',*descriptor_faults):raise ValueError('Unknown PC fault injection')
    uc.hook_del(code_hook);uc.hook_del(write_hook)
    delta=virtual_ram-ram_base
    mappings=[(physical_image,rounded),(arguments,0x10000)]
    if fault in descriptor_faults:
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
        if fault=='table-pxn':uc.mem_write(root+slot*8,struct.pack('<Q',table_desc|(1<<59)))
        elif fault=='table-readonly':uc.mem_write(root+slot*8,struct.pack('<Q',table_desc|(1<<62)))
        else:
            changed={'mapping':descriptor^(1<<25),'af':descriptor&~(1<<10),
                     'pxn':descriptor|(1<<53),'readonly':descriptor|(1<<7),'el0-writable':descriptor|(1<<6)}[fault]
            uc.mem_write(leaf,struct.pack('<Q',changed))
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
    register_inputs=dict(register_inputs or {})
    if set(register_inputs)-{'cntkctl_el1','cntvct_el0','mpidr_el1','clidr_el1','ctr_el0','daif','id_aa64dfr0_el1'} or any(type(v) is not int or not 0<=v<1<<64 for v in register_inputs.values()):
        raise ValueError('Unsupported explicit register fixture')
    if 'daif' in register_inputs and register_inputs['daif']&~0x3c0:
        raise ValueError('DAIF fixture has reserved bits')
    cache_inputs=dict(cache_inputs or {})
    if any(type(k) is not int or k not in range(14) or type(v) is not int or not 0<=v<1<<32 for k,v in cache_inputs.items()):
        raise ValueError('Unsupported explicit cache selector fixture')
    state.update(register_inputs)
    if fault=='wxn':state['sctlr_el1']|=1<<19
    if fault=='epd':state['tcr_el1']|=1<<23
    start=int(stop['address'],16)+4
    operations=Counter();recent=deque(maxlen=20);count=0;entry=None;boundary=None;platform_return=None;topology_return=None
    thread_return=None;startup_return=None
    stores=[];reads=0;fetches=0;pending=[];calls=[];decoded={}
    def flush_stores(engine):
        for address,size in pending:
            engine.mem_write(address-delta,bytes(engine.mem_read(address,size)))
        pending.clear()
    def translate(address,size,access):
        high=address>=virtual_ram
        physical=address-delta if high else address
        if not any(first<=physical and physical+size<=first+length for first,length in mappings):
            raise ValueError('Access left declared model buffers')
        for last in (0,size-1):
            if walk(address+last,high)!=physical+last:
                raise ValueError('Access differs from actual bootstrap translation')
        checked=check_access(lambda p:struct.unpack('<Q',uc.mem_read(p,8))[0],state,
                             address,size,high,access,pan=False)
        if checked['physical_address']!=physical:raise ValueError('Permission walker / address walker mismatch')
        return physical
    def gpr(name):
        if name=='xzr':return None
        return getattr(regs,'UC_ARM64_REG_'+name.upper())
    def read(name):
        if name.startswith('#'):return int(name[1:],0)
        register=gpr(name)
        return uc.reg_read(register) if register is not None else 0
    def instruction(engine,address,size,_):
        nonlocal count,entry,boundary,fetches,platform_return,topology_return,thread_return,startup_return,sp_select
        flush_stores(engine)
        count+=1
        translate(address,4,'fetch');fetches+=1
        opcode=bytes(engine.mem_read(address,4));key=(address,opcode)
        ins=decoded.get(key)
        if ins is None:
            ins=next(md.disasm(opcode,address));decoded[key]=ins
        recent.append(hex(address)+' '+ins.mnemonic+' '+ins.op_str)
        if startup_return is not None and address==startup_return:
            boundary={'reason':'after_kernel_startup_bootstrap','address':hex(address)}
            engine.emu_stop();return
        if platform_return is not None and address==platform_return:
            boundary={'reason':'after_platform_init_return','address':hex(address)}
            engine.emu_stop();return
        if topology_return is not None and address==topology_return:
            boundary={'reason':'after_cpu_topology_return','address':hex(address)}
            engine.emu_stop();return
        if thread_return is not None and address==thread_return:
            if engine.reg_read(regs.UC_ARM64_REG_X0)!=symbols['_init_thread']:
                raise ValueError('Bootstrap thread return differs from actual static object')
            boundary={'reason':'after_thread_bootstrap_return','address':hex(address),
                      'thread_pointer':hex(engine.reg_read(regs.UC_ARM64_REG_X0))}
            engine.emu_stop();return
        if address==target:
            if engine.reg_read(regs.UC_ARM64_REG_X0)!=expected_args:
                raise ValueError('C entry received wrong virtual boot_args')
            if bytes(engine.mem_read(expected_args,len(boot_args)))!=bytes(boot_args):
                raise ValueError('Virtual boot_args contents changed')
            entry={'symbol':'_arm_init','virtual_address':hex(address),
                   'x0':hex(expected_args),'stack_pointer':hex(engine.reg_read(regs.UC_ARM64_REG_SP))}
        if entry is not None and ins.mnemonic in ('bl','blr'):
            if ins.mnemonic=='bl':destination=int(ins.op_str.lstrip('#'),0)
            else:destination=read(ins.op_str.lower())
            names=[name for name,value in symbols.items() if value==destination]
            if not names:raise ValueError('First C call target has no linked symbol')
            record={'address':hex(address),'target_address':hex(destination),'target_symbols':sorted(names),
                    'indirect':ins.mnemonic=='blr','x0':hex(engine.reg_read(regs.UC_ARM64_REG_X0)),
                    'x1':hex(engine.reg_read(regs.UC_ARM64_REG_X1)),
                    'x2':hex(engine.reg_read(regs.UC_ARM64_REG_X2))}
            calls.append(record)
            if len(calls)>(32768 if c_phase in ('startup-return','vm') else 4096):raise ValueError('C continuation call budget exceeded')
            if c_phase=='vm' and '_arm_vm_init' in names:
                boundary={'reason':'before_arm_vm_init',**record}
                engine.emu_stop();return
            if c_phase=='startup' and '_kernel_startup_bootstrap' in names:
                boundary={'reason':'before_kernel_startup_bootstrap',**record}
                engine.emu_stop();return
            if c_phase=='startup-return' and '_kernel_startup_bootstrap' in names:startup_return=address+4
            if c_phase=='platform-return' and '_PE_init_platform' in names:
                platform_return=address+4
            if c_phase=='topology' and '_ml_parse_cpu_topology' in names:
                boundary={'reason':'before_cpu_topology','address':hex(address),
                          'target_address':hex(destination),'target_symbols':sorted(names)}
                engine.emu_stop();return
            if c_phase=='topology-return' and '_ml_parse_cpu_topology' in names:
                topology_return=address+4
            if c_phase=='thread' and '_thread_bootstrap' in names:
                boundary={'reason':'before_thread_bootstrap','address':hex(address),
                          'target_address':hex(destination),'target_symbols':sorted(names)}
                engine.emu_stop();return
            if c_phase=='thread-return' and '_thread_bootstrap' in names:thread_return=address+4
            if c_phase=='first-call' or (c_phase=='platform' and '_PE_init_platform' in names):
                boundary={'reason':'before_first_arm_init_call' if c_phase=='first-call' else 'before_platform_init',**record}
                engine.emu_stop();return
            if any(name in ('_panic','_panic_with_options','___stack_chk_fail') for name in names):
                pointer=engine.reg_read(regs.UC_ARM64_REG_X0);message=bytearray()
                try:
                    for i in range(512):
                        byte=bytes(engine.mem_read(pointer+i,1))
                        if byte==b'\0':break
                        message.extend(byte)
                except Exception:message=b'<unreadable panic format>'
                raise ModelPanic({'reason':'actual_panic_call','address':hex(address),
                                  'format':bytes(message).decode(errors='replace'),
                                  'instructions':count,'calls_observed':calls,'recent':list(recent),
                                  'hardware_verified':False})
        operands=[part.strip().lower() for part in ins.op_str.split(',')]
        if ins.mnemonic=='mrs':
            dst,reg=operands
            if reg=='ccsidr_el1':
                selector=state.get('csselr_el1')
                if selector not in cache_inputs:raise ValueError('Missing explicit CCSIDR fixture for selector '+str(selector))
                state[reg]=cache_inputs[selector]
            if reg not in state:raise ValueError('Unmodeled post-MMU register read: '+reg)
            engine.reg_write(gpr(dst),state[reg]);operations['modeled_mrs']+=1
        elif ins.mnemonic=='msr':
            reg,src=operands
            if reg=='spsel':
                number=read(src)
                if number not in (0,1):raise ValueError('Invalid modeled stack selection')
                banked_sp[sp_select]=engine.reg_read(regs.UC_ARM64_REG_SP)
                sp_select=number;engine.reg_write(regs.UC_ARM64_REG_SP,banked_sp[number])
                state[reg]=number;operations['modeled_msr']+=1
                engine.reg_write(regs.UC_ARM64_REG_PC,address+4);return
            if reg not in ('cpacr_el1','tpidr_el1','tpidr_el0','tpidrro_el0','contextidr_el1','csselr_el1') and not (reg=='cntkctl_el1' and reg in register_inputs):
                raise ValueError('Unexpected post-MMU register write: '+reg)
            state[reg]=read(src);operations['modeled_msr']+=1
        elif ins.mnemonic in ('dc','ic','tlbi','dsb','dmb','isb'):
            operations['modeled_'+ins.mnemonic]+=1
        else:return
        engine.reg_write(regs.UC_ARM64_REG_PC,address+4)
    def write(engine,access,address,size,value,_):
        physical=translate(address,size,'write')
        if address<virtual_ram:raise ValueError('Post-MMU store used physical alias')
        if not physical_image<=physical or physical+size>physical_image+rounded:
            raise ValueError('Post-MMU store left virtual kernel RAM')
        if size>16:raise ValueError('Unsupported post-MMU store size')
        # Read actual bytes after the instruction, including full SIMD stores
        # whose pre-write callback value cannot represent all 16 bytes.
        pending.append((address,size))
        stores.append((address,size))
    def load(engine,access,address,size,value,_):
        nonlocal reads
        translate(address,size,'read');reads+=1
    hook=uc.hook_add(UC_HOOK_CODE,instruction);memory_hook=uc.hook_add(UC_HOOK_MEM_WRITE,write)
    read_hook=uc.hook_add(UC_HOOK_MEM_READ,load)
    try:
        budget=10000 if c_phase=='first-call' else (2000000 if c_phase in ('startup-return','vm') else 500000)
        uc.emu_start(start,physical_image+rounded,count=budget)
        flush_stores(uc)
    except ModelPanic:raise
    except Exception as error:
        raise ModelExecutionError({'error':str(error),'c_phase':c_phase,'instructions':count,
                                   'calls_observed':calls,'recent':list(recent),
                                   'modeled_register_state':dict(state),'hardware_verified':False}) from error
    finally:uc.hook_del(hook);uc.hook_del(memory_hook);uc.hook_del(read_hook)
    if entry is None or boundary is None:
        raise ValueError('Did not reach C boundary: '+c_phase+' instructions='+str(count)+'\n'+'\n'.join(recent))
    if sp_select!=0 or banked_sp[1]!=expected_exception_stack:
        raise ValueError('C boundary did not preserve exception stack and SP selection')
    if bytes(uc.mem_read(arguments,len(boot_args)))!=bytes(boot_args):
        raise ValueError('Physical boot_args changed')
    for address,size in stores:
        if bytes(uc.mem_read(address,size))!=bytes(uc.mem_read(address-delta,size)):
            raise ValueError('Software physical/virtual store mirrors disagree')
    early_state=None
    if c_phase!='first-call':
        from early_c_state import inspect
        early_state=inspect(uc,kernel_raw,symbols,kernel_segments,boot_args,calls,stores,
                            expected_timebase,state.get('cntkctl_el1'))
        if c_phase in ('topology-return','thread','thread-return','startup','startup-return','vm'):
            from early_c_state import inspect_single_cpu
            early_state['single_cpu_fixture']=inspect_single_cpu(uc,symbols)
            if state.get('tpidr_el0')!=0 or state.get('tpidrro_el0')!=0:
                raise ValueError('CPU ID register model differs from logical CPU 0')
        if c_phase=='thread-return':
            from early_c_state import inspect_thread
            early_state['bootstrap_thread']=inspect_thread(uc,symbols,kernel_raw,calls)
        if c_phase in ('startup','startup-return','vm'):
            if expected_timebase is None:raise ValueError('Startup state requires explicit timebase')
            from early_c_state import inspect_startup
            early_state['startup']=inspect_startup(uc,symbols,state,expected_timebase)
        if c_phase in ('startup-return','vm'):
            from early_c_state import inspect_startup_entries
            early_state['startup_entries']=inspect_startup_entries(uc,kernel_raw,symbols,calls)
        if c_phase=='vm':
            from early_c_state import inspect_vm_boundary
            early_state['vm_boundary']=inspect_vm_boundary(uc,symbols,boot_args,cache_inputs,state)
    return {'passed':True,'instructions':count,'arm_init_entry':entry,'stop':boundary,
            'early_c_state':early_state,
            'c_phase':c_phase,'calls_observed':calls,
            'aliased_pages_checked':pages,'virtual_kernel_store_count':len(stores),
            'translated_instruction_fetches':fetches,'translated_data_reads':reads,
            'distinct_instruction_decodes':len(decoded),
            'modeled_system_operations':dict(operations),'exception_stack':hex(expected_exception_stack),
            'mmu_enable_executed':False,'hardware_verified':False,'c_initialization_completed':False,
            'stage1_permission_subset_checked':True,'complete_stage1_fault_model':False,
            'cache_tlb_coherence_tested':False,
            'el1_permission_subset_checked':['AF','AP','APTable','PXN','PXNTable','EL0-write-XN','WXN','PAN','EPD'],
            'synthetic_pan':False,
            'synthetic_register_inputs':register_inputs,
            'synthetic_cache_inputs':cache_inputs,
            'final_explicit_registers':{key:state[key] for key in register_inputs},
            'synthetic_tpidr_el0':state.get('tpidr_el0'),
            'scope':'Linked instructions with page-table-checked software VA aliases; modeled SCTLR/register/barriers'}
