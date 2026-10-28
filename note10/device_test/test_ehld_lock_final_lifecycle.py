"""Run v45 helpers through the actual composed CPU-PM caller/capture units."""
import argparse,hashlib,json,re,subprocess,sys
from pathlib import Path
import test_rcu_context_final_lifecycle as rcu
from test_pm_callbacks_producer import clean

CASES=['target-first','target-middle','target-late-with-trailing-nontarget','busy-valid','duplicate-capture','generation-wrap','invalid-mask','bad-prior-getter','stale-then-fresh','reentry-then-fresh']
PATHS={'chain':'kernel/note10_pm_pre_chain.c','capture':'kernel/power/note10_pm_pre_capture.c','worker':'arch/arm64/mm/note10_pm_timer_roundtrip.c','getter':'drivers/soc/samsung/debug/note10_ehld_lock_getter.c','lock_chain':'kernel/note10_ehld_lock_chain.c','lock_capture':'kernel/power/note10_ehld_lock_capture.c'}
EHLD_FIXTURE=r'''
struct exynos_ehld_ctrl { int ehld_running, lock; };
static struct exynos_ehld_ctrl g_ehld;
static struct notifier_block ehld_nb, tail_nb;
static int ehld_notify(void){return 0;}
#define exynos_ehld_c2_pm_notifier ehld_notify
#define exynos_ehld_c2_pm_nb ehld_nb
#define ehld_ctrl g_ehld
static int force_busy, fail_after_lock, running_reads, raw_unlocks, badmask, trigger_reentry;
#undef READ_ONCE
#define READ_ONCE(x) ({if((void *)&(x)==(void *)&g_ehld.ehld_running)running_reads++;(x);})
static int raw_spin_trylock(int *p){if(force_busy)return 0;if(*p)return 0;*p=1;pc++;if(fail_after_lock)active.qgeneration++;return 1;}
static void raw_spin_unlock(int *p){raw_unlocks++;*p=0;pc--;}
int n10_pre_ehld(struct notifier_block *n,struct n10_precond_row *r){if(n!=&ehld_nb)return 0;if(trigger_reentry){trigger_reentry=0;(void)n10_pre_capture(active.qgeneration);}r->valid=badmask?1:3;r->value[0]=READ_ONCE(g_ehld.ehld_running);r->value[1]=1;return 1;}
'''
MAIN=r'''
#define CHECK(x) do{if(!(x)){fprintf(stderr,"line %d: %s\n",__LINE__,#x);return 1;}}while(0)
static void link_nodes(int pos){struct notifier_block *a=&fpsimd_cpu_pm_notifier_block,*b=&pmus[0].cpu_pm_nb,*e=&ehld_nb,*t=&tail_nb;a->notifier_call=fpsimd_cpu_pm_notifier;b->notifier_call=cpu_pm_pmu_notify;e->notifier_call=ehld_notify;t->notifier_call=other_notify;
 if(pos==0){e->next=a;a->next=b;b->next=t;}else if(pos==1){a->next=e;e->next=b;b->next=t;}else{a->next=b;b->next=e;e->next=t;}t->next=NULL;cpu_pm_notifier_chain.head=pos==0?e:a;}
static void setup(unsigned int gen){owner=1;ready=1;n10_pm_active=&active;active.qgeneration=gen;active.qphase=1;active.pm_called=1;cpu=irq=pc=ops=0;online=count=1;pm_test_level=1;n10_pm_noirq_last=(struct n10_pm_noirq_sample){1,0,0,1,gen,1,1,1,1,1};task.mm=&task;task.thread.fpsimd_kernel_state.depth=2;fpsimd_last_state=&other;rcu_dynticks.dynticks=2;rcu_dynticks.dynticks_nesting=1;}
static int run(unsigned int gen,int pos,int busy,int badmask_arg,int badpmu,int reenter){struct n10_precond_sample pre;struct n10_ehld_lock_sample audit;unsigned int completed=gen+1;int ret;mode=badpmu?8:0;force_busy=busy;fail_after_lock=0;badmask=badmask_arg;trigger_reentry=reenter;g_ehld.lock=0;g_ehld.ehld_running=pos==0?INT_MIN:pos==1?-1:INT_MAX;running_reads=raw_unlocks=0;link_nodes(pos);setup(gen);active.qgeneration=gen;if(!completed)completed=1;
 ret=n10_pre_capture(gen);if(ret)fprintf(stderr,"capture=%d count=%u chainerr=%d bad=%d ehldidx=%u ehldkind=%u valid=%u old=%lld attempted=%d resolved=%d checked=%d\n",ret,n10_pre_last.count,n10_pre_last.error,n10_pre_bad,n10_ehld_lock_last.row.index,n10_pre_last.row[n10_ehld_lock_last.row.index].kind,n10_pre_last.row[n10_ehld_lock_last.row.index].valid,(long long)n10_pre_last.row[n10_ehld_lock_last.row.index].value[0],n10_ehld_lock_attempted,n10_ehld_lock_resolved,n10_ehld_lock_checked);if(badpmu){CHECK(ret!=0);CHECK(n10_ehld_lock_read(&audit,completed)!=0);return 0;}if(badmask_arg){CHECK(ret!=0);return 0;}if(reenter){CHECK(ret!=0);CHECK(n10_pre_read(&pre,completed)!=0);CHECK(n10_ehld_lock_read(&audit,completed)!=0);return 0;}CHECK(ret==0);CHECK(!n10_pre_read(&pre,completed));CHECK(!n10_ehld_lock_read(&audit,completed));CHECK(audit.row.index==(unsigned)(pos==0?0:pos==1?1:2));CHECK(audit.row.chain_count==4);CHECK(audit.row.lock_available==(unsigned)!busy);CHECK(audit.row.running_valid==(unsigned)!busy);CHECK(audit.row.running==(unsigned)(busy?0:1));CHECK(running_reads==(unsigned)!busy+1); /* one prior getter read plus locked sample */CHECK(raw_unlocks==(unsigned)!busy);CHECK(pc==0&&!irq);return 0;}
int main(int argc,char**argv){int m=atoi(argv[1]);struct n10_ehld_lock_sample audit;struct n10_precond_sample pre;if(m<=2)return run(1,m,0,0,0,0);if(m==3)return run(1,1,1,0,0,0);if(m==4){CHECK(run(1,1,0,0,0,0)==0);CHECK(n10_pre_capture(1)!=0);CHECK(n10_ehld_lock_read(&audit,2)!=0);CHECK(run(3,2,0,0,0,0)==0);return 0;}if(m==5){CHECK(run(0xffffffffU,2,0,0,0,0)==0);return run(1,1,0,0,0,0);}if(m==6)return run(1,1,0,1,0,0);if(m==7)return run(1,0,0,0,1,0);if(m==8){CHECK(run(2,2,0,0,0,0)==0);link_nodes(1);setup(1);active.qgeneration=1;CHECK(n10_pre_capture(1)!=0);CHECK(n10_pre_read(&pre,3)!=0);CHECK(n10_ehld_lock_read(&audit,3)!=0);return run(3,0,0,0,0,0);}if(m==9){CHECK(run(1,1,0,0,0,1)==0);return run(3,2,0,0,0,0);}return 1;}
'''

def make_code(root):
 code=rcu.make_code(root)
 prefix=code.rsplit(rcu.MAIN,1)[0]
 prefix=prefix.replace('#define CONFIG_NOTE10_RCU_CONTEXT_AUDIT 1','#define CONFIG_NOTE10_RCU_CONTEXT_AUDIT 1\n#define CONFIG_NOTE10_EHLD_LOCK_AUDIT 1',1)
 prefix=prefix.replace('GETTER(n10_pre_ehld,0)','int n10_pre_ehld(struct notifier_block *,struct n10_precond_row *);',1)
 anchor='int n10_pre_chain(struct n10_precond_sample *out, unsigned int generation)'
 contract=clean('ehld_lock_contract.h')
 prefix=prefix.replace(anchor,contract+'\n'+anchor,1)
 # Insert fixture before the real chain so the substituted prior getter can be defined.
 prefix=prefix.replace(anchor,EHLD_FIXTURE+'\n'+anchor,1)
 helpers=''
 helper_paths={'ehld_lock_getter.c':'drivers/soc/samsung/debug/note10_ehld_lock_getter.c','ehld_lock_chain.c':'kernel/note10_ehld_lock_chain.c','ehld_lock_capture.c':'kernel/power/note10_ehld_lock_capture.c'}
 for n,snapshot_path in helper_paths.items():
  public=Path(__file__).resolve().parent/n
  if (root/snapshot_path).read_bytes()!=public.read_bytes():raise ValueError('snapshot helper differs from public source: '+n)
  helpers+=clean(n)
 return prefix+helpers+MAIN

def main():
 p=argparse.ArgumentParser();p.add_argument('--source-root',required=True,type=Path);p.add_argument('--output',required=True,type=Path);p.add_argument('--cc',required=True);a=p.parse_args();root=a.source_root;out=a.output;out.mkdir(parents=True,exist_ok=False)
 code=make_code(root);src=out/'lifecycle.c';exe=out/('lifecycle.exe' if sys.platform=='win32' else 'lifecycle');src.write_text(code,encoding='utf8',newline='\n')
 c=subprocess.run([a.cc,'-std=gnu11','-O2',str(src),'-o',str(exe)],capture_output=True);(out/'compile.log').write_bytes(c.stdout+c.stderr)
 if c.returncode:raise RuntimeError('compile failed; inspect compile.log')
 for i,name in enumerate(CASES):
  x=subprocess.run([str(exe.resolve()),str(i)],capture_output=True);(out/(name+'.log')).write_bytes(x.stdout+x.stderr)
  if x.returncode:raise RuntimeError(name+' failed')
 h=lambda f:hashlib.sha256(f.read_bytes()).hexdigest()
 (out/'result.json').write_text(json.dumps({'passed':True,'hardware_verified':False,'cases':CASES,'source_sha256':{k:h(root/v) for k,v in PATHS.items()},'harness_sha256':h(Path(__file__)),'generated_sha256':h(src),'logs_sha256':{p.name:h(p) for p in out.glob('*.log')}},indent=2)+'\n',encoding='utf8',newline='\n')
if __name__=='__main__':main()
