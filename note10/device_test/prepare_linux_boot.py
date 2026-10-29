"""Prepare a PC-only boot-partition prototype using pinned AOSP mkbootimg.

Never flashes or accesses ADB. Keeps the recovery partition separate. A built
file is not evidence that Samsung will boot it or that recovery reentry works.
"""
import argparse
import re
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'note10'))
from inspect_firmware import boot_header

MKBOOTIMG_SHA256='2a8d05d34110f66c463668f43fc812ce2e46e66459c347eaadb080271df69aa8'
TWRP_SHA256='e8de29b03fc3eab95f51663b08b2f848e168854a15f8a598a1f80d216f4794df'
KERNEL_COMMIT='55f042627bb7030c93550faafa117674d32b21d1'


def payload_size(kernel_size,ramdisk_size,page,partition_size,*,allow_empty_ramdisk=False):
    if any(type(n) is not int or n<0 for n in (kernel_size,ramdisk_size,page,partition_size)):
        raise ValueError('Invalid image size input')
    if not kernel_size or (not ramdisk_size and not allow_empty_ramdisk) or page not in (2048,4096,8192,16384):
        raise ValueError('Unsupported prototype sizes or page')
    align=lambda n:(n+page-1)//page*page
    size=page+align(kernel_size)+align(ramdisk_size)
    if size>partition_size:raise ValueError('Prototype exceeds actual boot partition')
    return size


def read_verified_backup(directory):
    manifest=json.loads((directory/'backup-manifest.json').read_text())
    if manifest.get('complete') is not True or manifest.get('partition_writes') is not False:
        raise ValueError('Completed read-only boot backup required')
    result={}
    for item in manifest['partitions']:
        name=item['partition']
        if name not in ('boot','recovery','dtb','dtbo','vbmeta') or name in result or item['file']!=name+'.img':
            raise ValueError('Unexpected backup component')
        path=directory/item['file']
        if path.is_symlink() or not 0<item['size']<=128*1024*1024:raise ValueError('Unsafe backup component')
        data=path.read_bytes()
        if len(data)!=item['size'] or hashlib.sha256(data).hexdigest()!=item['sha256']:
            raise ValueError('Backup bytes differ from verified manifest')
        if item.get('remote_hash_before_and_after_match') is not True:raise ValueError('Unverified backup transfer')
        result[name]=data
    if len(result)!=5:raise ValueError('All five boot components required')
    if not manifest.get('bootloader','').startswith('N976N'):raise ValueError('N976N backup required')
    return result


def prepare(backup,kernel_build,twrp,mkbootimg,output,auto_cycle_token=None):
    if not output.resolve().is_relative_to((ROOT/'note10/private').resolve()):
        raise ValueError('Prototype output must remain in private workspace')
    if output.exists() or output.with_suffix('.partial').exists():raise ValueError('Output already exists')
    if hashlib.sha256(mkbootimg.read_bytes()).hexdigest()!=MKBOOTIMG_SHA256:
        raise ValueError('Expected pinned Android 12 AOSP mkbootimg script')
    official=twrp.read_bytes()
    if hashlib.sha256(official).hexdigest()!=TWRP_SHA256:raise ValueError('Expected verified official d2x TWRP')
    parts=read_verified_backup(backup)
    if not parts['recovery'].startswith(official):raise ValueError('Existing recovery does not match reference TWRP')
    build=json.loads((kernel_build/'build-result.json').read_text())
    if build.get('build_passed') is not True or build.get('builtin_cpu_diagnostic') is not True:
        raise ValueError('Successful CPU-diagnostic Linux build required')
    if build.get('diagnostic_preserves_external_initramfs') is not True:
        raise ValueError('Diagnostic must preserve external initramfs in normal boot')
    if build.get('source_commit')!=KERNEL_COMMIT or build.get('public_defconfig')!='exynos9820-d2x_defconfig':
        raise ValueError('Unexpected kernel source or target')
    auto_return=build.get('auto_return_diagnostic') is True
    if auto_return!=(auto_cycle_token is not None):raise ValueError('Auto-return build and per-cycle token must be paired')
    if auto_cycle_token is not None and not re.fullmatch(r'[0-9a-f]{32}',auto_cycle_token):raise ValueError('Invalid cycle token')
    kernel=kernel_build/'Image';data=kernel.read_bytes()
    if auto_return:
        from materialize_auto_cycle import validate
        validate(kernel_build,auto_cycle_token)
        if b'N10RET1' not in data:raise ValueError('Auto-return marker missing from actual kernel')
    if hashlib.sha256(data).hexdigest()!=build['image_sha256'] or len(data)!=build['image_size']:
        raise ValueError('Kernel image differs from build report')
    if len(data)<64 or data[56:60]!=b'ARM\x64':raise ValueError('Not an ARM64 Linux Image')
    config=(kernel_build/'handoff.config').read_bytes()
    from pm_quiesce_binding import assert_scope as assert_quiesce_scope
    assert_quiesce_scope(kernel_build,build)
    from gic_roundtrip_binding import validate_model as validate_gic
    validate_gic(kernel_build,build)
    from dma_pm_binding import validate_model as validate_dma
    validate_dma(kernel_build,build)
    from ufs_pm_binding import validate_model as validate_ufs
    validate_ufs(kernel_build,build)
    from iommu_pm_binding import validate_model as validate_iommu
    validate_iommu(kernel_build,build)
    from abox_pm_binding import validate_model as validate_abox
    validate_abox(kernel_build,build)
    from abox_pmu_binding import validate_model as validate_pmu
    validate_pmu(kernel_build,build)
    from pm_noirq_binding import validate_model as validate_noirq
    validate_noirq(kernel_build,build)
    from pmu_settle_binding import validate_model as validate_settle
    validate_settle(kernel_build,build)
    from pm_cpus_binding import validate_model as validate_cpus
    validate_cpus(kernel_build,build)
    from pm_post_arch_binding import validate_model as validate_post_arch
    validate_post_arch(kernel_build,build)
    from pm_edge_binding import validate_model as validate_edge
    validate_edge(kernel_build,build)
    from pm_callbacks_binding import validate_model as validate_callbacks
    validate_callbacks(kernel_build,build)
    from pm_preconditions_binding import validate_model as validate_preconditions
    validate_preconditions(kernel_build,build)
    from pm_branch_binding import validate_model as validate_branch
    validate_branch(kernel_build,build)
    from pmu_failure_binding import validate as validate_failure
    validate_failure(kernel_build,build)
    from gic_priority_binding import validate as validate_priority
    validate_priority(kernel_build,build)
    from pmu_state_binding import validate as validate_state
    validate_state(kernel_build,build)
    from pmu_control_binding import validate as validate_control
    validate_control(kernel_build,build)
    from fpsimd_reference_binding import validate as validate_fpsimd
    validate_fpsimd(kernel_build,build)
    from rcu_context_binding import validate as validate_rcu
    validate_rcu(kernel_build,build)
    from ehld_lock_binding import validate as validate_ehld
    validate_ehld(kernel_build,build)
    from ehld_irqsave_binding import validate as validate_ehld_irqsave,package_scope as irqsave_package_scope
    irqsave_scope=validate_ehld_irqsave(kernel_build,build)
    if type(irqsave_scope) is not bool or irqsave_scope is not irqsave_package_scope(build):raise ValueError('EHLD irqsave build validation scope differs')
    from pm_irq_binding import validate_model as validate_irq
    validate_irq(kernel_build,build)
    if hashlib.sha256(config).hexdigest()!=build['effective_config_sha256']:
        raise ValueError('Config differs from kernel build report')
    required={'CONFIG_BLK_DEV_INITRD=y','CONFIG_RD_LZMA=y','CONFIG_KEXEC=y','CONFIG_KEXEC_CORE=y','CONFIG_ARM64_4K_PAGES=y'}
    if not required.issubset(config.decode().splitlines()):
        raise ValueError('Kernel lacks required ramdisk/kexec/page configuration')
    builtin=build.get('builtin_idle_init') is True
    embedded_check=None
    if builtin:
        if build.get('early_xnu_reservation') is not True or 'CONFIG_INITRAMFS_FORCE=y' not in config.decode().splitlines():
            raise ValueError('Built-in reservation init must be forced')
        for name,key in (('minimal-init.elf','minimal_init_elf_sha256'),('initramfs.cpio','initramfs_cpio_sha256')):
            if hashlib.sha256((kernel_build/name).read_bytes()).hexdigest()!=build[key]:
                raise ValueError('Built-in init artifact differs from report')
        from prepare_reservation_kernel import verify_embedded_init
        embedded_check=verify_embedded_init(data,(kernel_build/'initramfs.cpio').read_bytes())
    xnu_stage=build.get('xnu_payload_stage_diagnostic') is True
    if xnu_stage:
        if build.get('window_access_diagnostic') is not True or build.get('xnu_payload_initramfs_verified') is not True:
            raise ValueError('XNU staging build must include verified initramfs payload and RAM-access test')
        required.update({'CONFIG_CRYPTO=y','CONFIG_CRYPTO_HASH=y','CONFIG_CRYPTO_SHA256=y'})
        if not {'CONFIG_CRYPTO=y','CONFIG_CRYPTO_HASH=y','CONFIG_CRYPTO_SHA256=y'}.issubset(config.decode().splitlines()):
            raise ValueError('Kernel lacks SHA256 staging support')
    boot=boot_header(parts['boot']);recovery=boot_header(official)
    if boot['header_version']!=1 or recovery['header_version']!=1 or boot['page_size']!=recovery['page_size']:
        raise ValueError('Expected observed matching v1 boot headers')
    if boot['recovery_dtbo_size'] or boot['second_size'] or recovery['second_size']:
        raise ValueError('Unexpected boot-only payload layout')
    for field in ('kernel_addr','tags_addr'):
        if boot[field]!=recovery[field]:raise ValueError('Boot/recovery load fields differ')
    if struct.unpack_from('<Q',data,8)[0]!=recovery['arm64_text_offset']:
        raise ValueError('Linux text offset differs from known recovery kernel')
    vbmeta=parts['vbmeta']
    if vbmeta[:4]!=b'AVB0' or not struct.unpack_from('>I',vbmeta,120)[0]&2:
        raise ValueError('Observed verification-disabled vbmeta header required; no vbmeta changes performed')
    start=recovery['ramdisk_file_offset']
    ramdisk=b'' if builtin else official[start:start+recovery['ramdisk_size']]
    size=payload_size(len(data),len(ramdisk),boot['page_size'],len(parts['boot']),allow_empty_ramdisk=builtin)
    output.parent.mkdir(exist_ok=True,parents=True)
    rd=output.with_suffix('.ramdisk.lzma')
    if ramdisk:
        if rd.exists():raise ValueError('Refusing to overwrite ramdisk staging input')
        rd.write_bytes(ramdisk)
    partial=output.with_suffix('.partial')
    # Boot uses the backed-up separate DTB/DTBO partitions. No embedded
    # recovery_dtbo is copied; this is an unbooted boot-only prototype.
    cmdline=recovery['cmdline']
    if 'n10.cycle=' in cmdline:raise ValueError('Existing cycle argument refused')
    if len(cmdline.encode())>1535:raise ValueError('BOOT command line too long')
    command=[sys.executable,'-X','utf8',str(mkbootimg),'--header_version','1',
             '--kernel',str(kernel),'--base','0',
             '--kernel_offset',hex(boot['kernel_addr']),
             '--ramdisk_offset',hex(boot['ramdisk_addr'] if builtin else recovery['ramdisk_addr']),
             '--tags_offset',hex(boot['tags_addr']),'--pagesize',str(boot['page_size']),
             '--board',boot['name'],'--cmdline',cmdline,
             '--os_version',boot['os_version'],'--os_patch_level',boot['security_patch_month'],
             '--output',str(partial)]
    if ramdisk:command.extend(['--ramdisk',str(rd)])
    subprocess.run(command,check=True,capture_output=True,timeout=60)
    packed=partial.read_bytes();header=boot_header(packed)
    if len(packed)!=size or header['kernel_sha256']!=build['image_sha256']:
        raise ValueError('Packed image does not match size/kernel contract')
    if any(header[field]!=boot[field] for field in ('name','os_version','security_patch_month','kernel_addr','tags_addr','page_size')):
        raise ValueError('Packed BOOT metadata differs from paired original')
    if header['cmdline']!=cmdline:raise ValueError('Packed cycle command line differs')
    if packed[header['ramdisk_file_offset']:header['ramdisk_file_offset']+header['ramdisk_size']]!=ramdisk:
        raise ValueError('Packed ramdisk differs from reference')
    if header['recovery_dtbo_size']!=0:raise ValueError('Unexpected embedded recovery DTBO')
    # Preserve the non-cryptographic Samsung BOOT trailer observed immediately
    # after the original aligned payload. Never copy its stale AVB hash/footer.
    trailer=b'SEANDROIDENFORCE'
    original_end=boot['second_file_offset']
    if parts['boot'][original_end:original_end+len(trailer)]!=trailer:
        raise ValueError('Expected observed Samsung BOOT trailer')
    if len(packed)+len(trailer)>len(parts['boot']):raise ValueError('BOOT trailer exceeds partition')
    packed+=trailer
    partial.write_bytes(packed)
    partial.rename(output)
    report={'prototype_created':True,'kind':'temporary Linux diagnostic boot; not XNU/iOS',
            'file':str(output),'size':len(packed),'boot_partition_size':len(parts['boot']),
            'sha256':hashlib.sha256(packed).hexdigest(),'kernel_build_sha256':build['image_sha256'],
            'backup_manifest_sha256':hashlib.sha256((backup/'backup-manifest.json').read_bytes()).hexdigest(),
            'original_boot_sha256':hashlib.sha256(parts['boot']).hexdigest(),
            'existing_recovery_partition_sha256':hashlib.sha256(parts['recovery']).hexdigest(),
            'aosp_mkbootimg_sha256':MKBOOTIMG_SHA256,
            'reference_ramdisk_sha256':None if builtin else hashlib.sha256(ramdisk).hexdigest(),
            'builtin_idle_init':builtin,'early_xnu_reservation':build.get('early_xnu_reservation') is True,
            'window_access_diagnostic':build.get('window_access_diagnostic') is True,
            'xnu_payload_stage_diagnostic':xnu_stage,
            'cpu_cache_roundtrip_diagnostic':build.get('cpu_cache_roundtrip_diagnostic') is True,
            'pm_timer_diagnostic':build.get('pm_timer_diagnostic') is True,
            'pm_quiesce_diagnostic':build.get('pm_quiesce_diagnostic') is True,
            'pm_quiesce_evidence_version':build.get('pm_quiesce_evidence_version'),
            'gic_roundtrip_diagnostic':build.get('gic_roundtrip_diagnostic') is True,
            'gic_roundtrip_evidence_version':build.get('gic_roundtrip_evidence_version'),
            'dma_pm_audit_diagnostic':build.get('dma_pm_audit_diagnostic') is True,
            'dma_pm_audit_evidence_version':build.get('dma_pm_audit_evidence_version'),
            'ufs_pm_audit_diagnostic':build.get('ufs_pm_audit_diagnostic') is True,
            'ufs_pm_audit_evidence_version':build.get('ufs_pm_audit_evidence_version'),
            'iommu_pm_audit_diagnostic':build.get('iommu_pm_audit_diagnostic') is True,
            'iommu_pm_audit_evidence_version':build.get('iommu_pm_audit_evidence_version'),
            'abox_failed_fw_resume_guard':build.get('abox_failed_fw_resume_guard') is True,
            'pm_noirq_diagnostic':build.get('pm_noirq_diagnostic') is True,
            'pm_noirq_evidence_version':build.get('pm_noirq_evidence_version'),
            'pmu_settle_diagnostic':build.get('pmu_settle_diagnostic') is True,
            'pmu_settle_evidence_version':build.get('pmu_settle_evidence_version'),
            'pm_cpus_diagnostic':build.get('pm_cpus_diagnostic') is True,
            'pm_cpus_evidence_version':build.get('pm_cpus_evidence_version'),
            'pm_post_arch_diagnostic':build.get('pm_post_arch_diagnostic') is True,
            'pm_post_arch_evidence_version':build.get('pm_post_arch_evidence_version'),
            'pm_edge_inventory_diagnostic':build.get('pm_edge_inventory_diagnostic') is True,
            'pm_edge_inventory_evidence_version':build.get('pm_edge_inventory_evidence_version'),
            'pm_callbacks_diagnostic':build.get('pm_callbacks_diagnostic') is True,
            'pm_callbacks_evidence_version':build.get('pm_callbacks_evidence_version'),
            'pm_preconditions_diagnostic':build.get('pm_preconditions_diagnostic') is True,
            'pm_preconditions_version':build.get('pm_preconditions_version'),
            'pm_branch_diagnostic':build.get('pm_branch_diagnostic') is True,
            'pm_branch_version':build.get('pm_branch_version'),
            'pmu_failure_restore':build.get('pmu_failure_restore') is True,
            'pmu_failure_restore_version':build.get('pmu_failure_restore_version'),
            'gic_priority_restore':build.get('gic_priority_restore') is True,
            'gic_priority_restore_version':build.get('gic_priority_restore_version'),
            'pmu_state_audit':build.get('pmu_state_audit') is True,
            'pmu_state_audit_version':build.get('pmu_state_audit_version'),
            'pmu_control_audit':build.get('pmu_control_audit') is True,
            'pmu_control_audit_version':build.get('pmu_control_audit_version'),
            'fpsimd_reference_audit':build.get('fpsimd_reference_audit') is True,
            'fpsimd_reference_audit_version':build.get('fpsimd_reference_audit_version'),
            'rcu_context_audit':build.get('rcu_context_audit') is True,
            'rcu_context_audit_version':build.get('rcu_context_audit_version'),
            'ehld_lock_audit':build.get('ehld_lock_audit') is True,
            'ehld_lock_audit_version':build.get('ehld_lock_audit_version'),
            'ehld_irqsave_audit':build.get('ehld_irqsave_audit') is True,
            'ehld_irqsave_audit_version':build.get('ehld_irqsave_audit_version'),
            'pm_irq_diagnostic':build.get('pm_irq_diagnostic') is True,
            'pm_irq_evidence_version':build.get('pm_irq_evidence_version'),
            'abox_pmu_audit_diagnostic':build.get('abox_pmu_audit_diagnostic') is True,
            'abox_pmu_audit_evidence_version':build.get('abox_pmu_audit_evidence_version'),
            'abox_pm_audit_diagnostic':build.get('abox_pm_audit_diagnostic') is True,
            'abox_pm_audit_evidence_version':build.get('abox_pm_audit_evidence_version'),
            'screen_log_diagnostic':build.get('screen_log_diagnostic') is True,
            'auto_return_diagnostic':auto_return,'auto_cycle_token':auto_cycle_token,
            'xnu_payload_sha256':build.get('xnu_payload_sha256') if xnu_stage else None,
            'xnu_payload_size':build.get('xnu_payload_size') if xnu_stage else None,
            'external_ramdisk_included':bool(ramdisk),
            'embedded_initramfs_check':embedded_check,
            'embedded_recovery_dtbo':False,'requires_existing_dtb_dtbo_partitions':True,
            'preserved_boot_os_version':boot['os_version'],
            'preserved_boot_security_patch_month':boot['security_patch_month'],
            'samsung_boot_trailer_preserved':True,'original_avb_footer_copied':False,
            'device_boot_tested':False,'recovery_reentry_verified_after_install':False,
            'deployment_ready':False,'partition_writes':False,'device_operations':[],
            'scope':'PC format/size validation only; Samsung runtime DT selection and boot behavior remain unverified',
            'command':command}
    output.with_suffix('.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('backup','kernel-build','twrp','mkbootimg','output'):parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--auto-cycle-token')
    args=parser.parse_args()
    result=prepare(args.backup,args.kernel_build,args.twrp,args.mkbootimg,args.output,args.auto_cycle_token)
    print(json.dumps({k:result[k] for k in ('prototype_created','size','boot_partition_size','deployment_ready')}))
