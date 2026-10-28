"""Verify the v37 prepared tree against prior layers and immutable inputs."""
import hashlib
from pathlib import Path
from prepare_pm_preconditions import HERE,PINS,FILES,GETTERS,KCONFIG,includes

def sha(raw): return hashlib.sha256(raw).hexdigest()
def reverse(raw,new,old):
 if raw.count(new)!=1: raise ValueError('precondition composition differs')
 return raw.replace(new,old,1)
def validate_prepared(snapshot,build):
 root=Path(snapshot); final=build['pm_preconditions_prepared_sha256']; prior=build['pm_preconditions_intermediate_sha256']
 changed=set(PINS)|set(GETTERS)|{'kernel/power/note10_pm_noirq.c','kernel/power/note10_pm_cpus.c','kernel/power/note10_pm_irq.c','arch/arm64/mm/note10_pm_timer_roundtrip.c','kernel/power/Kconfig'}
 if set(prior)!=changed or set(final)!=changed|set(FILES) or build.get('pm_preconditions_pins')!=PINS: raise ValueError('precondition source set differs')
 for name,digest in final.items():
  path=root/name
  if path.is_symlink() or sha(path.read_bytes())!=digest:raise ValueError('prepared file differs: '+name)
 for name,source in FILES.items():
  if (root/name).read_bytes()!=(HERE/source).read_bytes():raise ValueError('helper differs: '+name)
 for name in changed:
  raw=(root/name).read_bytes()
  if name in GETTERS:
   suffix=includes(GETTERS[name])
   if not raw.endswith(suffix):raise ValueError('getter suffix differs: '+name)
   raw=raw[:-len(suffix)]
  if name=='kernel/power/Kconfig':
   if not raw.endswith(KCONFIG):raise ValueError('config suffix differs')
   raw=raw[:-len(KCONFIG)]
  if name=='kernel/power/note10_pm_cpus.c':
   anchor=b'#ifdef CONFIG_NOTE10_PM_IRQ_TEST\n#include "note10_pm_irq.c"\n#endif'
   raw=reverse(raw,b'#ifdef CONFIG_NOTE10_CPU_PM_PRECONDITIONS\n#include "note10_pm_pre_capture.c"\n#endif\n'+anchor,anchor)
   anchor=b'    /* Mandatory even when freeze_secondary_cpus failed part-way. */'
   raw=reverse(raw,b'#ifdef CONFIG_NOTE10_CPU_PM_PRECONDITIONS\n    if (!result) result=n10_pre_capture(generation);\n#endif\n'+anchor,anchor)
  if name=='kernel/power/note10_pm_irq.c':
   for phase in range(3):
    old=('    if (!error) { error=n10_irq_gic_capture('+str(phase)+',&s->gic['+str(phase)+']);n10_pm_irq_error(s,error); }').encode()
    extra=('\n#ifdef CONFIG_NOTE10_CPU_PM_PRECONDITIONS\n    if (!error) { error=n10_pre_gic_step(generation,'+str(phase)+',s->gic['+str(phase)+'].cpu_ctlr,s->gic['+str(phase)+'].pmr);n10_pm_irq_error(s,error); }\n#endif').encode()
    raw=reverse(raw,old+extra,old)
  if name=='arch/arm64/mm/note10_pm_timer_roundtrip.c':
   anchor=b'static bool n10_timer_done;';raw=reverse(raw,anchor+b'\n#ifdef CONFIG_NOTE10_CPU_PM_PRECONDITIONS\n#include "note10_pm_pre_probe.c"\n#endif',anchor)
   anchor=b'    int result, error = 0, i;';raw=reverse(raw,anchor+b'\n#ifdef CONFIG_NOTE10_CPU_PM_PRECONDITIONS\n    bool preconditions_reported=false;\n#endif',anchor)
   anchor=b'    status = 0;\nreport:'
   raw=reverse(raw,b'#ifdef CONFIG_NOTE10_CPU_PM_PRECONDITIONS\n    preconditions_reported=true;\n    if (n10_report_pm_preconditions(pm.qgeneration,0)) goto report;\n#endif\n'+anchor+b'\n#ifdef CONFIG_NOTE10_CPU_PM_PRECONDITIONS\n    if (status && !preconditions_reported && pm.qgeneration && after==255 && num_online_cpus()==8 && !irqs_disabled())\n        (void)n10_report_pm_preconditions(pm.qgeneration,-EIO);\n#endif',anchor)
  if sha(raw)!=prior[name]:raise ValueError('precondition reverse layer differs: '+name)
  if name=='drivers/irqchip/irq-gic.c':
   for suffix in (b'\n#ifdef CONFIG_NOTE10_PM_IRQ_TEST\n#include "note10_pm_irq_gic.c"\n#endif\n',b'\n#ifdef CONFIG_NOTE10_GIC_ROUNDTRIP\n#include "note10_gic_roundtrip.c"\n#endif\n'):
    if not raw.endswith(suffix):raise ValueError('GIC earlier suffix differs')
    raw=raw[:-len(suffix)]
   if sha(raw)!=PINS[name]:raise ValueError('GIC original pin differs')
  if name in PINS and name!='drivers/irqchip/irq-gic.c' and prior[name]!=PINS[name]:raise ValueError('original pin differs: '+name)
  if name in ('kernel/cpu_pm.c','kernel/power/note10_pm_noirq.c','kernel/power/note10_pm_cpus.c','arch/arm64/mm/note10_pm_timer_roundtrip.c','kernel/power/Kconfig') and prior[name]!=build['pm_callbacks_prepared_sha256'][name]:raise ValueError('callback layer differs: '+name)
  if name in ('drivers/irqchip/irq-gic.c','kernel/power/note10_pm_irq.c') and prior[name]!=build['pm_irq_prepared_sha256'][name]:raise ValueError('IRQ layer differs: '+name)
 return True

MARKERS=(b'N10PRR1',b'N10PRG1',b'N10PRQ1')
SOURCES=tuple(sorted(set(FILES.values())|{'prepare_pm_preconditions.py','pm_preconditions_binding.py','decode_pm_preconditions.py','pm_cpus_contract.h','test_pm_post_arch_native.py','test_fsys_pm_native.py','test_pm_callbacks_producer.py','test_pm_irq_integration_native.py','test_pm_preconditions_native.py','test_pm_preconditions_gic_native.py','test_pm_preconditions_lifecycle.py','test_pm_preconditions_producer.py','test_pm_preconditions_prepared_binding.py','test_pm_preconditions_caller.py','test_pm_preconditions_worker.py','test_pm_preconditions_scope.py'}))
BINDING_KEYS=('pm_preconditions_diagnostic','pm_preconditions_version','pm_preconditions_pins','pm_preconditions_intermediate_sha256','pm_preconditions_prepared_sha256','pm_preconditions_sources_sha256')
def assert_scope(root,build):
 root=Path(root); config=(root/'handoff.config').read_bytes().splitlines(); image=(root/'Image').read_bytes();enabled=b'CONFIG_NOTE10_CPU_PM_PRECONDITIONS=y' in config
 if any((m in image)!=enabled for m in MARKERS) or enabled!=(build.get('pm_preconditions_diagnostic') is True):raise ValueError('preconditions Image/config/metadata scope differs')
 required=(b'CONFIG_NOTE10_CPU_PM_FAILURE_GUARD=y',b'CONFIG_NOTE10_PM_IRQ_TEST=y',b'CONFIG_NOTE10_PM_CALLBACK_INVENTORY=y',b'CONFIG_CPU_FREQ_GOV_SCHEDUTIL=y',b'CONFIG_ARM_ARCH_TIMER=y',b'CONFIG_ARM_PMU=y',b'CONFIG_EXYNOS_EHLD=y',b'CONFIG_ARM_GIC=y')
 if enabled and (build.get('pm_preconditions_version')!=1 or any(x not in config for x in required)):raise ValueError('preconditions config prerequisites differ')
 return enabled

def validate_model(root,build,check_scope_proof=True):
 import json
 root=Path(root)
 if not assert_scope(root,build):return False
 actual={n:sha((HERE/n).read_bytes()) for n in SOURCES}
 if build.get('pm_preconditions_sources_sha256')!=actual:raise ValueError('preconditions sources differ')
 validate_prepared(root/'pm-preconditions-prepared',build)
 models={
  'pm-preconditions-getters-model':('test_pm_preconditions_native.py',['getters.c'],[f'mode-{i}.log' for i in range(10)],'compile.log'),
  'pm-preconditions-gic-model':('test_pm_preconditions_gic_native.py',['gic.c'],[f'mode-{i}.log' for i in range(6)],'compile.log'),
  'pm-preconditions-lifecycle-model':('test_pm_preconditions_lifecycle.py',['lifecycle.c'],[f'mode-{i}.log' for i in range(17)],'compile.log'),
  'pm-preconditions-producer-model':('test_pm_preconditions_producer.py',['producer.c'],['mode-0.log','mode-1.log'],'compile.log'),
  'pm-preconditions-caller-model':('test_pm_preconditions_caller.py',['enabled.c','disabled.c'],[f'{s}-{i}.log' for s in ('enabled','disabled') for i in (0,1,3,9)],None),
  'pm-preconditions-worker-model':('test_pm_preconditions_worker.py',['worker.c'],['mode-0.log','mode-1.log','mode-10.log'],'compile.log')}
 source_sets={
  'pm-preconditions-getters-model':('pm_preconditions_contract.h','pm_preconditions_gic_getter.c','pm_preconditions_timer_getter.c','pm_preconditions_fpsimd_getter.c','pm_preconditions_sugov_getter.c','pm_preconditions_pmu_getter.c','pm_preconditions_ehld_getter.c','pm_preconditions_chain.c'),
  'pm-preconditions-gic-model':('pm_preconditions_contract.h','pm_preconditions_gic_regs.c'),
  'pm-preconditions-lifecycle-model':('pm_preconditions_contract.h','pm_preconditions_capture.c'),
  'pm-preconditions-producer-model':('pm_preconditions_contract.h','pm_preconditions_probe.c','decode_pm_preconditions.py')}
 cases={
  'pm-preconditions-getters-model':['six-and-unknown-multi-pmu','empty','trylock','pmu-bound','wrong-cpu','timer-not-started','capacity-32','capacity-33','pmu-zero','pmu-bit31'],
  'pm-preconditions-gic-model':['baseline','priority-mismatch','deactivate','bypass','pmr-mismatch','control-mismatch'],
  'pm-preconditions-lifecycle-model':['duplicate','under-lock-owner','post-unlock-noirq','point','null-active','pm-called','qphase','generation','cpu','mask','count','irq','preempt','late-ready','noirq-ready','ops','test-level'],
  'pm-preconditions-producer-model':['success','failed','truncated','damaged','stale','duplicate','negative-zero','wide-status','prefix-typo'],
  'pm-preconditions-caller-model':['enabled-success','enabled-partial-stop','enabled-irq-error','enabled-pre-error','disabled-success','disabled-partial-stop','disabled-irq-error','disabled-pre-error'],
  'pm-preconditions-worker-model':['success','outer-error','capture-error']}
 for name,(harness,generated,logs,compilelog) in models.items():
  d=root/name;model=json.loads((d/'result.json').read_text(encoding='utf-8'))
  if model.get('passed') is not True or model.get('hardware_verified') is not False or model.get('harness_sha256')!=actual[harness] or model.get('cases')!=cases[name]:raise ValueError('preconditions model differs: '+name)
  if len(generated)==1:
   if model.get('generated_c_sha256')!=sha((d/generated[0]).read_bytes()):raise ValueError('generated model differs: '+name)
  elif model.get('generated_c_sha256')!={n:sha((d/n).read_bytes()) for n in generated}:raise ValueError('generated caller differs')
  expected=logs+([compilelog] if compilelog else ['enabled-compile.log','disabled-compile.log'])
  if model.get('log_sha256')!={n:sha((d/n).read_bytes()) for n in expected}:raise ValueError('model logs differ: '+name)
  if name in source_sets and model.get('source_sha256')!={n:actual[n] for n in source_sets[name]}:raise ValueError('model source differs: '+name)
  if name.endswith('gic-model') and (model.get('exact_read_allowlist') is not True or model.get('no_gic_writes') is not True or model.get('read_count')!=36):raise ValueError('GIC proof differs')
  if name.endswith('caller-model') and (model.get('source_sha256')!=build['pm_preconditions_prepared_sha256']['kernel/power/note10_pm_cpus.c'] or model.get('mandatory_cpu_restore_on_failures') is not True):raise ValueError('caller proof differs')
  if name.endswith('worker-model'):
   deps=('pm_preconditions_contract.h','pm_preconditions_probe.c','decode_pm_preconditions.py','test_pm_preconditions_producer.py','test_pm_post_arch_native.py','test_fsys_pm_native.py','test_pm_callbacks_producer.py')
   if model.get('source_sha256')!=build['pm_preconditions_prepared_sha256']['arch/arm64/mm/note10_pm_timer_roundtrip.c'] or model.get('dependencies_sha256')!={n:actual[n] for n in deps}:raise ValueError('worker proof differs')
 binding=json.loads((root/'pm-preconditions-binding-model/result.json').read_text(encoding='utf-8'))
 if binding.get('passed') is not True or binding.get('cases')!=['baseline','original-gic','prior-cpu','helper','pinned-header','worker','prior-map','pin-map'] or binding.get('harness_sha256')!=actual['test_pm_preconditions_prepared_binding.py'] or binding.get('binding_sha256')!=actual['pm_preconditions_binding.py']:raise ValueError('precondition binding proof differs')
 if check_scope_proof:
  scope=json.loads((root/'pm-preconditions-scope-model/result.json').read_text(encoding='utf-8'))
  if scope.get('passed') is not True or scope.get('cases')!=['baseline','metadata-downgrade','config-downgrade','image-marker-omission','model-source-omission','model-case-omission','proof-file-omission'] or scope.get('harness_sha256')!=actual['test_pm_preconditions_scope.py']:raise ValueError('preconditions scope proof differs')
 return True
