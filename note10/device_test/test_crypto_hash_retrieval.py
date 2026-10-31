"""CP2 transport-only synthetic cases; no CP1 fixture imports or network calls."""
import argparse,copy,io,json,os,stat,subprocess,sys,tempfile,threading,time
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from crypto_hash_input_contract import bounded_api_process,retrieve_baseline,baseline_api_receipt,mirror_retrieval_evidence,redact_bytes,BASELINE_ENDPOINT_ORDER,RETRIEVAL_RECEIPT,RETRIEVAL_MIRROR_FILES,api_validate
from crypto_hash_composite import require,digest
from build_crypto_hash_composite import PUBLIC,preserve_failure_files

TOKEN='synthetic-credential-for-transport-only'
SHORT_PREFIX_CASES=('capped-stdout-token-prefix-1-redacted','capped-stdout-token-prefix-2-redacted','capped-stdout-token-prefix-3-redacted','capped-stderr-token-prefix-1-redacted','capped-stderr-token-prefix-2-redacted','capped-stderr-token-prefix-3-redacted')
CASES=('five-endpoint-ordered-success-no-log-request','bounded-redacted-nonzero-stderr-receipt','blocked-stdout-total-deadline-kill-reap','blocked-stderr-total-deadline-kill-reap','closed-pipes-stalled-wait-total-deadline','stdout-cap-bounded-partial-receipt','stderr-cap-bounded-partial-receipt','spawn-exception-redacted-persistent-receipt','read-exception-redacted-persistent-receipt','invalid-JSON-persistent-failed-row','identity-rejection-persistent-four-row-prefix','stdout-token-split-chunks-fails-success','stderr-token-split-chunks-redacted','debug-environment-suppressed','observed-and-redacted-digests-distinct','cancelled-spawn-late-child-killed-reaped','real-data-child-blocked-stdout-deadline','real-data-child-blocked-stderr-deadline','allowlisted-mirror-excludes-ZIP-extraction-arbitrary-files','mirror-redacts-text-before-storage','mirror-symlink-reject','mirror-directory-reject','mirror-reparse-reject','mirror-total-ceiling-reject','builder-failure-mirrors-partial-retrieval','five-row-consumer-success-after-mirror','consumer-missing-row-reject','consumer-duplicate-row-reject','consumer-extra-old-log-row-reject','consumer-order-reject','consumer-failed-row-reject','consumer-incomplete-row-reject','consumer-unreaped-row-reject','consumer-wrong-endpoint-reject','consumer-observed-hash-mismatch-reject','consumer-stored-hash-mismatch-reject','consumer-redacted-mandatory-success-reject','consumer-truncated-success-reject','consumer-global-failure-reject','consumer-identity-unvalidated-reject','consumer-wrong-ZIP-size-reject','consumer-wrong-ZIP-digest-reject','consumer-changed-metadata-bytes-reject','consumer-changed-stderr-bytes-reject','consumer-unchanged-mandatory-identity-guard','new-standalone-fixture-public-closure','no-credential-in-staged-failure-evidence')+SHORT_PREFIX_CASES


class Stream:
 def __init__(self,chunks=(),stall=False,error=False):self.chunks=list(chunks);self.position=0;self.stall=stall;self.error=error;self.eof=False;self.stop=threading.Event()
 def read(self,size):
  if self.error:raise OSError('synthetic read failure '+TOKEN)
  if self.stall:self.stop.wait(5)
  while self.chunks and not self.chunks[0]:self.chunks.pop(0)
  if self.stop.is_set() or not self.chunks:self.eof=True;return b''
  raw=self.chunks[0];head=raw[self.position:self.position+size];self.position+=len(head)
  if self.position>=len(raw):self.chunks.pop(0);self.position=0
  return head


class Process:
 def __init__(self,stdout=b'',stderr=b'',code=0,stall_out=False,stall_err=False,read_error=False,stall_wait=False):
  self.stdout=Stream(stdout if isinstance(stdout,list) else [stdout],stall_out,read_error);self.stderr=Stream(stderr if isinstance(stderr,list) else [stderr],stall_err);self.code=code;self.returncode=None;self.kill_count=0;self.wait_count=0;self.stall_wait=stall_wait
 def poll(self):
  if self.kill_count:self.returncode=-9
  elif self.stdout.eof and self.stderr.eof and not self.stall_wait:self.returncode=self.code
  return self.returncode
 def kill(self):self.kill_count+=1;self.returncode=-9;self.stdout.stop.set();self.stderr.stop.set()
 def wait(self,timeout=None):
  self.wait_count+=1
  if self.poll() is None:raise subprocess.TimeoutExpired('synthetic process',timeout)
  return self.returncode


def fixture():
 binary=b'synthetic-baseline-archive';pins={'repository':'synthetic/project','run_id':11,'run_attempt':1,'workflow_id':12,'job_id':13,'artifact_id':14,'zip_bytes':len(binary),'ordinary_members':1,'expanded_bytes':1,'source_commit':'a'*40,'zip_sha256':digest(binary),'object_sha256':'b'*64,'artifact_name':'note10-shash-core-pc-only','required_steps':['synthetic-required-step']};run={'id':11,'run_attempt':1,'workflow_id':12,'head_sha':'a'*40,'status':'completed','conclusion':'success','repository':{'full_name':pins['repository']}};jobs={'total_count':1,'jobs':[{'id':13,'run_id':11,'run_attempt':1,'head_sha':'a'*40,'name':'shash-core','status':'completed','conclusion':'success','steps':[{'name':'synthetic-required-step','status':'completed','conclusion':'success'}]}]};artifact={'id':14,'name':pins['artifact_name'],'expired':False,'size_in_bytes':len(binary),'digest':'sha256:'+pins['zip_sha256'],'workflow_run':{'id':11,'head_sha':'a'*40}};responses=[json.dumps(v).encode() for v in (run,jobs,{'total_count':1,'artifacts':[copy.deepcopy(artifact)]},artifact)]+[binary];return pins,responses


def factory_for(responses,first=None):
 calls=[];processes=[]
 def factory(command,**kwargs):
  calls.append({'command':list(command),'env':dict(kwargs['env'])});index=len(calls)-1
  if index==0 and first=='spawn-error':raise OSError('synthetic spawn failure '+TOKEN)
  process=first if index==0 and isinstance(first,Process) else Process(responses[index]);processes.append(process);return process
 return factory,calls,processes


def receipt(directory):return json.loads((Path(directory)/RETRIEVAL_RECEIPT).read_text())


def run_cases(completed=None):
 if completed is None:completed=[]
 def equal(a,b):require(a==b,'independent new CP2 transport expectation')
 def check(name,fn):
  require(name==CASES[len(completed)],'frozen standalone CP2 case order');fn();completed.append(name)
 def rejected(fn):
  try:fn()
  except (ValueError,KeyError,OSError,TypeError):return
  raise ValueError('invalid new CP2 fixture accepted')
 for name in CASES:
  def action(case=name):
   with tempfile.TemporaryDirectory() as tmp,patch.dict(os.environ,{'GH_TOKEN':TOKEN,'GH_DEBUG':'api','GH_DEBUG_API':'1','GIT_TRACE':'1'}):
    root=Path(tmp);directory=root/'input';pins,responses=fixture();first=None
    if case in SHORT_PREFIX_CASES:
     stream='stdout' if 'stdout' in case else 'stderr';length=int(case.split('-')[-2]);prefix=TOKEN[:length].encode();limit=8*1024*1024 if stream=='stdout' else 65536;fragment=b'X'*(limit-length)+prefix+b'!';first=Process(fragment if stream=='stdout' else responses[0],fragment if stream=='stderr' else b'');factory,calls,processes=factory_for(responses,first);rejected(lambda:retrieve_baseline(pins,directory,process_factory=factory,deadline_seconds=2));record=receipt(directory);row=record['rows'][0];entry=row[stream];stored=(directory/entry['path']).read_bytes();require(entry['observed_bytes']==limit+1 and entry['stored_bytes']<=limit and entry['redacted'] and entry['truncated'] and prefix not in stored and row['success'] is False and record['success'] is False,'every capped short prefix removed before storage; no metadata acceptance');mirror_retrieval_evidence(directory,root/'mirror',TOKEN);require(prefix not in (root/'mirror'/entry['path']).read_bytes(),'short prefix absent before forensic staging');equal(len(calls),1);return
    if case in ('blocked-stdout-total-deadline-kill-reap','blocked-stderr-total-deadline-kill-reap','closed-pipes-stalled-wait-total-deadline'):
     first=Process(responses[0],stall_out='stdout' in case,stall_err='stderr' in case,stall_wait='stalled-wait' in case)
    elif case=='bounded-redacted-nonzero-stderr-receipt':first=Process(b'partial metadata',b'failure '+TOKEN.encode(),code=7)
    elif case=='stdout-cap-bounded-partial-receipt':first=Process(b'x'*(8*1024*1024+1))
    elif case=='stderr-cap-bounded-partial-receipt':first=Process(responses[0],b'e'*65537)
    elif case=='spawn-exception-redacted-persistent-receipt':first='spawn-error'
    elif case=='read-exception-redacted-persistent-receipt':first=Process(read_error=True)
    elif case=='invalid-JSON-persistent-failed-row':first=Process(b'{')
    elif case=='identity-rejection-persistent-four-row-prefix':data=json.loads(responses[1]);data['jobs'][0]['id']=99;responses[1]=json.dumps(data).encode()
    elif case=='stdout-token-split-chunks-fails-success':first=Process([b'{"token":"'+TOKEN[:9].encode(),TOKEN[9:].encode()+b'"}'])
    elif case in ('stderr-token-split-chunks-redacted','observed-and-redacted-digests-distinct'):first=Process(responses[0],[b'warning '+TOKEN[:9].encode(),TOKEN[9:].encode()])
    if case=='cancelled-spawn-late-child-killed-reaped':
     delayed=Process()
     def slow(*args,**kwargs):time.sleep(.08);return delayed
     capture=bounded_api_process(['synthetic'],{},32,.02,process_factory=slow);require(capture['failure'] and capture['killed'] and capture['reaped'] and delayed.kill_count==1,'late cancelled owned child cleaned exactly once');return
    if case in ('real-data-child-blocked-stdout-deadline','real-data-child-blocked-stderr-deadline'):
     children=[];code='import time; time.sleep(10)'
     if 'stderr' in case:code='import sys,time; sys.stdout.close(); time.sleep(10)'
     def data_child(*unused,**kwargs):p=subprocess.Popen([sys.executable,'-u','-c',code],**kwargs);children.append(p);return p
     before=time.monotonic();capture=bounded_api_process(['synthetic-data-child'],dict(os.environ),64,.1,process_factory=data_child);require(capture['failure'] and capture['killed'] and capture['reaped'] and children[0].poll() is not None and time.monotonic()-before<3,'real blocked data-only child interrupted/reaped under total deadline');return
    if case.startswith('mirror-') or case=='allowlisted-mirror-excludes-ZIP-extraction-arbitrary-files':
     directory.mkdir();(directory/'run.stderr.txt').write_bytes(b'warning '+TOKEN.encode());(directory/'baseline.zip').write_bytes(TOKEN.encode());(directory/'arbitrary-secret').write_bytes(TOKEN.encode());(directory/'extraction').mkdir()
     if case=='mirror-directory-reject':(directory/'run.json').mkdir();rejected(lambda:mirror_retrieval_evidence(directory,root/'mirror',TOKEN));return
     if case in ('mirror-symlink-reject','mirror-reparse-reject'):
      path=directory/'run.stderr.txt';original=Path.lstat
      def info(self):
       if self==path:return SimpleNamespace(st_mode=stat.S_IFLNK if case=='mirror-symlink-reject' else stat.S_IFREG,st_file_attributes=1024 if case=='mirror-reparse-reject' else 0)
       return original(self)
      with patch.object(Path,'lstat',info):rejected(lambda:mirror_retrieval_evidence(directory,root/'mirror',TOKEN))
      return
     if case=='mirror-total-ceiling-reject':rejected(lambda:mirror_retrieval_evidence(directory,root/'mirror',TOKEN,ceiling=4));return
     result=mirror_retrieval_evidence(directory,root/'mirror',TOKEN);equal(set(result),{'run.stderr.txt'});require(TOKEN.encode() not in (root/'mirror/run.stderr.txt').read_bytes() and result['run.stderr.txt']['mirror_redacted'],'allowlisted bounded redacted mirror');return
    factory,calls,processes=factory_for(responses,first)
    failing=first is not None and case not in ('stderr-token-split-chunks-redacted','observed-and-redacted-digests-distinct') or case=='identity-rejection-persistent-four-row-prefix'
    if failing:
     timeout=.08 if case.startswith('blocked-') or case=='closed-pipes-stalled-wait-total-deadline' else 2
     rejected(lambda:retrieve_baseline(pins,directory,process_factory=factory,deadline_seconds=timeout));record=receipt(directory);require(record['success'] is False and record['completed'] is False and (directory/'diagnostics.json').is_file(),'canonical partial failure persisted');require(TOKEN.encode() not in b''.join(p.read_bytes() for p in directory.iterdir() if p.is_file()),'credential absent from all stored failure text')
     if case=='identity-rejection-persistent-four-row-prefix':equal(len(calls),4);require(not record['identity_validation_success'],'identity failure before ZIP');return
     equal(len(calls),1);row=record['rows'][0];require(row['success'] is False,'failed row cannot satisfy successful closure')
     if case.startswith('blocked-') or case=='closed-pipes-stalled-wait-total-deadline':require(row['killed'] and row['reaped'] and processes[0].kill_count==1,'deadline exact child kill/reap')
     if case=='stdout-cap-bounded-partial-receipt':require(row['stdout']['observed_bytes']==8*1024*1024+1 and row['stdout']['stored_bytes']<=8*1024*1024 and row['stdout']['truncated'],'bounded stdout cap prefix')
     if case=='stderr-cap-bounded-partial-receipt':require(row['stderr']['observed_bytes']==65537 and row['stderr']['stored_bytes']<=65536 and row['stderr']['truncated'],'bounded stderr cap prefix')
     if case=='bounded-redacted-nonzero-stderr-receipt':equal(row['returncode'],7);require(row['stderr']['redacted'],'nonzero redacted diagnostics')
     return
    retrieve_baseline(pins,directory,process_factory=factory,deadline_seconds=1);record=receipt(directory)
    if case=='five-endpoint-ordered-success-no-log-request':equal([r['label'] for r in record['rows']],list(BASELINE_ENDPOINT_ORDER));equal(len(calls),5);require(not any('/logs' in c['command'][-1] for c in calls),'no redundant old log GET');baseline_api_receipt(directory,pins);return
    if case=='debug-environment-suppressed':require(all(not any(k.startswith(('GH_DEBUG','GH_TRACE','GIT_TRACE','CURL_VERBOSE')) for k in c['env']) for c in calls),'unsafe inherited debug disabled');return
    if case in ('stderr-token-split-chunks-redacted','observed-and-redacted-digests-distinct'):
     row=record['rows'][0]['stderr'];require(row['redacted'] and row['observed_sha256']!=row['stored_sha256'] and TOKEN.encode() not in (directory/row['path']).read_bytes(),'split-token redaction and distinct raw/stored facts');return
    if case=='builder-failure-mirrors-partial-retrieval':
     # A separately fresh partial request, never a replay of a completed case.
     partial=root/'partial';f,_,_=factory_for(responses,Process(b'partial',TOKEN.encode(),code=3));rejected(lambda:retrieve_baseline(pins,partial,process_factory=f));out=root/'out';out.mkdir();retained=preserve_failure_files(out,root/'no-build',partial);require('baseline-api/'+RETRIEVAL_RECEIPT in retained and not (out/'baseline-api/baseline.zip').exists(),'partial metadata mirrored before forensic stage');return
    if case=='no-credential-in-staged-failure-evidence':
     partial=root/'partial';f,_,_=factory_for(responses,Process(b'partial '+TOKEN.encode(),TOKEN.encode(),code=5));rejected(lambda:retrieve_baseline(pins,partial,process_factory=f));mirror_retrieval_evidence(partial,root/'mirror',TOKEN);require(TOKEN.encode() not in b''.join(p.read_bytes() for p in (root/'mirror').iterdir()),'all staged diagnostics redacted');return
    if case=='new-standalone-fixture-public-closure':require('note10/device_test/test_crypto_hash_retrieval.py' in PUBLIC,'new standalone fixture belongs to source closure');return
    mirror=root/'mirror';mirror_retrieval_evidence(directory,mirror,TOKEN)
    if case=='five-row-consumer-success-after-mirror':baseline_api_receipt(mirror,pins);return
    if case=='consumer-unchanged-mandatory-identity-guard':
     values=[json.loads((mirror/(label+'.json')).read_text()) for label in BASELINE_ENDPOINT_ORDER[:-1]];values[1]['jobs'][0]['id']=99;rejected(lambda:api_validate(pins,*values));return
    path=mirror/RETRIEVAL_RECEIPT;record=json.loads(path.read_text());row=record['rows'][0]
    if case=='consumer-missing-row-reject':record['rows'].pop()
    elif case=='consumer-duplicate-row-reject':record['rows'][1]=copy.deepcopy(row)
    elif case=='consumer-extra-old-log-row-reject':record['rows'].append(dict(row,label='job-log'))
    elif case=='consumer-order-reject':record['rows'][0:2]=reversed(record['rows'][0:2])
    elif case=='consumer-failed-row-reject':row['success']=False
    elif case=='consumer-incomplete-row-reject':row['completed']=False
    elif case=='consumer-unreaped-row-reject':row['reaped']=False
    elif case=='consumer-wrong-endpoint-reject':row['command'][-1]='repos/other/project/actions/runs/11'
    elif case=='consumer-observed-hash-mismatch-reject':row['stdout']['observed_sha256']='0'*64
    elif case=='consumer-stored-hash-mismatch-reject':row['sha256']=row['stdout']['stored_sha256']='0'*64
    elif case=='consumer-redacted-mandatory-success-reject':row['stdout']['redacted']=True
    elif case=='consumer-truncated-success-reject':row['stdout']['truncated']=True
    elif case=='consumer-global-failure-reject':record['success']=False
    elif case=='consumer-identity-unvalidated-reject':record['identity_validation_success']=False
    elif case=='consumer-wrong-ZIP-size-reject':pins['zip_bytes']+=1
    elif case=='consumer-wrong-ZIP-digest-reject':pins['zip_sha256']='0'*64
    elif case=='consumer-changed-metadata-bytes-reject':(mirror/'run.json').write_bytes(b'changed')
    elif case=='consumer-changed-stderr-bytes-reject':(mirror/'run.stderr.txt').write_bytes(b'changed')
    else:raise ValueError('unhandled new case '+case)
    path.write_text(json.dumps(record));rejected(lambda:baseline_api_receipt(mirror,pins))
  check(name,action)
 return {'passed':True,'cases':completed,'case_count':len(completed),'synthetic_only':True,'actual_network_compiler_target_device_or_CP1_case_execution':False}


def main():
 p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--checkpoint',type=Path,required=True);p.add_argument('--checkpoint-sha256',required=True);p.add_argument('--inventory',type=Path,required=True);p.add_argument('--inventory-sha256',required=True);a=p.parse_args();root=Path(__file__).resolve().parents[2];require(not a.output.exists() and a.output.absolute().is_relative_to(root/'note10/private'),'fresh private CP2 result');completed=[];phase='attribution';attribution={'checkpoint_path':str(a.checkpoint.absolute()),'inventory_path':str(a.inventory.absolute())}
 try:
  cpraw=a.checkpoint.read_bytes();invraw=a.inventory.read_bytes();require(digest(cpraw)==a.checkpoint_sha256 and digest(invraw)==a.inventory_sha256,'exact frozen CP2 checkpoint/inventory SHA256');cp=json.loads(cpraw);inventory=json.loads(invraw);attribution.update(checkpoint_sha256=digest(cpraw),inventory_sha256=digest(invraw));require(cp['version']=='v65' and cp['checkpoint']==2 and cp['new_retrieval_fixture_inventory']==list(CASES) and inventory['cases']==list(CASES) and inventory['case_count']==len(CASES) and inventory['fixture_sha256']==digest(Path(__file__).read_bytes()),'exact standalone CP2 inventory')
  for group in ('public_sources_sha256','private_sources_sha256','shared_sources_sha256'):
   for name,expected in cp[group].items():require(digest((root/name).read_bytes())==expected,'current frozen source/import closure')
  phase='new_retrieval_cases';result=run_cases(completed);result.update(attribution)
 except BaseException as error:
  a.output.parent.mkdir(parents=True,exist_ok=True)
  with a.output.open('x',encoding='utf8',newline='\n') as stream:stream.write(json.dumps(dict(attribution,passed=False,cases=completed,case_count=len(completed),completed_case_names=completed,completed_case_count=len(completed),failing_next_case=CASES[len(completed)] if len(completed)<len(CASES) else None,failure_phase=phase,exception_type=type(error).__name__,exception_message=str(error),automatic_retry=False),indent=2)+'\n')
  raise
 a.output.parent.mkdir(parents=True,exist_ok=True)
 with a.output.open('x',encoding='utf8',newline='\n') as stream:stream.write(json.dumps(result,indent=2)+'\n')
if __name__=='__main__':main()
