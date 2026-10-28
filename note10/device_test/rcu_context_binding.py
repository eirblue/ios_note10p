"""Bind v44 RCU observation to the exact previous composition and proofs."""
import hashlib,json,re,shutil,tempfile
from pathlib import Path
from prepare_rcu_context_audit import prepare,PINS
HERE=Path(__file__).resolve().parent
SOURCES=('prepare_rcu_context_audit.py','rcu_context_contract.h','rcu_context_getter.c','rcu_context_chain.c','rcu_context_capture.c','rcu_context_probe.c','decode_rcu_context.py','test_rcu_context_native.py','test_rcu_context_final_lifecycle.py','test_rcu_context_worker.py','test_rcu_context_decoder.py','test_rcu_context_collector.py','rcu_context_binding.py','test_rcu_context_binding.py','test_rcu_context_package_flow.py','prepare_rcu_context_flow_compat.py')
PACKAGE_SOURCES=('prepare_linux_boot.py','build_boot_test_packages.py','precheck_window_access.py','stage_phase2.py','collect_reservation.py')
COLLECTOR_DEPENDENCIES=('test_fpsimd_reference_collector.py','test_fpsimd_reference_decoder.py','test_pmu_control_decoder.py','test_pmu_state_decoder.py','test_pmu_state_collector.py','test_collect_reservation.py','test_cpu_cache_decode.py','test_cpu_cache_native.py','test_pm_timer_contract.py')
MARKERS=(b'N10RCM1',b'N10RCQ1')
def sha(x):return hashlib.sha256(x).hexdigest()
def valid_map(x,names):return isinstance(x,dict) and set(x)==set(names) and all(isinstance(v,str) and re.fullmatch(r'[0-9a-f]{64}',v) for v in x.values())
def validate_core(root,build):
 root=Path(root);config=(root/'handoff.config').read_bytes().splitlines();image=(root/'Image').read_bytes();enabled=b'CONFIG_NOTE10_RCU_CONTEXT_AUDIT=y' in config
 if enabled!=(build.get('rcu_context_audit') is True) or any(enabled!=(x in image) for x in MARKERS):raise ValueError('RCU Image/config/metadata mismatch')
 if not enabled:
  keys={k for k in build if k.startswith('rcu_context_')}
  if keys-{'rcu_context_audit','rcu_context_audit_version'} or build.get('rcu_context_audit') not in (None,False) or build.get('rcu_context_audit_version') is not None or any((root/n).exists() for n in ('rcu-context-prepared','rcu-context-native-model','rcu-context-final-lifecycle-model','rcu-context-worker-model','rcu-context-decoder-model','rcu-context-collector-model')):raise ValueError('RCU evidence downgrade')
  return False
 if build.get('rcu_context_audit_version')!=1 or not all(x in config for x in (b'CONFIG_PREEMPT_RCU=y',b'CONFIG_NOTE10_FPSIMD_REFERENCE_AUDIT=y',b'CONFIG_NOTE10_CPU_PM_PRECONDITIONS=y')):raise ValueError('RCU prerequisites differ')
 from fpsimd_reference_binding import validate as validate_prior
 if validate_prior(root,build) is not True:raise ValueError('prior reference binding missing')
 hashes={n:sha((HERE/n).read_bytes()) for n in SOURCES}
 if build.get('rcu_context_sources_sha256')!=hashes:raise ValueError('RCU source hashes differ')
 if not valid_map(build.get('rcu_context_package_sources_sha256'),PACKAGE_SOURCES) or not valid_map(build.get('rcu_context_collector_dependencies_sha256'),COLLECTOR_DEPENDENCIES):raise ValueError('recorded dependencies differ')
 with tempfile.TemporaryDirectory() as temp:
  expected=Path(temp)/'source';shutil.copytree(root/'fpsimd-reference-prepared',expected);snapshot=root/'rcu-context-prepared'
  for n,digest in PINS.items():
   p=snapshot/n
   if p.is_symlink():raise ValueError('RCU source symlink')
   raw=p.read_bytes()
   if n=='kernel/rcu/tree.c':
    suffix=b'\n#ifdef CONFIG_NOTE10_RCU_CONTEXT_AUDIT\n#include "note10_rcu_context_getter.c"\n#endif\n'
    if not raw.endswith(suffix):raise ValueError('RCU getter include differs')
    raw=raw[:-len(suffix)]
   if sha(raw)!=digest:raise ValueError('RCU original pin differs: '+n)
   target=expected/n;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(raw)
  result=prepare(expected,build)
  if any(build.get(k)!=v for k,v in result.items()):raise ValueError('RCU composition differs')
  paths=list(snapshot.rglob('*'))
  if snapshot.is_symlink() or any(p.is_symlink() for p in paths):raise ValueError('RCU snapshot symlink')
  files={p.relative_to(snapshot).as_posix() for p in paths if p.is_file()};wanted=set(build['fpsimd_reference_snapshot_sha256'])|set(result['rcu_context_prepared_sha256'])|set(PINS)
  if files!=wanted or build.get('rcu_context_snapshot_sha256')!={n:sha((snapshot/n).read_bytes()) for n in sorted(files)}:raise ValueError('RCU snapshot map differs')
  for n in files:
   if (snapshot/n).read_bytes()!=(expected/n).read_bytes():raise ValueError('RCU reverse composition differs: '+n)
 _models(root,snapshot,hashes,build);return True
def _models(root,snapshot,hashes,build):
 import test_rcu_context_native as native
 import test_rcu_context_final_lifecycle as life
 import test_rcu_context_worker as worker
 import test_rcu_context_decoder as decoder
 def model(n):return root/('rcu-context-'+n+'-model')
 def result(p):return json.loads((p/'result.json').read_text(encoding='utf8'))
 paths={'getter':snapshot/'kernel/rcu/note10_rcu_context_getter.c','chain':snapshot/'kernel/note10_rcu_context_chain.c'};n=model('native');m=result(n);code=native.PRE+''.join('\n'.join(l for l in p.read_text().splitlines() if not l.startswith('#include')) for p in paths.values())+native.POST
 if m.get('passed') is not True or m.get('hardware_verified') is not False or m.get('cases')!=native.CASES or m.get('source_sha256')!={k:sha(v.read_bytes()) for k,v in paths.items()} or m.get('harness_sha256')!=hashes['test_rcu_context_native.py'] or m.get('generated_sha256')!=sha(code.encode()) or (n/'model.c').read_bytes()!=code.encode() or m.get('log_sha256')!={x:sha((n/x).read_bytes()) for x in ('compile.log','run.log')}:raise ValueError('RCU native proof differs')
 n=model('final-lifecycle');m=result(n);code=life.make_code(snapshot);logs=['compile.log']+[x+'.log' for x in life.CASES]
 if m.get('passed') is not True or m.get('hardware_verified') is not False or m.get('cases')!=life.CASES or m.get('source_sha256')!={k:sha((snapshot/v).read_bytes()) for k,v in life.PATHS.items()} or m.get('harness_sha256')!=hashes['test_rcu_context_final_lifecycle.py'] or m.get('generated_sha256')!=sha(code.encode()) or (n/'lifecycle.c').read_bytes()!=code.encode() or m.get('log_sha256')!={x:sha((n/x).read_bytes()) for x in logs}:raise ValueError('RCU lifecycle proof differs')
 n=model('worker');m=result(n);code=worker.make_code(snapshot);expected={'enabled.c':'#define CONFIG_NOTE10_RCU_CONTEXT_AUDIT 1\n'+code,'disabled.c':code};paths={'worker':'arch/arm64/mm/note10_pm_timer_roundtrip.c','fps_producer':'arch/arm64/mm/note10_fpsimd_reference_probe.c','rcu_producer':'arch/arm64/mm/note10_rcu_context_probe.c'};logs=[x+'-compile.log' for x in ('enabled','disabled')]+[x+'.log' for x in worker.CASES]
 if m.get('passed') is not True or m.get('hardware_verified') is not False or m.get('cases')!=worker.CASES or m.get('source_sha256')!={k:sha((snapshot/v).read_bytes()) for k,v in paths.items()} or m.get('harness_sha256')!=hashes['test_rcu_context_worker.py'] or m.get('generated_sha256')!={k:sha(v.encode()) for k,v in expected.items()} or any((n/k).read_bytes()!=v.encode() for k,v in expected.items()) or m.get('log_sha256')!={x:sha((n/x).read_bytes()) for x in logs}:raise ValueError('RCU worker proof differs')
 n=model('decoder');m=result(n)
 if m.get('passed') is not True or m.get('hardware_verified') is not False or m.get('cases')!=decoder.CASES or m.get('harness_sha256')!=hashes['test_rcu_context_decoder.py'] or m.get('decoder_sha256')!=hashes['decode_rcu_context.py']:raise ValueError('RCU decoder proof differs')
 n=model('collector');m=result(n)
 if m.get('passed') is not True or m.get('hardware_verified') is not False or m.get('cases')!=['valid-38-evaluations','missing-and-malformed-fail','unexpected-disabled-fail'] or m.get('dependencies_sha256')!=build['rcu_context_collector_dependencies_sha256'] or m.get('harness_sha256')!=hashes['test_rcu_context_collector.py']:raise ValueError('RCU collector proof differs')
def validate(root,build,require_package_flow=True):
 if not validate_core(root,build):return False
 from test_rcu_context_binding import CASES
 p=json.loads((Path(root)/'rcu-context-binding-model/result.json').read_text(encoding='utf8'))
 if p.get('passed') is not True or p.get('cases')!=list(CASES) or p.get('harness_sha256')!=build['rcu_context_sources_sha256']['test_rcu_context_binding.py']:raise ValueError('RCU mutation proof differs')
 if require_package_flow:
  p=json.loads((Path(root)/'rcu-context-package-flow-model/result.json').read_text(encoding='utf8'));cases=['synthetic-prototype-to-packages','missing-flag','missing-version','missing-binding-proof']
  if p.get('passed') is not True or p.get('hardware_verified') is not False or p.get('cases')!=cases or p.get('harness_sha256')!=build['rcu_context_sources_sha256']['test_rcu_context_package_flow.py'] or p.get('package_sources_sha256')!=build['rcu_context_package_sources_sha256']:raise ValueError('RCU package proof differs')
 return True
