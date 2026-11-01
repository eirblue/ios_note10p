"""New output-only finite pair projection; accepted inputs remain frozen data."""
import hashlib
import importlib.util
from pathlib import Path

HELPER_SHA = '881c01a5ff6e00d91337c2190a516da094e28f186f36bfc996f68b651a382de2'


def require(ok, message):
    if not ok:
        raise ValueError(message)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def parse_output(raw):
    """Only the fresh linked output enters the generic ELF parser."""
    path=Path(__file__).with_name('crypto_hash_composite.py')
    def identity(st): return (st.st_dev,st.st_ino,st.st_nlink,st.st_size,st.st_mtime_ns,st.st_ctime_ns,getattr(st,'st_birthtime_ns',None))
    before=path.stat(); require(path.is_file() and not path.is_symlink() and before.st_nlink==1 and not getattr(before,'st_file_attributes',0)&1024 and before.st_size<=1024*1024, 'bounded pinned helper source')
    with path.open('rb') as stream: source=stream.read(1024*1024+1)
    require(len(source)==before.st_size and identity(path.stat())==identity(before) and digest(source)==HELPER_SHA, 'immutable helper before import')
    spec=importlib.util.spec_from_file_location('_pair_generic_parser',path)
    module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    require(identity(path.stat())==identity(before), 'helper unchanged through import')
    return module.parse_object(raw)


def attributes(symbol):
    return {k:symbol[k] for k in ('name','info','other','value','size')}


def prove(profile, input_buffers, output):
    """No accepted input ELF parsing or historical semantic calls."""
    require(set(input_buffers)=={'provider','core'}, 'exact two byte inputs')
    for role,raw in input_buffers.items():
        record=profile['object_records'][role]
        require(type(raw) is bytes and len(raw)==record['bytes'] and digest(raw)==record['sha256'], 'whole accepted input bytes')
    sections=output['sections']; symbols=output['symbols']; mapping={}; span_rows=[]
    spans=profile['selected_direct_spans']; require(len(spans)==10 and len({x['section']['name'] for x in spans})==10, 'ten uniquely named finite spans')
    for row in spans:
        source=row['section']; role=row['role']; raw=input_buffers[role]
        require(row['object_sha256']==profile['object_records'][role]['sha256'] and row['all_same_name_contributions']==[dict(source,role=role,object_sha256=row['object_sha256'])], 'reviewed unique qualified owner')
        require(source['type']==1 and not source['flags']&(16|32|512) and 0<=source['offset']<source['offset']+source['size']<=len(raw), 'unmerged bounded source slice')
        data=raw[source['offset']:source['offset']+source['size']]
        require(digest(data)==row['section_bytes_sha256'], 'same-buffer source slice SHA')
        matches=[s for s in sections if s['name']==source['name']]
        require(len(matches)==1, 'unique output full-span owner')
        target=matches[0]
        require(all(target[k]==source[k] for k in ('type','flags','size','alignment','entsize','link','info')) and target['bytes']==data, 'exact selected/direct complete span bytes/metadata')
        key=(role,source['index']); require(key not in mapping, 'no duplicate source span')
        mapping[key]=target['index']; span_rows.append({'role':role,'input_section':source,'output_section':{k:v for k,v in target.items() if k!='bytes'},'bytes_sha256':digest(data)})
    def definition(role, raw):
        require((role,raw['section']) in mapping, 'definition inside finite owner')
        target=mapping[(role,raw['section'])]
        found=[s for s in symbols if s['section']==target and attributes(s)==attributes(raw)]
        require(len(found)==1 and raw['info']>>4 in (0,1) and raw['info']&15 in (1,2), 'unique original typed definition/coordinate')
        if raw['info']>>4==1:
            same=[s for s in symbols if s['name']==raw['name']]
            require(same==found, 'one strong named output, no undefined/weak/cross-owner duplicate')
        return found[0]
    definitions=[]
    for row in profile['selected_complete_RELA']:
        require(row['raw_symbol']==row['accepted_label'] and row['full_section_extent'] is True, 'historical selected label')
        result=definition(row['role'],row['raw_symbol']); definitions.append({'role':row['role'],'input':row['raw_symbol'],'output':result})
    for row in profile['direct_named_definition_candidates']:
        require(len(row['definitions'])==1, 'unique input strong candidate')
        candidate=row['definitions'][0]; require(candidate['eligible_strong_normal_definition'] is True and candidate['raw_symbol']['info']==18 and candidate['object_sha256']==profile['object_records'][candidate['role']]['sha256'], 'qualified strong candidate')
        result=definition(candidate['role'],candidate['raw_symbol']); definitions.append({'role':candidate['role'],'input':candidate['raw_symbol'],'output':result})
    for row in profile['relocation_destinations_and_allowed_forms']:
        for witness in row.get('coordinate_definition_candidates',[]):
            result=definition(row['destination_role'],witness); definitions.append({'role':row['destination_role'],'input':witness,'output':result})
    selected=[]
    for group in profile['selected_complete_RELA']:
        origin=group['role']; target=mapping[(origin,group['raw_symbol']['section'])]
        actual=[x for x in output['relocations'] if x['section']==target]
        old=group['raw_complete_section_RELA']
        require(len(actual)==len(old) and len({x['offset'] for x in actual})==len(actual), 'complete selected RELA cardinality')
        by_place={x['offset']:x for x in actual}; ranges=[]
        for previous in old:
            require(previous['offset'] in by_place, 'exact relocation place')
            current=by_place[previous['offset']]; typ=previous['type']; widths=profile['selected_RELA_width_bytes']
            require(str(typ) in widths and current['type']==typ, 'observed relocation kind only')
            width=widths[str(typ)]; ranges.append((current['offset'],current['offset']+width))
            require(current['offset']%width==0 and current['offset']+width<=sections[target]['size'], 'whole aligned field')
            refs=[x for x in profile['relocation_destinations_and_allowed_forms'] if x['origin_role']==origin and x['selected_purpose']==group['purpose'] and x['relocation']==previous]
            require(len(refs)==1, 'one exact frozen typed destination')
            ref=refs[0]; raw=ref['raw_target_symbol']; new=symbols[current['symbol']]
            destination=[x for x in spans if x['role']==ref['destination_role'] and x['section']['name']==ref['destination_section_name']]
            require(len(destination)==1, 'one destination owner')
            dest_index=mapping[(ref['destination_role'],destination[0]['section']['index'])]
            require(new['section']==dest_index and new['value']+current['addend']==ref['destination_coordinate'] and 0<=ref['destination_coordinate']<sections[dest_index]['size'], 'exact qualified destination coordinate')
            forms=ref['allowed_output_forms']
            canonical=new['name']=='' and new['info']==3 and new['other']==0 and new['value']==new['size']==0
            if raw['section']==0:
                required=ref['required_definition']; mapped=definition(ref['destination_role'],required)
                require(forms==['named_defined_registration_target_only'] and group['purpose']=='init' and typ==283 and raw['name']==required['name']=='crypto_register_shashes' and raw['info']==16 and raw['other']==raw['value']==raw['size']==0 and required['info']==18 and new==mapped and current['addend']==previous['addend']==0, 'only contextual registration NOTYPE-to-defined-FUNC edge')
            elif raw['info']==3:
                require(forms==['anonymous_local_section_symbol_only'] and canonical and current['addend']==previous['addend'], 'canonical anonymous section target only')
            elif canonical:
                require('anonymous_local_section_symbol_with_exact_coordinate_rebase' in forms and current['addend']==raw['value']+previous['addend'], 'only listed exact section-symbol rebase')
                definition(origin,raw)
            else:
                require('same_named_definition' in forms and attributes(new)==attributes(raw) and current['addend']==previous['addend'], 'unchanged named defined target')
                definition(origin,raw)
            selected.append({'origin_role':origin,'purpose':group['purpose'],'input_relocation':previous,'output_relocation':current,'output_target':new,'destination_role':ref['destination_role'],'destination_section':dest_index,'destination_coordinate':ref['destination_coordinate']})
        ranges.sort(); require(all(a[1]<=b[0] for a,b in zip(ranges,ranges[1:])), 'no overlapping selected fields')
    require(len(selected)==profile['selected_RELA_count']==13, 'all13 selected typed rows')
    return {'schema':'provider-core-pair-projection-v1','output_sha256':output['sha256'],'output_bytes':output['bytes'],'finite_spans':span_rows,'definitions':definitions,'selected_RELA':selected,'output_sections':[{**{k:v for k,v in s.items() if k!='bytes'},'bytes_sha256':digest(s['bytes'])} for s in sections],'output_symbols':symbols,'unresolved_raw':[s for s in symbols if s['section']==0],'output_relocations_raw':output['relocations'],'global_input_same_name_groups_outside_claim':profile['global_same_name_group_count'],'input_ELF_parses':0,'old_query_or_semantic_calls':0,'direct_only_outgoing_RELA_proven':False,'registration_execution_proven':False,'binary_ABI_proven':False}
