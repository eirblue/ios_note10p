"""Separate default-off source-only reservation/planner component preparation.

The canonical reservation adapter reproduces only the pinned source transform;
it does NOT execute the older preparer or create its minimal-init/CPIO outputs.
"""
import hashlib
import json
from pathlib import Path
import re
import uuid

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
INIT='arch/arm64/mm/init.c'
RESERVE='arch/arm64/mm/note10_xnu_reserve.c'
KCONFIG='arch/arm64/Kconfig'
OPTION='CONFIG_NOTE10_XNU_RUNTIME_PLAN'
INIT_SHA='cc990de7d8222f56fd71519c8b5dbf87a50abd4131e9eeb49ba78c04e3b6e3f3'
RESERVE_SHA='5a173cc7a1fa6b97ee8063850a10c35c51b24db4718fe7ef5838e4f8743327f8'
OLD_PREPARER_SHA='c5903dabc15bd2ab5bd676849112c0413d84cd434b8bcadebf876e507aa086dc'
RUNTIME_C_SHA='dc51d22fce4c8e0d566d6158f53aa3d512a65954541e4ea4201c5878cb17e448'
# Public Git checkout uses LF; the saved original uses uniform CRLF.
MANIFEST_SHA='d5b1f88274396c524c38925389df2e123140b2c081824afdb3001119db4dd80c'
ORIGINAL_MANIFEST_RAW_SHA='ada09fb634e63430d5b7f111607c8ec919d224b39fbd4e928423c37abf0169ec'
DECL=b'void __init arm64_memblock_init(void)'
CALL=b'\tmemblock_allow_resize();'
CANON_INCLUDE=b'#include "note10_xnu_reserve.c"\n\n'+DECL
CANON_CALL=b'\tnote10_reserve_xnu_window();\n\n'+CALL
PREFIX=b'arch/arm64/mm/'
COPIES={'runtime_relocation.c':ROOT/'note10/xnu26/runtime_relocation.c',
        'runtime_relocation.h':ROOT/'note10/xnu26/runtime_relocation.h',
        'note10_xnu_runtime_plan.c':HERE/'xnu_runtime_plan.c'}
GEOMETRY='note10_xnu_runtime_geometry.h'
FORBIDDEN=('note10_xnu_window_access.c','note10_xnu_payload_stage.c','note10_xnu_payload_stage.h',
           'note10_cpu_cache_roundtrip.c','note10_pm_timer_roundtrip.c','note10_auto_return.c')
BLOCK=b'''\nconfig NOTE10_XNU_RUNTIME_PLAN
\tbool "PC-only reservation runtime planner integration"
\tdepends on ARM64
\tdefault n
'''
INCLUDE=b'''#ifdef CONFIG_NOTE10_XNU_RUNTIME_PLAN
#include "runtime_relocation.c"
#include "note10_xnu_runtime_plan.c"
#endif

'''
INVOKE=b'''#ifdef CONFIG_NOTE10_XNU_RUNTIME_PLAN
    (void)n10_xnu_runtime_plan_check(reserved,count,invalid);
#endif

'''


def sha(raw):return hashlib.sha256(raw).hexdigest()


def file(root,name):
    path=Path(root)/name
    if (Path(root).is_symlink() or path.is_symlink() or not path.is_file() or
            not path.resolve().is_relative_to(Path(root).resolve())):
        raise ValueError('source/input missing or unsafe: '+name)
    return path


def once(raw,anchor,replacement):
    if raw.count(anchor)!=1:raise ValueError('pinned insertion anchor differs')
    return raw.replace(anchor,replacement,1)


def manifest_bytes(path):
    path=Path(path)
    if path.is_symlink() or not path.is_file():raise ValueError('actual payload geometry manifest missing/unsafe')
    raw=path.read_bytes()
    canonical=raw.replace(b'\r\n',b'\n')
    if (b'\r' in canonical or raw not in (canonical,canonical.replace(b'\n',b'\r\n')) or
            sha(canonical)!=MANIFEST_SHA):raise ValueError('actual payload canonical geometry manifest pin/encoding differs')
    return raw,canonical


def validate_manifest(path):
    raw,canonical=manifest_bytes(path)
    data=json.loads(canonical)
    expected={'schema':1,'purpose':'xnu-data-only-ram-stage','source_kind':'experimental-source-built-arm64-macho',
      'source_macho_sha256':'b2c80dea6762dc8a388563a099810b48a9157533c6b9c9db8889c29bdddf8d3f',
      'source_macho_size':18522008,'virtual_base':'0xfffffff007004000','entry_virtual_address':'0xfffffff007340490',
      'payload_file':'kernel.mem','payload_size':19578880,
      'payload_sha256':'7a573eb6d2f5efc87bd5c85af130ea854eb4bad8370d17a4247e54f9593a836a',
      'physical_address':None,'physical_reservation_verified':False,'deployment_ready':False,'device_operations':[],
      'xnu_executed':False}
    if data!=expected or type(data['schema']) is not int or type(data['payload_size']) is not int:
        raise ValueError('actual input geometry/scope differs')
    return data


def geometry_header(manifest):
    image=int(manifest['virtual_base'],16);entry=int(manifest['entry_virtual_address'],16)
    virtual=image&~(0x2000000-1);size=manifest['payload_size']
    if (virtual!=0xfffffff006000000 or image-virtual!=0x1004000 or entry-virtual!=0x1340490 or
            image-virtual+size!=0x22b0000 or size%0x4000 or not image<=entry<image+size):
        raise ValueError('actual input offsets/alignment differ')
    values={'IMAGE_VA':image,'ENTRY_VA':entry,'IMAGE_SIZE':size,'VIRTUAL_BASE':virtual,
            'KERNEL_OFFSET':image-virtual,'ENTRY_OFFSET':entry-virtual,'END_OFFSET':image-virtual+size}
    return ('/* Actual hash-bound payload geometry; no physical base. */\n'+
            ''.join('#define N10_RTP_'+key+' UINT64_C('+hex(value)+')\n' for key,value in values.items())+
            '#define N10_RTP_MANIFEST_CANONICAL_LF_SHA256 "'+MANIFEST_SHA+'"\n').encode('ascii')


def reservation_body():
    if sha(file(HERE,'prepare_reservation_kernel.py').read_bytes())!=OLD_PREPARER_SHA:
        raise ValueError('canonical source-transform provenance changed')
    body=file(HERE,'xnu_reserve.c').read_bytes()
    if sha(body)!=RESERVE_SHA:raise ValueError('original reservation body pin differs')
    return body


def canonical_reservation(source,build_id=None):
    source=Path(source);init=file(source,INIT);config=file(source,KCONFIG)
    raw=init.read_bytes();body=reservation_body()
    if sha(raw)!=INIT_SHA:raise ValueError('upstream reservation TU pin differs')
    identifier=uuid.uuid4().hex if build_id is None else build_id
    if not isinstance(identifier,str) or re.fullmatch('[0-9a-f]{32}',identifier) is None:
        raise ValueError('fresh canonical reservation ID must be 32 lowercase hex')
    if (source/RESERVE).exists() or (source/RESERVE).is_symlink():raise ValueError('reservation extension already exists')
    if b'NOTE10_XNU_RUNTIME_PLAN' in config.read_bytes():raise ValueError('runtime config already inserted')
    prepared=once(once(raw,DECL,CANON_INCLUDE),CALL,CANON_CALL)
    extension=b'#define N10_RESERVE_BUILD_ID "'+identifier.encode()+b'"\n'+body
    init.write_bytes(prepared);(source/RESERVE).write_bytes(extension)
    return {'schema':1,'canonical_reservation_only':True,'source_only_equivalent':True,
            'older_preparer_executed':False,'ancillary_init_or_cpio_generated':False,
            'reservation_build_id':identifier,'upstream_init_sha256':INIT_SHA,
            'reservation_body_sha256':RESERVE_SHA,'old_preparer_source_sha256':OLD_PREPARER_SHA,
            'canonical_source_sha256':{name:sha(file(source,name).read_bytes()) for name in (INIT,RESERVE,KCONFIG)}}


def validate_canonical(source,baseline):
    if (not isinstance(baseline,dict) or type(baseline.get('schema')) is not int or baseline.get('schema')!=1 or
            baseline.get('canonical_reservation_only') is not True or baseline.get('source_only_equivalent') is not True or
            baseline.get('older_preparer_executed') is not False or baseline.get('ancillary_init_or_cpio_generated') is not False or
            baseline.get('upstream_init_sha256')!=INIT_SHA or baseline.get('reservation_body_sha256')!=RESERVE_SHA or
            baseline.get('old_preparer_source_sha256')!=OLD_PREPARER_SHA):raise ValueError('canonical source provenance differs')
    identifier=baseline.get('reservation_build_id')
    if not isinstance(identifier,str) or re.fullmatch('[0-9a-f]{32}',identifier) is None:raise ValueError('canonical fresh ID malformed')
    raw=file(source,INIT).read_bytes();extension=file(source,RESERVE).read_bytes();body=reservation_body()
    restored=once(once(raw,CANON_INCLUDE,DECL),CANON_CALL,CALL)
    if sha(restored)!=INIT_SHA or extension!=b'#define N10_RESERVE_BUILD_ID "'+identifier.encode()+b'"\n'+body:
        raise ValueError('reservation-only source body changed or scope expanded')
    actual={name:sha(file(source,name).read_bytes()) for name in (INIT,RESERVE,KCONFIG)}
    if baseline.get('canonical_source_sha256')!=actual:raise ValueError('canonical source/config hashes differ')
    parent=Path(source)/'arch/arm64/mm'
    if any((parent/name).exists() or (parent/name).is_symlink() for name in (*FORBIDDEN,*COPIES,GEOMETRY)):
        raise ValueError('noncanonical writer, prior runtime file or duplicate insertion exists')
    if b'NOTE10_XNU_RUNTIME_PLAN' in file(source,KCONFIG).read_bytes():raise ValueError('duplicate/stray runtime config')
    return actual


def prepare(source,baseline,payload_manifest,enabled=False):
    if type(enabled) is not bool:raise ValueError('runtime source opt-in must be an explicit bool')
    source=Path(source);before=validate_canonical(source,baseline);manifest=validate_manifest(payload_manifest)
    report={'schema':1,'enabled':enabled,'payload_manifest_sha256':MANIFEST_SHA,
            'payload_manifest_digest_encoding':'canonical-LF',
            'payload_manifest_raw_sha256':sha(manifest_bytes(payload_manifest)[0]),
            'payload_manifest_original_raw_sha256':ORIGINAL_MANIFEST_RAW_SHA,
            'before_sha256':before,'source_only_equivalent':True,'materialized':False,
            'physical_reservation_verified':False,'deployment_ready':False,'device_operations':[]}
    if not enabled:
        return dict(report,after_sha256=before,files_copied=[],config_added=False)
    if any(path.is_symlink() or not path.is_file() for path in COPIES.values()):
        raise ValueError('production source missing or unsafe')
    copies={name:regular.read_bytes() for name,regular in COPIES.items()}
    if sha(copies['runtime_relocation.c'])!=RUNTIME_C_SHA:raise ValueError('immutable v54 production C differs')
    header=geometry_header(manifest)
    reserve=file(source,RESERVE);config=file(source,KCONFIG)
    extension=once(reserve.read_bytes(),b'static int __init note10_check_xnu_window(void)',
                   INCLUDE+b'static int __init note10_check_xnu_window(void)')
    extension=once(extension,b'    /* Reserved pages remain excluded from Linux',
                   INVOKE+b'    /* Reserved pages remain excluded from Linux')
    # The original early return remains; expose only the failed computational
    # admission status without reading the base or calling the planner.
    failure=b'        pr_err("N10RAM1 FAILED stage=late-no-window\\n");\n'
    extension=once(extension,failure,failure+
        b'#ifdef CONFIG_NOTE10_XNU_RUNTIME_PLAN\n        n10_runtime_plan_report(-1,0,0,0,0,0);\n#endif\n')
    # All input, pin, duplicate and insertion checks complete before any write.
    for name,raw in {**copies,GEOMETRY:header}.items():(source/'arch/arm64/mm'/name).write_bytes(raw)
    reserve.write_bytes(extension);config.write_bytes(config.read_bytes()+BLOCK)
    names=(INIT,RESERVE,KCONFIG,*('arch/arm64/mm/'+name for name in (*copies,GEOMETRY)))
    return dict(report,after_sha256={name:sha(file(source,name).read_bytes()) for name in names},
                files_copied=list(copies)+[GEOMETRY],config_added=True,
                production_sources_sha256={name:sha(raw) for name,raw in copies.items()},
                geometry_sha256=sha(header))
