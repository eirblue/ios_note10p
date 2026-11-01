"""New bounded provenance/serialization contract for reported layout metadata."""
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import subprocess
import threading
import time
import zipfile

CAP=64*1024*1024
CONTROL=Path(__file__).with_name('paired_layout_relation_control.json')
PUBLIC=('note10/device_test/build_paired_layout_relation.py','note10/device_test/paired_layout_relation.py','note10/device_test/paired_layout_input_contract.py','note10/device_test/stage_paired_layout_relation.py','note10/device_test/test_paired_layout_relation.py','.github/workflows/note10-paired-layout-relation.yml','note10/device_test/paired_layout_relation_control.json')
STEPS=('Checkout exact source','Prove reported paired metadata relation','Stage complete layout evidence','Upload complete layout evidence')
ORIGINAL_STEPS=('Checkout exact source','Provision GNU linker','Produce one pair link','Stage complete evidence','Upload complete evidence')

def require(ok, message):
    if not ok:
        raise ValueError(message)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def keys(value, names):
    require(type(value) is dict and set(value) == set(names.split()), 'closed object keys: ' + names)


def integer(value, minimum=0, maximum=CAP):
    require(type(value) is int and minimum <= value <= maximum, 'bounded integer')


def hexsha(value):
    require(type(value) is str and re.fullmatch('[0-9a-f]{64}', value) is not None, 'lowercase SHA256')


def member(name):
    require(type(name) is str and name and '\\' not in name and ':' not in name and '\x00' not in name, 'safe member spelling')
    require(len(name.encode('utf8'))<=512 and len(name.split('/'))<=32,'bounded namespace name/depth')
    p = PurePosixPath(name)
    require(not p.is_absolute() and all(x not in ('', '.', '..') for x in name.split('/')) and str(p) == name, 'canonical relative member')
    return name


def identity(st):
    result = (st.st_dev, st.st_ino, st.st_nlink, st.st_size, st.st_mtime_ns, st.st_ctime_ns)
    require(all(type(x) is int for x in result), 'integer identity fields')
    if os.name == 'nt':
        birth = getattr(st, 'st_birthtime_ns', None)
        require(type(birth) is int, 'Windows integer birthtime profile')
        result += (birth,)
    return result


def compatible(a, b):
    require(a[:5] == b[:5], 'cross-API compatible file identity')
    require(a[6:] == b[6:] if os.name == 'nt' else a[5:] == b[5:], 'cross-API birthtime or POSIX ctime')


def ordinary(path):
    path = Path(path).absolute()
    for parent in reversed(path.parents):
        st = parent.lstat()
        require(stat.S_ISDIR(st.st_mode) and not stat.S_ISLNK(st.st_mode) and not getattr(st, 'st_file_attributes', 0) & 1024 and not parent.is_symlink(), 'ordinary ancestor')
    st = path.lstat()
    require(stat.S_ISREG(st.st_mode) and not stat.S_ISLNK(st.st_mode) and st.st_nlink == 1 and not getattr(st, 'st_file_attributes', 0) & 1024 and not path.is_symlink(), 'ordinary nonlink file')
    return st


def parent_identities(path):
    records=[]
    for parent in Path(path).absolute().parents:
        st=parent.lstat()
        require(stat.S_ISDIR(st.st_mode) and not stat.S_ISLNK(st.st_mode) and not parent.is_symlink() and not getattr(st,'st_file_attributes',0)&1024,'ordinary output ancestor')
        records.append((parent,st.st_dev,st.st_ino))
    return records


def snapshot(path, cap, expected=None):
    path = Path(path).absolute()
    before = identity(ordinary(path))
    require(before[3] <= cap, 'file stat cap before read')
    with path.open('rb') as stream:
        fd = identity(os.fstat(stream.fileno()))
        compatible(before, fd)
        raw = stream.read(cap + 1)
        after_fd = identity(os.fstat(stream.fileno()))
    after = identity(ordinary(path))
    require(before == after and fd == after_fd and len(raw) == before[3] <= cap, 'stable complete bounded snapshot')
    record = {'bytes': len(raw), 'sha256': digest(raw)}
    if expected is not None:
        require(record == expected, 'exact snapshot bytes/SHA')
    return {'path': path, 'identity': before, 'raw': raw, **record}


def unchanged(snap):
    require(identity(ordinary(snap['path'])) == snap['identity'], 'snapshot identity stable through use')


def write_bytes(path, raw):
    require(type(raw) is bytes and len(raw) <= CAP, 'bounded output bytes')
    path = Path(path)
    parents=parent_identities(path)
    with path.open('xb') as stream:
        stream.write(raw)
    require(parent_identities(path)==parents,'same output ancestor ownership')
    return snapshot(path, len(raw), {'bytes': len(raw), 'sha256': digest(raw)})


def json_bytes(value):
    return (json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False, allow_nan=False) + '\n').encode()


def write_json(path, value):
    return write_bytes(path, json_bytes(value))


def parse_json(raw):
    require(type(raw) is bytes and len(raw) <= 8 * 1024 * 1024, 'bounded JSON')
    def pairs(rows):
        out = {}
        for k, v in rows:
            require(k not in out, 'no duplicate JSON key')
            out[k] = v
        return out
    def invalid(value):
        raise ValueError('nonfinite JSON: ' + value)
    return json.loads(raw.decode('utf8'), object_pairs_hook=pairs, parse_constant=invalid)


def file_row(row):
    keys(row, 'bytes sha256'); integer(row['bytes']); hexsha(row['sha256'])


def inventory(root):
    root=Path(root); out={}; total=0; nodes=0
    for path in root.rglob('*'):
        nodes+=1; require(nodes<=8192,'bounded file/directory namespace scan')
        st=path.lstat(); require(not stat.S_ISLNK(st.st_mode) and not getattr(st,'st_file_attributes',0)&1024, 'safe inventory node')
        if stat.S_ISDIR(st.st_mode): continue
        rel=member(path.relative_to(root).as_posix()); snap=snapshot(path,CAP); total+=snap['bytes']
        require(total<=CAP and len(out)<4096, 'complete inventory aggregate cap'); out[rel]={k:snap[k] for k in ('bytes','sha256')}
    return out


def zip_snapshot(raw, expected=None):
    require(type(raw) is bytes and len(raw)<=16*1024*1024, 'bounded whole ZIP')
    files={}; buffers={}; total=0; folded=set()
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        rows=archive.infolist(); require(len(rows)<=4096, 'ZIP member cap')
        for row in rows:
            require(not row.is_dir() and not row.flag_bits&1 and row.compress_type in (0,8), 'ordinary unencrypted ZIP member')
            name=member(row.filename); mode=row.external_attr>>16
            require(name.casefold() not in folded and (stat.S_IFMT(mode) in (0,stat.S_IFREG)) and row.file_size<=CAP, 'unique regular ZIP member')
            folded.add(name.casefold()); total+=row.file_size; require(total<=CAP, 'ZIP expanded cap')
            with archive.open(row) as stream: data=stream.read(row.file_size+1)
            require(len(data)==row.file_size, 'complete bounded ZIP member'); buffers[name]=data; files[name]={'bytes':len(data),'sha256':digest(data)}
    if expected is not None: require(files==expected, 'same complete original ZIP namespace')
    require(not any('/'.join(name.split('/')[:i]) in files for name in files for i in range(1,len(name.split('/')))), 'no ZIP file/directory prefix shadow')
    return files,buffers


def redact(raw, token):
    if not token: return raw
    secret=token.encode(); raw=raw.replace(secret,b'[REDACTED]')
    for n in range(len(secret)-1,0,-1):
        if raw.endswith(secret[:n]): return raw[:-n]+b'[REDACTED-PREFIX]'
    return raw


def capture(argv, cwd, directory, label, limit, timeout, env=None, deadline=None):
    """Pipes drained concurrently; wall timeout interrupts a blocked child read."""
    require(type(argv) is list and all(type(x) is str for x in argv), 'literal argv, no shell')
    require(type(label) is str and re.fullmatch('[A-Za-z][A-Za-z0-9_-]*',label) is not None,'exclusive fixed capture filenames')
    now=time.monotonic(); require(type(timeout) in (int,float) and timeout>0,'positive remaining capture budget')
    deadline=now+timeout if deadline is None else min(now+timeout,deadline)
    require(deadline>now,'shared role deadline before process creation')
    directory=Path(directory); start=time.time_ns(); buffers=[bytearray(),bytearray()]; errors=[]
    process=subprocess.Popen(argv,cwd=cwd,env=env,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    def drain(stream, index):
        try:
            while True:
                chunk=stream.read(65536)
                if not chunk: break
                room=limit+1-len(buffers[index]); buffers[index].extend(chunk[:max(room,0)])
                if len(buffers[index])>limit:
                    errors.append('stream cap'); break
        except Exception as exc: errors.append(type(exc).__name__+': '+str(exc))
    threads=[threading.Thread(target=drain,args=(stream,i),daemon=True) for i,stream in enumerate((process.stdout,process.stderr))]
    for thread in threads: thread.start()
    failure=None
    while process.poll() is None or any(t.is_alive() for t in threads):
        if errors or time.monotonic()>=deadline:
            failure='stream cap/read failure' if errors else 'total timeout'; break
        time.sleep(.01)
    if failure:
        if process.poll() is None: process.kill()
        process.wait(timeout=10)
    else: process.wait(timeout=10)
    for stream in (process.stdout,process.stderr): stream.close()
    for thread in threads: thread.join(timeout=2)
    token=(env or os.environ).get('GH_TOKEN',''); outputs=[]
    for suffix,buf in zip(('stdout','stderr'),buffers):
        raw=redact(bytes(buf),token); path=directory/(label+'.'+suffix)
        snap=write_bytes(path,raw); outputs.append({k:snap[k] for k in ('bytes','sha256')})
    row={'label':label,'argv':argv,'returncode':process.returncode,'started_ns':start,'ended_ns':time.time_ns(),'stdout':outputs[0],'stderr':outputs[1],'failure':failure,'reaped':process.poll() is not None}
    write_json(directory/(label+'.receipt.json'),row)
    require(not failure and not errors and not any(t.is_alive() for t in threads) and process.returncode==0,'command failed; bounded partial evidence retained')
    require(bytes(buffers[0])==redact(bytes(buffers[0]),token),'secret-bearing command stdout rejected')
    return bytes(buffers[0]),row


def exception_record(exc):
    return {'type':type(exc).__name__,'message':str(exc)}


ATTRS={
 'DW_TAG_structure_type':['DW_AT_name','DW_AT_byte_size','DW_AT_alignment'],
 'DW_TAG_union_type':['DW_AT_name','DW_AT_byte_size','DW_AT_alignment'],
 'DW_TAG_base_type':['DW_AT_name','DW_AT_byte_size','DW_AT_encoding'],
 'DW_TAG_typedef':['DW_AT_name'],'DW_TAG_const_type':[],'DW_TAG_pointer_type':[],
 'DW_TAG_array_type':[],'DW_TAG_subrange_type':['DW_AT_count'],
 'DW_TAG_member':['DW_AT_name','DW_AT_data_member_location','DW_AT_alignment'],
 'DW_TAG_formal_parameter':[],'DW_TAG_subroutine_type':['DW_AT_prototyped'],
 'DW_TAG_subprogram':['DW_AT_name','DW_AT_prototyped','DW_AT_declaration','DW_AT_external']}
FORMS={'DW_AT_name':['DW_FORM_strp'],'DW_AT_byte_size':['DW_FORM_data1','DW_FORM_data2'],'DW_AT_alignment':['DW_FORM_udata'],'DW_AT_count':['DW_FORM_data1'],'DW_AT_data_member_location':['DW_FORM_data1','DW_FORM_data2'],'DW_AT_encoding':['DW_FORM_data1'],'DW_AT_prototyped':['DW_FORM_flag_present'],'DW_AT_declaration':['DW_FORM_flag_present'],'DW_AT_external':['DW_FORM_flag_present'],'DW_AT_type':['DW_FORM_ref4']}
CHILDREN={'DW_TAG_structure_type':['DW_TAG_member'],'DW_TAG_union_type':[],'DW_TAG_subprogram':['DW_TAG_formal_parameter'],'DW_TAG_subroutine_type':['DW_TAG_formal_parameter'],'DW_TAG_array_type':['DW_TAG_subrange_type']}
CAPS={'API_stderr':8388608,'API_stdout':8388608,'API_total_seconds':180,'artifact_expanded':67108864,'artifact_members':4096,'control_JSON':8388608,'current_artifact_ZIP':16777216,'graph_depth':64,'members_per_structure':512,'node_pairs':4096,'nodes':1024,'object':16777216,'original_ZIP':16777216,'raw_name_bytes':4096,'type_chain':32}
NONCLAIMS=('whole_binary_ABI_proven','transitive_opaque_layout_equivalence_proven','pointed_to_layouts_proven','shash_alg_alignment_measured','pointer_byte_size_measured','complete_member_storage_extents_measured','machine_code_DIE_ownership_proven','calling_convention_or_runtime_arguments_proven','compiler_or_linker_replayed','query_or_old_proof_replayed','provider_runtime_available','registration_callbacks_or_allocation_executed','unresolved_services_available','whole_toolchain_identity_proven','Image_BOOT_XNU_iOS_readiness','device_authorized','physical_BOOT_reboot')


def text(value): require(type(value) is str and 0<len(value.encode('utf8'))<=4096,'bounded text')


def node_id(value):
    require(type(value) is str and re.fullmatch('[0-9]{1,8}:[0-9]{1,8}',value) is not None,'qualified raw node ID')
    for part in value.split(':'): integer(int(part),0,16777216)


def attribute(name,row):
    keys(row,'form value'); require(name in FORMS and row['form'] in FORMS[name],'approved attribute/form')
    value=row['value']
    if name=='DW_AT_name':
        keys(value,'bytes_hex'); encoded=value['bytes_hex']; require(type(encoded) is str and len(encoded)<=8192 and len(encoded)%2==0 and re.fullmatch('[0-9a-f]*',encoded) is not None,'bounded canonical raw name bytes')
        decoded=bytes.fromhex(encoded).decode('utf8'); require(re.fullmatch('[A-Za-z_][A-Za-z0-9_ ]*',decoded) is not None,'reported identifier/base-type name, no path')
    elif name in ('DW_AT_prototyped','DW_AT_declaration','DW_AT_external'):
        require(value is True,'literal present flag')
    else:
        integer(value)
        if name in ('DW_AT_byte_size','DW_AT_alignment'): require(value>0,'positive reported size/alignment')
        if name=='DW_AT_alignment': require(value&(value-1)==0,'reported alignment power of two')


def profile_schema(profile):
    keys(profile,'selected_CUs candidates nodes opaque_pair_allowlist object_debug_slices recorded_counts')
    require(type(profile['selected_CUs']) is list and len(profile['selected_CUs'])==2,'two role CU records')
    for cu in profile['selected_CUs']:
        keys(cu,'role CU_offset source_label DWARF_version address_size label_attribution'); require(cu['role'] in ('provider','core'),'CU role'); integer(cu['CU_offset'],0,16777216)
        require(type(cu['DWARF_version']) is int and cu['DWARF_version']==4 and type(cu['address_size']) is int and cu['address_size']==8,'one reported CU encoding profile')
        require(cu['source_label']==('crypto/sha256_generic.c' if cu['role']=='provider' else 'crypto/shash.c'),'reviewed normalized source label'); text(cu['label_attribution'])
    require(type(profile['candidates']) is list and len(profile['candidates'])<=128,'bounded candidate records')
    for c in profile['candidates']:
        keys(c,'role target node tag'); require(c['role'] in ('provider','core') and c['target'] in ('shash_alg','crypto_alg','crypto_register_shashes') and c['tag'] in ('DW_TAG_structure_type','DW_TAG_subprogram'),'intended candidate metadata'); node_id(c['node'])
    require(type(profile['nodes']) is list and 0<len(profile['nodes'])<=1024,'bounded raw finite graph')
    for n in profile['nodes']:
        keys(n,'id role tag attributes references children opaque'); node_id(n['id']); require(n['role'] in ('provider','core') and n['tag'] in ATTRS and type(n['opaque']) is bool,'typed graph role/tag/boundary')
        require(type(n['attributes']) is dict and set(n['attributes'])<=set(ATTRS[n['tag']]),'closed per-tag relation attributes')
        for name,row in n['attributes'].items(): attribute(name,row)
        require(type(n['references']) is dict and set(n['references'])<={'DW_AT_type'},'one approved reference kind')
        for name,ref in n['references'].items(): keys(ref,'form target'); require(ref['form']=='DW_FORM_ref4','one observed reference form'); node_id(ref['target'])
        require(type(n['children']) is list and len(n['children'])<=512,'bounded ordered selected children')
        for child in n['children']: node_id(child)
        if n['opaque']: require(n['tag'] in ('DW_TAG_structure_type','DW_TAG_union_type') and not n['children'],'opaque aggregates have no invented children')
    require(type(profile['opaque_pair_allowlist']) is list and len(profile['opaque_pair_allowlist'])<=512,'bounded opaque stops')
    for pair in profile['opaque_pair_allowlist']:
        keys(pair,'provider core comparison allowed_contexts'); node_id(pair['provider']); node_id(pair['core']); text(pair['comparison'])
        require(pair['allowed_contexts']==['by_value_member_storage_metadata','pointer_target_label_metadata'],'finite opaque stop contexts only')
    require(type(profile['object_debug_slices']) is list and len(profile['object_debug_slices'])==4,'four raw source slices')
    for s in profile['object_debug_slices']:
        keys(s,'alignment bytes_sha256 entsize flags index info link name name_offset offset size type'); hexsha(s['bytes_sha256'])
        require(s['name'] in ('.debug_info','.rela.debug_info','.debug_abbrev','.debug_str'),'only selected raw debug slices')
        for name,value in s.items():
            if name not in ('name','bytes_sha256'): integer(value,0,16777216)
    keys(profile['recorded_counts'],'nodes expanded_aggregates opaque_aggregates candidates direct_members pointer_records')
    for value in profile['recorded_counts'].values(): integer(value,0,4096)
    return profile


def validate_control(c):
    keys(c,'schema accepted_v67 measurement_attribution finite_profile relation_policy caps nonclaims'); require(c['schema']=='paired-layout-relation-control-v1','one control schema')
    a=c['accepted_v67']; keys(a,'profile repository source_commit run_id run_attempt workflow_id job_id artifact_id artifact_name ZIP complete_member_map object producer_result accepted_private_result_sha256 accepted_reader_sha256 accepted_review_sha256 accepted_collector_sha256 required_original_steps')
    require(a['profile']=='accepted-v67-paired-object-whole-ZIP-v1' and a['artifact_name']=='note10-provider-core-pair-pc-only' and type(a['run_attempt']) is int and a['run_attempt']==1,'one accepted source role')
    require(type(a['source_commit']) is str and re.fullmatch('[0-9a-f]{40}',a['source_commit']) is not None and type(a['repository']) is str and re.fullmatch('[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+',a['repository']) is not None,'exact original source/repository')
    for name in ('run_id','workflow_id','job_id','artifact_id'): integer(a[name],1,1<<63)
    keys(a['ZIP'],'bytes sha256 namespace ordinary_members ordinary_expanded_bytes'); file_row({k:a['ZIP'][k] for k in ('bytes','sha256')}); require(a['ZIP']['namespace']=='v67-ci-pair','original namespace'); integer(a['ZIP']['ordinary_members'],1,4096); integer(a['ZIP']['ordinary_expanded_bytes'])
    rows=a['complete_member_map']; require(type(rows) is dict and 0<len(rows)<=4096,'complete original namespace map')
    for name,row in rows.items(): member(name); require(name.startswith(a['ZIP']['namespace']+'/'),'original member root'); file_row(row)
    require(len(rows)==a['ZIP']['ordinary_members'] and sum(x['bytes'] for x in rows.values())==a['ZIP']['ordinary_expanded_bytes'],'complete namespace aggregate')
    for name in ('object','producer_result'):
        record=a[name]; keys(record,'bytes member sha256'); member(record['member']); file_row({k:record[k] for k in ('bytes','sha256')}); require(rows.get(record['member'])=={k:record[k] for k in ('bytes','sha256')},'selected original member bound to full map')
    for name in ('accepted_private_result_sha256','accepted_reader_sha256','accepted_review_sha256','accepted_collector_sha256'): hexsha(a[name])
    require(a['required_original_steps']==list(ORIGINAL_STEPS),'exact original successful steps')
    m=c['measurement_attribution']; keys(m,'raw_query_result_sha256 raw_query_checkpoint_sha256 raw_query_sources raw_query_review_sha256 opaque_boundary_addendum_sha256 scope')
    for name,value in m.items():
        if name.endswith('sha256'): hexsha(value)
    keys(m['raw_query_sources'],'query loader')
    for row in m['raw_query_sources'].values(): file_row(row)
    text(m['scope']); profile_schema(c['finite_profile'])
    policy=c['relation_policy']; keys(policy,'arrays attribute_allowlist_by_tag attribute_form_allowlist base_binding complete_candidate_rule declaration_role expanded_targets graph_safety opaque_scope pointer_scope prototypes recorded_count_markers reference_allowlist registration_formal_count registration_name selected_children_by_tag top_structures typedef_const_scope')
    require(policy['attribute_allowlist_by_tag']==ATTRS and policy['attribute_form_allowlist']==FORMS and policy['selected_children_by_tag']==CHILDREN and policy['reference_allowlist']==['DW_AT_type'] and policy['expanded_targets']==['shash_alg','crypto_alg'] and policy['registration_name']=='crypto_register_shashes' and type(policy['registration_formal_count']) is int and policy['registration_formal_count']==2,'closed relation language')
    structured={'attribute_allowlist_by_tag','attribute_form_allowlist','selected_children_by_tag','reference_allowlist','expanded_targets','registration_name','registration_formal_count'}
    for key in set(policy)-structured: text(policy[key])
    require(c['caps']==CAPS,'fixed resource caps')
    for value in c['caps'].values(): integer(value)
    require(type(c['nonclaims']) is dict and set(c['nonclaims'])==set(NONCLAIMS),'closed nonclaims')
    for key,value in c['nonclaims'].items(): require((type(value) is int and value==0) if key=='physical_BOOT_reboot' else value is False,'literal nonclaim, no inferred ABI/runtime/layout claim')
    return c


def load_control(expected_sha):
    hexsha(expected_sha); snap=snapshot(CONTROL,8*1024*1024); require(snap['sha256']==expected_sha,'exact fixed control source SHA')
    control=validate_control(parse_json(snap['raw'])); unchanged(snap); return control,snap


def source_closure(root):
    return {name:{k:snap[k] for k in ('bytes','sha256')} for name in PUBLIC for snap in [snapshot(Path(root)/name,8*1024*1024)]}


def plaintext_log(raw):
    require(type(raw) is bytes and 0<len(raw)<=8*1024*1024,'mandatory bounded current plaintext job log')
    text=raw.decode('utf-8-sig',errors='strict'); display=re.sub(r'\x1b\[[0-9;]*m','',text)
    require(display.strip() and all(ch.isprintable() or ch in '\r\n\t' for ch in display) and not display.lstrip().startswith(('{','[','"')),'UTF8 plaintext, no binary/JSON/control payload')
    try: json.loads(display)
    except (ValueError,TypeError): return
    raise ValueError('JSON value is not a job log')


def api_identity(documents,role,required_steps,job_name=None):
    keys(documents,'run jobs artifacts artifact'); run=documents['run']
    require(run['id']==role['run_id'] and type(run['run_attempt']) is int and run['run_attempt']==role['run_attempt']==1 and run['head_sha']==role['source_commit'] and run['repository']['full_name']==role['repository'] and run['workflow_id']==role['workflow_id'] and run['status']=='completed' and run['conclusion']=='success','authenticated exact completed source run')
    jobs=documents['jobs']; require(type(jobs['total_count']) is int and jobs['total_count']==len(jobs['jobs'])<=100,'complete jobs/steps page')
    found=[j for j in jobs['jobs'] if j['id']==role['job_id']]; require(len(found)==1,'exact authenticated job'); job=found[0]
    require(job['status']=='completed' and job['conclusion']=='success' and (job_name is None or job['name']==job_name),'required successful job role')
    for name in required_steps:
        rows=[s for s in job['steps'] if s['name']==name]; require(len(rows)==1 and rows[0]['status']=='completed' and rows[0]['conclusion']=='success','exact required successful step '+name)
    listing=documents['artifacts']; require(type(listing['total_count']) is int and listing['total_count']==len(listing['artifacts'])<=100,'complete artifact listing')
    matches=[a for a in listing['artifacts'] if a['id']==role['artifact_id']]; require(len(matches)==1 and matches[0]==documents['artifact'],'same individual/listed artifact')
    artifact=matches[0]; require(artifact['name']==role['artifact_name'] and artifact['expired'] is False and artifact['size_in_bytes']==role['ZIP']['bytes'] and artifact['workflow_run']['id']==role['run_id'] and artifact['workflow_run']['head_sha']==role['source_commit'],'artifact source/size identity')


def endpoints(role,current=False):
    p='repos/'+role['repository']+'/actions/'; result={'run':p+'runs/'+str(role['run_id'])+'/attempts/1','jobs':p+'runs/'+str(role['run_id'])+'/attempts/1/jobs?filter=all&per_page=100','artifacts':p+'runs/'+str(role['run_id'])+'/artifacts?per_page=100','artifact':p+'artifacts/'+str(role['artifact_id'])}
    if current: result['joblog']=p+'jobs/'+str(role['job_id'])+'/logs'
    return result


def retrieve(role,directory,current=False):
    deadline=time.monotonic()+CAPS['API_total_seconds']
    directory=Path(directory); directory.mkdir(); documents={}; receipts=[]; targets=endpoints(role,current)
    def take(label,endpoint,limit):
        remaining=deadline-time.monotonic(); require(remaining>0,'role API total deadline exceeded before capture')
        raw,row=capture(['gh','api','--hostname','github.com',endpoint],None,directory,label,limit,remaining,deadline=deadline)
        require(time.monotonic()<=deadline,'role API total deadline exceeded after capture'); receipts.append(row); return raw
    for label in ('run','jobs','artifacts','artifact'):
        documents[label]=parse_json(take(label,targets[label],8*1024*1024))
    require(time.monotonic()<=deadline,'role API total deadline exceeded before metadata authentication')
    api_identity(documents,role,STEPS if current else ORIGINAL_STEPS,'paired-layout-relation' if current else None)
    if current: plaintext_log(take('joblog',targets['joblog'],8*1024*1024))
    endpoint='repos/'+role['repository']+'/actions/artifacts/'+str(role['artifact_id'])+'/zip'
    raw=take('ZIP',endpoint,16*1024*1024)
    require({'bytes':len(raw),'sha256':digest(raw)}=={k:role['ZIP'][k] for k in ('bytes','sha256')},'complete authenticated ZIP')
    require(time.monotonic()<=deadline,'role API total deadline exceeded before completion')
    return raw,{'schema':'layout-retrieval-v1','endpoints':targets,'receipts':receipts}


def verify_retrieval(role,receipt,buffers,prefix,current=False):
    keys(receipt,'schema endpoints receipts'); require(receipt['schema']=='layout-retrieval-v1' and receipt['endpoints']==endpoints(role,current),'exact authenticated endpoint roles')
    expected=list(receipt['endpoints'].items())+[('ZIP','repos/'+role['repository']+'/actions/artifacts/'+str(role['artifact_id'])+'/zip')]; require(type(receipt['receipts']) is list and len(receipt['receipts'])==len(expected),'complete no-duplicate retrieval ledger')
    documents={}; log=None; zipped=None
    for label,endpoint in expected:
        rows=[r for r in receipt['receipts'] if r['label']==label]; require(len(rows)==1,'one endpoint capture'); row=rows[0]
        keys(row,'label argv returncode started_ns ended_ns stdout stderr failure reaped')
        require(row['argv']==['gh','api','--hostname','github.com',endpoint] and type(row['returncode']) is int and row['returncode']==0 and row['failure'] is None and row['reaped'] is True and type(row['started_ns']) is int and type(row['ended_ns']) is int and row['started_ns']<=row['ended_ns'],'exact successful endpoint receipt')
        for suffix in ('stdout','stderr'):
            file_row(row[suffix]); data=buffers[prefix+label+'.'+suffix]; require(row[suffix]=={'bytes':len(data),'sha256':digest(data)},'actual bounded endpoint bytes/SHA')
        require(parse_json(buffers[prefix+label+'.receipt.json'])==row,'same retained command receipt')
        raw=buffers[prefix+label+'.stdout']
        if label=='joblog': log=raw
        elif label=='ZIP': zipped=raw
        else: documents[label]=parse_json(raw)
    api_identity(documents,role,STEPS if current else ORIGINAL_STEPS,'paired-layout-relation' if current else None)
    if current: plaintext_log(log)
    require({'bytes':len(zipped),'sha256':digest(zipped)}=={k:role['ZIP'][k] for k in ('bytes','sha256')},'same authenticated entire ZIP')
    return zipped


def bind_object(control,raw):
    record=control['accepted_v67']['object']; require(type(raw) is bytes and len(raw)==record['bytes']<=16777216 and digest(raw)==record['sha256'],'whole accepted linked object bytes/SHA only')
    out=[]
    for span in control['finite_profile']['object_debug_slices']:
        start,size=span['offset'],span['size']; require(type(start) is int and type(size) is int and 0<=start<start+size<=len(raw),'bounded raw source slice')
        require(digest(raw[start:start+size])==span['bytes_sha256'],'same-buffer raw debug slice SHA')
        out.append({'name':span['name'],'offset':start,'bytes':size,'sha256':span['bytes_sha256']})
    require(len({s['name'] for s in out})==4,'four unique source debug spans'); return out


def verify_source(buffers,manifest,expected):
    require(manifest==expected and set(expected)==set(PUBLIC),'exact current public source/control set')
    for name,row in expected.items():
        raw=buffers['source/'+name]; require(row=={'bytes':len(raw),'sha256':digest(raw)},'actual retained source blob bytes/SHA')
