"""Exercise actual capture lifecycle and gates using synthetic PM state."""
import argparse, hashlib, json, subprocess, sys
from pathlib import Path
from test_pm_callbacks_producer import clean
HERE=Path(__file__).resolve().parent
STUB=r'''
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>
typedef unsigned int u32; typedef long long s64;
struct n10_pm_noirq_sample {unsigned int seen,bad,finished,state,generation,late,late_ok,noirq,noirq_ok,point;};
struct active {unsigned int qgeneration,qphase,pm_called;} active, *n10_pm_active=&active;
static struct n10_pm_noirq_sample n10_pm_noirq_last;
static int owner=1,irq,pc,cpu,online=1,count=1,ready=1,ops,pm_test_level=1,pm_mutex,mode;
#define PM_SUSPEND_MEM 1
#define TEST_PLATFORM 1
#define N10_Q_PM_ENTERED 1
#define current 1
#define n10_pm_owner owner
#define raw_smp_processor_id() cpu
#define num_online_cpus() count
#define cpu_online_mask (&online)
#define cpumask_bits(p) (p)
#define irqs_disabled() irq
#define preempt_count() pc
#define preemptible() (!irq && !pc)
#define mutex_lock(p) ((void)0)
#define mutex_unlock(p) ((void)0)
static int n10_pm_noirq_owned(void){return ready && n10_pm_active && owner==current && active.pm_called==1 && active.qphase==1 && active.qgeneration;}
static int n10_pm_noirq_ops_mask(void){return ops;}
'''
MOCK=r'''
int n10_pre_chain(struct n10_precond_sample *s,unsigned int generation){irq=1;pc=1;if(mode==1) owner=0; if(!n10_pre_context(generation,1,1))s->error=-EIO; irq=0;pc=0;if(mode==2) n10_pm_noirq_last.noirq_ok=0;return s->error;}
int n10_pre_gic_regs(unsigned int phase,struct n10_precond_gic_row *r,u32 c,u32 p){(void)phase;(void)c;(void)p;r->seen=1;return 0;}
'''
MAIN=r'''
#define CHECK(x) do{if(!(x)){fprintf(stderr,"line %d\n",__LINE__);return 1;}}while(0)
int main(int argc,char **argv){struct n10_precond_sample out;int r;mode=atoi(argv[1]);active.qgeneration=1;active.qphase=1;active.pm_called=1;n10_pm_noirq_last=(struct n10_pm_noirq_sample){1,0,0,1,1,1,1,1,1,1};
 if(mode==3)n10_pm_noirq_last.point=0;
 if(mode==4)n10_pm_active=0;if(mode==5)active.pm_called=0;if(mode==6)active.qphase=0;if(mode==7)active.qgeneration=0;
 if(mode==8)cpu=1;if(mode==9)online=3;if(mode==10)count=2;if(mode==11)irq=1;if(mode==12)pc=1;
 if(mode==13)n10_pm_noirq_last.late_ok=0;if(mode==14)n10_pm_noirq_last.noirq_ok=0;if(mode==15)ops=1;if(mode==16)pm_test_level=0;
 r=n10_pre_capture(1);
 if(mode==0){CHECK(!r);CHECK(!n10_pre_read(&out,2));CHECK(n10_pre_capture(1));CHECK(n10_pre_read(&out,2));}
 else {CHECK(r);CHECK(n10_pre_read(&out,2));}
 owner=ready=1;mode=0;n10_pm_active=&active;active.pm_called=1;active.qphase=1;cpu=irq=pc=ops=0;online=count=1;pm_test_level=1;active.qgeneration=2;n10_pm_noirq_last=(struct n10_pm_noirq_sample){1,0,0,1,2,1,1,1,1,1};CHECK(!n10_pre_capture(2));CHECK(!n10_pre_read(&out,3));
 CHECK(!n10_pre_gic_step(2,0,0,0) == 0); /* preempt must be disabled */
 pc=1;CHECK(!n10_pre_gic_step(2,0,0,0));irq=1;CHECK(!n10_pre_gic_step(2,1,0,0));irq=0;CHECK(!n10_pre_gic_step(2,2,0,0));pc=0;{struct n10_precond_gic_sample g;CHECK(!n10_pre_gic_read(&g,3));}return 0;}
'''
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--output',required=True);o=Path(ap.parse_args().output);o.mkdir(parents=True,exist_ok=False)
 src=o/'lifecycle.c';src.write_text(STUB+clean('pm_preconditions_contract.h')+MOCK+clean('pm_preconditions_capture.c')+MAIN,encoding='utf-8')
 cc=Path('host-tools/windows-build/llvm-mingw/llvm-mingw-20261006-ucrt-x86_64/bin/clang.exe') if sys.platform=='win32' else 'cc';exe=o/('lifecycle.exe' if sys.platform=='win32' else 'lifecycle')
 r=subprocess.run([str(cc),'-std=gnu11',str(src),'-o',str(exe)],capture_output=True,timeout=60);(o/'compile.log').write_bytes(r.stdout+r.stderr)
 if r.returncode:raise RuntimeError(r.stderr.decode(errors='replace'))
 for mode in range(17):
  r=subprocess.run([str(exe),str(mode)],capture_output=True,timeout=20);(o/f'mode-{mode}.log').write_bytes(r.stdout+r.stderr)
  if r.returncode:raise RuntimeError('lifecycle case %d: %s'%(mode,r.stderr.decode(errors='replace')))
 names=('pm_preconditions_contract.h','pm_preconditions_capture.c')
 (o/'result.json').write_text(json.dumps({'passed':True,'hardware_verified':False,'cases':['duplicate','under-lock-owner','post-unlock-noirq','point','null-active','pm-called','qphase','generation','cpu','mask','count','irq','preempt','late-ready','noirq-ready','ops','test-level'],'source_sha256':{n:hashlib.sha256((HERE/n).read_bytes()).hexdigest() for n in names},'harness_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'generated_c_sha256':hashlib.sha256(src.read_bytes()).hexdigest(),'log_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in o.glob('*.log')}},indent=2)+'\n',encoding='utf-8')
if __name__=='__main__':main()
