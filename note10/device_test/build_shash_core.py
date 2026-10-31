"""One real Kbuild shash core object; static only, zero fixture commands."""
import argparse,ast,hashlib,json,os,re,shlex,shutil,subprocess,sys,tarfile
from pathlib import Path,PurePosixPath
sys.dont_write_bytecode=True
from build_xnu_runtime_plan_component import acquire,extract,parse_dependencies,COMMIT,ARCHIVE_SHA,SOURCE_TOP,DEFCONFIG
from pre_pm_archive_contract import PROFILE,ARCHIVE_BYTES,archive_identity,stable_archive,no_embedded_archive,match_prerequisite,require
from xnu_runtime_scratch_stack import postprocess_provenance,KBUILD_PINS
from sha256_provider_dependency import load_parser,WHEEL_SHA,WHEEL_BYTES
from shash_core_object import shash_object_proof
import shash_core_oracle as oracle_module
ROOT=Path(__file__).resolve().parents[2]
TARGET='crypto/shash.o'
SOURCE='crypto/shash.c'
CMD='crypto/.shash.o.cmd'
FLAGS='-gdwarf-4 -fstack-usage -ffunction-sections -fdata-sections -mllvm -enable-machine-outliner=never -fno-inline-functions'
PUBLIC=('note10/device_test/build_shash_core.py','note10/device_test/shash_core_object.py','note10/device_test/shash_core_dwarf.py','note10/device_test/shash_core_oracle.py','note10/device_test/shash_core_layout_oracle.c','note10/device_test/shash_core_instructions.py','note10/device_test/shash_core_registration_cfg.py','note10/device_test/test_shash_core_registration_cfg.py','note10/device_test/test_shash_core_scoped_input.py','note10/device_test/shash_core_clamped_cfg.py','note10/device_test/test_shash_core_clamped_cfg.py','note10/device_test/test_shash_core_observed_gpr.py','note10/device_test/stage_shash_core.py','note10/device_test/test_shash_core.py','.github/workflows/note10-shash-core.yml')
KBUILD_FILES=(*KBUILD_PINS,'scripts/basic/fixdep.c','scripts/config','Makefile','crypto/Makefile','crypto/Kconfig',SOURCE,'crypto/internal.h','include/crypto/hash.h','include/crypto/internal/hash.h','include/crypto/algapi.h','include/linux/crypto.h','arch/arm64/Makefile','arch/arm64/configs/'+DEFCONFIG)
SETTINGS={'CONFIG_CRYPTO':'y','CONFIG_CRYPTO_HASH':'y','CONFIG_CRYPTO_HASH2':'y','CONFIG_CRYPTO_ALGAPI':'y','CONFIG_CRYPTO_ALGAPI2':'y','CONFIG_ARM64_4K_PAGES':'y','CONFIG_MODVERSIONS':'y','CONFIG_DEBUG_INFO':'y','CONFIG_DEBUG_INFO_REDUCED':'n','CONFIG_DEBUG_INFO_SPLIT':'n','CONFIG_FTRACE_MCOUNT_RECORD':'n','CONFIG_STACK_VALIDATION':'n','CONFIG_LTO':'n','CONFIG_LTO_CLANG':'n','CONFIG_INITRAMFS_SOURCE':'""','CONFIG_LOCALVERSION':'"-v64-shash-static"','CONFIG_LOCALVERSION_AUTO':'n'}

def sha(path):
 h=hashlib.sha256()
 with path.open('rb') as f:
  for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
 return h.hexdigest()
def write(path,data):
 path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(data,indent=2,sort_keys=True)+'\n',encoding='utf8',newline='\n')
def sources():
 seen=set(PUBLIC)|{'note10/device_test/sha256_provider_requirements.txt'};todo=[n for n in PUBLIC if n.endswith('.py')]
 while todo:
  name=todo.pop();tree=ast.parse((ROOT/name).read_text());nodes=ast.walk(tree) if 'shash_core' in name else tree.body
  for node in nodes:
   mods=[node.module] if isinstance(node,ast.ImportFrom) else [x.name for x in node.names] if isinstance(node,ast.Import) else []
   for mod in mods:
    if mod:
     other='note10/device_test/'+mod.split('.')[0]+'.py'
     if (ROOT/other).is_file() and other not in seen:seen.add(other);todo.append(other)
 return sorted(seen)
def config_proof(raw):
 actual={}
 for line in raw.decode('ascii').splitlines():
  if line.startswith('CONFIG_') and '=' in line:k,v=line.split('=',1);require(k not in actual,'duplicate actual config');actual[k]=v
  elif re.fullmatch('# CONFIG_[A-Z0-9_]+ is not set',line):actual[line[2:-11]]='n'
 for name,value in SETTINGS.items():require(actual.get(name,'n')==value,'fresh actual shash configuration: '+name)
 return {'settings':dict(SETTINGS),'sha256':hashlib.sha256(raw).hexdigest(),'historical_raw_config_reused':False}

def command_origin(text,config,target=TARGET,source_name=SOURCE):
 prefix='cmd_'+target+' :=';lines=[line for line in text.splitlines() if line.startswith('cmd_')];require(len(lines)==1 and lines[0].startswith(prefix),'unique actual shash compiler assignment')
 stage=lines[0][len(prefix):].strip();require(stage and not any(c in stage for c in ';|&<>`$\r\n') and not stage.endswith('\\'),'single recorded actual compiler stage')
 args=shlex.split(stage);require(args[0] in ('clang-14','/usr/bin/clang-14') and args.count('-c')==1 and args.count('-o')==1 and '--target=aarch64-linux-gnu' in args and '-D__KERNEL__' in args and '-DMODULE' not in args,'actual builtin ARM64 Clang14 shash compilation')
 require(not any((x.startswith('-o') and x!='-o') or x.startswith(('--output','-fno-stack-usage','-stack-usage-file')) for x in args),'alternate object/stack outputs rejected')
 output=args[args.index('-o')+1];require(output==str(PurePosixPath(target).parent/('.tmp_'+PurePosixPath(target).name)),'actual compiler temporary output under MODVERSIONS=y')
 require(args[-1].endswith('/'+SOURCE_TOP+'/'+source_name) and PurePosixPath(args[-1]).is_absolute() and '..' not in PurePosixPath(args[-1]).parts,'exact original shash source')
 for flag in ('-fstack-usage','-ffunction-sections','-fdata-sections','-fno-inline-functions'):require(args.count(flag)==1,'actual analysis option: '+flag)
 positions=[i for i,x in enumerate(args) if 'enable-machine-outliner' in x];require(len(positions)==1 and args[positions[0]-1:positions[0]+1]==['-mllvm','-enable-machine-outliner=never'],'exact unique outliner-never pair')
 require(not any(x.startswith('-flto') or x in ('-finline-functions','-finline-hint-functions') for x in args),'no conflicting LTO/inlining')
 require([x for x in args if x.startswith('-gdwarf-')][-1:]==['-gdwarf-4'] and [x for x in args if re.fullmatch('-O[0-3szg]',x)][-1:]==['-Oz'],'actual DWARF4 and retained effective optimization')
 require('-mno-implicit-float' in args and args.index('-fno-inline-functions')>max(i for i,x in enumerate(args) if re.fullmatch('-O[0-3szg]',x)),'actual scalar/noinline analysis ordering')
 stem=PurePosixPath(target).stem.replace('-','_')
 for macro in ('KBUILD_BASENAME','KBUILD_MODNAME'):
  value='crypto_hash' if target==TARGET and macro=='KBUILD_MODNAME' else stem
  require([x for x in args if x.startswith('-D'+macro+'=')]==['-D'+macro+'=\"'+value+'\"'],'exact source/Makefile-bound Kbuild macro: '+macro)
 config_proof(config)
 return {'args':args,'compiler_output':output,'sidecar':str(PurePosixPath(output).with_suffix('.su')),'source':args[-1],'raw_compiler_temporary_object_identity_claimed':False,'stage_sha256':hashlib.sha256(stage.encode()).hexdigest()}

def key(path,roots):
 p=PurePosixPath(path);require(p.is_absolute() and '..' not in p.parts,'canonical absolute recorded prerequisite');found=[(n,PurePosixPath(r)) for n,r in roots.items() if p.is_relative_to(PurePosixPath(r))];require(len(found)==1,'unambiguous actual prerequisite roots');n,r=found[0];return n+'/'+p.relative_to(r).as_posix()
def capture(source,objects,compiler,out,target=TARGET,source_name=SOURCE,cmd_name=CMD,evidence='evidence'):
 proof=out/evidence;proof.mkdir(parents=True,exist_ok=True)
 stem=PurePosixPath(target).stem;parent=PurePosixPath(target).parent
 raw_d=str(parent/('.'+stem+'.o.d'))
 for name in (target,cmd_name,'.config','include/generated/autoconf.h','include/config/auto.conf',str(parent/('.tmp_'+stem+'.su')),str(parent/(stem+'.su')),raw_d):
  p=objects/name
  if p.is_file():dest=proof/'kbuild'/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,dest)
 for name in (*KBUILD_FILES,*((source_name,) if source_name==oracle_module.SOURCE else ())):
  p=source/name
  if p.is_file():dest=proof/'stock-source'/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,dest)
 text=(objects/cmd_name).read_text();ordinary,wildcard=parse_dependencies(text);source_rows=re.findall(r'^source_'+re.escape(target)+r'\s*:=\s*(.*)$',text,re.M);require(len(source_rows)==1,'actual fixdep primary shash source')
 roots={'source':source.resolve().as_posix(),'objects':objects.resolve().as_posix(),'compiler-include':compiler.resolve().as_posix()};files={};tokens={};absent=[]
 def retain(token,optional=False):
  p=Path(token);found=[p] if p.is_absolute() else [objects/p,source/p];found=[p for p in found if p.is_file()]
  if not found:require(optional,'actual nonoptional prerequisite missing: '+token);absent.append(token);return
  p=found[0].resolve();name=key(p.as_posix(),roots);dest=proof/'dependency-files'/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,dest);files[name]=sha(dest);tokens[token]=name
 retain(source_rows[0])
 for token in ordinary:retain(token)
 for group in wildcard:
  for token in group:retain(token,True)
 for name in ('.config','include/generated/autoconf.h','include/config/auto.conf'):retain(str(objects/name))
 report={'roots':roots,'primary':source_rows[0],'files_sha256':files,'token_to_key':tokens,'optional_absent':absent,'raw_compiler_d_captured':(objects/raw_d).is_file(),'stack_sidecars_observed':{n:(objects/n).is_file() for n in (str(parent/('.tmp_'+stem+'.su')),str(parent/(stem+'.su')))},'fixdep_cmd_is_not_raw_d':True}
 write(proof/'dependencies.json',report);return report

def stock_bytes(archive,names):
 wanted={SOURCE_TOP+'/'+n:n for n in names};found={};total=0
 with tarfile.open(archive,'r|gz') as z:
  for item in z:
   if item.name not in wanted:continue
   require(item.isfile() and item.size<=8*1024*1024,'bounded actual archive prerequisite');raw=z.extractfile(item).read(item.size+1);require(len(raw)==item.size,'complete member');total+=len(raw);require(total<=128*1024*1024,'bounded actual source closure');found[wanted[item.name]]=raw
 require(set(found)==set(names),'actual stock prerequisite absent: '+repr(sorted(set(names)-set(found))));return found


def verify_evidence(proof,archive,target=TARGET,source_name=SOURCE,cmd_name=CMD):
 dep=json.loads((proof/'dependencies.json').read_text());cmd=(proof/'kbuild'/cmd_name).read_text();config=(proof/'kbuild/.config').read_bytes();origin=command_origin(cmd,config,target,source_name);ordinary,wildcard=parse_dependencies(cmd)
 primary_rows=re.findall(r'^source_'+re.escape(target)+r'\s*:=\s*(.*)$',cmd,re.M);require(primary_rows==[dep['primary']] and dep['primary']==origin['source'],'actual fixdep/compiler primary source equality')
 require(len(re.findall(r'^deps_'+re.escape(target)+r'\s*:=',cmd,re.M))==1,'exact actual shash dependency target')
 expected_tokens={dep['primary'],*ordinary,*[n for group in wildcard for n in group],*[str(PurePosixPath(dep['roots']['objects'])/n) for n in ('.config','include/generated/autoconf.h','include/config/auto.conf')]}
 require(set(dep['token_to_key'])|set(dep['optional_absent'])==expected_tokens and not(set(dep['token_to_key'])&set(dep['optional_absent'])),'complete exact actual dependency expression')
 require(set(dep['optional_absent'])<={n for group in wildcard for n in group} and set(ordinary)|{dep['primary']}<=set(dep['token_to_key']),'nonoptional prerequisites never marked absent')
 require(set(dep['files_sha256'])==set(dep['token_to_key'].values()),'exact retained prerequisite inventory')
 for token,name in dep['token_to_key'].items():
  p=PurePosixPath(token);candidates=[p] if p.is_absolute() else [PurePosixPath(dep['roots']['objects'])/p,PurePosixPath(dep['roots']['source'])/p];require(name in [key(str(p),dep['roots']) for p in candidates],'actual lexical dependency binding')
 for name,v in dep['files_sha256'].items():require(sha(proof/'dependency-files'/name)==v,'every retained prerequisite byte')
 required={'source/'+source_name,'objects/.config','objects/include/generated/autoconf.h','objects/include/config/auto.conf'};require(required<=set(dep['files_sha256']),'actual source/config/generated closure')
 require((proof/'dependency-files/objects/.config').read_bytes()==config,'actual config bytes closure')
 stock={n[7:] for n in dep['files_sha256'] if n.startswith('source/')}|set(KBUILD_FILES);require(source_name==oracle_module.SOURCE or 'source/'+oracle_module.SOURCE not in dep['files_sha256'],'oracle overlay belongs only to separate oracle target');stock.discard(oracle_module.SOURCE);original=stock_bytes(archive,stock)
 if source_name==oracle_module.SOURCE:
  require((proof/'dependency-files/source'/source_name).read_bytes()==(proof/'stock-source'/source_name).read_bytes()==(ROOT/oracle_module.PUBLIC_SOURCE).read_bytes(),'exact public defining-header oracle source overlay')
 for name in stock:
  if 'source/'+name in dep['files_sha256']:match_prerequisite(name,(proof/'dependency-files/source'/name).read_bytes(),original[name])
 for name in KBUILD_FILES:match_prerequisite(name,(proof/'stock-source'/name).read_bytes(),original[name])
 scripts={name:original[name] for name in KBUILD_PINS};obj=(proof/'kbuild'/target).read_bytes();post=postprocess_provenance(config,scripts,obj,True)
 return dep,origin,original,config,obj,post


def same_build(dep,origin,other,other_origin,config,other_config):
 require(config==other_config and dep['roots']==other['roots'],'same actual source/build/config/compiler resource roots')
 def normalized(args):
  result=[];skip=False
  for value in args:
   if skip:skip=False;continue
   if value=='-o':skip=True;result+=['-o','<target>'];continue
   if value.startswith(('-DKBUILD_BASENAME=','-DKBUILD_MODNAME=')):continue
   if value==args[-1]:result.append('<source>')
   elif value.startswith('-Wp,-MD,'):result.append('-Wp,-MD,<target>')
   else:result.append(value)
  return result
 require(normalized(origin['args'])==normalized(other_origin['args']),'same actual Kbuild compiler/ABI/instrumentation flags; only source/target macro names differ')
 shared=set(dep['files_sha256'])&set(other['files_sha256'])
 for name in shared:require(dep['files_sha256'][name]==other['files_sha256'][name],'same defining header/config/tool prerequisite bytes')
 require({'source/include/crypto/hash.h','source/include/crypto/algapi.h','source/include/linux/crypto.h'}<=shared,'same real defining header closure')

def verify_shash_bundle(root,archive,site,wheel):
 result=json.loads((root/'result.json').read_text());snapshot=archive_identity(archive);require(result['passed'] is True and result['version']=='v64' and result['archive_profile']==PROFILE and result['kernel_commit']==COMMIT and result['kernel_archive_sha256']==ARCHIVE_SHA,'exact new external shash contract')
 require(not Path(archive).absolute().is_relative_to(root.absolute()),'independent protected input outside artifact');no_embedded_archive({n:{'bytes':(root/n).stat().st_size,'sha256':v} for n,v in result['files_sha256'].items()})
 expected={n:sha(ROOT/n) for n in sources()};require(result['source_sha256']==expected,'full new/imported source closure')
 for n,v in expected.items():require(sha(root/'source'/n)==v,'retained exact new/shared source')
 proof=root/'evidence';dep,origin,original,config,obj,post=verify_evidence(proof,archive)
 oracle_root=root/'oracle-evidence';odep,oorigin,ooriginal,ocfg,oobj,opost=verify_evidence(oracle_root,archive,oracle_module.TARGET,oracle_module.SOURCE,oracle_module.CMD)
 same_build(dep,origin,odep,oorigin,config,ocfg)
 oracle=oracle_module.parse_oracle(oobj)
 ELFFile,dependency=load_parser(site,wheel);require(dependency==result['parser_dependency']==json.loads((root/'parser-input.json').read_text()),'actual pinned parser input and runtime')
 install=json.loads((root/'dependencies/install-report.json').read_text());require(len(install['install'])==1 and install['install'][0]['metadata']['name']=='pyelftools' and install['install'][0]['metadata']['version']=='0.32' and install['install'][0]['download_info']['archive_info']['hashes']['sha256']==WHEEL_SHA,'actual pinned parser installation report')
 contract=json.loads((root/'archive-contract.json').read_text());require(contract['profile']==PROFILE and contract['sha256']==ARCHIVE_SHA and contract['bytes']==ARCHIVE_BYTES and contract['before']==contract['after'] and contract['complete_hash_before_compile'] is True,'external complete input stability')
 report=shash_object_proof(obj,(proof/'disassembly.log').read_text(),(proof/'kbuild'/origin['sidecar']).read_text(),ELFFile,{n:original[n] for n in KBUILD_FILES},oracle,config)
 require(result['proof']==report and result['command_origin']==origin and result['postprocess_provenance']==post and result['oracle']==oracle and result['oracle_command_origin']==oorigin and result['oracle_postprocess_provenance']==opost,'independently recomputed new shash facts')
 commands=json.loads((root/'commands.json').read_text());require(all(r['completed'] and r['returncode']==0 for r in commands),'all actual shash commands completed')
 require(not any(any(PurePosixPath(x).name.startswith('test_') or x in ('arch/arm64/mm/init.o','Image','boot.img') for x in r['command']) for r in commands),'zero prior/new fixture commands and no old/image target')
 builds=[r for r in commands if r['log']=='build/03-shash-object.log'];require(len(builds)==1 and builds[0]['command'][-2:]==[TARGET,oracle_module.TARGET] and builds[0]['command'].count('KCFLAGS='+FLAGS)==1,'one exact real shash target/analysis flags')
 stable_archive(archive,snapshot)
 return {'shash_object_static_verified':True,'compiler_or_shash_execution_replayed':False,'runtime_availability_proven':False,'physical_safety_proven':False}

def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--output',type=Path,required=True);ap.add_argument('--archive-profile',choices=[PROFILE],required=True);ap.add_argument('--archive',type=Path);ap.add_argument('--elftools-site',type=Path,required=True);ap.add_argument('--elftools-wheel',type=Path,required=True);ap.add_argument('--install-report',type=Path,required=True);ap.add_argument('--jobs',type=int,default=2);a=ap.parse_args()
 out=a.output.absolute();require(sys.platform=='linux' and not out.exists() and out.is_relative_to(ROOT/'note10/private') and 1<=a.jobs<=16,'fresh bounded Linux shash output');out.mkdir(parents=True)
 env=dict(os.environ,PLATFORM_VERSION='11',ANDROID_MAJOR_VERSION='r');commands=[]
 def run(args,name):
  row={'command':[str(x) for x in args],'log':name,'completed':False};commands.append(row);write(out/'commands.json',commands);path=out/name;path.parent.mkdir(parents=True,exist_ok=True)
  with path.open('wb') as log:process=subprocess.run(row['command'],stdout=log,stderr=subprocess.STDOUT,env=env,timeout=1800)
  row.update(completed=True,returncode=process.returncode);write(out/'commands.json',commands);require(process.returncode==0,'new target command failed: '+name)
 try:
  require(sha(ROOT/'note10/device_test/pre_pm_archive_contract.py')=='966a5b032e516ecc984defc9b0313192667d4f4585511fa232966ce79ac3b5c5','immutable accepted external archive helper')
  source_map={n:sha(ROOT/n) for n in sources()}
  for name in source_map:dest=out/'source'/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/name,dest)
  write(out/'source-manifest.json',source_map);ELFFile,parser=load_parser(a.elftools_site,a.elftools_wheel)
  write(out/'parser-input.json',parser)
  dependency=out/'dependencies';dependency.mkdir();wheel=dependency/'pyelftools-0.32-py3-none-any.whl';shutil.copyfile(a.elftools_wheel,wheel);shutil.copyfile(a.install_report,dependency/'install-report.json')
  archive=a.archive.absolute() if a.archive else out.parent/'v64-kernel-source-input.tar.gz';require(not archive.is_relative_to(out),'external archive outside uploaded root')
  if not a.archive:acquire(archive)
  before=archive_identity(archive);write(out/'archive-contract.json',{'profile':PROFILE,'sha256':ARCHIVE_SHA,'bytes':ARCHIVE_BYTES,'before':before,'complete_hash_before_compile':True})
  tools={}
  for tool in ('clang-14','gcc','make','aarch64-linux-gnu-gcc','arm-linux-gnueabi-gcc','aarch64-linux-gnu-ld','llvm-objdump-14'):
   path=Path(shutil.which(tool) or '').resolve(strict=True);run([tool,'--version'],'tools/'+tool+'.log');tools[tool]={'path':str(path),'sha256':sha(path)}
  write(out/'toolchain.json',tools)
  run(['clang-14','-print-file-name=include'],'tools/include.log');compiler=Path((out/'tools/include.log').read_text().strip()).resolve(strict=True)
  workspace=out.parent/(out.name+'-workspace');require(not workspace.exists(),'fresh build workspace outside artifact');workspace.mkdir();source=extract(archive,workspace/'source');objects=workspace/'objects';objects.mkdir();
  shutil.copyfile(ROOT/oracle_module.PUBLIC_SOURCE,source/oracle_module.SOURCE)
  make=['make','-C',source,'O='+str(objects),'ARCH=arm64','CC=clang-14','CROSS_COMPILE=aarch64-linux-gnu-','CLANG_TRIPLE=aarch64-linux-gnu-','CROSS_COMPILE_ARM32=arm-linux-gnueabi-','GCC_TOOLCHAIN_DIR=/usr/aarch64-linux-gnu/bin/','HOSTCC=gcc','HOSTCFLAGS=-Wno-error=deprecated-declarations','KCFLAGS='+FLAGS]
  try:
   run([*make,DEFCONFIG],'build/01-defconfig.log')
   for i,(name,value) in enumerate(SETTINGS.items()):
    action=['--enable',name[7:]] if value=='y' else ['--disable',name[7:]] if value=='n' else ['--set-str',name[7:],value[1:-1]]
    run([source/'scripts/config','--file',objects/'.config',*action],f'build/settings/{i:03}.log')
   run([*make,'olddefconfig'],'build/02-olddefconfig.log');run([*make,'V=1','-j'+str(a.jobs),TARGET,oracle_module.TARGET],'build/03-shash-object.log')
  finally:
   failures=[]
   for target,source_name,cmd_name,evidence in ((TARGET,SOURCE,CMD,'evidence'),(oracle_module.TARGET,oracle_module.SOURCE,oracle_module.CMD,'oracle-evidence')):
    try:capture(source,objects,compiler,out,target,source_name,cmd_name,evidence)
    except Exception as error:failures.append({'target':target,'error':repr(error)})
   if failures:write(out/'capture-failure.json',{'errors':failures,'accepted':False})
  run(['llvm-objdump-14','-d',objects/TARGET],'evidence/disassembly.log');proofroot=out/'evidence';cfg=(objects/'.config').read_bytes();origin=command_origin((objects/CMD).read_text(),cfg)
  obj=(objects/TARGET).read_bytes();post=postprocess_provenance(cfg,{n:(source/n).read_bytes() for n in KBUILD_PINS},obj,True)
  odep,oorigin,ooriginal,ocfg,oobj,opost=verify_evidence(out/'oracle-evidence',archive,oracle_module.TARGET,oracle_module.SOURCE,oracle_module.CMD)
  dep=json.loads((proofroot/'dependencies.json').read_text());same_build(dep,origin,odep,oorigin,cfg,ocfg);oracle=oracle_module.parse_oracle(oobj)
  report=shash_object_proof(obj,(proofroot/'disassembly.log').read_text(),(objects/origin['sidecar']).read_text(),ELFFile,{n:(source/n).read_bytes() for n in KBUILD_FILES},oracle,cfg)
  after=stable_archive(archive,before);write(out/'archive-contract.json',{'profile':PROFILE,'sha256':ARCHIVE_SHA,'bytes':ARCHIVE_BYTES,'before':before,'after':after,'complete_hash_before_compile':True})
  result={'schema':1,'version':'v64','passed':True,'archive_profile':PROFILE,'kernel_commit':COMMIT,'kernel_archive_sha256':ARCHIVE_SHA,'kernel_archive_bytes':ARCHIVE_BYTES,'source_sha256':source_map,'command_origin':origin,'postprocess_provenance':post,'oracle':oracle,'oracle_command_origin':oorigin,'oracle_postprocess_provenance':opost,'parser_dependency':parser,'toolchain':tools,'proof':report,'executed_fixture_commands':0,'shash_executed':False,'Image_or_BOOT_built':False,'runtime_shash_availability_proven':False,'ci_context':{k:os.environ.get(k) for k in ('GITHUB_RUN_ID','GITHUB_RUN_ATTEMPT','GITHUB_SHA','GITHUB_JOB')}}
  result['files_sha256']={p.relative_to(out).as_posix():sha(p) for p in out.rglob('*') if p.is_file() and 'work' not in p.relative_to(out).parts};write(out/'result.json',result);write(out/'independent-verification.json',verify_shash_bundle(out,archive,a.elftools_site,wheel))
 except Exception as error:write(out/'failure.json',{'error':repr(error),'accepted':False,'shash_executed':False,'files_sha256':{p.relative_to(out).as_posix():sha(p) for p in out.rglob('*') if p.is_file() and 'work' not in p.relative_to(out).parts}});raise
if __name__=='__main__':main()
