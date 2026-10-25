"""Decode complete reservation evidence from one previous Linux boot log."""
import argparse
import json
from pathlib import Path
import re


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
