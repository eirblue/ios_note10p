"""Only corrected probe locator and two unexecuted276 Python assertions."""
import copy,hashlib,json
from pathlib import Path
HERE=Path(__file__).resolve().parent
if hashlib.sha256((HERE/'test_v276_watchdog_core_completion.py').read_bytes()).hexdigest()!='48b0617a19195549d5e7ee961511c39a24afbc0d95fd5f9bc647ac9bf5296177':raise ValueError('immutable276 synthetic metadata source')
from test_v276_watchdog_core_completion import synthetic,reject
CASES=('probe-scoped-error-seam','core-frame-schema','cross-TU-domain')

def run(output,producer,parameters):
    p=producer;out=Path(output);done=[]
    def save(name,value):(out/name).write_text(json.dumps(value,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    try:
        pin=parameters['driver_source'];raw=Path(pin['path']).read_bytes()
        if len(raw)!=pin['bytes']or p.sha(raw)!=pin['sha256']:raise ValueError('exact retained driver input')
        driver=p.transform_binding(p.TARGET[:-2]+'.c',raw)
        start=driver.index(b'static int s3c2410wdt_probe(');end=driver.index(b'\nstatic int s3c2410wdt_remove(',start);probe=driver[start:end]
        chunk=b' err:\n\tif (n269_token == 1) n269_remove(wdt);\n\treturn ret;'
        prior=p.prior_transform_binding(p.TARGET[:-2]+'.c',raw)
        undo=driver.replace(b'#include "v276_watchdog_driver.inc"',b'#include "v270_watchdog_driver.inc"',1).replace(b'\tif (n269_token == 1) n269_remove(wdt);\n',b'',1)
        if probe.count(chunk)!=1 or undo!=prior:raise ValueError('new277 exact probe-scoped error seam')
        done.append(CASES[0]);identity=dict(id='a'*32,boot='b'*32,cycle='c'*32)
        def report(schema=2,state=2,flags=63,dog=7):return 'N276WDT '+' '.join(k+'='+v for k,v in identity.items())+f' result=0 schema={schema} state={state} error=0 cluster=0 variant=1 flags={flags} watchdog_id={dog} probe_cached_rate_hz=26000000 reserved=0 post_shutdown=0 armed=0 autonomous_return=0 XNU=0'
        observed=p.decode_binding([report()],identity)
        if not observed['qualified']or observed['watchdog_id_semantics']!='successful-core-registration'or p.decode_binding([report(flags=59,dog=4294967295)],identity)['qualified']or p.decode_binding([report(state=1)],identity)['qualified']or not reject(lambda:p.decode_binding([report(schema=1)],identity))or not reject(lambda:p.decode_binding([report().replace('a'*32,'d'*32)],identity)):raise ValueError('new276 strict core-registration frame')
        done.append(CASES[1]);item,table,raw,helper,graph=synthetic(p);proof=p.core_certificate(item,table,raw,helper,graph);aggregate=p.aggregate_extents(graph,proof['symbol']);bad=copy.deepcopy(item);bad['elf_sections_and_symbols']=bad['elf_sections_and_symbols'].replace('FUNC LOCAL','FUNC GLOBAL');bad['elf_evidence_sha256']=p.sha(bad['elf_sections_and_symbols'].encode())
        too_many=copy.deepcopy(graph)
        for i in range(31):
            address=0x4000+4*i;too_many['nodes'][format(address,'016x')+':4']=dict(proof=dict(symbol=dict(symbol='OUTLINED_FUNCTION_'+str(i),address=address,bytes=4)),selected_local_peak_bytes=0)
        too_many.update(selected_extents=38,outlined_extents=31)
        if not(aggregate['total']==8 and proof['notification_local_peak_bytes']==16 and proof['other_core_callee_peaks_included']is False and reject(lambda:p.core_provenance(bad,table))and reject(lambda:p.core_certificate(item,table,raw.replace('bl 2600','bl 2604'),helper,graph))and reject(lambda:p.aggregate_extents(too_many,proof['symbol']))and p.driver_provenance.__globals__['ROOTS']==p.ROOTS and len(p.ROOTS)==7 and len(p.own_frame.__globals__['ROOTS'])==8 and p.scoped_closure.__globals__['classify_edge']is p.classify_edge and p.scoped_closure.__globals__['own_frame']is p.own_frame and p._driver_collect.__globals__['scoped_closure']is p.scoped_closure and p._ENV['collect_binding']is p.collect_binding and p.BOUNDARIES is p.retained.BOUNDARIES and p.retained.retained._WATCHDOG['ROOTS']!=p.ROOTS):raise ValueError('new276 fixed cross-TU/aggregate/namespace predicate')
        save('CORE-SYNTHETIC.json',dict(certificate=proof,aggregate=aggregate));done.append(CASES[2])
    except BaseException as error:
        error.fixture_progress=dict(groups=1,variants=3,assertions=len(done),planned_assertions=3,completed_variants=len(done),completed_assertions=len(done),case_names=done);raise
    return dict(groups=1,variants=3,assertions=3,completed_variants=3,completed_assertions=3,case_names=done,host_compile_attempts=0,host_fixture_process_attempts=0,old_tests_replayed=0)
