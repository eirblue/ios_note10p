"""New finite byte/provenance contract. No prior project code or data readers."""
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import queue
import signal
import stat
import struct
import subprocess
import threading
import time
import zipfile

PUBLIC = ('note10/device_test/cra_u_union_body_input_contract.py', 'note10/device_test/cra_u_union_body_relation.py', 'note10/device_test/build_cra_u_union_body_relation.py', 'note10/device_test/stage_cra_u_union_body_relation.py', 'note10/device_test/test_cra_u_union_body_relation.py', 'note10/device_test/cra_u_union_body_control.json', '.github/workflows/note10-cra-u-union-body.yml')
CONTROL = PUBLIC[5]
NAMESPACE = 'v69-ci-union-body'
CAP = 100663296


def require(ok, message):
    if not ok: raise ValueError(message)


def keys(value, fields):
    require(type(value) is dict and set(value) == set(fields.split()), 'closed keys: ' + fields)


def integer(value, maximum=2**64-1):
    require(type(value) is int and 0 <= value <= maximum, 'exact bounded integer')
    return value


def digest(value):
    require(type(value) is str and len(value)==64 and all(x in '0123456789abcdef' for x in value), 'lowercase SHA256')
    return value


def sha(raw): return hashlib.sha256(raw).hexdigest()


def encoded(value): return (json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False)+'\n').encode()


def parse(raw):
    def pairs(rows):
        out = {}
        for k,v in rows: require(k not in out, 'duplicate JSON key'); out[k]=v
        return out
    def bad(value): raise ValueError('nonfinite JSON')
    return json.loads(raw.decode('utf-8'), object_pairs_hook=pairs, parse_constant=bad)


def identity(st):
    row = tuple(getattr(st,n) for n in ('st_dev','st_ino','st_nlink','st_size','st_mtime_ns','st_ctime_ns'))
    require(all(type(v) is int for v in row), 'integer per-API identity')
    if os.name == 'nt':
        birth = getattr(st,'st_birthtime_ns',None); require(type(birth) is int,'Windows exact integer birthtime'); row += (birth,)
    return row


def compatible(a,b): return a[:5]==b[:5] and (a[6:]==b[6:] if os.name=='nt' else a[5:]==b[5:])


def int5(st): return [st.st_dev,st.st_ino,st.st_size,st.st_mtime_ns,st.st_nlink]


def ordinary(path, directory=False):
    path=Path(os.path.abspath(path))
    for part in (*reversed(path.parents),path):
        st=part.lstat(); require(not stat.S_ISLNK(st.st_mode) and not part.is_symlink() and not getattr(st,'st_file_attributes',0)&1024,'ordinary nonlink/reparse path')
        if part!=path: require(stat.S_ISDIR(st.st_mode),'ordinary directory ancestor')
    require(stat.S_ISDIR(st.st_mode) if directory else stat.S_ISREG(st.st_mode) and st.st_nlink==1,'ordinary target type/nlink')
    return st


def snapshot(path, cap=CAP, expected=None):
    path=Path(os.path.abspath(path)); before=ordinary(path); ident=identity(before)
    require(before.st_size<=cap,'stat bound before materialization')
    with path.open('rb') as stream:
        fd=identity(os.fstat(stream.fileno())); require(compatible(ident,fd),'compatible canonical lstat/fstat identity')
        raw=stream.read(cap+1); end=identity(os.fstat(stream.fileno()))
    require(len(raw)==before.st_size<=cap and fd==end and ident==identity(ordinary(path)),'stable bounded same-buffer snapshot')
    row={'path':path,'raw':raw,'bytes':len(raw),'sha256':sha(raw),'identity':ident,'int5':int5(before)}
    if expected is not None:
        keys(expected,'path bytes sha256 int5'); require(type(expected['int5']) is list and len(expected['int5'])==5 and all(type(v) is int for v in expected['int5']),'typed flat int5')
        require(Path(os.path.abspath(expected['path']))==path and expected['bytes']==row['bytes'] and type(expected['bytes']) is int and expected['sha256']==row['sha256'] and expected['int5']==row['int5'],'exact flat file pin')
    return row


def unchanged(snap): require(identity(ordinary(snap['path']))==snap['identity'],'input unchanged through use')


def fresh(path, directory=False):
    path=Path(os.path.abspath(path)); require(not os.path.lexists(path),'fresh exclusive namespace')
    ordinary(path.parent,True)
    if directory: path.mkdir()
    return path


def put(path,raw):
    path=fresh(path)
    with path.open('xb') as stream: stream.write(raw)
    return {'bytes':len(raw),'sha256':sha(raw)}


def output(path,value):
    raw=encoded(value); require(len(raw)<=8388608,'bounded result JSON'); return put(path,raw)


def safe_name(name):
    require(type(name) is str and 0<len(name)<=1024 and '\\' not in name and ':' not in name and '\x00' not in name,'safe relative name bytes')
    p=PurePosixPath(name); require(not p.is_absolute() and all(x not in ('','.','..') for x in name.split('/')) and str(p)==name,'normalized relative member')
    return name


def scan(root, expected=None, count_cap=4096, aggregate_cap=CAP):
    root=Path(os.path.abspath(root)); initial=identity(ordinary(root,True)); found={}; directories=set(); queue_paths=[(root,'',0)]; entries=0; total=0
    prefixes=None if expected is None else {'/'.join(n.split('/')[:i]) for n in expected for i in range(1,len(n.split('/')))}
    limit=count_cap*2 if expected is None else len(expected)+len(prefixes)
    while queue_paths:
        directory,prefix,depth=queue_paths.pop(); require(depth<=16,'streaming namespace depth'); ordinary(directory,True)
        with os.scandir(directory) as iterator:
            for entry in iterator:
                require(entries<limit,'namespace count before retention'); entries+=1
                name=safe_name(prefix+entry.name)
                require(expected is None or name in expected or name in prefixes,'unknown namespace entry before descent')
                path=Path(entry.path); st=path.lstat()
                require(not stat.S_ISLNK(st.st_mode) and not path.is_symlink() and not getattr(st,'st_file_attributes',0)&1024,'ordinary streaming entry')
                if stat.S_ISDIR(st.st_mode):
                    require(depth<16 and len(queue_paths)<count_cap and name not in directories and (prefixes is None or name in prefixes),'directory prefix/depth/queue limits before retaining')
                    directories.add(name); queue_paths.append((path,name+'/',depth+1))
                else:
                    require(stat.S_ISREG(st.st_mode) and st.st_nlink==1 and name not in found and len(found)<count_cap and (expected is None or name in expected),'regular finite file membership')
                    total+=st.st_size; require(total<=aggregate_cap,'namespace aggregate cap')
                    snap=snapshot(path,aggregate_cap); found[name]={'bytes':snap['bytes'],'sha256':snap['sha256']}; unchanged(snap)
    require(identity(ordinary(root,True))==initial,'stable namespace root identity')
    if expected is not None: require(found==expected and directories==prefixes,'complete namespace equality')
    return found


def archive(raw, expected=None, zip_cap=33554432, expanded_cap=CAP, member_cap=4096):
    require(22<=len(raw)<=zip_cap,'bounded complete ZIP buffer')
    pos=raw.rfind(b'PK\x05\x06',max(0,len(raw)-65557)); require(pos>=0 and pos+22<=len(raw),'ordinary ZIP EOCD')
    _,disk,cdisk,on_disk,count,csz,coff,comment=struct.unpack_from('<4s4H2IH',raw,pos)
    require(disk==cdisk==0 and on_disk==count<=member_cap and count<65535 and csz<2**32-1 and coff<2**32-1 and pos+22+comment==len(raw) and coff+csz==pos,'single disk/non-ZIP64 bounded central count before library allocation')
    files={}; buffers={}; seen=set(); total=0
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        require(len(z.infolist())==count,'complete central record count')
        for entry in z.infolist():
            name=safe_name(entry.filename[:-1] if entry.is_dir() else entry.filename); folded=name.casefold()
            require(folded not in seen and not entry.flag_bits&1 and entry.compress_type in (zipfile.ZIP_STORED,zipfile.ZIP_DEFLATED),'unique ordinary supported archive member'); seen.add(folded)
            mode=(entry.external_attr>>16)&65535; require(not stat.S_ISLNK(mode) and (not mode or stat.S_IFMT(mode) in (0,stat.S_IFREG,stat.S_IFDIR)),'no archive link/special file')
            if entry.is_dir():
                require(entry.file_size==0 and expected is not None and any(n.startswith(name+'/') for n in expected),'only exact expected directory prefixes'); continue
            require(expected is None or name in expected,'unlisted original ZIP file')
            total+=entry.file_size; require(entry.file_size<=expanded_cap and total<=expanded_cap,'expansion cap before read')
            with z.open(entry) as stream: data=stream.read(entry.file_size+1)
            require(len(data)==entry.file_size,'exact bounded archive bytes')
            files[name]={'bytes':len(data),'sha256':sha(data)}; buffers[name]=data
    require(expected is None or files==expected,'same complete bounded raw ZIP inventory')
    return files,buffers


def extract(buffers,dest):
    dest=fresh(dest,True)
    for name,raw in buffers.items():
        name=safe_name(name); path=dest/name; path.parent.mkdir(parents=True,exist_ok=True); ordinary(path.parent,True); put(path,raw)
    return dest


def plaintext(raw,cap=4194304):
    require(type(raw) is bytes and 0<len(raw)<=cap and b'\x00' not in raw,'bounded nonempty nonbinary log')
    text=raw.decode('utf-8-sig'); require(text.strip() and text.lstrip()[:1] not in ('{','[') and all(ord(c)>=32 or c in '\t\r\n' for c in text),'strict UTF8 plaintext, no JSON/control bytes')
    return {'bytes':len(raw),'sha256':sha(raw),'format':'UTF8 optional BOM, no human step captions required'}


def redact(raw,secrets):
    for value in secrets:
        if value:
            token=value.encode() if type(value) is str else value
            raw=raw.replace(token,b'<redacted>')
            for length in range(len(token)-1,0,-1):
                if raw.endswith(token[:length]): raw=raw[:-length]+b'<redacted-prefix>'; break
    return raw


def capture(endpoint,label,parent,deadline,cap,clock=time.monotonic,popen=subprocess.Popen):
    require(type(endpoint) is str and endpoint.startswith('repos/') and not any(c.isspace() for c in endpoint),'closed relative GitHub endpoint')
    parent=Path(parent); ordinary(parent,True); require(clock()<deadline,'shared role deadline before capture')
    for suffix in ('.stdout','.stderr','.receipt.json'): fresh(parent/(label+suffix))
    argv=['gh','api','--hostname','github.com',endpoint]; start=clock(); process=None; pipes=[]; chunks={'stdout':[],'stderr':[]}; sizes={'stdout':0,'stderr':0}; limits={'stdout':cap,'stderr':1048576}; events=queue.Queue(maxsize=16); stopped=threading.Event(); threads=[]; failure=None; rc=None; timed=False; capped=False
    def pump(name,stream):
        try:
            while not stopped.is_set():
                data=stream.read(4096)
                while not stopped.is_set():
                    try: events.put((name,data,None),timeout=.05); break
                    except queue.Full: pass
                if not data: return
        except Exception as exc:
            while not stopped.is_set():
                try: events.put((name,b'',str(exc)),timeout=.05); return
                except queue.Full: pass
    try:
        kwargs={'stdout':subprocess.PIPE,'stderr':subprocess.PIPE,'stdin':subprocess.DEVNULL,'shell':False,'bufsize':0}
        if os.name!='nt': kwargs['start_new_session']=True
        process=popen(argv,**kwargs); pipes=[process.stdout,process.stderr]
        for name,stream in zip(('stdout','stderr'),pipes):
            thread=threading.Thread(target=pump,args=(name,stream),daemon=True); threads.append(thread); thread.start()
        done=set()
        while len(done)<2:
            remaining=deadline-clock()
            if remaining<=0: timed=True; raise TimeoutError('shared180s role deadline')
            try: name,data,error=events.get(timeout=min(.05,remaining))
            except queue.Empty: continue
            require(error is None,'capture stream error')
            if not data: done.add(name); continue
            room=limits[name]+1-sizes[name]
            if room>0: chunks[name].append(data[:room]); sizes[name]+=min(room,len(data))
            if sizes[name]>limits[name]: capped=True; raise ValueError('capture byte cap: '+name)
        remaining=deadline-clock()
        if remaining<=0: timed=True; raise TimeoutError('shared role deadline before reap')
        rc=process.wait(timeout=remaining); require(rc==0,'authenticated gh command failed')
    except Exception as exc:
        failure=exc; timed=timed or isinstance(exc,(TimeoutError,subprocess.TimeoutExpired))
    finally:
        stopped.set()
        if process is not None:
            if process.poll() is None:
                if os.name!='nt':
                    try: os.killpg(process.pid,signal.SIGKILL)
                    except ProcessLookupError: pass
                else: process.kill()
            if rc is None:
                try: rc=process.wait(timeout=5)
                except Exception as exc: failure=failure or exc
        for thread in threads: thread.join(timeout=.1)
        if any(thread.is_alive() for thread in threads): failure=failure or TimeoutError('capture reader did not stop after owned child kill/reap')
        if not any(thread.is_alive() for thread in threads):
            for stream in pipes:
                try: stream.close()
                except Exception: pass
    secrets=[os.environ.get(n,'') for n in ('GH_TOKEN','GITHUB_TOKEN')]
    raw={n:redact(b''.join(chunks[n]),secrets) for n in chunks}
    channels={n:{'path':str(parent/(label+'.'+n)),**put(parent/(label+'.'+n),raw[n])} for n in raw}
    row={'label':label,'command':argv,'stdout':channels['stdout'],'stderr':channels['stderr'],'returncode':rc,'elapsed_seconds':clock()-start,'deadline_seconds_remaining':max(0,deadline-clock()),'timed_out':timed,'capped':capped,'complete':failure is None}
    output(parent/(label+'.receipt.json'),row)
    if failure is not None: raise failure
    return raw['stdout'],row


def endpoints(profile):
    repo=profile['repository']; run=integer(profile['run_id']); artifact=integer(profile['artifact_id']); job=integer(profile['job_id'])
    require(type(repo) is str and len(repo.split('/'))==2 and all(x and all(c.isalnum() or c in '-_.' for c in x) for x in repo.split('/')),'closed repository')
    return {'run':f'repos/{repo}/actions/runs/{run}/attempts/1','jobs':f'repos/{repo}/actions/runs/{run}/attempts/1/jobs?filter=all&per_page=100','artifacts':f'repos/{repo}/actions/runs/{run}/artifacts?per_page=100','artifact':f'repos/{repo}/actions/artifacts/{artifact}','joblog':f'repos/{repo}/actions/jobs/{job}/logs','ZIP':f'repos/{repo}/actions/artifacts/{artifact}/zip'}


def api_identity(docs,p):
    require(set(docs)=={'run','jobs','artifacts','artifact'},'all four authenticated metadata documents')
    run,jobs,listing,artifact=(docs[k] for k in ('run','jobs','artifacts','artifact'))
    require(run['id']==p['run_id'] and run['run_attempt']==p['run_attempt']==1 and run['head_sha']==p['source_commit'] and run['workflow_id']==p['workflow_id'] and run['status']=='completed' and run['conclusion']=='success','completed exact run/head/attempt/workflow')
    require(type(jobs['total_count']) is int and jobs['total_count']==len(jobs['jobs'])<=100 and type(listing['total_count']) is int and listing['total_count']==len(listing['artifacts'])<=100,'complete bounded jobs/artifact pages')
    matching=[j for j in jobs['jobs'] if j['id']==p['job_id']]; require(len(matching)==1,'exact unique current job'); job=matching[0]
    require(job['run_id']==p['run_id'] and job['run_attempt']==1 and job['status']=='completed' and job['conclusion']=='success','exact completed job')
    required=p['required_original_steps'] if 'required_original_steps' in p else p['required_steps']
    for row in required:
        candidates=[s for s in job['steps'] if s['name']==(row if type(row) is str else row['name']) and (type(row) is str or s['number']==row['number'])]
        require(len(candidates)==1 and candidates[0]['status']=='completed' and candidates[0]['conclusion']=='success','every required step completed successfully')
    require(artifact['id']==p['artifact_id'] and artifact['name']==p['artifact_name'] and artifact['expired'] is False and artifact['workflow_run']['id']==p['run_id'] and artifact['workflow_run']['head_sha']==p['source_commit'],'exact selected artifact identity')
    if 'ZIP' in p: require(artifact['size_in_bytes']==p['ZIP']['bytes'],'exact accepted artifact ZIP byte count')
    rows=[a for a in listing['artifacts'] if a['id']==p['artifact_id']]; require(len(rows)==1 and all(rows[0][k]==artifact[k] for k in ('id','name','size_in_bytes','expired','workflow_run')),'complete listing/individual agreement')
    return {'run_id':p['run_id'],'job_id':p['job_id'],'artifact_id':p['artifact_id'],'source_commit':p['source_commit']}


def retrieve(profile,parent,current=False,zip_get=True,transport=capture,clock=time.monotonic):
    parent=fresh(parent,True); deadline=clock()+180; rows=[]; docs={}; values={}; ep=endpoints(profile); summary={'passed':False,'rows':rows,'current':current,'ZIP_GET':zip_get,'host':'github.com'}
    try:
        for label in ('run','jobs','artifacts','artifact'):
            raw,row=transport(ep[label],label,parent,deadline,4194304); rows.append(row); docs[label]=parse(raw); values[label]=raw
        summary['identity']=api_identity(docs,profile)
        if current:
            raw,row=transport(ep['joblog'],'joblog',parent,deadline,4194304); rows.append(row); summary['plaintext']=plaintext(raw); values['joblog']=raw
        if zip_get:
            raw,row=transport(ep['ZIP'],'ZIP',parent,deadline,33554432 if current else 16777216); rows.append(row); values['ZIP']=raw
        summary['passed']=True; output(parent/'retrieval.json',summary); return values,summary
    except Exception as exc:
        summary['failed_next_label']=label
        failed=parent/(label+'.receipt.json')
        if failed.exists():
            failed_snap=snapshot(failed,65536); failed_row=parse(failed_snap['raw'])
            if not rows or rows[-1].get('label')!=label: rows.append(failed_row)
            unchanged(failed_snap)
        summary['exception']={'type':type(exc).__name__,'message':redact(str(exc).encode(),[os.environ.get('GH_TOKEN',''),os.environ.get('GITHUB_TOKEN','')]).decode('utf8','replace')}; output(parent/'retrieval.json',summary); raise


def object_binding(raw,control):
    accepted=control['accepted_v68']; expected=accepted['object']; require({'bytes':len(raw),'sha256':sha(raw)}=={k:expected[k] for k in ('bytes','sha256')},'same accepted whole object')
    slices=[]
    for row in accepted['object_debug_slices']:
        start,size=integer(row['offset']),integer(row['size']); require(start+size<=len(raw) and sha(raw[start:start+size])==row['bytes_sha256'],'exact accepted debug slice byte hash without parsing')
        slices.append({'name':row['name'],'offset':start,'bytes':size,'sha256':row['bytes_sha256']})
    return {'object':{'bytes':len(raw),'sha256':sha(raw)},'debug_slices':slices,'ELF_DWARF_parser_calls':0}


def validate_control(value):
    """Schema only: does not evaluate the new relation or any old semantic fact."""
    def text(v): require(type(v) is str and 0<len(v.encode())<=8192,'bounded schema text')
    def boolean(v): require(type(v) is bool,'literal boolean')
    def seq(v,maximum,fn):
        require(type(v) is list and len(v)<=maximum,'bounded schema list')
        for item in v: fn(item)
    def obj(v,schema):
        require(type(v) is dict and set(v)==set(schema),'closed nested schema')
        for key,fn in schema.items(): fn(v[key])
    def fingerprint(v): obj(v,{'bytes':integer,'sha256':digest})
    def member(v): obj(v,{'member':safe_name,'bytes':integer,'sha256':digest})
    def mapping(v):
        require(type(v) is dict and 0<len(v)<=4096,'complete finite member map')
        for name,row in v.items(): safe_name(name); fingerprint(row)
        require(len({n.casefold() for n in v})==len(v),'casefold-distinct member names')
    def step(v):
        obj(v,{'number':integer,'name':text,'status':text,'conclusion':text}); require(v['status']=='completed' and v['conclusion']=='success','accepted required step values')
    def slice_row(v):
        obj(v,{k:(text if k=='name' else digest if k=='bytes_sha256' else integer) for k in ('alignment','bytes_sha256','entsize','flags','index','info','link','name','name_offset','offset','size','type')})
    def anchor(v):
        obj(v,{'CU_header_inherited':lambda x:obj(x,{k:integer for k in ('address_size','debug_abbrev_offset','unit_length','version')}),'CU_offset':integer,'inherited_member_id':text,'inherited_union_id':text,'member_name':text,'member_start_inherited':integer,'role':text,'union_size_inherited':integer})
    def ref(v):
        obj(v,{'form':text,'value':integer,'raw_value':integer,'target':text}); require(v['form']=='DW_FORM_ref4' and v['value']==v['raw_value']<2**32,'closed raw reference values')
    def attribute(v):
        keys(v,'form value raw_value'); text(v['form']); integer(v['raw_value'])
        if v['form']=='DW_FORM_strp':
            obj(v['value'],{'bytes_hex':text}); token=v['value']['bytes_hex']; require(len(token)%2==0 and all(c in '0123456789abcdef' for c in token),'canonical hex bytes')
        else: require(v['form']=='DW_FORM_data1' and integer(v['value'])==v['raw_value']<256,'closed reported numeric value')
    def node(v):
        keys(v,'id role tag attributes type_reference complete entry_basis independent_lexical_DIE_boundary_proven')
        for k in ('id','role','tag'): text(v[k])
        require(v['role'] in ('provider','core') and v['complete'] is True and v['independent_lexical_DIE_boundary_proven'] is False,'raw complete and reference-limit values')
        seq(v['entry_basis'],1,text); require(len(v['entry_basis'])==1 and v['entry_basis'][0] in ('parser_sequential_direct_child','parser_interpreted_in_CU_reference'),'observation entry basis')
        allowed={'DW_TAG_member':{'DW_AT_name','DW_AT_data_member_location'},'DW_TAG_structure_type':{'DW_AT_name','DW_AT_byte_size'},'DW_TAG_pointer_type':set()}
        require(v['tag'] in allowed and type(v['attributes']) is dict and set(v['attributes'])==allowed[v['tag']],'only observed attributes; no pointer width/alignment')
        for a in v['attributes'].values(): attribute(a)
        if v['tag']=='DW_TAG_structure_type': require(v['type_reference'] is None,'structure reference absent')
        else: ref(v['type_reference'])
    def edge(v): obj(v,{k:text for k in ('role','parent','child')})
    def inherited(v): obj(v,{k:text for k in ('pair_id','provider','core','accepted_RESULT_sha256','accepted_comparison_JSON_pointer','accepted_comparison_canonical_sha256','meaning')}); digest(v['accepted_RESULT_sha256']); digest(v['accepted_comparison_canonical_sha256'])
    def inherited_context(v): obj(v,{k:text for k in ('role','parent','target','context','pair_id')}); require(v['context']=='type_inherited_stop','finite inherited context')
    def pointer_context(v): obj(v,{'id':text,'role':text,'raw_type_reference':ref,'boundary':text})
    def opaque(v): obj(v,{'allowed_contexts':lambda x:seq(x,2,text),'comparison':text,'provider':text,'core':text}); require(set(v['allowed_contexts'])=={'by_value_member_storage_metadata','pointer_target_label_metadata'},'prior opaque contexts only')
    def premises(v):
        obj(v,{'member_pair':lambda x:obj(x,{'provider':text,'core':text,'reported_member_start':integer,'source':text}),'union_pair':lambda x:obj(x,{'provider':text,'core':text,'reported_byte_size':integer,'accepted_control_sha256':digest,'accepted_opaque_pair':opaque,'claim':text})})
    def counts(v): obj(v,{k:integer for k in ('new_nodes_total','new_nodes_per_role','new_member_nodes_total','new_structure_nodes_total','new_pointer_nodes_total','direct_union_members_each_role','new_direct_child_edges_total','inherited_contexts_total','pointer_contexts_total','unsupported_or_unresolved','new_alignment_attributes_reported','old210_intersection')})
    def profile(v): obj(v,{'anchors':lambda x:obj(x,{'provider':anchor,'core':anchor}),'new_nodes':lambda x:seq(x,512,node),'direct_child_edges':lambda x:seq(x,2048,edge),'inherited_boundary_pairs':lambda x:seq(x,1,inherited),'inherited_contexts':lambda x:seq(x,512,inherited_context),'pointer_contexts':lambda x:seq(x,512,pointer_context),'anchor_premises':premises,'accepted_raw_counts':counts})
    def accepted(v):
        obj(v,{'repository':text,'run_id':integer,'run_attempt':integer,'source_commit':text,'workflow_id':integer,'job_id':integer,'artifact_id':integer,'artifact_name':text,'ZIP':fingerprint,'private_RESULT':fingerprint,'private_review':fingerprint,'accepted_collector_sha256':digest,'namespace':safe_name,'complete_member_map':mapping,'producer_result':member,'source_manifest':member,'control':member,'object':lambda x:obj(x,{'bytes':integer,'member':safe_name,'sha256':digest,'original_v67_member_label':safe_name}),'object_debug_slices':lambda x:seq(x,4,slice_row),'job_name':text,'required_original_steps':lambda x:seq(x,100,step),'prior_joblog_policy':text})
        require(v['run_attempt']==1 and len(v['source_commit'])==40 and all(c in '0123456789abcdef' for c in v['source_commit']),'accepted attempt/source tuple')
        for name in ('producer_result','source_manifest','control','object'):
            row=v[name]; require(v['complete_member_map'].get(row['member'])=={k:row[k] for k in ('bytes','sha256')},'exact accepted complete member binding')
        require(len(v['object_debug_slices'])==4,'four accepted slice labels')
    def basis(v):
        obj(v,{'query_result':fingerprint,'query_review_sha256':digest,'query_close_sha256':digest,'query_source':fingerprint,'query_checkpoint_sha256':digest,'query_pins_sha256':digest,'input_profile_sha256':digest,'parser_package_manifest_sha256':digest,'query_invocations_consumed':integer,'independent_lexical_DIE_boundary_proven':boolean,'reference_resolution_basis':text})
        require(v['query_invocations_consumed']==1 and v['independent_lexical_DIE_boundary_proven'] is False,'consumed query and explicit boundary limit')
    def policy(v):
        names='level member_match new_tag_allowlist attribute_forms raw_reference_forms attributes_absence reference_check pairing pointer_stop inherited_stop closure result'.split(); require(type(v) is dict and set(v)==set(names),'closed relation policy')
        for k in set(names)-{'new_tag_allowlist','attribute_forms','raw_reference_forms'}: text(v[k])
        seq(v['new_tag_allowlist'],3,text); require(set(v['new_tag_allowlist'])=={'DW_TAG_member','DW_TAG_structure_type','DW_TAG_pointer_type'},'observed tag policy')
        obj(v['attribute_forms'],{'DW_AT_name':lambda x:seq(x,1,text),'DW_AT_data_member_location':lambda x:seq(x,1,text),'DW_AT_byte_size':lambda x:seq(x,1,text)})
        require(v['attribute_forms']=={'DW_AT_name':['DW_FORM_strp'],'DW_AT_data_member_location':['DW_FORM_data1'],'DW_AT_byte_size':['DW_FORM_data1']} and v['raw_reference_forms']==['DW_FORM_ref4'],'observed form policy')
    maxima={'control_bytes':262144,'object_bytes':16777216,'old_ZIP_bytes':16777216,'old_expanded_bytes':67108864,'old_members':4096,'new_nodes':512,'new_edges':2048,'relation_depth':32,'metadata_JSON_bytes':4194304,'current_ZIP_bytes':33554432,'current_expanded_bytes':100663296,'current_members':4096,'API_JSON_bytes':4194304,'plaintext_joblog_bytes':4194304,'stderr_bytes':1048576,'capture_role_total_seconds':180,'kill_reap_grace_seconds':5,'result_bytes':8388608}
    def limits(v):
        require(type(v) is dict and set(v)==set(maxima),'closed caps')
        for k in v: require(0<integer(v[k])<=maxima[k],'fixed upper cap')
    obj(value,{'schema':text,'accepted_v68':accepted,'new_observation_basis':basis,'finite_profile':profile,'relation_policy':policy,'caps':limits,'nonclaims':lambda x:seq(x,32,text)})
    require(value['schema']=='v69-finite-parser-observed-cra-u-body-control-v1','control schema version')
    return {'schema_checked':True,'relation_executed':False,'query_parser_old_proof_calls':0}


def source_manifest(value,files,context=None):
    keys(value,'schema context files bootstrap'); require(value['schema']=='v69-public-source-manifest-v1' and value['files']==files and set(files)==set(PUBLIC),'exact public7 source manifest')
    ctx=value['context']; keys(ctx,'server_url repository event_name run_id run_attempt source_commit workflow_commit workflow_path')
    require(ctx['server_url']=='https://github.com' and ctx['repository']=='eirblue/ios_note10p' and ctx['event_name']=='workflow_dispatch' and type(ctx['run_attempt']) is int and ctx['run_attempt']==1 and integer(ctx['run_id'])>0 and ctx['workflow_path']==PUBLIC[-1],'trusted source context')
    require(type(ctx['source_commit']) is str and len(ctx['source_commit'])==40 and all(c in '0123456789abcdef' for c in ctx['source_commit']) and ctx['workflow_commit']==ctx['source_commit'],'workflow/source commit equality')
    if context is not None:
        require(all(ctx[k]==v for k,v in context.items() if k in ctx),'source context agrees with actual current tuple')
    boot=value['bootstrap']; keys(boot,'status git_read_command_count shared_deadline_seconds elapsed_seconds commands failed_next_index exception')
    require(boot['status']=='complete' and type(boot['git_read_command_count']) is int and boot['git_read_command_count']==8 and boot['shared_deadline_seconds']==60 and type(boot['shared_deadline_seconds']) is int and type(boot['elapsed_seconds']) in (int,float) and 0<=boot['elapsed_seconds']<=60 and boot['failed_next_index'] is None and boot['exception'] is None and type(boot['commands']) is list and len(boot['commands'])==8,'complete bounded8 command bootstrap, not flag alone')
    workspace=None
    for index,row in enumerate(boot['commands']):
        keys(row,'index argv returncode stdout stderr elapsed_seconds timed_out capped complete')
        argv=row['argv']; require(type(argv) is list and all(type(v) is str for v in argv) and len(argv)>=3 and argv[:2]==['git','-C'],'literal readonly local Git command')
        current=argv[2]; require(PurePosixPath(current).is_absolute() and '..' not in current.split('/'),'canonical CI POSIX workspace')
        if workspace is None: workspace=current
        require(current==workspace and type(row['index']) is int and row['index']==index and type(row['returncode']) is int and row['returncode']==0 and row['complete'] is True and row['timed_out'] is False and row['capped'] is False and type(row['elapsed_seconds']) in (int,float) and 0<=row['elapsed_seconds']<=60,'exact successful source command metadata')
        keys(row['stdout'],'bytes sha256'); integer(row['stdout']['bytes'],1048576); digest(row['stdout']['sha256'])
        keys(row['stderr'],'bytes sha256 redacted_utf8'); integer(row['stderr']['bytes'],262144); digest(row['stderr']['sha256']); require(type(row['stderr']['redacted_utf8']) is str,'redacted source stderr')
        retained=row['stderr']['redacted_utf8'].encode(); require(len(retained)==row['stderr']['bytes'] and sha(retained)==row['stderr']['sha256'],'exact retained source stderr digest')
        expected=['git','-C',workspace,'rev-parse','--verify','HEAD'] if index==0 else ['git','-C',workspace,'cat-file','blob',ctx['source_commit']+':'+PUBLIC[index-1]]
        expected_out={'bytes':41,'sha256':sha(ctx['source_commit'].encode()+b'\n')} if index==0 else files[PUBLIC[index-1]]
        require(argv==expected and row['stdout']==expected_out,'source blob/HEAD stdout matches retained7 files')
    return ctx
