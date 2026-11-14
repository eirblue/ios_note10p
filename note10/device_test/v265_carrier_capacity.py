"""One closed compiled holder change; old repository carrier sources remain intact."""
import hashlib
import re
import struct
OLD_CAP=6209536
SOURCE_CAP=6213860
POOL_BYTES=49152
KERNEL_CAP=19169280
RAW_CAP=19186176
HEADER_BYTES=96
MEMBER_BYTES=6213764
HEADER_PRE_SHA='2207009c47adc326538e007702c2f3d1fd8248f0f2b3ac9c81832c4e24f07ebd'
STREAM_PRE_SHA='f446d66b54b647d6aaeb4c398fd1149d3ce08252303df605b5859e275168ccfb'

def require(ok,message):
    if not ok:raise ValueError(message)
def sha(raw):return hashlib.sha256(raw).hexdigest()

def overlay(header,stream):
    require(sha(header)==HEADER_PRE_SHA and sha(stream)==STREAM_PRE_SHA,'exact installed241 source preimages')
    define=b'#define N226_SOURCE_CAP 6209536\n'
    before=b'"n226_source_slot:\\n.zero 6209536\\n.size n226_source_slot,6209536\\n.popsection\\n");'
    require(header.count(define)==stream.count(before)==1,'one exact cap declaration and assembler extent')
    header=header.replace(define,b'#ifndef N226_SOURCE_CAP\n'+define+b'#endif\n',1)
    prefix=b'extern const n209_u8 n226_source_slot[N226_SOURCE_CAP];'
    require(stream.count(prefix)==1,'one holder declaration')
    stream=stream.replace(prefix,b'#define N265_STRING1(x) #x\n#define N265_STRING(x) N265_STRING1(x)\n'+prefix,1)
    after=b'"n226_source_slot:\\n.zero " N265_STRING(N226_SOURCE_CAP) "\\n.size n226_source_slot," N265_STRING(N226_SOURCE_CAP) "\\n.popsection\\n");'
    return header,stream.replace(before,after,1)

def install(source,preparation,ordinary):
    from pathlib import Path
    directory=Path(source)/'arch/arm64/mm';header=directory/'native_source_stream.h';stream=directory/'v226_source_stream_kernel.c'
    first,second=ordinary(header),ordinary(stream);changed_header,changed_stream=overlay(first,second)
    header.write_bytes(changed_header);stream.write_bytes(changed_stream)
    preparation['capacity_overlay']=dict(default_holder_bytes=OLD_CAP,compiled_holder_bytes=SOURCE_CAP,named_native_resident_bytes=SOURCE_CAP+POOL_BYTES,KCFLAGS='-DN226_SOURCE_CAP=6213860',source_preimages=dict(header=sha(first),stream=sha(second)),source_postimages=dict(header=sha(changed_header),stream=sha(changed_stream)),public_sources_changed=False)
    return preparation

def reader_fit(kernel_span,member_bytes,raw_bytes):
    require(all(type(x)is int for x in (kernel_span,member_bytes,raw_bytes))and 0<kernel_span<=KERNEL_CAP and kernel_span%16384==0 and 18<=member_bytes<=SOURCE_CAP-HEADER_BYTES and raw_bytes==((kernel_span+16384+496+511)&~511)and raw_bytes<=RAW_CAP,'exact measured265 compiled holder limits')
    return dict(kernel_span=kernel_span,adapter_bytes=16384,member_bytes=member_bytes,raw_newc_bytes=raw_bytes,source_holder_bytes=SOURCE_CAP,source_zero_tail_bytes=SOURCE_CAP-HEADER_BYTES-member_bytes,compiled_reader_fit=True)

def retained_binding(received,progress,parcel,expected):
    require(set(expected)=={'member_sha256','descriptor_sha256','member_bytes','kernel_span','raw_newc_bytes'}and expected['member_bytes']==MEMBER_BYTES and expected['kernel_span']==KERNEL_CAP and expected['raw_newc_bytes']==RAW_CAP and all(re.fullmatch('[0-9a-f]{64}',expected[k])for k in ('member_sha256','descriptor_sha256')),'reviewed exact retained-input expectation')
    require(all(received[k]is True for k in ('passed','authenticated','producer_passed','capture_passed','final_passed','candidate_usable')),'actual retained264 native success')
    require(progress['completed']is progress['member_hash_complete']is True and progress['compressions']==1 and progress['member_bytes']==MEMBER_BYTES and progress['member_sha256']==expected['member_sha256'] and progress['uncompressed_newc_bytes']==RAW_CAP,'actual completed retained264 member')
    require(parcel['schema']=='note10-v264-native-capture-receipt-source-parcel-v1'and parcel['kernel_materialized_bytes']==KERNEL_CAP and parcel['descriptor_sha256']==expected['descriptor_sha256'] and parcel['kernel_sha256']==received['members']['kernel/note10-experimental.macho']['sha256']and all(progress['inputs'][n]['EOF_verified']is progress['inputs'][n]['hash_complete']is True for n in ('kernel.mem','adapter.mem'))and progress['inputs']['kernel.mem']['sha256']==parcel['kernel_materialized_sha256'],'retained native/member/descriptor join without another materialization')
    return reader_fit(KERNEL_CAP,MEMBER_BYTES,RAW_CAP)

def target_layout(symbols,sections,system_map,image_bytes,cpio_bytes):
    require(type(symbols)is type(sections)is type(system_map)is str and type(image_bytes)is type(cpio_bytes)is int and
        4096<cpio_bytes<=65536+8192,'typed actual layout evidence required')
    rows=[line.split()for line in symbols.splitlines()if line.strip()]
    expected={'n226_source_slot':(SOURCE_CAP,('R','r')),'n226_source_pool':(POOL_BYTES,('B','b')),
              'n226_control_storage':(688,('B','b')),'n226_stream_storage':(264,('B','b'))}
    owned={}
    for name,(size,kinds)in expected.items():
        found=[row for row in rows if row[0]==name]
        require(len(found)==1 and len(found[0])==4 and found[0][1]in kinds and int(found[0][3],16)==size,'actual bounded source/pool/type symbol required: '+name)
        owned[name]=int(found[0][2],16)
    require(owned['n226_source_slot']%4096==owned['n226_source_pool']%4096==0 and
        owned['n226_control_storage']==owned['n226_source_pool']+42312 and owned['n226_stream_storage']==owned['n226_source_pool']+42736,'actual pool aliases/alignment required')
    parsed={}
    for line in sections.splitlines():
        match=re.search(r'\[\s*\d+\]\s+(\S+)\s+(\S+)\s+[0-9a-fA-F]+\s+[0-9a-fA-F]+\s+([0-9a-fA-F]+)\s+[0-9a-fA-F]+\s+([A-Z]+)\s+\d+\s+\d+\s+(\d+)',line)
        if match:
            name,kind,size,flags,align=match.groups()
            require(name not in parsed,'unique ELF section required');parsed[name]=(kind,int(size,16),flags,int(align))
    require(parsed.get('.rodata.n226_source')==('PROGBITS',SOURCE_CAP,'A',4096) and
        parsed.get('.bss.n226_source_pool')==('NOBITS',POOL_BYTES,'WA',4096),'one actual readonly source/noninit BSS pool section required')
    names={'_text','_end','__start_rodata','__end_rodata','__init_begin','__init_end','__initramfs_start','n226_source_slot','n226_source_pool'}
    linked={}
    for line in system_map.splitlines():
        row=line.split()
        if len(row)==3 and row[2]in names:
            require(row[2]not in linked,'one actual linked section boundary required');linked[row[2]]=int(row[0],16)
    require(set(linked)==names and linked['__start_rodata']<=linked['n226_source_slot'] and
        linked['n226_source_slot']+SOURCE_CAP<=linked['__end_rodata']<=linked['__init_begin']<linked['__init_end']<=linked['n226_source_pool'] and
        linked['n226_source_pool']+POOL_BYTES<=linked['_end'] and linked['__init_begin']<=linked['__initramfs_start'] and
        linked['__initramfs_start']+cpio_bytes<=linked['__init_end'],'source/pool must survive initmem release without overlap')
    offset=linked['n226_source_slot']-linked['_text']
    require(type(image_bytes)is int and 64<=offset<=image_bytes-SOURCE_CAP and type(cpio_bytes)is int and 4096<cpio_bytes<=65536+8192,'source file extent/small metadata initramfs required')
    return dict(schema='note10-v265-resident-source-layout-v1',source_holder_offset=offset,source_holder_bytes=SOURCE_CAP,
        fixed_pool_bytes=POOL_BYTES,control_bytes=688,stream_bytes=264,internal_request_offset=43000,internal_request_bytes=496,
        stats_offset=43496,stats_bytes=48,stage_offset=45056,stage_bytes=4096,named_native_resident_bytes=SOURCE_CAP+POOL_BYTES,
        old_large_initramfs_slot_present=False,source_readonly_noninit=True,pool_noninit=True,
        linked_noninit_extent=linked['_end']-linked['_text']-(linked['__init_end']-linked['__init_begin']),linked_symbols=linked,hardware_authorized=False)

def insert(image,build,descriptor,member,member_sha,cycle,fit,private_member):
    require(type(image)is bytes and type(descriptor)is bytes and len(descriptor)==256 and type(member)is bytes and member[:4]==b'\x1f\x8b\x08\x00'and sha(member)==member_sha,'actual new descriptor/member')
    span=struct.unpack_from('<Q',descriptor,24)[0]
    require(reader_fit(span,len(member),fit['raw_newc_bytes'])==fit,'measured current member fit')
    meta,size,marker,source,capacity=(build[k]for k in ('slot_offset','slot_bytes','cycle_offset','source_holder_offset','source_holder_bytes'))
    require(all(type(x)is int for x in (meta,size,marker,source,capacity))and size==4096 and capacity==SOURCE_CAP and all(64<=a and a+z<=len(image)for a,z in ((meta,size),(marker,33),(source,capacity))),'fixed241 insertion geometry')
    intervals=sorted(((meta,meta+size),(source,source+capacity),(marker,marker+33)))
    require(all(a[1]<=b[0]for a,b in zip(intervals,intervals[1:]))and not any(image[meta:meta+size])and not any(image[source:source+capacity]),'disjoint original zero carrier slots')
    require(re.fullmatch('[0-9a-f]{32}',cycle)and image[marker:marker+33]==b'N10_CYCLE_SLOT_UNSET_0123456789A'+b'\0'and image.count(b'N10_CYCLE_SLOT_UNSET_0123456789A'+b'\0')==1,'original cycle placeholder')
    metadata,binding=private_member(descriptor,build['build_evidence_id'],cycle)
    require(len(metadata)<=4096 and len(binding)==128,'existing metadata/binding ABI')
    header=struct.pack('<8sIIQQ32s32s',b'N226SRC1',1,96,len(member),fit['raw_newc_bytes'],bytes.fromhex(member_sha),bytes.fromhex(sha(descriptor)))
    changed=bytearray(image);changed[meta:meta+size]=metadata+bytes(size-len(metadata));changed[source:source+capacity]=header+member+bytes(capacity-96-len(member));changed[marker:marker+32]=cycle.encode()
    return bytes(changed),binding
