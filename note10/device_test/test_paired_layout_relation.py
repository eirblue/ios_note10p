"""Thirty-two invented-data finite relation cases; no captured control/proof input."""
import argparse
import json
from pathlib import Path
import tempfile
import hashlib
import os
import stat
import sys

builder=None
relation=None
contract=None

CASES=('layout-reported-direct-roots-positive', 'layout-embedded-base-exact-type-identity-positive', 'layout-registration-reported-prototype-positive', 'layout-callback-qualified-type-graphs-positive', 'layout-opaque-by-value-metadata-limit-positive', 'layout-opaque-pointee-stop-limit-positive', 'layout-missing-shash-alignment-nonclaim-positive', 'layout-missing-pointer-byte-size-nonclaim-positive', 'layout-CU-address-size-drift-reject', 'layout-missing-or-ambiguous-qualified-CU-reject', 'layout-candidate-count-or-complete-identity-reject', 'layout-graph-duplicate-id-or-foreign-role-reject', 'layout-unresolved-or-unreachable-extra-node-reject', 'layout-unapproved-tag-attribute-or-form-reject', 'layout-structure-byte-size-drift-reject', 'layout-direct-member-order-name-or-offset-drift-reject', 'layout-reported-member-alignment-drift-reject', 'layout-base-name-only-or-cross-root-reference-reject', 'layout-base-type-encoding-or-width-drift-reject', 'layout-typedef-or-const-placement-drift-reject', 'layout-array-count-or-element-reference-drift-reject', 'layout-callback-return-reference-presence-drift-reject', 'layout-formal-parameter-type-order-or-arity-drift-reject', 'layout-prototyped-flag-or-variadic-child-drift-reject', 'layout-opaque-boundary-expansion-or-transitive-claim-reject', 'layout-opaque-reported-tag-name-size-alignment-drift-reject', 'layout-declaration-definition-role-not-machine-ownership', 'layout-cycle-depth-node-budget-reject', 'layout-object-query-review-or-debug-slice-crosswire-reject', 'layout-sanitized-control-closed-schema-positive', 'layout-private-address-location-decl-metadata-reject', 'layout-finite-output-nonclaims-no-parser-replay')

# This gate uses only stdlib. No production/private module import precedes it.
_SOURCE_PATHS=('.github/workflows/note10-paired-layout-relation.yml', 'note10/device_test/build_paired_layout_relation.py', 'note10/device_test/paired_layout_input_contract.py', 'note10/device_test/paired_layout_relation.py', 'note10/device_test/paired_layout_relation_control.json', 'note10/device_test/stage_paired_layout_relation.py', 'note10/device_test/test_paired_layout_relation.py', 'note10/private/device-test/v68-paired-layout-relation-20261101/collect_layout_artifact.py', 'note10/private/device-test/v68-paired-layout-relation-20261101/layout_gate.py', 'note10/private/device-test/v68-paired-layout-relation-20261101/test_layout_namespace.py', 'note10/private/device-test/v68-paired-layout-relation-20261101/verify_layout_ci.py')
_IMPORT_NAMES=('build_paired_layout_relation','paired_layout_relation','paired_layout_input_contract','layout_gate','collect_layout_artifact','verify_layout_ci')


def _ensure(ok,message):
    if not ok: raise ValueError(message)


def _signature(st):
    parts=(st.st_dev,st.st_ino,st.st_nlink,st.st_size,st.st_mtime_ns,st.st_ctime_ns)
    _ensure(all(type(v) is int for v in parts),'exact identity integers')
    if os.name=='nt':
        birth=getattr(st,'st_birthtime_ns',None);_ensure(type(birth) is int,'Windows birthtime profile');parts+=(birth,)
    return parts


def _read(path,sha,expected_bytes=None):
    path=Path(path).absolute();_ensure(type(sha) is str and len(sha)==64 and all(ch in '0123456789abcdef' for ch in sha),'exact SHA pin')
    for item in (*reversed(path.parents),path):
        st=item.lstat();_ensure(not stat.S_ISLNK(st.st_mode) and not item.is_symlink() and not getattr(st,'st_file_attributes',0)&1024,'ordinary preflight path')
        if item!=path:_ensure(stat.S_ISDIR(st.st_mode),'ordinary preflight ancestor')
    _ensure(stat.S_ISREG(st.st_mode) and st.st_nlink==1 and st.st_size<=8*1024*1024,'bounded single-link preflight file')
    before=_signature(st)
    with path.open('rb') as stream:
        fd=_signature(os.fstat(stream.fileno()));_ensure(fd[:5]==before[:5] and (fd[6:]==before[6:] if os.name=='nt' else fd[5:]==before[5:]),'compatible preflight APIs')
        raw=stream.read(8*1024*1024+1);endfd=_signature(os.fstat(stream.fileno()))
    _ensure(fd==endfd and before==_signature(path.lstat()) and len(raw)==st.st_size<=8*1024*1024 and hashlib.sha256(raw).hexdigest()==sha,'stable exact preflight snapshot')
    if expected_bytes is not None:_ensure(type(expected_bytes) is int and len(raw)==expected_bytes,'exact source byte count')
    return raw


def _json(raw):
    def pairs(rows):
        value={}
        for key,item in rows:_ensure(key not in value,'duplicate preflight JSON key');value[key]=item
        return value
    def invalid(value):raise ValueError('nonfinite preflight JSON')
    return json.loads(raw.decode('utf8'),object_pairs_hook=pairs,parse_constant=invalid)


def _preflight(args,root,role):
    checkpoint=_json(_read(args.checkpoint,args.checkpoint_sha256));inventory=_json(_read(args.inventory,args.inventory_sha256))
    _ensure(checkpoint['inventory']['sha256']==args.inventory_sha256,'checkpoint binds exact R2 inventory')
    rows=checkpoint['production_sources'];_ensure(type(rows) is dict and set(rows)==set(_SOURCE_PATHS),'complete exact eleven-source map before imports')
    for name,row in rows.items():
        _ensure(type(row) is dict and set(row)=={'bytes','sha256'} and type(row['bytes']) is int and 0<=row['bytes']<=8*1024*1024,'closed typed source hash row');_read(root/name,row['sha256'],row['bytes'])
    _ensure(checkpoint['control']==rows['note10/device_test/paired_layout_relation_control.json'],'fixed control/source pair, hash only')
    _ensure(inventory['public']==checkpoint['inventory']['ordered_public'] and inventory['private']==checkpoint['inventory']['ordered_private'],'frozen ordered identities')
    _ensure(type(inventory['public_count']) is int and inventory['public_count']==32 and type(inventory['private_count']) is int and inventory['private_count']==11 and type(inventory['total']) is int and inventory['total']==43,'exact32+11 unexecuted inventory')
    _ensure(len(inventory['public'])==32 and len(inventory['private'])==11 and len(set(inventory['public']+inventory['private']))==43 and tuple(inventory[role])==CASES,'unique role order and count')
    _ensure(not any(name in sys.modules for name in _IMPORT_NAMES),'no production/private preload before integrity preflight')
    return checkpoint


def _write(path,value):
    raw=(json.dumps(value,sort_keys=True,indent=2,allow_nan=False)+'\n').encode();_ensure(len(raw)<=8*1024*1024,'bounded partial result')
    with Path(path).open('xb') as stream:stream.write(raw)



def attr(name,value):
    form={'DW_AT_name':'DW_FORM_strp','DW_AT_byte_size':'DW_FORM_data1','DW_AT_alignment':'DW_FORM_udata','DW_AT_count':'DW_FORM_data1','DW_AT_data_member_location':'DW_FORM_data1','DW_AT_encoding':'DW_FORM_data1','DW_AT_prototyped':'DW_FORM_flag_present','DW_AT_declaration':'DW_FORM_flag_present','DW_AT_external':'DW_FORM_flag_present'}[name]
    return {'form':form,'value':{'bytes_hex':value.encode().hex()} if name=='DW_AT_name' else value}


def recount(profile):
    ns=profile['nodes']; profile['recorded_counts']={'nodes':len(ns),'expanded_aggregates':sum(n['tag'] in ('DW_TAG_structure_type','DW_TAG_union_type') and not n['opaque'] for n in ns),'opaque_aggregates':sum(n['opaque'] for n in ns),'candidates':len(profile['candidates']),'direct_members':sum(n['tag']=='DW_TAG_member' for n in ns),'pointer_records':sum(n['tag']=='DW_TAG_pointer_type' for n in ns)}


def synthetic():
    nodes=[]; index={}; candidates=[]; cus=[]
    for role,cu in (('provider',111),('core',222)):
        table={}; cursor=31
        def make(key,tag,name=None,fields=None,target=None,children=None,opaque=False):
            nonlocal cursor
            ident=str(cu)+':'+str(cursor); cursor+=11
            attributes={} if fields is None else {k:attr(k,v) for k,v in fields.items()}
            if name is not None: attributes['DW_AT_name']=attr('DW_AT_name',name)
            node={'id':ident,'role':role,'tag':tag,'attributes':attributes,'references':{} if target is None else {'DW_AT_type':{'form':'DW_FORM_ref4','target':target['id']}},'children':[] if children is None else [x['id'] for x in children],'opaque':opaque}; nodes.append(node); table[key]=node; return node
        shash=make('shash','DW_TAG_structure_type','shash_alg',{'DW_AT_byte_size':96})
        crypto=make('crypto','DW_TAG_structure_type','crypto_alg',{'DW_AT_byte_size':48,'DW_AT_alignment':16})
        integer=make('int','DW_TAG_base_type','int',{'DW_AT_byte_size':8,'DW_AT_encoding':5})
        unsigned=make('unsigned','DW_TAG_base_type','unsigned int',{'DW_AT_byte_size':4,'DW_AT_encoding':7})
        char=make('char','DW_TAG_base_type','char',{'DW_AT_byte_size':1,'DW_AT_encoding':8})
        alias=make('alias','DW_TAG_typedef','fixture_word',target=unsigned)
        union=make('union','DW_TAG_union_type',fields={'DW_AT_byte_size':8},opaque=True)
        handle=make('handle','DW_TAG_structure_type','fixture_handle',{'DW_AT_byte_size':16,'DW_AT_alignment':16},opaque=True)
        const=make('const','DW_TAG_const_type',target=handle)
        pointer=make('handleptr','DW_TAG_pointer_type',target=const)
        void=make('voidptr','DW_TAG_pointer_type')
        constvoid=make('constvoid','DW_TAG_const_type')
        constvoidptr=make('constvoidptr','DW_TAG_pointer_type',target=constvoid)
        subrange=make('subrange','DW_TAG_subrange_type',fields={'DW_AT_count':3},target=unsigned)
        array=make('array','DW_TAG_array_type',target=char,children=[subrange])
        fa=make('callback_a','DW_TAG_formal_parameter',target=pointer)
        fb=make('callback_b','DW_TAG_formal_parameter',target=constvoidptr)
        fc=make('callback_c','DW_TAG_formal_parameter',target=void)
        function=make('callback','DW_TAG_subroutine_type',fields={'DW_AT_prototyped':True},target=integer,children=[fa,fb])
        no_return=make('no_return','DW_TAG_subroutine_type',fields={'DW_AT_prototyped':True},children=[fc])
        fptr=make('callbackptr','DW_TAG_pointer_type',target=function)
        vptr=make('releaseptr','DW_TAG_pointer_type',target=no_return)
        update=make('update','DW_TAG_member','update',{'DW_AT_data_member_location':0},target=fptr)
        release=make('release','DW_TAG_member','release',{'DW_AT_data_member_location':12},target=vptr)
        base=make('base','DW_TAG_member','base',{'DW_AT_data_member_location':32,'DW_AT_alignment':16},target=crypto)
        shash['children']=[x['id'] for x in (update,release,base)]
        word=make('word','DW_TAG_member','word',{'DW_AT_data_member_location':0},target=alias)
        scratch=make('scratch','DW_TAG_member','scratch',{'DW_AT_data_member_location':4},target=array)
        slot=make('slot','DW_TAG_member','opaque_slot',{'DW_AT_data_member_location':8},target=union)
        hp=make('hp','DW_TAG_member','handle',{'DW_AT_data_member_location':24},target=pointer)
        crypto['children']=[x['id'] for x in (word,scratch,slot,hp)]
        regptr=make('regptr','DW_TAG_pointer_type',target=shash)
        pa=make('param0','DW_TAG_formal_parameter',target=regptr)
        pb=make('param1','DW_TAG_formal_parameter',target=integer)
        flags={'DW_AT_prototyped':True,'DW_AT_external':True}
        if role=='provider':flags['DW_AT_declaration']=True
        reg=make('registration','DW_TAG_subprogram','crypto_register_shashes',flags,target=integer,children=[pa,pb])
        index[role]=table
        for node in (shash,crypto,reg): candidates.append({'role':role,'target':relation.name_of(node),'node':node['id'],'tag':node['tag']})
        cus.append({'role':role,'CU_offset':cu,'source_label':'crypto/sha256_generic.c' if role=='provider' else 'crypto/shash.c','DWARF_version':4,'address_size':8,'label_attribution':'invented source-label record'})
    raw=b'new synthetic metadata-only bytes.'*6; spans=[]
    for i,name in enumerate(('.debug_info','.rela.debug_info','.debug_abbrev','.debug_str')):
        offset=i*16; data=raw[offset:offset+8];spans.append({'index':i+1,'name':name,'name_offset':0,'type':4 if name.startswith('.rela') else 1,'flags':0,'offset':offset,'size':8,'link':0,'info':0,'alignment':1,'entsize':0,'bytes_sha256':contract.digest(data)})
    pairs=[{'provider':index['provider'][key]['id'],'core':index['core'][key]['id'],'comparison':'invented reported metadata only','allowed_contexts':['by_value_member_storage_metadata','pointer_target_label_metadata']} for key in ('union','handle')]
    profile={'selected_CUs':cus,'nodes':nodes,'candidates':candidates,'opaque_pair_allowlist':pairs,'object_debug_slices':spans,'recorded_counts':{}}; recount(profile)
    text_keys=('arrays','base_binding','complete_candidate_rule','declaration_role','graph_safety','opaque_scope','pointer_scope','prototypes','recorded_count_markers','top_structures','typedef_const_scope')
    policy={k:'invented policy text' for k in text_keys};policy.update(attribute_allowlist_by_tag=contract.ATTRS,attribute_form_allowlist=contract.FORMS,selected_children_by_tag=contract.CHILDREN,reference_allowlist=['DW_AT_type'],expanded_targets=['shash_alg','crypto_alg'],registration_name='crypto_register_shashes',registration_formal_count=2)
    nonclaims={k:0 if k=='physical_BOOT_reboot' else False for k in contract.NONCLAIMS}
    object_row={'member':'v67-ci-pair/invented.o','bytes':len(raw),'sha256':contract.digest(raw)};producer={'member':'v67-ci-pair/invented-result.json','bytes':2,'sha256':contract.digest(b'{}')};members={x['member']:{k:x[k] for k in ('bytes','sha256')} for x in (object_row,producer)}
    accepted={'profile':'accepted-v67-paired-object-whole-ZIP-v1','repository':'fixture/project','source_commit':'a'*40,'run_id':101,'run_attempt':1,'workflow_id':103,'job_id':107,'artifact_id':109,'artifact_name':'note10-provider-core-pair-pc-only','ZIP':{'bytes':11,'sha256':contract.digest(b'inventedZIP'),'namespace':'v67-ci-pair','ordinary_members':2,'ordinary_expanded_bytes':len(raw)+2},'complete_member_map':members,'object':object_row,'producer_result':producer,'accepted_private_result_sha256':contract.digest(b'invented parent result'),'accepted_reader_sha256':contract.digest(b'invented parent reader'),'accepted_review_sha256':contract.digest(b'invented review'),'accepted_collector_sha256':contract.digest(b'invented collector'),'required_original_steps':list(contract.ORIGINAL_STEPS)}
    measurement={'raw_query_result_sha256':contract.digest(b'invented raw records'),'raw_query_checkpoint_sha256':contract.digest(b'invented checkpoint'),'raw_query_sources':{k:{'bytes':len(k),'sha256':contract.digest(k.encode())} for k in ('query','loader')},'raw_query_review_sha256':contract.digest(b'invented raw review'),'opaque_boundary_addendum_sha256':contract.digest(b'invented boundary review'),'scope':'invented metadata-only label'}
    control={'schema':'paired-layout-relation-control-v1','accepted_v67':accepted,'measurement_attribution':measurement,'finite_profile':profile,'relation_policy':policy,'caps':dict(contract.CAPS),'nonclaims':nonclaims}
    return control,index,raw


def reject(call):
    try:call()
    except (ValueError,KeyError,IndexError):return
    raise AssertionError('expected finite-contract rejection')


def run_case(name):
    control,idx,raw=synthetic();p=control['finite_profile'];core=idx['core'];provider=idx['provider'];i=CASES.index(name)
    proof=lambda:relation.compare(p,control['relation_policy'],control['caps'],control['nonclaims'])
    if i in tuple(range(8))+(26,29,31):
        if i==29:contract.validate_control(control)
        result=proof();contract.require(result['reported_direct_metadata_relation'] is True,'finite positive relation')
        if i==1:contract.require(result['candidate_identities']['provider']['crypto_alg']==provider['crypto']['id'],'exact selected embedded identity')
        if i==2:contract.require(result['registration_reported_prototype_relation'] is True,'reported registration shape')
        if i==3:contract.require(any(x.get('tag')=='DW_TAG_const_type' for x in result['comparisons']),'qualified callback metadata')
        if i in (4,5):contract.require(any(x['context']==('by_value_member_storage_metadata' if i==4 else 'pointer_target_label_metadata') and x['transitive_layout_equivalence_proven'] is False for x in result['opaque_limits']),'explicit approved opaque limit')
        if i==6:contract.require(result['shash_alg_alignment_status'].startswith('unreported'),'no inferred struct alignment')
        if i==7:contract.require(result['pointer_byte_size_status'].startswith('unreported') and result['common_CU_address_size_metadata']==8,'address metadata not pointer width')
        if i==26:contract.require(result['declaration_markers']=={'provider':True,'core':None} and not result['nonclaims']['machine_code_DIE_ownership_proven'],'declaration asymmetry, no machine ownership')
        if i==31:contract.require(result['input_ELF_DWARF_parses']==result['query_or_old_helper_calls']==0 and all(v is False for k,v in result['nonclaims'].items() if k!='physical_BOOT_reboot'),'new-only finite nonclaims')
        return
    if i==8:p['selected_CUs'][1]['address_size']=16
    elif i==9:p['selected_CUs'][1]=dict(p['selected_CUs'][0])
    elif i==10:p['candidates'].append(dict(p['candidates'][0]))
    elif i==11:p['nodes'].append(dict(p['nodes'][0]));recount(p)
    elif i==12:core['word']['references']['DW_AT_type']['target']='222:999999'
    elif i==13:core['int']['attributes']['DW_AT_low_pc']={'form':'DW_FORM_addr','value':7}
    elif i==14:core['shash']['attributes']['DW_AT_byte_size']['value']+=16
    elif i==15:core['update']['attributes']['DW_AT_data_member_location']['value']+=1
    elif i==16:core['base']['attributes']['DW_AT_alignment']['value']=32
    elif i==17:core['base']['references']['DW_AT_type']['target']=core['handle']['id']
    elif i==18:core['int']['attributes']['DW_AT_encoding']['value']=7
    elif i==19:core['alias']['attributes']['DW_AT_name']=attr('DW_AT_name','different_word')
    elif i==20:core['subrange']['attributes']['DW_AT_count']['value']=4
    elif i==21:core['no_return']['references']['DW_AT_type']={'form':'DW_FORM_ref4','target':core['int']['id']}
    elif i==22:core['registration']['children'].reverse()
    elif i==23:core['callback']['attributes'].pop('DW_AT_prototyped')
    elif i==24:core['union']['children']=[core['word']['id']]
    elif i==25:core['handle']['attributes']['DW_AT_byte_size']['value']=24
    elif i==27:core['alias']['references']['DW_AT_type']['target']=core['alias']['id']
    elif i==28:
        reject(lambda:contract.bind_object(control,b'?'+raw[1:]));control['finite_profile']['object_debug_slices'][0]['bytes_sha256']=contract.digest(b'other invented slice');reject(lambda:contract.bind_object(control,raw))
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'synthetic-control.json';snap=contract.write_json(path,control);saved=contract.CONTROL
            try:contract.CONTROL=path;reject(lambda:contract.load_control(contract.digest(b'wrong expected control')))
            finally:contract.CONTROL=saved
        return
    elif i==30:control['full_private_query']={};reject(lambda:contract.validate_control(control));return
    else:raise AssertionError('unassigned new finite case')
    reject(proof)


def main():
    global builder,relation,contract
    parser=argparse.ArgumentParser()
    for name in ('checkpoint','checkpoint-sha256','inventory','inventory-sha256','output'):parser.add_argument('--'+name,required=True)
    a=parser.parse_args();_ensure(not Path(a.output).exists(),'fresh exclusive partial result');done=[];current=None;receipt={'role':'public','checkpoint_sha256':a.checkpoint_sha256,'inventory_sha256':a.inventory_sha256}
    try:
        root=Path(__file__).absolute().parents[2];_preflight(a,root,'public')
        import paired_layout_input_contract as loaded_contract
        import paired_layout_relation as loaded_relation
        import build_paired_layout_relation as loaded_builder
        contract=loaded_contract;relation=loaded_relation;builder=loaded_builder
        for module,path in ((contract,'note10/device_test/paired_layout_input_contract.py'),(relation,'note10/device_test/paired_layout_relation.py'),(builder,'note10/device_test/build_paired_layout_relation.py')):_ensure(Path(module.__file__).absolute()==root/path,'imported only exact preflighted source path')
        for current in CASES:run_case(current);done.append(current)
        _write(a.output,dict(receipt,passed=True,completed=done,completed_count=len(done),next_case=None))
    except Exception as exc:
        _write(a.output,dict(receipt,passed=False,completed=done,completed_count=len(done),next_case=current,exception={'type':type(exc).__name__,'message':str(exc)}));raise


if __name__=='__main__':main()
