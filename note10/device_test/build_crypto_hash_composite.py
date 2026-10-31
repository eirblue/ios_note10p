"""One new actual Kbuild composite, selected byte/link origin only; no fixtures."""
import argparse,hashlib,json,os,re,shlex,shutil,subprocess,sys,tarfile,time,urllib.request
from pathlib import Path
sys.dont_write_bytecode=True
from crypto_hash_composite import parse_object,link_origin,require,digest
from crypto_hash_input_contract import KERNEL_COMMIT,KERNEL_SHA,KERNEL_BYTES,SOURCE_TOP,CAP,BASELINE_ROOT,NEW_ROOT,write,protected,stable,separate,disk_budget,tree_inventory,extract_kernel,extract_zip,verify_extraction,retrieve_baseline,baseline_labels,baseline_api_receipt,prerequisite_capture,leaf_equality,normalized,command_line,composite_command,config_contract

ROOT=Path(__file__).resolve().parents[2]
PUBLIC=('note10/device_test/build_crypto_hash_composite.py','note10/device_test/crypto_hash_composite.py','note10/device_test/crypto_hash_input_contract.py','note10/device_test/stage_crypto_hash_composite.py','note10/device_test/test_crypto_hash_composite.py','.github/workflows/note10-crypto-hash-composite.yml')
FLAGS='-gdwarf-4 -fstack-usage -ffunction-sections -fdata-sections -mllvm -enable-machine-outliner=never -fno-inline-functions'
TARGET='crypto/crypto_hash.o'


def sources():return {name:digest((ROOT/name).read_bytes()) for name in PUBLIC}


def make_command(source,objects):
 return ['make','-C',str(source),'O='+str(objects),'ARCH=arm64','CC=clang-14','LD=aarch64-linux-gnu-ld','CROSS_COMPILE=aarch64-linux-gnu-','CLANG_TRIPLE=aarch64-linux-gnu-','CROSS_COMPILE_ARM32=arm-linux-gnueabi-','GCC_TOOLCHAIN_DIR=/usr/aarch64-linux-gnu/bin/','HOSTCC=gcc','HOSTCFLAGS=-Wno-error=deprecated-declarations','KCFLAGS='+FLAGS,'CONFIG_THIN_ARCHIVES=','LDFLAGS=-m aarch64linux --no-relax','V=1','-j2',TARGET]


def build_output_size(objects,source):
 total=0;links=[];objects=Path(objects);source=Path(source).resolve()
 for parent,dirs,files in os.walk(objects,followlinks=False):
  for name in dirs+files:
   path=Path(parent)/name
   if path.is_symlink():require(path==objects/'source' and path.resolve()==source,'only pinned normal Kbuild output/source alias');links.append(path.relative_to(objects).as_posix());continue
   require(not getattr(path.lstat(),'st_file_attributes',0)&1024,'no unexpected output reparse')
   if path.is_file():total+=path.stat().st_size;require(total<=512*1024*1024,'complete actual build-output cap')
 return {'regular_bytes':total,'normal_source_aliases':links,'cap':512*1024*1024}


def ahash_profile(shash,ahash):
 require(shash['roots']==ahash['roots'],'both actual leafs share the same fresh source/output/compiler roots')
 for name in ('objects/.config','objects/include/generated/autoconf.h','objects/include/config/auto.conf'):require(shash['files_sha256'][name]==ahash['files_sha256'][name],'both leafs use identical actual generated/config bytes')
 args=[x.replace('crypto/.ahash.o.d','crypto/.shash.o.d').replace('crypto/.tmp_ahash.o','crypto/.tmp_shash.o').replace('crypto/ahash.c','crypto/shash.c').replace('KBUILD_BASENAME="ahash"','KBUILD_BASENAME="shash"') for x in ahash['actual_CC_argv']];require(normalized(args,ahash['roots'])==normalized(shash['actual_CC_argv'],shash['roots']),'new ahash shares actual compiler/config/profile, no semantic claim')


def archive_prerequisites(archive,reports,root):
 wanted={}
 for report in reports:
  for name,sha in report['files_sha256'].items():
   if name.startswith('source/'):
    key=SOURCE_TOP+'/'+name[len('source/'):];require(key not in wanted or wanted[key]==sha,'same stock source prerequisite across leafs');wanted[key]=sha
 for name in ('scripts/Makefile.build','scripts/Makefile.lib','scripts/Kbuild.include','crypto/Makefile','Makefile'):wanted[SOURCE_TOP+'/'+name]=digest((Path(root)/'evidence/stock-source'/name).read_bytes())
 with tarfile.open(archive,'r:gz') as bundle:
  found={};total=0
  for member in bundle.getmembers():
   if member.name not in wanted:continue
   require(member.name not in found and member.isfile() and member.size<=8*1024*1024,'unique actual stock prerequisite member');raw=bundle.extractfile(member).read(member.size+1);total+=len(raw);require(len(raw)==member.size and total<=CAP and digest(raw)==wanted[member.name],'actual new source prerequisite bytes equal protected stock archive');found[member.name]=True
 require(set(found)==set(wanted),'all actual new source/recipe prerequisites in protected archive')


def postprocess_commands(log,linker):
 result={}
 for line in log.splitlines():
  if 'aarch64-linux-gnu-ld ' not in line and linker['path']+' ' not in line:continue
  lexer=shlex.shlex(line,posix=True,punctuation_chars=';|&<>');lexer.whitespace_split=True;tokens=list(lexer)
  for i,token in enumerate(tokens):
   if token not in ('aarch64-linux-gnu-ld',linker['path']):continue
   end=next((j for j in range(i+1,len(tokens)) if tokens[j] in (';','&&','||','|','>','<')),len(tokens));args=tokens[i:end]
   if '-o' not in args:continue
   target=args[args.index('-o')+1]
   if target not in ('crypto/shash.o','crypto/ahash.o',TARGET):continue
   require(target not in result,'one expanded actual selected link/postprocess recipe')
   if target==TARGET:composite_command(args,linker)
   else:
    stem=Path(target).stem;require(args[1:]==['-m','aarch64linux','--no-relax','-r','-o',target,'crypto/.tmp_'+stem+'.o','-T','crypto/.tmp_'+stem+'.ver'],'only declared GNU leaf postprocess option delta and exact temp/version-script references')
   result[target]={'args':args,'expanded_Kbuild_recipe_line':line,'conditional_branch_execution_observed':False}
 require(set(result)=={'crypto/shash.o','crypto/ahash.o',TARGET},'all actual expanded selected link/postprocess provenance retained');return result


def preserve_failure_files(out,workspace,baseline_input):
 retained=[];total=0;objects=Path(workspace)/'objects'
 candidates=[(objects/'crypto'/name,Path('evidence/crypto')/name) for name in ('shash.o','ahash.o','crypto_hash.o','.shash.o.cmd','.ahash.o.cmd','.crypto_hash.o.cmd','.tmp_shash.o','.tmp_ahash.o','.tmp_shash.ver','.tmp_ahash.ver')]
 candidates += [(objects/name,Path('failure-config')/name) for name in ('.config','include/generated/autoconf.h','include/config/auto.conf')]
 candidates += [(Path(baseline_input)/name,Path('baseline-api')/name) for name in ('run.json','jobs.json','artifacts.json','artifact.json','job-log.log','AUTHENTICATED-API-RETRIEVAL-RECEIPT.json')]
 for source,name in candidates:
  if not source.is_file() or source.is_symlink():continue
  total+=source.stat().st_size;require(total<=CAP,'bounded forensic-only new evidence copy');target=Path(out)/name
  if not target.exists():target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,target)
  retained.append(str(name))
 return retained


def verify_bundle(root,kernel,baseline_zip,baseline_extraction,pins):
 root=Path(root);result=json.loads((root/'result.json').read_text());require(result['passed'] is True and result['version']=='v65' and result['executed_fixture_commands']==0,'new successful producer and zero fixture invocations')
 expected=sources();require(result['source_sha256']==expected,'exact complete new public source closure')
 for name,sha in expected.items():require(digest((root/'source'/name).read_bytes())==sha,'actual uploaded new source byte closure')
 inventory=tree_inventory(root);require(set(inventory)==set(result['files'])|{'result.json'} and all(inventory[k]==v for k,v in result['files'].items()),'complete new evidence namespace, no extra/missing file')
 kernel_record=protected(kernel,'kernel-source-v1',KERNEL_BYTES,KERNEL_SHA);baseline_record=protected(baseline_zip,'accepted-v64-baseline-ZIP-v1',pins['zip_bytes'],pins['zip_sha256']);separate([kernel,baseline_zip,baseline_extraction,root],[kernel_record['file_identity'],baseline_record['file_identity']]);verify_extraction(baseline_zip,baseline_extraction,BASELINE_ROOT,pins['ordinary_members'],pins['expanded_bytes']);oldroot=Path(baseline_extraction)/BASELINE_ROOT;old=baseline_labels(oldroot,pins)
 api_dir=root/'baseline-api';from crypto_hash_input_contract import api_validate
 baseline_api_receipt(api_dir,pins);api_validate(pins,*[json.loads((api_dir/(name+'.json')).read_text()) for name in ('run','jobs','artifacts','artifact')])
 for leaf in ('shash','ahash'):
  report=json.loads((root/'evidence'/leaf/'prerequisites.json').read_text());actual=tree_inventory(root/'evidence'/leaf/'dependency-files');require(set(actual)==set(report['files_sha256']) and all(actual[k]['sha256']==v for k,v in report['files_sha256'].items()),'complete uploaded actual leaf prerequisites')
 shash=json.loads((root/'evidence/shash/prerequisites.json').read_text());ahash=json.loads((root/'evidence/ahash/prerequisites.json').read_text());olddeps=json.loads((oldroot/'evidence/dependencies.json').read_text());equality=leaf_equality(old,olddeps,shash);require(equality==result['shash_input_equality'],'independent new shash input/argv equality');ahash_profile(shash,ahash);require((root/'tools/compiler-resource.log').read_text().strip()==shash['roots']['compiler-include'],'actual compiler resource probe binds captured prerequisite root')
 config=(root/'evidence/shash/dependency-files/objects/.config').read_bytes();config_contract(config);require(config==(oldroot/'evidence/dependency-files/objects/.config').read_bytes(),'exact baseline .config')
 cmd=(root/'evidence/crypto/.crypto_hash.o.cmd').read_text();composite_command(command_line(cmd,TARGET),result['linker'])
 post=postprocess_commands((root/'build/composite.log').read_text(),result['linker']);require(post==result['normal_leaf_postprocess']['expanded_selected_link_commands'],'independent actual full selected link/postprocess command binding')
 for leaf in ('shash','ahash'):
  report=json.loads((root/'evidence'/leaf/'prerequisites.json').read_text());cmd=(root/'evidence/crypto'/('.'+leaf+'.o.cmd')).read_text();require(command_line(cmd,'crypto/'+leaf+'.o')==report['actual_CC_argv'] and digest(cmd.encode())==report['actual_cmd_sha256'],'actual uploaded saved leaf command binds captured CC argv')
 for name in ('scripts/Makefile.build','scripts/Makefile.lib','scripts/Kbuild.include','crypto/Makefile','Makefile'):require((root/'evidence/stock-source'/name).read_bytes()==(oldroot/'evidence/stock-source'/name).read_bytes(),'unchanged accepted pinned Kbuild recipe bytes')
 make=result['composite_make_command'];require(make==make_command(shash['roots']['source'],shash['roots']['objects']),'exact declared actual Kbuild argv, one target and allowed overrides only');commands=json.loads((root/'commands.json').read_text());require(len(commands)==4 and sum(c['command']==make for c in commands)==1 and sum(c['command'][0]=='make' for c in commands)==1,'exactly one actual composite invocation and three tool probes')
 for row in commands:require(row['completed'] is True and row['returncode']==0 and digest((root/row['log']).read_bytes())==row['log_sha256'] and type(row['start_ns']) is int and row['start_ns']<=row['end_ns'],'complete actual command/log/time receipts')
 build=next(c for c in commands if c['command']==make);fresh=result['build_freshness'];require(fresh['output_files_before']==['.config'] and all(build['start_ns']<=fresh['object_mtime_ns'][n]<=build['end_ns'] for n in ('shash.o','ahash.o','crypto_hash.o')),'fresh leaf/composite origins produced by the one recorded Kbuild invocation');archive_prerequisites(kernel,[json.loads((root/'evidence'/leaf/'prerequisites.json').read_text()) for leaf in ('shash','ahash')],root)
 require(result['config_packaging']==config_contract(config),'honest source/effective packaging split')
 before=result['protected_inputs_before'];after=result['protected_inputs_after'];require(before==after and len(before)==2 and {r['profile'] for r in before}=={'kernel-source-v1','accepted-v64-baseline-ZIP-v1'} and all(len(r['file_identity'])==5 and all(type(n) is int for n in r['file_identity']) for r in before),'producer-local dual full-hash/five-stat stability, no cross-host numeric comparison');expected_inputs={r['profile']:(r['bytes'],r['sha256']) for r in (kernel_record,baseline_record)};require(all((r['bytes'],r['sha256'])==expected_inputs[r['profile']] for r in before),'producer inputs equal both independently protected parent digests/sizes');require(result['baseline_pins']==pins and result['baseline_original_producer_result_sha256']==digest((oldroot/'result.json').read_bytes()),'exact accepted baseline labels, source/context and input pins')
 for tool,key in (('clang-14','compiler'),('aarch64-linux-gnu-ld','linker')):require(result[key]['sha256']==old['toolchain'][tool]['sha256'],'same accepted compiler/GNU linker binary identity')
 require(result['compiler']['version']==(root/'tools/clang-version.log').read_text() and result['linker']['version']==(root/'tools/linker-version.log').read_text(),'full actual compiler/GNU version outputs retained exactly')
 raw=[(oldroot/'evidence/kbuild/crypto/shash.o').read_bytes()]+[(root/'evidence/crypto'/name).read_bytes() for name in ('shash.o','ahash.o','crypto_hash.o')];proof=link_origin(*[parse_object(x) for x in raw]);require(proof==result['link_origin'],'independent new origin proof equals producer evidence')
 require(stable(kernel_record)['file_identity']==kernel_record['file_identity'] and stable(baseline_record)['file_identity']==baseline_record['file_identity'],'both protected inputs stable after all reader use');return {'passed':True,'source_sha256':expected,'link_origin':proof,'protected_inputs':[kernel_record,baseline_record],'old_semantic_fixture_or_target_execution':False}


def main():
 p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--workspace',type=Path,required=True);p.add_argument('--kernel-archive',type=Path,required=True);p.add_argument('--baseline-pins',type=Path,required=True);p.add_argument('--baseline-input',type=Path,required=True);p.add_argument('--baseline-extraction',type=Path,required=True);a=p.parse_args();out=a.output.absolute();workspace=a.workspace.absolute();kernel=a.kernel_archive.absolute();baseline_input=a.baseline_input.absolute();baseline_extraction=a.baseline_extraction.absolute();private=ROOT/'note10/private'
 require(out.name==NEW_ROOT and out.is_relative_to(private) and workspace.is_relative_to(private) and not out.exists() and not workspace.exists() and not baseline_input.exists() and not baseline_extraction.exists(),'fresh separate PC-only build roots');separate([out,workspace,kernel,baseline_input,baseline_extraction]);pins=json.loads(a.baseline_pins.read_text());out.mkdir(parents=True);commands=[]
 def run(args,name,cwd=None):
  path=out/name;path.parent.mkdir(parents=True,exist_ok=True)
  started=time.time_ns()
  with path.open('xb') as stream:done=subprocess.run(args,cwd=cwd,stdout=stream,stderr=subprocess.STDOUT,check=False)
  ended=time.time_ns();commands.append({'command':args,'returncode':done.returncode,'completed':True,'log':name,'log_sha256':digest(path.read_bytes()),'start_ns':started,'end_ns':ended});require(done.returncode==0,'new Kbuild/tool command failed: '+name);return path.read_text()
 try:
  write(out/'source-manifest.json',sources())
  for name in PUBLIC:dest=out/'source'/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/name,dest)
  compiler_path=Path(shutil.which('clang-14')).resolve();linker_path=Path(shutil.which('aarch64-linux-gnu-ld')).resolve();compiler_version=run(['clang-14','--version'],'tools/clang-version.log');linker_version=run(['aarch64-linux-gnu-ld','--version'],'tools/linker-version.log');compiler={'role':'clang-14','path':str(compiler_path),'sha256':digest(compiler_path.read_bytes()),'version':compiler_version};linker={'role':'aarch64-linux-gnu-ld','path':str(linker_path),'sha256':digest(linker_path.read_bytes()),'version':linker_version};composite_command(['aarch64-linux-gnu-ld','-m','aarch64linux','--no-relax','-r','-o',TARGET,'crypto/ahash.o','crypto/shash.o'],linker)
  budget=KERNEL_BYTES+pins['zip_bytes']+4*1024**3+CAP+512*1024**2+CAP+512*1024**2;write(out/'disk-before-inputs.json',disk_budget(private,budget))
  baseline_archive=retrieve_baseline(pins,baseline_input);baseline_before=protected(baseline_archive,'accepted-v64-baseline-ZIP-v1',pins['zip_bytes'],pins['zip_sha256']);extract_zip(baseline_archive,baseline_extraction,BASELINE_ROOT,pins['ordinary_members'],pins['expanded_bytes']);oldroot=baseline_extraction/BASELINE_ROOT;old=baseline_labels(oldroot,pins);olddeps=json.loads((oldroot/'evidence/dependencies.json').read_text());require(compiler['sha256']==old['toolchain']['clang-14']['sha256'] and linker['sha256']==old['toolchain']['aarch64-linux-gnu-ld']['sha256'],'accepted compiler/GNU linker binary identities')
  for name in ('run.json','jobs.json','artifacts.json','artifact.json','job-log.log','AUTHENTICATED-API-RETRIEVAL-RECEIPT.json'):dest=out/'baseline-api'/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(baseline_input/name,dest)
  if not kernel.exists():
   kernel.parent.mkdir(parents=True,exist_ok=True)
   with urllib.request.urlopen('https://codeload.github.com/corsicanu/android_kernel_samsung_universal9820/tar.gz/'+KERNEL_COMMIT,timeout=120) as response,kernel.open('xb') as stream:
    total=0
    for block in iter(lambda:response.read(1024*1024),b''):total+=len(block);require(total<=KERNEL_BYTES,'exact bounded stock compressed source');stream.write(block)
  kernel_before=protected(kernel,'kernel-source-v1',KERNEL_BYTES,KERNEL_SHA);separate([kernel,baseline_archive],[kernel_before['file_identity'],baseline_before['file_identity']]);write(out/'disk-before-extraction.json',disk_budget(private,4*1024**3+512*1024**2+CAP+512*1024**2));workspace.mkdir(parents=True);source,tar_report=extract_kernel(kernel,workspace/'source');objects=workspace/'objects';objects.mkdir();config=(oldroot/'evidence/dependency-files/objects/.config').read_bytes();packaging=config_contract(config);(objects/'.config').write_bytes(config)
  resource=run(['clang-14','-print-file-name=include'],'tools/compiler-resource.log').strip();require(Path(resource).is_absolute() and Path(resource).is_dir(),'actual compiler resource root')
  make=make_command(source,objects);require(list(tree_inventory(objects))==['.config'],'fresh output contains only copied accepted config');freshness={'output_files_before':['.config']};build_log=run(make,'build/composite.log');freshness['object_mtime_ns']={n:(objects/'crypto'/n).stat().st_mtime_ns for n in ('shash.o','ahash.o','crypto_hash.o')};freshness['complete_output_size']=build_output_size(objects,source);postprocess=postprocess_commands(build_log,linker);require((objects/'.config').read_bytes()==config,'source config remains byte-identical')
  reports={}
  for leaf in ('shash','ahash'):
   reports[leaf]=prerequisite_capture(objects,source,resource,'crypto/'+leaf+'.o',out/'evidence'/leaf/'dependency-files');write(out/'evidence'/leaf/'prerequisites.json',reports[leaf])
  equality=leaf_equality(old,olddeps,reports['shash']);ahash_profile(reports['shash'],reports['ahash'])
  for name in ('shash.o','ahash.o','crypto_hash.o','.shash.o.cmd','.ahash.o.cmd','.crypto_hash.o.cmd','.tmp_shash.su','.tmp_ahash.su','.shash.o.d','.ahash.o.d'):
   src=objects/'crypto'/name
   if src.is_file():dest=out/'evidence/crypto'/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(src,dest)
  for name in ('scripts/Makefile.build','scripts/Makefile.lib','scripts/Kbuild.include','crypto/Makefile','Makefile'):
   dest=out/'evidence/stock-source'/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source/name,dest)
  command=composite_command(command_line((objects/'crypto/.crypto_hash.o.cmd').read_text(),TARGET),linker);proof=link_origin(parse_object((oldroot/'evidence/kbuild/crypto/shash.o').read_bytes()),*[parse_object((objects/'crypto'/n).read_bytes()) for n in ('shash.o','ahash.o','crypto_hash.o')]);write(out/'commands.json',commands)
  after_kernel=stable(kernel_before);after_baseline=stable(baseline_before);require(after_kernel['file_identity']==kernel_before['file_identity'] and after_baseline['file_identity']==baseline_before['file_identity'],'both external protected inputs stable after build')
  result={'schema':1,'version':'v65','passed':True,'executed_fixture_commands':0,'ci_context':{k:os.environ.get(k) for k in ('GITHUB_RUN_ID','GITHUB_RUN_ATTEMPT','GITHUB_SHA','GITHUB_JOB')},'source_sha256':sources(),'compiler':compiler,'linker':linker,'composite_make_command':make,'actual_composite_command':command,'config_packaging':packaging,'shash_input_equality':equality,'link_origin':proof,'build_freshness':freshness,'kernel_expansion':tar_report,'protected_inputs_before':[kernel_before,baseline_before],'protected_inputs_after':[after_kernel,after_baseline],'baseline_pins':pins,'baseline_original_producer_result_sha256':digest((oldroot/'result.json').read_bytes()),'normal_leaf_postprocess':{'same_GNU_LD_role':True,'full_expanded_command_log':'build/composite.log','expanded_selected_link_commands':postprocess,'saved_CC_commands':['evidence/crypto/.shash.o.cmd','evidence/crypto/.ahash.o.cmd'],'temporary_compiler_object_retained':False,'temporary_version_script_retained':False,'reason':'normal pinned Kbuild consumes temporary objects/version scripts; expanded actual shell provenance and final objects retained','declared_LDFLAGS':'-m aarch64linux --no-relax'},'physical_BOOT_reboot':0,'device_authorized':False,'deployment_ready':False,'old_semantic_or_target_execution':False};result['files']=tree_inventory(out);write(out/'result.json',result)
 except BaseException as error:
  if not (out/'commands.json').exists():write(out/'commands.json',commands)
  try:retained=preserve_failure_files(out,workspace,baseline_input)
  except Exception as copying:retained={'copy_exception_type':type(copying).__name__,'copy_exception_message':str(copying)}
  write(out/'failure.json',{'exception_type':type(error).__name__,'exception_message':str(error),'commands_completed':len(commands),'retained_forensic_files':retained,'passed':False,'automatic_retry':False});raise


if __name__=='__main__':main()
