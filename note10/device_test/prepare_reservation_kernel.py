"""Prepare pinned-source early reservation and an original minimal initramfs."""
import hashlib
import json
from pathlib import Path
import zlib
import uuid

INIT_SHA='cc990de7d8222f56fd71519c8b5dbf87a50abd4131e9eeb49ba78c04e3b6e3f3'


def verify_embedded_init(image,archive):
    if not archive.startswith(b'070701') or not 0<len(archive)<=64*1024*1024:
        raise ValueError('Invalid expected initramfs archive')
    offset=image.find(archive)
    if offset>=0:return {'embedded_initramfs_verified':True,'encoding':'raw','image_offset':offset}
    start=0;attempts=0
    while True:
        offset=image.find(b'\x1f\x8b\x08',start)
        if offset<0:break
        attempts+=1
        if attempts>4096:raise ValueError('Too many compressed image candidates')
        start=offset+3
        decoder=zlib.decompressobj(31)
        try:data=decoder.decompress(image[offset:offset+64*1024*1024],64*1024*1024)
        except zlib.error:continue
        if decoder.eof and data==archive:
            return {'embedded_initramfs_verified':True,'encoding':'gzip','image_offset':offset}
    raise ValueError('Expected original initramfs not found in actual kernel Image')


def cpio(init, xnu_payload=None):
    if not 64<=len(init)<=1024*1024 or not init.startswith(b'\x7fELF\x02\x01') or init[18:20]!=b'\xb7\x00':
        raise ValueError('Bounded ARM64 ELF init required')
    output=bytearray()
    inode=0
    def entry(name,mode,data=b'',major=0,minor=0):
        nonlocal inode
        inode+=1
        encoded=name.encode('ascii')+b'\0'
        fields=(inode,mode,0,0,2 if mode==0o040755 else 1,0,len(data),0,0,major,minor,len(encoded),0)
        output.extend(b'070701'+''.join(f'{v:08x}' for v in fields).encode())
        output.extend(encoded);output.extend(bytes(-len(output)%4))
        output.extend(data);output.extend(bytes(-len(output)%4))
    entry('dev',0o040755)
    entry('dev/console',0o020600,major=5,minor=1)
    entry('init',0o100755,init)
    if xnu_payload is not None:
        entry('xnu',0o040755)
        entry('xnu/kernel.mem',0o100444,xnu_payload)
    entry('TRAILER!!!',0)
    output.extend(bytes(-len(output)%512))
    return bytes(output)


def prepare(source,output,run,window_access=False,xnu_payload=None,xnu_manifest=None):
    here=Path(__file__).resolve().parent
    if (xnu_payload is None)!=(xnu_manifest is None):
        raise ValueError('XNU stage payload and manifest must be supplied together')
    if xnu_payload is not None and not window_access:
        raise ValueError('XNU payload staging requires the opt-in reservation/window diagnostic')
    path=source/'arch/arm64/mm/init.c';raw=path.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=INIT_SHA:raise ValueError('Pinned arm64 memblock source differs')
    text=raw.decode()
    declaration='void __init arm64_memblock_init(void)'
    call='\tmemblock_allow_resize();'
    if text.count(declaration)!=1 or text.count(call)!=1:raise ValueError('Unexpected reservation insertion points')
    target=path.with_name('note10_xnu_reserve.c')
    if target.exists():raise ValueError('Existing reservation extension')
    extension=(here/'xnu_reserve.c').read_bytes()
    access_report={}
    if window_access:
        needle=b'static int __init note10_check_xnu_window(void)'
        marker=b'    /* Reserved pages remain excluded from Linux'
        if extension.count(needle)!=1 or extension.count(marker)!=1:
            raise ValueError('Unexpected access diagnostic insertion points')
        files={'note10_xnu_window_access.c':here/'xnu_window_access.c',
               'note10_window_access_core.h':here/'window_access_core.h'}
        if any(path.with_name(name).exists() for name in files):
            raise ValueError('Existing access diagnostic extension')
        for name,original in files.items():path.with_name(name).write_bytes(original.read_bytes())
        access_report={'window_access_diagnostic':True,'window_access_evidence_version':1,
                       'window_access_sources_sha256':{name:hashlib.sha256(original.read_bytes()).hexdigest()
                                                       for name,original in files.items()},
                       'physical_window_access_tested_on_device':False,'xnu_executed':False}
        extension=extension.replace(needle,b'#include "note10_xnu_window_access.c"\n\n'+needle)
        extension=extension.replace(marker,b'    note10_test_xnu_window_access(reserved, count, invalid);\n\n'+marker)
        extension=extension.replace(b'Reservation diagnostic only: does not write the window or execute XNU.',
                                    b'Reservation and opt-in cached RAM access test; never executes XNU.')
    payload_report={}
    if xnu_payload is not None:
        payload=xnu_payload.read_bytes()
        manifest=json.loads(xnu_manifest.read_text(encoding='utf-8'))
        digest=hashlib.sha256(payload).hexdigest()
        if (manifest.get('schema')!=1 or manifest.get('purpose')!='xnu-data-only-ram-stage' or
            manifest.get('source_kind')!='experimental-source-built-arm64-macho' or
            manifest.get('payload_file')!='kernel.mem' or manifest.get('payload_size')!=len(payload) or
            manifest.get('payload_sha256')!=digest or manifest.get('physical_address') is not None or
            manifest.get('physical_reservation_verified') is not False or
            manifest.get('deployment_ready') is not False or manifest.get('xnu_executed') is not False):
            raise ValueError('XNU payload manifest does not match a data-only experimental image')
        if not 0<len(payload)<=64*1024*1024 or len(payload)%16384:
            raise ValueError('XNU payload size must be bounded and 16K aligned')
        generated=path.with_name('note10_xnu_payload_stage.h')
        if generated.exists():raise ValueError('Unexpected existing XNU stage header')
        digest_bytes=','.join('0x'+digest[i:i+2] for i in range(0,64,2))
        generated.write_text('#define N10_XNU_PAYLOAD_SIZE '+str(len(payload))+'ULL\n'+
                             '#define N10_XNU_PAYLOAD_SHA256_BYTES {'+digest_bytes+'}\n',encoding='ascii')
        source=path.with_name('note10_xnu_payload_stage.c')
        if source.exists():raise ValueError('Unexpected existing XNU stage extension')
        source.write_bytes((here/'xnu_payload_stage.c').read_bytes())
        include=b'#include "note10_xnu_payload_stage.c"\n'
        stage_call=b'    n10_stage_xnu_payload(reserved, count, invalid);\n'
        marker=b'    /* Reserved pages remain excluded from Linux'
        if extension.count(marker)!=1:raise ValueError('Unexpected reservation staging insertion point')
        extension=extension.replace(marker,stage_call+marker)
        extension=extension.replace(b'#include "note10_xnu_window_access.c"\n',
                                    b'#include "note10_xnu_window_access.c"\n'+include)
        access_report.update(xnu_payload_stage_diagnostic=True,
                             xnu_payload_size=len(payload),xnu_payload_sha256=digest,
                             xnu_source_macho_sha256=manifest['source_macho_sha256'],
                             xnu_payload_manifest_sha256=hashlib.sha256(xnu_manifest.read_bytes()).hexdigest(),
                             xnu_payload_stage_sources_sha256=hashlib.sha256((here/'xnu_payload_stage.c').read_bytes()).hexdigest(),
                             xnu_executed=False)
        payload_report={'xnu_payload':str(xnu_payload),'xnu_payload_size':len(payload),
                        'xnu_payload_sha256':digest,'xnu_source_macho_sha256':manifest['source_macho_sha256'],
                        'xnu_payload_stage_diagnostic':True}
    evidence_id=uuid.uuid4().hex
    target.write_bytes(('#define N10_RESERVE_BUILD_ID "'+evidence_id+'"\n').encode()+extension)
    text=text.replace(declaration,'#include "note10_xnu_reserve.c"\n\n'+declaration)
    text=text.replace(call,'\tnote10_reserve_xnu_window();\n\n'+call)
    path.write_text(text)
    assembly=here/'minimal_init.S';obj=output/'minimal-init.o';elf=output/'minimal-init.elf'
    run(['clang-14','--target=aarch64-linux-gnu','-I','/usr/aarch64-linux-gnu/include',
         '-D__ASSEMBLY__','-c',str(assembly),'-o',str(obj)],'00-minimal-init-compile.log')
    run(['aarch64-linux-gnu-ld','--build-id=none','-static','-e','_start',str(obj),'-o',str(elf)],
        '00-minimal-init-link.log')
    init=elf.read_bytes()
    if len(init)<64 or init[18:20]!=b'\xb7\x00':raise ValueError('Not an ARM64 init ELF')
    archive=output/'initramfs.cpio';archive.write_bytes(cpio(init,xnu_payload.read_bytes() if xnu_payload else None))
    return {**access_report,'early_xnu_reservation':True,'builtin_idle_init':True,
            'reservation_evidence_id':evidence_id,'reservation_evidence_version':2,
            'reservation_source_sha256':hashlib.sha256(extension).hexdigest(),
            'patched_arm64_init_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
            'minimal_init_source_sha256':hashlib.sha256(assembly.read_bytes()).hexdigest(),
            'minimal_init_elf_sha256':hashlib.sha256(init).hexdigest(),
            'initramfs_cpio_sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),**payload_report,
            'physical_reservation_tested_on_device':False}
