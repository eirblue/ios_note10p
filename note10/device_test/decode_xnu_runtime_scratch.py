"""Strict selected-boot scratch evidence, independently reconstructed bytes."""
import re
import struct
from decode_reservation import checksum
from decode_xnu_runtime_observation import decode as decode_prior

KEYS=('id','copy','phase','generation','pm_completion_claimed','status','base','size','payload_sha','geometry_sha',
 'args_size','record_size','adt_size','args_fnv','record_fnv','adt_fnv','checked','canaries','synthetic',
 'scratch_materialized','reserved_materialized','ownership','executed')

def expected_bytes(base):
    args=bytearray(1152)
    struct.pack_into('<HH',args,0,2,2)
    struct.pack_into('<QQQQ',args,8,0xfffffff006000000,base,0x10000000,base+0x22b0000)
    struct.pack_into('<QI',args,96,0xfffffff006004000,56)
    struct.pack_into('<Q',args,1144,0x10000000)
    record=struct.pack('<8sIIQQ',b'N10XFER1',1,64,base,base+0x1340490)+bytes(32)
    adt=struct.pack('<II32sI12s',1,0,b'name',12,b'device-tree\0')
    return bytes(args),record,adt

def decode(text,identity,payload_sha,payload_size,geometry_sha):
    baseline=decode_prior(text,identity,payload_sha,payload_size,geometry_sha)
    base=baseline['region']['base'];args,record,adt=expected_bytes(base)
    fixed=dict(zip(KEYS,('',)*len(KEYS)))
    fixed.update(id=identity,phase='late-init',generation='1',pm_completion_claimed='0',status='0',base=f'{base:x}',size='10000000',
      payload_sha=payload_sha,geometry_sha=geometry_sha,args_size='1152',record_size='64',adt_size='56',
      args_fnv=f'{checksum(args):08x}',record_fnv=f'{checksum(record):08x}',adt_fnv=f'{checksum(adt):08x}',
      checked='1',canaries='1',synthetic='1',scratch_materialized='1',reserved_materialized='0',ownership='0',executed='0')
    lines=[line[line.index('N10XSO1'):] for line in text.splitlines() if 'N10XSO1' in line]
    if len(lines)!=2:raise ValueError('exactly two scratch copies required')
    copies=set()
    for line in lines:
        match=re.fullmatch(r'N10XSO1 ([^\r\n\x00]{1,767}) checksum=([0-9a-f]{8})',line)
        if not match or checksum(match[1].encode('ascii'))!=int(match[2],16):raise ValueError('scratch truncated/checksum invalid')
        pairs=[word.split('=') for word in match[1].split(' ')]
        if any(len(p)!=2 for p in pairs) or tuple(p[0] for p in pairs)!=KEYS:raise ValueError('scratch schema differs')
        row=dict(pairs);copy=row['copy']
        if copy not in ('0','1') or copy in copies:raise ValueError('scratch copy invalid/duplicate')
        if any(row[k]!=v for k,v in fixed.items() if k!='copy'):raise ValueError('scratch bound facts differ')
        copies.add(copy)
    return dict(observed=True,phase='late-init',generation=1,pm_completion_claimed=False,build_evidence_id=identity,
      region=baseline['region'],payload_sha256=payload_sha,geometry_sha256=geometry_sha,
      args_size=1152,record_size=64,adt_size=56,bytes_checked=True,canaries_checked=True,
      synthetic_adt=True,scratch_materialized=True,reserved_materialized=False,physical_ownership=False,xnu_executed=False)
