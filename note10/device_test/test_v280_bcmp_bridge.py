"""One synthetic bridge conjunction; no claim about missing actual279 bytes."""
import copy
import v280_native_prepare as p

def refused(fn,*args):
    try:fn(*args)
    except (ValueError,KeyError):return True
    return False

def predicate():
    source='/synthetic/source/lib/string.c';target=p.STRING_TARGET
    command='cmd_'+target+' := clang-14 -fstack-usage -fno-strict-aliasing -fno-optimize-sibling-calls -o '+target+' -c '+source+'\nsource_'+target+' := '+source+'\n'
    usage=source+':905:1:bcmp\t16\tstatic\n'
    elf=' [ 1] .text PROGBITS 00000000 000040 000014 00 AX 0 0 4\n 1: 0000000000000000 20 FUNC GLOBAL DEFAULT 1 bcmp\n'
    prior=dict(command=command,command_sha256=p.sha(command.encode()),stack_usage=usage,stack_sha256=p.sha(usage.encode()),stack_relative='lib/string.su',elf_sections_and_symbols=elf,elf_evidence_sha256=p.sha(elf.encode()))
    item=p.string_item(prior,'bcmp T 0 14\n','0'*64)
    table={'bcmp':[dict(kind='T',address=4096,bytes=20,ordinal=0)],'memcmp':[dict(kind='T',address=8192,bytes=4,ordinal=1)]}
    context,roots,unused=p.provenance(target,('bcmp',),item,table)
    symbol=p.scoped.symbol_extent(table,'bcmp',dict(name='bcmp',**table['bcmp'][0],offset=0))
    text='''0000000000001000 <bcmp>:
 1000: a9bf7bfd stp x29, x30, [sp, #-16]!
 1004: 910003fd mov x29, sp
 1008: 94000400 bl 2000 <memcmp>
 100c: a8c17bfd ldp x29, x30, [sp], #16
 1010: d65f03c0 ret
'''
    leaves={(8192,4):dict(symbol='memcmp',address=8192,bytes=4,aliases=['memcmp'])}
    incoming=dict(mnemonic='bl',unresolved=False,target=4096,address=2048,resolved_symbols=['bcmp'],resolved_records=[dict(name='bcmp',**table['bcmp'][0],offset=0)])
    assert p.edge_target(incoming,leaves)[0]=='body'
    for field,value in (('offset',4),('bytes',24),('kind','W')):
        bad=copy.deepcopy(incoming);bad['resolved_records'][0][field]=value
        assert refused(p.edge_target,bad,leaves)
    def cert(proof=roots['bcmp'],body=text,nm=table,leaf=leaves,digest=p.STRING_SOURCE_SHA):
        return p.bcmp_certificate(proof,symbol,body,nm,leaf,digest)
    accepted=cert()
    assert accepted['frame_certificate']['own_peak_bytes']==16 and accepted['frame_certificate']['call_SP_offsets']=={4104:-16}and not accepted['local_edges']
    for field,value in (('translation_unit','/synthetic/source/wrong.c'),('object',p.OWNER_TARGET),('bytes',24)):
        bad=copy.deepcopy(roots['bcmp']);bad[field]=value;assert refused(cert,bad)
    for field,value in (('bytes',0),('kind','dynamic')):
        bad=copy.deepcopy(roots['bcmp']);bad['frame'][field]=value;assert refused(cert,bad)
    bad=dict(item,usage=usage.replace('\t16\t','\t0\t'))
    _,badroots,_=p.provenance(target,('bcmp',),bad,table)
    assert refused(cert,badroots['bcmp'])
    assert refused(p.provenance,target,('bcmp',),dict(item,elf=elf.replace('00 AX','00 WA')),table)
    assert refused(p.string_item,{**prior,'stack_sha256':'0'*64},item['nm'],'0'*64)
    assert refused(cert,roots['bcmp'],text,table,leaves,'0'*64)
    assert refused(cert,roots['bcmp'],text.replace('bl 2000 <memcmp>','blr x0'))
    assert refused(cert,roots['bcmp'],text.replace('stp x29, x30, [sp, #-16]!','sub sp, sp, #32'))
    badtable=copy.deepcopy(table);badtable['foreign']=[dict(kind='T',address=12288,bytes=4,ordinal=2)]
    assert refused(cert,roots['bcmp'],text.replace('bl 2000 <memcmp>','bl 3000 <foreign>'),badtable)
    badtable=copy.deepcopy(table);badtable['memcmp'][0]['bytes']=8
    assert refused(cert,roots['bcmp'],text.replace('bl 2000 <memcmp>','bl 2004 <memcmp+0x4>'),badtable)
    badtable=copy.deepcopy(table);badtable['foreign_alias']=[dict(kind='T',address=8192,bytes=8,ordinal=2)]
    assert refused(cert,roots['bcmp'],text,badtable)
    assert (p.NAMED_CAP,p.OUTLINED_CAP,p.EXTENT_CAP)==(14,30,44)
    return dict(passed=True,groups=1,variants=1,assertions=1)
