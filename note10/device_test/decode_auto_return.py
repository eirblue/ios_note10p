"""Exact per-cycle recovery-request evidence; never proof of hardware restart alone."""
import re
from decode_reservation import checksum
PATTERN=re.compile(rb'N10RET1 (id=([0-9a-f]{32}) cycle=([0-9a-f]{32}) phase=([0-9]+) seq=([0-9]+) delay_ms=([0-9]+) status=([0-9]+)) checksum=([0-9a-f]{8})(?=\r?\n|$)')

def records(data,identity,cycle):
    if not re.fullmatch('[0-9a-f]{32}',identity) or not re.fullmatch('[0-9a-f]{32}',cycle):raise ValueError('Invalid cycle identity')
    rows={}
    for m in PATTERN.finditer(data):
        body,rid,token,phase,seq,delay,status,total=m.groups()
        if rid.decode()!=identity or token.decode()!=cycle or checksum(body)!=int(total,16):continue
        phase,seq,delay,status=map(int,(phase,seq,delay,status))
        if phase>3 or seq>=16 or delay!=90000 or status>0xffffffff:raise ValueError('Invalid return frame')
        key=(phase,seq)
        if key in rows:raise ValueError('Duplicate cycle evidence')
        rows[key]=dict(phase=phase,seq=seq,delay=delay,status=status,offset=m.start())
    return rows

def select_cycle_log(data,identity,cycle):
    rows=records(data,identity,cycle)
    armed=[r for r in rows.values() if r['phase']==0]
    if len(armed)<2 or any(r['status'] for r in armed):raise ValueError('Two intact cycle arm records required')
    offset=min(r['offset'] for r in armed)
    return data[offset:],offset

def decode(data,identity,cycle):
    rows=records(data,identity,cycle)
    for phase in (0,1):
        found=[r for r in rows.values() if r['phase']==phase]
        if len(found)<2 or any(r['status'] for r in found):raise ValueError('Two intact arm and recovery-request records required')
    if any(phase in (2,3) for phase,seq in rows):raise ValueError('Recovery request failed or unexpectedly returned')
    if max(r['offset'] for r in rows.values() if r['phase']==0)>=min(r['offset'] for r in rows.values() if r['phase']==1):raise ValueError('Recovery record order differs')
    return dict(auto_recovery_request_observed=True,cycle=cycle,
        arm_frames=sum(p==0 for p,s in rows),request_frames=sum(p==1 for p,s in rows),
        hardware_recovery_reentry_verified=False)
