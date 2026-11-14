"""Two new custody boundaries; carry prior native/media tests without replay."""
from copy import deepcopy
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import zipfile
CASE_NAMES=('serialized_context_uses_explicit_actual_storage_receipt','capture_rejection_is_sealed_before_failure_and_never_eligible')
def reject(call):
    try:call()
    except (ValueError,KeyError):return True
    return False

def storage_join(factory):
    native=factory.native;context=dict(producer=dict(owned_ram_factory=factory.profile(),readonly_ram_nub={},user_exception_fetch={}),bindings=dict(owned_ram_factory=native.digest(factory.profile())),producer_id='1'*64,input_binding='2'*64,dependencies={factory.UNIT:dict(path=str(factory.ROOT/factory.SOURCE),source_sha256=factory.PINS[factory.SOURCE])})
    factory_row=dict(source=factory.UNIT,category='port',source_sha256=factory.PINS[factory.SOURCE],object_path='/own/factory.o',object_sha256='3'*64)
    media_row=dict(source='@storage/IOMedia.cpp',category='storage',source_sha256='38de6ac74dab48808261eed136137107a30a826e0845c9c5c6d039b53141da30',object_path='/own/IOMedia.o',object_sha256='4'*64,passed=True,producer_id=context['producer_id'],input_binding=context['input_binding'])
    compiler=dict(passed=True,object_path=media_row['object_path'],object_sha256=media_row['object_sha256'],source_sha256=media_row['source_sha256'])
    binding_proof=dict(producer_id=context['producer_id'],input_binding=context['input_binding'],media_compile=compiler);binding=native.digest(binding_proof);media_row['storage_binding']=binding
    storage=dict(binding=dict(binding=binding,proof=binding_proof),units=[media_row])
    proof=dict(profile=factory.profile(),producer_id=context['producer_id'],input_binding=context['input_binding'],row=deepcopy(factory_row),passed=True,object_provenance_verified=True,final_symbols_verified=True,native_kernel_contains_factory=True,linked_objects=1080,external_consumer_callers=0,consumer_invoked=False,consumer_retained=True,local_factory_source_consumer='note10_attach_owned_readonly_ram_nub',local_factory_source_calls=1,factory_invoked=False,provider_started=False,provider_registered=False,native_activation=False,physical_ready=False,media=dict(class_retained=True,object_provenance_verified=True,instantiated=False,started=False,row={k:media_row[k]for k in ('source','source_sha256','object_path','object_sha256','category')}))
    state={factory.KEY:proof};producer={factory.KEY:deepcopy(proof)};link=dict(object_count=1080)
    factory.verify_profile(context,[factory_row],storage,state,producer,link)
    forged_context=deepcopy(context);forged_context['storage']={'own_forged_value':True}
    factory.verify_profile(forged_context,[factory_row],storage,state,producer,link)
    missing=deepcopy(storage);missing['units']=[];duplicate=deepcopy(storage);duplicate['units'].append(deepcopy(media_row));wrong=deepcopy(storage);wrong['units'][0]['object_sha256']='f'*64
    return 'storage'not in context and all(reject(lambda receipt=receipt:factory.verify_profile(context,[factory_row],receipt,state,producer,link))for receipt in (missing,duplicate,wrong))

def failure_custody(out,producer,artifact,receive_result,finalize,package_gate):
    root=out/'own-capture';build=root/'build';build.mkdir(parents=True);(build/'compiler.log').write_text('own synthetic compiler diagnostic',encoding='utf-8');(build/'result.json').write_text(json.dumps(dict(own_synthetic_state=True)),encoding='utf-8');summary=root/'summary.json';stage=root/'stage';sealed=root/'own.n10sealed';log=root/'producer.log';log.write_text('own synthetic producer log',encoding='utf-8')
    result=dict(schema=producer.STEM+'-build-v1',source_head='a'*40,run_id=1,run_attempt=1,passed=True);summary.write_text(json.dumps(result),encoding='utf-8');events=[]
    def fail_capture(*args,**kwargs):events.append('capture-rejected');raise artifact.Rejected('own_new_capture_rejection')
    def fake_seal(argv,**kwargs):
        if argv[2]!='seal' or Path(argv[4])!=sealed:raise ValueError('only own synthetic seal call')
        events.append('seal');sealed.write_bytes(b'own synthetic seal sentinel');return SimpleNamespace(returncode=0)
    with patch.multiple(producer,OUT=build,SUMMARY=summary,STAGE=stage,SEALED=sealed),patch.object(artifact,'success_payloads',side_effect=fail_capture):
        failed=reject(lambda:producer.capture_native(result,'a'*40,log,runner=fake_seal))
    with zipfile.ZipFile(stage.with_suffix('.zip'))as bundle:
        members={name:{}for name in bundle.namelist()};record=json.loads(bundle.read('result.json'));no_kernel=not any(name.endswith('.macho')for name in bundle.namelist());diagnostics=any(name.startswith('diagnostics/')for name in bundle.namelist())
    received=receive_result(dict(authenticated=True,CI_conclusion='failure',members=members),record,artifact);finalize(received,'receive');ineligible=reject(lambda:package_gate(received));forged=deepcopy(record);forged['final_passed']=True
    return failed and events==['capture-rejected','seal']and sealed.is_file()and no_kernel and diagnostics and record['packaging_failure_code']=='own_new_capture_rejection'and record['capture_rejection_detail']=='own_new_capture_rejection'and record['producer_passed']is True and record['capture_passed']is record['final_passed']is False and received['producer_passed']is True and received['passed']is received['candidate_usable']is False and received['outcome']=='authenticated-capture-rejection-diagnostic-only' and ineligible and reject(lambda:artifact.apply_capture_verdict(dict(authenticated=True),forged))

def run(output,factory,producer,artifact,receive_result,finalize,package_gate):
    out=Path(output);done=[]
    try:
        for name,predicate in ((CASE_NAMES[0],lambda:storage_join(factory)),(CASE_NAMES[1],lambda:failure_custody(out,producer,artifact,receive_result,finalize,package_gate))):
            if predicate()is not True:raise ValueError('new capture boundary: '+name)
            done.append(name)
    except BaseException as error:error.fixture_progress=dict(groups=1,variants=2,assertions=len(done),planned_assertions=2,completed_variants=len(done),completed_assertions=len(done),case_names=done);raise
    return dict(groups=1,variants=2,assertions=2,completed_variants=2,completed_assertions=2,case_names=done,host_compile_attempts=0,host_fixture_process_attempts=0,old_tests_replayed=0,native_media_instantiations=0,native_activation=False)
