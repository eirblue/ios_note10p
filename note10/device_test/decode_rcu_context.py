"""Validate v44 RCU context frames against prior observations."""
import re
from decode_reservation import checksum
TAGS=('N10RCM1','N10RCQ1')
SCHEMA={'N10RCM1':('id','copy','generation','chain_count','watching','nesting_class','positive_headroom_two','nmi_nonzero','task_nesting_nonzero','task_special_nonzero','irq_enter_disabled'),'N10RCQ1':('id','copy','generation','status','row_count','complete')}
def decode(text,identity,completed,prior):
 if not 0<completed<=0xffffffff:raise ValueError('invalid completed generation')
 for line in text.splitlines():
  for occurrence in re.finditer(r'N10RC',line):
   if not re.match(r'(?:N10RCM1|N10RCQ1) ',line[occurrence.start():]):raise ValueError('malformed RCU prefix')
 found={tag:[[],[]] for tag in TAGS}
 for m in re.finditer(r'(N10RCM1|N10RCQ1) ([^\r\n]*)',text):
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
 q=found['N10RCQ1'];rows=found['N10RCM1']
 if len(q)!=1 or len(rows)!=1:raise ValueError('summary/row count')
 q=q[0];r=rows[0];g=q['generation']
 if not g or ((g+1)&0xffffffff or 1)!=completed or q['status'] or q['row_count']!=1 or q['complete']!=1 or r['generation']!=g:raise ValueError('transaction failed')
 if prior.get('generation')!=g:raise ValueError('prior generation differs')
 old=prior['rows'];count=len(old)
 if not 1<=count<=32 or r['chain_count']!=count:raise ValueError('chain count differs')
 for index,p in enumerate(old):
  if p.get('generation')!=g or p.get('index')!=index or p.get('count')!=count:raise ValueError('prior row identity differs')
 if r['nesting_class'] not in (0,1,2) or any(r[k] not in (0,1) for k in ('watching','positive_headroom_two','nmi_nonzero','task_nesting_nonzero','task_special_nonzero','irq_enter_disabled')):raise ValueError('field range differs')
 if r['positive_headroom_two'] and r['nesting_class']!=2:raise ValueError('headroom requires positive nesting')
 return {'generation':g,'row':r,'cpu0_rcu_context_audit':True,'interpretation':'separate same-walk RAM reads are not a readiness verdict or atomic snapshot'}
