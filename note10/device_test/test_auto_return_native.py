"""Actual auto-return C with modeled kernel APIs; never contacts a device."""
import argparse,hashlib,json,re,shutil,subprocess,sys
from pathlib import Path
from run_probe import ROOT
from decode_auto_return import decode
HERE=Path(__file__).resolve().parent
ID='0123456789abcdef0123456789abcdef'
CYCLE='1234567890abcdef1234567890abcdef'
STUB=r'''#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>
#include <setjmp.h>
#include <stdint.h>
typedef uint32_t u32;
#define __init
#define __setup(a,b)
#define N10_RESERVE_BUILD_ID "0123456789abcdef0123456789abcdef"
#define pr_info printf
#define scnprintf snprintf
#define SYSTEM_RUNNING 3
#define WQ_UNBOUND 1
#define WQ_MEM_RECLAIM 2
static int mode,system_state=3,reboots,queued,allocated;
static unsigned long first_delay;
static jmp_buf reset;
typedef int atomic_t;
#define ATOMIC_INIT(v) (v)
static int atomic_read(atomic_t *p){return *p;}
static int atomic_cmpxchg(atomic_t *p,int a,int b){int old=*p;if(old==a)*p=b;return old;}
struct work_struct {int unused;};
struct delayed_work {int unused;};
struct workqueue_struct {int unused;};
static struct workqueue_struct queue;
#define DECLARE_DELAYED_WORK(name,fn) struct delayed_work name={0}
#define msecs_to_jiffies(n) (n)
static struct workqueue_struct *alloc_workqueue(const char *name,int flags,int n){
 if(strcmp(name,"n10_recovery")||flags!=3||n!=1)exit(60);
 ++allocated;return mode==3?NULL:&queue;
}
static int queue_delayed_work(struct workqueue_struct *q,struct delayed_work *w,unsigned long delay){
 (void)w;if(q!=&queue)exit(61);if(!queued)first_delay=delay;++queued;return mode==4?0:1;
}
static void kernel_restart(char *cmd){if(strcmp(cmd,"recovery"))exit(62);++reboots;if(mode!=8)longjmp(reset,1);}
'''
MAIN=r'''
int main(int argc,char **argv){
 if(argc!=2)return 70;
 mode=atoi(argv[1]);
 if(mode!=1){const char *token=mode==2?"AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA":"1234567890abcdef1234567890abcdef";for(int i=0;i<32;++i)n10_cycle[i]=token[i];}
 int armed=n10_arm_auto_return();
 if(mode>=1&&mode<=4){if(!armed||reboots)return 72;printf("MODEL reboots=%d queued=%d allocated=%d\n",reboots,queued,allocated);return 0;}
 if(armed||first_delay!=90000)return 73;
 if(mode==7&&(n10_arm_auto_return()!=-EBUSY||allocated!=1))return 74;
 if(mode==5||mode==6)system_state=0;
 if(!setjmp(reset)){
  if(mode==5){for(int i=0;i<30;++i)n10_return_worker(NULL);}
  else if(mode==6){n10_return_worker(NULL);system_state=3;n10_return_worker(NULL);}
  else n10_return_worker(NULL);
 }
 if(mode==9)n10_return_worker(NULL);
 if(reboots!=(mode==5?0:1))return 75;
 if(mode==5&&queued!=30)return 76;
 printf("MODEL reboots=%d queued=%d allocated=%d\n",reboots,queued,allocated);
 return 0;
}
'''

def test(output):
    output=Path(output).resolve()
    if not output.is_relative_to((ROOT/'note10/private').resolve()) or output.exists():raise ValueError('Fresh private model output required')
    output.mkdir(parents=True)
    actual=(HERE/'auto_return.c').read_bytes()
    checksum=re.search(r'static u32 n10_frame_checksum[^}]+}',(HERE/'xnu_reserve.c').read_text()).group()
    source=output/'model.c';source.write_text(STUB+checksum+'\n'+re.sub(r'^#include[^\n]*\n','',actual.decode(),flags=re.M)+MAIN)
    compiler=ROOT/'host-tools/windows-build/llvm-mingw/llvm-mingw-20261006-ucrt-x86_64/bin/clang.exe' if sys.platform=='win32' else shutil.which('cc')
    exe=output/('model.exe' if sys.platform=='win32' else 'model')
    built=subprocess.run([str(compiler),'-std=c11','-O2','-Wall','-Wextra','-Werror',str(source),'-o',str(exe)],capture_output=True,timeout=60)
    (output/'compile.log').write_bytes(built.stdout+built.stderr)
    if built.returncode:raise RuntimeError('Auto-return C model compilation failed')
    outcomes=[]
    for mode in range(10):
        result=subprocess.run([str(exe),str(mode)],capture_output=True,timeout=15)
        (output/f'mode-{mode}.txt').write_bytes(result.stdout+result.stderr)
        if result.returncode:raise ValueError('Auto-return C model failed mode '+str(mode))
        try:decode(result.stdout,ID,CYCLE);accepted=True
        except ValueError:accepted=False
        if accepted!=(mode in {0,6,7,9}):raise ValueError('Auto-return frame disposition differs')
        outcomes.append(dict(mode=mode,accepted=accepted))
    report=dict(passed=True,cases=10,source_sha256=hashlib.sha256(actual).hexdigest(),outcomes=outcomes,
        device_operations=[],hardware_verified=False,scope='Actual C; modeled atomic/workqueue/restart APIs')
    (output/'result.json').write_text(json.dumps(report,indent=2))
    return report

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);r=test(p.parse_args().output);print(json.dumps(dict(passed=r['passed'],cases=r['cases'])))
