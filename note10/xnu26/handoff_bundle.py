"""Materialize PC-only XNU load buffers from an explicit synthetic RAM plan.

Not a reservation mechanism, Linux kexec loader or Android boot image.
There is deliberately no device-mode option or automatic address selection.
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct
from boot_contract import Region,PAGE,BLOCK,SIZE,encode_boot_args,validate_placement,uint
from boot_adt import RAMDISK_MAX_BYTES,decode as decode_adt
from verify_experimental_artifact import verify

ROOT=Path(__file__).resolve().parents[2]
MAX_IMAGE=256*1024*1024
TRUST_CACHE_FILE = 'trust-cache.mem'


def _validate_ramdisk(tree, ram, reserved, occupied, kernel, top):
    chosen = next((node for node in tree.children if node.name == 'chosen'), None)
    memory_map = next((node for node in chosen.children if node.name == 'memory-map'), None) if chosen else None
    if memory_map is None or 'RAMDisk' not in memory_map.properties:
        return
    value = memory_map.properties['RAMDisk']
    if len(value) != 16:
        raise ValueError('RAMDisk property must contain exactly two uint64 values')
    disk = Region(*struct.unpack('<QQ', value))
    if not disk.start or disk.start % 0x1000 or disk.size % 0x1000 or disk.size > RAMDISK_MAX_BYTES:
        raise ValueError('RAMDisk must fit the aligned 32-bit consumer byte extent')
    if not ram.contains(disk) or any(disk.overlaps(region) for region in occupied):
        raise ValueError('RAMDisk must lie in modeled RAM outside occupied memory')
    if not any(ram.contains(region) and region.contains(disk) and not region.start % PAGE and not region.size % PAGE
               and kernel.end <= region.start and region.end <= top
               for region in reserved):
        raise ValueError('RAMDisk requires a containing page-aligned reserved backing')


def _trust_cache_backing(plan, ram, blocked):
    if 'trust_cache' not in plan:
        return None
    extent = plan['trust_cache']
    if not isinstance(extent, dict) or set(extent) != {'start', 'size'}:
        raise ValueError('Expected explicit synthetic TrustCache backing')
    backing = Region(**extent)
    if not backing.start or backing.start % PAGE or backing.size % PAGE or not ram.contains(backing):
        raise ValueError('TrustCache backing must be page-aligned inside modeled RAM')
    if any(backing.overlaps(region) for region in blocked):
        raise ValueError('TrustCache backing overlaps reserved, occupied or allocated RAM')
    return backing


def _validate_trust_cache(tree, backing, segment):
    if backing is None:
        if segment is not None:
            raise ValueError('TrustCache segment requires explicit backing')
        return
    if not isinstance(segment, bytes) or not 8 < len(segment) <= min(backing.size, MAX_IMAGE):
        raise ValueError('TrustCache segment must contain one module inside its backing')
    if struct.unpack_from('<II', segment) != (1, 8):
        raise ValueError('TrustCache segment requires one module at offset eight')
    # The ADT decoder already rejects duplicate sibling names and properties.
    chosen = next((node for node in tree.children if node.name == 'chosen'), None)
    memory_map = next((node for node in chosen.children if node.name == 'memory-map'), None) if chosen else None
    value = memory_map.properties.get('TrustCache') if memory_map else None
    if value != struct.pack('<QQ', backing.start, len(segment)):
        raise ValueError('TrustCache ADT property must match the exact segment range')


def _framebuffer_video(plan, ram, blocked):
    """Validate the optional synthetic framebuffer and derive its Boot_Video fields."""
    if 'framebuffer' not in plan:
        return (0, 0, 0, 0, 0, 0)
    frame = plan['framebuffer']
    if not isinstance(frame, dict) or set(frame) != {'cpu_backing', 'dma_base', 'dma_end', 'stride', 'display'}:
        raise ValueError('Expected explicit synthetic framebuffer layout')
    cpu = frame['cpu_backing']
    if not isinstance(cpu, dict) or set(cpu) != {'start', 'size'}:
        raise ValueError('Expected explicit framebuffer CPU backing')
    backing = Region(**cpu)

    # Match the fixed Davinci packed mode and native IDMA field widths.
    width, height, pixel_bytes = 1440, 3040, 4
    stride = uint(frame['stride'])
    dma_base, dma_end = uint(frame['dma_base'], 32), uint(frame['dma_end'])
    if stride % pixel_bytes or not width <= stride // pixel_bytes <= 0xffff:
        raise ValueError('Framebuffer stride is outside Davinci IDMA bounds')
    required = stride * height
    if not dma_base or dma_base % pixel_bytes or dma_base + required > min(dma_end, 1 << 32):
        raise ValueError('Framebuffer DMA extent is outside the IDMA aperture')
    if (not backing.start or backing.start % PAGE or backing.size % PAGE or
            required > backing.size or not ram.contains(backing)):
        raise ValueError('Framebuffer CPU backing must cover the frame in page-aligned RAM')
    if any(backing.overlaps(region) for region in blocked):
        raise ValueError('Framebuffer CPU backing overlaps reserved, occupied or allocated RAM')
    return (backing.start, uint(frame['display']), stride, width, height, pixel_bytes * 8)


def materialize_kernel(raw,segments):
    selected=[s for s in segments if s['virtual_size']]
    if not selected:raise ValueError('No loadable XNU segments')
    base=min(s['virtual_address'] for s in selected)
    end=max(s['virtual_address']+s['virtual_size'] for s in selected)
    uint(base);uint(end)
    size=(end-base+PAGE-1)&~(PAGE-1)
    if not 0<size<=MAX_IMAGE:raise ValueError('XNU memory image exceeds cap')
    memory=bytearray(size);ranges=[]
    for s in selected:
        start=s['virtual_address']-base;length=s['virtual_size']
        off=s['file_offset'];count=s['file_size']
        if any(type(v) is not int or v<0 for v in (start,length,off,count)):
            raise ValueError('Invalid segment integer')
        if start+length>size or count>length or off+count>len(raw):raise ValueError('Invalid segment data bounds')
        region=Region(start,length)
        if any(region.overlaps(r) for r in ranges):raise ValueError('Overlapping XNU segments')
        ranges.append(region)
        # Zero-filled allocation explicitly includes BSS, alignment and holes.
        memory[start:start+count]=raw[off:off+count]
    return base,bytes(memory)


def materialize_adapter(raw):
    if len(raw)<64 or raw[:7]!=b'\x7fELF\x02\x01\x01':raise ValueError('Expected little-endian ELF64 adapter')
    _,kind,machine,version,entry,phoff,shoff,_,ehsize,phsize,phnum,shsize,shnum,_=struct.unpack_from('<16sHHIQQQIHHHHHH',raw)
    if (kind,machine,version,ehsize,phsize)!=(2,183,1,64,56) or not 1<=phnum<=16 or entry%4:
        raise ValueError('Unsupported ARM64 adapter ELF')
    if phoff+phnum*phsize>len(raw) or not 1<=shnum<=4096 or shsize!=64 or shoff+shnum*shsize>len(raw):
        raise ValueError('Adapter table outside file')
    for i in range(shnum):
        section=struct.unpack_from('<IIQQQQIIQQ',raw,shoff+i*shsize)
        if section[1] in (4,6,9):raise ValueError('Adapter contains relocations or dynamic dependencies')
    memory=bytearray(PAGE);ranges=[];entry_ok=False;writable=[]
    for i in range(phnum):
        typ,flags,off,va,pa,size,memsize,alignment=struct.unpack_from('<II6Q',raw,phoff+i*phsize)
        if typ in (2,3):raise ValueError('Adapter has dynamic loader dependencies')
        if typ!=1:continue
        if not memsize or size>memsize or off+size>len(raw) or va+memsize>PAGE or va!=pa:
            raise ValueError('Adapter segment outside one relative page')
        if flags not in (4,5,6):raise ValueError('Unsafe adapter segment permissions')
        region=Region(va,memsize)
        if any(region.overlaps(r) for r in ranges):raise ValueError('Overlapping adapter segments')
        ranges.append(region)
        memory[va:va+size]=raw[off:off+size]
        if flags&1 and va<=entry<va+size:entry_ok=True
        if flags&2:writable.append(region)
    if not ranges or not entry_ok:raise ValueError('Adapter entry not executable/file-backed')
    template=struct.pack('<8sII6Q',b'N10XFER1',1,64,0,0,0,0,0,0)
    record=memory.find(template)
    if record<0 or memory.find(template,record+1)>=0 or record%64:
        raise ValueError('Expected one aligned unpatched transfer record')
    if not any(r.contains(Region(record,64)) for r in writable):raise ValueError('Transfer record not writable')
    return bytes(memory),entry,record


def construct(raw,checked,adapter_raw,adt,plan,*,trust_cache=None):
    """Build the synthetic bundle, optionally binding an opaque TrustCache fixture segment."""
    if plan.get('schema')!=1 or plan.get('purpose')!='synthetic-pc-model':
        raise ValueError('Only explicit synthetic PC plans are supported')
    if plan.get('physical_reservation_verified') is not False:
        raise ValueError('This producer cannot certify physical reservations')
    ram=Region(**plan['ram']);virtual=uint(plan['virtual_base'])
    if ram.end>1<<40:raise ValueError('Plan exceeds compiled 40bit IPS')
    reserved=[Region(**r) for r in plan['reserved']];occupied=[Region(**r) for r in plan['occupied']]
    base,kernel=materialize_kernel(raw,checked['segments'])
    if base<virtual:raise ValueError('Kernel precedes supplied virtual base')
    kernel_pa=ram.start+base-virtual
    kernel_region=Region(kernel_pa,len(kernel))
    entry_va=int(checked['entry_virtual_address'],16)
    entry_pa=ram.start+entry_va-virtual
    if not kernel_region.contains(Region(entry_pa,4)):
        raise ValueError('XNU entry outside materialized kernel')
    adt_root=decode_adt(adt)
    if not adt or len(adt)>PAGE:raise ValueError('Initial ADT exceeds metadata page')
    top=uint(plan['top_of_kernel'])
    _validate_ramdisk(adt_root,ram,reserved,occupied,kernel_region,top)
    adapter,relative_entry,record=materialize_adapter(adapter_raw)
    arguments=Region(plan['arguments_address'],PAGE)
    tree=Region(plan['device_tree_address'],PAGE)
    transfer=Region(plan['adapter_address'],PAGE)
    validate_placement(ram=ram,reserved=reserved,occupied=occupied,kernel=kernel_region,
                       arguments=arguments,device_tree=tree,adapter=transfer,top_of_kernel=top)
    blocked=(*reserved,*occupied,kernel_region,arguments,tree,transfer)
    trust_backing=_trust_cache_backing(plan,ram,blocked)
    _validate_trust_cache(adt_root,trust_backing,trust_cache)
    if trust_backing is not None:
        blocked+=(trust_backing,)
    video=_framebuffer_video(plan,ram,blocked)
    args=encode_boot_args(virtual_base=virtual,physical_base=ram.start,memory_size=ram.size,
                         top_of_kernel=top,device_tree_pointer=virtual+tree.start-ram.start,
                         device_tree_length=len(adt),command_line=plan.get('command_line',''),video=video)
    adapter=bytearray(adapter)
    struct.pack_into('<QQ',adapter,record+16,arguments.start,entry_pa)
    files={'kernel.mem':kernel,'boot-args.mem':args+bytes(PAGE-len(args)),
           'device-tree.mem':adt+bytes(PAGE-len(adt)),'adapter.mem':bytes(adapter)}
    addresses={'kernel.mem':kernel_pa,'boot-args.mem':arguments.start,'device-tree.mem':tree.start,'adapter.mem':transfer.start}
    if trust_backing is not None:
        files[TRUST_CACHE_FILE]=trust_cache
        addresses[TRUST_CACHE_FILE]=trust_backing.start
    manifest={'schema':1,'purpose':'synthetic-pc-model','plan':plan,
              'kernel_sha256':hashlib.sha256(raw).hexdigest(),'adapter_elf_sha256':hashlib.sha256(adapter_raw).hexdigest(),
              'adapter_entry_physical':transfer.start+relative_entry,'adapter_record_physical':transfer.start+record,
              'xnu_entry_physical':entry_pa,'boot_args_physical':arguments.start,'device_tree_length':len(adt),
              'buffers':[{'file':name,'physical_address':addresses[name],'size':len(data),
                          'sha256':hashlib.sha256(data).hexdigest()} for name,data in files.items()],
              'physical_reservation_verified':False,'device_operations':[],'deployment_ready':False,
              'scope':'PC materialization only; not a kexec/flash image or a hardware load authorization'}
    return manifest,files


def build(directory,adapter,adt,plan,output):
    if not output.resolve().is_relative_to((ROOT/'note10/private').resolve()):raise ValueError('Private output required')
    if output.exists():raise ValueError('Refusing existing bundle output')
    checked=verify(directory)
    manifest,files=construct((directory/'note10-experimental.macho').read_bytes(),checked,
                             adapter.read_bytes(),adt.read_bytes(),plan)
    output.mkdir(parents=True,exist_ok=False)
    for name,data in files.items():(output/name).write_bytes(data)
    (output/'handoff.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    return manifest


def load(directory,*,kernel_sha256,allow_trust_cache=False):
    """Reload a synthetic bundle. TrustCache fixture segments require explicit opt-in."""
    manifest=json.loads((directory/'handoff.json').read_text())
    if manifest.get('schema')!=1 or manifest.get('purpose')!='synthetic-pc-model' or manifest.get('physical_reservation_verified') is not False:
        raise ValueError('Invalid PC handoff bundle scope')
    if manifest.get('deployment_ready') is not False or manifest.get('device_operations')!=[]:
        raise ValueError('Bundle cannot authorize hardware deployment')
    if manifest['kernel_sha256']!=kernel_sha256:raise ValueError('Bundle bound to another XNU executable')
    plan=manifest['plan']
    expected={'kernel.mem','boot-args.mem','device-tree.mem','adapter.mem'}
    if 'trust_cache' in plan:
        if allow_trust_cache is not True:
            raise ValueError('Explicit TrustCache fixture reload required')
        expected.add(TRUST_CACHE_FILE)
    if len(manifest['buffers'])!=len(expected) or {b['file'] for b in manifest['buffers']}!=expected:
        raise ValueError('Unexpected bundle buffers')
    files={};regions=[]
    for item in manifest['buffers']:
        path=directory/item['file']
        if path.is_symlink() or not 0<path.stat().st_size<=MAX_IMAGE:raise ValueError('Unsafe bundle file')
        data=path.read_bytes()
        if len(data)!=item['size'] or hashlib.sha256(data).hexdigest()!=item['sha256']:raise ValueError('Bundle payload hash mismatch')
        region=Region(item['physical_address'],len(data))
        if (region.start%PAGE or (item['file']!=TRUST_CACHE_FILE and region.size%PAGE) or
                any(region.overlaps(r) for r in regions)):
            raise ValueError('Invalid bundle memory extents')
        regions.append(region);files[item['file']]=data
    by_name={b['file']:Region(b['physical_address'],b['size']) for b in manifest['buffers']}
    if plan.get('schema')!=1 or plan.get('purpose')!='synthetic-pc-model' or plan.get('physical_reservation_verified') is not False:
        raise ValueError('Invalid embedded plan')
    ram=Region(**plan['ram'])
    if ram.end>1<<40:raise ValueError('Bundle exceeds compiled IPS')
    for name,field in (('boot-args.mem','arguments_address'),('device-tree.mem','device_tree_address'),('adapter.mem','adapter_address')):
        if by_name[name]!=Region(plan[field],PAGE):raise ValueError('Metadata buffer differs from plan')
    reserved=[Region(**r) for r in plan['reserved']];occupied=[Region(**r) for r in plan['occupied']]
    top=uint(plan['top_of_kernel'])
    validate_placement(ram=ram,reserved=reserved,occupied=occupied,kernel=by_name['kernel.mem'],
                       arguments=by_name['boot-args.mem'],device_tree=by_name['device-tree.mem'],
                       adapter=by_name['adapter.mem'],top_of_kernel=top)
    trust_region=by_name.pop(TRUST_CACHE_FILE,None)
    blocked=(*reserved,*occupied,*by_name.values())
    trust_backing=_trust_cache_backing(plan,ram,blocked)
    if trust_backing is not None:
        if trust_region.start!=trust_backing.start:
            raise ValueError('TrustCache segment address differs from backing')
        blocked+=(trust_backing,)
    video=_framebuffer_video(plan,ram,blocked)
    length=uint(manifest['device_tree_length'],32)
    if not 0<length<=PAGE or any(files['device-tree.mem'][length:]):raise ValueError('Invalid padded ADT')
    adt_root=decode_adt(files['device-tree.mem'][:length])
    _validate_ramdisk(adt_root,ram,reserved,occupied,by_name['kernel.mem'],top)
    _validate_trust_cache(adt_root,trust_backing,files.get(TRUST_CACHE_FILE))
    virtual=uint(plan['virtual_base'])
    args=encode_boot_args(virtual_base=virtual,physical_base=ram.start,memory_size=ram.size,
                         top_of_kernel=plan['top_of_kernel'],device_tree_pointer=virtual+plan['device_tree_address']-ram.start,
                         device_tree_length=length,command_line=plan.get('command_line',''),video=video)
    if files['boot-args.mem']!=args+bytes(PAGE-len(args)):raise ValueError('Boot arguments differ from plan')
    if manifest['boot_args_physical']!=plan['arguments_address']:raise ValueError('Wrong boot args pointer')
    entry=uint(manifest['xnu_entry_physical']);record=uint(manifest['adapter_record_physical'])
    if entry%4 or not by_name['kernel.mem'].contains(Region(entry,4)):
        raise ValueError('XNU entry outside kernel allocation')
    if not by_name['adapter.mem'].contains(Region(uint(manifest['adapter_entry_physical']),4)) or record%64 or not by_name['adapter.mem'].contains(Region(record,64)):
        raise ValueError('Adapter metadata outside allocation')
    offset=record-by_name['adapter.mem'].start
    expected_record=struct.pack('<8sII6Q',b'N10XFER1',1,64,plan['arguments_address'],entry,0,0,0,0)
    if files['adapter.mem'][offset:offset+64]!=expected_record:raise ValueError('Transfer descriptor differs from manifest')
    return manifest,files


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('kernel-build','adapter','adt','plan','output'):parser.add_argument('--'+name,type=Path,required=True)
    a=parser.parse_args();r=build(a.kernel_build,a.adapter,a.adt,json.loads(a.plan.read_text()),a.output)
    print(json.dumps({'buffers':len(r['buffers']),'physical_reservation_verified':False,'deployment_ready':False}))
