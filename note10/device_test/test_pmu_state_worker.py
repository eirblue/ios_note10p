"""Execute final v41 worker and all three producers with synthetic state."""
import argparse,hashlib,json,subprocess,sys
from pathlib import Path
from test_fsys_pm_native import function
from test_pm_post_arch_native import WORKER_STUB
from test_pm_callbacks_producer import clean
from test_pm_preconditions_producer import MOCK
from test_pm_branch_producer import BRANCH_MOCK
from decode_pm_preconditions import decode as decode_pre
from decode_pm_branch import decode as decode_branch
from decode_pmu_state import decode as decode_state
HERE=Path(__file__).resolve().parent
ADD=r'''
#include <errno.h>
typedef long long s64;
#define CONFIG_NOTE10_CPU_PM_PRECONDITIONS 1
#define CONFIG_NOTE10_CPU_PM_BRANCH_AUDIT 1
#define GICD_INT_DEF_PRI_X4 0xa0a0a0a0U
static int num_online_cpus(void){return 8;}
static int irqs_disabled(void){return 0;}
'''
STATE_MOCK=r"""
int n10_state_read(struct n10_state_sample *s,unsigned int completed){int i;(void)completed;if(mode==11)return -EIO;s->generation=1;s->seen=s->completed=1;s->count=7;for(i=0;i<7;i++){s->row[i].index=i;s->row[i].kind=i;}s->row[5].num=4;s->row[5].supported=1;s->row[5].used=s->row[5].present=s->row[5].owned=s->row[5].observed=3;s->row[5].running=1;s->row[5].stopped=2;s->row[5].unbound=3;s->row[5].oncpu0=1;s->row[5].active=1;return 0;}
"""
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--source-root',required=True);ap.add_argument('--output',required=True);a=ap.parse_args();root=Path(a.source_root);out=Path(a.output);out.mkdir(parents=True,exist_ok=False);worker=root/'arch/arm64/mm/note10_pm_timer_roundtrip.c';raw=worker.read_text(encoding='utf-8')
 stub=WORKER_STUB.replace('static u32 n10_frame_checksum(const char*p,int n){(void)p;(void)n;return 0;}','static u32 n10_frame_checksum(const char*p,int n){u32 h=2166136261U;while(n--)h=(h^(unsigned char)*p++)*16777619U;return h;}')
 code=stub+ADD+clean('pm_preconditions_contract.h')+clean('pm_branch_contract.h')+clean('pmu_state_contract.h')+MOCK.replace('value[4]=1','value[4]=2')+BRANCH_MOCK.replace('mode==1','mode==10').replace('nonnull=1','nonnull=3')+STATE_MOCK+clean('pm_preconditions_probe.c')+clean('pm_branch_probe.c')+clean('pmu_state_probe.c')+function(raw,'static void n10_pm_worker(struct work_struct *unused)\n{')+'\nint main(int argc,char**argv){mode=atoi(argv[1]);n10_pm_worker(NULL);return 0;}\n';cc=Path('host-tools/windows-build/llvm-mingw/llvm-mingw-20261006-ucrt-x86_64/bin/clang.exe') if sys.platform=='win32' else 'cc';identity='0123456789abcdef0123456789abcdef'
 for label,define in (('enabled','#define CONFIG_NOTE10_PMU_STATE_AUDIT 1\n'),('disabled','')):
  src=out/(label+'.c');exe=out/(label+('.exe' if sys.platform=='win32' else ''));src.write_text(define+code,encoding='utf-8',newline='\n');r=subprocess.run([str(cc),'-std=gnu11',str(src),'-o',str(exe)],capture_output=True,timeout=60);(out/(label+'-compile.log')).write_bytes(r.stdout+r.stderr)
  if r.returncode:raise RuntimeError(r.stderr.decode(errors='replace'))
  for mode in (0,1,9,10,11):
   r=subprocess.run([str(exe),str(mode)],capture_output=True,timeout=20);(out/f'{label}-{mode}.log').write_bytes(r.stdout+r.stderr)
   if r.returncode:raise RuntimeError('worker failed: '+label+' '+str(mode))
   text=r.stdout.decode()
   if label=='disabled':
    if 'N10STA' in text:raise ValueError('disabled state emitted frames')
   elif mode==0:
    prior=decode_pre(text,identity,2);branch=decode_branch(text,identity,2,prior);state=decode_state(text,identity,2,prior,branch);assert state['rows'][5]['stopped']==2
   else:
    if 'N10STAQ1' not in text:raise ValueError('state failure summary missing')
    try:decode_state(text,identity,2,{'generation':1,'rows':[]},{'generation':1,'rows':[]})
    except ValueError:continue
    raise ValueError('failure branch accepted')
 d={'passed':True,'hardware_verified':False,'actual_final_worker_and_producers':True,'state_feature':True,'cases':['enabled-success','enabled-outer-error','enabled-gic-error','enabled-branch-error','enabled-state-error','disabled-success','disabled-outer-error','disabled-gic-error','disabled-branch-error','disabled-state-error'],'source_sha256':hashlib.sha256(worker.read_bytes()).hexdigest(),'harness_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'generated_c_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in out.glob('*.c')},'log_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in out.glob('*.log')}};(out/'result.json').write_text(json.dumps(d,indent=2)+'\n',encoding='utf-8')
if __name__=='__main__':main()
