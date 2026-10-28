"""Bind v45 EHLD lock availability to its source, profile, and execution proofs."""
import hashlib,json,re,shutil,tempfile
from pathlib import Path
from ehld_lock_profile import PINS as PROFILE_PINS,verify_config
from prepare_ehld_lock_audit import prepare,FILES,CHANGED

HERE=Path(__file__).resolve().parent
SOURCES=('prepare_ehld_lock_audit.py','prepare_ehld_lock_flow_compat.py','ehld_lock_profile.py','ehld_lock_contract.h','ehld_lock_getter.c','ehld_lock_chain.c','ehld_lock_capture.c','ehld_lock_probe.c','decode_ehld_lock.py','test_ehld_lock_native.py','test_ehld_lock_composition.py','test_ehld_lock_final_lifecycle.py','test_ehld_lock_worker.py','test_ehld_lock_decoder.py','test_ehld_lock_profile.py','test_ehld_lock_collector.py','ehld_lock_binding.py','test_ehld_lock_binding.py','test_ehld_lock_package_flow.py')
PACKAGE_SOURCES=('prepare_linux_boot.py','build_boot_test_packages.py','precheck_window_access.py','stage_phase2.py','collect_reservation.py')
from test_ehld_lock_collector import DEPENDENCIES as COLLECTOR_DEPENDENCIES
MARKERS=(b'N10ELM1',b'N10ELQ1')

def sha(data):return hashlib.sha256(data).hexdigest()
def valid_map(value,names):return isinstance(value,dict) and set(value)==set(names) and all(isinstance(x,str) and re.fullmatch('[0-9a-f]{64}',x) for x in value.values())

def assert_scope(root,build):
 root=Path(root);raw=(root/'Image').read_bytes();config=(root/'handoff.config').read_bytes().splitlines()
 enabled=b'CONFIG_NOTE10_EHLD_LOCK_AUDIT=y' in config
 if enabled!=(build.get('ehld_lock_audit') is True) or any((marker in raw)!=enabled for marker in MARKERS):raise ValueError('EHLD Image/config/metadata mismatch')
 if not enabled:
  if build.get('ehld_lock_audit') not in (None,False):raise ValueError('EHLD audit flag malformed')
  extras={k for k in build if k.startswith('ehld_lock_') and k not in ('ehld_lock_audit','ehld_lock_audit_version')}
  outputs=('ehld-lock-prepared','ehld-lock-profile-inputs','ehld-lock-profile-model','ehld-lock-composition-model','ehld-lock-native-model','ehld-lock-final-lifecycle-model','ehld-lock-worker-model','ehld-lock-decoder-model','ehld-lock-collector-model','ehld-lock-binding-model','ehld-lock-package-flow-model')
  if extras or build.get('ehld_lock_audit_version') is not None or any((root/name).exists() for name in outputs):raise ValueError('EHLD evidence downgrade')
 return enabled

def validate_core(root,build):
 root=Path(root)
 if not assert_scope(root,build):return False
 if build.get('ehld_lock_audit_version')!=1:raise ValueError('EHLD schema version differs')
 if build.get('rcu_context_audit') is not True:raise ValueError('EHLD requires the prior RCU profile')
 from rcu_context_binding import validate as validate_rcu
 if validate_rcu(root,build,require_package_flow=False) is not True:raise ValueError('prior RCU binding missing')
 config=(root/'handoff.config').read_bytes()
 profile=verify_config(config)
 recorded=build.get('ehld_lock_profile_result')
 if not isinstance(recorded,dict) or recorded.get('measured_config_sha256')!=sha(config) or recorded.get('disabled')!=profile['disabled'] or recorded.get('preserved')!=profile['preserved']:
  raise ValueError('measured EHLD profile result differs')
 inputs=root/'ehld-lock-profile-inputs'
 if inputs.is_symlink() or {p.relative_to(inputs).as_posix() for p in inputs.rglob('*') if p.is_file()}!=set(PROFILE_PINS):raise ValueError('profile input snapshot allowlist differs')
 profile_map={n:sha((inputs/n).read_bytes()) for n in sorted(PROFILE_PINS)}
 if profile_map!=PROFILE_PINS or build.get('ehld_lock_profile_inputs_sha256')!=profile_map or build.get('ehld_lock_profile_source_sha256')!=profile_map:raise ValueError('profile input snapshot pin differs')
 baseline=build.get('rcu_context_snapshot_sha256');prepared=build.get('ehld_lock_prepared_sha256');snapmap=build.get('ehld_lock_snapshot_sha256')
 if not isinstance(baseline,dict) or len(baseline)!=73 or not isinstance(prepared,dict) or set(prepared)!=set(CHANGED)|set(FILES) or not isinstance(snapmap,dict) or set(snapmap)!=set(baseline)|set(prepared) or len(snapmap)!=78:raise ValueError('EHLD 78-source snapshot maps differ')
 snapshot=root/'ehld-lock-prepared'
 paths=list(snapshot.rglob('*'))
 if snapshot.is_symlink() or any(x.is_symlink() for x in paths):raise ValueError('EHLD snapshot symlink')
 actual={x.relative_to(snapshot).as_posix() for x in paths if x.is_file()}
 if actual!=set(snapmap) or {n:sha((snapshot/n).read_bytes()) for n in sorted(actual)}!=snapmap:raise ValueError('EHLD snapshot bytes differ')
 if any(snapmap[n]!=prepared[n] for n in prepared):raise ValueError('EHLD prepared map differs from final snapshot')
 # Rebuild the composition from the pinned v44 snapshot so a coherent
 # mutation of both source bytes and their recorded maps cannot pass.
 with tempfile.TemporaryDirectory() as temp:
  base=Path(temp)/'v44';shutil.copytree(root/'rcu-context-prepared',base)
  expected_report=dict(build);prepare(base,expected_report)
  expected=Path(temp)/'v45';expected_map=__import__('prepare_ehld_lock_audit').snapshot(base,expected,expected_report)
  if expected_map!=snapmap or any((expected/n).read_bytes()!=(snapshot/n).read_bytes() for n in snapmap):raise ValueError('EHLD reverse composition differs from v44 baseline')
 sources=build.get('ehld_lock_sources_sha256');packages=build.get('ehld_lock_package_sources_sha256');collector=build.get('ehld_lock_collector_dependencies_sha256')
 if not valid_map(sources,SOURCES) or sources!={n:sha((HERE/n).read_bytes()) for n in SOURCES}:raise ValueError('EHLD source map differs')
 if not valid_map(packages,PACKAGE_SOURCES) or packages!={n:sha((HERE/n).read_bytes()) for n in PACKAGE_SOURCES}:raise ValueError('EHLD package map differs')
 if not valid_map(collector,COLLECTOR_DEPENDENCIES) or collector!={n:sha((HERE/n).read_bytes()) for n in COLLECTOR_DEPENDENCIES}:raise ValueError('EHLD collector dependency map differs')
 # The build artifact must retain the exact source composition, not just its hashes.
 for name in prepared:
  if sha((snapshot/name).read_bytes())!=prepared[name]:raise ValueError('EHLD prepared source changed: '+name)
 _models(root,build)
 return True

def _models(root,build):
 from test_ehld_lock_native import CASES as NATIVE_CASES
 from test_ehld_lock_final_lifecycle import CASES as LIFE_CASES,PATHS as LIFE_PATHS,make_code as make_life
 from test_ehld_lock_worker import make_code as make_worker
 snapshot=root/'ehld-lock-prepared'
 def result(name):return json.loads((root/name/'result.json').read_text(encoding='utf8'))
 profile=result('ehld-lock-profile-model')
 expected_profile_cases=['valid-profile']+['reject-'+name+'-'+value for name in __import__('ehld_lock_profile').DISABLE for value in ('y','m','garbage')]+['reject-missing-'+name for name in __import__('ehld_lock_profile').PRESERVE]+['reject-disabled-'+name for name in ('NOTE10_EHLD_LOCK_AUDIT','NOTE10_RCU_CONTEXT_AUDIT')]+['reject-duplicate','pinned-source-map']
 if profile.get('passed') is not True or profile.get('hardware_verified') is not False or profile.get('cases')!=expected_profile_cases or profile.get('harness_sha256')!=build['ehld_lock_sources_sha256']['test_ehld_lock_profile.py'] or profile.get('profile_sha256')!=build['ehld_lock_sources_sha256']['ehld_lock_profile.py'] or profile.get('pins')!=PROFILE_PINS:raise ValueError('EHLD profile proof differs')
 composition=json.loads((root/'ehld-lock-composition-model/composition-proof.json').read_text(encoding='utf8'))
 composition_dir=root/'ehld-lock-composition-model';composition_snapshot=composition_dir/'snapshot';composition_source=composition_dir/'source'
 composition_checks={'collector-once':True,'final-chain-check':True,'check-before-unlock':True,'lifecycle-hooks':True,'worker-ifdef':True,'getter-no-event-pmu':True,'config-default-off':True}
 composition_map={p.relative_to(composition_snapshot).as_posix():sha(p.read_bytes()) for p in composition_snapshot.rglob('*') if p.is_file()}
 composition_source_map={p.relative_to(composition_source).as_posix():sha(p.read_bytes()) for p in composition_source.rglob('*') if p.is_file()}
 if composition.get('passed') is not True or composition.get('hardware_verified') is not False or composition.get('baseline_files')!=73 or composition.get('final_files')!=78 or composition.get('checks')!=composition_checks or composition.get('prepared_sha256')!=build['ehld_lock_prepared_sha256'] or composition.get('snapshot_sha256')!=build['ehld_lock_snapshot_sha256'] or composition_map!=build['ehld_lock_snapshot_sha256'] or composition_source_map!=composition_map or any((composition_source/n).read_bytes()!=(composition_snapshot/n).read_bytes() for n in composition_map) or composition.get('harness_sha256')!=build['ehld_lock_sources_sha256']['test_ehld_lock_composition.py']:raise ValueError('EHLD composition proof differs')
 m=result('ehld-lock-native-model');native_dir=root/'ehld-lock-native-model'
 native_paths=('include/linux/note10_ehld_lock_audit.h','drivers/soc/samsung/debug/note10_ehld_lock_getter.c','kernel/note10_ehld_lock_chain.c')
 native_code=__import__('test_ehld_lock_native').PRELUDE+''.join(__import__('test_ehld_lock_native').source(root/'ehld-lock-prepared'/n) for n in native_paths)+__import__('test_ehld_lock_native').MAIN
 native_logs={p.name:sha(p.read_bytes()) for p in native_dir.glob('*.log')}
 expected_native_logs={'compile.log',*[name+'.log' for name in NATIVE_CASES]}
 if m.get('passed') is not True or m.get('hardware_verified') is not False or m.get('cases')!=NATIVE_CASES or m.get('source_sha256')!={n:sha((snapshot/n).read_bytes()) for n in native_paths} or m.get('harness_sha256')!=build['ehld_lock_sources_sha256']['test_ehld_lock_native.py'] or m.get('generated_sha256')!=sha(native_code.encode()) or (native_dir/'model.c').read_bytes()!=native_code.encode() or set(native_logs)!=expected_native_logs or m.get('logs_sha256')!=native_logs:raise ValueError('EHLD native model proof differs')
 m=result('ehld-lock-final-lifecycle-model');code=make_life(root/'ehld-lock-prepared')
 life_dir=root/'ehld-lock-final-lifecycle-model';life_paths={n:v for n,v in LIFE_PATHS.items()}
 life_logs={p.name:sha(p.read_bytes()) for p in life_dir.glob('*.log')}
 if m.get('passed') is not True or m.get('hardware_verified') is not False or m.get('cases')!=LIFE_CASES or m.get('source_sha256')!={k:sha((snapshot/v).read_bytes()) for k,v in life_paths.items()} or m.get('harness_sha256')!=build['ehld_lock_sources_sha256']['test_ehld_lock_final_lifecycle.py'] or m.get('generated_sha256')!=sha(code.encode()) or (life_dir/'lifecycle.c').read_bytes()!=code.encode() or set(life_logs)!={'compile.log',*[x+'.log' for x in LIFE_CASES]} or m.get('logs_sha256')!=life_logs:raise ValueError('EHLD actual caller proof differs')
 m=result('ehld-lock-worker-model');worker=make_worker(root/'ehld-lock-prepared')
 worker_dir=root/'ehld-lock-worker-model';worker_cases=['enabled-'+str(i) for i in (0,1,9,10,11,12,13,16,17,18,19,20,22,23,24,25)]+['disabled-'+str(i) for i in (0,1,9,10,11,12,13,16,19)]
 worker_sources={'worker':sha((snapshot/'arch/arm64/mm/note10_pm_timer_roundtrip.c').read_bytes()),'producer':sha((snapshot/'arch/arm64/mm/note10_ehld_lock_probe.c').read_bytes())}
 worker_generated={p.name:sha(p.read_bytes()) for p in worker_dir.glob('*.c')};worker_logs={p.name:sha(p.read_bytes()) for p in worker_dir.glob('*.log')}
 worker_code=make_worker(snapshot);expected_worker_code={'enabled.c':'#define CONFIG_NOTE10_RCU_CONTEXT_AUDIT 1\n#define CONFIG_NOTE10_EHLD_LOCK_AUDIT 1\n'+worker_code,'disabled.c':'#define CONFIG_NOTE10_RCU_CONTEXT_AUDIT 1\n'+worker_code}
 if m.get('passed') is not True or m.get('hardware_verified') is not False or m.get('actual_worker') is not True or m.get('cases')!=worker_cases or m.get('source_sha256')!=worker_sources or m.get('harness_sha256')!=build['ehld_lock_sources_sha256']['test_ehld_lock_worker.py'] or m.get('generated_sha256')!={k:sha(v.encode()) for k,v in expected_worker_code.items()} or any((worker_dir/k).read_bytes()!=v.encode() for k,v in expected_worker_code.items()) or set(worker_generated)!={'enabled.c','disabled.c'} or m.get('log_sha256')!=worker_logs or set(worker_logs)!={'enabled-compile.log','disabled-compile.log',*[x+'.log' for x in worker_cases]}:raise ValueError('EHLD actual worker proof differs')
 m=result('ehld-lock-decoder-model')
 decoder=__import__('test_ehld_lock_decoder')
 if m.get('passed') is not True or m.get('hardware_verified') is not False or m.get('cases')!=decoder.CASES or m.get('harness_sha256')!=build['ehld_lock_sources_sha256']['test_ehld_lock_decoder.py'] or m.get('decoder_sha256')!=build['ehld_lock_sources_sha256']['decode_ehld_lock.py'] or m.get('prior_decoder_sha256')!=sha((HERE/'decode_pm_preconditions.py').read_bytes()):raise ValueError('EHLD decoder proof differs')
 m=result('ehld-lock-collector-model')
 from test_ehld_lock_collector import DEPENDENCIES as collector_dependencies
 if tuple(COLLECTOR_DEPENDENCIES)!=tuple(collector_dependencies):raise ValueError('EHLD collector dependency allowlist differs')
 if m.get('passed') is not True or m.get('hardware_verified') is not False or m.get('cases')!=['valid-39-preserves-prior-38','missing-malformed-mutation-fail','unrequested-fail','package-scope-version-fail'] or m.get('dependencies_sha256')!=build['ehld_lock_collector_dependencies_sha256'] or m.get('harness_sha256')!=build['ehld_lock_sources_sha256']['test_ehld_lock_collector.py']:raise ValueError('EHLD collector proof differs')

def validate(root,build,require_package_flow=True):
 if not validate_core(root,build):return False
 from test_ehld_lock_binding import CASES
 proof=json.loads((Path(root)/'ehld-lock-binding-model/result.json').read_text(encoding='utf8'))
 if proof.get('passed') is not True or proof.get('cases')!=list(CASES) or proof.get('harness_sha256')!=build['ehld_lock_sources_sha256']['test_ehld_lock_binding.py']:raise ValueError('EHLD binding mutation proof differs')
 if require_package_flow:
  root=Path(root);proof=json.loads((root/'ehld-lock-package-flow-model/result.json').read_text(encoding='utf8'))
  from test_ehld_lock_package_flow import HISTORY_FILES
  expected_history={name:sha((HERE/name).read_bytes()) for name in HISTORY_FILES}
  cases={'v44':('test_rcu_context_package_flow.py',['synthetic-prototype-to-packages','missing-flag','missing-version','missing-binding-proof']),'v43':('test_fpsimd_reference_package_flow.py',['synthetic-prototype-to-packages','missing-flag','missing-version','missing-binding-proof']),'v42':('test_pmu_control_package_flow.py',['synthetic-prototype-to-packages','missing-flag','missing-version','missing-binding-proof']),'v41':('test_pmu_state_package_flow.py',['synthetic-prototype-to-packages','missing-flag','missing-version','missing-binding-proof']),'v40':('test_gic_priority_package_flow.py',['synthetic-prototype-to-packages','missing-flag','missing-version','missing-binding-proof']),'v39':('test_pmu_failure_package_flow.py',['synthetic-prototype-to-packages','missing-flag','missing-version','missing-binding-proof'])}
  if proof.get('passed') is not True or proof.get('hardware_verified') is not False or proof.get('cases')!=['synthetic-prototype-to-packages','missing-flag','missing-version','missing-binding-proof'] or proof.get('harness_sha256')!=build['ehld_lock_sources_sha256']['test_ehld_lock_package_flow.py'] or proof.get('package_sources_sha256')!=build['ehld_lock_package_sources_sha256'] or proof.get('history_versions')!=list(cases) or proof.get('history_files_sha256')!=expected_history:raise ValueError('EHLD package/history flow proof differs')
  for version,(script,expected_cases) in cases.items():
   item=json.loads((root/'ehld-lock-package-flow-model/history'/(version+'-package-flow')/'result.json').read_text(encoding='utf8'))
   if item.get('passed') is not True or item.get('hardware_verified') is not False or item.get('cases')!=expected_cases or item.get('harness_sha256')!=sha((HERE/script).read_bytes()):raise ValueError('Historical package-flow proof differs: '+version)
 return True
