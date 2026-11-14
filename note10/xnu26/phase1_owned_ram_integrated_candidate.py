"""One complete native-selected factory link; its output is never executed."""
import argparse
import ast
import base64
from contextlib import redirect_stdout,redirect_stderr
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import zipfile
import build_current_native_kernel as builder
import native_handoff_artifact as artifact
import phase1_owned_ram_factory_object as retained
import phase1_owned_ram_kernel_integration as factory

ROOT=Path(__file__).resolve().parents[2]
HERE=ROOT/'note10/xnu26'
WORKFLOW='.github/workflows/note10-v264-native-capture-receipt.yml'
JOB='v264-native-capture-receipt'
ARTIFACT='note10-v264-native-capture-receipt-sealed-evidence'
STEM='note10-v264-native-capture-receipt'
OUT=ROOT/'note10/private/v264-native-integrated-build'
WORK=ROOT/'note10/private/v264-native-integrated-work'
STAGE=ROOT/'note10/private/v264-native-integrated-evidence'
SUMMARY=ROOT/'note10/private/v264-native-integrated-summary.json'
SEALED=ROOT/'note10/private/v264-native-integrated.n10sealed'
CAP=67108864


def require(ok,message):
    if not ok:raise ValueError(message)


def sha(raw):return hashlib.sha256(raw).hexdigest()


def save(path,value):
    with Path(path).open('x',encoding='utf-8',newline='\n')as stream:json.dump(value,stream,sort_keys=True,indent=2);stream.write('\n')


def source_files():
    names=set(retained.public_files())|{WORKFLOW,'note10/target.json','note10/device_test/v264_current_native_parcel.py'}
    names.update('note10/xnu26/'+name for name in ('phase1_owned_ram_integrated_candidate.py','phase1_owned_ram_kernel_integration.py','test_native_capture_receipt.py','native_handoff_artifact.py','compact_native_receipts.py','build_current_native_kernel.py','phase1_iostorage_kernel_link.py'))
    names.update('note10/xnu26/patches/'+name for name in ('0014-memdev-wide-byte-extent.patch','0015-user-exception-checked-fetch.patch'))
    pending=list(names)
    while pending:
        name=pending.pop()
        if not name.endswith('.py'):continue
        for node in ast.walk(ast.parse((ROOT/name).read_text(encoding='utf-8'))):
            modules=[item.name for item in node.names]if isinstance(node,ast.Import)else[node.module]if isinstance(node,ast.ImportFrom)and node.module else[]
            for module in modules:
                for folder in ('note10/xnu26','note10/device_test','note10'):
                    candidate=folder+'/'+module.replace('.','/')+'.py'
                    if (ROOT/candidate).is_file():
                        if candidate not in names:names.add(candidate);pending.append(candidate)
                        break
    return sorted(names)


def sources():return {name:sha((ROOT/name).read_bytes())for name in source_files()}


def public_context(head,fixture,fixture_sha,predecessor,predecessor_sha):
    require(re.fullmatch('[0-9a-f]{40}',head),'new reviewed public head')
    def summary(row,count,digest):
        require(row['passed']is True and(row['groups'],row['variants'],row['assertions'])==(1,count,count)and re.fullmatch('[0-9a-f]{64}',digest),'actual new/carried PASS')
        return dict(passed=True,groups=1,variants=count,assertions=count,result_sha256=digest)
    return dict(schema=STEM+'-public-input-v1',source_head=head,source_sha256=sources(),fixture=summary(fixture,2,fixture_sha),predecessor263=summary(predecessor,3,predecessor_sha))


def produce(head,context):
    ci=builder.ci_context(storage=True,checked=True,owned_ram_factory=True)
    require(sys.platform=='darwin'and os.environ.get('GITHUB_EVENT_NAME')=='workflow_dispatch'and head==ci['GITHUB_SHA']and os.environ.get('GITHUB_RUN_ATTEMPT')=='1','new genuine SDK first build')
    require(set(context)=={'schema','source_head','source_sha256','fixture','predecessor263'}and context['schema']==STEM+'-public-input-v1'and context['source_head']==head and context['source_sha256']==sources(),'exact new public closure')
    for key,count in (('fixture',2),('predecessor263',3)):
        row=context[key];require(set(row)=={'passed','groups','variants','assertions','result_sha256'}and row['passed']is True and(row['groups'],row['variants'],row['assertions'])==(1,count,count)and re.fullmatch('[0-9a-f]{64}',row['result_sha256']),'actual source-bound new/carried predicates')
    require(all(not p.exists()for p in (OUT,WORK,STAGE,SUMMARY,SEALED)),'new native build roots only')
    SUMMARY.parent.mkdir(parents=True,exist_ok=True);save(SUMMARY.with_suffix('.STARTED.json'),dict(source_head=head,public_input=context))
    producer_log=SUMMARY.with_suffix('.log')
    result=dict(schema='note10-v264-native-capture-receipt-build-v1',source_head=head,run_id=int(ci['GITHUB_RUN_ID']),run_attempt=1,passed=False,runtime_executed=False,physical_ready=False,native_activation=False,media_instantiated=False,media_started=False,consumer_invoked=False,factory_invoked=False,provider_started=False,provider_registered=False,source_sha256=context['source_sha256'],public_input=context,old_tests_replayed=0,old_proof_replays=0,Linux_Image_build_attempts=0,PID1_compile_attempts=0,full_native_build_attempts=0,tool_preflight={})
    try:
        with producer_log.open('x',encoding='utf-8')as log,redirect_stdout(log),redirect_stderr(log):
            log.write('[v264 full selected native build]\n');log.flush()
            preflight=result['tool_preflight'];preflight['compiler']=retained.inputs.command('xcrun','-f','clang');preflight['compiler_version']=retained.inputs.command(preflight['compiler'],'--version');preflight['SDK_version']=retained.inputs.command('xcrun','--sdk','macosx','--show-sdk-version');preflight['SDK_path']=retained.inputs.command('xcrun','--sdk','macosx','--show-sdk-path')
            require(retained.inputs.CLANG_VERSION in preflight['compiler_version']and preflight['SDK_version']==retained.inputs.SDK_VERSION,'genuine Apple compiler21/SDK26.5 before target build')
            result['full_native_build_attempts']=1
            builder.build(WORK,OUT,storage=True,memdev=True,user_exception_fetch=True,readonly_ram_nub=True,owned_ram_factory=True)
        state=json.loads((OUT/'result.json').read_text(encoding='utf-8'));link=state.get('link',{});storage=state.get('storage',{})
        require(state['passed']is True and state['phase']=='complete'and link['link_succeeded']is True and link['object_count']==1080 and state['owned_ram_factory']['passed']is True,'complete native factory selection/link')
        toolchain=json.loads((OUT/'producer-context.json').read_text(encoding='utf-8'))['producer']['toolchain'];preflight=result['tool_preflight']
        require(toolchain['compiler']==preflight['compiler']and toolchain['sdk']==preflight['SDK_path']and toolchain['compiler_version'].strip()==preflight['compiler_version'],'actual full-build tool context matches early observed compiler/SDK')
        result.update(passed=True,kernel_sha256=state['output_sha256'],kernel_bytes=state['output_bytes'],final_object_count=link['object_count'],storage_binding_sha256=storage['storage_binding_sha256'],storage_object_sha256=storage['storage_object_sha256'],memdev_integration=state['memdev'],user_exception_fetch_link=state['user_exception_fetch_link'],user_exception_tool_counts=state['user_exception_tool_counts'],readonly_ram_nub=state['readonly_ram_nub'],owned_ram_factory=state['owned_ram_factory'])
    except BaseException as error:
        result.update(error_type=type(error).__name__,error=str(error)[:2048]);raise
    finally:
        if OUT.is_dir()and producer_log.is_file():
            (OUT/'producer.log').write_bytes(producer_log.read_bytes())
        state=json.loads((OUT/'result.json').read_text(encoding='utf-8'))if (OUT/'result.json').is_file()else{}
        result.update(native_link_attempts=int(state.get('link',{}).get('attempted',False)),linked_unit_compile_attempts=state.get('memdev',{}).get('total_target_compile_attempts'),auxiliary_genassym_target_compiles=state.get('user_exception_tool_counts',{}).get('auxiliary_genassym_target_compiles'),factory_target_compile_attempts=state.get('owned_ram_factory',{}).get('compile_attempts',0),media_target_compile_attempts=state.get('storage',{}).get('media_target_compile_attempts',0),host_preparation_compiler_total=None)
        save(SUMMARY,result)
        capture_native(result,head,producer_log)
    return result


def capture_native(result,head,producer_log,*,runner=subprocess.run):
    record=artifact.stage(OUT,SUMMARY,STAGE,head=head,run_id=result['run_id'],attempt=1,compact=True,user_exception_fetch=True,readonly_ram_nub=True,owned_ram_factory=True)
    # Preserve bounded failure diagnostics too; no native object archive is uploaded.
    diagnostics=STAGE/'diagnostics';diagnostics.mkdir();captured=[];total=0
    logs=sorted(OUT.rglob('*.log'))
    if not OUT.exists()and producer_log.is_file():logs.append(producer_log)
    for path in logs:
        if path.is_symlink()or not path.is_file():continue
        size=path.stat().st_size;row=dict(path=path.relative_to(OUT).as_posix()if path.is_relative_to(OUT)else path.name,bytes=size,preserved=False)
        if 0<size<=1048576 and total+size<=4194304:
            raw=path.read_bytes();target=diagnostics/(str(len(captured))+'.log');target.write_bytes(raw);row.update(preserved=True,member=target.relative_to(STAGE).as_posix(),sha256=sha(raw));total+=size
        captured.append(row)
    save(diagnostics/'manifest.json',captured)
    # Refresh the new member manifest after adding actual failure/success logs.
    manifest=json.loads((STAGE/'members.json').read_text(encoding='utf-8'));manifest['members']=[dict(file=p.relative_to(STAGE).as_posix(),bytes=p.stat().st_size,sha256=sha(p.read_bytes()))for p in sorted(STAGE.rglob('*'))if p.is_file()and p.name!='members.json'];(STAGE/'members.json').write_text(json.dumps(manifest,indent=2,sort_keys=True)+'\n')
    packed=STAGE.with_suffix('.zip')
    with zipfile.ZipFile(packed,'x',zipfile.ZIP_DEFLATED)as bundle:
        for path in sorted(STAGE.rglob('*')):
            if path.is_file():bundle.write(path,path.relative_to(STAGE).as_posix())
    require(packed.stat().st_size<=CAP and sum(p.stat().st_size for p in STAGE.rglob('*')if p.is_file())<=CAP,'bounded new sealed native evidence')
    runner(['node',str(ROOT/'note10/device_test/sealed_affinity_artifact.cjs'),'seal',str(packed),str(SEALED),head],cwd=ROOT,check=True,timeout=180)
    artifact.capture_verdict(record)
    require(record['kernel_retained']is result['passed'],'truthful authenticated native capture')
    return record


if __name__=='__main__':
    cli=argparse.ArgumentParser(description=__doc__);cli.add_argument('--expected-source-head',required=True);cli.add_argument('--passed-new-test-context',required=True);args=cli.parse_args()
    context=json.loads(base64.b64decode(args.passed_new_test_context,validate=True))
    produce(args.expected_source_head,context)
