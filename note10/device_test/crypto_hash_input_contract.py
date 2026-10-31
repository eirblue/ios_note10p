"""New composite's dual protected inputs, authenticated baseline and provenance."""
import hashlib,json,os,posixpath,re,shlex,shutil,stat,subprocess,tarfile,zipfile
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


def retrieve_baseline(pins,directory):
 require(re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+',pins['repository']) and all(type(pins[k]) is int and pins[k]>0 for k in ('run_id','run_attempt','workflow_id','job_id','artifact_id','zip_bytes')) and re.fullmatch(r'[0-9a-f]{40}',pins['source_commit']) and re.fullmatch(r'[0-9a-f]{64}',pins['zip_sha256']),'generic baseline API pins validated before credential use');directory=Path(directory);require(not directory.exists(),'fresh authenticated retrieval directory');directory.mkdir(parents=True);rows=[];env=dict(os.environ,GH_HOST='github.com');require(env.get('GH_TOKEN'),'existing Actions credential required, never altered or printed')
 def call(label,endpoint,binary=False):
  require(endpoint.startswith('repos/'+pins['repository']+'/actions/') and '://' not in endpoint,'fixed authenticated github.com API endpoint');path=directory/(label+('.log' if binary=='log' else '.zip' if binary else '.json'));command=['gh','api',endpoint]
  limit=pins['zip_bytes'] if binary is True else 16*1024*1024 if binary=='log' else 8*1024*1024
  with path.open('xb') as stream:
   process=subprocess.Popen(command,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,env=env);total=0
   try:
    for block in iter(lambda:process.stdout.read(1024*1024),b''):total+=len(block);require(total<=limit,'bounded complete authenticated API response');stream.write(block)
    code=process.wait(timeout=120)
   except BaseException:process.kill();process.wait();raise
  require(code==0,'authenticated API retrieval failed: '+label);raw=path.read_bytes();rows.append({'label':label,'command':command,'returncode':0,'path':str(path),'bytes':len(raw),'sha256':digest(raw)});return path if binary else json.loads(raw)
 prefix='repos/'+pins['repository']+'/actions/';run=call('run',prefix+'runs/'+str(pins['run_id'])+'/attempts/'+str(pins['run_attempt']));jobs=call('jobs',prefix+'runs/'+str(pins['run_id'])+'/attempts/'+str(pins['run_attempt'])+'/jobs?filter=all&per_page=100');listing=call('artifacts',prefix+'runs/'+str(pins['run_id'])+'/artifacts?per_page=100');artifact=call('artifact',prefix+'artifacts/'+str(pins['artifact_id']));identity=api_validate(pins,run,jobs,listing,artifact);call('job-log',prefix+'jobs/'+str(pins['job_id'])+'/logs','log');raw=call('baseline',prefix+'artifacts/'+str(pins['artifact_id'])+'/zip',True);write(directory/'AUTHENTICATED-API-RETRIEVAL-RECEIPT.json',{'rows':rows,'identity':identity});return raw


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
 directory=Path(directory);receipt=json.loads((directory/'AUTHENTICATED-API-RETRIEVAL-RECEIPT.json').read_text());rows=receipt['rows'];prefix='repos/'+pins['repository']+'/actions/';endpoints={'run':prefix+'runs/'+str(pins['run_id'])+'/attempts/'+str(pins['run_attempt']),'jobs':prefix+'runs/'+str(pins['run_id'])+'/attempts/'+str(pins['run_attempt'])+'/jobs?filter=all&per_page=100','artifacts':prefix+'runs/'+str(pins['run_id'])+'/artifacts?per_page=100','artifact':prefix+'artifacts/'+str(pins['artifact_id']),'job-log':prefix+'jobs/'+str(pins['job_id'])+'/logs','baseline':prefix+'artifacts/'+str(pins['artifact_id'])+'/zip'};require(len(rows)==len(endpoints) and {r['label'] for r in rows}==set(endpoints),'complete original baseline authenticated retrieval closure')
 for row in rows:
  label=row['label'];require(row['command']==['gh','api',endpoints[label]] and row['returncode']==0,'exact authenticated baseline endpoint receipt')
  if label=='baseline':require(row['bytes']==pins['zip_bytes'] and row['sha256']==pins['zip_sha256'],'authenticated full raw baseline ZIP binding');continue
  raw=(directory/(label+('.log' if label=='job-log' else '.json'))).read_bytes();require(len(raw)==row['bytes'] and digest(raw)==row['sha256'],'complete retained baseline API/log bytes')
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
