"""Build-only271: persist target rejection evidence before unchanged guards."""
import hashlib,json,re,subprocess
from pathlib import Path
HERE=Path(__file__).resolve().parent
RETAINED_SHA='a2b0068aa8754e78b2c318323a3c888ae620f109a26fc79798a3daf10c897a2f'
if hashlib.sha256((HERE/'v270_native_prepare.py').read_bytes()).hexdigest()!=RETAINED_SHA:raise ValueError('immutable270 producer source')
import v270_native_prepare as retained
base=retained.retained
p=base.p
require=base.require
sha=base.sha
stream_candidate=base.stream_candidate
WORKFLOW='.github/workflows/note10-v271-native-prepare.yml'
JOB='v271-native-prepare'
BUILD_SCHEMA='note10-v271-holder-carrier-build-v1'
CONTEXT_SCHEMA='note10-v271-holder-carrier-public-input-v1'
MANIFEST_SCHEMA='note10-v271-holder-carrier-sealed-members-v1'
CAPTURE_SCHEMA='note10-v271-watchdog-failure-capture-v1'
CAPTURE_LIMIT=16777216
SUCCESS_MEMBERS=(*retained.SUCCESS_MEMBERS,'watchdog-capture.json')
NEW_FILES=('v271_native_prepare.py','test_v271_watchdog_capture.py')
CARRIED270=dict(source_head='59c9af72e39ca828876778ed17d1ce0acd814381',result_sha256='814b49d82014e1732eaef5564ae31761f75746086db88dce6aea8e4a005031b9',passed=True,groups=1,variants=1,assertions=1,host_compile_attempts=1,host_fixture_process_attempts=0,replayed=False)
def source_pins():
    pins=retained.source_pins();pins.pop(retained.WORKFLOW)
    pins.update({'note10/device_test/'+n:sha(p.ordinary(HERE/n))for n in NEW_FILES})
    pins[WORKFLOW]=sha(p.ordinary(base.ROOT/WORKFLOW));return pins
def public_context(head,passed):
    p.hexid(head,40)
    require(type(passed)is dict and set(passed)=={'passed','groups','variants','assertions','result_sha256'}and passed['passed']is True and(passed['groups'],passed['variants'],passed['assertions'])==(1,2,2),'two new persist-before-reject predicates only')
    p.hexid(passed['result_sha256'])
    return dict(schema=CONTEXT_SCHEMA,source_head=head,source_sha256=source_pins(),new_fixture_PASS=passed,carried269_fixture_PASS=retained.CARRIED269,carried270_fixture_PASS=CARRIED270,holder_bytes=base.capacity.SOURCE_CAP,CI_native_source_input_bytes=0,build_only=True)
def capture_document(result,target,command,required,allowed):
    return dict(schema=CAPTURE_SCHEMA,source_head=result['source_head'],run_id=result['run_id'],build_evidence_id=result['build_evidence_id'],source_sha256=result['source_sha256'],driver_target=target,driver_command_sha256=sha(command),required_helpers=sorted(required),allowed_external_edges=sorted(allowed),complete=False,status='incomplete',phase='helper-loop',current_helper=None,rejected_helper=None,helpers={},owner=None)
def save_capture(out,value):
    def encoded(data):return (json.dumps(data,indent=2,sort_keys=True)+'\n').encode()
    raw=encoded(value)
    if len(raw)>CAPTURE_LIMIT:
        small={**value,'complete':False,'status':'capture-limit-exceeded','candidate_json_bytes':len(raw),'raw_text_omitted_due_to_limit':True}
        small['helpers']={n:{k:v for k,v in entry.items()if k!='raw_objdump'}for n,entry in value['helpers'].items()}
        if value['owner']is not None:small['owner']={k:v for k,v in value['owner'].items()if k!='raw_objdump'}
        bounded=encoded(small)
        if len(bounded)>CAPTURE_LIMIT:
            small['edge_details_omitted_due_to_limit']=True
            for entry in small['helpers'].values():
                for key in ('calls','unknown_edges'):
                    details=entry.pop(key);entry[key+'_count']=len(details);entry[key+'_sha256']=sha(encoded(details))
            bounded=encoded(small)
        require(len(bounded)<=CAPTURE_LIMIT,'bounded271 incomplete metadata')
        (out/'watchdog-capture.json').write_bytes(bounded)
        raise ValueError('bounded271 capture report exceeded')
    (out/'watchdog-capture.json').write_bytes(raw)
def guard_binding_body(out,bundle,name,argv,body,frame,required,allowed):
    calls=set(re.findall(r'R_AARCH64_(?:CALL26|JUMP26)\s+(\S+)',body))
    indirect=bool(re.search(r'\bblr\b',body));unknown=sorted(calls-(required|allowed))
    passed=calls<=required|allowed and not indirect
    bundle['helpers'][name]=dict(helper=name,argv=list(map(str,argv)),raw_objdump=body,raw_objdump_bytes=len(body.encode()),raw_objdump_sha256=sha(body.encode()),calls=sorted(calls),unknown_edges=unknown,indirect_blr=indirect,guard_passed=passed,frame=frame,frame_passed=False)
    bundle.update(current_helper=name,phase='helper-guard',status='incomplete'if passed else'rejected',rejected_helper=None if passed else name)
    save_capture(out,bundle)
    require(calls<=required|allowed and not re.search(r'\bblr\b',body),'no new269 indirect/hardware/external callback')
    return calls
def collect_binding(objects,out,result,run,linked):
    def capture(argv):
        done=subprocess.run(list(map(str,argv)),stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=True,timeout=60)
        require(0<len(done.stdout)<=8388608 and len(done.stderr)<=65536,'bounded269 target text');return done.stdout.decode()
    target='drivers/watchdog/s3c2410_wdt.o';obj=objects/target;command=p.ordinary(objects/'drivers/watchdog/.s3c2410_wdt.o.cmd')
    require(b'clang-14'in command and b'-DMODULE'not in command,'same builtin269 driver command')
    usage= p.ordinary(objects/stream_candidate.compiler_stack_path(command,target)).decode();frames=stream_candidate.frames(usage)
    nm=capture(['aarch64-linux-gnu-nm','--format=posix','--print-size',obj]);rows={r[0]:r for l in nm.splitlines()if len(r:=l.split())in (3,4)}
    require(all(len(rows[n])==3 and rows[n][1]=='A'and int(rows[n][2],16)==v for n,v in {'n269_size_binding':40,'n269_align_binding':8}.items()),'actual269 ABI40/8')
    required={'n269_empty','n269_begin','n269_publish','n269_remove','n269_snapshot','n269_layout_witness'}
    require(required<=set(rows)and required<=set(frames),'actual269 driver/helper frames')
    linked_rows={r[0]:r for l in linked.splitlines()if len(r:=l.split())==4}
    owner_rows={r[0]:r for l in p.ordinary(out/'owner-symbols.log').decode().splitlines()if len(r:=l.split())==4}
    require(int(owner_rows['n269_binding_storage'][3],16)==40 and int(owner_rows['n269_binding_storage'][2],16)-int(owner_rows['n226_source_pool'][2],16)==43664,'actual269 pool alias')
    disassembly={};edges={};allowed={'memcpy','memset','_raw_spin_lock','_raw_spin_trylock','_raw_spin_unlock','preempt_schedule','preempt_schedule_notrace','__stack_chk_fail','queued_spin_lock_slowpath'}
    bundle=capture_document(result,target,command,required,allowed);save_capture(out,bundle)
    for name in sorted(required):
        bundle.update(current_helper=name,phase='linked-body');save_capture(out,bundle)
        require(name in linked_rows and int(rows[name][3],16)==int(linked_rows[name][3],16)>0,'actual269 linked body')
        argv=['aarch64-linux-gnu-objdump','-dr','--disassemble='+name,obj]
        body=capture(argv);disassembly[name]=body
        calls=guard_binding_body(out,bundle,name,argv,body,frames[name],required,allowed);edges[name]=sorted(calls)
        require(frames[name]['kind']=='static'and 0<=frames[name]['bytes']<=8192,'actual269 static helper frame')
        bundle['helpers'][name]['frame_passed']=True
        save_capture(out,bundle)
    owner_argv=['aarch64-linux-gnu-objdump','-dr','--disassemble=n226_ingest_prepared_locked',objects/'arch/arm64/mm/init.o']
    owner_call=capture(owner_argv)
    bundle['owner']=dict(argv=list(map(str,owner_argv)),raw_objdump=owner_call,raw_objdump_bytes=len(owner_call.encode()),raw_objdump_sha256=sha(owner_call.encode()))
    bundle.update(current_helper=None,phase='owner-caller');save_capture(out,bundle)
    require(len(re.findall(r'R_AARCH64_CALL26\s+n269_snapshot\b',owner_call))==1,'one actual269 current owner caller')
    writable={n:int(row[3],16)for n,row in rows.items()if n.startswith('n269_')and len(row)==4 and row[1]in('b','B','d','D')}
    bundle.update(phase='writable',driver_writable_bytes=writable);save_capture(out,bundle)
    require(writable.get('n269_cache')==40 and set(writable)=={'n269_cache','n269_cache_lock'},'actual269 named driver writable inventory')
    value=dict(schema='note10-v269-watchdog-binding-target-v1',source_head=result['source_head'],run_id=result['run_id'],compiled_current_callers=1,record_bytes=40,pool_offset=43664,new_pool_bytes=0,driver_object_sha256=sha(p.ordinary(obj,67108864)),driver_command_sha256=sha(command),driver_writable_bytes=writable,driver_writable_total_bytes=sum(writable.values()),frames={n:frames[n]for n in required},external_edges=edges,disassembly=disassembly,owner_call_disassembly=owner_call,driver_symbols=nm,probe_cached_rate_stale_possible=True,armed=False,autonomous_return=False,post_shutdown=False)
    p.save(out/'watchdog-evidence.json',value)
    bundle.update(complete=True,status='complete',phase='complete');save_capture(out,bundle)
    return {k:v for k,v in value.items()if k not in ('disassembly','owner_call_disassembly','driver_symbols')}

_bind=retained._bind
_ENV={**retained._ENV,**{k:globals()[k]for k in ('WORKFLOW','JOB','BUILD_SCHEMA','CONTEXT_SCHEMA','MANIFEST_SCHEMA','SUCCESS_MEMBERS','source_pins','public_context','collect_binding')}}
run_build=_bind(retained.run_build,_ENV,{'note10/private/v270-ci-native-prepare':'note10/private/v271-ci-native-prepare','v270':'v271','"-v270-watchdog-noinline-macro"':'"-v271-watchdog-failure-capture"'})
seal=_bind(retained.seal,_ENV,{})
_ENV.update(run_build=run_build,seal=seal)
main=_bind(retained.main,_ENV,{})
if __name__=='__main__':main()
