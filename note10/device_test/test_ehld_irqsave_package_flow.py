"""Exercise production prototype, package and verification flow for v46 scope flags."""
import argparse,hashlib,json,shutil,struct,sys,tempfile
from pathlib import Path
from contextlib import ExitStack
from unittest.mock import patch
import prepare_linux_boot as prep
import build_boot_test_packages as packages
import precheck_window_access as precheck
from collect_reservation import collect as collect_reservation
from stage_phase2 import verify_packages
from ehld_irqsave_binding import PACKAGE_SOURCES,validate as validate_irqsave
from ehld_lock_binding import MARKERS as LOCK_MARKERS,validate as validate_lock
from rcu_context_binding import MARKERS as RCU_MARKERS,validate as validate_rcu
from test_pm_callbacks_producer import clean
from pm_callbacks_binding import MARKERS as CALLBACKS
from pm_preconditions_binding import MARKERS as PRECONDITIONS
from pm_branch_binding import MARKERS as BRANCH
from pmu_failure_binding import MARKER as PMU_FAILURE
from gic_priority_binding import MARKER as GIC_PRIORITY
from pmu_state_binding import MARKERS as PMU_STATE
from pmu_control_binding import MARKERS as PMU_CONTROL
from fpsimd_reference_binding import MARKERS as FPSIMD

CASES=('actual-production-flow','missing-flag','missing-version','missing-binding-proof','build-false')
COLLECTOR_CASES=('collector-option-on-preserves-39','collector-option-off-preserves-39','collector-pair-scope-mismatch-rejected')
PRECHECK_CASES=('precheck-on-scope-ready','precheck-off-old-ehld-ready','precheck-pair-scope-mismatch-rejected')
def sha(raw):return hashlib.sha256(raw).hexdigest()
def make_fixture(root,artifact,mode):
 from prepare_ehld_irqsave_flow_compat import KEEP_FILES,MODEL_PREFIXES
 artifact=Path(artifact);art=root/'artifact'
 if artifact.is_symlink() or not artifact.is_dir() or art.exists() or art.is_symlink():raise ValueError('unsafe package-flow fixture paths')
 art.mkdir(parents=True)
 for item in artifact.iterdir():
  if item.is_symlink():raise ValueError('symlink in package-flow input')
  keep_dir=item.is_dir() and item.name.startswith(MODEL_PREFIXES)
  keep_file=item.is_file() and (item.name in KEEP_FILES or (item.suffix=='.log' and item.stat().st_size<=1024*1024) or item.name in ('window-core-model.json','window-gate-model.json','window-init-model.json'))
  if not (keep_dir or keep_file):continue
  destination=art/item.name
  if keep_dir:
   if any(path.is_symlink() for path in item.rglob('*')):raise ValueError('nested symlink in package-flow model input')
   shutil.copytree(item,destination)
  elif item.name not in ('Image','initramfs.cpio'):
   shutil.copy2(item,destination)
 # Compact model inputs retain the markers and measured hashes used by the production gates.
 build=json.loads((art/'build-result.json').read_text(encoding='utf8'))
 identity=build.get('reservation_evidence_id','e'*32)
 if not isinstance(identity,str) or len(identity)!=32:raise ValueError('invalid fixture reservation identity')
 build['reservation_evidence_id']=identity
 build.setdefault('reservation_evidence_version',2)
 image=bytearray(4096);image[56:60]=b'ARM\x64';markers=b''.join(CALLBACKS+PRECONDITIONS+BRANCH)+PMU_FAILURE+GIC_PRIORITY+b''.join(PMU_STATE+PMU_CONTROL+FPSIMD+RCU_MARKERS+LOCK_MARKERS)+b'N10RET1N10MEM1N10XNU1N10QUI1N10CPU2N10PMS1N10PMT1N10TMR1N10BND1N10TRY1'+identity.encode();image[128:128+len(markers)]=markers;(art/'Image').write_bytes(image)
 initramfs=b'v46-offline-initramfs-fixture';(art/'initramfs.cpio').write_bytes(initramfs)
 build['image_sha256']=sha(image);build['image_size']=len(image);build['initramfs_cpio_sha256']=sha(initramfs)
 build['effective_config_sha256']=sha((art/'handoff.config').read_bytes())
 if mode=='build-false':build['build_passed']=False
 else:build['build_passed']=True
 if mode=='missing-flag':build.pop('ehld_irqsave_audit',None)
 if mode=='missing-version':build.pop('ehld_irqsave_audit_version',None)
 if mode=='missing-binding-proof':build.pop('ehld_irqsave_model_sha256',None)
 (art/'build-result.json').write_text(json.dumps(build),encoding='utf8')
 parts={'boot':bytearray(131072),'recovery':b'R'*256,'dtb':b'D','dtbo':b'O','vbmeta':bytearray(256)}
 parts['boot'][32:48]=b'SEANDROIDENFORCE';parts['vbmeta'][:4]=b'AVB0';struct.pack_into('>I',parts['vbmeta'],120,2);parts={k:bytes(v) for k,v in parts.items()}
 backup=root/'backup';backup.mkdir();records=[]
 for i,(name,data) in enumerate(parts.items()):
  (backup/(name+'.img')).write_bytes(data);records.append({'partition':name,'file':name+'.img','block_node':'/dev/block/sda'+str(i+14),'size':len(data),'sha256':sha(data),'remote_hash_before_and_after_match':True})
 (backup/'backup-manifest.json').write_text(json.dumps({'complete':True,'partition_writes':False,'bootloader':'N976NTEST','partitions':records}),encoding='utf8')
 twrp=root/'twrp.img';twrp.write_bytes(parts['recovery']);mk=root/'mkbootimg.py';mk.write_bytes(b'mkboot-fixture')
 return art,backup,twrp,mk,parts

def run_collector_scope(active,pair_change=None):
 import test_ehld_lock_collector as legacy
 from ehld_irqsave_binding import package_scope
 original=Path.read_text
 def scoped_read(path,*args,**kwargs):
  raw=original(path,*args,**kwargs)
  if path.name not in ('build-result.json','package-result.json'):return raw
  value=json.loads(raw)
  value.update(ehld_irqsave_audit=active,ehld_irqsave_audit_version=1 if active else None)
  if path.name=='package-result.json' and pair_change:value.update(pair_change)
  return json.dumps(value)
 with patch.object(Path,'read_text',scoped_read),patch('ehld_irqsave_binding.validate',side_effect=lambda root,build,require_package_flow=True:package_scope(build)):
  return legacy.EHLDCollectorTests().run_case(active=True)

class FakeAdb:
 def __init__(self,backup,package_dir):
  self.executable='fake-adb';self.serial='fixture';self.backup=backup;self.package_dir=package_dir
  manifest=json.loads((backup/'backup-manifest.json').read_text());self.partitions={x['block_node']:x['sha256'] for x in manifest['partitions']}
  self.packages={}
  for record in verify_packages(package_dir):self.packages[record['file']]=record['sha256']
 def text(self,*args):
  if args==('shell','getprop','ro.bootloader'):return 'N976NTEST'
  if args==('shell','cat','/sys/class/power_supply/battery/capacity'):return '70'
  if len(args)==3 and args[:2]==('shell','sha256sum'):
   path=args[2]
   if path in self.partitions:return self.partitions[path]+'  '+path
   name=Path(path).name
   if name in self.packages:return self.packages[name]+'  '+path
  raise AssertionError(args)

def run_precheck_flow(kernel_build,backup,package_dir,header):
 from types import SimpleNamespace
 for name in ('auto-return-model','cpu-cache-model','pm-timer-model'):
  destination=kernel_build/name
  if not destination.exists():raise ValueError('precheck fixture missing required model: '+name)
 patch_model=kernel_build/'pm-source-model.json'
 if not patch_model.is_file():raise ValueError('precheck fixture missing PM source model')
 core=json.loads((kernel_build/'build-result.json').read_text());sources=core['window_access_sources_sha256']
 core_path=kernel_build/'window-core-model.json';core_path.write_text(json.dumps({'passed':True,'cases':[1],'core_sha256':sources['note10_window_access_core.h']}),encoding='utf8',newline='\n')
 gate_path=kernel_build/'window-gate-model.json';gate_path.write_text(json.dumps({'passed':True,'cases':[1],'core_sha256':sources['note10_window_access_core.h'],'wrapper_sha256':sources['note10_xnu_window_access.c']}),encoding='utf8',newline='\n')
 init_path=kernel_build/'window-init-model.json';init_path.write_text(json.dumps({'passed':True,'cases':[1],'elf_sha256':sha((kernel_build/'minimal-init.elf').read_bytes())}),encoding='utf8',newline='\n')
 adb=FakeAdb(backup,package_dir)
 with ExitStack() as stack:
  stack.enter_context(patch.object(precheck,'preflight',return_value={'twrp_version':'fixture'}))
  stack.enter_context(patch.object(precheck,'pm_suspend_patch_bound',return_value=True))
  stack.enter_context(patch.object(precheck,'verify_embedded_init',return_value={'passed':True}))
  for module in ('pm_quiesce_binding','gic_roundtrip_binding','dma_pm_binding','ufs_pm_binding','iommu_pm_binding','abox_pm_binding','abox_pmu_binding','pm_noirq_binding','pmu_settle_binding','pm_cpus_binding','pm_post_arch_binding','pm_edge_binding','pm_callbacks_binding','pm_preconditions_binding','pm_branch_binding','pm_irq_binding'):
   imported=__import__(module)
   if hasattr(imported,'assert_scope'):stack.enter_context(patch(module+'.assert_scope',return_value=True))
   if hasattr(imported,'validate_model'):stack.enter_context(patch(module+'.validate_model',return_value=True))
  stack.enter_context(patch('inspect_firmware.boot_header',return_value=header))
  stack.enter_context(patch.object(precheck.subprocess,'run',return_value=SimpleNamespace(returncode=0,stdout=b'',stderr=b'')))
  result=precheck.check(package_dir,kernel_build,backup,core_path,gate_path,init_path,adb)
 if result.get('ready_for_manual_access_test') is not True or result.get('partition_writes') is not False:raise AssertionError('production precheck did not return a read-only ready result')
 return result

def main():
 p=argparse.ArgumentParser();p.add_argument('--artifact',required=True,type=Path);p.add_argument('--output',required=True,type=Path);a=p.parse_args();source_dir=Path(__file__).resolve().parent
 measured={n:sha((source_dir/n).read_bytes()) for n in PACKAGE_SOURCES}
 initial=json.loads((a.artifact/'build-result.json').read_text(encoding='utf8'))
 if initial.get('ehld_irqsave_package_sources_sha256')!=measured:raise ValueError('package source map differs')
 a.output.mkdir(parents=True,exist_ok=False)
 with tempfile.TemporaryDirectory(dir=prep.ROOT/'note10/private') as td:
  root=Path(td);art,backup,twrp,mk,parts=make_fixture(root,a.artifact,'actual-production-flow')
  build=json.loads((art/'build-result.json').read_text(encoding='utf8'));build['reservation_evidence_id']='c'*32;build['reservation_evidence_version']=2
  image=bytearray(4096);image[56:60]=b'ARM\x64';markers=b''.join(CALLBACKS+PRECONDITIONS+BRANCH)+PMU_FAILURE+GIC_PRIORITY+b''.join(PMU_STATE+PMU_CONTROL+FPSIMD+RCU_MARKERS+LOCK_MARKERS)+b'N10RET1N10MEM1N10XNU1N10QUI1N10CPU2N10PMS1N10PMT1N10TMR1N10BND1N10TRY1'+build['reservation_evidence_id'].encode();image[128:128+len(markers)]=markers;(art/'Image').write_bytes(image)
  build['image_sha256']=sha(image);build['image_size']=len(image);(art/'build-result.json').write_text(json.dumps(build),encoding='utf8')
  header={'header_version':1,'page_size':2048,'recovery_dtbo_size':0,'second_size':0,'kernel_addr':0,'tags_addr':0,'arm64_text_offset':0,'ramdisk_addr':0,'ramdisk_file_offset':2048,'ramdisk_size':0,'second_file_offset':32,'cmdline':'fixture','name':'fixture','os_version':'1.0.0','security_patch_month':'2026-01','kernel_sha256':build['image_sha256']}
  def fake_mk(cmd,**kwargs):
   out=Path(cmd[cmd.index('--output')+1]);size=prep.payload_size(len(image),0,2048,len(parts['boot']),allow_empty_ramdisk=True);out.write_bytes(b'P'*2048+image+bytes(size-2048-len(image)))
  validators=('pm_quiesce_binding.assert_scope','gic_roundtrip_binding.validate_model','dma_pm_binding.validate_model','ufs_pm_binding.validate_model','iommu_pm_binding.validate_model','abox_pm_binding.validate_model','abox_pmu_binding.validate_model','pm_noirq_binding.validate_model','pmu_settle_binding.validate_model','pm_cpus_binding.validate_model','pm_post_arch_binding.validate_model','pm_edge_binding.validate_model','pm_callbacks_binding.validate_model','pm_preconditions_binding.validate_model','pm_branch_binding.validate_model','pmu_failure_binding.validate','gic_priority_binding.validate','pmu_state_binding.validate','pmu_control_binding.validate','fpsimd_reference_binding.validate','pm_irq_binding.validate_model','materialize_auto_cycle.validate','prepare_reservation_kernel.verify_embedded_init')
  with ExitStack() as stack:
   for name in validators:stack.enter_context(patch(name,return_value=True))
   stack.enter_context(patch('rcu_context_binding.validate',return_value=True))
   stack.enter_context(patch('ehld_lock_binding.validate',return_value=True))
   stack.enter_context(patch('ehld_irqsave_binding.validate',side_effect=lambda r,b,require_package_flow=True:validate_irqsave(r,b,require_package_flow=False)))
   stack.enter_context(patch.object(prep,'MKBOOTIMG_SHA256',sha(mk.read_bytes())));stack.enter_context(patch.object(prep,'TWRP_SHA256',sha(twrp.read_bytes())))
   stack.enter_context(patch.object(prep,'read_verified_backup',return_value=parts));stack.enter_context(patch.object(packages,'read_verified_backup',return_value=parts));stack.enter_context(patch.object(prep,'boot_header',return_value=header));stack.enter_context(patch.object(prep.subprocess,'run',side_effect=fake_mk))
   results=[]
   for mode in CASES:
    # Use an independent artifact copy for each negative case.
    if mode!='actual-production-flow':
     case_root=root/mode;case_root.mkdir();case_art,case_backup,case_twrp,case_mk,case_parts=make_fixture(case_root,a.artifact,mode)
    else:case_art,case_backup,case_twrp,case_mk,case_parts=art,backup,twrp,mk,parts
    try:
     report=prep.prepare(case_backup,case_art,case_twrp,case_mk,root/(mode+'.img'),auto_cycle_token='c'*32)
     if mode!='actual-production-flow':raise AssertionError('production prepare accepted '+mode)
     packages_out=root/'packages';built=packages.build(case_backup,root/(mode+'.img'),packages_out);records=verify_packages(packages_out);diag=next(x for x in records if x['mode']=='diagnostic');rollback=next(x for x in records if x['mode']=='rollback')
     if mode=='actual-production-flow':
      (packages_out/'ram-stage-fixture.json').write_text(json.dumps({'ram_directory':'/tmp/note10-reserve-deadbeef'}),encoding='utf8',newline='\n')
      precheck_result=run_precheck_flow(case_art,case_backup,packages_out,header)
      if precheck_result['ready_for_manual_access_test'] is not True:raise AssertionError('precheck did not pass')
     if report.get('ehld_irqsave_audit') is not True or built.get('ehld_irqsave_audit') is not True or diag.get('ehld_irqsave_audit') is not True or diag.get('ehld_irqsave_audit_version')!=1 or rollback.get('ehld_irqsave_audit') is not False or rollback.get('ehld_irqsave_audit_version') is not None:raise AssertionError('production package flags differ')
     results.append({'case':mode,'accepted':True,'diagnostic':True,'rollback':False})
    except (ValueError,KeyError,FileNotFoundError):
     if mode=='actual-production-flow':raise
     results.append({'case':mode,'accepted':False})
   # Exercise an explicit new-option-off model while retaining the prior EHLD scope.
   from prepare_ehld_irqsave_flow_compat import prepare as prepare_irqsave_off
   off_art=root/'irqsave-off-artifact';prepare_irqsave_off(art,off_art)
   off_build=json.loads((off_art/'build-result.json').read_text(encoding='utf8'));off_build['build_passed']=True;off_build['reservation_evidence_id']='d'*32;off_build['reservation_evidence_version']=2
   off_image=bytearray(4096);off_image[56:60]=b'ARM\x64';off_markers=b''.join(CALLBACKS+PRECONDITIONS+BRANCH)+PMU_FAILURE+GIC_PRIORITY+b''.join(PMU_STATE+PMU_CONTROL+FPSIMD+RCU_MARKERS+LOCK_MARKERS)+b'N10RET1N10MEM1N10XNU1N10QUI1N10CPU2N10PMS1N10PMT1N10TMR1N10BND1N10TRY1'+off_build['reservation_evidence_id'].encode();off_image[128:128+len(off_markers)]=off_markers;(off_art/'Image').write_bytes(off_image);off_build['image_sha256']=sha(off_image);off_build['image_size']=len(off_image);(off_art/'build-result.json').write_text(json.dumps(off_build),encoding='utf8',newline='\n');image=off_image
   header['kernel_sha256']=off_build['image_sha256'];off_header=header
   off_img=root/'irqsave-off.img';off_report=prep.prepare(backup,off_art,twrp,mk,off_img,auto_cycle_token='d'*32);off_packages=root/'irqsave-off-packages';off_built=packages.build(backup,off_img,off_packages);verify_packages(off_packages)
   if off_report.get('ehld_irqsave_audit') is not False or off_built.get('ehld_irqsave_audit') is not False or off_report.get('ehld_lock_audit') is not True:raise AssertionError('new-option-off did not preserve old EHLD scope')
   (off_packages/'ram-stage-fixture.json').write_text(json.dumps({'ram_directory':'/tmp/note10-reserve-deadbeef'}),encoding='utf8',newline='\n')
   off_precheck=run_precheck_flow(off_art,backup,off_packages,off_header)
   if off_precheck.get('ready_for_manual_access_test') is not True or off_precheck.get('ehld_irqsave_audit_scope_verified') is not False:raise AssertionError('new-option-off precheck scope differs')
   bad_packages=root/'irqsave-pair-mismatch';shutil.copytree(off_packages,bad_packages);pair_path=bad_packages/'package-result.json';pair=json.loads(pair_path.read_text(encoding='utf8'));pair['ehld_irqsave_audit']=True;pair['ehld_irqsave_audit_version']=1;pair_path.write_text(json.dumps(pair),encoding='utf8',newline='\n')
   try:run_precheck_flow(off_art,backup,bad_packages,off_header)
   except (ValueError,KeyError):pass
   else:raise AssertionError('precheck accepted mismatched package scope')
   precheck_cases=[{'case':PRECHECK_CASES[0],'accepted':True,'scope':True,'ready':True,'partition_writes':False},{'case':PRECHECK_CASES[1],'accepted':True,'scope':False,'ready':True,'partition_writes':False},{'case':PRECHECK_CASES[2],'accepted':False}]
 result={'passed':True,'hardware_verified':False,'cases':results,'harness_sha256':sha(Path(__file__).read_bytes()),'package_sources_sha256':measured}
 collector_results=[]
 try:
  on=run_collector_scope(True)
  if len(on['evaluation_items'])!=39 or on['evaluation_items'].get('cpu0_ehld_lock_audit')!={'required':True,'status':'passed'} or on.get('ehld_irqsave_audit_scope_verified') is not True:raise AssertionError('collector option-on 39-row contract differs')
  collector_results.append({'case':COLLECTOR_CASES[0],'accepted':True,'evaluation_items':len(on['evaluation_items']),'irqsave_scope':True})
  off=run_collector_scope(False)
  if len(off['evaluation_items'])!=39 or off['evaluation_items']!=on['evaluation_items'] or 'cpu0_ehld_irqsave_audit' in off['evaluation_items'] or off.get('ehld_irqsave_audit_scope_verified') is not False:raise AssertionError('collector option-off row contract differs')
  collector_results.append({'case':COLLECTOR_CASES[1],'accepted':True,'evaluation_items':len(off['evaluation_items']),'irqsave_scope':False})
  try:run_collector_scope(True,{'ehld_irqsave_audit':False})
  except ValueError:pass
  else:raise AssertionError('collector accepted mismatched irqsave package scope')
  collector_results.append({'case':COLLECTOR_CASES[2],'accepted':False})
 except Exception:
  raise
 result['collector_cases']=collector_results
 result['precheck_cases']=precheck_cases
 (a.output/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8',newline='\n')
if __name__=='__main__':main()
