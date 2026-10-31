"""CP4 include-search argv binding only; no prior fixtures or make execution."""
import argparse,copy,json,tempfile
from pathlib import Path
from crypto_hash_composite import require,digest
from build_crypto_hash_composite import PUBLIC,ROUTING_WRAPPER,MAKE_ENVIRONMENT,make_command,routing_evidence,verify_routing_evidence

CASES=('one-source-include-before-first-f','remaining-CP3-argv-preserved','object-cwd-retained-for-generated-includes','reader-exact-include-context-positive','missing-source-include-reject','wrong-source-subdirectory-reject','duplicate-source-include-reject','relative-source-include-reject','foreign-source-include-reject','object-root-as-source-include-reject','source-include-after-first-f-reject','split-include-option-reject','short-I-alias-reject','actual-command-missing-include-reject','route-record-only-missing-include-reject','standalone-include-fixture-public-closure')


def run_cases(completed=None):
 if completed is None:completed=[]
 source='/synthetic/work/source/kernel';objects='/synthetic/work/objects';wrapper='/synthetic/work/routing/composite.mk';option='--include-dir='+source
 def rejected(fn):
  try:fn()
  except (ValueError,KeyError,TypeError):return
  raise ValueError('invalid new include-context fixture accepted')
 for name in CASES:
  require(name==CASES[len(completed)],'frozen CP4 case order')
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);args=make_command(source,objects,wrapper)
   if name=='one-source-include-before-first-f':require(args.count(option)==1 and args[4]==option and args[5]=='-f' and args[7]=='-f','exactly one source include-dir before unchanged ordered Makefiles')
   elif name=='remaining-CP3-argv-preserved':
    expected=['make','-C',objects,'KBUILD_SRC='+source,'-f',source+'/Makefile','-f',wrapper,'ARCH=arm64','CC=clang-14','LD=aarch64-linux-gnu-ld','CROSS_COMPILE=aarch64-linux-gnu-','CLANG_TRIPLE=aarch64-linux-gnu-','CROSS_COMPILE_ARM32=arm-linux-gnueabi-','GCC_TOOLCHAIN_DIR=/usr/aarch64-linux-gnu/bin/','HOSTCC=gcc','HOSTCFLAGS=-Wno-error=deprecated-declarations','KCFLAGS=-gdwarf-4 -fstack-usage -ffunction-sections -fdata-sections -mllvm -enable-machine-outliner=never -fno-inline-functions','CONFIG_THIN_ARCHIVES=','LDFLAGS=-m aarch64linux --no-relax','V=1','-j2','crypto/crypto_hash.o'];require([v for v in args if v!=option]==expected,'only the reviewed include-dir addition changes the CP3 argv')
   elif name=='object-cwd-retained-for-generated-includes':require(args[:4]==['make','-C',objects,'KBUILD_SRC='+source] and args[4]==option and not any(v.startswith(('O=','MAKEFLAGS=')) for v in args),'object current directory and normal generated-include/MAKEFLAGS behavior retained; no source-cwd fallback')
   elif name=='standalone-include-fixture-public-closure':require('note10/device_test/test_crypto_hash_include_context.py' in PUBLIC,'new standalone fixture included in public closure')
   else:
    evidence=routing_evidence(source,objects,wrapper);(root/'routing').mkdir();(root/'routing/composite.mk').write_bytes(ROUTING_WRAPPER);commands=[{'command':['clang-14','--version']},{'command':['aarch64-linux-gnu-ld','--version']},{'command':['clang-14','-print-file-name=include']},{'command':list(args),'make_environment':dict(MAKE_ENVIRONMENT)}]
    if name=='reader-exact-include-context-positive':require(verify_routing_evidence(root,evidence,source,objects,commands)==args,'existing reader binds full new source include context')
    else:
     changed=list(args)
     if name=='missing-source-include-reject':changed.remove(option)
     elif name=='wrong-source-subdirectory-reject':changed[4]=option+'/include'
     elif name=='duplicate-source-include-reject':changed.insert(4,option)
     elif name=='relative-source-include-reject':changed[4]='--include-dir=relative/source'
     elif name=='foreign-source-include-reject':changed[4]='--include-dir=/synthetic/foreign/kernel'
     elif name=='object-root-as-source-include-reject':changed[4]='--include-dir='+objects
     elif name=='source-include-after-first-f-reject':changed.pop(4);changed.insert(6,option)
     elif name=='split-include-option-reject':changed[4:5]=['--include-dir',source]
     elif name=='short-I-alias-reject':changed[4]='-I'+source
     elif name in ('actual-command-missing-include-reject','route-record-only-missing-include-reject'):changed.remove(option)
     else:raise ValueError('unhandled new CP4 case '+name)
     if name!='actual-command-missing-include-reject':evidence['make_argv']=list(changed)
     if name!='route-record-only-missing-include-reject':commands[-1]['command']=list(changed)
     rejected(lambda:verify_routing_evidence(root,evidence,source,objects,commands))
   completed.append(name)
 return {'passed':True,'cases':completed,'case_count':len(completed),'synthetic_only':True,'GNU_make_behavior_executed_or_preleaf_equality_claimed':False,'prior120_42_53_58_fixture_import_or_replay':False,'make_dryrun_compiler_object_parse_network_API_device_execution':False}


def main():
 p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--checkpoint',type=Path,required=True);p.add_argument('--checkpoint-sha256',required=True);p.add_argument('--inventory',type=Path,required=True);p.add_argument('--inventory-sha256',required=True);a=p.parse_args();root=Path(__file__).resolve().parents[2];require(not a.output.exists() and a.output.absolute().is_relative_to(root/'note10/private'),'fresh private CP4 result');completed=[];phase='attribution';attribution={'checkpoint_path':str(a.checkpoint.absolute()),'inventory_path':str(a.inventory.absolute())}
 try:
  cpraw=a.checkpoint.read_bytes();invraw=a.inventory.read_bytes();require(digest(cpraw)==a.checkpoint_sha256 and digest(invraw)==a.inventory_sha256,'exact frozen CP4 checkpoint/inventory SHA256');cp=json.loads(cpraw);inventory=json.loads(invraw);attribution.update(checkpoint_sha256=digest(cpraw),inventory_sha256=digest(invraw));require(cp['version']=='v65' and cp['checkpoint']==4 and cp['new_include_context_fixture_inventory']==list(CASES) and inventory['cases']==list(CASES) and inventory['case_count']==len(CASES) and inventory['fixture_sha256']==digest(Path(__file__).read_bytes()),'exact standalone CP4 inventory')
  for group in ('public_sources_sha256','private_sources_sha256','shared_sources_sha256'):
   for name,expected in cp[group].items():require(digest((root/name).read_bytes())==expected,'current frozen source/import closure')
  phase='new_include_context_cases';result=run_cases(completed);result.update(attribution)
 except BaseException as error:
  a.output.parent.mkdir(parents=True,exist_ok=True)
  with a.output.open('x',encoding='utf8',newline='\n') as stream:stream.write(json.dumps(dict(attribution,passed=False,cases=completed,case_count=len(completed),completed_case_names=completed,completed_case_count=len(completed),failing_next_case=CASES[len(completed)] if len(completed)<len(CASES) else None,failure_phase=phase,exception_type=type(error).__name__,exception_message=str(error),automatic_retry=False),indent=2)+'\n')
  raise
 a.output.parent.mkdir(parents=True,exist_ok=True)
 with a.output.open('x',encoding='utf8',newline='\n') as stream:stream.write(json.dumps(result,indent=2)+'\n')
if __name__=='__main__':main()
