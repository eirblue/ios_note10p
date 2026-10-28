"""Execute the actual v45 worker/report producer with EHLD feature on and off."""
import argparse,hashlib,json,re,subprocess,sys
from pathlib import Path
import test_rcu_context_worker as prior
from test_pm_callbacks_producer import clean
from decode_pm_preconditions import decode as decode_pre
from decode_ehld_lock import decode as decode_ehld
from decode_reservation import checksum

IDENTITY='0123456789abcdef0123456789abcdef'
EHLD_MOCK=r'''int n10_ehld_lock_read(struct n10_ehld_lock_sample *s,unsigned int completed){(void)completed;if(mode==20)return -EIO;s->generation=1;s->seen=s->completed=1;s->row.index=6;s->row.chain_count=7;s->row.lock_available=mode==23?0:1;s->row.running_valid=mode==23?0:1;s->row.running=mode==23?0:mode==24?1:0;return 0;}'''
MAIN=r'''
int main(int argc,char**argv){mode=atoi(argv[1]);
#ifdef CONFIG_NOTE10_RCU_CONTEXT_AUDIT
 if(mode==17 || mode==18){unsigned int budget=mode==17?0:4090;return n10_rcu_emit("N10RCM1","",mode==17?512:10,&budget,0)?0:1;}
#endif
#ifdef CONFIG_NOTE10_EHLD_LOCK_AUDIT
 if(mode==22){unsigned int budget=0;char frame[384];memset(frame,'x',sizeof(frame));if(n10_ehld_lock_emit("N10ELM1",frame,383,&budget,0))return 1;if(n10_ehld_lock_emit("N10ELM1",frame,384,&budget,0)!=-E2BIG)return 2;return 0;}
 if(mode==25){unsigned int budget=2040;return n10_ehld_lock_emit("N10ELM1","12345678901234567890",20,&budget,0)==-E2BIG?0:1;}
#endif
 n10_pm_worker(NULL);return 0;}
'''

def make_code(root):
 worker=root/'arch/arm64/mm/note10_pm_timer_roundtrip.c'
 probe=root/'arch/arm64/mm/note10_ehld_lock_probe.c'
 if not worker.is_file() or not probe.is_file():raise ValueError('required snapshot source missing')
 contract=clean('ehld_lock_contract.h')
 producer='\n'.join(line for line in probe.read_text(encoding='utf8').splitlines() if not line.startswith('#include'))+'\n'
 code=prior.make_code(root)
 code=code.replace('s->row[6].value[1]=1;','s->row[6].value[0]=mode==24?1:0;s->row[6].value[1]=1;',1)
 if code.count('int main(')!=1:raise ValueError('worker harness main cardinality')
 worker_anchor='static void n10_pm_worker(struct work_struct *unused)\n{'
 if code.count(worker_anchor)!=1:raise ValueError('actual worker function cardinality')
 code=code.replace(worker_anchor,contract+'\n'+EHLD_MOCK+'\n'+producer+'\n'+worker_anchor,1)
 return code[:code.rfind('int main(')]+MAIN

def main():
 p=argparse.ArgumentParser();p.add_argument('--source-root',required=True,type=Path);p.add_argument('--output',required=True,type=Path);p.add_argument('--cc',required=True);a=p.parse_args();root=a.source_root;out=a.output;out.mkdir(parents=True,exist_ok=False)
 code=make_code(root)
 paths={'worker':'arch/arm64/mm/note10_pm_timer_roundtrip.c','producer':'arch/arm64/mm/note10_ehld_lock_probe.c'}
 cases=[]
 for label,define in (('enabled','#define CONFIG_NOTE10_RCU_CONTEXT_AUDIT 1\n#define CONFIG_NOTE10_EHLD_LOCK_AUDIT 1\n'),('disabled','#define CONFIG_NOTE10_RCU_CONTEXT_AUDIT 1\n')):
  src=out/(label+'.c');exe=out/(label+('.exe' if sys.platform=='win32' else ''));src.write_text(define+code,encoding='utf8',newline='\n')
  c=subprocess.run([a.cc,'-std=gnu11','-O2',str(src),'-o',str(exe)],capture_output=True);(out/(label+'-compile.log')).write_bytes(c.stdout+c.stderr)
  if c.returncode:raise RuntimeError(label+' compile failed')
  modes=(0,1,9,10,11,12,13,16,17,18,19,20,22,23,24,25) if label=='enabled' else (0,1,9,10,11,12,13,16,19)
  for mode in modes:
   r=subprocess.run([str(exe.resolve()),str(mode)],capture_output=True);(out/f'{label}-{mode}.log').write_bytes(r.stdout+r.stderr)
   if r.returncode:raise RuntimeError(label+' mode '+str(mode)+' failed')
   cases.append(label+'-'+str(mode));text=r.stdout.decode(errors='strict')
   if mode in (17,18,22,25):continue
   if label=='disabled':
    if 'N10EL' in text:raise ValueError('disabled EHLD emitted frames')
   elif mode in (0,19,23,24):
    pre=decode_pre(text,IDENTITY,2)
    row=decode_ehld(text,IDENTITY,2,pre)['row']
    expected=(0 if mode==23 else 1,0 if mode==23 else 1,1 if mode==24 else 0)
    if (row['index'],row['chain_count'],row['lock_available'],row['running_valid'],row['running'])!=(6,7,*expected):raise ValueError('worker EHLD success fields')
   else:
    lines=[];records=[]
    for line in text.splitlines():
     match=re.fullmatch(r'N10ELQ1 (.*?) checksum=([0-9a-f]{8})',line)
     if not match:continue
     body,digest=match.groups()
     if checksum(body.encode('ascii'))!=int(digest,16):raise ValueError('worker EHLD summary checksum')
     fields=dict(part.split('=',1) for part in body.split(' '))
     if tuple(fields)!=('id','copy','generation','status','row_count','complete'):raise ValueError('worker EHLD failure schema')
     lines.append(line);records.append((fields['copy'],fields['status'],fields['row_count'],fields['complete']))
    if sorted(records)!=[('0','-5','0','0'),('1','-5','0','0')] or 'N10ELM1' in text:raise ValueError('worker EHLD failure summary shape')
    try:decode_ehld('\n'.join(lines)+'\n',IDENTITY,2,{'generation':1,'rows':[{'generation':1,'index':i,'count':7,'kind':6 if i==6 else i,'valid':3,'a':0} for i in range(7)]})
    except ValueError:pass
    else:raise ValueError('strict decoder accepted EHLD error summary')
 proof={'passed':True,'hardware_verified':False,'actual_worker':True,'cases':cases,'source_sha256':{k:hashlib.sha256((root/v).read_bytes()).hexdigest() for k,v in paths.items()},'harness_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'generated_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in out.glob('*.c')},'log_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in out.glob('*.log')}}
 (out/'result.json').write_text(json.dumps(proof,indent=2)+'\n',encoding='utf8',newline='\n')
if __name__=='__main__':main()
