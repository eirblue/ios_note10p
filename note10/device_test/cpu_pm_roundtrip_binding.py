"""Strict v49 CPU_PM roundtrip scope and proof binding."""
import hashlib, json, re, shutil, tempfile
from pathlib import Path
from prepare_cpu_pm_roundtrip import KCONFIG, OPTION, SCHEMA_VERSION, TARGETS, prepare, snapshot, validate_transform

HERE=Path(__file__).resolve().parent
SOURCES=('prepare_cpu_pm_roundtrip.py','prepare_cpu_pm_roundtrip_flow_compat.py','test_cpu_pm_roundtrip.py','decode_cpu_pm_roundtrip.py','test_cpu_pm_roundtrip_decoder.py','test_cpu_pm_notifier_counts.py','cpu_pm_roundtrip_binding.py','test_cpu_pm_roundtrip_binding.py','test_cpu_pm_roundtrip_package_flow.py')
PACKAGE_SOURCES=('prepare_linux_boot.py','build_boot_test_packages.py','precheck_window_access.py','stage_phase2.py','collect_reservation.py','decode_cpu_pm_roundtrip.py','decode_cpu_pm_notifier_trace.py')
PREFIX='cpu_pm_roundtrip_'
MARKER=b'N10CPMRT1'
TERMINAL_MARKER=b'N10CPT1'
PREPARED='cpu-pm-roundtrip-prepared'
NATIVE='cpu-pm-roundtrip-model'
BINDING='cpu-pm-roundtrip-binding-model'
PACKAGE='cpu-pm-roundtrip-package-flow-model'
DECODER='cpu-pm-roundtrip-decoder-model'
COUNTS='cpu-pm-notifier-counts-model'
FIELDS=('cpu_pm_roundtrip_version','cpu_pm_roundtrip_baseline_sha256','cpu_pm_roundtrip_prepared_sha256','cpu_pm_roundtrip_snapshot_sha256','cpu_pm_roundtrip_sources_sha256','cpu_pm_roundtrip_package_sources_sha256','cpu_pm_roundtrip_model_sha256','cpu_pm_roundtrip_decoder_sha256','cpu_pm_roundtrip_binding_sha256','cpu_pm_roundtrip_package_flow_sha256')
COUNTS_FLAG='cpu_pm_notifier_counts'
COUNTS_VERSION='cpu_pm_notifier_counts_version'
COUNTS_PREFIX='cpu_pm_notifier_counts_'
COUNTS_MARKER=b'N10CPNC1'

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

def _legacy_helper_executable(root):
 candidates=[Path(root)/name for name in ('legacy-roundtrip-helper','legacy-roundtrip-helper.exe')]
 if any(p.is_symlink() or (p.exists() and not p.is_file()) for p in candidates):
  raise ValueError('legacy CPU_PM helper executable missing/unsafe/ambiguous')
 files=[p for p in candidates if p.is_file()]
 if len(files)!=1:raise ValueError('legacy CPU_PM helper executable missing/unsafe/ambiguous')
 return files[0]

def _native_transcript_profiles(cases,transcripts):
 cases=tuple(cases)
 if len(cases)!=22 or len(set(cases))!=22 or set(transcripts)!=set(cases):
  raise ValueError('CPU_PM native transcript case set differs')
 windows={name:'PASS|'+'|'.join(str(x) for x in transcripts[name]) for name in cases}
 linux=dict(windows)
 for name in ('nested-active','repeat-generation'):
  fields=windows.get(name,'').split('|')
  if len(fields)!=9 or fields[2] not in ('-103','-114'):
   raise ValueError('CPU_PM known errno ABI anchors differ')
  windows_fields=list(fields); windows_fields[2]='-103'
  linux_fields=list(fields); linux_fields[2]='-114'
  windows[name]='|'.join(windows_fields)
  linux[name]='|'.join(linux_fields)
 return {'linux-ealready-114':(linux,b'\n'),
         'windows-ealready-103':(windows,b'\r\n')}

def _cpu_pm_terminal_transcript_profiles(cases):
 expected_cases=(
  'caller-context-refusal','prior-chain-refusal','helper-admission-refusal',
  'enter-failure','exit-failure','postcondition-failure','strict-success-no-terminal',
  'outer-only-postcondition','helper-reentry-unattempted','probe-read-failure-after-pair')
 if tuple(cases)!=expected_cases: raise ValueError('CPU_PM terminal case set differs')
 common={
  'caller-context-refusal':'PASS|0|-1|-1|0|0|0|0|0|-1|0|-1|0',
  'prior-chain-refusal':'PASS|1|-5|-5|1|0|0|0|0|-5|0|-5|0',
  'helper-admission-refusal':'PASS|2|-16|-16|2|1|1|0|0|0|-16|-16|-16',
  'enter-failure':'PASS|3|-5|-5|3|1|1|1|0|0|-5|-5|-5',
  'exit-failure':'PASS|4|-5|-5|4|1|1|1|1|0|-5|-5|-5',
  'postcondition-failure':'PASS|5|-5|-5|5|1|1|1|1|0|-5|-5|-5',
  'strict-success-no-terminal':'PASS|6|0|0|0|0|0|0|0|0|0|0',
  'outer-only-postcondition':'PASS|7|-5|-5|5|1|1|1|1|-5|0|-5|0',
  'probe-read-failure-after-pair':'PASS|9|0|-5|5|1|1|1|1|0|0|-5|0'}
 profiles={}
 for profile,errno in (('linux-ealready-114',-114),('windows-ealready-103',-103)):
  expected=dict(common)
  expected['helper-reentry-unattempted']=(
   f'PASS|8|{errno}|{errno}|2|0|1|0|0|0|{errno}|{errno}|{errno}')
  profiles[profile]=expected
 return profiles

def _select_cpu_pm_terminal_profile(transcripts):
 from test_cpu_pm_roundtrip import TERMINAL_CASES
 if not isinstance(transcripts,dict): return None
 profiles=_cpu_pm_terminal_transcript_profiles(TERMINAL_CASES)
 if set(transcripts)!=set(TERMINAL_CASES): return None
 matches=[name for name,expected in profiles.items() if transcripts==expected]
 return matches[0] if len(matches)==1 else None

def _validate_native_transcript_proof(proof,native):
 from test_cpu_pm_roundtrip import CASES,TRANSCRIPTS
 profiles=_native_transcript_profiles(CASES,TRANSCRIPTS)
 observed=proof.get('case_transcripts')
 profile=next((name for name,(expected,_ending) in profiles.items() if observed==expected),None)
 if profile is None:
  raise ValueError('v49 native transcript map is not an exact Linux/Windows ABI profile')
 log_hashes=proof.get('case_log_sha256')
 if not _map(log_hashes,CASES):
  raise ValueError('v49 native case log hash map differs')
 expected,ending=profiles[profile]
 for index,case in enumerate(CASES):
  path=Path(native)/(f'case-{index:02d}.log')
  if path.is_symlink() or not path.is_file():
   raise ValueError('v49 native case log missing/unsafe: '+case)
  raw=path.read_bytes()
  if sha(raw)!=log_hashes[case] or raw!=(expected[case].encode('ascii')+ending):
   raise ValueError('v49 native transcript/log content differs: '+case)
 return profile

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

def counts_package_scope(metadata,allow_build_proof=False):
 if not isinstance(metadata,dict):raise ValueError('CPU_PM notifier-count metadata must be an object')
 if type(allow_build_proof) is not bool:raise ValueError('allow_build_proof must be bool')
 roundtrip=package_scope(metadata)
 flag=metadata.get(COUNTS_FLAG,False)
 if type(flag) is not bool:raise ValueError('CPU_PM notifier-count flag must be bool or absent')
 version=metadata.get(COUNTS_VERSION)
 if flag:
  if not roundtrip or type(version) is not int or version!=1:raise ValueError('CPU_PM notifier counts require versioned roundtrip scope')
 elif version is not None:raise ValueError('CPU_PM notifier-count version is stray while disabled')
 allowed={COUNTS_FLAG,COUNTS_VERSION}
 if flag and allow_build_proof:allowed.update({'cpu_pm_notifier_counts_sources_sha256','cpu_pm_notifier_counts_model_sha256'})
 stray=[k for k in metadata if k.startswith(COUNTS_PREFIX) and k not in allowed]
 if stray:raise ValueError('CPU_PM notifier-count proof is stray while disabled')
 return flag

def trace_package_scope(metadata,allow_build_proof=False):
 from prepare_cpu_pm_notifier_trace import FLAG,VERSION,PREFIX
 if not isinstance(metadata,dict) or type(allow_build_proof) is not bool:
  raise ValueError('CPU_PM dispatch metadata/options malformed')
 counts=counts_package_scope(metadata,allow_build_proof=allow_build_proof)
 flag=metadata.get(FLAG,False)
 if type(flag) is not bool:raise ValueError('CPU_PM dispatch flag must be bool')
 version=metadata.get(VERSION)
 if flag:
  if not counts or type(version) is not int or version!=1:raise ValueError('CPU_PM dispatch requires versioned counts')
 elif version is not None:raise ValueError('disabled CPU_PM dispatch version is stray')
 allowed={VERSION}
 if flag and allow_build_proof:
  allowed.update(PREFIX+n for n in ('baseline_sha256','prepared_sha256','sources_sha256','model_sha256','package_sha256','link_symbols','link_verified'))
 if any(k.startswith(PREFIX) and k not in allowed for k in metadata):
  raise ValueError('CPU_PM dispatch proof metadata is stray or unknown')
 return flag

def _validate_trace(root,build,require_package_flow=False):
 from prepare_cpu_pm_notifier_trace import (FLAG,PREFIX,OPTION,MARKER,BASE,PREPARED,
  MODEL,PACKAGE,TARGETS as DT,SOURCES as DS,transform as dispatch_transform)
 root=Path(root);enabled=trace_package_scope(build,allow_build_proof=True)
 entries=[line for line in (root/'handoff.config').read_bytes().splitlines() if OPTION.encode() in line]
 if enabled:
  if entries!=[OPTION.encode()+b'=y']:raise ValueError('CPU_PM dispatch config scope differs')
 elif entries not in ([],[OPTION.encode()+b'=n'],[b'# '+OPTION.encode()+b' is not set']):
  raise ValueError('CPU_PM dispatch disabled config malformed')
 if (MARKER in (root/'Image').read_bytes()) is not enabled:raise ValueError('CPU_PM dispatch Image scope differs')
 dirs=(BASE,PREPARED,MODEL,PACKAGE)
 if any(p.name.startswith('cpu-pm-notifier-trace-') and p.name not in dirs for p in root.iterdir()):
  raise ValueError('unknown CPU_PM dispatch output directory')
 if not enabled:
  if any((root/name).exists() or (root/name).is_symlink() for name in dirs):raise ValueError('disabled CPU_PM dispatch evidence exists')
  return False
 if build.get(PREFIX+'sources_sha256')!=_filemap(HERE,DS):raise ValueError('CPU_PM dispatch source closure differs')
 expected_link=['n10_dispatch_arm','n10_dispatch_begin','n10_dispatch_disarm','n10_dispatch_finish','n10_dispatch_marker','n10_dispatch_observe','n10_dispatch_seed']
 if build.get(PREFIX+'link_verified') is not True or build.get(PREFIX+'link_symbols')!=expected_link:
  raise ValueError('CPU_PM dispatch private kernel link proof differs')
 maps=[];inputs=[]
 for dirname,key in ((BASE,'baseline_sha256'),(PREPARED,'prepared_sha256')):
  directory=root/dirname
  if directory.is_symlink() or not directory.is_dir() or any(p.is_symlink() for p in directory.rglob('*')):
   raise ValueError('CPU_PM dispatch snapshot unsafe')
  if _files(directory)!=set(DT):raise ValueError('CPU_PM dispatch snapshot inventory differs')
  mapping=_filemap(directory,DT)
  if not _map(build.get(PREFIX+key),DT) or build[PREFIX+key]!=mapping:raise ValueError('CPU_PM dispatch snapshot hash differs')
  maps.append(mapping);inputs.append({n:(directory/n).read_bytes() for n in DT})
 if dispatch_transform(inputs[0])!=inputs[1]:raise ValueError('CPU_PM composed dispatch transformation differs')
 for name in DT:
  if name!='kernel/notifier.c' and sha((root/'cpu-pm-roundtrip-prepared'/name).read_bytes())!=maps[0][name]:
   raise ValueError('CPU_PM dispatch baseline differs from validated v52 composition')
 proof_root=root/MODEL
 if proof_root.is_symlink() or not proof_root.is_dir() or any(p.is_symlink() for p in proof_root.rglob('*')):
  raise ValueError('CPU_PM dispatch model unsafe')
 raw=(proof_root/'result.json').read_bytes()
 if sha(raw)!=build.get(PREFIX+'model_sha256'):raise ValueError('CPU_PM dispatch model digest differs')
 proof=json.loads(raw)
 from test_cpu_pm_notifier_trace import NATIVE_CASES,PARSER_CASES,native_source,disabled_source
 if (proof.get('passed') is not True or proof.get('synthetic_only') is not True or
     proof.get('hardware_verified') is not False or proof.get('native_cases')!=list(NATIVE_CASES) or
     proof.get('parser_cases')!=list(PARSER_CASES) or proof.get('source_sha256')!=maps[1] or
     proof.get('baseline_sha256')!=maps[0] or proof.get('sources_sha256')!=_filemap(HERE,DS) or
     proof.get('original_callback_operand_preserved') is not True or
     proof.get('original_notify_enter_exit_preserved') is not True):
  raise ValueError('CPU_PM dispatch model contract/source differs')
 if proof.get('generated_sha256')!=sha(native_source(inputs[1])) or proof.get('disabled_source_sha256')!=sha(disabled_source(inputs[1])):
  raise ValueError('CPU_PM dispatch generated source differs from actual extracted production functions')
 for filename,key in (('dispatch-native.c','generated_sha256'),('compile.log','compile_log_sha256'),('native.log','native_log_sha256'),('parser.log','parser_log_sha256'),('parser-vectors.json','parser_vectors_sha256'),('dispatch-disabled.c','disabled_source_sha256'),('disabled-compile.log','disabled_compile_log_sha256'),('disabled-native.log','disabled_native_log_sha256')):
  if proof.get(key)!=sha((proof_root/filename).read_bytes()):raise ValueError('CPU_PM dispatch native evidence differs')
 candidates=[proof_root/n for n in ('dispatch-native','dispatch-native.exe')]
 if any(p.is_symlink() or (p.exists() and not p.is_file()) for p in candidates):raise ValueError('CPU_PM dispatch executable unsafe')
 executables=[p for p in candidates if p.is_file()]
 if len(executables)!=1 or proof.get('executable_sha256')!=sha(executables[0].read_bytes()):raise ValueError('CPU_PM dispatch executable missing/ambiguous/hash differs')
 expected_native=''.join('PASS|'+name+'\n' for name in NATIVE_CASES)
 if (proof_root/'native.log').read_text(encoding='ascii')!=expected_native:raise ValueError('CPU_PM dispatch native case transcript differs')
 if proof.get('parser_results')!={name:True for name in PARSER_CASES}:raise ValueError('CPU_PM dispatch parser outcomes differ')
 if (proof_root/'parser.log').read_text(encoding='ascii')!=''.join('PASS|'+name+'\n' for name in PARSER_CASES):raise ValueError('CPU_PM dispatch parser case transcript differs')
 candidates=[proof_root/n for n in ('dispatch-disabled','dispatch-disabled.exe')]
 if any(p.is_symlink() or (p.exists() and not p.is_file()) for p in candidates):raise ValueError('disabled dispatch executable unsafe')
 executables=[p for p in candidates if p.is_file()]
 if (len(executables)!=1 or proof.get('disabled_executable_sha256')!=sha(executables[0].read_bytes()) or
     MARKER in executables[0].read_bytes() or proof.get('disabled_marker_absent') is not True or
     (proof_root/'disabled-native.log').read_text(encoding='ascii')!='PASS|trace-disabled-original-semantics\n'):
  raise ValueError('disabled dispatch native behavior/marker binding differs')
 if require_package_flow:
  path=root/PACKAGE
  if path.is_symlink() or not path.is_dir() or any(p.is_symlink() for p in path.rglob('*')):raise ValueError('CPU_PM dispatch package proof unsafe')
  raw=(path/'result.json').read_bytes()
  if sha(raw)!=build.get(PREFIX+'package_sha256'):raise ValueError('CPU_PM dispatch package proof hash differs')
  package=json.loads(raw)
  from test_cpu_pm_notifier_trace_package import CASES as PC
  if (package.get('passed') is not True or package.get('synthetic_fixture') is not True or
      package.get('hardware_verified') is not False or package.get('cases')!=list(PC) or
      package.get('results')!={name:True for name in PC} or package.get('sources_sha256')!=_filemap(HERE,DS) or
      package.get('package_sources_sha256')!=_filemap(HERE,PACKAGE_SOURCES) or
      package.get('cpu_pm_validator_scope_only_stub') is not True):
   raise ValueError('CPU_PM dispatch package proof contract differs')
 return True

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
 counts_enabled=counts_package_scope(build,allow_build_proof=True)
 counts_opt=b'CONFIG_NOTE10_CPU_PM_NOTIFIER_COUNTS'
 counts_entries=[line for line in lines if counts_opt in line]
 if counts_enabled:
  if not enabled or counts_entries != [counts_opt+b'=y']:raise ValueError('CPU_PM notifier-count Kconfig scope differs')
 elif counts_entries not in ([],[counts_opt+b'=n'],[b'# '+counts_opt+b' is not set']):
  raise ValueError('CPU_PM notifier-count disabled Kconfig malformed')
 if 'effective_config_sha256' in build and build['effective_config_sha256']!=sha(cfg): raise ValueError('effective config hash differs')
 if enabled and 'effective_config_sha256' not in build: raise ValueError('effective config hash missing')
 image_path=root/'Image'
 if image_path.is_symlink() or not image_path.is_file():raise ValueError('CPU_PM Image missing/unsafe')
 image=image_path.read_bytes()
 if (MARKER in image) is not enabled or (TERMINAL_MARKER in image) is not enabled: raise ValueError('CPU_PM Image marker/scope differs')
 if (COUNTS_MARKER in image) is not counts_enabled:raise ValueError('CPU_PM notifier-count Image marker/scope differs')
 _validate_trace(root,build)
 dirs=(PREPARED,NATIVE,DECODER,BINDING,PACKAGE,COUNTS)
 straydirs=[p.name for p in root.iterdir() if p.name.startswith(('cpu-pm-roundtrip-','cpu-pm-notifier-counts-')) and p.name not in dirs]
 if not enabled:
  allowed={'cpu_pm_roundtrip','cpu_pm_roundtrip_version'}
  if any(k.startswith(PREFIX) and k not in allowed for k in build): raise ValueError('disabled CPU_PM proof metadata')
  if 'cpu_pm_roundtrip_version' in build and build['cpu_pm_roundtrip_version'] is not None: raise ValueError('disabled CPU_PM version is stray')
  if any((root/d).exists() for d in dirs) or straydirs: raise ValueError('disabled CPU_PM evidence exists')
  return False
 if type(build.get('cpu_pm_roundtrip_version')) is not int or build['cpu_pm_roundtrip_version']!=SCHEMA_VERSION: raise ValueError('CPU_PM schema version invalid')
 if counts_enabled and (type(build.get(COUNTS_VERSION)) is not int or build[COUNTS_VERSION]!=1):raise ValueError('CPU_PM notifier-count schema version invalid')
 if counts_enabled:
  if not _map(build.get('cpu_pm_notifier_counts_sources_sha256'),SOURCES) or build['cpu_pm_notifier_counts_sources_sha256']!=_filemap(HERE,SOURCES):raise ValueError('CPU_PM notifier-count source map differs')
  if not _hash(build.get('cpu_pm_notifier_counts_model_sha256')):raise ValueError('CPU_PM notifier-count model hash missing')
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
 counts_root=root/COUNTS
 if not counts_enabled and counts_root.exists():raise ValueError('disabled CPU_PM notifier-count proof exists')
 if counts_enabled:
  if counts_root.is_symlink() or not counts_root.is_dir():raise ValueError('CPU_PM notifier-count proof directory missing/unsafe')
  counts_raw=(counts_root/'result.json').read_bytes()
  if sha(counts_raw)!=build.get('cpu_pm_notifier_counts_model_sha256'):raise ValueError('CPU_PM notifier-count proof hash differs')
  counts_proof=json.loads(counts_raw)
  from test_cpu_pm_notifier_counts import CASES as COUNTS_CASES
  if (counts_proof.get('passed') is not True or counts_proof.get('synthetic_only') is not True or
      counts_proof.get('hardware_verified') is not False or counts_proof.get('cases')!=list(COUNTS_CASES) or
      counts_proof.get('old_native_and_decoder_models_reexecuted') is not False or
      counts_proof.get('count_marker_present') is not True or
      counts_proof.get('existing_pair_and_terminal_markers_preserved') is not True or
      counts_proof.get('transform_source_sha256')!=_filemap(prepared,TARGETS) or
      counts_proof.get('baseline_target_sha256')!={n:baseline[n] for n in TARGETS}):
   raise ValueError('CPU_PM notifier-count proof contract/source binding differs')
  if (not _hash(counts_proof.get('generated_sha256')) or
      counts_proof['generated_sha256']!=sha((counts_root/'notifier-counts-native.c').read_bytes()) or
      counts_proof.get('compile_log_sha256')!=sha((counts_root/'compile.log').read_bytes()) or
      counts_proof.get('native_log_sha256')!=sha((counts_root/'native.log').read_bytes())):
   raise ValueError('CPU_PM notifier-count native outputs differ')
  legacy=counts_proof.get('legacy_helper_extraction_compile_only')
  legacy_root=counts_root/'legacy-helper-compile-only'
  legacy_executable=_legacy_helper_executable(legacy_root)
  if (not isinstance(legacy,dict) or legacy.get('passed') is not True or
      legacy.get('compiled_only') is not True or legacy.get('executed') is not False or
      legacy_root.is_symlink() or not legacy_root.is_dir() or
      legacy.get('generated_sha256')!=sha((legacy_root/'legacy-roundtrip-helper.c').read_bytes()) or
      legacy.get('compile_log_sha256')!=sha((legacy_root/'compile.log').read_bytes()) or
      legacy.get('executable_sha256')!=sha(legacy_executable.read_bytes()) or
      not _hash(legacy.get('extracted_helper_sha256')) or
      json.loads((legacy_root/'result.json').read_text(encoding='utf8'))!=legacy):
   raise ValueError('legacy CPU_PM helper extraction compile-only proof differs')
 native=root/NATIVE
 if native.is_symlink() or not native.is_dir(): raise ValueError('v49 native proof missing')
 nraw=(native/'result.json').read_bytes()
 if sha(nraw)!=build.get('cpu_pm_roundtrip_model_sha256'): raise ValueError('v49 native proof hash mismatch')
 proof=json.loads(nraw)
 from test_cpu_pm_roundtrip import CASES,TRANSFORM_CASES
 if proof.get('schema_version') != 1 or proof.get('passed') is not True or proof.get('hardware_verified') is not False or proof.get('cases')!=list(CASES) or proof.get('transform_cases')!=list(TRANSFORM_CASES): raise ValueError('v49 native proof contract differs')
 if proof.get('harness_sha256')!=sha((HERE/'test_cpu_pm_roundtrip.py').read_bytes()): raise ValueError('v49 native harness hash differs')
 if proof.get('production_source_sha256')!=_filemap(prepared,TARGETS) or proof.get('baseline_source_sha256')!=_filemap(base,TARGETS): raise ValueError('v49 native source hashes differ')
 if (not _map(proof.get('case_log_sha256'),CASES) or not _hash(proof.get('generated_sha256')) or
     proof.get('compile_log_sha256')!=sha((native/'compile.log').read_bytes())):
  raise ValueError('v49 native outputs not bound')
 _validate_native_transcript_proof(proof,native)
 if sha((native/'roundtrip.c').read_bytes())!=proof['generated_sha256']:
  raise ValueError('v49 generated native source hash differs')
 if proof.get('transform_mutations_rejected') != {name:True for name in TRANSFORM_CASES}: raise ValueError('v49 transform mutation results differ')
 tl=proof.get('terminal_lifecycle')
 from test_cpu_pm_roundtrip import TERMINAL_CASES,extract_terminal_functions
 capture=(prepared/'kernel/power/note10_pm_pre_capture.c').read_bytes()
 probe=(prepared/'arch/arm64/mm/note10_pm_pre_probe.c').read_bytes()
 capture_fn,reader_fn,emitter_fn,report_fn=extract_terminal_functions(capture,probe)
 terminal_profile=_select_cpu_pm_terminal_profile(tl.get('case_transcripts') if isinstance(tl,dict) else None)
 if terminal_profile is None: raise ValueError('v50 terminal transcript is not one exact Linux/Windows ABI profile')
 expected_terminal=_cpu_pm_terminal_transcript_profiles(TERMINAL_CASES)[terminal_profile]
 terminal_errno=-114 if terminal_profile=='linux-ealready-114' else -103
 if (not isinstance(tl,dict) or tl.get('passed') is not True or tl.get('hardware_verified') is not False or
     tl.get('cases')!=TERMINAL_CASES or tl.get('harness_sha256')!=sha((HERE/'test_cpu_pm_roundtrip.py').read_bytes()) or
     tl.get('source_capture_sha256')!=sha(capture) or tl.get('source_probe_sha256')!=sha(probe) or
     tl.get('extracted_capture_sha256')!=sha(capture_fn) or tl.get('extracted_reader_sha256')!=sha(reader_fn) or
     tl.get('extracted_emitter_sha256')!=sha(emitter_fn) or tl.get('extracted_report_sha256')!=sha(report_fn) or
     tl.get('case_transcripts')!=expected_terminal or
     tl.get('decoded_terminal_cases')!=TERMINAL_CASES or
     not isinstance(tl.get('emitted_frame_sha256'),dict) or set(tl['emitted_frame_sha256'])!=set(TERMINAL_CASES) or
     tl['emitted_frame_sha256'].get('strict-success-no-terminal') is not None or
     any(not _hash(tl['emitted_frame_sha256'].get(case)) for case in TERMINAL_CASES if case!='strict-success-no-terminal') or
     not _map(tl.get('case_log_sha256'),TERMINAL_CASES) or not _hash(tl.get('generated_sha256')) or
     not _hash(tl.get('compile_log_sha256'))):
  raise ValueError('v50 terminal caller/reader/probe proof contract differs')
 tlroot=native/'terminal-lifecycle'
 if tlroot.is_symlink() or not tlroot.is_dir():raise ValueError('v50 terminal native output missing/unsafe')
 if sha((tlroot/'terminal.c').read_bytes())!=tl['generated_sha256'] or sha((tlroot/'compile.log').read_bytes())!=tl['compile_log_sha256']:
  raise ValueError('v50 terminal generated C/compile evidence differs')
 for index,case in enumerate(TERMINAL_CASES):
  log=tlroot/(f'case-{index:02d}.log')
  if log.is_symlink() or not log.is_file() or sha(log.read_bytes())!=tl['case_log_sha256'][case]:
   raise ValueError('v50 terminal case evidence differs: '+case)
  lines=log.read_text(encoding='ascii').splitlines()
  if not lines or lines[0]!=expected_terminal[case]:raise ValueError('v50 terminal transcript differs: '+case)
  frames=[line[6:] for line in lines[1:] if line.startswith('FRAME|')]
  if case=='strict-success-no-terminal':
   if frames:raise ValueError('v50 successful capture emitted failure terminal')
  else:
   if len(frames)!=2:raise ValueError('v50 terminal frame copies missing: '+case)
   from decode_cpu_pm_roundtrip import decode_terminal
   parsed=decode_terminal('\n'.join(frames),'a'*32,42)
   frame_digest=sha(('\n'.join(frames)+'\n').encode('ascii'))
   fields=lines[0].split('|')
   if (frame_digest!=tl['emitted_frame_sha256'][case] or parsed.get('pair_passed') is not False or
       parsed.get('stage')!=int(fields[4]) or parsed.get('attempted')!=int(fields[5]) or
       parsed.get('caller_invoked') is not bool(int(fields[6]))):raise ValueError('v50 terminal output decode differs: '+case)
   if case=='helper-reentry-unattempted' and (
       parsed.get('outer_error')!=0 or parsed.get('helper_error')!=terminal_errno or
       parsed.get('probe_error')!=terminal_errno):
    raise ValueError('v50 helper-reentry frame is mixed/unknown ABI')
 decoder=root/DECODER
 if decoder.is_symlink() or not decoder.is_dir():raise ValueError('v49 decoder proof missing')
 draw=(decoder/'result.json').read_bytes()
 if sha(draw)!=build.get('cpu_pm_roundtrip_decoder_sha256'):raise ValueError('v49 decoder proof hash differs')
 dp=json.loads(draw)
 from test_cpu_pm_roundtrip_decoder import CASES as DC,TERMINAL_CASES as TC
 if (dp.get('schema_version')!=1 or dp.get('passed') is not True or dp.get('hardware_verified') is not False or
     dp.get('cases')!=list(DC) or dp.get('decoder_sha256')!=sha((HERE/'decode_cpu_pm_roundtrip.py').read_bytes()) or
     dp.get('harness_sha256')!=sha((HERE/'test_cpu_pm_roundtrip_decoder.py').read_bytes()) or
     dp.get('terminal_cases')!=list(TC)):raise ValueError('v50 decoder proof contract differs')
 from test_cpu_pm_roundtrip_decoder import EXPECTED as decoder_expected,input_vector,TERMINAL_EXPECTED,terminal_input_vector
 if dp.get('case_results')!=decoder_expected():raise ValueError('v49 decoder mutation outcomes differ')
 if dp.get('terminal_case_results')!=TERMINAL_EXPECTED():raise ValueError('v50 terminal decoder outcomes differ')
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
 terminal_expected={item['case']:('FAILURE-OBSERVED|' if item['accepted'] else 'REJECT|')+item['case'] for item in TERMINAL_EXPECTED()}
 terminal_vectors={case:sha(terminal_input_vector(case)) for case in TC}
 if (dp.get('terminal_case_transcripts')!=terminal_expected or
     dp.get('terminal_generated_sha256')!=terminal_vectors or
     not _map(dp.get('terminal_generated_sha256'),TC) or not _map(dp.get('terminal_logs_sha256'),TC)):
  raise ValueError('v50 terminal decoder vectors/transcripts differ')
 for index,case in enumerate(TC):
  code=decoder/('terminal-'+case+'.json');log=decoder/('terminal-'+case+'.log')
  expected_log=terminal_expected[case]+'\n'
  if (code.is_symlink() or log.is_symlink() or not code.is_file() or not log.is_file() or
      sha(code.read_bytes())!=dp['terminal_generated_sha256'][case] or
      sha(log.read_bytes())!=dp['terminal_logs_sha256'][case] or
      log.read_text(encoding='utf8')!=expected_log):
   raise ValueError('v50 terminal decoder case evidence differs: '+case)
 return True


def validate(root,build,require_package_flow=True):
 root=Path(root)
 scope=assert_scope(root,build)
 if scope is not True:return False
 if require_package_flow is not False and require_package_flow is not True:raise ValueError('require_package_flow must be bool')
 if require_package_flow:_validate_trace(root,build,require_package_flow=True)
 binding=root/BINDING
 if binding.is_symlink() or not binding.is_dir():raise ValueError('v49 binding proof missing')
 braw=(binding/'result.json').read_bytes()
 if sha(braw)!=build.get('cpu_pm_roundtrip_binding_sha256'):raise ValueError('v49 binding proof hash mismatch')
 bp=json.loads(braw)
 from test_cpu_pm_roundtrip_binding import CASES as BC,PACKAGE_SCOPE_CASES,TERMINAL_PROFILE_CASES
 expected_terminal_profiles=[
  {'case':'terminal-profile-linux','accepted':True,'selected_profile':'linux-ealready-114'},
  {'case':'terminal-profile-windows','accepted':True,'selected_profile':'windows-ealready-103'},
  {'case':'terminal-profile-mixed-rejected','accepted':False,'selected_profile':None},
  {'case':'terminal-profile-unknown-rejected','accepted':False,'selected_profile':None}]
 if (bp.get('passed') is not True or bp.get('hardware_verified') is not False or
     bp.get('immutable_v49_prior_validator_stubbed') is not True or bp.get('cases')!=list(BC) or
     bp.get('terminal_profile_cases')!=list(TERMINAL_PROFILE_CASES) or
     bp.get('terminal_profile_results')!=expected_terminal_profiles or
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
      proof.get('cpu_pm_validator_scope_only_stub') is not True or
      proof.get('harness_sha256')!=sha((HERE/'test_cpu_pm_roundtrip_package_flow.py').read_bytes()) or
      proof.get('package_sources_sha256')!=_filemap(HERE,PACKAGE_SOURCES)):
   raise ValueError('v49 package-flow proof contract differs')
  if proof.get('cases')!=['production-flow-on','production-flow-off','invalid-scope-rejected'] or proof.get('precheck_cases')!=['on','off','invalid-pair'] or proof.get('collector_cases')!=['on','off','invalid-pair']:
   raise ValueError('v49 production flow inventory differs')
  if proof.get('terminal_collector_cases')!=['strict-success','terminal-failure','success-failure-conflict'] or proof.get('terminal_collector_results')!=[
      {'case':'strict-success','accepted':True,'pair_observed':True,'required':True,'status':'passed'},
      {'case':'terminal-failure','accepted':True,'pair_observed':False,'terminal_failure_observed':True,'required':True,'status':'failed'},
      {'case':'success-failure-conflict','accepted':False}]:
   raise ValueError('v50 terminal collector outcomes differ')
  if proof.get('notifier_count_collector_cases')!=[
      'counts-on-pass','counts-on-partial-fails-only-count-row',
      'counts-on-mismatch-fails-only-count-row','counts-on-terminal-fails-both',
      'counts-off-retains-old-row-set'] or proof.get('notifier_count_collector_results')!=[
      {'case':'counts-on-pass','pair':'passed','counts':'passed'},
      {'case':'counts-on-partial-fails-only-count-row','pair':'passed','counts':'failed'},
      {'case':'counts-on-mismatch-fails-only-count-row','pair':'passed','counts':'failed'},
      {'case':'counts-on-terminal-fails-both','pair':'failed','counts':'failed'},
      {'case':'counts-off-retains-old-row-set','counts_row':False}]:
   raise ValueError('CPU_PM notifier-count collector outcomes differ')
  if proof.get('notifier_count_scope_cases')!=['counts-scope-on','counts-scope-off','counts-requires-roundtrip',
      'counts-scope-on-unknown-rejected','counts-scope-package-build-proof-rejected',
      'counts-scope-off-stray-proof-rejected','counts-scope-build-proof-allowed'] or proof.get('notifier_count_scope_results')!=[
      {'case':'counts-scope-on','accepted':True,'scope':True},
      {'case':'counts-scope-off','accepted':True,'scope':False},
      {'case':'counts-requires-roundtrip','accepted':False},
      {'case':'counts-scope-on-unknown-rejected','accepted':False},
      {'case':'counts-scope-package-build-proof-rejected','accepted':False},
      {'case':'counts-scope-off-stray-proof-rejected','accepted':False},
      {'case':'counts-scope-build-proof-allowed','accepted':True,'scope':True}]:
   raise ValueError('CPU_PM notifier-count package scopes differ')
  if proof.get('notifier_count_package_flow_cases')!=['counts-on-build-prepare-package-precheck-stage-collector'] or proof.get('notifier_count_package_flow_results')!=[
      {'case':'counts-on-build-prepare-package-precheck-stage-collector','build_flag':True,
       'prototype_marker':True,'diagnostic_scope':True,'rollback_scope':False,
       'precheck_scope':True,'collector_scope':True,'collector_rows':41,
       'legacy_rows_equal_off':True,'missing_log_counts_row':'failed'}]:
   raise ValueError('CPU_PM notifier-count package-flow scopes differ')
  if proof.get('collector_entry_failure_case')!={
      'case':'collect-entry-pmt-error-prq-failure-valid-terminal','accepted':True,
      'terminal_preserved':True,'pair_passed':False,'strict_pm_preconditions_rejected':True,
      'pm_timer_failure':'PM devices or timer roundtrip failed'}:
   raise ValueError('v50 actual collect-entry terminal preservation differs')
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
