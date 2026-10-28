"""Validate RCU context frames, including non-ready but valid observations."""
import argparse,hashlib,json
from pathlib import Path
from decode_rcu_context import decode
from decode_reservation import checksum
CASES=['positive','negative','zero','not-watching','flags-nonzero','headroom-false','prior-generation','prior-count','prior-index','bad-class','bad-bool','bad-headroom','bad-checksum','missing-copy','duplicate','bad-prefix','noncanonical','copy-mismatch','schema-missing','row-generation','too-many','summary-status']
def frame(tag,fields):
 body=' '.join(f'{k}={v}' for k,v in fields);return f'{tag} {body} checksum={checksum(body.encode()):08x}'
def build(cls=2,room=1,watch=1,flags=0):
 lines=[]
 for copy in (0,1):
  lines.append(frame('N10RCM1',[('id','test'),('copy',copy),('generation',9),('chain_count',1),('watching',watch),('nesting_class',cls),('positive_headroom_two',room),('nmi_nonzero',flags),('task_nesting_nonzero',flags),('task_special_nonzero',flags),('irq_enter_disabled',flags)]));lines.append(frame('N10RCQ1',[('id','test'),('copy',copy),('generation',9),('status',0),('row_count',1),('complete',1)]))
 return '\n'.join(lines)
def prior():return {'generation':9,'rows':[{'generation':9,'index':0,'count':1}]}
def reject(text,p=None):
 try:decode(text,'test',10,p or prior())
 except ValueError:return
 raise AssertionError('invalid frame accepted')
def rewrite(text,key,value,tag='N10RCM1'):
 out=[]
 for line in text.splitlines():
  kind,tail=line.split(' ',1);body=tail.rsplit(' checksum=',1)[0]
  if kind==tag:body=' '.join(key+'='+str(value) if f.startswith(key+'=') else f for f in body.split(' '))
  out.append(kind+' '+body+' checksum=%08x'%checksum(body.encode()))
 return '\n'.join(out)
def main():
 a=argparse.ArgumentParser();a.add_argument('--output',type=Path);args=a.parse_args()
 for kwargs in ({},{'cls':0,'room':0},{'cls':1,'room':0},{'watch':0},{'flags':1},{'room':0}):assert decode(build(**kwargs),'test',10,prior())['cpu0_rcu_context_audit']
 for key in ('generation','count','index'):
  p=prior()
  if key=='generation':p[key]=8
  else:p['rows'][0][key]=2
  reject(build(),p)
 for key,val in [('nesting_class',3),('watching',2),('generation',8),('chain_count',33)]:reject(rewrite(build(),key,val))
 reject(rewrite(build(cls=1,room=0),'positive_headroom_two',1));reject(build().replace('checksum=','checksum=f',1));reject('\n'.join(build().splitlines()[:-1]));reject(build()+'\n'+build().splitlines()[0]);reject(build()+'\nN10RCX1 broken');reject(build().replace('watching=1','watching=01',1));reject(rewrite(build(),'status',1,'N10RCQ1'))
 lines=build().splitlines();tag,rest=lines[0].split(' ',1);body=rest.rsplit(' checksum=',1)[0].replace('watching=1','watching=0');lines[0]=tag+' '+body+' checksum=%08x'%checksum(body.encode());reject('\n'.join(lines))
 lines=build().splitlines();tag,rest=lines[0].split(' ',1);body=rest.rsplit(' checksum=',1)[0].replace(' watching=1','');lines[0]=tag+' '+body+' checksum=%08x'%checksum(body.encode());reject('\n'.join(lines))
 if args.output:
  args.output.mkdir(parents=True,exist_ok=False);h=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();result={'passed':True,'hardware_verified':False,'cases':CASES,'harness_sha256':h(Path(__file__)),'decoder_sha256':h(Path(__file__).with_name('decode_rcu_context.py'))};(args.output/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8')
 print('RCU decoder: 6 valid + 16 rejected')
if __name__=='__main__':main()
