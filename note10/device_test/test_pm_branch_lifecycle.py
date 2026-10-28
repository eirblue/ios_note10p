"""Run final prepared v38 capture and chain with fault-injected context."""
import argparse,hashlib,json,re,subprocess,sys
from pathlib import Path
from test_pm_preconditions_lifecycle import STUB as BASE
from test_pm_callbacks_producer import clean
HERE=Path(__file__).resolve().parent
EXTRA=r'''
#define CONFIG_NOTE10_CPU_PM_BRANCH_AUDIT 1
#define READ_ONCE(x) (x)
#define ARRAY_SIZE(x) (sizeof(x)/sizeof((x)[0]))
#define rcu_dereference_raw(x) (x)
struct notifier_block {int priority;struct notifier_block *next;};static struct notifier_block node;
struct {int lock;struct notifier_block *head;} cpu_pm_notifier_chain;
#define spin_trylock_irqsave(lock,flags) (mode==1?0:((flags)=irq,irq=1,pc++,*(lock)=1,1))
#define spin_unlock_irqrestore(lock,flags) do{*(lock)=0;pc--;irq=(flags);if(mode==2)n10_pm_noirq_last.noirq_ok=0;}while(0)
'''
MOCK=r'''
#define GETTER(n,v) int n(struct notifier_block *b,struct n10_precond_row *r){(void)b;(void)r;return v;}
GETTER(n10_pre_gic,0) GETTER(n10_pre_timer,0) GETTER(n10_pre_fpsimd,0) GETTER(n10_pre_sugov,0) GETTER(n10_pre_pmu,1) GETTER(n10_pre_ehld,0)
int n10_branch_pmu(struct notifier_block *n,struct n10_branch_row *r){(void)n;r->num=1;r->nonnull=1;return 1;}
int n10_pre_gic_regs(unsigned int phase,struct n10_precond_gic_row *r,u32 c,u32 p){(void)phase;(void)c;(void)p;r->seen=1;return 0;}
'''
MAIN=r'''
#define CHECK(x) do{if(!(x)){fprintf(stderr,"line %d\n",__LINE__);return 1;}}while(0)
static void setup(unsigned int generation){owner=1;ready=1;n10_pm_active=&active;active.qgeneration=generation;active.qphase=1;active.pm_called=1;cpu=irq=pc=ops=0;online=count=1;pm_test_level=1;n10_pm_noirq_last=(struct n10_pm_noirq_sample){1,0,0,1,generation,1,1,1,1,1};}
int main(int argc,char **argv){int ret;struct n10_branch_sample out;mode=0;cpu_pm_notifier_chain.head=&node;setup(1);CHECK(!n10_pre_capture(1));CHECK(!n10_branch_read(&out,2));
 mode=atoi(argv[1]);if(mode==3)owner=0;else if(mode==4){}else setup(2);
 ret=n10_pre_capture(mode==3||mode==4?1:2);if(mode==0)CHECK(!ret);else CHECK(ret);
 if(mode)CHECK(n10_branch_read(&out,2));else CHECK(!n10_branch_read(&out,3));
 mode=0;setup(3);CHECK(!n10_pre_capture(3));CHECK(!n10_branch_read(&out,4));return 0;}
'''
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--source-root',required=True);ap.add_argument('--output',required=True);a=ap.parse_args();root=Path(a.source_root);o=Path(a.output);o.mkdir(parents=True,exist_ok=False);paths={'chain':'kernel/note10_pm_pre_chain.c','capture':'kernel/power/note10_pm_pre_capture.c','branch_chain':'kernel/note10_pm_branch_chain.c','branch_capture':'kernel/power/note10_pm_branch_capture.c'}
 def raw(n):return re.sub(r'^#include[^\n]*\n','',(root/paths[n]).read_text(encoding='utf-8-sig'),flags=re.M)
 src=o/'lifecycle.c';src.write_text(BASE+EXTRA+clean('pm_preconditions_contract.h')+clean('pm_branch_contract.h')+MOCK+raw('branch_chain')+raw('branch_capture')+raw('chain')+raw('capture')+MAIN,encoding='utf-8');cc=Path('host-tools/windows-build/llvm-mingw/llvm-mingw-20261006-ucrt-x86_64/bin/clang.exe') if sys.platform=='win32' else 'cc';exe=o/('lifecycle.exe' if sys.platform=='win32' else 'lifecycle');r=subprocess.run([str(cc),'-std=gnu11',str(src),'-o',str(exe)],capture_output=True,timeout=60);(o/'compile.log').write_bytes(r.stdout+r.stderr)
 if r.returncode:raise RuntimeError(r.stderr.decode(errors='replace'))
 cases=('success','trylock-failure','post-context-failure','foreign-owner','duplicate-generation')
 for i,n in enumerate(cases):
  r=subprocess.run([str(exe),str(i)],capture_output=True,timeout=20);(o/f'case-{i}.log').write_bytes(r.stdout+r.stderr)
  if r.returncode:raise RuntimeError(n+': '+r.stderr.decode(errors='replace'))
 d={'passed':True,'hardware_verified':False,'actual_final_capture_and_chain':True,'cases':list(cases),'source_sha256':{k:hashlib.sha256((root/p).read_bytes()).hexdigest() for k,p in paths.items()},'harness_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'generated_c_sha256':hashlib.sha256(src.read_bytes()).hexdigest(),'log_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in o.glob('*.log')}};(o/'result.json').write_text(json.dumps(d,indent=2)+'\n',encoding='utf-8')
if __name__=='__main__':main()
