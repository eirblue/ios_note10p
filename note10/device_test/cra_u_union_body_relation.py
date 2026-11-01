"""Finite relation of new parser-observed records; no reader or old graph imports."""
import json


def require(ok, message):
    if not ok:
        raise ValueError(message)


def keys(row, names):
    require(type(row) is dict and set(row) == set(names.split()), 'closed record keys: ' + names)


def integer(value):
    require(type(value) is int and 0 <= value < 2**64, 'unsigned exact integer')
    return value


def coordinate(value):
    require(type(value) is str and len(value) <= 64, 'bounded role coordinate')
    parts = value.split(':')
    require(len(parts) == 2 and all(p.isascii() and p.isdecimal() and str(int(p)) == p for p in parts), 'canonical coordinate')
    return tuple(integer(int(p)) for p in parts)


def relation(control):
    """Recompute new finite closure and pairing; accepted premises are opaque labels."""
    profile = control['finite_profile']
    keys(profile, 'anchors new_nodes direct_child_edges inherited_boundary_pairs inherited_contexts pointer_contexts anchor_premises accepted_raw_counts')
    anchors = profile['anchors']; require(set(anchors) == {'provider', 'core'}, 'two exact anchor roles')
    caps = control['caps']; nodes = {}; children = {}; roles = {'provider': [], 'core': []}
    inherited = {}; premise_ids = set()
    for pair in profile['inherited_boundary_pairs']:
        keys(pair, 'pair_id provider core accepted_RESULT_sha256 accepted_comparison_JSON_pointer accepted_comparison_canonical_sha256 meaning')
        require(type(pair['pair_id']) is str and pair['pair_id'] not in inherited, 'unique inherited premise')
        inherited[pair['pair_id']] = pair
        for role in roles:
            premise_ids.add(pair[role]); coordinate(pair[role])
    require(len(inherited) == 1, 'one narrowly admitted scalar premise')
    roots = {}
    for role, anchor in anchors.items():
        keys(anchor, 'CU_header_inherited CU_offset inherited_member_id inherited_union_id member_name member_start_inherited role union_size_inherited')
        keys(anchor['CU_header_inherited'], 'address_size debug_abbrev_offset unit_length version')
        require(anchor['role'] == role, 'anchor role identity')
        for value in anchor['CU_header_inherited'].values(): integer(value)
        integer(anchor['CU_offset']); integer(anchor['member_start_inherited']); integer(anchor['union_size_inherited'])
        roots[role] = anchor['inherited_union_id']
        require(coordinate(roots[role])[0] == anchor['CU_offset'] and coordinate(anchor['inherited_member_id'])[0] == anchor['CU_offset'], 'inherited anchor CU')
        premise_ids.update((roots[role], anchor['inherited_member_id']))
    require(type(profile['new_nodes']) is list and 0 < len(profile['new_nodes']) <= caps['new_nodes'], 'bounded nonempty new nodes')
    attributes_allowed = {'DW_TAG_member': {'DW_AT_name', 'DW_AT_data_member_location'}, 'DW_TAG_structure_type': {'DW_AT_name', 'DW_AT_byte_size'}, 'DW_TAG_pointer_type': set()}
    for node in profile['new_nodes']:
        keys(node, 'id role tag attributes type_reference complete entry_basis independent_lexical_DIE_boundary_proven')
        role = node['role']; require(role in roles, 'new role')
        ident = node['id']; require(ident not in nodes and ident not in premise_ids, 'unique new ID disjoint from admitted inherited labels')
        cu, offset = coordinate(ident); anchor = anchors[role]
        require(cu == anchor['CU_offset'] and cu < offset < cu + anchor['CU_header_inherited']['unit_length'] + 4, 'new ID in exact role CU')
        require(node['complete'] is True and node['independent_lexical_DIE_boundary_proven'] is False, 'completed observation with honest reference limit')
        require(type(node['entry_basis']) is list and len(node['entry_basis']) == 1 and node['entry_basis'][0] in ('parser_sequential_direct_child', 'parser_interpreted_in_CU_reference'), 'exact observation entry basis')
        tag = node['tag']; require(tag in attributes_allowed, 'supported newly observed tag')
        require(type(node['attributes']) is dict and set(node['attributes']) == attributes_allowed[tag], 'reported attribute set only; width/alignment absent')
        for name, attr in node['attributes'].items():
            keys(attr, 'form value raw_value'); integer(attr['raw_value'])
            if name == 'DW_AT_name':
                require(attr['form'] == 'DW_FORM_strp', 'reported name form')
                keys(attr['value'], 'bytes_hex'); text = attr['value']['bytes_hex']
                require(type(text) is str and 0 < len(text) <= 8192 and len(text) % 2 == 0 and all(c in '0123456789abcdef' for c in text), 'bounded exact emitted name bytes')
            else:
                require(attr['form'] == 'DW_FORM_data1' and integer(attr['value']) == attr['raw_value'] < 256, 'reported numeric form/value')
        ref = node['type_reference']
        if tag == 'DW_TAG_structure_type':
            require(ref is None, 'no invented structure type reference')
        else:
            keys(ref, 'form value raw_value target')
            require(ref['form'] == 'DW_FORM_ref4' and integer(ref['value']) == integer(ref['raw_value']) < 2**32, 'closed emitted reference')
            target_cu, target_offset = coordinate(ref['target'])
            require(target_cu == cu and target_offset == cu + ref['raw_value'] and cu < target_offset < cu + anchor['CU_header_inherited']['unit_length'] + 4, 'role-local reference arithmetic')
        nodes[ident] = node; roles[role].append(ident)
    edges = profile['direct_child_edges']; require(type(edges) is list and len(edges) <= caps['new_edges'], 'finite child edges')
    child_parent = {}; unique_edges = set()
    for edge in edges:
        keys(edge, 'role parent child'); role = edge['role']; require(role in roles, 'edge role')
        parent, child = edge['parent'], edge['child']; require(child in nodes and nodes[child]['role'] == role and nodes[child]['tag'] == 'DW_TAG_member', 'direct child must be NEW member')
        require(parent == roots[role] or parent in nodes and nodes[parent]['role'] == role and nodes[parent]['tag'] == 'DW_TAG_structure_type', 'finite direct parent')
        signature = (role, parent, child); require(signature not in unique_edges and child not in child_parent, 'unique child/parent edge')
        unique_edges.add(signature); child_parent[child] = parent; children.setdefault(parent, []).append(child)
    for role in roles:
        require(children.get(roots[role]), 'incomplete new direct union-body role: ' + role)
    require(set(child_parent) == {i for i, n in nodes.items() if n['tag'] == 'DW_TAG_member'}, 'complete member parent closure')
    scalar_contexts = set(); pointer_contexts = set()
    for row in profile['inherited_contexts']:
        keys(row, 'role parent target context pair_id')
        require(row['role'] in roles and row['pair_id'] in inherited and row['context'] == 'type_inherited_stop', 'admitted inherited context only')
        require(row['target'] == inherited[row['pair_id']][row['role']], 'exact inherited identity, not a name substitute')
        signature = (row['role'], row['parent'], row['target'], row['pair_id'])
        require(signature not in scalar_contexts, 'unique inherited stop context'); scalar_contexts.add(signature)
    for row in profile['pointer_contexts']:
        keys(row, 'id role raw_type_reference boundary'); ident = row['id']
        require(ident in nodes and nodes[ident]['role'] == row['role'] and nodes[ident]['tag'] == 'DW_TAG_pointer_type' and ident not in pointer_contexts, 'exact pointer stop context')
        require(row['raw_type_reference'] == nodes[ident]['type_reference'] and row['boundary'] == 'New pointer tag/raw emitted reference only; width, signature and pointee not observed', 'raw pointer stop only')
        pointer_contexts.add(ident)
    require(pointer_contexts == {i for i,n in nodes.items() if n['tag'] == 'DW_TAG_pointer_type'}, 'complete opaque pointer stops')
    generated_scalar = set(); visited = set(); active = set()
    def close(ident, role, depth):
        require(depth <= caps['relation_depth'], 'finite new graph depth')
        require(ident not in active, 'new by-value cycle')
        if ident in visited: return
        active.add(ident); visited.add(ident)
        node = nodes[ident]; require(node['role'] == role, 'same-role reachability')
        if node['tag'] != 'DW_TAG_pointer_type':
            for child in children.get(ident, []): close(child, role, depth + 1)
            if node['type_reference'] is not None:
                target = node['type_reference']['target']
                if target in nodes: close(target, role, depth + 1)
                else:
                    pairs = [k for k,p in inherited.items() if p[role] == target]
                    require(len(pairs) == 1, 'unresolved by-value target')
                    generated_scalar.add((role, ident, target, pairs[0]))
        active.remove(ident)
    for role in roles:
        for child in children[roots[role]]: close(child, role, 1)
    require(visited == set(nodes) and generated_scalar == scalar_contexts, 'complete new graph and exact inherited context closure')
    pairing = {}; reverse = {}; comparisons = []
    def attrs(node): return {k:{'form':v['form'], 'value':v['value']} for k,v in node['attributes'].items()}
    def member_map(parent):
        result = {}
        for child in children.get(parent, []):
            name = nodes[child]['attributes']['DW_AT_name']['value']['bytes_hex']
            require(name not in result, 'exactly one candidate name within paired parent'); result[name] = child
        return result
    def pair_children(left, right, depth):
        lp, rp = member_map(left), member_map(right); require(set(lp) == set(rp), 'same finite named children')
        for name in sorted(lp): pair(lp[name], rp[name], depth + 1)
    def pair(left, right, depth):
        require(depth <= caps['relation_depth'], 'pair depth cap')
        if left in pairing:
            require(pairing[left] == right, 'role-local sharing topology drift'); return
        require(right not in reverse, 'bijective new pairing')
        a, z = nodes[left], nodes[right]
        require(a['role'] == 'provider' and z['role'] == 'core' and a['tag'] == z['tag'] and attrs(a) == attrs(z), 'new reported tag/form/value relation')
        pairing[left] = right; reverse[right] = left
        comparisons.append({'provider':left,'core':right,'tag':a['tag'],'reported_attributes':attrs(a),'scope':'new parser-observed record only'})
        if a['tag'] == 'DW_TAG_pointer_type':
            require(a['type_reference']['form'] == z['type_reference']['form'], 'pointer raw reference form only')
            return
        pair_children(left, right, depth)
        ar, zr = a['type_reference'], z['type_reference']; require((ar is None) == (zr is None), 'same reference presence')
        if ar is not None:
            require(ar['form'] == zr['form'], 'reported reference forms')
            if ar['target'] in nodes:
                require(zr['target'] in nodes, 'new/inherited context mismatch'); pair(ar['target'], zr['target'], depth + 1)
            else:
                require(any(p['provider'] == ar['target'] and p['core'] == zr['target'] for p in inherited.values()), 'exact accepted inherited pair premise')
    pair_children(roots['provider'], roots['core'], 0)
    require(set(pairing) == set(roles['provider']) and set(reverse) == set(roles['core']), 'all new nodes paired once')
    counts = profile['accepted_raw_counts']
    expected = {'new_nodes_total':len(nodes),'new_nodes_per_role':len(roles['provider']),'new_member_nodes_total':sum(n['tag']=='DW_TAG_member' for n in nodes.values()),'new_structure_nodes_total':sum(n['tag']=='DW_TAG_structure_type' for n in nodes.values()),'new_pointer_nodes_total':len(pointer_contexts),'direct_union_members_each_role':len(children[roots['provider']]),'new_direct_child_edges_total':len(edges),'inherited_contexts_total':len(scalar_contexts),'pointer_contexts_total':len(pointer_contexts),'unsupported_or_unresolved':0,'new_alignment_attributes_reported':0,'old210_intersection':0}
    require(type(counts) is dict and set(counts)==set(expected) and all(type(v) is int for v in counts.values()) and counts==expected and len(roles['provider'])==len(roles['core']) and len(children[roots['provider']])==len(children[roots['core']]), 'recomputed finite counts, not status-marker trust')
    return {'passed':True,'level':'new finite parser-observation-level metadata relation','counts':expected,'comparisons':comparisons,'inherited_premises_used':sorted(inherited),'pointer_stop_count':len(pointer_contexts),'full_old210_disjointness_basis':'accepted raw query label; not remeasured','independent_lexical_DIE_boundary_proven':False,'pointer_width_signature_pointee_alignment_member_extent_proven':False,'whole_layout_ABI_runtime_proven':False,'old_graph_or_query_replayed':False}
