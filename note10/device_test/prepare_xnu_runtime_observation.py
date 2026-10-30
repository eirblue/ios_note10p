"""Separate full diagnostic adapter; canonical v55 preparation is unchanged."""
import hashlib
from pathlib import Path
import re
import shutil
import prepare_xnu_runtime_plan as canonical

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
FLAG='xnu_runtime_observation'
VERSION=FLAG+'_version'
OPTION='CONFIG_NOTE10_XNU_RUNTIME_OBSERVATION'
MARKER=b'N10XPO1'
BASE='xnu-runtime-observation-before'
PREPARED='xnu-runtime-observation-prepared'
MODEL='xnu-runtime-observation-model'
PACKAGE='xnu-runtime-observation-package-model'
# Accepted v53 final composition, distinct from the original timer provider.
FINAL_TIMER_SHA='164aa5bed9eb6bf4692789e46e0cb59653a82156fb0e1bcab8b30ce7f3980763'
RESERVE=canonical.RESERVE
KCONFIG='arch/arm64/Kconfig'
SOURCES=('prepare_xnu_runtime_observation.py','xnu_runtime_observation.c',
 'decode_xnu_runtime_observation.py','xnu_runtime_observation_binding.py',
 'test_xnu_runtime_observation.py','test_xnu_runtime_observation_package.py')
REUSE={
 'note10/xnu26/runtime_relocation.c':'dc51d22fce4c8e0d566d6158f53aa3d512a65954541e4ea4201c5878cb17e448',
 'note10/xnu26/runtime_relocation.h':'2956336fbec371636acb62a4fc51aae451e74a65bdf4595b12e80c3be8ca9037',
 'note10/device_test/xnu_runtime_plan.c':'82009f2f6355726556a83fe4040ca117557ae5d2c8456290ae72753d6c42fd7e',
 'note10/device_test/prepare_reservation_kernel.py':'c5903dabc15bd2ab5bd676849112c0413d84cd434b8bcadebf876e507aa086dc',
 'note10/device_test/prepare_xnu_runtime_plan.py':'6b9b21ab93f3b49ef43e947a26ad1985d2f11bbd94002e30fcf6dcca875ac41c'}
BLOCK=b'\nconfig NOTE10_XNU_RUNTIME_OBSERVATION\n\tbool "Hypothetical XNU runtime plan observation only"\n\tdepends on NOTE10_CPU_PM_NOTIFIER_TRACE\n\tdefault n\n'
INCLUDE=b'#ifdef CONFIG_NOTE10_XNU_RUNTIME_OBSERVATION\n#include "runtime_relocation.c"\n#include "note10_xnu_runtime_plan.c"\n#include "note10_xnu_runtime_observation.c"\n#endif\n\n'
CALL=b'#ifdef CONFIG_NOTE10_XNU_RUNTIME_OBSERVATION\n    n10_observe_runtime_plan(reserved,count,invalid);\n#endif\n\n'


def sha(raw):return hashlib.sha256(raw).hexdigest()


def safe_path(root,name,exists=True):
    if not isinstance(name,str):raise ValueError('artifact relative path must be text')
    relative=Path(name);root=Path(root)
    if relative.is_absolute() or relative.as_posix()!=name or not relative.parts or '..' in relative.parts or root.is_symlink():
        raise ValueError('unsafe artifact relative path')
    path=root
    for part in relative.parts:
        path=path/part
        if path.is_symlink():raise ValueError('symlink in artifact path')
    if not path.resolve().is_relative_to(root.resolve()) or (exists and not path.is_file()):
        raise ValueError('artifact path missing or escaped root')
    return path


def full_body():
    """Exact old full reservation composition, no old preparer/callback run."""
    raw=canonical.reservation_body();once=canonical.once
    raw=once(raw,b'static int __init note10_check_xnu_window(void)',
        b'#include "note10_xnu_window_access.c"\n\nstatic int __init note10_check_xnu_window(void)')
    raw=once(raw,b'    /* Reserved pages remain excluded from Linux',
        b'    note10_test_xnu_window_access(reserved, count, invalid);\n\n    /* Reserved pages remain excluded from Linux')
    raw=raw.replace(b'Reservation diagnostic only: does not write the window or execute XNU.',b'Reservation and opt-in cached RAM access test; never executes XNU.')
    raw=once(raw,b'    /* Reserved pages remain excluded from Linux',
        b'    n10_stage_xnu_payload(reserved, count, invalid);\n    /* Reserved pages remain excluded from Linux')
    raw=once(raw,b'#include "note10_xnu_window_access.c"\n',b'#include "note10_xnu_window_access.c"\n#include "note10_xnu_payload_stage.c"\n#include "note10_cpu_cache_roundtrip.c"\n#include "note10_auto_return.c"\n#include "note10_pm_timer_roundtrip.c"\n')
    raw=once(raw,b'    note10_test_xnu_window_access(reserved, count, invalid);\n',b'    if (note10_test_xnu_window_access(reserved, count, invalid))\n        return 0;\n')
    raw=once(raw,b'    n10_stage_xnu_payload(reserved, count, invalid);\n',b'    if (n10_stage_xnu_payload(reserved, count, invalid))\n        return 0;\n    if (n10_test_cpu_cache())\n        return 0;\n    n10_start_pm_timer();\n')
    local=b'    unsigned long start, count, i, reserved = 0, invalid = 0;\n'
    return once(raw,local,local+b'\n    if (n10_arm_auto_return())\n        return 0;\n')


def files(root,names):return {name:canonical.file(root,name).read_bytes() for name in names}


def geometry(manifest):
    header=canonical.geometry_header(manifest)
    companion=('#define N10_OBS_PAYLOAD_SHA "'+manifest['payload_sha256']+'"\n'+
        '#define N10_OBS_PAYLOAD_SIZE '+str(manifest['payload_size'])+'U\n'+
        '#define N10_OBS_GEOMETRY_SHA "'+sha(header)+'"\n').encode()
    return header,companion


PROVIDERS=('arch/arm64/mm/note10_xnu_payload_stage.c','arch/arm64/mm/note10_xnu_payload_stage.h',
       'arch/arm64/mm/note10_cpu_cache_roundtrip.c','arch/arm64/mm/note10_auto_return.c','arch/arm64/mm/note10_pm_timer_roundtrip.c',
       'arch/arm64/mm/note10_xnu_window_access.c','arch/arm64/mm/note10_window_access_core.h')


def validate_providers(providers,report,manifest):
    provider_names=PROVIDERS
    if set(providers)!=set(PROVIDERS):raise ValueError('exact original provider inventory missing')
    if (providers[provider_names[0]]!=(HERE/'xnu_payload_stage.c').read_bytes() or
        sha(providers[provider_names[0]])!=report.get('xnu_payload_stage_sources_sha256') or
        providers[provider_names[2]]!=(HERE/'cpu_cache_roundtrip.c').read_bytes() or
        providers[provider_names[3]]!=(HERE/'auto_return.c').read_bytes() or
        sha(providers[provider_names[2]])!=report.get('cpu_cache_source_sha256') or
        sha(providers[provider_names[3]])!=report.get('auto_return_source_sha256')):raise ValueError('unchanged stage/cache/recovery provider pin differs')
    window=report.get('window_access_sources_sha256')
    if not isinstance(window,dict) or set(window)!={'note10_xnu_window_access.c','note10_window_access_core.h'}:
        raise ValueError('window provider source inventory differs')
    for prepared,public in ((provider_names[5],'xnu_window_access.c'),(provider_names[6],'window_access_core.h')):
        if sha(providers[prepared])!=window['note10_'+public] or providers[prepared]!=(HERE/public).read_bytes():
            raise ValueError('window provider pin differs')
    digest=manifest['payload_sha256'];stage_header=('#define N10_XNU_PAYLOAD_SIZE '+str(manifest['payload_size'])+'ULL\n#define N10_XNU_PAYLOAD_SHA256_BYTES {'+','.join('0x'+digest[i:i+2] for i in range(0,64,2))+'}\n').encode()
    if providers[provider_names[1]]!=stage_header:raise ValueError('actual writer payload header differs')
    composition=dict(report.get('cpu_pm_roundtrip_snapshot_sha256',{}));composition.update(report.get('cpu_pm_notifier_trace_prepared_sha256',{}))
    if not composition:raise ValueError('final full provider composition missing')
    if (provider_names[4] not in composition or composition[provider_names[4]]!=FINAL_TIMER_SHA or
            sha(providers[provider_names[4]])!=FINAL_TIMER_SHA):
        raise ValueError('final composed PM timer provider is missing or differs')
    if report.get('pm_timer_source_sha256')!=sha((HERE/'pm_timer_roundtrip.c').read_bytes()):
        raise ValueError('original PM timer provider provenance differs')


def prepare(source,output,report,manifest_path,enabled=False):
    if type(enabled) is not bool:raise ValueError('runtime observation opt-in must be bool')
    if not enabled:return {}
    from cpu_pm_roundtrip_binding import trace_package_scope
    if not trace_package_scope(report,allow_build_proof=True):raise ValueError('full trace/count/pair prerequisite missing')
    for flag in ('early_xnu_reservation','window_access_diagnostic','xnu_payload_stage_diagnostic',
       'cpu_cache_roundtrip_diagnostic','pm_timer_diagnostic','auto_return_diagnostic','pm_quiesce_diagnostic'):
        if report.get(flag) is not True:raise ValueError('full planner prerequisite missing: '+flag)
    for name,digest in REUSE.items():
        if sha(canonical.file(ROOT,name).read_bytes())!=digest:raise ValueError('immutable reused source changed: '+name)
    manifest=canonical.validate_manifest(manifest_path);identity=report.get('reservation_evidence_id','')
    if not isinstance(identity,str) or re.fullmatch('[0-9a-f]{32}',identity) is None:raise ValueError('reservation build ID missing')
    if (report.get('xnu_payload_sha256')!=manifest['payload_sha256'] or report.get('xnu_payload_size')!=manifest['payload_size']):raise ValueError('actual staged payload/geometry mismatch')
    source=Path(source);output=Path(output);names=(canonical.INIT,RESERVE,KCONFIG)
    private=(ROOT/'note10/private').resolve()
    if (source.is_symlink() or output.is_symlink() or not source.resolve().is_relative_to(private) or
        not output.resolve().is_relative_to(private)):raise ValueError('full adapter work must stay project-private')
    for folder in (BASE,PREPARED):
        target=(output/folder).resolve()
        if target.is_relative_to(source.resolve()) or source.resolve().is_relative_to(target):raise ValueError('full source/proof roots overlap')
    before=files(source,names);body=full_body();expected=b'#define N10_RESERVE_BUILD_ID "'+identity.encode()+b'"\n'+body
    if before[RESERVE]!=expected or report.get('reservation_source_sha256')!=sha(body):raise ValueError('full prepared reservation body/guard pin differs')
    restored=canonical.once(canonical.once(before[canonical.INIT],canonical.CANON_INCLUDE,canonical.DECL),canonical.CANON_CALL,canonical.CALL)
    if sha(restored)!=canonical.INIT_SHA or sha(before[canonical.INIT])!=report.get('patched_arm64_init_sha256'):raise ValueError('full prepared init pin differs')
    provider_names=PROVIDERS
    providers=files(source,provider_names)
    validate_providers(providers,report,manifest)
    composition=dict(report.get('cpu_pm_roundtrip_snapshot_sha256',{}));composition.update(report.get('cpu_pm_notifier_trace_prepared_sha256',{}))
    for name,digest in composition.items():
        if sha(canonical.file(source,name).read_bytes())!=digest:raise ValueError('full final provider snapshot changed: '+name)
    if OPTION.removeprefix('CONFIG_').encode() in before[KCONFIG] or MARKER in before[RESERVE]:raise ValueError('duplicate runtime observation')
    header,companion=geometry(manifest)
    copies={'runtime_relocation.c':ROOT/'note10/xnu26/runtime_relocation.c','runtime_relocation.h':ROOT/'note10/xnu26/runtime_relocation.h',
      'note10_xnu_runtime_plan.c':HERE/'xnu_runtime_plan.c','note10_xnu_runtime_observation.c':HERE/'xnu_runtime_observation.c'}
    additions={'arch/arm64/mm/'+name:canonical.file(path.parent,path.name).read_bytes() for name,path in copies.items()}
    additions.update({'arch/arm64/mm/'+canonical.GEOMETRY:header,'arch/arm64/mm/note10_xnu_observation_geometry.h':companion})
    if any((source/name).exists() or (source/name).is_symlink() for name in additions):raise ValueError('prior runtime source insertion')
    after=dict(before);after[RESERVE]=canonical.once(before[RESERVE],b'static int __init note10_check_xnu_window(void)',INCLUDE+b'static int __init note10_check_xnu_window(void)')
    after[RESERVE]=canonical.once(after[RESERVE],b'    /* Reserved pages remain excluded from Linux',CALL+b'    /* Reserved pages remain excluded from Linux')
    after[KCONFIG]+=BLOCK;after.update(additions)
    for folder,mapping in ((BASE,{**before,**providers}),(PREPARED,{**after,**providers})):
        if (output/folder).exists():raise ValueError('observation source proof already exists')
        for name,raw in mapping.items():
            target=output/folder/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(raw)
    for name,raw in after.items():canonical.file(source,name).write_bytes(raw) if name not in additions else (source/name).write_bytes(raw)
    return {FLAG:True,VERSION:1,FLAG+'_before_sha256':{n:sha(r) for n,r in {**before,**providers}.items()},
      FLAG+'_prepared_sha256':{n:sha(r) for n,r in {**after,**providers}.items()},
      FLAG+'_sources_sha256':{n:sha((HERE/n).read_bytes()) for n in SOURCES},
      FLAG+'_geometry_sha256':sha(header),FLAG+'_manifest_canonical_sha256':canonical.MANIFEST_SHA,
      FLAG+'_manifest_raw_sha256':sha(canonical.manifest_bytes(manifest_path)[0]),
      'reservation_source_before_runtime_sha256':report['reservation_source_sha256'],
      'reservation_source_sha256':sha(after[RESERVE].split(b'\n',1)[1])}
