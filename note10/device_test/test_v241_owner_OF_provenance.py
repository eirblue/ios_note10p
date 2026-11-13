"""New-only fixed caller-domain and already-captured owner body regressions."""
from copy import deepcopy
import v241_owner_OF_provenance as q
from test_v240_guarded_query import graph_data as guarded_fixture
COUNTS=dict(groups=1,variants=14,assertions=14)


def fixture():
    guarded,target,nm,stack,root=guarded_fixture();owner=stack['objects'][q.OWNER_OBJECT];old_name='OUTLINED_FUNCTION_999';name='OUTLINED_FUNCTION_15'
    nm=nm.replace(old_name+' t ',name+' t ');owner['stack_usage']=owner['stack_usage'].replace(':'+old_name+'\t',':'+name+'\t');owner['elf_sections_and_symbols']=owner['elf_sections_and_symbols'].replace(' '+old_name+'\n',' '+name+'\n')
    for key,item in guarded['symbols'].items():
        if item['symbol']==old_name:item['symbol']=name;item['aliases']=[name]
        guarded['assembly'][key]=guarded['assembly'][key].replace('<'+old_name+'>','<'+name+'>')
    source='/ci/work/source/arch/arm64/mm/init.c';caller=q.OWNER_CALLERS[0];nm+=caller+' T 10200 8\n'
    owner['stack_usage']+=source+':1:'+caller+'\t32\tstatic\n';owner['elf_sections_and_symbols']+=' 95: 0000000000000200 8 FUNC GLOBAL DEFAULT 1 '+caller+'\n'
    owner_command=('cmd_arch/arm64/mm/init.o := clang-14 -fstack-usage -fno-strict-aliasing -o arch/arm64/mm/.tmp_init.o -c '+source+'\nsource_arch/arm64/mm/init.o := '+source+'\n')
    owner.update(command=owner_command,command_sha256=q.sha(owner_command.encode()),stack_relative='arch/arm64/mm/.tmp_init.su',stack_sha256=q.sha(owner['stack_usage'].encode()),elf_evidence_sha256=q.sha(owner['elf_sections_and_symbols'].encode()))
    of_source='/ci/work/source/drivers/of/base.c';names=(*q.outlined.ANCHORS,*q.outlined.OUTLINED_NAMES);addresses={n:i*16 for i,n in enumerate(names)}
    cmd=('cmd_'+q.outlined.OBJECT+' := clang-14 -fstack-usage -fno-strict-aliasing -o '+q.outlined.OBJECT+' -c '+of_source+'\nsource_'+q.outlined.OBJECT+' := '+of_source+'\n')
    usage=''.join(of_source+':0:'+n+'\t0\tstatic\n'for n in q.outlined.OUTLINED_NAMES);elf=' [ 1] .text PROGBITS 0000000000000000 000040 000800 00 AX 0 0 4\n'
    for i,n in enumerate(names):
        local=n in q.outlined.OUTLINED_NAMES or n=='__of_find_property';binding='LOCAL'if local else'WEAK'if n=='arch_find_n_match_cpu_physical_id'else'GLOBAL'
        elf+=' '+str(i+1)+': '+format(addresses[n],'016x')+' 8 FUNC '+binding+' DEFAULT 1 '+n+'\n';nm+=n+' '+('t'if local else'W'if binding=='WEAK'else'T')+' '+format(0x90000+addresses[n],'x')+' 8\n'
    nm+='strcmp T a0000 8\n__pi_strcmp T a0000 8\n';table=q.p.linked_symbols(nm)
    guarded['linked_nm_sha256']=q.sha(nm.encode())
    for row in guarded['tools']:row['stdout_sha256']=q.sha(guarded['assembly'][row['key']].encode())
    for row in guarded['symbols'].values():row['aliases']=sorted({n for n,rs in table.items()for v in rs if v['address']==row['address']and v['bytes']==row['bytes']})
    target=deepcopy(target);guarded['target']=target
    anchors={n:dict(object=q.outlined.OBJECT,object_address=addresses[n],linked_address=0x90000+addresses[n],bytes=8,section='.text')for n in q.outlined.ANCHORS}
    edges=[]
    for n in q.outlined.OUTLINED_NAMES:
        row=next(v for v in table[n]if v['address']==0x90000+addresses[n]);edges.append(dict(address=0x90000,target=row['address'],mnemonic='bl',resolved_records=[dict(name=n,**row,offset=0)]))
    assembly={n:dict(external_transfers=edges if n==q.outlined.ANCHORS[0]else[])for n in q.outlined.ANCHORS}
    text='10200 <'+caller+'>:\n 10200: 94000000 bl 10100 <'+name+'>\n 10204: d65f03c0 ret\n'
    symbol=dict(symbol=caller,address=0x10200,bytes=8,aliases=[caller]);assembly[caller]=q.p.transfers(text,symbol,table)
    anchors[caller]=dict(object=q.OWNER_OBJECT,translation_unit=source,object_address=0x200,linked_address=0x10200,bytes=8,binding='GLOBAL',section='.text',frame_bytes=32,frame_kind='static')
    primary=dict(object_provenance=anchors,assembly=assembly)
    raw=dict(objects={q.outlined.OBJECT:dict(command=cmd,stack_usage=usage,elf_sections_and_symbols=elf)},assembly={caller:text},tools=[dict(argv=['aarch64-linux-gnu-readelf','--wide','--sections','--symbols',root+'/'+q.outlined.OBJECT])])
    return raw,primary,stack,nm,guarded,target


def run():
    cases=[]
    def accepted(name,call):cases.append((name,call,True))
    def rejected(name,call):cases.append((name,call,False))
    def check(change=None):
        data=fixture()
        if change:change(*data)
        return q.partition(*data)
    def separate():
        proof=check();owner=proof['owner_reuse'][0];OF=next(v for v in proof['OF']['helpers']if v['symbol']['symbol']=='OUTLINED_FUNCTION_15')
        return len(proof['OF']['helpers'])==13 and owner['nm_record']['name']==OF['nm_record']['name']and owner['target']!=OF['symbol']['address']
    accepted('same spelling preserves strict OF13 and different owner body',separate)
    def unchanged():
        data=fixture();before=deepcopy(data);q.partition(*data);return data==before
    accepted('full primary records and nm multiplicity are not mutated',unchanged)
    accepted('owner reuse retains exact ordinal and call site',lambda:check()['owner_reuse'][0]['call_site']==0x10200 and check()['owner_reuse'][0]['nm_record']['ordinal']>=0)
    accepted('SU0 is not promoted to own-stack0',lambda:check()['owner_reuse'][0]['zero_own_stack_inferred_from_SU']is False)
    def unsupported(raw,primary,*rest):primary['assembly']['unsupported']=primary['assembly'].pop(q.OWNER_CALLERS[0])
    rejected('unlisted outlined caller rejected',lambda:check(unsupported))
    def wrong_TU(raw,primary,stack,*rest):stack['objects'][q.OWNER_OBJECT]['stack_usage']=stack['objects'][q.OWNER_OBJECT]['stack_usage'].replace('/ci/work/source/arch/arm64/mm/init.c','/other/source/arch/arm64/mm/init.c')
    rejected('wrong owner TU rejected',lambda:check(wrong_TU))
    def dynamic(raw,primary,stack,*rest):stack['objects'][q.OWNER_OBJECT]['stack_usage']=stack['objects'][q.OWNER_OBJECT]['stack_usage'].replace(':OUTLINED_FUNCTION_15\t0\tstatic',':OUTLINED_FUNCTION_15\t0\tdynamic')
    rejected('dynamic owner helper SU rejected',lambda:check(dynamic))
    def wrong_ELF(raw,primary,stack,*rest):stack['objects'][q.OWNER_OBJECT]['elf_sections_and_symbols']=stack['objects'][q.OWNER_OBJECT]['elf_sections_and_symbols'].replace('0000000000000100 4 FUNC LOCAL','0000000000000104 4 FUNC LOCAL')
    rejected('wrong owner helper ELF extent rejected',lambda:check(wrong_ELF))
    def ordinal(raw,primary,*rest):primary['assembly'][q.OWNER_CALLERS[0]]['external_transfers'][0]['resolved_records'][0]['ordinal']+=999
    rejected('wrong original nm ordinal rejected',lambda:check(ordinal))
    def interior(raw,primary,*rest):primary['assembly'][q.OWNER_CALLERS[0]]['external_transfers'][0]['resolved_records'][0]['offset']=4
    rejected('interior owner helper entry rejected',lambda:check(interior))
    def missing(raw,primary,stack,nm,guarded,target):guarded['assembly'].pop('owner-outlined@0000000000010100:4')
    rejected('absent existing guarded helper body rejected without new capture',lambda:check(missing))
    def wrong_root(raw,primary,stack,nm,guarded,target):
        for row in guarded['tools']:row['argv'][-1]='/other/objects/vmlinux'
    rejected('jointly moved owner body tools rejected',lambda:check(wrong_root))
    def wrong_OF(raw,primary,*rest):
        edge=next(v for v in primary['assembly'][q.outlined.ANCHORS[0]]['external_transfers']if v['resolved_records'][0]['name']=='OUTLINED_FUNCTION_15');edge['resolved_records'][0]['address']=0x10100
    rejected('OF record cannot borrow same-named owner address',lambda:check(wrong_OF))
    def wrong_delta(raw,primary,stack,nm,guarded,target):
        owner=stack['objects'][q.OWNER_OBJECT];owner['elf_sections_and_symbols']=owner['elf_sections_and_symbols'].replace('0000000000000200 8 FUNC GLOBAL','0000000000000204 8 FUNC GLOBAL');owner['elf_evidence_sha256']=q.sha(owner['elf_sections_and_symbols'].encode());primary['object_provenance'][q.OWNER_CALLERS[0]]['object_address']+=4
    rejected('owner caller must share measured section translation',lambda:check(wrong_delta))
    for name,call,wanted in cases:
        try:actual=call()is not False
        except(ValueError,KeyError,TypeError):actual=False
        if actual is not wanted:raise AssertionError(name)
    q.require(len(cases)==COUNTS['variants'],'exact new-only provenance case count')
    return dict(COUNTS)
