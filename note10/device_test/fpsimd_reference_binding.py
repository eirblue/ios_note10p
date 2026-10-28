"""Bind v43 reference audit to exact previous composition and final evidence."""
import hashlib,json,re,shutil,tempfile
from pathlib import Path
from prepare_fpsimd_reference_audit import prepare
HERE=Path(__file__).resolve().parent
SOURCES=('prepare_fpsimd_reference_audit.py','fpsimd_reference_contract.h','fpsimd_reference_getter.c','fpsimd_reference_chain.c','fpsimd_reference_capture.c','fpsimd_reference_probe.c','decode_fpsimd_reference.py','test_fpsimd_reference_native.py','test_fpsimd_reference_final_lifecycle.py','test_fpsimd_reference_worker.py','test_fpsimd_reference_decoder.py','test_fpsimd_reference_collector.py','fpsimd_reference_binding.py','test_fpsimd_reference_binding.py','test_fpsimd_reference_package_flow.py','prepare_fpsimd_reference_flow_compat.py')
PACKAGE_SOURCES=('prepare_linux_boot.py','build_boot_test_packages.py','precheck_window_access.py','stage_phase2.py','collect_reservation.py')
COLLECTOR_DEPENDENCIES=('test_pmu_control_collector.py','test_pmu_control_decoder.py','test_pmu_state_decoder.py','test_fpsimd_reference_decoder.py','test_pmu_state_collector.py','test_collect_reservation.py','test_cpu_cache_decode.py','test_cpu_cache_native.py','test_pm_timer_contract.py')
MARKERS=(b'N10FPSM1',b'N10FPSQ1')
def sha(data):return hashlib.sha256(data).hexdigest()
def valid_map(value,names):return isinstance(value,dict) and set(value)==set(names) and all(isinstance(x,str) and re.fullmatch(r'[0-9a-f]{64}',x) for x in value.values())
def validate_core(root,build):
 root=Path(root);config=(root/'handoff.config').read_bytes().splitlines();image=(root/'Image').read_bytes();enabled=b'CONFIG_NOTE10_FPSIMD_REFERENCE_AUDIT=y' in config
 if enabled!=(build.get('fpsimd_reference_audit') is True) or any(enabled!=(x in image) for x in MARKERS):raise ValueError('reference Image/config/metadata mismatch')
 if not enabled:
  keys={k for k in build if k.startswith('fpsimd_reference_')}
  if keys-{'fpsimd_reference_audit','fpsimd_reference_audit_version'} or build.get('fpsimd_reference_audit') not in (None,False) or build.get('fpsimd_reference_audit_version') is not None or any((root/n).exists() for n in ('fpsimd-reference-prepared','fpsimd-reference-native-model','fpsimd-reference-final-lifecycle-model','fpsimd-reference-worker-model','fpsimd-reference-decoder-model','fpsimd-reference-collector-model')):raise ValueError('reference evidence downgrade')
  return False
 if build.get('fpsimd_reference_audit_version')!=1 or not all(x in config for x in (b'CONFIG_NOTE10_PMU_CONTROL_AUDIT=y',b'CONFIG_NOTE10_CPU_PM_PRECONDITIONS=y')):raise ValueError('reference prerequisites differ')
 from pmu_control_binding import validate as validate_prior
 if validate_prior(root,build) is not True:raise ValueError('prior control binding missing')
 hashes={n:sha((HERE/n).read_bytes()) for n in SOURCES}
 if build.get('fpsimd_reference_sources_sha256')!=hashes:raise ValueError('reference source hashes differ')
 if not valid_map(build.get('fpsimd_reference_package_sources_sha256'),PACKAGE_SOURCES) or not valid_map(build.get('fpsimd_reference_collector_dependencies_sha256'),COLLECTOR_DEPENDENCIES):raise ValueError('recorded dependencies differ')
 with tempfile.TemporaryDirectory() as temp:
  expected=Path(temp)/'source';expected.mkdir()
  for field,folder in (('pm_preconditions_prepared_sha256','pm-preconditions-prepared'),('pmu_control_snapshot_sha256','pmu-control-prepared')):
   for name,digest in build[field].items():
    src=root/folder/name;dst=expected/name
    if src.is_symlink() or sha(src.read_bytes())!=digest:raise ValueError('prior snapshot differs: '+name)
    dst.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(src,dst)
  result=prepare(expected,build)
  if any(build.get(k)!=v for k,v in result.items()):raise ValueError('reference composition differs')
  snapshot=root/'fpsimd-reference-prepared';paths=list(snapshot.rglob('*'))
  if snapshot.is_symlink() or any(p.is_symlink() for p in paths):raise ValueError('reference snapshot symlink')
  files={p.relative_to(snapshot).as_posix() for p in paths if p.is_file()};wanted=set(build['pm_preconditions_prepared_sha256'])|set(build['pmu_control_snapshot_sha256'])|set(result['fpsimd_reference_prepared_sha256'])
  if files!=wanted:raise ValueError('reference snapshot file set differs')
  if build.get('fpsimd_reference_snapshot_sha256')!={n:sha((snapshot/n).read_bytes()) for n in sorted(files)}:raise ValueError('reference snapshot hashes differ')
  for name in files:
   if (snapshot/name).read_bytes()!=(expected/name).read_bytes():raise ValueError('reference reverse composition differs: '+name)
 _validate_models(root,snapshot,hashes,build)
 return True

def _validate_models(root,snapshot,hashes,build):
 import test_fpsimd_reference_native as native
 import test_fpsimd_reference_final_lifecycle as life
 import test_fpsimd_reference_worker as worker
 from test_pm_callbacks_producer import clean
 from test_fsys_pm_native import function
 def model(name):return root/('fpsimd-reference-'+name+'-model')
 def load(path):return json.loads((path/'result.json').read_text(encoding='utf8'))
 def strip(p):return re.sub(r'^#include[^\n]*\n','',p.read_text(encoding='utf8'),flags=re.M)
 native_paths={'fpsimd_reference_getter.c':snapshot/'arch/arm64/kernel/note10_fpsimd_reference_getter.c','fpsimd_reference_chain.c':snapshot/'kernel/note10_fpsimd_reference_chain.c'}
 n=model('native');m=load(n);code=native.PRE+''.join('\n'.join(x for x in p.read_text().splitlines() if not x.startswith('#include')) for p in native_paths.values())+native.POST
 cases=['null-reference','current-reference','other-reference','complete-missing','duplicate-collect','prior-mask-mismatch','negative-depth','error-finish-overwrite','duplicate-finish','wrong-context','wrong-notifier','zero-mm-foreign-depth']
 if m.get('passed') is not True or m.get('hardware_verified') is not False or m.get('cases')!=cases or m.get('compiler_options')!=['-std=c11','-O2','-Wall','-Werror'] or m.get('source_sha256')!={k:sha(v.read_bytes()) for k,v in native_paths.items()} or m.get('harness_sha256')!=hashes['test_fpsimd_reference_native.py'] or m.get('generated_sha256')!=sha(code.encode()) or (n/'model.c').read_bytes()!=code.encode() or m.get('log_sha256')!={x:sha((n/x).read_bytes()) for x in ('compile.log','run.log')}:raise ValueError('reference native model differs')
 paths={'chain':'kernel/note10_pm_pre_chain.c','capture':'kernel/power/note10_pm_pre_capture.c','branch_chain':'kernel/note10_pm_branch_chain.c','branch_capture':'kernel/power/note10_pm_branch_capture.c','state_chain':'kernel/note10_pmu_state_chain.c','state_capture':'kernel/power/note10_pmu_state_capture.c','bridge':'drivers/perf/note10_pmu_control_bridge.c','control_chain':'kernel/note10_pmu_control_chain.c','control_capture':'kernel/power/note10_pmu_control_capture.c','fps_getter':'arch/arm64/kernel/note10_fpsimd_reference_getter.c','fps_chain':'kernel/note10_fpsimd_reference_chain.c','fps_capture':'kernel/power/note10_fpsimd_reference_capture.c'}
 zero='#define barrier_data(ptr) __asm__ __volatile__("": :"r"(ptr) :"memory")\n'+function((snapshot/'lib/string.c').read_text(),'void memzero_explicit(void *s, size_t count)\n{')+'\n'
 mock=life.MOCK.replace('GETTER(n10_pre_fpsimd,0)','int n10_pre_fpsimd(struct notifier_block *b,struct n10_precond_row *r){if(b!=&fpsimd_cpu_pm_notifier_block)return 0;r->valid=15;r->value[0]=1;r->value[1]=1;r->value[2]=2;r->value[3]=0;return 1;}')
 order=('bridge','branch_chain','branch_capture','state_chain','state_capture','control_chain','control_capture','fps_getter','fps_chain','fps_capture','chain','capture')
 code=life.BASE+life.EXTRA+life.ADD+zero+''.join(clean(x) for x in ('pm_preconditions_contract.h','pm_branch_contract.h','pmu_state_contract.h','pmu_control_contract.h','fpsimd_reference_contract.h'))+mock+''.join(strip(snapshot/paths[x]) for x in order)+life.MAIN
 n=model('final-lifecycle');m=load(n);cases=['success','trylock','post-context','missing-fpsimd','duplicate-fpsimd','prior-getter-error'];logs=['compile.log']+[x+'.log' for x in cases]
 if m.get('passed') is not True or m.get('hardware_verified') is not False or m.get('cases')!=cases or m.get('source_sha256')!={k:sha((snapshot/v).read_bytes()) for k,v in paths.items()} or m.get('harness_sha256')!=hashes['test_fpsimd_reference_final_lifecycle.py'] or m.get('generated_sha256')!=sha(code.encode()) or (n/'lifecycle.c').read_bytes()!=code.encode() or m.get('log_sha256')!={x:sha((n/x).read_bytes()) for x in logs}:raise ValueError('reference lifecycle model differs')
 wp=snapshot/'arch/arm64/mm/note10_pm_timer_roundtrip.c';producer=snapshot/'arch/arm64/mm/note10_fpsimd_reference_probe.c'
 stub=worker.WORKER_STUB.replace('static u32 n10_frame_checksum(const char*p,int n){(void)p;(void)n;return 0;}','static u32 n10_frame_checksum(const char*p,int n){u32 h=2166136261U;while(n--)h=(h^(unsigned char)*p++)*16777619U;return h;}')
 code=stub+worker.ADD+'#define CONFIG_NOTE10_PMU_CONTROL_AUDIT 1\n'+''.join(clean(x) for x in ('pm_preconditions_contract.h','pm_branch_contract.h','pmu_state_contract.h','pmu_control_contract.h','fpsimd_reference_contract.h'))+worker.MOCK.replace('value[4]=1','value[4]=2')+worker.BRANCH_MOCK.replace('mode==1','mode==10').replace('nonnull=1','nonnull=3')+worker.STATE_MOCK+worker.CONTROL_MOCK+worker.FPS_MOCK+''.join(clean(x) for x in ('pm_preconditions_probe.c','pm_branch_probe.c','pmu_state_probe.c','pmu_control_probe.c'))+strip(producer)+function(wp.read_text(),'static void n10_pm_worker(struct work_struct *unused)\n{')+'''\nint main(int argc,char**argv){mode=atoi(argv[1]);
#ifdef CONFIG_NOTE10_FPSIMD_REFERENCE_AUDIT
 if(mode==14 || mode==15){unsigned int budget=mode==14?0:4090;return n10_fps_emit("N10FPSM1","",mode==14?512:10,&budget,0)?0:1;}
#endif
 n10_pm_worker(NULL);return 0;}\n'''
 expected={'enabled.c':'#define CONFIG_NOTE10_FPSIMD_REFERENCE_AUDIT 1\n'+code,'disabled.c':code};n=model('worker');m=load(n);cases=[label+'-'+str(i) for label in ('enabled','disabled') for i in ((0,1,9,10,11,12,13,14,15) if label=='enabled' else (0,1,9,10,11,12,13))];logs=[label+'-compile.log' for label in ('enabled','disabled')]+[f'{label}-{i}.log' for label in ('enabled','disabled') for i in ((0,1,9,10,11,12,13,14,15) if label=='enabled' else (0,1,9,10,11,12,13))]
 if m.get('passed') is not True or m.get('hardware_verified') is not False or m.get('cases')!=cases or m.get('source_sha256')!={'worker':sha(wp.read_bytes()),'producer':sha(producer.read_bytes())} or m.get('harness_sha256')!=hashes['test_fpsimd_reference_worker.py'] or m.get('generated_sha256')!={k:sha(v.encode()) for k,v in expected.items()} or any((n/k).read_bytes()!=v.encode() for k,v in expected.items()) or m.get('log_sha256')!={x:sha((n/x).read_bytes()) for x in logs}:raise ValueError('reference worker model differs')
 n=model('decoder');m=load(n);cases=['null','current','other','prior-mask','prior-equality','prior-generation','depth-width','prefix','checksum','missing-copy','duplicate','noncanonical','row-generation','index','count','kind','mm','foreign','depth','reference','identity','extra-prefix','copy-mismatch','schema-missing']
 if m.get('passed') is not True or m.get('hardware_verified') is not False or m.get('cases')!=cases or m.get('harness_sha256')!=hashes['test_fpsimd_reference_decoder.py'] or m.get('decoder_sha256')!=hashes['decode_fpsimd_reference.py']:raise ValueError('reference decoder model differs')
 n=model('collector');m=load(n)
 if m.get('passed') is not True or m.get('hardware_verified') is not False or m.get('cases')!=['valid-reference-37-evaluations','missing-and-malformed-fail','unexpected-disabled-fail'] or m.get('dependencies_sha256')!=build['fpsimd_reference_collector_dependencies_sha256'] or m.get('harness_sha256')!=hashes['test_fpsimd_reference_collector.py']:raise ValueError('reference collector model differs')

def validate(root,build,require_package_flow=True):
 if not validate_core(root,build):return False
 from test_fpsimd_reference_binding import CASES
 proof=json.loads((Path(root)/'fpsimd-reference-binding-model/result.json').read_text(encoding='utf8'))
 if proof.get('passed') is not True or proof.get('cases')!=list(CASES) or proof.get('harness_sha256')!=build['fpsimd_reference_sources_sha256']['test_fpsimd_reference_binding.py']:raise ValueError('reference mutation proof differs')
 if require_package_flow:
  proof=json.loads((Path(root)/'fpsimd-reference-package-flow-model/result.json').read_text(encoding='utf8'))
  cases=['synthetic-prototype-to-packages','missing-flag','missing-version','missing-binding-proof']
  if proof.get('passed') is not True or proof.get('hardware_verified') is not False or proof.get('cases')!=cases or proof.get('harness_sha256')!=build['fpsimd_reference_sources_sha256']['test_fpsimd_reference_package_flow.py'] or proof.get('package_sources_sha256')!=build['fpsimd_reference_package_sources_sha256']:raise ValueError('reference package proof differs')
 return True
