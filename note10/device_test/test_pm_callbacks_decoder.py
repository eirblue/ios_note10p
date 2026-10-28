"""Exercise strict semantic mutations against both copies of actual producer output."""
import argparse,hashlib,json,re
from pathlib import Path
from decode_pm_callbacks import decode
from decode_reservation import checksum
ID='0123456789abcdef0123456789abcdef'
def mutate(text,tag,selector,changes):
 pattern=re.compile(r'('+tag+r') ([^\r\n]*?) checksum=[0-9a-f]{8}')
 changed=0
 def sub(m):
  nonlocal changed
  body=m.group(2);fields=dict(x.split('=',1) for x in body.split(' '))
  if not all(fields.get(k)==v for k,v in selector.items()):return m.group(0)
  fields.update(changes);body=' '.join(k+'='+v for k,v in fields.items());changed+=1
  return m.group(1)+' '+body+' checksum='+format(checksum(body.encode()),'08x')
 out=pattern.sub(sub,text)
 if changed!=2:raise ValueError('Mutation did not reach both copies')
 return out
def main():
 p=argparse.ArgumentParser();p.add_argument('--native',required=True);p.add_argument('--output',required=True);a=p.parse_args();native=Path(a.native);o=Path(a.output);o.mkdir(parents=True,exist_ok=True);text=(native/'mode-0.log').read_text();decode(text,ID,2)
 cases={'null_notifier':('0','0',{'s0':'0'}),'notifier_unused':('0','0',{'a':'1'}),'priority_order':('0','0',{'priority':'-6'}),'empty_name':('0','1',{'name':'invalid'}),'empty_scalar':('0','1',{'a':'1'}),'empty_symbol':('0','1',{'s1':'1'}),'irq_unused':('0','1',{'priority':'1'}),'source_bool':('0','2',{'a':'2'}),'source_unused':('0','2',{'s2':'1'}),'event_state':('0','3',{'a':'5'}),'event_mask':('0','3',{'mask':'100'}),'event_unused':('0','3',{'c':'1'}),'symbol_reference':('0','3',{'s0':'3'}),'signed_overflow':('0','3',{'x':'2147483648'}),'uint_overflow':('0','3',{'b':'4294967296'})}
 outcomes=[]
 for name,(phase,family,changes) in cases.items():
  bad=mutate(text,'N10CBR1',{'phase':phase,'family':family,'index':'0'},changes)
  try:decode(bad,ID,2)
  except ValueError:outcomes.append({'case':name,'passed':True});continue
  raise AssertionError('decoder accepted '+name)
 result={'passed':True,'cases':len(outcomes),'outcomes':outcomes,'decoder_sha256':hashlib.sha256((Path(__file__).parent/'decode_pm_callbacks.py').read_bytes()).hexdigest(),'producer_log_sha256':hashlib.sha256((native/'mode-0.log').read_bytes()).hexdigest(),'harness_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()};(o/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print('decoder mutation cases:',len(outcomes))
if __name__=='__main__':main()
