"""Focused strict protocol checks for the reference audit."""
import argparse,hashlib,json
from pathlib import Path
from decode_fpsimd_reference import decode
from decode_reservation import checksum

def frame(tag, fields):
 body=' '.join(f'{k}={v}' for k,v in fields)
 return f'{tag} {body} checksum={checksum(body.encode()):08x}'
def build(reference=0,*,depth=2):
 out=[]
 for copy in (0,1):
  out.append(frame('N10FPSM1',[('id','test'),('copy',copy),('generation',9),('index',0),('chain_count',1),('kind',3),('reference',reference),('mm',1),('foreign',1),('depth',depth)]))
  out.append(frame('N10FPSQ1',[('id','test'),('copy',copy),('generation',9),('status',0),('row_count',1),('complete',1)]))
 return '\n'.join(out)
def prior(reference=0):
 return {'generation':9,'rows':[{'generation':9,'index':0,'count':1,'kind':3,'valid':15,'a':1,'b':1,'c':2,'d':int(reference==1)}]}
def reject(text,p=None):
 try:decode(text,'test',10,p or prior())
 except ValueError:return
 raise AssertionError('invalid protocol accepted')
def rewrite(text,key,value):
 out=[]
 for line in text.splitlines():
  tag,rest=line.split(' ',1);body=rest.rsplit(' checksum=',1)[0]
  if tag=='N10FPSM1':
   fields=body.split(' ');fields=[(key+'='+str(value)) if f.startswith(key+'=') else f for f in fields];body=' '.join(fields)
  out.append(tag+' '+body+' checksum=%08x'%checksum(body.encode()))
 return '\n'.join(out)
def main():
 parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path);args=parser.parse_args()
 for n in range(3):assert decode(build(n),'test',10,prior(n))['row']['reference']==n
 p=prior();p['rows'][0]['valid']=7;reject(build(),p)
 p=prior();p['rows'][0]['d']=1;reject(build(),p)
 p=prior();p['generation']=8;reject(build(),p)
 reject(build(depth=2147483648));reject(build().replace('N10FPSM1','N10FPSM2',1));reject(build().replace('checksum=','checksum=f',1));reject('\n'.join(build().splitlines()[:-1]));reject(build()+'\n'+build().splitlines()[0]);reject(build().replace('reference=0','reference=00',1))
 for key,value in [('generation',8),('index',1),('chain_count',2),('kind',4),('mm',0),('foreign',0),('depth',3),('reference',1)]:reject(rewrite(build(),key,value))
 reject(build().replace('id=test','id=other',1));reject(build()+'\nN10FPS malformed')
 lines=build().splitlines();tag,rest=lines[0].split(' ',1);body=rest.rsplit(' checksum=',1)[0].replace('mm=1','mm=0');lines[0]=tag+' '+body+' checksum=%08x'%checksum(body.encode());reject('\n'.join(lines))
 lines=build().splitlines();tag,rest=lines[0].split(' ',1);body=rest.rsplit(' checksum=',1)[0].replace(' mm=1','');lines[0]=tag+' '+body+' checksum=%08x'%checksum(body.encode());reject('\n'.join(lines))
 cases=['null','current','other','prior-mask','prior-equality','prior-generation','depth-width','prefix','checksum','missing-copy','duplicate','noncanonical','row-generation','index','count','kind','mm','foreign','depth','reference','identity','extra-prefix','copy-mismatch','schema-missing']
 if args.output:
  args.output.mkdir(parents=True,exist_ok=False);(args.output/'result.json').write_text(json.dumps({'passed':True,'hardware_verified':False,'cases':cases,'harness_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'decoder_sha256':hashlib.sha256(Path(__file__).with_name('decode_fpsimd_reference.py').read_bytes()).hexdigest()},indent=2)+'\n',encoding='utf8')
 print('reference decoder: 3 valid + 21 rejected')
if __name__=='__main__':main()
