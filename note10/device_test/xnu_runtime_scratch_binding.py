"""Source/config/Image/native/stack/package closure for scratch-only metadata."""
import json
from pathlib import Path
import prepare_xnu_runtime_scratch as p
from prepare_xnu_runtime_observation import sha,safe_path

def package_scope(metadata,allow_build_proof=False):
    if not isinstance(metadata,dict) or type(allow_build_proof) is not bool:raise ValueError('scratch metadata malformed')
    active=metadata.get(p.FLAG,False)
    if type(active) is not bool:raise ValueError('scratch flag must be boolean')
    if not active:
        if any(k.startswith(p.FLAG+'_') for k in metadata):raise ValueError('disabled scratch metadata stray')
        return False
    from xnu_runtime_observation_binding import package_scope as prior_scope
    if not prior_scope(metadata,allow_build_proof=allow_build_proof):raise ValueError('scratch requires planner observation')
    if type(metadata.get(p.FLAG+'_version')) is not int or metadata[p.FLAG+'_version']!=1:raise ValueError('scratch version invalid')
    if metadata.get(p.FLAG+'_geometry_sha256')!=metadata.get('xnu_runtime_observation_geometry_sha256'):raise ValueError('scratch geometry differs')
    allowed={p.FLAG+'_version',p.FLAG+'_geometry_sha256'}
    if allow_build_proof:allowed.update(p.FLAG+'_'+n for n in ('before_sha256','prepared_sha256','sources_sha256','model_sha256','package_sha256','stack_sha256','stack_preflight_sha256','capture_model_sha256','leaf_model_sha256','link_symbols','link_verified'))
    if any(k.startswith(p.FLAG+'_') and k not in allowed for k in metadata):raise ValueError('unknown scratch proof field')
    return True

def metadata_fields(build):
    return {p.FLAG:True,p.FLAG+'_version':1,p.FLAG+'_geometry_sha256':build[p.FLAG+'_geometry_sha256']} if package_scope(build,True) else {}

def validate(root,build,require_package_flow=False):
    root=Path(root);active=package_scope(build,True)
    config=(root/'handoff.config').read_bytes().splitlines();image=(root/'Image').read_bytes()
    options=[line for line in config if p.OPTION.encode() in line]
    if not active:
        if p.MARKER in image or options not in ([],[b'# '+p.OPTION.encode()+b' is not set'],[p.OPTION.encode()+b'=n']):raise ValueError('disabled scratch actual scope differs')
        return False
    if options!=[p.OPTION.encode()+b'=y'] or p.MARKER not in image:raise ValueError('scratch config/Image missing')
    p.validate_delta(root,build)
    if build.get(p.FLAG+'_link_verified') is not True:raise ValueError('scratch linked integration missing')
    linked=build.get(p.FLAG+'_link_symbols',[])
    for name in ('n10_observe_runtime_scratch','n10_scratch_build','n10_scratch_check','n10_scratch_report'):
        if not any(n==name or n.startswith(name+'.') for n in linked):raise ValueError('scratch private symbol missing')
    from xnu_runtime_scratch_stack import validate as validate_stack
    validate_stack(root,build)
    for folder,field in ((p.MODEL,'model_sha256'),(p.PACKAGE,'package_sha256')):
        if folder==p.PACKAGE and not require_package_flow:continue
        raw=safe_path(root,folder+'/result.json').read_bytes();proof=json.loads(raw)
        if sha(raw)!=build.get(p.FLAG+'_'+field) or proof.get('passed') is not True or proof.get('source_sha256')!=p.source_hashes():raise ValueError('scratch actual proof/source binding differs')
        if (proof.get('fixture_only') is not True or proof.get('synthetic_only') is not True or
            proof.get('hardware_verified') is not False or proof.get('physical_memory_or_hardware_accessed') is not False):raise ValueError('scratch hosted proof scope differs')
        if folder==p.MODEL:
            from test_xnu_runtime_scratch import native_source,verify_log,NATIVE_CASES,PARSER_CASES
            if safe_path(root,folder+'/native.c').read_bytes()!=native_source(root/p.PREPARED):raise ValueError('scratch native production source differs')
            for name,digest in proof['files_sha256'].items():
                if sha(safe_path(root,folder+'/'+name).read_bytes())!=digest:raise ValueError('scratch native bytes differ')
            if set(proof['files_sha256']) not in ({'native.c','native','compile.log','native.log'},{'native.c','native.exe','compile.log','native.log'}):raise ValueError('scratch native exact inventory differs')
            if verify_log(safe_path(root,folder+'/native.log').read_text(),build)!=proof.get('native_cases'):raise ValueError('scratch native transcript differs')
            if tuple(proof.get('native_cases',{}))!=NATIVE_CASES or tuple(proof.get('parser_cases',{}))!=PARSER_CASES or not all(proof['parser_cases'].values()):raise ValueError('scratch focused cases differ')
            if proof.get('adapter_cases')!={n:True for n in ('exact','off','duplicate','before-tamper')} or proof.get('actual_production_build_and_wrapper_executed') is not True:raise ValueError('scratch actual adapter/wrapper execution missing')
        else:
            from test_xnu_runtime_scratch_package import CASES
            if tuple(proof.get('cases',{}))!=CASES or not all(proof['cases'].values()):raise ValueError('scratch package cases differ')
    return True
