"""Bind v38 branch evidence to the exact v37 prepared snapshot and Image."""
import hashlib,json,shutil,tempfile
from pathlib import Path
from prepare_pm_branch import HERE,FILES,prepare
from prepare_pm_preconditions import PINS as PRE_PINS
from pm_preconditions_binding import validate_prepared as validate_prepared_v37
MARKERS=(b'N10BRAR1',b'N10BRAG1',b'N10BRAQ1')
SOURCES=tuple(sorted(set(FILES.values())|{'prepare_pm_branch.py','pm_branch_binding.py','decode_pm_branch.py','test_pm_branch_native.py','test_pm_branch_producer.py','test_pm_branch_source_native.py','test_pm_branch_gic_source_native.py'}))
def sha(raw):return hashlib.sha256(raw).hexdigest()
def assert_scope(root,build):
 root=Path(root);config=(root/'handoff.config').read_bytes().splitlines();image=(root/'Image').read_bytes();enabled=b'CONFIG_NOTE10_CPU_PM_BRANCH_AUDIT=y' in config
 if any((m in image)!=enabled for m in MARKERS) or enabled!=(build.get('pm_branch_diagnostic') is True):raise ValueError('branch Image/config/metadata scope differs')
 if enabled and (build.get('pm_branch_version')!=1 or b'CONFIG_NOTE10_CPU_PM_PRECONDITIONS=y' not in config):raise ValueError('branch prerequisites differ')
 return enabled

def validate_prepared(root,build):
 root=Path(root);prior=root/'pm-preconditions-prepared';snapshot=root/'pm-branch-prepared';validate_prepared_v37(prior,build)
 with tempfile.TemporaryDirectory() as temp:
  expected=Path(temp)/'source';shutil.copytree(prior,expected);result=prepare(expected,build)
  if any(build.get(k)!=v for k,v in result.items()):raise ValueError('branch composition map differs')
  entries=list(snapshot.rglob('*'))
  if snapshot.is_symlink() or any(p.is_symlink() for p in entries):raise ValueError('branch snapshot contains symlink')
  actual_files={str(p.relative_to(snapshot)).replace('\\','/') for p in entries if p.is_file()}
  if actual_files!=set(result['pm_branch_prepared_sha256']):raise ValueError('branch snapshot file set differs')
  for name,digest in result['pm_branch_prepared_sha256'].items():
   p=snapshot/name
   if p.is_symlink() or sha(p.read_bytes())!=digest or p.read_bytes()!=(expected/name).read_bytes():raise ValueError('branch prepared file differs: '+name)
 return True

from pm_preconditions_binding import SOURCES as PRE_SOURCES,validate_model as validate_preconditions
SOURCES=tuple(sorted(set(SOURCES)|set(PRE_SOURCES)|{'test_pm_branch_lifecycle.py','test_pm_branch_worker.py','test_pm_branch_binding.py','test_pm_branch_scope.py','test_pm_preconditions_caller.py'}))
def validate_core(root,build):
 root=Path(root)
 if not assert_scope(root,build):return False
 validate_preconditions(root,build)
 actual={n:sha((HERE/n).read_bytes()) for n in SOURCES}
 if build.get('pm_branch_sources_sha256')!=actual:raise ValueError('branch source binding differs')
 validate_prepared(root,build)
 models={
  'native':('test_pm_branch_native.py',['branch.c'],[f'case-{i}.log' for i in range(10)],['compile.log'],['match','null-ehld','unsupported','zero-slots','bit31','overflow','no-callbacks','invalidate-and-recover','capacity','multiple-pmu']),
  'producer':('test_pm_branch_producer.py',['producer.c'],[f'mode-{i}.log' for i in range(3)],['compile.log'],['cross-bound-success','lane-intersections','failure','truncated','damaged','duplicate','prefix']),
  'pmu-source':('test_pm_branch_source_native.py',['pmu-branch.c'],[f'case-{i}.log' for i in range(8)],['compile.log'],['enter','exit','enter-failed','empty-failed','empty-exit-reset','unsupported','exit-no-reset','unknown-command']),
  'gic-source':('test_pm_branch_gic_source_native.py',['gic-branch.c'],[f'case-{i}.log' for i in range(4)],['compile.log'],['restore-write-sequence','missing-distributor','missing-interface','null-gic']),
  'lifecycle':('test_pm_branch_lifecycle.py',['lifecycle.c'],[f'case-{i}.log' for i in range(5)],['compile.log'],['success','trylock-failure','post-context-failure','foreign-owner','duplicate-generation']),
  'worker':('test_pm_branch_worker.py',['enabled.c','disabled.c'],[f'{s}-{i}.log' for s in ('enabled','disabled') for i in (0,1,9,10)],['enabled-compile.log','disabled-compile.log'],['enabled-success','enabled-outer-error','enabled-gic-error','enabled-branch-error','disabled-success','disabled-outer-error','disabled-gic-error','disabled-branch-error']),
  'caller':('test_pm_preconditions_caller.py',['enabled.c','disabled.c'],[f'{s}-{i}.log' for s in ('enabled','disabled') for i in (0,1,3,9)],['enabled-compile.log','disabled-compile.log'],['enabled-success','enabled-partial-stop','enabled-irq-error','enabled-pre-error','disabled-success','disabled-partial-stop','disabled-irq-error','disabled-pre-error'])}
 for name,(harness,generated,logs,compiles,cases) in models.items():
  p=root/('pm-branch-'+name+'-model');m=json.loads((p/'result.json').read_text(encoding='utf-8'))
  if m.get('passed') is not True or m.get('hardware_verified') is not False or m.get('cases')!=cases or m.get('harness_sha256')!=actual[harness]:raise ValueError('branch model differs: '+name)
  hashes={n:sha((p/n).read_bytes()) for n in generated}
  expected=next(iter(hashes.values())) if len(generated)==1 else hashes
  if m.get('generated_c_sha256')!=expected or m.get('log_sha256')!={n:sha((p/n).read_bytes()) for n in logs+compiles}:raise ValueError('branch generated evidence differs: '+name)
  if name=='native':
   fields=('pm_branch_contract.h','pm_branch_ehld.c','pm_branch_pmu.c','pm_branch_chain.c')
   if m.get('source_sha256')!={n:actual[n] for n in fields}:raise ValueError('branch getter sources differ')
  if name=='producer':
   fields=('pm_preconditions_contract.h','pm_preconditions_probe.c','pm_branch_contract.h','pm_branch_probe.c','decode_pm_preconditions.py','decode_pm_branch.py')
   if m.get('source_sha256')!={n:actual[n] for n in fields}:raise ValueError('branch producer sources differ')
  if name=='pmu-source' and (m.get('source_sha256')!=build['pm_branch_prepared_sha256']['drivers/perf/arm_pmu.c'] or m.get('actual_pinned_branch_bodies') is not True or m.get('callbacks_invoked_on_hardware') is not False):raise ValueError('PMU dispatch evidence differs')
  if name=='gic-source' and (m.get('source_sha256')!=build['pm_preconditions_prepared_sha256']['drivers/irqchip/irq-gic.c'] or m.get('actual_pinned_branch_body') is not True or m.get('callbacks_invoked_on_hardware') is not False):raise ValueError('GIC dispatch evidence differs')
  if name=='lifecycle':
   paths={'chain':'kernel/note10_pm_pre_chain.c','capture':'kernel/power/note10_pm_pre_capture.c','branch_chain':'kernel/note10_pm_branch_chain.c','branch_capture':'kernel/power/note10_pm_branch_capture.c'}
   if m.get('actual_final_capture_and_chain') is not True or m.get('source_sha256')!={k:build['pm_branch_prepared_sha256'][v] for k,v in paths.items()}:raise ValueError('branch lifecycle evidence differs')
  if name=='worker' and (m.get('actual_final_worker_and_producers') is not True or m.get('source_sha256')!=build['pm_branch_prepared_sha256']['arch/arm64/mm/note10_pm_timer_roundtrip.c']):raise ValueError('branch worker evidence differs')
  if name=='caller' and (m.get('mandatory_cpu_restore_on_failures') is not True or m.get('source_sha256')!=build['pm_preconditions_prepared_sha256']['kernel/power/note10_pm_cpus.c']):raise ValueError('branch caller evidence differs')
 bind=json.loads((root/'pm-branch-binding-model/result.json').read_text(encoding='utf-8'))
 if bind.get('passed') is not True or bind.get('cases')!=['baseline','chain','capture','worker','pmu','kconfig','new-helper','v37-prior'] or bind.get('harness_sha256')!=actual['test_pm_branch_binding.py'] or bind.get('binding_sha256')!=actual['pm_branch_binding.py']:raise ValueError('branch prepared binding proof differs')
 return True

def validate_model(root,build):
 if not validate_core(root,build):return False
 actual=sha((HERE/'test_pm_branch_scope.py').read_bytes());m=json.loads((Path(root)/'pm-branch-scope-model/result.json').read_text(encoding='utf-8'))
 if m.get('passed') is not True or m.get('harness_sha256')!=actual or m.get('cases')!=['baseline','metadata','config','marker','source','cases','proof']:raise ValueError('branch scope proof differs')
 return True
