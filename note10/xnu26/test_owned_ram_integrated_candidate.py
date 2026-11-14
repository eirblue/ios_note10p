"""Seven new integration predicates; no compiler/device process or old tests."""
from copy import deepcopy
import io
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch


def run(output,factory,native,recipe,retained,parcel,codec,producer_source):
    out=Path(output);done=[]
    def reject(call):
        try:call()
        except(ValueError,KeyError):return True
        return False
    def current():
        producer=dict(source_commit='1'*40,readonly_ram_nub={},user_exception_fetch={},owned_ram_factory=factory.profile(),toolchain=dict(compiler='/synthetic/clang',sdk='/synthetic/SDK'),ci_context={})
        bindings=dict(owned_ram_factory=native.digest(factory.profile()));return dict(kind='v84-current-native',producer=producer,bindings=bindings,producer_id=native.digest(producer),input_binding=native.digest(bindings),dependencies={factory.UNIT:dict(path=str(factory.ROOT/factory.SOURCE),source_sha256=factory.PINS[factory.SOURCE])})
    def modes():
        return factory.mode(False,False,False,False,False)is False and factory.mode(True,True,True,True,True)is True and all(reject(lambda flags=flags:factory.mode(*flags))for flags in ((True,False,True,True,True),(True,True,False,True,True),(True,True,True,False,True),(True,True,True,True,False)))
    def binding():
        good=current();bad=deepcopy(good);bad['dependencies'][factory.UNIT]['source_sha256']='f'*64;other=deepcopy(good);other['bindings']['owned_ram_factory']='f'*64;foreign=deepcopy(good);foreign['dependencies'][factory.UNIT]['path']=str(out/'foreign.cpp')
        return factory.enabled(good)is True and reject(lambda:factory.enabled(bad))and reject(lambda:factory.enabled(other))and reject(lambda:factory.enabled(foreign))and reject(lambda:factory.bind_origins(good,[dict(source=factory.UNIT),dict(source=factory.UNIT)],{},{},{},{}))
    def bridge():
        private=out/'synthetic-native';source=out/'synthetic-source';apple=out/'synthetic-apple';objects=private/'objects/DEVELOPMENT'
        objects.mkdir(parents=True);source.mkdir();apple.mkdir();(apple/'IOStorage.h').write_text('/* own synthetic declaration */\n')
        conf=private/'configured/DEVELOPMENT/iokit';conf.mkdir(parents=True);(conf/'Makefile').write_text('export CONFIG_DEFINES = -DMACH=1\n');(conf/'meta_features.h').write_text('/* own synthetic features */\n')
        header=private/'native-link/include/libkern/version.h';header.parent.mkdir(parents=True);header.write_text('/* own synthetic version */\n')
        for name in ('configure-result.json','exports-result.json','native-mig-result.json','native-extra-result.json','native-link/generate-result.json'):
            path=private/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(dict(version_header_sha256=native.file_sha(header))if name.endswith('generate-result.json')else{}))
        cur=current();fixed=dict(kind='note10-v260-owned-ram-factory-object-v1',producer=dict(source_commit='1'*40,public_source_commit='ac9718fb1af618d5ce8678d0dc6e8a58f252216f',configuration='DEVELOPMENT_ARM64_EXYNOS9825',compiler='/synthetic/clang',sdk='/synthetic/SDK',source_root=str(source),generated_root=str(private),objects_root=str(objects),apple_headers_root=str(apple),ci_context={}),unit=dict(source=factory.UNIT,component='iokit',kind='C++',path=str(factory.ROOT/factory.SOURCE),source_sha256=factory.PINS[factory.SOURCE],object_path=str(objects/'port_note10_owned_ram_nub.cpp.o')))
        # Replace only the generation root in this synthetic profile; actual admission and command body run.
        fixed['producer'].update(generated_root=str(private),objects_root=str(objects));fixed['producer_id']=native.digest(fixed['producer']);fixed['unit']['object_path']=str(objects/'port_note10_owned_ram_nub.cpp.o')
        fixed['bindings']={name:native.file_sha(private/name)for name in ('configure-result.json','exports-result.json','native-mig-result.json','native-extra-result.json','native-link/generate-result.json')};fixed['bindings'].update(port_source_sha256={Path(n).name:h for n,h in factory.PINS.items()},apple_header_sha256={'IOStorage.h':native.file_sha(apple/'IOStorage.h')});fixed['input_binding']=native.digest(fixed['bindings'])
        calls=[]
        def fake(argv,**kwargs):calls.append(argv);Path(argv[argv.index('-o')+1]).write_bytes(b'own synthetic object');return SimpleNamespace(returncode=0,stdout=b'',stderr=b'')
        def actual_command(*,owned_ram_factory_profile):
            selected=native.admit_owned_ram_factory_object(owned_ram_factory_profile)
            context=dict(deployment_target='arm64-apple-ios26.5.2',source=source,private=private,compiler='/synthetic/clang',sdk='/synthetic/SDK',owners=selected['owners'],input_files=selected['input_files'],current=None,mode=('FIXED_FACTORY','C++','owned-ram-factory'),exported=private/'exports',support_export=private/'support',borrowed_mig=private/'FOREIGN',mig=private/'FOREIGN',native_mig=private/'native-mig',extra_report=private/'native-extra-result.json',output=objects,audit=True,private_flags={'iokit':['-DIOKIT_KERNEL_PRIVATE']},factory_profile=owned_ram_factory_profile)
            return dict(units=[recipe.compile_one(factory.UNIT,context,runner=fake)])
        with patch.object(retained,'profile_for',return_value=fixed),patch.object(retained.compiler_recipe,'main',side_effect=actual_command):report=factory.compile_provider(cur,source,private,apple)
        row=report['units'][0]
        return len(calls)==1 and row['category']=='port'and row['producer_id']==cur['producer_id']and row['input_binding']==cur['input_binding']and row['factory_profile_producer_id']==fixed['producer_id']and row['factory_profile_input_binding']==fixed['input_binding']and '-std=gnu++2b'in calls[0]and str(apple)in calls[0]and not any('FOREIGN'in x for x in calls[0])
    def origins():
        cur=current();row=dict(source=factory.UNIT,category='port',source_sha256=factory.PINS[factory.SOURCE],object_path='/synthetic/factory.o',object_sha256='2'*64,passed=True,producer_id=cur['producer_id'],input_binding=cur['input_binding']);provider=dict(source='iokit/synthetic.cpp',category='native',source_sha256='3'*64,object_path='/synthetic/provider.o',object_sha256='4'*64,passed=True);symbol='_own_note10_create_owned_readonly_ram_nub';defined={symbol:[row['object_path']],'_own_provider':[provider['object_path']]};refs={'_own_provider':[row['object_path']]};proof={}
        factory.bind_origins(cur,[row,provider],defined,refs,{},proof);root=factory.link_root(cur)
        missing=deepcopy(defined);del missing[symbol];called=deepcopy(refs);called[symbol]=[provider['object_path']]
        # An incomplete/wrong-count final link must never promote retained factory presence.
        bad_link=dict(link_succeeded=True,object_count=1078)
        with patch.object(native,'expected_objects',return_value=1079):
            factory.final_symbols('0 T '+symbol,dict(link_succeeded=True,object_count=1079),cur,proof)
            wrong_count=reject(lambda:factory.final_symbols('0 T '+symbol,bad_link,cur,proof))
        return proof['native_kernel_contains_factory']is True and wrong_count and root==['-Wl,-u,'+symbol]and proof['compiled_callers']==0 and reject(lambda:factory.bind_origins(cur,[row,provider],missing,refs,{},{}))and reject(lambda:factory.bind_origins(cur,[row,provider],defined,called,{},{}))and reject(lambda:factory.bind_origins(cur,[row,provider],defined,refs,{symbol:'_own_provider'},{}))
    def limits():
        span=16384;raw=(span+16384+496+511)&~511;good=parcel.reader_fit(span,18,raw)
        return good['compiled_reader_fit']is True and all(reject(lambda values=values:parcel.reader_fit(*values))for values in ((parcel.KERNEL_CAP+16384,18,raw),(span,parcel.SOURCE_CAP-95,raw),(span,18,raw+512),(span+1,18,raw)))
    def fresh():
        identity=parcel.candidate_identity(dict(schema=parcel.STEM+'-source-parcel-v1',source_head='1'*40,run_id=1,kernel_sha256='2'*64,descriptor_sha256='3'*64),dict(producer_revision='v241',source_head='4'*40,build_evidence_id='5'*32),'6'*32)
        context=dict(own_synthetic=True);encoded=codec.encode_wire(producer_source,context)
        image=bytearray(parcel.SOURCE_CAP+65536);marker=16384;source_offset=32768;meta=64;image[marker:marker+33]=b'N10_CYCLE_SLOT_UNSET_0123456789A'+b'\0'
        descriptor=bytearray(256);descriptor[:8]=b'N209PAY1';__import__('struct').pack_into('<IIQQ',descriptor,8,1,256,0,16384);member=b'\x1f\x8b\x08\x00'+bytes(14);fit=parcel.reader_fit(16384,len(member),(16384+16384+496+511)&~511)
        build=dict(slot_offset=meta,slot_bytes=4096,cycle_offset=marker,source_holder_offset=source_offset,source_holder_bytes=parcel.SOURCE_CAP,build_evidence_id='5'*32)
        patched,binding=parcel.insert(bytes(image),build,bytes(descriptor),member,parcel.sha(member),'6'*32,fit,lambda d,b,c:(b'own-synthetic-metadata',bytes(128)))
        bad_image=bytearray(image);bad_image[marker]=0
        marker_rejected=reject(lambda:parcel.insert(bytes(bad_image),build,bytes(descriptor),member,parcel.sha(member),'6'*32,fit,lambda d,b,c:(b'own-synthetic-metadata',bytes(128))))
        insertion_ok=marker_rejected and patched[marker:marker+32]==b'6'*32 and len(binding)==128 and patched[source_offset:source_offset+8]==b'N226SRC1'and patched[source_offset+96:source_offset+96+len(member)]==member
        journal=dict(identity,build_evidence_id=identity['candidate_id'][:32]);journal_ok=parcel.journal_id(journal)==identity['candidate_id'][:32]and reject(lambda:parcel.journal_id(dict(journal,build_evidence_id=identity['carrier_build_evidence_id'])))
        # A retained carrier is identified honestly; its compiled build ID is never substituted.
        return insertion_ok and journal_ok and identity['version']=='v261'and identity['carrier_build_evidence_id']=='5'*32 and identity['candidate_id'][:32]!='5'*32 and identity['carrier_runtime_recompiled']is False and codec.boundary_decode(producer_source,encoded)==context and reject(lambda:parcel.candidate_identity(dict(schema='old',source_head='1'*40),{},'6'*32))
    def observed():
        identity=dict(carrier_build_evidence_id='1'*32,cycle='2'*32,descriptor_sha256='3'*64,materialized_sha256='4'*64);metadata=dict(kernel_materialized_bytes=16384,descriptor_sha256='3'*64,kernel_materialized_sha256='4'*64);row=dict(build='1'*32,cycle='2'*32,copied_kernel=16384,copied_adapter=16384,native_source=1,destination_hash_verified=1,XNU=0)
        result=parcel.observation(row,identity,metadata);stale=dict(row,cycle='3'*32);old=dict(row,copied_kernel=19169280)
        return parcel.battery(b'43\r\n')==43 and reject(lambda:parcel.battery(b'9\r\n'))and reject(lambda:parcel.battery(b'43garbage'))and result['ingested_new_native_data']is True and result['factory_invoked']is False and reject(lambda:parcel.observation(stale,identity,metadata))and reject(lambda:parcel.observation(old,identity,metadata))and reject(lambda:parcel.observation(row,identity,dict(metadata,descriptor_sha256='f'*64)))
    cases=(('closed_opt_in_mode',modes),('same_job_fixed_dependency_binding',binding),('new_current_factory_recipe_bridge',bridge),('unique_retained_uncalled_factory_origin',origins),('actual_compiled_carrier_size_limits',limits),('new_candidate_retained_carrier_identity_and_wire',fresh),('dynamic_same_cycle_receipt_and_raw_battery',observed))
    try:
        for name,predicate in cases:
            if predicate()is not True:raise ValueError('new integrated predicate: '+name)
            done.append(name)
    except BaseException as error:error.fixture_progress=dict(groups=1,variants=7,assertions=len(done),planned_assertions=7,completed_variants=len(done),completed_assertions=len(done),case_names=done);raise
    return dict(groups=1,variants=7,assertions=7,completed_variants=7,completed_assertions=7,case_names=done,target_compiler_processes=0,old_tests_replayed=0)
