"""Execute final prepared worker and both producers with synthetic state."""
import argparse,hashlib,json,subprocess,sys
from pathlib import Path
from test_fsys_pm_native import function
from test_pm_post_arch_native import WORKER_STUB
from test_pm_callbacks_producer import clean
from test_pm_preconditions_producer import MOCK
from test_pm_branch_producer import BRANCH_MOCK
from decode_pm_preconditions import decode as decode_pre
from decode_pm_branch import decode as decode_branch
HERE=Path(__file__).resolve().parent
ADD=r'''
#include <errno.h>
typedef long long s64;
#define CONFIG_NOTE10_CPU_PM_PRECONDITIONS 1
#define GICD_INT_DEF_PRI_X4 0xa0a0a0a0U
static int num_online_cpus(void){return 8;}
static int irqs_disabled(void){return 0;}
'''
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--source-root',required=True);ap.add_argument('--output',required=True);a=ap.parse_args();root=Path(a.source_root);out=Path(a.output);out.mkdir(parents=True,exist_ok=False);worker=root/'arch/arm64/mm/note10_pm_timer_roundtrip.c';raw=worker.read_text(encoding='utf-8')
 stub=WORKER_STUB.replace('static u32 n10_frame_checksum(const char*p,int n){(void)p;(void)n;return 0;}','static u32 n10_frame_checksum(const char*p,int n){u32 h=2166136261U;while(n--)h=(h^(unsigned char)*p++)*16777619U;return h;}')
 code=stub+ADD+clean('pm_preconditions_contract.h')+clean('pm_branch_contract.h')+MOCK+BRANCH_MOCK.replace('mode==1','mode==10')+clean('pm_preconditions_probe.c')+clean('pm_branch_probe.c')+function(raw,'static void n10_pm_worker(struct work_struct *unused)\n{')+'\nint main(int argc,char**argv){mode=atoi(argv[1]);n10_pm_worker(NULL);return 0;}\n';cc=Path('host-tools/windows-build/llvm-mingw/llvm-mingw-20261006-ucrt-x86_64/bin/clang.exe') if sys.platform=='win32' else 'cc';identity='0123456789abcdef0123456789abcdef'
 for label,define in (('enabled','#define CONFIG_NOTE10_CPU_PM_BRANCH_AUDIT 1\n'),('disabled','')):
  src=out/(label+'.c');exe=out/(label+('.exe' if sys.platform=='win32' else ''));src.write_text(define+code,encoding='utf-8');r=subprocess.run([str(cc),'-std=gnu11',str(src),'-o',str(exe)],capture_output=True,timeout=60);(out/(label+'-compile.log')).write_bytes(r.stdout+r.stderr)
  if r.returncode:raise RuntimeError(r.stderr.decode(errors='replace'))
  for mode in (0,1,9,10):
   r=subprocess.run([str(exe),str(mode)],capture_output=True,timeout=20);(out/f'{label}-{mode}.log').write_bytes(r.stdout+r.stderr)
   if r.returncode:raise RuntimeError('worker failed: '+label+' '+str(mode))
   text=r.stdout.decode()
   if label=='disabled':
    if 'N10BRA' in text:raise ValueError('disabled branch emitted frames')
   elif mode==0:
    prior=decode_pre(text,identity,2);decode_branch(text,identity,2,prior)
   else:
    if 'N10BRAQ1' not in text:raise ValueError('branch failure summary missing')
    try:decode_branch(text,identity,2,{'generation':1,'rows':[],'gic':[]})
    except ValueError:continue
    raise ValueError('failure branch accepted')
 d={'passed':True,'hardware_verified':False,'actual_final_worker_and_producers':True,'cases':['enabled-success','enabled-outer-error','enabled-gic-error','enabled-branch-error','disabled-success','disabled-outer-error','disabled-gic-error','disabled-branch-error'],'source_sha256':hashlib.sha256(worker.read_bytes()).hexdigest(),'harness_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'generated_c_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in out.glob('*.c')},'log_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in out.glob('*.log')}};(out/'result.json').write_text(json.dumps(d,indent=2)+'\n',encoding='utf-8')
if __name__=='__main__':main()
