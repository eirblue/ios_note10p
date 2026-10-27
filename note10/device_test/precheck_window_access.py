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

# Exact outputs of the pinned base guard and its read-only DMA observer recipe.
# The recipe integration test recomputes both; neither hash substitutes for the
# existing actual-C/source/model checks or the Image/config scope checks.
BASE_GUARDED_SUSPEND_SHA='8d7d2afaf265f9c944cc8ffc69303d06a8fc1bca53382ceff449c9da1b79b3d1'
DMA_GUARDED_SUSPEND_SHA='d9e4a9e8e23188c0ca1758993066ed06c379b19d35c67ae40bc0f6eada77a947'

def pm_suspend_patch_bound(build,patch_model):
    if build.get('dma_pm_audit_diagnostic') is not True:
        return patch_model.get('patched_sha256')==build.get('patched_suspend_sha256')
    from prepare_pm_diagnostic import SUSPEND_SHA
    return (patch_model.get('source_sha256')==SUSPEND_SHA and
        patch_model.get('patched_sha256')==BASE_GUARDED_SUSPEND_SHA and
        build.get('patched_suspend_sha256')==DMA_GUARDED_SUSPEND_SHA and
        build.get('dma_pm_audit_patched_sha256',{}).get('kernel/power/suspend.c')==DMA_GUARDED_SUSPEND_SHA)


MINIMUM_INSTALL_BATTERY = 10

def require_install_battery(battery):
    if not MINIMUM_INSTALL_BATTERY <= battery <= 100:
        raise ValueError(f'Charge to at least {MINIMUM_INSTALL_BATTERY} percent before manual install')


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
        from pm_quiesce_binding import assert_scope as assert_quiesce_scope
        assert_quiesce_scope(kernel_build,build)
        from gic_roundtrip_binding import assert_scope as assert_gic_scope,validate_model as validate_gic
        gic_roundtrip=assert_gic_scope(kernel_build,build)
        if gic_roundtrip!=bool(paired.get('gic_roundtrip_diagnostic')) or gic_roundtrip!=bool(diagnostic.get('gic_roundtrip_diagnostic')):
            raise ValueError('GIC package scope differs from actual Image/config')
        if gic_roundtrip:
            if paired.get('gic_roundtrip_evidence_version')!=1 or diagnostic.get('gic_roundtrip_evidence_version')!=1:
                raise ValueError('GIC package evidence version missing')
            validate_gic(kernel_build,build)
        from dma_pm_binding import assert_scope as assert_dma_scope,validate_model as validate_dma
        dma_pm_audit=assert_dma_scope(kernel_build,build)
        if dma_pm_audit!=bool(paired.get('dma_pm_audit_diagnostic')) or dma_pm_audit!=bool(diagnostic.get('dma_pm_audit_diagnostic')):
            raise ValueError('DMA PM package scope differs from actual Image/config')
        if dma_pm_audit:
            if paired.get('dma_pm_audit_evidence_version')!=1 or diagnostic.get('dma_pm_audit_evidence_version')!=1:
                raise ValueError('DMA PM package evidence version differs')
            validate_dma(kernel_build,build)
        from ufs_pm_binding import assert_scope as assert_ufs_scope,validate_model as validate_ufs
        ufs_pm_audit=assert_ufs_scope(kernel_build,build)
        if ufs_pm_audit!=bool(paired.get('ufs_pm_audit_diagnostic')) or ufs_pm_audit!=bool(diagnostic.get('ufs_pm_audit_diagnostic')):
            raise ValueError('UFS PM package scope differs from actual Image/config')
        if ufs_pm_audit:
            if paired.get('ufs_pm_audit_evidence_version')!=2 or diagnostic.get('ufs_pm_audit_evidence_version')!=2:
                raise ValueError('UFS PM package evidence version differs')
            validate_ufs(kernel_build,build)
        if not (build.get('build_passed') is True and build.get('window_access_diagnostic') is True and
                build.get('window_access_evidence_version')==1 and build.get('reservation_evidence_version')==2):
            raise ValueError('Successful opt-in access kernel build required')
        xnu_stage=paired.get('xnu_payload_stage_diagnostic') is True
        cpu_cache=paired.get('cpu_cache_roundtrip_diagnostic') is True
        pm_timer=paired.get('pm_timer_diagnostic') is True
        pm_quiesce=build.get('pm_quiesce_diagnostic') is True
        if pm_quiesce!=bool(paired.get('pm_quiesce_diagnostic')) or pm_quiesce!=bool(diagnostic.get('pm_quiesce_diagnostic')):
            raise ValueError('PM quiesce package scope differs')
        if pm_quiesce:
            if not pm_timer or paired.get('pm_quiesce_evidence_version')!=1 or diagnostic.get('pm_quiesce_evidence_version')!=1:
                raise ValueError('Invalid PM quiesce package contract')
            from pm_quiesce_binding import validate_model as validate_quiesce
            validate_quiesce(kernel_build,build)
        auto_return=paired.get('auto_return_diagnostic') is True
        if auto_return!=(build.get('auto_return_diagnostic') is True) or auto_return!=(diagnostic.get('auto_return_diagnostic') is True):raise ValueError('Auto-return scope mismatch')
        screen_log=build.get('screen_log_diagnostic') is True
        if screen_log!=bool(paired.get('screen_log_diagnostic')) or screen_log!=bool(diagnostic.get('screen_log_diagnostic')):raise ValueError('Screen log package scope differs')
        if screen_log:
            from prepare_screen_log import validate_model
            validate_model(kernel_build,build)
        if auto_return:
            from inspect_firmware import boot_header
            cycle=paired.get('auto_cycle_token')
            if not pm_timer or not re.fullmatch(r'[0-9a-f]{32}',cycle or '') or diagnostic.get('auto_cycle_token')!=cycle:raise ValueError('Invalid auto-return token')
            with zipfile.ZipFile(packages/diagnostic['file']) as z:header=boot_header(z.read('boot.img'))
            if header['kernel_sha256']!=build['image_sha256']:raise ValueError('Actual BOOT kernel differs from build')
            from materialize_auto_cycle import validate
            validate(kernel_build,cycle)
            if 'n10.cycle=' in header['cmdline']:raise ValueError('Unexpected legacy cycle argument')
            model=json.loads((kernel_build/'auto-return-model/result.json').read_text())
            actual=hashlib.sha256(Path(__file__).with_name('auto_return.c').read_bytes()).hexdigest()
            if model.get('passed') is not True or model.get('cases')!=10 or model.get('source_sha256')!=actual or build.get('auto_return_source_sha256')!=actual:raise ValueError('Auto-return C model/build mismatch')
        if pm_timer!=(build.get('pm_timer_diagnostic') is True) or pm_timer!=(diagnostic.get('pm_timer_diagnostic') is True):
            raise ValueError('PM/timer package and kernel scope differ')
        if pm_timer:
            pm_model=json.loads((kernel_build/'pm-timer-model/result.json').read_text())
            patch_model=json.loads((kernel_build/'pm-source-model.json').read_text())
            here=Path(__file__).resolve().parent
            bindings=(('source_sha256','pm_timer_source_sha256','pm_timer_roundtrip.c'),
                      ('backend_source_sha256','pm_backend_source_sha256','pm_devices_backend.c'),
                      ('contract_sha256','pm_contract_sha256','pm_test_contract.h'))
            if (not cpu_cache or build.get('pm_timer_evidence_version')!=1 or pm_model.get('passed') is not True or
                len(pm_model.get('cases',[]))!=32 or pm_model.get('first_delay_ms')!=30000 or
                build.get('boot_binding_evidence_version')!=1 or pm_model.get('max_pm_attempts')!=3 or pm_model.get('timer_precedes_pm') is not True or patch_model.get('passed') is not True or patch_model.get('cases')!=8 or
                not pm_suspend_patch_bound(build,patch_model) or
                pm_model.get('payload_sha256')!=build.get('xnu_payload_sha256') or
                pm_model.get('payload_size')!=build.get('xnu_payload_size') or
                pm_model.get('cpu_source_sha256')!=build.get('cpu_cache_source_sha256')):
                raise ValueError('PM/timer model or guarded suspend patch differs from kernel')
            for model_key,build_key,filename in bindings:
                if pm_model.get(model_key)!=build.get(build_key) or pm_model.get(model_key)!=hashlib.sha256((here/filename).read_bytes()).hexdigest():
                    raise ValueError('PM/timer actual C source binding mismatch')
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
        if build.get('pm_failure_stage_evidence_version')==1 and b'N10PMS1' not in image:raise ValueError('PM stage marker missing')
        if pm_timer and any(marker not in image for marker in (b'N10PMT1',b'N10TMR1',b'N10BND1',b'N10TRY1')):raise ValueError('PM/timer markers missing')
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
        require_install_battery(battery)
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
                      pm_timer_diagnostic=pm_timer,auto_return_diagnostic=auto_return,
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
