"""Bounded mixed initramfs framing; no private payload decoding in production."""
import struct
from v130_contract import SLOT,DISABLED,SPAN

PRIVATE_NAMES={'n10/kernel.mem','n10/adapter.raw','n10/payload.contract'}
METADATA_NAMES={'n10/platform.adt','n10/platform.contract','n10/activation.contract'}

def newc(entries):
    out=bytearray()
    for index,(name,mode,data,major,minor) in enumerate([*entries,('TRAILER!!!',0,b'',0,0)],1):
        if not isinstance(data,bytes) or not name or name.startswith('/') or '..' in name.split('/') or '\0' in name:
            raise ValueError('bounded relative newc entry required')
        encoded=name.encode('ascii')+b'\0'
        fields=(index,mode,0,0,2 if mode==0o040755 else 1,0,len(data),0,0,major,minor,len(encoded),0)
        out.extend(b'070701'+''.join(f'{value:08x}' for value in fields).encode()+encoded)
        out.extend(bytes(-len(out)%4));out.extend(data);out.extend(bytes(-len(out)%4))
    return bytes(out)

def generic(init):
    if init[:6]!=b'\x7fELF\x02\x01' or init[18:20]!=b'\xb7\0' or not len(init)<=2097152 or init.count(DISABLED)!=1:
        raise ValueError('new disabled bounded AArch64 PID1 required')
    raw=newc([('dev',0o040755,b'',0,0),('sys',0o040755,b'',0,0),('n10',0o040755,b'',0,0),
        ('dev/console',0o020600,b'',5,1),('dev/kmsg',0o020600,b'',1,11),('init',0o100755,init,0,0)])
    prefix=raw+bytes(-len(raw)%512)
    return prefix+bytes(SLOT),len(prefix)

def metadata(adt,platform,capture_sha):
    if not 0<len(adt)<=1048576 or len(platform)!=128:raise ValueError('bounded actual platform files required')
    from v130_contract import digest,hexid
    activation=struct.pack('<8sIIQ32s32s32sQ',b'N10ACTV1',1,128,len(adt),bytes.fromhex(digest(adt)),
        bytes.fromhex(digest(platform)),bytes.fromhex(hexid(capture_sha)),0)
    return newc([(name,0o100400,data,0,0) for name,data in (
        ('n10/platform.adt',adt),('n10/platform.contract',platform),('n10/activation.contract',activation))])

def insert(image,layout,member,meta,cycle):
    from v130_contract import hexid
    hexid(cycle,32)
    start=layout['slot_offset'];length=layout['slot_bytes'];cycle_at=layout['cycle_offset']
    if length!=SLOT or start<0 or start+length>len(image) or cycle_at<0 or cycle_at+32>start or image[cycle_at:cycle_at+32]!=DISABLED:
        raise ValueError('source-built slot/cycle geometry differs')
    if any(image[start:start+length]) or image.count(DISABLED)!=1 or not member.startswith(b'\x1f\x8b'):
        raise ValueError('generic source-built slot is not disabled/empty')
    combined=member+bytes(-len(member)%4)+meta
    if len(combined)>length:raise ValueError('actual ONE compressed member plus metadata exceeds8MiB')
    result=bytearray(image);result[start:start+length]=combined+bytes(length-len(combined))
    result[cycle_at:cycle_at+32]=cycle.encode()
    return bytes(result),dict(private_member_bytes=len(member),metadata_bytes=len(meta),used_slot_bytes=len(combined),zero_tail_bytes=length-len(combined))
