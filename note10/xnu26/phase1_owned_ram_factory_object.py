"""One genuine SDK factory-object capture; no full kernel, target execution or link."""
import argparse
import ast
import base64
from contextlib import redirect_stdout,redirect_stderr
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import struct
import subprocess
import sys
import zipfile
import current_native_kernel as native
import compile_native_components as compiler_recipe
import phase1_iostorage_native_inputs as inputs
import phase1_iostorage_declaration as storage

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
SCHEMA='note10-v260-owned-ram-factory-sdk'
WORKFLOW='.github/workflows/note10-v260-owned-ram-factory-sdk.yml'
JOB='v260-owned-ram-factory-sdk'
ARTIFACT='note10-v260-owned-ram-factory-sdk-sealed-evidence'
OUT=ROOT/'note10/private/v260-owned-ram-factory-sdk-once'
MEMBERS={'result.json','members.json','sources.json','generation.json','profile.json','compile.json','dependencies.json','factory.o','factory.d','compiler.log','preparation.log','preparation-files.json','preparation-diagnostics.log','COMPILE-STARTED.json'}
SUCCESS_MEMBERS=MEMBERS-{'compiler.log'}
FACTORY_NAMES=('note10_owned_ram_nub.cpp','note10_owned_ram_nub.h','note10_readonly_ram_block_device.h')


def require(ok,message):
    if not ok:raise ValueError(message)


def sha(raw):return hashlib.sha256(raw).hexdigest()


def bounded(path,limit=8388608):
    p=Path(path);require(p.is_file()and not p.is_symlink()and 0<p.stat().st_size<=limit,'bounded ordinary evidence file');return p.read_bytes()


def save(path,value):
    with Path(path).open('x',encoding='utf-8')as stream:json.dump(value,stream,indent=2,sort_keys=True);stream.write('\n')


def public_files():
    names={'note10/xnu26/'+n for n in ('phase1_owned_ram_factory_object.py','test_owned_ram_factory_object.py','compile_native_components.py','current_native_kernel.py','phase1_iostorage_native_inputs.py','phase1_iostorage_declaration.py','build_windows_config.py',*FACTORY_NAMES,'exynos_early_clock.c','exynos_leaf_mapper.h','exynos_leaf_mapper.S','exynos_checked_ptpage.c')}
    names.update('note10/'+name for name in inputs.RECIPE_SHA256);names.update((WORKFLOW,'note10/target.json','note10/device_test/sealed_affinity_artifact.cjs','note10/xnu26/patches/series'));names.update('note10/xnu26/patches/'+name for name in (HERE/'patches/series').read_text().splitlines())
    pending=list(names)
    while pending:
        name=pending.pop()
        if not name.endswith('.py'):continue
        for node in ast.parse(bounded(ROOT/name).decode()).body:
            modules=[node.module]if isinstance(node,ast.ImportFrom)and node.module else [x.name for x in node.names]if isinstance(node,ast.Import)else []
            for module in modules:
                if '.'in module:continue
                for directory in ('note10/xnu26','note10'):
                    relative=directory+'/'+module+'.py'
                    if (ROOT/relative).is_file()and relative not in names:names.add(relative);pending.append(relative);break
    return tuple(sorted(names))


def sources():return {name:sha(bounded(ROOT/name))for name in public_files()}


def public_context(head,fixture,fixture_sha,predecessor,predecessor_sha):
    require(re.fullmatch('[0-9a-f]{40}',head)and re.fullmatch('[0-9a-f]{64}',fixture_sha)and re.fullmatch('[0-9a-f]{64}',predecessor_sha),'new source and actual PASS identifiers')
    def summary(row,count,digest):
        result={k:row[k]for k in ('passed','groups','variants','assertions')};require(result['passed']is True and (result['groups'],result['variants'],result['assertions'])==(1,count,count),'exact retained/new logical fixture counts');return dict(**result,result_sha256=digest)
    return dict(schema=SCHEMA+'-public-input-v1',source_head=head,source_sha256=sources(),fixture=summary(fixture,4,fixture_sha),predecessor259=summary(predecessor,8,predecessor_sha))


def profile_for(compiler,sdk,source,apple,head,ci):
    private=ROOT/'note10/private/windows-xnu';producer=dict(source_commit=head,public_source_commit=inputs.XNU_COMMIT,configuration='DEVELOPMENT_ARM64_EXYNOS9825',compiler=compiler,sdk=sdk,source_root=str(source),generated_root=str(private),objects_root=str(private/'objects/DEVELOPMENT'),apple_headers_root=str(apple),ci_context=ci)
    bindings={name:native.file_sha(private/name)for name in ('configure-result.json','exports-result.json','native-mig-result.json','native-extra-result.json','native-link/generate-result.json')};bindings['port_source_sha256']={name:native.file_sha(HERE/name)for name in FACTORY_NAMES};bindings['apple_header_sha256']={p.relative_to(apple).as_posix():native.file_sha(p)for p in apple.rglob('*.h')}
    unit=dict(source='@port/note10_owned_ram_nub.cpp',component='iokit',kind='C++',path=str(HERE/'note10_owned_ram_nub.cpp'),source_sha256=bindings['port_source_sha256']['note10_owned_ram_nub.cpp'],object_path=str(private/'objects/DEVELOPMENT/port_note10_owned_ram_nub.cpp.o'))
    return dict(kind='note10-v260-owned-ram-factory-object-v1',producer=producer,producer_id=native.digest(producer),bindings=bindings,input_binding=native.digest(bindings),unit=unit)


def dependency_rows(text,profile):
    target,separator,rest=text.replace('\\\n',' ').partition(': ');require(separator and Path(target.strip())==Path(profile['unit']['object_path']),'actual depfile object target');names=shlex.split(rest);require(0<len(names)<=8192,'bounded actual dependency set');rows=[];seen=set();producer=profile['producer'];roots=[('SDK',Path(producer['sdk']).resolve()),('toolchain',Path(producer['compiler']).parent.parent.resolve()),('project',ROOT.resolve())]
    for name in names:
        path=Path(name);path=(ROOT/path).resolve()if not path.is_absolute()else path.resolve();require(path not in seen and 'fixture-includes'not in path.parts and not path.name.endswith('_fixture_support.h'),'unique genuine dependency, no fixture header');seen.add(path)
        kind=next((kind for kind,root in roots if path.is_relative_to(root)),None);require(kind is not None,'dependency outside actual project/SDK/toolchain roots');raw=bounded(path,8388608);rows.append(dict(path=str(path),origin=kind,bytes=len(raw),sha256=sha(raw)))
    require(any(row['path']==profile['unit']['path']for row in rows),'factory must appear in actual compiler dependencies');return rows


def preserve_preparation():
    native_root=ROOT/'note10/private/windows-xnu';paths=list((OUT/'native-provisioning').glob('*.log'))+list((OUT/'native-provisioning').glob('*.json'))+list(native_root.glob('*-result.json'))+[native_root/'native-link/generate-result.json']
    for config in (native_root/'configured/DEVELOPMENT').glob('*'):
        paths.extend(path for path in config.glob('*')if path.suffix in ('.h','.log')or path.name=='Makefile')
    records=[];metadata_left=2097152;diagnostics=bytearray(b'[native preparation diagnostics]\n');seen=set()
    for path in sorted(paths):
        if path in seen or not path.is_file()or path.is_symlink():continue
        seen.add(path);size=path.stat().st_size;record=dict(path=str(path),bytes=size,captured=False)
        if 0<size<=8388608:
            raw=bounded(path);record['sha256']=sha(raw)
            if path.suffix=='.log':
                block=('\n['+str(path.relative_to(ROOT))+']\n').encode()+raw;room=max(0,8388608-len(diagnostics));diagnostics.extend(block[:room]);record.update(captured=len(block)<=room,diagnostic_prefix_bytes=min(len(block),room))
            elif size<=metadata_left:
                try:record['text_utf8']=raw.decode();record['metadata_preserved']=True;metadata_left-=size
                except UnicodeError:record['metadata_preserved']=False
            else:record['metadata_preserved']=False
        records.append(record)
    save(OUT/'preparation-files.json',records);(OUT/'preparation-diagnostics.log').write_bytes(diagnostics)


def produce(head,context):
    require(sys.platform=='darwin'and not OUT.exists(),'fresh macOS factory capture only');ci={k:os.environ.get(k,'')for k in ('GITHUB_SHA','GITHUB_WORKFLOW_SHA','GITHUB_RUN_ID','GITHUB_RUN_ATTEMPT','GITHUB_JOB','GITHUB_WORKFLOW_REF','GITHUB_REPOSITORY','GITHUB_EVENT_NAME')}
    require(ci['GITHUB_SHA']==ci['GITHUB_WORKFLOW_SHA']==head and ci['GITHUB_RUN_ATTEMPT']=='1'and ci['GITHUB_JOB']==JOB and ci['GITHUB_WORKFLOW_REF']=='eirblue/ios_note10p/'+WORKFLOW+'@refs/heads/main'and ci['GITHUB_REPOSITORY']=='eirblue/ios_note10p'and ci['GITHUB_EVENT_NAME']=='workflow_dispatch','exact new reviewed workflow/head/attempt')
    expected=set(('schema','source_head','source_sha256','fixture','predecessor259'));require(set(context)==expected and context['schema']==SCHEMA+'-public-input-v1'and context['source_head']==head and context['source_sha256']==sources(),'exact reviewed public input closure')
    for key,count in (('fixture',4),('predecessor259',8)):
        row=context[key];require(set(row)=={'passed','groups','variants','assertions','result_sha256'}and row['passed']is True and (row['groups'],row['variants'],row['assertions'])==(1,count,count)and re.fullmatch('[0-9a-f]{64}',row['result_sha256']),'exact actual new/carried PASS metadata')
    OUT.mkdir(parents=True);result=dict(schema=SCHEMA+'-build-v1',passed=False,source_head=head,source_sha256=sources(),public_input=context,run_id=int(ci['GITHUB_RUN_ID']),run_attempt=1,factory_target_compile_attempts=0,other_XNU_target_object_compiles=0,native_kernel_link_attempts=0,host259_replays=0,old_tests_replayed=0,old_proof_replays=0,native_ABI_verified=False,native_kernel_contains_factory=False,native_activation=False,registered_provider=False,runtime_RAM_growth_measured=False,physical_ready=False);generation={};save(OUT/'sources.json',result['source_sha256']);profile=None
    try:
        with (OUT/'preparation.log').open('x',encoding='utf-8')as log,redirect_stdout(log),redirect_stderr(log):
            log.write('[native input preparation START]\n');log.flush();inputs.generate(generation,OUT)
        native_root=ROOT/'note10/private/windows-xnu';configured=json.loads(bounded(native_root/'configure-result.json'));source=ROOT/configured['source_directory'];compiler=os.environ['N10_CC'];sdk=os.environ['N10_SDKROOT'];apple=OUT/'original-headers';storage.stage_headers(apple)
        profile=profile_for(compiler,sdk,source,apple,head,ci);save(OUT/'profile.json',profile)
        with (OUT/'preparation.log').open('a',encoding='utf-8')as log,redirect_stdout(log),redirect_stderr(log):report=compiler_recipe.main(owned_ram_factory_profile=profile)
        require(len(report['units'])==1 and report['units'][0]['passed']is True,'exact single factory success');row=report['units'][0];obj=Path(profile['unit']['object_path']);raw=bounded(obj);require(len(raw)>=16 and struct.unpack_from('<4I',raw)==(0xfeedfacf,0x0100000c,0,1),'plain arm64 Mach-O object only');require(sha(raw)==row['object_sha256'],'intrinsic emitted object digest');(OUT/'factory.o').write_bytes(raw)
        dep=bounded(obj.with_suffix('.d'));(OUT/'factory.d').write_bytes(dep);save(OUT/'dependencies.json',dependency_rows(dep.decode(),profile));save(OUT/'compile.json',report);result.update(passed=True,genuine_SDK_factory_object_compiled=True,object_sha256=sha(raw),object_bytes=len(raw),producer_id=profile['producer_id'],input_binding=profile['input_binding'])
    except BaseException as error:result.update(error_type=type(error).__name__,error=str(error)[:2048]);raise
    finally:
        if profile is not None:
            obj=Path(profile['unit']['object_path']);partial={'factory.o':obj,'factory.d':obj.with_suffix('.d'),'compiler.log':obj.with_suffix('.log'),'COMPILE-STARTED.json':obj.parent/'FACTORY-COMPILE-STARTED.json','compile.json':obj.parent/'owned-ram-factory-result.json'}
            for name,path in partial.items():
                if path.is_file()and not(OUT/name).exists():
                    size=path.stat().st_size;result.setdefault('partial_member_metadata',{})[name]=dict(bytes=size,preserved=0<size<=8388608)
                    if 0<size<=8388608:(OUT/name).write_bytes(bounded(path))
        preserve_preparation();result['factory_target_compile_attempts']=int((OUT/'COMPILE-STARTED.json').exists());save(OUT/'generation.json',generation);save(OUT/'result.json',result)
        files=[p for p in OUT.iterdir()if p.is_file()];require(all(p.name in MEMBERS and 0<p.stat().st_size<=8388608 for p in files)and sum(p.stat().st_size for p in files)<=67108864,'bounded intrinsic capture set');save(OUT/'members.json',dict(schema=SCHEMA+'-members-v1',source_head=head,member_bytes={p.name:p.stat().st_size for p in files},member_sha256={p.name:sha(p.read_bytes())for p in files}))
        with zipfile.ZipFile(OUT.with_suffix('.zip'),'x',compression=zipfile.ZIP_DEFLATED)as bundle:
            for path in [*files,OUT/'members.json']:bundle.write(path,path.name)
        subprocess.run(['node',ROOT/'note10/device_test/sealed_affinity_artifact.cjs','seal',OUT.with_suffix('.zip'),OUT.with_suffix('.n10sealed'),head],check=True,timeout=120)


if __name__=='__main__':
    cli=argparse.ArgumentParser();cli.add_argument('--expected-source-head',required=True);cli.add_argument('--passed-new-test-context',required=True);args=cli.parse_args()
    context=json.loads(base64.b64decode(args.passed_new_test_context,validate=True));produce(args.expected_source_head,context)
