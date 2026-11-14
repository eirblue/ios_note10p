"""Five new synthetic caller argument/CFG predicates; no prior proof execution."""
import hashlib
import struct


def sample(change=None):
    words=[0xaa0003f4,0xaa0103f3,0x94000000,0x37000048,0xd503201f,0xd503201f,0xaa1403e0,0xaa1303e1,0x94000000,0xd65f03c0]
    mnemonics=['mov','mov','bl','tbnz','nop','nop','mov','mov','bl','ret'];operands=['x20, x0','x19, x1','0 <opaque_helper>','w8, #0, 114 <__switch_to+0x14>','','','x0, x20','x1, x19','0 <cpu_switch_to>','']
    if change=='w19':words[5]=0x2a1f03f3;mnemonics[5]='mov';operands[5]='w19, wzr'
    if change=='pair_second':words[5]=0xa94053e8;mnemonics[5]='ldp';operands[5]='x8, x20, [sp]'
    if change=='relocated_B':words[4]=0x14000001;mnemonics[4]='b';operands[4]='114 <__switch_to+0x14>'
    if change=='bypass':words[6]=0x14000002;mnemonics[6]='b';operands[6]='120 <__switch_to+0x20>'
    if change=='wrong_source':words[7]=0xaa1403e1;operands[7]='x1, x20'
    text='0000000000000100 <__switch_to>:\n'+''.join(f' {0x100+4*i:x}: {word:08x} {mnemonics[i]} {operands[i]}\n'for i,word in enumerate(words));target=dict(index=2,name='cpu_switch_to',type=0,binding=1,section=0,value=0,bytes=0,visibility=0);helper=dict(index=1,name='opaque_helper',type=0,binding=1,section=0,value=0,bytes=0,visibility=0)
    boundary=dict(offset=32,type=283,symbol_index=2,target=target,addend=0,mnemonic='bl');proof=dict(provider=dict(name='__switch_to',value=0x100,bytes=40),body_sha256=hashlib.sha256(b''.join(struct.pack('<I',w)for w in words)).hexdigest(),backend_boundary=boundary,selected_relocations=[dict(offset=8,type=283,symbol_index=1,target=helper,addend=0),{k:v for k,v in boundary.items()if k!='mnemonic'}]);source='struct task_struct *__switch_to(struct task_struct *prev, struct task_struct *next) { return cpu_switch_to(prev,next); }'
    if change=='relocated_B':proof['selected_relocations'].append(dict(offset=16,type=282,symbol_index=3,target=dict(index=3,name='external_branch_target',type=0,binding=1,section=0,value=0,bytes=0,visibility=0),addend=0))
    return text,proof,source


def run(helper):
    cases=(('valid_conditional_two_pointer_flow',None),('w19_pointer_clobber_rejected','w19'),('LDP_second_x20_destination_rejected','pair_second'),('argument_setup_bypass_rejected','bypass'),('wrong_backend_argument_source_rejected','wrong_source'));completed=[]
    try:
        for name,change in cases:
            if change is None:
                result=helper.prove(*sample());ok=result['argument_mapping_at_backend_call_under_ABI_contract']is True and result['machine_argument_register_flow_proven']is result['switch_resume_contract_proven']is False and len(result['opaque_helper_contracts'])==1
            else:
                # One branch-admissibility verdict: both setup bypass and relocation ambiguity must reject.
                ok=True
                for mutation in (('bypass','relocated_B')if change=='bypass'else(change,)):
                    try:helper.prove(*sample(mutation))
                    except ValueError:pass
                    else:ok=False
            if not ok:raise ValueError('new argument predicate failed: '+name)
            completed.append(name)
    except BaseException as error:
        error.fixture_progress=dict(groups=1,variants=5,assertions=5,completed_variants=len(completed),completed_assertions=len(completed),case_names=completed);raise
    return dict(groups=1,variants=5,assertions=5,completed_variants=5,completed_assertions=5,case_names=completed,host_processes=0,disassembly_reads=0,provider_source_reads=0,fresh_object_reads=0)
