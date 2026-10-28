"""Stateful native model of exact final PMU bodies; no hardware calls."""
import argparse, hashlib, json, subprocess, sys
from pathlib import Path
from test_fsys_pm_native import function
STUB = r"""
#include <stdio.h>
#include <stdlib.h>
#include <stdbool.h>
#include <stddef.h>
#include <string.h>
#define CPU_PM_ENTER 1
#define CPU_PM_EXIT 2
#define CPU_PM_ENTER_FAILED 3
#define PERF_HES_STOPPED 1
#define PERF_HES_UPTODATE 2
#define PERF_EF_RELOAD 2
#define PERF_EF_UPDATE 1
#define NOTIFY_OK 1
#define NOTIFY_DONE 0
#define NOTIFY_STOP_MASK 0x8000
#define CONFIG_NOTE10_CPU_PM_FAILURE_GUARD 1
#define rcu_dereference_raw(x) (x)
#define dbg_snapshot_print_notifier_call(...) ((void)0)
#define DSS_FLAG_IN 0
#define DSS_FLAG_OUT 1
#define ARMPMU_MAX_HWEVENTS 32
#define container_of(p,t,m) ((t*)((char*)(p)-offsetof(t,m)))
#define this_cpu_ptr(p) (p)
#define RCU_NONIDLE(x) do { rcu_calls++; x; } while (0)
#define WARN_ON_ONCE(x) ((void)(x))
#define pr_warn_once(...) ((void)0)
struct notifier_block { int (*notifier_call)(struct notifier_block *,unsigned long,void *); struct notifier_block *next; };
struct hw_perf_event { int state; };
struct perf_event { struct arm_pmu *pmu; struct hw_perf_event hw; int idx, enabled; };
struct pmu_hw_events { unsigned long used_mask[1]; struct perf_event *events[32]; bool n10_failure_valid,n10_failure_pending; struct perf_event *n10_failure_events[32]; };
struct arm_pmu { struct notifier_block cpu_pm_nb; struct pmu_hw_events *hw_events; int num_events; unsigned long supported_cpus; void (*reset)(void*); void (*stop)(struct arm_pmu*); void (*start)(struct arm_pmu*); void (*enable)(struct perf_event*); void (*disable)(struct perf_event*); };
static int trace[256], nt, irqoff=1, rcu_calls, current_cpu;
static void logop(int n) { if (nt>=256) abort(); trace[nt++]=n; }
static int irqs_disabled(void) {return irqoff;}
static int test_bit(int i,unsigned long *p){return !!((*p>>i)&1);}
static int bitmap_weight(unsigned long *p,int n){int i,c=0;for(i=0;i<n;i++)c+=test_bit(i,p);return c;}
static int smp_processor_id(void){return current_cpu;}
static int cpumask_test_cpu(int i,unsigned long *p){return !!((*p>>i)&1);}
static struct arm_pmu *to_arm_pmu(struct arm_pmu *p){return p;}
static void armpmu_event_update(struct perf_event *e){logop(100+e->idx);}
static void armpmu_event_set_period(struct perf_event *e){logop(200+e->idx);}
static void en(struct perf_event *e){e->enabled=1;logop(300+e->idx);}
static void dis(struct perf_event *e){e->enabled=0;logop(400+e->idx);}
static void reset(void *p){(void)p;logop(1);}
static void stop(struct arm_pmu*p){(void)p;logop(2);}
static void start(struct arm_pmu*p){(void)p;logop(3);}
"""
CHAIN = r"""
static struct notifier_block *chain_head;
static int cpu_pm_notify(int event,int nr_to_call,int *nr_calls) {
 int result=notifier_call_chain(&chain_head,event,NULL,nr_to_call,nr_calls);
 return result & NOTIFY_STOP_MASK ? -1 : 0;
}
"""
CHAIN_MAIN = r"""
static int failed_enter,failed_failed,later_enter,later_failed;
static int fail_cb(struct notifier_block *nb,unsigned long cmd,void *p){(void)nb;(void)p;if(cmd==CPU_PM_ENTER){failed_enter++;return NOTIFY_STOP_MASK;}failed_failed++;return NOTIFY_OK;}
static int later_cb(struct notifier_block *nb,unsigned long cmd,void *p){(void)nb;(void)p;if(cmd==CPU_PM_ENTER)later_enter++;else later_failed++;return NOTIFY_OK;}
"""
MAIN = r"""
#define ASSERT(x) do { if (!(x)) {fprintf(stderr,"assertion line %d\n",__LINE__); return 1;} } while(0)
int main(int argc,char **argv) {
 int mode=atoi(argv[1]), i, result; struct pmu_hw_events hw={0};
 struct arm_pmu p={{0},&hw,32,1,reset,stop,start,en,dis};
 struct perf_event a={&p,{0},0,1}, b={&p,{PERF_HES_STOPPED},31,0};
 hw.used_mask[0]=(1UL<<0)|(1UL<<31);hw.events[0]=&a;hw.events[31]=&b;
 if(mode==12){struct pmu_hw_events h2={0};struct perf_event c={&p,{0},1,1};p.supported_cpus=3;cpu_pm_pmu_notify(&p.cpu_pm_nb,CPU_PM_ENTER,0);current_cpu=1;p.hw_events=&h2;h2.used_mask[0]=2;h2.events[1]=&c;cpu_pm_pmu_notify(&p.cpu_pm_nb,CPU_PM_ENTER,0);cpu_pm_pmu_notify(&p.cpu_pm_nb,CPU_PM_ENTER_FAILED,0);
#ifdef CONFIG_NOTE10_PMU_FAILURE_RESTORE
 ASSERT(c.enabled && !a.enabled);current_cpu=0;p.hw_events=&hw;cpu_pm_pmu_notify(&p.cpu_pm_nb,CPU_PM_ENTER_FAILED,0);ASSERT(a.enabled && !b.enabled);
#else
 ASSERT(!c.enabled && !a.enabled);
#endif
 return 0;}
 if(mode==14){struct perf_event ev[32];hw.used_mask[0]=0xffffffffUL;for(i=0;i<32;i++){ev[i]=(struct perf_event){&p,{0},i,1};hw.events[i]=&ev[i];}cpu_pm_pmu_notify(&p.cpu_pm_nb,CPU_PM_ENTER,0);cpu_pm_pmu_notify(&p.cpu_pm_nb,CPU_PM_ENTER_FAILED,0);for(i=0;i<32;i++){
#ifdef CONFIG_NOTE10_PMU_FAILURE_RESTORE
 ASSERT(ev[i].enabled);
#else
 ASSERT(!ev[i].enabled);
#endif
 }return 0;}
 if(mode==11){struct notifier_block bad={fail_cb,0},late={later_cb,0};p.cpu_pm_nb.notifier_call=cpu_pm_pmu_notify;p.cpu_pm_nb.next=&bad;bad.next=&late;chain_head=&p.cpu_pm_nb;ASSERT(cpu_pm_enter()!=0);ASSERT(failed_enter==1 && !failed_failed && !later_enter && !later_failed);ASSERT(trace[nt-1]==3);
#ifdef CONFIG_NOTE10_PMU_FAILURE_RESTORE
 ASSERT(a.enabled && !b.enabled);
#else
 ASSERT(!a.enabled && !b.enabled);
#endif
 return 0;}
 if(mode==3)hw.used_mask[0]=0;
 if(mode==4)p.supported_cpus=0;
 result=cpu_pm_pmu_notify(&p.cpu_pm_nb,CPU_PM_ENTER,0);
 ASSERT(result==(mode==4?NOTIFY_DONE:NOTIFY_OK));
 if(mode==4) return 0;
 if(mode==3){ASSERT(cpu_pm_pmu_notify(&p.cpu_pm_nb,CPU_PM_ENTER_FAILED,0)==NOTIFY_OK);return 0;}
 ASSERT((a.hw.state & PERF_HES_STOPPED) && !a.enabled);ASSERT(!b.enabled);
 if(mode==2){cpu_pm_pmu_notify(&p.cpu_pm_nb,CPU_PM_EXIT,0); ASSERT(a.enabled && b.enabled); ASSERT(trace[nt-1]==3);return 0;}
 if(mode==5)hw.events[0]=&b;
 if(mode==6)hw.used_mask[0]&=~1UL;
 if(mode==7)irqoff=0;
 if(mode==13)a.hw.state=0;
 if(mode==8)cpu_pm_pmu_notify(&p.cpu_pm_nb,CPU_PM_ENTER,0);
 result=cpu_pm_pmu_notify(&p.cpu_pm_nb,CPU_PM_ENTER_FAILED,0); ASSERT(result==NOTIFY_OK); ASSERT(trace[nt-1]==3);
#ifdef CONFIG_NOTE10_PMU_FAILURE_RESTORE
 if(mode==0 || mode==1 || mode==9 || mode==10){ASSERT(a.enabled && !b.enabled);ASSERT(rcu_calls==1);ASSERT(b.hw.state==PERF_HES_STOPPED);ASSERT(a.hw.state==0);ASSERT(nt>=3 && trace[nt-3]==200 && trace[nt-2]==300);}
 else ASSERT(!a.enabled && !b.enabled);
 ASSERT(!hw.n10_failure_valid && !hw.n10_failure_pending);
 for(i=0;i<32;i++) ASSERT(!hw.n10_failure_events[i]);
#else
 ASSERT(!a.enabled && !b.enabled);ASSERT(rcu_calls==0);
#endif
 if(mode==9){nt=0;cpu_pm_pmu_notify(&p.cpu_pm_nb,CPU_PM_ENTER,0);cpu_pm_pmu_notify(&p.cpu_pm_nb,CPU_PM_ENTER_FAILED,0);ASSERT(a.enabled && !b.enabled && b.hw.state==PERF_HES_STOPPED);}
 if(mode==10){struct pmu_hw_events h2={0};struct arm_pmu q={{0},&h2,1,1,reset,stop,start,en,dis};struct perf_event c={&q,{0},0,1};h2.used_mask[0]=1;h2.events[0]=&c;cpu_pm_pmu_notify(&q.cpu_pm_nb,CPU_PM_ENTER,0);ASSERT(!c.enabled && a.enabled);cpu_pm_pmu_notify(&q.cpu_pm_nb,CPU_PM_ENTER_FAILED,0);ASSERT(c.enabled && a.enabled);}
 if(mode==1){int old=a.enabled;nt=0;cpu_pm_pmu_notify(&p.cpu_pm_nb,CPU_PM_ENTER_FAILED,0);ASSERT(a.enabled==old);ASSERT(nt==1 && trace[0]==3);}
 return 0;
}
"""
CASES=("mixed-failed","unmatched-failed","successful-exit","empty","unsupported","pointer-mismatch","used-bit-mismatch","irq-on","duplicate-enter","next-generation","multiple-pmu","notifier-chain-failure","cpu-isolation","state-mismatch","all-slots")
def generate(raw,helper,cpu,notifier):
 return STUB+''.join(function(raw,s) for s in ('static void\narmpmu_stop(', 'static void armpmu_start(', 'static void cpu_pm_pmu_setup('))+'\n#ifdef CONFIG_NOTE10_PMU_FAILURE_RESTORE\n'+helper+'\n#endif\n'+function(raw,'static int cpu_pm_pmu_notify(')+function(notifier,'static int notifier_call_chain(')+CHAIN+function(cpu,'int cpu_pm_enter(')+CHAIN_MAIN+MAIN
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--source',required=True);ap.add_argument('--helper',required=True);ap.add_argument('--cpu-source',required=True);ap.add_argument('--notifier-source',required=True);ap.add_argument('--output',required=True);a=ap.parse_args();out=Path(a.output);out.mkdir(parents=True,exist_ok=False);p=Path(a.source);raw=p.read_text(encoding='utf8');helper=Path(a.helper).read_text(encoding='utf8')
 cpu=Path(a.cpu_source).read_text(encoding='utf8');notifier=Path(a.notifier_source).read_text(encoding='utf8');body=generate(raw,helper,cpu,notifier)
 cc=Path('host-tools/windows-build/llvm-mingw/llvm-mingw-20261006-ucrt-x86_64/bin/clang.exe') if sys.platform=='win32' else 'cc'
 for mode in ('off','on'):
  src=out/(mode+'.c');src.write_text(body,encoding='utf8');exe=out/(mode+('.exe' if sys.platform=='win32' else ''));args=[str(cc),'-std=gnu11',str(src),'-o',str(exe)];
  if mode=='on':args.insert(1,'-DCONFIG_NOTE10_PMU_FAILURE_RESTORE')
  r=subprocess.run(args,capture_output=True,timeout=60);(out/(mode+'-compile.log')).write_bytes(r.stdout+r.stderr)
  if r.returncode:raise RuntimeError(r.stderr.decode(errors='replace'))
  for i in (list(range(15)) if mode=='on' else list(range(5))+[11,12,14]):
   r=subprocess.run([str(exe),str(i)],capture_output=True,timeout=20);(out/(mode+'-'+str(i)+'.log')).write_bytes(r.stdout+r.stderr)
   if r.returncode:raise RuntimeError(mode+' case '+str(i)+' '+r.stderr.decode(errors='replace'))
 result={'passed':True,'hardware_verified':False,'source_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'helper_sha256':hashlib.sha256(Path(a.helper).read_bytes()).hexdigest(),'harness_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'cpu_source_sha256':hashlib.sha256(Path(a.cpu_source).read_bytes()).hexdigest(),'notifier_source_sha256':hashlib.sha256(Path(a.notifier_source).read_bytes()).hexdigest(),'cases':{'off':[CASES[i] for i in (0,1,2,3,4,11,12,14)],'on':list(CASES)},'generated_sha256':{x.name:hashlib.sha256(x.read_bytes()).hexdigest() for x in out.glob('*.c')},'log_sha256':{x.name:hashlib.sha256(x.read_bytes()).hexdigest() for x in out.glob('*.log')}};(out/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8')
if __name__=='__main__':main()
