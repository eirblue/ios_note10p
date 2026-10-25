"""Bind complete previous-boot RAM-access frames to reservation and kernel ID."""
import re
from decode_reservation import checksum,decode_frames

COUNTS={'words':33554432,'written':67108864,'checked':67108864,
        'zeroed':33554432,'zero_checked':33554432,'mismatches':0,'rounds':2,'status':0}


def decode(text,expected_id):
    reservation=decode_frames(text,expected_id)
    keys=('words','written','checked','zeroed','zero_checked','mismatches','rounds','status')
    pattern=(r'N10MEM1 (id=([0-9a-f]{32}) seq=([0-9]+) base=([0-9a-f]+) size=([0-9a-f]+) '+
             ' '.join(name+r'=([0-9]+)' for name in keys)+r') checksum=([0-9a-f]{8})(?=\r?\n|$)')
    valid={}
    for match in re.finditer(pattern,text):
        body,identity,sequence,base,size,*tail=match.groups()
        digest=tail.pop()
        if identity!=expected_id or checksum(body.encode('ascii'))!=int(digest,16):continue
        numbers=[int(base,16),int(size,16),int(sequence),*map(int,tail)]
        if any(number>=1<<64 for number in numbers):raise ValueError('RAM access integer overflow')
        actual_base,actual_size,seq,*counts=numbers
        if seq>=32:raise ValueError('Unexpected RAM access sequence')
        if (actual_base,actual_size)!=(reservation['region']['base'],reservation['region']['size']):
            raise ValueError('RAM access region differs from same-boot reservation')
        if dict(zip(keys,counts))!=COUNTS:raise ValueError('RAM access test failed or incomplete')
        if seq in valid:raise ValueError('Duplicate RAM access sequence / merged logs')
        valid[seq]=body
    if len(valid)<2:raise ValueError('At least two intact distinct RAM access frames required')
    return {**reservation,'previous_boot_window_access_observed':True,
            'access_evidence_version':1,'access_intact_frame_count':len(valid),'access_intact_sequences':sorted(valid),
            'memory_access_counts':dict(COUNTS),'cached_linux_access_only':True,
            'physical_cache_mmu_handoff_verified':False,'kernel_to_xnu_transfer_verified':False,
            'scope':'Previous Linux boot cached reserved-RAM patterns/readback/scrub; not current recovery RAM or XNU execution'}
