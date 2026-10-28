"""Read previous reservation-test boot logs from TWRP; never change a phone."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import uuid
from decode_reservation import decode,decode_frames,checksum
from decode_window_access import decode as decode_access
from decode_xnu_stage import decode as decode_xnu_stage
from decode_cpu_cache import decode as decode_cpu_cache
from decode_pm_timer import decode as decode_pm_timer
from decode_linux_caps import decode as decode_caps
from run_probe import ROOT,Adb,preflight
from stage_phase2 import verify_packages

def pm_completed_generation(pm_observation):
    generations=pm_observation['quiescence']['attempts']
    return generations[max(generations,key=int)]['result']['generation']

def decode_dma_pm_observation(text,identity,pm_observation):
    from decode_dma_pm import decode as decode_dma
    return decode_dma(text,identity,pm_completed_generation(pm_observation))

def decode_ufs_pm_observation(text,identity,pm_observation):
    from decode_ufs_pm import decode as decode_ufs
    return decode_ufs(text,identity,pm_completed_generation(pm_observation))


def decode_iommu_pm_observation(text,identity,pm_observation):
    from decode_iommu_pm import decode as decode_iommu
    return decode_iommu(text,identity,pm_completed_generation(pm_observation))


def decode_abox_pm_observation(text,identity,pm_observation):
    from decode_abox_pm import decode as decode_abox
    return decode_abox(text,identity,pm_completed_generation(pm_observation))


def select_latest_boot(data,expected_banner,allow_panic_corroboration=False,boot_binding_id=None):
    """Select one contiguous boot using an intact zero-time Linux banner.

    Never combine frames across boots or search backwards for a passing boot.
    With no intact boundary, retain the whole input and its duplicate checks.
    """
    headers=list(re.finditer(
        rb'(?m)^[ \t]*(?:<[0-9]+>)?\[\s*0\.000000\][^\r\n]*?(Linux version [^\r\n]*)',data))
    offset=0;corroborated=False;bound_banner=False
    if headers:
        latest=headers[-1]
        if latest.group(1)!=expected_banner.encode('ascii'):
            panic_banners=re.findall(rb'(?m)^<[0-9]+>\[\s*[0-9]+\.[0-9]+\][^\r\n]* linux_banner: (Linux version [^\r\n]*)',data[latest.start():])
            if allow_panic_corroboration and panic_banners and all(value==expected_banner.encode('ascii') for value in panic_banners):
                corroborated=True
            elif boot_binding_id is not None:
                valid={}
                pattern=rb'N10BND1 (id=([0-9a-f]{32}) seq=([0-9]+) banner=(Linux version [^\r\n]+)) checksum=([0-9a-f]{8})(?=\r?\n|$)'
                for match in re.finditer(pattern,data[latest.start():]):
                    body,identity,sequence,banner,total=match.groups()
                    if identity.decode()!=boot_binding_id or checksum(body)!=int(total,16):continue
                    sequence=int(sequence)
                    if sequence>=16 or sequence in valid:raise ValueError('Invalid or duplicate boot binding sequence')
                    if banner!=expected_banner.encode('ascii'):raise ValueError('Checksummed boot banner differs from Image')
                    valid[sequence]=banner
                if len(valid)<2:raise ValueError('Two intact exact boot banner bindings required')
                bound_banner=True
            else:
                raise ValueError('Latest intact boot-start banner differs from verified Image')
        offset=latest.start()
    selected=data[offset:]
    return selected,{'method':'latest-intact-zero-time-banner' if headers else 'whole-log-no-intact-boundary',
                     'intact_boot_start_count':len(headers),'byte_start':offset,'byte_end':len(data),
                     'start_banner_matches_image':latest.group(1)==expected_banner.encode('ascii') if headers else None,
                     'exact_checksummed_banner_binding':bound_banner,
                     'exact_panic_banner_corroboration':corroborated,
                     'selected_sha256':hashlib.sha256(selected).hexdigest(),
                     'older_pass_fallback':False,'corrupted_bytes_repaired':False}


def collect(packages,kernel_build,adb):
    records=verify_packages(packages)
    if {r['file'] for r in records}!={'note10-reservation-diagnostic.zip','note10-reservation-rollback.zip'}:
        raise ValueError('Reservation package pair required')
    result=json.loads((kernel_build/'build-result.json').read_text())
    image=(kernel_build/'Image').read_bytes()
    from pm_quiesce_binding import assert_scope as assert_quiesce_scope
    assert_quiesce_scope(kernel_build,result)
    from gic_roundtrip_binding import assert_scope as assert_gic_scope
    gic_roundtrip=assert_gic_scope(kernel_build,result)
    from dma_pm_binding import assert_scope as assert_dma_scope
    dma_pm_audit=assert_dma_scope(kernel_build,result)
    from ufs_pm_binding import assert_scope as assert_ufs_scope
    ufs_pm_audit=assert_ufs_scope(kernel_build,result)
    from iommu_pm_binding import assert_scope as assert_iommu_scope
    iommu_pm_audit=assert_iommu_scope(kernel_build,result)
    from abox_pm_binding import assert_scope as assert_abox_scope
    abox_pm_audit=assert_abox_scope(kernel_build,result)
    from abox_pmu_binding import assert_scope as assert_pmu_scope
    abox_pmu_audit=assert_pmu_scope(kernel_build,result)
    from pm_noirq_binding import assert_scope as assert_noirq_scope
    pm_noirq=assert_noirq_scope(kernel_build,result)
    from pmu_settle_binding import assert_scope as assert_settle_scope
    pmu_settle=assert_settle_scope(kernel_build,result)
    from pm_cpus_binding import assert_scope as assert_cpu_scope
    pm_cpus=assert_cpu_scope(kernel_build,result)
    from pm_post_arch_binding import assert_scope as assert_post_scope
    pm_post_arch=assert_post_scope(kernel_build,result)
    from pm_edge_binding import assert_scope as assert_edge_scope,validate_model as validate_edge
    pm_edge=assert_edge_scope(kernel_build,result)
    if pm_edge:validate_edge(kernel_build,result)
    from pm_callbacks_binding import assert_scope as assert_callbacks_scope,validate_model as validate_callbacks
    pm_callbacks=assert_callbacks_scope(kernel_build,result)
    if pm_callbacks:validate_callbacks(kernel_build,result)
    from pm_preconditions_binding import assert_scope as assert_preconditions_scope,validate_model as validate_preconditions
    pm_preconditions=assert_preconditions_scope(kernel_build,result)
    if pm_preconditions:validate_preconditions(kernel_build,result)
    from pm_branch_binding import assert_scope as assert_branch_scope,validate_model as validate_branch
    pm_branch=assert_branch_scope(kernel_build,result)
    if pm_branch:validate_branch(kernel_build,result)
    from pmu_failure_binding import validate as validate_failure
    pmu_failure=validate_failure(kernel_build,result)
    from pm_irq_binding import assert_scope as assert_irq_scope,validate_model as validate_irq
    pm_irq=assert_irq_scope(kernel_build,result)
    if pm_irq:validate_irq(kernel_build,result)
    if result.get('build_passed') is not True or result.get('early_xnu_reservation') is not True:
        raise ValueError('Successful reservation kernel build required')
    digest=hashlib.sha256(image).hexdigest()
    if digest!=result['image_sha256'] or digest!=json.loads((packages/'package-result.json').read_text())['kernel_image_sha256']:
        raise ValueError('Kernel source artifact and package differ')
    evidence_id=result.get('reservation_evidence_id')
    access=result.get('window_access_diagnostic') is True
    xnu_stage=result.get('xnu_payload_stage_diagnostic') is True
    cpu_cache=result.get('cpu_cache_roundtrip_diagnostic') is True
    pm_timer=result.get('pm_timer_diagnostic') is True
    pm_quiesce=result.get('pm_quiesce_diagnostic') is True
    if pm_quiesce and (not pm_timer or result.get('pm_quiesce_evidence_version')!=1):
        raise ValueError('Invalid PM quiesce build contract')
    auto_return=result.get('auto_return_diagnostic') is True
    if pm_timer and (not cpu_cache or result.get('pm_timer_evidence_version')!=1):raise ValueError('Invalid PM/timer batch contract')
    if cpu_cache and not xnu_stage:raise ValueError('CPU/cache batch requires XNU staging')
    if cpu_cache and result.get('cpu_cache_evidence_version')!=1:raise ValueError('Unsupported CPU/cache evidence version')
    if xnu_stage and not access:raise ValueError('XNU staging requires the verified window-access diagnostic')
    paired=json.loads((packages/'package-result.json').read_text(encoding='utf-8'))
    if paired.get('kernel_image_sha256')!=digest:
        raise ValueError('Diagnostic packages do not match this kernel Image')
    if (paired.get('window_access_diagnostic') is True)!=access or \
       (paired.get('xnu_payload_stage_diagnostic') is True)!=xnu_stage:
        raise ValueError('Diagnostic package scope differs from this kernel build')
    if (paired.get('cpu_cache_roundtrip_diagnostic') is True)!=cpu_cache:
        raise ValueError('CPU/cache package and kernel scope differ')
    if (paired.get('auto_return_diagnostic') is True)!=auto_return:raise ValueError('Auto-return package and build scope differ')
    cycle=paired.get('auto_cycle_token')
    if auto_return and (result.get('auto_return_evidence_version')!=1 or not re.fullmatch(r'[0-9a-f]{32}',cycle or '')):raise ValueError('Invalid auto-return cycle contract')
    if (paired.get('pm_timer_diagnostic') is True)!=pm_timer:raise ValueError('PM/timer package and kernel scope differ')
    if bool(paired.get('pm_quiesce_diagnostic'))!=pm_quiesce or (pm_quiesce and paired.get('pm_quiesce_evidence_version')!=1):
        raise ValueError('PM quiesce package and kernel contract differs')
    if bool(paired.get('dma_pm_audit_diagnostic'))!=dma_pm_audit or (dma_pm_audit and paired.get('dma_pm_audit_evidence_version')!=1):
        raise ValueError('DMA PM package and kernel contract differs')
    if bool(paired.get('ufs_pm_audit_diagnostic'))!=ufs_pm_audit or (ufs_pm_audit and paired.get('ufs_pm_audit_evidence_version')!=2):
        raise ValueError('UFS PM package and kernel contract differs')
    if bool(paired.get('iommu_pm_audit_diagnostic'))!=iommu_pm_audit or (iommu_pm_audit and paired.get('iommu_pm_audit_evidence_version')!=2):
        raise ValueError('IOMMU PM package and kernel contract differs')
    if abox_pm_audit and paired.get('abox_failed_fw_resume_guard') is not True:raise ValueError('Failed-firmware guard scope differs')
    if bool(paired.get('abox_pm_audit_diagnostic'))!=abox_pm_audit or (abox_pm_audit and paired.get('abox_pm_audit_evidence_version')!=8):
        raise ValueError('ABOX package and kernel scope differs')
    if bool(paired.get('pm_noirq_diagnostic'))!=pm_noirq or (pm_noirq and paired.get('pm_noirq_evidence_version')!=1):raise ValueError('Noirq package/kernel scope differs')
    if bool(paired.get('pmu_settle_diagnostic'))!=pmu_settle or (pmu_settle and paired.get('pmu_settle_evidence_version')!=1):raise ValueError('Timed PMU package/kernel scope differs')
    if bool(paired.get('pm_cpus_diagnostic'))!=pm_cpus or (pm_cpus and paired.get('pm_cpus_evidence_version')!=1):raise ValueError('CPU noirq package/kernel scope differs')
    if bool(paired.get('pm_post_arch_diagnostic'))!=pm_post_arch or (pm_post_arch and paired.get('pm_post_arch_evidence_version')!=1):raise ValueError('Post-PM CPU package/kernel scope differs')
    if bool(paired.get('pm_edge_inventory_diagnostic'))!=pm_edge or (pm_edge and paired.get('pm_edge_inventory_evidence_version')!=1):raise ValueError('PM edge package/kernel scope differs')
    if bool(paired.get('pm_callbacks_diagnostic'))!=pm_callbacks or (pm_callbacks and paired.get('pm_callbacks_evidence_version')!=1):raise ValueError('Callback package/kernel scope differs')
    if bool(paired.get('pm_preconditions_diagnostic'))!=pm_preconditions or (pm_preconditions and paired.get('pm_preconditions_version')!=1):raise ValueError('Preconditions package/kernel scope differs')
    if bool(paired.get('pm_branch_diagnostic'))!=pm_branch or (pm_branch and paired.get('pm_branch_version')!=1):raise ValueError('Branch package/kernel scope differs')
    if bool(paired.get('pmu_failure_restore'))!=pmu_failure or (pmu_failure and paired.get('pmu_failure_restore_version')!=1):raise ValueError('Failure guard package/kernel scope differs')
    if bool(paired.get('pm_irq_diagnostic'))!=pm_irq or (pm_irq and paired.get('pm_irq_evidence_version')!=1):raise ValueError('CPU0 IRQ package/kernel scope differs')
    if bool(paired.get('abox_pmu_audit_diagnostic'))!=abox_pmu_audit or (abox_pmu_audit and paired.get('abox_pmu_audit_evidence_version')!=3):raise ValueError('PMU package/kernel scope differs')
    if xnu_stage and (paired.get('xnu_payload_sha256')!=result.get('xnu_payload_sha256') or
                      paired.get('xnu_payload_size')!=result.get('xnu_payload_size')):
        raise ValueError('XNU payload package and kernel build differ')
    if access and (evidence_id is None or result.get('window_access_evidence_version')!=1):
        raise ValueError('Window access requires build-bound reservation and access evidence versions')
    if xnu_stage and (result.get('xnu_payload_size') is None or
                      not re.fullmatch(r'[0-9a-f]{64}',result.get('xnu_payload_sha256',''))):
        raise ValueError('XNU staging requires a build-bound payload size and SHA256')
    if evidence_id is not None:
        if (result.get('reservation_evidence_version')!=2 or
            not re.fullmatch(r'[0-9a-f]{32}',evidence_id) or image.count(evidence_id.encode())!=1):
            raise ValueError('Unique build evidence ID must be embedded in verified Image')
    banners=re.findall(rb'Linux version 4\.14\.113-note10-reserve-pc [^\x00\r\n]+',image)
    if len(banners)!=1:raise ValueError('Expected unique source kernel banner')
    banner=banners[0].decode('ascii')
    state=preflight(adb)
    if not adb.text('shell','getprop','ro.bootloader').startswith('N976N'):raise ValueError('N976N required')
    out=ROOT/'note10/private/device-observations'/('reservation-test-'+uuid.uuid4().hex[:12]);out.mkdir(parents=True)
    logs={}
    for name,remote in (('last_kmsg.txt','/proc/last_kmsg'),('console-ramoops-0','/sys/fs/pstore/console-ramoops-0'),
                        ('dmesg-ramoops-0','/sys/fs/pstore/dmesg-ramoops-0')):
        try:
            # Some recovery adbd versions return success for exec-out even
            # when cat fails. Never classify a missing-file error as a log.
            adb.call('shell','test','-r',remote)
            data=adb.call('exec-out','cat',remote,timeout=60)
        except RuntimeError:continue
        if not 0<len(data)<=16*1024*1024:continue
        (out/name).write_bytes(data);logs[name]=data
    report={'directory':str(out),'twrp_version':state['twrp_version'],'kernel_image_sha256':digest,
            'partition_writes':False,'rebooted':False,'xnu_executed':False,
            'previous_boot_reservation_observed':False,
            'window_access_required':access,'previous_boot_window_access_observed':False,
            'xnu_payload_stage_required':xnu_stage,'previous_boot_xnu_payload_stage_observed':False,
            'cpu_cache_roundtrip_required':cpu_cache,'previous_boot_cpu_cache_roundtrip_observed':False,
            'pm_timer_required':pm_timer,'previous_boot_pm_timer_observed':False,
            'logs_sha256':{n:hashlib.sha256(d).hexdigest() for n,d in logs.items()},
            'gic_roundtrip_required':gic_roundtrip,'previous_boot_gic_roundtrip_observed':False,
            'dma_pm_audit_required':dma_pm_audit,'previous_boot_dma_pm_audit_observed':False,
            'ufs_pm_audit_required':ufs_pm_audit,'previous_boot_ufs_pm_audit_observed':False,
            'iommu_pm_audit_required':iommu_pm_audit,'previous_boot_iommu_pm_audit_observed':False,
            'abox_pm_audit_required':abox_pm_audit,'previous_boot_abox_pm_audit_observed':False,
            'pm_late_noirq_required':pm_noirq,'previous_boot_pm_late_noirq_observed':False,
            'pmu_settle_required':pmu_settle,'previous_boot_pmu_settle_observed':False,
            'pm_cpus_noirq_required':pm_cpus,'previous_boot_pm_cpus_noirq_observed':False,
            'cpu_stop_pmu_domains_required':pm_cpus,'previous_boot_cpu_stop_pmu_domains_observed':False,
            'pm_cpus_timers_required':pm_cpus,'previous_boot_pm_cpus_timers_observed':False,
            'pm_cpus_arch_restore_required':pm_post_arch,'previous_boot_pm_cpus_arch_restore_observed':False,
            'pm_cpus_payload_readback_required':pm_post_arch,'previous_boot_pm_cpus_payload_readback_observed':False,
            'dma_noirq_coverage_required':pm_edge,'previous_boot_dma_noirq_coverage_observed':False,
            'iommu_noirq_inventory_required':pm_edge,'previous_boot_iommu_noirq_inventory_observed':False,
            'syscore_inventory_required':pm_edge,'previous_boot_syscore_inventory_observed':False,
            'cpu_pm_notifier_inventory_required':pm_callbacks,'previous_boot_cpu_pm_notifier_inventory_observed':False,
            'generic_irq_callback_inventory_required':pm_callbacks,'previous_boot_generic_irq_callback_inventory_observed':False,
            'clocksource_callback_inventory_required':pm_callbacks,'previous_boot_clocksource_callback_inventory_observed':False,
            'clockevent_callback_inventory_required':pm_callbacks,'previous_boot_clockevent_callback_inventory_observed':False,
            'cpu0_pm_software_context_required':pm_preconditions,'previous_boot_cpu0_pm_software_context_observed':False,
            'cpu0_gic_restore_inputs_required':pm_preconditions,'previous_boot_cpu0_gic_restore_inputs_observed':False,
            'cpu0_pmu_branch_audit_required':pm_branch,'previous_boot_cpu0_pmu_branch_audit_observed':False,
            'cpu0_gic_priority_footprint_required':pm_branch,'previous_boot_cpu0_gic_priority_footprint_observed':False,
            'cpu0_irq_arch_timer_required':pm_irq,'previous_boot_cpu0_irq_arch_timer_observed':False,
            'cpu0_irq_gic_readback_required':pm_irq,'previous_boot_cpu0_irq_gic_readback_observed':False,
            'noirq_pmu_domains_required':pm_noirq,'previous_boot_noirq_pmu_domains_observed':False,
            'fsys0a_policy_required':abox_pmu_audit,'previous_boot_fsys0a_policy_observed':False,
            'pmu_domain_status_required':abox_pmu_audit,'previous_boot_pmu_domain_status_observed':False,
            'abox_pmu_audit_required':abox_pmu_audit,'previous_boot_abox_pmu_audit_observed':False,
            'log_selections':{},'decode_failures':{}}
    for name,data in logs.items():
        try:
            selected,selection=select_latest_boot(data,banner,allow_panic_corroboration=evidence_id is not None,
                boot_binding_id=evidence_id if result.get('boot_binding_evidence_version')==1 else None)
            if auto_return:
                from decode_auto_return import select_cycle_log
                selected,cycle_offset=select_cycle_log(selected,evidence_id,cycle)
                selection['cycle_arm_offset']=cycle_offset
                selection['byte_start']+=cycle_offset
                selection['selected_sha256']=hashlib.sha256(selected).hexdigest()
                selection['cycle_token']=cycle
            report['log_selections'][name]=selection
            if selection['byte_start']:
                selected_name=name+'.selected-boot.txt'
                (out/selected_name).write_bytes(selected)
                selection['selected_file']=selected_name
            text=selected.decode(errors='replace')
            if result.get('pm_failure_stage_evidence_version')==1:
                from decode_pm_timer import decode_stages
                report['pm_failure_stage_observation']=decode_stages(text,evidence_id)
            if pm_quiesce:
                from decode_pm_timer import decode_quiescence
                report['pm_quiesce_observation']=decode_quiescence(text,evidence_id,require_success=False)
            if evidence_id is None and banner not in text:
                raise ValueError('Exact source build banner not observed')
            observation=decode_frames(text,evidence_id) if evidence_id else decode(text)
            report['previous_boot_reservation_observed']=True
            (out/'reservation-observation.json').write_text(json.dumps(observation,indent=2),encoding='utf-8')
            if access:
                observation=decode_access(text,evidence_id)
                report['previous_boot_window_access_observed']=True
            if xnu_stage:
                stage_observation=decode_xnu_stage(text,evidence_id,result['xnu_payload_sha256'],
                                                   result['xnu_payload_size'])
                report['previous_boot_xnu_payload_stage_observed']=True
                report['xnu_payload_stage_observation']=stage_observation
                observation['xnu_payload_stage']=stage_observation
                observation['xnu_payload_executed']=False
                observation['kernel_to_xnu_transfer_verified']=False
            if cpu_cache:
                cpu_observation=decode_cpu_cache(text,evidence_id,result['xnu_payload_sha256'],result['xnu_payload_size'])
                report['previous_boot_cpu_cache_roundtrip_observed']=True
                observation['cpu_cache_roundtrip']=cpu_observation
            if pm_timer:
                observation['pm_timer']=decode_pm_timer(text,evidence_id,result['xnu_payload_sha256'],result['xnu_payload_size'],require_quiesce=pm_quiesce)
                report['previous_boot_pm_timer_observed']=True
            if gic_roundtrip:
                from decode_gic_roundtrip import decode as decode_gic
                observation['gic_cpu_roundtrip']=decode_gic(text,evidence_id)
                report['previous_boot_gic_roundtrip_observed']=True
            if dma_pm_audit:
                observation['dma_pm_audit']=decode_dma_pm_observation(text,evidence_id,observation['pm_timer'])
                report['previous_boot_dma_pm_audit_observed']=True
            if ufs_pm_audit:
                observation['ufs_pm_audit']=decode_ufs_pm_observation(text,evidence_id,observation['pm_timer'])
                report['previous_boot_ufs_pm_audit_observed']=True
            if iommu_pm_audit:
                observation['iommu_pm_audit']=decode_iommu_pm_observation(text,evidence_id,observation['pm_timer'])
                report['previous_boot_iommu_pm_audit_observed']=True
            if abox_pm_audit:
                observation['abox_pm_audit']=decode_abox_pm_observation(text,evidence_id,observation['pm_timer'])
                report['previous_boot_abox_pm_audit_observed']=True
            if abox_pmu_audit:
                from decode_abox_pmu import decode as decode_pmu
                observation['abox_pmu_audit']=decode_pmu(text,evidence_id,pm_completed_generation(observation['pm_timer']))
                report['previous_boot_abox_pmu_audit_observed']=True
                report['previous_boot_pmu_domain_status_observed']=observation['abox_pmu_audit']['pmu_domain_status_observed']
                report['previous_boot_fsys0a_policy_observed']=observation['abox_pmu_audit']['fsys0a_policy_observed']
            if pm_noirq:
                from decode_pm_noirq import decode as decode_noirq
                observation['pm_noirq']=decode_noirq(text,evidence_id,pm_completed_generation(observation['pm_timer']),cpu_roundtrip=pm_cpus)
                report['previous_boot_pm_late_noirq_observed']=observation['pm_noirq']['pm_late_noirq_roundtrip_observed']
                report['previous_boot_noirq_pmu_domains_observed']=observation['pm_noirq']['noirq_pmu_domain_status_observed']
            if pmu_settle:
                from decode_pmu_settle import decode as decode_settle
                observation['pmu_settle']=decode_settle(text,evidence_id,pm_completed_generation(observation['pm_timer']))
                report['previous_boot_pmu_settle_observed']=observation['pmu_settle']['pmu_settled_post_resume_observed']
            if pm_cpus:
                from decode_pm_cpus import decode as decode_cpus,decode_timers
                observation['pm_cpus']=decode_cpus(text,evidence_id,pm_completed_generation(observation['pm_timer']))
                observation['pm_cpus']['timers']=decode_timers(text,evidence_id,pm_completed_generation(observation['pm_timer']))
                report['previous_boot_pm_cpus_noirq_observed']=observation['pm_cpus']['pm_cpus_noirq_roundtrip_observed']
                report['previous_boot_cpu_stop_pmu_domains_observed']=observation['pm_cpus']['cpu_stop_pmu_domains_observed']
                report['previous_boot_pm_cpus_timers_observed']=observation['pm_cpus']['timers']['pm_cpus_timer_restore_observed']
            if pm_post_arch:
                from decode_pm_post_arch import decode as decode_post_arch
                observation['pm_post_arch']=decode_post_arch(text,evidence_id,pm_completed_generation(observation['pm_timer']),cpu_observation,result['xnu_payload_size'])
                report['previous_boot_pm_cpus_arch_restore_observed']=observation['pm_post_arch']['pm_cpus_arch_restore_observed']
                report['previous_boot_pm_cpus_payload_readback_observed']=observation['pm_post_arch']['pm_cpus_payload_readback_observed']
            if pm_edge:
                from decode_pm_edge import decode as decode_edge
                observation['pm_edge']=decode_edge(text,evidence_id,pm_completed_generation(observation['pm_timer']),observation['dma_pm_audit'],observation['iommu_pm_audit'])
                for key in ('dma_noirq_coverage','iommu_noirq_inventory','syscore_inventory'):
                    report['previous_boot_'+key+'_observed']=observation['pm_edge'][key]
            if pm_irq:
                from decode_pm_irq import decode as decode_irq
                observation['pm_irq']=decode_irq(text,evidence_id,pm_completed_generation(observation['pm_timer']),cpu_observation,observation['pm_cpus']['timers'])
                for key in ('cpu0_irq_arch_timer','cpu0_irq_gic_readback'):
                    report['previous_boot_'+key+'_observed']=observation['pm_irq'][key]
            if pm_callbacks:
                from decode_pm_callbacks import decode as decode_callbacks
                observation['pm_callbacks']=decode_callbacks(text,evidence_id,pm_completed_generation(observation['pm_timer']))
                for key in ('cpu_pm_notifier_inventory', 'generic_irq_callback_inventory', 'clocksource_callback_inventory', 'clockevent_callback_inventory'):
                    report['previous_boot_'+key+'_observed']=observation['pm_callbacks'][key]
            if pm_preconditions:
                from decode_pm_preconditions import decode as decode_preconditions
                observation['pm_preconditions']=decode_preconditions(text,evidence_id,pm_completed_generation(observation['pm_timer']))
                report['previous_boot_cpu0_pm_software_context_observed']=True
                report['previous_boot_cpu0_gic_restore_inputs_observed']=True
            if pm_branch:
                from decode_pm_branch import decode as decode_branch
                observation['pm_branch']=decode_branch(text,evidence_id,pm_completed_generation(observation['pm_timer']),observation['pm_preconditions'])
                for key in ('cpu0_pmu_branch_audit','cpu0_gic_priority_footprint'):
                    report['previous_boot_'+key+'_observed']=observation['pm_branch'][key]
        except ValueError as error:
            report['decode_failures'][name]=str(error);continue
        (out/'reservation-observation.json').write_text(json.dumps(observation,indent=2),encoding='utf-8')
        report.update(previous_boot_reservation_observed=True,evidence_file=name,
                      idle_init_marker_observed='N10INIT1 IDLE ' in text,
                      android_root_mount_message_observed='VFS: Mounted root' in text,
                      kernel_panic_observed='Kernel panic' in text,
                      init_execution_failure_observed='Failed to execute /init' in text or 'No working init found' in text)
        try:
            caps=decode_caps(text)
            (out/'cpu-capabilities.json').write_text(json.dumps(caps,indent=2),encoding='utf-8')
            report['observed_cpus']=caps['observed_cpus']
        except ValueError as error:report['cpu_decode_failure']=str(error)
        break
    report['diagnostic_passed']=(report['previous_boot_reservation_observed'] and
                                 (not access or report['previous_boot_window_access_observed']) and
                                 (not xnu_stage or report['previous_boot_xnu_payload_stage_observed']) and
                                 (not cpu_cache or report['previous_boot_cpu_cache_roundtrip_observed']) and
                                 (not pm_timer or report['previous_boot_pm_timer_observed']) and
                                 (not gic_roundtrip or report['previous_boot_gic_roundtrip_observed']) and
                                 (not dma_pm_audit or report['previous_boot_dma_pm_audit_observed']) and
                                 (not ufs_pm_audit or report['previous_boot_ufs_pm_audit_observed']) and
                                 (not iommu_pm_audit or report['previous_boot_iommu_pm_audit_observed']) and
                                 (not abox_pm_audit or report['previous_boot_abox_pm_audit_observed']) and
                                 (not abox_pmu_audit or (report['previous_boot_abox_pmu_audit_observed'] and report['previous_boot_pmu_domain_status_observed'] and report['previous_boot_fsys0a_policy_observed'])) and
                                 (not pm_noirq or (report['previous_boot_pm_late_noirq_observed'] and report['previous_boot_noirq_pmu_domains_observed'])) and
                                 (not pmu_settle or report['previous_boot_pmu_settle_observed']) and
                                 (not pm_cpus or (report['previous_boot_pm_cpus_noirq_observed'] and report['previous_boot_cpu_stop_pmu_domains_observed'] and report['previous_boot_pm_cpus_timers_observed'])) and
                                 (not pm_post_arch or (report['previous_boot_pm_cpus_arch_restore_observed'] and report['previous_boot_pm_cpus_payload_readback_observed'])) and
                                 (not pm_edge or all(report['previous_boot_'+key+'_observed'] for key in ('dma_noirq_coverage','iommu_noirq_inventory','syscore_inventory'))) and
                                 (not pm_irq or all(report['previous_boot_'+key+'_observed'] for key in ('cpu0_irq_arch_timer','cpu0_irq_gic_readback'))) and
                                 (not pm_callbacks or all(report['previous_boot_'+key+'_observed'] for key in ('cpu_pm_notifier_inventory', 'generic_irq_callback_inventory', 'clocksource_callback_inventory', 'clockevent_callback_inventory'))) and
                                 (not pm_preconditions or all(report['previous_boot_'+key+'_observed'] for key in ('cpu0_pm_software_context','cpu0_gic_restore_inputs'))) and
                                 (not pm_branch or all(report['previous_boot_'+key+'_observed'] for key in ('cpu0_pmu_branch_audit','cpu0_gic_priority_footprint'))))
    report['evaluation_items']={}
    for item in ('reservation','window_access','xnu_payload_stage','cpu_cache_roundtrip','pm_timer','gic_roundtrip','dma_pm_audit','ufs_pm_audit','iommu_pm_audit','abox_pm_audit','abox_pmu_audit','pmu_domain_status','fsys0a_policy','pm_late_noirq','noirq_pmu_domains','pmu_settle','pm_cpus_noirq','cpu_stop_pmu_domains','pm_cpus_timers','pm_cpus_arch_restore','pm_cpus_payload_readback','dma_noirq_coverage','iommu_noirq_inventory','syscore_inventory','cpu0_irq_arch_timer','cpu0_irq_gic_readback','cpu_pm_notifier_inventory','generic_irq_callback_inventory','clocksource_callback_inventory','clockevent_callback_inventory','cpu0_pm_software_context','cpu0_gic_restore_inputs','cpu0_pmu_branch_audit','cpu0_gic_priority_footprint'):
        required=item=='reservation' or report[item+'_required']
        observed=report['previous_boot_'+item+'_observed']
        report['evaluation_items'][item]={'required':required,'status':'passed' if observed else ('failed' if required else 'not_requested')}
    (out/'capture-result.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--packages',type=Path,required=True);parser.add_argument('--kernel-build',type=Path,required=True)
    args=parser.parse_args();r=collect(args.packages,args.kernel_build,Adb(ROOT/'host-tools/platform-tools/adb.exe'))
    print(json.dumps({'directory':r['directory'],'previous_boot_reservation_observed':r['previous_boot_reservation_observed'],
                      'previous_boot_window_access_observed':r['previous_boot_window_access_observed'],
                      'previous_boot_xnu_payload_stage_observed':r['previous_boot_xnu_payload_stage_observed'],
                      'diagnostic_passed':r['diagnostic_passed'],
                      'partition_writes':False,'xnu_executed':False}))
    if not r['diagnostic_passed']:raise SystemExit(1)
