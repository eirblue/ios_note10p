"""Strict two-copy CPU0 preconditions and banked GIC observation decoder."""
import re
from decode_reservation import checksum
TAGS=('N10PRR1','N10PRG1','N10PRQ1')
SCHEMA={'N10PRR1':('id','copy','generation','index','count','kind','priority','valid','a','b','c','d','e','f','g','h'),'N10PRG1':('id','copy','generation','phase','enable','active','config0','config1','p0','p1','p2','p3','p4','p5','p6','p7','matches'),'N10PRQ1':('id','copy','generation','status','count','complete','gic_complete')}
SIGNED={'priority','status','a','b','c','d','e','f','g','h'}
def decode(text,identity,completed):
 if not 0<completed<=0xffffffff:raise ValueError('invalid completed generation')
 found={tag:[[],[]] for tag in TAGS}
 for line in text.splitlines():
  if 'N10PR' in line and not re.search(r'\b(?:N10PRR1|N10PRG1|N10PRQ1) ',line):raise ValueError('malformed precondition prefix')
 for m in re.finditer(r'(N10PRR1|N10PRG1|N10PRQ1) ([^\r\n]*)',text):
  tag,line=m.groups();frame=re.fullmatch(r'(.*?) checksum=([0-9a-f]{8})',line)
  if not frame:raise ValueError('malformed frame')
  body,digest=frame.groups();pairs=[x.split('=',1) for x in body.split(' ')]
  if any(len(x)!=2 for x in pairs) or tuple(x[0] for x in pairs)!=SCHEMA[tag]:raise ValueError('frame schema differs')
  raw=dict(pairs)
  if raw['id']!=identity:continue
  if checksum(body.encode('ascii'))!=int(digest,16):raise ValueError('checksum differs')
  row={'id':identity}
  for key,value in pairs[1:]:
   if not re.fullmatch(r'(?:0|-?[1-9][0-9]*)' if key in SIGNED else r'(?:0|[1-9][0-9]*)',value):raise ValueError('number syntax differs')
   number=int(value);lo=-(1<<63) if key in SIGNED else 0;hi=(1<<63)-1 if key in SIGNED else (1<<32)-1
   if not lo<=number<=hi:raise ValueError('number width differs')
   if key in ('status','priority') and not -(1<<31)<=number<(1<<31):raise ValueError('int width differs')
   row[key]=number
  if row['copy'] not in (0,1):raise ValueError('copy differs')
  found[tag][row['copy']].append(row)
 for tag in TAGS:
  left=[{k:v for k,v in x.items() if k!='copy'} for x in found[tag][0]];right=[{k:v for k,v in x.items() if k!='copy'} for x in found[tag][1]]
  if left!=right:raise ValueError('copies differ')
  found[tag]=left
 q=found['N10PRQ1']
 if len(q)!=1:raise ValueError('summary missing or repeated')
 q=q[0];generation=q['generation'];count=q['count']
 if not generation or ((generation+1)&0xffffffff or 1)!=completed or q['status'] or q['complete']!=1 or q['gic_complete']!=1 or count>32:raise ValueError('transaction failed')
 rows=found['N10PRR1'];gic=found['N10PRG1']
 if len(rows)!=count or len(gic)!=3:raise ValueError('row count differs')
 for i,r in enumerate(rows):
  if r['generation']!=generation or r['index']!=i or r['count']!=count or r['kind']>6 or not -(1<<31)<=r['priority']<(1<<31):raise ValueError('row identity differs')
  if i and rows[i-1]['priority']<r['priority']:raise ValueError('priority order differs')
  v=[r[x] for x in 'abcdefgh'];kind=r['kind'];valid=r['valid']
  if kind<=2:
   if valid or any(v):raise ValueError('unclassified fields differ')
  elif kind==3:
   if valid!=15 or v[0] not in (0,1) or v[1] not in (0,1) or not -(1<<31)<=v[2]<(1<<31) or v[3] not in (0,1) or any(v[4:]):raise ValueError('fpsimd fields differ')
  elif kind==4:
   if valid not in (3,7) or not -(1<<31)<=v[0]<(1<<31) or v[1] not in (0,1) or (valid==7)!=bool(v[1]) or (v[2] not in (0,1) if valid==7 else v[2]!=0) or any(v[3:]):raise ValueError('schedutil fields differ')
  elif kind==5:
   if valid!=31 or v[0] not in (0,1) or not 0<=v[1]<=32 or not 0<=v[2]<(1<<v[1]) or v[3]!=v[2].bit_count() or not 0<=v[4]<=v[1] or any(v[5:]):raise ValueError('pmu fields differ')
  elif kind==6:
   if valid!=3 or not -(1<<31)<=v[0]<(1<<31) or v[1] not in (0,1) or any(v[2:]):raise ValueError('ehld fields differ')
 for i,r in enumerate(gic):
  if r['generation']!=generation or r['phase']!=i or r['matches'] not in (0,1):raise ValueError('gic observation differs')
 return {'generation':generation,'rows':rows,'gic':gic}
