"""Run the four actual callback membership backends against bounded fixtures."""
import argparse,hashlib,json,subprocess,sys
from pathlib import Path
from test_fsys_pm_native import function
HERE=Path(__file__).resolve().parent
STUB=r'''
#include <stdio.h>
#include <stdlib.h>
#include <stddef.h>
#include <string.h>
#include <errno.h>
#define READ_ONCE(x) (x)
#define rcu_dereference_raw(x) (x)
struct list_head {struct list_head *next,*prev;};
#define list_for_each_entry(pos,head,member) for(pos=(void*)((char*)(head)->next - offsetof(__typeof__(*pos),member)); &pos->member!=(head); pos=(void*)((char*)pos->member.next - offsetof(__typeof__(*pos),member)))
struct notifier_block {struct notifier_block *next;int priority;void (*notifier_call)(void);};
static struct {int lock;struct notifier_block *head;} cpu_pm_notifier_chain;
struct irq_chip {void (*irq_suspend)(void),(*irq_resume)(void),(*irq_pm_shutdown)(void);};struct irq_chip_type {struct irq_chip chip;};
struct irq_chip_generic {void (*suspend)(void),(*resume)(void);unsigned int irq_base,num_ct,irq_cnt;unsigned long installed;void *domain;struct list_head list;struct irq_chip_type chip_types[1];};
static struct list_head gc_list;static int gc_lock;
struct clocksource {char *name;struct list_head list;void (*suspend)(void),(*resume)(void);};
static struct list_head clocksource_list;static int clocksource_mutex;static struct clocksource *curr_clocksource;
struct cpumask {unsigned long bits;};
#define cpumask_bits(p) (&(p)->bits)
struct clock_event_device {unsigned int state_use_accessors,features;int bound_on,irq;struct cpumask *cpumask;char *name;struct list_head list;void (*suspend)(void),(*resume)(void);};
static struct list_head clockevent_devices;static int clockevents_lock;
static int fail_lock,irq,preempt,locks,unlocks;
#define TRY(lock,flags) ((flags)=irq, irq=1, preempt++, fail_lock?(irq=(flags),preempt--,0):(locks++,1))
#define spin_trylock_irqsave(lock,flags) TRY(lock,flags)
#define raw_spin_trylock_irqsave(lock,flags) TRY(lock,flags)
#define spin_unlock_irqrestore(lock,flags) do{irq=(flags);preempt--;unlocks++;}while(0)
#define raw_spin_unlock_irqrestore(lock,flags) spin_unlock_irqrestore(lock,flags)
static int mutex_trylock(int *m){(void)m;if(fail_lock)return 0;locks++;return 1;}
static void mutex_unlock(int *m){(void)m;unlocks++;}
static void init(struct list_head *l){l->next=l->prev=l;}
static void add(struct list_head *h,struct list_head *n){n->next=h;n->prev=h->prev;h->prev->next=n;h->prev=n;}

'''
MAIN=r'''
static struct cpumask mask={1};static struct n10_cb_family out;static struct notifier_block nb[65];static struct irq_chip_generic gc[65];static struct clocksource cs[65];static struct clock_event_device ce[65];
static void callback(void){abort();}
#define CHECK(x) do{if(!(x)){fprintf(stderr,"line %d\n",__LINE__);return 1;}}while(0)
int main(int argc,char **argv){int family=atoi(argv[1]),mode=atoi(argv[2]),i,count,ret;struct list_head *head;init(&gc_list);init(&clocksource_list);init(&clockevent_devices);count=mode==0?0:mode==2?(family==0||family==2?32:64):mode==3?(family==0||family==2?33:65):1;
 for(i=0;i<count;i++){
  if(family==0){nb[i].priority=count-i;nb[i].notifier_call=callback;nb[i].next=i+1<count?&nb[i+1]:NULL;}
  if(family==1){gc[i].num_ct=1;gc[i].suspend=callback;add(&gc_list,&gc[i].list);}
  if(family==2){cs[i].name="clock";cs[i].suspend=callback;add(&clocksource_list,&cs[i].list);}
  if(family==3){ce[i].name="event";ce[i].cpumask=&mask;ce[i].suspend=callback;add(&clockevent_devices,&ce[i].list);}
 }
 cpu_pm_notifier_chain.head=count?&nb[0]:NULL;curr_clocksource=count?&cs[0]:NULL;
 if(mode==4){fail_lock=1;} if(mode==5&&count){if(family==2)cs[0].name=NULL;if(family==3)ce[0].cpumask=NULL;}
 if(mode==6&&count){if(family==0)nb[count-1].next=&nb[0];else {head=family==1?&gc_list:family==2?&clocksource_list:&clockevent_devices;head->prev->next=head->next;}}
 ret=family==0?n10_cb_cpu_pm(&out):family==1?n10_cb_irq(&out):family==2?n10_cb_clocksource(&out):n10_cb_clockevent(&out);
 CHECK(!irq&&!preempt);CHECK(locks==unlocks);
 if(mode==4)CHECK(ret==-EBUSY);
 else if(mode==3||mode==6)CHECK(ret==-E2BIG);
 else if(mode==5&&(family==2||family==3))CHECK(ret==-EINVAL);
 else if(mode==0&&(family==2||family==3))CHECK(ret==-EINVAL);
 else CHECK(!ret);
 return 0;}
'''
def clean(n):return '\n'.join(x for x in (HERE/n).read_text(encoding='utf-8-sig').splitlines() if not x.startswith('#include'))+'\n'
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--output',required=True);o=Path(ap.parse_args().output);o.mkdir(parents=True,exist_ok=True);src=o/'families.c';src.write_text(STUB+clean('pm_callbacks_contract.h')+function((HERE/'pm_callbacks_backend.c').read_text(encoding='utf-8'),'int n10_cb_name(')+''.join(clean('pm_callbacks_'+n+'_backend.c') for n in ('cpu_pm','irq','clocksource','clockevent'))+MAIN,encoding='utf-8');compiler=Path('host-tools/windows-build/llvm-mingw/llvm-mingw-20261006-ucrt-x86_64/bin/clang.exe') if sys.platform=='win32' else 'cc';exe=o/('families.exe' if sys.platform=='win32' else 'families');p=subprocess.run([str(compiler),'-std=gnu11','-O2',str(src),'-o',str(exe)],capture_output=True,timeout=60);(o/'compile.log').write_bytes(p.stdout+p.stderr)
 if p.returncode:raise RuntimeError(p.stderr.decode(errors='replace'))
 results=[]
 for family in range(4):
  for mode in range(7):
   p=subprocess.run([str(exe),str(family),str(mode)],capture_output=True,timeout=20);(o/f'family-{family}-{mode}.log').write_bytes(p.stdout+p.stderr);results.append({'family':family,'mode':mode,'passed':p.returncode==0})
   if p.returncode:raise RuntimeError(f'{family}/{mode}: '+p.stderr.decode(errors='replace'))
 (o/'result.json').write_text(json.dumps({'source_sha256':{n:hashlib.sha256((HERE/n).read_bytes()).hexdigest() for n in ('pm_callbacks_contract.h','pm_callbacks_backend.c','pm_callbacks_cpu_pm_backend.c','pm_callbacks_irq_backend.c','pm_callbacks_clocksource_backend.c','pm_callbacks_clockevent_backend.c')},'generated_c_sha256':hashlib.sha256(src.read_bytes()).hexdigest(),'log_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(o.glob('*.log'))},'harness_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'passed':True,'cases':len(results),'actual_backend_bodies':True,'hardware_verified':False,'outcomes':results},indent=2)+'\n',encoding='utf-8');print('family cases passed:',len(results))
if __name__=='__main__':main()
