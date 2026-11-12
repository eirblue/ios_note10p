"""227 host ABI regression and first actual C stream fixture; ROOT executes once."""
import gzip
import hashlib
import io
import json
import os
from pathlib import Path
import struct
import subprocess
from v130_payload import Newc
import v227_host_inflate as host_abi
HERE=Path(__file__).resolve().parent
SOURCE_NAMES=('include/linux/zlib.h','include/linux/zconf.h','include/linux/zutil.h',
 'lib/zlib_inflate/inflate.c','lib/zlib_inflate/inffast.c','lib/zlib_inflate/inftrees.c',
 'lib/zlib_inflate/inflate.h','lib/zlib_inflate/infutil.h','lib/zlib_inflate/inftrees.h',
 'lib/zlib_inflate/inffast.h','lib/zlib_inflate/inffixed.h')


def command(output,compiler):
    stock=Path(output)/'stock'
    return [compiler,'-std=c11','-O2','-Wall','-Wextra','-Werror','-Wno-sign-compare','-Wno-implicit-fallthrough',
        '-I',str(stock/'include'),'-I',str(stock/'zlib'),'-I',str(HERE),
        *[str(HERE/name)for name in ('native_source_stream.c','native_source_stream_fixture.c','native_source_ingest.c','native_source_sha256.c','native_parcel_core.c')],
        *[str(stock/'zlib'/name)for name in ('inflate.c','inffast.c','inftrees.c')],'-o',str(Path(output)/'source-stream-fixture.exe')]


def run(output,compiler_argv,source_pins):
    output=Path(output);stock=output/'stock';stock.mkdir()
    if set(source_pins)!=set(SOURCE_NAMES):raise ValueError('exact pinned rawinflate source set required')
    for name,item in source_pins.items():
        source=Path(item['path']);raw=source.read_bytes()
        if source.resolve()!=source or source.is_symlink()or not 0<len(raw)<=262144 or len(raw)!=item['bytes']or hashlib.sha256(raw).hexdigest()!=item['sha256']:
            raise ValueError('pinned rawinflate source differs')
        if name=='lib/zlib_inflate/inffast.c':
            raw,abi=host_abi.regression(raw)
            (output/'HOST-ABI-RESULT.json').write_text(json.dumps(abi,indent=2,sort_keys=True)+'\n',encoding='utf-8')
        target=stock/name if name.startswith('include/')else stock/'zlib'/Path(name).name
        target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(raw)
    (stock/'include/linux/string.h').write_text('#include <string.h>\n',encoding='ascii')
    (stock/'include/linux/kernel.h').write_text('#include <stddef.h>\n',encoding='ascii')
    cases=output/'cases';cases.mkdir();kernel=b'K'*65536;adapter=b'A'*16384
    payload=struct.pack('<8sII10Q32s32s32s32s32s',b'N209PAY1',1,256,0x1004000,65536,0,0,16384,32768,16384,16384,0,64,
        bytes([0x21])*32,hashlib.sha256(kernel).digest(),hashlib.sha256(adapter).digest(),b'p'*32,b'i'*32)
    (cases/'payload.bin').write_bytes(payload)
    for variant in range(14):
        raw=io.BytesIO();writer=Newc(raw);writer.header('n10',0,0o040700)
        writer.header('n10/../kernel.mem'if variant==4 else'n10/kernel.mem',len(kernel),0o100600 if variant==5 else 0o100400)
        writer.write(kernel);writer.pad(4);writer.file('n10/adapter.mem',adapter);writer.finish();unpacked=raw.getvalue()
        compressed=io.BytesIO()
        with gzip.GzipFile(filename='',mode='wb',fileobj=compressed,compresslevel=9,mtime=0)as stream:stream.write(unpacked)
        member=compressed.getvalue()
        if variant==1:member=member[:-8]+bytes([member[-8]^1])+member[-7:]
        elif variant==2:member=member[:-7]
        elif variant==3:member+=gzip.compress(b'extra',mtime=0)
        digest=hashlib.sha256(member).digest()
        if variant==11:member=member[:15]+bytes([member[15]^1])+member[16:]
        header=struct.pack('<8sIIQQ32s32s',b'N226SRC1',1,96,len(member),len(unpacked)+(512 if variant==6 else 0),digest,hashlib.sha256(payload).digest())
        (cases/f'case{variant}.bin').write_bytes(header+member)
    if compiler_argv!=command(output,compiler_argv[0]):raise ValueError('exact new C fixture argv required')
    env=dict(os.environ);env['PATH']=str(Path(compiler_argv[0]).parent)+os.pathsep+env.get('PATH','')
    (output/'COMPILE-STARTED.json').write_text(json.dumps(dict(argv=compiler_argv,attempt=1))+'\n',encoding='utf-8')
    with (output/'compile.log').open('xb')as log:
        subprocess.run(compiler_argv,stdout=log,stderr=subprocess.STDOUT,env=env,check=True,timeout=120)
    (output/'COMPILE-COMPLETED.json').write_text('{"returncode":0}\n',encoding='ascii')
    argv=[str(output/'source-stream-fixture.exe'),str(cases)]
    (output/'C-FIXTURE-STARTED.json').write_text(json.dumps(dict(argv=argv,attempt=1))+'\n',encoding='utf-8')
    done=subprocess.run(argv,capture_output=True,env=env,check=False,timeout=120)
    (output/'fixture.stdout').write_bytes(done.stdout);(output/'fixture.stderr').write_bytes(done.stderr)
    (output/'C-FIXTURE-COMPLETED.json').write_text(json.dumps(dict(returncode=done.returncode))+'\n',encoding='ascii')
    done.check_returncode()
    actual=json.loads(done.stdout)
    if actual!=dict(groups=1,variants=14,assertions=33):raise ValueError('actual new C stream batch counts differ')
    return dict(host_ABI=abi,C_stream=actual)

