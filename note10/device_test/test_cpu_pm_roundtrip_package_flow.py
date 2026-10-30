"""Exercise production package, precheck and collector flows for v49 scope flags."""
import argparse,hashlib,json,shutil,struct,sys,tempfile
from pathlib import Path
from contextlib import ExitStack
from unittest.mock import patch
import prepare_linux_boot as prep
import build_boot_test_packages as packages
import precheck_window_access as precheck
import collect_reservation as collector_module
from collect_reservation import collect as collect_reservation
from stage_phase2 import verify_packages
from cpu_pm_roundtrip_binding import PACKAGE_SOURCES,counts_package_scope
from ehld_lock_binding import MARKERS as LOCK_MARKERS,validate as validate_lock
from cpu_pm_roundtrip_binding import validate as validate_running_lock,package_scope as running_package_scope
from prepare_cpu_pm_roundtrip_flow_compat import prepare as prepare_running_lock_off
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

CASES=('production-flow-on','production-flow-off','invalid-scope-rejected')
COLLECTOR_CASES=('on','off','invalid-pair')
PRECHECK_CASES=('on','off','invalid-pair')
def sha(raw):return hashlib.sha256(raw).hexdigest()

def model_image(identity,roundtrip=False,counts=False):
 if not isinstance(identity,str) or len(identity)!=32 or any(c not in '0123456789abcdef' for c in identity):raise ValueError('invalid fixture reservation identity')
 image=bytearray(4096);image[56:60]=b'ARM\x64'
 markers=(b'N10CPMRT1' if roundtrip else b'')+(b'N10CPNC1' if counts else b'')+b''.join(CALLBACKS+PRECONDITIONS+BRANCH)+PMU_FAILURE+GIC_PRIORITY+b''.join(PMU_STATE+PMU_CONTROL+FPSIMD+RCU_MARKERS+LOCK_MARKERS)+b'N10RET1N10MEM1N10XNU1N10QUI1N10CPU2N10PMS1N10PMT1N10TMR1N10BND1N10TRY1'+identity.encode()
 image[128:128+len(markers)]=markers
 banner=b'Linux version 4.14.113-note10-reserve-pc fixture-v49'
 image[1024:1024+len(banner)]=banner
 return bytes(image)

def make_fixture(root,artifact,mode,scope_expected,counts_expected=False):
 from prepare_ehld_irqsave_flow_compat import KEEP_FILES,MODEL_PREFIXES
 artifact=Path(artifact);art=root/'artifact'
 if artifact.is_symlink() or not artifact.is_dir() or art.exists() or art.is_symlink():raise ValueError('unsafe package-flow fixture paths')
 art.mkdir(parents=True)
 for item in artifact.iterdir():
  if item.is_symlink():raise ValueError('symlink in package-flow input')
  counts_model=item.name=='cpu-pm-notifier-counts-model'
  keep_dir=item.is_dir() and (item.name.startswith(MODEL_PREFIXES) or item.name.startswith('cpu-pm-roundtrip-')) and (not counts_model or counts_expected)
  keep_file=item.is_file() and (item.name in KEEP_FILES or (item.suffix=='.log' and item.stat().st_size<=1024*1024) or item.name in ('window-core-model.json','window-gate-model.json','window-init-model.json'))
  if not (keep_dir or keep_file):continue
  destination=art/item.name
  if keep_dir:
   if any(path.is_symlink() for path in item.rglob('*')):raise ValueError('nested symlink in package-flow model input')
   shutil.copytree(item,destination)
  elif item.name not in ('Image','initramfs.cpio'):
   shutil.copy2(item,destination)
 counts_model_dir=art/'cpu-pm-notifier-counts-model'
 if counts_model_dir.exists() is not counts_expected:
  raise AssertionError('notifier-count model directory feature scope differs from fixture expectation')
 # Compact model inputs retain the markers and measured hashes used by the production gates.
 build=json.loads((art/'build-result.json').read_text(encoding='utf8'))
 identity=build.get('reservation_evidence_id','e'*32)
 if not isinstance(identity,str) or len(identity)!=32:raise ValueError('invalid fixture reservation identity')
 build['reservation_evidence_id']=identity
 build.setdefault('reservation_evidence_version',2)
 image=model_image(identity,scope_expected,counts_expected);(art/'Image').write_bytes(image)
 initramfs=b'v47-offline-initramfs-fixture';(art/'initramfs.cpio').write_bytes(initramfs)
 build['image_sha256']=sha(image);build['image_size']=len(image);build['initramfs_cpio_sha256']=sha(initramfs)
 # Normalize every notifier-count field/option for this synthetic scope.  The
 # input can be a counts-enabled CI artifact even when this fixture models the
 # legacy feature-off package; production validators remain strict.
 count_prefix='cpu_pm_notifier_counts_'
 for key in list(build):
  if key.startswith(count_prefix) and key not in ('cpu_pm_notifier_counts_version',):
   build.pop(key)
 config=(art/'handoff.config').read_text(encoding='ascii').splitlines()
 count_option='CONFIG_NOTE10_CPU_PM_NOTIFIER_COUNTS'
 config=[line for line in config if count_option not in line]
 build['cpu_pm_notifier_counts']=counts_expected
 build['cpu_pm_notifier_counts_version']=1 if counts_expected else None
 if counts_expected:
  from cpu_pm_roundtrip_binding import SOURCES as count_sources
  build['cpu_pm_notifier_counts_sources_sha256']={n:sha((Path(__file__).resolve().parent/n).read_bytes()) for n in count_sources}
  build['cpu_pm_notifier_counts_model_sha256']='0'*64
  config.append(count_option+'=y')
 (art/'handoff.config').write_text('\n'.join(config)+'\n',encoding='ascii',newline='\n')
 build['effective_config_sha256']=sha((art/'handoff.config').read_bytes())
 build['build_passed']=True;build['early_xnu_reservation']=True;build['reservation_evidence_version']=2
 (art/'build-result.json').write_text(json.dumps(build),encoding='utf8')
 parts={'boot':bytearray(131072),'recovery':b'R'*256,'dtb':b'D','dtbo':b'O','vbmeta':bytearray(256)}
 parts['boot'][32:48]=b'SEANDROIDENFORCE';parts['vbmeta'][:4]=b'AVB0';struct.pack_into('>I',parts['vbmeta'],120,2);parts={k:bytes(v) for k,v in parts.items()}
 backup=root/'backup';backup.mkdir();records=[]
 for i,(name,data) in enumerate(parts.items()):
  (backup/(name+'.img')).write_bytes(data);records.append({'partition':name,'file':name+'.img','block_node':'/dev/block/sda'+str(i+14),'size':len(data),'sha256':sha(data),'remote_hash_before_and_after_match':True})
 (backup/'backup-manifest.json').write_text(json.dumps({'complete':True,'partition_writes':False,'bootloader':'N976NTEST','partitions':records}),encoding='utf8')
 twrp=root/'twrp.img';twrp.write_bytes(parts['recovery']);mk=root/'mkbootimg.py';mk.write_bytes(b'mkboot-fixture')
 return art,backup,twrp,mk,parts

def run_collector_flow(kernel_build,backup,package_dir,private_root,log=None):
 adb=LogFakeAdb(backup,package_dir,log) if log is not None else FakeAdb(backup,package_dir)
 with ExitStack() as stack:
  _patch_legacy_gates(stack)
  stack.enter_context(patch.object(collector_module,'preflight',return_value={'twrp_version':'fixture'}))
  stack.enter_context(patch.object(collector_module,'ROOT',private_root))
  stack.enter_context(patch('cpu_pm_roundtrip_binding.validate',side_effect=lambda r,b,require_package_flow=True:running_package_scope(b)))
  return collect_reservation(package_dir,kernel_build,adb)

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
 def call(self,*args,**kwargs):
  if len(args)==4 and args[:3]==('shell','test','-r'):raise RuntimeError('fixture: no prior-boot logs')
  raise AssertionError(args)

class LogFakeAdb(FakeAdb):
 def __init__(self,backup,package_dir,log):super().__init__(backup,package_dir);self.log=log
 def call(self,*args,**kwargs):
  if len(args)==4 and args[:3]==('shell','test','-r'):
   if args[3]=='/proc/last_kmsg':return b''
   raise RuntimeError('fixture: absent optional pstore')
  if args==('exec-out','cat','/proc/last_kmsg'):return self.log
  raise AssertionError(args)

def run_precheck_flow(kernel_build,backup,package_dir,header,parts):
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
  stack.enter_context(patch.object(precheck,'read_verified_backup',return_value=parts))
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

def _patch_legacy_gates(stack):
 validators=('pm_quiesce_binding.assert_scope','gic_roundtrip_binding.validate_model','dma_pm_binding.validate_model','ufs_pm_binding.validate_model','iommu_pm_binding.validate_model','abox_pm_binding.validate_model','abox_pmu_binding.validate_model','pm_noirq_binding.validate_model','pmu_settle_binding.validate_model','pm_cpus_binding.validate_model','pm_post_arch_binding.validate_model','pm_edge_binding.validate_model','pm_callbacks_binding.validate_model','pm_preconditions_binding.validate_model','pm_branch_binding.validate_model','pmu_failure_binding.validate','gic_priority_binding.validate','pmu_state_binding.validate','pmu_control_binding.validate','fpsimd_reference_binding.validate','pm_irq_binding.validate_model','materialize_auto_cycle.validate','prepare_reservation_kernel.verify_embedded_init')
 for name in validators:stack.enter_context(patch(name,return_value=True))
 for module in ('gic_roundtrip_binding','dma_pm_binding','ufs_pm_binding','iommu_pm_binding','abox_pm_binding','abox_pmu_binding','pm_noirq_binding','pmu_settle_binding','pm_cpus_binding','pm_post_arch_binding','pm_edge_binding','pm_callbacks_binding','pm_preconditions_binding','pm_branch_binding','pm_irq_binding'):
  stack.enter_context(patch(module+'.assert_scope',return_value=True))
 stack.enter_context(patch('rcu_context_binding.validate',return_value=True))
 stack.enter_context(patch('ehld_lock_binding.validate',return_value=True))
 stack.enter_context(patch('ehld_irqsave_binding.validate',side_effect=lambda r,b,require_package_flow=True:b.get('ehld_irqsave_audit') is True))
 stack.enter_context(patch('ehld_running_lock_binding.validate',return_value=True))
 stack.enter_context(patch('cpu_pm_roundtrip_binding.validate',side_effect=lambda r,b,require_package_flow=True:running_package_scope(b)))

def _header(kernel_sha):
 return {'header_version':1,'page_size':2048,'recovery_dtbo_size':0,'second_size':0,'kernel_addr':0,'tags_addr':0,'arm64_text_offset':0,'ramdisk_addr':0,'ramdisk_file_offset':2048,'ramdisk_size':0,'second_file_offset':32,'cmdline':'fixture','name':'fixture','os_version':'1.0.0','security_patch_month':'2026-01','kernel_sha256':kernel_sha}

def _prepare_packages(root,source,mode,identity,scope_expected,counts_expected=False):
 case_root=root/mode;case_root.mkdir();art,backup,twrp,mk,parts=make_fixture(case_root,source,mode,scope_expected,counts_expected)
 image=model_image(identity,scope_expected,counts_expected);(art/'Image').write_bytes(image)
 build=json.loads((art/'build-result.json').read_text(encoding='utf8'));build.update(reservation_evidence_id=identity,reservation_evidence_version=2,image_sha256=sha(image),image_size=len(image),build_passed=True,early_xnu_reservation=True,cpu_pm_notifier_counts=counts_expected,cpu_pm_notifier_counts_version=1 if counts_expected else None)
 (art/'build-result.json').write_text(json.dumps(build,indent=2)+'\n',encoding='utf8',newline='\n')
 header=_header(build['image_sha256']);prototype=case_root/(mode+'.img');packages_out=case_root/'packages'
 def fake_mk(cmd,**kwargs):
  out=Path(cmd[cmd.index('--output')+1]);size=prep.payload_size(len(image),0,2048,len(parts['boot']),allow_empty_ramdisk=True);out.write_bytes(b'P'*2048+image+bytes(size-2048-len(image)))
 with ExitStack() as stack:
  _patch_legacy_gates(stack)
  stack.enter_context(patch.object(prep,'MKBOOTIMG_SHA256',sha(mk.read_bytes())));stack.enter_context(patch.object(prep,'TWRP_SHA256',sha(twrp.read_bytes())))
  stack.enter_context(patch.object(prep,'read_verified_backup',return_value=parts));stack.enter_context(patch.object(packages,'read_verified_backup',return_value=parts))
  stack.enter_context(patch.object(prep,'boot_header',return_value=header));stack.enter_context(patch.object(prep.subprocess,'run',side_effect=fake_mk))
  report=prep.prepare(backup,art,twrp,mk,prototype,auto_cycle_token=identity)
  built=packages.build(backup,prototype,packages_out);records=verify_packages(packages_out)
  diag=next(record for record in records if record['mode']=='diagnostic');rollback=next(record for record in records if record['mode']=='rollback')
  metadata=json.loads((packages_out/'package-result.json').read_text(encoding='utf8'))
  if (report.get('cpu_pm_roundtrip') is not scope_expected or built.get('cpu_pm_roundtrip') is not scope_expected or
      running_package_scope(metadata) is not scope_expected or counts_package_scope(metadata) is not counts_expected):
   raise AssertionError('production prep/package CPU-PM-roundtrip scope differs')
  if diag.get('cpu_pm_roundtrip') is not scope_expected or diag.get('cpu_pm_roundtrip_version')!=(1 if scope_expected else None):
   raise AssertionError('diagnostic package CPU-PM-roundtrip scope differs')
  if rollback.get('cpu_pm_roundtrip') is not False or rollback.get('cpu_pm_roundtrip_version') is not None:
   raise AssertionError('rollback package unexpectedly carries CPU-PM-roundtrip scope')
  if diag.get('cpu_pm_notifier_counts') is not counts_expected or diag.get('cpu_pm_notifier_counts_version')!=(1 if counts_expected else None):
   raise AssertionError('diagnostic package CPU-PM notifier-count scope differs')
  if rollback.get('cpu_pm_notifier_counts') is not False or rollback.get('cpu_pm_notifier_counts_version') is not None:
   raise AssertionError('rollback package unexpectedly carries notifier-count scope')
  (packages_out/'ram-stage-fixture.json').write_text(json.dumps({'ram_directory':'/tmp/note10-reserve-deadbeef'}),encoding='utf8',newline='\n')
  precheck_result=run_precheck_flow(art,backup,packages_out,header,parts)
  if (precheck_result.get('ready_for_manual_access_test') is not True or precheck_result.get('partition_writes') is not False or
      precheck_result.get('cpu_pm_roundtrip_scope_verified') is not scope_expected or
      precheck_result.get('cpu_pm_notifier_counts_scope_verified') is not counts_expected):
   raise AssertionError('production precheck scope/result differs')
  collector_result=run_collector_flow(art,backup,packages_out,case_root)
  expected_rows=41 if counts_expected else (40 if scope_expected else 39)
  if len(collector_result.get('evaluation_items',{}))!=expected_rows or collector_result.get('cpu_pm_roundtrip_scope_verified') is not scope_expected or collector_result.get('cpu_pm_notifier_counts_scope_verified') is not counts_expected:
   raise AssertionError('production collector scope/39-row contract differs')
 return {'art':art,'backup':backup,'twrp':twrp,'mkboot':mk,'parts':parts,'prototype':prototype,'packages':packages_out,'header':header,
         'report':report,'built':built,'precheck':precheck_result,'collector':collector_result}

def _invalid_prepare(root,source,identity):
 case_root=root/'invalid';case_root.mkdir();art,backup,twrp,mk,parts=make_fixture(case_root,source,'invalid',False)
 build=json.loads((art/'build-result.json').read_text(encoding='utf8'));build['cpu_pm_roundtrip']=None
 (art/'build-result.json').write_text(json.dumps(build,indent=2)+'\n',encoding='utf8',newline='\n')
 prototype=case_root/'invalid.img';header=_header(build['image_sha256'])
 def fake_mk(cmd,**kwargs):
  image=(art/'Image').read_bytes();out=Path(cmd[cmd.index('--output')+1]);size=prep.payload_size(len(image),0,2048,len(parts['boot']),allow_empty_ramdisk=True);out.write_bytes(b'P'*2048+image+bytes(size-2048-len(image)))
 with ExitStack() as stack:
  _patch_legacy_gates(stack)
  stack.enter_context(patch.object(prep,'MKBOOTIMG_SHA256',sha(mk.read_bytes())));stack.enter_context(patch.object(prep,'TWRP_SHA256',sha(twrp.read_bytes())))
  stack.enter_context(patch.object(prep,'read_verified_backup',return_value=parts));stack.enter_context(patch.object(prep,'boot_header',return_value=header));stack.enter_context(patch.object(prep.subprocess,'run',side_effect=fake_mk))
  try:prep.prepare(backup,art,twrp,mk,prototype,auto_cycle_token=identity)
  except (ValueError,TypeError,KeyError):return {'case':'invalid-scope-rejected','accepted':False}
 raise AssertionError('production prepare accepted explicit null CPU-PM-roundtrip flag')

def _mismatched_pair(root,off):
 bad_prototype=root/'mismatched.img';shutil.copyfile(off['prototype'],bad_prototype)
 shutil.copyfile(off['prototype'].with_suffix('.json'),bad_prototype.with_suffix('.json'))
 meta_path=bad_prototype.with_suffix('.json');meta=json.loads(meta_path.read_text(encoding='utf8'));meta['cpu_pm_roundtrip']=True;meta['cpu_pm_roundtrip_version']=1
 raw=bytearray(bad_prototype.read_bytes());raw[512:521]=b'N10CPMRT1';bad_prototype.write_bytes(raw);meta['sha256']=sha(raw);meta['size']=len(raw)
 meta_path.write_text(json.dumps(meta,indent=2)+'\n',encoding='utf8',newline='\n')
 out=root/'mismatched-packages'
 with patch.object(packages,'read_verified_backup',return_value=off['parts']):packages.build(off['backup'],bad_prototype,out)
 verify_packages(out)
 (out/'ram-stage-fixture.json').write_text(json.dumps({'ram_directory':'/tmp/note10-reserve-deadbeef'}),encoding='utf8',newline='\n')
 with ExitStack() as stack:
  _patch_legacy_gates(stack)
  try:run_precheck_flow(off['art'],off['backup'],out,off['header'],off['parts'])
  except (ValueError,KeyError,FileNotFoundError):pre_rejected=True
  else:raise AssertionError('production precheck accepted package/kernel scope mismatch')
  try:run_collector_flow(off['art'],off['backup'],out,root)
  except (ValueError,KeyError,FileNotFoundError):collector_rejected=True
  else:raise AssertionError('production collector accepted package/kernel scope mismatch')
 return pre_rejected,collector_rejected

def _frame(tag,values):
 from decode_reservation import checksum
 body=' '.join(k+'='+str(v) for k,v in values.items())
 return f'{tag} {body} checksum={checksum(body.encode("ascii")):08x}\n'

def terminal_pm_failure_log(kernel_build,package_dir,reservation_failure=False):
 build=json.loads((kernel_build/'build-result.json').read_text(encoding='utf8'))
 paired=json.loads((package_dir/'package-result.json').read_text(encoding='utf8'))
 identity=build['reservation_evidence_id'];cycle=paired['auto_cycle_token'];generation=7;completed_generation=generation+1
 digest=build['xnu_payload_sha256'];size=build['xnu_payload_size'];words=size//8
 lines=[]
 for seq in (0,1):lines.append(_frame('N10RET1',dict(id=identity,cycle=cycle,phase=0,seq=seq,delay_ms=90000,status=0)))
 lines.append('Linux version 4.14.113-note10-reserve-pc fixture-v49\n')
 reserved=65535 if reservation_failure else 65536
 for seq in (0,1):lines.append(_frame('N10RAM2',dict(id=identity,seq=seq,base='a00000000',size='10000000',align='2000000',pages=65536,reserved=reserved,invalid=0,shift=12)))
 for seq in (0,1):lines.append(_frame('N10QSC1',dict(id=identity,seq=seq,attempt=1,version=1,generation=completed_generation,epoch=0,phase=10,called=1,restored=1,screen=0,display=0,usb=0,wake=0,r_usb=0,r_display=0,r_screen=0)))
 for seq in (0,1):lines.append(_frame('N10PMS1',dict(id=identity,seq=seq,attempt=1,stage=21,error=1)))
 from decode_window_access import COUNTS
 for seq in (0,1):lines.append(_frame('N10MEM1',dict(id=identity,seq=seq,base='a00000000',size='10000000',**COUNTS)))
 for seq in (0,1):lines.append(_frame('N10XNU1',dict(id=identity,seq=seq,base='a00000000',size='10000000',bytes=size,sha256=digest,status=0)))
 for seq in (0,1):lines.append(_frame('N10QUI1',dict(id=identity,seq=seq,before='ff',stopped=1,restored='ff',cpus=8,words=words,fnv='123',sha256=digest,clean=1,status=0)))
 for cpu in range(8):
  for seq in (0,1):lines.append(_frame('N10CPU2',dict(id=identity,seq=seq,cpu=cpu,el='4',mpidr=format(cpu,'x'),sctlr='1005',tcr='123',ttbr1='456',mair='ff',cntkctl='0',cntfrq='18cba80',words=words,fnv='123')))
 for seq in (0,1):lines.append(_frame('N10PMT1',dict(id=identity,seq=seq,before='ff',after='ff',devices=1,resume=1,blocked=0,oldlevel=0,newlevel=0,resume_errors=0,timers=8,error=1,sha256=digest,status=0)))
 for copy in (0,1):lines.append(_frame('N10PRQ1',dict(id=identity,copy=copy,generation=generation,status=-5,count=0,complete=0,gic_complete=0)))
 terminal=dict(id=identity,copy=0,generation=generation,attempted=1,recorded=1,completed=1,caller_invoked=1,stage=2,outer_error=0,helper_error=-16,probe_error=-16,enter_calls=0,exit_calls=0,enter_error=0,exit_error=0)
 for copy in (0,1):terminal['copy']=copy;lines.append(_frame('N10CPT1',terminal.copy()))
 return ''.join(lines)

def terminal_collect_entry_case(on,case_root):
 log=terminal_pm_failure_log(on['art'],on['packages'])
 identity=json.loads((on['art']/'build-result.json').read_text(encoding='utf8'))['reservation_evidence_id']
 from decode_pm_preconditions import decode as decode_preconditions
 try:decode_preconditions(log,identity,8)
 except ValueError:strict_preconditions_rejected=True
 else:raise AssertionError('strict PM preconditions accepted status=-5 fixture')
 report=run_collector_flow(on['art'],on['backup'],on['packages'],case_root,log.encode('ascii'))
 observation=json.loads((Path(report['directory'])/'reservation-observation.json').read_text(encoding='utf8'))
 if (report.get('previous_boot_cpu0_cpu_pm_terminal_failure_observed') is not True or
     report.get('previous_boot_cpu0_cpu_pm_enter_exit_pair_observed') is not False or
     report.get('evaluation_items',{}).get('cpu0_cpu_pm_enter_exit_pair')!={'required':True,'status':'failed'} or
     report.get('diagnostic_passed') is not False or
     report.get('decode_failures',{}).get('last_kmsg.txt')!='PM devices or timer roundtrip failed' or
     'cpu_pm_roundtrip_terminal_failure' not in observation):
  raise AssertionError('production collect() did not preserve failure terminal before strict PM decode: '+repr({k:report.get(k) for k in ('previous_boot_cpu0_cpu_pm_terminal_failure_observed','previous_boot_cpu0_cpu_pm_enter_exit_pair_observed','evaluation_items','diagnostic_passed','decode_failures')})+' observation='+repr(observation))
 return {'case':'collect-entry-pmt-error-prq-failure-valid-terminal','accepted':True,
         'terminal_preserved':True,'pair_passed':False,'strict_pm_preconditions_rejected':strict_preconditions_rejected,
         'pm_timer_failure':report['decode_failures']['last_kmsg.txt']}

def terminal_reservation_entry_case(on,case_root):
 log=terminal_pm_failure_log(on['art'],on['packages'],reservation_failure=True)
 report=run_collector_flow(on['art'],on['backup'],on['packages'],case_root,log.encode('ascii'))
 observation=json.loads((Path(report['directory'])/'reservation-observation.json').read_text(encoding='utf8'))
 if (report.get('previous_boot_cpu0_cpu_pm_terminal_failure_observed') is not True or
     report.get('previous_boot_reservation_observed') is not False or
     report.get('previous_boot_cpu0_cpu_pm_enter_exit_pair_observed') is not False or
     report.get('evaluation_items',{}).get('reservation')!={'required':True,'status':'failed'} or
     report.get('evaluation_items',{}).get('cpu0_cpu_pm_enter_exit_pair')!={'required':True,'status':'failed'} or
     report.get('diagnostic_passed') is not False or
     report.get('decode_failures',{}).get('last_kmsg.txt')!='Linux did not retain all reserved pages' or
     'cpu_pm_roundtrip_terminal_failure' not in observation):
  raise AssertionError('production collect() lost terminal before strict reservation failure: '+repr({k:report.get(k) for k in ('previous_boot_cpu0_cpu_pm_terminal_failure_observed','previous_boot_reservation_observed','previous_boot_cpu0_cpu_pm_enter_exit_pair_observed','diagnostic_passed','decode_failures')})+' observation='+repr(observation))
 return {'case':'collect-entry-reservation-failure-valid-terminal','accepted':True,
         'terminal_preserved':True,'reservation_passed':False,'pair_passed':False,
         'reservation_failure':report['decode_failures']['last_kmsg.txt']}

def terminal_collector_cases():
 from test_cpu_pm_roundtrip_decoder import input_vector,terminal_input_vector
 identity='a'*32;completed=10
 success_text=json.loads(input_vector('valid-pair'))['text']
 failure_text=json.loads(terminal_input_vector('stage2-admission'))['text']
 success=collector_module.decode_cpu_pm_roundtrip_observation(success_text,identity,completed)
 failure=collector_module.decode_cpu_pm_roundtrip_observation(failure_text,identity,completed)
 if success.get('pair_observed') is not True or success.get('evaluation_item')!={'required':True,'status':'passed'}:
  raise AssertionError('collector strict success pair was not preserved')
 if (failure.get('pair_observed') is not False or failure.get('terminal_failure_observed') is not True or
     failure.get('pair_passed') is not False or failure.get('evaluation_item')!={'required':True,'status':'failed'}):
  raise AssertionError('collector terminal failure was promoted')
 try:collector_module.decode_cpu_pm_roundtrip_observation(success_text+'\n'+failure_text,identity,completed)
 except ValueError:pass
 else:raise AssertionError('collector accepted conflicting strict-success and terminal-failure frames')
 return ['strict-success','terminal-failure','success-failure-conflict'],[
  {'case':'strict-success','accepted':True,'pair_observed':True,'required':True,'status':'passed'},
  {'case':'terminal-failure','accepted':True,'pair_observed':False,'terminal_failure_observed':True,'required':True,'status':'failed'},
  {'case':'success-failure-conflict','accepted':False}]

def notifier_count_collector_cases():
 from test_cpu_pm_roundtrip_decoder import input_vector,terminal_input_vector
 from decode_cpu_pm_roundtrip import COUNTS_SCHEMA
 from decode_reservation import checksum
 identity='a'*32;completed=10;generation=9
 success_text=json.loads(input_vector('valid-pair'))['text']
 def counts(nr=6,include_second=True):
  frames=[]
  for copy in (0,1) if include_second else (0,):
   values={'id':identity,'copy':copy,'generation':generation,'attempted':1,'roster':6,
    'roster_valid':1,'enter_calls':1,'exit_calls':1,'enter_nr_calls':nr,'exit_nr_calls':6,
    'enter_seen':1,'exit_seen':1,'capture_valid':1,'conflict':0,'enter_error':0,
    'exit_error':0,'error':0,'caller_invoked':1,'terminal_stage':0,
    'terminal_helper_error':0,'terminal_probe_error':0,'terminal_outer_error':0}
   body=' '.join(k+'='+str(values[k]) for k in COUNTS_SCHEMA)
   frames.append('N10CPN1 '+body+' checksum=%08x\n'%checksum(body.encode('ascii')))
  return ''.join(frames)
 passed=collector_module.decode_cpu_pm_roundtrip_observation(success_text+'\n'+counts(),identity,completed,True)
 if passed['evaluation_item']['status']!='passed' or passed['counts_evaluation_item']['status']!='passed':
  raise AssertionError('valid paired CPU PM plus notifier-count companion rejected')
 partial=collector_module.decode_cpu_pm_roundtrip_observation(success_text+'\n'+counts(include_second=False),identity,completed,True)
 mismatch=collector_module.decode_cpu_pm_roundtrip_observation(success_text+'\n'+counts(nr=5),identity,completed,True)
 terminal_text=json.loads(terminal_input_vector('stage2-admission'))['text']
 terminal=collector_module.decode_cpu_pm_roundtrip_observation(terminal_text,identity,completed,True)
 if (partial['pair_observed'] is not True or partial['evaluation_item']['status']!='passed' or
     partial['counts_evaluation_item']['status']!='failed' or mismatch['evaluation_item']['status']!='passed' or
     mismatch['counts_evaluation_item']['status']!='failed'):
  raise AssertionError('notifier-count failure changed independent CPR pass result')
 if terminal['evaluation_item']['status']!='failed' or terminal['counts_evaluation_item']['status']!='failed':
  raise AssertionError('terminal CPU_PM state satisfied notifier-count row')
 no_feature=collector_module.decode_cpu_pm_roundtrip_observation(success_text,identity,completed,False)
 if no_feature.get('counts_evaluation_item') is not None:raise AssertionError('old package gained notifier-count row')
 return ['counts-on-pass','counts-on-partial-fails-only-count-row','counts-on-mismatch-fails-only-count-row','counts-on-terminal-fails-both','counts-off-retains-old-row-set'],[
  {'case':'counts-on-pass','pair':'passed','counts':'passed'},
  {'case':'counts-on-partial-fails-only-count-row','pair':'passed','counts':'failed'},
  {'case':'counts-on-mismatch-fails-only-count-row','pair':'passed','counts':'failed'},
  {'case':'counts-on-terminal-fails-both','pair':'failed','counts':'failed'},
  {'case':'counts-off-retains-old-row-set','counts_row':False}]

def notifier_count_scope_cases():
 prior={'ehld_lock_audit':True,'ehld_lock_audit_version':1,'ehld_irqsave_audit':True,
  'ehld_irqsave_audit_version':1,'ehld_running_lock_audit':True,
  'ehld_running_lock_audit_version':2,'auto_return_diagnostic':True}
 on={'cpu_pm_roundtrip':True,'cpu_pm_roundtrip_version':1,**prior,
     'cpu_pm_notifier_counts':True,'cpu_pm_notifier_counts_version':1}
 off={'cpu_pm_roundtrip':True,'cpu_pm_roundtrip_version':1,**prior,
      'cpu_pm_notifier_counts':False,'cpu_pm_notifier_counts_version':None}
 if counts_package_scope(on) is not True or counts_package_scope(off) is not False:
  raise AssertionError('CPU PM notifier-count package scope ON/OFF differs')
 try:counts_package_scope({'cpu_pm_notifier_counts':True,'cpu_pm_notifier_counts_version':1})
 except (ValueError,TypeError,KeyError):pass
 else:raise AssertionError('CPU PM notifier-count scope accepted without roundtrip')
 for name,metadata,allow in (
  ('counts-scope-on-unknown-rejected',{**on,'cpu_pm_notifier_counts_unreviewed':True},False),
  ('counts-scope-package-build-proof-rejected',{**on,'cpu_pm_notifier_counts_model_sha256':'0'*64},False),
  ('counts-scope-off-stray-proof-rejected',{**off,'cpu_pm_notifier_counts_model_sha256':'0'*64},False)):
  try:counts_package_scope(metadata,allow_build_proof=allow)
  except (ValueError,TypeError,KeyError):continue
  raise AssertionError('CPU PM notifier-count scope accepted stray metadata: '+name)
 build={**on,'cpu_pm_notifier_counts_sources_sha256':{'source.py':'0'*64},
        'cpu_pm_notifier_counts_model_sha256':'0'*64}
 if counts_package_scope(build,allow_build_proof=True) is not True:
  raise AssertionError('CPU PM notifier-count build proof metadata rejected')
 return ['counts-scope-on','counts-scope-off','counts-requires-roundtrip',
  'counts-scope-on-unknown-rejected','counts-scope-package-build-proof-rejected',
  'counts-scope-off-stray-proof-rejected','counts-scope-build-proof-allowed'],[
  {'case':'counts-scope-on','accepted':True,'scope':True},
  {'case':'counts-scope-off','accepted':True,'scope':False},
  {'case':'counts-requires-roundtrip','accepted':False},
  {'case':'counts-scope-on-unknown-rejected','accepted':False},
  {'case':'counts-scope-package-build-proof-rejected','accepted':False},
  {'case':'counts-scope-off-stray-proof-rejected','accepted':False},
  {'case':'counts-scope-build-proof-allowed','accepted':True,'scope':True}]

def main():
 p=argparse.ArgumentParser();p.add_argument('--artifact',type=Path);p.add_argument('--output',type=Path);p.add_argument('--counts-only',action='store_true');a=p.parse_args()
 if a.counts_only:
  cases,results=notifier_count_collector_cases();scopes,scope_results=notifier_count_scope_cases()
  print(json.dumps({'passed':True,'cases':cases,'results':results,'scope_cases':scopes,'scope_results':scope_results}))
  return
 if a.artifact is None or a.output is None:raise ValueError('--artifact and --output are required')
 source_dir=Path(__file__).resolve().parent
 measured={n:sha((source_dir/n).read_bytes()) for n in PACKAGE_SOURCES}
 initial=json.loads((a.artifact/'build-result.json').read_text(encoding='utf8'))
 if initial.get('cpu_pm_roundtrip_package_sources_sha256')!=measured:raise ValueError('v49 package source map differs')
 if initial.get('build_passed') is not False:raise ValueError('package-flow requires explicitly synthetic outer build_passed=False')
 counts_enabled=initial.get('cpu_pm_notifier_counts',False)
 if type(counts_enabled) is not bool:raise ValueError('counts fixture input flag must be bool or absent')
 counts_version=initial.get('cpu_pm_notifier_counts_version')
 count_option=b'CONFIG_NOTE10_CPU_PM_NOTIFIER_COUNTS'
 input_config=(a.artifact/'handoff.config').read_bytes().splitlines()
 count_config=[line for line in input_config if count_option in line]
 input_image=(a.artifact/'Image').read_bytes()
 count_model=(a.artifact/'cpu-pm-notifier-counts-model')
 count_proof_keys=[k for k in initial if k.startswith('cpu_pm_notifier_counts_') and k!='cpu_pm_notifier_counts_version']
 if counts_enabled:
  if (type(counts_version) is not int or counts_version!=1 or
      count_config!=[count_option+b'=y'] or b'N10CPNC1' not in input_image or
      not count_model.is_dir() or not isinstance(initial.get('cpu_pm_notifier_counts_sources_sha256'),dict) or
      not isinstance(initial.get('cpu_pm_notifier_counts_model_sha256'),str)):
   raise ValueError('counts-enabled package-flow input is incomplete')
 elif (counts_version is not None or count_config not in ([],[count_option+b'=n'],[b'# '+count_option+b' is not set']) or b'N10CPNC1' in input_image or
       count_model.exists() or count_model.is_symlink() or count_proof_keys):
  raise ValueError('counts-disabled package-flow input contains feature evidence')
 a.output.mkdir(parents=True,exist_ok=False)
 with tempfile.TemporaryDirectory(dir=prep.ROOT/'note10/private') as td:
  root=Path(td);on=_prepare_packages(root,a.artifact,'on','c'*32,True)
  off_base=root/'v46-compat';prepare_running_lock_off(a.artifact,off_base)
  off=_prepare_packages(root,off_base,'off','d'*32,False)
  counts_on=None
  counts_on_model_dir=None
  if counts_enabled:
   counts_on=_prepare_packages(root,a.artifact,'counts-on','f'*32,True,True)
   counts_on_model_dir=(counts_on['art']/'cpu-pm-notifier-counts-model').is_dir()
  off_model_dir=(off['art']/'cpu-pm-notifier-counts-model').exists()
  if (counts_enabled and counts_on_model_dir is not True) or off_model_dir is not False:
   raise AssertionError('counts model directory was not kept ON/excluded OFF')
  if {k:v for k,v in on['collector']['evaluation_items'].items() if k!='cpu0_cpu_pm_enter_exit_pair'}!=off['collector']['evaluation_items']:
   raise AssertionError('the original collector evaluation rows changed with v49 scope')
  if counts_enabled:
   unchanged={k:v for k,v in counts_on['collector']['evaluation_items'].items()
              if k not in ('cpu0_cpu_pm_enter_exit_pair','cpu0_cpu_pm_notifier_counts')}
   if unchanged!=off['collector']['evaluation_items']:
    raise AssertionError('new counts scope changed legacy collector rows')
   if (counts_on['collector']['evaluation_items'].get('cpu0_cpu_pm_enter_exit_pair',{}).get('required') is not True or
       counts_on['collector']['evaluation_items'].get('cpu0_cpu_pm_notifier_counts')!={'required':True,'status':'failed'}):
    raise AssertionError('counts feature rows do not remain independently required')
  invalid=_invalid_prepare(root,a.artifact,'e'*32)
  pre_rejected,collector_rejected=_mismatched_pair(root,off)
  package_results=[{'case':CASES[0],'accepted':True,'scope':True,'diagnostic':True,'rollback':False},
                   {'case':CASES[1],'accepted':True,'scope':False,'diagnostic':False,'rollback':False},invalid]
  precheck_cases=[{'case':'on','accepted':True,'scope':True,'ready':True,'partition_writes':False},
                  {'case':'off','accepted':True,'scope':False,'ready':True,'partition_writes':False},
                  {'case':'invalid-pair','accepted':False}]
  collector_cases=[{'case':'on','accepted':True,'evaluation_items':40,'scope':True},
                   {'case':'off','accepted':True,'evaluation_items':39,'scope':False},
                   {'case':'invalid-pair','accepted':False}]
  terminal_cases,terminal_results=terminal_collector_cases()
  counts_cases,counts_results=notifier_count_collector_cases()
  count_scope_cases,count_scope_results=notifier_count_scope_cases()
  if counts_enabled:
   counts_package_cases=['counts-on-build-prepare-package-precheck-stage-collector']
   counts_package_results=[{'case':counts_package_cases[0],'build_flag':True,
       'prototype_marker':True,'diagnostic_scope':True,'rollback_scope':False,
       'precheck_scope':True,'collector_scope':True,'collector_rows':41,
       'legacy_rows_equal_off':True,'missing_log_counts_row':'failed'}]
   counts_package_status='counts-enabled production fixture passed'
  else:
   counts_package_cases=[]
   counts_package_results=[]
   counts_package_status='not executed; counts feature disabled in input'
  collector_entry_result=terminal_collect_entry_case(on,root/'collector-terminal-entry')
  collector_reservation_result=terminal_reservation_entry_case(on,root/'collector-reservation-terminal-entry')
  items=on['collector']['evaluation_items'];items_off=off['collector']['evaluation_items']
  result={'schema_version':1,'passed':True,'hardware_verified':False,'synthetic_fixture':True,'legacy_gate_stubs':['ehld_lock','ehld_irqsave','ehld_running_lock'],'cpu_pm_validator_scope_only_stub':True,'cases':list(CASES),'case_results':package_results,
          'precheck_cases':['on','off','invalid-pair'],'precheck_cases_result':precheck_cases,'collector_cases':['on','off','invalid-pair'],'collector_cases_result':collector_cases,'collector_evaluation_items':items,'collector_evaluation_items_off':items_off,
          'terminal_collector_cases':terminal_cases,'terminal_collector_results':terminal_results,
          'notifier_count_collector_cases':counts_cases,'notifier_count_collector_results':counts_results,
          'notifier_count_scope_cases':count_scope_cases,'notifier_count_scope_results':count_scope_results,
          'notifier_count_package_flow_cases':counts_package_cases,'notifier_count_package_flow_results':counts_package_results,
          'notifier_count_package_flow_status':counts_package_status,
          'counts_enabled_in_input':counts_enabled,
          'counts_fixture_model_directory_scope':{'on_present':counts_on_model_dir,'off_present':off_model_dir},
          'collector_entry_failure_case':collector_entry_result,
          'collector_reservation_failure_case':collector_reservation_result,
          'collector_evaluation_items_sha256':sha(json.dumps(items,sort_keys=True,separators=(',',':')).encode()),
          'harness_sha256':sha(Path(__file__).read_bytes()),'package_sources_sha256':measured}
  (a.output/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8',newline='\n')

if __name__=='__main__':main()
