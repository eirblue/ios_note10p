"""Four new capacity boundaries only; no compression/native/old fixture replay."""
from copy import deepcopy
import hashlib
from pathlib import Path
from unittest.mock import patch
CASE_NAMES=('isolated_overlay_preserves_old_default','exact_new_holder_fit_boundary','actual_readonly_layout_bound','retained264_input_join_no_new_stream')
def reject(call):
    try:call()
    except (ValueError,KeyError):return True
    return False

def overlay_boundary(cap):
    header=b'#define N226_SOURCE_CAP 6209536\n#define OWN_UNCHANGED 1\n'
    stream=b'extern const n209_u8 n226_source_slot[N226_SOURCE_CAP];\n"n226_source_slot:\\n.zero 6209536\\n.size n226_source_slot,6209536\\n.popsection\\n");'
    with patch.object(cap,'HEADER_PRE_SHA',cap.sha(header)),patch.object(cap,'STREAM_PRE_SHA',cap.sha(stream)):
        changed_header,changed_stream=cap.overlay(header,stream);bad=reject(lambda:cap.overlay(header+b'own drift',stream))
    return b'#ifndef N226_SOURCE_CAP\n#define N226_SOURCE_CAP 6209536\n#endif\n'in changed_header and changed_header.endswith(b'#define OWN_UNCHANGED 1\n')and changed_stream.count(b'N265_STRING(N226_SOURCE_CAP)')==2 and b'.zero 6209536'not in changed_stream and bad

def fit_boundary(cap):
    fit=cap.reader_fit(cap.KERNEL_CAP,cap.MEMBER_BYTES,cap.RAW_CAP)
    return fit['source_holder_bytes']==6213860 and fit['source_zero_tail_bytes']==0 and all(reject(lambda args=args:cap.reader_fit(*args))for args in ((cap.KERNEL_CAP,cap.MEMBER_BYTES+1,cap.RAW_CAP),(cap.KERNEL_CAP+16384,cap.MEMBER_BYTES,cap.RAW_CAP),(cap.KERNEL_CAP,cap.MEMBER_BYTES,cap.RAW_CAP+512)))

def layout_boundary(cap):
    text=0x100000;slot=text+4096;init=(slot+cap.SOURCE_CAP+8191)&~4095;endinit=init+8192;pool=endinit;end=pool+cap.POOL_BYTES
    syms='\n'.join((f'n226_source_slot R {slot:x} {cap.SOURCE_CAP:x}',f'n226_source_pool B {pool:x} {cap.POOL_BYTES:x}',f'n226_control_storage B {pool+42312:x} {688:x}',f'n226_stream_storage B {pool+42736:x} {264:x}'))
    sections=f'[1] .rodata.n226_source PROGBITS 00000000 00000000 {cap.SOURCE_CAP:x} 00 A 0 0 4096\n[2] .bss.n226_source_pool NOBITS 00000000 00000000 {cap.POOL_BYTES:x} 00 WA 0 0 4096'
    values=dict(_text=text,_end=end,__start_rodata=slot,__end_rodata=init,__init_begin=init,__init_end=endinit,__initramfs_start=init,n226_source_slot=slot,n226_source_pool=pool);system='\n'.join(f'{v:x} T {n}'for n,v in values.items());size=cap.SOURCE_CAP+65536
    result=cap.target_layout(syms,sections,system,size,8192)
    return result['source_holder_bytes']==6213860 and result['named_native_resident_bytes']==6263012 and reject(lambda:cap.target_layout(syms.replace(f'{slot:x} {cap.SOURCE_CAP:x}',f'{slot:x} {cap.SOURCE_CAP-1:x}'),sections,system,size,8192))and reject(lambda:cap.target_layout(syms,sections.replace('00 A 0 0','00 WA 0 0'),system,size,8192))

def retained_boundary(cap):
    received=dict(passed=True,authenticated=True,producer_passed=True,capture_passed=True,final_passed=True,candidate_usable=True,members={'kernel/note10-experimental.macho':dict(sha256='a'*64)})
    progress=dict(completed=True,member_hash_complete=True,compressions=1,member_bytes=cap.MEMBER_BYTES,member_sha256='b'*64,uncompressed_newc_bytes=cap.RAW_CAP,inputs={n:dict(EOF_verified=True,hash_complete=True,sha256='d'*64)for n in ('kernel.mem','adapter.mem')})
    parcel=dict(schema='note10-v264-native-capture-receipt-source-parcel-v1',kernel_materialized_bytes=cap.KERNEL_CAP,descriptor_sha256='c'*64,kernel_sha256='a'*64,kernel_materialized_sha256='d'*64)
    expected=dict(member_sha256='b'*64,descriptor_sha256='c'*64,member_bytes=cap.MEMBER_BYTES,kernel_span=cap.KERNEL_CAP,raw_newc_bytes=cap.RAW_CAP)
    fit=cap.retained_binding(received,progress,parcel,expected);bad=deepcopy(progress);bad['member_sha256']='f'*64;failed=dict(received,capture_passed=False)
    return fit['compiled_reader_fit']is True and reject(lambda:cap.retained_binding(received,bad,parcel,expected))and reject(lambda:cap.retained_binding(failed,progress,parcel,expected))

def run(output,cap):
    done=[]
    try:
        for name,predicate in ((CASE_NAMES[0],lambda:overlay_boundary(cap)),(CASE_NAMES[1],lambda:fit_boundary(cap)),(CASE_NAMES[2],lambda:layout_boundary(cap)),(CASE_NAMES[3],lambda:retained_boundary(cap))):
            if predicate()is not True:raise ValueError('new capacity boundary: '+name)
            done.append(name)
    except BaseException as error:error.fixture_progress=dict(groups=1,variants=4,assertions=len(done),planned_assertions=4,completed_variants=len(done),completed_assertions=len(done),case_names=done);raise
    return dict(groups=1,variants=4,assertions=4,completed_variants=4,completed_assertions=4,case_names=done,host_compile_attempts=0,host_fixture_process_attempts=0,old_tests_replayed=0)
