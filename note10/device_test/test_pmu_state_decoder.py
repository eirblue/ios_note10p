"""Focused transaction checks, including unused nonnull and STOPPED."""
from decode_pmu_state import decode,SCHEMA
from decode_reservation import checksum

def frame(tag,fields):
 body=' '.join(f'{k}={fields[k]}' for k in SCHEMA[tag])
 return f'{tag} {body} checksum={checksum(body.encode()):08x}'

def transaction():
 row=dict(id='test',copy=0,generation=1,index=0,count=1,kind=5,num=2,supported=1,used=1,present=1,owned=1,observed=1,running=0,stopped=1,uptodate=0,abnormal=0,affinity0=0,unbound=1,other=0,oncpu0=0,active=0)
 q=dict(id='test',copy=0,generation=1,status=0,count=1,complete=1); lines=[]
 for c in (0,1):
  row['copy']=q['copy']=c;lines.extend((frame('N10STAR1',row),frame('N10STAQ1',q)))
 return '\n'.join(lines)

def main():
 prior={'generation':1,'rows':[{'kind':5,'b':2,'c':1}]};branch={'generation':1,'rows':[{'kind':5,'num':2,'used':1,'nonnull':3}]};text=transaction()
 result=decode(text,'test',2,prior,branch)
 assert result['rows'][0]['stopped_count']==1 and result['rows'][0]['unbound_count']==1
 for bad in ('N10STAX1 broken','N10STAQ1 bad'):
  try:decode(text+'\n'+bad,'test',2,prior,branch)
  except ValueError:pass
  else:raise AssertionError('malformed input accepted')
 print('valid STOPPED/unused nonnull and malformed rejection passed')
if __name__=='__main__':main()
