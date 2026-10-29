"""Strict v49 CPU_PM roundtrip scope and proof binding."""
import hashlib, json, re, shutil, tempfile
from pathlib import Path
from prepare_cpu_pm_roundtrip import KCONFIG, OPTION, SCHEMA_VERSION, TARGETS, prepare, snapshot, validate_transform

HERE=Path(__file__).resolve().parent
SOURCES=('prepare_cpu_pm_roundtrip.py','prepare_cpu_pm_roundtrip_flow_compat.py','test_cpu_pm_roundtrip.py','decode_cpu_pm_roundtrip.py','test_cpu_pm_roundtrip_decoder.py','cpu_pm_roundtrip_binding.py','test_cpu_pm_roundtrip_binding.py','test_cpu_pm_roundtrip_package_flow.py')
PACKAGE_SOURCES=('prepare_linux_boot.py','build_boot_test_packages.py','precheck_window_access.py','stage_phase2.py','collect_reservation.py','decode_cpu_pm_roundtrip.py')
PREFIX='cpu_pm_roundtrip_'
MARKER=b'N10CPMRT1'
PREPARED='cpu-pm-roundtrip-prepared'
NATIVE='cpu-pm-roundtrip-model'
BINDING='cpu-pm-roundtrip-binding-model'
PACKAGE='cpu-pm-roundtrip-package-flow-model'
DECODER='cpu-pm-roundtrip-decoder-model'
FIELDS=('cpu_pm_roundtrip_version','cpu_pm_roundtrip_baseline_sha256','cpu_pm_roundtrip_prepared_sha256','cpu_pm_roundtrip_snapshot_sha256','cpu_pm_roundtrip_sources_sha256','cpu_pm_roundtrip_package_sources_sha256','cpu_pm_roundtrip_model_sha256','cpu_pm_roundtrip_decoder_sha256','cpu_pm_roundtrip_binding_sha256','cpu_pm_roundtrip_package_flow_sha256')

def sha(raw): return hashlib.sha256(raw).hexdigest()
def _hash(v): return isinstance(v,str) and re.fullmatch(r'[0-9a-f]{64}',v) is not None
def _map(v,keys): return isinstance(v,dict) and set(v)==set(keys) and all(_hash(x) for x in v.values())
def _filemap(root,keys):
 root=Path(root);out={}
 for n in keys:
  p=root/n
  if p.is_symlink() or not p.is_file(): raise ValueError('missing/unsafe source: '+n)
  out[n]=sha(p.read_bytes())
 return out
def _files(root): return {p.relative_to(root).as_posix() for p in Path(root).rglob('*') if p.is_file() and not p.is_symlink()}

def package_scope(metadata):
 if not isinstance(metadata,dict): raise ValueError('CPU_PM metadata must be an object')
 from ehld_running_lock_binding import package_scope as prior_scope
 prior=prior_scope(metadata)
 if type(prior) is not bool: raise ValueError('prior v48 scope malformed')
 flag=metadata.get('cpu_pm_roundtrip')
 if 'cpu_pm_roundtrip' in metadata and type(flag) is not bool: raise ValueError('CPU_PM flag must be bool or absent')
 version=metadata.get('cpu_pm_roundtrip_version')
 if flag is True:
  if type(version) is not int or version!=SCHEMA_VERSION or prior is not True or metadata.get('auto_return_diagnostic') is not True: raise ValueError('CPU_PM opt-in requires v48 and automatic recovery')
  return True
 if version is not None: raise ValueError('CPU_PM version is stray while disabled')
 stray=[k for k in metadata if k.startswith(PREFIX) and k not in ('cpu_pm_roundtrip','cpu_pm_roundtrip_version')]
 if stray: raise ValueError('CPU_PM evidence is stray while disabled')
 return False

def assert_scope(root,build):
 root=Path(root)
 if not isinstance(build,dict): raise ValueError('CPU_PM build metadata must be an object')
 flag=build.get('cpu_pm_roundtrip')
 if 'cpu_pm_roundtrip' in build and type(flag) is not bool: raise ValueError('CPU_PM flag malformed')
 enabled=flag is True
 configp=root/'handoff.config'
 if configp.is_symlink() or not configp.is_file(): raise ValueError('config missing or unsafe')
 cfg=configp.read_bytes(); lines=cfg.splitlines(); opt=OPTION.encode()
 entries=[line for line in lines if opt in line]
 if enabled:
  if entries != [opt+b'=y']: raise ValueError('CPU_PM Kconfig must be uniquely enabled')
  deps=(b'CONFIG_NOTE10_EHLD_RUNNING_LOCK_AUDIT=y',b'CONFIG_NOTE10_EHLD_IRQSAVE_AUDIT=y',b'CONFIG_NOTE10_EHLD_LOCK_AUDIT=y',b'CONFIG_NOTE10_CPU_PM_PRECONDITIONS=y',b'CONFIG_NOTE10_PM_IRQ_TEST=y')
  if any(x not in lines for x in deps): raise ValueError('CPU_PM Kconfig dependencies missing')
 elif entries not in ([],[opt+b'=n'],[b'# '+opt+b' is not set']): raise ValueError('CPU_PM disabled Kconfig malformed')
 if 'effective_config_sha256' in build and build['effective_config_sha256']!=sha(cfg): raise ValueError('effective config hash differs')
 if enabled and 'effective_config_sha256' not in build: raise ValueError('effective config hash missing')
 image_path=root/'Image'
 if image_path.is_symlink() or not image_path.is_file() or (MARKER in image_path.read_bytes()) is not enabled: raise ValueError('CPU_PM Image marker/scope differs')
 dirs=(PREPARED,NATIVE,DECODER,BINDING,PACKAGE)
 straydirs=[p.name for p in root.iterdir() if p.name.startswith('cpu-pm-roundtrip-') and p.name not in dirs]
 if not enabled:
  allowed={'cpu_pm_roundtrip','cpu_pm_roundtrip_version'}
  if any(k.startswith(PREFIX) and k not in allowed for k in build): raise ValueError('disabled CPU_PM proof metadata')
  if 'cpu_pm_roundtrip_version' in build and build['cpu_pm_roundtrip_version'] is not None: raise ValueError('disabled CPU_PM version is stray')
  if any((root/d).exists() for d in dirs) or straydirs: raise ValueError('disabled CPU_PM evidence exists')
  return False
 if type(build.get('cpu_pm_roundtrip_version')) is not int or build['cpu_pm_roundtrip_version']!=SCHEMA_VERSION: raise ValueError('CPU_PM schema version invalid')
 if build.get('ehld_running_lock_audit') is not True or build.get('auto_return_diagnostic') is not True: raise ValueError('CPU_PM requires EHLD running-lock and automatic recovery')
 # Full previous schema and native evidence are chained before accepting the new source.
 from ehld_running_lock_binding import validate as validate_prior
 prior=validate_prior(root,build,require_package_flow=False)
 if type(prior) is not bool or prior is not True: raise ValueError('v48 EHLD running-lock prerequisite invalid')
 baseline=build.get('ehld_running_lock_snapshot_sha256')
 if not isinstance(baseline,dict) or len(baseline)!=78: raise ValueError('v48 78-source baseline map missing')
 if any(Path(k).is_absolute() or Path(k).as_posix()!=k or '..' in Path(k).parts or not _hash(v) for k,v in baseline.items()): raise ValueError('invalid v48 baseline map')
 base=root/'ehld-running-lock-prepared'; prepared=root/PREPARED
 if _files(base)!=set(baseline) or _filemap(base,baseline)!=baseline: raise ValueError('v48 source baseline mismatch')
 current=build.get('cpu_pm_roundtrip_snapshot_sha256')
 if not _map(current,baseline) or _files(prepared)!=set(baseline) or _filemap(prepared,baseline)!=current: raise ValueError('v49 snapshot map/file mismatch')
 changed={n for n in baseline if current[n]!=baseline[n]}
 if changed!=set(TARGETS): raise ValueError('v49 changed source set differs')
 if build.get('cpu_pm_roundtrip_baseline_sha256')!={n:baseline[n] for n in TARGETS}: raise ValueError('v49 baseline target map differs')
 if build.get('cpu_pm_roundtrip_prepared_sha256')!={n:current[n] for n in TARGETS}: raise ValueError('v49 prepared target map differs')
 validate_transform({n:(base/n).read_bytes() for n in TARGETS},{n:(prepared/n).read_bytes() for n in TARGETS})
 if not _map(build.get('cpu_pm_roundtrip_sources_sha256'),SOURCES) or build['cpu_pm_roundtrip_sources_sha256']!=_filemap(HERE,SOURCES): raise ValueError('v49 source map differs')
 if not _map(build.get('cpu_pm_roundtrip_package_sources_sha256'),PACKAGE_SOURCES) or build['cpu_pm_roundtrip_package_sources_sha256']!=_filemap(HERE,PACKAGE_SOURCES): raise ValueError('v49 package source map differs')
 native=root/NATIVE
 if native.is_symlink() or not native.is_dir(): raise ValueError('v49 native proof missing')
 nraw=(native/'result.json').read_bytes()
 if sha(nraw)!=build.get('cpu_pm_roundtrip_model_sha256'): raise ValueError('v49 native proof hash mismatch')
 proof=json.loads(nraw)
 from test_cpu_pm_roundtrip import CASES,TRANSFORM_CASES
 if proof.get('schema_version') != 1 or proof.get('passed') is not True or proof.get('hardware_verified') is not False or proof.get('cases')!=list(CASES) or proof.get('transform_cases')!=list(TRANSFORM_CASES): raise ValueError('v49 native proof contract differs')
 if proof.get('harness_sha256')!=sha((HERE/'test_cpu_pm_roundtrip.py').read_bytes()): raise ValueError('v49 native harness hash differs')
 if proof.get('production_source_sha256')!=_filemap(prepared,TARGETS) or proof.get('baseline_source_sha256')!=_filemap(base,TARGETS): raise ValueError('v49 native source hashes differ')
 from test_cpu_pm_roundtrip import TRANSCRIPTS
 if (not _map(proof.get('case_log_sha256'),CASES) or not _hash(proof.get('generated_sha256')) or
     proof.get('compile_log_sha256')!=sha((native/'compile.log').read_bytes()) or
     proof.get('case_transcripts')!={name:'PASS|'+'|'.join(str(x) for x in TRANSCRIPTS[name]) for name in CASES}):
  raise ValueError('v49 native outputs not bound')
 if sha((native/'roundtrip.c').read_bytes())!=proof['generated_sha256']:
  raise ValueError('v49 generated native source hash differs')
 for index,case in enumerate(CASES):
  lp=native/(f'case-{index:02d}.log')
  if lp.is_symlink() or not lp.is_file() or sha(lp.read_bytes())!=proof['case_log_sha256'][case]: raise ValueError('v49 native case log differs: '+case)
 if proof.get('transform_mutations_rejected') != {name:True for name in TRANSFORM_CASES}: raise ValueError('v49 transform mutation results differ')
 decoder=root/DECODER
 if decoder.is_symlink() or not decoder.is_dir():raise ValueError('v49 decoder proof missing')
 draw=(decoder/'result.json').read_bytes()
 if sha(draw)!=build.get('cpu_pm_roundtrip_decoder_sha256'):raise ValueError('v49 decoder proof hash differs')
 dp=json.loads(draw)
 from test_cpu_pm_roundtrip_decoder import CASES as DC
 if (dp.get('schema_version')!=1 or dp.get('passed') is not True or dp.get('hardware_verified') is not False or
     dp.get('cases')!=list(DC) or dp.get('decoder_sha256')!=sha((HERE/'decode_cpu_pm_roundtrip.py').read_bytes()) or
     dp.get('harness_sha256')!=sha((HERE/'test_cpu_pm_roundtrip_decoder.py').read_bytes())):raise ValueError('v49 decoder proof contract differs')
 from test_cpu_pm_roundtrip_decoder import EXPECTED as decoder_expected,input_vector
 if dp.get('case_results')!=decoder_expected():raise ValueError('v49 decoder mutation outcomes differ')
 expected_transcripts={case:('PASS|' if case=='valid-pair' else 'REJECT|')+case for case in DC}
 expected_generated={case:sha(input_vector(case)) for case in DC}
 if dp.get('case_transcripts')!=expected_transcripts or dp.get('generated_sha256')!=expected_generated:raise ValueError('v49 decoder vectors/transcripts differ')
 if not _map(dp.get('generated_sha256'),DC) or not _map(dp.get('logs_sha256'),DC):raise ValueError('v49 decoder case maps differ')
 for case in DC:
  code=decoder/(case+'.json');log=decoder/(case+'.log')
  expected_log=expected_transcripts[case]+'\n'
  if (code.is_symlink() or log.is_symlink() or not code.is_file() or not log.is_file() or
      sha(code.read_bytes())!=dp['generated_sha256'][case] or sha(log.read_bytes())!=dp['logs_sha256'][case] or
      log.read_text(encoding='utf8')!=expected_log):raise ValueError('v49 decoder case evidence differs: '+case)
 return True


def validate(root,build,require_package_flow=True):
 root=Path(root)
 scope=assert_scope(root,build)
 if scope is not True:return False
 if require_package_flow is not False and require_package_flow is not True:raise ValueError('require_package_flow must be bool')
 binding=root/BINDING
 if binding.is_symlink() or not binding.is_dir():raise ValueError('v49 binding proof missing')
 braw=(binding/'result.json').read_bytes()
 if sha(braw)!=build.get('cpu_pm_roundtrip_binding_sha256'):raise ValueError('v49 binding proof hash mismatch')
 bp=json.loads(braw)
 from test_cpu_pm_roundtrip_binding import CASES as BC,PACKAGE_SCOPE_CASES
 if (bp.get('passed') is not True or bp.get('hardware_verified') is not False or bp.get('cases')!=list(BC) or
     bp.get('package_scope_cases')!=list(PACKAGE_SCOPE_CASES) or
     bp.get('harness_sha256')!=sha((HERE/'test_cpu_pm_roundtrip_binding.py').read_bytes()) or
     bp.get('binding_sha256')!=sha((HERE/'cpu_pm_roundtrip_binding.py').read_bytes())):raise ValueError('v49 binding proof contract differs')
 if not _map(bp.get('generated_sha256'),BC) or not _map(bp.get('logs_sha256'),BC):raise ValueError('v49 binding case maps differ')
 for case in BC:
  code=binding/(case+'.py');log=binding/(case+'.log')
  if code.is_symlink() or log.is_symlink() or not code.is_file() or not log.is_file() or sha(code.read_bytes())!=bp['generated_sha256'][case] or sha(log.read_bytes())!=bp['logs_sha256'][case]:raise ValueError('v49 binding mutation evidence differs: '+case)
 if require_package_flow:
  package=root/PACKAGE
  if package.is_symlink() or not package.is_dir():raise ValueError('v49 package-flow proof missing')
  raw=(package/'result.json').read_bytes()
  if sha(raw)!=build.get('cpu_pm_roundtrip_package_flow_sha256'):raise ValueError('v49 package-flow digest differs')
  proof=json.loads(raw)
  if (proof.get('passed') is not True or proof.get('hardware_verified') is not False or
      proof.get('synthetic_fixture') is not True or proof.get('legacy_gate_stubs')!=['ehld_lock','ehld_irqsave','ehld_running_lock'] or
      proof.get('harness_sha256')!=sha((HERE/'test_cpu_pm_roundtrip_package_flow.py').read_bytes()) or
      proof.get('package_sources_sha256')!=_filemap(HERE,PACKAGE_SOURCES)):
   raise ValueError('v49 package-flow proof contract differs')
  if proof.get('cases')!=['production-flow-on','production-flow-off','invalid-scope-rejected'] or proof.get('precheck_cases')!=['on','off','invalid-pair'] or proof.get('collector_cases')!=['on','off','invalid-pair']:
   raise ValueError('v49 production flow inventory differs')
  expected_flow=[
   {'case':'production-flow-on','accepted':True,'scope':True,'diagnostic':True,'rollback':False},
   {'case':'production-flow-off','accepted':True,'scope':False,'diagnostic':False,'rollback':False},
   {'case':'invalid-scope-rejected','accepted':False},
  ]
  if proof.get('case_results')!=expected_flow or proof.get('precheck_cases_result')!=[
      {'case':'on','accepted':True,'scope':True,'ready':True,'partition_writes':False},
      {'case':'off','accepted':True,'scope':False,'ready':True,'partition_writes':False},
      {'case':'invalid-pair','accepted':False}]:
   raise ValueError('v49 prepare/package/precheck E2E outcomes differ')
  if proof.get('collector_cases_result')!=[
      {'case':'on','accepted':True,'evaluation_items':40,'scope':True},
      {'case':'off','accepted':True,'evaluation_items':39,'scope':False},
      {'case':'invalid-pair','accepted':False}]:
   raise ValueError('v49 collector E2E outcomes differ')
  on_items=proof.get('collector_evaluation_items');off_items=proof.get('collector_evaluation_items_off')
  if (not isinstance(on_items,dict) or not isinstance(off_items,dict) or len(on_items)!=40 or len(off_items)!=39 or
      {key:value for key,value in on_items.items() if key!='cpu0_cpu_pm_enter_exit_pair'}!=off_items or
      on_items.get('cpu0_cpu_pm_enter_exit_pair')!={'required':True,'status':'failed'} or
      proof.get('collector_evaluation_items_sha256')!=sha(json.dumps(on_items,sort_keys=True,separators=(',',':')).encode())):
   raise ValueError('v49 collector retained rows/new required row differs')
 return True
