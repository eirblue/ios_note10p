"""Strictly decode two complete v35 callback inventory copies."""
import re
from decode_reservation import checksum
TAGS=('N10CBS1','N10CBR1','N10CBQ1')
SCHEMAS={
 'N10CBS1':('id','copy','generation','index','count','name'),
 'N10CBR1':('id','copy','generation','phase','family','index','count','name','a','b','c','d','mask','x','y','priority','s0','s1','s2','s3','s4'),
 'N10CBQ1':('id','copy','generation','status','symbols','seen0','seen1','seen2','error0','error1','error2','bad'),
}
SIGNED={'x','y','priority','status','error0','error1','error2','bad'}
def decode(text,identity,completed):
 if not 0<completed<=0xffffffff: raise ValueError('Invalid completed generation')
 found={tag:[[],[]] for tag in TAGS}
 pattern=re.compile(r'(N10CBS1|N10CBR1|N10CBQ1) ([^\r\n]*)')
 for match in pattern.finditer(text):
  tag,line=match.groups(); frame=re.fullmatch(r'(.*?) checksum=([0-9a-f]{8})',line)
  if not frame: raise ValueError('Malformed callback frame')
  body,digest=frame.groups(); tokens=body.split(' '); names=SCHEMAS[tag]
  if len(tokens)!=len(names): raise ValueError('Callback frame field count differs')
  pairs=[x.split('=',1) for x in tokens]
  if any(len(x)!=2 for x in pairs) or tuple(x[0] for x in pairs)!=names: raise ValueError('Callback frame schema differs')
  raw=dict(pairs)
  if raw['id']!=identity: continue
  if checksum(body.encode('ascii'))!=int(digest,16): raise ValueError('Callback checksum differs')
  row={}
  for key,value in raw.items():
   if key in ('id','name'): row[key]=value; continue
   base=16 if key=='mask' else 10
   regex=r'[0-9a-f]+' if base==16 else (r'-?(?:0|[1-9][0-9]*)' if key in SIGNED else r'(?:0|[1-9][0-9]*)')
   if not re.fullmatch(regex,value): raise ValueError('Callback numeric syntax differs')
   number=int(value,base); lo=-(1<<31) if key in SIGNED else 0; hi=(1<<31)-1 if key in SIGNED else ((1<<64)-1 if key=='mask' else (1<<32)-1)
   if not lo<=number<=hi: raise ValueError('Callback numeric width differs')
   row[key]=number
  if row['copy'] not in (0,1): raise ValueError('Callback copy differs')
  found[tag][row['copy']].append(row)
 for tag in TAGS:
  left=[{k:v for k,v in x.items() if k!='copy'} for x in found[tag][0]]; right=[{k:v for k,v in x.items() if k!='copy'} for x in found[tag][1]]
  if left!=right: raise ValueError('Callback copies differ')
  found[tag]=left
 q=found['N10CBQ1']
 if len(q)!=1: raise ValueError('Callback summary missing or duplicated')
 q=q[0]; gen=q['generation']
 if not gen or ((gen+1)&0xffffffff or 1)!=completed or q['status'] or q['bad'] or any(q['error'+str(i)] for i in range(3)) or any(q['seen'+str(i)]!=1 for i in range(3)) or q['symbols']>128: raise ValueError('Callback transaction failed')
 syms=found['N10CBS1']; count=q['symbols']
 if len(syms)!=count: raise ValueError('Callback symbol count differs')
 for i,s in enumerate(syms,1):
  if s['generation']!=gen or s['index']!=i or s['count']!=count or not 1<=len(s['name'])<=96 or any(ord(c)<33 or ord(c)>126 or c in '=,' for c in s['name']): raise ValueError('Callback symbol differs')
 rows=found['N10CBR1']; cursor=0; phases=[]
 for phase in range(3):
  families=[]
  for family,limit in enumerate((32,64,32,64)):
   if cursor>=len(rows): raise ValueError('Callback family missing')
   count=rows[cursor]['count']
   if count>limit or (family in (2,3) and count==0): raise ValueError('Callback count invalid')
   group=rows[cursor:cursor+max(count,1)]; cursor+=max(count,1)
   if len(group)!=max(count,1): raise ValueError('Callback rows missing')
   for i,row in enumerate(group):
    if (row['generation'],row['phase'],row['family'],row['index'],row['count'])!=(gen,phase,family,i,count): raise ValueError('Callback coverage differs')
    name=row['name']
    if name!='-' and (not 1<=len(name)<=96 or any(ord(c)<33 or ord(c)>126 or c in '=,' for c in name)): raise ValueError('Invalid object name')
    if family in (0,1) and name!='-': raise ValueError('Unexpected object name')
    if family in (2,3) and count and name=='-': raise ValueError('Missing object name')
    if any(row['s'+str(j)]>len(syms) for j in range(5)): raise ValueError('Unknown callback symbol')
    if not count and (name!='-' or any(row[k] for k in ('a','b','c','d','mask','x','y','priority','s0','s1','s2','s3','s4'))): raise ValueError('Noncanonical empty row')
    unused={0:('a','b','c','d','mask','x','y','s1','s2','s3','s4'),1:('x','y','priority'),2:('b','c','d','mask','x','y','priority','s2','s3','s4'),3:('c','d','priority','s2','s3','s4')}[family]
    if any(row[k] for k in unused): raise ValueError('Unexpected family fields')
    if family==1 and (row['d'] not in (0,1) or (not row['b'] and any(row['s'+str(j)] for j in (2,3,4)))): raise ValueError('Invalid generic IRQ metadata')
    if family==2 and row['a'] not in (0,1): raise ValueError('Invalid current clocksource flag')
    if family==3 and row['mask'] & ~255: raise ValueError('Clockevent CPU mask exceeds eight CPUs')
    if family==0 and count and not row['s0']: raise ValueError('Null notifier callback')
    if family==3 and row['a']>4: raise ValueError('Invalid clockevent state')
   if family==0 and any(group[i]['priority']<group[i+1]['priority'] for i in range(len(group)-1)): raise ValueError('Notifier priority order differs')
   if family==2 and sum(x['a'] for x in group)!=1: raise ValueError('Clocksource current membership differs')
   families.append(group if count else [])
  phases.append(families)
 if cursor!=len(rows): raise ValueError('Extra callback rows')
 return {'cpu_pm_notifier_inventory':True,'generic_irq_callback_inventory':True,'clocksource_callback_inventory':True,'clockevent_callback_inventory':True,'generation':gen,'symbols':[x['name'] for x in syms],'phases':phases,'callbacks_executed':False,'hardware_dma_shutdown_verified':False,'xnu_executed':False}
