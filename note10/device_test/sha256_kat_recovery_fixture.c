/* Only NEW scheduling connection is compiled/executed. No old KAT/recovery body. */
#include <assert.h>
#include <limits.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#define __init
#define late_initcall(fn)
#define READ_ONCE(x) (x)
#define pr_info printf
#define WQ_UNBOUND 2
#define WQ_MEM_RECLAIM 8
typedef struct { int value; } atomic_t;
#define ATOMIC_INIT(v) {v}
static int atomic_read(const atomic_t *p) { return p->value; }
static int atomic_cmpxchg(atomic_t *p, int old, int replacement)
{ int prior=p->value; if (prior==old) p->value=replacement; return prior; }
struct work_struct { int unused; };
struct delayed_work { struct work_struct work; void (*callback)(struct work_struct *); };
struct workqueue_struct { int identity; };
#define DECLARE_DELAYED_WORK(name, callback) struct delayed_work name = {{0},callback}
static unsigned long jiffies;
static unsigned long msecs_to_jiffies(unsigned int value) { return value; }
#define time_after_eq(a,b) ((long)((a)-(b)) >= 0)
enum { SYSTEM_BOOTING, SYSTEM_RUNNING, SYSTEM_RESTART };
static int system_state;
static atomic_t n10_return_requested = ATOMIC_INIT(0);
static struct workqueue_struct recovery_queue={1}, kat_queue={2};
static struct delayed_work *pending;
static int scenario, armed, allocations, queues, destroyed, kat_calls;
static int n10_arm_auto_return(void)
{ armed++; return scenario==1 ? -22 : 0; }
static struct workqueue_struct *alloc_workqueue(const char *name, unsigned int flags, int active)
{
 assert(armed==1 && !strcmp(name,"n10_sha256") && flags==(WQ_UNBOUND|WQ_MEM_RECLAIM) && active==1);
 allocations++;
 return scenario==2 ? NULL : &kat_queue;
}
static int queue_delayed_work(struct workqueue_struct *queue, struct delayed_work *work, unsigned long delay)
{
 assert(queue==&kat_queue && queue!=&recovery_queue && delay==1000);
 queues++;
 if (scenario==3 || (scenario==8 && queues==2)) return 0;
 pending=work;
 return 1;
}
static void destroy_workqueue(struct workqueue_struct *queue)
{ assert(queue==&kat_queue && !pending); destroyed++; }
static int n10_sha256_kat_init(void)
{ assert(system_state==SYSTEM_RUNNING && !n10_return_requested.value); kat_calls++; return scenario==10 ? -5 : 0; }
#include "sha256_kat_recovery_work.c"

static void tick(void)
{
 struct delayed_work *work=pending;
 assert(work);
 pending=NULL;
 work->callback(&work->work);
}
int main(int argc,char **argv)
{
 assert(argc==2);
 scenario=atoi(argv[1]);
 assert(scenario>=0 && scenario<=10);
 system_state=SYSTEM_RUNNING;
 jiffies=scenario==9 ? ULONG_MAX-30000 : 100;
 assert(n10_sha256_recovery_init()==0 && !kat_calls && armed==1);
 if (scenario==1) { assert(!allocations && !queues); goto done; }
 assert(allocations==1);
 if (scenario==2) { assert(!queues && !destroyed); goto done; }
 assert(queues==1);
 if (scenario==3) { assert(destroyed==1 && !pending); goto done; }
 if (scenario==4 || scenario==8) {
  system_state=SYSTEM_BOOTING;
  jiffies+=1000;
  tick();
  assert(!kat_calls && queues==2);
  if (scenario==8) { assert(!pending); goto done; }
  system_state=SYSTEM_RUNNING;
 }
 if (scenario==5) jiffies=n10_sha256_admission_deadline;
 if (scenario==6) n10_return_requested.value=1;
 if (scenario==7) { assert(!n10_sha256_recovery_init() && armed==1 && allocations==1 && queues==1); }
 if (scenario==9) jiffies+=1000;
 tick();
 assert(!pending && kat_calls==(scenario!=5 && scenario!=6));
 assert(!destroyed); /* Successful/finished jobs live until this diagnostic reboot. */
done:
 printf("N10NEW71 case=%d armed=%d queues=%d kat_calls=%d\n",scenario,armed,queues,kat_calls);
 return 0;
}
