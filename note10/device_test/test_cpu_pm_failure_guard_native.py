"""Native guarded CPU PM and notifier/syscore model; synthetic clients only."""
import argparse, hashlib, json, subprocess, sys
from pathlib import Path
from test_fsys_pm_native import function
from prepare_pm_callbacks import PINS, reverse_guard, GUARD_MARKER, verify_edge_syscore

def sha(b): return hashlib.sha256(b).hexdigest()
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--source-root',required=True);ap.add_argument('--cpu-source');ap.add_argument('--notifier-source');ap.add_argument('--output',required=True);a=ap.parse_args();root=Path(a.source_root);out=Path(a.output);out.mkdir(parents=True,exist_ok=True)
 files={n:(root/n).read_bytes() for n in ('kernel/cpu_pm.c','kernel/notifier.c','drivers/base/syscore.c','include/linux/notifier.h','include/linux/cpu_pm.h')}
 if a.cpu_source:files['kernel/cpu_pm.c']=Path(a.cpu_source).read_bytes()
 if a.notifier_source:files['kernel/notifier.c']=Path(a.notifier_source).read_bytes()
 cpu=files['kernel/cpu_pm.c']; suffix=b'\n#ifdef CONFIG_NOTE10_PM_CALLBACK_INVENTORY\n#include "note10_pm_callbacks_cpu_pm.c"\n#endif\n'
 if not cpu.endswith(suffix) or not cpu[:-len(suffix)].endswith(GUARD_MARKER) or sha(reverse_guard(cpu[:-len(suffix)-len(GUARD_MARKER)]))!=PINS['kernel/cpu_pm.c']:raise ValueError('guard composition differs')
 original_syscore=verify_edge_syscore(files['drivers/base/syscore.c']).decode()
 for n in ('kernel/notifier.c','include/linux/notifier.h','include/linux/cpu_pm.h'):
  if sha(files[n])!=PINS[n]:raise ValueError('source pin differs '+n)
 c=cpu.decode();n=files['kernel/notifier.c'].decode();sc=files['drivers/base/syscore.c'].decode()
 stub=r"""
#include <stdio.h>
#include <stdlib.h>
#include <stddef.h>
#include <errno.h>
#include <stdbool.h>
#define CONFIG_NOTE10_CPU_PM_FAILURE_GUARD 1
#define NOTIFY_DONE 0
#define NOTIFY_OK 1
#define NOTIFY_STOP_MASK 0x8000
#define NOTIFY_STOP 0x8001
#define rcu_dereference_raw(x) (x)
#define rcu_irq_enter_irqson() ((void)0)
#define rcu_irq_exit_irqson() ((void)0)
#define rcu_read_lock() ((void)0)
#define rcu_read_unlock() ((void)0)
#define dbg_snapshot_print_notifier_call(...) ((void)0)
#define DSS_FLAG_IN 0
#define DSS_FLAG_OUT 0
struct notifier_block { int (*notifier_call)(struct notifier_block*,unsigned long,void*); struct notifier_block *next; int id; };
struct atomic_notifier_head { struct notifier_block *head; } cpu_pm_notifier_chain;
#define trace_suspend_resume(...) ((void)0)
#define pr_debug(...) ((void)0)
#define pr_info(...) ((void)0)
#define pr_err(...) ((void)0)
#define WARN_ONCE(...) ((void)0)
#define dbg_snapshot_suspend(...) ((void)0)
#define log_suspend_abort_reason(...) ((void)0)
#define irqs_disabled() 1
#define TPS(x) (x)
int initcall_debug, wakeup;
#define pm_wakeup_pending() wakeup
struct syscore_ops { int (*suspend)(void); void (*resume)(void); int id; };
struct syscore_ops *nodes[2]; int nodecount;
#define syscore_ops_list 0
#define list_for_each_entry_reverse(p,h,m) for(int idx=nodecount-1;idx>=0 && ((p)=nodes[idx],1);--idx)
#define list_for_each_entry_continue(p,h,m) for(int idx=(p)->id+1;idx<nodecount && ((p)=nodes[idx],1);++idx)
#define list_for_each_entry(p,h,m) for(int idx=0;idx<nodecount && ((p)=nodes[idx],1);++idx)
""".replace('\\"','"')
 header=files['include/linux/cpu_pm.h'].decode(); start=header.index('enum cpu_pm_event {'); end=header.index('};',start)+2
 code=stub+header[start:end]+'\n'+function(files['include/linux/notifier.h'].decode(),'static inline int notifier_to_errno(')+function(n,'static int notifier_call_chain(')+function(n,'int __atomic_notifier_call_chain(')+function(c,'static int cpu_pm_notify(')
 for name in ('int cpu_pm_enter(', 'int cpu_pm_exit(', 'int cpu_cluster_pm_enter(', 'int cpu_cluster_pm_exit(', 'static int cpu_pm_suspend(', 'static void cpu_pm_resume('):code+=function(c,name)
 for name in ('int syscore_suspend(', 'void syscore_resume('):
  if function(sc,name)!=function(original_syscore,name):raise ValueError('syscore function differs from original: '+name)
  code+=function(sc,name)
 code+=r"""
static int ev[8][6], fail_event=-1, fail_index=-1, exit_fail, stop_index=-1;
static int client(struct notifier_block*b,unsigned long e,void*v){(void)v;ev[e][b->id]++;if(fail_event==99 && e==CPU_PM_ENTER && b->id==5)return 2;if((int)e==fail_event && b->id==fail_index)return 0x8006;if(e==CPU_PM_EXIT && exit_fail && b->id==0)return 0x8007;if((int)e==fail_event && b->id==stop_index)return NOTIFY_STOP;return NOTIFY_DONE;}
static int bad(void){return -17;}
static void check(int x){if(!x)abort();}
int main(int argc,char**argv){int mode=atoi(argv[1]),i,r;struct notifier_block b[6];struct syscore_ops pm={cpu_pm_suspend,cpu_pm_resume,1},other={bad,0,0};for(i=0;i<6;i++){b[i]=(struct notifier_block){client,i<5?&b[i+1]:0,i};}cpu_pm_notifier_chain.head=b;nodes[0]=&other;nodes[1]=&pm;nodecount=2;
if(mode==1)cpu_pm_notifier_chain.head=0;
if(mode>=10&&mode<16){fail_event=CPU_PM_ENTER;fail_index=mode-10;}
if(mode>=20&&mode<26){fail_event=CPU_CLUSTER_PM_ENTER;fail_index=mode-20;}
if(mode==30)wakeup=1;
if(mode==31){fail_event=CPU_CLUSTER_PM_ENTER;fail_index=3;exit_fail=1;}
if(mode==32){fail_event=CPU_PM_ENTER;stop_index=2;}
if(mode==34)fail_event=99;
if(mode==33){nodecount=1;nodes[0]=&pm;pm.id=0;}
r=syscore_suspend();
if(mode==30){check(r==-EBUSY);return 0;}
if(mode==34){check(r==-1);for(i=0;i<6;i++)check(ev[CPU_PM_ENTER_FAILED][i]==(i<5));}
else if(mode>=10&&mode<16){check(r==-5);for(i=0;i<6;i++)check(ev[CPU_PM_ENTER_FAILED][i]==(i<fail_index));}
else if((mode>=20&&mode<26)||mode==31){check(r==-5);for(i=0;i<6;i++)check(ev[CPU_CLUSTER_PM_ENTER_FAILED][i]==(i<fail_index));check(ev[CPU_PM_EXIT][0]==1);if(!exit_fail)for(i=0;i<6;i++)check(ev[CPU_PM_EXIT][i]==1);}
else if(mode==33){check(r==0);syscore_resume();for(i=0;i<6;i++)check(ev[CPU_PM_EXIT][i]==1);}
else {check(r==-17);if(mode==32){check(ev[CPU_PM_ENTER][2]==1&&ev[CPU_PM_ENTER][3]==0);}if(mode!=1)for(i=0;i<6;i++)check(ev[CPU_PM_EXIT][i]==1);}
return 0;}
""".replace('\\"','"')
 src=out/'guard.c';src.write_text(code,encoding='utf-8');cc=Path('host-tools/windows-build/llvm-mingw/llvm-mingw-20261006-ucrt-x86_64/bin/clang.exe') if sys.platform=='win32' else 'cc';exe=out/('guard.exe' if sys.platform=='win32' else 'guard');r=subprocess.run([str(cc),'-std=gnu11',str(src),'-o',str(exe)],capture_output=True,timeout=60);(out/'compile.log').write_bytes(r.stdout+r.stderr)
 if r.returncode:raise RuntimeError(r.stderr.decode(errors='replace'))
 # Preprocess the actual three changed functions with guard absent; compare
 # with the original pinned bodies without executing the uninitialized path.
 original=reverse_guard(cpu[:-len(suffix)-len(GUARD_MARKER)]).decode()
 names=('int cpu_pm_enter(', 'int cpu_cluster_pm_enter(', 'static int cpu_pm_suspend(')
 for label,body in (('guard-off',c),('original',original)):
  part=out/(label+'.c');part.write_text('\n'.join(function(body,x) for x in names),encoding='utf-8')
  pre=subprocess.run([str(cc),'-E','-P',str(part)],capture_output=True,timeout=30)
  if pre.returncode:raise RuntimeError('preprocessor failed')
  (out/(label+'.log')).write_bytes(pre.stdout)
 if (out/'guard-off.log').read_bytes()!=(out/'original.log').read_bytes():raise RuntimeError('guard-off preprocessed bodies differ')
 cases=[0,1,*range(10,16),*range(20,26),30,31,32,33,34]
 for case in cases:
  r=subprocess.run([str(exe),str(case)],capture_output=True,timeout=20);(out/f'case-{case}.log').write_bytes(r.stdout+r.stderr)
  if r.returncode:raise RuntimeError('guard case failed '+str(case))
 result={'passed':True,'hardware_verified':False,'source_sha256':{k:sha(v) for k,v in files.items()},'harness_sha256':sha(Path(__file__).read_bytes()),'generated_c_sha256':sha(src.read_bytes()),'log_sha256':{f.name:sha(f.read_bytes()) for f in sorted(out.glob('*.log'))},'guard_off_body_equivalent':True,'outcomes':[{'case':x,'passed':True} for x in cases]};(out/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
if __name__=='__main__':main()
