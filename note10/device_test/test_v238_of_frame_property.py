"""New-only borrowed-frame and bounded property-frontier synthetic cases."""
from copy import deepcopy
import v238_of_frame_property as p

COUNTS=dict(groups=1,variants=38,assertions=38)


def run():
    cases=[]
    def accepted(name,call):cases.append((name,call,True))
    def rejected(name,call):cases.append((name,call,False))
    def dis(name,start,ops):
        return format(start,'016x')+' <'+name+'>:\n'+''.join(' '+format(start+4*i,'x')+': d503201f '+op+'\n'for i,op in enumerate(ops))
    helper=dict(symbol='OUTLINED_FUNCTION_0',address=0x4000,bytes=16,aliases=['OUTLINED_FUNCTION_0'])
    caller=dict(symbol='of_find_property',address=0x1000,bytes=32,aliases=['of_find_property'])
    table=p.p.linked_symbols('of_find_property T 1000 20\nOUTLINED_FUNCTION_0 t 4000 10\n')
    helper_ops=['ldr x23, [sp, #16]','ldp x22, x21, [sp, #32]','ldp x20, x19, [sp, #48]','ret']
    caller_ops=['stp x29, x30, [sp, #-64]!','mov x29, sp','str x23, [sp, #16]','bl 4000','nop','nop','ldp x29, x30, [sp], #64','ret']
    def effect(ops=helper_ops):
        text=dis(helper['symbol'],helper['address'],ops);return p.borrowed_helper(text,p.p.transfers(text,helper,table))
    def coverage(ops=caller_ops,frame=64,e=None,sites=None):
        text=dis(caller['symbol'],caller['address'],ops)
        return p.caller_coverage(text,p.p.transfers(text,caller,table),frame,[dict(address=0x100c)]if sites is None else sites,helper,effect()if e is None else e)
    def known_effect():
        row=effect();return row['SP_delta_bytes']==0 and row['additional_below_entry_SP_depth_bytes']==0 and row['read_extent_max_bytes']==64 and row['zero_own_stack_proven']is False
    accepted('constant borrowed loads prove effects not own allocation0',known_effect)
    accepted('actual helper BL and caller allocated frame cover loads',lambda:coverage()['proven']is True)
    def changed_helper(op):return effect([op,*helper_ops[1:]])
    accepted('helper postindex writeback stays unknown',lambda:changed_helper('ldr x23, [sp], #16')['understood']is False)
    accepted('helper SP arithmetic stays unknown',lambda:changed_helper('add sp, sp, #16')['SP_delta_bytes']is None)
    accepted('dynamic SP index stays unknown',lambda:changed_helper('ldr x23, [sp, x0]')['understood']is False)
    accepted('helper store is outside read-only shape',lambda:changed_helper('str x23, [sp, #16]')['understood']is False)
    accepted('helper cannot replace the normal return link',lambda:changed_helper('ldr x30, [sp, #16]')['understood']is False)
    accepted('helper call remains unknown',lambda:changed_helper('bl 5000')['understood']is False)
    def changed_caller(index,op):
        ops=list(caller_ops);ops[index]=op;return coverage(ops)
    accepted('allocation reentry is not frame coverage',lambda:changed_caller(4,'b 1000')['proven']is False)
    accepted('skipped allocation is not frame coverage',lambda:changed_caller(0,'nop')['proven']is False)
    accepted('branch bypass of deallocation is rejected',lambda:changed_caller(4,'b 101c')['proven']is False)
    accepted('missing deallocation is not frame coverage',lambda:changed_caller(6,'nop')['proven']is False)
    accepted('other SP write is not stable frame coverage',lambda:changed_caller(4,'mov sp, x0')['proven']is False)
    accepted('indirect caller control stays unknown',lambda:changed_caller(4,'br x0')['proven']is False)
    accepted('internal BL cannot skip the normal C-entry shape',lambda:changed_caller(4,'bl 101c')['proven']is False)
    accepted('unresolved caller transfer stays unknown',lambda:changed_caller(4,'bl 5000')['proven']is False)
    accepted('SU and actual allocation must agree',lambda:coverage(frame=48)['proven']is False)
    accepted('helper loads must fit caller interval',lambda:coverage(e=changed_helper('ldr x23, [sp, #80]'))['proven']is False)
    accepted('missing actual helper call-site is not coverage',lambda:coverage(sites=[])['proven']is False)
    def incomplete():
        text=dis(helper['symbol'],helper['address'],helper_ops);proof=p.p.transfers(text,helper,table);text='\n'.join(text.splitlines()[:-1])+'\n';proof['disassembly_sha256']=p.sha(text.encode());return p.borrowed_helper(text,proof)
    rejected('incomplete helper instructions rejected',incomplete)
    source='/ci/work/source/drivers/of/property.c'
    cmd=('cmd_'+p.OBJECT+' := clang-14 -fstack-usage -fno-strict-aliasing -o drivers/of/.tmp_property.o -c '+source+'\nsource_'+p.OBJECT+' := '+source+'\n').encode()
    nm=p.PUBLIC+' T 8000 8\n'+p.STATIC+' t 8010 8\nOUTLINED_FUNCTION_0 t 8040 8\nOUTLINED_FUNCTION_0 t 9000 8\n'
    prop_table=p.p.linked_symbols(nm)
    usage=source+':1:'+p.PUBLIC+'\t32\tstatic\n'+source+':2:'+p.STATIC+'\t32\tstatic\n'+source+':0:OUTLINED_FUNCTION_0\t0\tstatic\n'
    elf=' [ 1] .text PROGBITS 0000000000000000 000040 000080 00 AX 0 0 4\n 1: 0000000000000000 8 FUNC GLOBAL DEFAULT 1 '+p.PUBLIC+'\n 2: 0000000000000010 8 FUNC LOCAL DEFAULT 1 '+p.STATIC+'\n 3: 0000000000000040 8 FUNC LOCAL DEFAULT 1 OUTLINED_FUNCTION_0\n'
    item=dict(command=cmd.decode(),command_sha256=p.sha(cmd),stack_usage=usage,stack_sha256=p.sha(usage.encode()),stack_relative='drivers/of/.tmp_property.su',elf_sections_and_symbols=elf,elf_evidence_sha256=p.sha(elf.encode()))
    accepted('new property anchors join exact cmd/TU/SU/ELF/nm',lambda:p.property_target(item,prop_table)[0]['linked_minus_object_address']==0x8000)
    def change_item(field,before,after):
        row=deepcopy(item);row[field]=row[field].replace(before,after,1)
        key={'command':'command_sha256','stack_usage':'stack_sha256','elf_sections_and_symbols':'elf_evidence_sha256'}[field];row[key]=p.sha(row[field].encode());return p.property_target(row,prop_table)
    rejected('wrong property TU rejected',lambda:change_item('stack_usage',source,'/other/source/drivers/of/property.c'))
    rejected('dynamic property C frame rejected',lambda:change_item('stack_usage','32\tstatic','32\tdynamic'))
    rejected('property ELF size cannot differ from linked record',lambda:change_item('elf_sections_and_symbols','0000000000000000 8 FUNC','0000000000000000 12 FUNC'))
    rejected('ambiguous property C symbol rejected',lambda:p.property_target(item,p.p.linked_symbols(nm+p.PUBLIC+' T a000 8\n')))
    public_text=dis(p.PUBLIC,0x8000,['bl 8010','ret']);static_text=dis(p.STATIC,0x8010,['bl 8040','ret'])
    C={p.PUBLIC:p.p.transfers(public_text,p.c_symbol(prop_table,p.PUBLIC),prop_table),p.STATIC:p.p.transfers(static_text,p.c_symbol(prop_table,p.STATIC),prop_table)}
    target,functions=p.property_target(item,prop_table);joined=p.local_joins(item,target,functions,C,prop_table)
    accepted('local target uses exact address despite duplicate global name',lambda:len(joined)==1 and next(iter(joined.values()))['symbol']['address']==0x8040)
    def wrong_ordinal():
        changed=deepcopy(C);changed[p.STATIC]['external_transfers'][0]['resolved_records'][0]['ordinal']+=100;return p.local_joins(item,target,functions,changed,prop_table)
    rejected('local helper original ordinal required',wrong_ordinal)
    def wrong_section():
        changed=deepcopy(functions);changed['OUTLINED_FUNCTION_0']['section_index']='2';return p.local_joins(item,target,changed,C,prop_table)
    rejected('local helper must share measured input section',wrong_section)
    def dynamic_local():
        row=deepcopy(item);row['stack_usage']=usage.replace(':0:OUTLINED_FUNCTION_0\t0\tstatic',':0:OUTLINED_FUNCTION_0\t0\tdynamic');return p.local_joins(row,target,functions,C,prop_table)
    rejected('dynamic local helper never supplies a static frame',dynamic_local)
    accepted('only actually reached static C helper is selected',lambda:p.reaches_static({p.PUBLIC:C[p.PUBLIC]},prop_table)is True)
    accepted('no invented static C edge when absent',lambda:p.reaches_static({},prop_table)is False)
    local_key=next(iter(joined));local_text=dis('OUTLINED_FUNCTION_0',0x8040,['nop','ret'])
    raw=dict(schema=p.RAW_SCHEMA,retained=None,property_object=item,assembly={p.PUBLIC:public_text,p.STATIC:static_text,local_key:local_text},tools=[])
    raw['tools'].append(dict(capture_id='object',argv=['aarch64-linux-gnu-readelf','--wide','--sections','--symbols','/ci/work/objects/'+p.OBJECT],returncode=0,stdout_sha256=p.sha(elf.encode()),stderr=''))
    for name,text in ((p.PUBLIC,public_text),(p.STATIC,static_text)):
        raw['tools'].append(dict(capture_id=name,argv=p.property_command('/ci/work/objects/vmlinux',p.c_symbol(prop_table,name)),returncode=0,stdout_sha256=p.sha(text.encode()),stderr=''))
    raw['tools'].append(dict(capture_id=local_key,argv=p.property_command('/ci/work/objects/vmlinux',joined[local_key]['symbol'],('OUTLINED_FUNCTION_0',)),returncode=0,stdout_sha256=p.sha(local_text.encode()),stderr=''))
    accepted('new full property reader binds one object and actual bodies',lambda:p.property_evidence(raw,dict(linked_nm=nm),'/ci/work/objects')['static_C_body_captured']is True)
    def no_static():
        row=deepcopy(raw);text=dis(p.PUBLIC,0x8000,['nop','ret']);row['assembly']={p.PUBLIC:text};row['tools']=row['tools'][:2];row['tools'][1]['stdout_sha256']=p.sha(text.encode());return p.property_evidence(row,dict(linked_nm=nm),'/ci/work/objects')
    accepted('zero direct locals and unreached static body need no dump',lambda:no_static()['static_C_body_captured']is False)
    def wrong_tool():
        row=deepcopy(raw);row['tools'][-1]['argv'][-1]='/other/objects/vmlinux';return p.property_evidence(row,dict(linked_nm=nm),'/ci/work/objects')
    rejected('different ELF body capture rejected',wrong_tool)
    def jointly_moved():
        row=deepcopy(raw)
        for tool in row['tools']:tool['argv'][-1]=tool['argv'][-1].replace('/ci/work/objects/','/other/objects/')
        return p.property_evidence(row,dict(linked_nm=nm),'/ci/work/objects')
    rejected('jointly moved object and all bodies cannot leave retained Image root',jointly_moved)
    def duplicate_tool():
        row=deepcopy(raw);row['tools'].append(row['tools'][0]);return p.property_evidence(row,dict(linked_nm=nm),'/ci/work/objects')
    rejected('duplicate new capture rejected',duplicate_tool)
    def unexpected_body():
        row=deepcopy(raw);row['assembly']['unrelated']=local_text;return p.property_evidence(row,dict(linked_nm=nm),'/ci/work/objects')
    rejected('unreviewed extra body cannot expand frontier',unexpected_body)
    rejected('oversized local extent rejected',lambda:p.property_command('/ci/work/objects/vmlinux',{**joined[local_key]['symbol'],'bytes':260},('OUTLINED_FUNCTION_0',)))
    for name,call,wanted in cases:
        try:actual=call()is not False
        except(ValueError,KeyError,TypeError):actual=False
        if actual is not wanted:raise AssertionError(name)
    if len(cases)!=COUNTS['variants']:raise AssertionError('new frame/property case count')
    return dict(COUNTS)
