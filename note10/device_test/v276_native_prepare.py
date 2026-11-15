"""276 records actual core completion; fixed-domain scalar lifecycle and source proofs."""
import hashlib,json,re,subprocess
from collections import deque
from pathlib import Path
HERE=Path(__file__).resolve().parent
RETAINED_SHA='9f0492cf5e5250ff0b21e3a8fd40560176105b40d44b8aec7c57428a065dd8e4'
if hashlib.sha256((HERE/'v275_native_prepare.py').read_bytes()).hexdigest()!=RETAINED_SHA:raise ValueError('immutable275 producer')
import v275_native_prepare as retained
selected=retained.selected
p,require,sha=retained.p,retained.require,retained.sha
reader,flow=selected.reader,selected.flow
ROOTS=(*selected.ROOTS,'n276_core_registered')
CORE_CALLER='__watchdog_register_device'
CORE_TARGET='drivers/watchdog/watchdog_core.o'
FRAME_C_NAMES=(*ROOTS,CORE_CALLER)
TARGET=selected.TARGET
BOUNDARIES=retained.BOUNDARIES
WORKFLOW='.github/workflows/note10-v276-native-prepare.yml'
JOB='v276-native-prepare'
BUILD_SCHEMA='note10-v276-holder-carrier-build-v1'
CONTEXT_SCHEMA='note10-v276-holder-carrier-public-input-v1'
MANIFEST_SCHEMA='note10-v276-holder-carrier-sealed-members-v1'
CAPTURE_SCHEMA='note10-v276-watchdog-core-completion-raw-v1'
TARGET_SCHEMA='note10-v276-watchdog-binding-target-v1'
SUCCESS_MEMBERS=retained.SUCCESS_MEMBERS
NEW_FILES=('v276_watchdog_binding.h','v276_watchdog_driver.inc','v276_watchdog_owner.inc','v276_watchdog_binding_fixture.c','test_v276_watchdog_core_completion.py','v276_native_prepare.py')
CORE_PREIMAGE='a6f79808ca6cb599483beda9054cc838f14016ee3be6ad863da2b9d41cabda53'
DRIVER_PREPARED='3b83eadeb05153537c95a11c48fb1f1e0d132a7bd989d9f1970a7953b657c648'
CARRIED275=dict(source_head='290296a1d231011042551e2cfd9f9651db40e740',result_sha256='540b5045159a701c7e18e85ed0560eafcf6bb23ecf2083e8df474370f72b41ba',passed=True,groups=1,variants=3,assertions=3,host_compile_attempts=0,host_fixture_process_attempts=0,replayed=False)
GUARD=b'#if defined(CONFIG_NOTE10_V210_NATIVE_PREPARE) && defined(CONFIG_S3C2410_WATCHDOG)\n'

def source_pins():
    pins=retained.source_pins();pins.pop(retained.WORKFLOW)
    pins.update({'note10/device_test/'+n:sha(p.ordinary(HERE/n))for n in NEW_FILES})
    pins[WORKFLOW]=sha(p.ordinary(selected.base.ROOT/WORKFLOW));return pins

def public_context(head,passed):
    p.hexid(head,40)
    require(type(passed)is dict and set(passed)=={'passed','groups','variants','assertions','result_sha256'}and passed['passed']is True and(passed['groups'],passed['variants'],passed['assertions'])==(1,9,9),'new nine completion predicates')
    p.hexid(passed['result_sha256'])
    carried=retained.public_context(CARRIED275['source_head'],dict(passed=True,groups=1,variants=3,assertions=3,result_sha256=CARRIED275['result_sha256']))
    carried.update(schema=CONTEXT_SCHEMA,source_head=head,source_sha256=source_pins(),new_fixture_PASS=passed,carried275_fixture_PASS=CARRIED275);return carried

def once(raw,old,new):
    require(raw.count(old)==1,'one exact276 source seam');return raw.replace(old,new,1)

def extend_driver(raw):
    require(sha(raw)==DRIVER_PREPARED,'exact retained275 prepared driver')
    raw=once(raw,b'#include "v270_watchdog_driver.inc"',b'#include "v276_watchdog_driver.inc"')
    return once(raw,b' err:\n\treturn ret;',b' err:\n\tif (n269_token == 1) n269_remove(wdt);\n\treturn ret;')

def transform_core(raw):
    require(sha(raw)==CORE_PREIMAGE,'exact stock watchdog core source')
    anchor=b'#include "watchdog_core.h"\t/* For watchdog_dev_register/... */\n'
    raw=once(raw,anchor,anchor+GUARD+b'#include <linux/v276_watchdog_binding.h>\n#endif\n')
    anchor=b'\treturn 0;\n}\n\n/**\n * watchdog_register_device() - register a watchdog device'
    return once(raw,anchor,GUARD+b'\tn276_core_registered(wdd);\n#endif\n'+anchor)

def transform_binding(path,raw):
    changed=retained._ENV['transform_binding'](path,raw)
    return extend_driver(changed)if path==TARGET[:-2]+'.c'else changed

def install_binding(source,buffers):
    value=retained._ENV['install_binding'](source,buffers)
    for name,target in {'v276_watchdog_binding.h':'include/linux/v276_watchdog_binding.h','v276_watchdog_driver.inc':'drivers/watchdog/v276_watchdog_driver.inc','v276_watchdog_owner.inc':'arch/arm64/mm/v276_watchdog_owner.inc'}.items():
        path=source/target;require(not path.exists(),'fresh276 include target');path.write_bytes(buffers['note10/device_test/'+name])
    replacements={'arch/arm64/mm/init.c':(b'#include "v269_watchdog_owner.inc"',b'#include "v276_watchdog_owner.inc"'),'arch/arm64/mm/v226_source_stream_kernel.c':(b'#include <linux/v269_watchdog_binding.h>',b'#include <linux/v276_watchdog_binding.h>')}
    for name,(old,new)in replacements.items():
        path=source/name;changed=once(p.ordinary(path),old,new);path.write_bytes(changed);value['compiler_inputs'][name]['after_sha256']=sha(changed)
    path=source/'drivers/watchdog/s3c2410_wdt.c';changed=extend_driver(p.ordinary(path));path.write_bytes(changed);value['compiler_inputs']['drivers/watchdog/s3c2410_wdt.c']['after_sha256']=sha(changed)
    path=source/'drivers/watchdog/watchdog_core.c';before=p.ordinary(path);after=transform_core(before);path.write_bytes(after)
    value['compiler_inputs']['drivers/watchdog/watchdog_core.c']=dict(before_sha256=sha(before),after_sha256=sha(after))
    value.update(source_sha256={n:sha(buffers['note10/device_test/'+n])for n in('v276_watchdog_binding.h','v276_watchdog_driver.inc','v276_watchdog_owner.inc')},record_schema=2,core_success_only=True,scalar_latch_merge=True,probe_error_invalidation=True,live_pointer_escape=False)
    return value

def classify_edge(edge,context,roots):
    records=edge['resolved_records'];names={r['name']for r in records};witness=names&BOUNDARIES
    if not witness:return _root_classifier(edge,context,roots)
    require(edge['mnemonic']in('bl','b')and not edge['unresolved'],'ordinary resolved watchdog call/tail only')
    require(1<=len(records)<=32 and edge['resolved_symbols']==sorted(names)and all(r['kind']in('T','t','W','w')and type(r['ordinal'])is int and r['ordinal']>=0 for r in records)and len({r['ordinal']for r in records})==len(records),'bounded complete boundary alias records')
    require(all(r['offset']==0 and r['address']==edge['target']for r in records),'exact boundary alias entry only')
    extents={(r['address'],r['bytes'])for r in records};require(len(extents)==1,'one exact boundary alias extent')
    start,size=next(iter(extents))
    require(type(start)is type(size)is int and 0<start<1<<64 and 0<size<1<<64 and start%4==size%4==0 and start+size<1<<64,'valid bounded AArch64 boundary alias extent')
    return dict(kind='boundary',names=sorted(witness),key=(start,size),aliases=sorted(names),alias_records=records)

def scoped_closure(out,bundle,context,roots,table,capture):
    pending=deque();selected={};nodes={};outlined_count=0
    def enqueue(name,record,outlined,provenance):
        nonlocal outlined_count
        symbol=symbol_extent(table,name,record,outlined);key=(symbol['address'],symbol['bytes'])
        if key in selected:return key
        if outlined:outlined_count+=1
        require(outlined_count<=32 and len(selected)<37,'bounded watchdog selected frontier')
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

def decode_binding(texts,expected):
    require(set(expected)=={'id','boot','cycle'}and all(re.fullmatch('[0-9a-f]{32}',v)for v in expected.values()),'same actual frame identity')
    fields={'id','boot','cycle','result','schema','state','error','cluster','variant','flags','watchdog_id','probe_cached_rate_hz','reserved','post_shutdown','armed','autonomous_return','XNU'};rows=[]
    for text in texts:
        for line in text.splitlines():
            if 'N276WDT 'not in line:continue
            words=line.split('N276WDT ',1)[1].split();row={}
            for word in words:
                require(word.count('=')==1,'exact269 frame token');k,v=word.split('=');require(k not in row,'no duplicate269 field');row[k]=v
            require(set(row)==fields and all(row[k]==v for k,v in expected.items()),'current269 closed frame identity')
            values={k:int(v)for k,v in row.items()if k not in expected}
            require(values['schema']==2 and 0<=values['state']<=6 and values['flags']&~255==0 and values['reserved']==0 and all(values[k]==0 for k in ('post_shutdown','armed','autonomous_return','XNU')),'closed269 values/no authority')
            require(all(0<=values[k]<=0xffffffff for k in ('error','cluster','variant','flags','watchdog_id'))and 0<=values['probe_cached_rate_hz']<=0xffffffffffffffff,'fixed width269 values')
            require(not rows or rows[0]==values,'no conflicting269 frames');rows.append(values)
    require(rows,'actual269 frame missing');v=rows[0]
    qualified=v['result']==v['error']==0 and v['state']==2 and v['cluster']==0 and v['variant']==1 and v['flags']&63==63 and not v['flags']&64 and v['watchdog_id']!=0xffffffff and v['probe_cached_rate_hz']>0
    return dict(schema='note10-v276-watchdog-core-completion-observation-v1',identity=expected,values=v,qualified=qualified,watchdog_id_semantics='successful-core-registration',probe_cached_rate_stale_possible=True,post_shutdown=False,armed=False,autonomous_return=False,XNU=False)


def core_provenance(item,table):
    require(CORE_CALLER in table and len(table[CORE_CALLER])==1,'one actual fixed core caller')
    row=table[CORE_CALLER][0]
    require(row['kind']=='t','actual LOCAL core caller required')
    proof=reader.object_proof(CORE_TARGET,item,(CORE_CALLER,),{CORE_CALLER:row})[CORE_CALLER]
    require(proof['binding']=='LOCAL','actual core ELF binding')
    return dict(**proof,ordinal=row['ordinal'])

def aggregate_extents(driver,core_symbol):
    nodes=driver['nodes'];keys={(v['proof']['symbol']['address'],v['proof']['symbol']['bytes'])for v in nodes.values()}
    names={v['proof']['symbol']['symbol']for v in nodes.values()}
    require(set(ROOTS)<=names and driver['selected_extents']==len(nodes)==len(keys)<=37,'seven driver roots within reserved aggregate budget')
    core_key=(core_symbol['address'],core_symbol['bytes'])
    require(core_key not in keys and len(keys)+1<=38 and driver['outlined_extents']<=30,'one aggregate38 including fixed core caller')
    return dict(total=len(keys)+1,driver_extents=len(keys),core_caller_extents=1,outlined_extents=driver['outlined_extents'],extents=[dict(address=a,bytes=b,kind='core-caller'if(a,b)==core_key else'driver')for a,b in sorted(keys|{core_key})])

def core_certificate(item,table,raw,helper,driver):
    provenance=core_provenance(item,table);record=table[CORE_CALLER][0]
    symbol=selected.symbol_extent(table,CORE_CALLER,record)
    proof=selected.scoped_transfers(raw,symbol,table);rows=flow.parse_body(raw,proof);external={};notifications=[]
    for edge in proof['external_transfers']:
        records=edge['resolved_records'];keys={(r['address'],r['bytes'])for r in records}
        require(edge['mnemonic']in('bl','b')and not edge['unresolved']and 1<=len(records)<=32 and len(keys)==1 and all(r['offset']==0 and r['address']==edge['target']for r in records),'entry-bound ordinary core caller transfers only')
        external[edge['address']]='opaque-core-call'
        if edge['target']==helper['linked_address']:
            require(edge['mnemonic']=='bl'and keys=={(helper['linked_address'],helper['bytes'])}and {r['name']for r in records}=={'n276_core_registered'},'exact core-to-driver notification entry')
            notifications.append(edge)
    require(len(notifications)==1,'one actual core successful-completion caller')
    frame=own_frame(CORE_CALLER,rows,external,provenance['frame_bytes'],False)
    key=format(helper['linked_address'],'016x')+':'+str(helper['bytes']);site=notifications[0]['address']
    require(key in driver['nodes']and site in frame['call_SP_offsets'],'actual helper local certificate at core notification')
    peak=max(frame['own_peak_bytes'],-frame['call_SP_offsets'][site]+driver['nodes'][key]['selected_local_peak_bytes'])
    require(peak<=8192,'bounded core-own plus notification-helper local contribution')
    return dict(provenance=provenance,symbol=symbol,proof=proof,frame_certificate=frame,notification=notifications[0],notification_local_peak_bytes=peak,other_core_callee_peaks_included=False,whole_core_stack_bound_proven=False)

def save_driver_pending(out,bundle):
    if bundle.get('complete')is True:bundle={**bundle,'complete':False,'status':'incomplete','phase':'driver-complete-core-pending'}
    retained.save_capture(out,bundle)

def collect_binding(objects,out,result,run,linked):
    value=_driver_collect(objects,out,result,run,linked)
    bundle=json.loads(p.ordinary(out/'watchdog-capture.json',16777216));bundle.update(complete=False,status='incomplete',phase='core-metadata',core=dict(frame_passed=False));retained.save_capture(out,bundle)
    def persist():retained.save_capture(out,bundle)
    def capture(argv):
        argv=list(map(str,argv));tool=dict(argv=argv,returncode=None);bundle['tools'].append(tool);persist()
        try:done=subprocess.run(argv,stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=False,timeout=120)
        except subprocess.TimeoutExpired as error:
            tool.update(timeout=True,raw_stdout=(error.stdout or b'').decode(errors='replace'),raw_stderr=(error.stderr or b'').decode(errors='replace'));persist();raise
        tool.update(returncode=done.returncode,stdout_sha256=sha(done.stdout),raw_stdout=done.stdout.decode(errors='replace'),raw_stderr=done.stderr.decode(errors='replace'));persist()
        require(done.returncode==0 and 0<len(done.stdout)<=2097152 and len(done.stderr)<=65536,'bounded actual core evidence tool');return done.stdout.decode()
    try:
        require(all(result['effective_profile'].get(k)=='y'for k in('NOTE10_V210_NATIVE_PREPARE','S3C2410_WATCHDOG','WATCHDOG_CORE')),'builtin276 diagnostic/core source domain')
        table=reader.linked_symbols(linked);core=bundle['core'];command=p.ordinary(objects/'drivers/watchdog/.watchdog_core.o.cmd');core.update(raw_command=command.decode(),command_sha256=sha(command));persist()
        relative=selected.stream_candidate.compiler_stack_path(command,CORE_TARGET);usage=p.ordinary(objects/relative).decode();core.update(raw_SU=usage,stack_relative=str(relative),stack_sha256=sha(usage.encode()));persist()
        elf=capture(['aarch64-linux-gnu-readelf','--wide','--sections','--symbols',objects/CORE_TARGET]);core.update(raw_ELF=elf,elf_sha256=sha(elf.encode()));persist()
        item=dict(command=command.decode(),command_sha256=sha(command),stack_usage=usage,stack_sha256=sha(usage.encode()),stack_relative=str(relative),elf_sections_and_symbols=elf,elf_evidence_sha256=sha(elf.encode()))
        provenance=core_provenance(item,table);core['provenance']=provenance
        compiler=result['preparation']['watchdog_binding']['compiler_inputs'];source=Path(provenance['translation_unit'])
        require(sha(p.ordinary(source))==compiler['drivers/watchdog/watchdog_core.c']['after_sha256'],'actual compiled core source after exact success overlay')
        require(sha(p.ordinary(Path(value['driver_TU']['translation_unit'])))==compiler['drivers/watchdog/s3c2410_wdt.c']['after_sha256'],'actual compiled driver lifecycle source overlay')
        require(len({(v['linked_address'],v['bytes'])for v in value['root_provenance'].values()})==7,'seven distinct driver-root extents')
        record=table[CORE_CALLER][0];symbol=selected.symbol_extent(table,CORE_CALLER,record)
        aggregate=aggregate_extents(value['local_closure'],symbol);core['symbol']=symbol;bundle['phase']='core-body';persist()
        raw=capture(['aarch64-linux-gnu-objdump','-d','--disassemble-zeroes','--start-address='+hex(symbol['address']),'--stop-address='+hex(symbol['address']+symbol['bytes']),objects/'vmlinux'])
        core.update(raw_objdump=raw,raw_objdump_sha256=sha(raw.encode()));bundle['phase']='core-frame';persist()
        certificate=core_certificate(item,table,raw,value['root_provenance']['n276_core_registered'],value['local_closure']);core.update(certificate=certificate,frame_passed=True);persist()
        value.update(record_schema=2,compiled_core_notification_callers=1,watchdog_id_semantics='successful-core-registration',core_registration_caller=certificate,aggregate_selected=aggregate,completed_core_evidence_required=True,live_pointer_escape=False)
        complete=json.loads(p.ordinary(out/'watchdog-evidence.json',16777216));complete.update(value);p.save(out/'watchdog-evidence.json',complete)
        bundle.update(complete=True,status='complete',phase='complete',current_helper=None,current_edge=None,aggregate_selected=aggregate);persist();return value
    except BaseException as error:
        bundle.update(complete=False,status='rejected',rejection_type=type(error).__name__,rejection_reason=str(error)[:2048]);persist();raise

_bind=retained._bind
_FRAME_ENV={**retained.own_frame.__globals__,'ROOTS':FRAME_C_NAMES}
own_frame=_bind(retained.own_frame,_FRAME_ENV,{})
_WATCHDOG={**retained._WATCHDOG,**{k:globals()[k]for k in('ROOTS','CAPTURE_SCHEMA','TARGET_SCHEMA','own_frame','classify_edge')},'save_capture':save_driver_pending}
_root_classifier=_bind(selected.classify_edge,_WATCHDOG,{})
driver_provenance=_bind(selected.driver_provenance,_WATCHDOG,{})
_WATCHDOG['driver_provenance']=driver_provenance
capture_document=_bind(retained.capture_document,_WATCHDOG,{})
scoped_closure=_bind(scoped_closure,_WATCHDOG,{})
_WATCHDOG.update(capture_document=capture_document,scoped_closure=scoped_closure)
_driver_collect=_bind(retained.collect_binding,_WATCHDOG,{})
_ENV={**retained._ENV,**{k:globals()[k]for k in('WORKFLOW','JOB','BUILD_SCHEMA','CONTEXT_SCHEMA','MANIFEST_SCHEMA','SUCCESS_MEMBERS','source_pins','public_context','install_binding','collect_binding')}}
run_build=_bind(retained.run_build,_ENV,{'note10/private/v275-ci-native-prepare':'note10/private/v276-ci-native-prepare','v275':'v276','"-v275-watchdog-C-frame-address"':'"-v276-watchdog-core-completion"'})
seal=_bind(retained.seal,_ENV,{})
_ENV.update(run_build=run_build,seal=seal)
main=_bind(retained.main,_ENV,{})
save_capture=retained.save_capture
if __name__=='__main__':main()
