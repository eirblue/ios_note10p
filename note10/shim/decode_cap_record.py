"""Decode the versioned diagnostic record; never infer silicon from synthetic/user-mode values."""
import argparse
import json
from pathlib import Path
import struct

NAMES = ('status','current_el','x0','x1','x2','x3','sp','daif','mpidr','cntfrq','mmfr0','mmfr1',
         'isar0','isar1','pfr0','ctr','clidr','sctlr_el1','tcr_el1','ttbr0_el1','ttbr1_el1',
         'vbar_el1','sctlr_el2','tcr_el2','hcr_el2','csselr')

def decode(raw):
    if len(raw)!=320 or raw[:8]!=b'N10CAP01' or struct.unpack_from('<II',raw,8)!=(1,320):
        raise ValueError('Record size/magic/version mismatch')
    r = dict(zip(NAMES,struct.unpack_from('<26Q',raw,16)))
    if r['status']!=1 or r['current_el'] not in (4,8):
        raise ValueError('Record incomplete or entry EL unsupported')
    if any(raw[280:]): raise ValueError('Reserved bytes are not zero')
    mmfr = r['mmfr0']
    # Reserved encodings remain unknown, never accepted as proven support.
    support = lambda v, known: known.get(v,'reserved_unknown')
    granules = {
        '4k':support((mmfr>>28)&15,{0:True,1:True,15:False}),
        '16k':support((mmfr>>20)&15,{0:False,1:True,2:True}),
        '64k':support((mmfr>>24)&15,{0:True,15:False})}
    cache=[]
    for level,value in enumerate(struct.unpack_from('<7Q',raw,224),1):
        kind=(r['clidr']>>(3*(level-1)))&7
        if kind in (2,3,4): cache.append({'level':level,'type':kind,'raw_ccsidr':hex(value),
                                         'maintenance_line_bytes':1<<((value&7)+4)})
        elif value: raise ValueError('CCSIDR data for an unprobed cache level')
    return {'raw':{k:hex(v) for k,v in r.items()},'granules_stage1':granules,'caches':cache,
            'entry_el':r['current_el']>>2,'limits':'Captured register view only; may be trapped/virtualized. No boot or cross-core proof.'}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('record',type=Path);a=p.parse_args()
    print(json.dumps(decode(a.record.read_bytes()),indent=2))
if __name__=='__main__':main()
