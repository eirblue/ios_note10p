"""New-only synthetic outlined identity/section joins and strict own-stack evidence."""
from copy import deepcopy
import v237_outlined_evidence as p

COUNTS=dict(groups=1,variants=27,assertions=27)


def run():
    cases=[]
    def accepted(name,call):cases.append((name,call,True))
    def rejected(name,call):cases.append((name,call,False))
    source='/ci/work/source/drivers/of/base.c';delta=0x10000
    names=(*p.ANCHORS,*p.OUTLINED_NAMES);addresses={name:i*16 for i,name in enumerate(names)}
    cmd=('cmd_'+p.OBJECT+' := clang-14 -fstack-usage -fno-strict-aliasing -o '+p.OBJECT+' -c '+source+'\nsource_'+p.OBJECT+' := '+source+'\n').encode()
    usage=''.join(source+':0:'+name+'\t0\tstatic\n'for name in p.OUTLINED_NAMES)
    elf=' [ 1] .text PROGBITS 0000000000000000 000040 000800 00 AX 0 0 4\n'
    nm=''
    for i,name in enumerate(names):
        local=name in p.OUTLINED_NAMES or name=='__of_find_property'
        binding='LOCAL'if local else'WEAK'if name=='arch_find_n_match_cpu_physical_id'else'GLOBAL'
        elf+=' '+str(i+1)+': '+format(addresses[name],'016x')+' 8 FUNC '+binding+' DEFAULT 1 '+name+'\n'
        nm+=name+' '+('t'if local else'W'if binding=='WEAK'else'T')+' '+format(delta+addresses[name],'x')+' 8\n'
    # Same name in a different input object must never replace the exact called row.
    nm+='OUTLINED_FUNCTION_0 t 90000 8\nstrcmp T a0000 8\n__pi_strcmp T a0000 8\n'
    table=p.retained.linked_symbols(nm)
    anchors={name:dict(object=p.OBJECT,object_address=addresses[name],linked_address=delta+addresses[name],bytes=8,section='.text')for name in p.ANCHORS}
    edges=[]
    for name in p.OUTLINED_NAMES:
        record=table[name][0]
        edges.append(dict(address=delta,target=record['address'],mnemonic='bl',resolved_records=[dict(name=name,**record,offset=0)]))
    assembly={name:dict(symbol=dict(symbol=name,address=delta+addresses[name],bytes=8,aliases=[name]),external_transfers=edges if name==p.ANCHORS[0]else[])for name in p.ANCHORS}
    strcmp=p.retained.extent(table,'strcmp')
    assembly['strcmp']=dict(symbol=strcmp,alias_records=[dict(name=name,**table[name][0])for name in ('strcmp','__pi_strcmp')],external_transfers=[])
    primary=dict(object_provenance=anchors,assembly=assembly)
    item=dict(command=cmd.decode(),stack_usage=usage,elf_sections_and_symbols=elf)
    raw_primary=dict(objects={p.OBJECT:item},assembly={'strcmp':'00000000000a0000 <__pi_strcmp>:\n a0000: eb01001f cmp x0, x1\n a0004: d65f03c0 ret\n'},
        tools=[dict(argv=['aarch64-linux-gnu-readelf','--wide','--sections','--symbols','/ci/work/objects/'+p.OBJECT])])
    def joins(raw=raw_primary,proof=primary,text=nm):return p.outline_joins(raw,proof,text)
    def complete_join():
        proof=joins();return len(proof['helpers'])==13 and proof['linked_minus_object_address']==delta
    accepted('thirteen exact local addresses join one nine-anchor section',complete_join)
    accepted('unrelated duplicate name cannot replace called local record',lambda:next(row for row in joins()['helpers']if row['symbol']['symbol']=='OUTLINED_FUNCTION_0')['symbol']['address']==delta+addresses['OUTLINED_FUNCTION_0'])
    def split_anchor():
        raw=deepcopy(raw_primary);proof=deepcopy(primary);name=p.ANCHORS[0]
        raw['objects'][p.OBJECT]['elf_sections_and_symbols']=elf.replace('1: 0000000000000000 8 FUNC','1: 0000000000000004 8 FUNC',1)
        proof['object_provenance'][name]['object_address']+=4
        return joins(raw,proof)
    rejected('different measured anchor translations fail',split_anchor)
    def helper_section():
        raw=deepcopy(raw_primary);name=p.OUTLINED_NAMES[0]
        raw['objects'][p.OBJECT]['elf_sections_and_symbols']=elf.replace('DEFAULT 1 '+name,'DEFAULT 2 '+name)+' [ 2] .text.other PROGBITS 0000000000000000 000900 000008 00 AX 0 0 4\n'
        return joins(raw)
    rejected('helper from another input section rejected',helper_section)
    def changed_usage(before,after):
        raw=deepcopy(raw_primary);raw['objects'][p.OBJECT]['stack_usage']=usage.replace(before,after,1);return joins(raw)
    rejected('wrong helper TU rejected',lambda:changed_usage(source+':0:'+p.OUTLINED_NAMES[0],'/other/source/drivers/of/base.c:0:'+p.OUTLINED_NAMES[0]))
    rejected('dynamic helper frame rejected',lambda:changed_usage('\t0\tstatic','\t0\tdynamic'))
    rejected('missing helper frame never becomes zero',lambda:changed_usage(source+':0:'+p.OUTLINED_NAMES[0]+'\t0\tstatic\n',''))
    def wrong_identity():
        proof=deepcopy(primary);proof['assembly'][p.ANCHORS[0]]['external_transfers'][0]['resolved_records'][0]['ordinal']+=1000;return joins(proof=proof)
    rejected('wrong actual nm ordinal rejected',wrong_identity)
    def wrong_extent():
        proof=deepcopy(primary);proof['assembly'][p.ANCHORS[0]]['external_transfers'][0]['resolved_records'][0]['bytes']=12;return joins(proof=proof)
    rejected('wrong called extent rejected',wrong_extent)
    def foreign_caller():
        proof=deepcopy(primary);proof['assembly']['not-an-OF-anchor']=proof['assembly'].pop(p.ANCHORS[0]);return joins(proof=proof)
    rejected('non-OF caller cannot widen inventory',foreign_caller)
    helper=joins()['helpers'][0];symbol=helper['symbol'];address=symbol['address']
    def body(first='d503201f nop'):
        return format(address,'016x')+' <'+symbol['symbol']+'>:\n '+format(address,'x')+': '+first+'\n '+format(address+4,'x')+': d65f03c0 ret\n'
    accepted('strict actual helper leaf and SU0 prove own stack0',lambda:p.classify_leaf(body(),symbol,table,0)['zero_own_stack_proven']is True)
    accepted('SP use remains unknown despite compiler SU0',lambda:p.classify_leaf(body('910003e0 mov x0, sp'),symbol,table,0)['own_stack_bytes']is None)
    accepted('WSP alias also remains unknown',lambda:p.classify_leaf(body('110003e0 mov w0, wsp'),symbol,table,0)['zero_own_stack_proven']is False)
    accepted('external call remains unknown without recursive expansion',lambda:p.classify_leaf(body('94000000 bl 90000 <OUTLINED_FUNCTION_0>'),symbol,table,0)['classification']=='unknown')
    accepted('indirect transfer remains unknown',lambda:p.classify_leaf(body('d61f0000 br x0'),symbol,table,0)['classification']=='unknown')
    accepted('trap remains unknown',lambda:p.classify_leaf(body('d4000001 svc #0'),symbol,table,0)['classification']=='unknown')
    def nonzero_frame():
        proof=p.classify_leaf(body(),symbol,table,16);return proof['compiler_static_frame_bytes']==16 and proof['own_stack_bytes']is None
    accepted('nonzero compiler frame is preserved as unknown',nonzero_frame)
    accepted('internal branch only stays bounded to actual instructions',lambda:p.classify_leaf(body('14000001 b '+format(address+4,'x')),symbol,table,0)['zero_own_stack_proven']is True)
    rejected('incomplete helper body rejected',lambda:p.classify_leaf(body().splitlines()[0]+'\n',symbol,table,0))
    rejected('arbitrary helper alias label rejected',lambda:p.classify_leaf(body().replace('<'+symbol['symbol']+'>:','<unbound>:'),symbol,table,0))
    accepted('strcmp and __pi alias use one existing complete body',lambda:p.classify_leaf(raw_primary['assembly']['strcmp'],strcmp,table,None)['zero_own_stack_proven']is True)
    rejected('only fixed helper or strcmp namespace accepted',lambda:p.classify_leaf(body(),{**symbol,'symbol':'arbitrary'},table,0))
    accepted('helper argv is an exact bounded range of same ELF',lambda:p.helper_command('/ci/work/objects/vmlinux',symbol)==['aarch64-linux-gnu-objdump','-d','--disassemble-zeroes','--start-address='+hex(address),'--stop-address='+hex(address+8),'/ci/work/objects/vmlinux'])
    rejected('oversized helper capture rejected',lambda:p.helper_command('/ci/work/objects/vmlinux',{**symbol,'bytes':260}))
    bundle=dict(schema=p.RAW_SCHEMA,primary=raw_primary,outlined_assembly={},tools=[])
    for row in joins()['helpers']:
        s=row['symbol'];a=s['address'];text=format(a,'016x')+' <'+s['symbol']+'>:\n '+format(a,'x')+': d503201f nop\n '+format(a+4,'x')+': d65f03c0 ret\n'
        bundle['outlined_assembly'][row['identity']]=text
        bundle['tools'].append(dict(argv=p.helper_command('/ci/work/objects/vmlinux',s),returncode=0,stdout_sha256=p.sha(text.encode()),stderr=''))
    def full():
        proof=p.finish(bundle,dict(linked_nm=nm),primary)
        return proof['outlined_capture_count']==13 and proof['lookup_runtime_bound_proven']is False and proof['runtime_hook_allowed']is False and proof['recursive_expansion']is False
    accepted('full new-only reader preserves explicit nonauthority',full)
    def wrong_tool():
        raw=deepcopy(bundle);raw['tools'][0]['argv'][-1]='/other/objects/vmlinux';return p.finish(raw,dict(linked_nm=nm),primary)
    rejected('different ELF helper capture rejected',wrong_tool)
    def wrong_strcmp_alias():
        proof=deepcopy(primary);proof['assembly']['strcmp']['alias_records'][1]['address']+=4;return p.finish(bundle,dict(linked_nm=nm),proof)
    rejected('strcmp alias must bind exact existing body',wrong_strcmp_alias)
    for name,call,wanted in cases:
        try:actual=call()is not False
        except(ValueError,KeyError,TypeError):actual=False
        if actual is not wanted:raise AssertionError(name)
    if len(cases)!=COUNTS['variants']:raise AssertionError('new outlined case count')
    return dict(COUNTS)
