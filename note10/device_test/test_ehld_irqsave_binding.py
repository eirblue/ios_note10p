"""Mutation-test the v46 EHLD irqsave source and model binding."""
import argparse,copy,hashlib,json,shutil,tempfile
from pathlib import Path
from ehld_irqsave_binding import assert_scope,package_scope
from prepare_ehld_irqsave_audit import TARGET,KCONFIG,BLOCK,prepare
CASES=('baseline','source-map-omitted','snapshot-third-mutated','coherent-target-mutated','config-off','config-m','config-garbage','config-duplicate','model-case-omitted','stale-harness-updated','model-log-mutated','coherent-log-mutated','generated-coherent-mutated','disabled-binding-hash-stray','schema-bool','disabled-artifact-downgrade','helper-short-map-no-write','helper-duplicate-kconfig-no-write')
PACKAGE_SCOPE_CASES=('off-missing','off-false','on-valid','flag-string','flag-integer','version-bool','version-string','missing-old-lock','old-lock-version-bool','stray-off-version')
OFF_SCOPE_CASES=('missing-flags','explicit-false','missing-config-hash','null-config-hash','wrong-config-hash','config-m','config-garbage','config-duplicate','stray-version','stray-binding-proof','stray-artifact')
def sha(b):return hashlib.sha256(b).hexdigest()
def clone(src,dst):
 dst.mkdir()
 for name in ('Image','handoff.config','build-result.json'):
  shutil.copyfile(src/name,dst/name)
 for name in ('ehld-lock-prepared','ehld-irqsave-prepared','ehld-irqsave-model'):
  shutil.copytree(src/name,dst/name)
def check_off_scope(case):
 from ehld_irqsave_binding import validate
 with tempfile.TemporaryDirectory() as td:
  root=Path(td);(root/'Image').write_bytes(b'plain-image')
  cfg=b'# CONFIG_NOTE10_EHLD_LOCK_AUDIT is not set\n# CONFIG_NOTE10_EHLD_IRQSAVE_AUDIT is not set\n'
  build={'effective_config_sha256':sha(cfg)}
  if case=='explicit-false':build['ehld_irqsave_audit']=False
  if case=='config-m':cfg=cfg.replace(b'# CONFIG_NOTE10_EHLD_IRQSAVE_AUDIT is not set',b'CONFIG_NOTE10_EHLD_IRQSAVE_AUDIT=m')
  elif case=='config-garbage':cfg=cfg.replace(b'# CONFIG_NOTE10_EHLD_IRQSAVE_AUDIT is not set',b'CONFIG_NOTE10_EHLD_IRQSAVE_AUDIT=garbage')
  elif case=='config-duplicate':cfg+=b'CONFIG_NOTE10_EHLD_IRQSAVE_AUDIT=n\n'
  elif case=='stray-version':build['ehld_irqsave_audit_version']=1
  elif case=='stray-binding-proof':build['ehld_irqsave_binding_sha256']='0'*64
  elif case=='stray-artifact':(root/'ehld-irqsave-model').mkdir()
  (root/'handoff.config').write_bytes(cfg)
  if case=='missing-config-hash':build.pop('effective_config_sha256',None)
  elif case=='null-config-hash':build['effective_config_sha256']=None
  elif case=='wrong-config-hash':build['effective_config_sha256']='0'*64
  else:build['effective_config_sha256']=sha(cfg)
  try:result=validate(root,build,require_package_flow=False)
  except (ValueError,KeyError,TypeError,FileNotFoundError):
   if case in ('missing-flags','explicit-false'):raise
   return False
  if case not in ('missing-flags','explicit-false','missing-config-hash') or result is not False:raise AssertionError('wrong default-off validation: '+case)
  return True
def main():
 p=argparse.ArgumentParser();p.add_argument('--artifact',required=True,type=Path);p.add_argument('--output',required=True,type=Path);a=p.parse_args();src,out=a.artifact,a.output;out.mkdir(parents=True,exist_ok=False)
 base=json.loads((src/'build-result.json').read_text(encoding='utf8'))
 if base.get('build_passed') is True:raise ValueError('mutation proof fixture must not claim a real build')
 package_inputs=({'off-missing':({},False),'off-false':({'ehld_irqsave_audit':False},False),'on-valid':({'ehld_irqsave_audit':True,'ehld_irqsave_audit_version':1,'ehld_lock_audit':True,'ehld_lock_audit_version':1},True),'flag-string':({'ehld_irqsave_audit':'true'},None),'flag-integer':({'ehld_irqsave_audit':1},None),'version-bool':({'ehld_irqsave_audit':True,'ehld_irqsave_audit_version':True,'ehld_lock_audit':True,'ehld_lock_audit_version':1},None),'version-string':({'ehld_irqsave_audit':True,'ehld_irqsave_audit_version':'1','ehld_lock_audit':True,'ehld_lock_audit_version':1},None),'missing-old-lock':({'ehld_irqsave_audit':True,'ehld_irqsave_audit_version':1},None),'old-lock-version-bool':({'ehld_irqsave_audit':True,'ehld_irqsave_audit_version':1,'ehld_lock_audit':True,'ehld_lock_audit_version':True},None),'stray-off-version':({'ehld_irqsave_audit':False,'ehld_irqsave_audit_version':1},None)})
 package_results=[]
 for case in PACKAGE_SCOPE_CASES:
  value,expected=package_inputs[case];accepted=True;observed=None
  try:observed=package_scope(value)
  except (ValueError,TypeError):accepted=False
  if expected is None and accepted:raise AssertionError('accepted malformed package scope: '+case)
  if expected is not None and (not accepted or observed is not expected):raise AssertionError('wrong package scope result: '+case)
  package_results.append({'case':case,'accepted':accepted,'scope':observed})
 off_results=[{'case':case,'accepted':check_off_scope(case)} for case in OFF_SCOPE_CASES]
 for case in CASES:
  with tempfile.TemporaryDirectory() as td:
   if case.startswith('helper-'):
    source=Path(td)/'source';shutil.copytree(src/'ehld-lock-prepared',source)
    target=source/TARGET;old=target.read_bytes();k=source/KCONFIG
    if case=='helper-short-map-no-write':
     short={n:sha((source/n).read_bytes()) for n in (TARGET,KCONFIG)}
     try:prepare(source,True,short)
     except ValueError:pass
     else:raise AssertionError('accepted short v45 map')
    else:
     k.write_bytes(k.read_bytes()+BLOCK)
     mapping={p.relative_to(source).as_posix():sha(p.read_bytes()) for p in source.rglob('*') if p.is_file()}
     try:prepare(source,True,mapping)
     except ValueError:pass
     else:raise AssertionError('accepted duplicate Kconfig symbol')
    if target.read_bytes()!=old:raise AssertionError('failed helper validation partially modified EHLD source')
    continue
   root=Path(td)/'fixture';clone(src,root);b=copy.deepcopy(base)
   if case=='baseline':
    if assert_scope(root,b) is not True:raise AssertionError('enabled v46 source did not validate')
    continue
   if case=='source-map-omitted':b.pop('ehld_irqsave_sources_sha256',None)
   elif case=='snapshot-third-mutated':
    path=root/'ehld-irqsave-prepared/kernel/cpu_pm.c';path.write_bytes(path.read_bytes()+b'\nmutation\n')
   elif case=='coherent-target-mutated':
    path=root/'ehld-irqsave-prepared/drivers/soc/samsung/debug/exynos-ehld.c';path.write_bytes(path.read_bytes()+b'\nmutation\n');d=sha(path.read_bytes());b['ehld_irqsave_snapshot_sha256'][path.relative_to(root/'ehld-irqsave-prepared').as_posix()]=d;b['ehld_irqsave_prepared_sha256']['drivers/soc/samsung/debug/exynos-ehld.c']=d
   elif case=='config-off':
    path=root/'handoff.config';path.write_bytes(path.read_bytes().replace(b'CONFIG_NOTE10_EHLD_IRQSAVE_AUDIT=y',b'# CONFIG_NOTE10_EHLD_IRQSAVE_AUDIT is not set'))
   elif case=='config-m':
    path=root/'handoff.config';path.write_bytes(path.read_bytes().replace(b'CONFIG_NOTE10_EHLD_IRQSAVE_AUDIT=y',b'CONFIG_NOTE10_EHLD_IRQSAVE_AUDIT=m'))
   elif case=='config-garbage':
    path=root/'handoff.config';path.write_bytes(path.read_bytes().replace(b'CONFIG_NOTE10_EHLD_IRQSAVE_AUDIT=y',b'CONFIG_NOTE10_EHLD_IRQSAVE_AUDIT=garbage'))
   elif case=='config-duplicate':
    path=root/'handoff.config';path.write_bytes(path.read_bytes()+b'CONFIG_NOTE10_EHLD_IRQSAVE_AUDIT=y\n')
   elif case=='model-case-omitted':
    path=root/'ehld-irqsave-model/result.json';r=json.loads(path.read_text());r['cases'].pop();raw=(json.dumps(r,indent=2)+'\n').encode();path.write_bytes(raw);b['ehld_irqsave_model_sha256']=sha(raw)
   elif case=='stale-harness-updated':
    path=root/'ehld-irqsave-model/result.json';r=json.loads(path.read_text());r['harness_sha256']='0'*64;raw=(json.dumps(r,indent=2)+'\n').encode();path.write_bytes(raw);b['ehld_irqsave_model_sha256']=sha(raw)
   elif case=='model-log-mutated':
    path=root/'ehld-irqsave-model/original_irqon_rejected.log';path.write_bytes(path.read_bytes()+b'mutation')
   elif case=='coherent-log-mutated':
    result_path=root/'ehld-irqsave-model/result.json';r=json.loads(result_path.read_text());name='one_irqon';path=root/'ehld-irqsave-model'/f'{name}.log';path.write_bytes(path.read_bytes().replace(b'locks=2',b'locks=3'));digest=sha(path.read_bytes());r['logs_sha256'][name]=digest;next(x for x in r['case_results'] if x['case']==name)['log_sha256']=digest;raw=(json.dumps(r,indent=2)+'\n').encode();result_path.write_bytes(raw);b['ehld_irqsave_model_sha256']=sha(raw)
   elif case=='generated-coherent-mutated':
    result_path=root/'ehld-irqsave-model/result.json';r=json.loads(result_path.read_text());name='one_irqon';path=root/'ehld-irqsave-model'/f'{name}.c';path.write_bytes(path.read_bytes()+b'\nmutation\n');digest=sha(path.read_bytes());r['generated_sha256'][name]=digest;next(x for x in r['case_results'] if x['case']==name)['source_sha256']=digest;raw=(json.dumps(r,indent=2)+'\n').encode();result_path.write_bytes(raw);b['ehld_irqsave_model_sha256']=sha(raw)
   elif case=='disabled-artifact-downgrade':
    b={k:v for k,v in b.items() if not k.startswith('ehld_irqsave_')};b['ehld_irqsave_audit']=False
   elif case=='disabled-binding-hash-stray':
    b={k:v for k,v in b.items() if not k.startswith('ehld_irqsave_')};b.update(ehld_irqsave_audit=False,ehld_irqsave_binding_sha256='0'*64)
   elif case=='schema-bool':b['ehld_irqsave_audit_version']=True
   try:assert_scope(root,b)
   except (ValueError,KeyError,TypeError,FileNotFoundError):pass
   else:raise AssertionError('accepted irqsave mutation: '+case)
 result={'passed':True,'hardware_verified':False,'cases':list(CASES),'package_scope_cases':list(PACKAGE_SCOPE_CASES),'package_scope_results':package_results,'off_scope_cases':list(OFF_SCOPE_CASES),'off_scope_results':off_results,'harness_sha256':sha(Path(__file__).read_bytes()),'source_map_sha256':sha((Path(__file__).resolve().parent/'ehld_irqsave_binding.py').read_bytes())}
 (out/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8',newline='\n')
if __name__=='__main__':main()
