"""Fail-closed binding for callback inventory Image, config and model evidence."""
import hashlib,json
from pathlib import Path
from prepare_pm_callbacks import HERE,PINS,SOURCES,FILES
MARKERS=(b'N10CBS1',b'N10CBR1',b'N10CBQ1')
REQUIRED=(b'CONFIG_NOTE10_PM_IRQ_TEST=y',b'CONFIG_CPU_PM=y',b'CONFIG_GENERIC_IRQ_CHIP=y',b'CONFIG_GENERIC_CLOCKEVENTS=y',b'CONFIG_SMP=y',b'CONFIG_PREEMPT_COUNT=y',b'CONFIG_KALLSYMS=y',b'CONFIG_LOG_BUF_SHIFT=21')
FORBIDDEN=('DEBUG_SNAPSHOT_SPINLOCK','DEBUG_SPINLOCK','DEBUG_MUTEXES','DEBUG_LOCK_ALLOC','TRACE_IRQFLAGS','DEBUG_SNAPSHOT_IRQ_DISABLED','DEBUG_SNAPSHOT_REG')
def assert_scope(root,build):
 root=Path(root);config=(root/'handoff.config').read_bytes().splitlines();image=(root/'Image').read_bytes();enabled=b'CONFIG_NOTE10_PM_CALLBACK_INVENTORY=y' in config
 if any((m in image)!=enabled for m in MARKERS):raise ValueError('Callback actual Image/config scope differs')
 if enabled!=(build.get('pm_callbacks_diagnostic') is True):raise ValueError('Callback metadata cannot downgrade actual scope')
 if enabled and (build.get('pm_callbacks_evidence_version')!=1 or any(x not in config for x in REQUIRED) or any(('CONFIG_'+n+'='+v).encode() in config for n in FORBIDDEN for v in ('y','m'))):raise ValueError('Callback config prerequisites differ')
 return enabled
def verify_snapshot(root,final,paths):
 snapshot=Path(root)/'pm-callbacks-prepared'
 if not snapshot.is_dir() or snapshot.is_symlink():raise ValueError('Callback prepared snapshot missing')
 entries=list(snapshot.rglob('*'))
 if any(p.is_symlink() or (not p.is_dir() and not p.is_file()) for p in entries):raise ValueError('Unsafe prepared snapshot entry')
 files={p.relative_to(snapshot).as_posix():p for p in entries if p.is_file()}
 allowed_dirs={parent.as_posix() for name in paths for parent in Path(name).parents if parent.as_posix()!='.'}
 if {p.relative_to(snapshot).as_posix() for p in entries if p.is_dir()}!=allowed_dirs:raise ValueError('Unexpected prepared snapshot directory')
 if set(files)!=paths or any(hashlib.sha256(files[k].read_bytes()).hexdigest()!=final[k] for k in paths):raise ValueError('Callback prepared snapshot missing, extra or corrupted')

def verify_composition(root,intermediate):
 snapshot=Path(root)/'pm-callbacks-prepared'
 def reverse(raw,new,old):
  if raw.count(new)!=1:raise ValueError('Callback final composition differs')
  return raw.replace(new,old)
 def same(path,raw):
  if hashlib.sha256(raw).hexdigest()!=intermediate[path]:raise ValueError('Callback intermediate composition differs: '+path)
 for name,helper in (('kernel/cpu_pm.c','note10_pm_callbacks_cpu_pm.c'),('kernel/irq/generic-chip.c','note10_pm_callbacks_irq.c'),('kernel/time/clocksource.c','note10_pm_callbacks_clocksource.c'),('kernel/time/clockevents.c','note10_pm_callbacks_clockevent.c')):
  raw=(snapshot/name).read_bytes();suffix=('\n#ifdef CONFIG_NOTE10_PM_CALLBACK_INVENTORY\n#include "'+helper+'"\n#endif\n').encode()
  if not raw.endswith(suffix) or hashlib.sha256(raw[:-len(suffix)]).hexdigest()!=PINS[name]:raise ValueError('Callback pinned TU composition differs: '+name)
 cpu='kernel/power/note10_pm_cpus.c';raw=(snapshot/cpu).read_bytes();prefix=b'#ifdef CONFIG_NOTE10_PM_CALLBACK_INVENTORY\n#include <linux/note10_pm_callbacks.h>\n#endif\n'
 if not raw.startswith(prefix):raise ValueError('Callback CPU include differs')
 raw=raw[len(prefix):];raw=reverse(raw,b'#ifdef CONFIG_NOTE10_PM_CALLBACK_INVENTORY\n    if (!result) result = n10_cb_capture(1, generation);\n#endif\n    /* Mandatory even when freeze_secondary_cpus failed part-way. */',b'    /* Mandatory even when freeze_secondary_cpus failed part-way. */')
 raw=reverse(raw,b'#ifdef CONFIG_NOTE10_PM_CALLBACK_INVENTORY\n    if (s->restored != s->before || num_online_cpus() != 8 || irqs_disabled()) { if (!result) result = -EIO; }\n#else\n    if (s->restored != s->before || num_online_cpus() != 8 || irqs_disabled()) result = -EIO;\n#endif',b'    if (s->restored != s->before || num_online_cpus() != 8 || irqs_disabled()) result = -EIO;');same(cpu,raw)
 noirq='kernel/power/note10_pm_noirq.c';raw=(snapshot/noirq).read_bytes();suffix=b'\n#ifdef CONFIG_NOTE10_PM_CALLBACK_INVENTORY\n#include "note10_pm_callbacks.c"\n#endif\n'
 if not raw.endswith(suffix):raise ValueError('Callback dispatcher include differs')
 same(noirq,raw[:-len(suffix)])
 dma='drivers/base/power/note10_dma_pm.c';raw=(snapshot/dma).read_bytes()
 if not raw.startswith(prefix):raise ValueError('Callback DMA include differs')
 raw=raw[len(prefix):];raw=reverse(raw,b'    if (phase == 0 || phase == 2) n10_edge_capture(phase == 0 ? 0 : 3, generation);\n#ifdef CONFIG_NOTE10_PM_CALLBACK_INVENTORY\n    if (phase == 0 || phase == 2) (void)n10_cb_capture(phase == 0 ? 0 : 2, generation);\n#endif',b'    if (phase == 0 || phase == 2) n10_edge_capture(phase == 0 ? 0 : 3, generation);');same(dma,raw)
 worker='arch/arm64/mm/note10_pm_timer_roundtrip.c';raw=(snapshot/worker).read_bytes()
 raw=reverse(raw,b'static bool n10_timer_done;\n#ifdef CONFIG_NOTE10_PM_CALLBACK_INVENTORY\n#include "note10_pm_callbacks_probe.c"\n#endif',b'static bool n10_timer_done;')
 raw=reverse(raw,b'    int result, error = 0, i;\n#ifdef CONFIG_NOTE10_PM_CALLBACK_INVENTORY\n    bool callbacks_reported = false;\n#endif',b'    int result, error = 0, i;')
 raw=reverse(raw,b'#ifdef CONFIG_NOTE10_PM_CALLBACK_INVENTORY\n    callbacks_reported = true;\n    if (n10_report_pm_callbacks(pm.qgeneration, 0)) goto report;\n#endif\n    status = 0;\nreport:\n#ifdef CONFIG_NOTE10_PM_CALLBACK_INVENTORY\n    if (status && !callbacks_reported && pm.qgeneration && after == 255 && num_online_cpus() == 8 && !irqs_disabled())\n        (void)n10_report_pm_callbacks(pm.qgeneration, -EIO);\n#endif',b'    status = 0;\nreport:');same(worker,raw)
 config='kernel/power/Kconfig';raw=(snapshot/config).read_bytes();suffix=b'\nconfig NOTE10_PM_CALLBACK_INVENTORY\n\tbool "Experimental PM callback metadata inventory"\n\tdepends on NOTE10_PM_IRQ_TEST && CPU_PM && GENERIC_IRQ_CHIP && GENERIC_CLOCKEVENTS && SMP && PREEMPT_COUNT && KALLSYMS && !DEBUG_SNAPSHOT_SPINLOCK && !DEBUG_SPINLOCK && !DEBUG_MUTEXES && !DEBUG_LOCK_ALLOC\n\tdefault n\n'
 if not raw.endswith(suffix):raise ValueError('Callback Kconfig differs')
 same(config,raw[:-len(suffix)])

def _validate_core(root,build):
 if not assert_scope(root,build):return False
 root=Path(root);actual={n:hashlib.sha256((HERE/n).read_bytes()).hexdigest() for n in SOURCES}
 if build.get('pm_callbacks_source_pins')!=PINS or build.get('pm_callbacks_sources_sha256')!=actual:raise ValueError('Callback pinned source or harness differs')
 final=build.get('pm_callbacks_prepared_sha256');intermediate=build.get('pm_callbacks_intermediate_sha256')
 if not isinstance(final,dict) or not isinstance(intermediate,dict):raise ValueError('Callback prepared binding missing')
 paths=set(FILES)|{'kernel/power/note10_pm_cpus.c','kernel/power/note10_pm_noirq.c','drivers/base/power/note10_dma_pm.c','arch/arm64/mm/note10_pm_timer_roundtrip.c','kernel/power/suspend.c','kernel/power/Kconfig','kernel/cpu_pm.c','kernel/irq/generic-chip.c','kernel/time/clocksource.c','kernel/time/clockevents.c'}
 if set(final)!=paths or any(not isinstance(v,str) or len(v)!=64 for v in final.values()) or any(final[k]!=actual[v] for k,v in FILES.items()):raise ValueError('Callback prepared helper differs')
 verify_snapshot(root,final,paths)
 prior_irq=build.get('pm_irq_prepared_sha256',{});prior_edge=build.get('pm_edge_prepared_sha256',{})
 expected_prior={'kernel/power/note10_pm_cpus.c':prior_irq.get('kernel/power/note10_pm_cpus.c'),'arch/arm64/mm/note10_pm_timer_roundtrip.c':prior_irq.get('arch/arm64/mm/note10_pm_timer_roundtrip.c'),'kernel/power/Kconfig':prior_irq.get('kernel/power/Kconfig'),'kernel/power/note10_pm_noirq.c':prior_edge.get('kernel/power/note10_pm_noirq.c'),'drivers/base/power/note10_dma_pm.c':prior_edge.get('drivers/base/power/note10_dma_pm.c'),'kernel/power/suspend.c':prior_irq.get('kernel/power/suspend.c')}
 if intermediate!=expected_prior or any(not v for v in expected_prior.values()):raise ValueError('Callback intermediate prerequisite differs')
 verify_composition(root,intermediate)
 prepared_meta=json.loads((root/'pm-callbacks-prepared-binding.json').read_text(encoding='utf-8'))
 if prepared_meta!={'final':final,'intermediate':intermediate}:raise ValueError('Callback prepared map differs')
 prepared_model=json.loads((root/'pm-callbacks-prepared-binding-model/result.json').read_text(encoding='utf-8'))
 if prepared_model.get('passed') is not True or prepared_model.get('cases')!=7 or prepared_model.get('harness_sha256')!=actual['test_pm_callbacks_prepared_binding.py'] or prepared_model.get('binding_sha256')!=actual['pm_callbacks_binding.py'] or prepared_model.get('prepared_map_sha256')!=hashlib.sha256((root/'pm-callbacks-prepared-binding.json').read_bytes()).hexdigest():raise ValueError('Callback composition mutation proof differs')
 if intermediate.get('kernel/power/suspend.c')!=final.get('kernel/power/suspend.c') or final.get('kernel/power/suspend.c')!='2bad7dc2695559e4df992a6571fb2c79cc4879384819f946254da4519049efde':raise ValueError('Guarded suspend differs')
 for name,harness in (('lock','test_pm_callbacks_lock_native.py'),('dispatcher','test_pm_callbacks_dispatcher_native.py'),('families','test_pm_callbacks_families_native.py'),('producer','test_pm_callbacks_producer.py'),('integration','test_pm_callbacks_integration_native.py')):
  model=json.loads((root/('pm-callbacks-'+name+'-model/result.json')).read_text(encoding='utf-8'))
  if model.get('passed') is not True or model.get('hardware_verified') is not False or model.get('harness_sha256')!=actual[harness]:raise ValueError('Callback model binding differs: '+name)
  directory=root/('pm-callbacks-'+name+'-model')
  if name=='lock':
   expected_source={n:PINS[n] for n in ('include/linux/spinlock.h','include/linux/spinlock_api_smp.h','kernel/locking/spinlock.c')}
   if model.get('source_sha256')!=expected_source or model.get('cases')!=8 or model.get('actual_public_macros_and_wrappers') is not True or model.get('architecture_atomicity_verified') is not False:raise ValueError('Public lock proof differs')
   if model.get('generated_c_sha256')!=hashlib.sha256((directory/'lock.c').read_bytes()).hexdigest() or model.get('compile_log_sha256')!=hashlib.sha256((directory/'compile.log').read_bytes()).hexdigest():raise ValueError('Lock generated C or log differs')
  else:
   expected_names={'dispatcher':('pm_callbacks_contract.h','pm_callbacks_backend.c'),'families':('pm_callbacks_contract.h','pm_callbacks_backend.c','pm_callbacks_cpu_pm_backend.c','pm_callbacks_irq_backend.c','pm_callbacks_clocksource_backend.c','pm_callbacks_clockevent_backend.c'),'producer':('pm_callbacks_contract.h','pm_callbacks_probe.c','decode_pm_callbacks.py')}
   if name in expected_names and model.get('source_sha256')!={n:actual[n] for n in expected_names[name]}:raise ValueError('Callback actual source proof differs: '+name)
   generated={'dispatcher':'dispatcher.c','families':'families.c','producer':'producer.c'}
   if name in generated and model.get('generated_c_sha256')!=hashlib.sha256((directory/generated[name]).read_bytes()).hexdigest():raise ValueError('Callback generated C differs: '+name)
   if name=='integration' and model.get('generated_c_sha256')!={n:hashlib.sha256((directory/n).read_bytes()).hexdigest() for n in ('integration.c','integration-disabled.c')}:raise ValueError('Callback final generated C differs')
   logs=model.get('log_sha256'); actual_logs={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in directory.glob('*.log')}
   if not isinstance(logs,dict) or not logs or logs!=actual_logs:raise ValueError('Callback model logs differ: '+name)
  expected_cases={'lock':8,'dispatcher':17,'families':28}
  if name in expected_cases and (model.get('cases')!=expected_cases[name] or len(model.get('outcomes',[]))!=expected_cases[name] or any(r.get('passed') is not True for r in model['outcomes'])):raise ValueError('Callback model cases differ: '+name)
  if name=='producer' and any(model.get(k) is not True for k in ('actual_producer','same_name_distinct_ids','failure_rejected','overbudget_rejected')):raise ValueError('Callback producer proof differs')
  if name=='integration':
   deps=('pm_cpus_contract.h','pm_callbacks_contract.h','pm_callbacks_probe.c','test_pm_post_arch_native.py','test_fsys_pm_native.py','test_pm_callbacks_producer.py','decode_pm_callbacks.py')
   if model.get('dependencies_sha256')!={n:hashlib.sha256((HERE/n).read_bytes()).hexdigest() for n in deps}:raise ValueError('Callback integration dependency differs')
   expected={'cpu':final['kernel/power/note10_pm_cpus.c'],'worker':final['arch/arm64/mm/note10_pm_timer_roundtrip.c'],'probe':final['arch/arm64/mm/note10_pm_callbacks_probe.c']}
   if model.get('source_sha256')!=expected or any(model.get(k) is not True for k in ('actual_prepared_cpu_caller','actual_prepared_worker','actual_producer','failure_cpu_restored','failure_stdout_rejected','four_family_failure_paths','irq_failure_skips_callback','pmu_failure_skips_callback','later_gic_failure_blocks_success','feature_off_prior_restore_error')):raise ValueError('Final prepared callback caller not verified')
 decoder=json.loads((root/'pm-callbacks-decoder-model/result.json').read_text(encoding='utf-8'))
 if decoder.get('passed') is not True or decoder.get('cases')!=15 or decoder.get('decoder_sha256')!=actual['decode_pm_callbacks.py'] or decoder.get('harness_sha256')!=actual['test_pm_callbacks_decoder.py'] or decoder.get('producer_log_sha256')!=hashlib.sha256((root/'pm-callbacks-producer-model/mode-0.log').read_bytes()).hexdigest():raise ValueError('Callback decoder proof differs')
 binding=json.loads((root/'pm-callbacks-binding-model/result.json').read_text(encoding='utf-8'))
 if binding.get('passed') is not True or binding.get('cases')!=14 or binding.get('harness_sha256')!=actual['test_pm_callbacks_binding.py'] or binding.get('binding_sha256')!=actual['pm_callbacks_binding.py']:raise ValueError('Callback binding scope proof differs')
 return True

BINDING_KEYS=('pm_callbacks_diagnostic','pm_callbacks_evidence_version','pm_callbacks_source_pins','pm_callbacks_sources_sha256','pm_callbacks_prepared_sha256','pm_callbacks_intermediate_sha256','pm_irq_prepared_sha256','pm_edge_prepared_sha256')
def binding_inputs(build):
 return {k:build.get(k) for k in BINDING_KEYS}
def validate_model(root,build):
 if not _validate_core(root,build):return False
 root=Path(root);record=json.loads((root/'pm-callbacks-binding-input.json').read_text(encoding='utf-8'))
 if record!=binding_inputs(build):raise ValueError('Callback binding input differs')
 coverage=json.loads((root/'pm-callbacks-coverage-model/result.json').read_text(encoding='utf-8'))
 source=Path(__file__).parent/'test_pm_callbacks_full_binding.py'
 if coverage.get('passed') is not True or coverage.get('cases')!=8 or any(not x.get('passed') for x in coverage.get('outcomes',[])) or coverage.get('harness_sha256')!=hashlib.sha256(source.read_bytes()).hexdigest() or coverage.get('binding_sha256')!=hashlib.sha256(Path(__file__).read_bytes()).hexdigest() or coverage.get('binding_input_sha256')!=hashlib.sha256((root/'pm-callbacks-binding-input.json').read_bytes()).hexdigest():raise ValueError('Callback binding mutation proof differs')
 model_dirs=('prepared-binding','lock','dispatcher','families','producer','decoder','binding','integration');manifest={};outcomes={}
 for name in model_dirs:
  directory=root/('pm-callbacks-'+name+'-model');report=json.loads((directory/'result.json').read_text(encoding='utf-8'));outcomes[name]=report.get('outcomes',[])
  for f in sorted(directory.iterdir()):
   if f.is_file() and f.suffix in ('.json','.c','.log'):manifest[f.relative_to(root).as_posix()]=hashlib.sha256(f.read_bytes()).hexdigest()
 expected_counts={'prepared-binding':7,'lock':8,'dispatcher':17,'families':28,'producer':7,'decoder':15,'binding':14,'integration':12}
 if coverage.get('manifest')!=manifest or coverage.get('model_outcomes')!=outcomes or any(len(outcomes[k])!=v or any(r.get('passed') is not True for r in outcomes[k]) for k,v in expected_counts.items()):raise ValueError('Callback coverage manifest or cases differ')
 expected_ids={
  'prepared-binding':{'baseline','cpu_hook','worker_hook','dma_hook','noirq_hook','kconfig','upstream_tu'},
  'producer':{'baseline','same_name_distinct_ids','failure','overbudget','truncated','damaged','wrong_generation'},
  'decoder':{'null_notifier','notifier_unused','priority_order','empty_name','empty_scalar','empty_symbol','irq_unused','source_bool','source_unused','event_state','event_mask','event_unused','symbol_reference','signed_overflow','uint_overflow'},
  'binding':{'enabled','metadata_omitted','version_omitted','marker_missing','config_omitted','debug_enabled','logbuf_wrong','off','off_marker','snapshot_good','snapshot_corrupt','snapshot_missing','snapshot_extra','snapshot_extra_dir'},
  'integration':{'success','later_gic_failure','family0_failure','capture_and_restore_failure','family1_failure','family2_failure','family3_failure','irq_failure','pmu_cpu_failure','pmu_pre_failure','off_success','off_restore_failure'}}
 if any({row.get('case') for row in outcomes[k]}!=v for k,v in expected_ids.items()):raise ValueError('Callback coverage case IDs differ')
 if {row.get('mode') for row in outcomes['dispatcher']}!={0,1,2,3,4,5,6,7,8,10,11,12,13,20,21,22,23} or {(r.get('family'),r.get('mode')) for r in outcomes['families']}!={(f,m) for f in range(4) for m in range(7)} or {(r.get('family'),r.get('success'),r.get('initial_irq_disabled')) for r in outcomes['lock']}!={(f,s,i) for f in (0,1) for s in (0,1) for i in (0,1)}:raise ValueError('Callback native case IDs differ')
 if {r.get('case') for r in coverage['outcomes']}!={'baseline','metadata_omitted','image_marker','snapshot_corrupt','snapshot_extra','intermediate_mismatch','producer_log','source_model'}:raise ValueError('Callback binding mutation case IDs differ')
 return True
