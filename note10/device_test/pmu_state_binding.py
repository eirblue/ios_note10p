"""Bind v41 state observation to the composed source and offline proofs."""
import hashlib,json,re,shutil,tempfile
from pathlib import Path
from prepare_pmu_state_audit import prepare,PIN
HERE=Path(__file__).resolve().parent
SOURCES=('prepare_pmu_state_audit.py','pmu_state_contract.h','pmu_state_pmu.c','pmu_state_chain.c','pmu_state_capture.c','pmu_state_probe.c','decode_pmu_state.py','test_pmu_state_native.py','test_pmu_state_lifecycle.py','test_pmu_state_final_lifecycle.py','test_pmu_state_worker.py','test_pmu_state_decoder.py','test_pmu_state_collector.py','pmu_state_binding.py','test_pmu_state_binding.py','test_pmu_state_package_flow.py','prepare_pmu_state_flow_compat.py')
PACKAGE_SOURCES=('prepare_linux_boot.py','build_boot_test_packages.py','precheck_window_access.py','stage_phase2.py','collect_reservation.py')
MARKERS=(b'N10STAR1',b'N10STAQ1')
COLLECTOR_DEPENDENCIES=('test_collect_reservation.py','test_cpu_cache_decode.py','test_cpu_cache_native.py','test_pm_timer_contract.py')
def sha(raw):return hashlib.sha256(raw).hexdigest()
def validate_core(root,build):
 root=Path(root);config=(root/'handoff.config').read_bytes().splitlines();image=(root/'Image').read_bytes();enabled=b'CONFIG_NOTE10_PMU_STATE_AUDIT=y' in config
 if enabled!=(build.get('pmu_state_audit') is True) or any(enabled!=(marker in image) for marker in MARKERS):raise ValueError('state Image/config/metadata mismatch')
 if not enabled:
  keys={k for k in build if k.startswith('pmu_state_')}
  if keys-{'pmu_state_audit','pmu_state_audit_version'} or build.get('pmu_state_audit') not in (None,False) or build.get('pmu_state_audit_version') is not None or any((root/n).exists() for n in ('pmu-state-prepared','pmu-state-native-model','pmu-state-final-lifecycle-model','pmu-state-worker-model')):raise ValueError('state evidence downgrade')
  return False
 if build.get('pmu_state_audit_version')!=1 or not all(x in config for x in (b'CONFIG_CPU_PM=y',b'CONFIG_ARM_PMU=y',b'CONFIG_NOTE10_CPU_PM_PRECONDITIONS=y',b'CONFIG_NOTE10_CPU_PM_BRANCH_AUDIT=y',b'CONFIG_NOTE10_PMU_FAILURE_RESTORE=y',b'CONFIG_NOTE10_GIC_PRIORITY_RESTORE=y')):raise ValueError('state prerequisites differ')
 from gic_priority_binding import validate as validate_prior
 if validate_prior(root,build) is not True:raise ValueError('prior binding missing')
 hashes={n:sha((HERE/n).read_bytes()) for n in SOURCES}
 if build.get('pmu_state_sources_sha256')!=hashes:raise ValueError('state source binding differs')
 package=build.get('pmu_state_package_sources_sha256')
 if not isinstance(package,dict) or set(package)!=set(PACKAGE_SOURCES) or any(not isinstance(v,str) or re.fullmatch(r'[0-9a-f]{64}',v) is None for v in package.values()):raise ValueError('state package source map differs')
 with tempfile.TemporaryDirectory() as tmp:
  expected=Path(tmp)/'source';shutil.copytree(root/'gic-priority-prepared',expected)
  header=root/'pmu-state-prepared/include/linux/perf_event.h';dst=expected/'include/linux/perf_event.h';dst.parent.mkdir(parents=True,exist_ok=True)
  if header.is_symlink() or sha(header.read_bytes())!=PIN:raise ValueError('perf header pin differs')
  shutil.copyfile(header,dst);result=prepare(expected,build)
  if any(build.get(k)!=v for k,v in result.items()):raise ValueError('state composition differs')
  snapshot=root/'pmu-state-prepared';paths=list(snapshot.rglob('*'))
  if snapshot.is_symlink() or any(p.is_symlink() for p in paths):raise ValueError('state snapshot symlink')
  files={p.relative_to(snapshot).as_posix() for p in paths if p.is_file()};wanted=set(build['gic_priority_snapshot_sha256'])|set(result['pmu_state_prepared_sha256'])|{'include/linux/perf_event.h'}
  if files!=wanted:raise ValueError('state snapshot file set differs')
  digests={n:sha((snapshot/n).read_bytes()) for n in sorted(files)}
  if build.get('pmu_state_snapshot_sha256')!=digests:raise ValueError('state snapshot hashes differ')
  for n in files:
   if (snapshot/n).read_bytes()!=(expected/n).read_bytes():raise ValueError('state reverse composition differs: '+n)
 _models(root,snapshot,hashes)
 dependencies=build.get('pmu_state_collector_dependencies_sha256')
 if not isinstance(dependencies,dict) or set(dependencies)!=set(COLLECTOR_DEPENDENCIES) or any(not isinstance(v,str) or re.fullmatch(r'[0-9a-f]{64}',v) is None for v in dependencies.values()):raise ValueError('collector dependency map differs')
 proof=json.loads((root/'pmu-state-collector-model/result.json').read_text(encoding='utf8'))
 if proof.get('passed') is not True or proof.get('hardware_verified') is not False or proof.get('cases')!=['valid-stopped-35-evaluations','missing-and-malformed-fail'] or proof.get('dependencies_sha256')!=dependencies or proof.get('harness_sha256')!=hashes['test_pmu_state_collector.py']:raise ValueError('collector model proof differs')
 return True

def _models(root,snapshot,hashes):
 from test_pmu_state_native import STUB,MAIN
 from test_pmu_state_final_lifecycle import BASE,EXTRA,MOCK,MAIN as LMAIN
 from test_pm_callbacks_producer import clean
 import test_pmu_state_worker as worker
 from test_fsys_pm_native import function
 getter=root/'pmu-state-native-model';m=json.loads((getter/'result.json').read_text(encoding='utf8'))
 cases=['32-slots-mixed-unbound-active-and-abnormal','foreign-pmu-first-only','index-mismatch-only','context-rejected','interrupt-rejected','unused-nonnull-unread','null-event','count-33','count-0']
 helper=snapshot/'drivers/perf/note10_pmu_state_pmu.c';source='\n'.join(x for x in helper.read_text().splitlines() if not x.startswith('#include'))
 generated=(STUB+'\n'+source+'\n'+MAIN).encode('utf8')
 if m.get('passed') is not True or m.get('hardware_verified') is not False or m.get('input_objects_unchanged') is not True or m.get('cases')!=cases or m.get('perf_event_header_sha256')!=PIN or m.get('helper_sha256')!=sha(helper.read_bytes()) or m.get('harness_sha256')!=hashes['test_pmu_state_native.py'] or m.get('generated_sha256')!=sha(generated) or (getter/'native.c').read_bytes().replace(b'\r\n',b'\n')!=generated.replace(b'\r\n',b'\n') or any((getter/n).read_bytes() for n in ('compile.log','run.log')):raise ValueError('getter model differs')
 lifecycle=root/'pmu-state-final-lifecycle-model';m=json.loads((lifecycle/'result.json').read_text(encoding='utf8'))
 paths={'chain':'kernel/note10_pm_pre_chain.c','capture':'kernel/power/note10_pm_pre_capture.c','branch_chain':'kernel/note10_pm_branch_chain.c','branch_capture':'kernel/power/note10_pm_branch_capture.c','state_chain':'kernel/note10_pmu_state_chain.c','state_capture':'kernel/power/note10_pmu_state_capture.c'}
 def raw(n):return re.sub(r'^#include[^\n]*\n','',(snapshot/paths[n]).read_text(encoding='utf-8-sig'),flags=re.M)
 gen=(BASE+EXTRA+clean('pm_preconditions_contract.h')+clean('pm_branch_contract.h')+clean('pmu_state_contract.h')+MOCK+raw('branch_chain')+raw('branch_capture')+raw('state_chain')+raw('state_capture')+raw('chain')+raw('capture')+LMAIN).encode('utf8')
 logs={n:sha((lifecycle/n).read_bytes()) for n in ['compile.log']+[f'case-{i}.log' for i in range(5)]}
 if m.get('passed') is not True or m.get('hardware_verified') is not False or m.get('actual_final_capture_and_chain') is not True or m.get('state_feature') is not True or m.get('cases')!=['success','trylock-failure','post-context-failure','foreign-owner','duplicate-generation'] or m.get('source_sha256')!={k:sha((snapshot/v).read_bytes()) for k,v in paths.items()} or m.get('harness_sha256')!=hashes['test_pmu_state_final_lifecycle.py'] or m.get('generated_c_sha256')!=sha(gen) or (lifecycle/'lifecycle.c').read_bytes().replace(b'\r\n',b'\n')!=gen.replace(b'\r\n',b'\n') or m.get('log_sha256')!=logs:raise ValueError('lifecycle model differs')
 wm=root/'pmu-state-worker-model';m=json.loads((wm/'result.json').read_text(encoding='utf8'));path=snapshot/'arch/arm64/mm/note10_pm_timer_roundtrip.c';raw_worker=path.read_text(encoding='utf8')
 stub=worker.WORKER_STUB.replace('static u32 n10_frame_checksum(const char*p,int n){(void)p;(void)n;return 0;}','static u32 n10_frame_checksum(const char*p,int n){u32 h=2166136261U;while(n--)h=(h^(unsigned char)*p++)*16777619U;return h;}')
 code=stub+worker.ADD+clean('pm_preconditions_contract.h')+clean('pm_branch_contract.h')+clean('pmu_state_contract.h')+worker.MOCK.replace('value[4]=1','value[4]=2')+worker.BRANCH_MOCK.replace('mode==1','mode==10').replace('nonnull=1','nonnull=3')+worker.STATE_MOCK+clean('pm_preconditions_probe.c')+clean('pm_branch_probe.c')+clean('pmu_state_probe.c')+function(raw_worker,'static void n10_pm_worker(struct work_struct *unused)\n{')+'\nint main(int argc,char**argv){mode=atoi(argv[1]);n10_pm_worker(NULL);return 0;}\n'
 expected={'enabled.c':'#define CONFIG_NOTE10_PMU_STATE_AUDIT 1\n'+code,'disabled.c':code};generated={n:sha(text.encode('utf8')) for n,text in expected.items()}
 logs={n:sha((wm/n).read_bytes()) for n in [f'{mode}-compile.log' for mode in ('enabled','disabled')]+[f'{mode}-{i}.log' for mode in ('enabled','disabled') for i in (0,1,9,10,11)]}
 cases=['enabled-success','enabled-outer-error','enabled-gic-error','enabled-branch-error','enabled-state-error','disabled-success','disabled-outer-error','disabled-gic-error','disabled-branch-error','disabled-state-error']
 if m.get('passed') is not True or m.get('hardware_verified') is not False or m.get('actual_final_worker_and_producers') is not True or m.get('state_feature') is not True or m.get('cases')!=cases or m.get('source_sha256')!=sha(path.read_bytes()) or m.get('harness_sha256')!=hashes['test_pmu_state_worker.py'] or m.get('generated_c_sha256')!=generated or m.get('log_sha256')!=logs or any((wm/n).read_bytes().replace(b'\r\n',b'\n')!=text.encode('utf8').replace(b'\r\n',b'\n') for n,text in expected.items()):raise ValueError('worker model differs')

def validate(root,build,require_package_flow=True):
 if not validate_core(root,build):return False
 from test_pmu_state_binding import CASES
 proof=json.loads((Path(root)/'pmu-state-binding-model/result.json').read_text(encoding='utf8'))
 if proof.get('passed') is not True or proof.get('cases')!=list(CASES) or proof.get('harness_sha256')!=build['pmu_state_sources_sha256']['test_pmu_state_binding.py']:raise ValueError('state mutation proof differs')
 if require_package_flow:
  proof=json.loads((Path(root)/'pmu-state-package-flow-model/result.json').read_text(encoding='utf8'))
  cases=['synthetic-prototype-to-packages','missing-flag','missing-version','missing-binding-proof']
  if proof.get('passed') is not True or proof.get('hardware_verified') is not False or proof.get('cases')!=cases or proof.get('harness_sha256')!=build['pmu_state_sources_sha256']['test_pmu_state_package_flow.py'] or proof.get('package_sources_sha256')!=build['pmu_state_package_sources_sha256']:raise ValueError('state package proof differs')
 return True
