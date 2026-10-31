"""New composite's dual protected inputs, authenticated baseline and provenance."""
import hashlib,json,os,posixpath,re,shlex,shutil,stat,subprocess,tarfile,threading,time,zipfile
from pathlib import Path,PurePosixPath
from crypto_hash_composite import require,digest

KERNEL_COMMIT='55f042627bb7030c93550faafa117674d32b21d1'
KERNEL_SHA='46d6a563af04e0c2ed9c96c2a1af8cab2344b458c9554b09098e6a9e7219ae4c'
KERNEL_BYTES=212648376
SOURCE_TOP='android_kernel_samsung_universal9820-'+KERNEL_COMMIT
CAP=64*1024*1024
BASELINE_ROOT='v64-ci-shash'
NEW_ROOT='v65-ci-composite'


def write(path,data):
 path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
 with path.open('x',encoding='utf8',newline='\n') as stream:stream.write(json.dumps(data,indent=2,sort_keys=True)+'\n')


def five(info):return [int(info.st_dev),int(info.st_ino),int(info.st_size),int(info.st_mtime_ns),int(info.st_nlink)]


def protected(path,profile,expected_bytes,expected_sha):
 path=Path(path).absolute();before=path.stat();require(path.is_file() and not path.is_symlink() and not getattr(before,'st_file_attributes',0)&1024,'ordinary protected input, no links/reparse');require(before.st_size==expected_bytes,'exact protected input byte size');h=hashlib.sha256()
 with path.open('rb') as stream:
  require(five(os.fstat(stream.fileno()))==five(before),'opened protected input identity')
  for block in iter(lambda:stream.read(1024*1024),b''):h.update(block)
  require(five(os.fstat(stream.fileno()))==five(before)==five(path.stat()),'stable full protected input hash/stat')
 require(h.hexdigest()==expected_sha,'exact protected input SHA256');return {'profile':profile,'path':str(path),'bytes':before.st_size,'sha256':h.hexdigest(),'file_identity':five(before)}


def stable(record):return protected(record['path'],record['profile'],record['bytes'],record['sha256'])


def separate(paths,identities=()):
 resolved=[Path(p).resolve() for p in paths];require(len(set(resolved))==len(resolved) and all(not a.is_relative_to(b) and not b.is_relative_to(a) for i,a in enumerate(resolved) for b in resolved[i+1:]),'disjoint canonical input/output roots')
 require(len({tuple(x[:2]) for x in identities})==len(identities),'protected inputs are not aliases')


def disk_budget(path,required):
 require(type(required) is int and required>0,'integer disk budget');free=shutil.disk_usage(path).free;require(free>=required,'fresh complete-namespace disk budget');return {'required_bytes':required,'free_bytes':free}


def safe_name(name):
 require(type(name) is str and name and '\\' not in name and ':' not in name and '\x00' not in name and not name.startswith('/') and all(p not in ('','..','.') for p in name.rstrip('/').split('/')),'canonical safe archive path');return PurePosixPath(name.rstrip('/'))


def tree_inventory(root,cap=CAP):
 root=Path(root);result={};total=0
 for path in sorted(root.rglob('*')):
  require(not path.is_symlink() and not getattr(path.lstat(),'st_file_attributes',0)&1024,'no links/reparse in complete evidence namespace')
  if path.is_dir():continue
  require(path.is_file(),'ordinary complete evidence file');raw=path.read_bytes();total+=len(raw);require(total<=cap,'complete evidence namespace cap');result[path.relative_to(root).as_posix()]={'bytes':len(raw),'sha256':digest(raw)}
 return result


def zip_inventory(path,root,cap=CAP):
 require(Path(path).stat().st_size<=CAP,'bounded complete raw ZIP');result={};total=0;seen=set();folded=set()
 with zipfile.ZipFile(path) as bundle:
  require(len(bundle.infolist())<=65536,'bounded complete central directory')
  for member in bundle.infolist():
   name=safe_name(member.filename);require(str(name).split('/')[0]==root and str(name) not in seen and str(name).casefold() not in folded,'one unique whole archive root, no case aliases');seen.add(str(name));folded.add(str(name).casefold());mode=member.external_attr>>16;kind=stat.S_IFMT(mode)
   require(not member.flag_bits&1 and not member.external_attr&1024 and kind in (0,stat.S_IFREG,stat.S_IFDIR) and member.compress_type in (0,8),'unencrypted ordinary ZIP members, no link/reparse/unknown compression')
   if member.is_dir():require(member.file_size==0 and kind in (0,stat.S_IFDIR),'empty directory entry');continue
   require(kind in (0,stat.S_IFREG),'ordinary file metadata')
   require(len(name.parts)>=2,'ordinary files strictly below the one root directory')
   total+=member.file_size;require(total<=cap and member.file_size<=cap,'bounded complete ZIP expansion');raw=bundle.read(member);require(len(raw)==member.file_size,'complete ZIP member');result[str(name)]={'bytes':len(raw),'sha256':digest(raw)}
 require(result,'nonempty complete ZIP');return result


def extract_zip(path,destination,root,expected_count=None,expected_bytes=None):
 destination=Path(destination);require(not destination.exists(),'fresh complete ZIP extraction');inventory=zip_inventory(path,root)
 require(expected_count is None or len(inventory)==expected_count,'exact accepted ordinary ZIP member count');require(expected_bytes is None or sum(v['bytes'] for v in inventory.values())==expected_bytes,'exact accepted full expansion bytes');destination.mkdir(parents=True)
 with zipfile.ZipFile(path) as bundle:
  for name in inventory:
   target=destination/Path(*PurePosixPath(name).parts);target.parent.mkdir(parents=True,exist_ok=True)
   with target.open('xb') as stream:stream.write(bundle.read(name))
 require(tree_inventory(destination)==inventory,'every complete extracted file equals original ZIP');return inventory


def verify_extraction(path,destination,root,count=None,total=None):
 inventory=zip_inventory(path,root);require(count is None or len(inventory)==count,'complete ZIP count');require(total is None or sum(x['bytes'] for x in inventory.values())==total,'complete ZIP byte sum');require(tree_inventory(destination)==inventory,'whole retained extraction equals raw ZIP');return inventory


def extract_kernel(path,destination):
 destination=Path(destination);require(not destination.exists(),'fresh kernel extraction')
 with tarfile.open(path,'r:gz') as bundle:
  members=bundle.getmembers();seen=set();total=0
  for member in members:
   name=str(safe_name(member.name));require(name.split('/')[0]==SOURCE_TOP and name not in seen,'whole unique stock tar source root');seen.add(name)
   require(member.isfile() or member.isdir() or member.issym() or member.islnk(),'known stock tar member type')
   if member.issym() or member.islnk():
    link=member.linkname;require(not link.startswith('/') and '\\' not in link and ':' not in link,'relative stock tar link');target=posixpath.normpath(posixpath.join(posixpath.dirname(name),link) if member.issym() else link);require(target==SOURCE_TOP or target.startswith(SOURCE_TOP+'/'),'contained stock source link')
   if member.isfile():total+=member.size;require(total<=4*1024**3,'complete stock tar expansion4GiB cap')
  destination.mkdir(parents=True);bundle.extractall(destination,members=members,filter='data')
 return destination/SOURCE_TOP,{'regular_expanded_bytes':total,'members':len(members)}


def api_validate(pins,run,jobs,listing,artifact):
 require(re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+',pins['repository']) and re.fullmatch(r'[0-9a-f]{40}',pins['source_commit']),'exact generic repository/head pins')
 for key in ('run_id','run_attempt','workflow_id','job_id','artifact_id','zip_bytes','ordinary_members','expanded_bytes'):require(type(pins[key]) is int and pins[key]>0,'integer baseline API pin '+key)
 require(run['id']==pins['run_id'] and run['run_attempt']==pins['run_attempt'] and run['workflow_id']==pins['workflow_id'] and run['head_sha']==pins['source_commit'] and run['status']=='completed' and run['conclusion']=='success' and run['repository']['full_name']==pins['repository'],'authenticated successful exact original baseline run/attempt/head/workflow/repository')
 require(jobs['total_count']==len(jobs['jobs'])==1,'complete unique original baseline job list');job=jobs['jobs'][0];require(job['id']==pins['job_id'] and job['run_id']==pins['run_id'] and job['run_attempt']==pins['run_attempt'] and job['head_sha']==pins['source_commit'] and job['name']=='shash-core' and job['status']=='completed' and job['conclusion']=='success','exact successful original baseline job')
 for name in pins['required_steps']:
  steps=[s for s in job['steps'] if s['name']==name];require(len(steps)==1 and steps[0]['status']=='completed' and steps[0]['conclusion']=='success','successful required baseline step '+name)
 require(listing['total_count']==len(listing['artifacts']) and listing['total_count']<=100,'complete baseline artifact listing');matches=[a for a in listing['artifacts'] if a['id']==pins['artifact_id']];require(len(matches)==1 and matches[0]==artifact,'independent list/individual artifact metadata equality')
 require(artifact['id']==pins['artifact_id'] and artifact['name']==pins['artifact_name']=='note10-shash-core-pc-only' and artifact['expired'] is False and artifact['size_in_bytes']==pins['zip_bytes'] and artifact['digest']=='sha256:'+pins['zip_sha256'] and artifact['workflow_run']['id']==pins['run_id'] and artifact['workflow_run']['head_sha']==pins['source_commit'],'exact unexpired authenticated baseline artifact/digest/size/head')
 return {'run_id':run['id'],'attempt':run['run_attempt'],'job_id':job['id'],'artifact_id':artifact['id'],'source_commit':run['head_sha'],'repository':pins['repository']}


BASELINE_ENDPOINT_ORDER=('run','jobs','artifacts','artifact','baseline')
RETRIEVAL_RECEIPT='AUTHENTICATED-API-RETRIEVAL-RECEIPT.json'
RETRIEVAL_MIRROR_FILES=tuple(label+suffix for label in BASELINE_ENDPOINT_ORDER[:-1] for suffix in ('.json','.stderr.txt'))+('baseline.stderr.txt',RETRIEVAL_RECEIPT,'diagnostics.json')


def redact_bytes(raw,token):
 secret=token.encode('utf8') if isinstance(token,str) else token
 if not secret:return raw,False
 result=raw.replace(secret,b'[REDACTED]')
 # Do not retain a credential prefix when a capped response ends mid-token.
 for length in range(min(len(secret)-1,len(result)),0,-1):
  if result.endswith(secret[:length]):result=result[:-length]+b'[REDACTED]';break
 return result,result!=raw


def redact_text(text,token):return redact_bytes(str(text).encode('utf8',errors='replace'),token)[0].decode('utf8',errors='replace')


def bounded_api_process(command,env,stdout_limit,deadline_seconds=120,stderr_limit=65536,process_factory=None):
 """A supervising thread never blocks on a pipe, spawn or normal wait.

 Raw capture is memory-only and bounded to each limit+1. A cancelled spawn
 owns a late-child cleanup guard; any published child is killed and reaped.
 """
 require(type(stdout_limit) is int and 0<stdout_limit<=CAP and type(stderr_limit) is int and 0<stderr_limit<=65536 and deadline_seconds>0,'bounded API transport limits');started=time.monotonic();deadline=started+deadline_seconds;cancel=threading.Event();spawned=threading.Event();changed=threading.Event();lock=threading.Lock();cleanup_lock=threading.Lock();state={'process':None,'spawn_error':None,'cleaned':False,'killed':False,'reaped':False,'cleanup_error':None};captures={n:{'data':bytearray(),'eof':False,'error':None,'cap':False} for n in ('stdout','stderr')}
 def stop_process():
  with cleanup_lock:
   process=state['process']
   if state['cleaned'] or process is None:return
   if isinstance(process,subprocess.Popen) and not getattr(process,'_child_created',False):return
   state['cleaned']=True
   try:
    if process.poll() is None:process.kill();state['killed']=True
    process.wait(timeout=2);state['reaped']=True
   except Exception as error:state['cleanup_error']=type(error).__name__+': '+str(error)
 def spawn():
  try:
   if process_factory is None:
    # Publish the owned Popen object before __init__ can wait on its exec pipe.
    process=subprocess.Popen.__new__(subprocess.Popen);state['process']=process;subprocess.Popen.__init__(process,command,stdout=subprocess.PIPE,stderr=subprocess.PIPE,env=env,bufsize=0)
   else:state['process']=process_factory(command,stdout=subprocess.PIPE,stderr=subprocess.PIPE,env=env,bufsize=0)
  except BaseException as error:state['spawn_error']=type(error).__name__+': '+str(error)
  finally:spawned.set();changed.set()
  if cancel.is_set():stop_process()
 spawner=threading.Thread(target=spawn,daemon=True);spawner.start();failure=None
 readers=[]
 try:
  while not spawned.is_set():
   remaining=deadline-time.monotonic()
   if remaining<=0:failure='total-deadline-during-spawn';cancel.set();stop_process();break
   changed.wait(min(remaining,.02));changed.clear()
  readers=[];process=state['process']
  def read_stream(name,stream,limit):
   capture=captures[name]
   try:
    while not cancel.is_set():
     with lock:remaining=limit+1-len(capture['data'])
     if remaining<=0:
      with lock:capture['cap']=True
      changed.set();return
     block=stream.read(min(8192,remaining))
     with lock:
      if not block:capture['eof']=True;changed.set();return
      require(type(block) is bytes,'byte-oriented API pipe');capture['data'].extend(block)
      if len(capture['data'])>limit:capture['cap']=True;changed.set();return
     changed.set()
   except Exception as error:
    with lock:capture['error']=type(error).__name__+': '+str(error)
    changed.set()
  if failure is None and state['spawn_error'] is not None:failure='spawn-error'
  if failure is None and time.monotonic()>=deadline:failure='total-deadline-after-spawn'
  if failure is None:
   for name,limit in (('stdout',stdout_limit),('stderr',stderr_limit)):
    thread=threading.Thread(target=read_stream,args=(name,getattr(process,name),limit),daemon=True);readers.append(thread);thread.start()
   while True:
    with lock:cap=any(c['cap'] for c in captures.values());read_error=any(c['error'] for c in captures.values());eof=all(c['eof'] for c in captures.values())
    if cap:failure='stream-cap';break
    if read_error:failure='pipe-read-error';break
    if time.monotonic()>=deadline:failure='total-deadline-during-read-or-wait';break
    try:code=process.poll()
    except Exception as error:failure='poll-error: '+type(error).__name__+': '+str(error);break
    if code is not None and eof:
     try:process.wait(timeout=max(.001,deadline-time.monotonic()));state['reaped']=True
     except Exception as error:failure='wait-error: '+type(error).__name__+': '+str(error)
     break
    changed.wait(min(.02,max(.001,deadline-time.monotonic())));changed.clear()
 except BaseException as error:failure='supervisor-error: '+type(error).__name__+': '+str(error);cancel.set();stop_process()
 if failure is not None:cancel.set();stop_process()
 for thread in readers:thread.join(timeout=.5)
 spawner.join(timeout=.5)
 if any(t.is_alive() for t in readers):failure=failure or 'pipe-reader-not-settled'
 if spawner.is_alive():failure=failure or 'spawn-not-settled-with-cancel-guard'
 with lock:result={name:{'observed':bytes(c['data']),'eof':c['eof'],'error':c['error'],'cap':c['cap']} for name,c in captures.items()}
 result.update(returncode=getattr(state['process'],'returncode',None),failure=failure,spawn_error=state['spawn_error'],cleanup_error=state['cleanup_error'],killed=state['killed'],reaped=state['reaped'],elapsed_seconds=time.monotonic()-started,deadline_seconds=deadline_seconds);return result


def mirror_retrieval_evidence(source,destination,token='',ceiling=CAP):
 source=Path(source);destination=Path(destination);require(0<ceiling<=CAP and source.resolve()!=destination.resolve(),'bounded disjoint allowlisted retrieval mirror');destination.mkdir(parents=True,exist_ok=True);require(destination.is_dir() and not destination.is_symlink() and not getattr(destination.lstat(),'st_file_attributes',0)&1024,'ordinary retrieval mirror directory');rows={};total=0
 for name in RETRIEVAL_MIRROR_FILES:
  path=source/name
  if not path.exists() and not path.is_symlink():continue
  info=path.lstat();require(stat.S_ISREG(info.st_mode) and not path.is_symlink() and not getattr(info,'st_file_attributes',0)&1024,'ordinary allowlisted retrieval evidence only');require(info.st_size<=ceiling-total,'whole allowlisted retrieval mirror ceiling')
  with path.open('rb') as stream:require(five(os.fstat(stream.fileno()))==five(info),'same opened mirror input');raw=stream.read(ceiling-total+1);require(len(raw)==info.st_size and five(os.fstat(stream.fileno()))==five(info)==five(path.lstat()),'bounded complete stable mirror input')
  stored,redacted=redact_bytes(raw,token);total+=len(stored);require(total<=ceiling,'whole redacted retrieval mirror ceiling');target=destination/name
  if target.exists():require(target.is_file() and not target.is_symlink() and target.read_bytes()==stored,'existing mirrored evidence unchanged')
  else:
   with target.open('xb') as stream:stream.write(stored)
  rows[name]={'bytes':len(stored),'sha256':digest(stored),'mirror_redacted':redacted}
 return rows


def retrieve_baseline(pins,directory,process_factory=None,deadline_seconds=120):
 require(re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+',pins['repository']) and all(type(pins[k]) is int and pins[k]>0 for k in ('run_id','run_attempt','workflow_id','job_id','artifact_id','zip_bytes')) and re.fullmatch(r'[0-9a-f]{40}',pins['source_commit']) and re.fullmatch(r'[0-9a-f]{64}',pins['zip_sha256']),'generic baseline API pins validated before credential use');directory=Path(directory);require(not directory.exists(),'fresh authenticated retrieval directory');directory.mkdir(parents=True);rows=[];env={k:v for k,v in os.environ.items() if not k.startswith(('GH_DEBUG','GH_TRACE','GIT_TRACE','CURL_VERBOSE'))};env['GH_HOST']='github.com';token=env.get('GH_TOKEN','');receipt={'schema':2,'rows':rows,'completed':False,'success':False,'identity_validation_success':False};previous=None
 def persist():
  nonlocal previous
  path=directory/RETRIEVAL_RECEIPT
  if previous is not None:require(path.is_file() and not path.is_symlink() and digest(path.read_bytes())==previous,'own exclusive canonical retrieval receipt')
  else:require(not path.exists(),'fresh exclusive retrieval receipt')
  raw=(json.dumps(receipt,indent=2,sort_keys=True)+'\n').encode();require(token.encode() not in raw if token else True,'no credential in canonical receipt');temporary=directory/(RETRIEVAL_RECEIPT+'.next')
  with temporary.open('xb') as stream:stream.write(raw)
  os.replace(temporary,path);previous=digest(raw)
 def call(label,endpoint,binary=False):
  require(label==BASELINE_ENDPOINT_ORDER[len(rows)] and endpoint.startswith('repos/'+pins['repository']+'/actions/') and '://' not in endpoint and token not in endpoint,'exact ordered credential-free API endpoint');command=['gh','api',endpoint];limit=pins['zip_bytes'] if binary else 8*1024*1024;capture=bounded_api_process(command,env,limit,deadline_seconds,process_factory=process_factory);row={'label':label,'command':command,'returncode':capture['returncode'],'no_code_reason':None if capture['returncode'] is not None else 'spawn/read failure without exit code','completed':False,'success':False,'killed':capture['killed'],'reaped':capture['reaped'],'elapsed_seconds':capture['elapsed_seconds'],'deadline_seconds':deadline_seconds,'spawn_error':redact_text(capture['spawn_error'],token) if capture['spawn_error'] else None,'cleanup_error':redact_text(capture['cleanup_error'],token) if capture['cleanup_error'] else None};rows.append(row)
  for name,bound in (('stdout',limit),('stderr',65536)):
   observed=capture[name]['observed'];kept=observed[:bound];stored,changed=(kept,False) if binary and name=='stdout' else redact_bytes(kept,token);stored_over_cap=len(stored)>bound;stored=stored[:bound];filename=label+('.zip' if binary and name=='stdout' else '.json' if name=='stdout' else '.stderr.txt')
   with (directory/filename).open('xb') as stream:stream.write(stored)
   row[name]={'path':filename,'observed_bytes':len(observed),'observed_sha256':digest(observed),'stored_bytes':len(stored),'stored_sha256':digest(stored),'redacted':changed,'truncated':len(observed)>bound or stored_over_cap,'eof':capture[name]['eof'],'read_error':redact_text(capture[name]['error'],token) if capture[name]['error'] else None}
  row.update(path=row['stdout']['path'],bytes=row['stdout']['stored_bytes'],sha256=row['stdout']['stored_sha256']);reason=capture['failure'] or capture['spawn_error'] or capture['cleanup_error'];row['completed']=reason is None and all(capture[n]['eof'] for n in ('stdout','stderr')) and capture['reaped'];row['success']=row['completed'] and row['returncode']==0 and not row['stdout']['redacted'] and not row['stdout']['truncated'];row['failure_reason']=redact_text(reason or ('nonzero-exit' if row['returncode']!=0 else 'redacted-or-truncated-success-response' if not row['success'] else ''),token);persist()
  require(row['success'],'authenticated baseline retrieval failed: '+label+' '+row['failure_reason'])
  if binary:return directory/row['path']
  try:return json.loads((directory/row['path']).read_bytes())
  except Exception as error:row['success']=False;row['failure_reason']=redact_text(type(error).__name__+': '+str(error),token);persist();raise ValueError('invalid authenticated JSON: '+label) from None
 try:
  require(re.fullmatch(r'[A-Za-z0-9_.-]{8,4096}',token),'existing bounded ASCII Actions credential required, never printed');persist();prefix='repos/'+pins['repository']+'/actions/';run=call('run',prefix+'runs/'+str(pins['run_id'])+'/attempts/'+str(pins['run_attempt']));jobs=call('jobs',prefix+'runs/'+str(pins['run_id'])+'/attempts/'+str(pins['run_attempt'])+'/jobs?filter=all&per_page=100');listing=call('artifacts',prefix+'runs/'+str(pins['run_id'])+'/artifacts?per_page=100');artifact=call('artifact',prefix+'artifacts/'+str(pins['artifact_id']));identity=api_validate(pins,run,jobs,listing,artifact);receipt.update(identity=identity,identity_validation_success=True);persist();raw=call('baseline',prefix+'artifacts/'+str(pins['artifact_id'])+'/zip',True);require(raw.stat().st_size==pins['zip_bytes'] and digest(raw.read_bytes())==pins['zip_sha256'],'complete authenticated baseline ZIP digest/bytes');receipt.update(completed=True,success=True);persist();return raw
 except BaseException as error:
  receipt.update(completed=False,success=False,failure_reason=redact_text(type(error).__name__+': '+str(error),token));persist();write(directory/'diagnostics.json',{'success':False,'completed_endpoints':len(rows),'failure_reason':receipt['failure_reason'],'automatic_retry':False});raise ValueError(receipt['failure_reason']) from None


def command_line(text,target):
 require(type(text) is str and len(text)<=2*1024*1024,'bounded actual .cmd text');prefix='cmd_'+target+' := ';lines=[line for line in text.splitlines() if line.startswith(prefix)];require(len(lines)==1,'one exact saved Kbuild command assignment');line=lines[0][len(prefix):];require(not any(c in line for c in (';','\n','`','$','|','&','<','>')),'no shell postfix/substitution in actual command');return shlex.split(line,posix=True)


def normalized(args,roots):
 require(set(roots)=={'source','objects','compiler-include'} and all(PurePosixPath(p).is_absolute() for p in roots.values()),'explicit absolute mapped provenance roots');result=[]
 for arg in args:
  replacements=[]
  for label,root in roots.items():
   for prefix in ('','-I','O='):
    value=prefix+root
    if arg==value or arg.startswith(value+'/'):replacements.append(prefix+'{'+label+'}'+arg[len(value):])
  require(len(replacements)<=1,'unambiguous exact root mapping');result.append(replacements[0] if replacements else arg)
 return result


def composite_command(args,linker):
 require(args and args[0] in ('aarch64-linux-gnu-ld',linker['path']) and args[1:]==['-m','aarch64linux','--no-relax','-r','-o','crypto/crypto_hash.o','crypto/ahash.o','crypto/shash.o'],'exact GNU mapless composite command/input order')
 require(linker['role']=='aarch64-linux-gnu-ld' and PurePosixPath(linker['path']).is_absolute() and re.fullmatch(r'[0-9a-f]{64}',linker['sha256']) and re.search(r'GNU ld[^\n]*\b2\.38(?:[.\s)\-]|$)',linker['version']) and 'LLD' not in linker['version'],'pinned GNU binutils2.38 linker profile');return {'args':args,'linker':linker}


def config_contract(raw):
 text=raw.decode('ascii');required=('CONFIG_CRYPTO_HASH2=y','CONFIG_LTO_NONE=y','CONFIG_THIN_ARCHIVES=y','CONFIG_MODVERSIONS=y','# CONFIG_LTO is not set','# CONFIG_LTO_CLANG is not set','# CONFIG_DEBUG_SECTION_MISMATCH is not set')
 for value in required:require(text.splitlines().count(value)==1,'exact baseline source config '+value)
 return {'source_CONFIG_THIN_ARCHIVES':'y','effective_make_CONFIG_THIN_ARCHIVES':'','declared_LDFLAGS':'-m aarch64linux --no-relax'}


def baseline_labels(root,pins):
 root=Path(root);result=json.loads((root/'result.json').read_text());manifest=json.loads((root/'source-manifest.json').read_text());context=result['ci_context']
 require(result['passed'] is True and result['version']=='v64' and result['executed_fixture_commands']==0 and context['GITHUB_RUN_ID']==str(pins['run_id']) and context['GITHUB_RUN_ATTEMPT']==str(pins['run_attempt']) and context['GITHUB_SHA']==pins['source_commit'] and context['GITHUB_JOB']=='shash-core','accepted producer labels retain original source/context, not a new semantic pass')
 require(manifest==result['source_sha256'],'baseline original complete source manifest binding')
 for name,sha in manifest.items():safe_name(name);require(digest((root/'source'/name).read_bytes())==sha,'baseline original source byte identity')
 for name,sha in result['files_sha256'].items():safe_name(name);require(digest((root/name).read_bytes())==sha,'baseline fixed evidence byte identity')
 raw=(root/'evidence/kbuild/crypto/shash.o').read_bytes();require(digest(raw)==pins['object_sha256']==result['proof']['object_sha256'],'accepted baseline object identity without old semantic proof replay');return result


def baseline_api_receipt(directory,pins):
 directory=Path(directory);receipt=json.loads((directory/RETRIEVAL_RECEIPT).read_text());rows=receipt['rows'];prefix='repos/'+pins['repository']+'/actions/';endpoints={'run':prefix+'runs/'+str(pins['run_id'])+'/attempts/'+str(pins['run_attempt']),'jobs':prefix+'runs/'+str(pins['run_id'])+'/attempts/'+str(pins['run_attempt'])+'/jobs?filter=all&per_page=100','artifacts':prefix+'runs/'+str(pins['run_id'])+'/artifacts?per_page=100','artifact':prefix+'artifacts/'+str(pins['artifact_id']),'baseline':prefix+'artifacts/'+str(pins['artifact_id'])+'/zip'};require(receipt['schema']==2 and receipt['completed'] is True and receipt['success'] is True and receipt['identity_validation_success'] is True and [r['label'] for r in rows]==list(BASELINE_ENDPOINT_ORDER),'exact successful ordered five-endpoint baseline closure')
 for row in rows:
  label=row['label'];stdout=row['stdout'];stderr=row['stderr'];require(row['command']==['gh','api',endpoints[label]] and row['returncode']==0 and row['completed'] is True and row['success'] is True and row['reaped'] is True and row['killed'] is False and row['spawn_error'] is None and row['cleanup_error'] is None and row['failure_reason']=='' and not stdout['redacted'] and not stdout['truncated'] and not stderr['truncated'] and stdout['eof'] is True and stderr['eof'] is True and stdout['read_error'] is None and stderr['read_error'] is None,'complete unaltered successful baseline endpoint')
  require(stdout['observed_bytes']==stdout['stored_bytes']==row['bytes'] and stdout['observed_sha256']==stdout['stored_sha256']==row['sha256'],'original observed/stored success response identity')
  for stream in ('stdout','stderr'):
   entry=row[stream];expected=label+('.zip' if label=='baseline' and stream=='stdout' else '.json' if stream=='stdout' else '.stderr.txt');require(entry['path']==expected,'exact allowlisted endpoint response path')
   if label=='baseline' and stream=='stdout':require(row['bytes']==pins['zip_bytes'] and row['sha256']==pins['zip_sha256'],'authenticated full raw baseline ZIP binding');continue
   raw=(directory/expected).read_bytes();require(len(raw)==entry['stored_bytes'] and digest(raw)==entry['stored_sha256'],'complete stored baseline metadata/diagnostic bytes')
  require(row['path']==stdout['path'],'canonical response alias')
 return receipt


def dependency_tokens(text,target):
 prefix='deps_'+target+' := ';lines=text.splitlines();starts=[i for i,line in enumerate(lines) if line.startswith(prefix)];require(len(starts)==1,'one actual fixdep dependency assignment');tokens=[]
 for line in lines[starts[0]+1:]:
  if not line.strip():break
  value=line.strip();require(value.endswith('\\'),'finite continued fixdep dependency');value=value[:-1].strip();optional=False
  if value.startswith('$(wildcard ') and value.endswith(')'):value=value[11:-1].strip();optional=True
  require(value and not any(c in value for c in ('$',';','`','|','&','<','>','\n')) and len(shlex.split(value))==1,'one bounded ordinary fixdep token');tokens.append((value,optional))
 require(tokens,'complete nonempty fixdep dependency inventory');return tokens


def prerequisite_capture(objects,source,compiler_include,target,destination):
 roots={'objects':str(Path(objects).resolve()),'source':str(Path(source).resolve()),'compiler-include':str(Path(compiler_include).resolve())};objects=Path(objects);destination=Path(destination);destination.mkdir(parents=True);cmd=objects/(PurePosixPath(target).parent/('.'+PurePosixPath(target).name+'.cmd'));text=cmd.read_text();tokens=dependency_tokens(text,target);tokens+=[(str(objects/x),False) for x in ('.config','include/generated/autoconf.h','include/config/auto.conf')];files={};optional=[];mapping={}
 for token,may_absent in tokens:
  path=Path(token) if Path(token).is_absolute() else objects/token;path=path.resolve();matches=[(label,Path(root)) for label,root in roots.items() if path.is_relative_to(Path(root))];require(len(matches)==1,'prerequisite belongs to one explicit actual root');label,root=matches[0];key=label+'/'+path.relative_to(root).as_posix()
  if not path.exists():require(may_absent,'mandatory prerequisite missing');optional.append(key);continue
  require(path.is_file(),'ordinary actual prerequisite file');raw=path.read_bytes();require(len(raw)<=8*1024*1024,'bounded prerequisite bytes');files[key]=digest(raw);mapping[token]=key;out=destination/key;out.parent.mkdir(parents=True,exist_ok=True)
  if not out.exists():out.write_bytes(raw)
 require(sum(p.stat().st_size for p in destination.rglob('*') if p.is_file())<=CAP,'complete prerequisite capture cap');return {'roots':roots,'files_sha256':files,'optional_absent':sorted(set(optional)),'token_to_key':mapping,'actual_cmd_sha256':digest(cmd.read_bytes()),'actual_CC_argv':command_line(text,target)}


def leaf_equality(baseline,old_dependencies,new_dependencies):
 require(old_dependencies['files_sha256']==new_dependencies['files_sha256'],'complete original source/generated/compiler-resource prerequisite identity')
 require(normalized(baseline['command_origin']['args'],old_dependencies['roots'])==normalized(new_dependencies['actual_CC_argv'],new_dependencies['roots']),'exact CC argv modulo explicitly mapped roots only')
 return {'old_roots':old_dependencies['roots'],'new_roots':new_dependencies['roots'],'files_sha256':new_dependencies['files_sha256'],'normalized_CC_argv':normalized(new_dependencies['actual_CC_argv'],new_dependencies['roots']),'old_semantic_checks_replayed':False}
