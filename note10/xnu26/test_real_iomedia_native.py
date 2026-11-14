"""Three new source-selection/command/provenance verdicts; pure synthetic inputs."""
from copy import deepcopy
import hashlib
import io
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
CASE_NAMES=('closed_real_media_member_and_unit_selection','new_media_uses_actual_native_iokit_command','same_job_real_media_provider_retention')
def reject(call):
    try:call()
    except (ValueError,KeyError):return True
    return False

def selection(out,complete,storage):
    commit='own-synthetic-commit';writes=[]
    class Archive:
        def __init__(self,duplicate=False,foreign=False):
            self.members=[SimpleNamespace(name='IOStorageFamily-'+commit+'/'+name,size=size,isfile=lambda:True)for name,size in ((complete.MEMBER,complete.MEMBER_BYTES),('IOStorage.h',28158),(complete.MEDIA_MEMBER,complete.MEDIA_BYTES))]
            if duplicate:self.members.append(self.members[-1])
            if foreign:self.members[-1].name='foreign/'+self.members[-1].name
        def getmembers(self):return self.members
        def getmember(self,name):return next(x for x in self.members if x.name==name)
        def extractfile(self,member):return io.BytesIO(b'own synthetic source')
    # Pinned-byte writing is an unchanged boundary; exercise only the new selection.
    with patch.object(complete,'write_pinned',side_effect=lambda raw,destination,digest:writes.append((destination,digest))):
        complete.stage_apple(Archive(),out/'apple',commit,'1'*64,media=True)
        duplicate=reject(lambda:complete.stage_apple(Archive(duplicate=True),out/'duplicate',commit,'1'*64,media=True))
        foreign=reject(lambda:complete.stage_apple(Archive(foreign=True),out/'foreign',commit,'1'*64,media=True))
    selected=storage.storage_units(out,True,media=True);default=storage.storage_units(out,True,media=False)
    return (out/'apple/IOMedia.cpp',complete.MEDIA_SHA256)in writes and duplicate and foreign and len(selected)==7 and len(default)==6 and sum(x[0].name=='IOMedia.cpp'for x in selected)==1 and not any(x[0].name=='IOMedia.cpp'for x in default)

def command_context(out,complete):
    apple=out/'synthetic-media-command';apple.mkdir();source=apple/complete.MEDIA_MEMBER;source.write_bytes(b'/'*complete.MEDIA_BYTES);calls=[]
    header_root=out/'public-sdk-objects/include';headers=header_root/'IOKit/storage';headers.mkdir(parents=True)
    header_pins={}
    for name in complete.MEDIA_HEADER_SHA256:
        path=headers/name;path.write_text('/* own synthetic staged header '+name+' */',encoding='utf-8');header_pins[name]=hashlib.sha256(path.read_bytes()).hexdigest()
    # The prior authenticated source input is synthetic here; no original source replay.
    def digest(path):return complete.MEDIA_SHA256 if path.name==complete.MEDIA_MEMBER else hashlib.sha256(path.read_bytes()).hexdigest()
    argv=['/own/clang',*complete.PRE_CONFIG_FLAGS,'-include','/own/generated/meta_features.h','-DMACH=1','-isysroot','/own/SDK',*complete.POST_CONFIG_FLAGS,'-I','/own/XNU/iokit','-c',str(apple/complete.MEMBER),'-o',str(apple/'IOStorage.o')]
    def run(actual,**kwargs):calls.append(actual);Path(actual[-1]).write_bytes(b'own synthetic media object');return SimpleNamespace(returncode=0,stdout=b'',stderr=b'')
    result=dict(compile_attempts=1,target_object_compile_attempts=1,compiled_arm64_objects=1)
    with patch.object(complete,'MEDIA_HEADER_SHA256',header_pins),patch.object(complete,'sha',side_effect=digest):ok=complete.compile_media(result,apple,argv,lambda path:None,runner=run)
    proof=result['media_compile'];failed=out/'synthetic-media-failure';failed.mkdir();bad_source=failed/complete.MEDIA_MEMBER;bad_source.write_bytes(b'/'*complete.MEDIA_BYTES)
    failed_argv=[*argv[:-4],'-c',str(failed/complete.MEMBER),'-o',str(failed/'IOStorage.o')]
    with patch.object(complete,'MEDIA_HEADER_SHA256',header_pins),patch.object(complete,'sha',side_effect=digest):
        bad=complete.compile_media(dict(compile_attempts=1,target_object_compile_attempts=1,compiled_arm64_objects=1),failed,failed_argv,lambda p:None,runner=lambda *a,**k:SimpleNamespace(returncode=1,stdout=b'own failure',stderr=b'own compiler error'))
    return ok is True and calls==[[argv[0],'-I',str(header_root),*argv[1:-4],'-c',str(source),'-o',str(apple/'IOMedia.o')]]and proof['header_root']==str(header_root)and proof['staged_header_sha256']==header_pins and proof['passed']is True and result['compile_attempts']==2 and result['media_target_compile_attempts']==1 and proof['argv']==calls[0]and bad is False and (failed/'IOMedia-COMPILE-STARTED.json').is_file()and json.loads((failed/'IOMedia-compile.json').read_text())['passed']is False and (failed/'IOMedia.compiler.log').read_bytes()==b'own failureown compiler error'

def provenance(out,factory,complete):
    native=factory.native;producer=dict(owned_ram_factory=factory.profile(),readonly_ram_nub={},user_exception_fetch={});current=dict(producer=producer,bindings=dict(owned_ram_factory=native.digest(factory.profile())),producer_id='1'*64,input_binding='2'*64,dependencies={factory.UNIT:dict(path=str(factory.ROOT/factory.SOURCE),source_sha256=factory.PINS[factory.SOURCE])})
    row=dict(source='@storage/IOMedia.cpp',source_sha256=complete.MEDIA_SHA256,category='storage',passed=True,object_path='/own/IOMedia.o',object_sha256='3'*64,producer_id=current['producer_id'],input_binding=current['input_binding'],storage_binding='4'*64)
    dependency=dict(source='iokit/Kernel/own-provider.cpp',source_sha256='5'*64,category='native',passed=True,object_path='/own/provider.o',object_sha256='6'*64,producer_id=current['producer_id'],input_binding=current['input_binding'])
    current['storage']=dict(binding='4'*64,proof=dict(media_compile=dict(passed=True,target_compile_attempts=1,source='IOMedia.cpp',source_bytes=complete.MEDIA_BYTES,source_sha256=complete.MEDIA_SHA256,object_path=row['object_path'],object_sha256=row['object_sha256'])))
    symbol='__own_IOMedia10gMetaClassE';definitions={symbol:[row['object_path']],'_own_provider':[dependency['object_path']]};refs={'_own_provider':[row['object_path']]};media=factory.bind_media_origins(current,[row,dependency],definitions,refs,{})
    proof=dict(profile=factory.profile(),producer_id=current['producer_id'],input_binding=current['input_binding'],object_provenance_verified=True,external_consumer_callers=0,consumer_invoked=False,symbol='_own_factory',consumer_symbol='_own_attach',media=media);current['owned_ram_factory_link']=proof
    roots=factory.link_root(current)
    with patch.object(native,'expected_objects',return_value=1080):
        text='0 T _own_factory\n1 T _own_attach\n2 D '+symbol;factory.final_symbols(text,dict(link_succeeded=True,object_count=1080),current,proof)
        stale=reject(lambda:factory.final_symbols(text,dict(link_succeeded=True,object_count=1079),current,proof))
        missing=reject(lambda:factory.final_symbols('0 T _own_factory\n1 T _own_attach',dict(link_succeeded=True,object_count=1080),current,proof))
    duplicate=deepcopy(definitions);duplicate['__other_IOMedia10gMetaClassE']=[row['object_path']]
    foreign=dict(dependency,category='port')
    return roots[-1]=='-Wl,-u,'+symbol and media['class_retained']is True and media['instantiated']is media['started']is False and stale and missing and reject(lambda:factory.bind_media_origins(current,[row,dependency],duplicate,refs,{}))and reject(lambda:factory.bind_media_origins(current,[row,foreign],definitions,refs,{}))and reject(lambda:factory.bind_media_origins(current,[row,dependency],definitions,refs,{'_own_provider':'_own_substitute'}))

def run(output,factory,complete,storage):
    out=Path(output);done=[]
    try:
        for name,predicate in ((CASE_NAMES[0],lambda:selection(out,complete,storage)),(CASE_NAMES[1],lambda:command_context(out,complete)),(CASE_NAMES[2],lambda:provenance(out,factory,complete))):
            if predicate()is not True:raise ValueError('new IOMedia predicate: '+name)
            done.append(name)
    except BaseException as error:error.fixture_progress=dict(groups=1,variants=3,assertions=len(done),planned_assertions=3,completed_variants=len(done),completed_assertions=len(done),case_names=done);raise
    return dict(groups=1,variants=3,assertions=3,completed_variants=3,completed_assertions=3,case_names=done,host_compile_attempts=0,host_fixture_process_attempts=0,old_tests_replayed=0,native_media_instantiations=0,native_activation=False)
