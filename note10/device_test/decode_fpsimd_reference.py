"""Validate v43 FPSIMD reference frames against prior observations."""
import re
from decode_reservation import checksum
TAGS=('N10FPSM1','N10FPSQ1')
SCHEMA={'N10FPSM1':('id','copy','generation','index','chain_count','kind','reference','mm','foreign','depth'),'N10FPSQ1':('id','copy','generation','status','row_count','complete')}
def decode(text,identity,completed,prior):
 if not 0<completed<=0xffffffff:raise ValueError('invalid completed generation')
 for line in text.splitlines():
  for occurrence in re.finditer(r'N10FPS',line):
   if not re.match(r'(?:N10FPSM1|N10FPSQ1) ',line[occurrence.start():]):raise ValueError('malformed FPSIMD prefix')
 found={tag:[[],[]] for tag in TAGS}
 for m in re.finditer(r'(N10FPSM1|N10FPSQ1) ([^\r\n]*)',text):
  tag,line=m.groups();frame=re.fullmatch(r'(.*?) checksum=([0-9a-f]{8})',line)
  if not frame:raise ValueError('malformed frame')
  body,digest=frame.groups();pairs=[x.split('=',1) for x in body.split(' ')]
  if any(len(x)!=2 for x in pairs) or tuple(x[0] for x in pairs)!=SCHEMA[tag]:raise ValueError('frame schema')
  if pairs[0][1]!=identity:raise ValueError('identity differs')
  if checksum(body.encode('ascii'))!=int(digest,16):raise ValueError('checksum differs')
  row={'id':identity}
  for key,value in pairs[1:]:
   if not re.fullmatch(r'(?:0|-[1-9][0-9]*|[1-9][0-9]*)' if key=='status' else r'(?:0|[1-9][0-9]*)',value):raise ValueError('number syntax')
   n=int(value)
   if not (-(1<<31)<=n<(1<<31) if key=='status' else 0<=n<=0xffffffff):raise ValueError('number width')
   row[key]=n
  if row['copy'] not in (0,1):raise ValueError('copy differs')
  found[tag][row['copy']].append(row)
 for tag in TAGS:
  left=[{k:v for k,v in x.items() if k!='copy'} for x in found[tag][0]];right=[{k:v for k,v in x.items() if k!='copy'} for x in found[tag][1]]
  if left!=right:raise ValueError('copies differ')
  found[tag]=left
 q=found['N10FPSQ1'];rows=found['N10FPSM1']
 if len(q)!=1 or len(rows)!=1:raise ValueError('summary/row count')
 q=q[0];r=rows[0];g=q['generation'];index=r['index']
 if not g or ((g+1)&0xffffffff or 1)!=completed or q['status'] or q['row_count']!=1 or q['complete']!=1 or r['generation']!=g:raise ValueError('transaction failed')
 if prior.get('generation')!=g:raise ValueError('prior generation differs')
 old=prior['rows'];count=len(old)
 if not count or count>32 or r['chain_count']!=count or index>=count or r['kind']!=3 or sum(x['kind']==3 for x in old)!=1:raise ValueError('chain identity differs')
 p=old[index]
 if p['index']!=index or p['count']!=count or p['generation']!=g or p['kind']!=3 or p['valid']!=15:raise ValueError('prior row identity differs')
 if r['reference'] not in (0,1,2) or r['mm'] not in (0,1) or r['foreign'] not in (0,1) or r['depth']>0x7fffffff:raise ValueError('observation differs')
 if (p['a'],p['b'],p['c'],p['d'])!=(r['mm'],r['foreign'],r['depth'],int(r['reference']==1)):raise ValueError('prior observation differs')
 return {'generation':g,'row':r,'cpu0_fpsimd_reference_audit':True,'interpretation':'reference class only; separate same-walk reads are not an atomic snapshot'}
