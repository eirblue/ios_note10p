"""Inspect real early-C state against immutable linked Mach-O metadata."""
from collections import defaultdict
import struct


def sections(raw):
    result={};offset=32
    for _ in range(struct.unpack_from('<I',raw,16)[0]):
        command,size=struct.unpack_from('<II',raw,offset)
        if command==25:
            for index in range(struct.unpack_from('<I',raw,offset+64)[0]):
                at=offset+72+index*80
                name=raw[at:at+16].split(b'\0')[0].decode()
                if name not in ('__static_if','__static_ifinit'):continue
                if name in result:raise ValueError('Duplicate static-if section')
                va,length,fileoff=struct.unpack_from('<QQI',raw,at+32)
                if fileoff+length>len(raw):raise ValueError('Static-if section exceeds file')
                result[name]=(va,raw[fileoff:fileoff+length])
        offset+=size
    if set(result)!={'__static_if','__static_ifinit'}:raise ValueError('Static-if metadata required')
    return result


def inspect_static_if(read,original_at,entries_address,entries,initializers,calls,stores):
    if not entries or len(entries)%16 or len(entries)>1024*1024 or len(initializers)%8:
        raise ValueError('Invalid static-if metadata geometry')
    groups=defaultdict(set);records={};key_state={}
    for offset in range(0,len(entries),16):
        address=entries_address+offset
        base,target,link=struct.unpack_from('<iiQ',entries,offset)
        key=link&~3
        if not key:raise ValueError('Static-if key pointer missing')
        runtime=read(address,16)
        if runtime[:8]!=entries[offset:offset+8]:raise ValueError('Static-if immutable offsets changed')
        if struct.unpack_from('<Q',runtime,8)[0]&3!=link&3:raise ValueError('Static-if flags changed')
        groups[key].add(address);records[address]=(address+base,target,key,bool(link&1))
    for key,expected in groups.items():
        initial=struct.unpack('<hBBIQQ',original_at(key,24))
        if initial[3] or initial[4]:raise ValueError('Initial static-if key is not empty')
        current=struct.unpack('<hBBIQQ',read(key,24))
        if current[1]!=initial[1] or current[1] not in (0,1) or current[2] not in (0,1):
            raise ValueError('Static-if key Boolean state corrupted')
        key_state[key]=(current[0]>=0,bool(initial[1]))
        if current[3]!=len(expected):raise ValueError('Static-if key count mismatch')
        seen=set();address=current[4]
        while address:
            if address not in expected or address in seen:raise ValueError('Static-if chain cycle or wrong membership')
            seen.add(address);address=struct.unpack_from('<Q',read(address,16),8)[0]&~3
        if seen!=expected:raise ValueError('Static-if chain incomplete')
    expected_initializers=list(struct.unpack('<'+'Q'*(len(initializers)//8),initializers))
    observed=[int(c['target_address'],16) for c in calls if c.get('indirect')]
    if observed!=expected_initializers:raise ValueError('Static-if initializer call sequence mismatch')
    patches=[]
    for call in calls:
        if '_ml_static_if_entry_patch' not in call['target_symbols']:continue
        entry=int(call['x0'],16);branch=int(call['x1'],16)
        if entry not in records or branch not in (0,1):raise ValueError('Invalid static-if patch arguments')
        point,relative_target,key,is_jump=records[entry]
        enabled,initial_enabled=key_state[key]
        if bool(branch)!=((enabled!=initial_enabled)^is_jump):
            raise ValueError('Static-if branch does not match key state')
        if point&3 or relative_target&3 or not -(1<<27)<=relative_target<1<<27:
            raise ValueError('Static-if patch outside instruction geometry')
        instruction=0x14000000|((relative_target>>2)&0x3ffffff) if branch else 0xd503201f
        if struct.unpack('<I',read(point,4))[0]!=instruction:
            raise ValueError('Static-if patch instruction mismatch')
        if (point,4) not in stores:raise ValueError('Static-if patch store not executed')
        patches.append(point)
    return {'entries_checked':len(records),'keys_checked':len(groups),
            'initializers_executed':len(expected_initializers),'patches_checked':len(patches),
            'cache_coherence_verified':False}


def inspect(uc,raw,symbols,segments,boot_args,calls,stores,expected_timebase=None,timer_register=None):
    def read(address,size):return bytes(uc.mem_read(address,size))
    def original_at(address,size):
        for segment in segments:
            start=segment['virtual_address'];offset=address-start
            if 0<=offset and offset+size<=segment['virtual_size']:
                length=max(0,min(size,segment['file_size']-offset))
                begin=segment['file_offset']+offset
                return raw[begin:begin+length]+bytes(size-length)
        raise ValueError('Original state outside linked segments')
    metadata=sections(raw)
    result=inspect_static_if(read,original_at,*metadata['__static_if'],metadata['__static_ifinit'][1],calls,stores)
    constant=symbols['_const_boot_args']
    if read(constant,len(boot_args))!=bytes(boot_args):raise ValueError('Actual C boot_args copy differs')
    if struct.unpack('<Q',read(symbols['_BootArgs'],8))[0]!=constant:
        raise ValueError('BootArgs does not point at actual C copy')
    if struct.unpack('<Q',read(symbols['_vm_kernel_slide'],8))[0]!=0:
        raise ValueError('Unexpected slide in zero-slide PC fixture')
    result.update(const_boot_args_bytes_checked=len(boot_args),boot_args_global_checked=True,
                  zero_slide_fixture_checked=True)
    platform_calls=[c for c in calls if '_PE_init_platform' in c['target_symbols']]
    if platform_calls:
        if any(int(c['x0'],16)!=0 or int(c['x1'],16)!=constant for c in platform_calls):
            raise ValueError('Early PE arguments differ from real C boot_args copy')
        initialized=struct.unpack('<I',read(symbols['_PE_state'],4))[0]
        timebase=struct.unpack('<Q',read(symbols['_gPEClockFrequencyInfo']+9*8,8))[0]
        result.update(pe_state_initialized=initialized==1,timebase_frequency_hz=timebase)
        if expected_timebase is not None:
            if initialized!=1 or timebase!=expected_timebase:raise ValueError('PE clock fixture was not adopted')
            ticks=expected_timebase//1000000
            if not ticks:raise ValueError('Fixture produces zero ticks per WFE event')
            expected_index=max(0,(ticks-1).bit_length()-1)
            actual_index=struct.unpack('<I',read(symbols['_arm64_eventi'],4))[0]
            if actual_index!=expected_index:raise ValueError('C WFE event index mismatch')
            if timer_register is None or ((timer_register>>4)&15)!=expected_index:
                raise ValueError('Unexpected event-stream index in explicit timer state')
            result.update(wfe_event_index=actual_index,timer_register_checked=True)
    return result


def inspect_single_cpu(uc,symbols):
    def read(address,size):return bytes(uc.mem_read(address,size))
    fields=struct.unpack('<6I4Q',read(symbols['_topology_info'],56))
    if fields[:6]!=(2,1,0,1,0,0):raise ValueError('Unexpected single-CPU fixture topology counts')
    cpus,clusters,boot_cpu,boot_cluster=fields[6:]
    if not cpus or not clusters or cpus!=boot_cpu or clusters!=boot_cluster:
        raise ValueError('Single-CPU boot topology pointers disagree')
    if struct.unpack('<4I',read(cpus,16))!=(0,0,0,0):
        raise ValueError('Synthetic CPU identity differs from declared CPU ID 0')
    cluster=struct.unpack('<4IQ',read(clusters,24))
    if cluster[0]!=0 or cluster[2:]!=(1,0,1):raise ValueError('Single-CPU cluster membership differs')
    if any(struct.unpack('<9Q',read(cpus+40,72))) or any(struct.unpack('<6Q',read(clusters+32,48))):
        raise ValueError('Undeclared synthetic CPU MMIO mapping')
    if read(symbols['_cpu_config_correct'],1)!=b'\x01':raise ValueError('CPU configuration marked invalid')
    return {'version':2,'cpus':1,'clusters':1,'logical_cpu_id':0,'synthetic_phys_id':0,
            'boot_cpu_and_cluster_checked':True,'cpu_mmio_declared':False,
            'scope':'Explicit single-CPU PC fixture; not the physical SM-N976N topology'}
