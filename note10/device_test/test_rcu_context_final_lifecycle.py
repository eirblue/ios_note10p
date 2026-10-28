"""Execute actual final capture and chain with synthetic RCU and callbacks."""
import argparse,hashlib,json,re,subprocess,sys
from pathlib import Path
import test_fpsimd_reference_final_lifecycle as prior
from test_pm_callbacks_producer import clean
from test_fsys_pm_native import function
from prepare_pmu_control_audit import PINS
ADD=r'''#include <limits.h>
#include <stdbool.h>
#define CONFIG_NOTE10_RCU_CONTEXT_AUDIT 1
#define RCU_DYNTICK_CTRL_CTR 2
typedef int atomic_t;
struct rcu_dynticks {long long dynticks_nesting;int dynticks_nmi_nesting;atomic_t dynticks;};static struct rcu_dynticks rcu_dynticks;static bool disable_rcu_irq_enter;
#define this_cpu_ptr(p) (p)
'''
MAIN=r'''
#define CHECK(x) do{if(!(x)){fprintf(stderr,"line %d\n",__LINE__);return 1;}}while(0)
static void setup(unsigned int gen){owner=1;ready=1;n10_pm_active=&active;active.qgeneration=gen;active.qphase=1;active.pm_called=1;cpu=irq=pc=ops=0;online=count=1;pm_test_level=1;n10_pm_noirq_last=(struct n10_pm_noirq_sample){1,0,0,1,gen,1,1,1,1,1};}
int main(int argc,char **argv){struct n10_rcu_sample out;int ret;mode=atoi(argv[1]);pmus[0].cpu_pm_nb.notifier_call=cpu_pm_pmu_notify;fpsimd_cpu_pm_notifier_block.notifier_call=fpsimd_cpu_pm_notifier;fpsimd_cpu_pm_notifier_block.next=&pmus[0].cpu_pm_nb;cpu_pm_notifier_chain.head=&fpsimd_cpu_pm_notifier_block;task.mm=&task;task.thread.fpsimd_kernel_state.depth=2;fpsimd_last_state=&other;rcu_dynticks.dynticks=2;rcu_dynticks.dynticks_nesting=1;setup(1);
 if(mode==3)cpu_pm_notifier_chain.head=&pmus[0].cpu_pm_nb;
 if(mode==4)pmus[0].cpu_pm_nb.next=&fpsimd_cpu_pm_notifier_block;
 if(mode==5)mode=8;
 ret=n10_pre_capture(1);if(mode==0){CHECK(!ret);CHECK(!n10_rcu_read(&out,2));CHECK(out.row.watching==1 && out.row.chain_count==2);}else{CHECK(ret);CHECK(n10_rcu_read(&out,2));}
 mode=0;pmus[0].cpu_pm_nb.next=0;cpu_pm_notifier_chain.head=&fpsimd_cpu_pm_notifier_block;setup(2);CHECK(!n10_pre_capture(2));CHECK(!n10_rcu_read(&out,3));CHECK(n10_pre_capture(2));CHECK(n10_rcu_read(&out,3));setup(3);CHECK(!n10_pre_capture(3));CHECK(!n10_rcu_read(&out,4));setup(2);CHECK(n10_pre_capture(2));CHECK(n10_rcu_read(&out,4));
 memset(&n10_pre_last,0,sizeof(n10_pre_last));n10_pre_bad=0;setup(0xffffffffU);CHECK(!n10_pre_capture(0xffffffffU));CHECK(!n10_rcu_read(&out,1));setup(1);CHECK(!n10_pre_capture(1));CHECK(!n10_rcu_read(&out,2));return 0;}
'''
CASES=['success','trylock','post-context','missing-fpsimd','duplicate-fpsimd','prior-getter-error']
PATHS={'chain':'kernel/note10_pm_pre_chain.c','capture':'kernel/power/note10_pm_pre_capture.c','branch_chain':'kernel/note10_pm_branch_chain.c','branch_capture':'kernel/power/note10_pm_branch_capture.c','state_chain':'kernel/note10_pmu_state_chain.c','state_capture':'kernel/power/note10_pmu_state_capture.c','bridge':'drivers/perf/note10_pmu_control_bridge.c','control_chain':'kernel/note10_pmu_control_chain.c','control_capture':'kernel/power/note10_pmu_control_capture.c','fps_getter':'arch/arm64/kernel/note10_fpsimd_reference_getter.c','fps_chain':'kernel/note10_fpsimd_reference_chain.c','fps_capture':'kernel/power/note10_fpsimd_reference_capture.c','rcu_getter':'kernel/rcu/note10_rcu_context_getter.c','rcu_chain':'kernel/note10_rcu_context_chain.c','rcu_capture':'kernel/power/note10_rcu_context_capture.c'}
def make_code(root):
 def raw(n):return re.sub(r'^#include[^\n]*\n','',(root/PATHS[n]).read_text(encoding='utf8'),flags=re.M)
 for n,digest in PINS.items():
  if n.startswith('include/linux/compiler') or n in ('include/linux/string.h','lib/string.c'):
   if hashlib.sha256((root/n).read_bytes()).hexdigest()!=digest:raise ValueError('zero pin differs')
 zero='#define barrier_data(ptr) __asm__ __volatile__("": :"r"(ptr) :"memory")\n'+function((root/'lib/string.c').read_text(),'void memzero_explicit(void *s, size_t count)\n{')+'\n'
 prev=prior.ADD.replace('struct fake_task {void *mm;','struct fake_task {int rcu_read_lock_nesting;union {u32 s;} rcu_read_unlock_special;void *mm;')
 mock=prior.MOCK.replace('GETTER(n10_pre_fpsimd,0)','int n10_pre_fpsimd(struct notifier_block *b,struct n10_precond_row *r){if(b!=&fpsimd_cpu_pm_notifier_block)return 0;r->valid=15;r->value[0]=1;r->value[1]=1;r->value[2]=2;r->value[3]=0;return 1;}')
 order=('bridge','branch_chain','branch_capture','state_chain','state_capture','control_chain','control_capture','fps_getter','fps_chain','fps_capture','rcu_getter','rcu_chain','rcu_capture','chain','capture')
 return prior.BASE+prior.EXTRA+prev+ADD+zero+''.join(clean(n) for n in ('pm_preconditions_contract.h','pm_branch_contract.h','pmu_state_contract.h','pmu_control_contract.h','fpsimd_reference_contract.h','rcu_context_contract.h'))+mock+''.join(raw(n) for n in order)+MAIN
def main():
 p=argparse.ArgumentParser();p.add_argument('--source-root',required=True,type=Path);p.add_argument('--output',required=True,type=Path);p.add_argument('--cc',default='clang');a=p.parse_args();root=a.source_root;out=a.output;out.mkdir(parents=True,exist_ok=False);code=make_code(root);(out/'lifecycle.c').write_bytes(code.encode());exe=out/('lifecycle.exe' if sys.platform=='win32' else 'lifecycle');c=subprocess.run([a.cc,'-std=gnu11','-O2',str(out/'lifecycle.c'),'-o',str(exe)],capture_output=True);(out/'compile.log').write_bytes(c.stdout+c.stderr)
 if c.returncode:raise RuntimeError(c.stderr.decode(errors='replace'))
 for i,name in enumerate(CASES):
  x=subprocess.run([str(exe.resolve()),str(i)],capture_output=True);(out/(name+'.log')).write_bytes(x.stdout+x.stderr)
  if x.returncode:raise RuntimeError(name+': '+x.stderr.decode(errors='replace'))
 h=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();proof={'passed':True,'hardware_verified':False,'cases':CASES,'source_sha256':{k:h(root/v) for k,v in PATHS.items()},'harness_sha256':h(Path(__file__)),'generated_sha256':hashlib.sha256(code.encode()).hexdigest(),'log_sha256':{n:h(out/n) for n in ['compile.log']+[x+'.log' for x in CASES]}};(out/'result.json').write_text(json.dumps(proof,indent=2)+'\n',encoding='utf8')
if __name__=='__main__':main()
