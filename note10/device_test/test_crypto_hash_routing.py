"""Only new fixed routing/environment/generated-input synthetic cases."""
import argparse,copy,json,stat,tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from crypto_hash_composite import require,digest
from build_crypto_hash_composite import ROUTING_WRAPPER,MAKE_ENVIRONMENT,GENERATED_INPUTS,PUBLIC,make_command,make_environment,create_routing_wrapper,initial_output_state,generated_input_identity,routing_evidence,verify_routing_evidence,preserve_routing_diagnostics,SOURCE_TOP

CONFIG_CASES=('config-missing-.config','config-missing-include/generated/autoconf.h','config-missing-include/config/auto.conf','config-mutated-.config','config-mutated-include/generated/autoconf.h','config-mutated-include/config/auto.conf','config-unsafe-.config','config-unsafe-include/generated/autoconf.h','config-unsafe-include/config/auto.conf')
ROUTE_CASES=('route-extra-schema-field','route-missing-wrapper-hash','route-wrong-wrapper-hash','route-wrong-wrapper-location','route-source-mismatch','route-output-mismatch','route-two-f-order','route-outer-O-fallback','route-wholecrypto-fallback','route-ko-fallback','route-default-goal-fallback','route-environment-missing','route-environment-wrong-platform','route-environment-wrong-major','route-environment-extra-secret-field','route-preleaf-claim-reject','route-schema-bool-reject','route-wrapper-tampered','route-wrapper-unsafe','route-command-receipt-missing','route-second-make-reject','route-duplicate-make-reject','route-effective-env-missing','route-effective-env-wrong','route-effective-env-extra-field')
DIAGNOSTIC_CASES=('diagnostic-exact-three-allowlist','diagnostic-directory-reject','diagnostic-symlink-reject','diagnostic-reparse-reject','diagnostic-file-cap-reject','diagnostic-total-cap-reject')
CASES=('exact-inner-stock-make-argv','exact-reviewed-wrapper-bytes-and-hash','one-stock-build-recursion-no-link-recipe','fresh-exclusive-wrapper','wrapper-existing-directory-reject','wrapper-existing-file-reject','wrapper-workspace-unsafe-reject','environment-restores-two-values','environment-preserves-other-values-without-recording-secret','reader-exact-route-positive','three-generated-inputs-exact-positive','initial-output-config-only-positive','initial-output-missing-config-reject','initial-output-shash-present-reject','initial-output-ahash-present-reject','initial-output-composite-present-reject','initial-output-generated-header-present-reject','new-routing-fixture-public-closure')+CONFIG_CASES+ROUTE_CASES+DIAGNOSTIC_CASES


def route_fixture(root):
 source='/synthetic/work/source/kernel';objects='/synthetic/work/objects';wrapper='/synthetic/work/routing/composite.mk';evidence=routing_evidence(source,objects,wrapper);(root/'routing').mkdir();(root/'routing/composite.mk').write_bytes(ROUTING_WRAPPER);commands=[{'command':['clang-14','--version']},{'command':['aarch64-linux-gnu-ld','--version']},{'command':['clang-14','-print-file-name=include']},{'command':list(evidence['make_argv']),'make_environment':dict(MAKE_ENVIRONMENT)}];return source,objects,evidence,commands


def config_fixture(root):
 fresh=root/'fresh';baseline=root/'baseline';fresh.mkdir();baseline.mkdir()
 for index,name in enumerate(GENERATED_INPUTS):
  raw=('synthetic-complete-config-'+str(index)+'\n').encode()
  for directory in (fresh,baseline):path=directory/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw)
 return fresh,baseline


def unsafe_lstat(path,kind):
 original=Path.lstat
 def changed(self):
  if self==path:return SimpleNamespace(st_mode=stat.S_IFLNK if kind=='symlink' else stat.S_IFREG,st_file_attributes=1024 if kind=='reparse' else 0,st_size=1)
  return original(self)
 return patch.object(Path,'lstat',changed)


def run_cases(completed=None):
 if completed is None:completed=[]
 def equal(a,b):require(a==b,'independent CP3 routing expectation')
 def rejected(fn):
  try:fn()
  except (ValueError,KeyError,OSError,TypeError):return
  raise ValueError('invalid new routing fixture accepted')
 def check(name,fn):require(name==CASES[len(completed)],'frozen CP3 new-only case order');fn();completed.append(name)
 for name in CASES:
  def action(case=name):
   with tempfile.TemporaryDirectory() as tmp:
    root=Path(tmp)
    if case=='exact-inner-stock-make-argv':
     args=make_command('/synthetic/source','/synthetic/objects','/synthetic/routing/composite.mk');equal(args[:8],['make','-C','/synthetic/objects','KBUILD_SRC=/synthetic/source','-f','/synthetic/source/Makefile','-f','/synthetic/routing/composite.mk']);equal(args[-1],'crypto/crypto_hash.o');require(not any(a.startswith('O=') for a in args),'no outer O routing');return
    if case in ('exact-reviewed-wrapper-bytes-and-hash','one-stock-build-recursion-no-link-recipe'):
     equal(ROUTING_WRAPPER,b'crypto/crypto_hash.o: prepare scripts FORCE\n\t$(Q)$(MAKE) $(build)=crypto crypto/crypto_hash.o\n');equal(digest(ROUTING_WRAPPER),'22103b6a1d81e52c9d9a7f66199af6824c13bfb1867e7b13d419fc112e9518f1');require(ROUTING_WRAPPER.count(b'$(MAKE)')==1 and b'$(LD)' not in ROUTING_WRAPPER and b'__build' not in ROUTING_WRAPPER and b'modpost' not in ROUTING_WRAPPER,'one stock recursion only');return
    if case in ('fresh-exclusive-wrapper','wrapper-existing-directory-reject','wrapper-existing-file-reject','wrapper-workspace-unsafe-reject'):
     workspace=root/'workspace';workspace.mkdir()
     if case=='wrapper-existing-directory-reject':(workspace/'routing').mkdir();rejected(lambda:create_routing_wrapper(workspace));return
     if case=='wrapper-existing-file-reject':(workspace/'routing').mkdir();(workspace/'routing/composite.mk').write_bytes(b'existing');rejected(lambda:create_routing_wrapper(workspace));return
     if case=='wrapper-workspace-unsafe-reject':
      with unsafe_lstat(workspace,'reparse'):rejected(lambda:create_routing_wrapper(workspace))
      return
     path=create_routing_wrapper(workspace);equal(path.read_bytes(),ROUTING_WRAPPER);equal(path.parent,workspace/'routing');return
    if case.startswith('environment-'):
     inherited={'PLATFORM_VERSION':'wrong','ANDROID_MAJOR_VERSION':'q','GH_TOKEN':'synthetic-secret-only','OTHER':'kept'};effective=make_environment(inherited);equal({k:effective[k] for k in MAKE_ENVIRONMENT},MAKE_ENVIRONMENT);equal(effective['OTHER'],'kept');equal(effective['GH_TOKEN'],inherited['GH_TOKEN']);source,objects,evidence,commands=route_fixture(root);require('synthetic-secret-only' not in json.dumps(evidence) and set(evidence['environment'])==set(MAKE_ENVIRONMENT),'only whitelisted environment recorded');equal(inherited['PLATFORM_VERSION'],'wrong');return
    if case.startswith('initial-output-'):
     objects=root/'objects';objects.mkdir()
     if case!='initial-output-missing-config-reject':(objects/'.config').write_bytes(b'synthetic accepted config')
     extra={'initial-output-shash-present-reject':'crypto/shash.o','initial-output-ahash-present-reject':'crypto/ahash.o','initial-output-composite-present-reject':'crypto/crypto_hash.o','initial-output-generated-header-present-reject':'include/generated/autoconf.h'}.get(case)
     if extra:path=objects/extra;path.parent.mkdir(parents=True);path.write_bytes(b'unexpected existing input')
     if case=='initial-output-config-only-positive':equal(initial_output_state(objects),['.config'])
     else:rejected(lambda:initial_output_state(objects))
     return
    if case=='new-routing-fixture-public-closure':require('note10/device_test/test_crypto_hash_routing.py' in PUBLIC,'new standalone routing fixture in public closure');return
    if case=='three-generated-inputs-exact-positive' or case in CONFIG_CASES:
     fresh,baseline=config_fixture(root)
     if case=='three-generated-inputs-exact-positive':
      result=generated_input_identity(fresh,baseline);equal(set(result),set(GENERATED_INPUTS));require(all(result[n]=={'bytes':len((fresh/n).read_bytes()),'sha256':digest((fresh/n).read_bytes())} for n in GENERATED_INPUTS),'full bytes/hash of all three generated inputs');return
     mode,relative=case.removeprefix('config-').split('-',1);path=fresh/relative
     if mode=='missing':path.unlink()
     elif mode=='mutated':path.write_bytes(b'mutated generated input')
     else:
      with unsafe_lstat(path,'symlink'):rejected(lambda:generated_input_identity(fresh,baseline))
      return
     rejected(lambda:generated_input_identity(fresh,baseline));return
    if case in DIAGNOSTIC_CASES:
     workspace=root/'workspace';objects=workspace/'objects';source=workspace/'source'/SOURCE_TOP;allowed={'objects/include/config/auto.conf.cmd':objects/'include/config/auto.conf.cmd','source/scripts/android-version.sh':source/'scripts/android-version.sh','source/scripts/android-major-version.sh':source/'scripts/android-major-version.sh'}
     for key,path in allowed.items():path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(('synthetic '+key).encode())
     (source/'arbitrary-secret').write_bytes(b'not selected');(workspace/'baseline.zip').write_bytes(b'not selected');out=root/'out';out.mkdir();target=allowed['objects/include/config/auto.conf.cmd']
     if case=='diagnostic-directory-reject':target.unlink();target.mkdir();rejected(lambda:preserve_routing_diagnostics(out,workspace));return
     if case in ('diagnostic-symlink-reject','diagnostic-reparse-reject'):
      with unsafe_lstat(target,'symlink' if 'symlink' in case else 'reparse'):rejected(lambda:preserve_routing_diagnostics(out,workspace))
      return
     if case=='diagnostic-file-cap-reject':
      with target.open('wb') as stream:stream.truncate(8*1024*1024+1)
      rejected(lambda:preserve_routing_diagnostics(out,workspace));return
     if case=='diagnostic-total-cap-reject':rejected(lambda:preserve_routing_diagnostics(out,workspace,ceiling=4));return
     result=preserve_routing_diagnostics(out,workspace);equal(set(result),set(allowed));require(all((out/'routing-diagnostics'/key).read_bytes()==path.read_bytes() for key,path in allowed.items()),'only exact diagnostic source bytes retained');saved=json.loads((out/'routing-diagnostics/manifest.json').read_text());require(saved['diagnostic_only'] is True and saved['Kconfig_cause_proven'] is False,'no unproven Kconfig cause claim');require(not (out/'baseline.zip').exists() and not (out/'routing-diagnostics/source/arbitrary-secret').exists(),'no ZIP/arbitrary source copied');return
    source,objects,evidence,commands=route_fixture(root)
    if case=='reader-exact-route-positive':equal(verify_routing_evidence(root,evidence,source,objects,commands),evidence['make_argv']);return
    if case=='route-extra-schema-field':evidence['extra']=1
    elif case=='route-missing-wrapper-hash':evidence.pop('wrapper_sha256')
    elif case=='route-wrong-wrapper-hash':evidence['wrapper_sha256']='0'*64
    elif case=='route-wrong-wrapper-location':evidence['wrapper_path']='/synthetic/unreviewed.mk'
    elif case=='route-source-mismatch':evidence['source']='/other/source'
    elif case=='route-output-mismatch':evidence['objects']='/other/objects'
    elif case=='route-two-f-order':evidence['make_argv'][5],evidence['make_argv'][7]=evidence['make_argv'][7],evidence['make_argv'][5]
    elif case=='route-outer-O-fallback':evidence['make_argv'].insert(3,'O='+objects)
    elif case=='route-wholecrypto-fallback':evidence['make_argv'][-1]='crypto/'
    elif case=='route-ko-fallback':evidence['make_argv'][-1]='crypto/crypto_hash.ko'
    elif case=='route-default-goal-fallback':evidence['make_argv'][-1]='__build'
    elif case=='route-environment-missing':evidence.pop('environment')
    elif case=='route-environment-wrong-platform':evidence['environment']['PLATFORM_VERSION']='10'
    elif case=='route-environment-wrong-major':evidence['environment']['ANDROID_MAJOR_VERSION']='q'
    elif case=='route-environment-extra-secret-field':evidence['environment']['GH_TOKEN']='synthetic-secret'
    elif case=='route-preleaf-claim-reject':evidence['preleaf_input_equality_claimed']=True
    elif case=='route-schema-bool-reject':evidence['schema']=True
    elif case=='route-wrapper-tampered':(root/'routing/composite.mk').write_bytes(ROUTING_WRAPPER+b'bad:; arbitrary\n')
    elif case=='route-wrapper-unsafe':
     with unsafe_lstat(root/'routing/composite.mk','symlink'):rejected(lambda:verify_routing_evidence(root,evidence,source,objects,commands))
     return
    elif case=='route-command-receipt-missing':commands.pop()
    elif case=='route-second-make-reject':commands.append(copy.deepcopy(commands[-1]))
    elif case=='route-duplicate-make-reject':commands[0]=copy.deepcopy(commands[-1])
    elif case=='route-effective-env-missing':commands[-1].pop('make_environment')
    elif case=='route-effective-env-wrong':commands[-1]['make_environment']['PLATFORM_VERSION']='wrong'
    elif case=='route-effective-env-extra-field':commands[-1]['make_environment']['GH_TOKEN']='synthetic-secret'
    else:raise ValueError('unhandled new CP3 case '+case)
    rejected(lambda:verify_routing_evidence(root,evidence,source,objects,commands))
  check(name,action)
 return {'passed':True,'cases':completed,'case_count':len(completed),'synthetic_only':True,'prior120_42_53_fixture_import_or_replay':False,'make_dryrun_compiler_object_parse_network_API_device_execution':False}


def main():
 p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--checkpoint',type=Path,required=True);p.add_argument('--checkpoint-sha256',required=True);p.add_argument('--inventory',type=Path,required=True);p.add_argument('--inventory-sha256',required=True);a=p.parse_args();root=Path(__file__).resolve().parents[2];require(not a.output.exists() and a.output.absolute().is_relative_to(root/'note10/private'),'fresh private CP3 result');completed=[];phase='attribution';attribution={'checkpoint_path':str(a.checkpoint.absolute()),'inventory_path':str(a.inventory.absolute())}
 try:
  cpraw=a.checkpoint.read_bytes();invraw=a.inventory.read_bytes();require(digest(cpraw)==a.checkpoint_sha256 and digest(invraw)==a.inventory_sha256,'exact frozen CP3 checkpoint/inventory SHA256');cp=json.loads(cpraw);inventory=json.loads(invraw);attribution.update(checkpoint_sha256=digest(cpraw),inventory_sha256=digest(invraw));require(cp['version']=='v65' and cp['checkpoint']==3 and cp['new_routing_fixture_inventory']==list(CASES) and inventory['cases']==list(CASES) and inventory['case_count']==len(CASES) and inventory['fixture_sha256']==digest(Path(__file__).read_bytes()),'exact standalone CP3 inventory')
  for group in ('public_sources_sha256','private_sources_sha256','shared_sources_sha256'):
   for name,expected in cp[group].items():require(digest((root/name).read_bytes())==expected,'current frozen source/import closure')
  phase='new_routing_cases';result=run_cases(completed);result.update(attribution)
 except BaseException as error:
  a.output.parent.mkdir(parents=True,exist_ok=True)
  with a.output.open('x',encoding='utf8',newline='\n') as stream:stream.write(json.dumps(dict(attribution,passed=False,cases=completed,case_count=len(completed),completed_case_names=completed,completed_case_count=len(completed),failing_next_case=CASES[len(completed)] if len(completed)<len(CASES) else None,failure_phase=phase,exception_type=type(error).__name__,exception_message=str(error),automatic_retry=False),indent=2)+'\n')
  raise
 a.output.parent.mkdir(parents=True,exist_ok=True)
 with a.output.open('x',encoding='utf8',newline='\n') as stream:stream.write(json.dumps(result,indent=2)+'\n')
if __name__=='__main__':main()
