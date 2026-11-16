"""280 proves the existing compiler-generated bcmp bridge as a real C node."""
import hashlib,json,re,subprocess
from collections import deque
from pathlib import Path
from types import SimpleNamespace
import v279_native_prepare as retained
p,require,sha=retained.p,retained.require,retained.sha
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
WORKFLOW='.github/workflows/note10-v280-native-prepare.yml';JOB='v280-native-prepare'
BUILD_SCHEMA='note10-v280-holder-carrier-build-v1'
CONTEXT_SCHEMA='note10-v280-holder-carrier-public-input-v1'
MANIFEST_SCHEMA='note10-v280-holder-carrier-sealed-members-v1'
CAPTURE_SCHEMA=retained.CAPTURE_SCHEMA
SUCCESS_MEMBERS=retained.SUCCESS_MEMBERS
OWNER_TARGET,SEAL_TARGET,OWNER=retained.OWNER_TARGET,retained.SEAL_TARGET,retained.OWNER
VALIDATORS,SOURCE_HELPERS=retained.VALIDATORS,retained.SOURCE_HELPERS
STRING_TARGET='lib/string.o'
STRING_SOURCE_SHA='fc869eb46f5d63ce7c894f2a6b4ca3c996899a4241691373df81c5a0cf1a8ccb'
NAMED=(*retained.NAMED,'bcmp');NAMED_CAP,OUTLINED_CAP,EXTENT_CAP=14,30,44
DOMAIN=((OWNER_TARGET,(OWNER,'n279_layout_witness',*VALIDATORS)),(SEAL_TARGET,('n278_seal_once',)),(STRING_TARGET,('bcmp',)))
scoped=retained.scoped
provenance,storage=retained.provenance,retained.storage
install_binding,owner_overlay,decode_binding=retained.install_binding,retained.owner_overlay,retained.decode_binding
bind=retained.bind
_FRAME_ENV={**retained.own_frame.__globals__,'ROOTS':NAMED}
own_frame=bind(retained.own_frame,_FRAME_ENV)
_STACK_ENV={**retained.stack_once.__globals__,'_STACK':{}}
stack_once=bind(retained.stack_once,_STACK_ENV)
stream_candidate=SimpleNamespace(**{**vars(retained.stream_candidate),'verify_stack_evidence':stack_once})
NEW_FILES=('v280_native_prepare.py','test_v280_bcmp_bridge.py')
CARRIED279={'passed': True, 'groups': 1, 'variants': 2, 'assertions': 2, 'host_compile_attempts': 1, 'host_fixture_process_attempts': 1, 'source_head': '446e4477d8321f80924b45cb2029d615a1bfd1f1', 'result_sha256': 'efed3740d19848389ffe7dcb3c3a87fc8f9fdf4ae9a720435d29985fe02a0954', 'replayed': False}

def source_pins():
    pins=retained.source_pins();pins.pop(retained.WORKFLOW)
    pins.update({'note10/device_test/'+n:sha(p.ordinary(HERE/n))for n in NEW_FILES})
    pins[WORKFLOW]=sha(p.ordinary(ROOT/WORKFLOW));return pins

def public_context(head,passed):
    p.hexid(head,40)
    require(set(passed)=={'passed','groups','variants','assertions','result_sha256'}and passed['passed']is True and tuple(passed[k]for k in ('groups','variants','assertions'))==(1,1,1),'one new Python bcmp bridge conjunction')
    p.hexid(passed['result_sha256'])
    return dict(schema=CONTEXT_SCHEMA,source_head=head,source_sha256=source_pins(),new_fixture_PASS=passed,carried279_fixture_PASS=CARRIED279)

def string_item(old,nm,object_sha256):
    require(type(old)is dict and set(old)=={'command','command_sha256','stack_usage','stack_sha256','stack_relative','elf_sections_and_symbols','elf_evidence_sha256'}and all(type(v)is str for v in old.values())and type(nm)is str and type(object_sha256)is str and re.fullmatch('[0-9a-f]{64}',object_sha256),'actual retained lib/string stack schema/types')
    require(sha(old['command'].encode())==old['command_sha256']and sha(old['stack_usage'].encode())==old['stack_sha256']and sha(old['elf_sections_and_symbols'].encode())==old['elf_evidence_sha256'],'actual string command/SU/ELF bytes')
    return dict(command=old['command'],command_sha256=old['command_sha256'],usage=old['stack_usage'],usage_sha256=old['stack_sha256'],stack_relative=old['stack_relative'],elf=old['elf_sections_and_symbols'],nm=nm,object_sha256=object_sha256)

def edge_target(edge,leaves):
    rows=edge['resolved_records']
    if any(r['name']=='bcmp'for r in rows):
        require(edge['mnemonic']in('bl','b')and not edge['unresolved']and edge['resolved_symbols']==['bcmp']and len(rows)==1 and rows[0]['kind']=='T'and rows[0]['offset']==0 and rows[0]['address']==edge['target']and rows[0]['bytes']==20,'exact distinct bcmp entry/extent, never leaf alias')
        return 'body',(rows,False)
    return retained.edge_target(edge,leaves)

def bcmp_certificate(provenance,symbol,text,table,leaves,source_sha256):
    frame=provenance['frame']
    require(source_sha256==STRING_SOURCE_SHA and provenance['object']==STRING_TARGET and provenance['translation_unit'].endswith('/lib/string.c')and frame['source']==provenance['translation_unit']and frame['kind']=='static'and frame['bytes']==16 and provenance['binding']=='GLOBAL'and provenance['bytes']==symbol['bytes']==20 and provenance['linked_address']==symbol['address'],'actual pinned third-TU bcmp20/frame16')
    proof=scoped.scoped_transfers(text,symbol,table)
    require(len(proof['external_transfers'])==1,'one actual bcmp callee only')
    edge=proof['external_transfers'][0];kind,key=edge_target(edge,leaves)
    require(kind=='leaf'and leaves[key]['symbol']=='memcmp','bcmp must reach the current certified memcmp extent')
    certificate=own_frame('bcmp',scoped.flow.parse_body(text,proof),{edge['address']:'leaf:memcmp'},16,False)
    require(certificate['own_peak_bytes']==16,'bcmp contributes16, not leaf0')
    return dict(proof=proof,frame_certificate=certificate,local_edges={},certified_memcmp=edge)

def verify_seal(raw,linked,stack_data,profile,binding):
    require(raw['schema']=='note10-v280-seal-raw-v1'and raw['complete']is True and raw['linked_nm_sha256']==sha(linked.encode())and raw['compiler_input_binding']==binding,'actual complete new seal capture')
    require(profile.get('LTO_NONE')=='y'and profile.get('LTO','n')=='n','actual LTO_NONE, no cross-TU LTO inference')
    table=scoped.reader.linked_symbols(linked);objects=raw['objects']
    require(set(objects)=={OWNER_TARGET,SEAL_TARGET,STRING_TARGET},'fixed three object domain')
    string=objects[STRING_TARGET]
    require(string==string_item(stack_data['objects'][STRING_TARGET],string['nm'],string['object_sha256']),'same current retained string TU evidence')
    contexts={};roots={}
    for target,names in DOMAIN:
        item=objects[target]
        require(item['command_sha256']==sha(item['command'].encode())and item['usage_sha256']==sha(item['usage'].encode())and '-flto'not in item['command'],'actual command/SU/no-LTO')
        require(str(stream_candidate.compiler_stack_path(item['command'].encode(),target))==item['stack_relative'],'actual compiler SU path')
        contexts[target]=provenance(target,names,item,table);roots.update(contexts[target][1])
    require(raw['string_source_sha256']==STRING_SOURCE_SHA and '-fno-optimize-sibling-calls'in objects[STRING_TARGET]['command'],'pinned existing string source/actual command')
    abi=storage(objects[OWNER_TARGET]['nm'],linked,objects[SEAL_TARGET]['elf'],objects[SEAL_TARGET]['usage'])
    stack=stack_once(stack_data)
    require(stack_data['assembly_symbol_table_sha256']==sha(linked.encode()),'current leaf certificate source table')
    leaves={}
    for n,proof in stack['assembly_leaves'].items():
        sym=stack_data['assembly_symbols'][n];key=(sym['address'],sym['bytes'])
        require(proof['start']==key[0]and proof['end']==sum(key)and proof['stack_bytes']==proof['external_calls']==0,'existing actual assembly leaf certificate')
        leaves[key]=sym
    def join(record,outlined):
        matches=[]
        for target,(context,unused,reader)in contexts.items():
            allowed=('bcmp',)if target==STRING_TARGET else(('n278_seal_once',)if target==SEAL_TARGET else(OWNER,'n279_layout_witness',*VALIDATORS,*SOURCE_HELPERS))
            if not outlined and record['name']not in allowed:continue
            if outlined and target==STRING_TARGET:continue
            try:
                proof=reader(context,record,outlined);index=proof['section_index']
                require(index in context['deltas']and proof['object_address']+context['deltas'][index]==record['address'],'actual section-to-linked join')
                matches.append(proof)
            except (ValueError,KeyError):pass
        require(len(matches)==1,'one real TU/ELF/SU/body provenance');return matches[0]
    selected={};pending=deque();outlined_count=0
    def enqueue(record,outlined=False):
        nonlocal outlined_count
        symbol=scoped.symbol_extent(table,record['name'],record,outlined);key=(symbol['address'],symbol['bytes'])
        if key in selected:return key
        proof=join(record,outlined)
        if outlined:outlined_count+=1
        require(outlined_count<=OUTLINED_CAP and len(selected)+2<EXTENT_CAP,'joint fixed44/outlined30 domain')
        selected[key]=dict(name=record['name'],symbol=symbol,provenance=proof,outlined=outlined);pending.append(key);return key
    enqueue(dict(name='n278_seal_once',**table['n278_seal_once'][0],offset=0))
    nodes={};used_bodies=set()
    while pending:
        key=pending.popleft();item=selected[key];ident=format(key[0],'016x')+':'+str(key[1]);used_bodies.add(ident)
        text=raw['bodies'][ident]
        if item['name']=='bcmp':
            nodes[key]=bcmp_certificate(item['provenance'],item['symbol'],text,table,leaves,raw['string_source_sha256']);continue
        proof=scoped.scoped_transfers(text,item['symbol'],table)
        external={};edges={}
        for edge in proof['external_transfers']:
            kind,target=edge_target(edge,leaves)
            if kind=='leaf':external[edge['address']]='leaf:'+leaves[target]['symbol'];continue
            records,outlined=target
            for record in records:join(record,outlined)
            target=enqueue(records[0],outlined);edges[edge['address']]=target;external[edge['address']]=target
        certificate=own_frame(item['name'],scoped.flow.parse_body(text,proof),external,item['provenance']['frame']['bytes'],item['outlined'])
        nodes[key]=dict(proof=proof,frame_certificate=certificate,local_edges=edges)
    require(any(v['symbol']['symbol']=='bcmp'for v in selected.values()),'bcmp must be reached in actual seal closure')
    peaks=scoped.close_graph(nodes)
    # Reuse the already captured current owner extent rather than disassemble it twice.
    for name in (OWNER,'n279_layout_witness'):
        record=dict(name=name,**table[name][0],offset=0);item=scoped.symbol_extent(table,name,record);ident=format(item['address'],'016x')+':'+str(item['bytes']);used_bodies.add(ident)
        proof=scoped.scoped_transfers(raw['bodies'][ident],item,table)
        external={e['address']:'existing-owner'for e in proof['external_transfers']}
        own_frame(name,scoped.flow.parse_body(raw['bodies'][ident],proof),external,roots[name]['frame']['bytes'],False)
        if name==OWNER:
            seal=roots['n278_seal_once'];calls=[e for e in proof['external_transfers']if e['mnemonic']=='bl'and any(r['name']=='n278_seal_once'and r['offset']==0 and(r['address'],r['bytes'])==(seal['linked_address'],seal['bytes'])for r in e['resolved_records'])]
            require(len(calls)==1,'one actual mandatory direct seal caller')
        else:require(not proof['external_transfers'],'ABI witness must not call runtime code')
    require(set(raw['bodies'])==used_bodies and len(used_bodies)<=EXTENT_CAP,'closed captured fixed frontier')
    extra=sum(v['frame_certificate']['own_peak_bytes']for v in nodes.values())
    require(stack['selected_static_frame_sum']+extra<=8192,'new selected chain conservative sum within existing8KiB')
    return dict(schema='note10-v280-seal-target-v1',**{k:raw[k]for k in ('source_head','run_id','build_evidence_id','source_sha256')},ABI=abi,objects=[OWNER_TARGET,SEAL_TARGET,STRING_TARGET],selected_extents=len(used_bodies),outlined_extents=outlined_count,fixed_named_cap=NAMED_CAP,aggregate_cap=EXTENT_CAP,frontier_closed=True,actual_mandatory_callers=1,selected_seal_peak=max(peaks.values()),selected_conservative_sum=stack['selected_static_frame_sum']+extra,bcmp_frame_bytes=16,string_source_sha256=STRING_SOURCE_SHA,new_BSS_bytes=0,new_pool_bytes=0,LTO_NONE=True,source_coupled_N226_success=True,whole_stack_bound_proven=False,hardware_ready=False)

def collect_binding(objects,out,result,run,linked):
    value=retained.retained.collect_binding(objects,out,result,run,linked)
    raw=dict(schema='note10-v280-seal-raw-v1',**{k:result[k]for k in ('source_head','run_id','build_evidence_id','source_sha256')},complete=False,linked_nm_sha256=sha(linked.encode()),compiler_input_binding=result['preparation']['watchdog_binding']['current_owner_seal'],objects={},bodies={},tools=[])
    def persist():
        require(len(json.dumps(raw).encode())<=16777216,'bounded seal capture metadata')
        p.save(out/'seal-evidence.json',raw)
    def capture(argv):
        argv=list(map(str,argv));done=subprocess.run(argv,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=120)
        raw['tools'].append(dict(argv=argv,returncode=done.returncode,stdout_sha256=sha(done.stdout)));persist()
        require(done.returncode==0 and 0<len(done.stdout)<=2097152 and len(done.stderr)<=65536,'bounded seal target tool');return done.stdout.decode()
    try:
        table=scoped.reader.linked_symbols(linked);contexts={}
        for target,names in ((OWNER_TARGET,(OWNER,'n279_layout_witness',*VALIDATORS)),(SEAL_TARGET,('n278_seal_once',))):
            rel=Path(target);command=p.ordinary(objects/rel.with_name('.'+rel.name+'.cmd'));path=stream_candidate.compiler_stack_path(command,target);usage=p.ordinary(objects/path).decode()
            nm=capture(['aarch64-linux-gnu-nm','--format=posix','--print-size',objects/target]);elf=capture(['aarch64-linux-gnu-readelf','--wide','--sections','--symbols',objects/target])
            raw['objects'][target]=dict(command=command.decode(),command_sha256=sha(command),usage=usage,usage_sha256=sha(usage.encode()),stack_relative=str(path),nm=nm,elf=elf,object_sha256=sha(p.ordinary(objects/target,67108864)))
            contexts[target]=provenance(target,names,raw['objects'][target],table);persist()
            if target==SEAL_TARGET:
                (out/'seal-object.o').write_bytes(p.ordinary(objects/target,67108864));(out/'seal-object.cmd').write_bytes(command);(out/'seal-object.su').write_text(usage);(out/'seal-object-elf.log').write_text(elf)
        stack_data=json.loads(p.ordinary(out/'stack-evidence.json',16777216))
        string_nm=capture(['aarch64-linux-gnu-nm','--format=posix','--print-size',objects/STRING_TARGET])
        raw['objects'][STRING_TARGET]=string_item(stack_data['objects'][STRING_TARGET],string_nm,sha(p.ordinary(objects/STRING_TARGET,67108864)))
        contexts[STRING_TARGET]=provenance(STRING_TARGET,('bcmp',),raw['objects'][STRING_TARGET],table)
        raw['string_source_sha256']=sha(p.ordinary(Path(contexts[STRING_TARGET][0]['TU']['translation_unit'])))
        require(raw['string_source_sha256']==STRING_SOURCE_SHA,'unchanged pinned lib/string.c')
        persist()
        binding=raw['compiler_input_binding'];source=Path(contexts[OWNER_TARGET][0]['TU']['translation_unit']).parent
        require(sha(p.ordinary(source/'v226_source_stream_kernel.c'))==binding['owner_after_sha256']and sha(p.ordinary(source/'Makefile'))==binding['Kbuild_after_sha256'],'actual transformed owner/Kbuild source')
        for name,h in binding['copied'].items():require(sha(p.ordinary(source/Path(name).name))==h,'actual copied seal compiler input')
        query=json.loads(p.ordinary(out/'guarded-query-evidence.json',8388608));owner_text=query['assembly'][OWNER]

        leaves={(s['address'],s['bytes']):s for s in stack_data['assembly_symbols'].values()}
        pending=deque((n,dict(name=n,**table[n][0],offset=0))for n in ('n278_seal_once','bcmp',OWNER,'n279_layout_witness'));seen=set();outlined=0
        # Capture only the fixed source domain and actual reached neutral candidates;
        # the pure verifier performs exact per-TU joins and all frame/edge checks.
        while pending:
            name,record=pending.popleft();key=(record['address'],record['bytes'])
            if key in seen:continue
            seen.add(key);is_outline=bool(re.fullmatch(r'OUTLINED_FUNCTION_\d+',name))
            if is_outline:outlined+=1
            require(len(seen)<=EXTENT_CAP and outlined<=OUTLINED_CAP,'bounded fixed capture frontier')
            symbol=scoped.symbol_extent(table,name,record,is_outline)
            text=owner_text if name==OWNER else capture(['aarch64-linux-gnu-objdump','-d','--disassemble-zeroes','--start-address='+hex(key[0]),'--stop-address='+hex(sum(key)),objects/'vmlinux'])
            ident=format(key[0],'016x')+':'+str(key[1]);raw['bodies'][ident]=text;persist()
            proof=scoped.scoped_transfers(text,symbol,table)
            if name in (OWNER,'n279_layout_witness'):continue
            for edge in proof['external_transfers']:
                kind,target=edge_target(edge,leaves)
                if kind=='body':
                    records,unused=target;pending.append((records[0]['name'],records[0]))
        raw['complete']=True;persist()
        result['current_owner_seal_target']=verify_seal(raw,linked,stack_data,result['effective_profile'],binding)
        return value
    except BaseException as error:
        raw.update(complete=False,rejection=str(error)[:2048]);persist();raise

_bind=retained._bind
_ENV={**retained._ENV,**{n:globals()[n]for n in ('WORKFLOW','JOB','BUILD_SCHEMA','CONTEXT_SCHEMA','MANIFEST_SCHEMA','SUCCESS_MEMBERS','source_pins','public_context','install_binding','collect_binding','stream_candidate')}}
run_build=_bind(retained.run_build,_ENV,{'note10/private/v279-ci-native-prepare':'note10/private/v280-ci-native-prepare','v279':'v280','"-v279-current-locked-seal"':'"-v280-bcmp-bridge"'})
seal=_bind(retained.seal,_ENV,{})
_ENV.update(run_build=run_build,seal=seal)
main=_bind(retained.main,_ENV,{})
if __name__=='__main__':main()
