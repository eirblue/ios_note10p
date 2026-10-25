"""Verify manual RAM-access ZIPs staged in TWRP RAM; never install/reboot."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import zipfile
from prepare_linux_boot import ROOT,read_verified_backup
from prepare_reservation_kernel import verify_embedded_init
from run_probe import Adb,preflight
from stage_phase2 import verify_packages


def check(packages,kernel_build,backup,core_model,gate_model,init_model,adb):
    if not packages.resolve().is_relative_to((ROOT/'note10/private').resolve()):
        raise ValueError('Private package directory required')
    report={'ready_for_manual_access_test':False,'current_device_checks_pending':True,
            'partition_writes':False,'rebooted':False,'installed_by_agent':False,'xnu_executed':False}
    target=packages/'PREINSTALL-CHECK.json'
    target.write_text(json.dumps(report,indent=2))
    try:
        records=verify_packages(packages)
        diagnostic=next(r for r in records if r['mode']=='diagnostic')
        if diagnostic.get('test_purpose') not in ('ram-window-access','xnu-payload-stage') or diagnostic.get('window_access_diagnostic') is not True:
            raise ValueError('RAM-access diagnostic pair required')
        paired=json.loads((packages/'package-result.json').read_text())
        build=json.loads((kernel_build/'build-result.json').read_text())
        if not (build.get('build_passed') is True and build.get('window_access_diagnostic') is True and
                build.get('window_access_evidence_version')==1 and build.get('reservation_evidence_version')==2):
            raise ValueError('Successful opt-in access kernel build required')
        xnu_stage=paired.get('xnu_payload_stage_diagnostic') is True
        cpu_cache=paired.get('cpu_cache_roundtrip_diagnostic') is True
        if cpu_cache!=(build.get('cpu_cache_roundtrip_diagnostic') is True) or \
           cpu_cache!=(diagnostic.get('cpu_cache_roundtrip_diagnostic') is True):
            raise ValueError('CPU/cache diagnostic package and kernel scope differ')
        if cpu_cache:
            model=json.loads((kernel_build/'cpu-cache-model/result.json').read_text())
            source_sha=hashlib.sha256(Path(__file__).with_name('cpu_cache_roundtrip.c').read_bytes()).hexdigest()
            if (not xnu_stage or model.get('passed') is not True or len(model.get('cases',[]))<10 or
                model.get('source_sha256')!=source_sha or model.get('source_sha256')!=build.get('cpu_cache_source_sha256') or
                model.get('payload_sha256')!=build.get('xnu_payload_sha256') or
                model.get('payload_size')!=build.get('xnu_payload_size')):
                raise ValueError('Actual CPU/cache C model does not match this kernel and payload')
        if xnu_stage!=(build.get('xnu_payload_stage_diagnostic') is True):
            raise ValueError('Package and kernel XNU-stage scope differs')
        if xnu_stage and (paired.get('xnu_payload_sha256')!=build.get('xnu_payload_sha256') or
                          paired.get('xnu_payload_size')!=build.get('xnu_payload_size') or
                          diagnostic.get('xnu_payload_sha256')!=build.get('xnu_payload_sha256') or
                          diagnostic.get('xnu_payload_size')!=build.get('xnu_payload_size') or
                          build.get('xnu_payload_initramfs_verified') is not True):
            raise ValueError('Package XNU payload differs from the current kernel Image')
        image=(kernel_build/'Image').read_bytes();digest=hashlib.sha256(image).hexdigest()
        if digest!=build['image_sha256'] or digest!=paired['kernel_image_sha256']:
            raise ValueError('Kernel build/package mismatch')
        identity=build['reservation_evidence_id']
        if not re.fullmatch(r'[0-9a-f]{32}',identity) or image.count(identity.encode())!=1 or b'N10MEM1' not in image:
            raise ValueError('Expected unique build ID and access marker in Image')
        if xnu_stage and b'N10XNU1' not in image:raise ValueError('XNU stage evidence marker missing from Image')
        if cpu_cache and any(marker not in image for marker in (b'N10QUI1',b'N10CPU2')):
            raise ValueError('CPU/cache diagnostic markers missing from Image')
        embedded=verify_embedded_init(image,(kernel_build/'initramfs.cpio').read_bytes())
        core=json.loads(core_model.read_text());gate=json.loads(gate_model.read_text());init=json.loads(init_model.read_text())
        sources=build['window_access_sources_sha256']
        if not (core.get('passed') is True and gate.get('passed') is True and init.get('passed') is True):
            raise ValueError('Actual C and init instruction models must pass')
        if core['core_sha256']!=sources['note10_window_access_core.h'] or gate['core_sha256']!=core['core_sha256']:
            raise ValueError('Actual core model/build source differs')
        if gate['wrapper_sha256']!=sources['note10_xnu_window_access.c']:
            raise ValueError('Actual wrapper model/build source differs')
        if init['elf_sha256']!=hashlib.sha256((kernel_build/'minimal-init.elf').read_bytes()).hexdigest():
            raise ValueError('Init instruction model differs from actual ELF')
        read_verified_backup(backup)
        baseline=json.loads((backup/'backup-manifest.json').read_text())
        if paired['backup_manifest_sha256']!=hashlib.sha256((backup/'backup-manifest.json').read_bytes()).hexdigest():
            raise ValueError('Backup and package differ')
        stages=list(packages.glob('ram-stage-*.json'))
        if not stages:raise ValueError('TWRP RAM staging required')
        stage=json.loads(max(stages,key=lambda p:p.stat().st_mtime_ns).read_text())
        remote=stage['ram_directory']
        if not re.fullmatch(r'/tmp/note10-reserve-[0-9a-f]{8}',remote):raise ValueError('Unexpected RAM path')
        state=preflight(adb)
        if adb.text('shell','getprop','ro.bootloader')!=baseline['bootloader']:raise ValueError('Bootloader changed')
        battery=int(adb.text('shell','cat','/sys/class/power_supply/battery/capacity'))
        if not 30<=battery<=100:raise ValueError('Charge to at least 30 percent before manual install')
        native=[]
        for record in records:
            with zipfile.ZipFile(packages/record['file']) as archive:
                code=archive.read('META-INF/com/google/android/update-binary')
            syntax=subprocess.run([adb.executable,'-s',adb.serial,'shell','-T','sh','-n'],
                                  input=code,capture_output=True,timeout=30)
            if syntax.returncode:raise ValueError('Native updater syntax failed')
            if adb.text('shell','sha256sum',remote+'/'+record['file']).split()[0]!=record['sha256']:
                raise ValueError('RAM ZIP hash mismatch')
            native.append({'file':record['file'],'native_syntax_passed':True,'ram_hash_matched':True})
        checks=[]
        if len(baseline['partitions'])!=5 or {p['partition'] for p in baseline['partitions']}!={'boot','recovery','dtb','dtbo','vbmeta'}:
            raise ValueError('Expected five paired partition records')
        for item in baseline['partitions']:
            if not re.fullmatch(r'/dev/block/sd[a-z][0-9]+',item['block_node']):raise ValueError('Unexpected partition node')
            expected=paired['expected_current_boot_sha256'] if item['partition']=='boot' else item['sha256']
            if adb.text('shell','sha256sum',item['block_node']).split()[0]!=expected:
                raise ValueError('Current partition changed: '+item['partition'])
            checks.append({'partition':item['partition'],'matches_expected':True})
        report.update(ready_for_manual_access_test=True,current_device_checks_pending=False,
                      ram_directory=remote,battery_percent=battery,twrp_version=state['twrp_version'],
                      native_checks=native,partition_checks=checks,kernel_image_sha256=digest,
                      build_evidence_id=identity,embedded_initramfs_check=embedded,
                      core_model_cases=len(core['cases']),gate_model_cases=len(gate['cases']),
                      xnu_payload_stage_diagnostic=xnu_stage,
                      cpu_cache_roundtrip_diagnostic=cpu_cache,
                      xnu_payload_sha256=build.get('xnu_payload_sha256') if xnu_stage else None,
                      xnu_payload_size=build.get('xnu_payload_size') if xnu_stage else None,
                      scope=('Read-only readiness for manual same-boot XNU-data staging/readback test'
                             if xnu_stage else 'Read-only device readiness for manual same-boot cached RAM write/read/scrub test'))
    except Exception as error:
        report['failure']=str(error);target.write_text(json.dumps(report,indent=2));raise
    target.write_text(json.dumps(report,indent=2));return report


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('packages','kernel-build','backup','core-model','gate-model','init-model'):
        p.add_argument('--'+name,type=Path,required=True)
    args=p.parse_args()
    r=check(args.packages,args.kernel_build,args.backup,args.core_model,args.gate_model,args.init_model,
            Adb(ROOT/'host-tools/platform-tools/adb.exe'))
    print(json.dumps({key:r[key] for key in ('ready_for_manual_access_test','ram_directory','battery_percent','partition_writes','rebooted')}))
