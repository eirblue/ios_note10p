"""Real full diagnostic init.o only. No Image, linker, emulator or wrapper execution."""
import argparse,ast,hashlib,json,os,re,shlex,shutil,subprocess,sys,uuid,tarfile
from pathlib import Path,PurePosixPath
from build_xnu_runtime_plan_component import acquire,extract,parse_dependencies,source_dependency,COMMIT,ARCHIVE_SHA,SOURCE_TOP,DEFCONFIG,TARGET,CMD
from prepare_pre_pm_trial import ROOT,BASE,OPTION,render,install,config_settings,require,digest
from pre_pm_trial_object import object_proof
from pre_pm_crypto_provider import provider_proof
from xnu_runtime_scratch_stack import command_origin,postprocess_provenance,KBUILD_PINS
INSTRUMENTATION='-gdwarf-4 -fstack-usage -ffunction-sections -fdata-sections -mllvm -enable-machine-outliner=never -fno-inline-functions'
PUBLIC_DRIVER='note10/device_test/build_pre_pm_trial.py'
EXTRA_SOURCE=('note10/device_test/pre_pm_trial_wrapper.c','note10/device_test/pre_pm_trial_policy.h','note10/device_test/pre_pm_trial_policy_fixture.c','note10/device_test/kernel_trial_stack_oracle.c','note10/device_test/relocation_trial_input.py','note10/device_test/test_pre_pm_provider.py','.github/workflows/note10-pre-pm-trial.yml')
IMMUTABLE=('note10/xnu26/runtime_relocation.c','note10/xnu26/runtime_relocation.h','note10/xnu26/runtime_relocation_trial.c','note10/xnu26/runtime_relocation_trial.h','note10/device_test/relocation_trial_aarch64_abi.c')
CORE_PINS={
 'note10/xnu26/runtime_relocation.c':'dc51d22fce4c8e0d566d6158f53aa3d512a65954541e4ea4201c5878cb17e448',
 'note10/xnu26/runtime_relocation.h':'2956336fbec371636acb62a4fc51aae451e74a65bdf4595b12e80c3be8ca9037',
 'note10/xnu26/runtime_relocation_trial.c':'3295a1d005c38b4ab213b69c56705a6caec453916a11d54e3287434b4a3853b9',
 'note10/xnu26/runtime_relocation_trial.h':'7b76597c2436029fdc3c259ec9d1998047d2b5e4c8ed33f9d47adf52be03eaf2',
 'note10/device_test/relocation_trial_aarch64_abi.c':'e20258dfbb8cc93793c974a4386df5e8dda32a9db77c3d14e0c3456601b7b0d7'}
KBUILD_FILES=(*KBUILD_PINS,'scripts/basic/fixdep.c','scripts/config','Makefile','arch/arm64/Makefile','arch/arm64/mm/Makefile','arch/arm64/configs/'+DEFCONFIG,'crypto/sha256_generic.c','crypto/Makefile','include/crypto/sha.h','crypto/Kconfig','include/linux/preempt.h','include/linux/preempt_mask.h','include/linux/interrupt.h','include/linux/vmalloc.h','include/linux/sort.h','include/crypto/hash.h')
PREFIX_SHA='3b3e7299672928ebe7086582891ddf35878e1cd5ed60bfd9ce710d8a864e7b36'
def sha(path):
 h=hashlib.sha256()
 with path.open('rb') as f:
  for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
 return h.hexdigest()
def write(path,value):
 path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(value,indent=2,sort_keys=True)+'\n',encoding='utf8',newline='\n')
def import_closure():
 todo=[PUBLIC_DRIVER,'note10/device_test/test_pre_pm_trial.py'];seen=set()
 while todo:
  name=todo.pop()
  if name in seen:continue
  seen.add(name);tree=ast.parse((ROOT/name).read_text())
  # Old utility modules are imported, but their unrelated deferred mains are never called.
  nodes=ast.walk(tree) if 'pre_pm' in Path(name).name else tree.body
  for node in nodes:
   candidates=[node.module] if isinstance(node,ast.ImportFrom) else [x.name for x in node.names] if isinstance(node,ast.Import) else []
   for module in candidates:
    if module:
     file='note10/device_test/'+module.split('.')[0]+'.py'
     if (ROOT/file).is_file() and file not in seen:todo.append(file)
 manifest=json.loads((BASE/'manifest.json').read_text())
 seen.update(x['public_source'] for x in manifest['files']);seen.update(EXTRA_SOURCE);seen.update(IMMUTABLE)
 seen.add('note10/device_test/relocation_trial_kernel_profile.json')
 seen.update(('note10/device_test/full_diagnostic_v57/manifest.json','note10/device_test/full_diagnostic_v57/config.json'))
 return sorted(seen)
def validate_flags(args):
 require(args.count('-fno-inline-functions')==1 and not any(x in args for x in ('-finline-functions','-finline-functions-hint','-finline-hint-functions','-flto','-flto=thin','-flto=full')),'explicit noinline analysis; no conflicting inline/LTO')
 require([x for x in args if re.fullmatch('-O[0-3szg]',x)][-1:]==['-Oz'],'retained actual Oz order')
 for x in ('-gdwarf-4','-fstack-usage','-ffunction-sections','-fdata-sections','-mno-implicit-float'):require(args.count(x)==1,'actual analysis/codegen option: '+x)
 options=[i for i,x in enumerate(args) if 'enable-machine-outliner' in x]
 require(len(options)==1 and args[options[0]]=='-enable-machine-outliner=never' and options[0]>0 and args[options[0]-1]=='-mllvm','exact single outliner-never pair')
 for expected,group in (('-mlittle-endian',{'-mlittle-endian','-mbig-endian'}),('-fno-common',{'-fno-common','-fcommon'}),('-fno-PIE',{'-fno-PIE','-fPIE','-fpie','-fno-pie'}),('-mno-implicit-float',{'-mno-implicit-float','-mimplicit-float'}),('-fno-pic',{'-fno-pic','-fpic','-fPIC','-fno-PIC'}),('-mno-global-merge',{'-mno-global-merge','-mglobal-merge'})):
  require([x for x in args if x in group][-1:]==[expected],'effective actual baseline flag: '+expected)
 require([x for x in args if x.startswith('-march=')][-1:]==['-march=armv8-a+lse'] and [x for x in args if x.startswith(('-fstack-protector','-fno-stack-protector'))][-1:]==['-fno-stack-protector'],'architecture/protector effective options')
 require(args.index('-fno-inline-functions')>max(i for i,x in enumerate(args) if re.fullmatch('-O[0-3szg]',x)),'analysis noinline after optimization')
 return {'instrumented_actual_TU':True,'unchanged_production_Image_codegen':False,'KCFLAGS':INSTRUMENTATION}
def key(name,roots):
 p=PurePosixPath(name);require(p.is_absolute() and '..' not in p.parts,'canonical recorded absolute prerequisite')
 matches=[(label,PurePosixPath(root)) for label,root in roots.items() if p.is_relative_to(PurePosixPath(root))]
 require(len(matches)==1,'prerequisite root escape/ambiguity');label,root=matches[0];return label+'/'+p.relative_to(root).as_posix()
def capture(source,objects,compiler,proof):
 proof.mkdir(parents=True,exist_ok=True)
 # Preserve all available failure inputs BEFORE validating any compile output.
 for name in (TARGET,CMD,'.config','include/generated/autoconf.h','include/config/auto.conf','arch/arm64/mm/.tmp_init.su','arch/arm64/mm/init.su','arch/arm64/mm/.init.o.d'):
  p=objects/name
  if p.is_file():dest=proof/'kbuild'/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,dest)
 for name in KBUILD_FILES:
  p=source/name
  if p.is_file():dest=proof/'kbuild-source'/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,dest)
 command=(objects/CMD).read_text();ordinary,wildcard=parse_dependencies(command);primary=source_dependency(command,source)
 roots={'source':str(source.resolve()),'objects':str(objects.resolve()),'compiler-include':str(compiler.resolve())};files={};tokens={};absent=[]
 def retain(name,optional=False):
  p=Path(name);choices=[p] if p.is_absolute() else [objects/p,source/p];found=[p for p in choices if p.is_file()]
  if not found:require(optional,'missing actual prerequisite: '+name);absent.append(name);return
  p=found[0].resolve();n=key(p.as_posix(),roots);dest=proof/'dependency-files'/n;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,dest);files[n]=sha(dest);tokens[name]=n
 retain(primary)
 for name in ordinary:retain(name)
 for group in wildcard:
  for name in group:retain(name,True)
 for name in ('.config','include/generated/autoconf.h','include/config/auto.conf'):retain(str(objects/name))
 report={'roots':roots,'files_sha256':files,'tokens':tokens,'optional_absent':absent,'raw_d_captured':(objects/'arch/arm64/mm/.init.o.d').is_file(),'fixdep_cmd_is_not_raw_d':True,'primary':primary}
 write(proof/'dependencies.json',report);return report

def config_gate(config,enabled):
 actual={}
 for line in config.decode().splitlines():
  if line.startswith('CONFIG_') and '=' in line:k,v=line.split('=',1);require(k not in actual,'duplicate config');actual[k]=v
  elif re.fullmatch('# CONFIG_[A-Z0-9_]+ is not set',line):actual[line[2:-11]]='n'
 for k,v in config_settings(enabled).items():require(actual.get(k,'n')==v,'semantic config mismatch: '+k)
 require(actual.get('CONFIG_INITRAMFS_SOURCE')=='""' and 'rdinit=' not in actual.get('CONFIG_CMDLINE',''),'no historical packaging')
 return {'settings':config_settings(enabled),'raw_historical_config_reused':False,'config_sha256':digest(config)}
def verify_mode(proof,enabled,identifier):
 prepared=render(identifier);actual={p.relative_to(proof/'prepared-source').as_posix():p.read_bytes() for p in (proof/'prepared-source').rglob('*') if p.is_file()}
 require(actual==prepared,'exact full baseline plus reviewed insertions')
 config=(proof/'kbuild/.config').read_bytes();config_proof=config_gate(config,enabled)
 cmd=(proof/'kbuild'/CMD).read_text();origin=command_origin(cmd,config)
 tokens=re.findall(r'^cmd_[^\n]+ := (.*)$',cmd,re.M);require(len(tokens)==1,'unique actual command');args=shlex.split(tokens[0]);flags=validate_flags(args)
 obj=(proof/'kbuild'/TARGET).read_bytes();scripts={n:(proof/'kbuild-source'/n).read_bytes() for n in KBUILD_PINS}
 post=postprocess_provenance(config,scripts,obj,True);usage=proof/'kbuild'/origin['sidecar'];require(usage.is_file(),'compiler-output-derived actual stack sidecar')
 dependencies=json.loads((proof/'dependencies.json').read_text());ordinary,wildcard=parse_dependencies(cmd)
 expected_tokens={dependencies['primary'],*ordinary,*[n for group in wildcard for n in group],*map(lambda n:str(PurePosixPath(dependencies['roots']['objects'])/n),('.config','include/generated/autoconf.h','include/config/auto.conf'))}
 require(set(dependencies['tokens'])|set(dependencies['optional_absent'])==expected_tokens and not(set(dependencies['tokens'])&set(dependencies['optional_absent'])),'complete actual dependency expression')
 for token,n in dependencies['tokens'].items():
  p=PurePosixPath(token);candidates=[p] if p.is_absolute() else [PurePosixPath(dependencies['roots']['objects'])/p,PurePosixPath(dependencies['roots']['source'])/p]
  require(n in [key(str(c),dependencies['roots']) for c in candidates],'recorded dependency canonical path binding')
 for n,h in dependencies['files_sha256'].items():require(sha(proof/'dependency-files'/n)==h,'actual dependency bytes')
 for n,raw in prepared.items():
  if n.endswith(('Kconfig','runtime_relocation_trial.c','runtime_relocation_trial.h','pre_pm_trial_policy.h','pre_pm_trial_wrapper.c','kernel_trial_stack_oracle.c')) and (not enabled and ('trial' in n or 'oracle' in n)):continue
  if n.endswith('Kconfig'):continue
  require(dependencies['files_sha256'].get('source/'+n)==digest(raw),'complete actual custom TU prerequisites: '+n)
 require((proof/'dependency-files/objects/.config').read_bytes()==config,'config closure actual bytes')
 provider=provider_proof(config,(proof/'kbuild-source/crypto/Makefile').read_bytes(),(proof/'kbuild-source/crypto/sha256_generic.c').read_bytes(),(proof/'kbuild-source/include/crypto/sha.h').read_bytes())
 proof_object=object_proof(obj,(proof/'disassembly.log').read_text(),usage.read_text(),enabled)
 return {'provider_source_plan':provider,'config':config_proof,'command_origin':origin,'flags':flags,'postprocess':post,'object':proof_object,'dependencies_sha256':sha(proof/'dependencies.json')}
def archive_sources(archive,names):
 wanted={SOURCE_TOP+'/'+n:n for n in names};found={};total=0
 with tarfile.open(archive,'r|gz') as z:
  for entry in z:
   if entry.name not in wanted:continue
   require(entry.isfile() and entry.size<=8*1024*1024,'bounded stock source member')
   raw=z.extractfile(entry).read(entry.size+1);require(len(raw)==entry.size,'complete stock member');total+=len(raw);require(total<=128*1024*1024,'bounded full TU stock source closure');found[wanted[entry.name]]=raw
 require(set(found)==set(names),'all original stock source prerequisites retained');return found

def verify_bundle(root,payload):
 result=json.loads((root/'result.json').read_text());require(result['passed'] is True and result['wrapper_executed'] is False,'static-only producer result')
 require(len(payload)==19578880 and digest(payload)=='7a573eb6d2f5efc87bd5c85af130ea854eb4bad8370d17a4247e54f9593a836a','actual native payload')
 require(digest(payload+b'\0'*(0x22b0000-len(payload)))==PREFIX_SHA==result['prefix_sha256'],'fresh full staged-prefix digest')
 require(result['source_sha256']=={n:sha(ROOT/n) for n in import_closure()},'exact full import/source closure')
 require(sha(root/'kernel-source.tar.gz')==ARCHIVE_SHA,'pinned complete archive')
 overlay=render(result['build_id']);stock=set()
 for mode in ('disabled','enabled'):
  dep=json.loads((root/'evidence'/mode/'dependencies.json').read_text())
  stock|={n.removeprefix('source/') for n in dep['files_sha256'] if n.startswith('source/') and n.removeprefix('source/') not in overlay}
 stock.update(KBUILD_FILES);original=archive_sources(root/'kernel-source.tar.gz',stock)
 for mode in ('disabled','enabled'):
  proof=root/'evidence'/mode;dep=json.loads((proof/'dependencies.json').read_text())
  for n,h in dep['files_sha256'].items():
   if n.startswith('source/'):
    relative=n[7:];expected=overlay[relative] if relative in overlay else original[relative]
    require((proof/'dependency-files'/n).read_bytes()==expected,'real stock header/source or exact reviewed overlay')
  for n in KBUILD_FILES:require((proof/'kbuild-source'/n).read_bytes()==original[n],'real archive provider/API/Kbuild source')
 commands=json.loads((root/'commands.json').read_text())
 require(all(row['completed'] is True and row['returncode']==0 for row in commands),'all recorded actual producer commands completed')
 for mode in ('disabled','enabled'):
  selected=[row for row in commands if row['log']=='evidence/'+mode+'/03-init-object.log'];require(len(selected)==1,'actual unique object-only make')
  args=selected[0]['command'];require(args[0]=='make' and args[-1]==TARGET and args.count('KCFLAGS='+INSTRUMENTATION)==1,'actual recorded object target/analysis command')
 require(not any(any(x in ('Image','Image.gz','boot.img') for x in row['command']) for row in commands),'no Image/BOOT target')
 for name,h in result['source_sha256'].items():require(sha(root/'source'/name)==h,'retained full source bytes')
 for mode in ('disabled','enabled'):
  require(verify_mode(root/'evidence'/mode,mode=='enabled',result['build_id'])==result['modes'][mode],'independently recomputed actual TU proof')
 return {'static_full_TU_verified':True,'compiler_replayed':False,'emulator_replayed':False,'wrapper_executed':False,'physical_safety_proven':False}
def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--payload',type=Path,required=True);ap.add_argument('--output',type=Path,required=True);ap.add_argument('--archive',type=Path);ap.add_argument('--jobs',type=int,default=2);a=ap.parse_args()
 out=a.output.resolve();require(sys.platform=='linux' and 1<=a.jobs<=16 and not out.exists() and out.is_relative_to(ROOT/'note10/private'),'fresh Linux private output');out.mkdir(parents=True)
 commands=[];env=dict(os.environ,PLATFORM_VERSION='11',ANDROID_MAJOR_VERSION='r')
 def run(args,name):
  cmd=[str(x) for x in args];row={'command':cmd,'log':name,'completed':False};commands.append(row);write(out/'commands.json',commands);p=out/name;p.parent.mkdir(parents=True,exist_ok=True)
  with p.open('wb') as log:proc=subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT,env=env,timeout=1800)
  row.update(completed=True,returncode=proc.returncode);write(out/'commands.json',commands);require(proc.returncode==0,'actual command failed: '+name)
 try:
  require(all(sha(ROOT/n)==h for n,h in CORE_PINS.items()),'unchanged production4/ABI oracle')
  payload=a.payload.read_bytes();require(len(payload)==19578880 and digest(payload)=='7a573eb6d2f5efc87bd5c85af130ea854eb4bad8370d17a4247e54f9593a836a' and digest(payload+b'\0'*(0x22b0000-len(payload)))==PREFIX_SHA,'fresh exact payload and staged-prefix digest before Kbuild')
  source_map={n:sha(ROOT/n) for n in import_closure()}
  write(out/'source-manifest.json',source_map)
  for name in source_map:dest=out/'source'/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/name,dest)
  run([sys.executable,ROOT/'note10/device_test/test_pre_pm_trial.py','--output',out/'fixtures'],'fixtures.log')
  run([sys.executable,ROOT/'note10/device_test/test_pre_pm_provider.py','--output',out/'provider-fixtures/result.json'],'provider-fixtures.log')
  archive=out/'kernel-source.tar.gz'
  if a.archive:shutil.copyfile(a.archive,archive)
  else:acquire(archive)
  require(sha(archive)==ARCHIVE_SHA,'actual pinned kernel archive');tools={}
  for tool in ('clang-14','gcc','make','aarch64-linux-gnu-gcc','arm-linux-gnueabi-gcc','aarch64-linux-gnu-ld','llvm-objdump-14'):
   p=Path(shutil.which(tool) or '').resolve(strict=True);run([tool,'--version'],'toolchain/'+tool+'.log');tools[tool]={'path':str(p),'sha256':sha(p)}
  run(['clang-14','-print-file-name=include'],'toolchain/include.log');compiler=Path((out/'toolchain/include.log').read_text().strip()).resolve(strict=True)
  identifier=uuid.uuid4().hex;modes={}
  for mode in ('disabled','enabled'):
   source=extract(archive,out/'work'/mode/'source');objects=out/'work'/mode/'objects';objects.mkdir();proof=out/'evidence'/mode;proof.mkdir(parents=True)
   installed=install(source,identifier)
   for name in installed:dest=proof/'prepared-source'/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source/name,dest)
   make=['make','-C',source,'O='+str(objects),'ARCH=arm64','CC=clang-14','CROSS_COMPILE=aarch64-linux-gnu-','CLANG_TRIPLE=aarch64-linux-gnu-','CROSS_COMPILE_ARM32=arm-linux-gnueabi-','GCC_TOOLCHAIN_DIR=/usr/aarch64-linux-gnu/bin/','HOSTCC=gcc','HOSTCFLAGS=-Wno-error=deprecated-declarations','KCFLAGS='+INSTRUMENTATION]
   try:
    run([*make,DEFCONFIG],'evidence/'+mode+'/01-configure.log')
    for i,(k,v) in enumerate(config_settings(mode=='enabled').items()):
     action=['--enable',k[7:]] if v=='y' else ['--disable',k[7:]] if v=='n' else ['--set-str',k[7:],v[1:-1]] if v.startswith('"') else ['--set-val',k[7:],v]
     run([source/'scripts/config','--file',objects/'.config',*action],'evidence/'+mode+f'/settings/{i:03}.log')
    run([*make,'olddefconfig'],'evidence/'+mode+'/02-olddefconfig.log');run([*make,'V=1','-j'+str(a.jobs),TARGET],'evidence/'+mode+'/03-init-object.log')
   finally:
    try:capture(source,objects,compiler,proof)
    except Exception as capture_error:write(proof/'capture-failure.json',{'error':repr(capture_error),'accepted':False})
   run(['llvm-objdump-14','-d',objects/TARGET],'evidence/'+mode+'/disassembly.log');modes[mode]=verify_mode(proof,mode=='enabled',identifier)
  payload=a.payload.read_bytes();require(digest(payload+b'\0'*(0x22b0000-len(payload)))==PREFIX_SHA,'actual fresh staged prefix')
  result={'schema':1,'version':'v62','passed':True,'source_sha256':source_map,'kernel_commit':COMMIT,'kernel_archive_sha256':sha(archive),'build_id':identifier,'modes':modes,'prefix_sha256':PREFIX_SHA,'toolchain':tools,'ci_context':{k:os.environ.get(k) for k in ('GITHUB_RUN_ID','GITHUB_RUN_ATTEMPT','GITHUB_SHA','GITHUB_JOB')},'wrapper_executed':False,'whole_ci_accepted':False,'hardware_verified':False,'physical_memory_or_hardware_accessed':False,'full_Image_or_BOOT_built':False,'deployment_ready':False}
  result['files_sha256']={p.relative_to(out).as_posix():sha(p) for p in out.rglob('*') if p.is_file() and 'work' not in p.relative_to(out).parts};write(out/'result.json',result);write(out/'independent-verification.json',verify_bundle(out,payload))
 except Exception as error:write(out/'failure.json',{'error':repr(error),'accepted':False,'wrapper_executed':False,'ci_context':{k:os.environ.get(k) for k in ('GITHUB_RUN_ID','GITHUB_RUN_ATTEMPT','GITHUB_SHA','GITHUB_JOB')},'files_sha256':{p.relative_to(out).as_posix():sha(p) for p in out.rglob('*') if p.is_file() and 'work' not in p.relative_to(out).parts}});raise
if __name__=='__main__':main()
