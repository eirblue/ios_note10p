"""Closed new reader triple; only fresh copied-tree files change."""
import hashlib,re,struct
from pathlib import Path
from types import FunctionType
import v265_carrier_capacity as retained
SOURCE_CAP=6237242
KERNEL_CAP=19283968
RAW_CAP=19300864
MEMBER_BYTES=6237146
HEADER_BYTES=96
POOL_BYTES=49152
HEADER_PRE_SHA=retained.HEADER_PRE_SHA
READER_PRE_SHA='0a25696f8d79d067868e1d119cfa4754e43747ae13890ab8658a12a3c29751d5'
FLAGS=('-DN226_SOURCE_CAP=6237242','-DN226_KERNEL_CAP=19283968ULL','-DN226_RAW_CAP=19300864ULL')

def require(ok,message):
    if not ok:raise ValueError(message)
def sha(raw):return hashlib.sha256(raw).hexdigest()

def reader_overlay(header,reader):
    require(sha(header)==HEADER_PRE_SHA and sha(reader)==READER_PRE_SHA,'exact default reader/header source preimages')
    source=b'#define N226_SOURCE_CAP 6209536\n';raw=b'#define N226_RAW_CAP 19186176ULL\n';guard=b'decoded.kernel_span>19169280ULL'
    require(header.count(source)==header.count(raw)==reader.count(guard)==1,'one exact definition and kernel-span guard')
    header=header.replace(source,b'#ifndef N226_SOURCE_CAP\n'+source+b'#endif\n',1)
    header=header.replace(raw,b'#ifndef N226_KERNEL_CAP\n#define N226_KERNEL_CAP 19169280ULL\n#endif\n#ifndef N226_RAW_CAP\n'+raw+b'#endif\n',1)
    return header,reader.replace(guard,b'decoded.kernel_span>N226_KERNEL_CAP',1)

def install(source,preparation,ordinary):
    directory=Path(source)/'arch/arm64/mm';paths={n:directory/n for n in ('native_source_stream.h','native_source_stream.c','v226_source_stream_kernel.c')};before={n:ordinary(p)for n,p in paths.items()}
    header,reader=reader_overlay(before['native_source_stream.h'],before['native_source_stream.c'])
    ignored,wrapper=retained.overlay(before['native_source_stream.h'],before['v226_source_stream_kernel.c'])
    after=dict(zip(paths,(header,reader,wrapper)))
    for name,p in paths.items():p.write_bytes(after[name])
    preparation['capacity_overlay']=dict(default_holder_bytes=6209536,default_kernel_cap=19169280,default_raw_cap=19186176,compiled_holder_bytes=SOURCE_CAP,compiled_kernel_cap=KERNEL_CAP,compiled_raw_cap=RAW_CAP,named_native_resident_bytes=SOURCE_CAP+POOL_BYTES,KCFLAGS=list(FLAGS),source_preimages={n:sha(v)for n,v in before.items()},source_postimages={n:sha(v)for n,v in after.items()},public_sources_changed=False)
    return preparation

def reader_fit(kernel_span,member_bytes,raw_bytes):
    require(all(type(v)is int for v in (kernel_span,member_bytes,raw_bytes))and 0<kernel_span<=KERNEL_CAP and kernel_span%16384==0 and 18<=member_bytes<=SOURCE_CAP-96 and raw_bytes==((kernel_span+16384+496+511)&~511)and raw_bytes<=RAW_CAP,'exact new three coupled reader bounds')
    return dict(kernel_span=kernel_span,adapter_bytes=16384,member_bytes=member_bytes,raw_newc_bytes=raw_bytes,source_holder_bytes=SOURCE_CAP,source_zero_tail_bytes=SOURCE_CAP-96-member_bytes,compiled_reader_fit=True)

def target_layout(*args):
    run=FunctionType(retained.target_layout.__code__,{**retained.__dict__,'SOURCE_CAP':SOURCE_CAP},'new_triple_layout')
    value=run(*args);value.update(schema='note10-v267-resident-source-layout-v1',compiled_kernel_cap=KERNEL_CAP,compiled_raw_cap=RAW_CAP);return value

def insert(image,build,descriptor,member,member_sha,cycle,fit,private_member):
    run=FunctionType(retained.insert.__code__,{**retained.__dict__,'SOURCE_CAP':SOURCE_CAP,'reader_fit':reader_fit},'new_triple_insert')
    return run(image,build,descriptor,member,member_sha,cycle,fit,private_member)

def retained_binding(received,progress,parcel,expected):
    require(set(expected)=={'member_sha256','descriptor_sha256','member_bytes','kernel_span','raw_newc_bytes','geometry','adapter'}and(expected['member_bytes'],expected['kernel_span'],expected['raw_newc_bytes'])==(MEMBER_BYTES,KERNEL_CAP,RAW_CAP),'exact retained266 reviewed expectation')
    require(all(received[k]is True for k in ('passed','authenticated','producer_passed','capture_passed','final_passed','candidate_usable'))and parcel['schema']=='note10-v266-genuine-block-driver-source-parcel-v1','actual authenticated266 native origin')
    require(progress['completed']is progress['member_hash_complete']is True and progress['compressions']==1 and progress['member_bytes']==MEMBER_BYTES and progress['member_sha256']==expected['member_sha256']and progress['uncompressed_newc_bytes']==RAW_CAP and parcel['descriptor_sha256']==expected['descriptor_sha256']and parcel['kernel_materialized_bytes']==KERNEL_CAP,'completed once-only266 member/descriptor/span')
    require(parcel['kernel_sha256']==received['members']['kernel/note10-experimental.macho']['sha256']and all(progress['inputs'][n]['EOF_verified']is progress['inputs'][n]['hash_complete']is True for n in ('kernel.mem','adapter.mem'))and progress['inputs']['kernel.mem']['sha256']==parcel['kernel_materialized_sha256'],'exact native/memory/member input joins')
    require(parcel['geometry']==expected['geometry']and expected['geometry']['kernel_span']==KERNEL_CAP and parcel['adapter_bytes']==expected['adapter']['bytes']==16384 and parcel['adapter_entry_offset']==expected['adapter']['entry_offset']==0 and parcel['adapter_record_offset']==expected['adapter']['record_offset']==256 and parcel['adapter_sha256']==expected['adapter']['sha256'],'reviewed exact new geometry/unchanged adapter; no execution authority')
    return reader_fit(KERNEL_CAP,MEMBER_BYTES,RAW_CAP)
