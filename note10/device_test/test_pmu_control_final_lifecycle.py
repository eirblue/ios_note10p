"""Execute final capture, single chain and actual bridge with synthetic PMU backend."""
import argparse,hashlib,json,re,subprocess,sys
from pathlib import Path
from test_pm_preconditions_lifecycle import STUB as BASE
from test_pm_callbacks_producer import clean
from test_fsys_pm_native import function
from prepare_pmu_control_audit import PINS
EXTRA=r"""
#include <stddef.h>
#define CONFIG_NOTE10_CPU_PM_BRANCH_AUDIT 1
#define CONFIG_NOTE10_PMU_STATE_AUDIT 1
#define CONFIG_NOTE10_PMU_CONTROL_AUDIT 1
#define READ_ONCE(x) (x)
#define ARRAY_SIZE(x) (sizeof(x)/sizeof((x)[0]))
#define rcu_dereference_raw(x) (x)
#define container_of(p,t,m) ((t*)((char*)(p)-offsetof(t,m)))
static int in_interrupt(void){return 0;}
struct notifier_block {int priority;struct notifier_block *next;int (*notifier_call)(void);};
struct arm_pmu {struct notifier_block cpu_pm_nb;int unsupported;};static struct arm_pmu pmus[2];
static int cpu_pm_pmu_notify(void){return 0;}static int other_notify(void){return 0;}
struct {int lock;struct notifier_block *head;} cpu_pm_notifier_chain;static int control_reads,fail_backend;
#define spin_trylock_irqsave(lock,flags) (mode==1?0:((flags)=irq,irq=1,pc++,*(lock)=1,1))
#define spin_unlock_irqrestore(lock,flags) do{if(ctl_stage.candidate || ctl_stage.count || ctl_stage.index)abort();*(lock)=0;pc--;irq=(flags);if(mode==2)n10_pm_noirq_last.noirq_ok=0;}while(0)
"""
MOCK=r"""
#define GETTER(n,v) int n(struct notifier_block *b,struct n10_precond_row *r){(void)b;(void)r;return v;}
GETTER(n10_pre_gic,0) GETTER(n10_pre_timer,0) GETTER(n10_pre_fpsimd,0) GETTER(n10_pre_sugov,0) GETTER(n10_pre_ehld,0)
int n10_pre_pmu(struct notifier_block *b,struct n10_precond_row *r){(void)r;if(mode==8)return -EIO;return b->notifier_call==cpu_pm_pmu_notify;}
int n10_state_pmu(struct notifier_block *n,struct n10_state_row *r,unsigned int gen){(void)n;(void)r;(void)gen;return 1;}
int n10_branch_pmu(struct notifier_block *n,struct n10_branch_row *r){(void)n;r->num=1;r->nonnull=1;return 1;}
int n10_ctl_backend(struct arm_pmu *p,struct n10_ctl_row *r,unsigned int gen){(void)r;if(!p||!n10_pre_context(gen,1,1)||!cpu_pm_notifier_chain.lock)abort();if(fail_backend || p->unsupported)return -ENODEV;control_reads+=3;return 0;}
int n10_pre_gic_regs(unsigned int phase,struct n10_precond_gic_row *r,u32 c,u32 p){(void)phase;(void)c;(void)p;r->seen=1;return 0;}
"""
MAIN=r"""
#define CHECK(x) do{if(!(x)){fprintf(stderr,"line %d\n",__LINE__);return 1;}}while(0)
static void setup(unsigned int generation){owner=1;ready=1;n10_pm_active=&active;active.qgeneration=generation;active.qphase=1;active.pm_called=1;cpu=irq=pc=ops=0;online=count=1;pm_test_level=1;n10_pm_noirq_last=(struct n10_pm_noirq_sample){1,0,0,1,generation,1,1,1,1,1};}
int main(int argc,char **argv){int ret,before;struct n10_ctl_sample ctl;struct n10_ctl_stage stage={0};mode=atoi(argv[1]);pmus[0].cpu_pm_nb.notifier_call=cpu_pm_pmu_notify;pmus[1].cpu_pm_nb.notifier_call=cpu_pm_pmu_notify;cpu_pm_notifier_chain.head=&pmus[0].cpu_pm_nb;
 setup(1);n10_ctl_begin(1);n10_ctl_finish(0);CHECK(n10_ctl_read(&ctl,2));
 setup(1);irq=pc=1;cpu_pm_notifier_chain.lock=1;n10_ctl_begin(1);stage.candidate=&pmus[0];stage.count=1;before=control_reads;fail_backend=1;CHECK(n10_ctl_resolve(&stage,1,1));CHECK(n10_ctl_resolve(&stage,1,1));CHECK(control_reads==before);fail_backend=0;n10_ctl_begin(1);CHECK(!n10_ctl_resolve(&stage,1,1));before=control_reads;CHECK(n10_ctl_resolve(&stage,1,1));CHECK(control_reads==before);cpu_pm_notifier_chain.lock=0;irq=pc=0;
 setup(1);mode=0;CHECK(!n10_pre_capture(1));CHECK(!n10_ctl_read(&ctl,2));before=control_reads;
 mode=atoi(argv[1]);if(mode==3)owner=0;else if(mode==4){}else setup(2);
 if(mode==5)cpu_pm_notifier_chain.head=0;
 if(mode==6 || mode==7){pmus[0].cpu_pm_nb.next=&pmus[1].cpu_pm_nb;if(mode==7)pmus[1].unsupported=1;}
 if(mode==9)fail_backend=1;
 ret=n10_pre_capture(mode==3||mode==4?1:2);if(mode==0)CHECK(!ret);else CHECK(ret);
 if(mode){CHECK(n10_ctl_read(&ctl,2));if(mode!=2)CHECK(control_reads==before);}else CHECK(!n10_ctl_read(&ctl,3));
 mode=0;fail_backend=0;pmus[0].cpu_pm_nb.next=0;cpu_pm_notifier_chain.head=&pmus[0].cpu_pm_nb;setup(3);CHECK(!n10_pre_capture(3));CHECK(!n10_ctl_read(&ctl,4));CHECK(!cpu_pm_notifier_chain.lock && !irq && !pc);return 0;}
"""
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--source-root',required=True);ap.add_argument('--output',required=True);a=ap.parse_args();root=Path(a.source_root);out=Path(a.output);out.mkdir(parents=True,exist_ok=False)
 paths={'chain':'kernel/note10_pm_pre_chain.c','capture':'kernel/power/note10_pm_pre_capture.c','branch_chain':'kernel/note10_pm_branch_chain.c','branch_capture':'kernel/power/note10_pm_branch_capture.c','state_chain':'kernel/note10_pmu_state_chain.c','state_capture':'kernel/power/note10_pmu_state_capture.c','bridge':'drivers/perf/note10_pmu_control_bridge.c','control_chain':'kernel/note10_pmu_control_chain.c','control_capture':'kernel/power/note10_pmu_control_capture.c'}
 def raw(n):return re.sub(r'^#include[^\n]*\n','',(root/paths[n]).read_text(encoding='utf-8-sig'),flags=re.M)
 for n in ('include/linux/string.h','include/linux/compiler.h','include/linux/compiler-gcc.h','include/linux/compiler-clang.h','include/linux/compiler_types.h','lib/string.c'):
  if hashlib.sha256((root/n).read_bytes()).hexdigest()!=PINS[n]:raise ValueError('zero helper source pin differs: '+n)
 decl=(root/'include/linux/string.h').read_text();gcc=(root/'include/linux/compiler-gcc.h').read_text();types=(root/'include/linux/compiler_types.h').read_text();clang=(root/'include/linux/compiler-clang.h').read_text()
 macro='#define barrier_data(ptr) __asm__ __volatile__("": :"r"(ptr) :"memory")'
 if 'void memzero_explicit(void *s, size_t count);' not in decl or macro not in gcc or 'barrier_data' in clang or 'compiler-gcc.h' not in types or 'compiler-clang.h' not in types:raise ValueError('zero declaration/compiler selection differs')
 zero=macro+'\n'+function((root/'lib/string.c').read_text(),'void memzero_explicit(void *s, size_t count)\n{')+'\n'
 src=out/'lifecycle.c';src.write_text(BASE+EXTRA+zero+clean('pm_preconditions_contract.h')+clean('pm_branch_contract.h')+clean('pmu_state_contract.h')+clean('pmu_control_contract.h')+MOCK+raw('bridge')+raw('branch_chain')+raw('branch_capture')+raw('state_chain')+raw('state_capture')+raw('control_chain')+raw('control_capture')+raw('chain')+raw('capture')+MAIN,encoding='utf8',newline='\n');cc=Path('host-tools/windows-build/llvm-mingw/llvm-mingw-20261006-ucrt-x86_64/bin/clang.exe') if sys.platform=='win32' else 'cc';exe=out/('lifecycle.exe' if sys.platform=='win32' else 'lifecycle');r=subprocess.run([str(cc),'-std=gnu11','-O2',str(src),'-o',str(exe)],capture_output=True);(out/'compile.log').write_bytes(r.stdout+r.stderr)
 if r.returncode:raise RuntimeError(r.stderr.decode(errors='replace'))
 cases=('success','trylock-failure','post-context-failure','foreign-owner','duplicate-generation','zero-pmu','duplicate-supported','duplicate-unsupported','getter-failure','backend-failure')
 for i,name in enumerate(cases):
  r=subprocess.run([str(exe),str(i)],capture_output=True);(out/f'case-{i}.log').write_bytes(r.stdout+r.stderr)
  if r.returncode:raise RuntimeError(name+': '+r.stderr.decode(errors='replace'))
 d={'passed':True,'hardware_verified':False,'actual_final_chain_capture_bridge':True,'optimized_O2':True,'actual_pinned_memzero_body':True,'zero_pins':{n:PINS[n] for n in ('include/linux/string.h','include/linux/compiler.h','include/linux/compiler-gcc.h','include/linux/compiler-clang.h','include/linux/compiler_types.h','lib/string.c')},'cases':list(cases),'source_sha256':{k:hashlib.sha256((root/v).read_bytes()).hexdigest() for k,v in paths.items()},'harness_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'generated_sha256':hashlib.sha256(src.read_bytes()).hexdigest(),'log_sha256':{x.name:hashlib.sha256(x.read_bytes()).hexdigest() for x in out.glob('*.log')}};(out/'result.json').write_text(json.dumps(d,indent=2)+'\n',encoding='utf8',newline='\n')
if __name__=='__main__':main()
