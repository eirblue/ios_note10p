"""Compile extracted EHLD paths and check v48 observer lock progress on a host model."""
import argparse
import hashlib
import json
import subprocess
from pathlib import Path

from prepare_ehld_running_lock_audit import TARGET, transform, validate_transform

PRE_GETTER = 'drivers/soc/samsung/debug/note10_pm_pre_ehld_getter.c'
LOCK_GETTER = 'drivers/soc/samsung/debug/note10_ehld_lock_getter.c'
DAIF_NONIRQ = (0x000, 0x040, 0x100, 0x140, 0x200, 0x240, 0x300, 0x340)
TRANSITION_CASES = tuple(
    f'repeat-transition-daif-{bits:03x}-irq{irq}-pc{pc}'
    for bits in DAIF_NONIRQ for irq in (0, 1) for pc in (0, 3)
)
RUNTIME_CASES = (*TRANSITION_CASES, 'start-create-error', 'prior-getter-trylock-busy-match-stale')
MUTATION_CASES = (
    'mutation-remove-start-store', 'mutation-remove-stop-store', 'mutation-wrong-lock',
    'mutation-perf-api-under-lock', 'mutation-event-pointer-helper', 'mutation-duplicate-anchor',
    'mutation-move-start-store', 'mutation-move-stop-store', 'mutation-unpatched-baseline',
    'mutation-update-main-blocking', 'mutation-update-ctrl-blocking',
    'mutation-dump-main-blocking',
)
CASES = (*RUNTIME_CASES, *MUTATION_CASES)
OBSERVER_CASES = (
    'observer-update-main-busy', 'observer-dump-main-busy',
    'observer-update-ctrl-busy-continues-later-cpu',
    'observer-update-free-online-offline', 'observer-dump-free',
)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def extract_function(raw, signature):
    if raw.count(signature) != 1:
        raise ValueError('function signature must occur exactly once: ' + signature.decode())
    start = raw.index(signature)
    brace = raw.index(b'{', start)
    depth = 0
    for pos in range(brace, len(raw)):
        if raw[pos:pos + 1] == b'{':
            depth += 1
        elif raw[pos:pos + 1] == b'}':
            depth -= 1
            if depth == 0:
                return raw[start:pos + 1].decode()
    raise ValueError('unclosed function: ' + signature.decode())


def extract_functions(source_root):
    source_root = Path(source_root)
    ehld = (source_root / TARGET).read_bytes()
    prior = (source_root / PRE_GETTER).read_bytes()
    lock_getter = (source_root / LOCK_GETTER).read_bytes()
    functions = {
        'start': extract_function(ehld, b'static int exynos_ehld_start_cpu(unsigned int cpu)'),
        'stop': extract_function(ehld, b'static int exynos_ehld_stop_cpu(unsigned int cpu)'),
        'cpu_online': extract_function(ehld, b'static int exynos_ehld_cpu_online(unsigned int cpu)'),
        'cpu_predown': extract_function(ehld, b'static int exynos_ehld_cpu_predown(unsigned int cpu)'),
        'updater': extract_function(ehld, b'void exynos_ehld_event_raw_update_allcpu(void)'),
        'dumper': extract_function(ehld, b'void exynos_ehld_event_raw_dump_allcpu(void)'),
        'prior_getter': extract_function(prior, b'int n10_pre_ehld('),
        'trylock_getter': extract_function(lock_getter, b'int n10_ehld_lock_get('),
    }
    setter_signature = b'static void exynos_ehld_set_running('
    if setter_signature in ehld:
        functions['setter'] = extract_function(ehld, setter_signature)
    return functions


def check_legacy_paths(functions):
    setter, start, stop = functions['setter'], functions['start'], functions['stop']
    if any(token in setter for token in ('event', 'perf_event', 'ehld_printk', 'readq', 'readl', 'DBG_')):
        raise ValueError('running setter exceeds scalar-only boundary')
    if not (start.index('exynos_ehld_set_running(ctrl, 1);') < start.index('perf_event_enable(event);')):
        raise ValueError('start scalar store moved after event enable')
    if not (stop.index('perf_event_release_kernel(event);') < stop.index('ctrl->event = NULL;') < stop.index('exynos_ehld_set_running(ctrl, 0);')):
        raise ValueError('stop scalar store moved across event release/publication')
    if any(api in setter for api in ('perf_event_create_kernel_counter', 'perf_event_enable',
                                     'perf_event_disable', 'perf_event_release_kernel')):
        raise ValueError('perf API moved into scalar setter')
    online, predown = functions['cpu_online'], functions['cpu_predown']
    for name, fn, value in (('online', online, '1'), ('predown', predown, '0')):
        lock = 'raw_spin_lock_irqsave(&ctrl->lock, flags);'
        store = 'ctrl->ehld_running = ' + value + ';'
        unlock = 'raw_spin_unlock_irqrestore(&ctrl->lock, flags);'
        if not (lock in fn and store in fn and unlock in fn and fn.index(lock) < fn.index(store) < fn.index(unlock)):
            raise ValueError('existing CPU_PM ' + name + ' scalar store left ctrl lock')
        if any(api in fn for api in ('perf_event_create_kernel_counter', 'perf_event_enable',
                                     'perf_event_disable', 'perf_event_release_kernel')):
            raise ValueError('unexpected perf API in CPU_PM ' + name + ' callback')
    prior = functions['prior_getter']
    if 'READ_ONCE(c->ehld_running)' not in prior or 'READ_ONCE(c->event)' not in prior or 'raw_spin_lock' in prior:
        raise ValueError('v46 prior getter is no longer the explicit unlocked READ_ONCE sample')
    getter = functions['trylock_getter']
    if 'raw_spin_trylock(&ctrl->lock)' not in getter or 'row->running_valid = 0;' not in getter or 'READ_ONCE(ctrl->ehld_running)' not in getter:
        raise ValueError('v46 trylock getter/busy sentinel source differs')
    if '->event' in getter:
        raise ValueError('trylock getter must not access event pointer')
    updater = functions['updater']
    outer = 'if (!raw_spin_trylock_irqsave(&ehld_main.lock, main_flags))'
    inner = 'if (!raw_spin_trylock_irqsave(&ctrl->lock, ctrl_flags))'
    read = '!ctrl->ehld_running'
    inner_unlock = 'raw_spin_unlock_irqrestore(&ctrl->lock, ctrl_flags);'
    outer_unlock = 'raw_spin_unlock_irqrestore(&ehld_main.lock, main_flags);'
    if not (outer in updater and inner in updater and read in updater and inner_unlock in updater and outer_unlock in updater and
            updater.index(outer) < updater.index(inner) < updater.index(read) < updater.index(inner_unlock) < updater.index(outer_unlock)):
        raise ValueError('v48 updater trylock/scalar read nesting differs')
    if updater.index('if (ctrl->event)') > updater.index(inner):
        raise ValueError('updater event-presence test moved under ctrl lock')
    if 'continue;' not in updater[updater.index(inner):updater.index(read)]:
        raise ValueError('busy ctrl lock must skip this CPU before sample mutation')
    dumper = functions['dumper']
    dump_try = 'if (!raw_spin_trylock_irqsave(&ehld_main.lock, flags))'
    if dump_try not in dumper or 'raw_spin_lock_irqsave(&ehld_main.lock, flags);' in dumper:
        raise ValueError('v48 dumper main lock is not best-effort')
    if not (dumper.index(dump_try) < dumper.index('for_each_possible_cpu(cpu)') <
            dumper.index('lookup_symbol_name(') < dumper.index('raw_spin_unlock_irqrestore(&ehld_main.lock, flags);')):
        raise ValueError('v48 dumper trylock does not guard ring traversal')


def c_harness(functions):
    setter = functions['setter'].replace('ctrl->ehld_running = running;', 'observed_store(ctrl, running);')
    start, stop = functions['start'], functions['stop']
    online = functions['cpu_online'].replace('ctrl->ehld_running = 1;', 'observed_store(ctrl, 1);')
    predown = functions['cpu_predown'].replace('ctrl->ehld_running = 0;', 'observed_store(ctrl, 0);')
    return r'''#include <stdint.h>
#include <stdio.h>
#include <stdarg.h>
#include <stdlib.h>
#include <limits.h>
#include <errno.h>
typedef struct { int held; } raw_spinlock_t;
struct perf_event { int tag; };
struct perf_event_attr { int unused; };
struct perf_sample_data { int unused; };
struct pt_regs { int unused; };
struct exynos_ehld_ctrl { struct perf_event *event; int ehld_running; raw_spinlock_t lock; };
struct exynos_ehld_ctrl ehld_ctrl[4];
struct { raw_spinlock_t lock; } ehld_main;
struct notifier_block { int (*notifier_call)(struct notifier_block *, unsigned long, void *); };
struct n10_precond_row { unsigned int kind,valid; long value[2]; };
struct n10_precond_sample { unsigned int generation,count,seen; int bad,completed,error; struct n10_precond_row row[8]; };
struct n10_ehld_lock_row { unsigned int index,lock_available,running_valid; int running; };
enum { N10_PRE_EHLD=7, N10_PRECOND_CAP=8 };
static struct perf_event_attr exynos_ehld_attr;
static struct perf_event event_pool[4];
static unsigned long daif, IRQ_BIT=0x80UL;
static int pc_depth,entry_pc_depth,active_cpu,expected_store,failures;
static int create_calls,enable_calls,disable_calls,release_calls,store_calls,log_calls,lock_calls,unlock_calls;
static int create_error,force_busy,in_irq_context,read_running_context,read_running_count,read_event_count;
static unsigned int expected_generation=77;
static struct notifier_block exynos_ehld_c2_pm_nb;
static int exynos_ehld_c2_pm_notifier(struct notifier_block *n,unsigned long action,void *data) {(void)n;(void)action;(void)data;return 0;}
static void exynos_ehld_callback(struct perf_event *event,struct perf_sample_data *data,struct pt_regs *regs) {(void)event;(void)data;(void)regs;}
static struct exynos_ehld_ctrl *per_cpu_ptr(void *p,unsigned int cpu) { return ((struct exynos_ehld_ctrl *)p)+cpu; }
static struct exynos_ehld_ctrl *this_cpu_ptr(void *p) { return ((struct exynos_ehld_ctrl *)p)+active_cpu; }
static void read_once_check(const volatile void *address) {
  if (address==(const volatile void *)&ehld_ctrl[active_cpu].ehld_running) {
    read_running_count++;
    if (read_running_context==1 && ehld_ctrl[active_cpu].lock.held) failures++;
    if (read_running_context==2 && !ehld_ctrl[active_cpu].lock.held) failures++;
  }
  if (address==(const volatile void *)&ehld_ctrl[active_cpu].event) {
    read_event_count++;
    if (ehld_ctrl[active_cpu].lock.held) failures++;
  }
}
#define READ_ONCE(x) (read_once_check((const volatile void *)&(x)),(x))
#define IS_ERR(p) ((uintptr_t)(p) > UINTPTR_MAX-4096)
#define PTR_ERR(p) (-1)
static int in_interrupt(void) { return in_irq_context; }
static int n10_pre_context(unsigned int gen,unsigned int seen,unsigned int count) {
  (void)seen;(void)count;return gen==expected_generation;
}
static void lock_irqsave(raw_spinlock_t *lock,unsigned long *flags) {
  if (lock->held) failures++;
  *flags=daif; daif|=IRQ_BIT; lock->held=1;pc_depth++;lock_calls++;
  if (pc_depth!=entry_pc_depth+1) failures++;
}
static void unlock_irqrestore(raw_spinlock_t *lock,unsigned long flags) {
  if (!lock->held || pc_depth!=entry_pc_depth+1 || !(daif&IRQ_BIT)) failures++;
  lock->held=0;pc_depth--;unlock_calls++;daif=flags;
  if (pc_depth!=entry_pc_depth || daif!=flags) failures++;
}
#define raw_spin_lock_irqsave(l,f) lock_irqsave((raw_spinlock_t *)(l),&(f))
#define raw_spin_unlock_irqrestore(l,f) unlock_irqrestore((raw_spinlock_t *)(l),(f))
static int raw_spin_trylock(raw_spinlock_t *lock) {
  if (force_busy || lock->held) return 0;
  lock->held=1;lock_calls++;return 1;
}
static void raw_spin_unlock(raw_spinlock_t *lock) {
  if (!lock->held) failures++;
  lock->held=0;unlock_calls++;
}
static void observed_store(struct exynos_ehld_ctrl *ctrl,int value) {
  if (ctrl!=&ehld_ctrl[active_cpu] || !ctrl->lock.held || ehld_main.lock.held || !(daif&IRQ_BIT) || pc_depth!=entry_pc_depth+1) failures++;
  if (value!=expected_store) failures++;
  ctrl->ehld_running=value;store_calls++;
}
static struct perf_event *perf_event_create_kernel_counter(struct perf_event_attr *a,int cpu,void *task,
    void (*cb)(struct perf_event *,struct perf_sample_data *,struct pt_regs *),void *ctx) {
  (void)a;(void)task;(void)cb;(void)ctx;create_calls++;
  if (ehld_ctrl[active_cpu].lock.held || ehld_main.lock.held || cpu!=(int)active_cpu) failures++;
  if (create_error)return (struct perf_event *)(intptr_t)-1;
  return &event_pool[cpu];
}
static void perf_event_enable(struct perf_event *event) {
  enable_calls++;if(ehld_ctrl[active_cpu].lock.held || ehld_main.lock.held || !event || ehld_ctrl[active_cpu].event!=event || ehld_ctrl[active_cpu].ehld_running!=1 || store_calls<1)failures++;
}
static void perf_event_disable(struct perf_event *event) {
  disable_calls++;if(ehld_ctrl[active_cpu].lock.held || ehld_main.lock.held || !event || ehld_ctrl[active_cpu].ehld_running!=1)failures++;
}
static void perf_event_release_kernel(struct perf_event *event) {
  release_calls++;if(ehld_ctrl[active_cpu].lock.held || ehld_main.lock.held || !event || ehld_ctrl[active_cpu].event!=event || ehld_ctrl[active_cpu].ehld_running!=1)failures++;
}
static void ehld_printk(int level,const char *fmt,...) {(void)level;(void)fmt;log_calls++;if(ehld_ctrl[active_cpu].lock.held || ehld_main.lock.held)failures++;}
''' + setter + '\n' + start + '\n' + stop + '\n' + online + '\n' + predown + '\n' + functions['prior_getter'] + '\n' + functions['trylock_getter'] + r'''
static int run_transitions(unsigned long nonirq,int irqoff,int pc) {
  int n; unsigned long initial=nonirq|(irqoff?IRQ_BIT:0); active_cpu=0;daif=initial;entry_pc_depth=pc;pc_depth=pc;expected_store=1;
  ehld_ctrl[0].event=0;ehld_ctrl[0].ehld_running=0;
  for(n=0;n<2;n++) {
    if(exynos_ehld_start_cpu(0) || daif!=initial || pc_depth!=pc || !ehld_ctrl[0].event || ehld_ctrl[0].ehld_running!=1) return 1;
    expected_store=0;
    if(exynos_ehld_stop_cpu(0) || daif!=initial || pc_depth!=pc || ehld_ctrl[0].event || ehld_ctrl[0].ehld_running!=0) return 2;
    expected_store=1;
  }
  if(create_calls!=2 || enable_calls!=2 || disable_calls!=2 || release_calls!=2 || store_calls!=4 || lock_calls!=4 || unlock_calls!=4 || ehld_ctrl[0].lock.held || ehld_main.lock.held) return 3;
  return 0;
}
static int run_create_error(void) {
  active_cpu=0;entry_pc_depth=0;pc_depth=0;daif=0x145;expected_store=1;create_error=1;
  if(exynos_ehld_start_cpu(0)!=-1 || create_calls!=1 || store_calls || enable_calls || ehld_ctrl[0].event || ehld_ctrl[0].ehld_running || daif!=0x145 || pc_depth) return 1;
  return 0;
}
static int run_getters(void) {
  struct n10_precond_row prior={0};struct n10_precond_sample pre={0};struct n10_ehld_lock_row row={0};int rc;
  active_cpu=0;in_irq_context=0;ehld_ctrl[0].event=&event_pool[0];ehld_ctrl[0].ehld_running=1;read_running_context=1;
  exynos_ehld_c2_pm_nb.notifier_call=exynos_ehld_c2_pm_notifier;
  if(n10_pre_ehld(&exynos_ehld_c2_pm_nb,&prior)!=1 || prior.valid!=3 || prior.value[0]!=1 || prior.value[1]!=1 || ehld_ctrl[0].lock.held || read_running_count!=1 || read_event_count!=1) return 1;
  prior.kind=N10_PRE_EHLD;pre.generation=expected_generation;pre.count=1;pre.seen=1;pre.row[0]=prior;row.index=0;read_running_context=2;force_busy=1;
  rc=n10_ehld_lock_get(&row,&exynos_ehld_c2_pm_nb,&pre,0,expected_generation);
  if(rc || row.lock_available!=0 || row.running_valid!=0 || row.running!=0 || ehld_ctrl[0].lock.held || read_running_count!=1) return 2;
  force_busy=0;row=(struct n10_ehld_lock_row){.index=0};
  rc=n10_ehld_lock_get(&row,&exynos_ehld_c2_pm_nb,&pre,0,expected_generation);
  if(rc || row.lock_available!=1 || row.running_valid!=1 || row.running!=1 || ehld_ctrl[0].lock.held) return 3;
  pre.row[0].value[0]=0;row=(struct n10_ehld_lock_row){.index=0};
  rc=n10_ehld_lock_get(&row,&exynos_ehld_c2_pm_nb,&pre,0,expected_generation);
  if(rc!=-EIO || ehld_ctrl[0].lock.held || row.lock_available || row.running_valid) return 4;
  if(read_event_count!=1 || failures) return 5;
  return 0;
}
int main(int argc,char **argv) {
  int mode=argc>1?atoi(argv[1]):-1,rc;
  if(mode==0) { static const unsigned long masks[8]={0x000,0x040,0x100,0x140,0x200,0x240,0x300,0x340};int mi=atoi(argv[2]),irq=atoi(argv[3]),pc=atoi(argv[4]);rc=run_transitions(masks[mi],irq,pc); }
  else if(mode==1) rc=run_create_error();
  else if(mode==2) rc=run_getters();
  else return 9;
  if(rc || failures || pc_depth!=entry_pc_depth || ehld_ctrl[active_cpu].lock.held || ehld_main.lock.held) {printf("FAIL rc=%d failures=%d daif=%lx pc=%d stores=%d reads=%d/%d\n",rc,failures,daif,pc_depth,store_calls,read_running_count,read_event_count);return 1;}
  printf("PASS mode=%d daif=%lx pc=%d stores=%d locks=%d/%d reads=%d/%d\n",mode,daif,pc_depth,store_calls,lock_calls,unlock_calls,read_running_count,read_event_count);return 0;
}
'''


def observer_c_harness(functions):
    """Compile and run the actual v48 updater/dumper bodies with bounded lock stubs."""
    updater = functions['updater']
    dumper = functions['dumper']
    return r'''#include <stdint.h>
#include <stdio.h>
#include <stdarg.h>
#include <string.h>
#include <stdlib.h>
#include <stdbool.h>
#define NUM_CPUS 2
#define NUM_TRACE 4
#define KSYM_NAME_LEN 16
#define IRQ_BIT 0x80UL
#define PMU_OFFSET 0x10UL
#define PMUPCSR 0x20UL
#define MSB_MASKING (1ULL<<55)
#define MSB_PADDING (1ULL<<55)
#define __iomem
typedef struct { int held; } raw_spinlock_t;
struct perf_event { int id; };
struct exynos_ehld_data { unsigned long data_ptr; unsigned long long time[NUM_TRACE]; unsigned int event[NUM_TRACE]; unsigned long long pmpcsr[NUM_TRACE]; };
struct exynos_ehld_ctrl { struct perf_event *event; struct exynos_ehld_data data; unsigned char *dbg_base; int ehld_running; raw_spinlock_t lock; };
static struct exynos_ehld_ctrl ehld_ctrl[NUM_CPUS];
static struct { raw_spinlock_t lock; } ehld_main;
static unsigned char mmio[NUM_CPUS][128];
static unsigned long irq_state, entry_irq, preempt_depth, entry_preempt;
static int offline[NUM_CPUS], power[NUM_CPUS], q_reads, l_reads, dbg_unlocks, dbg_locks;
static int logs, lookups, failures, clock_reads;
struct { int (*power_state)(int); } exynos_cpu;
static int power_state(int cpu) { return power[cpu]; }
static int dbg_snapshot_get_sjtag_status(void) { return 0; }
static int cpu_is_offline(int cpu) { return offline[cpu]; }
static unsigned long long cpu_clock(int cpu) { clock_reads++; return 1000ULL+(unsigned long long)cpu; }
static int trylock_irqsave(raw_spinlock_t *lock, unsigned long *flags) {
  *flags=irq_state; irq_state|=IRQ_BIT;
  if (lock->held) { irq_state=*flags; return 0; }
  lock->held=1; preempt_depth++; return 1;
}
static void unlock_irqrestore(raw_spinlock_t *lock, unsigned long flags) {
  if (!lock->held || preempt_depth<=entry_preempt || !(irq_state&IRQ_BIT)) failures++;
  lock->held=0; preempt_depth--; irq_state=flags;
}
#define raw_spin_trylock_irqsave(l,f) trylock_irqsave((raw_spinlock_t *)(l), &(f))
#define raw_spin_unlock_irqrestore(l,f) unlock_irqrestore((raw_spinlock_t *)(l), (f))
#define for_each_possible_cpu(cpu) for ((cpu)=0; (cpu)<NUM_CPUS; (cpu)++)
#define per_cpu_ptr(base,cpu) (&ehld_ctrl[(cpu)])
#define DBG_UNLOCK(addr) do { (void)(addr); dbg_unlocks++; } while (0)
#define DBG_LOCK(addr) do { (void)(addr); dbg_locks++; } while (0)
static unsigned long long __raw_readq(void *address) { (void)address; q_reads++; return 0x123456789ULL; }
static unsigned int __raw_readl(void *address) { (void)address; l_reads++; return 0x55U; }
static int lookup_symbol_name(unsigned long long address,char *name) { (void)address; lookups++; strcpy(name,"sample"); return 0; }
static int ehld_printk(int level,const char *format,...) { (void)level; (void)format; logs++; return 0; }
''' + updater + '\n' + dumper + r'''
static void reset(unsigned long initial_irq) {
  int cpu;
  memset(ehld_ctrl,0,sizeof(ehld_ctrl)); memset(&ehld_main,0,sizeof(ehld_main));
  memset(offline,0,sizeof(offline)); memset(power,0,sizeof(power));
  memset(mmio,0,sizeof(mmio)); q_reads=l_reads=dbg_unlocks=dbg_locks=logs=lookups=failures=clock_reads=0;
  irq_state=initial_irq; entry_irq=initial_irq; entry_preempt=preempt_depth=2;
  exynos_cpu.power_state=power_state;
  for(cpu=0;cpu<NUM_CPUS;cpu++) ehld_ctrl[cpu].dbg_base=mmio[cpu];
}
static int clean_exit(void) {
  if (irq_state!=entry_irq || preempt_depth!=entry_preempt || ehld_main.lock.held) failures++;
  return failures ? 1 : 0;
}
static int busy_update_main(void) {
  unsigned long before[NUM_CPUS]; int cpu;
  reset(0x340UL|IRQ_BIT);
  for(cpu=0;cpu<NUM_CPUS;cpu++) { ehld_ctrl[cpu].event=(struct perf_event *)(uintptr_t)(cpu+1); before[cpu]=ehld_ctrl[cpu].data.data_ptr; }
  ehld_main.lock.held=1;
  exynos_ehld_event_raw_update_allcpu();
  if(!ehld_main.lock.held || logs || q_reads || l_reads || dbg_unlocks || dbg_locks || clock_reads) failures++;
  for(cpu=0;cpu<NUM_CPUS;cpu++) {
    struct exynos_ehld_data *data=&ehld_ctrl[cpu].data; unsigned int i;
    if(data->data_ptr!=before[cpu]) failures++;
    for(i=0;i<NUM_TRACE;i++) if(data->time[i] || data->event[i] || data->pmpcsr[i]) failures++;
  }
  ehld_main.lock.held=0;
  return clean_exit();
}
static int busy_dump_main(void) {
  unsigned long before[NUM_CPUS]; int cpu;
  reset(0x240UL);
  for(cpu=0;cpu<NUM_CPUS;cpu++) { ehld_ctrl[cpu].data.data_ptr=cpu+1; before[cpu]=ehld_ctrl[cpu].data.data_ptr; }
  ehld_main.lock.held=1;
  exynos_ehld_event_raw_dump_allcpu();
  if(!ehld_main.lock.held || logs || lookups || q_reads || l_reads || dbg_unlocks || dbg_locks) failures++;
  for(cpu=0;cpu<NUM_CPUS;cpu++) if(ehld_ctrl[cpu].data.data_ptr!=before[cpu]) failures++;
  ehld_main.lock.held=0;
  return clean_exit();
}
static int busy_ctrl_later_cpu(void) {
  reset(0x340UL|IRQ_BIT);
  ehld_ctrl[0].event=(struct perf_event *)(uintptr_t)1; ehld_ctrl[0].lock.held=1;
  ehld_ctrl[1].event=(struct perf_event *)(uintptr_t)2; power[1]=1; ehld_ctrl[1].ehld_running=1;
  exynos_ehld_event_raw_update_allcpu();
  if(ehld_ctrl[0].data.data_ptr!=0 || !ehld_ctrl[0].lock.held || ehld_ctrl[1].data.data_ptr!=1 ||
     ehld_ctrl[1].data.event[1]!=0x55U || q_reads!=1 || l_reads!=1 || logs!=2 || clock_reads!=1) failures++;
  if(ehld_ctrl[0].data.time[0] || ehld_ctrl[0].data.event[0] || ehld_ctrl[0].data.pmpcsr[0]) failures++;
  ehld_ctrl[0].lock.held=0;
  return clean_exit();
}
static int free_update_online_offline(void) {
  reset(0x200UL);
  ehld_ctrl[0].event=(struct perf_event *)(uintptr_t)1; power[0]=1; ehld_ctrl[0].ehld_running=1;
  ehld_ctrl[1].event=(struct perf_event *)(uintptr_t)2; offline[1]=1; power[1]=0;
  exynos_ehld_event_raw_update_allcpu();
  if(ehld_ctrl[0].data.data_ptr!=1 || ehld_ctrl[1].data.data_ptr!=1 ||
     ehld_ctrl[0].data.event[1]!=0x55U || ehld_ctrl[1].data.event[1]!=0xC2U ||
     q_reads!=1 || l_reads!=1 || dbg_unlocks!=1 || dbg_locks!=1 || logs!=4 || clock_reads!=2) failures++;
  return clean_exit();
}
static int free_dump(void) {
  reset(0x340UL|IRQ_BIT);
  exynos_ehld_event_raw_dump_allcpu();
  if(ehld_ctrl[0].data.data_ptr!=NUM_TRACE || ehld_ctrl[1].data.data_ptr!=NUM_TRACE ||
     logs!=1+NUM_CPUS*(NUM_TRACE+1) || lookups!=NUM_CPUS*NUM_TRACE || q_reads || l_reads) failures++;
  return clean_exit();
}
int main(int argc,char **argv) {
  int mode=argc>1?atoi(argv[1]):-1,rc;
  if(mode==0) rc=busy_update_main();
  else if(mode==1) rc=busy_dump_main();
  else if(mode==2) rc=busy_ctrl_later_cpu();
  else if(mode==3) rc=free_update_online_offline();
  else if(mode==4) rc=free_dump();
  else return 9;
  if(rc || clean_exit()) { printf("FAIL mode=%d failures=%d irq=%lx pc=%lu logs=%d mmio=%d/%d\n",mode,failures,irq_state,preempt_depth,logs,q_reads,l_reads); return 1; }
  printf("PASS mode=%d irq=%lx pc=%lu logs=%d mmio=%d/%d\n",mode,irq_state,preempt_depth,logs,q_reads,l_reads); return 0;
}
'''


def _mutation_rejections(baseline, patched):
    validate_transform(baseline, patched)
    def replace_once(raw, name, old, new):
        if raw.count(old) != 1:
            raise ValueError('mutation anchor must occur once: ' + name)
        return raw.replace(old, new, 1)

    def mutated(name, old, new):
        return replace_once(patched, name, old, new)

    def in_function(name, signature, old, new):
        if patched.count(signature) != 1:
            raise ValueError('mutation function must occur once: ' + name)
        start = patched.index(signature)
        brace = patched.index(b'{', start)
        depth = 0
        end = None
        for pos in range(brace, len(patched)):
            if patched[pos:pos + 1] == b'{':
                depth += 1
            elif patched[pos:pos + 1] == b'}':
                depth -= 1
                if depth == 0:
                    end = pos + 1
                    break
        if end is None:
            raise ValueError('mutation function is unterminated: ' + name)
        function = replace_once(patched[start:end], name, old, new)
        return patched[:start] + function + patched[end:]

    mutations = {
        'mutation-remove-start-store': mutated('start-store', b'exynos_ehld_set_running(ctrl, 1);', b'ctrl->ehld_running = 1;'),
        'mutation-remove-stop-store': mutated('stop-store', b'exynos_ehld_set_running(ctrl, 0);', b'ctrl->ehld_running = 0;'),
        'mutation-wrong-lock': in_function('wrong-lock', b'static void exynos_ehld_set_running(', b'raw_spin_lock_irqsave(&ctrl->lock, flags);', b'raw_spin_lock_irqsave(&ehld_main.lock, flags);'),
        'mutation-perf-api-under-lock': in_function('perf-api', b'static void exynos_ehld_set_running(', b'ctrl->ehld_running = running;', b'perf_event_enable(event);\n\tctrl->ehld_running = running;'),
        'mutation-event-pointer-helper': in_function('event-pointer', b'static void exynos_ehld_set_running(', b'ctrl->ehld_running = running;', b'if (READ_ONCE(ctrl->event)) ctrl->ehld_running = running;'),
        'mutation-move-start-store': mutated('start-order', b'\t\texynos_ehld_set_running(ctrl, 1);\n\t\tperf_event_enable(event);', b'\t\tperf_event_enable(event);\n\t\texynos_ehld_set_running(ctrl, 1);'),
        'mutation-move-stop-store': mutated('stop-order', b'\t\tperf_event_release_kernel(event);\n\t\tctrl->event = NULL;\n\t\texynos_ehld_set_running(ctrl, 0);', b'\t\texynos_ehld_set_running(ctrl, 0);\n\t\tperf_event_release_kernel(event);\n\t\tctrl->event = NULL;'),
        'mutation-update-main-blocking': mutated('updater-main', b'if (!raw_spin_trylock_irqsave(&ehld_main.lock, main_flags))\n\t\treturn;', b'raw_spin_lock_irqsave(&ehld_main.lock, main_flags);'),
        'mutation-update-ctrl-blocking': mutated('updater-ctrl', b'if (!raw_spin_trylock_irqsave(&ctrl->lock, ctrl_flags))\n\t\t\t\tcontinue;', b'raw_spin_lock_irqsave(&ctrl->lock, ctrl_flags);'),
        'mutation-dump-main-blocking': mutated('dumper-main', b'if (!raw_spin_trylock_irqsave(&ehld_main.lock, flags))\n\t\treturn;', b'raw_spin_lock_irqsave(&ehld_main.lock, flags);'),
    }
    rows = []
    for name, mutant in mutations.items():
        try:
            validate_transform(baseline, mutant)
        except ValueError:
            rejected = True
        else:
            rejected = False
        if not rejected:
            raise ValueError('production source reconstruction accepted mutation: ' + name)
        rows.append({'case': name, 'accepted': False, 'production_reconstruction_rejected': True,
                     'mutated_source_sha256': sha(mutant)})
    duplicate = baseline + b'\nstatic int exynos_ehld_start_cpu(unsigned int cpu) { return 0; }\n'
    try:
        validate_transform(duplicate, patched)
    except ValueError:
        rows.append({'case': 'mutation-duplicate-anchor', 'accepted': False,
                     'production_reconstruction_rejected': True, 'mutated_source_sha256': sha(duplicate)})
    else:
        raise ValueError('production source transform accepted duplicate anchor')
    try:
        validate_transform(baseline, baseline)
    except ValueError:
        rows.append({'case': 'mutation-unpatched-baseline', 'accepted': False,
                     'production_reconstruction_rejected': True, 'mutated_source_sha256': sha(baseline)})
    else:
        raise ValueError('production source transform accepted the unpatched v46 baseline')
    return rows


def _run_observer(source_root, output, cc):
    source_root, output = Path(source_root), Path(output)
    functions = extract_functions(source_root)
    code = observer_c_harness(functions)
    model = output / 'observer-model'
    model.mkdir()
    src, exe = model / 'observer_harness.c', model / 'observer_harness.exe'
    src.write_text(code, encoding='utf8', newline='\n')
    compile_result = subprocess.run(
        [cc, '-std=gnu11', '-Werror', '-O0', str(src), '-o', str(exe)],
        capture_output=True, text=True,
    )
    (model / 'compile.log').write_text(
        compile_result.stdout + compile_result.stderr, encoding='utf8', newline='\n')
    if compile_result.returncode:
        raise RuntimeError('observer native harness compile failed: ' + compile_result.stderr)
    generated_sha = sha(src.read_bytes())
    case_results, log_hashes = [], {}
    expected = {
        'observer-update-main-busy': (0, 'PASS mode=0 irq=3c0 pc=2 logs=0 mmio=0/0\n'),
        'observer-dump-main-busy': (1, 'PASS mode=1 irq=240 pc=2 logs=0 mmio=0/0\n'),
        'observer-update-ctrl-busy-continues-later-cpu': (2, 'PASS mode=2 irq=3c0 pc=2 logs=2 mmio=1/1\n'),
        'observer-update-free-online-offline': (3, 'PASS mode=3 irq=200 pc=2 logs=4 mmio=1/1\n'),
        'observer-dump-free': (4, 'PASS mode=4 irq=3c0 pc=2 logs=11 mmio=0/0\n'),
    }
    for name in OBSERVER_CASES:
        mode, expected_stdout = expected[name]
        process = subprocess.run([str(exe), str(mode)], capture_output=True, text=True)
        log = 'COMPILE\nreturncode=0\nRUN\n' + process.stdout + process.stderr
        path = model / (name + '.log')
        path.write_text(log, encoding='utf8', newline='\n')
        if process.returncode or process.stdout != expected_stdout or process.stderr:
            raise RuntimeError(name + ' observer runtime failed: ' + process.stdout + process.stderr)
        log_hashes[name] = sha(path.read_bytes())
        case_results.append({
            'case': name, 'accepted': True, 'compile_returncode': 0,
            'returncode': process.returncode, 'generated_sha256': generated_sha,
            'log_sha256': log_hashes[name], 'expected_stdout': expected_stdout,
        })
    observer = {
        'schema_version': 1, 'passed': True, 'hardware_verified': False,
        'cases': list(OBSERVER_CASES), 'case_results': case_results,
        'generated_sha256': generated_sha,
        'binary_sha256': sha(exe.read_bytes()),
        'harness_sha256': sha(Path(__file__).read_bytes()),
        'compile_log_sha256': sha((model / 'compile.log').read_bytes()),
        'logs_sha256': log_hashes,
        'source_sha256': sha((source_root / TARGET).read_bytes()),
        'source_function_sha256': {
            name: sha(functions[name].encode('utf8')) for name in ('updater', 'dumper')
        },
    }
    (model / 'result.json').write_text(
        json.dumps(observer, indent=2) + '\n', encoding='utf8', newline='\n')
    return observer


def run(source_root, baseline_source, output, cc):
    source_root, baseline_source, output = map(Path, (source_root, baseline_source, output))
    output.mkdir(parents=True, exist_ok=False)
    baseline_target = (baseline_source / TARGET).read_bytes()
    patched_target = (source_root / TARGET).read_bytes()
    if transform(baseline_target) != patched_target:
        raise ValueError('v48 source differs from exact transform of actual v46 source')
    source_inputs = (TARGET, PRE_GETTER, LOCK_GETTER)
    source_hashes = {name: sha((source_root / name).read_bytes()) for name in source_inputs}
    if (source_root / PRE_GETTER).read_bytes() != (baseline_source / PRE_GETTER).read_bytes() or (source_root / LOCK_GETTER).read_bytes() != (baseline_source / LOCK_GETTER).read_bytes():
        raise ValueError('v46 getter source changed in v48 snapshot')
    functions = extract_functions(source_root)
    baseline_functions = extract_functions(baseline_source)
    unchanged_functions = ('cpu_online', 'cpu_predown', 'prior_getter', 'trylock_getter')
    for name in unchanged_functions:
        if functions[name] != baseline_functions[name]:
            raise ValueError('v48 changed immutable legacy function: ' + name)
    check_legacy_paths(functions)
    code = c_harness(functions)
    src, exe = output / 'running_lock_model.c', output / 'running_lock_model.exe'
    src.write_text(code, encoding='utf8', newline='\n')
    compile_result = subprocess.run([cc, '-std=gnu11', '-Werror', '-Wno-pointer-to-int-cast', '-O0', str(src), '-o', str(exe)], capture_output=True, text=True)
    (output / 'compile.log').write_text(compile_result.stdout + compile_result.stderr, encoding='utf8', newline='\n')
    if compile_result.returncode:
        raise RuntimeError('native harness compile failed: ' + compile_result.stderr)
    generated_sha = sha(src.read_bytes())
    compile_log_sha = sha((output / 'compile.log').read_bytes())
    case_results, log_hashes = [], {}
    for mask_index, bits in enumerate(DAIF_NONIRQ):
        for irq in (0, 1):
            for pc in (0, 3):
                name = f'repeat-transition-daif-{bits:03x}-irq{irq}-pc{pc}'
                process = subprocess.run([str(exe), '0', str(mask_index), str(irq), str(pc)], capture_output=True, text=True)
                log = 'COMPILE\nreturncode=0\nRUN\n' + process.stdout + process.stderr
                path = output / (name + '.log')
                path.write_text(log, encoding='utf8', newline='\n')
                if process.returncode:
                    raise RuntimeError(name + ' runtime failed: ' + process.stdout + process.stderr)
                log_hashes[name] = sha(path.read_bytes())
                case_results.append({'case': name, 'accepted': True, 'compile_returncode': 0,
                                     'returncode': process.returncode, 'generated_sha256': generated_sha,
                                     'log_sha256': log_hashes[name], 'irq_entry': irq, 'nonirq_daif': bits,
                                     'preempt_entry_depth': pc, 'expected_stdout': process.stdout})
    for name, mode in (('start-create-error', '1'), ('prior-getter-trylock-busy-match-stale', '2')):
        process = subprocess.run([str(exe), mode], capture_output=True, text=True)
        path = output / (name + '.log')
        path.write_text('COMPILE\nreturncode=0\nRUN\n' + process.stdout + process.stderr, encoding='utf8', newline='\n')
        if process.returncode:
            raise RuntimeError(name + ' runtime failed: ' + process.stdout + process.stderr)
        log_hashes[name] = sha(path.read_bytes())
        case_results.append({'case': name, 'accepted': True, 'compile_returncode': 0,
                             'returncode': process.returncode, 'generated_sha256': generated_sha,
                             'log_sha256': log_hashes[name], 'expected_stdout': process.stdout})
    mutation_rows = _mutation_rejections(baseline_target, patched_target)
    case_results.extend(mutation_rows)
    for row in mutation_rows:
        name = row['case']
        path = output / (name + '.log')
        path.write_text('REJECT\nproduction reconstruction mismatch\n', encoding='utf8', newline='\n')
        row['log_sha256'] = sha(path.read_bytes())
        log_hashes[name] = row['log_sha256']
    proof = {
        'schema_version': 2, 'passed': True, 'hardware_verified': False,
        'cases': list(CASES), 'runtime_cases': list(RUNTIME_CASES),
        'case_results': case_results,
        'generated_sha256': {name: generated_sha for name in RUNTIME_CASES},
        'compile_log_sha256': compile_log_sha, 'logs_sha256': log_hashes,
        'harness_sha256': sha(Path(__file__).read_bytes()),
        'source_inputs_sha256': source_hashes,
        'source_function_sha256': {name: sha(value.encode()) for name, value in functions.items()},
        'baseline_unchanged_function_sha256': {name: sha(baseline_functions[name].encode()) for name in unchanged_functions},
        'legacy_function_inventory': {
            'cpu_pm_online': 'cpu_online', 'cpu_pm_predown': 'cpu_predown',
            'prior_unlocked_getter': 'prior_getter', 'trylock_getter': 'trylock_getter',
            'main_then_ctrl_updater': 'updater',
        },
        'baseline_source_sha256': sha(baseline_target), 'patched_source_sha256': sha(patched_target),
        'legacy_path_inventory': {
            'cpu_pm_online_locked': True, 'cpu_pm_predown_locked': True,
            'prior_getter_unlocked_read_once': True, 'trylock_getter_busy_sentinel_no_event_access': True,
            'updater_main_then_ctrl_trylocked_running_read': True,
            'dumper_main_trylocked': True,
            'cpu_pm_callbacks_invoked': False, 'updater_invoked': False,
            'event_pointer_dereferenced': False,
        },
        'mutation_results': mutation_rows,
        'observer': _run_observer(source_root, output, cc),
    }
    (output / 'result.json').write_text(json.dumps(proof, indent=2) + '\n', encoding='utf8', newline='\n')
    return proof


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--source-root', type=Path, required=True)
    parser.add_argument('--baseline-source', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--cc', required=True)
    args = parser.parse_args()
    print(json.dumps(run(args.source_root, args.baseline_source, args.output, args.cc), sort_keys=True))
