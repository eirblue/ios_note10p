"""Four new pure closure predicates, no compiler or inherited suites."""
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import json
CASES=('closed_default_selection','same_context_twelve_five_origin','official_IIG_and_five_native_commands','foreign_missing_alias_activation_denied')

def rejected(call):
    try:call()
    except (ValueError,KeyError):return True
    return False

def model(driver):
    current=dict(producer={driver.KEY:driver.profile(),'owned_ram_factory':{}},bindings={driver.KEY:__import__('current_native_kernel').digest(driver.profile())},producer_id='1'*64,input_binding='2'*64,storage=dict(proof=dict(driver_compile=dict(profile=driver.profile(),passed=True,IIG=dict(attempts=1,returncode=0,generated_impl_compiled=True),generated_sha256='3'*64))))
    rows=[]
    for name in driver.SOURCES+(driver.GENERATED,):
        rows.append(dict(source=('@storage-generated/'if name==driver.GENERATED else '@storage/')+name,source_sha256='3'*64 if name==driver.GENERATED else driver.PINS[name][1],object_path='/own/'+name+'.o',object_sha256='4'*64,category='storage',passed=True,producer_id='1'*64,input_binding='2'*64))
    native=dict(source='iokit/Kernel/IOService.cpp',source_sha256='5'*64,object_path='/own/provider.o',object_sha256='6'*64,category='native',passed=True,producer_id='1'*64,input_binding='2'*64);rows.append(native)
    defined={'__own_IOBlockStorageDriver10gMetaClassE':[rows[0]['object_path']],'__own_IOUserBlockStorageDevice10gMetaClassE':[rows[1]['object_path']],'_own_real':[native['object_path']]};refs={'_own_real':[r['object_path']for r in rows[:5]]}
    return current,rows,defined,refs

def selection(driver):
    default=dict(producer={'owned_ram_factory':{}},bindings={});closed=dict(producer={},bindings={});c,*_=model(driver)
    return driver.mode(False,False)is False and driver.storage_count(default)==7 and driver.linked_count(default)==1080 and driver.storage_count(closed)==6 and driver.storage_count(c)==12 and driver.linked_count(c)==1085 and rejected(lambda:driver.mode(True,False))and rejected(lambda:driver.mode(1,True))

def origins(driver):
    c,rows,defs,refs=model(driver);proof=driver.bind_origins(c,rows,defs,refs,{})
    lock=dict(source=driver.LOCK_SOURCE,source_sha256=driver.LOCK_SHA,object_path='/own/lock.o',object_sha256='7'*64,category='native',passed=True,producer_id=c['producer_id'],input_binding=c['input_binding']);mapping=dict(driver.LOCK_EXPORTS);alias_defs={**defs,**{target:[lock['object_path']]for target in mapping.values()}};alias_refs={**refs,**{name:[rows[0]['object_path']]for name in mapping}};exports={'config/IOKit.exports':driver.EXPORT_SHA}
    allowed=driver.bind_origins(c,rows+[lock],alias_defs,alias_refs,mapping,exports);text='\n'.join('1000 T '+n for n in (*allowed['roots'].values(),*mapping,*mapping.values()));driver.final_symbols(text,allowed)
    alias_ok=allowed['retained_lock_export_addresses_verified']is True and allowed['retained_lock_exports']==mapping and rejected(lambda:driver.bind_origins(c,rows+[dict(lock,source_sha256='f'*64)],alias_defs,alias_refs,mapping,exports))and rejected(lambda:driver.final_symbols(text.replace('1000 T _lck_mtx_lock','2000 T _lck_mtx_lock'),deepcopy(allowed)))and rejected(lambda:driver.final_symbols(text.replace('1000 T _lck_mtx_unlock','2000 T _lck_mtx_unlock'),deepcopy(allowed)))
    from phase1_iostorage_kernel_link import storage_units
    # Actual selection function: generated-source hash supplied by genuine-generator receipt.
    units=storage_units(Path('/own/storage'),True,media=True,driver=True,driver_proof=c['storage']['proof']['driver_compile'])
    old=storage_units(Path('/own/storage'),True,media=True)
    return alias_ok and len(proof['rows'])==5 and len(proof['roots'])==2 and proof['runtime_invoked']is False and len(units)==12 and len(old)==7 and len({str(obj)for _,obj,_ in units})==12 and [s.name for s,_,_ in units][2:7]==list(driver.SOURCES)+( [driver.GENERATED]) and sum(s.name==driver.GENERATED for s,_,_ in units)==1

def commands(driver,output):
    import phase1_iostorage_native_inputs as inputs
    output=Path(output);root=output/'synthetic-driver-commands'
    if not output.is_absolute()or output.resolve()!=output or output.is_symlink()or not output.is_dir()or root.exists()or root.is_symlink():raise ValueError('fresh reviewed workspace fixture path')
    root.mkdir()
    apple=root/'storage/apple-implementation';apple.mkdir(parents=True);(apple.parent/'public-sdk-objects/include').mkdir(parents=True);source=root/'xnu';sdk=root/'SDK';own={n:b'// own synthetic source '+n.encode()for n in driver.SOURCES};pins={n:(len(raw),driver.digest(raw))for n,raw in own.items()}
    for name,raw in own.items():(apple/name).write_bytes(raw)
    argv=['/own/clang','-DKERNEL','-I',str(root/'native-config'),'-c',str(apple/'IOStorage.cpp'),'-o',str(apple/'IOStorage.o')];calls=[]
    def run(command,**kwargs):
        calls.append(command)
        if '--def'in command:
            Path(command[command.index('--header')+1]).write_bytes(b'// own generated header');Path(command[command.index('--impl')+1]).write_bytes(b'// own official-generator stand-in output')
        else:Path(command[-1]).write_bytes(b'own object fixture')
        return SimpleNamespace(returncode=0,stdout=b'',stderr=b'')
    result=dict(compile_attempts=2,target_object_compile_attempts=2,compiled_arm64_objects=2)
    with patch.object(driver,'PINS',pins),patch.object(inputs,'command',return_value='/own/iig'):
        ok=driver.compile_members(result,apple,argv,source,sdk,lambda p:None,runner=run)
    proof=result['driver_compile'];expected=driver.iig_argv('/own/iig',apple,source,sdk)
    return ok is True and calls[0]==expected and len(calls)==6 and all('-DKERNEL'in a and '-I'in a for a in calls[1:])and result['target_object_compile_attempts']==7 and result['compiled_arm64_objects']==7 and proof['IIG']['generated_impl_compiled']is True and len(proof['units'])==5 and sum(Path(x['source']).name==driver.GENERATED for x in proof['units'])==1 and all(str(apple.parent/'public-sdk-objects/include')in a for a in calls[1:])

def denials(driver):
    c,rows,defs,refs=model(driver);missing=dict(defs);missing.pop('_own_real');foreign=deepcopy(rows);foreign[0]['source_sha256']='f'*64;stub=deepcopy(rows);stub[-1]['category']='port';bad=deepcopy(c);bad['producer'][driver.KEY]['runtime_invoked']=True
    return all((rejected(lambda:driver.bind_origins(c,rows,missing,refs,{})),rejected(lambda:driver.bind_origins(c,foreign,defs,refs,{})),rejected(lambda:driver.bind_origins(c,stub,defs,refs,{})),rejected(lambda:driver.bind_origins(c,rows,defs,refs,{'_own_real':'_own_stub'})),rejected(lambda:driver.enabled(bad))))

def run(output,driver):
    done=[]
    try:
        for name,check in zip(CASES,(selection,origins,lambda driver:commands(driver,output),denials)):
            if check(driver)is not True:raise ValueError('new driver boundary: '+name)
            done.append(name)
    except BaseException as error:error.fixture_progress=dict(groups=1,variants=4,assertions=len(done),planned_assertions=4,completed_variants=len(done),completed_assertions=len(done),case_names=done);raise
    return dict(groups=1,variants=4,assertions=4,completed_variants=4,completed_assertions=4,case_names=done,host_compile_attempts=0,host_fixture_process_attempts=0,old_tests_replayed=0)


def run_remaining(output,driver):
    """Only two previously unexecuted predicates; no selection/origins/run replay."""
    done=[]
    try:
        for name,check in ((CASES[2],lambda:commands(driver,output)),(CASES[3],lambda:denials(driver))):
            if check()is not True:raise ValueError('remaining driver boundary: '+name)
            done.append(name)
    except BaseException as error:error.fixture_progress=dict(groups=1,variants=2,assertions=len(done),planned_assertions=2,completed_variants=len(done),completed_assertions=len(done),case_names=done);raise
    return dict(groups=1,variants=2,assertions=2,completed_variants=2,completed_assertions=2,case_names=done,host_compile_attempts=0,host_fixture_process_attempts=0,old_tests_replayed=0)
