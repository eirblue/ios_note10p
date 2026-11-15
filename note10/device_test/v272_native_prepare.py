"""272 exact watchdog extents and bounded driver-local outlined closure."""
import hashlib,json,re,subprocess
from collections import deque
from pathlib import Path
HERE=Path(__file__).resolve().parent
RETAINED_SHA='38ef7f0253f701f55c67bdc5435ef6eda8b6870e2a89210f5166bd25141d9b82'
if hashlib.sha256((HERE/'v271_native_prepare.py').read_bytes()).hexdigest()!=RETAINED_SHA:raise ValueError('immutable271 producer source')
import v271_native_prepare as retained
import v236_nm_multiplicity as reader
import v239_query_admission as flow
base=retained.base
p,require,sha,stream_candidate=retained.p,retained.require,retained.sha,retained.stream_candidate
WORKFLOW='.github/workflows/note10-v272-native-prepare.yml'
JOB='v272-native-prepare'
BUILD_SCHEMA='note10-v272-holder-carrier-build-v1'
CONTEXT_SCHEMA='note10-v272-holder-carrier-public-input-v1'
MANIFEST_SCHEMA='note10-v272-holder-carrier-sealed-members-v1'
CAPTURE_SCHEMA='note10-v272-watchdog-scoped-closure-raw-v1'
TARGET_SCHEMA='note10-v272-watchdog-binding-target-v1'
SUCCESS_MEMBERS=retained.SUCCESS_MEMBERS
NEW_FILES=('v272_native_prepare.py','test_v272_watchdog_closure.py')
ROOTS=('n269_begin','n269_empty','n269_layout_witness','n269_publish','n269_remove','n269_snapshot')
BOUNDARIES=frozenset(('memcpy','memset','_raw_spin_lock','_raw_spin_trylock','_raw_spin_unlock','preempt_schedule','preempt_schedule_notrace','__stack_chk_fail','queued_spin_lock_slowpath'))
TARGET='drivers/watchdog/s3c2410_wdt.o'
CAPTURE_LIMIT=16777216
CARRIED271=dict(source_head='5de2dd1090bcc3d6d24ccf9c636ab86a500bc519',result_sha256='c56d9796bea2740fe7a18d1a5f073190e0a2eec639ae61450419009439b914d4',passed=True,groups=1,variants=2,assertions=2,host_compile_attempts=0,host_fixture_process_attempts=0,replayed=False)

def source_pins():
    pins=retained.source_pins();pins.pop(retained.WORKFLOW)
    pins.update({'note10/device_test/'+n:sha(p.ordinary(HERE/n))for n in NEW_FILES})
    pins[WORKFLOW]=sha(p.ordinary(base.ROOT/WORKFLOW));return pins

def public_context(head,passed):
    p.hexid(head,40)
    require(type(passed)is dict and set(passed)=={'passed','groups','variants','assertions','result_sha256'}and passed['passed']is True and(passed['groups'],passed['variants'],passed['assertions'])==(1,6,6),'six new scoped closure predicates only')
    p.hexid(passed['result_sha256'])
    return dict(schema=CONTEXT_SCHEMA,source_head=head,source_sha256=source_pins(),new_fixture_PASS=passed,carried269_fixture_PASS=retained.retained.CARRIED269,carried270_fixture_PASS=retained.CARRIED270,carried271_fixture_PASS=CARRIED271,holder_bytes=base.capacity.SOURCE_CAP,CI_native_source_input_bytes=0)

def save_capture(out,bundle):
    def encoded(value):return(json.dumps(value,indent=2,sort_keys=True)+'\n').encode()
    raw=encoded(bundle)
    if len(raw)>CAPTURE_LIMIT:
        def bounded(value):
            if isinstance(value,dict):return{k:(dict(omitted=True,bytes=len(v.encode()),sha256=sha(v.encode()))if k.startswith('raw_')and isinstance(v,str)else bounded(v))for k,v in value.items()}
            if isinstance(value,list):return[bounded(v)for v in value]
            return value
        small=bounded(bundle);small.update(complete=False,status='capture-limit-exceeded',candidate_json_bytes=len(raw));raw=encoded(small)
        require(len(raw)<=CAPTURE_LIMIT,'bounded272 capture metadata')
        (out/'watchdog-capture.json').write_bytes(raw);raise ValueError('bounded272 raw capture exceeded')
    (out/'watchdog-capture.json').write_bytes(raw)

def capture_document(result,linked):
    return dict(schema=CAPTURE_SCHEMA,**{k:result[k]for k in ('source_head','run_id','build_evidence_id','source_sha256')},driver_target=TARGET,linked_nm_sha256=sha(linked.encode()),compiler_input_binding=result.get('preparation',{}).get('watchdog_binding'),complete=False,status='incomplete',phase='metadata',current_helper=None,current_edge=None,tools=[],helpers={},owner=None)

def object_symbols(raw):
    result={}
    for line in raw.splitlines():
        row=line.split()
        if len(row)in(3,4):result.setdefault(row[0],[]).append(row)
    return result

def driver_provenance(command,usage,elf,nm,table):
    require(b'clang-14'in command and b'-DMODULE'not in command,'same builtin272 driver command')
    tu=reader.translation_unit(command,TARGET);frames=stream_candidate.frames(usage);sections={};functions={};objrows=object_symbols(nm)
    for line in elf.splitlines():
        section=re.match(r'^\s*\[\s*(\d+)\]\s+(\S+)\s+\S+\s+[0-9a-fA-F]+\s+[0-9a-fA-F]+\s+[0-9a-fA-F]+\s+[0-9a-fA-F]+\s+([A-Z]+)\s+',line)
        if section:sections[section[1]]=(section[2],section[3])
        row=re.match(r'^\s*\d+:\s+([0-9a-fA-F]+)\s+(\d+|0x[0-9a-fA-F]+)\s+FUNC\s+(LOCAL|GLOBAL|WEAK)\s+DEFAULT\s+(\d+)\s+(\S+)\s*$',line)
        if row:functions.setdefault(row[5],[]).append(dict(address=int(row[1],16),bytes=int(row[2],16 if row[2].startswith('0x')else 10),binding=row[3],section_index=row[4]))
    context=dict(TU=tu,frames=frames,sections=sections,functions=functions,object_rows=objrows,deltas={})
    roots={}
    for name in ROOTS:
        require(name in table and len(table[name])==1,'unique linked watchdog root: '+name)
        record=dict(name=name,**table[name][0],offset=0)
        proof=join_driver(context,record,False);index=proof['section_index'];delta=record['address']-proof['object_address']
        require(index not in context['deltas']or context['deltas'][index]==delta,'consistent driver section translation')
        context['deltas'][index]=delta;roots[name]=proof
    return context,roots

def join_driver(context,record,outlined):
    name=record['name'];functions=context['functions'];frames=context['frames'];rows=context['object_rows']
    require(name in functions and len(functions[name])==1 and name in frames and name in rows and len(rows[name])==1,'one actual driver ELF/nm/SU function: '+name)
    item=functions[name][0];frame=frames[name];row=rows[name][0];index=item['section_index']
    require(index in context['sections'],'driver input section exists');section,flags=context['sections'][index]
    require(not section.startswith(('.init','.exit'))and'A'in flags and'X'in flags and'W'not in flags,'non-init executable nonwritable driver section')
    require(len(row)==4 and row[1]==record['kind']and record['kind']in('t','T')and int(row[2],16)==item['address']and int(row[3],16)==item['bytes']==record['bytes']and item['binding']==('LOCAL'if record['kind']=='t'else'GLOBAL'),'actual object/linked type size binding')
    require(frame['source']==context['TU']['translation_unit']and frame['kind']=='static'and 0<=frame['bytes']<=8192,'same TU actual static watchdog SU')
    if outlined:
        require(re.fullmatch(r'OUTLINED_FUNCTION_\d+',name)is not None and item['binding']=='LOCAL'and record['kind']=='t'and record['offset']==0 and index in context['deltas']and item['address']+context['deltas'][index]==record['address']and frame['bytes']==0,'actual driver-local entry/section/SU0 outlined join')
    return dict(name=name,object=TARGET,translation_unit=frame['source'],object_address=item['address'],linked_address=record['address'],bytes=item['bytes'],ordinal=record['ordinal'],binding=item['binding'],section=section,section_index=index,frame=frame)

def symbol_extent(table,name,record,outlined=False):
    start,size=record['address'],record['bytes'];limit=256 if outlined else 8192
    require(0<start<1<<64 and 0<size<=limit and start%4==size%4==0 and start+size<1<<64,'bounded aligned watchdog extent')
    aliases=sorted({n for n,rows in table.items()for r in rows if(r['address'],r['bytes'])==(start,size)})
    require(name in aliases and len(aliases)<=32,'bounded exact watchdog aliases')
    return dict(symbol=name,address=start,bytes=size,aliases=aliases)

def scoped_transfers(raw,symbol,table):
    require('R_AARCH64_'not in raw,'relocation outside scoped linked instructions')
    return reader.transfers(raw,symbol,table)

def classify_edge(edge,context,roots):
    require(edge['mnemonic']in('bl','b')and not edge['unresolved'],'ordinary resolved watchdog call/tail only')
    records=edge['resolved_records'];require(records and all(r['offset']==0 and r['address']==edge['target']for r in records),'exact target entry only')
    extents={(r['address'],r['bytes'])for r in records};require(len(extents)==1,'unambiguous target extent')
    names={r['name']for r in records};key=next(iter(extents))
    if names<=BOUNDARIES:return dict(kind='boundary',names=sorted(names),key=key)
    admitted=[r for r in records if r['name']in ROOTS and(r['address'],r['bytes'])==(roots[r['name']]['linked_address'],roots[r['name']]['bytes'])]
    if admitted:
        require(names<=set(ROOTS),'root alias must not authorize foreign helper');return dict(kind='root',record=admitted[0],key=key)
    require(all(re.fullmatch(r'OUTLINED_FUNCTION_\d+',n)for n in names),'foreign watchdog transfer')
    proofs=[join_driver(context,r,True)for r in records]
    require(all(v['linked_address']==key[0]and v['bytes']==key[1]for v in proofs),'all outlined aliases need driver provenance')
    return dict(kind='outlined',record=records[0],key=key,provenance=proofs)

def own_frame(name,rows,external,frame,outlined):
    if outlined:
        allowed={'mov','movz','movn','movk','add','adds','sub','subs','and','ands','orr','eor','bic','bics','orn','eon','mvn','neg','negs','cmp','cmn','tst','csel','csinc','csinv','csneg','cset','csetm','lsl','lsr','asr','ror','ubfx','sbfx','bfi','bfxil','uxtb','uxth','uxtw','sxtb','sxth','sxtw','adr','adrp','ldr','ldrb','ldrh','ldrsw','ldur','ldurb','ldurh','ldursw','str','strb','strh','stur','sturb','sturh','ldp','stp','nop','ret','b','cbz','cbnz','tbz','tbnz'}
        require(frame==0 and all((op in allowed or re.fullmatch(r'b\.(eq|ne|cs|cc|hs|lo|mi|pl|vs|vc|hi|ls|ge|lt|gt|le|al|nv)',op))and(op=='ret'and args in('','x30')or not re.search(r'\b(?:sp|wsp|x29|w29|fp|x30|w30|lr)\b',args))for _,op,args in rows),'outlined supported SP/FP/LR-neutral instructions; no BL')
    states={0:(0,None)};pending=deque([0]);calls={};peak=0;closures=0;visits=0
    while pending:
        index=pending.popleft();visits+=1;require(visits<=len(rows)*32,'bounded watchdog own-frame convergence')
        sp,fp=states[index];address,op,args=rows[index];access=flow.memory(op,args)
        math=re.fullmatch(r'(sp|x29),\s*sp,\s*#(-?(?:0x[0-9a-f]+|\d+))',args)if op in('add','sub')else None
        if access:
            if access['pre']:sp+=access['offset'];offset=0
            else:offset=access['offset']
            origin=sp if access['base']=='sp'else fp
            require(origin is not None and sp<=origin+offset<origin+offset+access['width']<=0,'watchdog stack access within live own allocation')
            if access['load']and'x29'in access['regs']:fp=None
            sp+=access['post']
        elif math:
            value=flow.immediate(math[2])*(1 if op=='add'else-1)
            if math[1]=='sp':sp+=value
            else:fp=sp+value
        elif op=='mov'and flow.normalized(args)=='x29,sp':fp=sp
        else:require(not re.search(r'\b(?:sp|wsp|x29|w29|fp)\b',args),'unsupported watchdog own SP/FP effect')
        require(-frame<=sp<=0,'watchdog allocation exceeds actual SU');peak=max(peak,-sp)
        if address in external:
            require(op in('bl','b')and(op!='b'or sp==0),'balanced SP0 external tail only');calls[address]=sp
            if op=='b':closures+=1
        if op=='ret':require(sp==0,'balanced watchdog return');closures+=1
        for nxt in flow.successors(rows,index,external):
            state=(sp,fp)
            if nxt in states:require(states[nxt]==state,'compatible watchdog own-frame merge')
            else:states[nxt]=state;pending.append(nxt)
    require(closures>0 and peak==frame,'closed watchdog own peak equals actual static SU')
    return dict(own_peak_bytes=peak,call_SP_offsets=calls,neutral_outlined=outlined,normal_ABI_call_return_assumed=not outlined,callee_peaks_included=False)

def close_graph(nodes):
    active=set();peaks={}
    def visit(key):
        require(key not in active,'watchdog interprocedural recursion/cycle')
        if key in peaks:return peaks[key]
        active.add(key);node=nodes[key];peak=node['frame_certificate']['own_peak_bytes']
        for address,target in node['local_edges'].items():peak=max(peak,-node['frame_certificate']['call_SP_offsets'][address]+visit(target))
        require(peak<=8192,'bounded selected watchdog local chain');active.remove(key);peaks[key]=peak;return peak
    for key in nodes:visit(key)
    return {key:peaks[key]for key in nodes}

def scoped_closure(out,bundle,context,roots,table,capture):
    pending=deque();selected={};nodes={};outlined_count=0
    def enqueue(name,record,outlined,provenance):
        nonlocal outlined_count
        symbol=symbol_extent(table,name,record,outlined);key=(symbol['address'],symbol['bytes'])
        if key in selected:return key
        if outlined:outlined_count+=1
        require(outlined_count<=32 and len(selected)<38,'bounded watchdog selected frontier')
        selected[key]=(name,symbol,outlined,provenance);pending.append(key);return key
    for name in ROOTS:enqueue(name,dict(name=name,**table[name][0],offset=0),False,[roots[name]])
    while pending:
        key=pending.popleft();name,symbol,outlined,provenance=selected[key];identity=format(key[0],'016x')+':'+str(key[1])
        bundle.update(current_helper=identity,current_edge=None,phase='linked-body');entry=dict(name=name,symbol=symbol,provenance=provenance,frame_passed=False);bundle['helpers'][identity]=entry;save_capture(out,bundle)
        raw=capture(symbol);entry.update(raw_objdump=raw,raw_objdump_sha256=sha(raw.encode()));save_capture(out,bundle)
        bundle['phase']='scope';save_capture(out,bundle);proof=scoped_transfers(raw,symbol,table);entry['proof']=proof
        external={};local={};boundaries=[]
        for edge in proof['external_transfers']:
            bundle.update(phase='frontier',current_edge=edge);save_capture(out,bundle);target=classify_edge(edge,context,roots)
            if target['kind']=='boundary':external[edge['address']]='opaque:'+','.join(target['names']);boundaries.append(dict(edge=edge,boundary=target['names']))
            else:
                r=target['record'];destination=enqueue(r['name'],r,target['kind']=='outlined',target.get('provenance',[roots[r['name']]]if r['name']in roots else[]))
                external[edge['address']]=destination;local[edge['address']]=destination
        bundle.update(phase='frame',current_edge=None);save_capture(out,bundle)
        rows=flow.parse_body(raw,proof);certificate=own_frame(name,rows,external,provenance[0]['frame']['bytes'],outlined)
        entry.update(frame_certificate=certificate,frame_passed=True);save_capture(out,bundle)
        nodes[key]=dict(proof=proof,frame_certificate=certificate,local_edges=local,opaque_boundaries=boundaries)
    bundle.update(phase='graph',current_helper=None);save_capture(out,bundle);peaks=close_graph(nodes)
    return dict(selected_extents=len(nodes),outlined_extents=outlined_count,frontier_closed=True,acyclic=True,supported_own_frames=True,scoped_complete=True,provenance_complete=True,selected_local_peak_bytes=max(peaks.values()),nodes={format(k[0],'016x')+':'+str(k[1]):{**v,'local_edges':{str(a):list(t)for a,t in v['local_edges'].items()},'selected_local_peak_bytes':peaks[k]}for k,v in nodes.items()},opaque_external_boundaries=sorted(BOUNDARIES),opaque_external_peaks_included=False,whole_kernel_stack_bound_proven=False,IRQ_NMI_bound_proven=False,atomic_duration_measured=False)

def owner_caller(objects,out,result,table,roots):
    graph=result['guarded_query_graph'];raw_bytes=p.ordinary(out/'guarded-query-evidence.json',8388608);raw=json.loads(raw_bytes)
    require(graph['raw_sha256']==sha(raw_bytes)and raw['linked_nm_sha256']==sha(p.ordinary(out/'leaf-symbols.log',16777216)),'current guarded raw and linked table binding')
    name='n226_ingest_prepared_locked';proof=graph['named_bodies'][name];symbol=proof['symbol'];text=raw['assembly'][name]
    require(raw['symbols'][name]==symbol and name in table and len(table[name])==1 and table[name][0]['address']==symbol['address']and table[name][0]['bytes']==symbol['bytes'],'current scoped owner extent')
    argv=['aarch64-linux-gnu-objdump','-d','--disassemble-zeroes','--start-address='+hex(symbol['address']),'--stop-address='+hex(symbol['address']+symbol['bytes']),str(objects/'vmlinux')]
    tools=[v for v in raw['tools']if v['key']==name]
    require(len(tools)==1 and tools[0]['argv']==argv and tools[0]['returncode']==0 and tools[0]['stdout_sha256']==sha(text.encode())and proof==scoped_transfers(text,symbol,table),'reuse exact current guarded tool/body/proof')
    wanted=roots['n269_snapshot'];calls=[e for e in proof['external_transfers']if e['mnemonic']=='bl'and e['target']==wanted['linked_address']and e['resolved_records']and all(r['offset']==0 and(r['address'],r['bytes'])==(wanted['linked_address'],wanted['bytes'])for r in e['resolved_records'])]
    require(len(calls)==1,'one current scoped direct BL snapshot caller')
    return dict(raw_sha256=sha(raw_bytes),proof=proof,tool=tools[0],snapshot_call=calls[0]),text

def collect_binding(objects,out,result,run,linked):
    bundle=capture_document(result,linked);save_capture(out,bundle)
    def capture(argv):
        argv=list(map(str,argv));tool=dict(argv=argv,returncode=None);bundle['tools'].append(tool);save_capture(out,bundle)
        try:done=subprocess.run(argv,stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=False,timeout=120)
        except subprocess.TimeoutExpired as error:
            tool.update(timeout=True,raw_stdout=(error.stdout or b'').decode(errors='replace'),raw_stderr=(error.stderr or b'').decode(errors='replace'));save_capture(out,bundle);raise
        tool.update(returncode=done.returncode,stdout_sha256=sha(done.stdout),raw_stdout=done.stdout.decode(errors='replace'),raw_stderr=done.stderr.decode(errors='replace'));save_capture(out,bundle)
        require(done.returncode==0 and 0<len(done.stdout)<=2097152 and len(done.stderr)<=65536,'bounded successful272 scoped tool');return done.stdout.decode()
    try:
        command=p.ordinary(objects/'drivers/watchdog/.s3c2410_wdt.o.cmd');bundle.update(raw_command=command.decode(),command_sha256=sha(command));save_capture(out,bundle)
        usage_path=stream_candidate.compiler_stack_path(command,TARGET);usage=p.ordinary(objects/usage_path).decode();bundle.update(stack_relative=str(usage_path),raw_SU=usage,stack_sha256=sha(usage.encode()));save_capture(out,bundle)
        nm=capture(['aarch64-linux-gnu-nm','--format=posix','--print-size',objects/TARGET]);elf=capture(['aarch64-linux-gnu-readelf','--wide','--sections','--symbols',objects/TARGET]);bundle.update(raw_driver_nm=nm,raw_driver_elf=elf,phase='provenance');save_capture(out,bundle)
        table=reader.linked_symbols(linked);context,roots=driver_provenance(command,usage,elf,nm,table);bundle.update(driver_TU=context['TU'],root_provenance=roots);save_capture(out,bundle)
        def body(symbol):return capture(['aarch64-linux-gnu-objdump','-d','--disassemble-zeroes','--start-address='+hex(symbol['address']),'--stop-address='+hex(symbol['address']+symbol['bytes']),objects/'vmlinux'])
        closure=scoped_closure(out,bundle,context,roots,table,body)
        bundle['phase']='owner-caller';save_capture(out,bundle);caller,owner_text=owner_caller(objects,out,result,table,roots);bundle['owner']=caller;save_capture(out,bundle)
        rows=object_symbols(nm)
        for name,size in {'n269_size_binding':40,'n269_align_binding':8}.items():require(name in rows and len(rows[name])==1 and len(rows[name][0])==3 and rows[name][0][1]=='A'and int(rows[name][0][2],16)==size,'actual272 ABI40/align8')
        owner_rows=object_symbols(p.ordinary(out/'owner-symbols.log').decode());storage=owner_rows['n269_binding_storage'];pool=owner_rows['n226_source_pool']
        require(len(storage)==len(pool)==1 and int(storage[0][3],16)==40 and int(storage[0][2],16)-int(pool[0][2],16)==43664,'actual272 pool alias40')
        writable={n:int(v[0][3],16)for n,v in rows.items()if n.startswith('n269_')and len(v)==1 and len(v[0])==4 and v[0][1]in('b','B','d','D')}
        bundle.update(phase='writable',driver_writable_bytes=writable);save_capture(out,bundle)
        require(writable.get('n269_cache')==40 and set(writable)=={'n269_cache','n269_cache_lock'},'actual272 driver writable inventory')
        value=dict(schema=TARGET_SCHEMA,**{k:result[k]for k in ('source_head','run_id','build_evidence_id','source_sha256')},compiled_current_callers=1,record_bytes=40,pool_offset=43664,new_pool_bytes=0,driver_object_sha256=sha(p.ordinary(objects/TARGET,67108864)),driver_command_sha256=sha(command),driver_SU_sha256=sha(usage.encode()),driver_ELF_sha256=sha(elf.encode()),linked_nm_sha256=sha(linked.encode()),compiler_input_binding=bundle['compiler_input_binding'],driver_TU=context['TU'],root_provenance=roots,driver_writable_bytes=writable,driver_writable_total_bytes=sum(writable.values()),frames={n:context['frames'][n]for n in ROOTS},local_closure=closure,owner_caller=caller,disassembly={k:v['raw_objdump']for k,v in bundle['helpers'].items()},owner_call_disassembly=owner_text,driver_symbols=nm,probe_cached_rate_stale_possible=True,armed=False,autonomous_return=False,post_shutdown=False)
        p.save(out/'watchdog-evidence.json',value);bundle.update(complete=True,status='complete',phase='complete',current_helper=None,current_edge=None);save_capture(out,bundle)
        return{k:v for k,v in value.items()if k not in('disassembly','owner_call_disassembly','driver_symbols')}
    except BaseException as error:
        bundle.update(complete=False,status='rejected',rejection_type=type(error).__name__,rejection_reason=str(error)[:2048]);save_capture(out,bundle);raise

_bind=retained._bind
_ENV={**retained._ENV,**{k:globals()[k]for k in('WORKFLOW','JOB','BUILD_SCHEMA','CONTEXT_SCHEMA','MANIFEST_SCHEMA','SUCCESS_MEMBERS','source_pins','public_context','collect_binding')}}
run_build=_bind(retained.run_build,_ENV,{'note10/private/v271-ci-native-prepare':'note10/private/v272-ci-native-prepare','v271':'v272','"-v271-watchdog-failure-capture"':'"-v272-watchdog-scoped-closure"'})
seal=_bind(retained.seal,_ENV,{})
_ENV.update(run_build=run_build,seal=seal)
main=_bind(retained.main,_ENV,{})
decode_binding=retained.retained.decode_binding
if __name__=='__main__':main()
