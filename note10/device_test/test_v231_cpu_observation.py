"""One new C register-IO group plus its fresh overlay/target-evidence boundaries."""
import json
import os
from pathlib import Path
import subprocess
HERE=Path(__file__).resolve().parent


def command(output,compiler):
    return [compiler,'-std=c11','-O2','-Wall','-Wextra','-Werror','-DN231_HOST_FIXTURE','-I',str(HERE),
        str(HERE/'v231_cpu_observation.c'),str(HERE/'v231_cpu_observation_fixture.c'),'-o',str(Path(output)/'cpu-observation-fixture.exe')]


def new_evidence_cases():
    import v231_native_prepare as producer
    # Existing transformations instantiate the exact retained source preimages;
    # only the new231 transforms/order and type/slot gate are asserted here.
    stream=producer.pool_section.prepare((HERE/'v226_source_stream_kernel.c').read_bytes())
    store=producer.stream_candidate.prepare_owner((HERE/'v210_native_prepare_kernel.c').read_bytes())
    changed=producer.prepare_stream(stream);logging=producer.prepare_store(store)
    function=changed.split(b'static N226_NOINLINE int n226_ingest_prepared_locked',1)[1]
    initial=function.index(b'if(!n226_stack_room(');owner=function.index(b'n217_owner(ctx,&n210_destination)')
    capture=function.index(b'error=n231_capture_cpu_observation(');fresh=function.index(b'stats->ready=0;')
    sample=function.index(b'stats->sp=current_stack_pointer;',fresh);gate=function.index(b'if(!n226_stack_room(',fresh)
    decode=function.index(b'error=n226_open(');clear=function.index(b'if(error)memset(n226_source_pool+N231_POOL_OFFSET')
    if not (initial<owner<capture<fresh<sample<gate<decode<clear and function.count(b'error=n231_capture_cpu_observation(')==1 and
            b'n226_emit(error);n231_emit(error);}'in logging and logging.index(b'n231_emit(error);}')<logging.index(b'mutex_unlock(&n210_lock)')):
        raise AssertionError('admission/capture-unwind/fresh-room/decode/clear/outer-log order required')
    for transform,preimage in ((producer.prepare_stream,stream),(producer.prepare_store,store)):
        try:transform(preimage+b'\n')
        except ValueError:pass
        else:raise AssertionError('mutated new-overlay preimage must reject')
    symbols='\n'.join(name+' A '+format(value,'x')for name,value in producer.OBSERVATION_ABS.items())+'\n'
    symbols+='n226_source_pool b 1000 c000\nn231_observation_storage B '+format(0x1000+43544,'x')+' 20\nn231_capture_cpu_observation T 20000 40\n'
    usage='v231_cpu_observation.c:1:1:n231_capture_cpu_observation\t32\tstatic\n'
    sections='  [ 1] .text PROGBITS 0000000000000000 000040 000040 00 AX 0 0 4\n  1: 0000000000000000 64 FUNC GLOBAL DEFAULT 1 n231_capture_cpu_observation\n'
    actual=producer.observation_target(symbols,usage,sections)
    if actual['pool_offset']!=43544 or actual['record_bytes']!=32 or actual['capture_scheduler_chain_bound']is not False or actual['decoder_bound_includes_capture']is not False:
        raise AssertionError('record alias and separate capture-frame evidence required')
    try:producer.observation_target(symbols.replace(format(0x1000+43544,'x'),format(0x1000+43552,'x')),usage,sections)
    except ValueError:pass
    else:raise AssertionError('wrong existing-pool alias must reject')


def run(output,compiler_argv):
    output=Path(output)
    if compiler_argv!=command(output,compiler_argv[0]):raise ValueError('exact new C capture fixture argv required')
    env=dict(os.environ);env['PATH']=str(Path(compiler_argv[0]).parent)+os.pathsep+env.get('PATH','')
    (output/'COMPILE-STARTED.json').write_text(json.dumps(dict(argv=compiler_argv,attempt=1))+'\n',encoding='utf-8')
    with (output/'compile.log').open('xb')as log:
        subprocess.run(compiler_argv,stdout=log,stderr=subprocess.STDOUT,env=env,check=True,timeout=120)
    (output/'COMPILE-COMPLETED.json').write_text('{"returncode":0}\n',encoding='ascii')
    argv=[str(output/'cpu-observation-fixture.exe')]
    (output/'C-FIXTURE-STARTED.json').write_text(json.dumps(dict(argv=argv,attempt=1))+'\n',encoding='utf-8')
    done=subprocess.run(argv,capture_output=True,env=env,check=False,timeout=120)
    (output/'fixture.stdout').write_bytes(done.stdout);(output/'fixture.stderr').write_bytes(done.stderr)
    (output/'C-FIXTURE-COMPLETED.json').write_text(json.dumps(dict(returncode=done.returncode))+'\n',encoding='ascii')
    done.check_returncode()
    if json.loads(done.stdout)!=dict(groups=1,variants=8,assertions=30):raise ValueError('actual C capture counts differ')
    new_evidence_cases();return dict(groups=1,variants=13,assertions=35,C_variants=8,C_assertions=30,evidence_variants=5,evidence_assertions=5)
