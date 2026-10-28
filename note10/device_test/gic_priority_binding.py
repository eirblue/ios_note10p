"""Bind target-only GIC priority guard to final source, models and Image."""
import hashlib,json,re,shutil,tempfile
from pathlib import Path
from prepare_gic_priority_restore import prepare
HERE=Path(__file__).resolve().parent
SOURCES=('prepare_gic_priority_restore.py','gic_priority_restore.c','test_gic_priority_restore.py','gic_priority_binding.py','test_gic_priority_binding.py','test_gic_priority_package_flow.py','prepare_pmu_failure_flow_compat.py')
PACKAGE_SOURCES=('prepare_linux_boot.py','build_boot_test_packages.py','precheck_window_access.py','stage_phase2.py','collect_reservation.py')
MARKER=b'N10GIPR1: missing GIC priority snapshot'
def sha(raw):return hashlib.sha256(raw).hexdigest()
def validate_core(root,build):
 root=Path(root);config=(root/'handoff.config').read_bytes().splitlines();enabled=b'CONFIG_NOTE10_GIC_PRIORITY_RESTORE=y' in config
 if enabled!=(build.get('gic_priority_restore') is True) or enabled!=(MARKER in (root/'Image').read_bytes()):raise ValueError('GIC priority Image/config/metadata mismatch')
 if not enabled:
  feature_keys={k for k in build if k.startswith('gic_priority_')}
  if feature_keys-{'gic_priority_restore','gic_priority_restore_version'} or build.get('gic_priority_restore') not in (None,False) or build.get('gic_priority_restore_version') is not None or (root/'gic-priority-prepared').exists() or (root/'gic-priority-model').exists():raise ValueError('GIC priority evidence downgrade')
  return False
 if build.get('gic_priority_restore_version')!=1 or not all(x in config for x in (b'CONFIG_CPU_PM=y',b'CONFIG_ARM_GIC=y',b'CONFIG_ARM_GIC_MAX_NR=1',b'CONFIG_NOTE10_CPU_PM_FAILURE_GUARD=y',b'CONFIG_NOTE10_PMU_FAILURE_RESTORE=y')) or b'CONFIG_GIC_NON_BANKED=y' in config or sum(x.startswith(b'CONFIG_ARM_GIC_MAX_NR=') for x in config)!=1:raise ValueError('Unsupported GIC priority configuration')
 from pmu_failure_binding import validate as validate_previous
 if validate_previous(root,build) is not True:raise ValueError('Prior PMU binding missing')
 sourcehash={n:sha((HERE/n).read_bytes()) for n in SOURCES}
 if build.get('gic_priority_sources_sha256')!=sourcehash:raise ValueError('GIC priority source binding differs')
 package_sources=build.get('gic_priority_package_sources_sha256')
 if not isinstance(package_sources,dict) or set(package_sources)!=set(PACKAGE_SOURCES) or any(not isinstance(v,str) or re.fullmatch(r'[0-9a-f]{64}',v) is None for v in package_sources.values()):raise ValueError('GIC package source map differs')
 with tempfile.TemporaryDirectory() as tmp:
  expected=Path(tmp)/'source';shutil.copytree(root/'pmu-failure-prepared',expected)
  name='drivers/irqchip/irq-gic.c';src=root/'pm-preconditions-prepared'/name;dst=expected/name;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(src,dst)
  result=prepare(expected,build)
  if any(build.get(k)!=v for k,v in result.items()):raise ValueError('GIC composition map differs')
  snapshot=root/'gic-priority-prepared';paths=list(snapshot.rglob('*'))
  if snapshot.is_symlink() or any(p.is_symlink() for p in paths):raise ValueError('GIC snapshot symlink')
  files={p.relative_to(snapshot).as_posix() for p in paths if p.is_file()};wanted=set(build['pmu_failure_snapshot_sha256'])|set(result['gic_priority_prepared_sha256'])
  if files!=wanted:raise ValueError('GIC snapshot file set differs')
  hashes={n:sha((snapshot/n).read_bytes()) for n in sorted(files)}
  if build.get('gic_priority_snapshot_sha256')!=hashes:raise ValueError('GIC snapshot hashes differ')
  for n in files:
   if (snapshot/n).read_bytes()!=(expected/n).read_bytes():raise ValueError('GIC reverse composition differs: '+n)
 model=root/'gic-priority-model';m=json.loads((model/'result.json').read_text(encoding='utf8'))
 from test_gic_priority_restore import CASES,source
 if m.get('passed') is not True or m.get('hardware_verified') is not False or m.get('original_off_traces_equal') is not True or m.get('cases')!={k:list(CASES) for k in ('orig','off','on')}:raise ValueError('GIC source model cases differ')
 if m.get('source_sha256')!=hashes['drivers/irqchip/irq-gic.c'] or m.get('baseline_sha256')!=build['pm_preconditions_prepared_sha256']['drivers/irqchip/irq-gic.c'] or m.get('helper_sha256')!=sourcehash['gic_priority_restore.c'] or m.get('harness_sha256')!=sourcehash['test_gic_priority_restore.py']:raise ValueError('GIC source model hashes differ')
 baseline=(root/'pm-preconditions-prepared/drivers/irqchip/irq-gic.c').read_text(encoding='utf8');final=(snapshot/'drivers/irqchip/irq-gic.c').read_text(encoding='utf8');helper=(HERE/'gic_priority_restore.c').read_text(encoding='utf8')
 for n,text in (('orig.c',source(baseline,helper)),('off.c',source(final,helper)),('on.c',source(final,helper))):
  if (model/n).read_bytes().replace(b'\r\n',b'\n')!=text.encode('utf8').replace(b'\r\n',b'\n'):raise ValueError('GIC generated source differs')
 generated={n:sha((model/n).read_bytes()) for n in ('orig.c','off.c','on.c')};logs={n:sha((model/n).read_bytes()) for n in [f'{mode}-compile.log' for mode in ('orig','off','on')]+[f'{mode}-{i}.log' for mode in ('orig','off','on') for i in range(len(CASES))]}
 if m.get('generated_sha256')!=generated or m.get('log_sha256')!=logs:raise ValueError('GIC generated evidence differs')
 for i in range(len(CASES)):
  if (model/f'orig-{i}.log').read_bytes()!=(model/f'off-{i}.log').read_bytes():raise ValueError('Original and off traces differ')
 return True

def validate(root,build,require_package_flow=True):
 if not validate_core(root,build):return False
 from test_gic_priority_binding import CASES
 q=Path(root)/'gic-priority-binding-model/result.json';proof=json.loads(q.read_text(encoding='utf8'))
 if proof.get('passed') is not True or proof.get('cases')!=list(CASES) or proof.get('harness_sha256')!=build['gic_priority_sources_sha256']['test_gic_priority_binding.py']:raise ValueError('GIC binding mutation proof differs')
 if require_package_flow:
  flow=json.loads((Path(root)/'gic-priority-package-flow-model/result.json').read_text(encoding='utf8'))
  cases=['synthetic-prototype-to-packages','missing-flag','missing-version','missing-binding-proof']
  if flow.get('passed') is not True or flow.get('hardware_verified') is not False or flow.get('cases')!=cases or flow.get('harness_sha256')!=build['gic_priority_sources_sha256']['test_gic_priority_package_flow.py'] or flow.get('package_sources_sha256')!=build['gic_priority_package_sources_sha256']:raise ValueError('GIC package flow proof differs')
 return True
