"""Prepare/inspect offline. Device mutations require the explicit run --execute path."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import zipfile
import time
import uuid
from run_probe import ROOT,Adb,preflight
from stage_phase2 import stage,verify_packages
from precheck_window_access import check
from collect_reservation import collect
from decode_auto_return import decode as decode_return
from materialize_auto_cycle import materialize,validate as validate_variant


def read(path):return json.loads(Path(path).read_text(encoding='utf-8-sig'))
def save(path,value):Path(path).write_text(json.dumps(value,indent=2),encoding='utf-8')
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def private(path):
    path=Path(path).resolve()
    if not path.is_relative_to((ROOT/'note10/private').resolve()):raise ValueError('Private workspace path required')
    return path


def prepare_plan(*,kernel_build,backup,twrp,mkbootimg,current_packages,output,cycles=1):
    from prepare_linux_boot import prepare
    from build_boot_test_packages import build
    output=private(output)
    if output.exists() or not 1<=cycles<=5:raise ValueError('Fresh output and 1..5 cycles required')
    kernel_build=private(kernel_build);backup=private(backup);current_packages=private(current_packages)
    result=read(kernel_build/'build-result.json')
    if result.get('build_passed') is not True or result.get('auto_return_diagnostic') is not True:raise ValueError('Compiled opt-in auto-return kernel required; v7 cannot auto-return')
    verify_packages(current_packages)
    output.mkdir(parents=True)
    stages=[];previous=current_packages
    for index in range(cycles):
        cycle=uuid.uuid4().hex;folder=output/f'cycle-{index+1:02d}';folder.mkdir()
        variant=folder/'kernel-build';variant_report=materialize(kernel_build,variant,cycle)
        image=folder/'boot.img'
        prepare(backup,variant,Path(twrp),Path(mkbootimg),image,auto_cycle_token=cycle)
        packages=folder/'packages';pair=build(backup,image,packages,previous)
        stages.append(dict(index=index+1,cycle=cycle,kernel_build=str(variant),image_sha256=variant_report['image_sha256'],build_result_sha256=sha(variant/'build-result.json'),packages=str(packages),package_result_sha256=sha(packages/'package-result.json')))
        previous=packages
    plan=dict(schema=1,kind='note10-bounded-auto-cycle',kernel_build=str(kernel_build),backup=str(backup),
        backup_manifest_sha256=sha(backup/'backup-manifest.json'),build_result_sha256=sha(kernel_build/'build-result.json'),
        image_sha256=sha(kernel_build/'Image'),identity=result['reservation_evidence_id'],
        core_model=str(kernel_build.parent/'window-access-core-ci/result.json'),
        gate_model=str(kernel_build.parent/'window-access-gate-ci/result.json'),
        init_model=str(kernel_build/'minimal-init-model.json'),minimum_battery=30,return_timeout_seconds=240,stages=stages)
    save(output/'plan.json',plan)
    return dict(plan=str(output/'plan.json'),plan_sha256=sha(output/'plan.json'),cycles=cycles,device_operations=[])


def validate_plan(path,expected):
    path=private(path)
    if not re.fullmatch('[0-9a-f]{64}',expected or '') or sha(path)!=expected:raise ValueError('Exact reviewed plan SHA256 required')
    plan=read(path)
    if plan.get('schema')!=1 or plan.get('kind')!='note10-bounded-auto-cycle' or plan.get('minimum_battery')!=30 or plan.get('return_timeout_seconds')!=240:raise ValueError('Unsupported cycle policy')
    stages=plan.get('stages',[])
    if not 1<=len(stages)<=5 or len({s['cycle'] for s in stages})!=len(stages):raise ValueError('Invalid cycle count or reused token')
    build=private(plan['kernel_build']);backup=private(plan['backup'])
    if sha(build/'build-result.json')!=plan['build_result_sha256'] or sha(build/'Image')!=plan['image_sha256'] or sha(backup/'backup-manifest.json')!=plan['backup_manifest_sha256']:raise ValueError('Plan build/backup changed')
    report=read(build/'build-result.json')
    if report.get('build_passed') is not True or report.get('auto_return_diagnostic') is not True or report.get('reservation_evidence_id')!=plan['identity']:raise ValueError('Auto-return build binding differs')
    last=None
    for number,item in enumerate(stages,1):
        folder=private(item['packages'])
        if item['index']!=number or not re.fullmatch('[0-9a-f]{32}',item['cycle']) or sha(folder/'package-result.json')!=item['package_result_sha256']:raise ValueError('Stage manifest changed')
        variant=private(item['kernel_build']);variant_report=validate_variant(variant,item['cycle'],build)
        if sha(variant/'build-result.json')!=item['build_result_sha256'] or variant_report['image_sha256']!=item['image_sha256']:raise ValueError('Stage variant changed')
        records=verify_packages(folder);pair=read(folder/'package-result.json')
        diag=next(r for r in records if r['mode']=='diagnostic')
        if pair.get('auto_return_diagnostic') is not True or pair.get('auto_cycle_token')!=item['cycle'] or diag.get('auto_cycle_token')!=item['cycle'] or diag.get('auto_return_diagnostic') is not True or pair['kernel_image_sha256']!=item['image_sha256']:raise ValueError('Stage cycle scope differs')
        from prepare_linux_boot import boot_header
        with zipfile.ZipFile(folder/diag['file']) as archive:header=boot_header(archive.read('boot.img'))
        if header['kernel_sha256']!=item['image_sha256'] or 'n10.cycle=' in header['cmdline']:raise ValueError('Actual BOOT kernel/cycle binding differs')
        if last and pair['expected_current_boot_sha256']!=last:raise ValueError('Stage BOOT chain differs')
        last=diag['payload_sha256']
    for key in ('core_model','gate_model','init_model'):private(plan[key])
    return plan


def boot_id(adb):
    value=adb.text('shell','cat','/proc/sys/kernel/random/boot_id')
    if not re.fullmatch('[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}',value):raise ValueError('Recovery boot ID unavailable')
    return value


def verify_partitions(adb,backup,boot_sha):
    manifest=read(Path(backup)/'backup-manifest.json')
    if adb.text('shell','getprop','ro.bootloader')!=manifest['bootloader']:raise ValueError('Bootloader changed')
    if {p['partition'] for p in manifest['partitions']}!={'boot','recovery','dtb','dtbo','vbmeta'}:raise ValueError('Five partition baseline required')
    for row in manifest['partitions']:
        if not re.fullmatch('/dev/block/sd[a-z][0-9]+',row['block_node']):raise ValueError('Invalid block path')
        expected=boot_sha if row['partition']=='boot' else row['sha256']
        if adb.text('shell','sha256sum',row['block_node']).split()[0]!=expected:raise ValueError('Partition differs: '+row['partition'])


def wait_recovery(adb,previous_id,seconds,monotonic=time.monotonic,sleep=time.sleep):
    deadline=monotonic()+seconds
    original=adb.call
    def bounded_call(*args,**kwargs):
        remaining=deadline-monotonic()
        if remaining<=0:raise TimeoutError('Recovery deadline expired')
        kwargs['timeout']=min(kwargs.get('timeout',30),3,remaining)
        return original(*args,**kwargs)
    adb.call=bounded_call
    try:
        while monotonic()<deadline:
            try:
                preflight(adb)
                current=boot_id(adb)
                if current!=previous_id:return current
            except (RuntimeError,ValueError,subprocess.TimeoutExpired):pass
            sleep(min(2,max(0,deadline-monotonic())))
        raise TimeoutError('Recovery did not return with a new boot ID; stop, do not flash or reboot again')
    finally:
        adb.call=original


def run_plan(path,expected,output,*,execute=False,limit=1,adb=None,verified_roundtrip=None,roundtrip_sha256=None):
    if not execute:raise ValueError('Preparation only: run requires explicit --execute; no device contacted')
    plan=validate_plan(path,expected)
    if limit not in range(1,len(plan['stages'])+1):raise ValueError('Cycle limit exceeds reviewed plan')
    proof=None
    if limit>1:
        if verified_roundtrip is None:raise ValueError('First execution is one cycle; verified single-cycle journal required for repetitions')
        proof_path=private(verified_roundtrip)
        if sha(proof_path)!=roundtrip_sha256:raise ValueError('Reviewed roundtrip journal SHA256 required')
        proof=read(proof_path)
        if proof.get('status')!='complete' or proof.get('single_cycle_verified') is not True or proof.get('kernel_image_sha256')!=plan['image_sha256'] or proof.get('backup_manifest_sha256')!=plan['backup_manifest_sha256'] or not proof.get('completed') or not all(x.get('passed') and x.get('recovery_boot_id_changed') for x in proof['completed']):raise ValueError('Prior automatic roundtrip is not verified for this build')
    output=private(output)
    if output.exists():raise ValueError('Fresh journal directory required')
    output.mkdir(parents=True)
    journal=dict(plan_sha256=expected,kernel_image_sha256=plan['image_sha256'],backup_manifest_sha256=plan['backup_manifest_sha256'],single_cycle_verified=False,status='started',completed=[],partition_writes_attempted=False,reboots_attempted=False)
    def persist():save(output/'journal.json',journal)
    persist()
    try:
        adb=adb or Adb(shutil.which('adb') or 'adb')
        initial=preflight(adb);journal['device_binding_sha256']=hashlib.sha256(adb.serial.encode()).hexdigest();persist()
        if proof and proof.get('device_binding_sha256')!=journal['device_binding_sha256']:raise ValueError('Prior roundtrip belongs to another device')
        for item in plan['stages'][:limit]:
            if item['index']>1 and not journal['completed'][-1]['passed']:raise ValueError('Previous cycle did not pass')
            packages=Path(item['packages']);records=verify_packages(packages);diag=next(r for r in records if r['mode']=='diagnostic')
            staged=stage(packages,adb)
            ready=check(packages,Path(item['kernel_build']),Path(plan['backup']),Path(plan['core_model']),Path(plan['gate_model']),Path(plan['init_model']),adb)
            if ready.get('ready_for_manual_access_test') is not True:raise ValueError('Readiness did not pass')
            before=boot_id(adb)
            if adb.text('shell','command','-v','twrp')!='/sbin/twrp':raise ValueError('Expected TWRP CLI unavailable')
            journal['active_cycle']=item['cycle'];journal['partition_writes_attempted']=True;persist()
            adb.call('shell','twrp','install',staged['ram_directory']+'/'+diag['file'],timeout=180)
            preflight(adb);verify_partitions(adb,plan['backup'],diag['payload_sha256'])
            journal['reboots_attempted']=True;persist()
            try:adb.call('shell','twrp','reboot',timeout=30)
            except RuntimeError:pass  # adbd may close as reboot starts; never resend.
            after=wait_recovery(adb,before,plan['return_timeout_seconds'])
            if preflight(adb)['twrp_version']!=initial['twrp_version']:raise ValueError('Recovery version changed')
            # Preserve diagnostic logs immediately after return, even when tests failed.
            captured=collect(packages,Path(item['kernel_build']),adb)
            verify_partitions(adb,plan['backup'],diag['payload_sha256'])
            return_observation=None
            for name,selection in captured.get('log_selections',{}).items():
                selected=Path(captured['directory'])/selection.get('selected_file',name)
                try:return_observation=decode_return(selected.read_bytes(),plan['identity'],item['cycle']);break
                except ValueError:continue
            passed=bool(captured.get('diagnostic_passed') and return_observation)
            entry=dict(index=item['index'],cycle=item['cycle'],passed=passed,capture=captured['directory'],
                recovery_boot_id_changed=after!=before,auto_return=return_observation)
            journal['completed'].append(entry);persist()
            if not passed:raise ValueError('Diagnostic or automatic-return evidence failed; repetitions stopped')
        journal['status']='complete';journal['single_cycle_verified']=limit==1;persist();return journal
    except BaseException as error:
        journal.update(status='stopped',failure=str(error) or type(error).__name__);persist();raise


def main():
    parser=argparse.ArgumentParser(description=__doc__);sub=parser.add_subparsers(dest='command',required=True)
    p=sub.add_parser('prepare')
    for name in ('kernel-build','backup','twrp','mkbootimg','current-packages','output'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--cycles',type=int,default=1)
    for command in ('inspect','run'):
        p=sub.add_parser(command);p.add_argument('--plan',type=Path,required=True);p.add_argument('--plan-sha256',required=True)
        if command=='run':p.add_argument('--output',type=Path,required=True);p.add_argument('--execute',action='store_true');p.add_argument('--limit',type=int,default=1);p.add_argument('--verified-roundtrip',type=Path);p.add_argument('--roundtrip-sha256')
    args=vars(parser.parse_args());command=args.pop('command')
    if command=='prepare':result=prepare_plan(**args)
    elif command=='inspect':
        plan=validate_plan(args['plan'],args['plan_sha256']);result=dict(valid=True,cycles=len(plan['stages']),device_operations=[])
    else:result=run_plan(args['plan'],args['plan_sha256'],args['output'],execute=args['execute'],limit=args['limit'],verified_roundtrip=args['verified_roundtrip'],roundtrip_sha256=args['roundtrip_sha256'])
    print(json.dumps(result,indent=2))

if __name__=='__main__':main()
