"""Bind the v46 paired irqsave tokens to exact source/config and model evidence."""
import hashlib,json,re,shutil,tempfile
from pathlib import Path
from prepare_ehld_irqsave_audit import TARGET,KCONFIG,prepare,snapshot
HERE=Path(__file__).resolve().parent
SOURCES=('prepare_ehld_irqsave_audit.py','prepare_ehld_irqsave_flow_compat.py','test_ehld_irqsave_audit.py','ehld_irqsave_binding.py','test_ehld_irqsave_binding.py','test_ehld_irqsave_package_flow.py')
PACKAGE_SOURCES=('prepare_linux_boot.py','build_boot_test_packages.py','precheck_window_access.py','stage_phase2.py','collect_reservation.py')
MODEL='ehld-irqsave-model'
PREPARED='ehld-irqsave-prepared'
OPTION=b'CONFIG_NOTE10_EHLD_IRQSAVE_AUDIT'
FIELDS=('ehld_irqsave_audit_version','ehld_irqsave_baseline_sha256','ehld_irqsave_prepared_sha256','ehld_irqsave_snapshot_sha256','ehld_irqsave_sources_sha256','ehld_irqsave_package_sources_sha256','ehld_irqsave_model_sha256','ehld_irqsave_binding_sha256','ehld_irqsave_package_flow_sha256')
def sha(b):return hashlib.sha256(b).hexdigest()
def _map(v,names):return isinstance(v,dict) and set(v)==set(names) and all(isinstance(x,str) and re.fullmatch(r'[0-9a-f]{64}',x) for x in v.values())
def _files(root):return {p.relative_to(root).as_posix() for p in Path(root).rglob('*') if p.is_file()}
def package_scope(metadata):
 flag=metadata.get('ehld_irqsave_audit');version=metadata.get('ehld_irqsave_audit_version')
 if flag is not None and type(flag) is not bool:raise ValueError('malformed EHLD irqsave package flag')
 old=metadata.get('ehld_lock_audit');old_version=metadata.get('ehld_lock_audit_version')
 if old is not None and type(old) is not bool:raise ValueError('malformed prior EHLD package flag')
 if old is True and (type(old_version) is not int or old_version!=1):raise ValueError('invalid prior EHLD package dependency')
 if old is not True and old_version is not None:raise ValueError('stray prior EHLD package version')
 if flag is True:
  if type(version) is not int or version!=1 or old is not True:raise ValueError('invalid EHLD irqsave package dependency/version')
  return True
 if version is not None:raise ValueError('stray EHLD irqsave package version')
 return False

def _expected_transcript(name):
 if name=='original_irqon_rejected':return b'COMPILE\nRUN\nPASS expected rejection: failures=1 daif=b5\\n'
 if name=='wrong_main_token_inner_rejected':return b'COMPILE\nRUN\nPASS expected rejection: failures=2 daif=35\\n'
 case_id=__import__('test_ehld_irqsave_audit').CASES.index(name)
 locks=0;mmio=0;daif=0x35
 fixed={2:(0,0,0x35),3:(1,0,0x35),4:(2,2,0x35),5:(4,6,0x35),6:(2,0,0x35),7:(2,0,0x35),8:(2,0,0x35),9:(2,2,0x35),10:(1,0,0xb5),11:(2,2,0xb5),12:(4,6,0xb5),13:(2,2,0x95),14:(1,0,0x35)}
 if case_id in fixed:locks,mmio,daif=fixed[case_id]
 else:
  ds=(0x000,0x080,0x040,0x0c0,0x100,0x180,0x140,0x1c0,0x200,0x280,0x240,0x2c0,0x300,0x380,0x340,0x3c0)
  locks,mmio,daif=2,2,ds[case_id-15]
 return f'COMPILE\nRUN\nPASS {case_id} locks={locks} mmio={mmio} daif={daif:x}\\n'.encode()
def assert_scope(root,build):
 root=Path(root); flag=build.get('ehld_irqsave_audit')
 if flag is not None and type(flag) is not bool:raise ValueError('irqsave flag malformed')
 enabled=flag is True
 config=(root/'handoff.config').read_bytes().splitlines()
 mentions=[line for line in config if OPTION in line]
 if enabled:
  if mentions!=[OPTION+b'=y']:raise ValueError('irqsave config must contain exactly one enabled option')
 elif mentions not in ([],[b'# '+OPTION+b' is not set'],[OPTION+b'=n']):raise ValueError('unsupported or duplicate disabled irqsave config')
 if build.get('effective_config_sha256')!=sha((root/'handoff.config').read_bytes()):raise ValueError('irqsave measured config hash differs')
 keys=FIELDS
 outputs=(PREPARED,MODEL,'ehld-irqsave-binding-model','ehld-irqsave-package-flow-model')
 if not enabled:
  if any(k.startswith('ehld_irqsave_') and k!='ehld_irqsave_audit' for k in build) or any((root/x).exists() for x in outputs):raise ValueError('disabled irqsave evidence downgrade')
  return False
 if build.get('ehld_lock_audit') is not True:raise ValueError('irqsave requires ehld_lock_audit=true')
 if type(build.get('ehld_irqsave_audit_version')) is not int or build.get('ehld_irqsave_audit_version')!=1:raise ValueError('irqsave schema version mismatch')
 if b'CONFIG_NOTE10_EHLD_LOCK_AUDIT=y' not in config:raise ValueError('prior EHLD lock config missing')
 if not (root/'ehld-lock-prepared').is_dir():raise ValueError('prior v45 EHLD snapshot missing')
 for k,names in (('ehld_irqsave_baseline_sha256',(TARGET,KCONFIG)),('ehld_irqsave_prepared_sha256',(TARGET,KCONFIG)),('ehld_irqsave_snapshot_sha256',build.get('ehld_lock_snapshot_sha256',{}).keys()),('ehld_irqsave_sources_sha256',SOURCES),('ehld_irqsave_package_sources_sha256',PACKAGE_SOURCES)):
  if not _map(build.get(k),names):raise ValueError('irqsave map invalid: '+k)
 for key,names in (('ehld_irqsave_sources_sha256',SOURCES),('ehld_irqsave_package_sources_sha256',PACKAGE_SOURCES)):
  actual={n:sha((HERE/n).read_bytes()) for n in names}
  if build[key]!=actual:raise ValueError('irqsave current source map differs: '+key)
 prior=build['ehld_lock_snapshot_sha256']
 if not isinstance(prior,dict) or set(prior)!=set(build['ehld_irqsave_snapshot_sha256']):raise ValueError('v45/v46 snapshot path sets differ')
 v45=root/'ehld-lock-prepared'; v46=root/PREPARED
 if _files(v45)!=set(prior) or _files(v46)!=set(prior):raise ValueError('v45/v46 snapshot file sets differ')
 if {n:sha((v45/n).read_bytes()) for n in prior}!=prior:raise ValueError('v45 snapshot hash mismatch')
 if {n:sha((v46/n).read_bytes()) for n in prior}!=build['ehld_irqsave_snapshot_sha256']:raise ValueError('v46 snapshot hash mismatch')
 changed={n for n in prior if prior[n]!=build['ehld_irqsave_snapshot_sha256'][n]}
 if changed!={TARGET,KCONFIG}:raise ValueError('v46 snapshot changes more than the approved pair')
 if build['ehld_irqsave_baseline_sha256']!={n:prior[n] for n in (TARGET,KCONFIG)}:raise ValueError('irqsave baseline pair mismatch')
 if build['ehld_irqsave_prepared_sha256']!={n:build['ehld_irqsave_snapshot_sha256'][n] for n in (TARGET,KCONFIG)}:raise ValueError('irqsave prepared pair mismatch')
 with tempfile.TemporaryDirectory() as d:
  tmp=Path(d)/'source';shutil.copytree(v45,tmp)
  report=prepare(tmp,True,prior)
  got=snapshot(tmp,Path(d)/'snapshot',prior)
  if got!=build['ehld_irqsave_snapshot_sha256']:raise ValueError('v46 snapshot cannot be reconstructed from v45')
 model=root/MODEL
 if model.is_symlink() or not model.is_dir():raise ValueError('irqsave model proof missing')
 raw=(model/'result.json').read_bytes()
 if sha(raw)!=build.get('ehld_irqsave_model_sha256'):raise ValueError('irqsave model proof hash differs')
 result=json.loads(raw)
 from test_ehld_irqsave_audit import CASES,_extract_original,harness
 if result.get('passed') is not True or result.get('hardware_verified') is not False:raise ValueError('irqsave model truth fields invalid')
 if result.get('harness_sha256')!=sha((HERE/'test_ehld_irqsave_audit.py').read_bytes()):raise ValueError('irqsave harness source hash stale')
 if result.get('cases')!=list(CASES):raise ValueError('irqsave model cases differ')
 records=result.get('case_results');names=list(CASES)
 if not isinstance(records,list) or [x.get('case') for x in records]!=names:raise ValueError('irqsave case result order differs')
 if not _map(result.get('generated_sha256'),names) or not _map(result.get('logs_sha256'),names):raise ValueError('irqsave generated/log hash maps invalid')
 baseline_function=_extract_original((v45/TARGET).read_bytes())
 fixed_function=_extract_original((v46/TARGET).read_bytes())
 wrong_function=fixed_function.replace('raw_spin_unlock_irqrestore(&ctrl->lock, ctrl_flags);','raw_spin_unlock_irqrestore(&ctrl->lock, main_flags);')
 for x in records:
  n=x['case'];c=model/(n+'.c');log=model/(n+'.log')
  if type(x.get('compile_returncode')) is not int or x.get('compile_returncode')!=0 or type(x.get('returncode')) is not int or x.get('returncode')!=0 or not c.is_file() or not log.is_file():raise ValueError('irqsave case execution incomplete: '+n)
  if sha(c.read_bytes())!=result['generated_sha256'][n] or sha(log.read_bytes())!=result['logs_sha256'][n] or x.get('source_sha256')!=result['generated_sha256'][n] or x.get('log_sha256')!=result['logs_sha256'][n]:raise ValueError('irqsave case evidence hash differs: '+n)
  if log.read_bytes()!=_expected_transcript(n):raise ValueError('irqsave deterministic transcript differs: '+n)
  mode='original' if n=='original_irqon_rejected' else ('wrong' if n=='wrong_main_token_inner_rejected' else 'fixed')
  fn=baseline_function if mode=='original' else (wrong_function if mode=='wrong' else fixed_function)
  if c.read_bytes()!=harness(fn,mode).encode():raise ValueError('irqsave generated source recipe differs: '+n)
 if result.get('baseline_source_sha256')!=prior[TARGET] or result.get('patched_source_sha256')!=build['ehld_irqsave_snapshot_sha256'][TARGET]:raise ValueError('irqsave original/patch source identities differ')
 if result.get('baseline_function_sha256')!=sha(baseline_function.encode()) or result.get('function_source_sha256')!=sha(fixed_function.encode()) or result.get('negative_function_sha256')!={'original':sha(baseline_function.encode()),'wrong_main_inner':sha(wrong_function.encode())}:raise ValueError('irqsave function/negative mutation identity differs')
 if result.get('fixed_generated_sha256')!=sha(harness(fixed_function,'fixed').encode()):raise ValueError('irqsave model generation recipe differs')
 return True
def validate(root,build,require_package_flow=True):
 from ehld_lock_binding import validate as validate_prior_ehld
 prior_scope=validate_prior_ehld(root,build) if require_package_flow else validate_prior_ehld(root,build,require_package_flow=False)
 if type(prior_scope) is not bool:raise ValueError('v45 EHLD baseline scope is malformed')
 if not assert_scope(root,build):
  return False
 if prior_scope is not True:raise ValueError('v45 EHLD baseline binding is not trusted')
 for name in ('ehld-irqsave-binding-model',):
  p=Path(root)/name
  if p.is_symlink() or not p.is_dir():raise ValueError('irqsave binding proof missing')
  raw=(p/'result.json').read_bytes()
  if sha(raw)!=build.get('ehld_irqsave_binding_sha256'):raise ValueError('irqsave binding proof hash differs')
  proof=json.loads(raw)
  from test_ehld_irqsave_binding import CASES as BINDING_CASES
  if proof.get('cases')!=list(BINDING_CASES):raise ValueError('irqsave binding mutation set differs')
  from test_ehld_irqsave_binding import PACKAGE_SCOPE_CASES,OFF_SCOPE_CASES
  if proof.get('package_scope_cases')!=list(PACKAGE_SCOPE_CASES):raise ValueError('irqsave package-scope mutation set differs')
  scope_results=proof.get('package_scope_results')
  if not isinstance(scope_results,list) or [x.get('case') for x in scope_results]!=list(PACKAGE_SCOPE_CASES):raise ValueError('irqsave package-scope results differ')
  expected_scope={'off-missing':(True,False),'off-false':(True,False),'on-valid':(True,True),'flag-string':(False,None),'flag-integer':(False,None),'version-bool':(False,None),'version-string':(False,None),'missing-old-lock':(False,None),'old-lock-version-bool':(False,None),'stray-off-version':(False,None)}
  if any(type(x.get('accepted')) is not bool or x.get('accepted') is not expected_scope[x['case']][0] or x.get('scope') is not expected_scope[x['case']][1] for x in scope_results):raise ValueError('irqsave package-scope result values differ')
  if proof.get('off_scope_cases')!=list(OFF_SCOPE_CASES):raise ValueError('irqsave default-off mutation set differs')
  off_results=proof.get('off_scope_results')
  if not isinstance(off_results,list) or [x.get('case') for x in off_results]!=list(OFF_SCOPE_CASES) or any(type(x.get('accepted')) is not bool or x.get('accepted')!=(x['case'] in ('missing-flags','explicit-false')) for x in off_results):raise ValueError('irqsave default-off results differ')
  if proof.get('passed') is not True or proof.get('hardware_verified') is not False or proof.get('harness_sha256')!=sha((HERE/'test_ehld_irqsave_binding.py').read_bytes()) or proof.get('source_map_sha256')!=sha((HERE/'ehld_irqsave_binding.py').read_bytes()):raise ValueError('irqsave binding proof identity differs')
 if require_package_flow:
  p=Path(root)/'ehld-irqsave-package-flow-model'
  if p.is_symlink() or not p.is_dir():raise ValueError('irqsave package-flow proof missing')
  raw=(p/'result.json').read_bytes()
  if sha(raw)!=build.get('ehld_irqsave_package_flow_sha256'):raise ValueError('irqsave package-flow proof stale')
  proof=json.loads(raw); expected={n:sha((HERE/n).read_bytes()) for n in PACKAGE_SOURCES}
  if proof.get('passed') is not True or proof.get('hardware_verified') is not False or proof.get('harness_sha256')!=sha((HERE/'test_ehld_irqsave_package_flow.py').read_bytes()) or proof.get('package_sources_sha256')!=expected:raise ValueError('irqsave package-flow proof identity differs')
  cases=proof.get('cases')
  if not isinstance(cases,list) or [x.get('case') for x in cases]!=['actual-production-flow','missing-flag','missing-version','missing-binding-proof','build-false'] or cases[0].get('accepted') is not True or cases[0].get('diagnostic') is not True or cases[0].get('rollback') is not False or any(x.get('accepted') is not False for x in cases[1:]):raise ValueError('irqsave package-flow cases differ')
  from test_ehld_irqsave_package_flow import COLLECTOR_CASES,PRECHECK_CASES
  collector_cases=proof.get('collector_cases')
  if not isinstance(collector_cases,list) or [x.get('case') for x in collector_cases]!=list(COLLECTOR_CASES):raise ValueError('irqsave collector E2E cases differ')
  if collector_cases[0]!={'case':COLLECTOR_CASES[0],'accepted':True,'evaluation_items':39,'irqsave_scope':True} or collector_cases[1]!={'case':COLLECTOR_CASES[1],'accepted':True,'evaluation_items':39,'irqsave_scope':False} or collector_cases[2]!={'case':COLLECTOR_CASES[2],'accepted':False}:raise ValueError('irqsave collector E2E results differ')
  precheck_cases=proof.get('precheck_cases')
  if precheck_cases!=[{'case':PRECHECK_CASES[0],'accepted':True,'scope':True,'ready':True,'partition_writes':False},{'case':PRECHECK_CASES[1],'accepted':True,'scope':False,'ready':True,'partition_writes':False},{'case':PRECHECK_CASES[2],'accepted':False}]:raise ValueError('irqsave precheck E2E cases differ')
 return True
