"""Decode complete reservation evidence from one previous Linux boot log."""
import argparse
import json
from pathlib import Path
import re


def checksum(data):
    value=2166136261
    for byte in data:value=((value^byte)*16777619)&0xffffffff
    return value


def decode_frames(text,expected_id):
    """Require two intact agreeing frames bound to the verified kernel Image.

    Corrupted copies are ignored, never repaired. The checksum detects damage;
    it is not authentication. The caller must verify the build artifact/ID.
    """
    if not re.fullmatch(r'[0-9a-f]{32}',expected_id):raise ValueError('Invalid build evidence ID')
    pattern=(r'N10RAM2 (id=([0-9a-f]{32}) seq=([0-9]+) base=([0-9a-f]+) '
             r'size=([0-9a-f]+) align=([0-9a-f]+) pages=([0-9]+) '
             r'reserved=([0-9]+) invalid=([0-9]+) shift=([0-9]+)) checksum=([0-9a-f]{8})(?=\r?\n|$)')
    valid={};observation=None
    for match in re.finditer(pattern,text):
        body,identity,sequence,base,size,align,pages,reserved,invalid,shift,digest=match.groups()
        if identity!=expected_id or checksum(body.encode('ascii'))!=int(digest,16):continue
        seq=int(sequence)
        if seq>=32:raise ValueError('Unexpected evidence sequence')
        # Reuse strict geometry validation; these strings come only from a
        # complete checksummed frame, never a repaired or guessed log value.
        item=decode('Linux version 4.14.113-note10-reserve-pc\n'
                    f'N10RAM1 RESERVED base={base} size={size} align={align}\n'
                    f'N10RAM1 CHECK pages={pages} reserved={reserved} invalid={invalid} shift={shift}\n')
        if observation is not None and item!=observation:raise ValueError('Conflicting intact reservation frames')
        observation=item
        if seq in valid:raise ValueError('Duplicate evidence sequence / merged boot logs')
        valid[seq]=body
    if len(valid)<2:raise ValueError('At least two intact distinct matching build frames required')
    observation.update(evidence_version=2,build_evidence_id=expected_id,
                       intact_frame_count=len(valid),intact_sequences=sorted(valid),
                       corrupted_frames_repaired=False)
    return observation


def decode(text):
    if re.findall(r'Linux version ([^\s\x00]+)',text)!=['4.14.113-note10-reserve-pc']:
        raise ValueError('Exactly one reservation-kernel boot log required')
    records=re.findall(r'N10RAM1 ([A-Z]+) ([^\r\n\x00]+)',text)
    if [kind for kind,_ in records]!=['RESERVED','CHECK']:raise ValueError('Missing, duplicate or failed reservation evidence')
    def fields(raw,expected,base):
        values={}
        for token in raw.split():
            match=re.fullmatch(r'([a-z]+)=([0-9a-f]+)',token)
            if not match or match[1] in values:raise ValueError('Invalid reservation field')
            if base==10 and not match[2].isdigit():raise ValueError('Invalid decimal reservation field')
            number=int(match[2],base)
            if number>=1<<64:raise ValueError('Reservation integer overflow')
            values[match[1]]=number
        if set(values)!=set(expected):raise ValueError('Unexpected reservation fields')
        return values
    region=fields(records[0][1],('base','size','align'),16)
    state=fields(records[1][1],('pages','reserved','invalid','shift'),10)
    if region['size']!=256*1024*1024 or region['align']!=32*1024*1024:
        raise ValueError('Unexpected reservation geometry')
    if region['base']<1<<31 or region['base']%region['align'] or region['base']+region['size']>1<<40:
        raise ValueError('Reservation outside supported aligned physical range')
    if state!={'pages':65536,'reserved':65536,'invalid':0,'shift':12}:
        raise ValueError('Linux did not retain all reserved pages')
    return {'previous_boot_reservation_observed':True,'region':region,'page_state':state,
            'valid_in_current_recovery_boot':False,'safe_to_reuse_address_after_reboot':False,
            'scope':'Previous Linux boot allocator exclusion only; not DMA quiescence or a live load authorization',
            'xnu_executed':False,'deployment_ready':False}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('log',type=Path);a=p.parse_args()
    if not 0<a.log.stat().st_size<=16*1024*1024:raise ValueError('Invalid reservation log size')
    print(json.dumps(decode(a.log.read_bytes().decode(errors='replace')),indent=2))
