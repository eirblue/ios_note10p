"""Bind PM edge inventories to config, Image, source and actual-C models."""
import hashlib
import json
from pathlib import Path
from prepare_pm_edge import HERE, PINS, SOURCES
MARKERS=(b'N10EDG1',b'N10EIM1',b'N10EID1',b'N10ESC1',b'N10EOK1',b'N10EER1')

def assert_scope(root,build):
    root=Path(root);config_path=root/'handoff.config'
    config=config_path.read_bytes().splitlines() if config_path.exists() else []
    image=(root/'Image').read_bytes()
    enabled=b'CONFIG_NOTE10_PM_EDGE_INVENTORY=y' in config
    if any(enabled!=(marker in image) for marker in MARKERS) or enabled!=(build.get('pm_edge_inventory_diagnostic') is True):raise ValueError('PM edge Image/config/build scope differs')
    if enabled and (build.get('pm_edge_inventory_evidence_version')!=1 or any(build.get(k) is not True for k in ('pm_post_arch_diagnostic','pm_cpus_diagnostic','dma_pm_audit_diagnostic','iommu_pm_audit_diagnostic')) or any(x not in config for x in (b'CONFIG_KALLSYMS=y',b'CONFIG_NOTE10_PM_POST_ARCH=y',b'CONFIG_NOTE10_PM_CPUS_TEST=y',b'CONFIG_NOTE10_DMA_PM_AUDIT=y',b'CONFIG_NOTE10_IOMMU_PM_AUDIT=y'))):raise ValueError('Incomplete PM edge prerequisites')
    return enabled

def validate_model(root,build):
    if not assert_scope(root,build):return False
    actual={n:hashlib.sha256((HERE/n).read_bytes()).hexdigest() for n in SOURCES}
    if build.get('pm_edge_sources_sha256')!=actual or build.get('pm_edge_source_pins')!=PINS:raise ValueError('PM edge source binding differs')
    from pm_irq_binding import assert_scope as assert_irq_scope
    irq_enabled=assert_irq_scope(root,build)
    prepared=build.get('pm_edge_prepared_sha256')
    expected_helpers={
       'drivers/base/power/note10_pm_edge_dma.c':'pm_edge_dma_backend.c',
       'drivers/iommu/note10_pm_edge_iommu.c':'pm_edge_iommu_backend.c',
       'drivers/base/note10_pm_edge_syscore.c':'pm_edge_syscore_backend.c',
       'arch/arm64/mm/note10_pm_edge_probe.c':'pm_edge_probe.c',
       **{'include/linux/note10_pm_edge_'+k+'.h':'pm_edge_'+k+'_contract.h' for k in ('dma','iommu','syscore')},
    }
    expected_paths=set(expected_helpers)|{'drivers/base/power/note10_dma_pm.c','kernel/power/note10_pm_noirq.c',
      'arch/arm64/mm/note10_pm_timer_roundtrip.c','kernel/power/suspend.c','kernel/power/Kconfig',
      'drivers/base/power/main.c','drivers/iommu/exynos-iommu.c','drivers/base/syscore.c'}
    if (not isinstance(prepared,dict) or set(prepared)!=expected_paths or
        any(not isinstance(v,str) or len(v)!=64 or any(c not in '0123456789abcdef' for c in v) for v in prepared.values()) or
        any(prepared[k]!=actual[v] for k,v in expected_helpers.items()) or
        prepared['kernel/power/suspend.c']!='2bad7dc2695559e4df992a6571fb2c79cc4879384819f946254da4519049efde' or
        prepared['drivers/base/power/main.c']!='271c104727a0266b9803c667fe5bddb8da679cc3f54d7cd5052d163b54e66270' or
        prepared['drivers/iommu/exynos-iommu.c']!='121f9001105ac9456418269fa31b7bd4a12726dbefd924c5c5c27c1564889260' or
        prepared['drivers/base/syscore.c']!='d15cab08efd46310218cfb08a056d16362f77a0252c3bce2c36158ae3eddf0d6' or
        (not irq_enabled and prepared['kernel/power/Kconfig']!=build.get('pm_quiesce_patched_sha256',{}).get('kernel/power/Kconfig'))):
        raise ValueError('PM edge prepared helper binding differs')
    root=Path(root)
    cases=(('dma',18,{0,14,21,28},'test_pm_edge_dma_native.py'),('iommu',32,{0,14,19,21,29},'test_pm_edge_iommu_native.py'),('syscore',25,{0,15,24},'test_pm_edge_syscore_native.py'))
    modes={'dma':{0,1,3,4,5,6,14,*range(20,31)},'iommu':{0,*range(1,15),*range(16,33)},'syscore':set(range(25))}
    for kind,count,accepted,harness in cases:
        model=json.loads((root/('pm-edge-'+kind+'-model/result.json')).read_text())
        outcomes=model.get('outcomes');expected={k:actual[k] for k in ('pm_edge_'+kind+'_contract.h','pm_edge_'+kind+'_backend.c')}
        if (model.get('passed') is not True or model.get('cases')!=count or model.get('actual_backend_executed') is not True or
            model.get('source_sha256')!=expected or model.get('harness_sha256')!=actual[harness] or not isinstance(outcomes,list) or len(outcomes)!=count or
            {x.get('mode') for x in outcomes}!=modes[kind] or any(x.get('accepted')!=(x.get('mode') in accepted) for x in outcomes)):
            raise ValueError('PM edge actual-C model differs: '+kind)
        if kind=='iommu' and model.get('legacy_backend_same_translation_unit') is not True:raise ValueError('IOMMU combined TU proof missing')
    integration=json.loads((root/'pm-edge-integration-model/result.json').read_text())
    prepared=build.get('pm_edge_prepared_sha256',{});src=integration.get('source_sha256',{})
    expected={'dma':prepared.get('drivers/base/power/note10_dma_pm.c'),'noirq':prepared.get('kernel/power/note10_pm_noirq.c'),
              'worker':prepared.get('arch/arm64/mm/note10_pm_timer_roundtrip.c'),'suspend':prepared.get('kernel/power/suspend.c'),
              'edge':actual['pm_edge_dma_backend.c'],'producer':actual['pm_edge_probe.c'],
              'kconfig':prepared.get('kernel/power/Kconfig'),'pm_main':prepared.get('drivers/base/power/main.c'),
              'iommu_driver':prepared.get('drivers/iommu/exynos-iommu.c'),'syscore':prepared.get('drivers/base/syscore.c')}
    if (integration.get('passed') is not True or integration.get('cases')!=22 or integration.get('source_sha256')!=expected or
        integration.get('harness_sha256')!=actual['test_pm_edge_integration_native.py'] or integration.get('hardware_verified') is not False or
        any(integration.get(k) is not True for k in ('actual_prepared_dma_hook_executed','actual_prepared_noirq_hook_executed',
          'actual_suspend_caller_and_enter_executed','actual_prepared_worker_executed','actual_prepared_producer_executed','disabled_profile_matches_enabled_flow'))):
        raise ValueError('PM edge prepared integration proof differs')
    rows=integration.get('outcomes')
    expected_names={*(f'suspend-flow-{n}' for n in (0,1,2,19)),*(f'worker-{n}' for n in range(9)),*(f'producer-{n}' for n in range(9))}
    if not isinstance(rows,list) or len(rows)!=22 or {r.get('name') for r in rows}!=expected_names or any(r.get('passed') is not True or r.get('mode')!=int(r['name'].rsplit('-',1)[1]) for r in rows):raise ValueError('PM edge integration cases differ')
    producer_logs={f'producer-{i}.log':hashlib.sha256((root/'pm-edge-integration-model'/f'producer-{i}.log').read_bytes()).hexdigest() for i in range(9)}
    if integration.get('producer_log_sha256')!=producer_logs:raise ValueError('PM edge actual producer logs differ')
    decoder=json.loads((root/'pm-edge-decoder-model/result.json').read_text())
    names={'baseline','runtime_change','missing_dma','bad_checksum','missing_identity','missing_callback','missing_status','duplicate','dma_conflict','iommu_conflict','callback_conflict','callback_mask','bad_phase','wrong_generation','bad_sentinel','bad_status','failure_bitmask',*(f'producer_failure_{i}' for i in range(1,8))}
    rows=decoder.get('outcomes')
    if (decoder.get('passed') is not True or decoder.get('harness_sha256')!=actual['test_pm_edge_decoder.py'] or decoder.get('decoder_sha256')!=actual['decode_pm_edge.py'] or decoder.get('cases')!=24 or decoder.get('producer_log_sha256')!=producer_logs or decoder.get('actual_producer_frames_decoded') is not True or not isinstance(rows,list) or len(rows)!=24 or {r.get('case') for r in rows}!=names or any(r.get('passed') is not True or r.get('accepted')!=(r.get('case') in ('baseline','runtime_change')) for r in rows)):
        raise ValueError('PM edge independent decoder proof differs')
    return True
