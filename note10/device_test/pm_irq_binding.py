"""Bind CPU0 IRQ observations to the actual Image, config, models and source."""
import hashlib,json
from pathlib import Path
from prepare_pm_irq import HERE,PINS,SOURCES,instrument_cpu
from prepare_pm_noirq import FINAL_SHA
MARKERS=(b'N10IAR1',b'N10ITR1',b'N10IGR1',b'N10IQR1')
FORBIDDEN=('GIC_NON_BANKED','TRACE_IRQFLAGS','DEBUG_SNAPSHOT_IRQ_DISABLED','DEBUG_SNAPSHOT_REG')

def assert_scope(root,build):
 root=Path(root);p=root/'handoff.config';config=p.read_bytes().splitlines() if p.exists() else [];image=(root/'Image').read_bytes()
 enabled=b'CONFIG_NOTE10_PM_IRQ_TEST=y' in config
 if any(enabled!=(m in image) for m in MARKERS) or enabled!=(build.get('pm_irq_diagnostic') is True):raise ValueError('Actual CPU0 IRQ Image/config scope differs')
 required=(b'CONFIG_NOTE10_PM_CPUS_TEST=y',b'CONFIG_NOTE10_PM_POST_ARCH=y',b'CONFIG_NOTE10_PM_EDGE_INVENTORY=y',b'CONFIG_NOTE10_GIC_ROUNDTRIP=y',b'CONFIG_ARM_GIC=y',b'CONFIG_ARM64_4K_PAGES=y',b'CONFIG_PREEMPT_COUNT=y',b'CONFIG_ARM64_VA_BITS=39',b'CONFIG_PGTABLE_LEVELS=3',b'# CONFIG_UNMAP_KERNEL_AT_EL0 is not set',b'# CONFIG_ARM64_SW_TTBR0_PAN is not set')
 if enabled and (build.get('pm_irq_evidence_version')!=1 or any(build.get(k) is not True for k in ('pm_cpus_diagnostic','pm_post_arch_diagnostic','pm_edge_inventory_diagnostic','gic_roundtrip_diagnostic')) or any(x not in config for x in required) or any(('CONFIG_'+n+'='+v).encode() in config for n in FORBIDDEN for v in ('y','m'))):raise ValueError('CPU0 IRQ prerequisites or debug config differ')
 return enabled

def validate_model(root,build):
 if not assert_scope(root,build):return False
 root=Path(root);actual={n:hashlib.sha256((HERE/n).read_bytes()).hexdigest() for n in SOURCES}
 if build.get('pm_irq_source_pins')!=PINS or build.get('pm_irq_sources_sha256')!=actual:raise ValueError('CPU0 IRQ source binding differs')
 from pm_callbacks_binding import assert_scope as assert_callbacks_scope
 callbacks_enabled=assert_callbacks_scope(root,build)
 prepared=build.get('pm_irq_prepared_sha256')
 prior_config=(build.get('pm_callbacks_intermediate_sha256',{}).get('kernel/power/Kconfig') if callbacks_enabled else build.get('pm_quiesce_patched_sha256',{}).get('kernel/power/Kconfig'))
 helpers={'include/linux/note10_pm_irq.h':'pm_irq_contract.h','kernel/power/note10_pm_irq.c':'pm_irq_backend.c','drivers/irqchip/note10_pm_irq_gic.c':'pm_irq_gic_backend.c','arch/arm64/mm/note10_pm_irq_probe.c':'pm_irq_probe.c'}
 expected=set(helpers)|{'kernel/power/note10_pm_cpus.c','arch/arm64/mm/note10_pm_timer_roundtrip.c','drivers/irqchip/irq-gic.c','kernel/power/suspend.c','kernel/power/Kconfig'}
 if not isinstance(prepared,dict) or set(prepared)!=expected or any(not isinstance(v,str) or len(v)!=64 or any(c not in '0123456789abcdef' for c in v) for v in prepared.values()) or any(prepared[k]!=actual[v] for k,v in helpers.items()) or prepared['kernel/power/suspend.c']!=FINAL_SHA or prepared['drivers/irqchip/irq-gic.c']!='2df647363116dbdf69860e7d8c2b8491a0b383f7020633f11dee4ca0f21ed9f5' or prepared['kernel/power/note10_pm_cpus.c']!=hashlib.sha256(instrument_cpu((HERE/'pm_cpus_backend.c').read_bytes())).hexdigest() or prepared['kernel/power/Kconfig']!=prior_config:
  raise ValueError('CPU0 IRQ prepared source differs')
 native=json.loads((root/'pm-irq-native-model/result.json').read_text());rows=native.get('outcomes')
 expected_sources={n:actual[n] for n in ('pm_irq_contract.h','pm_irq_backend.c','pm_irq_gic_backend.c','pm_irq_probe.c')}
 if (native.get('passed') is not True or native.get('cases')!=64 or native.get('source_sha256')!=expected_sources or native.get('harness_sha256')!=actual['test_pm_irq_native.py'] or native.get('hardware_verified') is not False or any(native.get(k) is not True for k in ('actual_irq_transaction_executed','actual_gic_observer_executed','actual_producer_executed','strict_decoder_verified','exact_read_allowlist','no_gic_writes')) or not isinstance(rows,list) or len(rows)!=64 or {r.get('mode') for r in rows}!=set(range(64)) or any(r.get('passed') is not True or r.get('accepted')!=(r.get('mode') in (0,19,53,55)) for r in rows)):
  raise ValueError('CPU0 IRQ native proof differs')
 decoder=json.loads((root/'pm-irq-decoder-model/result.json').read_text());rows=decoder.get('outcomes')
 names={'baseline','wrap','missing_arch','missing_timer','missing_gic','missing_summary','corrupt_checksum','mixed_generation','wrong_phase','mask_missing','daif_other_bits','restore_changed','saved_changed','preempt_wrong','cpu_wrong','online_wrong','ttbr_local','timer_changed','frequency_bad','gic_changed','gic_disabled','pmr_zero','dist_disabled','conflicting_copy','wrong_completion','baseline_mpidr','baseline_sctlr','baseline_tcr','baseline_mair','baseline_ttbr','cross_asid_allowed','timer_cross_bind','actual_failure','generation_overflow',*(f'gic_overflow_{k}' for k in ('ctlr','pmr','bpr','iidr','dist','typer'))}
 logs={f'mode-{i}.log':hashlib.sha256((root/'pm-irq-native-model'/f'mode-{i}.log').read_bytes()).hexdigest() for i in (0,19,11)}
 if (decoder.get('passed') is not True or decoder.get('cases')!=40 or decoder.get('harness_sha256')!=actual['test_pm_irq_decoder.py'] or decoder.get('decoder_sha256')!=actual['decode_pm_irq.py'] or decoder.get('native_log_sha256')!=logs or decoder.get('actual_producer_frames_decoded') is not True or not isinstance(rows,list) or len(rows)!=40 or {r.get('case') for r in rows}!=names or any(r.get('passed') is not True or r.get('accepted')!=(r.get('case') in ('baseline','wrap','cross_asid_allowed')) for r in rows)):
  raise ValueError('CPU0 IRQ decoder proof differs')
 integration=json.loads((root/'pm-irq-integration-model/result.json').read_text());rows=integration.get('outcomes')
 sources={'cpu':prepared['kernel/power/note10_pm_cpus.c'],'worker':prepared['arch/arm64/mm/note10_pm_timer_roundtrip.c'],
          'noirq':build.get('pm_edge_prepared_sha256',{}).get('kernel/power/note10_pm_noirq.c'),
          'irq':prepared['kernel/power/note10_pm_irq.c'],'gic':prepared['drivers/irqchip/note10_pm_irq_gic.c']}
 names={*(f'caller-{n}' for n in (0,1,2,3,4,6,7,8)),*(f'noirq-{n}' for n in (0,3)),*(f'worker-{n}' for n in range(11))}
 if (integration.get('passed') is not True or integration.get('cases')!=21 or integration.get('source_sha256')!=sources or
     integration.get('harness_sha256')!=actual['test_pm_irq_integration_native.py'] or integration.get('hardware_verified') is not False or
     any(integration.get(k) is not True for k in ('actual_prepared_cpu_caller_executed','actual_prepared_noirq_hook_executed','actual_prepared_worker_executed','gic_failure_blocks_later_observers','mandatory_cpu_restore_on_failures')) or
     not isinstance(rows,list) or len(rows)!=21 or {r.get('name') for r in rows}!=names or any(r.get('passed') is not True or r.get('mode')!=int(r['name'].rsplit('-',1)[1]) for r in rows)):
  raise ValueError('CPU0 IRQ prepared caller/worker proof differs')
 return True
