"""New invented finite-body cases. Never loads the captured production profile."""
import argparse
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import stat
import tempfile

CASES = ('v69_public_complete_finite_new_body_positive','v69_public_unreported_width_alignment_positive','v69_public_empty_role_reject','v69_public_inherited_only_direct_body_reject','v69_public_duplicate_candidate_name_reject','v69_public_missing_direct_child_reject','v69_public_extra_unreachable_node_reject','v69_public_duplicate_node_identity_reject','v69_public_cross_role_reference_reject','v69_public_unresolved_byvalue_reference_reject','v69_public_byvalue_cycle_reject','v69_public_raw_reference_arithmetic_reject','v69_public_unknown_attribute_form_reject','v69_public_location_missing_reject','v69_public_location_drift_reject','v69_public_structure_size_drift_reject','v69_public_member_name_drift_reject','v69_public_sharing_topology_drift_reject','v69_public_inherited_target_identity_reject','v69_public_inherited_context_crosswire_reject','v69_public_pointer_signature_inference_reject','v69_public_unknown_keys_or_bool_integer_reject','v69_public_fake_complete_or_count_marker_reject','v69_public_object_or_debug_slice_digest_reject')


def synthetic():
    """Invented coordinates, names, byte buffers and source/API identities."""
    h=lambda raw:hashlib.sha256(raw).hexdigest()
    profile={'anchors':{},'new_nodes':[],'direct_child_edges':[],'inherited_boundary_pairs':[],'inherited_contexts':[],'pointer_contexts':[],'anchor_premises':{},'accepted_raw_counts':{}}
    def ident(cu,offset): return str(cu)+':'+str(cu+offset)
    def attr(name,value): return {'form':'DW_FORM_strp','value':{'bytes_hex':value.encode().hex()},'raw_value':100+len(value)} if name=='DW_AT_name' else {'form':'DW_FORM_data1','value':value,'raw_value':value}
    for role,cu in (('provider',0),('core',1000)):
        profile['anchors'][role]={'CU_header_inherited':{'address_size':8,'debug_abbrev_offset':0,'unit_length':500,'version':4},'CU_offset':cu,'inherited_member_id':ident(cu,9),'inherited_union_id':ident(cu,10),'member_name':'sample_union','member_start_inherited':64,'role':role,'union_size_inherited':16}
        def ref(offset): return {'form':'DW_FORM_ref4','value':offset,'raw_value':offset,'target':ident(cu,offset)}
        records=[(20,'DW_TAG_member','variant',0,30),(30,'DW_TAG_structure_type','sample_body',16,None),(40,'DW_TAG_member','callback',0,50),(45,'DW_TAG_member','callback_other',4,50),(50,'DW_TAG_pointer_type',None,None,80),(60,'DW_TAG_member','count',8,90)]
        for offset,tag,name,number,target in records:
            attrs={} if name is None else {'DW_AT_name':attr('DW_AT_name',name),('DW_AT_byte_size' if tag=='DW_TAG_structure_type' else 'DW_AT_data_member_location'):attr('number',number)}
            profile['new_nodes'].append({'id':ident(cu,offset),'role':role,'tag':tag,'attributes':attrs,'type_reference':None if target is None else ref(target),'complete':True,'entry_basis':['parser_sequential_direct_child' if tag=='DW_TAG_member' else 'parser_interpreted_in_CU_reference'],'independent_lexical_DIE_boundary_proven':False})
        for parent,child in ((10,20),(30,40),(30,45),(30,60)): profile['direct_child_edges'].append({'role':role,'parent':ident(cu,parent),'child':ident(cu,child)})
        profile['inherited_contexts'].append({'role':role,'parent':ident(cu,60),'target':ident(cu,90),'context':'type_inherited_stop','pair_id':'sample_accepted_pair'})
        profile['pointer_contexts'].append({'id':ident(cu,50),'role':role,'raw_type_reference':ref(80),'boundary':'New pointer tag/raw emitted reference only; width, signature and pointee not observed'})
    profile['inherited_boundary_pairs']=[{'pair_id':'sample_accepted_pair','provider':'0:90','core':'1000:1090','accepted_RESULT_sha256':h(b'synthetic private result'),'accepted_comparison_JSON_pointer':'/finite_relation/comparisons/0','accepted_comparison_canonical_sha256':h(b'synthetic accepted pair'),'meaning':'Invented premise only'}]
    profile['anchor_premises']={'member_pair':{'provider':'0:9','core':'1000:1009','reported_member_start':64,'source':'invented prior label'},'union_pair':{'provider':'0:10','core':'1000:1010','reported_byte_size':16,'accepted_control_sha256':h(b'synthetic prior control'),'accepted_opaque_pair':{'allowed_contexts':['by_value_member_storage_metadata','pointer_target_label_metadata'],'comparison':'invented opaque labels','provider':'0:10','core':'1000:1010'},'claim':'Prior labels only'}}
    profile['accepted_raw_counts']={'new_nodes_total':12,'new_nodes_per_role':6,'new_member_nodes_total':8,'new_structure_nodes_total':2,'new_pointer_nodes_total':2,'direct_union_members_each_role':1,'new_direct_child_edges_total':8,'inherited_contexts_total':2,'pointer_contexts_total':2,'unsupported_or_unresolved':0,'new_alignment_attributes_reported':0,'old210_intersection':0}
    blob=b'synthetic object bytes'; fp=lambda raw:{'bytes':len(raw),'sha256':h(raw)}
    namespace='sample-input'; members={namespace+'/data.o':fp(blob),namespace+'/result.json':fp(b'sample result'),namespace+'/source-manifest.json':fp(b'sample manifest'),namespace+'/control.json':fp(b'sample control')}
    member=lambda name:{'member':namespace+'/'+name,**members[namespace+'/'+name]}
    accepted={'repository':'example/project','run_id':101,'run_attempt':1,'source_commit':'a'*40,'workflow_id':102,'job_id':103,'artifact_id':104,'artifact_name':'sample-evidence','ZIP':fp(b'invented ZIP label'),'private_RESULT':fp(b'private label'),'private_review':fp(b'review label'),'accepted_collector_sha256':h(b'collector'),'namespace':namespace,'complete_member_map':members,'producer_result':member('result.json'),'source_manifest':member('source-manifest.json'),'control':member('control.json'),'object':{**member('data.o'),'original_v67_member_label':'sample-prior/data.o'},'object_debug_slices':[{'name':'sample_slice_'+str(i),'offset':i,'size':1,'bytes_sha256':h(blob[i:i+1]),'alignment':1,'entsize':0,'flags':0,'index':i+1,'info':0,'link':0,'name_offset':i,'type':1} for i in range(4)],'job_name':'sample_job','required_original_steps':[{'number':1,'name':'sample step','status':'completed','conclusion':'success'}],'prior_joblog_policy':'No prior joblog fetch'}
    basis={'query_result':fp(b'sample raw result'),'query_review_sha256':h(b'raw review'),'query_close_sha256':h(b'close'),'query_source':fp(b'query source'),'query_checkpoint_sha256':h(b'query checkpoint'),'query_pins_sha256':h(b'pins'),'input_profile_sha256':h(b'input profile'),'parser_package_manifest_sha256':h(b'parser manifest'),'query_invocations_consumed':1,'independent_lexical_DIE_boundary_proven':False,'reference_resolution_basis':'parser interpretation only'}
    policy={k:'synthetic policy' for k in ('level','member_match','attributes_absence','reference_check','pairing','pointer_stop','inherited_stop','closure','result')}; policy.update(new_tag_allowlist=['DW_TAG_member','DW_TAG_structure_type','DW_TAG_pointer_type'],attribute_forms={'DW_AT_name':['DW_FORM_strp'],'DW_AT_data_member_location':['DW_FORM_data1'],'DW_AT_byte_size':['DW_FORM_data1']},raw_reference_forms=['DW_FORM_ref4'])
    caps={'control_bytes':262144,'object_bytes':16777216,'old_ZIP_bytes':16777216,'old_expanded_bytes':67108864,'old_members':4096,'new_nodes':512,'new_edges':2048,'relation_depth':32,'metadata_JSON_bytes':4194304,'current_ZIP_bytes':33554432,'current_expanded_bytes':100663296,'current_members':4096,'API_JSON_bytes':4194304,'plaintext_joblog_bytes':4194304,'stderr_bytes':1048576,'capture_role_total_seconds':180,'kill_reap_grace_seconds':5,'result_bytes':8388608}
    return {'schema':'v69-finite-parser-observed-cra-u-body-control-v1','accepted_v68':accepted,'new_observation_basis':basis,'finite_profile':profile,'relation_policy':policy,'caps':caps,'nonclaims':['Synthetic metadata only; no runtime/width/layout claim']},blob


def run_case(name,contract,module):
    value,blob=synthetic(); p=value['finite_profile']; nodes=p['new_nodes']; byid={n['id']:n for n in nodes}; core=lambda offset:byid['1000:'+str(1000+offset)]
    if name==CASES[0]:
        contract.validate_control(value); result=module.relation(value); assert result['passed'] and len(result['comparisons'])==6; return
    if name==CASES[1]:
        result=module.relation(value); assert result['pointer_width_signature_pointee_alignment_member_extent_proven'] is False and all(not n['attributes'] for n in nodes if n['tag']=='DW_TAG_pointer_type'); return
    if name==CASES[2]: p['direct_child_edges']=[e for e in p['direct_child_edges'] if e['parent']!='1000:1010']
    elif name==CASES[3]: p['direct_child_edges'][-4]['child']='1000:1090'
    elif name==CASES[4]:
        n=copy.deepcopy(core(20)); n['id']='1000:1021'; nodes.append(n); p['direct_child_edges'].append({'role':'core','parent':'1000:1010','child':n['id']})
    elif name==CASES[5]: p['direct_child_edges'].pop()
    elif name==CASES[6]:
        n=copy.deepcopy(core(30)); n['id']='1000:1031'; nodes.append(n)
    elif name==CASES[7]: nodes.append(copy.deepcopy(nodes[0]))
    elif name==CASES[8]: core(20)['type_reference']['target']='0:30'
    elif name==CASES[9]: core(20)['type_reference']={'form':'DW_FORM_ref4','value':200,'raw_value':200,'target':'1000:1200'}
    elif name==CASES[10]: core(40)['type_reference']={'form':'DW_FORM_ref4','value':30,'raw_value':30,'target':'1000:1030'}
    elif name==CASES[11]: core(20)['type_reference']['raw_value']=31
    elif name==CASES[12]: core(60)['attributes']['DW_AT_data_member_location']['form']='DW_FORM_data2'
    elif name==CASES[13]: del core(60)['attributes']['DW_AT_data_member_location']
    elif name==CASES[14]: core(60)['attributes']['DW_AT_data_member_location'].update(value=9,raw_value=9)
    elif name==CASES[15]: core(30)['attributes']['DW_AT_byte_size'].update(value=24,raw_value=24)
    elif name==CASES[16]: core(20)['attributes']['DW_AT_name']['value']['bytes_hex']=b'changed'.hex()
    elif name==CASES[17]:
        n=copy.deepcopy(core(50)); n['id']='1000:1051'; nodes.append(n); core(45)['type_reference']={'form':'DW_FORM_ref4','value':51,'raw_value':51,'target':n['id']}; stop=copy.deepcopy(p['pointer_contexts'][-1]); stop['id']=n['id']; p['pointer_contexts'].append(stop)
    elif name==CASES[18]:
        core(60)['type_reference']={'form':'DW_FORM_ref4','value':91,'raw_value':91,'target':'1000:1091'}; p['inherited_contexts'][-1]['target']='1000:1091'
    elif name==CASES[19]: p['inherited_contexts'][-1]['parent']='1000:1040'
    elif name==CASES[20]: core(50)['attributes']['DW_AT_byte_size']={'form':'DW_FORM_data1','value':8,'raw_value':8}
    elif name==CASES[21]:
        bad=copy.deepcopy(value); bad['finite_profile']['new_nodes'][0]['extra']=True
        try: module.relation(bad)
        except (ValueError,KeyError): pass
        else: raise AssertionError('extra key accepted')
        core(60)['attributes']['DW_AT_data_member_location'].update(value=True,raw_value=True)
    elif name==CASES[22]: p['accepted_raw_counts']['new_nodes_total']+=1
    elif name==CASES[23]:
        contract.object_binding(blob,value)
        try: contract.object_binding(blob+b'x',value)
        except ValueError: return
        raise AssertionError('changed object accepted')
    else: raise AssertionError('unknown new case')
    try: module.relation(value)
    except (ValueError,KeyError): return
    raise AssertionError('mutation accepted: '+name)


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


def _preflight(args,inventory=False,audit=False):
    guards=[]; raw,guard=_read(args.checkpoint,4194304,args.checkpoint_sha256); guards.append(guard); cp=_json(raw)
    _require(cp['schema']=='v69-finite-union-body-coding-checkpoint-v1','checkpoint schema')
    root=Path(os.path.abspath(cp['workspace_root'])); rows=cp['production_sources']; _require(type(rows) is dict and len(rows)==11 and set(rows)==set(cp['public_sources'])|set(cp['private_sources']),'all11 source closure before custom imports')
    for name,row in rows.items():
        _require(type(row) is dict and set(row)=={'bytes','sha256'} and not Path(name).is_absolute() and '..' not in name.split('/'),'flat source/hash rows')
        data,guard=_read(root/name,1048576,row['sha256'],row['bytes']); guards.append(guard)
    source=Path(os.path.abspath(__file__)); expected={root/name for name in rows}
    if audit:
        row=cp['audit']['source']; data,guard=_read(row['path'],1048576,row['sha256'],row['bytes']); guards.append(guard); expected.add(Path(os.path.abspath(row['path'])))
    _require(source in expected,'entrypoint in exact source closure')
    invrow=cp['inventory']; invraw,guard=_read(invrow['path'],4194304,invrow['sha256'],invrow['bytes']); guards.append(guard); inv=_json(invraw)
    if inventory:
        _require(Path(os.path.abspath(args.inventory))==Path(os.path.abspath(invrow['path'])) and args.inventory_sha256==invrow['sha256'],'exact harness inventory CLI')
    row=cp['control']; controlraw,guard=_read(root/row['path'],262144,row['sha256'],row['bytes']); guards.append(guard)
    _require(rows[row['path']]=={k:row[k] for k in ('bytes','sha256')},'source/control blob pair')
    _stable(guards); return cp,root,inv,_json(controlraw),guards


def _load(cp,root,name):
    _require(name in cp['production_sources'],'new source in checkpoint'); row=cp['production_sources'][name]; raw,guard=_read(root/name,1048576,row['sha256'],row['bytes'])
    spec=importlib.util.spec_from_file_location('_new_body_'+Path(name).stem,root/name); module=importlib.util.module_from_spec(spec)
    # Execute the verified in-memory source buffer, never reopen an unbounded file.
    exec(compile(raw,str(root/name),'exec'),module.__dict__); _stable([guard]); return module


def _harness(args,role,expected_cases,runner):
    _fresh_output(args.output); completed=[]; next_case='source_preflight'; cp=None; guards=[]
    result={'schema':'v69-new-case-receipt-v1','passed':False,'checkpoint_sha256':args.checkpoint_sha256,'inventory_sha256':args.inventory_sha256,'role':role,'completed_cases':completed,'completed_count':0,'next_case':next_case}
    try:
        cp,root,inv,control,guards=_preflight(args,inventory=True)
        cases=tuple(row['id'] for row in inv[role]); _require(cases==tuple(expected_cases),'frozen new case order/count')
        reviewraw,guard=_read(args.first_use_review,4194304,args.first_use_review_sha256); guards.append(guard); review=_json(reviewraw)
        _require(set(review)=={'schema','approved','checkpoint_sha256','inventory_sha256','sources','role','cases','output_path','execution_budget'} and review['schema']=='v69-new-cases-first-use-v1' and review['approved'] is True and review['checkpoint_sha256']==args.checkpoint_sha256 and review['inventory_sha256']==args.inventory_sha256 and review['sources']==cp['production_sources'] and review['role']==role and review['cases']==list(cases) and Path(os.path.abspath(review['output_path']))==Path(os.path.abspath(args.output)) and type(review['execution_budget']) is int and review['execution_budget']==1,'exact reviewed source/new-case first use')
        result['sources']=cp['production_sources']
        modules=runner(cp,root,None,None)
        for name in cases:
            next_case=name; result['next_case']=name; runner(cp,root,name,modules); completed.append(name); result['completed_count']=len(completed)
        _stable(guards); result.update(passed=True,next_case=None); _emit(args.output,result)
    except Exception as exc:
        result.update(passed=False,next_case=next_case,completed_count=len(completed),exception={'type':type(exc).__name__,'message':str(exc)}); _emit(args.output,result); raise


def _harness_cli():
    parser=argparse.ArgumentParser()
    for name in ('checkpoint','checkpoint-sha256','inventory','inventory-sha256','first-use-review','first-use-review-sha256','output'): parser.add_argument('--'+name,required=True)
    return parser.parse_args()


def _runner(cp,root,name,modules):
    if name is None: return (_load(cp,root,'note10/device_test/cra_u_union_body_input_contract.py'),_load(cp,root,'note10/device_test/cra_u_union_body_relation.py'))
    run_case(name,*modules)


if __name__=='__main__': _harness(_harness_cli(),'public',CASES,_runner)
