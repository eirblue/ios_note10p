"""279 mandatory current-owner value seal; no transfer or new observation."""
import hashlib,json,re,subprocess
from collections import deque
from pathlib import Path
from types import FunctionType,SimpleNamespace
import v277_native_prepare as retained
import v272_native_prepare as scoped
HERE=Path(__file__).resolve().parent
p,require,sha=retained.p,retained.require,retained.sha
ROOT=HERE.parents[1]
WORKFLOW='.github/workflows/note10-v279-native-prepare.yml'
JOB='v279-native-prepare'
BUILD_SCHEMA='note10-v279-holder-carrier-build-v1'
CONTEXT_SCHEMA='note10-v279-holder-carrier-public-input-v1'
MANIFEST_SCHEMA='note10-v279-holder-carrier-sealed-members-v1'
CAPTURE_SCHEMA=retained.CAPTURE_SCHEMA
decode_binding=retained.decode_binding
SEAL_TARGET='arch/arm64/mm/v278_current_owner_seal.o'
OWNER_TARGET='arch/arm64/mm/init.o'
OWNER='n226_ingest_prepared_locked'
VALIDATORS=('n210_request_valid','n210_receipt_matches','n209_decode_payload','n209_layout_bounds')
# Exact unprefixed helpers from retained includes and actual277 owner-init.su;
# extent is source-static and currently inlined, admitted only if actually reached.
SOURCE_HELPERS=('little','magic','nonzero','equal','hex32','extent')
NAMED=(OWNER,'n278_seal_once','n279_layout_witness',*VALIDATORS,*SOURCE_HELPERS)
NAMED_CAP,OUTLINED_CAP,EXTENT_CAP=13,30,43
SUCCESS_MEMBERS=(*retained.SUCCESS_MEMBERS,'seal-evidence.json','seal-object.o','seal-object.cmd','seal-object.su','seal-object-elf.log')
NEW_FILES=('v279_native_prepare.py','v279_current_owner_seal.inc','v279_current_owner_seal_fixture.c','test_v279_current_owner_seal.py')
SEAL_FILES=('v278_current_owner_seal.c','v278_current_owner_seal.h')
CARRIED278={'passed': True, 'groups': 1, 'variants': 5, 'assertions': 5, 'host_compile_attempts': 1, 'host_fixture_process_attempts': 1, 'source_head': '27bc5f19da992fe711ac8f5b8afec3416564b6be', 'result_sha256': 'a8b0451e1b2b351a5f2b8a02a9218e571d81d30af1cf2db1cf8d0b2bb8b30d41', 'source_sha256': {'note10/device_test/v278_current_owner_seal.c': '677131bc54e3c05852930a121f856d643fb2301fb687ffbb802dc2b7af956dc4', 'note10/device_test/v278_current_owner_seal.h': '2f015fd53de86504ca42b3c6fdec3e3c4343be805fb1bd864f839ae277949fa9', 'note10/device_test/v278_current_owner_seal_fixture.c': '840c221e8b30a80ed82179986b0ba1956f0bec157854bd26f31b8204686ed440'}, 'replayed': False}
SEAM=b'    error=n217_consume(request,&ctx->owner.base.destination,&ctx->owner.base.identity,&n210_result,&n217_kernel_state,&io,ctx,\n                       n226_source_pool+N226_STAGE_OFFSET,N217_CHUNK);\n    goto done;'
CALL=b'    if(!error)error=n278_seal_once(N279_SEAL,prepared,&n210_destination,context,\n        n210_result.descriptor_sha256,&n210_result,n210_spent,&n217_kernel_state);\n'
KBUILD=b'obj-$(CONFIG_NOTE10_V210_NATIVE_PREPARE) += v278_current_owner_seal.o\n'

def source_pins():
    pins=retained.source_pins();pins.pop(retained.WORKFLOW)
    pins.update({'note10/device_test/'+n:sha(p.ordinary(HERE/n))for n in (*SEAL_FILES,*NEW_FILES)})
    pins[WORKFLOW]=sha(p.ordinary(ROOT/WORKFLOW));return pins

def public_context(head,passed):
    p.hexid(head,40)
    require(set(passed)=={'passed','groups','variants','assertions','result_sha256'}and passed['passed']is True and tuple(passed[k]for k in ('groups','variants','assertions'))==(1,2,2),'new279 composition/seam batch only')
    p.hexid(passed['result_sha256'])
    return dict(schema=CONTEXT_SCHEMA,source_head=head,source_sha256=source_pins(),new_fixture_PASS=passed,carried278_fixture_PASS=CARRIED278)

def owner_overlay(raw):
    require(raw.count(SEAM)==1 and b'n278_seal_once'not in raw,'unique current success seam')
    signature=b'static N226_NOINLINE int n226_ingest_prepared_locked('
    require(raw.count(signature)==1,'actual owner definition')
    begin=raw.index(signature);body=raw[begin:]
    guard=b'    if(n217_kernel_state.spent)return -EALREADY;'
    clear=b'    memset(n226_source_pool,0,sizeof(n226_source_pool));'
    require(body.count(guard)==body.count(clear)==1 and body.index(b'lockdep_assert_held(&n210_lock)')<body.index(guard)<body.index(clear)<body.index(SEAM),'shared pre-clear lock/spent refusal preserved')
    require(body.count(b'return ')==2 and body.endswith(b'return error;\n}\n'),'one error-propagating owner return')
    changed=raw.replace(signature,b'#include "v279_current_owner_seal.inc"\n'+signature,1)
    return changed.replace(SEAM,SEAM.replace(b'    goto done;',CALL+b'    goto done;'),1)

def install_binding(source,buffers):
    value=retained._ENV['install_binding'](source,buffers)
    owner=source/'arch/arm64/mm/v226_source_stream_kernel.c';before=p.ordinary(owner);after=owner_overlay(before);owner.write_bytes(after)
    require(value['compiler_inputs']['arch/arm64/mm/v226_source_stream_kernel.c']['after_sha256']==sha(before),'exact current owner overlay chain')
    value['compiler_inputs']['arch/arm64/mm/v226_source_stream_kernel.c']['after_sha256']=sha(after)
    copied={}
    for n in (*SEAL_FILES,'v279_current_owner_seal.inc'):
        target=source/'arch/arm64/mm'/n;require(not target.exists(),'fresh seal compiler input')
        raw=buffers['note10/device_test/'+n];target.write_bytes(raw);copied[str(target.relative_to(source))]=sha(raw)
    make=source/'arch/arm64/mm/Makefile';old=p.ordinary(make)
    require(b'v278_current_owner_seal'not in old and old.endswith(b'\n'),'one new dedicated builtin TU')
    make.write_bytes(old+KBUILD)
    value['current_owner_seal']=dict(owner_path=str(owner.relative_to(source)),owner_before_sha256=sha(before),owner_after_sha256=sha(after),copied=copied,Kbuild_before_sha256=sha(old),Kbuild_after_sha256=sha(old+KBUILD),new_BSS_bytes=0,new_pool_bytes=0,pool_offset=43704)
    return value

def bind(fn,env):
    result=FunctionType(fn.__code__,env,fn.__name__,fn.__defaults__,fn.__closure__)
    result.__kwdefaults__=fn.__kwdefaults__;return result

_FRAME_ENV={**retained.own_frame.__globals__,'ROOTS':NAMED}
own_frame=bind(retained.own_frame,_FRAME_ENV)
_STACK={}
_original_stack=scoped.stream_candidate
def stack_once(data):
    key=sha(json.dumps(data,sort_keys=True,separators=(',',':')).encode())
    if _STACK:
        require(_STACK['key']==key,'one actual new stack input');return _STACK['proof']
    proof=_original_stack.verify_stack_evidence(data);_STACK.update(key=key,proof=proof);return proof
stream_candidate=SimpleNamespace(**{**vars(_original_stack),'verify_stack_evidence':stack_once})

def provenance(target,roots,item,table):
    env={**scoped.__dict__,'TARGET':target,'ROOTS':roots}
    env['join_driver']=bind(scoped.join_driver,env)
    context,proofs=bind(scoped.driver_provenance,env)(item['command'].encode(),item['usage'],item['elf'],item['nm'],table)
    return context,proofs,env['join_driver']

def storage(nm,linked,elf,usage):
    rows=scoped.object_symbols(nm);lr=scoped.object_symbols(linked)
    expected={'n279_size_seal':1192,'n279_align_seal':8,'n279_offset_values':8,'n279_owner_hash_offset':42528,'n279_owner_hash_bytes':112}
    for n,v in expected.items():
        require(n in rows and len(rows[n])==1 and rows[n][0][1]=='A'and int(rows[n][0][2],16)==v,'actual computed target seal ABI: '+n)
    for table in (rows,lr):
        require(all(n in table and len(table[n])==1 and len(table[n][0])==4 for n in ('n226_source_pool','n279_seal_storage')),'actual pool/storage symbols')
        pool,slot=table['n226_source_pool'][0],table['n279_seal_storage'][0]
        require(pool[1]in('b','B')and slot[1]in('b','B')and int(pool[3],16)==49152 and int(slot[3],16)==1192 and int(slot[2],16)-int(pool[2],16)==43704,'same existing pool alias only')
    obj=retained._ENV['metadata_object_evidence'](elf,usage)
    require(obj['writable_section_bytes']==0,'dedicated seal TU adds no writable section')
    return dict(**expected,pool_bytes=49152,pool_offset=43704,new_writable_bytes=0)

def edge_target(edge,leaves):
    records=edge['resolved_records']
    require(edge['mnemonic']in('bl','b')and not edge['unresolved']and records and all(r['offset']==0 and r['address']==edge['target']for r in records),'exact direct call entry')
    keys={(r['address'],r['bytes'])for r in records};require(len(keys)==1,'one unambiguous callee extent');dest=next(iter(keys))
    if dest in leaves:
        require(set(edge['resolved_symbols'])==set(leaves[dest]['aliases']),'complete certified leaf aliases')
        return 'leaf',dest
    names={r['name']for r in records};outlined=all(re.fullmatch(r'OUTLINED_FUNCTION_\d+',n)for n in names)
    require(outlined or names<=set(VALIDATORS)|set(SOURCE_HELPERS)|{'n278_seal_once'},'foreign callee is not a validator boundary')
    return 'body',(records,outlined)

def verify_seal(raw,linked,stack_data,profile,binding):
    require(raw['schema']=='note10-v279-seal-raw-v1'and raw['complete']is True and raw['linked_nm_sha256']==sha(linked.encode())and raw['compiler_input_binding']==binding,'actual complete new seal capture')
    require(profile.get('LTO_NONE')=='y'and profile.get('LTO','n')=='n','actual LTO_NONE, no cross-TU LTO inference')
    table=scoped.reader.linked_symbols(linked);objects=raw['objects']
    require(set(objects)=={OWNER_TARGET,SEAL_TARGET},'fixed two object domain')
    contexts={};roots={}
    for target,names in ((OWNER_TARGET,(OWNER,'n279_layout_witness',*VALIDATORS)),(SEAL_TARGET,('n278_seal_once',))):
        item=objects[target]
        require(item['command_sha256']==sha(item['command'].encode())and item['usage_sha256']==sha(item['usage'].encode())and '-flto'not in item['command'],'actual command/SU/no-LTO')
        require(str(stream_candidate.compiler_stack_path(item['command'].encode(),target))==item['stack_relative'],'actual compiler SU path')
        contexts[target]=provenance(target,names,item,table);roots.update(contexts[target][1])
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
            if not outlined and record['name']not in (('n278_seal_once',)if target==SEAL_TARGET else(OWNER,'n279_layout_witness',*VALIDATORS,*SOURCE_HELPERS)):continue
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
        require(outlined_count<=OUTLINED_CAP and len(selected)+2<EXTENT_CAP,'joint fixed43/outlined30 domain')
        selected[key]=dict(name=record['name'],symbol=symbol,provenance=proof,outlined=outlined);pending.append(key);return key
    enqueue(dict(name='n278_seal_once',**table['n278_seal_once'][0],offset=0))
    nodes={};used_bodies=set()
    while pending:
        key=pending.popleft();item=selected[key];ident=format(key[0],'016x')+':'+str(key[1]);used_bodies.add(ident)
        text=raw['bodies'][ident];proof=scoped.scoped_transfers(text,item['symbol'],table)
        external={};edges={}
        for edge in proof['external_transfers']:
            kind,target=edge_target(edge,leaves)
            if kind=='leaf':external[edge['address']]='leaf:'+leaves[target]['symbol'];continue
            records,outlined=target
            for record in records:join(record,outlined)
            target=enqueue(records[0],outlined);edges[edge['address']]=target;external[edge['address']]=target
        certificate=own_frame(item['name'],scoped.flow.parse_body(text,proof),external,item['provenance']['frame']['bytes'],item['outlined'])
        nodes[key]=dict(proof=proof,frame_certificate=certificate,local_edges=edges)
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
    return dict(schema='note10-v279-seal-target-v1',**{k:raw[k]for k in ('source_head','run_id','build_evidence_id','source_sha256')},ABI=abi,objects=[OWNER_TARGET,SEAL_TARGET],selected_extents=len(used_bodies),outlined_extents=outlined_count,fixed_named_cap=NAMED_CAP,aggregate_cap=EXTENT_CAP,frontier_closed=True,actual_mandatory_callers=1,selected_seal_peak=max(peaks.values()),selected_conservative_sum=stack['selected_static_frame_sum']+extra,new_BSS_bytes=0,new_pool_bytes=0,LTO_NONE=True,source_coupled_N226_success=True,whole_stack_bound_proven=False,hardware_ready=False)

def collect_binding(objects,out,result,run,linked):
    value=retained.collect_binding(objects,out,result,run,linked)
    raw=dict(schema='note10-v279-seal-raw-v1',**{k:result[k]for k in ('source_head','run_id','build_evidence_id','source_sha256')},complete=False,linked_nm_sha256=sha(linked.encode()),compiler_input_binding=result['preparation']['watchdog_binding']['current_owner_seal'],objects={},bodies={},tools=[])
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
        binding=raw['compiler_input_binding'];source=Path(contexts[OWNER_TARGET][0]['TU']['translation_unit']).parent
        require(sha(p.ordinary(source/'v226_source_stream_kernel.c'))==binding['owner_after_sha256']and sha(p.ordinary(source/'Makefile'))==binding['Kbuild_after_sha256'],'actual transformed owner/Kbuild source')
        for name,h in binding['copied'].items():require(sha(p.ordinary(source/Path(name).name))==h,'actual copied seal compiler input')
        query=json.loads(p.ordinary(out/'guarded-query-evidence.json',8388608));owner_text=query['assembly'][OWNER]
        stack_data=json.loads(p.ordinary(out/'stack-evidence.json',16777216))
        leaves={(s['address'],s['bytes']):s for s in stack_data['assembly_symbols'].values()}
        pending=deque((n,dict(name=n,**table[n][0],offset=0))for n in ('n278_seal_once',OWNER,'n279_layout_witness'));seen=set();outlined=0
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
run_build=_bind(retained.run_build,_ENV,{'note10/private/v277-ci-native-prepare':'note10/private/v279-ci-native-prepare','v277':'v279','"-v277-watchdog-completion-remaining"':'"-v279-current-locked-seal"'})
seal=_bind(retained.seal,_ENV,{})
_ENV.update(run_build=run_build,seal=seal)
main=_bind(retained.main,_ENV,{})
if __name__=='__main__':main()

