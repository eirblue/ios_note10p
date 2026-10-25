"""Verify that an experimental XNU memory image was copied and read back in Linux RAM."""
import re
from decode_reservation import checksum,decode_frames


def decode(text,expected_id,expected_sha256,expected_size):
    reservation=decode_frames(text,expected_id)
    if not re.fullmatch(r'[0-9a-f]{64}',expected_sha256):raise ValueError('Invalid payload digest')
    if type(expected_size) is not int or not 0<expected_size<=256*1024*1024 or expected_size%16384:
        raise ValueError('Invalid staged payload size')
    pattern=(r'N10XNU1 (id=([0-9a-f]{32}) seq=([0-9]+) base=([0-9a-f]+) size=([0-9a-f]+) '
             r'bytes=([0-9]+) sha256=([0-9a-f]{64}) status=([0-9]+)) checksum=([0-9a-f]{8})(?=\r?\n|$)')
    valid={};geometry=None
    for match in re.finditer(pattern,text):
        body,identity,sequence,base,size,length,digest,status,frame_sum=match.groups()
        if identity!=expected_id or checksum(body.encode('ascii'))!=int(frame_sum,16):continue
        values=(int(sequence),int(base,16),int(size,16),int(length),int(status))
        if any(value>=1<<64 for value in values):raise ValueError('XNU staging integer overflow')
        seq,actual_base,actual_size,actual_length,actual_status=values
        if seq>=32:raise ValueError('Unexpected XNU staging sequence')
        if (actual_base,actual_size)!=(reservation['region']['base'],reservation['region']['size']):
            raise ValueError('XNU staging region differs from same-boot reservation')
        if actual_length!=expected_size or digest!=expected_sha256 or actual_status!=0:
            raise ValueError('XNU payload copy/readback did not pass')
        current=(actual_base,actual_size,actual_length,digest,actual_status)
        if geometry is not None and geometry!=current:raise ValueError('Conflicting intact XNU staging frames')
        geometry=current
        if seq in valid:raise ValueError('Duplicate XNU staging sequence / merged logs')
        valid[seq]=body
    if len(valid)<2:raise ValueError('At least two intact distinct XNU staging frames required')
    return {'previous_boot_xnu_payload_stage_observed':True,'xnu_stage_intact_frame_count':len(valid),
            'xnu_stage_intact_sequences':sorted(valid),'xnu_stage_payload_size':expected_size,
            'xnu_stage_payload_sha256':expected_sha256,'xnu_payload_executed':False,
            'xnu_to_cpu_branch_verified':False,'physical_cache_mmu_handoff_verified':False,
            'region':reservation['region'],
            'scope':'Previous Linux boot copied/read back experimental XNU bytes in cached reserved RAM; no XNU execution'}
