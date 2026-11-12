"""One actual C parser/core/raw-kernel-inflate synthetic batch; ROOT executes it once."""
import gzip
import hashlib
import io
import json
import os
from pathlib import Path
import struct
import subprocess
from v130_payload import Newc
import v226_source_stream as stream_source
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
    return actual


def layout_batch():
    count=0
    def check(ok):
        nonlocal count
        count+=1
        if not ok:raise AssertionError('226 layout assertion failed')
    def denied(call):
        try:call()
        except ValueError:return True
        return False
    source=4096;meta=source+stream_source.SOURCE_CAP+512;marker=64
    image=bytearray(meta+4096+512);image[marker:marker+33]=stream_source.retained.p.CYCLE_MARKER+b'\0';image=bytes(image)
    build=dict(build_evidence_id='1'*32,slot_offset=meta,slot_bytes=4096,cycle_offset=marker,source_holder_offset=source,source_holder_bytes=stream_source.SOURCE_CAP)
    descriptor=b'N209PAY1'+struct.pack('<II',1,256)+bytes(240);member=b'\x1f\x8b\x08\0'+bytes(stream_source.MEMBER_BYTES-4)
    member_sha=hashlib.sha256(member).hexdigest();descriptor_sha=hashlib.sha256(descriptor).hexdigest()
    def compose(raw,row):return stream_source.insert_private(raw,row,descriptor,member,member_sha,descriptor_sha,'2'*32)
    changed,binding,result=compose(image,build)
    check(len(changed)==len(image)and changed[marker:marker+33]==b'2'*32+b'\0'and changed[source:source+8]==b'N226SRC1')
    check(changed[source+96:source+96+len(member)]==member and len(binding)==128 and result['named_native_resident_bytes']==6258688 and result['hardware_authorized']is False)
    check(changed[:marker]==image[:marker]and changed[marker+33:source]==image[marker+33:source]and changed[source+stream_source.SOURCE_CAP:meta]==image[source+stream_source.SOURCE_CAP:meta]and changed[meta+4096:]==image[meta+4096:])
    check(denied(lambda:compose(image,dict(build,slot_offset=source+100))))
    dirty=bytearray(image);dirty[source+100]=1
    check(denied(lambda:compose(bytes(dirty),build)))
    check(denied(lambda:compose(image,dict(build,source_holder_offset=len(image)-100))))
    return dict(groups=1,variants=3,assertions=count)


def evidence_batch():
    count=0
    def check(ok):
        nonlocal count
        count+=1
        if not ok:raise AssertionError('226 evidence assertion failed')
    def denied(call):
        try:call()
        except ValueError:return True
        return False
    cap=stream_source.SOURCE_CAP;pool=stream_source.POOL_BYTES
    symbols=f'n226_source_slot R 0 {cap:x}\nn226_source_pool b 0 {pool:x}\nn226_control_storage B {42312:x} 2b0\nn226_stream_storage B {42736:x} 108\n'
    sections=f'[1] .rodata.n226_source PROGBITS 0000 1000 {cap:x} 00 A 0 0 4096\n[2] .bss.n226_source_pool NOBITS 0000 1000 {pool:x} 00 WA 0 0 4096\n'
    linked={'_text':0,'__start_rodata':4096,'n226_source_slot':4096,'__end_rodata':cap+4096,'__init_begin':cap+8192,'__initramfs_start':cap+8192,'__init_end':cap+24576,'n226_source_pool':cap+28672,'_end':cap+28672+pool}
    system_map=''.join(f'{value:x} R {name}\n'for name,value in linked.items())
    check(stream_source.target_layout(symbols,sections,system_map,cap+12288,12288)['source_readonly_noninit']is True)
    cmd=b'cmd_arch/arm64/mm/init.o := clang-14 -fno-strict-aliasing -fstack-usage -c -o arch/arm64/mm/.tmp_init.o synthetic/init.c\n'
    changed=stream_source.direct_page_owner((HERE/'v217_source_owner_kernel.c').read_bytes())
    check(str(stream_source.compiler_stack_path(cmd,'arch/arm64/mm/init.o'))=='arch/arm64/mm/.tmp_init.su'and b'mapped=page_address(page)'in changed and b'kunmap(page);'not in changed)
    check(denied(lambda:stream_source.target_layout(symbols,sections.replace('00 A ','00 WA '),system_map,cap+12288,12288)))
    check(denied(lambda:stream_source.compiler_stack_path(cmd.replace(b'arch/arm64/mm/.tmp_init.o',b'arch/arm64/mm/../.tmp_init.o'),'arch/arm64/mm/init.o')))
    leaf_table='memcpy T 0 8\nmemset T 10 8\nmemcmp T 20 8\n'
    data=dict(schema='note10-v226-selected-stack-evidence-v1',objects={},
        assembly={name:f'{16*index:x} <{name}>:\n {16*index:x}: d503201f nop\n {16*index+4:x}: d65f03c0 ret\n'for index,name in enumerate(('memcpy','memset','memcmp'))},
        assembly_symbols=stream_source.leaf_symbols(leaf_table),assembly_symbol_table_sha256=hashlib.sha256(leaf_table.encode()).hexdigest())
    for target,names in stream_source.STACK_TARGETS.items():
        relative=Path(target);output=relative.with_name('.tmp_'+relative.name).as_posix();command=f'cmd_{target} := clang-14 -fno-strict-aliasing -fstack-usage -c -o {output} synthetic.c\n'
        usage=''.join(f'synthetic.c:1:{name}\t16\tstatic\n'for name in names)
        elf='[1] .text PROGBITS 0 0 1000 00 AX 0 0 16\n'+''.join(f'{index}: 0000 4 FUNC GLOBAL DEFAULT 1 {name}\n'for index,name in enumerate(names,1))
        data['objects'][target]=dict(command=command,command_sha256=hashlib.sha256(command.encode()).hexdigest(),stack_usage=usage,
            stack_sha256=hashlib.sha256(usage.encode()).hexdigest(),stack_relative=str(Path(output).with_suffix('.su')).replace('\\','/'),
            elf_sections_and_symbols=elf,elf_evidence_sha256=hashlib.sha256(elf.encode()).hexdigest())
    check(stream_source.verify_stack_evidence(data)['selected_static_frame_sum']<=8192)
    bad=json.loads(json.dumps(data));item=bad['objects']['arch/arm64/mm/init.o'];item['stack_usage']=item['stack_usage'].replace('\t16\tstatic','\t16\tdynamic',1);item['stack_sha256']=hashlib.sha256(item['stack_usage'].encode()).hexdigest()
    check(denied(lambda:stream_source.verify_stack_evidence(bad)))
    bad=json.loads(json.dumps(data));item=bad['objects']['arch/arm64/mm/init.o'];item['stack_usage']=item['stack_usage'].replace('\t16\tstatic','\t8192\tstatic',1);item['stack_sha256']=hashlib.sha256(item['stack_usage'].encode()).hexdigest()
    check(denied(lambda:stream_source.verify_stack_evidence(bad)))
    check(denied(lambda:stream_source.assembly_leaf('0000 <memcpy>:\n 0: d10043ff sub sp, sp, #0x10\n',dict(symbol='memcpy',address=0,bytes=4,aliases=['memcpy']))))
    bad=json.loads(json.dumps(data));item=bad['objects']['arch/arm64/mm/init.o'];item['elf_sections_and_symbols']=item['elf_sections_and_symbols'].replace('.text PROGBITS','.init.text PROGBITS');item['elf_evidence_sha256']=hashlib.sha256(item['elf_sections_and_symbols'].encode()).hexdigest()
    check(denied(lambda:stream_source.verify_stack_evidence(bad)))
    check(denied(lambda:stream_source.assembly_leaf('no instructions\n',data['assembly_symbols']['memcpy'])))
    prepared=(HERE/'v210_native_prepare_kernel.c').read_bytes()
    overlaid=stream_source.prepare_owner(prepared)
    store=overlaid[overlaid.index(b'static ssize_t n210_write('):overlaid.index(b'static struct bin_attribute n210_dest_attr=')]
    check(hashlib.sha256(overlaid).hexdigest()==stream_source.PREPARE_POST_SHA and
        b'crypto_alloc_shash'not in store and b'SHASH_DESC_ON_STACK'not in store and
        store.count(b'mutex_trylock(&n210_lock)')==store.count(b'mutex_unlock(&n210_lock)')==1 and
        store.count(b'error=n226_prepare_hash(request.payload,hash);')==store.count(b'error=n226_ingest_prepared_locked(&request,&context);')==1 and
        store.index(b'error=n226_prepare_hash(')<store.index(b'error=n210_prepare_once(')<
        store.index(b'error=n226_ingest_prepared_locked(')<store.index(b'n226_emit(error);')<store.index(b'mutex_unlock(&n210_lock)'))
    check(denied(lambda:stream_source.prepare_owner(prepared.replace(b'mutex_trylock(&n210_lock)',b'mutex_lock(&n210_lock)',1))))
    internal='1000 <__memcpy>:\n 1000: b4000042 cbz x2, 1008 <__memcpy+0x8>\n 1004: 17ffffff b 1000 <__memcpy>\n 1008: d65f03c0 ret\n'
    symbol=stream_source.leaf_symbols('memcpy W 1000 c\n__memcpy T 1000 c\nmemset W 2000 4\nmemcmp T 3000 4\n')['memcpy']
    check(stream_source.assembly_leaf(internal,symbol)['direct_branches']==2)
    short=dict(symbol='memcpy',address=0x1000,bytes=4,aliases=['memcpy'])
    check(denied(lambda:stream_source.assembly_leaf('1000 <memcpy>:\n 1000: 14000004 b 1010 <helper>\n',short))and
        denied(lambda:stream_source.assembly_leaf('1000 <memcpy>:\n 1000: d61f0020 br x1\n',short))and
        denied(lambda:stream_source.assembly_leaf('1000 <unbound>:\n 1000: d65f03c0 ret\n',short)))
    return dict(groups=1,variants=7,assertions=count)
