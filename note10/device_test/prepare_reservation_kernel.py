"""Prepare pinned-source early reservation and an original minimal initramfs."""
import hashlib
from pathlib import Path
import zlib
import uuid

INIT_SHA='cc990de7d8222f56fd71519c8b5dbf87a50abd4131e9eeb49ba78c04e3b6e3f3'


def verify_embedded_init(image,archive):
    if not archive.startswith(b'070701') or not 0<len(archive)<=2*1024*1024:
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
        try:data=decoder.decompress(image[offset:offset+2*1024*1024],2*1024*1024)
        except zlib.error:continue
        if decoder.eof and data==archive:
            return {'embedded_initramfs_verified':True,'encoding':'gzip','image_offset':offset}
    raise ValueError('Expected original initramfs not found in actual kernel Image')


def cpio(init):
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
    entry('TRAILER!!!',0)
    output.extend(bytes(-len(output)%512))
    return bytes(output)


def prepare(source,output,run,window_access=False):
    here=Path(__file__).resolve().parent
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
    archive=output/'initramfs.cpio';archive.write_bytes(cpio(init))
    return {**access_report,'early_xnu_reservation':True,'builtin_idle_init':True,
            'reservation_evidence_id':evidence_id,'reservation_evidence_version':2,
            'reservation_source_sha256':hashlib.sha256(extension).hexdigest(),
            'patched_arm64_init_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
            'minimal_init_source_sha256':hashlib.sha256(assembly.read_bytes()).hexdigest(),
            'minimal_init_elf_sha256':hashlib.sha256(init).hexdigest(),
            'initramfs_cpio_sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),
            'physical_reservation_tested_on_device':False}
