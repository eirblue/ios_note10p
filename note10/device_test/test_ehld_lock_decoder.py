"""Exercise strict EHLD wire decoding and the busy-valid sentinel."""
import argparse, hashlib, json
from pathlib import Path
from decode_ehld_lock import decode
from decode_reservation import checksum
from decode_pm_preconditions import decode as decode_prior

CASES=['valid-busy','valid-true-boundaries','valid-false','wrong-generation','wrong-index','wrong-count','missing-copy','duplicate','busy-nonzero-sentinel','busy-running-valid','boolean-mismatch','bad-mask','bad-status','bad-prefix','noncanonical-number']
def frame(tag,fields):
 body=' '.join(f'{k}={v}' for k,v in fields);return f'{tag} {body} checksum={checksum(body.encode()):08x}'
def build(lock=1,valid=None,running=1,old=1,generation=9,index=1,count=3):
 if valid is None:valid=lock
 out=[]
 for copy in (0,1):
  out.append(frame('N10ELM1',[('id','test'),('copy',copy),('generation',generation),('index',index),('chain_count',count),('lock_available',lock),('running_valid',valid),('running',running)]))
  out.append(frame('N10ELQ1',[('id','test'),('copy',copy),('generation',generation),('status',0),('row_count',1),('complete',1)]))
 return '\n'.join(out)
def prior(value=1,generation=9,index=1,count=3,valid=3):
 lines=[]
 for copy in (0,1):
  for i in range(count):
   kind=6 if i==index else 1;mask=valid if i==index else 0;a=value if i==index else 0;b=1 if i==index else 0
   lines.append(frame('N10PRR1',[('id','test'),('copy',copy),('generation',generation),('index',i),('count',count),('kind',kind),('priority',10-i),('valid',mask),('a',a),('b',b),('c',0),('d',0),('e',0),('f',0),('g',0),('h',0)]))
  for phase in range(3):
   lines.append(frame('N10PRG1',[('id','test'),('copy',copy),('generation',generation),('phase',phase),('enable',0),('active',0),('config0',0),('config1',0),('p0',0),('p1',0),('p2',0),('p3',0),('p4',0),('p5',0),('p6',0),('p7',0),('matches',0)]))
  lines.append(frame('N10PRQ1',[('id','test'),('copy',copy),('generation',generation),('status',0),('count',count),('complete',1),('gic_complete',1)]))
 completed=((generation+1)&0xffffffff) or 1
 return decode_prior('\n'.join(lines),'test',completed)
def reject(text,p=None,completed=10):
 try:decode(text,'test',completed,p or prior())
 except (ValueError,KeyError,TypeError):return
 raise AssertionError('invalid EHLD evidence accepted')
def rewrite(text,tag,key,value,copy=None):
 out=[]
 for line in text.splitlines():
  kind,tail=line.split(' ',1);body=tail.rsplit(' checksum=',1)[0]
  if kind==tag and (copy is None or f'copy={copy} ' in body or body.endswith(f'copy={copy}')):
   body=' '.join(key+'='+str(value) if item.startswith(key+'=') else item for item in body.split(' '))
  out.append(frame(kind,[x.split('=',1) for x in body.split(' ')]))
 return '\n'.join(out)
def main():
 p=argparse.ArgumentParser();p.add_argument('--output',type=Path);a=p.parse_args()
 for value in (-(1<<31),-1,1,(1<<31)-1):
  assert decode(build(lock=1,valid=1,running=1,old=value),'test',10,prior(value))['cpu0_ehld_lock_audit']
 assert decode(build(lock=0,valid=0,running=0,old=-1),'test',10,prior(-1))['cpu0_ehld_lock_audit']
 assert decode(build(lock=1,valid=1,running=0,old=0),'test',10,prior(0))['row']['running']==0
 assert decode(build(lock=1,valid=1,running=1,old=1,generation=0xffffffff),'test',1,prior(1,0xffffffff))['generation']==0xffffffff
 reject(build(generation=8),completed=10);reject(build(index=0));reject(build(count=2));reject('\n'.join(build().splitlines()[:-1]));reject(build()+'\n'+build().splitlines()[0]);reject(build(lock=0,valid=0,running=1),prior(-1));reject(build(lock=0,valid=1,running=0),prior(-1))
 reject(build(lock=1,valid=1,running=0),prior(1));bad=prior(-1);bad['rows'][1]['valid']=1;reject(build(),bad);reject(rewrite(build(),'N10ELQ1','status',1));reject(build()+'\nN10ELX1 malformed');reject(build().replace('index=1','index=01',1));reject(rewrite(build(),'N10ELM1','running',0,copy=1));reject(build().replace('checksum=','checksum=f',1));reject(build(generation=0),completed=1);reject(build(generation=0x100000000),completed=1);reject(build(),prior(1,8));reject(build(),prior(1,index=0));reject(build(),prior(1,count=2));
 for overflow in ((1<<31),-(1<<31)-1):
  bad=prior(-1);bad['rows'][1]['a']=overflow;reject(build(lock=0,valid=0,running=0),bad)
 if a.output:
  a.output.mkdir(parents=True,exist_ok=False);h=lambda f:hashlib.sha256(f.read_bytes()).hexdigest();(a.output/'result.json').write_text(json.dumps({'passed':True,'hardware_verified':False,'cases':CASES,'harness_sha256':h(Path(__file__)),'decoder_sha256':h(Path(__file__).with_name('decode_ehld_lock.py')),'prior_decoder_sha256':h(Path(__file__).with_name('decode_pm_preconditions.py'))},indent=2)+'\n',encoding='utf8')
 print('EHLD lock decoder: boundary and mutation cases passed')
if __name__=='__main__':main()
