"""Six new suffix-effect predicates; own ISA encoders and dummy context data."""
import hashlib
import struct


def wide(destination,value):return 0xd2800000|(value<<5)|destination

def add_register(destination,left,right):return 0x8b000000|(right<<16)|(left<<5)|destination

def sp_move(destination,source):return 0x91000000|(source<<5)|destination

def pair(load,first,second,base,stride=16):return 0xa8800000|(int(load)<<22)|(((stride//8)&127)<<15)|(second<<10)|(base<<5)|first

def scalar(load,register,base,offset=0):return 0xf9000000|(int(load)<<22)|((offset//8)<<10)|(base<<5)|register

def system_sp_el0(source):return 0xd5184100|source

def ret(register):return 0xd65f0000|(register<<5)


def sample(change=None):
    start=0x600;base=0x240;ops=[(wide(10,base),'mov'),(add_register(8,0,10),'add'),(sp_move(9,31),'mov')];pairs=[(i,i+1)for i in range(19,29,2)]+[(29,9)]
    ops.extend((pair(False,a,b,8),'stp')for a,b in pairs);ops.extend([(scalar(False,30,8),'str'),(add_register(8,1,10),'add')]);ops.extend((pair(True,a,b,8),'ldp')for a,b in pairs);ops.extend([(scalar(True,30,8),'ldr'),(sp_move(31,9),'mov'),(system_sp_el0(1),'msr'),(ret(30),'ret')])
    if change=='base_clobber':ops.insert(3,(sp_move(10,31),'mov'))
    if change=='stride':ops[3]=(pair(False,19,20,8,8),'stp')
    if change=='pair_second':ops[11]=(pair(True,19,21,8),'ldp')
    if change=='SP':ops[-3]=(sp_move(31,8),'mov')
    if change=='LR':ops[-4]=(scalar(True,30,8,8),'ldr')
    if change=='RET':ops[-1]=(ret(29),'ret')
    text=f'{start:016x} <cpu_switch_to>:\n'+''.join(f' {start+4*i:x}: {word:08x} {mnemonic} dummy\n'for i,(word,mnemonic)in enumerate(ops));digest=hashlib.sha256(b''.join(struct.pack('<I',w)for w,m in ops)).hexdigest();provider=dict(name='cpu_switch_to',value=start,bytes=4*len(ops));prefix=dict(generated_context_base_immediate_binding_proven=True,generated_THREAD_CPU_CONTEXT=base,ADD_x8_x0_x10_offset=4,materialization=[dict(offset=0,word=f'{ops[0][0]:08x}',x10=base)])
    return text,provider,digest,prefix,[]


def run(helper):
    cases=(('valid_conditional_slot_SP_LR_effects',None),('STP_post_index_stride_mismatch','stride'),('LDP_second_destination_mismatch','pair_second'),('wrong_SP_origin','SP'),('wrong_LR_slot','LR'),('wrong_RET_register','RET'));completed=[]
    try:
        for name,change in cases:
            if change is None:
                p=helper.prove(*sample());ok=p['local_context_slot_effects_under_conditions']is True and len(p['conditions'])==4 and p['context_slot_span_bytes']==104 and p['switch_resume_contract_proven']is p['numeric_internal_context_layout_proven']is p['assembly_C_compiler_SU_claimed']is False and p['compiler_static_SU_bytes']is None
            else:
                # One SP/base-admissibility verdict requires both wrong SP source and clobbered base to reject.
                ok=True
                for mutation in (('SP','base_clobber')if change=='SP'else(change,)):
                    try:helper.prove(*sample(mutation))
                    except ValueError:pass
                    else:ok=False
            if not ok:raise ValueError('new suffix predicate failed: '+name)
            completed.append(name)
    except BaseException as error:
        error.fixture_progress=dict(groups=1,variants=6,assertions=6,completed_variants=len(completed),completed_assertions=len(completed),case_names=completed);raise
    return dict(groups=1,variants=6,assertions=6,completed_variants=6,completed_assertions=6,case_names=completed,host_processes=0,disassembly_reads=0,selected_body_reads=0,fresh_object_reads=0)
