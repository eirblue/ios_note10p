"""Validate v42 EL1-visible PMU control frames against prior observations."""
import re
from decode_reservation import checksum
TAGS=('N10PCTR1','N10PCTQ1')
SCHEMA={'N10PCTR1':('id','copy','generation','index','chain_count','kind','num','used_sw','visible_phys','used_phys','current_el','model_match','variant','revision','pmuver','fgt','pmcr','cntenset','intenset'),'N10PCTQ1':('id','copy','generation','status','row_count','complete')}
def decode(text,identity,completed,prior,branch,state):
 if not 0<completed<=0xffffffff:raise ValueError('invalid completed generation')
 for line in text.splitlines():
  for occurrence in re.finditer(r'N10PCT',line):
   if not re.match(r'(?:N10PCTR1|N10PCTQ1) ',line[occurrence.start():]):raise ValueError('malformed control prefix')
 found={tag:[[],[]] for tag in TAGS}
 for m in re.finditer(r'(N10PCTR1|N10PCTQ1) ([^\r\n]*)',text):
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
 q=found['N10PCTQ1'];rows=found['N10PCTR1']
 if len(q)!=1 or len(rows)!=1:raise ValueError('summary/row count')
 q=q[0];r=rows[0];g=q['generation'];index=r['index'];num=r['num']
 if not g or ((g+1)&0xffffffff or 1)!=completed or q['status'] or q['row_count']!=1 or q['complete']!=1 or r['generation']!=g:raise ValueError('transaction failed')
 if any(x.get('generation')!=g for x in (prior,branch,state)):raise ValueError('prior generation differs')
 old,br,sw=prior['rows'],branch['rows'],state['rows'];count=len(old)
 if not count or len(br)!=count or len(sw)!=count or r['chain_count']!=count or index>=count or r['kind']!=5:raise ValueError('chain identity')
 if sum(x['kind']==5 for x in old)!=1 or old[index]['kind']!=5 or br[index]['kind']!=5 or sw[index]['kind']!=5:raise ValueError('PMU multiplicity differs')
 if not 1<=num<=32 or r['used_sw'] >= (1<<num) or num!=old[index]['b'] or num!=br[index]['num'] or num!=sw[index]['num'] or r['used_sw']!=old[index]['c'] or r['used_sw']!=br[index]['used'] or r['used_sw']!=sw[index]['used']:raise ValueError('prior PMU differs')
 if (r['current_el'],r['model_match'],r['variant'],r['revision'],r['pmuver'],r['fgt'])!=(1,1,1,0,4,0):raise ValueError('identity gate differs')
 if ((r['pmcr']>>11)&31)+1!=num:raise ValueError('EL1 visible PMCR count differs')
 visible=(1<<31)|((1<<(num-1))-1);used=0
 for i in range(num):
  if r['used_sw'] & (1<<i):used|=1<<((i-1)&31)
 if r['visible_phys']!=visible or r['used_phys']!=used:raise ValueError('counter mapping differs')
 return {'generation':g,'row':r,'cpu0_pmu_control_audit':True,'interpretation':'EL1-visible only; HPMN and higher-EL trap regime are not observed'}
