"""Three new coupled-bound verdicts; one compiled staged-C invocation only."""
from copy import deepcopy
from pathlib import Path
import json,struct,subprocess
CASES=('actual_C_kernel_span','actual_C_raw_header','host_compiled_triple_join')
STAGED=('native_source_stream.h','native_source_stream.c','native_source_sha256.h','native_source_sha256.c','native_source_ingest.h','native_prepare_core.h','native_parcel_core.h','native_parcel_core.c')

def reject(call):
    try:call()
    except (ValueError,KeyError):return True
    return False

def host_join(cap,compiled):
    if compiled!=dict(source=cap.SOURCE_CAP,kernel=cap.KERNEL_CAP,raw=cap.RAW_CAP):return False
    member=b'\x1f\x8b\x08\0'+b'own synthetic payload '*((cap.MEMBER_BYTES-4)//22+1);member=member[:cap.MEMBER_BYTES]
    if len(member)!=cap.MEMBER_BYTES:return False
    descriptor=bytearray(256);struct.pack_into('<Q',descriptor,24,cap.KERNEL_CAP);descriptor=bytes(descriptor)
    geometry=dict(virtual_base=0x4000,kernel_span=cap.KERNEL_CAP,kernel_entry_offset=0,entry_extent_offset=0,entry_extent_bytes=4,pool_offset=0x4000,pool_bytes=163840);adapter=dict(bytes=16384,entry_offset=0,record_offset=256,sha256='e'*64)
    expected=dict(member_sha256=cap.sha(member),descriptor_sha256=cap.sha(descriptor),member_bytes=len(member),kernel_span=cap.KERNEL_CAP,raw_newc_bytes=cap.RAW_CAP,geometry=geometry,adapter=adapter)
    received=dict(passed=True,authenticated=True,producer_passed=True,capture_passed=True,final_passed=True,candidate_usable=True,members={'kernel/note10-experimental.macho':dict(sha256='a'*64)})
    parcel=dict(schema='note10-v266-genuine-block-driver-source-parcel-v1',kernel_sha256='a'*64,kernel_materialized_bytes=cap.KERNEL_CAP,kernel_materialized_sha256='d'*64,descriptor_sha256=cap.sha(descriptor),geometry=geometry,adapter_bytes=16384,adapter_entry_offset=0,adapter_record_offset=256,adapter_sha256='e'*64)
    progress=dict(completed=True,member_hash_complete=True,compressions=1,member_bytes=len(member),member_sha256=cap.sha(member),uncompressed_newc_bytes=cap.RAW_CAP,inputs={n:dict(EOF_verified=True,hash_complete=True,sha256='d'*64)for n in ('kernel.mem','adapter.mem')})
    fit=cap.retained_binding(received,progress,parcel,expected)
    image=bytearray(cap.SOURCE_CAP+32768);offset=4096;meta=offset+cap.SOURCE_CAP;marker=meta+4096;image[marker:marker+33]=b'N10_CYCLE_SLOT_UNSET_0123456789A\0';image=bytes(image)
    build=dict(slot_offset=meta,slot_bytes=4096,cycle_offset=marker,source_holder_offset=offset,source_holder_bytes=cap.SOURCE_CAP,build_evidence_id='a'*32)
    enabled,binding=cap.insert(image,build,descriptor,member,cap.sha(member),'b'*32,fit,lambda *args:(b'own metadata',bytes(128)))
    bad_descriptor=bytearray(descriptor);struct.pack_into('<Q',bad_descriptor,24,19169280)
    text=0x100000;slot=text+4096;init=(slot+cap.SOURCE_CAP+8191)&~4095;endinit=init+8192;pool=endinit;end=pool+cap.POOL_BYTES
    symbols='\n'.join((f'n226_source_slot R {slot:x} {cap.SOURCE_CAP:x}',f'n226_source_pool B {pool:x} {cap.POOL_BYTES:x}',f'n226_control_storage B {pool+42312:x} {688:x}',f'n226_stream_storage B {pool+42736:x} {264:x}'))
    sections=f'[1] .rodata.n226_source PROGBITS 00000000 00000000 {cap.SOURCE_CAP:x} 00 A 0 0 4096\n[2] .bss.n226_source_pool NOBITS 00000000 00000000 {cap.POOL_BYTES:x} 00 WA 0 0 4096'
    linked=dict(_text=text,_end=end,__start_rodata=slot,__end_rodata=init,__init_begin=init,__init_end=endinit,__initramfs_start=init,n226_source_slot=slot,n226_source_pool=pool);system='\n'.join(f'{v:x} T {n}'for n,v in linked.items());layout=cap.target_layout(symbols,sections,system,len(image),8192)
    changed=deepcopy(parcel);changed['descriptor_sha256']='f'*64
    return fit['source_zero_tail_bytes']==0 and layout['source_holder_bytes']==cap.SOURCE_CAP and layout['compiled_kernel_cap']==cap.KERNEL_CAP and layout['compiled_raw_cap']==cap.RAW_CAP and struct.unpack_from('<Q',enabled,offset+24)[0]==cap.RAW_CAP and len(binding)==128 and reject(lambda:cap.insert(image,build,bytes(bad_descriptor),member,cap.sha(member),'b'*32,fit,lambda *args:(b'x',bytes(128))))and reject(lambda:cap.insert(image,dict(build,source_holder_bytes=6213860),descriptor,member,cap.sha(member),'b'*32,fit,lambda *args:(b'x',bytes(128))))and reject(lambda:cap.reader_fit(cap.KERNEL_CAP,cap.MEMBER_BYTES+1,cap.RAW_CAP))and reject(lambda:cap.retained_binding(received,progress,changed,expected))

def run(output,cap,parameters):
    output=Path(output);root=Path(__file__).resolve().parent;stage=output/'staged-source';stage.mkdir(exist_ok=False);done=[]
    def save(name,data):(output/name).write_text(json.dumps(data,indent=2)+'\n')
    try:
        for name in STAGED:(stage/name).write_bytes((root/name).read_bytes())
        header,reader=cap.reader_overlay((stage/'native_source_stream.h').read_bytes(),(stage/'native_source_stream.c').read_bytes());(stage/'native_source_stream.h').write_bytes(header);(stage/'native_source_stream.c').write_bytes(reader)
        save('STAGED-READER.json',dict(header_sha256=cap.sha(header),reader_sha256=cap.sha(reader),caps=dict(source=cap.SOURCE_CAP,kernel=cap.KERNEL_CAP,raw=cap.RAW_CAP),old_public_files_changed=False))
        argv=parameters['compiler_argv'];save('COMPILE-STARTED.json',dict(argv=argv,attempt=1))
        with(output/'compiler.stdout').open('xb')as out,(output/'compiler.stderr').open('xb')as err:compiled=subprocess.run(argv,cwd=output,stdout=out,stderr=err,timeout=120)
        if compiled.returncode:raise ValueError('new staged C compile failed')
        exe=output/'coupled-bounds-fixture.exe';save('C-FIXTURE-STARTED.json',dict(argv=[str(exe)],attempt=1))
        with(output/'fixture.stdout').open('xb')as out,(output/'fixture.stderr').open('xb')as err:called=subprocess.run([str(exe)],cwd=output,stdout=out,stderr=err,timeout=60)
        raw=(output/'fixture.stdout').read_bytes();lines=raw.replace(b'\r\n',b'\n').splitlines();expected=[b'N267CAPS source=6237242 kernel=19283968 raw=19300864',b'N267CASE kernel-span=PASS',b'N267CASE raw-header=PASS']
        if not lines or lines[0]!=expected[0]:raise ValueError('actual compiled triple mismatch')
        for index in (1,2):
            if len(lines)<=index or lines[index]!=expected[index]:raise ValueError('actual new C guard failed')
            done.append(CASES[index-1])
        if called.returncode or lines!=expected:raise ValueError('bounded C process failed or emitted foreign evidence')
        if host_join(cap,dict(source=6237242,kernel=19283968,raw=19300864))is not True:raise ValueError('new host/C triple join failed')
        done.append(CASES[2])
    except BaseException as error:error.fixture_progress=dict(groups=1,variants=3,assertions=len(done),planned_assertions=3,completed_variants=len(done),completed_assertions=len(done),case_names=done);raise
    return dict(groups=1,variants=3,assertions=3,completed_variants=3,completed_assertions=3,case_names=done,host_compile_attempts=1,host_fixture_process_attempts=1,old_tests_replayed=0)
