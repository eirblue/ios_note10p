"""One macro-enabled production-include compile; no link or C execution."""
import json,subprocess
from pathlib import Path
CASE='kernel-noinline-macro-all-six'
def run(output,producer,parameters):
    out=Path(output);here=Path(__file__).resolve().parent;done=[]
    def save(name,value):(out/name).write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8')
    try:
        old=(here/'v269_watchdog_driver.inc').read_bytes();fixed=(here/'v270_watchdog_driver.inc').read_bytes()
        if old.count(b'__attribute__((noinline))')!=6 or fixed!=old.replace(b'__attribute__((noinline))',b'__attribute__((__noinline__))'):raise ValueError('exact six reserved-token repairs')
        stage=out/'staged-source';linux=stage/'linux';linux.mkdir(parents=True)
        header=(here/'v269_watchdog_binding.h').read_bytes()
        (stage/'v269_watchdog_binding.h').write_bytes(header);(linux/'v269_watchdog_binding.h').write_bytes(header)
        (stage/'v270_watchdog_driver.inc').write_bytes(fixed)
        fixture=(here/'v269_watchdog_binding_fixture.c').read_bytes()
        if fixture.count(b'#include "v269_watchdog_driver.inc"')!=1:raise ValueError('one actual production include')
        (stage/'macro-fixture.c').write_bytes(b'#include <stddef.h>\n'+fixture.replace(b'#include "v269_watchdog_driver.inc"',b'#include "v270_watchdog_driver.inc"'))
        for name,raw in {'types.h':b'#include <stdint.h>\ntypedef uint32_t u32; typedef uint64_t u64;\n','preempt.h':b'','spinlock.h':b'','string.h':b'#include <string.h>\n','errno.h':b'#include <errno.h>\n'}.items():(linux/name).write_bytes(raw)
        argv=parameters['compiler_argv'];save('COMPILE-STARTED.json',dict(attempt=1,argv=argv,compile_only=True))
        with(out/'compiler.stdout').open('xb')as stdout,(out/'compiler.stderr').open('xb')as stderr:
            compiled=subprocess.run(argv,cwd=out,stdout=stdout,stderr=stderr,timeout=120)
        if compiled.returncode:raise ValueError('new270 kernel macro compile failed')
        done.append(CASE)
    except BaseException as error:
        error.fixture_progress=dict(groups=1,variants=1,assertions=len(done),planned_assertions=1,completed_variants=len(done),completed_assertions=len(done),case_names=done);raise
    return dict(groups=1,variants=1,assertions=1,completed_variants=1,completed_assertions=1,case_names=done,host_compile_attempts=1,host_fixture_process_attempts=0,old_tests_replayed=0)
