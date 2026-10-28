"""Execute actual six getters and chain collector with synthetic RAM/locks."""
import argparse,hashlib,json,subprocess,sys
from pathlib import Path
from test_pm_callbacks_producer import clean
HERE=Path(__file__).resolve().parent
STUB=r"""
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <errno.h>
typedef unsigned int u32;typedef long long s64;
#define READ_ONCE(x) (x)
#define ARRAY_SIZE(x) (sizeof(x)/sizeof((x)[0]))
#define container_of(p,t,m) ((t*)((char*)(p)-__builtin_offsetof(t,m)))
struct notifier_block {int (*notifier_call)(struct notifier_block*,unsigned long,void*);int priority;struct notifier_block *next;};
#define DECLARE_FN(n) static int n(struct notifier_block*a,unsigned long b,void*c){(void)a;(void)b;(void)c;return 0;}
DECLARE_FN(gic_notifier) DECLARE_FN(arch_timer_cpu_pm_notify) DECLARE_FN(fpsimd_cpu_pm_notifier) DECLARE_FN(sugov_pm_notifier) DECLARE_FN(cpu_pm_pmu_notify) DECLARE_FN(exynos_ehld_c2_pm_notifier)
static struct notifier_block gic_notifier_block,arch_timer_cpu_pm_notifier,fpsimd_cpu_pm_notifier_block,sugov_pm_nb,exynos_ehld_c2_pm_nb,unknown,many[33];
static int cpu,irq,preempt,lock_fail;
#define raw_smp_processor_id() cpu
#define irqs_disabled() irq
#define preempt_count() preempt
#define rcu_dereference_raw(x) (x)
struct {int lock;struct notifier_block *head;} cpu_pm_notifier_chain;
#define spin_trylock_irqsave(lock,flags) (lock_fail ? 0 : ((flags)=irq,irq=1,preempt++,*(lock)=1,1))
#define spin_unlock_irqrestore(lock,flags) do{*(lock)=0;preempt--;irq=(flags);}while(0)
int n10_pre_context(unsigned int generation,int irq_off,unsigned int expected_preempt){return generation==1 && !cpu && irq==irq_off && preempt==expected_preempt;}
struct fpstate {int x;};struct task {void *mm;struct {struct fpstate fpsimd_state;struct {int depth;} fpsimd_kernel_state;} thread;} task,*current=&task;
static struct fpstate *fpsimd_last_state;static int foreign;
#define TIF_FOREIGN_FPSTATE 1
#define test_thread_flag(x) (foreign)
#define atomic_read(p) (*(p))
#define __this_cpu_read(x) (x)
struct hnode {void *pprev;};struct timer_list {struct hnode entry;};struct sugov_exynos {int enabled,started;struct timer_list timer;};static struct sugov_exynos sugov_exynos;
struct exynos_ehld_ctrl {void *event;int ehld_running;};static struct exynos_ehld_ctrl ehld_ctrl;
#define this_cpu_ptr(p) (p)
struct pmu_hw_events {unsigned long used_mask[1];void *events[32];};struct arm_pmu {struct notifier_block cpu_pm_nb;int num_events;struct pmu_hw_events *hw_events;unsigned long supported_cpus;};static struct arm_pmu pmu,pmu2;static struct pmu_hw_events hw,hw2;
#define test_bit(i,p) (((p)[0]>>(i))&1)
#define cpumask_test_cpu(i,p) (((*(p))>>(i))&1)
""".replace('\\"','"')
MAIN=r"""
#define CHECK(x) do{if(!(x)){fprintf(stderr,"failed %d\\n",__LINE__);return 1;}}while(0)
int main(int argc,char **argv){int mode=atoi(argv[1]),i,r;struct n10_precond_sample out={0};struct notifier_block *chain[]={&gic_notifier_block,&arch_timer_cpu_pm_notifier,&fpsimd_cpu_pm_notifier_block,&sugov_pm_nb,&pmu.cpu_pm_nb,&exynos_ehld_c2_pm_nb,&unknown,&pmu2.cpu_pm_nb};
 gic_notifier_block.notifier_call=gic_notifier;arch_timer_cpu_pm_notifier.notifier_call=arch_timer_cpu_pm_notify;fpsimd_cpu_pm_notifier_block.notifier_call=fpsimd_cpu_pm_notifier;sugov_pm_nb.notifier_call=sugov_pm_notifier;pmu.cpu_pm_nb.notifier_call=pmu2.cpu_pm_nb.notifier_call=cpu_pm_pmu_notify;exynos_ehld_c2_pm_nb.notifier_call=exynos_ehld_c2_pm_notifier;pmu.num_events=pmu2.num_events=4;pmu.hw_events=&hw;pmu2.hw_events=&hw2;pmu.supported_cpus=1;hw.used_mask[0]=3;hw.events[0]=&hw;task.mm=&task;task.thread.fpsimd_kernel_state.depth=2;fpsimd_last_state=&task.thread.fpsimd_state;sugov_exynos.started=1;sugov_exynos.timer.entry.pprev=&task;ehld_ctrl.event=&task;for(i=0;i<8;i++){chain[i]->priority=8-i;chain[i]->next=i<7?chain[i+1]:0;}cpu_pm_notifier_chain.head=chain[0];
 if(mode==1)cpu_pm_notifier_chain.head=0;if(mode==2)lock_fail=1;if(mode==3)pmu.num_events=33;if(mode==4)cpu=1;if(mode==5)sugov_exynos.started=0;
 if(mode==6 || mode==7){for(i=0;i<33;i++)many[i].next=i<32?&many[i+1]:0;cpu_pm_notifier_chain.head=many;if(mode==6)many[31].next=0;}
 if(mode==8)pmu.num_events=0;
 if(mode==9){pmu.num_events=32;hw.used_mask[0]=(1UL<<31);hw.events[31]=&hw;}
 r=n10_pre_chain(&out,1);
 if(mode==2){CHECK(r==-EBUSY && !irq && !preempt);return 0;}
 if(mode==3){CHECK(r==-EINVAL && !irq && !preempt);return 0;}
 if(mode==4){CHECK(r==-EIO && !irq && !preempt);return 0;}
 if(mode==7){CHECK(r==-E2BIG && out.count==32 && !irq && !preempt);return 0;}
 CHECK(!r && !irq && !preempt);
 if(mode==1){CHECK(out.count==0);return 0;}
 if(mode==6){CHECK(out.count==32);return 0;}
 CHECK(out.count==8);for(i=0;i<6;i++)CHECK(out.row[i].kind==i+1);CHECK(out.row[6].kind==0 && !out.row[6].valid);CHECK(out.row[7].kind==5);CHECK(out.row[5].valid==3 && out.row[5].value[1]==1);
 if(mode==8)CHECK(out.row[4].value[1]==0 && !out.row[4].value[2] && !out.row[4].value[3] && !out.row[4].value[4]);
 else if(mode==9)CHECK(out.row[4].value[1]==32 && out.row[4].value[2]==2147483648LL && out.row[4].value[3]==1 && out.row[4].value[4]==2);
 else CHECK(out.row[4].value[2]==3 && out.row[4].value[3]==2 && out.row[4].value[4]==1);
 if(mode==5)CHECK(out.row[3].valid==3 && out.row[3].value[2]==0);else CHECK(out.row[3].valid==7 && out.row[3].value[2]==1);
 return 0;}
""".replace('\\"','"')
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--output',required=True);o=Path(ap.parse_args().output);o.mkdir(parents=True,exist_ok=True);names=['pm_preconditions_contract.h','pm_preconditions_gic_getter.c','pm_preconditions_timer_getter.c','pm_preconditions_fpsimd_getter.c','pm_preconditions_sugov_getter.c','pm_preconditions_pmu_getter.c','pm_preconditions_ehld_getter.c','pm_preconditions_chain.c'];src=o/'getters.c';src.write_text(STUB+''.join(clean(x) for x in names)+MAIN,encoding='utf-8');cc=Path('host-tools/windows-build/llvm-mingw/llvm-mingw-20261006-ucrt-x86_64/bin/clang.exe') if sys.platform=='win32' else 'cc';exe=o/('getters.exe' if sys.platform=='win32' else 'getters');r=subprocess.run([str(cc),'-std=gnu11',str(src),'-o',str(exe)],capture_output=True,timeout=60);(o/'compile.log').write_bytes(r.stdout+r.stderr)
 if r.returncode:raise RuntimeError(r.stderr.decode(errors='replace'))
 for mode in range(10):
  r=subprocess.run([str(exe),str(mode)],capture_output=True,timeout=20);(o/f'mode-{mode}.log').write_bytes(r.stdout+r.stderr)
  if r.returncode:raise RuntimeError('getter case '+str(mode)+' failed')
 d={'passed':True,'hardware_verified':False,'source_sha256':{n:hashlib.sha256((HERE/n).read_bytes()).hexdigest() for n in names},'generated_c_sha256':hashlib.sha256(src.read_bytes()).hexdigest(),'harness_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'log_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in o.glob('*.log')},'cases':['six-and-unknown-multi-pmu','empty','trylock','pmu-bound','wrong-cpu','timer-not-started','capacity-32','capacity-33','pmu-zero','pmu-bit31']};(o/'result.json').write_text(json.dumps(d,indent=2)+'\n',encoding='utf-8')
if __name__=='__main__':main()
