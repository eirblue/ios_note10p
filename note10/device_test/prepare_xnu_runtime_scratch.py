"""Exact post-v56 delta; earlier snapshots remain intermediate provenance."""
import json
from pathlib import Path
import prepare_xnu_runtime_observation as prior

HERE=prior.HERE
FLAG='xnu_runtime_scratch'
OPTION='CONFIG_NOTE10_XNU_RUNTIME_SCRATCH'
MARKER=b'N10XSO1'
BASE='xnu-runtime-scratch-before'
PREPARED='xnu-runtime-scratch-prepared'
MODEL='xnu-runtime-scratch-model'
PACKAGE='xnu-runtime-scratch-package-model'
WRAPPER='arch/arm64/mm/note10_xnu_runtime_scratch.c'
SOURCES=('prepare_xnu_runtime_scratch.py','xnu_runtime_scratch.c','decode_xnu_runtime_scratch.py',
 'xnu_runtime_scratch_binding.py','xnu_runtime_scratch_stack.py',
 'test_xnu_runtime_scratch.py','test_xnu_runtime_scratch_package.py')
INCLUDE=b'#ifdef CONFIG_NOTE10_XNU_RUNTIME_SCRATCH\n#include "note10_xnu_runtime_scratch.c"\n#endif\n\n'
CALL=b'#ifdef CONFIG_NOTE10_XNU_RUNTIME_SCRATCH\n    n10_observe_runtime_scratch(reserved,count,invalid);\n#endif\n\n'
BLOCK=b'\nconfig NOTE10_XNU_RUNTIME_SCRATCH\n\tbool "Caller-owned scratch XNU metadata roundtrip only"\n\tdepends on NOTE10_XNU_RUNTIME_OBSERVATION\n\tdefault n\n'

def source_hashes():return {n:prior.sha((HERE/n).read_bytes()) for n in SOURCES}

def transform(before):
    after=dict(before)
    after[prior.RESERVE]=prior.canonical.once(before[prior.RESERVE],
        b'static int __init note10_check_xnu_window(void)',INCLUDE+b'static int __init note10_check_xnu_window(void)')
    after[prior.RESERVE]=prior.canonical.once(after[prior.RESERVE],prior.CALL,prior.CALL+CALL)
    after[prior.KCONFIG]+=BLOCK
    after[WRAPPER]=(HERE/'xnu_runtime_scratch.c').read_bytes()
    return after

def prepare(source,output,report,enabled=False):
    if type(enabled) is not bool:raise ValueError('scratch opt-in must be bool')
    if not enabled:return {}
    from xnu_runtime_observation_binding import package_scope
    if not package_scope(report,allow_build_proof=True):raise ValueError('scratch requires v56')
    source=Path(source);output=Path(output)
    private=prior.ROOT/'note10/private'
    if (source.is_symlink() or output.is_symlink() or not source.resolve().is_relative_to(private.resolve()) or
        not output.resolve().is_relative_to(private.resolve())):raise ValueError('scratch roots must be private')
    names=report['xnu_runtime_observation_prepared_sha256']
    before={n:prior.safe_path(source,n).read_bytes() for n in names}
    if any(prior.sha(raw)!=names[n] for n,raw in before.items()):raise ValueError('v56 intermediate source mismatch')
    if (source/WRAPPER).exists() or (source/WRAPPER).is_symlink() or OPTION.encode() in before[prior.KCONFIG]:raise ValueError('duplicate scratch adapter')
    after=transform(before)
    for folder,mapping in ((BASE,before),(PREPARED,after)):
        dest=output/folder
        if dest.exists() or dest.is_symlink():raise ValueError('scratch proof exists')
        if dest.resolve().is_relative_to(source.resolve()) or source.resolve().is_relative_to(dest.resolve()):raise ValueError('scratch proof/source overlap')
        for name,raw in mapping.items():
            path=prior.safe_path(dest,name,exists=False);path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw)
    for name,raw in after.items():prior.safe_path(source,name,exists=False).write_bytes(raw)
    return {FLAG:True,FLAG+'_version':1,FLAG+'_geometry_sha256':report['xnu_runtime_observation_geometry_sha256'],
      FLAG+'_before_sha256':{n:prior.sha(r) for n,r in before.items()},
      FLAG+'_prepared_sha256':{n:prior.sha(r) for n,r in after.items()},FLAG+'_sources_sha256':source_hashes(),
      'reservation_source_before_scratch_sha256':report['reservation_source_sha256'],
      'reservation_source_sha256':prior.sha(after[prior.RESERVE].split(b'\n',1)[1])}

def validate_delta(root,build):
    root=Path(root);maps=[]
    for folder,key in ((BASE,'before_sha256'),(PREPARED,'prepared_sha256')):
        mapping=build.get(FLAG+'_'+key)
        if not isinstance(mapping,dict):raise ValueError('scratch source map missing')
        raw={n:prior.safe_path(root/folder,n).read_bytes() for n in mapping}
        if {n:prior.sha(r) for n,r in raw.items()}!=mapping:raise ValueError('scratch snapshot hash differs')
        maps.append(raw)
    before,after=maps
    if build[FLAG+'_before_sha256']!=build['xnu_runtime_observation_prepared_sha256'] or after!=transform(before):raise ValueError('scratch exact layered delta differs')
    if build.get(FLAG+'_sources_sha256')!=source_hashes():raise ValueError('scratch source closure differs')
    return before,after
