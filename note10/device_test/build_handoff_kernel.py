"""Linux CI build of a pinned public d2x kernel with legacy kexec enabled.

Build feasibility only. No phone access, image packaging or deployment.
Uses the public defconfig, never a private device capture.
"""
import hashlib
import argparse
import json
import os
from pathlib import Path
import struct
import subprocess
import sys
import tarfile
import urllib.request

ROOT = Path(__file__).resolve().parents[2]
COMMIT = '55f042627bb7030c93550faafa117674d32b21d1'
REPOSITORY = 'corsicanu/android_kernel_samsung_universal9820'
OUT = ROOT / 'note10/private/handoff-kernel'


def branch_source_path(out, model):
    """Use the immutable snapshot that actually owns each branch source."""
    paths = {'pmu-source': ('pm-branch-prepared', 'drivers/perf/arm_pmu.c'),
             'gic-source': ('pm-preconditions-prepared', 'drivers/irqchip/irq-gic.c')}
    if model not in paths:
        raise ValueError('Unknown PM branch source model')
    snapshot, name = paths[model]
    source = Path(out) / snapshot / name
    if not source.is_file() or source.is_symlink():
        raise ValueError('PM branch source snapshot missing or unsafe: ' + model)
    return source


def main(caps=False,reserve=False,window_access=False,xnu_payload=None,xnu_manifest=None,cpu_cache=False,pm_timer=False,auto_return=False,screen_log=False,gic_roundtrip=False,dma_pm_audit=False,ufs_pm_audit=False,ehld_lock_audit=False,ehld_irqsave_audit=False,ehld_running_lock_audit=False,cpu_pm_roundtrip=False,cpu_pm_notifier_counts=False,cpu_pm_notifier_trace=False):
    if not sys.platform.startswith('linux'): raise RuntimeError('Linux CI host required')
    if os.environ.get('PLATFORM_VERSION')!='11' or os.environ.get('ANDROID_MAJOR_VERSION')!='r':
        raise ValueError('Pinned Samsung build requires PLATFORM_VERSION=11 and ANDROID_MAJOR_VERSION=r')
    if reserve and not caps:raise ValueError('Reservation diagnostic requires caps/initramfs handling')
    if window_access and not reserve:raise ValueError('Window access requires the same-boot reservation diagnostic')
    if (xnu_payload is None)!=(xnu_manifest is None):raise ValueError('XNU payload and manifest must be paired')
    if xnu_payload is not None and not window_access:raise ValueError('XNU staging requires the opt-in window diagnostic')
    if cpu_cache and xnu_payload is None:raise ValueError('CPU/cache roundtrip requires XNU data staging')
    if screen_log and not auto_return:raise ValueError('Screen log requires automatic recovery')
    if auto_return and not pm_timer:raise ValueError('Auto return requires PM/timer diagnostic')
    if pm_timer and not cpu_cache:raise ValueError('PM/timer requires CPU/cache batch')
    if gic_roundtrip and not auto_return:raise ValueError('GIC roundtrip requires PM and automatic recovery')
    if dma_pm_audit and not gic_roundtrip:raise ValueError('DMA PM audit requires the restored GIC/PM diagnostic')
    if ufs_pm_audit and not dma_pm_audit:raise ValueError('UFS PM audit requires the DMA PM framework audit')
    if ehld_lock_audit and not ufs_pm_audit:raise ValueError('EHLD lock audit requires the full preserved v44 diagnostic bundle')
    if ehld_irqsave_audit and not ehld_lock_audit:raise ValueError('EHLD irqsave audit requires ehld_lock_audit=true')
    if ehld_running_lock_audit and not ehld_irqsave_audit:raise ValueError('EHLD running-lock audit requires ehld_irqsave_audit=true')
    if cpu_pm_roundtrip and (not ehld_running_lock_audit or not auto_return):raise ValueError('CPU_PM roundtrip requires EHLD running-lock audit and auto_return=true')
    if cpu_pm_notifier_counts and not cpu_pm_roundtrip:raise ValueError('CPU_PM notifier counts require cpu_pm_roundtrip=true')
    if cpu_pm_notifier_trace and not cpu_pm_notifier_counts:raise ValueError('CPU_PM notifier trace requires cpu_pm_notifier_counts=true')
    OUT.mkdir(parents=True,exist_ok=True)
    report = {'source_repository':REPOSITORY,'source_commit':COMMIT,
              'platform_version':os.environ['PLATFORM_VERSION'],
              'android_major_version':os.environ['ANDROID_MAJOR_VERSION'],
              'public_defconfig':'exynos9820-d2x_defconfig','build_passed':False,
              'device_operations':[],'deployment_ready':False,'device_boot_tested':False,
              'scope':'Linux shutdown-host build feasibility; not XNU or an installable image',
              'builtin_cpu_diagnostic':caps,
              'ehld_lock_audit':False,
              'ehld_irqsave_audit':False,
              'ehld_running_lock_audit':False,
              'cpu_pm_roundtrip':False,
              'cpu_pm_notifier_counts':False,
              'cpu_pm_notifier_trace':False,
              'auto_return_diagnostic':auto_return,
              'commands':[]}
    def run(arguments, log_name, timeout=120):
        report['commands'].append(arguments)
        print(log_name,flush=True)
        with (OUT/log_name).open('wb') as log:
            result=subprocess.run(arguments,stdout=log,stderr=subprocess.STDOUT,timeout=timeout)
        if result.returncode:raise RuntimeError(log_name+' failed; see saved build diagnostics')
    try:
        archive=OUT/'source.tar.gz'
        url='https://codeload.github.com/'+REPOSITORY+'/tar.gz/'+COMMIT
        print('Fetching pinned public kernel source',flush=True)
        with urllib.request.urlopen(url,timeout=90) as response, archive.open('wb') as target:
            total=0
            while chunk:=response.read(1024*1024):
                total+=len(chunk)
                if total>1536*1024*1024:raise ValueError('Source archive exceeds size cap')
                target.write(chunk)
        digest=hashlib.file_digest(archive.open('rb'),'sha256').hexdigest()
        report['source_archive_sha256']=digest
        parent=OUT/'source';parent.mkdir(exist_ok=True)
        expected='android_kernel_samsung_universal9820-'+COMMIT
        with tarfile.open(archive) as tree:
            members=tree.getmembers()
            if sum(m.size for m in members)>5*1024**3:raise ValueError('Expanded source exceeds size cap')
            for member in members:
                path=Path(member.name)
                if path.is_absolute() or '..' in path.parts or path.parts[0]!=expected:
                    raise ValueError('Unexpected kernel archive path')
            tree.extractall(parent,filter='data')
        source=parent/expected;objects=OUT/'objects'
        # The shipped-blob rule uses an object-relative .incbin path even
        # when make's VPATH found the real binary in the source tree. Prefer
        # that existing source binary, leaving generated .ihex outputs alone.
        firmware_make=source/'firmware/Makefile'
        firmware_text=firmware_make.read_text()
        old='$(call cmd,fwbin,$(patsubst %.gen.S,%,$@))'
        new='$(call cmd,fwbin,$(if $(wildcard $(srctree)/$(patsubst %.gen.S,%,$@)),$(srctree)/$(patsubst %.gen.S,%,$@),$(patsubst %.gen.S,%,$@)))'
        if firmware_text.count(old)!=1:raise ValueError('Unexpected pinned firmware rule')
        firmware_make.write_text(firmware_text.replace(old,new))
        report['firmware_rule_source_path_fix']=True
        report['firmware_makefile_patched_sha256']=hashlib.sha256(firmware_make.read_bytes()).hexdigest()
        if caps:
            import shutil
            # Samsung normal boot can append skip_initramfs. This diagnostic
            # must use the supplied TWRP initrd rather than mount Android root.
            initramfs=source/'init/initramfs.c'
            initramfs_text=initramfs.read_text()
            original_skip='\tdo_skip_initramfs = 1;'
            if initramfs_text.count(original_skip)!=1:
                raise ValueError('Unexpected pinned skip_initramfs parser')
            initramfs.write_text(initramfs_text.replace(original_skip,
                '\tpr_info("N10CAP1: keeping diagnostic initramfs\\n");'))
            report['diagnostic_preserves_external_initramfs']=True
            report['initramfs_patched_sha256']=hashlib.sha256(initramfs.read_bytes()).hexdigest()
            driver=Path(__file__).with_name('linux_caps.c')
            target=source/'drivers/misc/note10_handoff_caps.c'
            if target.exists():raise ValueError('Unexpected existing diagnostic source')
            shutil.copyfile(driver,target)
            with (source/'drivers/misc/Makefile').open('a') as build:
                build.write('\n# Note10 privileged capability diagnostic; no handoff execution\nobj-y += note10_handoff_caps.o\n')
            report['diagnostic_source_sha256']=hashlib.sha256(driver.read_bytes()).hexdigest()
        defconfig=source/'arch/arm64/configs/exynos9820-d2x_defconfig'
        if reserve:
            from prepare_reservation_kernel import prepare
            report.update(prepare(source,OUT,run,window_access=window_access,
                                  xnu_payload=xnu_payload,xnu_manifest=xnu_manifest,cpu_cache=cpu_cache,pm_timer=pm_timer,auto_return=auto_return))
            if window_access:report['scope']='Linux same-boot reserved RAM pattern/readback diagnostic; no XNU branch'
            if xnu_payload is not None:
                report['scope']='Experimental XNU memory-image data staging and SHA256 readback in this boot reservation; no XNU branch'
            if cpu_cache:
                report['scope']='Cached XNU data staging plus Linux CPU offline/online, cache maintenance and per-CPU readback; no DMA/MMU handoff'
        if pm_timer:
            report['scope']='Timer restoration before devices-only PM test, settled boot and bounded EBUSY retries; low-level entry blocked; no XNU branch'
        if screen_log:
            from prepare_screen_log import prepare as prepare_screen
            report.update(prepare_screen(source))
        if pm_timer:
            from prepare_pm_quiesce import prepare as prepare_quiesce
            report.update(prepare_quiesce(source,report if screen_log else None))
            run([sys.executable,str(ROOT/'note10/device_test/test_pm_quiesce_native.py'),
                 '--decon-core',str(source/'drivers/video/fbdev/exynos/dpu20/decon_core.c'),
                 '--output',str(OUT/'pm-quiesce-model')],'03-quiesce-model.log')
            run([sys.executable,str(ROOT/'note10/device_test/test_pm_usb_native.py'),
                 '--usb-helper',str(source/'drivers/usb/notify/note10_pm_usb_quiesce.c'),
                 '--output',str(OUT/'pm-usb-model')],'03-usb-quiesce-model.log')
            report['scope']='Owned normal display/USB quiesce and restore around the unchanged devices-only PM test; no DMA/GIC/MMU handoff or XNU branch'
        report['public_defconfig_sha256']=hashlib.sha256(defconfig.read_bytes()).hexdigest()
        if gic_roundtrip:
            from prepare_gic_roundtrip import prepare as prepare_gic
            report.update(prepare_gic(source))
            report['pm_quiesce_patched_sha256']['kernel/power/Kconfig']=hashlib.sha256((source/'kernel/power/Kconfig').read_bytes()).hexdigest()
            run([sys.executable,str(ROOT/'note10/device_test/test_gic_roundtrip_native.py'),
                 '--output',str(OUT/'gic-roundtrip-model')],'03-gic-roundtrip-model.log')
            report['scope']='Restored PM plus reversible per-CPU GICv2 priority mask test; no distributor writes, IRQ ownership transfer or XNU branch'
        if dma_pm_audit:
            from prepare_dma_pm import prepare as prepare_dma
            report.update(prepare_dma(source))
            report['pm_quiesce_patched_sha256']['kernel/power/Kconfig']=hashlib.sha256((source/'kernel/power/Kconfig').read_bytes()).hexdigest()
            report['patched_suspend_sha256']=hashlib.sha256((source/'kernel/power/suspend.c').read_bytes()).hexdigest()
            run([sys.executable,str(ROOT/'note10/device_test/test_dma_pm_native.py'),
                 '--output',str(OUT/'dma-pm-model')],'03-dma-pm-model.log')
            report['scope']='Read-only DMA-capable device PM framework snapshots plus restored GIC/PM tests; no hardware DMA-idle or XNU branch claim'
        if ufs_pm_audit:
            from prepare_ufs_pm import prepare as prepare_ufs
            report.update(prepare_ufs(source))
            report['pm_quiesce_patched_sha256']['kernel/power/Kconfig']=hashlib.sha256((source/'kernel/power/Kconfig').read_bytes()).hexdigest()
            run([sys.executable,str(ROOT/'note10/device_test/test_ufs_pm_native.py'),
                 '--dma-helper',str(source/'drivers/base/power/note10_dma_pm.c'),
                 '--output',str(OUT/'ufs-pm-model')],'03-ufs-pm-model.log')
            from prepare_iommu_pm import prepare as prepare_iommu
            report.update(prepare_iommu(source))
            report['pm_quiesce_patched_sha256']['kernel/power/Kconfig']=hashlib.sha256((source/'kernel/power/Kconfig').read_bytes()).hexdigest()
            run([sys.executable,str(ROOT/'note10/device_test/test_iommu_pm_native.py'),'--header',str(source/'drivers/iommu/exynos-iommu.h'),
                 '--dma-helper',str(source/'drivers/base/power/note10_dma_pm.c'),'--output',str(OUT/'iommu-pm-model')],'03-iommu-pm-model.log')
            from prepare_abox_pm import prepare as prepare_abox
            report.update(prepare_abox(source))
            report['pm_quiesce_patched_sha256']['kernel/power/Kconfig']=hashlib.sha256((source/'kernel/power/Kconfig').read_bytes()).hexdigest()
            run([sys.executable,str(ROOT/'note10/device_test/test_abox_pm_native.py'),'--driver',str(source/'sound/soc/samsung/abox/abox.c'),
                 '--dma-helper',str(source/'drivers/base/power/note10_dma_pm.c'),'--output',str(OUT/'abox-pm-model')],'03-abox-pm-model.log')
            from prepare_abox_pmu import prepare as prepare_pmu
            report.update(prepare_pmu(source))
            report['pm_quiesce_patched_sha256']['kernel/power/Kconfig']=hashlib.sha256((source/'kernel/power/Kconfig').read_bytes()).hexdigest()
            run([sys.executable,str(ROOT/'note10/device_test/test_abox_pmu_native.py'),'--core-driver',str(source/'sound/soc/samsung/abox/abox_core.c'),
                 '--pmu-source',str(source/'drivers/soc/samsung/exynos-pmu.c'),'--dma-helper',str(source/'drivers/base/power/note10_dma_pm.c'),
                 '--domain-source',str(source/'drivers/soc/samsung/cal-if/exynos9820/flexpmu_cal_local_exynos9820.h'),'--pd-driver',str(source/'drivers/soc/samsung/exynos-pd.c'),'--otg-source',str(source/'drivers/usb/dwc3/otg.c'),'--output',str(OUT/'abox-pmu-model')],'03-abox-pmu-model.log')
            from prepare_pm_noirq import prepare as prepare_noirq
            report.update(prepare_noirq(source))
            run([sys.executable,str(ROOT/'note10/device_test/test_pm_noirq_native.py'),
                 '--suspend-source',str(source/'kernel/power/suspend.c'),'--raw-suspend',str(source/'kernel/power/suspend-upstream.c'),
                 '--header',str(source/'include/linux/suspend.h'),'--core-driver',str(source/'sound/soc/samsung/abox/abox_core.c'),
                 '--pmu-source',str(source/'drivers/soc/samsung/exynos-pmu.c'),
                 '--domain-source',str(source/'drivers/soc/samsung/cal-if/exynos9820/flexpmu_cal_local_exynos9820.h'),
                 '--output',str(OUT/'pm-noirq-model')],'03-pm-noirq-model.log')
            from prepare_pmu_settle import prepare as prepare_settle
            report.update(prepare_settle(source))
            run([sys.executable,str(ROOT/'note10/device_test/test_pmu_settle_native.py'),
                 '--core-driver',str(source/'sound/soc/samsung/abox/abox_core.c'),
                 '--pmu-source',str(source/'drivers/soc/samsung/exynos-pmu.c'),
                 '--domain-source',str(source/'drivers/soc/samsung/cal-if/exynos9820/flexpmu_cal_local_exynos9820.h'),
                 '--output',str(OUT/'pmu-settle-model')],'03-pmu-settle-model.log')
            from prepare_pm_cpus import prepare as prepare_cpus
            report.update(prepare_cpus(source))
            report['pm_quiesce_patched_sha256']['kernel/power/Kconfig']=hashlib.sha256((source/'kernel/power/Kconfig').read_bytes()).hexdigest()
            run([sys.executable,str(ROOT/'note10/device_test/test_pm_cpus_native.py'),
                 '--suspend-source',str(source/'kernel/power/suspend.c'),'--raw-suspend',str(source/'kernel/power/suspend-upstream.c'),
                 '--header',str(source/'include/linux/suspend.h'),'--cpu-source',str(source/'kernel/cpu.c'),'--cpu-header',str(source/'include/linux/cpu.h'),
                 '--core-driver',str(source/'sound/soc/samsung/abox/abox_core.c'),'--pmu-source',str(source/'drivers/soc/samsung/exynos-pmu.c'),
                 '--domain-source',str(source/'drivers/soc/samsung/cal-if/exynos9820/flexpmu_cal_local_exynos9820.h'),
                 '--output',str(OUT/'pm-cpus-model')],'03-pm-cpus-model.log')
            from prepare_pm_post_arch import prepare as prepare_post_arch
            report.update(prepare_post_arch(source))
            report['pm_quiesce_patched_sha256']['kernel/power/Kconfig']=hashlib.sha256((source/'kernel/power/Kconfig').read_bytes()).hexdigest()
            run([sys.executable,str(ROOT/'note10/device_test/test_pm_post_arch_native.py'),'--worker',str(source/'arch/arm64/mm/note10_pm_timer_roundtrip.c'),'--output',str(OUT/'pm-post-arch-model')],'03-pm-post-arch-model.log')
            from prepare_pm_edge import prepare as prepare_edge
            report.update(prepare_edge(source))
            report['pm_quiesce_patched_sha256']['kernel/power/Kconfig']=hashlib.sha256((source/'kernel/power/Kconfig').read_bytes()).hexdigest()
            run([sys.executable,str(ROOT/'note10/device_test/test_pm_edge_dma_native.py'),'--output',str(OUT/'pm-edge-dma-model')],'03-pm-edge-dma-model.log')
            run([sys.executable,str(ROOT/'note10/device_test/test_pm_edge_iommu_native.py'),'--header',str(source/'drivers/iommu/exynos-iommu.h'),'--output',str(OUT/'pm-edge-iommu-model')],'03-pm-edge-iommu-model.log')
            run([sys.executable,str(ROOT/'note10/device_test/test_pm_edge_syscore_native.py'),'--output',str(OUT/'pm-edge-syscore-model')],'03-pm-edge-syscore-model.log')
            run([sys.executable,str(ROOT/'note10/device_test/test_pm_edge_integration_native.py'),'--source-root',str(source),'--raw-suspend',str(source/'kernel/power/suspend-upstream.c'),'--header',str(source/'include/linux/suspend.h'),'--output',str(OUT/'pm-edge-integration-model')],'03-pm-edge-integration-model.log')
            run([sys.executable,str(ROOT/'note10/device_test/test_pm_edge_decoder.py'),'--producer-dir',str(OUT/'pm-edge-integration-model'),'--output',str(OUT/'pm-edge-decoder-model')],'03-pm-edge-decoder-model.log')
            run([sys.executable,str(ROOT/'note10/device_test/test_pm_edge_binding.py'),'--output',str(OUT/'pm-edge-binding-model')],'03-pm-edge-binding-model.log')
            from prepare_pm_irq import prepare as prepare_irq
            report.update(prepare_irq(source))
            report['pm_quiesce_patched_sha256']['kernel/power/Kconfig']=hashlib.sha256((source/'kernel/power/Kconfig').read_bytes()).hexdigest()
            run([sys.executable,str(ROOT/'note10/device_test/test_pm_irq_native.py'),'--output',str(OUT/'pm-irq-native-model')],'03-pm-irq-native-model.log')
            run([sys.executable,str(ROOT/'note10/device_test/test_pm_irq_decoder.py'),'--native',str(OUT/'pm-irq-native-model'),'--output',str(OUT/'pm-irq-decoder-model')],'03-pm-irq-decoder-model.log')
            run([sys.executable,str(ROOT/'note10/device_test/test_pm_irq_integration_native.py'),'--source-root',str(source),'--output',str(OUT/'pm-irq-integration-model')],'03-pm-irq-integration-model.log')
            run([sys.executable,str(ROOT/'note10/device_test/test_pm_irq_binding.py'),'--edge-artifact',str(OUT),'--source-root',str(source),'--native',str(OUT/'pm-irq-native-model'),'--decoder',str(OUT/'pm-irq-decoder-model'),'--integration',str(OUT/'pm-irq-integration-model'),'--output',str(OUT/'pm-irq-binding-model')],'03-pm-irq-binding-model.log')
            from prepare_pm_callbacks import prepare as prepare_callbacks, snapshot_prepared as snapshot_callbacks
            report.update(prepare_callbacks(source))
            snapshot_callbacks(source,OUT/'pm-callbacks-prepared',report['pm_callbacks_prepared_sha256'])
            (OUT/'pm-callbacks-prepared-binding.json').write_text(json.dumps({'final':report['pm_callbacks_prepared_sha256'],'intermediate':report['pm_callbacks_intermediate_sha256']},indent=2)+'\n',encoding='utf-8')
            from prepare_pm_preconditions import prepare as prepare_preconditions, snapshot as snapshot_preconditions
            from pm_preconditions_binding import SOURCES as precondition_sources
            report.update(prepare_preconditions(source,report))
            report['pm_preconditions_sources_sha256']={n:hashlib.sha256((ROOT/'note10/device_test'/n).read_bytes()).hexdigest() for n in precondition_sources}
            snapshot_preconditions(source,OUT/'pm-preconditions-prepared',report['pm_preconditions_prepared_sha256'])
            from prepare_pm_branch import prepare as prepare_branch, snapshot as snapshot_branch
            from pm_branch_binding import SOURCES as branch_sources
            report.update(prepare_branch(source,report))
            report['pm_branch_sources_sha256']={n:hashlib.sha256((ROOT/'note10/device_test'/n).read_bytes()).hexdigest() for n in branch_sources}
            snapshot_branch(source,OUT/'pm-branch-prepared',report['pm_branch_prepared_sha256'])
            from prepare_pmu_failure_restore import prepare as prepare_failure, snapshot as snapshot_failure
            from pmu_failure_binding import SOURCES as failure_sources, PACKAGE_SOURCES as failure_package_sources
            report.update(prepare_failure(source,report))
            report['pmu_failure_sources_sha256']={n:hashlib.sha256((ROOT/'note10/device_test'/n).read_bytes()).hexdigest() for n in failure_sources}
            report['pmu_failure_package_sources_sha256']={n:hashlib.sha256((ROOT/'note10/device_test'/n).read_bytes()).hexdigest() for n in failure_package_sources}
            report['pmu_failure_snapshot_sha256']=snapshot_failure(source,OUT/'pmu-failure-prepared',report)
            from prepare_gic_priority_restore import prepare as prepare_priority, snapshot as snapshot_priority
            from gic_priority_binding import SOURCES as priority_sources, PACKAGE_SOURCES as priority_package_sources
            report.update(prepare_priority(source,report))
            report['gic_priority_sources_sha256']={n:hashlib.sha256((ROOT/'note10/device_test'/n).read_bytes()).hexdigest() for n in priority_sources}
            report['gic_priority_package_sources_sha256']={n:hashlib.sha256((ROOT/'note10/device_test'/n).read_bytes()).hexdigest() for n in priority_package_sources}
            report['gic_priority_snapshot_sha256']=snapshot_priority(source,OUT/'gic-priority-prepared',report)
            from prepare_pmu_state_audit import prepare as prepare_state, snapshot as snapshot_state
            from pmu_state_binding import SOURCES as state_sources, PACKAGE_SOURCES as state_package_sources
            report.update(prepare_state(source,report))
            report['pmu_state_sources_sha256']={n:hashlib.sha256((ROOT/'note10/device_test'/n).read_bytes()).hexdigest() for n in state_sources}
            from pmu_state_binding import COLLECTOR_DEPENDENCIES as state_collector_dependencies
            report['pmu_state_collector_dependencies_sha256']={n:hashlib.sha256((ROOT/'note10/device_test'/n).read_bytes()).hexdigest() for n in state_collector_dependencies}
            report['pmu_state_package_sources_sha256']={n:hashlib.sha256((ROOT/'note10/device_test'/n).read_bytes()).hexdigest() for n in state_package_sources}
            report['pmu_state_snapshot_sha256']=snapshot_state(source,OUT/'pmu-state-prepared',report)
            from prepare_pmu_control_audit import prepare as prepare_control, snapshot as snapshot_control
            from pmu_control_binding import SOURCES as control_sources, PACKAGE_SOURCES as control_package_sources, COLLECTOR_DEPENDENCIES as control_collector_dependencies
            report.update(prepare_control(source,report))
            report['pmu_control_sources_sha256']={n:hashlib.sha256((ROOT/'note10/device_test'/n).read_bytes()).hexdigest() for n in control_sources}
            report['pmu_control_package_sources_sha256']={n:hashlib.sha256((ROOT/'note10/device_test'/n).read_bytes()).hexdigest() for n in control_package_sources}
            report['pmu_control_collector_dependencies_sha256']={n:hashlib.sha256((ROOT/'note10/device_test'/n).read_bytes()).hexdigest() for n in control_collector_dependencies}
            report['pmu_control_snapshot_sha256']=snapshot_control(source,OUT/'pmu-control-prepared',report)
            from prepare_fpsimd_reference_audit import prepare as prepare_fpsimd, snapshot as snapshot_fpsimd
            from fpsimd_reference_binding import SOURCES as fpsimd_sources, PACKAGE_SOURCES as fpsimd_package_sources, COLLECTOR_DEPENDENCIES as fpsimd_collector_dependencies
            report.update(prepare_fpsimd(source,report))
            report['fpsimd_reference_sources_sha256']={n:hashlib.sha256((ROOT/'note10/device_test'/n).read_bytes()).hexdigest() for n in fpsimd_sources}
            report['fpsimd_reference_package_sources_sha256']={n:hashlib.sha256((ROOT/'note10/device_test'/n).read_bytes()).hexdigest() for n in fpsimd_package_sources}
            report['fpsimd_reference_collector_dependencies_sha256']={n:hashlib.sha256((ROOT/'note10/device_test'/n).read_bytes()).hexdigest() for n in fpsimd_collector_dependencies}
            report['fpsimd_reference_snapshot_sha256']=snapshot_fpsimd(source,OUT/'fpsimd-reference-prepared',report)
            from prepare_rcu_context_audit import prepare as prepare_rcu, snapshot as snapshot_rcu
            from rcu_context_binding import SOURCES as rcu_sources, PACKAGE_SOURCES as rcu_package_sources, COLLECTOR_DEPENDENCIES as rcu_collector_dependencies
            report.update(prepare_rcu(source,report))
            report['rcu_context_sources_sha256']={n:hashlib.sha256((ROOT/'note10/device_test'/n).read_bytes()).hexdigest() for n in rcu_sources}
            report['rcu_context_package_sources_sha256']={n:hashlib.sha256((ROOT/'note10/device_test'/n).read_bytes()).hexdigest() for n in rcu_package_sources}
            report['rcu_context_collector_dependencies_sha256']={n:hashlib.sha256((ROOT/'note10/device_test'/n).read_bytes()).hexdigest() for n in rcu_collector_dependencies}
            report['rcu_context_snapshot_sha256']=snapshot_rcu(source,OUT/'rcu-context-prepared',report)
            if ehld_lock_audit:
                from prepare_ehld_lock_audit import prepare as prepare_ehld,snapshot as snapshot_ehld
                from ehld_lock_binding import SOURCES as ehld_sources,PACKAGE_SOURCES as ehld_packages,COLLECTOR_DEPENDENCIES as ehld_collector
                from ehld_lock_profile import snapshot_profile
                report.update(prepare_ehld(source,report));report['ehld_lock_audit']=True
                report['ehld_lock_sources_sha256']={n:hashlib.sha256((ROOT/'note10/device_test'/n).read_bytes()).hexdigest() for n in ehld_sources}
                report['ehld_lock_package_sources_sha256']={n:hashlib.sha256((ROOT/'note10/device_test'/n).read_bytes()).hexdigest() for n in ehld_packages}
                report['ehld_lock_collector_dependencies_sha256']={n:hashlib.sha256((ROOT/'note10/device_test'/n).read_bytes()).hexdigest() for n in ehld_collector}
                report['ehld_lock_profile_inputs_sha256']=snapshot_profile(source,OUT/'ehld-lock-profile-inputs')
                report['ehld_lock_snapshot_sha256']=snapshot_ehld(source,OUT/'ehld-lock-prepared',report)
                prior=OUT/'ehld-lock-v44-composition-input.json'
                prior.write_text(json.dumps({'snapshot_sha256':report['rcu_context_snapshot_sha256']},indent=2)+'\n',encoding='utf-8',newline='\n')
                run([sys.executable,str(ROOT/'note10/device_test/test_ehld_lock_composition.py'),'--v44-source',str(OUT/'rcu-context-prepared'),'--v44-composition',str(prior),'--output',str(OUT/'ehld-lock-composition-model')],'03-ehld-lock-composition.log')
            if ehld_irqsave_audit:
                from prepare_ehld_irqsave_audit import prepare as prepare_irqsave,snapshot as snapshot_irqsave
                from ehld_irqsave_binding import SOURCES as irqsave_sources,PACKAGE_SOURCES as irqsave_packages
                report.update(prepare_irqsave(source,True,report['ehld_lock_snapshot_sha256']))
                report['ehld_irqsave_audit']=True
                report['ehld_irqsave_sources_sha256']={n:hashlib.sha256((ROOT/'note10/device_test'/n).read_bytes()).hexdigest() for n in irqsave_sources}
                report['ehld_irqsave_package_sources_sha256']={n:hashlib.sha256((ROOT/'note10/device_test'/n).read_bytes()).hexdigest() for n in irqsave_packages}
                report['ehld_irqsave_snapshot_sha256']=snapshot_irqsave(source,OUT/'ehld-irqsave-prepared',report['ehld_lock_snapshot_sha256'])
                run([sys.executable,str(ROOT/'note10/device_test/test_ehld_irqsave_audit.py'),'--source-root',str(OUT/'ehld-irqsave-prepared'),'--baseline-source',str(OUT/'ehld-lock-prepared'),'--output',str(OUT/'ehld-irqsave-model'),'--cc','clang-14'],'03-ehld-irqsave-model.log')
                report['ehld_irqsave_model_sha256']=hashlib.sha256((OUT/'ehld-irqsave-model/result.json').read_bytes()).hexdigest()
            if ehld_running_lock_audit:
                from prepare_ehld_running_lock_audit import prepare as prepare_running_lock,snapshot as snapshot_running_lock
                from ehld_running_lock_binding import SOURCES as running_sources,PACKAGE_SOURCES as running_packages
                running_baseline=report['ehld_irqsave_snapshot_sha256']
                report.update(prepare_running_lock(source,True,running_baseline))
                report['ehld_running_lock_audit']=True
                report['ehld_running_lock_sources_sha256']={n:hashlib.sha256((ROOT/'note10/device_test'/n).read_bytes()).hexdigest() for n in running_sources}
                report['ehld_running_lock_package_sources_sha256']={n:hashlib.sha256((ROOT/'note10/device_test'/n).read_bytes()).hexdigest() for n in running_packages}
                report['ehld_running_lock_snapshot_sha256']=snapshot_running_lock(source,OUT/'ehld-running-lock-prepared',running_baseline)
                run([sys.executable,str(ROOT/'note10/device_test/test_ehld_running_lock_audit.py'),'--source-root',str(OUT/'ehld-running-lock-prepared'),'--baseline-source',str(OUT/'ehld-irqsave-prepared'),'--output',str(OUT/'ehld-running-lock-model'),'--cc','clang-14'],'03-ehld-running-lock-model.log')
                report['ehld_running_lock_model_sha256']=hashlib.sha256((OUT/'ehld-running-lock-model/result.json').read_bytes()).hexdigest()
            if cpu_pm_roundtrip:
                from prepare_cpu_pm_roundtrip import prepare as prepare_roundtrip,snapshot as snapshot_roundtrip
                from cpu_pm_roundtrip_binding import SOURCES as roundtrip_sources,PACKAGE_SOURCES as roundtrip_packages
                roundtrip_baseline=report['ehld_running_lock_snapshot_sha256']
                report.update(prepare_roundtrip(source,True,roundtrip_baseline))
                report['cpu_pm_roundtrip']=True
                report['cpu_pm_roundtrip_sources_sha256']={n:hashlib.sha256((ROOT/'note10/device_test'/n).read_bytes()).hexdigest() for n in roundtrip_sources}
                report['cpu_pm_roundtrip_package_sources_sha256']={n:hashlib.sha256((ROOT/'note10/device_test'/n).read_bytes()).hexdigest() for n in roundtrip_packages}
                report['cpu_pm_roundtrip_snapshot_sha256']=snapshot_roundtrip(source,OUT/'cpu-pm-roundtrip-prepared',roundtrip_baseline)
                run([sys.executable,str(ROOT/'note10/device_test/test_cpu_pm_roundtrip.py'),'--source-root',str(OUT/'cpu-pm-roundtrip-prepared'),'--baseline-source',str(OUT/'ehld-running-lock-prepared'),'--output',str(OUT/'cpu-pm-roundtrip-model'),'--cc','clang-14'],'03-cpu-pm-roundtrip-model.log')
                report['cpu_pm_roundtrip_model_sha256']=hashlib.sha256((OUT/'cpu-pm-roundtrip-model/result.json').read_bytes()).hexdigest()
                if cpu_pm_notifier_counts:
                    run([sys.executable,str(ROOT/'note10/device_test/test_cpu_pm_notifier_counts.py'),
                         '--baseline-source',str(OUT/'ehld-running-lock-prepared'),
                         '--output',str(OUT/'cpu-pm-notifier-counts-model'),'--cc','clang-14'],
                        '03-cpu-pm-notifier-counts.log')
                    report['cpu_pm_notifier_counts']=True
                    report['cpu_pm_notifier_counts_version']=1
                    report['cpu_pm_notifier_counts_sources_sha256']={n:hashlib.sha256((ROOT/'note10/device_test'/n).read_bytes()).hexdigest() for n in roundtrip_sources}
                    report['cpu_pm_notifier_counts_model_sha256']=hashlib.sha256((OUT/'cpu-pm-notifier-counts-model/result.json').read_bytes()).hexdigest()
            if cpu_pm_notifier_trace:
                from prepare_cpu_pm_notifier_trace import prepare as prepare_trace,SOURCES as trace_sources
                report.update(prepare_trace(source,OUT))
                report['cpu_pm_notifier_trace_sources_sha256']={n:hashlib.sha256((ROOT/'note10/device_test'/n).read_bytes()).hexdigest() for n in trace_sources}
                run([sys.executable,str(ROOT/'note10/device_test/test_cpu_pm_notifier_trace.py'),'--artifact',str(OUT),'--output',str(OUT/'cpu-pm-notifier-trace-model'),'--cc','clang-14'],'03-cpu-pm-notifier-trace.log')
                report['cpu_pm_notifier_trace_model_sha256']=hashlib.sha256((OUT/'cpu-pm-notifier-trace-model/result.json').read_bytes()).hexdigest()
            report['pm_quiesce_patched_sha256']['kernel/power/Kconfig']=report['pm_callbacks_prepared_sha256']['kernel/power/Kconfig']
            report['scope']='Bundled PM, CPU architecture and payload observations; no global DMA shutdown or XNU execution claim'
        make=['make','-C',str(source),'O='+str(objects),'ARCH=arm64',
              'CC=clang-14','CROSS_COMPILE=aarch64-linux-gnu-',
              'CLANG_TRIPLE=aarch64-linux-gnu-','CROSS_COMPILE_ARM32=arm-linux-gnueabi-',
              # This older Makefile derives --prefix from elfedit's directory.
              # Debian keeps prefixed tools in /usr/bin and unprefixed cross
              # aliases here; using /usr/bin would select the x86 assembler.
              'GCC_TOOLCHAIN_DIR=/usr/aarch64-linux-gnu/bin/',
              # Avoid DWARF5 forms unsupported by this source's objdump-based
              # scripts. Do not disable -Werror globally: cc-option probes
              # must reject unsupported compiler switches correctly.
              'HOSTCC=gcc','HOSTCFLAGS=-Wno-error=deprecated-declarations','KCFLAGS=-gdwarf-4']
        run([*make,'exynos9820-d2x_defconfig'],'01-configure.log')
        config=objects/'.config'
        original=config.read_bytes();(OUT/'public-baseline.config').write_bytes(original)
        run([str(source/'scripts/config'),'--file',str(config),'--enable','KEXEC',
             '--set-str','LOCALVERSION','-note10-reserve-pc' if reserve else '-note10-handoff-pc','--disable','LOCALVERSION_AUTO'],
            '02-enable-kexec.log')
        if reserve:
            run([str(source/'scripts/config'),'--file',str(config),'--set-str','INITRAMFS_SOURCE',
                 str(OUT/'initramfs.cpio'),'--set-str','CMDLINE','rdinit=/init',
                 '--disable','CMDLINE_FROM_BOOTLOADER','--disable','CMDLINE_FORCE',
                 '--enable','CMDLINE_EXTEND','--enable','INITRAMFS_FORCE'],'02-initramfs.log')
        if screen_log:run([str(source/'scripts/config'),'--file',str(config),'--enable','NOTE10_SCREEN_LOG'],'02-screen-log.log')
        if pm_timer:run([str(source/'scripts/config'),'--file',str(config),'--enable','NOTE10_PM_QUIESCE'],'02-pm-quiesce.log')
        if gic_roundtrip:run([str(source/'scripts/config'),'--file',str(config),'--enable','NOTE10_GIC_ROUNDTRIP'],'02-gic-roundtrip.log')
        if dma_pm_audit:run([str(source/'scripts/config'),'--file',str(config),'--enable','NOTE10_DMA_PM_AUDIT'],'02-dma-pm-audit.log')
        if ufs_pm_audit:run([str(source/'scripts/config'),'--file',str(config),'--enable','NOTE10_UFS_PM_AUDIT','--enable','NOTE10_IOMMU_PM_AUDIT','--enable','NOTE10_ABOX_PM_AUDIT','--enable','NOTE10_ABOX_FW_FAILURE_GUARD','--enable','NOTE10_ABOX_PMU_AUDIT','--enable','NOTE10_PM_NOIRQ_TEST','--enable','NOTE10_PMU_SETTLE','--enable','NOTE10_PM_CPUS_TEST','--enable','NOTE10_PM_POST_ARCH','--enable','NOTE10_PM_EDGE_INVENTORY','--enable','NOTE10_PM_IRQ_TEST','--enable','NOTE10_PM_CALLBACK_INVENTORY','--enable','NOTE10_CPU_PM_FAILURE_GUARD','--enable','NOTE10_CPU_PM_PRECONDITIONS','--enable','NOTE10_CPU_PM_BRANCH_AUDIT','--enable','NOTE10_PMU_FAILURE_RESTORE','--enable','NOTE10_GIC_PRIORITY_RESTORE','--enable','NOTE10_PMU_STATE_AUDIT','--enable','NOTE10_PMU_CONTROL_AUDIT','--enable','NOTE10_FPSIMD_REFERENCE_AUDIT','--enable','NOTE10_RCU_CONTEXT_AUDIT','--set-val','LOG_BUF_SHIFT','21'],'02-ufs-pm-audit.log')
        if ehld_lock_audit:
            run([str(source/'scripts/config'),'--file',str(config),'--enable','NOTE10_EHLD_LOCK_AUDIT'],'02-ehld-lock-audit.log')
            from ehld_lock_profile import apply_profile
            report['ehld_lock_profile_source_sha256']=apply_profile(source,config,run)
        if ehld_irqsave_audit:
            run([str(source/'scripts/config'),'--file',str(config),'--enable','NOTE10_EHLD_IRQSAVE_AUDIT'],'02-ehld-irqsave-audit.log')
        if ehld_running_lock_audit:
            run([str(source/'scripts/config'),'--file',str(config),'--enable','NOTE10_EHLD_RUNNING_LOCK_AUDIT'],'02-ehld-running-lock-audit.log')
        if cpu_pm_roundtrip:run([str(source/'scripts/config'),'--file',str(config),'--enable','NOTE10_CPU_PM_ROUNDTRIP'],'02-cpu-pm-roundtrip.log')
        if cpu_pm_notifier_counts:run([str(source/'scripts/config'),'--file',str(config),'--enable','NOTE10_CPU_PM_NOTIFIER_COUNTS'],'02-cpu-pm-notifier-counts.log')
        if cpu_pm_notifier_trace:run([str(source/'scripts/config'),'--file',str(config),'--enable','NOTE10_CPU_PM_NOTIFIER_TRACE'],'02-cpu-pm-notifier-trace.log')
        run([*make,'olddefconfig'],'03-olddefconfig.log')
        configured=config.read_text()
        required=('CONFIG_KEXEC=y','CONFIG_KEXEC_CORE=y','CONFIG_PM_SLEEP_SMP=y','CONFIG_ARM64_4K_PAGES=y')
        (OUT/'handoff.config').write_bytes(config.read_bytes())
        if gic_roundtrip:required+=('CONFIG_NOTE10_GIC_ROUNDTRIP=y','CONFIG_ARM_GIC=y')
        if dma_pm_audit:required+=('CONFIG_NOTE10_DMA_PM_AUDIT=y',)
        if ufs_pm_audit:required+=('CONFIG_NOTE10_UFS_PM_AUDIT=y','CONFIG_SCSI_UFSHCD=y','CONFIG_SCSI_UFS_EXYNOS=y','CONFIG_NOTE10_IOMMU_PM_AUDIT=y','CONFIG_EXYNOS_IOMMU=y','CONFIG_NOTE10_ABOX_PM_AUDIT=y','CONFIG_NOTE10_ABOX_FW_FAILURE_GUARD=y','CONFIG_SND_SOC_SAMSUNG_ABOX=y','CONFIG_NOTE10_ABOX_PMU_AUDIT=y','CONFIG_EXYNOS_PMU=y','CONFIG_SOC_EXYNOS9820=y','CONFIG_EXYNOS_PM_DOMAINS=y','CONFIG_USB_DWC3_EXYNOS=y','CONFIG_NOTE10_PM_NOIRQ_TEST=y','CONFIG_NOTE10_PMU_SETTLE=y','CONFIG_NOTE10_PM_CPUS_TEST=y')
        if ufs_pm_audit:required+=('CONFIG_NOTE10_PM_POST_ARCH=y','CONFIG_NOTE10_PM_EDGE_INVENTORY=y','CONFIG_NOTE10_PM_IRQ_TEST=y','CONFIG_NOTE10_PM_CALLBACK_INVENTORY=y','CONFIG_NOTE10_CPU_PM_FAILURE_GUARD=y','CONFIG_NOTE10_CPU_PM_PRECONDITIONS=y','CONFIG_NOTE10_CPU_PM_BRANCH_AUDIT=y','CONFIG_NOTE10_PMU_FAILURE_RESTORE=y','CONFIG_NOTE10_GIC_PRIORITY_RESTORE=y','CONFIG_NOTE10_PMU_STATE_AUDIT=y','CONFIG_NOTE10_PMU_CONTROL_AUDIT=y','CONFIG_NOTE10_FPSIMD_REFERENCE_AUDIT=y','CONFIG_NOTE10_RCU_CONTEXT_AUDIT=y','CONFIG_PREEMPT_RCU=y','CONFIG_ARM_GIC_MAX_NR=1','CONFIG_LOG_BUF_SHIFT=21','CONFIG_PREEMPT_COUNT=y','CONFIG_KALLSYMS=y')
        if ehld_lock_audit:required+=('CONFIG_NOTE10_EHLD_LOCK_AUDIT=y','CONFIG_EXYNOS_EHLD=y','CONFIG_PREEMPT_COUNT=y')
        if ehld_irqsave_audit:required+=('CONFIG_NOTE10_EHLD_IRQSAVE_AUDIT=y','CONFIG_NOTE10_EHLD_LOCK_AUDIT=y')
        if ehld_running_lock_audit:required+=('CONFIG_NOTE10_EHLD_RUNNING_LOCK_AUDIT=y','CONFIG_NOTE10_EHLD_IRQSAVE_AUDIT=y','CONFIG_NOTE10_EHLD_LOCK_AUDIT=y')
        if cpu_pm_roundtrip:required+=('CONFIG_NOTE10_CPU_PM_ROUNDTRIP=y','CONFIG_NOTE10_EHLD_RUNNING_LOCK_AUDIT=y','CONFIG_NOTE10_PM_IRQ_TEST=y','CONFIG_NOTE10_CPU_PM_PRECONDITIONS=y')
        if cpu_pm_notifier_counts:required+=('CONFIG_NOTE10_CPU_PM_NOTIFIER_COUNTS=y',)
        if cpu_pm_notifier_trace:required+=('CONFIG_NOTE10_CPU_PM_NOTIFIER_TRACE=y',)
        if reserve:required+=('CONFIG_INITRAMFS_FORCE=y','CONFIG_CMDLINE_EXTEND=y','CONFIG_CMDLINE="rdinit=/init"')
        if xnu_payload is not None:required+=('CONFIG_CRYPTO=y','CONFIG_CRYPTO_HASH=y','CONFIG_CRYPTO_SHA256=y')
        if cpu_cache:required+=('CONFIG_HOTPLUG_CPU=y','CONFIG_SMP=y','CONFIG_PM_SLEEP_SMP=y')
        if screen_log:required+=('CONFIG_NOTE10_SCREEN_LOG=y','CONFIG_EXYNOS_WINDOW_UPDATE=y','CONFIG_EXYNOS_DPU20=y')
        if auto_return:required+=('CONFIG_EXYNOS_REBOOT=y','CONFIG_SEC_REBOOT=y')
        if pm_timer:required+=('CONFIG_SUSPEND=y','CONFIG_PM_SLEEP_DEBUG=y','CONFIG_PM_DEBUG=y')
        if pm_timer:required+=('CONFIG_NOTE10_PM_QUIESCE=y','CONFIG_USB_NOTIFY_LAYER=y','CONFIG_USB_NOTIFIER=y','CONFIG_USB_DWC3=y','CONFIG_USB_DWC3_EXYNOS=y')
        missing=[line for line in required if line not in configured.splitlines()]
        if missing:raise ValueError('Required Kconfig options missing: '+', '.join(missing))
        if ehld_lock_audit:
            from ehld_lock_profile import verify_config
            report['ehld_lock_profile_result']=verify_config(config.read_bytes())
            run([sys.executable,str(ROOT/'note10/device_test/test_ehld_lock_profile.py'),'--source',str(source),'--output',str(OUT/'ehld-lock-profile-model')],'03-ehld-lock-profile.log')
        if ufs_pm_audit and 'CONFIG_GIC_NON_BANKED=y' in configured.splitlines():raise ValueError('GIC priority guard requires banked GIC')
        report['effective_config_sha256']=hashlib.sha256(config.read_bytes()).hexdigest()
        if caps:run([*make,'drivers/misc/note10_handoff_caps.o'],'04-caps-object.log')
        if reserve:run([*make,'arch/arm64/mm/init.o'],'04-reservation-object.log')
        if pm_timer:
            targets=['kernel/power/suspend.o','drivers/usb/notify/usb_notify.o',
                     'drivers/usb/notify/usb_notifier.o','drivers/usb/dwc3/otg.o',
                     'drivers/usb/dwc3/dwc3-exynos.o']
            run([*make,'-j2',*targets],'04-quiesce-objects.log')
            # The parent Makefile owns ./cal_9820/*.o; that subdirectory has
            # no Makefile and cannot be invoked as a standalone Kbuild target.
            run([*make,'-j2','drivers/video/fbdev/exynos/dpu20/'],'04-display-objects.log')
        if ufs_pm_audit:
            from pm_build_concurrency import run_concurrent
            def validate_final():
                run([sys.executable,str(ROOT/'note10/device_test/test_pm_callbacks_prepared_binding.py'),'--artifact',str(OUT),'--output',str(OUT/'pm-callbacks-prepared-binding-model')],'03-pm-callbacks-prepared-binding.log')
                run([sys.executable,str(ROOT/'note10/device_test/test_pm_callbacks_lock_native.py'),'--source-root',str(source),'--output',str(OUT/'pm-callbacks-lock-model')],'03-pm-callbacks-lock.log')
                run([sys.executable,str(ROOT/'note10/device_test/test_pm_callbacks_dispatcher_native.py'),'--output',str(OUT/'pm-callbacks-dispatcher-model')],'03-pm-callbacks-dispatcher.log')
                run([sys.executable,str(ROOT/'note10/device_test/test_pm_callbacks_families_native.py'),'--output',str(OUT/'pm-callbacks-families-model')],'03-pm-callbacks-families.log')
                run([sys.executable,str(ROOT/'note10/device_test/test_pm_callbacks_producer.py'),'--output',str(OUT/'pm-callbacks-producer-model')],'03-pm-callbacks-producer.log')
                run([sys.executable,str(ROOT/'note10/device_test/test_pm_callbacks_decoder.py'),'--native',str(OUT/'pm-callbacks-producer-model'),'--output',str(OUT/'pm-callbacks-decoder-model')],'03-pm-callbacks-decoder.log')
                run([sys.executable,str(ROOT/'note10/device_test/test_pm_callbacks_binding.py'),'--output',str(OUT/'pm-callbacks-binding-model')],'03-pm-callbacks-binding.log')
                run([sys.executable,str(ROOT/'note10/device_test/test_pm_callbacks_integration_native.py'),'--source-root',str(OUT/'pm-callbacks-prepared'),'--output',str(OUT/'pm-callbacks-integration-model')],'03-pm-callbacks-integration.log')
                run([sys.executable,str(ROOT/'note10/device_test/test_pm_build_concurrency.py'),'--output',str(OUT/'pm-build-concurrency-model')],'03-pm-build-concurrency.log')
                run([sys.executable,str(ROOT/'note10/device_test/test_cpu_pm_failure_guard_native.py'),'--source-root',str(source),'--cpu-source',str(OUT/'pm-callbacks-prepared/kernel/cpu_pm.c'),'--output',str(OUT/'cpu-pm-failure-guard-model')],'03-cpu-pm-failure-guard.log')
                for script,model in (('test_pm_preconditions_native.py','getters'),('test_pm_preconditions_gic_native.py','gic'),('test_pm_preconditions_lifecycle.py','lifecycle'),('test_pm_preconditions_producer.py','producer')):
                    run([sys.executable,str(ROOT/'note10/device_test'/script),'--output',str(OUT/('pm-preconditions-'+model+'-model'))],'03-pm-preconditions-'+model+'.log')
                run([sys.executable,str(ROOT/'note10/device_test/test_pm_preconditions_caller.py'),'--source-root',str(OUT/'pm-preconditions-prepared'),'--output',str(OUT/'pm-preconditions-caller-model')],'03-pm-preconditions-caller.log')
                run([sys.executable,str(ROOT/'note10/device_test/test_pm_preconditions_worker.py'),'--source-root',str(OUT/'pm-preconditions-prepared'),'--output',str(OUT/'pm-preconditions-worker-model')],'03-pm-preconditions-worker.log')
                (OUT/'build-result.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
                run([sys.executable,str(ROOT/'note10/device_test/test_pm_preconditions_prepared_binding.py'),'--artifact',str(OUT),'--output',str(OUT/'pm-preconditions-binding-model')],'03-pm-preconditions-binding.log')
                for script,model in (('test_pm_branch_native.py','native'),('test_pm_branch_producer.py','producer')):
                    run([sys.executable,str(ROOT/'note10/device_test'/script),'--output',str(OUT/('pm-branch-'+model+'-model'))],'03-pm-branch-'+model+'.log')
                for script,model in (('test_pm_branch_source_native.py','pmu-source'),('test_pm_branch_gic_source_native.py','gic-source')):
                    run([sys.executable,str(ROOT/'note10/device_test'/script),'--source',str(branch_source_path(OUT,model)),'--output',str(OUT/('pm-branch-'+model+'-model'))],'03-pm-branch-'+model+'.log')
                import shutil
                historical=OUT/'pm-branch-historical-view'
                shutil.copytree(OUT/'pm-preconditions-prepared',historical)
                for name in report['pm_branch_prepared_sha256']:
                    dst=historical/name;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(OUT/'pm-branch-prepared'/name,dst)
                for script,model in (('test_pm_branch_lifecycle.py','lifecycle'),('test_pm_branch_worker.py','worker'),('test_pm_preconditions_caller.py','caller')):
                    run([sys.executable,str(ROOT/'note10/device_test'/script),'--source-root',str(historical),'--output',str(OUT/('pm-branch-'+model+'-model'))],'03-pm-branch-'+model+'.log')
                run([sys.executable,str(ROOT/'note10/device_test/test_gic_priority_restore.py'),'--source',str(source/'drivers/irqchip/irq-gic.c'),'--helper',str(source/'drivers/irqchip/note10_gic_priority_restore.c'),'--baseline',str(OUT/'pm-preconditions-prepared/drivers/irqchip/irq-gic.c'),'--output',str(OUT/'gic-priority-model')],'03-gic-priority-model.log')
                run([sys.executable,str(ROOT/'note10/device_test/test_pmu_failure_restore.py'),'--source',str(OUT/'pmu-failure-prepared/drivers/perf/arm_pmu.c'),'--helper',str(OUT/'pmu-failure-prepared/drivers/perf/note10_pmu_failure_restore.c'),'--cpu-source',str(OUT/'pmu-failure-prepared/kernel/cpu_pm.c'),'--notifier-source',str(OUT/'pmu-failure-prepared/kernel/notifier.c'),'--output',str(OUT/'pmu-failure-model')],'03-pmu-failure-model.log')
                run([sys.executable,str(ROOT/'note10/device_test/test_pm_branch_binding.py'),'--artifact',str(OUT),'--output',str(OUT/'pm-branch-binding-model')],'03-pm-branch-binding.log')
                run([sys.executable,str(ROOT/'note10/device_test/test_pmu_state_native.py'),'--source',str(OUT/'pmu-state-prepared'),'--out',str(OUT/'pmu-state-native-model'),'--cc','clang-14'],'03-pmu-state-native.log')
                run([sys.executable,str(ROOT/'note10/device_test/test_pmu_state_final_lifecycle.py'),'--source-root',str(OUT/'pmu-state-prepared'),'--output',str(OUT/'pmu-state-final-lifecycle-model')],'03-pmu-state-lifecycle.log')
                run([sys.executable,str(ROOT/'note10/device_test/test_pmu_state_worker.py'),'--source-root',str(OUT/'pmu-state-prepared'),'--output',str(OUT/'pmu-state-worker-model')],'03-pmu-state-worker.log')
                run([sys.executable,str(ROOT/'note10/device_test/test_pmu_state_decoder.py')],'03-pmu-state-decoder.log')
                run([sys.executable,str(ROOT/'note10/device_test/test_pmu_state_collector.py'),'--report',str(OUT/'build-result.json'),'--output',str(OUT/'pmu-state-collector-model')],'03-pmu-state-collector.log')
                run([sys.executable,str(ROOT/'note10/device_test/test_pmu_control_native.py'),'--source',str(OUT/'pmu-control-prepared/arch/arm64/kernel/note10_pmu_control_backend.c'),'--cc','clang-14','--output',str(OUT/'pmu-control-native-model')],'03-pmu-control-native.log')
                run([sys.executable,str(ROOT/'note10/device_test/test_pmu_control_final_lifecycle.py'),'--source-root',str(OUT/'pmu-control-prepared'),'--output',str(OUT/'pmu-control-final-lifecycle-model')],'03-pmu-control-lifecycle.log')
                run([sys.executable,str(ROOT/'note10/device_test/test_pmu_control_worker.py'),'--source-root',str(OUT/'pmu-control-prepared'),'--output',str(OUT/'pmu-control-worker-model')],'03-pmu-control-worker.log')
                run([sys.executable,str(ROOT/'note10/device_test/test_pmu_control_decoder.py')],'03-pmu-control-decoder.log')
                run([sys.executable,str(ROOT/'note10/device_test/test_pmu_control_collector.py'),'--report',str(OUT/'build-result.json'),'--output',str(OUT/'pmu-control-collector-model')],'03-pmu-control-collector.log')
                run([sys.executable,str(ROOT/'note10/device_test/test_fpsimd_reference_native.py'),'--source-root',str(OUT/'fpsimd-reference-prepared'),'--cc','clang-14','--output',str(OUT/'fpsimd-reference-native-model')],'03-fpsimd-reference-native.log')
                run([sys.executable,str(ROOT/'note10/device_test/test_fpsimd_reference_final_lifecycle.py'),'--source-root',str(OUT/'fpsimd-reference-prepared'),'--cc','clang-14','--output',str(OUT/'fpsimd-reference-final-lifecycle-model')],'03-fpsimd-reference-final-lifecycle.log')
                run([sys.executable,str(ROOT/'note10/device_test/test_fpsimd_reference_worker.py'),'--source-root',str(OUT/'fpsimd-reference-prepared'),'--cc','clang-14','--output',str(OUT/'fpsimd-reference-worker-model')],'03-fpsimd-reference-worker.log')
                run([sys.executable,str(ROOT/'note10/device_test/test_fpsimd_reference_decoder.py'),'--output',str(OUT/'fpsimd-reference-decoder-model')],'03-fpsimd-reference-decoder.log')
                run([sys.executable,str(ROOT/'note10/device_test/test_fpsimd_reference_collector.py'),'--report',str(OUT/'build-result.json'),'--output',str(OUT/'fpsimd-reference-collector-model')],'03-fpsimd-reference-collector.log')
                run([sys.executable,str(ROOT/'note10/device_test/test_rcu_context_native.py'),'--source-root',str(OUT/'rcu-context-prepared'),'--cc','clang-14','--output',str(OUT/'rcu-context-native-model')],'03-rcu-context-native.log')
                run([sys.executable,str(ROOT/'note10/device_test/test_rcu_context_final_lifecycle.py'),'--source-root',str(OUT/'rcu-context-prepared'),'--cc','clang-14','--output',str(OUT/'rcu-context-final-lifecycle-model')],'03-rcu-context-final-lifecycle.log')
                run([sys.executable,str(ROOT/'note10/device_test/test_rcu_context_worker.py'),'--source-root',str(OUT/'rcu-context-prepared'),'--cc','clang-14','--output',str(OUT/'rcu-context-worker-model')],'03-rcu-context-worker.log')
                run([sys.executable,str(ROOT/'note10/device_test/test_rcu_context_decoder.py'),'--output',str(OUT/'rcu-context-decoder-model')],'03-rcu-context-decoder.log')
                run([sys.executable,str(ROOT/'note10/device_test/test_rcu_context_collector.py'),'--report',str(OUT/'build-result.json'),'--output',str(OUT/'rcu-context-collector-model')],'03-rcu-context-collector.log')
                if ehld_lock_audit:
                    run([sys.executable,str(ROOT/'note10/device_test/test_ehld_lock_native.py'),'--source-root',str(OUT/'ehld-lock-prepared'),'--output',str(OUT/'ehld-lock-native-model'),'--cc','clang-14'],'03-ehld-lock-native.log')
                    run([sys.executable,str(ROOT/'note10/device_test/test_ehld_lock_final_lifecycle.py'),'--source-root',str(OUT/'ehld-lock-prepared'),'--output',str(OUT/'ehld-lock-final-lifecycle-model'),'--cc','clang-14'],'03-ehld-lock-final-lifecycle.log')
                    run([sys.executable,str(ROOT/'note10/device_test/test_ehld_lock_worker.py'),'--source-root',str(OUT/'ehld-lock-prepared'),'--output',str(OUT/'ehld-lock-worker-model'),'--cc','clang-14'],'03-ehld-lock-worker.log')
                    run([sys.executable,str(ROOT/'note10/device_test/test_ehld_lock_decoder.py'),'--output',str(OUT/'ehld-lock-decoder-model')],'03-ehld-lock-decoder.log')
                    run([sys.executable,str(ROOT/'note10/device_test/test_ehld_lock_collector.py'),'--report',str(OUT/'build-result.json'),'--output',str(OUT/'ehld-lock-collector-model')],'03-ehld-lock-collector.log')
            command=[*make,'-j'+str(min(os.cpu_count() or 2,8)),'Image']
            report['commands'].append(command)
            run_concurrent(command, OUT/'04-build.log', validate_final, timeout=1500)
        else:
            run([*make,'-j'+str(min(os.cpu_count() or 2,8)),'Image'],'04-build.log',timeout=1500)
        image=objects/'arch/arm64/boot/Image'
        with image.open('rb') as stream:header=stream.read(64)
        if len(header)!=64 or header[56:60]!=b'ARM\x64':raise ValueError('Missing ARM64 Image header')
        text_offset,image_size,flags=struct.unpack_from('<3Q',header,8)
        # image_size is the in-memory footprint and can include BSS; it is
        # not required to fit in the on-disk Image byte count.
        if not 0<image_size<=256*1024*1024:raise ValueError('Invalid Image memory footprint')
        target=OUT/'Image'
        # Copy only the completed output; retain object-tree logs for diagnosis.
        import shutil
        shutil.copyfile(image,target)
        if ufs_pm_audit and not ehld_lock_audit:
            for name,digest in report['rcu_context_snapshot_sha256'].items():
                if hashlib.sha256((source/name).read_bytes()).hexdigest()!=digest:raise ValueError('Final Image source changed after RCU context snapshot: '+name)
        if ehld_lock_audit and not ehld_irqsave_audit:
            for name,digest in report['ehld_lock_snapshot_sha256'].items():
                if hashlib.sha256((source/name).read_bytes()).hexdigest()!=digest:raise ValueError('Final Image source changed after EHLD lock snapshot: '+name)
        if ehld_irqsave_audit and not ehld_running_lock_audit:
            for name,digest in report['ehld_irqsave_snapshot_sha256'].items():
                if hashlib.sha256((source/name).read_bytes()).hexdigest()!=digest:raise ValueError('Final Image source changed after EHLD irqsave snapshot: '+name)
        if ehld_running_lock_audit and not cpu_pm_roundtrip:
            for name,digest in report['ehld_running_lock_snapshot_sha256'].items():
                if hashlib.sha256((source/name).read_bytes()).hexdigest()!=digest:raise ValueError('Final Image source changed after EHLD running-lock snapshot: '+name)
        if cpu_pm_roundtrip:
            final_sources=dict(report['cpu_pm_roundtrip_snapshot_sha256'])
            if cpu_pm_notifier_trace:final_sources.update(report['cpu_pm_notifier_trace_prepared_sha256'])
            for name,digest in final_sources.items():
                if hashlib.sha256((source/name).read_bytes()).hexdigest()!=digest:raise ValueError('Final Image source changed after composed CPU PM snapshot: '+name)
        if reserve and target.read_bytes().count(report['reservation_evidence_id'].encode())!=1:
            raise ValueError('Unique reservation evidence ID not embedded in Image')
        if xnu_payload is not None:
            from prepare_reservation_kernel import verify_embedded_init
            embedded=verify_embedded_init(target.read_bytes(),(OUT/'initramfs.cpio').read_bytes())
            report['xnu_payload_initramfs_verified']=embedded['embedded_initramfs_verified']
            if b'N10XNU1' not in target.read_bytes():raise ValueError('XNU stage evidence marker missing from Linux Image')
        if cpu_cache and any(marker not in target.read_bytes() for marker in (b'N10QUI1',b'N10CPU2')):
            raise ValueError('CPU/cache evidence markers missing from Linux Image')
        if pm_timer and any(marker not in target.read_bytes() for marker in (b'N10PMT1',b'N10TMR1',b'N10BND1',b'N10TRY1')):
            raise ValueError('PM/timer evidence markers missing from Linux Image')
        if pm_timer and b'N10PMS1' not in target.read_bytes():raise ValueError('PM failure stage marker missing')
        if pm_timer and b'N10QSC1' not in target.read_bytes():raise ValueError('PM quiesce marker missing')
        if ehld_lock_audit and any(marker not in target.read_bytes() for marker in (b'N10ELM1',b'N10ELQ1')):raise ValueError('EHLD lock audit Image markers missing')
        if cpu_pm_roundtrip and (b'N10CPMRT1' not in target.read_bytes() or b'N10CPT1' not in target.read_bytes()):raise ValueError('CPU PM roundtrip Image marker missing')
        if (b'N10CPNC1' in target.read_bytes()) is not cpu_pm_notifier_counts:raise ValueError('CPU PM notifier-count Image marker scope differs')
        if (b'N10CPDC1' in target.read_bytes()) is not cpu_pm_notifier_trace:raise ValueError('CPU PM notifier-trace Image marker scope differs')
        symbol_text=subprocess.check_output(['aarch64-linux-gnu-nm',str(objects/'vmlinux')],text=True)
        trace_names={line.split()[-1] for line in symbol_text.splitlines() if line.split() and 'n10_dispatch_' in line.split()[-1]}
        expected_trace={'n10_dispatch_begin','n10_dispatch_seed','n10_dispatch_arm','n10_dispatch_disarm','n10_dispatch_finish','n10_dispatch_observe','n10_dispatch_marker'}
        if cpu_pm_notifier_trace:
            if not expected_trace<=trace_names or any('__ksymtab_' in n or '__kstrtab_' in n for n in trace_names):raise ValueError('Private dispatch helpers not linked or unexpectedly exported')
            report['cpu_pm_notifier_trace_link_symbols']=sorted(expected_trace)
            report['cpu_pm_notifier_trace_link_verified']=True
        elif trace_names:raise ValueError('Disabled dispatch code remains linked')
        if pm_timer:
            from pm_quiesce_binding import validate_model as validate_quiesce
            validate_quiesce(OUT,report)
        if screen_log and b'N10DSP1' not in target.read_bytes():raise ValueError('Screen log marker missing')
        if gic_roundtrip:
            from gic_roundtrip_binding import validate_model as validate_gic
            validate_gic(OUT,report)
        if dma_pm_audit:
            from dma_pm_binding import validate_model as validate_dma
            validate_dma(OUT,report)
        if ufs_pm_audit:
            from ufs_pm_binding import validate_model as validate_ufs
            validate_ufs(OUT,report)
            from iommu_pm_binding import validate_model as validate_iommu
            validate_iommu(OUT,report)
            from abox_pm_binding import validate_model as validate_abox
            validate_abox(OUT,report)
            from abox_pmu_binding import validate_model as validate_pmu
            validate_pmu(OUT,report)
            from pm_noirq_binding import validate_model as validate_noirq
            validate_noirq(OUT,report)
            from pmu_settle_binding import validate_model as validate_settle
            validate_settle(OUT,report)
            from pm_cpus_binding import validate_model as validate_cpus
            validate_cpus(OUT,report)
            from pm_post_arch_binding import validate_model as validate_post_arch
            validate_post_arch(OUT,report)
            from pm_edge_binding import validate_model as validate_edge
            validate_edge(OUT,report)
            from pm_callbacks_binding import validate_model as validate_callbacks, binding_inputs as callback_binding_inputs
            (OUT/'pm-callbacks-binding-input.json').write_text(json.dumps(callback_binding_inputs(report),indent=2)+'\n',encoding='utf-8')
            run([sys.executable,str(ROOT/'note10/device_test/test_pm_callbacks_full_binding.py'),'--artifact',str(OUT),'--output',str(OUT/'pm-callbacks-coverage-model')],'03-pm-callbacks-coverage.log')
            validate_callbacks(OUT,report)
            from pm_preconditions_binding import validate_model as validate_preconditions
            (OUT/'build-result.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
            run([sys.executable,str(ROOT/'note10/device_test/test_pm_preconditions_scope.py'),'--artifact',str(OUT),'--output',str(OUT/'pm-preconditions-scope-model')],'03-pm-preconditions-scope.log')
            validate_preconditions(OUT,report)
            from pm_branch_binding import validate_model as validate_branch
            run([sys.executable,str(ROOT/'note10/device_test/test_pm_branch_scope.py'),'--artifact',str(OUT),'--output',str(OUT/'pm-branch-scope-model')],'03-pm-branch-scope.log')
            validate_branch(OUT,report)
            (OUT/'build-result.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
            run([sys.executable,str(ROOT/'note10/device_test/test_pmu_failure_binding.py'),'--artifact',str(OUT),'--output',str(OUT/'pmu-failure-binding-model')],'03-pmu-failure-binding.log')
            from pmu_failure_binding import validate as validate_failure
            validate_failure(OUT,report,require_package_flow=False)
            from prepare_pmu_failure_flow_compat import prepare as prepare_prior_flow
            from prepare_pmu_state_flow_compat import prepare as prepare_state_compat
            from prepare_pmu_control_flow_compat import prepare as prepare_control_compat
            from prepare_fpsimd_reference_flow_compat import prepare as prepare_fpsimd_compat
            from prepare_rcu_context_flow_compat import prepare as prepare_rcu_compat
            from prepare_ehld_lock_flow_compat import prepare as prepare_ehld_compat
            from prepare_ehld_irqsave_flow_compat import prepare as prepare_irqsave_compat
            from prepare_ehld_running_lock_flow_compat import prepare as prepare_running_lock_compat
            from prepare_cpu_pm_roundtrip_flow_compat import prepare as prepare_roundtrip_compat
            def prepare_v48_flow_base(temp_root):
                if cpu_pm_roundtrip:
                    return prepare_roundtrip_compat(OUT,Path(temp_root)/'v48-fixture')
                return OUT
            def prepare_v46_flow_base(temp_root):
                v48_base=prepare_v48_flow_base(temp_root)
                if ehld_running_lock_audit:
                    return prepare_running_lock_compat(v48_base,Path(temp_root)/'v46-fixture')
                return v48_base
            import tempfile
            with tempfile.TemporaryDirectory() as temp:
                v46_base=prepare_v46_flow_base(temp)
                irqsave_base=prepare_irqsave_compat(v46_base,Path(temp)/'v45-fixture') if ehld_irqsave_audit else v46_base
                ehld_base=prepare_ehld_compat(irqsave_base,Path(temp)/'v44-fixture') if ehld_lock_audit else OUT
                old41=prepare_control_compat(prepare_fpsimd_compat(prepare_rcu_compat(ehld_base,Path(temp)/'v43-fixture'),Path(temp)/'v42-fixture'),Path(temp)/'v41-fixture')
                old40=prepare_state_compat(old41,Path(temp)/'v40-fixture')
                prior_flow=prepare_prior_flow(old40,Path(temp)/'v39-fixture')
                run([sys.executable,str(ROOT/'note10/device_test/test_pmu_failure_package_flow.py'),'--artifact',str(prior_flow),'--output',str(OUT/'pmu-failure-package-flow-model')],'03-pmu-failure-package-flow.log')
            validate_failure(OUT,report)
            run([sys.executable,str(ROOT/'note10/device_test/test_gic_priority_binding.py'),'--artifact',str(OUT),'--output',str(OUT/'gic-priority-binding-model')],'03-gic-priority-binding.log')
            from gic_priority_binding import validate as validate_priority
            validate_priority(OUT,report,require_package_flow=False)
            with tempfile.TemporaryDirectory() as temp:
                v46_base=prepare_v46_flow_base(temp)
                irqsave_base=prepare_irqsave_compat(v46_base,Path(temp)/'v45-fixture') if ehld_irqsave_audit else v46_base
                ehld_base=prepare_ehld_compat(irqsave_base,Path(temp)/'v44-fixture') if ehld_lock_audit else OUT
                old41=prepare_control_compat(prepare_fpsimd_compat(prepare_rcu_compat(ehld_base,Path(temp)/'v43-fixture'),Path(temp)/'v42-fixture'),Path(temp)/'v41-fixture')
                old40=prepare_state_compat(old41,Path(temp)/'v40-fixture')
                run([sys.executable,str(ROOT/'note10/device_test/test_gic_priority_package_flow.py'),'--artifact',str(old40),'--output',str(OUT/'gic-priority-package-flow-model')],'03-gic-priority-package-flow.log')
            validate_priority(OUT,report)
            run([sys.executable,str(ROOT/'note10/device_test/test_pmu_state_binding.py'),'--artifact',str(OUT),'--output',str(OUT/'pmu-state-binding-model')],'03-pmu-state-binding.log')
            from pmu_state_binding import validate as validate_state
            validate_state(OUT,report,require_package_flow=False)
            with tempfile.TemporaryDirectory() as temp:
                v46_base=prepare_v46_flow_base(temp)
                irqsave_base=prepare_irqsave_compat(v46_base,Path(temp)/'v45-fixture') if ehld_irqsave_audit else v46_base
                ehld_base=prepare_ehld_compat(irqsave_base,Path(temp)/'v44-fixture') if ehld_lock_audit else OUT
                old41=prepare_control_compat(prepare_fpsimd_compat(prepare_rcu_compat(ehld_base,Path(temp)/'v43-fixture'),Path(temp)/'v42-fixture'),Path(temp)/'v41-fixture')
                run([sys.executable,str(ROOT/'note10/device_test/test_pmu_state_package_flow.py'),'--artifact',str(old41),'--output',str(OUT/'pmu-state-package-flow-model')],'03-pmu-state-package-flow.log')
            validate_state(OUT,report)
            run([sys.executable,str(ROOT/'note10/device_test/test_pmu_control_binding.py'),'--artifact',str(OUT),'--output',str(OUT/'pmu-control-binding-model')],'03-pmu-control-binding.log')
            from pmu_control_binding import validate as validate_control
            validate_control(OUT,report,require_package_flow=False)
            with tempfile.TemporaryDirectory() as temp:
                v46_base=prepare_v46_flow_base(temp)
                irqsave_base=prepare_irqsave_compat(v46_base,Path(temp)/'v45-fixture') if ehld_irqsave_audit else v46_base
                ehld_base=prepare_ehld_compat(irqsave_base,Path(temp)/'v44-fixture') if ehld_lock_audit else OUT
                old42=prepare_fpsimd_compat(prepare_rcu_compat(ehld_base,Path(temp)/'v43-fixture'),Path(temp)/'v42-fixture')
                run([sys.executable,str(ROOT/'note10/device_test/test_pmu_control_package_flow.py'),'--artifact',str(old42),'--output',str(OUT/'pmu-control-package-flow-model')],'03-pmu-control-package-flow.log')
            validate_control(OUT,report)
            run([sys.executable,str(ROOT/'note10/device_test/test_fpsimd_reference_binding.py'),'--artifact',str(OUT),'--output',str(OUT/'fpsimd-reference-binding-model')],'03-fpsimd-reference-binding.log')
            from fpsimd_reference_binding import validate as validate_fpsimd
            validate_fpsimd(OUT,report,require_package_flow=False)
            with tempfile.TemporaryDirectory() as temp:
                v46_base=prepare_v46_flow_base(temp)
                irqsave_base=prepare_irqsave_compat(v46_base,Path(temp)/'v45-fixture') if ehld_irqsave_audit else v46_base
                ehld_base=prepare_ehld_compat(irqsave_base,Path(temp)/'v44-fixture') if ehld_lock_audit else OUT
                old43=prepare_rcu_compat(ehld_base,Path(temp)/'v43-fixture')
                run([sys.executable,str(ROOT/'note10/device_test/test_fpsimd_reference_package_flow.py'),'--artifact',str(old43),'--output',str(OUT/'fpsimd-reference-package-flow-model')],'03-fpsimd-reference-package-flow.log')
            validate_fpsimd(OUT,report)
            run([sys.executable,str(ROOT/'note10/device_test/test_rcu_context_binding.py'),'--artifact',str(OUT),'--output',str(OUT/'rcu-context-binding-model')],'03-rcu-context-binding.log')
            from rcu_context_binding import validate as validate_rcu
            validate_rcu(OUT,report,require_package_flow=False)
            with tempfile.TemporaryDirectory() as temp:
                v46_base=prepare_v46_flow_base(temp)
                irqsave_base=prepare_irqsave_compat(v46_base,Path(temp)/'v45-fixture') if ehld_irqsave_audit else v46_base
                rcu_flow_input=prepare_ehld_compat(irqsave_base,Path(temp)/'v44-fixture') if ehld_lock_audit else OUT
                run([sys.executable,str(ROOT/'note10/device_test/test_rcu_context_package_flow.py'),'--artifact',str(rcu_flow_input),'--output',str(OUT/'rcu-context-package-flow-model')],'03-rcu-context-package-flow.log')
            validate_rcu(OUT,report)
        if ehld_lock_audit:
            (OUT/'Image').write_bytes(target.read_bytes())
            (OUT/'handoff.config').write_bytes((OUT/'objects/.config').read_bytes())
            (OUT/'build-result.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n')
            run([sys.executable,str(ROOT/'note10/device_test/test_ehld_lock_binding.py'),'--artifact',str(OUT),'--output',str(OUT/'ehld-lock-binding-model')],'03-ehld-lock-binding.log')
            from ehld_lock_binding import validate as validate_ehld
            validate_ehld(OUT,report,require_package_flow=False)
            with tempfile.TemporaryDirectory() as temp:
                v46_base=prepare_v46_flow_base(temp)
                ehld_flow_input=prepare_irqsave_compat(v46_base,Path(temp)/'v45-fixture') if ehld_irqsave_audit else v46_base
                run([sys.executable,str(ROOT/'note10/device_test/test_ehld_lock_package_flow.py'),'--artifact',str(ehld_flow_input),'--output',str(OUT/'ehld-lock-package-flow-model')],'03-ehld-lock-package-flow.log')
            validate_ehld(OUT,report)
            from pm_irq_binding import validate_model as validate_irq
            validate_irq(OUT,report)
        if ehld_irqsave_audit:
            (OUT/'Image').write_bytes(target.read_bytes())
            (OUT/'handoff.config').write_bytes((OUT/'objects/.config').read_bytes())
            (OUT/'build-result.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n')
            run([sys.executable,str(ROOT/'note10/device_test/test_ehld_irqsave_binding.py'),'--artifact',str(OUT),'--output',str(OUT/'ehld-irqsave-binding-model')],'03-ehld-irqsave-binding.log')
            report['ehld_irqsave_binding_sha256']=hashlib.sha256((OUT/'ehld-irqsave-binding-model/result.json').read_bytes()).hexdigest()
            from ehld_irqsave_binding import validate as validate_irqsave
            validate_irqsave(OUT,report,require_package_flow=False)
            (OUT/'build-result.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n')
            with tempfile.TemporaryDirectory() as temp:
                v46_base=prepare_v46_flow_base(temp)
                run([sys.executable,str(ROOT/'note10/device_test/test_ehld_irqsave_package_flow.py'),'--artifact',str(v46_base),'--output',str(OUT/'ehld-irqsave-package-flow-model')],'03-ehld-irqsave-package-flow.log')
            report['ehld_irqsave_package_flow_sha256']=hashlib.sha256((OUT/'ehld-irqsave-package-flow-model/result.json').read_bytes()).hexdigest()
            validate_irqsave(OUT,report)
        if ehld_running_lock_audit:
            (OUT/'Image').write_bytes(target.read_bytes())
            (OUT/'handoff.config').write_bytes((OUT/'objects/.config').read_bytes())
            (OUT/'build-result.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n')
            run([sys.executable,str(ROOT/'note10/device_test/test_ehld_running_lock_binding.py'),'--artifact',str(OUT),'--output',str(OUT/'ehld-running-lock-binding-model')],'03-ehld-running-lock-binding.log')
            report['ehld_running_lock_binding_sha256']=hashlib.sha256((OUT/'ehld-running-lock-binding-model/result.json').read_bytes()).hexdigest()
            from ehld_running_lock_binding import validate as validate_running_lock
            validate_running_lock(OUT,report,require_package_flow=False)
            (OUT/'build-result.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n')
            with tempfile.TemporaryDirectory() as temp:
                v48_base=prepare_v48_flow_base(temp)
                run([sys.executable,str(ROOT/'note10/device_test/test_ehld_running_lock_package_flow.py'),'--artifact',str(v48_base),'--output',str(OUT/'ehld-running-lock-package-flow-model')],'03-ehld-running-lock-package-flow.log')
            report['ehld_running_lock_package_flow_sha256']=hashlib.sha256((OUT/'ehld-running-lock-package-flow-model/result.json').read_bytes()).hexdigest()
            validate_running_lock(OUT,report)
        if cpu_pm_roundtrip:
            (OUT/'Image').write_bytes(target.read_bytes())
            (OUT/'handoff.config').write_bytes((OUT/'objects/.config').read_bytes())
            (OUT/'build-result.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n')
            run([sys.executable,str(ROOT/'note10/device_test/test_cpu_pm_roundtrip_decoder.py'),'--output',str(OUT/'cpu-pm-roundtrip-decoder-model')],'03-cpu-pm-roundtrip-decoder.log')
            report['cpu_pm_roundtrip_decoder_sha256']=hashlib.sha256((OUT/'cpu-pm-roundtrip-decoder-model/result.json').read_bytes()).hexdigest()
            (OUT/'build-result.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n')
            run([sys.executable,str(ROOT/'note10/device_test/test_cpu_pm_roundtrip_binding.py'),'--artifact',str(OUT),'--output',str(OUT/'cpu-pm-roundtrip-binding-model')],'03-cpu-pm-roundtrip-binding.log')
            report['cpu_pm_roundtrip_binding_sha256']=hashlib.sha256((OUT/'cpu-pm-roundtrip-binding-model/result.json').read_bytes()).hexdigest()
            from cpu_pm_roundtrip_binding import validate as validate_roundtrip
            validate_roundtrip(OUT,report,require_package_flow=False)
            (OUT/'build-result.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n')
            run([sys.executable,str(ROOT/'note10/device_test/test_cpu_pm_roundtrip_package_flow.py'),'--artifact',str(OUT),'--output',str(OUT/'cpu-pm-roundtrip-package-flow-model')],'03-cpu-pm-roundtrip-package-flow.log')
            report['cpu_pm_roundtrip_package_flow_sha256']=hashlib.sha256((OUT/'cpu-pm-roundtrip-package-flow-model/result.json').read_bytes()).hexdigest()
            if cpu_pm_notifier_trace:
                (OUT/'build-result.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n')
                run([sys.executable,str(ROOT/'note10/device_test/test_cpu_pm_notifier_trace_package.py'),'--artifact',str(OUT),'--output',str(OUT/'cpu-pm-notifier-trace-package-model')],'03-cpu-pm-notifier-trace-package.log')
                report['cpu_pm_notifier_trace_package_sha256']=hashlib.sha256((OUT/'cpu-pm-notifier-trace-package-model/result.json').read_bytes()).hexdigest()
            validate_roundtrip(OUT,report)
        if auto_return:
            from materialize_auto_cycle import SLOT
            if b'N10RET1' not in target.read_bytes() or target.read_bytes().count(SLOT+b'\0')!=1:raise ValueError('Auto-return marker/unique data slot missing')
        report.update(build_passed=True,image_size=target.stat().st_size,
                      image_sha256=hashlib.file_digest(target.open('rb'),'sha256').hexdigest(),
                      arm64_text_offset=hex(text_offset),arm64_header_image_size=image_size,arm64_flags=hex(flags))
        for name,command in (('compiler',['clang-14','--version']),('linker',['aarch64-linux-gnu-ld','--version'])):
            report[name]=subprocess.check_output(command,text=True).splitlines()[0]
    except Exception as error:
        report['failure']=str(error)
        raise
    finally:
        (OUT/'build-result.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
        print(json.dumps({key:report[key] for key in ('build_passed','deployment_ready','source_commit')}),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--caps',action='store_true',help='Include built-in per-CPU printk diagnostic for a future manual boot')
    parser.add_argument('--reserve',action='store_true',help='Early XNU RAM reservation diagnostic with original built-in idle PID1')
    parser.add_argument('--window-access',action='store_true',help='Opt-in write/read/scrub of this boot\'s checked reservation; no XNU execution')
    parser.add_argument('--xnu-payload',type=Path,help='Verified experimental XNU kernel.mem for data-only RAM staging')
    parser.add_argument('--xnu-payload-manifest',type=Path,help='Hash-bound manifest from materialize_stage_payload.py')
    parser.add_argument('--cpu-cache',action='store_true',help='Opt-in CPU offline/online, cache maintenance and per-CPU payload reads')
    parser.add_argument('--pm-timer',action='store_true',help='Devices-only PM test and restored per-CPU event-stream normalization')
    parser.add_argument('--auto-return',action='store_true',help='Opt-in one-shot recovery request after 90 seconds; requires cycle token')
    parser.add_argument('--screen-log',action='store_true',help='Experimental top-left quarter panel console; requires auto return')
    parser.add_argument('--gic-roundtrip',action='store_true',help='Reversible GICv2 CPU priority mask diagnostic after restored PM')
    parser.add_argument('--dma-pm-audit',action='store_true',help='Read-only DMA-capable device PM framework coverage snapshots')
    parser.add_argument('--ufs-pm-audit',action='store_true',help='Read-only Exynos UFS driver queue/link/clock/IRQ snapshots')
    parser.add_argument('--ehld-lock-audit',action='store_true',help='Experimental CPU0 EHLD ctrl lock-availability observation with a pinned no-dynamic-probes profile')
    parser.add_argument('--ehld-irqsave-audit',action='store_true',help='Opt in to the EHLD paired irqsave token source audit; requires --ehld-lock-audit')
    parser.add_argument('--ehld-running-lock-audit',action='store_true',help='Opt in to EHLD start/stop running-scalar ctrl-lock synchronization; requires both EHLD audit flags')
    parser.add_argument('--cpu-pm-roundtrip',action='store_true',help='Opt in to one bounded original CPU_PM enter/exit pair; requires EHLD running-lock audit and automatic recovery')
    parser.add_argument('--cpu-pm-notifier-counts',action='store_true',help='Opt in to bounded notifier callback counts within the guarded CPU_PM pair')
    parser.add_argument('--cpu-pm-notifier-trace',action='store_true',help='Opt in to bounded notifier-block dispatch order; requires notifier counts')
    args=parser.parse_args();main(caps=args.caps,reserve=args.reserve,window_access=args.window_access,
                                   xnu_payload=args.xnu_payload,xnu_manifest=args.xnu_payload_manifest,cpu_cache=args.cpu_cache,pm_timer=args.pm_timer,auto_return=args.auto_return,screen_log=args.screen_log,gic_roundtrip=args.gic_roundtrip,dma_pm_audit=args.dma_pm_audit,ufs_pm_audit=args.ufs_pm_audit,ehld_lock_audit=args.ehld_lock_audit,ehld_irqsave_audit=args.ehld_irqsave_audit,ehld_running_lock_audit=args.ehld_running_lock_audit,cpu_pm_roundtrip=args.cpu_pm_roundtrip,cpu_pm_notifier_counts=args.cpu_pm_notifier_counts,cpu_pm_notifier_trace=args.cpu_pm_notifier_trace)
