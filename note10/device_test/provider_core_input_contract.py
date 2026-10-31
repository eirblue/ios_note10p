"""New v66 bounded two-artifact input/transport contract; no old proof calls."""
import hashlib,json,os,re,stat,subprocess,selectors,time,zipfile
from pathlib import Path,PurePosixPath
from crypto_hash_composite import require,digest

ROOT=Path(__file__).resolve().parents[2]
CONTROL='note10/device_test/provider_core_interface_control.json'
HELPER='note10/device_test/crypto_hash_composite.py'
HELPER_SHA='881c01a5ff6e00d91337c2190a516da094e28f186f36bfc996f68b651a382de2'
PUBLIC=tuple('note10/device_test/'+n for n in ('build_provider_core_interface.py','provider_core_interface.py','provider_core_input_contract.py','stage_provider_core_interface.py','test_provider_core_interface.py','provider_core_interface_control.json','crypto_hash_composite.py'))+('.github/workflows/note10-provider-core-interface.yml',)
NAMESPACE='v66-ci-interface'
ARTIFACT='note10-provider-core-interface-pc-only'
JOB='provider-core-interface'
CAP=64*1024*1024
HEX=re.compile(r'[0-9a-f]{64}')
ROLE_KEYS={'profile','repository','source_commit','run_id','run_attempt','workflow_id','job_id','artifact_id','artifact_name','required_successful_steps','ZIP','selected_object','producer_result','source_manifest','accepted_private_result_sha256','accepted_collector_sha256'}
TOP_KEYS={'schema','version','roles','registration_pair','source_input_profile','provider_original_facts','review_bindings','nonclaims'}

SCHEMA_MARKERS={'call_status': 'accepted_registration_labels_only; complete_raw_RELA_is_new_observation_required', 'call_observations': ['full raw CALL26 RELA including signed addend/raw indices/relocation-section fields', 'complete init section metadata/bytes SHA and in-scope raw RELA inventory'], 'call_rule': 'Newly observe after approved implementation only from exact whole accepted object; bind accepted name/offset/init constraints and exact reviewed reference, label as new join metadata rather than invented accepted raw facts.', 'init_status': 'original accepted partial symbol label; missing raw fields new observations', 'table_status': 'original accepted partial symbol label', 'extent_marker': 'new_observation_required_from_bound_whole_object; not an accepted raw field', 'relocs_status': 'original accepted callback summaries, not complete raw table RELA records', 'relocs_complete': 'new_observation_required_from_bound_whole_object; label as new join metadata', 'cross_gap': 'v65 argv records GCC-toolchain and prefix paths, but accepted v65 metadata has no aarch64 GCC/as executable hash/version. Do not inherit v63 identity.', 'assembler_gap': 'Both compiler argv include -no-integrated-as; reviewed records do not provide the external assembler binary identity/version.', 'classifications': ['dependency_file_output_name follows C translation unit', 'KBUILD_BASENAME and KBUILD_MODNAME differ by source/module role', 'compiler output temp and C input source are role-specific'], 'limitations': ['Header-set profile is the surveyed source/include/*.h closure only:356 provider370 core351 common identical. Do not mislabel arch-specific or whole prerequisite-map equality.', 'Only retained source/prototype/declared input facts, not binary ABI/core-layout equivalence.', 'Provider layout remains original v63 fact; no measured v65 layout or paired DIE claim.', 'Missing v65 GCC and both assembler identity records remain unproved; no complete toolchain identity.', 'LOCALVERSION exact frozen same-index physical-line pair only in each3 complete files; all other bytes identical.', '89 tokens each84 equal; only3 exact declared role blocks; exact source-root prefix normalization only.'], 'layout_sources': ['DWARF and compiled real-header oracle', 'compiled real-header oracle; DW_AT_alignment absent']}
BUILD_PROFILE_DELTAS=['Both records use clang-14, arm64 and the same recorded KCFLAGS.', 'v65 composite build records LD=aarch64-linux-gnu-ld, LDFLAGS=-m aarch64linux --no-relax and CONFIG_THIN_ARCHIVES empty override; v63 selected provider build is standalone crypto/sha256_generic.o and records no LDFLAGS argument.', 'The generated CONFIG_LOCALVERSION difference remains explicit; no profile interchangeability is assumed.']
NONCLAIMS={'Image_BOOT_XNU_iOS_execution_or_readiness': False, 'SHA_correctness_reproved': False, 'allocation_success': False, 'compiler_or_linker_run': False, 'deployment_ready': False, 'device_authorized': False, 'generated_code_ABI_proven': False, 'independent_core_layout_measured': False, 'old_semantics_replayed': False, 'paired_DIE_equivalence': False, 'physical_BOOT_reboot': 0, 'provider_linked_into_core': False, 'provider_runtime_available': False, 'registration_or_callback_executed': False, 'runtime_or_vermagic_compatibility_proven': False, 'whole_binary_ABI_proven': False, 'whole_toolchain_identity_proven': False}


def exact_keys(value,keys,label):require(type(value) is dict and set(value)==set(keys),'closed '+label+' keys')


def safe_name(name):
 require(type(name) is str and name and len(name)<=4096 and '\\' not in name and ':' not in name and not name.startswith('/') and all(x not in ('','.','..') for x in name.split('/')),'safe relative member');return name


def api_identity(st):
 names=('st_dev','st_ino','st_nlink','st_size','st_mtime_ns','st_ctime_ns')+(('st_birthtime_ns',) if os.name=='nt' else ());require(os.name in ('nt','posix') and all(type(getattr(st,n,None)) is int for n in names),'typed API-aware input identity');raw=tuple(getattr(st,n) for n in names);return raw,raw[:5]+((st.st_birthtime_ns,) if os.name=='nt' else (st.st_ctime_ns,))


def ordinary(path):
 path=Path(path)
 for p in (path,*path.parents):
  st=p.lstat();require(not stat.S_ISLNK(st.st_mode) and not p.is_symlink() and not getattr(st,'st_file_attributes',0)&1024,'no input/ancestor links or reparse')
 st=path.lstat();require(stat.S_ISREG(st.st_mode),'ordinary input file');return st


def snapshot(path,cap=8*1024*1024,expected=None):
 path=Path(path);st=ordinary(path);require(type(cap) is int and 0<cap<=CAP and st.st_size<=cap,'bounded input before materialization');pb,pc=api_identity(st)
 with path.open('rb') as stream:
  fb,fc=api_identity(os.fstat(stream.fileno()));require(pc==fc,'compatible exact opened-file identity');raw=stream.read(cap+1);fa,fac=api_identity(os.fstat(stream.fileno()));pa,pac=api_identity(ordinary(path));require(pb==pa and fb==fa and pc==fc==fac==pac and len(raw)==st.st_size and len(raw)<=cap,'one complete stable bounded input snapshot')
 result={'path':path,'raw':raw,'bytes':len(raw),'sha256':digest(raw),'identity':pb,'int5':[st.st_dev,st.st_ino,st.st_size,st.st_mtime_ns,st.st_nlink]}
 if expected is not None:require(result['bytes']==expected['bytes'] and result['sha256']==expected['sha256'],'exact input size/SHA')
 return result


def unchanged(record):require(api_identity(ordinary(record['path']))[0]==record['identity'],'same-host snapshot identity stable across use')


def pairs(items):
 result={}
 for key,value in items:require(key not in result,'no duplicate JSON keys');result[key]=value
 return result


def json_bytes(raw):return json.loads(raw,object_pairs_hook=pairs)


def write_json(path,value):
 path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
 with path.open('x',encoding='utf8',newline='\n') as stream:stream.write(json.dumps(value,indent=2,sort_keys=True)+'\n')


def write_bytes(path,raw):
 path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
 with path.open('xb') as stream:stream.write(raw)


def source_map():
 result={}
 for name in PUBLIC:
  record=snapshot(ROOT/name);result[name]=record['sha256'];unchanged(record)
 require(result[HELPER]==HELPER_SHA,'immutable generic helper SHA');return result


def validate_control(c):
 exact_keys(c,TOP_KEYS,'control');require(c['schema']=='note10-v66-provider-core-control-v1' and c['version']=='v66','control schema');exact_keys(c['roles'],('provider','core'),'roles')
 for label,role in c['roles'].items():
  exact_keys(role,ROLE_KEYS,'role');require(role['profile']==('accepted-v63-provider-ZIP-v1' if label=='provider' else 'accepted-v65-core-ZIP-v1'),'finite role profile');require(re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+',role['repository']) and re.fullmatch(r'[0-9a-f]{40}',role['source_commit']),'source/repository identity')
  for key in ('run_id','run_attempt','workflow_id','job_id','artifact_id'):require(type(role[key]) is int and role[key]>0,'integer role API identity')
  require(role['run_attempt']==1 and type(role['required_successful_steps']) is list and role['required_successful_steps'] and len(set(role['required_successful_steps']))==len(role['required_successful_steps']),'complete required old steps')
  z=role['ZIP'];exact_keys(z,('sha256','bytes','root','ordinary_members','ordinary_expanded_bytes'),'ZIP');safe_name(z['root']);require(HEX.fullmatch(z['sha256']) and type(z['bytes']) is int and 0<z['bytes']<=16*1024*1024 and type(z['ordinary_members']) is int and 0<z['ordinary_members']<=4096 and type(z['ordinary_expanded_bytes']) is int and 0<z['ordinary_expanded_bytes']<=CAP,'closed bounded old ZIP profile')
  for key in ('selected_object','producer_result','source_manifest'):
   row=role[key];exact_keys(row,('member','bytes','sha256'),key);safe_name(row['member']);require(row['member'].startswith(z['root']+'/') and type(row['bytes']) is int and 0<row['bytes']<=16*1024*1024 and HEX.fullmatch(row['sha256']),'bounded role member record')
  require(HEX.fullmatch(role['accepted_private_result_sha256']) and HEX.fullmatch(role['accepted_collector_sha256']) and role['producer_result']['sha256']!=role['accepted_private_result_sha256'],'producer/private RESULT separation')
 for role in c['roles'].values():
  bounded_string(role['artifact_name'],'artifact name',256)
  for step in role['required_successful_steps']:bounded_string(step,'required successful step',256)
 a,b=c['roles']['provider'],c['roles']['core'];require(a['ZIP']['sha256']!=b['ZIP']['sha256'] and a['selected_object']['sha256']!=b['selected_object']['sha256'],'two distinct protected role artifacts')
 exact_keys(c['registration_pair'],('name','provider_raw_symbol','core_raw_symbol','accepted_call_record','accepted_init_symbol','accepted_core_origin','provider_object_sha256','core_object_sha256'),'registration pair')
 pair=c['registration_pair'];require(pair['name']=='crypto_register_shashes' and pair['provider_object_sha256']==a['selected_object']['sha256'] and pair['core_object_sha256']==b['selected_object']['sha256'],'only contextual registration name/object pair')
 for label in ('provider_raw_symbol','core_raw_symbol'):
  symbol=pair[label];exact_keys(symbol,('index','name','info','other','section','value','size'),'raw symbol');require(symbol['name']==pair['name'] and all(type(v) is int and v>=0 for k,v in symbol.items() if k!='name'),'typed raw symbol')
 u,v=pair['provider_raw_symbol'],pair['core_raw_symbol'];require((u['info'],u['other'],u['section'],u['value'],u['size'])==(16,0,0,0,0) and v['info']==18 and v['other']==0 and v['section']>0 and v['value']==0 and v['size']>0,'exact contextual NOTYPE/FUNC pair, not generic type relaxation')
 exact_keys(c['source_input_profile'],('header_sets','common_headers','primary_headers','prototype','generated_configs','normalized_argv','allowed_role_blocks','build_profile_deltas','retained_tool_records','limitations'),'declared source profile')
 exact_keys(c['provider_original_facts'],('accepted_result_sha256','producer_result_sha256','table_symbol','table_extent','table_relocations','registration_count','accepted_layout_labels'),'provider original labels')
 exact_keys(c['review_bindings'],('survey_sha256','cc_profile_addendum_sha256','cc_profile_review_sha256','provider_query_result_sha256','provider_query_review_sha256','final_design_review_sha256'),'reviews');require(all(type(v) is str and HEX.fullmatch(v) for v in c['review_bindings'].values()),'complete reviewed control digests')
 require(c['provider_original_facts']['accepted_result_sha256']==a['accepted_private_result_sha256'] and c['provider_original_facts']['producer_result_sha256']==a['producer_result']['sha256'],'original accepted provider labels bound separately')
 require(type(c['nonclaims']) is dict and c['nonclaims'] and all(value is False or type(value) is int and value==0 for value in c['nonclaims'].values()),'all explicit nonclaims false/zero');validate_nested_control(c);return c


def load_control(sha):
 require(type(sha) is str and HEX.fullmatch(sha),'exact64 lowercase dispatch control SHA');record=snapshot(ROOT/CONTROL);require(record['sha256']==sha,'fixed committed control matches dispatch/source');return validate_control(json_bytes(record['raw'])),record


def disjoint(paths,identities=()):
 normalized=[Path(p).absolute() for p in paths];require(all('..' not in p.parts and not p.is_symlink() for p in normalized),'explicit ordinary disjoint roots')
 for i,p in enumerate(normalized):
  for q in normalized[i+1:]:require(not p.is_relative_to(q) and not q.is_relative_to(p),'no overlapping input/output roots')
 require(len({tuple(row[:2]) for row in identities})==len(identities),'no same-file role alias')


def inventory(root,cap=CAP):
 root=Path(root);result={};total=0
 for p in sorted(root.rglob('*')):
  require(not p.is_symlink() and not getattr(p.lstat(),'st_file_attributes',0)&1024,'no namespace links/reparse')
  if p.is_dir():continue
  record=snapshot(p,16*1024*1024);total+=record['bytes'];require(total<=cap and len(result)<8192,'complete namespace cap');result[p.relative_to(root).as_posix()]={'bytes':record['bytes'],'sha256':record['sha256']};unchanged(record)
 return result


_ORIGINAL_BINDING_TOKEN=object()
_ORIGINAL_PROFILES=frozenset(('accepted-v63-provider-ZIP-v1','accepted-v65-core-ZIP-v1'))


class _OriginalInventory:
 """Internally sealed immutable original-ZIP provenance and scalar row tuples."""
 __slots__=('_profile','_role_digest','_root','_zip_bytes','_zip_sha256','_source_path','_source_identity','_rows')
 def __new__(cls,record,role,members,token=None):
  require(cls is _OriginalInventory and token is _ORIGINAL_BINDING_TOKEN,'original inventory is created only by the successful complete ZIP path');self=object.__new__(cls)
  values={'_profile':role['profile'],'_role_digest':digest(json.dumps(role,sort_keys=True,separators=(',',':')).encode()),'_root':role['ZIP']['root'],'_zip_bytes':record['bytes'],'_zip_sha256':record['sha256'],'_source_path':str(record['path'].absolute()),'_source_identity':tuple(record['identity']),'_rows':tuple((name,row['bytes'],row['sha256']) for name,row in sorted(members.items()))}
  for name,value in values.items():object.__setattr__(self,name,value)
  return self
 def __init__(self,record,role,members,token=None):pass
 def __setattr__(self,name,value):raise TypeError('immutable original inventory')
 def __delattr__(self,name):raise TypeError('immutable original inventory')
 def __init_subclass__(cls,**kwargs):raise TypeError('original inventory cannot be subclassed')
 @property
 def rows(self):return self._rows
 @property
 def profile(self):return self._profile
 def members(self):return {name:{'bytes':size,'sha256':sha} for name,size,sha in self._rows}
 def check(self,role):
  require(type(self) is _OriginalInventory and self._profile in _ORIGINAL_PROFILES and self._profile==role['profile'] and self._role_digest==digest(json.dumps(role,sort_keys=True,separators=(',',':')).encode()),'exact original inventory type/role record');require(self._root==role['ZIP']['root'] and self._zip_bytes==role['ZIP']['bytes'] and self._zip_sha256==role['ZIP']['sha256'] and len(self._rows)==role['ZIP']['ordinary_members'] and sum(size for _,size,_ in self._rows)==role['ZIP']['ordinary_expanded_bytes'],'same complete accepted raw-ZIP binding');require(api_identity(ordinary(Path(self._source_path)))[0]==self._source_identity,'original raw ZIP snapshot stable through use');return self
 def summary(self):return {'profile':self._profile,'ZIP_sha256':self._zip_sha256,'ZIP_bytes':self._zip_bytes,'root':self._root,'ordinary_members':len(self._rows),'ordinary_expanded_bytes':sum(size for _,size,_ in self._rows),'inventory_sha256':digest(json.dumps(self._rows,separators=(',',':')).encode())}


def zip_inventory(record,role,extract=None,original=False):
 require(type(original) is bool,'explicit original-binding mode')
 if original:require(role.get('profile') in _ORIGINAL_PROFILES and type(record['raw']) is bytes and len(record['raw'])==record['bytes'] and digest(record['raw'])==record['sha256'],'exact original profile and held raw snapshot bytes/hash');unchanged(record)
 z=role['ZIP'];require(record['bytes']==z['bytes'] and record['sha256']==z['sha256'],'exact protected whole ZIP');result={};total=0;seen=set()
 if extract is not None:require(not Path(extract).exists(),'fresh complete extraction');Path(extract).mkdir(parents=True)
 import io
 with zipfile.ZipFile(io.BytesIO(record['raw'])) as bundle:
  infos=bundle.infolist();require(len(infos)<=8192,'bounded central directory')
  for item in infos:
   name=item.filename.rstrip('/') if item.is_dir() else item.filename;safe_name(name);require(name==z['root'] or name.startswith(z['root']+'/'),'one exact original root');require(name not in seen,'unique central-directory name');seen.add(name);mode=item.external_attr>>16;require(not item.flag_bits&1 and not stat.S_ISLNK(mode) and not (item.external_attr&1024) and (not mode or stat.S_IFMT(mode) in (0,stat.S_IFREG,stat.S_IFDIR)),'ordinary unencrypted ZIP entry')
   if item.is_dir():continue
   require(item.file_size<=16*1024*1024 and item.compress_type in (zipfile.ZIP_STORED,zipfile.ZIP_DEFLATED),'bounded supported member');total+=item.file_size;require(total<=CAP and len(result)<4096,'complete expanded cap')
   with bundle.open(item) as stream:raw=stream.read(item.file_size+1)
   require(len(raw)==item.file_size,'whole member/CRC read');result[name]={'bytes':len(raw),'sha256':digest(raw)}
   if extract is not None:write_bytes(Path(extract)/name,raw)
 require(len(result)==z['ordinary_members'] and total==z['ordinary_expanded_bytes'],'exact complete accepted ZIP inventory count/bytes')
 for key in ('selected_object','producer_result','source_manifest'):require(result.get(role[key]['member'])=={k:role[key][k] for k in ('bytes','sha256')},'original exact selected member')
 if extract is not None:require(inventory(extract)==result,'complete extraction no missing/extra/changed member')
 unchanged(record)
 if original:return _OriginalInventory(record,role,result,_ORIGINAL_BINDING_TOKEN)
 return result


def old_labels(extraction,role,binding):
 require(type(binding) is _OriginalInventory,'mandatory internally verified complete original inventory binding');binding.check(role);extraction=Path(extraction);expected=binding.members();require(inventory(extraction)==expected,'entire extraction equals the SAME complete bounded raw-ZIP inventory before producer parsing');prefix=role['ZIP']['root']+'/';require(all(name.startswith(prefix) for name in expected),'one exact original root prefix');actual={name[len(prefix):]:row for name,row in expected.items()};root=extraction/role['ZIP']['root'];p=snapshot(extraction/role['producer_result']['member'],expected=role['producer_result']);prod=json_bytes(p['raw']);require(prod['passed'] is True,'original successful producer label');ctx=prod['ci_context'];require(ctx['GITHUB_SHA']==role['source_commit'] and ctx['GITHUB_RUN_ID']==str(role['run_id']) and ctx['GITHUB_RUN_ATTEMPT']=='1','exact old producer CI context')
 manifest_record=snapshot(extraction/role['source_manifest']['member'],expected=role['source_manifest']);manifest=json_bytes(manifest_record['raw']);require(type(manifest) is dict and manifest==prod['source_sha256'],'complete original source manifest')
 files=prod.get('files',prod.get('files_sha256'));require(type(files) is dict and files,'complete original producer member labels');result_name=role['producer_result']['member'][len(prefix):];manifest_name=role['source_manifest']['member'][len(prefix):];require(result_name=='result.json' and result_name not in files and manifest_name=='source-manifest.json' and manifest_name in files,'result and already-declared manifest control records retained');extras={result_name};opaque='independent-verification.json'
 if role['profile']=='accepted-v63-provider-ZIP-v1':require(opaque in actual and opaque not in files,'one mandatory provider-only unlisted opaque member');extras.add(opaque)
 else:require(role['profile']=='accepted-v65-core-ZIP-v1' and opaque not in actual,'core has no provider opaque metadata exception')
 require(set(actual)==set(files)|extras and not set(files)&extras,'complete exact original final namespace, no wildcard/subset/unlisted member')
 for name,expected_row in files.items():safe_name(name);require(actual[name]==expected_row if type(expected_row) is dict else actual[name]['sha256']==expected_row,'every producer-declared row matches bound raw ZIP')
 for name,sha in manifest.items():safe_name(name);require(snapshot(root/'source'/name)['sha256']==sha,'all original source bytes')
 # The opaque provider entry was hashed in the complete extraction comparison;
 # it has no invented direct control digest and its JSON is never deserialized.
 unchanged(p);unchanged(manifest_record);binding.check(role);return prod


def endpoints(role):
 prefix='repos/'+role['repository']+'/actions/';return {'run':prefix+'runs/'+str(role['run_id'])+'/attempts/1','jobs':prefix+'runs/'+str(role['run_id'])+'/attempts/1/jobs?filter=all&per_page=100','artifacts':prefix+'runs/'+str(role['run_id'])+'/artifacts?per_page=100','artifact':prefix+'artifacts/'+str(role['artifact_id'])}


def validate_api(role,api):
 exact_keys(api,('run','jobs','artifacts','artifact'),'four old API roles');run=api['run'];require(run['id']==role['run_id'] and run['run_attempt']==1 and run['head_sha']==role['source_commit'] and run['workflow_id']==role['workflow_id'] and run['repository']['full_name']==role['repository'] and run['status']=='completed' and run['conclusion']=='success','fresh original run identity/success')
 jobs=api['jobs'];require(jobs['total_count']==len(jobs['jobs'])==1,'complete old jobs');job=jobs['jobs'][0];require(job['id']==role['job_id'] and job['run_id']==role['run_id'] and job['run_attempt']==1 and job['head_sha']==role['source_commit'] and job['status']=='completed' and job['conclusion']=='success','exact original job success')
 for name in role['required_successful_steps']:
  matches=[s for s in job['steps'] if s['name']==name];require(len(matches)==1 and matches[0]['status']=='completed' and matches[0]['conclusion']=='success','all original required successful steps')
 listing=api['artifacts'];artifact=api['artifact'];require(listing['total_count']==len(listing['artifacts'])<=100 and [x for x in listing['artifacts'] if x['id']==role['artifact_id']]==[artifact],'complete listing/individual metadata equality');require(artifact['id']==role['artifact_id'] and artifact['name']==role['artifact_name'] and artifact['expired'] is False and artifact['digest']=='sha256:'+role['ZIP']['sha256'] and artifact['size_in_bytes']==role['ZIP']['bytes'] and artifact['workflow_run']['id']==role['run_id'] and artifact['workflow_run']['head_sha']==role['source_commit'],'exact authenticated original whole artifact')
 return True


def redact(raw,token):
 if not token:return raw
 secret=token.encode();result=raw.replace(secret,b'[REDACTED]')
 for n in range(len(secret)-1,0,-1):
  if result.endswith(secret[:n]):return result[:-n]+b'[REDACTED-PREFIX]'
 return result


def bounded_gh(args,stdout_cap,stderr_cap=65536,seconds=120):
 require(os.name=='posix' and args[:2]==['gh','api'] and len(args)==3 and 0<stdout_cap<=16*1024*1024 and 0<seconds<=120,'supported bounded Linux authenticated data command');started=time.time_ns();child=subprocess.Popen(args,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True,env=dict(os.environ,GH_HOST='github.com'));buffers=[bytearray(),bytearray()];limits=(stdout_cap,stderr_cap);selector=selectors.DefaultSelector();failure=None;deadline=time.monotonic()+seconds
 for index,stream in enumerate((child.stdout,child.stderr)):os.set_blocking(stream.fileno(),False);selector.register(stream,selectors.EVENT_READ,index)
 try:
  while selector.get_map():
   remaining=deadline-time.monotonic()
   if remaining<=0:failure='total_timeout';break
   for key,_ in selector.select(min(.1,remaining)):
    chunk=os.read(key.fileobj.fileno(),65536)
    if not chunk:selector.unregister(key.fileobj);continue
    index=key.data;room=limits[index]-len(buffers[index]);buffers[index].extend(chunk[:max(0,room)])
    if len(chunk)>room:failure='output_cap';break
   if failure is not None:break
  if failure is None:
   try:child.wait(timeout=max(.001,deadline-time.monotonic()))
   except subprocess.TimeoutExpired:failure='total_timeout'
 except BaseException as error:failure='pipe_error:'+type(error).__name__
 finally:
  if failure is not None:
   try:os.killpg(child.pid,9)
   except ProcessLookupError:pass
  child.wait(timeout=10);selector.close();child.stdout.close();child.stderr.close()
 return {'command':args,'returncode':child.returncode,'completed':failure is None,'failure':failure,'start_ns':started,'end_ns':time.time_ns(),'stdout':bytes(buffers[0]),'stderr':bytes(buffers[1])}


def retrieve(role,directory,evidence,deadline=None):
 deadline=time.monotonic()+120 if deadline is None else deadline;directory=Path(directory);evidence=Path(evidence);require(not directory.exists() and not evidence.exists(),'fresh role retrieval/evidence');directory.mkdir(parents=True);evidence.mkdir(parents=True);token=os.environ.get('GH_TOKEN','');require(re.fullmatch(r'[A-Za-z0-9_.-]{8,4096}',token),'existing environment credential, no auth change');rows=[];api={};receipt={'schema':1,'rows':rows,'success':False,'role_profile':role['profile']}
 def persist():
  target=evidence/'retrieval.json';raw=(json.dumps(receipt,indent=2,sort_keys=True)+'\n').encode();temp=evidence/'retrieval.pending';
  with temp.open('wb') as stream:stream.write(raw)
  temp.replace(target)
 def call(label,endpoint,cap):
  remaining=deadline-time.monotonic();require(remaining>0,'whole two-role retrieval deadline');result=bounded_gh(['gh','api',endpoint],cap,seconds=min(120,remaining));out=redact(result.pop('stdout'),token);err=redact(result.pop('stderr'),token);name=label+('.zip' if label=='ZIP' else '.json');target=directory/name;write_bytes(target,out);write_bytes(evidence/(label+'.stderr.txt'),err);row=dict(result,label=label,path=name,bytes=len(out),sha256=digest(out),stderr_path=label+'.stderr.txt',stderr_bytes=len(err),stderr_sha256=digest(err));rows.append(row)
  if label!='ZIP':write_bytes(evidence/name,out)
  persist();require(result['completed'] and result['returncode']==0,'authenticated bounded endpoint failed: '+label);return target
 for label,endpoint in endpoints(role).items():api[label]=json_bytes(snapshot(call(label,endpoint,8*1024*1024))['raw'])
 validate_api(role,api);archive=call('ZIP','repos/'+role['repository']+'/actions/artifacts/'+str(role['artifact_id'])+'/zip',role['ZIP']['bytes']);record=snapshot(archive,16*1024*1024,role['ZIP']);receipt['success']=True;persist();return record


def verify_retrieval(role,evidence):
 evidence=Path(evidence);receipt=json_bytes(snapshot(evidence/'retrieval.json')['raw']);require(receipt['success'] is True and receipt['role_profile']==role['profile'] and len(receipt['rows'])==5,'complete four metadata+ZIP retrieval');api={};eps=endpoints(role)
 for row in receipt['rows']:
  label=row['label'];require(row['path']==label+('.zip' if label=='ZIP' else '.json') and row['stderr_path']==label+'.stderr.txt','fixed role receipt member names, no arbitrary paths');endpoint=eps.get(label,'repos/'+role['repository']+'/actions/artifacts/'+str(role['artifact_id'])+'/zip');require(label in set(eps)|{'ZIP'} and row['command']==['gh','api',endpoint] and row['completed'] is True and row['returncode']==0 and type(row['start_ns']) is int and row['start_ns']<=row['end_ns'],'exact successful bounded endpoint receipt');err=snapshot(evidence/row['stderr_path']);require(err['bytes']==row['stderr_bytes'] and err['sha256']==row['stderr_sha256'],'complete retained stderr')
  if label=='ZIP':require(row['bytes']==role['ZIP']['bytes'] and row['sha256']==role['ZIP']['sha256'],'whole ZIP receipt')
  else:require(label not in api,'unique metadata endpoint');record=snapshot(evidence/row['path']);require(record['bytes']==row['bytes'] and record['sha256']==row['sha256'],'complete authenticated metadata bytes');api[label]=json_bytes(record['raw'])
 validate_api(role,api);return receipt

def namespace_allowed():
 names={'source-manifest.json','evidence/provider.o','evidence/core.o','join.json','result.json','failure.json'}|{'source/'+n for n in PUBLIC}
 for role in ('provider','core'):
  names.add('inputs/'+role+'/retrieval.json')
  for label in ('run','jobs','artifacts','artifact','ZIP'):
   names.add('inputs/'+role+'/'+label+'.stderr.txt')
   if label!='ZIP':names.add('inputs/'+role+'/'+label+'.json')
 return names


def validate_namespace(root,expected_sources=None,forensic=False):
 root=Path(root);actual=inventory(root);require(set(actual)<=namespace_allowed(),'exact new-only artifact namespace; no old proof/log/private paths')
 if forensic:require('failure.json' in actual and 'result.json' not in actual,'honest forensic-only failure namespace');return actual
 require('failure.json' not in actual and set(actual)==namespace_allowed()-{'failure.json'},'complete successful namespace no extra/missing members');result=json_bytes(snapshot(root/'result.json')['raw']);require(result['schema']=='v66-interface-producer-v1' and result['version']=='v66' and result['passed'] is True and result['executed_fixture_commands']==0 and result['compiler_linker_model_or_oldchecker_commands']==0,'new data-only successful producer')
 require(set(actual)==set(result['files'])|{'result.json'} and all(actual[k]==v for k,v in result['files'].items()),'complete new artifact manifest identity')
 manifest=json_bytes(snapshot(root/'source-manifest.json')['raw']);require(set(manifest)==set(PUBLIC) and manifest==result['source_sha256'],'full eight-entry source/control/helper closure')
 if expected_sources is not None:require(manifest==expected_sources,'exact reviewed current public source/control closure')
 for name,sha in manifest.items():require(actual['source/'+name]['sha256']==sha,'captured actual source/control bytes')
 require(manifest[HELPER]==HELPER_SHA and actual['source/'+CONTROL]['sha256']==result['control_sha256'],'exact immutable helper and fixed committed control')
 return actual


def current_int5(record):
 unchanged(record);st=ordinary(record['path']);return [st.st_dev,st.st_ino,st.st_size,st.st_mtime_ns,st.st_nlink]

def bounded_string(value,label,cap=4096):require(type(value) is str and 0<len(value)<=cap and '\x00' not in value and '\r' not in value and (cap>=65536 or '\n' not in value),'typed bounded '+label)


def unsigned(value,label,positive=False):require(type(value) is int and (value>0 if positive else value>=0) and value<1<<64,'typed integer '+label)


def hash_value(value,label):require(type(value) is str and HEX.fullmatch(value),'exact hash '+label)


def partial_symbol(value,label):
 exact_keys(value,('name','info','section','size','value'),label);bounded_string(value['name'],'accepted symbol name')
 for key in ('info','section','size','value'):unsigned(value[key],label+' '+key)
 require(value['info']<=255 and value['section']>0,'defined accepted partial symbol')


def full_symbol(value,label):
 exact_keys(value,('index','name','info','other','section','value','size'),label);require(type(value['name']) is str and len(value['name'])<=4096,'bounded raw symbol name')
 for key in ('index','info','other','section','value','size'):unsigned(value[key],label+' '+key)
 require(value['info']<=255 and value['other']<=3,'bounded raw symbol attributes')


def validate_nested_control(c):
 pair=c['registration_pair'];facts=c['provider_original_facts'];profile=c['source_input_profile'];markers=SCHEMA_MARKERS;role=c['roles']['provider']
 call=pair['accepted_call_record'];exact_keys(call,('evidence_status','producer_member','producer_json_pointer','accepted_call_offset','accepted_external_name','survey_relocation_type','survey_sha256','new_observation_required','rule'),'accepted call labels');require(call['evidence_status']==markers['call_status'] and call['new_observation_required']==markers['call_observations'] and call['rule']==markers['call_rule'],'exact call new-observation boundary markers');require(call['producer_member']==role['producer_result']['member'] and call['producer_json_pointer']=='/proof/registration' and call['accepted_external_name']==pair['name'] and type(call['survey_relocation_type']) is int and call['survey_relocation_type']==283 and call['survey_sha256']==c['review_bindings']['survey_sha256'],'closed original call provenance');unsigned(call['accepted_call_offset'],'call offset')
 init=pair['accepted_init_symbol'];exact_keys(init,('evidence_status','record','producer_json_pointer','new_raw_fields_required'),'accepted init');require(init['evidence_status']==markers['init_status'] and init['producer_json_pointer']=='/proof/registration/init_function' and init['new_raw_fields_required']==['index','other'],'exact init label/new-observation profile');partial_symbol(init['record'],'init record');require(init['record']['info']==2 and init['record']['size']>0,'typed original init extent')
 origin=pair['accepted_core_origin'];exact_keys(origin,('origin','input_symbol','output_symbol'),'accepted origin');require(origin['origin']=='shash','finite original origin role');full_symbol(origin['input_symbol'],'origin input');full_symbol(origin['output_symbol'],'origin output');require(origin['output_symbol']==pair['core_raw_symbol'] and origin['input_symbol']['section']>0 and all(origin['input_symbol'][key]==origin['output_symbol'][key] for key in ('name','info','other','value','size')),'original partial origin labels consistent without replay')
 ts=facts['table_symbol'];exact_keys(ts,('evidence_status','record','producer_json_pointer','new_raw_fields_required'),'table label');require(ts['evidence_status']==markers['table_status'] and ts['producer_json_pointer']=='/proof/table/symbol' and ts['new_raw_fields_required']==['index','other'],'exact original table status');partial_symbol(ts['record'],'table partial record');require(ts['record']['info']==1,'typed original table')
 extent=facts['table_extent'];exact_keys(extent,('accepted_value','accepted_size','accepted_element_size','registered_array_mutable_data','full_section_metadata_bytes_SHA'),'table extent');require(extent['full_section_metadata_bytes_SHA']==markers['extent_marker'] and extent['registered_array_mutable_data'] is True,'missing full table metadata remains an exact marker, not a hash')
 for key in ('accepted_value','accepted_size','accepted_element_size'):unsigned(extent[key],key,positive=key!='accepted_value')
 unsigned(facts['registration_count'],'registration count',positive=True);require(extent['accepted_size']==facts['registration_count']*extent['accepted_element_size']==ts['record']['size'] and extent['accepted_value']==ts['record']['value'],'closed accepted table/count/stride labels')
 tr=facts['table_relocations'];exact_keys(tr,('evidence_status','accepted_entries','producer_json_pointer','complete_raw_RELA'),'table relocation labels');require(tr['evidence_status']==markers['relocs_status'] and tr['complete_raw_RELA']==markers['relocs_complete'] and tr['producer_json_pointer']=='/proof/table/entries','exact callback-summary/new-raw status');require(type(tr['accepted_entries']) is list and len(tr['accepted_entries'])==facts['registration_count']<=4096,'bounded complete original entries')
 for index,entry in enumerate(tr['accepted_entries']):
  exact_keys(entry,('index','callbacks','cra_blocksize','cra_driver_name','cra_flags','cra_name','descsize','digestsize'),'original table entry');require(type(entry['index']) is int and entry['index']==index,'ordered typed original entry')
  for key in ('cra_blocksize','cra_flags','descsize','digestsize'):unsigned(entry[key],key)
  for key in ('cra_driver_name','cra_name'):bounded_string(entry[key],key)
  exact_keys(entry['callbacks'],('init','update','final','finup'),'original callbacks')
  for row in entry['callbacks'].values():
   exact_keys(row,('offset','section','symbol_name','symbol_info','symbol_value','symbol_size','addend','relocation_type','target_name'),'callback summary')
   for key in ('offset','section','symbol_info','symbol_value','symbol_size','relocation_type'):unsigned(row[key],key)
   require(type(row['addend']) is int and -(1<<63)<=row['addend']<1<<63 and row['relocation_type']==257 and row['section']>0 and row['symbol_info']<=255,'typed accepted callback summary');require(type(row['symbol_name']) is str and len(row['symbol_name'])<=4096,'bounded original callback symbol');bounded_string(row['target_name'],'target name')
 layouts=facts['accepted_layout_labels'];exact_keys(layouts,('crypto_alg','sha256_state','shash_alg','shash_desc'),'original provider layouts')
 for row in layouts.values():
  exact_keys(row,('alignment','alignment_source','byte_size'),'provider-only layout label');unsigned(row['alignment'],'alignment',positive=True);unsigned(row['byte_size'],'byte size',positive=True);require(row['alignment']<=1<<20 and row['alignment']&(row['alignment']-1)==0 and row['alignment_source'] in markers['layout_sources'],'closed original provider alignment source')
 require(layouts['shash_alg']['byte_size']==extent['accepted_element_size'],'original stride/layout association')
 exact_keys(profile['header_sets'],('provider','core'),'header role sets')
 for headers in [*profile['header_sets'].values(),profile['common_headers']]:
  require(type(headers) is dict and 0<len(headers)<=4096,'bounded header map')
  for name,sha in headers.items():safe_name(name);require(name.startswith('source/include/') and name.endswith('.h'),'frozen ABI header scope');hash_value(sha,'header')
 a,b=profile['header_sets']['provider'],profile['header_sets']['core'];require(set(profile['common_headers'])==set(a)&set(b) and all(a[name]==b[name]==sha for name,sha in profile['common_headers'].items()),'complete typed common header intersection');require(type(profile['primary_headers']) is list and len(profile['primary_headers'])==4 and len({row['path'] for row in profile['primary_headers']})==4,'four distinct primary header labels')
 for row in profile['primary_headers']:
  exact_keys(row,('path','bytes','v63_sha256','v65_sha256','byte_identical'),'primary header');require(row['byte_identical'] is True,'approved primary byte-identical flag is literal true');unsigned(row['bytes'],'header bytes',positive=True);require(row['path'] in profile['common_headers'] and row['v63_sha256']==row['v65_sha256']==profile['common_headers'][row['path']],'original primary hash association')
 require(profile['prototype']=='int crypto_register_shashes(struct shash_alg *algs, int count);','finite declared prototype');require(type(profile['generated_configs']) is list and len(profile['generated_configs'])==3 and {row['path'] for row in profile['generated_configs']}=={'objects/.config','objects/include/config/auto.conf','objects/include/generated/autoconf.h'},'exact three config roles')
 for row in profile['generated_configs']:
  exact_keys(row,('path','bytes_v63','bytes_v65','sha256_v63','sha256_v65','only_v63_lines','only_v65_lines'),'generated config')
  for suffix in ('v63','v65'):
   unsigned(row['bytes_'+suffix],'config bytes',positive=True);hash_value(row['sha256_'+suffix],'config SHA');require(type(row['only_'+suffix+'_lines']) is list and len(row['only_'+suffix+'_lines'])==1,'one typed config exception line');bounded_string(row['only_'+suffix+'_lines'][0],'config exception');line=row['only_'+suffix+'_lines'][0];pattern=r'#define CONFIG_LOCALVERSION \"-[A-Za-z0-9._+-]+\"' if row['path'].endswith('autoconf.h') else r'CONFIG_LOCALVERSION=\"-[A-Za-z0-9._+-]+\"';require(re.fullmatch(pattern,line),'closed LOCALVERSION definition syntax, no arbitrary exception line')
 exact_keys(profile['normalized_argv'],('v63_provider','v65_core_shash'),'normalized argv')
 for args in profile['normalized_argv'].values():
  require(type(args) is list and len(args)==89,'closed89-token profile')
  for value in args:bounded_string(value,'compiler token')
 require(type(profile['allowed_role_blocks']) is list and len(profile['allowed_role_blocks'])==3,'exact three role blocks')
 for index,row in enumerate(profile['allowed_role_blocks']):
  exact_keys(row,('classification','operation','v63_argv_indices','v65_argv_indices','v63_tokens','v65_tokens'),'role block');require(row['classification']==markers['classifications'][index] and row['operation']=='replace','finite role block classification')
  for key in ('v63_argv_indices','v65_argv_indices'):require(type(row[key]) is list and len(row[key])==2 and all(type(n) is int for n in row[key]) and 0<=row[key][0]<row[key][1]<=89,'bounded half-open argv block')
  require(row['v63_argv_indices']==row['v65_argv_indices'],'same-coordinate role block')
  for prefix in ('v63','v65'):
   require(type(row[prefix+'_tokens']) is list and len(row[prefix+'_tokens'])==row[prefix+'_argv_indices'][1]-row[prefix+'_argv_indices'][0],'complete block token count')
   for token in row[prefix+'_tokens']:bounded_string(token,'role token')
 require(profile['build_profile_deltas']==BUILD_PROFILE_DELTAS and profile['limitations']==markers['limitations'],'only reviewed finite build deltas and limitation status set');validate_tool_schema(profile['retained_tool_records']);require(c['nonclaims']==NONCLAIMS and all(type(c['nonclaims'][name]) is type(value) for name,value in NONCLAIMS.items()),'exact required nonclaim/value set')
 return c


def validate_tool_schema(tools):
 exact_keys(tools,('clang','linker','make','resource_directory','cross_toolchain','external_assembler'),'retained tool records')
 for name,role in (('clang','clang-14'),('linker','aarch64-linux-gnu-ld'),('make','make')):
  row=tools[name];flags=('same_path_sha256','version_text_equal') if name=='clang' else ('same_sha256',);exact_keys(row,('v63','v65','v63_version_log_sha256','v65_version_log_sha256',*flags),name+' records');require(all(row[flag] is True for flag in flags),'exact observed tool status booleans');exact_keys(row['v63'],('path','sha256'),'original tool');exact_keys(row['v65'],('path','role','sha256','version'),'core tool');require(row['v65']['role']==role,'exact recorded tool role')
  for record in (row['v63'],row['v65']):bounded_string(record['path'],'tool path');require(record['path'].startswith('/'),'absolute recorded tool path');hash_value(record['sha256'],'tool SHA')
  bounded_string(row['v65']['version'],'full version',65536)
  for key in ('v63_version_log_sha256','v65_version_log_sha256'):hash_value(row[key],'version SHA')
 resource=tools['resource_directory'];exact_keys(resource,('equal','v63','v65','v63_record_sha256','v65_record_sha256'),'resource');require(resource['equal'] is True,'observed resource status')
 for key in ('v63','v65'):bounded_string(resource[key],'resource path');require(resource[key].startswith('/'),'absolute declared resource')
 for key in ('v63_record_sha256','v65_record_sha256'):hash_value(resource[key],'resource SHA')
 cross=tools['cross_toolchain'];exact_keys(cross,('gap','v63_aarch64_gcc','v63_version_log_sha256','v65_binary_sha_or_version_record'),'cross-tool records');require(cross['gap']==SCHEMA_MARKERS['cross_gap'] and cross['v65_binary_sha_or_version_record'] is None,'missing core cross-tool record remains unavailable');exact_keys(cross['v63_aarch64_gcc'],('path','sha256'),'original cross GCC');bounded_string(cross['v63_aarch64_gcc']['path'],'original GCC path');require(cross['v63_aarch64_gcc']['path'].startswith('/'),'absolute original GCC path');hash_value(cross['v63_aarch64_gcc']['sha256'],'original GCC hash');hash_value(cross['v63_version_log_sha256'],'original GCC version')
 assembler=tools['external_assembler'];exact_keys(assembler,('gap','v63_identity','v65_identity'),'assembler record gaps');require(assembler['gap']==SCHEMA_MARKERS['assembler_gap'] and assembler['v63_identity'] is None and assembler['v65_identity'] is None,'both missing assembler records remain unavailable, never inherited')
