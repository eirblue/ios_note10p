"""Execute pinned CPU-PM PMU branch bodies with synthetic perf/hardware stubs."""
import argparse,hashlib,json,subprocess,sys
from pathlib import Path
from test_fsys_pm_native import function
HERE=Path(__file__).resolve().parent
STUB=r'''
#include <stdio.h>
#include <stdlib.h>
#include <stddef.h>
#include <string.h>
#define CPU_PM_ENTER 1
#define CPU_PM_EXIT 2
#define CPU_PM_ENTER_FAILED 3
#define NOTIFY_DONE 0
#define NOTIFY_OK 1
#define PERF_EF_UPDATE 1
#define PERF_EF_RELOAD 2
#define RCU_NONIDLE(x) (x)
#define container_of(p,t,m) ((t*)((char*)(p)-offsetof(t,m)))
#define this_cpu_ptr(p) (p)
struct notifier_block {int x;};struct perf_event {int index;};struct pmu_hw_events {unsigned long used_mask[1];struct perf_event *events[32];};
struct arm_pmu {struct notifier_block cpu_pm_nb;struct pmu_hw_events *hw_events;int num_events;unsigned long supported_cpus;void (*reset)(void*);void (*stop)(struct arm_pmu*);void (*start)(struct arm_pmu*);};
static int trace[100],count;
static void record(int v){if(count>=100)abort();trace[count++]=v;}
static int test_bit(int i,unsigned long *p){return !!((*p>>i)&1);}
static int bitmap_weight(unsigned long *p,int n){int i,c=0;for(i=0;i<n;i++)c+=test_bit(i,p);return c;}
static int smp_processor_id(void){return 0;}
static int cpumask_test_cpu(int i,unsigned long *p){return !!((*p>>i)&1);}
static void armpmu_stop(struct perf_event *e,int f){if(!e || f!=PERF_EF_UPDATE)abort();record(100+e->index);}
static void armpmu_start(struct perf_event *e,int f){if(!e || f!=PERF_EF_RELOAD)abort();record(200+e->index);}
static void reset(void*p){(void)p;record(1);}static void stop(struct arm_pmu*p){(void)p;record(2);}static void start(struct arm_pmu*p){(void)p;record(3);}
'''
MAIN=r'''
static void check(const int *expected,int n){int i;if(count!=n)abort();for(i=0;i<n;i++)if(trace[i]!=expected[i])abort();}
int main(int argc,char**argv){int mode=atoi(argv[1]),result;struct perf_event ev[2]={{0},{2}};struct pmu_hw_events hw={{5},{0}};struct arm_pmu p={{0},&hw,3,1,reset,stop,start};hw.events[0]=&ev[0];hw.events[2]=&ev[1];
 if(mode==3||mode==4)hw.used_mask[0]=0;if(mode==5)p.supported_cpus=0;if(mode==6)p.reset=0;
 result=cpu_pm_pmu_notify(&p.cpu_pm_nb,mode==0?CPU_PM_ENTER:mode==1||mode==4||mode==6?CPU_PM_EXIT:mode==2||mode==3?CPU_PM_ENTER_FAILED:mode==5?CPU_PM_ENTER:99,0);
 if(mode==0){int x[]={2,100,102};check(x,3);if(result!=NOTIFY_OK)abort();}
 if(mode==1){int x[]={1,200,202,3};check(x,4);if(result!=NOTIFY_OK)abort();}
 if(mode==2){int x[]={3};check(x,1);if(result!=NOTIFY_OK)abort();}
 if(mode==3){check(0,0);if(result!=NOTIFY_OK)abort();}
 if(mode==4){int x[]={1};check(x,1);if(result!=NOTIFY_OK)abort();}
 if(mode==5){check(0,0);if(result!=NOTIFY_DONE)abort();}
 if(mode==6){int x[]={200,202,3};check(x,3);if(result!=NOTIFY_OK)abort();}
 if(mode==7){check(0,0);if(result!=NOTIFY_DONE)abort();}
 return 0;}
'''
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--source',required=True);ap.add_argument('--output',required=True);a=ap.parse_args();p=Path(a.source);out=Path(a.output);out.mkdir(parents=True,exist_ok=False);raw=p.read_text(encoding='utf-8');source=out/'pmu-branch.c';source.write_text(STUB+function(raw,'static void cpu_pm_pmu_setup(')+function(raw,'static int cpu_pm_pmu_notify(')+MAIN,encoding='utf-8');cc=Path('host-tools/windows-build/llvm-mingw/llvm-mingw-20261006-ucrt-x86_64/bin/clang.exe') if sys.platform=='win32' else 'cc';exe=out/('pmu-branch.exe' if sys.platform=='win32' else 'pmu-branch');r=subprocess.run([str(cc),'-std=gnu11',str(source),'-o',str(exe)],capture_output=True,timeout=60);(out/'compile.log').write_bytes(r.stdout+r.stderr)
 if r.returncode:raise RuntimeError(r.stderr.decode(errors='replace'))
 cases=('enter','exit','enter-failed','empty-failed','empty-exit-reset','unsupported','exit-no-reset','unknown-command')
 for i,n in enumerate(cases):
  r=subprocess.run([str(exe),str(i)],capture_output=True,timeout=20);(out/('case-'+str(i)+'.log')).write_bytes(r.stdout+r.stderr)
  if r.returncode:raise RuntimeError(n+' failed')
 d={'passed':True,'hardware_verified':False,'actual_pinned_branch_bodies':True,'callbacks_invoked_on_hardware':False,'cases':list(cases),'source_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'harness_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'generated_c_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'log_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in out.glob('*.log')}};(out/'result.json').write_text(json.dumps(d,indent=2)+'\n',encoding='utf-8')
if __name__=='__main__':main()
