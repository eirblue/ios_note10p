"""Bind v42 PMU control observation to source, models and Image."""
import hashlib,json,re,shutil,tempfile
from pathlib import Path
from prepare_pmu_control_audit import prepare,PINS
HERE=Path(__file__).resolve().parent
SOURCES=('prepare_pmu_control_audit.py','pmu_control_contract.h','pmu_control_bridge.c','pmu_control_backend.c','pmu_control_chain.c','pmu_control_capture.c','pmu_control_probe.c','decode_pmu_control.py','test_pmu_control_native.py','test_pmu_control_final_lifecycle.py','test_pmu_control_worker.py','test_pmu_control_decoder.py','test_pmu_control_collector.py','pmu_control_binding.py','test_pmu_control_binding.py','test_pmu_control_package_flow.py','prepare_pmu_control_flow_compat.py')
PACKAGE_SOURCES=('prepare_linux_boot.py','build_boot_test_packages.py','precheck_window_access.py','stage_phase2.py','collect_reservation.py')
COLLECTOR_DEPENDENCIES=('test_pmu_state_collector.py','test_collect_reservation.py','test_cpu_cache_decode.py','test_cpu_cache_native.py','test_pm_timer_contract.py')
MARKERS=(b'N10PCTR1',b'N10PCTQ1')
def sha(raw):return hashlib.sha256(raw).hexdigest()
def validate_core(root,build):
 root=Path(root);config=(root/'handoff.config').read_bytes().splitlines();image=(root/'Image').read_bytes();enabled=b'CONFIG_NOTE10_PMU_CONTROL_AUDIT=y' in config
 if enabled!=(build.get('pmu_control_audit') is True) or any(enabled!=(marker in image) for marker in MARKERS):raise ValueError('control Image/config/metadata mismatch')
 if not enabled:
  keys={k for k in build if k.startswith('pmu_control_')}
  if keys-{'pmu_control_audit','pmu_control_audit_version'} or build.get('pmu_control_audit') not in (None,False) or build.get('pmu_control_audit_version') is not None or any((root/n).exists() for n in ('pmu-control-prepared','pmu-control-native-model','pmu-control-final-lifecycle-model','pmu-control-worker-model','pmu-control-collector-model')):raise ValueError('control evidence downgrade')
  return False
 if build.get('pmu_control_audit_version')!=1 or not all(x in config for x in (b'CONFIG_CPU_PM=y',b'CONFIG_ARM_PMU=y',b'CONFIG_NOTE10_PMU_STATE_AUDIT=y',b'CONFIG_NOTE10_GIC_PRIORITY_RESTORE=y',b'CONFIG_NOTE10_PMU_FAILURE_RESTORE=y',b'CONFIG_NOTE10_CPU_PM_PRECONDITIONS=y',b'CONFIG_NOTE10_CPU_PM_BRANCH_AUDIT=y')):raise ValueError('control prerequisites differ')
 from pmu_state_binding import validate as validate_prior
 if validate_prior(root,build) is not True:raise ValueError('prior state binding missing')
 hashes={n:sha((HERE/n).read_bytes()) for n in SOURCES}
 if build.get('pmu_control_sources_sha256')!=hashes:raise ValueError('control source binding differs')
 package=build.get('pmu_control_package_sources_sha256')
 if not isinstance(package,dict) or set(package)!=set(PACKAGE_SOURCES) or any(not isinstance(v,str) or re.fullmatch(r'[0-9a-f]{64}',v) is None for v in package.values()):raise ValueError('control package source map differs')
 with tempfile.TemporaryDirectory() as tmp:
  expected=Path(tmp)/'source';shutil.copytree(root/'pmu-state-prepared',expected)
  snapshot=root/'pmu-control-prepared'
  for n,digest in PINS.items():
   if n=='include/linux/perf/arm_pmu.h':continue
   src=snapshot/n;dst=expected/n;dst.parent.mkdir(parents=True,exist_ok=True)
   if src.is_symlink():raise ValueError('pinned source symlink')
   # The backend is modified by this layer; reconstruct its exact original below.
   data=src.read_bytes()
   if n=='arch/arm64/kernel/perf_event.c':
    suffix=b'\n#ifdef CONFIG_NOTE10_PMU_CONTROL_AUDIT\n#include "note10_pmu_control_backend.c"\n#endif\n'
    if not data.endswith(suffix):raise ValueError('backend suffix differs')
    data=data[:-len(suffix)]
   if sha(data)!=digest:raise ValueError('source pin differs: '+n)
   dst.write_bytes(data)
  result=prepare(expected,build)
  if any(build.get(k)!=v for k,v in result.items()):raise ValueError('control composition differs')
  paths=list(snapshot.rglob('*'))
  if snapshot.is_symlink() or any(p.is_symlink() for p in paths):raise ValueError('control snapshot symlink')
  files={p.relative_to(snapshot).as_posix() for p in paths if p.is_file()};wanted=set(build['pmu_state_snapshot_sha256'])|set(result['pmu_control_prepared_sha256'])|set(PINS)
  if files!=wanted:raise ValueError('control snapshot file set differs')
  digests={n:sha((snapshot/n).read_bytes()) for n in sorted(files)}
  if build.get('pmu_control_snapshot_sha256')!=digests:raise ValueError('control snapshot hashes differ')
  for n in files:
   if (snapshot/n).read_bytes()!=(expected/n).read_bytes():raise ValueError('control reverse composition differs: '+n)
 _models(root,snapshot,hashes)
 deps=build.get('pmu_control_collector_dependencies_sha256')
 if not isinstance(deps,dict) or set(deps)!=set(COLLECTOR_DEPENDENCIES) or any(not isinstance(v,str) or re.fullmatch(r'[0-9a-f]{64}',v) is None for v in deps.values()):raise ValueError('control collector dependency map differs')
 proof=json.loads((root/'pmu-control-collector-model/result.json').read_text(encoding='utf8'))
 if proof.get('passed') is not True or proof.get('hardware_verified') is not False or proof.get('cases')!=['valid-disabled-36-evaluations','missing-and-malformed-fail'] or proof.get('dependencies_sha256')!=deps or proof.get('harness_sha256')!=hashes['test_pmu_control_collector.py']:raise ValueError('control collector proof differs')
 return True

def _models(root,snapshot,hashes):
 from test_pmu_control_native import STUB,MAIN
 from test_pmu_control_final_lifecycle import BASE,EXTRA,MOCK,MAIN as LMAIN
 from test_pm_callbacks_producer import clean
 from test_fsys_pm_native import function
 import test_pmu_control_worker as worker
 model=root/'pmu-control-native-model';m=json.loads((model/'result.json').read_text(encoding='utf8'));helper=snapshot/'arch/arm64/kernel/note10_pmu_control_backend.c'
 cases=['count32-map','no-input-mutation','mmfr-high','fgt-nonzero','wrong-midr','wrong-pmuver','wrong-el','lock-busy','nested-context','pmcr-n','pmcr-width','enable-width','interrupt-width','wrong-backend','unsupported-cpu','null-hw','count0','count33','count1-map','bad-context']
 source='\n'.join(x for x in helper.read_text(encoding='utf8').splitlines() if not x.startswith('#include'));generated=(STUB+'\n'+source+'\n'+MAIN).encode('utf8')
 if m.get('passed') is not True or m.get('hardware_verified') is not False or m.get('input_objects_unchanged_every_call') is not True or m.get('pinned_sha256')!={n:PINS[n] for n in ('arch/arm64/kernel/perf_event.c','arch/arm64/include/asm/perf_event.h','arch/arm64/include/asm/cputype.h')} or m.get('cases')!=cases or m.get('helper_sha256')!=sha(helper.read_bytes()) or m.get('harness_sha256')!=hashes['test_pmu_control_native.py'] or m.get('generated_sha256')!=sha(generated) or (model/'native.c').read_bytes()!=generated or any((model/n).read_bytes() for n in ('compile.log','run.log')):raise ValueError('control backend model differs')
 life=root/'pmu-control-final-lifecycle-model';m=json.loads((life/'result.json').read_text(encoding='utf8'))
 paths={'chain':'kernel/note10_pm_pre_chain.c','capture':'kernel/power/note10_pm_pre_capture.c','branch_chain':'kernel/note10_pm_branch_chain.c','branch_capture':'kernel/power/note10_pm_branch_capture.c','state_chain':'kernel/note10_pmu_state_chain.c','state_capture':'kernel/power/note10_pmu_state_capture.c','bridge':'drivers/perf/note10_pmu_control_bridge.c','control_chain':'kernel/note10_pmu_control_chain.c','control_capture':'kernel/power/note10_pmu_control_capture.c'}
 def raw(n):return re.sub(r'^#include[^\n]*\n','',(snapshot/paths[n]).read_text(encoding='utf-8-sig'),flags=re.M)
 zero='#define barrier_data(ptr) __asm__ __volatile__("": :"r"(ptr) :"memory")'+'\n'+function((snapshot/'lib/string.c').read_text(),'void memzero_explicit(void *s, size_t count)\n{')+'\n'
 generated=(BASE+EXTRA+zero+clean('pm_preconditions_contract.h')+clean('pm_branch_contract.h')+clean('pmu_state_contract.h')+clean('pmu_control_contract.h')+MOCK+raw('bridge')+raw('branch_chain')+raw('branch_capture')+raw('state_chain')+raw('state_capture')+raw('control_chain')+raw('control_capture')+raw('chain')+raw('capture')+LMAIN).encode('utf8')
 logs={n:sha((life/n).read_bytes()) for n in ['compile.log']+[f'case-{i}.log' for i in range(10)]};cases=['success','trylock-failure','post-context-failure','foreign-owner','duplicate-generation','zero-pmu','duplicate-supported','duplicate-unsupported','getter-failure','backend-failure']
 if m.get('passed') is not True or m.get('hardware_verified') is not False or m.get('actual_final_chain_capture_bridge') is not True or m.get('optimized_O2') is not True or m.get('actual_pinned_memzero_body') is not True or m.get('zero_pins')!={n:PINS[n] for n in ('include/linux/string.h','include/linux/compiler.h','include/linux/compiler-gcc.h','include/linux/compiler-clang.h','include/linux/compiler_types.h','lib/string.c')} or m.get('cases')!=cases or m.get('source_sha256')!={k:sha((snapshot/v).read_bytes()) for k,v in paths.items()} or m.get('harness_sha256')!=hashes['test_pmu_control_final_lifecycle.py'] or m.get('generated_sha256')!=sha(generated) or (life/'lifecycle.c').read_bytes()!=generated or m.get('log_sha256')!=logs:raise ValueError('control lifecycle model differs')
 wm=root/'pmu-control-worker-model';m=json.loads((wm/'result.json').read_text(encoding='utf8'));path=snapshot/'arch/arm64/mm/note10_pm_timer_roundtrip.c';raw_worker=path.read_text(encoding='utf8')
 stub=worker.WORKER_STUB.replace('static u32 n10_frame_checksum(const char*p,int n){(void)p;(void)n;return 0;}','static u32 n10_frame_checksum(const char*p,int n){u32 h=2166136261U;while(n--)h=(h^(unsigned char)*p++)*16777619U;return h;}')
 code=stub+worker.ADD+clean('pm_preconditions_contract.h')+clean('pm_branch_contract.h')+clean('pmu_state_contract.h')+clean('pmu_control_contract.h')+worker.MOCK.replace('value[4]=1','value[4]=2')+worker.BRANCH_MOCK.replace('mode==1','mode==10').replace('nonnull=1','nonnull=3')+worker.STATE_MOCK+worker.CONTROL_MOCK+clean('pm_preconditions_probe.c')+clean('pm_branch_probe.c')+clean('pmu_state_probe.c')+clean('pmu_control_probe.c')+function(raw_worker,'static void n10_pm_worker(struct work_struct *unused)\n{')+'\nint main(int argc,char**argv){mode=atoi(argv[1]);n10_pm_worker(NULL);return 0;}\n'
 expected={'enabled.c':'#define CONFIG_NOTE10_PMU_CONTROL_AUDIT 1\n'+code,'disabled.c':code};generated={n:sha(text.encode('utf8')) for n,text in expected.items()}
 logs={n:sha((wm/n).read_bytes()) for n in [f'{mode}-compile.log' for mode in ('enabled','disabled')]+[f'{mode}-{i}.log' for mode in ('enabled','disabled') for i in (0,1,9,10,11,12)]}
 cases=['enabled-success','enabled-outer-error','enabled-gic-error','enabled-branch-error','enabled-state-error','enabled-control-error','disabled-success','disabled-outer-error','disabled-gic-error','disabled-branch-error','disabled-state-error','disabled-control-error']
 if m.get('passed') is not True or m.get('hardware_verified') is not False or m.get('actual_final_worker_and_producers') is not True or m.get('control_feature') is not True or m.get('cases')!=cases or m.get('source_sha256')!=sha(path.read_bytes()) or m.get('harness_sha256')!=hashes['test_pmu_control_worker.py'] or m.get('generated_c_sha256')!=generated or m.get('log_sha256')!=logs or any((wm/n).read_bytes()!=text.encode('utf8') for n,text in expected.items()):raise ValueError('control worker model differs')

def validate(root,build,require_package_flow=True):
 if not validate_core(root,build):return False
 from test_pmu_control_binding import CASES
 proof=json.loads((Path(root)/'pmu-control-binding-model/result.json').read_text(encoding='utf8'))
 if proof.get('passed') is not True or proof.get('cases')!=list(CASES) or proof.get('harness_sha256')!=build['pmu_control_sources_sha256']['test_pmu_control_binding.py']:raise ValueError('control mutation proof differs')
 if require_package_flow:
  proof=json.loads((Path(root)/'pmu-control-package-flow-model/result.json').read_text(encoding='utf8'))
  cases=['synthetic-prototype-to-packages','missing-flag','missing-version','missing-binding-proof']
  if proof.get('passed') is not True or proof.get('hardware_verified') is not False or proof.get('cases')!=cases or proof.get('harness_sha256')!=build['pmu_control_sources_sha256']['test_pmu_control_package_flow.py'] or proof.get('package_sources_sha256')!=build['pmu_control_package_sources_sha256']:raise ValueError('control package proof differs')
 return True
