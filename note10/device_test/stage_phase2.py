"""Copy verified phase-2 ZIPs to a fresh TWRP RAM directory; never install."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import uuid
import zipfile
from run_probe import Adb,ROOT,preflight


def verify_packages(directory):
    result=json.loads((directory/'package-result.json').read_text())
    expected=({'note10-phase2-diagnostic.zip','note10-phase2-rollback.zip'},
              {'note10-reservation-diagnostic.zip','note10-reservation-rollback.zip'})
    records=result.get('packages',[])
    if len(records)!=2 or {r['file'] for r in records} not in expected:raise ValueError('Expected a matched diagnostic/rollback pair')
    for record in records:
        path=directory/record['file']
        if path.is_symlink() or not 0<path.stat().st_size<=128*1024*1024:raise ValueError('Unsafe package file')
        if hashlib.sha256(path.read_bytes()).hexdigest()!=record['sha256']:raise ValueError('Package hash mismatch')
        with zipfile.ZipFile(path) as archive:
            if len(archive.namelist())!=len(set(archive.namelist())) or archive.testzip() is not None:
                raise ValueError('Invalid/duplicate archive members')
            meta=json.loads(archive.read('manifest.json'))
            for feature in ('gic_roundtrip','dma_pm_audit','ufs_pm_audit','iommu_pm_audit','abox_pm_audit','abox_pmu_audit','pm_noirq','pmu_settle','pm_cpus','pm_post_arch','pm_edge_inventory','pm_irq','pm_callbacks'):
                flag=feature+'_diagnostic';version=feature+'_evidence_version'
                if bool(meta.get(flag))!=bool(record.get(flag)) or meta.get(version)!=record.get(version):
                    raise ValueError('Diagnostic package record differs: '+feature)
                if record.get('mode')=='diagnostic' and (bool(meta.get(flag))!=bool(result.get(flag)) or meta.get(version)!=result.get(version)):
                    raise ValueError('Diagnostic package pair differs: '+feature)
            if bool(meta.get('pm_preconditions_diagnostic'))!=bool(record.get('pm_preconditions_diagnostic')) or meta.get('pm_preconditions_version')!=record.get('pm_preconditions_version'):
                raise ValueError('Preconditions package record differs')
            if record.get('mode')=='diagnostic' and (bool(meta.get('pm_preconditions_diagnostic'))!=bool(result.get('pm_preconditions_diagnostic')) or meta.get('pm_preconditions_version')!=result.get('pm_preconditions_version')):
                raise ValueError('Preconditions package pair differs')
            if bool(meta.get('pm_branch_diagnostic'))!=bool(record.get('pm_branch_diagnostic')) or meta.get('pm_branch_version')!=record.get('pm_branch_version'):
                raise ValueError('Branch package record differs')
            if record.get('mode')=='diagnostic' and (bool(meta.get('pm_branch_diagnostic'))!=bool(result.get('pm_branch_diagnostic')) or meta.get('pm_branch_version')!=result.get('pm_branch_version')):
                raise ValueError('Branch package pair differs')
            if bool(meta.get('pmu_failure_restore'))!=bool(record.get('pmu_failure_restore')) or meta.get('pmu_failure_restore_version')!=record.get('pmu_failure_restore_version'):
                raise ValueError('Failure guard package record differs')
            if record.get('mode')=='diagnostic' and (bool(meta.get('pmu_failure_restore'))!=bool(result.get('pmu_failure_restore')) or meta.get('pmu_failure_restore_version')!=result.get('pmu_failure_restore_version')):
                raise ValueError('Failure guard package pair differs')
            if bool(meta.get('gic_priority_restore'))!=bool(record.get('gic_priority_restore')) or meta.get('gic_priority_restore_version')!=record.get('gic_priority_restore_version'):
                raise ValueError('GIC priority package record differs')
            if record.get('mode')=='diagnostic' and (bool(meta.get('gic_priority_restore'))!=bool(result.get('gic_priority_restore')) or meta.get('gic_priority_restore_version')!=result.get('gic_priority_restore_version')):
                raise ValueError('GIC priority package pair differs')
            if bool(meta.get('pmu_state_audit'))!=bool(record.get('pmu_state_audit')) or meta.get('pmu_state_audit_version')!=record.get('pmu_state_audit_version'):
                raise ValueError('PMU state package record differs')
            if record.get('mode')=='diagnostic' and (bool(meta.get('pmu_state_audit'))!=bool(result.get('pmu_state_audit')) or meta.get('pmu_state_audit_version')!=result.get('pmu_state_audit_version')):
                raise ValueError('PMU state package pair differs')
            if bool(meta.get('pmu_control_audit'))!=bool(record.get('pmu_control_audit')) or meta.get('pmu_control_audit_version')!=record.get('pmu_control_audit_version'):
                raise ValueError('PMU control package record differs')
            if record.get('mode')=='diagnostic' and (bool(meta.get('pmu_control_audit'))!=bool(result.get('pmu_control_audit')) or meta.get('pmu_control_audit_version')!=result.get('pmu_control_audit_version')):
                raise ValueError('PMU control package pair differs')
            if bool(meta.get('fpsimd_reference_audit'))!=bool(record.get('fpsimd_reference_audit')) or meta.get('fpsimd_reference_audit_version')!=record.get('fpsimd_reference_audit_version'):
                raise ValueError('FPSIMD reference package metadata differs')
            if record.get('mode')=='diagnostic' and (bool(meta.get('fpsimd_reference_audit'))!=bool(result.get('fpsimd_reference_audit')) or meta.get('fpsimd_reference_audit_version')!=result.get('fpsimd_reference_audit_version')):
                raise ValueError('FPSIMD reference package pair differs')
            if bool(meta.get('rcu_context_audit'))!=bool(record.get('rcu_context_audit')) or meta.get('rcu_context_audit_version')!=record.get('rcu_context_audit_version'):
                raise ValueError('RCU context package metadata differs')
            if record.get('mode')=='diagnostic' and (bool(meta.get('rcu_context_audit'))!=bool(result.get('rcu_context_audit')) or meta.get('rcu_context_audit_version')!=result.get('rcu_context_audit_version')):
                raise ValueError('RCU context package pair differs')
            if bool(meta.get('abox_failed_fw_resume_guard'))!=bool(record.get('abox_failed_fw_resume_guard')) or (record.get('mode')=='diagnostic' and bool(meta.get('abox_failed_fw_resume_guard'))!=bool(result.get('abox_failed_fw_resume_guard'))):raise ValueError('Failed-firmware guard package scope differs')
            if meta['writes']!=['boot'] or meta['automatic_reboot'] is not False:raise ValueError('Unexpected installer scope')
            if meta.get('xnu_payload_stage_diagnostic') is True and (
                meta.get('window_access_diagnostic') is not True or meta.get('test_purpose')!='xnu-payload-stage' or
                not re.fullmatch(r'[0-9a-f]{64}',meta.get('xnu_payload_sha256','')) or
                type(meta.get('xnu_payload_size')) is not int):
                raise ValueError('Incomplete XNU data-stage package contract')
            if meta.get('mode')=='rollback' and meta.get('xnu_payload_stage_diagnostic',False) is not False:
                raise ValueError('Rollback package cannot claim XNU staging')
            if meta.get('cpu_cache_roundtrip_diagnostic') is True and (
                meta.get('xnu_payload_stage_diagnostic') is not True or meta.get('mode')!='diagnostic'):
                raise ValueError('CPU/cache diagnostic must explicitly require XNU staging')
            if bool(meta.get('screen_log_diagnostic'))!=bool(record.get('screen_log_diagnostic')):raise ValueError('Screen log package record differs')
            if meta.get('screen_log_diagnostic') and not meta.get('auto_return_diagnostic'):raise ValueError('Screen log without recovery refused')
            if bool(meta.get('auto_return_diagnostic'))!=bool(record.get('auto_return_diagnostic')) or meta.get('auto_cycle_token')!=record.get('auto_cycle_token'):raise ValueError('Auto-return package record differs from archive')
            if meta.get('auto_return_diagnostic') and (meta.get('mode')!='diagnostic' or not meta.get('pm_timer_diagnostic') or not re.fullmatch('[0-9a-f]{32}',meta.get('auto_cycle_token',''))):raise ValueError('Invalid auto-return manifest')
            if meta.get('pm_timer_diagnostic') is True and meta.get('cpu_cache_roundtrip_diagnostic') is not True:
                raise ValueError('PM/timer must explicitly require CPU/cache batch')
            if bool(meta.get('pm_quiesce_diagnostic'))!=bool(record.get('pm_quiesce_diagnostic')) or meta.get('pm_quiesce_evidence_version')!=record.get('pm_quiesce_evidence_version'):
                raise ValueError('PM quiesce package record differs')
            if meta.get('pm_quiesce_diagnostic') and (meta.get('mode')!='diagnostic' or not meta.get('pm_timer_diagnostic') or meta.get('pm_quiesce_evidence_version')!=1):
                raise ValueError('Invalid PM quiesce manifest')
            if hashlib.sha256(archive.read('META-INF/com/google/android/update-binary')).hexdigest()!=meta['updater_sha256']:
                raise ValueError('Updater integrity mismatch')
            if hashlib.sha256(archive.read('boot.img')).hexdigest()!=meta['payload_sha256']:
                raise ValueError('Payload integrity mismatch')
    return records


def stage(directory,adb):
    records=verify_packages(directory)
    state=preflight(adb)
    bootloader=adb.text('shell','getprop','ro.bootloader')
    if not re.fullmatch(r'N976N[A-Z0-9]+',bootloader):raise ValueError('N976N bootloader required')
    if not adb.text('shell','ls','-ld','/tmp').startswith('d'):raise ValueError('Unexpected tmp path')
    mounts=adb.text('shell','cat','/proc/mounts')
    candidates=[line.split() for line in mounts.splitlines() if len(line.split())>=3 and line.split()[1] in ('/','/tmp')]
    if not candidates or max(candidates,key=lambda row:len(row[1]))[2] not in ('tmpfs','ramfs','rootfs'):
        raise ValueError('Memory-backed tmp required')
    tools=adb.text('shell','command','-v','sh','unzip','dd','sha256sum','blockdev','readlink','sync','awk')
    if len(tools.splitlines())!=8:raise ValueError('Required native TWRP utilities not all found')
    prefix='note10-reserve-' if records[0]['file'].startswith('note10-reservation-') else 'note10-phase2-'
    remote='/tmp/'+prefix+uuid.uuid4().hex[:8]
    adb.call('shell','mkdir',remote)
    adb.call('shell','chmod','700',remote)
    for record in records:
        target=remote+'/'+record['file']
        adb.call('push',str(directory/record['file']),target,timeout=120)
        digest=adb.text('shell','sha256sum',target).split()[0]
        if digest!=record['sha256']:raise ValueError('RAM copy checksum mismatch')
        native_meta=json.loads(adb.text('shell','unzip','-p',target,'manifest.json'))
        if native_meta['payload_sha256']!=record['payload_sha256']:raise ValueError('Native ZIP manifest mismatch')
    report={'ram_directory':remote,'packages':[r['file'] for r in records],
            'model':state['model'],'twrp_version':state['twrp_version'],
            'native_archive_read_verified':True,'installed':False,'rebooted':False,
            'partition_writes':False,'xnu_executed':False,'deployment_ready':False,
            'scope':'TWRP RAM file staging only; paths disappear on reboot'}
    (directory/('ram-stage-'+remote.rsplit('-',1)[1]+'.json')).write_text(json.dumps(report,indent=2),encoding='utf-8')
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--packages',type=Path,required=True)
    report=stage(parser.parse_args().packages,Adb(ROOT/'host-tools/platform-tools/adb.exe'))
    print(json.dumps(report))
