"""Pure finite relation of accepted reported metadata; no parser or input IO."""
import re
CAP=64*1024*1024

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



def require(ok, message):
    if not ok:
        raise ValueError(message)


def keys(value, names):
    require(type(value) is dict and set(value) == set(names.split()), 'closed object keys: ' + names)


def integer(value, minimum=0, maximum=CAP):
    require(type(value) is int and minimum <= value <= maximum, 'bounded integer')


def hexsha(value):
    require(type(value) is str and re.fullmatch('[0-9a-f]{64}', value) is not None, 'lowercase SHA256')


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


def text(value): require(type(value) is str and 0<len(value.encode('utf8'))<=4096,'bounded text')


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


def name_of(node):
    row=node['attributes'].get('DW_AT_name')
    return None if row is None else bytes.fromhex(row['value']['bytes_hex']).decode('utf8')


def values(node,exclude=()):
    return {k:v['value'] for k,v in node['attributes'].items() if k not in exclude}


def compare(profile,policy,caps,nonclaims):
    """Recompute the finite relation from records, never from status markers."""
    profile_schema(profile)
    require(caps==CAPS and policy['attribute_allowlist_by_tag']==ATTRS and policy['attribute_form_allowlist']==FORMS and policy['selected_children_by_tag']==CHILDREN and policy['reference_allowlist']==['DW_AT_type'] and policy['expanded_targets']==['shash_alg','crypto_alg'] and policy['registration_name']=='crypto_register_shashes' and type(policy['registration_formal_count']) is int and policy['registration_formal_count']==2,'one reviewed finite comparison language')
    require(type(nonclaims) is dict and set(nonclaims)==set(NONCLAIMS) and all((type(v) is int and v==0) if k=='physical_BOOT_reboot' else v is False for k,v in nonclaims.items()),'honest closed nonclaims')
    cus={}
    for cu in profile['selected_CUs']:
        require(cu['role'] not in cus,'unique source-qualified role CU'); cus[cu['role']]=cu
    require(set(cus)=={'provider','core'} and cus['provider']['CU_offset']!=cus['core']['CU_offset'] and cus['provider']['address_size']==cus['core']['address_size'],'two distinct qualified CUs, common reported address size only')
    nodes={}
    for node in profile['nodes']:
        key=node['id']; require(key not in nodes and int(key.split(':')[0])==cus[node['role']]['CU_offset'],'unique CU/role-qualified node identity'); nodes[key]=node
    roots={role:{} for role in cus}
    for c in profile['candidates']:
        require(c['target'] not in roots[c['role']] and c['node'] in nodes,'exact one candidate per target/role')
        node=nodes[c['node']]; require(node['role']==c['role'] and node['tag']==c['tag'] and name_of(node)==c['target'],'candidate exact referenced identity/tag/name')
        if c['target'] in ('shash_alg','crypto_alg'):
            require(node['tag']=='DW_TAG_structure_type' and not node['opaque'] and type(values(node).get('DW_AT_byte_size')) is int and values(node)['DW_AT_byte_size']>0 and node['children'],'complete expanded structure derived from records')
        else:
            require(node['tag']=='DW_TAG_subprogram' and values(node).get('DW_AT_prototyped') is True and values(node).get('DW_AT_external') is True,'reported prototyped registration record')
        roots[c['role']][c['target']]=node['id']
    require(all(set(x)=={'shash_alg','crypto_alg','crypto_register_shashes'} for x in roots.values()) and len(profile['candidates'])==6,'exact six intended candidates, no pending flag accepted as evidence')
    expanded={roots[r][t] for r in roots for t in ('shash_alg','crypto_alg')}
    ref_tags={'DW_TAG_typedef','DW_TAG_const_type','DW_TAG_pointer_type','DW_TAG_array_type','DW_TAG_subrange_type','DW_TAG_member','DW_TAG_formal_parameter','DW_TAG_subroutine_type','DW_TAG_subprogram'}
    required_ref={'DW_TAG_typedef','DW_TAG_array_type','DW_TAG_subrange_type','DW_TAG_member','DW_TAG_formal_parameter','DW_TAG_subprogram'}
    for node in nodes.values():
        require(not node['references'] or node['tag'] in ref_tags,'reference kind valid for reported tag')
        if node['tag'] in required_ref: require(set(node['references'])=={'DW_AT_type'},'required reported type reference')
        require(len(set(node['children']))==len(node['children']),'no duplicated ordered child')
        for target in [x['target'] for x in node['references'].values()]+node['children']:
            require(target in nodes and nodes[target]['role']==node['role'],'closed resolved same-role graph, no foreign reference')
        allowed=CHILDREN.get(node['tag'],[])
        require(all(nodes[c]['tag'] in allowed for c in node['children']),'only approved member/formal/subrange child kinds')
        if node['tag'] in ('DW_TAG_structure_type','DW_TAG_union_type'):
            require(node['opaque']==(node['id'] not in expanded),'exact selected expansion versus opaque aggregate boundary')
        else: require(not node['opaque'],'nonaggregate cannot be opaque')
        if node['tag'] in ('DW_TAG_subprogram','DW_TAG_subroutine_type'): require(values(node).get('DW_AT_prototyped') is True,'emitted prototype flag required')
        if node['tag']=='DW_TAG_array_type': require(len(node['children'])==1,'one observed subrange dimension')
    reachable=set(); pending=[(key,0) for group in roots.values() for key in group.values()]
    while pending:
        key,depth=pending.pop()
        if key in reachable: continue
        require(depth<=caps['graph_depth'],'finite graph depth'); reachable.add(key); n=nodes[key]
        pending.extend((target,depth+1) for target in [x['target'] for x in n['references'].values()]+n['children'])
    require(reachable==set(nodes),'exact reachable finite closure, no unrelated extra record')
    def terminal(key,tags=('DW_TAG_typedef','DW_TAG_const_type')):
        seen=set()
        for _ in range(caps['type_chain']):
            require(key not in seen,'no cyclic type/qualifier chain'); seen.add(key); n=nodes[key]
            if n['tag'] not in tags or not n['references']: return key
            key=n['references']['DW_AT_type']['target']
        raise ValueError('type chain cap')
    for n in nodes.values():
        if n['tag'] in ('DW_TAG_typedef','DW_TAG_const_type'): terminal(n['id'])
    opaque_pairs={}; seen_provider=set(); seen_core=set()
    for pair in profile['opaque_pair_allowlist']:
        a,b=pair['provider'],pair['core']; require(a in nodes and b in nodes and nodes[a]['role']=='provider' and nodes[b]['role']=='core' and nodes[a]['opaque'] and nodes[b]['opaque'] and a not in seen_provider and b not in seen_core,'one qualified stopping pair per opaque node')
        seen_provider.add(a); seen_core.add(b); opaque_pairs[(a,b)]=pair
    require(seen_provider|seen_core=={n['id'] for n in nodes.values() if n['opaque']},'all and only approved opaque nodes paired')
    derived={'nodes':len(nodes),'expanded_aggregates':len(expanded),'opaque_aggregates':len(seen_provider|seen_core),'candidates':sum(len(x) for x in roots.values()),'direct_members':sum(n['tag']=='DW_TAG_member' for n in nodes.values()),'pointer_records':sum(n['tag']=='DW_TAG_pointer_type' for n in nodes.values())}
    require(profile['recorded_counts']==derived,'counts recomputed from raw records')
    for role,group in roots.items():
        shash=nodes[group['shash_alg']]; members=[nodes[k] for k in shash['children']]; base=[m for m in members if name_of(m)=='base']; require(len(base)==1 and terminal(base[0]['references']['DW_AT_type']['target'])==group['crypto_alg'],'base binds exact same-role selected complete crypto_alg')
        for root in ('shash_alg','crypto_alg'):
            children=[nodes[k] for k in nodes[group[root]]['children']]
            require(all(name_of(m) is not None and 'DW_AT_data_member_location' in m['attributes'] for m in children) and len({name_of(m) for m in children})==len(children),'complete ordered named direct members with reported starts')
        function=nodes[group['crypto_register_shashes']]; require(len(function['children'])==2,'two positional registration formals')
        return_id=terminal(function['references']['DW_AT_type']['target']); returned=nodes[return_id]
        require(returned['tag']=='DW_TAG_base_type' and name_of(returned)=='int' and 'DW_AT_encoding' in returned['attributes'] and 'DW_AT_byte_size' in returned['attributes'],'reported explicit integer return metadata')
        first=nodes[function['children'][0]]; pointer=nodes[terminal(first['references']['DW_AT_type']['target'])]
        require(pointer['tag']=='DW_TAG_pointer_type' and 'DW_AT_type' in pointer['references'] and terminal(pointer['references']['DW_AT_type']['target'])==group['shash_alg'],'registration formal points to exact selected shash_alg')
        count=nodes[function['children'][1]]; counted=nodes[terminal(count['references']['DW_AT_type']['target'])]
        require(counted['tag']=='DW_TAG_base_type' and name_of(counted)=='int' and values(counted)==values(returned),'reported count integer matches reported return metadata')
    comparisons=[]; boundaries=[]; absences=[]; active=set(); visits=0
    def pair(a,b,path,context='by_value_member_storage_metadata',depth=0):
        nonlocal visits
        visits+=1; require(visits<=caps['node_pairs'] and depth<=caps['graph_depth'],'bounded finite pair traversal')
        x,y=nodes[a],nodes[b]; require(x['role']=='provider' and y['role']=='core' and x['tag']==y['tag'],'qualified reported type tags match')
        tag=x['tag']; excluded=('DW_AT_declaration',) if tag=='DW_TAG_subprogram' else ()
        require(values(x,excluded)==values(y,excluded),'reported attribute presence/value match, no inferred metadata')
        if x['opaque'] or y['opaque']:
            require(x['opaque'] and y['opaque'] and (a,b) in opaque_pairs and context in opaque_pairs[(a,b)]['allowed_contexts'],'approved opaque stop, no expansion')
            boundaries.append({'path':path,'provider':a,'core':b,'context':context,'reported_metadata':values(x),'internal_layout_status':'unmeasured','transitive_layout_equivalence_proven':False}); return
        if context=='pointer_target_label_metadata' and a in expanded:
            require(any(roots['provider'][name]==a and roots['core'][name]==b for name in ('shash_alg','crypto_alg')),'selected pointee identity token, no general name match')
            comparisons.append({'path':path,'kind':'selected_pointee_reference_only','provider':a,'core':b,'pointed_to_layout_claim':False}); return
        key=(a,b,context); require(key not in active,'unapproved recursive type graph cycle'); active.add(key)
        comparisons.append({'path':path,'tag':tag,'provider':a,'core':b,'reported_attributes':values(x,excluded),'raw_forms':{'provider':{k:v['form'] for k,v in x['attributes'].items()},'core':{k:v['form'] for k,v in y['attributes'].items()}}})
        require(set(x['references'])==set(y['references']),'exact reported reference presence')
        if not x['references'] and tag in ('DW_TAG_pointer_type','DW_TAG_const_type','DW_TAG_subroutine_type'):
            absences.append({'path':path,'tag':tag,'missing':'DW_AT_type','interpretation':'matching reported absence, no invented void/pointee/return type'})
        if x['references']:
            next_context='pointer_target_label_metadata' if tag=='DW_TAG_pointer_type' else context
            pair(x['references']['DW_AT_type']['target'],y['references']['DW_AT_type']['target'],path+'/type',next_context,depth+1)
        require(len(x['children'])==len(y['children']),'reported positional child count matches')
        for index,(left,right) in enumerate(zip(x['children'],y['children'])):
            pair(left,right,path+'/child/'+str(index),context,depth+1)
        active.remove(key)
    for target in ('shash_alg','crypto_alg','crypto_register_shashes'):
        pair(roots['provider'][target],roots['core'][target],target)
    require({(p['provider'],p['core']) for p in boundaries}==set(opaque_pairs),'all approved opaque stopping pairs observed by finite paths')
    require(all('DW_AT_byte_size' not in n['attributes'] for n in nodes.values() if n['tag']=='DW_TAG_pointer_type'),'explicit pointer size remains unreported in this profile')
    require(all('DW_AT_alignment' not in nodes[group['shash_alg']]['attributes'] for group in roots.values()),'shash alignment remains unreported')
    return {'schema':'paired-reported-metadata-relation-v1','reported_direct_metadata_relation':True,'registration_reported_prototype_relation':True,'candidate_identities':roots,'derived_counts':derived,'common_CU_address_size_metadata':cus['provider']['address_size'],'comparisons':comparisons,'opaque_limits':boundaries,'matching_type_attribute_absences':absences,'declaration_markers':{role:values(nodes[group['crypto_register_shashes']]).get('DW_AT_declaration') for role,group in roots.items()},'pointer_byte_size_status':'unreported, not inferred from CU address size','shash_alg_alignment_status':'unreported, not inferred from members or size','input_ELF_DWARF_parses':0,'query_or_old_helper_calls':0,'nonclaims':nonclaims}
