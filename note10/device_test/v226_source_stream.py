"""226 fixed embedded stream layout, fresh-source overlays and same-Image evidence."""
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import shlex
import struct
from v130_slot import newc
import v225_native_prepare as retained
require,sha=retained.require,retained.sha
SOURCE_CAP=6209536
POOL_BYTES=49152
METADATA_BYTES=4096
MEMBER_BYTES=6208928
UNCOMPRESSED_BYTES=19186176
PREPARE_SHA='80e662c029d69e9f1a5219fbdc5e6a15c0c48560f7324fa163912d59317fd59d'
PREPARE_POST_SHA='6b6ce13122575a66c40cd2d1d1adec68fe78e8eae2bcd5ecdcdcd14f688e3cb8'
PAGE_SHA='8bf23ac47ce4429b2b30d34b8809fcb7ecf66b07388385ef92902de5552ba596'
PAGE_POST_SHA='3a12bbe460be26edf90f5e91375858ccd64a239298a7e8ae508834e8fecf0d0a'
ROOT=Path(__file__).resolve().parents[2]
HERE=ROOT/'note10/device_test'


def prepare_owner(raw):
    require(type(raw)is bytes and sha(raw)==PREPARE_SHA,'exact210 prepare input required')
    changed=raw.replace(b'#include "native_prepare_core.h"\n',b'#include "native_prepare_core.h"\n#include "native_source_stream.h"\nstatic int n226_prepare_hash(const n209_u8 *,n209_u8 *);\nstatic int n226_ingest_prepared_locked(const struct n210_request *,const struct n210_context *);\nstatic __always_inline void n226_emit(int);\n',1)
    changed=changed.replace(b'struct n210_request request;struct n210_context context;struct crypto_shash *tfm;',b'struct n210_request request;struct n210_context context;',1)
    begin=changed.index(b'    tfm=crypto_alloc_shash("sha256",0,0);');end=changed.index(b'    crypto_free_shash(tfm);\n',begin)+len(b'    crypto_free_shash(tfm);\n')
    changed=changed[:begin]+b'    error=n226_prepare_hash(request.payload,hash);\n'+changed[end:]
    anchor=b' out:\n    mutex_unlock(&n210_lock);return error?error:(ssize_t)count;'
    require(changed.count(anchor)==1,'one locked store return required')
    changed=changed.replace(anchor,b'    if(!error){error=n226_ingest_prepared_locked(&request,&context);n226_emit(error);}\n'+anchor,1)
    require(sha(changed)==PREPARE_POST_SHA and b'SHASH_DESC_ON_STACK'not in changed and b'crypto_alloc_shash'not in changed,'closed directSHA/single-lock source postimage required')
    return changed


def direct_page_owner(raw):
    require(type(raw)is bytes and sha(raw)==PAGE_SHA,'exact217 page owner source required')
    before=b'mapped=kmap(page);if(!mapped)return -ENOMEM;';after=b'mapped=page_address(page);if(!mapped)return -ENOMEM;'
    require(raw.count(before)==raw.count(b'kunmap(page);return 0;')==1,'one217 lowmem mapping seam required')
    changed=raw.replace(before,after,1).replace(b'kunmap(page);return 0;',b'return 0;',1)
    require(sha(changed)==PAGE_POST_SHA,'exact equivalent lowmem pointer postimage required')
    return changed


def install(source,identity,buffers,parser_sha):
    result=retained.install(source,identity,buffers,parser_sha)
    main=source/'arch/arm64/mm/init.c';raw=retained.p.ordinary(main);anchor=b'#include "v219_source_owner_kernel.c"\n#endif\n'
    require(raw.count(anchor)==1,'one shared225 owner inclusion seam required')
    changed=raw.replace(anchor,anchor.replace(b'#endif\n',b'#include "native_source_stream.c"\n#include "v226_source_stream_kernel.c"\n#endif\n'),1);main.write_bytes(changed)
    for name in ('native_source_stream.h','native_source_stream.c','v226_source_stream_kernel.c'):
        (main.parent/name).write_bytes(buffers['note10/device_test/'+name])
    prepare=main.parent/'v210_native_prepare_kernel.c';before=retained.p.ordinary(prepare);after=prepare_owner(before);prepare.write_bytes(after)
    page=main.parent/'v217_source_owner_kernel.c';page_before=retained.p.ordinary(page);page_after=direct_page_owner(page_before);page.write_bytes(page_after)
    result['source_stream_overlay']=dict(main_before_sha256=sha(raw),main_after_sha256=sha(changed),prepare_before_sha256=sha(before),prepare_after_sha256=sha(after),
        page_before_sha256=sha(page_before),page_after_sha256=sha(page_after),page_pointer='page_address',page_mapping_changed=False,
        source_sha256={name:sha(buffers['note10/device_test/'+name])for name in ('native_source_stream.h','native_source_stream.c','v226_source_stream_kernel.c')},
        source_holder_bytes=SOURCE_CAP,fixed_pool_bytes=POOL_BYTES,metadata_slot_bytes=METADATA_BYTES,compiled_ingestion_callers=1,hardware_authorized=False)
    return result


def generic(init):
    require(64<=len(init)<=65536 and init[:6]==b'\x7fELF\x02\x01' and init[18:20]==b'\xb7\0' and init.count(b'N10MININIT2:N226REQUEST')==1,'fresh226 log-only PID1 required')
    prefix=newc([('dev',0o040755,b'',0,0),('sys',0o040755,b'',0,0),('n10',0o040700,b'',0,0),
        ('dev/console',0o020600,b'',5,1),('dev/kmsg',0o020600,b'',1,11),('init',0o100755,init,0,0)])
    prefix+=bytes(-len(prefix)%512)
    return prefix+bytes(METADATA_BYTES),len(prefix)


def insert_private(image,build,descriptor,member,member_sha,descriptor_sha,cycle):
    retained.p.hexid(cycle,32);identity=retained.p.hexid(build['build_evidence_id'],32)
    retained.p.hexid(member_sha);retained.p.hexid(descriptor_sha)
    meta,size,marker=(build[k]for k in ('slot_offset','slot_bytes','cycle_offset'))
    source,capacity=(build[k]for k in ('source_holder_offset','source_holder_bytes'))
    require(type(image)is bytes and all(type(x)is int for x in (meta,size,marker,source,capacity)) and size==4096 and capacity==SOURCE_CAP and
        64<=meta<=len(image)-size and 64<=source<=len(image)-capacity and 64<=marker<=len(image)-33,'exact bounded metadata/source/marker extents required')
    intervals=sorted(((meta,meta+size),(source,source+capacity),(marker,marker+33)))
    require(all(left[1]<=right[0]for left,right in zip(intervals,intervals[1:])) and image[marker:marker+33]==retained.p.CYCLE_MARKER+b'\0' and
        image.count(retained.p.CYCLE_MARKER+b'\0')==1 and not any(image[meta:meta+size]) and not any(image[source:source+capacity]),'disjoint fresh zero source/metadata/cycle required')
    require(type(member)is bytes and len(member)==MEMBER_BYTES and member[:4]==b'\x1f\x8b\x08\x00','retained single filename-empty gzip member required')
    metadata,binding=retained.private_member(descriptor,identity,cycle)
    require(len(metadata)<=size and len(binding)==128,'metadata-only descriptor/binding frame required')
    header=struct.pack('<8sIIQQ32s32s',b'N226SRC1',1,96,len(member),UNCOMPRESSED_BYTES,bytes.fromhex(member_sha),bytes.fromhex(descriptor_sha))
    require(len(header)+len(member)<=capacity,'exact readonly holder capacity required')
    changed=bytearray(image);changed[meta:meta+size]=metadata+bytes(size-len(metadata));changed[source:source+capacity]=header+member+bytes(capacity-len(header)-len(member));changed[marker:marker+32]=cycle.encode()
    return bytes(changed),binding,dict(descriptor_bytes=256,binding_bytes=128,metadata_newc_bytes=len(metadata),metadata_slot_bytes=size,
        source_header_bytes=96,source_member_bytes=len(member),source_holder_bytes=capacity,source_zero_tail_bytes=capacity-96-len(member),fixed_pool_bytes=POOL_BYTES,
        named_native_resident_bytes=SOURCE_CAP+POOL_BYTES,hardware_authorized=False,physical_ready=False)


def compiler_stack_path(command,target):
    require(type(command)is bytes and type(target)is str,'typed command/target required');relative=PurePosixPath(target)
    require(not relative.is_absolute() and '..'not in relative.parts and str(relative)==target and relative.suffix=='.o','canonical object target required')
    lines=command.decode().splitlines();key='cmd_'+target+' := '
    require(lines and lines[0].startswith(key) and sum(line.startswith(key)for line in lines)==1,'exact sameImage Kbuild command required')
    argv=shlex.split(lines[0][len(key):]);require(argv and argv[0]=='clang-14' and argv.count('-o')==argv.count('-c')==1 and '-fstack-usage'in argv and '-fno-strict-aliasing'in argv and
        not any(x in argv for x in ('-fno-stack-usage','-pg','-mfentry','-finstrument-functions')) and
        not any(x.startswith(('-fsanitize','-fprofile'))for x in argv),'stack-enabled noninstrumented compile required')
    index=argv.index('-o');require(index+1<len(argv),'compiler output token required');out=PurePosixPath(argv[index+1])
    require(str(out)==argv[index+1] and out.parent==relative.parent and out.name in (relative.name,'.tmp_'+relative.name),'bounded actual compiler output required')
    return out.with_suffix('.su')


def frames(raw):
    result={}
    for line in raw.splitlines():
        cells=line.split('\t');require(len(cells)==3,'typed stack usage row required')
        site,count,kind=cells;name=site.rsplit(':',1)[-1];source=site.rsplit(':',3)[0]
        require(count.isdecimal() and name not in result,'unique numeric stack frame required')
        result[name]=dict(source=source,bytes=int(count),kind=kind)
    require(result,'actual stack rows required');return result


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
    return dict(schema='note10-v226-resident-source-layout-v1',source_holder_offset=offset,source_holder_bytes=SOURCE_CAP,
        fixed_pool_bytes=POOL_BYTES,control_bytes=688,stream_bytes=264,internal_request_offset=43000,internal_request_bytes=496,
        stats_offset=43496,stats_bytes=48,stage_offset=45056,stage_bytes=4096,named_native_resident_bytes=SOURCE_CAP+POOL_BYTES,
        old_large_initramfs_slot_present=False,source_readonly_noninit=True,pool_noninit=True,
        linked_noninit_extent=linked['_end']-linked['_text']-(linked['__init_end']-linked['__init_begin']),linked_symbols=linked,hardware_authorized=False)


STACK_TARGETS={
 'arch/arm64/mm/init.o':('n226_ingest_prepared_locked','n226_open','n226_read','n226_pull','n226_entry','n226_finish','n226_descriptor_digest','n226_stack_room',
    'n226_codec_begin','n226_codec_pull','n226_codec_crc','n226_codec_end','n226_hold','n226_source_read','n226_put','n226_prepare_hash',
    'n217_consume','n217_owner','n217_write_destination','n217_read_destination','n217_clear_destination',
    'n219_hash_begin','n219_hash_update','n219_hash_end','n219_sha256_init','n219_sha256_update','n219_sha256_final','n219_sha256_transform','n209_decode_payload','n209_layout_bounds','pfn_valid'),
 'lib/zlib_inflate/inflate.o':('zlib_inflate','zlib_inflateInit2','zlib_inflateEnd','zlib_inflateReset','zlib_inflate_workspacesize'),
 'lib/zlib_inflate/inffast.o':('inflate_fast',),
 'lib/zlib_inflate/inftrees.o':('zlib_inflate_table',),
 'drivers/misc/v154_linux_return.o':('n210_linux_context',),
 'lib/crc32.o':('crc32_le',),
 'mm/memblock.o':('memblock_is_map_memory',),
 'lib/string.o':('memzero_explicit',),
}
OWNER_UNCALLED={'n217_ingest_current','n219_ingest_current','n217_hold','n217_read','n217_put','n217_hash_begin','n217_hash_update','n217_hash_end'}


def stack_selected(target,name,row):
    if target=='arch/arm64/mm/init.o':
        basename=Path(row['source']).name
        return ((name.startswith(('n226_','n217_','n219_hash_','n219_sha256_'))and name not in OWNER_UNCALLED and name!='n226_emit')or
                basename in ('native_source_stream.c','native_source_ingest.c','native_source_sha256.c','native_parcel_core.c')or
                name in ('pfn_valid','n209_decode_payload','n209_layout_bounds','little','nonzero','magic','extent'))
    if target=='drivers/misc/v154_linux_return.o':return name=='n210_linux_context'
    if target=='mm/memblock.o':return name in ('memblock_is_map_memory','memblock_search')
    if target=='lib/string.o':return name=='memzero_explicit'
    return True


def noninit_functions(raw,names):
    sections={};symbols={}
    for line in raw.splitlines():
        section=re.match(r'^\s*\[\s*(\d+)\]\s+(\S+)\s+\S+\s+[0-9a-fA-F]+\s+[0-9a-fA-F]+\s+[0-9a-fA-F]+\s+[0-9a-fA-F]+\s+([A-Z]+)\s+',line)
        if section:sections[section.group(1)]=(section.group(2),section.group(3))
        symbol=re.match(r'^\s*\d+:\s+[0-9a-fA-F]+\s+(?:\d+|0x[0-9a-fA-F]+)\s+FUNC\s+\S+\s+\S+\s+(\d+)\s+(\S+)\s*$',line)
        if symbol:
            index,name=symbol.groups()
            require(name not in symbols,'unique same-object function required');symbols[name]=index
    result={}
    for name in names:
        require(name in symbols and symbols[name]in sections,'selected frame must match an actual ELF function: '+name)
        section,flags=sections[symbols[name]]
        require(not section.startswith(('.init','.exit'))and'A'in flags and'X'in flags and'W'not in flags,'selected runtime code must survive initmem release: '+name)
        result[name]=section
    return result


def leaf_symbols(raw):
    rows=[line.split()for line in raw.splitlines()if line.strip()];result={}
    for name in ('memcpy','memset','memcmp'):
        found=[row for row in rows if row[0]==name]
        require(len(found)==1 and len(found[0])==4 and found[0][1]in ('T','t','W','w'),'one actual defined leaf symbol required')
        address,size=int(found[0][2],16),int(found[0][3],16)
        require(address%4==size%4==0 and size>0,'actual leaf ELF extent required')
        aliases=[row[0]for row in rows if len(row)==4 and row[1]in ('T','t','W','w')and int(row[2],16)==address and int(row[3],16)==size]
        require(1<=len(aliases)<=32 and len(aliases)==len(set(aliases)),'bounded actual same-extent leaf aliases required')
        result[name]=dict(symbol=name,address=address,bytes=size,aliases=sorted(aliases))
    return result


def assembly_leaf(raw,symbol):
    labels=[];instructions=[]
    for line in raw.splitlines():
        label=re.fullmatch(r'\s*([0-9a-f]+) <([^>]+)>:\s*',line)
        if label:labels.append((int(label.group(1),16),label.group(2)))
        if re.match(r'^\s*[0-9a-f]+:',line):
            instruction=re.fullmatch(r'\s*([0-9a-f]+):\s+[0-9a-f]{8}\s+(.+)',line)
            require(instruction is not None,'every leaf instruction must decode')
            instructions.append((int(instruction.group(1),16),instruction.group(2).lower()))
    require(set(symbol)=={'symbol','address','bytes','aliases'}and type(symbol['address'])is type(symbol['bytes'])is int and
        symbol['symbol']in ('memcpy','memset','memcmp')and type(symbol['aliases'])is list and symbol['symbol']in symbol['aliases']and
        len(labels)==1 and labels[0][1]in symbol['aliases']and labels[0][0]==symbol['address']and
        instructions and len(instructions)*4==symbol['bytes']and
        all(address==symbol['address']+4*index for index,(address,_)in enumerate(instructions)),
        'one complete contiguous actual ELF function extent and bound alias required')
    addresses={address for address,_ in instructions};branches=0
    for _,text in instructions:
        text=text.split('//',1)[0].strip();parts=text.split(None,1);mnemonic=parts[0];operands=parts[1]if len(parts)==2 else''
        require(not re.search(r'\bsp\b',text) and not mnemonic.startswith('.') and
            mnemonic not in ('bl','blr','br','braa','brab','braaz','brabz','blraa','blrab','blraaz','blrabz','eret','eretaa','eretab','drps','svc','hvc','smc','brk','hlt','udf','dcps1','dcps2','dcps3'),
            'leaf must not adjust stack, call, trap or transfer indirectly')
        if mnemonic=='ret':
            require(operands in ('','x30'),'ordinary return required');continue
        direct=mnemonic in ('b','cbz','cbnz','tbz','tbnz')or re.fullmatch(r'b\.(eq|ne|cs|cc|hs|lo|mi|pl|vs|vc|hi|ls|ge|lt|gt|le|al|nv)',mnemonic)
        if direct:
            target=re.sub(r'<[^>]+>','',operands).split(',')[-1].strip()
            require(re.fullmatch(r'(?:0x)?[0-9a-f]+',target)is not None and int(target,16)in addresses,
                'every direct branch must stay inside the same actual function')
            branches+=1
        else:
            require(not mnemonic.startswith(('ret','b.','cb','tb'))and
                (not mnemonic.startswith('b')or mnemonic in ('bic','bics','bfi','bfxil')),'unknown control transfer is not a leaf proof')
    require(instructions[-1][1].split(None,1)[0]in ('ret','b'),'leaf extent must not fall through into unmeasured code')
    return dict(function=labels[0][1],start=labels[0][0],end=instructions[-1][0]+4,instructions=len(instructions),direct_branches=branches,stack_bytes=0,external_calls=0)


def verify_stack_evidence(data):
    require(type(data)is dict and data.get('schema')=='note10-v226-selected-stack-evidence-v1' and set(data['objects'])==set(STACK_TARGETS) and
        set(data['assembly'])==set(data['assembly_symbols'])=={'memcpy','memset','memcmp'},'exact selected stack evidence set required')
    total=0;selected={}
    for target,item in data['objects'].items():
        command=item['command'].encode();usage=item['stack_usage'];rows=frames(usage)
        require(sha(command)==item['command_sha256'] and sha(usage.encode())==item['stack_sha256'] and
            str(compiler_stack_path(command,target))==item['stack_relative'] and set(STACK_TARGETS[target])<=set(rows),'actual command/required frame binding required')
        chosen={name:row for name,row in rows.items()if stack_selected(target,name,row)}
        require(chosen and all(row['kind']=='static' and 0<=row['bytes']<=8192 for row in chosen.values()),'all selected frames must be static and bounded')
        require(sha(item['elf_sections_and_symbols'].encode())==item['elf_evidence_sha256'],'exact section/symbol evidence binding required')
        noninit_functions(item['elf_sections_and_symbols'],chosen)
        require(target!='arch/arm64/mm/init.o'or'n226_emit'not in rows,'receipt must inline into old store logging depth')
        selected[target]={name:row['bytes']for name,row in chosen.items()};total+=sum(selected[target].values())
    leaves={name:assembly_leaf(raw,data['assembly_symbols'][name])for name,raw in data['assembly'].items()}
    require(0<total<=8192,'acyclic selected provider/static callback frame sum exceeds8192B')
    return dict(schema='note10-v226-selected-stack-bound-v1',selected_static_frame_sum=total,selected_frame_bytes=selected,assembly_leaves=leaves,
        acyclic_review_required=True,selected_chain_cap=8192,existing_task_stack_bytes=16384,runtime_headroom_guard_bytes=4096,
        runtime_headroom_check_required=True,whole_frontdoor_static_bound_proven=False,runtime_headroom_observed=False,hardware_authorized=False)


PID1_CAP=65536
def inspect_pid1(raw,symbols):
    require(type(raw)is bytes and 64<=len(raw)<=PID1_CAP and raw[:7]==b'\x7fELF\x02\x01\x01' and
            struct.unpack_from('<HHI',raw,16)==(2,183,1),'bounded static ARM64 ELF required')
    entry,phoff=struct.unpack_from('<QQ',raw,24);ehsize,phsize,count=struct.unpack_from('<HHH',raw,52)
    require((ehsize,phsize)==(64,56) and 1<=count<=16 and phoff+count*phsize<=len(raw),'bounded ELF program headers')
    loads=[];entry_offsets=[];alignments=[]
    for index in range(count):
        kind,flags,offset,va,_,file_bytes,memory_bytes,alignment=struct.unpack_from('<II6Q',raw,phoff+index*phsize)
        require(kind not in (2,3),'PT_DYNAMIC/PT_INTERP forbidden')
        if kind!=1:continue
        require(flags in (4,5,6) and 0<memory_bytes and file_bytes<=memory_bytes and offset+file_bytes<=len(raw) and
                va+memory_bytes<1<<64 and alignment in (1,2,4,8,16,32,64,128,256,512,1024,2048,4096) and
                offset%alignment==va%alignment and not any(low<va+memory_bytes and va<high for low,high in loads),'bounded disjoint ELF loads')
        loads.append((va,va+memory_bytes));alignments.append(alignment)
        if flags&1 and va<=entry and entry+4<=va+file_bytes:entry_offsets.append(offset+entry-va)
    require(loads and entry%4==0 and len(entry_offsets)==1,'unique executable file-backed entry')
    mapped=((max(high for _,high in loads)+4095)//4096*4096)-(min(low for low,_ in loads)//4096*4096)
    require(0<mapped<=PID1_CAP and raw.count(b'N10MININIT2:N226REQUEST')==1,'bounded mapped PID1/identity required')
    rows=[line.split() for line in symbols.splitlines() if line.strip()]
    require(rows and all(len(row)>=2 and row[1] not in ('U','u','w','v') for row in rows),'runtime undefined imports forbidden')
    required=('_start','n212_start','memcpy','memset','n210_request_valid','n210_receipt_matches')
    for name in required:require(len([row for row in rows if row[0]==name and row[1] in ('T','t')])==1,'one defined production symbol required: '+name)
    start=next(row for row in rows if row[0]=='_start')
    require(len(start)>=3 and int(start[2],16)==entry,'_start symbol/entry differ')
    return dict(schema='note10-v226-freestanding-PID1-linkage-v1',passed=True,ELF_bytes=len(raw),ELF_sha256=sha(raw),entry=entry,
                entry_file_offset=entry_offsets[0],mapped_memory_bytes=sum(high-low for low,high in loads),mapped_span_bytes=mapped,
                max_load_alignment=max(alignments),load_alignment_cap=4096,undefined_symbols=[],defined_required=list(required),default_runtime_libraries=False,
                PT_INTERP=False,PT_DYNAMIC=False,PID1_revision='v226')
