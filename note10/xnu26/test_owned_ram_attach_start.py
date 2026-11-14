"""Five new host lifecycle verdicts and two direct integration predicates, once."""
from copy import deepcopy
import json
import os
from pathlib import Path
import subprocess
from unittest.mock import patch
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
CASE_NAMES=('null_provider_rejected_before_factory','factory_failure_has_no_attachment','attachment_failure_releases_owned_copy','start_failure_detaches_and_releases','started_unpublished_owned_read_and_teardown','consumer_and_factory_roots_bound_truthfully','new_origin_and_existing_carrier_admission')
def command(output,compiler):
    out=Path(output)
    return [str(compiler),'--driver-mode=g++','-std=c++17','-Wall','-Wextra','-Werror','-pthread','-DKERNEL=1','-I',str(out/'fixture-includes'),'-I',str(HERE),str(HERE/'note10_owned_ram_nub.cpp'),str(HERE/'note10_readonly_ram_block_device.cpp'),str(HERE/'owned_ram_attach_fixture.cpp'),'-o',str(out/'owned-ram-attach-fixture.exe')]
def save(path,value):
    with Path(path).open('x',encoding='utf-8')as f:json.dump(value,f,sort_keys=True);f.write('\n')
def rejected(call):
    try:call()
    except (ValueError,KeyError):return True
    return False
def integration(factory):
    native=factory.native
    producer=dict(owned_ram_factory=factory.profile(),readonly_ram_nub={},user_exception_fetch={})
    current=dict(producer=producer,bindings=dict(owned_ram_factory=native.digest(factory.profile())),producer_id='1'*64,input_binding='2'*64,dependencies={factory.UNIT:dict(path=str(factory.ROOT/factory.SOURCE),source_sha256=factory.PINS[factory.SOURCE])})
    row=dict(source=factory.UNIT,category='port',source_sha256=factory.PINS[factory.SOURCE],object_path='/own/factory.o',object_sha256='3'*64,passed=True,producer_id=current['producer_id'],input_binding=current['input_binding'])
    provider=dict(source='iokit/own-provider.cpp',category='native',object_path='/own/provider.o',source_sha256='4'*64,object_sha256='5'*64,passed=True)
    first='_own_note10_create_owned_readonly_ram_nub';second='_own_note10_attach_owned_readonly_ram_nub'
    definitions={first:[row['object_path']],second:[row['object_path']],'_own_service':[provider['object_path']]};refs={first:[row['object_path']],'_own_service':[row['object_path']]};proof={}
    factory.bind_origins(current,[row,provider],definitions,refs,{},proof)
    roots=factory.link_root(current)
    with patch.object(native,'expected_objects',return_value=1079):factory.final_symbols('0 T '+first+'\n1 T '+second,dict(link_succeeded=True,object_count=1079),current,proof)
    missing=deepcopy(definitions);del missing[second];external=deepcopy(refs);external[second]=[provider['object_path']]
    return roots==['-Wl,-u,'+first,'-Wl,-u,'+second]and proof['consumer_retained']is True and proof['factory_same_object_reference_observed']is True and proof['external_consumer_callers']==0 and proof['local_factory_source_calls']==1 and proof['consumer_invoked']is proof['factory_invoked']is proof['provider_started']is False and rejected(lambda:factory.bind_origins(current,[row,provider],missing,refs,{},{}))and rejected(lambda:factory.bind_origins(current,[row,provider],definitions,external,{},{}))
def origin(parcel):
    raw=b'own synthetic native input';expected=dict(source_head='1'*40,run_id=1,run_attempt=1,kernel_sha256=parcel.sha(raw),kernel_bytes=len(raw),producer_id='2'*64,input_binding='3'*64)
    proof=dict(passed=True,external_consumer_callers=0,consumer_retained=True,consumer_invoked=False,local_factory_source_consumer='note10_attach_owned_readonly_ram_nub',local_factory_source_calls=1)
    producer=dict(schema='note10-v262-owned-ram-attach-start-build-v1',passed=True,runtime_executed=False,consumer_invoked=False,physical_ready=False,native_activation=False,factory_invoked=False,provider_started=False,provider_registered=False,final_object_count=1079,owned_ram_factory=proof,**{k:expected[k]for k in ('source_head','run_id','run_attempt','kernel_sha256','kernel_bytes')})
    manifest=dict(schema='note10-v262-owned-ram-attach-start-native-handoff-build-v1',owned_ram_factory=proof,**{k:expected[v]for k,v in dict(source_commit='source_head',run_id='run_id',run_attempt='run_attempt',output_sha256='kernel_sha256',output_size='kernel_bytes',producer_id='producer_id',input_binding='input_binding').items()})
    geometry=dict(virtual_base=4096,kernel_span=16384,kernel_entry_offset=0,entry_extent_offset=0,entry_extent_bytes=4,pool_offset=4096,pool_bytes=4096,segments=[]);calls=[]
    def materialize(raw,segments):calls.append(1);return 4096,bytes(16384)
    with patch.object(parcel.core,'parse_kernel',return_value=geometry):
        memory,descriptor,metadata=parcel.parcel(raw,producer,manifest,expected,materialize)
        stale=dict(producer,schema='note10-v261-owned-ram-integrated-build-v1')
        old_rejected=rejected(lambda:parcel.parcel(raw,stale,manifest,expected,materialize))
    with patch.object(parcel.core,'parse_kernel',return_value=dict(geometry,kernel_span=parcel.KERNEL_CAP+16384)):
        over_rejected=rejected(lambda:parcel.parcel(raw,producer,manifest,expected,materialize))
    return len(calls)==1 and len(memory)==16384 and len(descriptor)==256 and metadata['schema']==parcel.STEM+'-source-parcel-v1'and old_rejected and over_rejected

def run(output,compiler_argv,factory,parcel):
    out=Path(output);done=[]
    if compiler_argv!=command(out,compiler_argv[0]):raise ValueError('exact new host compile argv')
    for name in ('IOKit/storage/IOBlockStorageDevice.h','IOKit/storage/IOStorage.h','IOKit/IOLocks.h','libkern/c++/OSData.h'):
        p=out/'fixture-includes'/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text('#include "owned_ram_attach_fixture_support.h"\n',encoding='utf-8')
    env=dict(os.environ);env['PATH']=str(Path(compiler_argv[0]).parent)+os.pathsep+env.get('PATH','')
    try:
        for name,argv,timeout in (('COMPILE',compiler_argv,120),('C-FIXTURE',[str(out/'owned-ram-attach-fixture.exe')],120)):
            save(out/(name+'-STARTED.json'),dict(attempt=1,argv=argv))
            with (out/(name+'.stdout')).open('xb')as stdout,(out/(name+'.stderr')).open('xb')as stderr:process=subprocess.run(argv,cwd=ROOT,env=env,stdout=stdout,stderr=stderr,timeout=timeout,check=False)
            save(out/(name+'-COMPLETED.json'),dict(returncode=process.returncode));process.check_returncode()
            if sum((out/(name+suffix)).stat().st_size for suffix in ('.stdout','.stderr'))>1048576:raise ValueError('bounded fixture logs')
        lines=(out/'C-FIXTURE.stdout').read_text(encoding='utf-8').splitlines();done=[line[5:]for line in lines if line.startswith('PASS|')]
        if tuple(done)!=CASE_NAMES[:5]or len(lines)!=6 or json.loads(lines[-1][7:])!=dict(groups=1,variants=5,assertions=5):raise ValueError('five exact lifecycle verdicts')
        for name,predicate in ((CASE_NAMES[5],lambda:integration(factory)),(CASE_NAMES[6],lambda:origin(parcel))):
            if predicate()is not True:raise ValueError(name)
            done.append(name)
    except BaseException as error:
        path=out/'C-FIXTURE.stdout'
        if not done and path.exists()and path.stat().st_size<=1048576:done=[line[5:]for line in path.read_text(encoding='utf-8',errors='replace').splitlines()if line.startswith('PASS|')]
        error.fixture_progress=dict(groups=1,variants=7,assertions=len(done),planned_assertions=7,completed_variants=len(done),completed_assertions=len(done),case_names=done);raise
    return dict(groups=1,variants=7,assertions=7,completed_variants=7,completed_assertions=7,case_names=done,host_compile_attempts=1,host_fixture_process_attempts=1,old_tests_replayed=0,native_ABI_verified=False,native_activation=False)
