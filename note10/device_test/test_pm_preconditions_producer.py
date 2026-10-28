"""Exercise actual precondition producer and strict decoder."""
import argparse,hashlib,json,subprocess,sys
from pathlib import Path
from test_pm_callbacks_producer import STUB,clean
from decode_pm_preconditions import decode
from decode_reservation import checksum
HERE=Path(__file__).resolve().parent
MOCK=r"""
int n10_pre_read(struct n10_precond_sample *s,unsigned int completed){int i;(void)completed;s->generation=1;s->seen=s->completed=1;s->count=7;for(i=0;i<7;i++){s->row[i].kind=i;s->row[i].priority=7-i;}s->row[3].valid=15;s->row[3].value[0]=1;s->row[3].value[2]=2;s->row[4].valid=7;s->row[4].value[1]=1;s->row[4].value[2]=1;s->row[5].valid=31;s->row[5].value[0]=1;s->row[5].value[1]=4;s->row[5].value[2]=3;s->row[5].value[3]=2;s->row[5].value[4]=1;s->row[6].valid=3;s->row[6].value[1]=1;return mode==1?-EIO:0;}
int n10_pre_gic_read(struct n10_precond_gic_sample *s,unsigned int completed){int i;(void)completed;s->generation=1;s->seen=s->completed=1;for(i=0;i<3;i++){s->phase[i].seen=1;s->phase[i].active=i;s->phase[i].restore_matches=i==1;}return 0;}
""".replace('\"','"')
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--output',required=True);o=Path(ap.parse_args().output);o.mkdir(parents=True,exist_ok=True);src=o/'producer.c';src.write_text(STUB+'typedef unsigned int u32;typedef long long s64;\n'+clean('pm_preconditions_contract.h')+MOCK+clean('pm_preconditions_probe.c')+'\nint main(int argc,char**argv){mode=atoi(argv[1]);(void)n10_report_pm_preconditions(2,0);return 0;}\n',encoding='utf-8');cc=Path('host-tools/windows-build/llvm-mingw/llvm-mingw-20261006-ucrt-x86_64/bin/clang.exe') if sys.platform=='win32' else 'cc';exe=o/('producer.exe' if sys.platform=='win32' else 'producer');r=subprocess.run([str(cc),'-std=gnu11','-O2',str(src),'-o',str(exe)],capture_output=True,timeout=60);(o/'compile.log').write_bytes(r.stdout+r.stderr)
 if r.returncode:raise RuntimeError(r.stderr.decode(errors='replace'))
 logs=[]
 for mode in (0,1):
  r=subprocess.run([str(exe),str(mode)],capture_output=True,timeout=20);assert not r.returncode;(o/f'mode-{mode}.log').write_bytes(r.stdout);logs.append(r.stdout.decode())
 result=decode(logs[0],'0123456789abcdef0123456789abcdef',2);assert len(result['rows'])==7 and [x['active'] for x in result['gic']]==[0,1,2] and result['gic'][1]['matches']==1
 def rewrite_both(text,tag,old,new):
  lines=[]
  for line in text.splitlines():
   if line.startswith(tag+' ') and old in line:
    body=line.rsplit(' checksum=',1)[0].replace(old,new,1)
    line=body+' checksum=%08x'%checksum(body.split(' ',1)[1].encode('ascii'))
   lines.append(line)
  return '\n'.join(lines)+'\n'
 for name,text in [('failed',logs[1]),('truncated',logs[0].splitlines()[0]+'\n'),('damaged',logs[0].replace('kind=1','kind=2',1)),('stale',logs[0].replace('generation=1','generation=3',1)),('duplicate',logs[0]+logs[0])]:
  try:decode(text,'0123456789abcdef0123456789abcdef',2)
  except ValueError:continue
  raise AssertionError(name+' accepted')
 for name,text in [('negative-zero',rewrite_both(logs[0],'N10PRR1',' a=0',' a=-0')),('wide-status',rewrite_both(logs[0],'N10PRQ1',' status=0',' status=2147483648')),('prefix-typo',logs[0]+'N10PRX1 broken\n')]:
  try:decode(text,'0123456789abcdef0123456789abcdef',2)
  except ValueError:continue
  raise AssertionError(name+' accepted')
 names=('pm_preconditions_contract.h','pm_preconditions_probe.c','decode_pm_preconditions.py');d={'passed':True,'hardware_verified':False,'source_sha256':{n:hashlib.sha256((HERE/n).read_bytes()).hexdigest() for n in names},'generated_c_sha256':hashlib.sha256(src.read_bytes()).hexdigest(),'harness_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'log_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in o.glob('*.log')},'cases':['success','failed','truncated','damaged','stale','duplicate','negative-zero','wide-status','prefix-typo']};(o/'result.json').write_text(json.dumps(d,indent=2)+'\n',encoding='utf-8')
if __name__=='__main__':main()
