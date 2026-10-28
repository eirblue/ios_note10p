"""Strict decoder for bounded EHLD ctrl-lock availability frames."""
import re
from decode_reservation import checksum

TAGS=('N10ELM1','N10ELQ1')
SCHEMA={
 'N10ELM1':('id','copy','generation','index','chain_count','lock_available','running_valid','running'),
 'N10ELQ1':('id','copy','generation','status','row_count','complete'),
}

def decode(text, identity, completed, prior):
    if not 0 < completed <= 0xffffffff: raise ValueError('invalid completed generation')
    for line in text.splitlines():
        for m in re.finditer(r'N10EL',line):
            if not re.match(r'(?:N10ELM1|N10ELQ1) ',line[m.start():]): raise ValueError('malformed EHLD prefix')
    found={tag:[[],[]] for tag in TAGS}
    for m in re.finditer(r'(N10ELM1|N10ELQ1) ([^\r\n]*)',text):
        tag,tail=m.groups();match=re.fullmatch(r'(.*?) checksum=([0-9a-f]{8})',tail)
        if not match: raise ValueError('malformed frame')
        body,digest=match.groups();pairs=[part.split('=',1) for part in body.split(' ')]
        if any(len(p)!=2 for p in pairs) or tuple(p[0] for p in pairs)!=SCHEMA[tag]: raise ValueError('frame schema')
        if pairs[0][1]!=identity or checksum(body.encode('ascii'))!=int(digest,16): raise ValueError('identity/checksum')
        row={'id':identity}
        for key,value in pairs[1:]:
            if not re.fullmatch(r'(?:0|-[1-9][0-9]*|[1-9][0-9]*)' if key=='status' else r'(?:0|[1-9][0-9]*)',value): raise ValueError('numeric syntax')
            number=int(value)
            if not (-(1<<31)<=number<(1<<31) if key=='status' else 0<=number<=0xffffffff): raise ValueError('numeric width')
            row[key]=number
        if row['copy'] not in (0,1): raise ValueError('copy index')
        found[tag][row['copy']].append(row)
    for tag in TAGS:
        left=[{k:v for k,v in x.items() if k!='copy'} for x in found[tag][0]]
        right=[{k:v for k,v in x.items() if k!='copy'} for x in found[tag][1]]
        if left!=right: raise ValueError('copies differ')
        found[tag]=left
    qs,rows=found['N10ELQ1'],found['N10ELM1']
    if len(qs)!=1 or len(rows)!=1: raise ValueError('row/summary cardinality')
    q,r=qs[0],rows[0];g=q['generation']
    if not g or ((g+1)&0xffffffff or 1)!=completed or q['status'] or q['row_count']!=1 or q['complete']!=1 or r['generation']!=g: raise ValueError('transaction')
    if prior.get('generation')!=g: raise ValueError('prior generation')
    old=prior.get('rows');count=len(old) if isinstance(old,list) else 0
    if not 1<=count<=32 or r['chain_count']!=count: raise ValueError('chain count')
    for i,row in enumerate(old):
        if row.get('generation')!=g or row.get('index')!=i or row.get('count')!=count: raise ValueError('prior row identity')
    targets=[(i,row) for i,row in enumerate(old) if row.get('kind')==6]
    if len(targets)!=1: raise ValueError('EHLD prior row cardinality')
    i,oldrow=targets[0]
    old_running=oldrow.get('a')
    if r['index']!=i or oldrow.get('valid')!=3 or not isinstance(old_running,int) or not -(1<<31)<=old_running<(1<<31): raise ValueError('EHLD prior identity')
    if r['lock_available'] not in (0,1) or r['running_valid']!=r['lock_available'] or r['running'] not in (0,1): raise ValueError('field range')
    if r['running_valid'] and r['running']!=int(bool(old_running)): raise ValueError('running boolean crosscheck')
    if not r['running_valid'] and r['running']!=0: raise ValueError('busy sentinel')
    return {'generation':g,'row':r,'cpu0_ehld_lock_audit':True,
            'interpretation':'lock availability and conditional running boolean only; not event lifetime or callback readiness'}
