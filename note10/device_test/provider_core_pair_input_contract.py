"""Bounded data and transport contract for a new provider/core pair link."""
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

CONTROL = Path(__file__).with_name('provider_core_pair_control.json')
CAP = 64 * 1024 * 1024
HELPER_SHA = '881c01a5ff6e00d91337c2190a516da094e28f186f36bfc996f68b651a382de2'
PUBLIC = ('note10/device_test/build_provider_core_pair.py', 'note10/device_test/provider_core_pair.py', 'note10/device_test/provider_core_pair_input_contract.py', 'note10/device_test/stage_provider_core_pair.py', 'note10/device_test/test_provider_core_pair.py', '.github/workflows/note10-provider-core-pair.yml', 'note10/device_test/provider_core_pair_control.json', 'note10/device_test/crypto_hash_composite.py')
STEPS = ('Checkout exact source', 'Provision GNU linker', 'Produce one pair link', 'Stage complete evidence', 'Upload complete evidence')


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


def symbol(row):
    keys(row, 'index name info other section value size')
    require(type(row['name']) is str and '\x00' not in row['name'], 'symbol name')
    for k in ('index', 'info', 'other', 'section', 'value', 'size'):
        integer(row[k])


def section(row, contribution=False):
    keys(row, 'alignment entsize flags index info link name name_offset offset size type' + (' object_sha256 role' if contribution else ''))
    for k in ('alignment', 'entsize', 'flags', 'index', 'info', 'link', 'name_offset', 'offset', 'size', 'type'):
        integer(row[k])
    require(type(row['name']) is str, 'section name')
    if contribution:
        hexsha(row['object_sha256']); require(row['role'] in ('provider', 'core'), 'section owner')


def rela(row):
    keys(row, 'addend entry offset relocation_section section symbol type')
    for k in ('entry', 'offset', 'relocation_section', 'section', 'symbol', 'type'):
        integer(row[k])
    require(type(row['addend']) is int and -(1 << 63) <= row['addend'] < 1 << 63, 'signed RELA addend')


def validate_control(c):
    keys(c, 'schema accepted_v66 frozen_input_profile link_profile caps nonclaims')
    require(c['schema'] == 'provider-core-pair-control-v1', 'one control schema')
    a = c['accepted_v66']
    keys(a, 'ZIP accepted_private_result accepted_reader_result_sha256 artifact_id artifact_name complete_collector complete_original_member_map independent_actual_review_sha256 job_id members profile repository run_attempt run_id source_commit use workflow_id')
    keys(a['ZIP'], 'bytes ordinary_expanded_bytes ordinary_members root sha256'); file_row({k:a['ZIP'][k] for k in ('bytes','sha256')})
    require(a['profile'] == 'accepted-v66-interface-ZIP-v1' and type(a['run_attempt']) is int and a['run_attempt'] == 1, 'single accepted role profile')
    require(re.fullmatch('[0-9a-f]{40}', a['source_commit']) is not None and re.fullmatch('[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', a['repository']) is not None, 'accepted source/repository')
    for k in ('accepted_private_result', 'complete_collector'):
        keys(a[k], 'sha256'); hexsha(a[k]['sha256'])
    for k in ('accepted_reader_result_sha256', 'independent_actual_review_sha256'):
        hexsha(a[k])
    for k in ('artifact_id', 'job_id', 'run_id', 'workflow_id'):
        integer(a[k], 1, 1 << 63)
    for k in ('artifact_name', 'use'):
        require(type(a[k]) is str and a[k], 'accepted role text')
    member(a['ZIP']['root']); integer(a['ZIP']['ordinary_members'], 1, 4096); integer(a['ZIP']['ordinary_expanded_bytes'])
    m = a['complete_original_member_map']
    require(type(m) is dict and len(m) == a['ZIP']['ordinary_members'] and sum(x['bytes'] for x in m.values()) == a['ZIP']['ordinary_expanded_bytes'], 'complete original namespace totals')
    for name, row in m.items():
        member(name); file_row(row); require(name.startswith(a['ZIP']['root'] + '/'), 'original namespace root')
    keys(a['members'], 'provider core join producer_result retained_tool_control source_manifest')
    for row in a['members'].values():
        keys(row, 'bytes member sha256'); member(row['member']); file_row({k:row[k] for k in ('bytes','sha256')})
        require(m.get(row['member']) == {k:row[k] for k in ('bytes','sha256')}, 'selected member bound to complete map')
    p = c['frozen_input_profile']
    keys(p, 'attribution object_records global_same_name_group_count global_collision_summary selected_direct_spans selected_complete_RELA direct_named_definition_candidates relocation_destinations_and_allowed_forms selected_RELA_count selected_RELA_kind_counts selected_RELA_width_bytes selected_span_count direct_only_span_count unique_owned_span_count unsupported_observed')
    keys(p['attribution'], 'accepted_v66_result_sha256 accepted_query_result_sha256 accepted_query_review_sha256 query_source_sha256 query_checkpoint_sha256 query_pins_sha256 provider_labels new_query_facts')
    for k, v in p['attribution'].items():
        require(type(v) is str, 'attribution text')
        if k.endswith('sha256'): hexsha(v)
    require(p['attribution']['accepted_v66_result_sha256'] == a['accepted_private_result']['sha256'], 'separate private accepted result identity')
    keys(p['global_collision_summary'], 'same_name_groups scope finite_uniqueness')
    require(p['global_same_name_group_count'] == p['global_collision_summary']['same_name_groups'] == 21 and all(type(p['global_collision_summary'][k]) is str for k in ('scope','finite_uniqueness')), 'global collisions outside finite claim')
    keys(p['object_records'], 'provider core')
    for role, row in p['object_records'].items():
        keys(row, 'bytes member sha256'); require(row == a['members'][role], 'whole-object role record')
    spans = p['selected_direct_spans']; require(type(spans) is list and len(spans) == p['unique_owned_span_count'] == 10, 'ten finite spans')
    seen = set()
    for row in spans:
        keys(row, 'all_same_name_contributions object_sha256 reasons role section section_bytes_sha256'); section(row['section']); hexsha(row['section_bytes_sha256'])
        require(row['role'] in ('provider','core') and row['object_sha256'] == p['object_records'][row['role']]['sha256'], 'qualified whole-object span')
        require(type(row['reasons']) is list and row['reasons'] and all(type(x) is str for x in row['reasons']), 'finite attribution reasons')
        require(type(row['all_same_name_contributions']) is list and len(row['all_same_name_contributions']) == 1, 'reviewed unique span contribution')
        contribution = row['all_same_name_contributions'][0]; section(contribution, True)
        require(contribution == dict(row['section'], role=row['role'], object_sha256=row['object_sha256']), 'same qualified section owner')
        s = row['section']; key = (row['role'], s['index'])
        require(key not in seen and s['type'] == 1 and s['size'] > 0 and not s['flags'] & (16|32|512) and s['offset'] + s['size'] <= p['object_records'][row['role']]['bytes'], 'finite unmerged complete input span')
        seen.add(key)
    selected = p['selected_complete_RELA']; require(type(selected) is list and len(selected) == p['selected_span_count'] == 3 and p['direct_only_span_count'] == 7, 'three selected sections')
    all_rows = []
    for row in selected:
        keys(row, 'accepted_label full_section_extent purpose raw_complete_section_RELA raw_symbol role'); symbol(row['accepted_label']); symbol(row['raw_symbol'])
        require(row['accepted_label'] == row['raw_symbol'] and row['full_section_extent'] is True and row['role'] in ('provider','core') and row['purpose'] in ('init','table','registration_target'), 'accepted selected label')
        require((row['role'], row['raw_symbol']['section']) in seen and type(row['raw_complete_section_RELA']) is list, 'selected section included')
        for rr in row['raw_complete_section_RELA']:
            rela(rr); require(rr['section'] == row['raw_symbol']['section'], 'selected complete RELA target'); all_rows.append((row['role'],row['purpose'],rr))
    require(len(all_rows) == p['selected_RELA_count'] == 13 and p['selected_RELA_width_bytes'] == {'257':8,'275':4,'277':4,'283':4}, 'only observed typed selected fields')
    require(p['selected_RELA_kind_counts'] == {str(t):sum(r['type']==t for _,_,r in all_rows) for t in (257,275,277,283)}, 'complete actual kind counts')
    for v in list(p['selected_RELA_kind_counts'].values())+list(p['selected_RELA_width_bytes'].values())+[p[k] for k in ('global_same_name_group_count','selected_RELA_count','selected_span_count','direct_only_span_count','unique_owned_span_count')]: integer(v)
    refs = p['relocation_destinations_and_allowed_forms']; require(type(refs) is list and len(refs) == 13, 'complete typed destinations')
    require([(x['origin_role'],x['selected_purpose'],x['relocation']) for x in refs] == all_rows, 'ordered complete selected destination rows')
    for row in refs:
        base = 'origin_role selected_purpose relocation raw_target_symbol destination_role destination_section_name destination_coordinate allowed_output_forms'
        undefined = row['raw_target_symbol']['section'] == 0
        keys(row, base + (' required_definition' if undefined else ' target_coordinate coordinate_definition_candidates'))
        rela(row['relocation']); symbol(row['raw_target_symbol']); integer(row['destination_coordinate'])
        require(row['destination_role'] in ('provider','core') and type(row['destination_section_name']) is str, 'qualified destination')
        require(any(x['role']==row['destination_role'] and x['section']['name']==row['destination_section_name'] for x in spans), 'destination finite owned span')
        if undefined:
            symbol(row['required_definition']); require(row['allowed_output_forms'] == ['named_defined_registration_target_only'] and row['relocation']['type']==283 and row['raw_target_symbol']['info']==16 and row['required_definition']['info']==18 and row['raw_target_symbol']['name']==row['required_definition']['name']=='crypto_register_shashes', 'one contextual NOTYPE/FUNC edge')
        else:
            integer(row['target_coordinate']); require(row['target_coordinate']==row['destination_coordinate'], 'frozen destination coordinate')
            require(type(row['coordinate_definition_candidates']) is list and len(row['coordinate_definition_candidates'])==1, 'one direct coordinate witness')
            for s in row['coordinate_definition_candidates']: symbol(s)
            expected = ['anonymous_local_section_symbol_only'] if row['raw_target_symbol']['info']==3 else ['same_named_definition','anonymous_local_section_symbol_with_exact_coordinate_rebase']
            require(row['allowed_output_forms']==expected, 'closed per-row output forms')
    require(type(p['direct_named_definition_candidates']) is list and p['unsupported_observed']==[], 'supported frozen inventory only')
    for row in p['direct_named_definition_candidates']:
        keys(row, 'definitions name'); require(type(row['name']) is str and type(row['definitions']) is list, 'direct candidate inventory')
        for x in row['definitions']:
            keys(x, 'eligible_strong_normal_definition object_sha256 role raw_symbol'); require(x['eligible_strong_normal_definition'] is True and x['role'] in ('provider','core'), 'unique strong raw candidate'); symbol(x['raw_symbol']); hexsha(x['object_sha256'])
            require(x['object_sha256']==p['object_records'][x['role']]['sha256'] and x['raw_symbol']['name']==row['name'], 'qualified strong candidate')
        require(len(row['definitions'])==1, 'unique strong definition')
    lp=c['link_profile']; keys(lp, 'exact_argv version_argv tool input_order link_count version_count'); keys(lp['tool'], 'path role sha256 version'); hexsha(lp['tool']['sha256'])
    require(lp['tool']['path']=='/usr/bin/aarch64-linux-gnu-ld.bfd' and lp['tool']['role']=='aarch64-linux-gnu-ld' and type(lp['tool']['version']) is str and lp['tool']['version'].startswith('GNU ld (GNU Binutils for Ubuntu) 2.38\n'), 'single GNU profile')
    require(lp['exact_argv']==['<pinned-resolved-GNU-ld>','-m','aarch64linux','--no-relax','-r','-o','paired/provider-core-pair.o','inputs/provider.o','inputs/core.o'] and lp['version_argv']==['<same-pinned-resolved-GNU-ld>','--version'] and lp['input_order']==['provider.o','core.o'] and lp['link_count']==lp['version_count']==1, 'one fixed real link command')
    integer(lp['link_count'],1,1); integer(lp['version_count'],1,1)
    require(c['caps']=={'old_ZIP':16777216,'expanded':67108864,'members':4096,'ELF':16777216,'ELF_sections':4096,'ELF_symbols':65536,'ELF_RELA':131072,'JSON_text':8388608,'tool_binary':33554432,'evidence':67108864,'command_stdout':8388608,'command_stderr':8388608,'command_total_seconds':180,'API_total_seconds':180}, 'fixed bounded resource profile')
    for v in c['caps'].values(): integer(v)
    keys(c['nonclaims'], 'Image_BOOT_XNU_iOS_execution_or_readiness SHA_correctness_reproved allocation_success core_recompiled deployment_ready device_authorized generated_or_whole_binary_ABI_proven independent_core_layout_or_paired_DIE_proven note old_semantic_origin_model_or_fixture_replay physical_BOOT_reboot provider_recompiled provider_runtime_available registration_or_callback_execution runtime_or_vermagic_compatibility_proven whole_stack_bound_or_full_Image whole_toolchain_identity_proven')
    require(all(v is False for k,v in c['nonclaims'].items() if k not in ('note','physical_BOOT_reboot')) and type(c['nonclaims']['note']) is str and type(c['nonclaims']['physical_BOOT_reboot']) is int and c['nonclaims']['physical_BOOT_reboot']==0, 'honest finite nonclaims')
    return c


def load_control(expected_sha):
    hexsha(expected_sha); snap=snapshot(CONTROL,8*1024*1024)
    require(snap['sha256']==expected_sha, 'fixed committed control SHA')
    value=validate_control(parse_json(snap['raw'])); unchanged(snap)
    return value,snap


def inventory(root):
    root=Path(root); out={}; total=0
    for path in sorted(root.rglob('*')):
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


def capture(argv, cwd, directory, label, limit, timeout, env=None):
    """Pipes drained concurrently; wall timeout interrupts a blocked child read."""
    require(type(argv) is list and all(type(x) is str for x in argv), 'literal argv, no shell')
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
    deadline=time.monotonic()+timeout; failure=None
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


def old_api_documents(documents, a):
    keys(documents,'run jobs artifacts artifact')
    run=documents['run']; require(run['id']==a['run_id'] and run['run_attempt']==a['run_attempt'] and run['head_sha']==a['source_commit'] and run['workflow_id']==a['workflow_id'] and run['status']=='completed' and run['conclusion']=='success' and run['repository']['full_name']==a['repository'], 'authenticated accepted run tuple')
    jobs=documents['jobs']; require(type(jobs['total_count']) is int and jobs['total_count']==len(jobs['jobs'])<=100, 'complete jobs page')
    matching=[j for j in jobs['jobs'] if j['id']==a['job_id']]; require(len(matching)==1, 'accepted exact job'); job=matching[0]
    require(job['status']=='completed' and job['conclusion']=='success' and all(s['status']=='completed' and s['conclusion'] in ('success','skipped') for s in job['steps']), 'complete accepted successful steps')
    required=('Produce finite provider core metadata join','Stage exact interface evidence namespace','Upload interface metadata evidence'); require(all(any(s['name']==name and s['conclusion']=='success' for s in job['steps']) for name in required), 'required accepted step names')
    rows=documents['artifacts']; require(rows['total_count']==len(rows['artifacts'])<=100, 'complete artifacts page')
    matches=[x for x in rows['artifacts'] if x['id']==a['artifact_id']]; require(len(matches)==1 and matches[0]==documents['artifact'], 'individual artifact matches complete listing')
    art=matches[0]; require(art['name']==a['artifact_name'] and art['size_in_bytes']==a['ZIP']['bytes'] and art['expired'] is False and art['workflow_run']['id']==a['run_id'] and art['workflow_run']['head_sha']==a['source_commit'], 'artifact source/size identity')


def retrieve_old(control, directory):
    directory=Path(directory); directory.mkdir(); a=control['accepted_v66']; prefix='repos/'+a['repository']+'/actions/'
    endpoints={'run':prefix+'runs/'+str(a['run_id'])+'/attempts/1','jobs':prefix+'runs/'+str(a['run_id'])+'/attempts/1/jobs?filter=all&per_page=100','artifacts':prefix+'runs/'+str(a['run_id'])+'/artifacts?per_page=100','artifact':prefix+'artifacts/'+str(a['artifact_id'])}
    documents={}; receipts=[]
    for label,endpoint in endpoints.items():
        raw,row=capture(['gh','api',endpoint],None,directory,label,8*1024*1024,180); documents[label]=parse_json(raw); receipts.append(row)
    old_api_documents(documents,a)
    raw,row=capture(['gh','api',prefix+'artifacts/'+str(a['artifact_id'])+'/zip'],None,directory,'ZIP',16*1024*1024,180); receipts.append(row)
    require({'bytes':len(raw),'sha256':digest(raw)}=={k:a['ZIP'][k] for k in ('bytes','sha256')}, 'authenticated entire old ZIP')
    files,buffers=zip_snapshot(raw,a['complete_original_member_map']); write_json(directory/'retrieval.json',{'endpoints':endpoints,'receipts':receipts,'files':files})
    return raw,buffers


def source_closure(root):
    rows={}
    for name in PUBLIC:
        snap=snapshot(Path(root)/name,8*1024*1024); rows[name]={k:snap[k] for k in ('bytes','sha256')}
    require(rows[PUBLIC[-1]]['sha256']==HELPER_SHA, 'immutable generic helper hash')
    return rows


def exception_record(exc):
    return {'type':type(exc).__name__,'message':str(exc)}


def verify_command_evidence(control, result, buffers):
    keys(result['commands'],'version link')
    profile=control['link_profile']; tool=profile['tool']; commands=result['commands']
    require(result['tool']==tool and result['link_count']==result['version_count']==1, 'exact fresh tool and counts')
    for label in ('version','link'):
        row=commands[label]
        keys(row,'label argv returncode started_ns ended_ns stdout stderr failure reaped')
        require(row['label']==label and row['returncode']==0 and row['failure'] is None and row['reaped'] is True and type(row['started_ns']) is int and type(row['ended_ns']) is int and row['started_ns']<=row['ended_ns'], 'successful bounded reaped tool command')
        expected=[tool['path'],'--version'] if label=='version' else [tool['path']]+profile['exact_argv'][1:]
        require(row['argv']==expected, 'exact single command argv/input order')
        for suffix in ('stdout','stderr'):
            file_row(row[suffix]); raw=buffers['commands/'+label+'.'+suffix]
            require(row[suffix]=={'bytes':len(raw),'sha256':digest(raw)}, 'bound actual command output')
        require(parse_json(buffers['commands/'+label+'.receipt.json'])==row, 'same command receipt bytes')
    require(buffers['commands/version.stdout']==tool['version'].encode() and commands['version']['ended_ns']<=commands['link']['started_ns'], 'complete exact fresh version then link')
    require(result['link_environment']=={'PATH':result['link_environment']['PATH'],'LC_ALL':'C','LANG':'C','TZ':'UTC'} and type(result['link_environment']['PATH']) is str, 'finite link environment')


def verify_stability(result, control):
    records=result['stable_capture']; keys(records,'provider core linker output')
    for role,row in records.items():
        keys(row,'bytes sha256 before after')
        require(type(row['before']) is list and row['before']==row['after'] and len(row['before']) in (6,7) and all(type(v) is int for v in row['before']) and row['before'][2]==1 and row['before'][3]==row['bytes'],'same-host full file identity across link/use')
        if role in ('provider','core'): expected=control['accepted_v66']['members'][role]
        elif role=='linker': expected=control['link_profile']['tool']
        else: expected=result['output']
        require(row['sha256']==expected['sha256'] and (role=='linker' or row['bytes']==expected['bytes']),'identity receipt bound to exact bytes/SHA')


def current_api(documents, pins):
    keys(documents,'run jobs artifacts artifact')
    run=documents['run']; require(run['id']==pins['run_id'] and run['run_attempt']==1 and run['head_sha']==pins['source_commit'] and run['workflow_id']==pins['workflow_id'] and run['repository']['full_name']==pins['repository'] and run['status']=='completed' and run['conclusion']=='success', 'current exact successful run')
    jobs=documents['jobs']; require(jobs['total_count']==len(jobs['jobs'])<=100, 'complete current jobs')
    matches=[j for j in jobs['jobs'] if j['id']==pins['job_id']]; require(len(matches)==1, 'one current job'); job=matches[0]
    require(job['name']=='provider-core-pair' and job['status']=='completed' and job['conclusion']=='success', 'new pair job only')
    for name in STEPS:
        rows=[s for s in job['steps'] if s['name']==name]; require(len(rows)==1 and rows[0]['status']=='completed' and rows[0]['conclusion']=='success', 'required complete successful current step '+name)
    listing=documents['artifacts']; require(listing['total_count']==len(listing['artifacts'])<=100, 'complete current artifact list')
    matches=[a for a in listing['artifacts'] if a['id']==pins['artifact_id']]; require(len(matches)==1 and matches[0]==documents['artifact'], 'current artifact metadata closure'); a=matches[0]
    require(a['name']=='note10-provider-core-pair-pc-only' and a['expired'] is False and a['size_in_bytes']==pins['ZIP']['bytes'] and a['workflow_run']['id']==pins['run_id'] and a['workflow_run']['head_sha']==pins['source_commit'], 'current artifact tuple')


def current_log(raw):
    require(type(raw) is bytes and 0<len(raw)<=8*1024*1024 and b'Produce one pair link' in raw and b'Upload complete evidence' in raw, 'fresh mandatory current plaintext job log')


def verify_source_manifest(buffers, manifest, expected):
    require(manifest==expected and set(expected)==set(PUBLIC), 'exact public source set')
    for name,row in expected.items():
        raw=buffers['source/'+name]; require(row=={'bytes':len(raw),'sha256':digest(raw)}, 'retained exact source blob')
    require(expected[PUBLIC[-1]]['sha256']==HELPER_SHA, 'immutable retained helper')
