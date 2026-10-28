"""Validate the two-copy v41 RAM-only PMU observation."""
import re
from decode_reservation import checksum
TAGS=('N10STAR1','N10STAQ1')
MASKS=('used','present','owned','observed','running','stopped','uptodate','abnormal','affinity0','unbound','other','oncpu0','active')
SCHEMA={'N10STAR1':('id','copy','generation','index','count','kind','num','supported')+MASKS,'N10STAQ1':('id','copy','generation','status','count','complete')}
def decode(text,identity,completed,prior,branch):
 if not 0<completed<=0xffffffff:raise ValueError('invalid generation')
 for line in text.splitlines():
  for occurrence in re.finditer(r'N10STA',line):
   if not re.match(r'(?:N10STAR1|N10STAQ1) ',line[occurrence.start():]):raise ValueError('malformed state prefix')
 found={tag:[[],[]] for tag in TAGS}
 for m in re.finditer(r'(N10STAR1|N10STAQ1) ([^\r\n]*)',text):
  tag,line=m.groups();frame=re.fullmatch(r'(.*?) checksum=([0-9a-f]{8})',line)
  if not frame:raise ValueError('malformed frame')
  body,digest=frame.groups();pairs=[x.split('=',1) for x in body.split(' ')]
  if any(len(x)!=2 for x in pairs) or tuple(x[0] for x in pairs)!=SCHEMA[tag]:raise ValueError('frame schema')
  raw=dict(pairs)
  if raw['id']!=identity:raise ValueError('identity differs')
  if checksum(body.encode('ascii'))!=int(digest,16):raise ValueError('checksum')
  row={'id':identity}
  for key,value in pairs[1:]:
   if not re.fullmatch(r'(?:0|-[1-9][0-9]*|[1-9][0-9]*)' if key=='status' else r'(?:0|[1-9][0-9]*)',value):raise ValueError('number syntax')
   n=int(value)
   if not (-(1<<31)<=n<(1<<31) if key=='status' else 0<=n<=0xffffffff):raise ValueError('number width')
   row[key]=n
  if row['copy'] not in (0,1):raise ValueError('copy')
  found[tag][row['copy']].append(row)
 for tag in TAGS:
  left=[{k:v for k,v in x.items() if k!='copy'} for x in found[tag][0]];right=[{k:v for k,v in x.items() if k!='copy'} for x in found[tag][1]]
  if left!=right:raise ValueError('copies differ')
  found[tag]=left
 q=found['N10STAQ1']
 if len(q)!=1:raise ValueError('summary count')
 q=q[0];generation=q['generation'];count=q['count']
 if not generation or ((generation+1)&0xffffffff or 1)!=completed or q['status'] or q['complete']!=1 or count>32:raise ValueError('transaction failed')
 rows=found['N10STAR1'];old=prior['rows'];other=branch['rows']
 if prior['generation']!=generation or branch['generation']!=generation or len(rows)!=count or len(old)!=count or len(other)!=count:raise ValueError('prior transaction differs')
 for i,r in enumerate(rows):
  if r['generation']!=generation or r['index']!=i or r['count']!=count or r['kind']!=old[i]['kind'] or r['kind']!=other[i]['kind']:raise ValueError('row identity')
  if r['kind']!=5:
   if r['num'] or r['supported'] or any(r[k] for k in MASKS):raise ValueError('unused fields')
   continue
  n=r['num']; used=r['used']; obs=r['observed']
  if n>32 or r['supported']!=1 or used >= (1<<n) or any(r[k] >= (1<<n) for k in MASKS):raise ValueError('mask bounds')
  if n!=old[i]['b'] or used!=old[i]['c'] or n!=other[i]['num'] or used!=other[i]['used'] or r['present']!=(other[i]['nonnull'] & used):raise ValueError('prior PMU differs')
  if not (used==r['present']==r['owned']==obs):raise ValueError('incomplete event')
  if (r['running']|r['stopped']|r['abnormal'])!=obs or r['running']&(r['stopped']|r['uptodate']|r['abnormal']):raise ValueError('state partition')
  if r['uptodate']&~(r['stopped']|r['abnormal']):raise ValueError('uptodate classification')
  if (r['affinity0']|r['unbound']|r['other'])!=obs or r['affinity0']&r['unbound'] or r['affinity0']&r['other'] or r['unbound']&r['other']:raise ValueError('affinity partition')
  if any(r[k]&~obs for k in MASKS[4:]):raise ValueError('unobserved event')
  for k in MASKS:r[k+'_count']=r[k].bit_count()
 return {'generation':generation,'rows':rows,'cpu0_pmu_state_audit':True}
