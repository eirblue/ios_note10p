"""New269 only: nine production-C predicates and three overlay/frame predicates."""
import hashlib,json,subprocess
from pathlib import Path
CASES=('ABI','incomplete','matching-success','big-null','unsupported','ambiguous','remove-reprobe','busy','context','overlay-order','frame-identity','frame-status')
def reject(call):
    try:call()
    except (ValueError,KeyError):return True
    return False
def run(output,producer,parameters):
    out=Path(output);here=Path(__file__).resolve().parent;done=[]
    def save(name,value):(out/name).write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8')
    try:
        stage=out/'staged-source';(stage/'linux').mkdir(parents=True)
        (stage/'linux/v269_watchdog_binding.h').write_bytes((here/'v269_watchdog_binding.h').read_bytes())
        argv=parameters['compiler_argv'];save('COMPILE-STARTED.json',dict(attempt=1,argv=argv))
        with(out/'compiler.stdout').open('xb')as stdout,(out/'compiler.stderr').open('xb')as stderr:
            compiled=subprocess.run(argv,cwd=out,stdout=stdout,stderr=stderr,timeout=120)
        if compiled.returncode:raise ValueError('new269 C compile failed')
        exe=out/'watchdog-binding-fixture.exe';save('C-FIXTURE-STARTED.json',dict(attempt=1,argv=[str(exe)]))
        with(out/'fixture.stdout').open('xb')as stdout,(out/'fixture.stderr').open('xb')as stderr:
            called=subprocess.run([str(exe)],cwd=out,stdout=stdout,stderr=stderr,timeout=60)
        lines=(out/'fixture.stdout').read_bytes().replace(b'\r\n',b'\n').splitlines()
        for index,name in enumerate(CASES[:9]):
            if len(lines)<=index or lines[index]!=('N269CASE '+name+'=PASS').encode():raise ValueError('new269 C predicate '+name)
            done.append(name)
        if called.returncode or len(lines)!=9:raise ValueError('foreign269 fixture output')
        pin=parameters['driver_source'];raw=Path(pin['path']).read_bytes()
        if len(raw)!=pin['bytes']or hashlib.sha256(raw).hexdigest()!=pin['sha256']:raise ValueError('exact269 driver source pin')
        changed=producer.transform_binding(producer.DRIVER,raw)
        undo=changed.replace(b'#include "v269_watchdog_driver.inc"\n',b'',1).replace(b'\tunsigned int n269_token = 0;\n',b'',1).replace(b'\tif (cluster_index == LITTLE_CLUSTER) n269_token = n269_begin();\n',b'',1).replace(b'\tn269_publish(n269_token, wdt);\n',b'',1).replace(b'\tif (wdt) n269_remove(wdt);\n',b'',1)
        if undo!=raw or not changed.index(b'n269_begin();')<changed.index(b's3c_wdt[cluster_index] = wdt;')or not changed.index(b'if (wdt) n269_remove(wdt);')<changed.index(b'if (wdt->drv_data->pmu_reset_func)',changed.index(b'static int s3c2410wdt_remove')):raise ValueError('new269 lifecycle/order')
        done.append(CASES[9]);identity=dict(id='a'*32,boot='b'*32,cycle='c'*32)
        def frame(state=2,flags=63,error=0):return 'N269WDT '+ ' '.join(k+'='+v for k,v in identity.items())+f' result=0 schema=1 state={state} error={error} cluster=0 variant=1 flags={flags} watchdog_id=0 probe_cached_rate_hz=26000000 reserved=0 post_shutdown=0 armed=0 autonomous_return=0 XNU=0'
        good=frame()
        if not producer.decode_binding([good],identity)['qualified']or not reject(lambda:producer.decode_binding([good.replace('a'*32,'d'*32)],identity)):raise ValueError('new269 exact frame identity')
        done.append(CASES[10])
        if any(producer.decode_binding([frame(state=s,error=19)],identity)['qualified']for s in (0,1,3,4,5,6))or not reject(lambda:producer.decode_binding([frame(flags=256)],identity))or not reject(lambda:producer.decode_binding([good,frame(flags=127)],identity)):raise ValueError('new269 status/closed flags')
        done.append(CASES[11])
    except BaseException as error:
        error.fixture_progress=dict(groups=1,variants=12,assertions=len(done),planned_assertions=12,completed_variants=len(done),completed_assertions=len(done),case_names=done);raise
    return dict(groups=1,variants=12,assertions=12,completed_variants=12,completed_assertions=12,case_names=done,host_compile_attempts=1,host_fixture_process_attempts=1,old_tests_replayed=0)
