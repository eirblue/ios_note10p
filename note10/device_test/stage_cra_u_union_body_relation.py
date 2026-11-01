"""Public CI entrypoint; stdlib public-seven source gate before project imports."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import queue
import signal
import stat
import subprocess
import threading
import time

PUBLIC=('note10/device_test/cra_u_union_body_input_contract.py', 'note10/device_test/cra_u_union_body_relation.py', 'note10/device_test/build_cra_u_union_body_relation.py', 'note10/device_test/stage_cra_u_union_body_relation.py', 'note10/device_test/test_cra_u_union_body_relation.py', 'note10/device_test/cra_u_union_body_control.json', '.github/workflows/note10-cra-u-union-body.yml')
CONTROL=PUBLIC[5]

def _require(ok,message):
    if not ok: raise ValueError(message)


def _json(raw):
    def pairs(rows):
        result={}
        for key,value in rows: _require(key not in result,'duplicate JSON key'); result[key]=value
        return result
    def bad(value): raise ValueError('nonfinite JSON')
    return json.loads(raw.decode('utf8'),object_pairs_hook=pairs,parse_constant=bad)


def _ident(st):
    result=tuple(getattr(st,n) for n in ('st_dev','st_ino','st_nlink','st_size','st_mtime_ns','st_ctime_ns'))
    _require(all(type(x) is int for x in result),'integer per-API identity')
    if os.name=='nt':
        birth=getattr(st,'st_birthtime_ns',None); _require(type(birth) is int,'exact Windows integer birthtime'); result+=(birth,)
    return result


def _ordinary(path,directory=False):
    path=Path(os.path.abspath(path))
    for part in (*reversed(path.parents),path):
        st=part.lstat(); _require(not stat.S_ISLNK(st.st_mode) and not part.is_symlink() and not getattr(st,'st_file_attributes',0)&1024,'ordinary nonlink/reparse bootstrap path')
        if part!=path: _require(stat.S_ISDIR(st.st_mode),'ordinary ancestor directory')
    _require(stat.S_ISDIR(st.st_mode) if directory else stat.S_ISREG(st.st_mode) and st.st_nlink==1,'ordinary bootstrap target')
    return st


def _read(path,cap,expected_sha=None,expected_bytes=None):
    path=Path(os.path.abspath(path)); before=_ordinary(path); first=_ident(before); _require(before.st_size<=cap,'stat bound before bootstrap read')
    with path.open('rb') as stream:
        fd=_ident(os.fstat(stream.fileno())); _require(first[:5]==fd[:5] and (first[6:]==fd[6:] if os.name=='nt' else first[5:]==fd[5:]),'compatible canonical bootstrap APIs')
        raw=stream.read(cap+1); end=_ident(os.fstat(stream.fileno()))
    _require(len(raw)==before.st_size<=cap and fd==end and first==_ident(_ordinary(path)),'stable bounded bootstrap snapshot')
    _require(expected_sha is None or hashlib.sha256(raw).hexdigest()==expected_sha,'bootstrap exact SHA')
    _require(expected_bytes is None or type(expected_bytes) is int and len(raw)==expected_bytes,'bootstrap exact bytes')
    return raw,(path,first)


def _stable(guards):
    for path,identity in guards: _require(_ident(_ordinary(path))==identity,'bootstrap inputs unchanged through use')


def _fresh_output(path):
    path=Path(os.path.abspath(path)); _require(not os.path.lexists(path),'fresh exclusive output'); _ordinary(path.parent,True); return path


def _emit(path,value):
    path=_fresh_output(path); raw=(json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False)+'\n').encode(); _require(len(raw)<=8388608,'bounded exclusive receipt')
    with path.open('xb') as stream: stream.write(raw)



def _redact(raw):
    for key in ('GH_TOKEN','GITHUB_TOKEN'):
        token=os.environ.get(key,'').encode()
        if not token: continue
        raw=raw.replace(token,b'<redacted>')
        for length in range(len(token)-1,0,-1):
            if raw.endswith(token[:length]): raw=raw[:-length]+b'<redacted-prefix>'; break
    return raw


def _git_read(argv,deadline,environment,clock=time.monotonic,popen=subprocess.Popen):
    start=clock(); _require(start<deadline,'shared60s source deadline before command')
    chunks={'stdout':[],'stderr':[]}; sizes={'stdout':0,'stderr':0}; limits={'stdout':1048576,'stderr':65536}; events=queue.Queue(maxsize=16); stop=threading.Event(); threads=[]; proc=None; rc=None; failure=None; timed=False; capped=False
    def pump(name,pipe):
        try:
            while not stop.is_set():
                chunk=pipe.read(4096)
                while not stop.is_set():
                    try: events.put((name,chunk,None),timeout=.05); break
                    except queue.Full: pass
                if not chunk: return
        except Exception as exc:
            while not stop.is_set():
                try: events.put((name,b'',str(exc)),timeout=.05); return
                except queue.Full: pass
    try:
        kwargs={'stdin':subprocess.DEVNULL,'stdout':subprocess.PIPE,'stderr':subprocess.PIPE,'shell':False,'bufsize':0,'env':environment}
        if os.name!='nt': kwargs['start_new_session']=True
        proc=popen(argv,**kwargs)
        for name,pipe in (('stdout',proc.stdout),('stderr',proc.stderr)):
            thread=threading.Thread(target=pump,args=(name,pipe),daemon=True); thread.start(); threads.append(thread)
        done=set()
        while len(done)<2:
            remaining=deadline-clock()
            if remaining<=0: timed=True; raise TimeoutError('shared60s source deadline')
            try: name,chunk,error=events.get(timeout=min(.05,remaining))
            except queue.Empty: continue
            _require(error is None,'Git stream error')
            if not chunk: done.add(name); continue
            room=limits[name]+1-sizes[name]
            if room>0: chunks[name].append(chunk[:room]); sizes[name]+=min(room,len(chunk))
            if sizes[name]>limits[name]: capped=True; raise ValueError('source Git byte cap: '+name)
        remaining=deadline-clock()
        if remaining<=0: timed=True; raise TimeoutError('source deadline before command reap')
        rc=proc.wait(timeout=remaining); _require(rc==0,'missing/unsupported local Git object')
    except Exception as exc: failure=exc; timed=timed or isinstance(exc,(TimeoutError,subprocess.TimeoutExpired))
    finally:
        stop.set()
        if proc is not None:
            if proc.poll() is None:
                if os.name!='nt':
                    try: os.killpg(proc.pid,signal.SIGKILL)
                    except ProcessLookupError: pass
                else: proc.kill()
            if rc is None:
                try: rc=proc.wait(timeout=5)
                except Exception as exc: failure=failure or exc
        for thread in threads: thread.join(timeout=.1)
        if any(t.is_alive() for t in threads): failure=failure or TimeoutError('source pipe did not stop after owned process kill/reap')
        else:
            if proc is not None: proc.stdout.close(); proc.stderr.close()
    stdout=b''.join(chunks['stdout']); stderr=_redact(b''.join(chunks['stderr']))
    row={'argv':argv,'returncode':rc,'stdout':{'bytes':len(stdout),'sha256':hashlib.sha256(stdout).hexdigest()},'stderr':{'bytes':len(stderr),'sha256':hashlib.sha256(stderr).hexdigest(),'redacted_utf8':stderr.decode('utf8','replace')},'elapsed_seconds':clock()-start,'timed_out':timed,'capped':capped,'complete':failure is None}
    if failure is not None:
        failure.source_command_receipt=row
        raise failure
    return stdout,row


def _ci_preflight(control_sha,environment=None,runner=None,clock=time.monotonic,progress=None):
    env=dict(os.environ if environment is None else environment); runner=_git_read if runner is None else runner
    _require(type(control_sha) is str and len(control_sha)==64 and all(c in '0123456789abcdef' for c in control_sha),'sole lowerhex control SHA')
    state={} if progress is None else progress; state.update(schema='v69-public-source-manifest-v1',context={},files={},bootstrap={'status':'failed','git_read_command_count':0,'shared_deadline_seconds':60,'elapsed_seconds':0,'commands':[],'failed_next_index':0,'exception':None})
    records=state['bootstrap']['commands']; started=clock(); deadline=started+60; guards=[]; buffers={}
    try:
        _require(env.get('GITHUB_SERVER_URL')=='https://github.com' and env.get('GITHUB_REPOSITORY')=='eirblue/ios_note10p' and env.get('GITHUB_EVENT_NAME')=='workflow_dispatch' and env.get('GITHUB_RUN_ATTEMPT')=='1','exact GitHub context server/repository/event/attempt')
        commit=env.get('GITHUB_SHA'); workflow=env.get('GITHUB_WORKFLOW_SHA'); _require(type(commit) is str and len(commit)==40 and all(c in '0123456789abcdef' for c in commit) and workflow==commit,'source/workflow lowerhex SHA equality')
        run=env.get('GITHUB_RUN_ID',''); _require(run.isascii() and run.isdecimal() and str(int(run))==run and int(run)>0,'positive canonical run ID')
        workspace=env.get('GITHUB_WORKSPACE',''); root=Path(os.path.abspath(workspace)); _require(workspace==str(root) and Path(workspace).is_absolute(),'canonical exact checkout workspace'); _ordinary(root,True); _ordinary(root/'.git',True)
        state['context']={'server_url':'https://github.com','repository':'eirblue/ios_note10p','event_name':'workflow_dispatch','run_id':int(run),'run_attempt':1,'source_commit':commit,'workflow_commit':workflow,'workflow_path':PUBLIC[-1]}
        child_env={k:v for k,v in env.items() if not k.startswith('GIT_')}; child_env.update(GIT_NO_LAZY_FETCH='1',GIT_TERMINAL_PROMPT='0',GIT_OPTIONAL_LOCKS='0',GIT_CONFIG_NOSYSTEM='1',GIT_CONFIG_GLOBAL=os.devnull)
        argv=['git','-C',str(root),'rev-parse','--verify','HEAD']; raw,row=runner(argv,deadline,child_env); row={'index':0,**row}; records.append(row); _require(raw==commit.encode()+b'\n','HEAD equals event/workflow source, no alternate ref')
        for index,name in enumerate(PUBLIC,1):
            state['bootstrap']['failed_next_index']=index
            data,guard=_read(root/name,1048576); guards.append(guard)
            argv=['git','-C',str(root),'cat-file','blob',commit+':'+name]; blob,row=runner(argv,deadline,child_env); records.append({'index':index,**row})
            _require(blob==data and len(blob)<=1048576,'committed blob equals stable ordinary worktree bytes')
            buffers[name]=data; state['files'][name]={'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}
        _require(hashlib.sha256(buffers[CONTROL]).hexdigest()==control_sha,'fixed control blob equals sole dispatch SHA')
        _require(clock()<=deadline and len(records)==8,'complete source bootstrap within shared60s')
        _stable(guards); state['bootstrap'].update(status='complete',git_read_command_count=8,elapsed_seconds=clock()-started,failed_next_index=None,exception=None)
        return {'root':root,'manifest':state,'buffers':buffers,'guards':guards}
    except Exception as exc:
        if hasattr(exc,'source_command_receipt'): records.append({'index':state['bootstrap']['failed_next_index'],**exc.source_command_receipt})
        state['bootstrap'].update(git_read_command_count=len(records),elapsed_seconds=clock()-started,exception={'type':type(exc).__name__,'message':_redact(str(exc).encode()).decode('utf8','replace')})
        raise


def _import_verified(state,name):
    _require(name in PUBLIC and name in state['buffers'] and state['manifest']['bootstrap']['status']=='complete','all7 verified before project import')
    raw=state['buffers'][name]; row=state['manifest']['files'][name]; _require(len(raw)==row['bytes'] and hashlib.sha256(raw).hexdigest()==row['sha256'],'verified import buffer identity')
    spec=importlib.util.spec_from_file_location('_new_ci_body_'+Path(name).stem,state['root']/name); module=importlib.util.module_from_spec(spec)
    exec(compile(raw,str(state['root']/name),'exec'),module.__dict__); return module


def _fixed_path(value,root,relative):
    path=Path(os.path.abspath(value)); _require(path==root/relative,'fixed owned CI target path'); _ordinary(path.parent,True); return path


def main():
    parser=argparse.ArgumentParser()
    for name in ('source','staging-parent','receipt','control-sha256'): parser.add_argument('--'+name,required=True)
    args=parser.parse_args(); root=Path(os.path.abspath(os.environ.get('GITHUB_WORKSPACE','')))
    source=_fixed_path(args.source,root,'note10/private/v69-ci-union-body'); staging=_fixed_path(args.staging_parent,root,'note10/private/v69-upload-staging'); receipt=_fixed_path(args.receipt,root,'note10/private/v69-stage-receipt.json'); _fresh_output(receipt)
    progress={}
    try:
        state=_ci_preflight(args.control_sha256,progress=progress); c=_import_verified(state,PUBLIC[0]); control=c.parse(state['buffers'][CONTROL]); c.validate_control(control)
        ordinary=_ordinary(source,True); original=c.scan(source); partial='result.json' not in original
        manifest_snap=c.snapshot(source/'source-manifest.json',4194304); producer_manifest=c.parse(manifest_snap['raw'])
        complete=producer_manifest.get('bootstrap',{}).get('status')=='complete'
        if complete:
            c.source_manifest(producer_manifest,state['manifest']['files'],state['manifest']['context'])
            for name,row in state['manifest']['files'].items():
                copied=c.snapshot(source/'source'/name,1048576); c.require({'bytes':copied['bytes'],'sha256':copied['sha256']}==row,'producer retained source equals independent stager Git/worktree'); c.unchanged(copied)
        else: c.require(partial,'incomplete source bootstrap cannot stage as successful proof')
        if not partial:
            snap=c.snapshot(source/'result.json',8388608); result=c.parse(snap['raw']); c.require(result['passed'] is True and result['source_context']==state['manifest']['context'] and result['sources']==state['manifest']['files'] and result['source_preflight_sha256']==c.sha(c.encoded(producer_manifest['bootstrap'])),'producer/stager source-context consistency'); c.unchanged(snap)
        c.fresh(staging,True); destination=c.fresh(staging/c.NAMESPACE,True)
        for name,row in original.items():
            snap=c.snapshot(source/name,33554432); c.require({'bytes':snap['bytes'],'sha256':snap['sha256']}==row,'stable declared source inventory'); target=destination/name; target.parent.mkdir(parents=True,exist_ok=True); c.ordinary(target.parent,True); c.put(target,snap['raw']); c.unchanged(snap)
        c.scan(destination,original); c.scan(source,original); c.unchanged(manifest_snap); _stable(state['guards'])
        _emit(receipt,{'schema':'v69-union-stage-v1','passed':True,'partial_producer':partial,'source_manifest_complete':complete,'source_context':state['manifest']['context'],'stager_source_preflight':state['manifest']['bootstrap'],'files':original,'no_additional_uploaded_member':True})
    except Exception as exc:
        _emit(receipt,{'schema':'v69-union-stage-v1','passed':False,'source_preflight':progress,'exception':{'type':type(exc).__name__,'message':_redact(str(exc).encode()).decode('utf8','replace')},'automatic_retry':False}); raise


if __name__=='__main__': main()
