"""Run v37 and v38 actual producers and cross-decode their output."""
import argparse,hashlib,json,subprocess,sys
from pathlib import Path
from test_pm_callbacks_producer import STUB,clean
from test_pm_preconditions_producer import MOCK
from decode_pm_preconditions import decode as decode_pre
from decode_pm_branch import decode as decode_branch
HERE=Path(__file__).resolve().parent
BRANCH_MOCK=r'''
int n10_branch_read(struct n10_branch_sample *s,unsigned int completed){int i;(void)completed;if(mode==1)return -EIO;s->generation=1;s->seen=s->completed=1;s->count=7;for(i=0;i<7;i++){s->row[i].index=i;s->row[i].kind=i;}s->row[5].num=4;s->row[5].supported=1;s->row[5].used=3;s->row[5].nonnull=1;s->row[5].match=1;s->row[5].start=1;return 0;}
'''
MOCK=MOCK.replace('s->phase[i].restore_matches=i==1;', 's->phase[i].restore_matches=i==1;if(mode==2){int j;for(j=0;j<8;j++)s->phase[i].priority[j]=0xa0a0a0a0U;s->phase[i].priority[0]=0xa000a0a0U;s->phase[i].enable=5;s->phase[i].active=i==2?4:0;}')
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--output',required=True);a=ap.parse_args();o=Path(a.output);o.mkdir(parents=True,exist_ok=False);names=('pm_preconditions_contract.h','pm_preconditions_probe.c','pm_branch_contract.h','pm_branch_probe.c','decode_pm_preconditions.py','decode_pm_branch.py');src=o/'producer.c';src.write_text(STUB+'typedef unsigned int u32;typedef long long s64;\n#define GICD_INT_DEF_PRI_X4 0xa0a0a0a0U\n'+clean('pm_preconditions_contract.h')+clean('pm_branch_contract.h')+MOCK+BRANCH_MOCK+clean('pm_preconditions_probe.c')+clean('pm_branch_probe.c')+'\nint main(int argc,char **argv){mode=atoi(argv[1]);(void)n10_report_pm_preconditions(2,0);(void)n10_report_pm_branch(2,0);return 0;}\n',encoding='utf-8');cc=Path('host-tools/windows-build/llvm-mingw/llvm-mingw-20261006-ucrt-x86_64/bin/clang.exe') if sys.platform=='win32' else 'cc';exe=o/('producer.exe' if sys.platform=='win32' else 'producer');r=subprocess.run([str(cc),'-std=gnu11',str(src),'-o',str(exe)],capture_output=True,timeout=60);(o/'compile.log').write_bytes(r.stdout+r.stderr)
 if r.returncode:raise RuntimeError(r.stderr.decode(errors='replace'))
 logs=[]
 for mode in (0,1,2):
  r=subprocess.run([str(exe),str(mode)],capture_output=True,timeout=20);(o/f'mode-{mode}.log').write_bytes(r.stdout+r.stderr)
  if r.returncode:raise RuntimeError('producer failed')
  logs.append(r.stdout.decode())
 identity='0123456789abcdef0123456789abcdef';prior=decode_pre(logs[0],identity,2);out=decode_branch(logs[0],identity,2,prior);assert len(out['rows'])==7 and out['gic'][0]['lanes']==0xffffffff
 prior2=decode_pre(logs[2],identity,2);out2=decode_branch(logs[2],identity,2,prior2);assert [x['lanes'] for x in out2['gic']]==[4,4,4] and [x['enabled'] for x in out2['gic']]==[4,4,4] and [x['active'] for x in out2['gic']]==[0,0,4]
 for name,text in [('failure',logs[1]),('truncated',logs[0].split('N10BRAR1')[0]),('damaged',logs[0].replace('nonnull=1','nonnull=2',1)),('duplicate',logs[0]+logs[0]),('prefix',logs[0]+'N10BRAX1 broken\n')]:
  try:decode_branch(text,identity,2,prior)
  except ValueError:continue
  raise AssertionError(name+' accepted')
 result={'passed':True,'hardware_verified':False,'cases':['cross-bound-success','lane-intersections','failure','truncated','damaged','duplicate','prefix'],'source_sha256':{n:hashlib.sha256((HERE/n).read_bytes()).hexdigest() for n in names},'harness_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'generated_c_sha256':hashlib.sha256(src.read_bytes()).hexdigest(),'log_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in o.glob('*.log')}};(o/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
if __name__=='__main__':main()
