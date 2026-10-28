"""Check v45 package flags and preserved v39-v44 package-flow history."""
import argparse,hashlib,json,shutil,struct,subprocess,sys,tempfile
from pathlib import Path
from contextlib import ExitStack
from unittest.mock import patch
import prepare_linux_boot as prep
import build_boot_test_packages as packages
from stage_phase2 import verify_packages
from ehld_lock_binding import MARKERS as EHLD_MARKERS,PACKAGE_SOURCES
from test_pm_callbacks_producer import clean
from pm_callbacks_binding import MARKERS as CALLBACKS
from pm_preconditions_binding import MARKERS as PRECONDITIONS
from pm_branch_binding import MARKERS as BRANCH
from pmu_failure_binding import MARKER as PMU_FAILURE
from gic_priority_binding import MARKER as GIC_PRIORITY
from pmu_state_binding import MARKERS as PMU_STATE
from pmu_control_binding import MARKERS as PMU_CONTROL
from fpsimd_reference_binding import MARKERS as FPSIMD
from rcu_context_binding import MARKERS as RCU,validate as validate_rcu
from ehld_lock_binding import validate as validate_ehld

HISTORY_FILES=('prepare_rcu_context_flow_compat.py','prepare_fpsimd_reference_flow_compat.py','prepare_pmu_control_flow_compat.py','prepare_pmu_state_flow_compat.py','prepare_pmu_failure_flow_compat.py','test_rcu_context_package_flow.py','test_fpsimd_reference_package_flow.py','test_pmu_control_package_flow.py','test_pmu_state_package_flow.py','test_gic_priority_package_flow.py','test_pmu_failure_package_flow.py')
CASES=['synthetic-prototype-to-packages','missing-flag','missing-version','missing-binding-proof']
def sha(raw):return hashlib.sha256(raw).hexdigest()

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--artifact',required=True,type=Path);ap.add_argument('--output',required=True,type=Path);a=ap.parse_args()
 src,out=a.artifact,a.output;build_at_start=json.loads((src/'build-result.json').read_text(encoding='utf8'));source_dir=Path(__file__).resolve().parent
 measured={name:sha((source_dir/name).read_bytes()) for name in PACKAGE_SOURCES}
 if build_at_start.get('ehld_lock_package_sources_sha256')!=measured:raise ValueError('package source map differs')
 out.mkdir(parents=True,exist_ok=False)
 with tempfile.TemporaryDirectory(dir=prep.ROOT/'note10/private') as temp:
  root=Path(temp);art=root/'artifact';shutil.copytree(src,art)
  build=json.loads((art/'build-result.json').read_text(encoding='utf8'));build['build_passed']=True
  image=bytearray(4096);image[56:60]=b'ARM\x64';image[128:]=b''.join(CALLBACKS+PRECONDITIONS+BRANCH)+PMU_FAILURE+GIC_PRIORITY+b''.join(PMU_STATE+PMU_CONTROL+FPSIMD+RCU+EHLD_MARKERS)+b'N10RET1'
  (art/'Image').write_bytes(image);build['image_sha256']=sha(image);build['image_size']=len(image)
  (art/'build-result.json').write_text(json.dumps(build),encoding='utf8')
  parts={'boot':bytearray(131072),'recovery':b'R'*128+b'X'*128,'dtb':b'D','dtbo':b'O','vbmeta':bytearray(256)}
  parts['boot'][32:48]=b'SEANDROIDENFORCE';parts['vbmeta'][:4]=b'AVB0';struct.pack_into('>I',parts['vbmeta'],120,2)
  parts={k:bytes(v) for k,v in parts.items()}
  backup=root/'backup';backup.mkdir();records=[]
  for index,(name,data) in enumerate(parts.items()):
   (backup/(name+'.img')).write_bytes(data);records.append({'partition':name,'file':name+'.img','block_node':'/dev/block/sda'+str(index+14),'size':len(data),'sha256':sha(data),'remote_hash_before_and_after_match':True})
  (backup/'backup-manifest.json').write_text(json.dumps({'complete':True,'partition_writes':False,'bootloader':'N976NTEST','partitions':records}),encoding='utf8')
  twrp=root/'twrp.img';twrp.write_bytes(parts['recovery'][:128]);mk=root/'mkbootimg.py';mk.write_bytes(b'mk');header={'header_version':1,'page_size':2048,'recovery_dtbo_size':0,'second_size':0,'kernel_addr':0,'tags_addr':0,'arm64_text_offset':0,'ramdisk_addr':0,'ramdisk_file_offset':2048,'ramdisk_size':0,'second_file_offset':32,'cmdline':'fixture','name':'fixture','os_version':'1.0.0','security_patch_month':'2026-01','kernel_sha256':build['image_sha256']}
  false_build=dict(build);false_build['build_passed']=False;(art/'build-result.json').write_text(json.dumps(false_build),encoding='utf8')
  with patch.object(prep,'MKBOOTIMG_SHA256',sha(mk.read_bytes())),patch.object(prep,'TWRP_SHA256',sha(twrp.read_bytes())),patch.object(prep,'read_verified_backup',return_value=parts):
   try:prep.prepare(backup,art,twrp,mk,root/'false-rejected.img',auto_cycle_token='c'*32)
   except ValueError as error:
    if 'Successful CPU-diagnostic Linux build required' not in str(error):raise
   else:raise AssertionError('synthetic build_passed=False report was accepted')
  (art/'build-result.json').write_text(json.dumps(build),encoding='utf8')
  def fake_mk(cmd,**kwargs):
   path=Path(cmd[cmd.index('--output')+1]);size=prep.payload_size(len(image),0,2048,len(parts['boot']),allow_empty_ramdisk=True);path.write_bytes(b'P'*2048+image+bytes(size-2048-len(image)))
  validators=('pm_quiesce_binding.assert_scope','gic_roundtrip_binding.validate_model','dma_pm_binding.validate_model','ufs_pm_binding.validate_model','iommu_pm_binding.validate_model','abox_pm_binding.validate_model','abox_pmu_binding.validate_model','pm_noirq_binding.validate_model','pmu_settle_binding.validate_model','pm_cpus_binding.validate_model','pm_post_arch_binding.validate_model','pm_edge_binding.validate_model','pm_callbacks_binding.validate_model','pm_preconditions_binding.validate_model','pm_branch_binding.validate_model','pmu_failure_binding.validate','gic_priority_binding.validate','pmu_state_binding.validate','pmu_control_binding.validate','fpsimd_reference_binding.validate','pm_irq_binding.validate_model','materialize_auto_cycle.validate','prepare_reservation_kernel.verify_embedded_init')
  proof=art/'ehld-lock-binding-model/result.json';saved=proof.read_bytes()
  with ExitStack() as stack:
   for name in validators:stack.enter_context(patch(name,return_value=True))
   stack.enter_context(patch('rcu_context_binding.validate',side_effect=lambda r,b,require_package_flow=True:validate_rcu(r,b,require_package_flow=False)))
   stack.enter_context(patch('ehld_lock_binding.validate',side_effect=lambda r,b:validate_ehld(r,b,require_package_flow=False)))
   for obj,key,data in ((prep,'MKBOOTIMG_SHA256',mk.read_bytes()),(prep,'TWRP_SHA256',twrp.read_bytes())):stack.enter_context(patch.object(obj,key,sha(data)))
   stack.enter_context(patch.object(prep,'read_verified_backup',return_value=parts));stack.enter_context(patch.object(packages,'read_verified_backup',return_value=parts))
   stack.enter_context(patch.object(prep,'boot_header',return_value=header));stack.enter_context(patch.object(prep.subprocess,'run',side_effect=fake_mk))
   for case in CASES:
    current=json.loads((art/'build-result.json').read_text(encoding='utf8'))
    current['build_passed']=True
    (art/'build-result.json').write_text(json.dumps(current),encoding='utf8')
    if case=='missing-flag':current.pop('ehld_lock_audit',None)
    elif case=='missing-version':current.pop('ehld_lock_audit_version',None)
    elif case=='missing-binding-proof':proof.unlink()
    if case!='synthetic-prototype-to-packages':(art/'build-result.json').write_text(json.dumps(current),encoding='utf8')
    try:
     try:
      prototype=root/(case+'.img');report=prep.prepare(backup,art,twrp,mk,prototype,auto_cycle_token='c'*32)
     except (ValueError,KeyError,FileNotFoundError):
      if case=='synthetic-prototype-to-packages':raise
     else:
      if case!='synthetic-prototype-to-packages':raise AssertionError('production prep accepted '+case)
      built=packages.build(backup,prototype,root/'packages');records_out=verify_packages(root/'packages');diag=next(x for x in records_out if x['mode']=='diagnostic');rollback=next(x for x in records_out if x['mode']=='rollback')
      if report.get('ehld_lock_audit') is not True or built.get('ehld_lock_audit') is not True or diag.get('ehld_lock_audit') is not True or diag.get('ehld_lock_audit_version')!=1 or rollback.get('ehld_lock_audit') is not False or rollback.get('ehld_lock_audit_version') is not None:raise AssertionError('EHLD diagnostic/rollback metadata differs')
    finally:
     if not proof.exists():proof.write_bytes(saved)
     (art/'build-result.json').write_text(json.dumps(build),encoding='utf8')
  if json.loads((src/'build-result.json').read_text(encoding='utf8'))!=build_at_start:raise AssertionError('input build report changed')
 history=out/'history';history.mkdir()
 from prepare_ehld_lock_flow_compat import prepare as make_v44
 from prepare_rcu_context_flow_compat import prepare as make_v43
 from prepare_fpsimd_reference_flow_compat import prepare as make_v42
 from prepare_pmu_control_flow_compat import prepare as make_v41
 from prepare_pmu_state_flow_compat import prepare as make_v40
 from prepare_pmu_failure_flow_compat import prepare as make_v39
 versions=[('v44',make_v44,src,'test_rcu_context_package_flow.py'),('v43',make_v43,None,'test_fpsimd_reference_package_flow.py'),('v42',make_v42,None,'test_pmu_control_package_flow.py'),('v41',make_v41,None,'test_pmu_state_package_flow.py'),('v40',make_v40,None,'test_gic_priority_package_flow.py'),('v39',make_v39,None,'test_pmu_failure_package_flow.py')]
 with tempfile.TemporaryDirectory(dir=out) as temp:
  temp=Path(temp);previous=None
  for version,prepare_flow,source,script in versions:
   source=source or previous;fixture=temp/(version+'-fixture');prepare_flow(source,fixture);previous=fixture
   proof=temp/(version+'-flow');subprocess.run([sys.executable,'-X','utf8',str(source_dir/script),'--artifact',str(fixture),'--output',str(proof)],check=True,capture_output=True,timeout=300)
   dest=history/(version+'-package-flow');dest.mkdir();shutil.copyfile(proof/'result.json',dest/'result.json')
 history_hashes={name:sha((source_dir/name).read_bytes()) for name in HISTORY_FILES}
 result={'passed':True,'hardware_verified':False,'cases':CASES,'harness_sha256':sha(Path(__file__).read_bytes()),'package_sources_sha256':measured,'history_versions':['v44','v43','v42','v41','v40','v39'],'history_files_sha256':history_hashes}
 (out/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8',newline='\n')
if __name__=='__main__':main()
