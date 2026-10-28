"""Strict v38 two-copy decoder, cross-bound to validated v37 observations."""
import re
from decode_reservation import checksum
TAGS=('N10BRAR1','N10BRAG1','N10BRAQ1')
SCHEMA={'N10BRAR1':('id','copy','generation','index','count','kind','num','supported','used','nonnull','match','reset','start','stop'),'N10BRAG1':('id','copy','generation','phase','lanes','enabled','active','matches'),'N10BRAQ1':('id','copy','generation','status','count','complete','gic_complete')}
def decode(text,identity,completed,prior):
 if not 0<completed<=0xffffffff:raise ValueError('invalid completed generation')
 for line in text.splitlines():
  if 'N10BRA' in line and not re.search(r'\b(?:N10BRAR1|N10BRAG1|N10BRAQ1) ',line):raise ValueError('malformed branch prefix')
 found={tag:[[],[]] for tag in TAGS}
 for m in re.finditer(r'(N10BRAR1|N10BRAG1|N10BRAQ1) ([^\r\n]*)',text):
  tag,line=m.groups();frame=re.fullmatch(r'(.*?) checksum=([0-9a-f]{8})',line)
  if not frame:raise ValueError('malformed frame')
  body,digest=frame.groups();pairs=[x.split('=',1) for x in body.split(' ')]
  if any(len(x)!=2 for x in pairs) or tuple(x[0] for x in pairs)!=SCHEMA[tag]:raise ValueError('frame schema differs')
  raw=dict(pairs)
  if raw['id']!=identity:continue
  if checksum(body.encode('ascii'))!=int(digest,16):raise ValueError('checksum differs')
  row={'id':identity}
  for key,value in pairs[1:]:
   if not re.fullmatch(r'(?:0|-?[1-9][0-9]*)' if key=='status' else r'(?:0|[1-9][0-9]*)',value):raise ValueError('number syntax differs')
   n=int(value)
   if not (-(1<<31)<=n<(1<<31) if key=='status' else 0<=n<=0xffffffff):raise ValueError('number width differs')
   row[key]=n
  if row['copy'] not in (0,1):raise ValueError('copy differs')
  found[tag][row['copy']].append(row)
 for tag in TAGS:
  left=[{k:v for k,v in x.items() if k!='copy'} for x in found[tag][0]];right=[{k:v for k,v in x.items() if k!='copy'} for x in found[tag][1]]
  if left!=right:raise ValueError('copies differ')
  found[tag]=left
 q=found['N10BRAQ1']
 if len(q)!=1:raise ValueError('summary missing or repeated')
 q=q[0];generation=q['generation'];count=q['count']
 if not generation or ((generation+1)&0xffffffff or 1)!=completed or q['status'] or q['complete']!=1 or q['gic_complete']!=1 or count>32:raise ValueError('transaction failed')
 if prior.get('generation')!=generation:raise ValueError('v37 generation differs')
 rows=found['N10BRAR1'];gic=found['N10BRAG1'];oldrows=prior['rows'];oldgic=prior['gic']
 if len(rows)!=count or len(oldrows)!=count or len(gic)!=3 or len(oldgic)!=3:raise ValueError('row count differs')
 for i,r in enumerate(rows):
  if r['generation']!=generation or r['index']!=i or r['count']!=count or r['kind']!=oldrows[i]['kind']:raise ValueError('row identity differs')
  fields=('num','supported','used','nonnull','match','reset','start','stop')
  if r['kind']!=5:
   if any(r[k] for k in fields):raise ValueError('unused fields differ')
  else:
   n=r['num'];v=oldrows[i]
   if n>32 or any(r[k] not in (0,1) for k in ('supported','reset','start','stop')):raise ValueError('PMU fields differ')
   if any(r[k]>=(1<<n) for k in ('used','nonnull','match')) or r['match']&~r['nonnull']:raise ValueError('PMU masks differ')
   if n!=v['b'] or r['supported']!=v['a'] or r['used']!=v['c'] or r['nonnull'].bit_count()!=v['e']:raise ValueError('v37 PMU observation differs')
 for i,r in enumerate(gic):
  g=oldgic[i];lanes=0
  for word in range(8):
   for lane in range(4):
    if ((g['p'+str(word)]>>(8*lane))&255)!=0xa0:lanes|=1<<(word*4+lane)
  if r['generation']!=generation or r['phase']!=i or r['lanes']!=lanes or r['enabled']!=lanes&g['enable'] or r['active']!=lanes&g['active'] or r['matches']!=g['matches']:raise ValueError('v37 GIC footprint differs')
 return {'generation':generation,'rows':rows,'gic':gic,'cpu0_pmu_branch_audit':True,'cpu0_gic_priority_footprint':True}
