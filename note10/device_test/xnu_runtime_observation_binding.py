"""Actual planner-only source/config/Image/proof closure; no old model replay."""
import json
import re
from pathlib import Path
from prepare_xnu_runtime_observation import (FLAG,VERSION,OPTION,MARKER,BASE,PREPARED,
 MODEL,PACKAGE,SOURCES,REUSE,RESERVE,KCONFIG,INCLUDE,CALL,BLOCK,ROOT,HERE,sha,full_body,safe_path,geometry,validate_providers,PROVIDERS)


def package_scope(metadata,allow_build_proof=False):
    if not isinstance(metadata,dict) or type(allow_build_proof) is not bool:raise ValueError('planner metadata/options malformed')
    flag=metadata.get(FLAG,False)
    if type(flag) is not bool:raise ValueError('planner flag must be bool')
    if not flag:
        if metadata.get(VERSION) is not None or any(k.startswith(FLAG+'_') and k!=VERSION for k in metadata):raise ValueError('disabled planner metadata is stray')
        return False
    from cpu_pm_roundtrip_binding import trace_package_scope
    if not trace_package_scope(metadata,allow_build_proof=allow_build_proof):raise ValueError('planner requires complete trace/count/pair chain')
    if type(metadata.get(VERSION)) is not int or metadata[VERSION]!=1:raise ValueError('planner version malformed')
    if metadata.get('auto_return_diagnostic') is not True or metadata.get('xnu_payload_stage_diagnostic') is not True:
        raise ValueError('planner requires preserved stage and recovery')
    geometry_digest=metadata.get(FLAG+'_geometry_sha256')
    if not isinstance(geometry_digest,str) or re.fullmatch('[0-9a-f]{64}',geometry_digest) is None:raise ValueError('planner geometry digest missing')
    allowed={VERSION,FLAG+'_geometry_sha256'}
    if allow_build_proof:allowed.update(FLAG+'_'+n for n in ('before_sha256','prepared_sha256','sources_sha256',
       'manifest_canonical_sha256','manifest_raw_sha256','model_sha256','package_sha256','link_symbols','link_verified'))
    if any(k.startswith(FLAG+'_') and k not in allowed for k in metadata):raise ValueError('unknown planner proof metadata')
    return True


def metadata_fields(build,enabled=None):
    active=package_scope(build,allow_build_proof=True)
    if enabled is not None:
        if type(enabled) is not bool:raise ValueError('planner package role malformed')
        active=active and enabled
    return {FLAG:True,VERSION:1,FLAG+'_geometry_sha256':build[FLAG+'_geometry_sha256']} if active else {}


def validate(root,build,require_package_flow=False):
    root=Path(root);enabled=package_scope(build,allow_build_proof=True)
    config=(root/'handoff.config').read_bytes().splitlines();lines=[line for line in config if OPTION.encode() in line]
    image=(root/'Image').read_bytes()
    if not enabled:
        if lines not in ([],[b'# '+OPTION.encode()+b' is not set'],[OPTION.encode()+b'=n']) or MARKER in image:
            raise ValueError('disabled planner config/Image scope differs')
        return False
    if lines!=[OPTION.encode()+b'=y'] or MARKER not in image:raise ValueError('planner actual config/Image scope differs')
    if build.get(FLAG+'_link_verified') is not True:raise ValueError('planner actual compiled symbol closure missing')
    linked=build.get(FLAG+'_link_symbols')
    if (not isinstance(linked,list) or any(not isinstance(name,str) for name in linked) or len(linked)!=len(set(linked)) or
        'n10_rt_plan' not in linked or not any(name.startswith('n10_observe_runtime_plan') for name in linked)):
        raise ValueError('planner actual linked symbol inventory differs')
    before=build.get(FLAG+'_before_sha256');after=build.get(FLAG+'_prepared_sha256')
    if not isinstance(before,dict) or not isinstance(after,dict) or not set(before)<=set(after):raise ValueError('planner before/final source map malformed')
    maps=[]
    for folder,mapping in ((BASE,before),(PREPARED,after)):
        actual={}
        for name,digest in mapping.items():
            path=safe_path(root/folder,name)
            if path.is_symlink() or not path.is_file() or not path.resolve().is_relative_to((root/folder).resolve()):raise ValueError('planner prepared source missing/unsafe')
            raw=path.read_bytes()
            if sha(raw)!=digest:raise ValueError('planner prepared source digest differs')
            actual[name]=raw
        maps.append(actual)
    prior,final=maps
    from prepare_xnu_runtime_plan import validate_manifest,geometry_header
    manifest=validate_manifest(HERE/'xnu_runtime_plan_payload.json');geom,companion=geometry(manifest)
    expected_added={'arch/arm64/mm/runtime_relocation.c':(ROOT/'note10/xnu26/runtime_relocation.c').read_bytes(),
      'arch/arm64/mm/runtime_relocation.h':(ROOT/'note10/xnu26/runtime_relocation.h').read_bytes(),
      'arch/arm64/mm/note10_xnu_runtime_plan.c':(HERE/'xnu_runtime_plan.c').read_bytes(),
      'arch/arm64/mm/note10_xnu_runtime_observation.c':(HERE/'xnu_runtime_observation.c').read_bytes(),
      'arch/arm64/mm/note10_xnu_runtime_geometry.h':geom,'arch/arm64/mm/note10_xnu_observation_geometry.h':companion}
    providers={'arch/arm64/mm/note10_xnu_payload_stage.c','arch/arm64/mm/note10_xnu_payload_stage.h',
      'arch/arm64/mm/note10_cpu_cache_roundtrip.c','arch/arm64/mm/note10_auto_return.c','arch/arm64/mm/note10_pm_timer_roundtrip.c',
      'arch/arm64/mm/note10_xnu_window_access.c','arch/arm64/mm/note10_window_access_core.h'}
    if set(prior)!={RESERVE,KCONFIG,'arch/arm64/mm/init.c'}|providers or set(final)!=set(prior)|set(expected_added):
        raise ValueError('planner exact before/final source inventory differs')
    if any(final[name]!=raw for name,raw in expected_added.items()) or build.get(FLAG+'_geometry_sha256')!=sha(geom):
        raise ValueError('planner copied production source/geometry differs')
    if (final[RESERVE].count(INCLUDE)!=1 or final[RESERVE].count(CALL)!=1 or
        final[RESERVE].replace(INCLUDE,b'',1).replace(CALL,b'',1)!=prior[RESERVE] or
        final[KCONFIG].removesuffix(BLOCK)!=prior[KCONFIG]):raise ValueError('planner source delta affects preserved diagnostic')
    identity=build.get('reservation_evidence_id','')
    if (not isinstance(identity,str) or re.fullmatch('[0-9a-f]{32}',identity) is None or
        prior[RESERVE]!=b'#define N10_RESERVE_BUILD_ID "'+identity.encode()+b'"\n'+full_body()):raise ValueError('planner baseline full guards differ')
    validate_providers({name:prior[name] for name in PROVIDERS},build,manifest)
    for name in set(before)-{RESERVE,KCONFIG}:
        if prior[name]!=final[name]:raise ValueError('planner mutated preserved provider')
    if build.get('xnu_runtime_scratch') is True:
        from prepare_xnu_runtime_scratch import validate_delta
        validate_delta(root,build)
    current={name:sha((HERE/name).read_bytes()) for name in SOURCES}
    if build.get(FLAG+'_sources_sha256')!=current:raise ValueError('planner production source closure differs')
    for name,digest in REUSE.items():
        if sha((ROOT/name).read_bytes())!=digest:raise ValueError('reused immutable planner source differs')
    for folder,field in ((MODEL,'model_sha256'),(PACKAGE,'package_sha256')):
        if folder==PACKAGE and not require_package_flow:continue
        path=safe_path(root/folder,'result.json');raw=path.read_bytes();proof=json.loads(raw)
        if not isinstance(proof,dict) or build.get(FLAG+'_'+field)!=sha(raw) or proof.get('passed') is not True or proof.get('source_sha256')!=current:
            raise ValueError('planner focused actual proof/source digest differs')
        if folder==MODEL:
            from test_xnu_runtime_observation import native_source,NATIVE_CASES,PARSER_CASES,PREPARER_CASES,verify_native_log
            if any(not isinstance(proof.get(key),dict) for key in ('native_cases','parser_cases','preparer_cases','compiled_files_sha256')):
                raise ValueError('planner focused proof case maps malformed')
            if ((root/folder/'native.c').read_bytes()!=native_source(root/PREPARED) or
                tuple(proof.get('native_cases',{}))!=NATIVE_CASES or
                tuple(proof.get('parser_cases',{}))!=PARSER_CASES or
                tuple(proof.get('preparer_cases',{}))!=PREPARER_CASES or
                not all(value is True for key in ('native_cases','parser_cases','preparer_cases') for value in proof[key].values()) or
                proof.get('actual_production_planner_and_companion_executed') is not True):
                raise ValueError('planner native actual source/case closure differs')
            for name,digest in proof.get('compiled_files_sha256',{}).items():
                actual=safe_path(root/folder,name)
                if (not isinstance(name,str) or Path(name).is_absolute() or '..' in Path(name).parts or actual.is_symlink() or
                    not actual.is_file() or sha(actual.read_bytes())!=digest):raise ValueError('planner native compiled/source/log bytes differ')
            observed,_valid=verify_native_log((root/folder/'native.log').read_bytes(),build)
            if observed!=proof['native_cases']:raise ValueError('planner actual native transcript differs')
            inventory=set(proof.get('compiled_files_sha256',{}))
            if inventory not in ({'native.c','native','compile.log','native.log'},{'native.c','native.exe','compile.log','native.log'}):
                raise ValueError('planner native compiled proof inventory differs')
            candidates=[root/folder/name for name in ('native','native.exe')]
            if any(path.is_symlink() or (path.exists() and not path.is_file()) for path in candidates) or sum(path.is_file() for path in candidates)!=1:
                raise ValueError('planner native executable missing/unsafe/ambiguous')
        else:
            from test_xnu_runtime_observation_package import CASES
            if tuple(proof.get('cases',{}))!=CASES or not all(value is True for value in proof['cases'].values()):raise ValueError('planner package focused case inventory differs')
    return True
