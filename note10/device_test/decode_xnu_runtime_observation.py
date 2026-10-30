"""Strict hypothetical late-init planner companion in one externally selected boot."""
import re
from decode_reservation import checksum,decode_frames
from prepare_xnu_runtime_observation import geometry
from prepare_xnu_runtime_plan import validate_manifest,HERE
import hashlib

KEYS=('id','copy','phase','plan_generation','pm_completion_claimed','status','base','size',
 'payload_sha','payload_size','geometry_sha','virt','image','entry','kernel_offset','entry_offset',
 'end_offset','mapped','spans','synthetic','materialized','ownership')


def decode(text,expected_id,payload_sha,payload_size,geometry_sha):
    if not isinstance(text,str) or len(text)>16*1024*1024:raise ValueError('selected boot log invalid')
    if not isinstance(expected_id,str) or re.fullmatch('[0-9a-f]{32}',expected_id) is None:raise ValueError('selected build ID invalid')
    manifest=validate_manifest(HERE/'xnu_runtime_plan_payload.json');header,_=geometry(manifest)
    if (payload_sha!=manifest['payload_sha256'] or type(payload_size) is not int or payload_size!=manifest['payload_size'] or
        geometry_sha!=hashlib.sha256(header).hexdigest()):raise ValueError('external payload/geometry pin differs')
    reservation=decode_frames(text,expected_id)
    lines=[line[line.index('N10XPO1'):] for line in text.splitlines() if 'N10XPO1' in line]
    if len(lines)!=2:raise ValueError('exactly two planner companion copies required')
    rows={}
    for line in lines:
        match=re.fullmatch(r'N10XPO1 ([^\r\n\x00]{1,1023}) checksum=([0-9a-f]{8})',line)
        if not match or checksum(match[1].encode('ascii'))!=int(match[2],16):raise ValueError('planner companion truncated/checksum invalid')
        fields=[token.split('=') for token in match[1].split(' ')]
        if any(len(pair)!=2 for pair in fields) or tuple(pair[0] for pair in fields)!=KEYS:raise ValueError('planner companion field order/schema differs')
        row=dict(fields)
        expected={'id':expected_id,'phase':'late-init','plan_generation':'1','pm_completion_claimed':'0','status':'0',
          'payload_sha':payload_sha,'payload_size':str(payload_size),'geometry_sha':geometry_sha,
          'virt':'fffffff006000000','image':'fffffff007004000','entry':'fffffff007340490',
          'kernel_offset':'1004000','entry_offset':'1340490','end_offset':'22b0000','mapped':'7','spans':'2',
          'synthetic':'1','materialized':'0','ownership':'0'}
        if any(row[key]!=value for key,value in expected.items()):raise ValueError('planner companion facts/identity/status differ')
        if row['copy'] not in ('0','1') or row['copy'] in rows:raise ValueError('duplicate/invalid planner copy')
        if any(re.fullmatch('[0-9a-f]{1,16}',row[key]) is None for key in ('base','size')):raise ValueError('planner extent syntax invalid')
        base,size=int(row['base'],16),int(row['size'],16)
        if (base<0x80000000 or base%0x2000000 or size!=0x10000000 or base+size>1<<40 or
            base!=reservation['region']['base'] or size!=reservation['region']['size']):raise ValueError('planner current-boot extent differs')
        rows[row['copy']]={key:value for key,value in row.items() if key!='copy'}
    if set(rows)!=set(('0','1')) or rows['0']!=rows['1']:raise ValueError('planner copies conflict')
    return {'observed':True,'phase':'late-init','plan_generation':1,'pm_completion_claimed':False,
      'build_evidence_id':expected_id,'region':reservation['region'],'payload_sha256':payload_sha,
      'payload_size':payload_size,'geometry_sha256':geometry_sha,'hypothetical_layout':True,
      'materialized':False,'physical_ownership':False,'xnu_executed':False,'deployment_ready':False}
