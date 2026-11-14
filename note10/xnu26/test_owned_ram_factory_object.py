"""Four new fixed-profile/recipe/wire predicates; fake compiler only."""
from copy import deepcopy
import json
import shlex
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch


def run(output,native,recipe,codec,producer_source,dependency_reader):
    out=Path(output);root=Path(__file__).resolve().parents[2];private=out/'synthetic-native';source=out/'synthetic-source';apple=out/'original-headers';objects=private/'objects/DEVELOPMENT'
    objects.mkdir(parents=True);source.mkdir();apple.mkdir();(apple/'IOStorage.h').write_text('/* synthetic declaration only */\n')
    config=private/'configured/DEVELOPMENT/iokit';config.mkdir(parents=True);(config/'Makefile').write_text('export CONFIG_DEFINES = -DMACH=1\n');(config/'meta_features.h').write_text('/* synthetic features */\n')
    version=private/'native-link/include/libkern/version.h';version.parent.mkdir(parents=True);version.write_text('/* synthetic version */\n')
    for name in ('configure-result.json','exports-result.json','native-mig-result.json','native-extra-result.json','native-link/generate-result.json'):
        path=private/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps({'version_header_sha256':native.file_sha(version)}if name.endswith('generate-result.json')else{}))
    producer=dict(source_commit='1'*40,public_source_commit='ac9718fb1af618d5ce8678d0dc6e8a58f252216f',configuration='DEVELOPMENT_ARM64_EXYNOS9825',compiler='/synthetic/clang',sdk=str(out/'genuine-SDK-path-model'),source_root=str(source),generated_root=str(private),objects_root=str(objects),apple_headers_root=str(apple),ci_context={})
    bindings={name:native.file_sha(private/name)for name in ('configure-result.json','exports-result.json','native-mig-result.json','native-extra-result.json','native-link/generate-result.json')};bindings['port_source_sha256']={name:native.file_sha(root/'note10/xnu26'/name)for name in ('note10_owned_ram_nub.cpp','note10_owned_ram_nub.h','note10_readonly_ram_block_device.h')};bindings['apple_header_sha256']={'IOStorage.h':native.file_sha(apple/'IOStorage.h')};unit=dict(source='@port/note10_owned_ram_nub.cpp',component='iokit',kind='C++',path=str(root/'note10/xnu26/note10_owned_ram_nub.cpp'),source_sha256=bindings['port_source_sha256']['note10_owned_ram_nub.cpp'],object_path=str(objects/'port_note10_owned_ram_nub.cpp.o'));profile=dict(kind='note10-v260-owned-ram-factory-object-v1',producer=producer,producer_id=native.digest(producer),bindings=bindings,input_binding=native.digest(bindings),unit=unit);completed=[]
    def valid():
        selected=native.admit_owned_ram_factory_object(profile);calls=[]
        def fake(argv,**kwargs):
            calls.append(argv);Path(argv[argv.index('-o')+1]).write_bytes(b'synthetic-object-only');return SimpleNamespace(returncode=0,stdout=b'',stderr=b'')
        context=dict(deployment_target='arm64-apple-ios26.5.2',source=source,private=private,compiler=producer['compiler'],sdk=producer['sdk'],owners=selected['owners'],input_files=selected['input_files'],current=None,mode=('FIXED_FACTORY','C++','owned-ram-factory'),exported=private/'exports',support_export=private/'support',borrowed_mig=private/'FOREIGN-borrowed',mig=private/'FOREIGN-MIG',native_mig=private/'native-mig',extra_report=private/'native-extra-result.json',output=objects,audit=True,private_flags={'iokit':['-DDRIVER_PRIVATE','-DIOKIT_KERNEL_PRIVATE']},factory_profile=profile)
        row=recipe.compile_one(unit['source'],context,runner=fake);argv=calls[0]
        sdk_real=out/'SDK-real';sdk_real.mkdir();header=sdk_real/'actual.h';header.write_text('/* synthetic SDK header */');alias=out/'SDK-versioned-alias';dep_profile=deepcopy(profile);dep_profile['producer']['sdk']=str(alias);dep_profile['producer']['compiler']=str(out/'toolchain/usr/bin/clang');original_resolve=Path.resolve
        def resolve_alias(path,*args,**kwargs):return original_resolve(sdk_real,*args,**kwargs)if path==alias else original_resolve(path,*args,**kwargs)
        with patch.object(Path,'resolve',resolve_alias):deps=dependency_reader(unit['object_path']+': '+shlex.quote(unit['path'])+' '+shlex.quote(str(header))+'\n',dep_profile)
        dependency_ok=any(item['path']==str(header)and item['origin']=='SDK'for item in deps)
        return dependency_ok and selected['units']==[unit['source']]and selected['native_headers_only']is True and len(calls)==1 and row['passed']is True and row['category']=='port'and '-std=gnu++2b'in argv and '-MD'in argv and argv[argv.index('-MF')+1]==str(Path(unit['object_path']).with_suffix('.d'))and not any('FOREIGN'in value for value in argv)and '-DIOKIT_KERNEL_PRIVATE'in argv and str(apple)in argv
    def reject(kind):
        changed=deepcopy(profile)
        if kind=='old':changed['kind']='v84-current-native'
        else:changed['unit']['path']=str(out/'foreign.cpp')
        try:native.admit_owned_ram_factory_object(changed)
        except ValueError:return True
        return False
    def wire():
        context=dict(schema='note10-v260-owned-ram-factory-sdk-public-input-v1',source_head='1'*40,source_sha256={},fixture=dict(passed=True,groups=1,variants=4,assertions=4,result_sha256='2'*64),predecessor259=dict(passed=True,groups=1,variants=8,assertions=8,result_sha256='3'*64));encoded=codec.encode_wire(producer_source,context);return codec.boundary_decode(producer_source,encoded)==context
    # Negative admission predicates run before the positive reserves its synthetic compile marker.
    cases=(('old_full_profile_rejected',lambda:reject('old')),('foreign_factory_path_rejected',lambda:reject('foreign')),('fixed_factory_native_recipe_fake_compile',valid),('actual_new_CLI_base64_roundtrip',wire))
    try:
        for name,predicate in cases:
            if predicate()is not True:raise ValueError('new factory-object predicate failed: '+name)
            completed.append(name)
    except BaseException as error:
        error.fixture_progress=dict(groups=1,variants=4,assertions=4,completed_variants=len(completed),completed_assertions=len(completed),case_names=completed);raise
    return dict(groups=1,variants=4,assertions=4,completed_variants=4,completed_assertions=4,case_names=completed,target_compiler_processes=0,host259_replays=0)
