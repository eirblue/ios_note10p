"""Strict v42 frame, identity, mapping, generation and copy tests."""
from decode_pmu_control import decode,SCHEMA
from decode_reservation import checksum

def frame(tag,fields):
 body=' '.join(f'{k}={fields[k]}' for k in SCHEMA[tag]);return f'{tag} {body} checksum={checksum(body.encode()):08x}'
def records(**changes):
 r=dict(id='test',copy=0,generation=1,index=0,chain_count=1,kind=5,num=32,used_sw=0x80000003,visible_phys=0xffffffff,used_phys=0xc0000001,current_el=1,model_match=1,variant=1,revision=0,pmuver=4,fgt=0,pmcr=31<<11,cntenset=0,intenset=0);r.update(changes)
 q=dict(id='test',copy=0,generation=1,status=0,row_count=1,complete=1);lines=[]
 for c in (0,1):
  r['copy']=q['copy']=c;lines.extend((frame('N10PCTR1',r),frame('N10PCTQ1',q)))
 return '\n'.join(lines)
def main():
 old={'generation':1,'rows':[{'kind':5,'b':32,'c':0x80000003}]};branch={'generation':1,'rows':[{'kind':5,'num':32,'used':0x80000003}]};state={'generation':1,'rows':[{'kind':5,'num':32,'used':0x80000003}]}
 valid=records();r=decode(valid,'test',2,old,branch,state);assert r['row']['cntenset']==r['row']['intenset']==0
 bad=[records(used_phys=0),records(visible_phys=0),records(current_el=2),records(variant=2),records(pmuver=5),records(fgt=1),records(pmcr=0),records(chain_count=2),valid+'\nN10PCTX1 bad',valid+'\n'+valid,valid.replace('cntenset=0','cntenset=1',1),valid.replace('generation=1','generation=0',1)]
 for i,text in enumerate(bad):
  try:decode(text,'test',2,old,branch,state)
  except ValueError:continue
  raise AssertionError('malformed case accepted: '+str(i))
 print('valid disabled control plus 12 malformed/cross-binding cases passed')
if __name__=='__main__':main()
