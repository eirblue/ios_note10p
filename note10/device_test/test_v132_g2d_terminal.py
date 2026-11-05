"""One NEW G2D provider/admission/lifetime batch; accepted131 tests are retained."""
import argparse
import base64
import json
from pathlib import Path
import re
import subprocess
from v130_contract import ROOT,ordinary,private,read,save,sha,hexid
from v132_build import source_pins,continuation,NEW_FILES,SCOPE,RETAINED_COMMIT,SETTINGS
import v132_prepare as prepare


def function(raw,name):
    matches=list(re.finditer(r'(?m)^(?:static )?(?:inline )?(?:int|void|bool|u32) '+re.escape(name)+r'\([^)]*\)\n\{',raw))
    if len(matches)!=1:raise ValueError('unique actual G2D function required: '+name)
    start=matches[0].start();at=raw.index('{',start)+1;depth=1
    while depth and at<len(raw):depth+=(raw[at]=='{')-(raw[at]=='}');at+=1
    if depth:raise ValueError('actual G2D function closing boundary missing')
    return raw[start:at]+'\n'


def macro(raw,name):
    rows=[line for line in raw.splitlines() if line.startswith('#define '+name) and
        line[len('#define '+name):len('#define '+name)+1] in ('(',' ','\t')]
    if len(rows)!=1:raise ValueError('actual G2D macro differs: '+name)
    return rows[0]+'\n'


def without_includes(raw):return '\n'.join(line for line in raw.splitlines() if not line.startswith('#include'))+'\n'


def fixture(rendered,stock):
    header=rendered['drivers/gpu/exynos/g2d/g2d.h'].decode()
    task_header=stock['drivers/gpu/exynos/g2d/g2d_task.h'].decode()
    regs=stock['drivers/gpu/exynos/g2d/g2d_regs.h'].decode()
    task_source=rendered['drivers/gpu/exynos/g2d/g2d_task.c'].decode()
    driver=rendered['drivers/gpu/exynos/g2d/g2d_drv.c'].decode()
    kernel=rendered['arch/arm64/mm/v130_kernel.c'].decode()
    enums=re.findall(r'enum n130_return_phase\s*\{[^}]+\};',kernel)
    if len(enums)!=1:raise ValueError('actual retained phase enum differs')
    constants=''.join(macro(raw,name) for raw,name in (
        (header,'G2D_DEVICE_STATE_SUSPEND'),(header,'G2D_DEVICE_STATE_IOVMM_DISABLED'),
        (task_header,'G2D_MAX_JOBS'),(task_header,'is_task_state_idle'),
        (regs,'G2D_FIFO_STAT_REG'),(regs,'G2D_JOB_ID0_STATE_REG'),(regs,'G2D_JOB_IDn_STATE_REG'),
        (regs,'G2D_JOB_STATE_DONE'),(regs,'G2D_JOB_STATE_RUNNING'),(regs,'G2D_JOB_STATE_MASK')))
    includes=r'''#include <assert.h>
#include <errno.h>
#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdio.h>
#include <string.h>
#include <stdarg.h>
'''
    prefix=r'''typedef uint32_t u32;
#define N10_KEXEC_BUILD_ID "0123456789abcdef0123456789abcdef"
#define READ_ONCE(x) (x)
#define WRITE_ONCE(x,v) ((x)=(v))
#define ARRAY_SIZE(x) (sizeof(x)/sizeof((x)[0]))
#define IS_ERR_OR_NULL(p) (!(p))
typedef struct {int held;} spinlock_t;
static void lock(spinlock_t *p){assert(!p->held);p->held=1;}
static void unlock(spinlock_t *p){assert(p->held);p->held=0;}
#define DEFINE_SPINLOCK(n) spinlock_t n={0}
#define spin_lock_irqsave(p,f) do{(f)=0;lock(p);}while(0)
#define spin_unlock_irqrestore(p,f) do{(void)(f);unlock(p);}while(0)
#define spin_lock_irq(p) lock(p)
#define spin_unlock_irq(p) unlock(p)
static int test_bit(unsigned int bit,const unsigned long *p){return !!(*p&(1UL<<bit));}
static void set_bit(unsigned int bit,unsigned long *p){*p|=1UL<<bit;}
static void clear_bit(unsigned int bit,unsigned long *p){*p&=~(1UL<<bit);}
static int test_and_set_bit(unsigned int bit,unsigned long *p){int old=test_bit(bit,p);set_bit(bit,p);return old;}
struct list_head {struct list_head *next,*prev;};
static void init_list(struct list_head *p){p->next=p->prev=p;}
static void add(struct list_head *h,struct list_head *n){n->next=h;n->prev=h->prev;h->prev->next=n;h->prev=n;}
#define list_empty(p) ((p)->next==(p))
#define container_of(p,t,m) ((t *)((char *)(p)-offsetof(t,m)))
#define list_first_entry(h,t,m) container_of((h)->next,t,m)
struct device_driver {int unused;};
struct device {struct device_driver *driver;void *data;const char *name;};
struct platform_device {struct device dev;};
static struct {struct device_driver driver;} g2d_driver;
static int platform_bus_type;
static struct platform_device pdev;
static void *dev_get_drvdata(struct device *d){return d->data;}
static void *platform_get_drvdata(struct platform_device *p){return p->dev.data;}
static const char *dev_name(struct device *d){return d->name;}
static int bus_for_each_dev(void *bus,void *start,void *arg,int (*call)(struct device *,void *)){assert(bus==&platform_bus_type && !start);return call(&pdev.dev,arg);}
struct timer_list {int pending;};
static int timer_pending(struct timer_list *t){return t->pending;}
struct workqueue_struct {int unused;};
struct clk {int enabled;};
struct g2d_task {struct g2d_task *next;unsigned long state;struct timer_list fence_timer,hw_timer;struct list_head node;};
struct g2d_device {
    unsigned long state;struct device *dev;struct clk *clock;void *reg;
    spinlock_t lock_task;struct g2d_task *tasks;struct list_head tasks_active,tasks_prepared;
    struct workqueue_struct *schedule_workq;int freeze_wait;
    bool n132_terminal,n132_ever_allocated,n132_shutdown_seen;
    int n132_shutdown_result;unsigned int n132_irq;
};
static struct g2d_device g2d;static struct g2d_task tasks[G2D_MAX_JOBS];
static struct workqueue_struct queue;static struct clk clock_source;static u32 registers[256];
static int pm_result,clock_result,pm_gets,pm_puts,forbids,clock_gets,clock_disables;
static int irq_disabled,irq_syncs,powered,mmio_reads,flushes,forced_clock_on,clock_checks,executions,logs;
static const char *last_stage,*last_reason;static unsigned int last_item;static unsigned long last_state;static int last_value;
static int n130_arm_state=2,n130_return_owner=N130_HARDWARE;
static struct {struct device *device;int result;} n130_dma[128];static unsigned int n130_dma_count;
static void message(const char *fmt,...)
{
    va_list ap;const char *owner;va_start(ap,fmt);(void)va_arg(ap,const char *);
    if(strstr(fmt," g2d reason=")){
        last_reason=va_arg(ap,const char *);last_item=va_arg(ap,unsigned int);
        last_state=va_arg(ap,unsigned long);last_value=va_arg(ap,int);owner=va_arg(ap,const char *);
        assert(!strcmp(owner,"g2d-test"));
    }else{last_stage=va_arg(ap,const char *);(void)va_arg(ap,int);(void)va_arg(ap,const char *);}
    va_end(ap);logs++;
}
#define pr_emerg(...) message(__VA_ARGS__)
static void flush_workqueue(struct workqueue_struct *q){assert(q==&queue && g2d.n132_terminal && !g2d.n132_ever_allocated && !g2d.lock_task.held);flushes++;}
static void disable_irq_nosync(unsigned int irq){assert(irq==g2d.n132_irq && !g2d.lock_task.held);irq_disabled=1;}
static void synchronize_irq(unsigned int irq){assert(irq==g2d.n132_irq && irq_disabled);irq_syncs++;}
static int pm_runtime_get_sync(struct device *d){assert(d==g2d.dev && irq_syncs && !g2d.lock_task.held);pm_gets++;if(pm_result>=0)powered=1;return pm_result;}
static void pm_runtime_put_noidle(struct device *d){assert(d==g2d.dev);pm_puts++;}
static void pm_runtime_forbid(struct device *d){assert(d==g2d.dev && powered);forbids++;}
static int pm_runtime_suspended(struct device *d){assert(d==g2d.dev);return !powered;}
static int clk_prepare_enable(struct clk *c){assert(c==g2d.clock && powered && forbids);clock_gets++;if(clock_result>=0)c->enabled=1;return clock_result;}
static void clk_disable(struct clk *c){assert(c==g2d.clock && c->enabled);c->enabled=0;clock_disables++;}
static bool __clk_is_enabled(struct clk *c){assert(c==g2d.clock && powered);clock_checks++;return c->enabled || forced_clock_on;}
static u32 readl(void *address){uintptr_t offset=(uintptr_t)address-(uintptr_t)g2d.reg;assert(powered && clock_source.enabled && irq_syncs && !g2d.lock_task.held && offset%4==0 && offset/4<ARRAY_SIZE(registers));mmio_reads++;return registers[offset/4];}
#define G2D_STAMP_STATE_RESUME 1
#define G2D_STAMP_STATE_SUSPEND 2
#define G2D_STAMP_STATE_SHUTDOWN 3
#define g2d_stamp_task(...) ((void)0)
#define wait_event(q,condition) do{(void)(q);assert(condition);}while(0)
static void g2d_execute_task(struct g2d_device *d,struct g2d_task *t){(void)d;(void)t;executions++;}
static void iovmm_deactivate(struct device *d){assert(d==g2d.dev);}
'''
    registry=without_includes(rendered['arch/arm64/mm/v131_dma_registry.inc'].decode())
    bodies=function(header,'n132_g2d_allocate_locked')+function(kernel,'n132_handoff_active')
    bodies+=function(regs,'g2d_hw_fifo_status')+function(regs,'g2d_hw_fifo_idle')+function(regs,'g2d_hw_get_job_state')
    bodies+=function(task_source,'g2d_prepare_suspend')+function(task_source,'g2d_suspend_finish')
    provider=without_includes(rendered['drivers/gpu/exynos/g2d/v132_g2d.inc'].decode())
    shutdown=function(driver,'g2d_shutdown')
    cases=r'''static void fresh(void)
{
    unsigned int i;memset(&g2d,0,sizeof(g2d));memset(tasks,0,sizeof(tasks));memset(registers,0,sizeof(registers));
    memset(n130_dma,0,sizeof(n130_dma));n130_dma_count=0;
    pdev.dev.driver=&g2d_driver.driver;pdev.dev.data=&g2d;pdev.dev.name="g2d-test";
    g2d.dev=&pdev.dev;g2d.clock=&clock_source;g2d.reg=registers;g2d.schedule_workq=&queue;g2d.n132_irq=55;
    init_list(&g2d.tasks_active);init_list(&g2d.tasks_prepared);
    for(i=0;i<G2D_MAX_JOBS;i++){tasks[i].next=i+1<G2D_MAX_JOBS?&tasks[i+1]:NULL;init_list(&tasks[i].node);}
    g2d.tasks=tasks;registers[G2D_FIFO_STAT_REG/4]=1;clock_source.enabled=0;
    pm_result=clock_result=pm_gets=pm_puts=forbids=clock_gets=clock_disables=0;
    irq_disabled=irq_syncs=powered=mmio_reads=flushes=forced_clock_on=clock_checks=executions=logs=0;
    last_stage=last_reason=NULL;last_item=0;last_state=0;last_value=0;
    n130_arm_state=2;n130_return_owner=N130_HARDWARE;
}
static void denied(int error)
{assert(last_stage && !strncmp(last_stage,"g2d-",4));assert(g2d.n132_shutdown_seen && g2d.n132_shutdown_result==error && n131_dma_status(g2d.dev)==error && n132_g2d_prepare()==error && !g2d.lock_task.held);}
int main(void)
{
    unsigned long flags;
    fresh();n130_arm_state=0;g2d_shutdown(&pdev);
    assert(!g2d.n132_terminal && !g2d.n132_shutdown_seen && !pm_gets && !mmio_reads && n131_dma_status(g2d.dev)==-ENOENT);
    fresh();n130_return_owner=N130_RECOVERY;g2d_shutdown(&pdev);assert(!g2d.n132_shutdown_seen && !pm_gets);
    fresh();g2d.n132_irq=0;g2d_shutdown(&pdev);denied(-ENODEV);assert(!irq_disabled && !pm_gets);
    fresh();spin_lock_irqsave(&g2d.lock_task,flags);assert(n132_g2d_allocate_locked(&g2d));spin_unlock_irqrestore(&g2d.lock_task,flags);
    g2d_shutdown(&pdev);denied(-EBUSY);assert(!pm_gets && !irq_disabled && !strcmp(last_reason,"allocation-history") && last_value==1);
    fresh();add(&g2d.tasks_prepared,&tasks[0].node);g2d_shutdown(&pdev);denied(-EBUSY);assert(!pm_gets);
    fresh();tasks[0].hw_timer.pending=1;g2d_shutdown(&pdev);denied(-EBUSY);assert(!pm_gets && !strcmp(last_reason,"hw-timer") && last_item==0 && last_value==1);
    fresh();tasks[G2D_MAX_JOBS-1].next=tasks;g2d_shutdown(&pdev);denied(-EBUSY);assert(!pm_gets);
    fresh();g2d.tasks=tasks+1;g2d_shutdown(&pdev);denied(-ENODEV);assert(!pm_gets);
    fresh();pm_result=-ETIMEDOUT;g2d_shutdown(&pdev);denied(-ETIMEDOUT);assert(pm_gets==1 && pm_puts==1 && !clock_gets && !mmio_reads && !strcmp(last_reason,"pm-get") && last_value==-ETIMEDOUT);
    fresh();clock_result=-EIO;g2d_shutdown(&pdev);denied(-EIO);assert(clock_gets==1 && !clock_disables && !mmio_reads && !strcmp(last_reason,"clock-prepare") && last_value==-EIO);
    fresh();registers[G2D_FIFO_STAT_REG/4]=0;g2d_shutdown(&pdev);denied(-EBUSY);assert(mmio_reads==120 && clock_gets==1 && clock_disables==1 && !clock_checks && !strcmp(last_reason,"fifo-idle"));
    fresh();registers[G2D_JOB_IDn_STATE_REG(4)/4]=0x100|G2D_JOB_STATE_RUNNING;g2d_shutdown(&pdev);denied(-EBUSY);assert(mmio_reads==6 && clock_disables==1 && !clock_checks && !strcmp(last_reason,"job-state") && last_item==4 && last_state==G2D_JOB_STATE_RUNNING);
    fresh();forced_clock_on=1;g2d_shutdown(&pdev);denied(-EBUSY);assert(mmio_reads==1+G2D_MAX_JOBS && clock_disables==1 && clock_checks==1 && !strcmp(last_reason,"clock-enabled"));
    fresh();g2d_shutdown(&pdev);
    assert(g2d.n132_shutdown_seen && g2d.n132_shutdown_result==0 && n131_dma_status(g2d.dev)==0);
    assert(irq_disabled && irq_syncs==1 && flushes==1 && pm_gets==1 && forbids==1 && clock_gets==1 && clock_disables==1 && !clock_source.enabled);
    assert(mmio_reads==1+G2D_MAX_JOBS && clock_checks==1 && !logs && !n132_g2d_prepare());
    {int reads=mmio_reads,gets=pm_gets;assert(!n132_g2d_prepare() && mmio_reads==reads && pm_gets==gets);}
    spin_lock_irqsave(&g2d.lock_task,flags);assert(!n132_g2d_allocate_locked(&g2d));spin_unlock_irqrestore(&g2d.lock_task,flags);
    g2d_suspend_finish(&g2d);assert(test_bit(G2D_DEVICE_STATE_SUSPEND,&g2d.state) && !executions);
    add(&g2d.tasks_active,&tasks[0].node);assert(n132_g2d_prepare()==-EBUSY);
    fresh();g2d_shutdown(&pdev);pdev.dev.driver=NULL;assert(n132_g2d_prepare()==-ENODEV);
    fresh();g2d_shutdown(&pdev);g2d_shutdown(&pdev);denied(-EALREADY);assert(pm_gets==1 && clock_gets==1);
    assert(logs && !g2d.lock_task.held);puts("NEW G2D terminal provider PASS");return 0;
}
'''
    return includes+enums[0]+'\n'+constants+prefix+registry+bodies+provider+shutdown+cases


def reject(call):
    try:call()
    except ValueError:return
    raise AssertionError('G2D successor admission did not reject')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--scope',required=True,choices=[SCOPE]);p.add_argument('--source-evidence',type=Path,required=True)
    p.add_argument('--source128',type=Path,required=True);p.add_argument('--retained-pass',type=Path,required=True)
    p.add_argument('--retained-pass-sha256',required=True);p.add_argument('--cc',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();out=private(a.output);prior=ordinary(a.retained_pass);cc=ordinary(a.cc)
    if out.exists() or sha(prior)!=hexid(a.retained_pass_sha256):p.error('fresh NEW G2D output and exact accepted131 PASS required')
    current=source_pins();delta={n:current[n] for n in NEW_FILES}
    candidate=dict(schema='note10-v132-public-g2d-terminal-continuation-v1',scope=SCOPE,passed=True,retained_source_commit=RETAINED_COMMIT,
        retained_terminal_dma_PASS=read(prior),delta_NEW_PASS=dict(schema='note10-v132-g2d-terminal-pass-v1',scope=SCOPE,passed=True,result_sha256='0'*64,source_sha256=delta),source_sha256=current)
    out.mkdir(parents=True);save(out/'attempt.json',dict(schema='note10-v132-g2d-terminal-attempt-v1',scope=SCOPE,source_sha256=delta))
    result=dict(schema='note10-v132-g2d-terminal-result-v1',scope=SCOPE,passed=False,source_sha256=delta,current_source_sha256=current,
        compiler_invocations=0,fixture_processes=0,old_tests_replayed=0,raw_kernel_reads=0,adapter_reads=0,compressions=0,Image_reads=0,Image_builds=0,device_operations=[])
    try:
        continuation(candidate,current)
        if SETTINGS.get(prepare.OPTION)!='y' or SETTINGS.get('EXYNOS_GRAPHICS_G2D')!='y':raise ValueError('actual G2D handoff profile required')
        stock={n:ordinary(a.source_evidence/n).read_bytes() for n in prepare.PINS}
        rendered=prepare.render(stock,'0123456789abcdef0123456789abcdef',a.source128)
        tasks=rendered['drivers/gpu/exynos/g2d/g2d_task.c'];start,end=prepare.function(tasks,'g2d_get_free_task');admission=tasks[start:end]
        assert admission.count(b'if(g2d_dev->n132_terminal)')==2 and admission.count(b'n132_g2d_allocate_locked(g2d_dev)')==1
        assert b'g2d_dev->n132_irq=res->start' in rendered['drivers/gpu/exynos/g2d/g2d_drv.c']
        kernel=function(rendered['arch/arm64/mm/v130_kernel.c'].decode(),'n130_after_shutdown')
        assert kernel.index('n130_ufs_prepare')<kernel.index('n132_g2d_prepare')<kernel.index('n130_iommu_prepare')
        source=out/'new-g2d-terminal.c';source.write_text(fixture(rendered,stock),encoding='utf-8',newline='\n')
        executable=out/('new-g2d-terminal.exe' if cc.suffix.lower()=='.exe' else 'new-g2d-terminal')
        argv=[str(cc),'-std=gnu11','-O2','-Wall','-Wextra','-Werror','-DCONFIG_'+prepare.OPTION+'=1',str(source),'-o',str(executable)]
        result['compiler_invocations']=1
        with (out/'compile.log').open('wb') as stream:subprocess.run(argv,cwd=ROOT,stdout=stream,stderr=subprocess.STDOUT,check=True,timeout=60)
        result['fixture_processes']=1
        with (out/'fixture.log').open('wb') as stream:subprocess.run([str(executable)],cwd=ROOT,stdout=stream,stderr=subprocess.STDOUT,check=True,timeout=15)
        import v132_cycle as cycle
        import v132_package as package
        assert package.INPUTS_SCHEMA=='note10-v132-package-inputs-v1' and cycle.LEDGER_SCHEMA=='note10-v132-owned-XNU-ledger-v1'
        identity='0123456789abcdef0123456789abcdef';cycle_id='fedcba9876543210fedcba9876543210'
        text='N10XNU132 id='+identity+' cycle='+cycle_id+' stage=begin\nN10XNU132 id='+identity+' stage=g2d-job errno=-16 owner=g2d-test\n'
        text+='N10XNU132 id='+identity+' g2d reason=job-state item=4 state=3 value=0 owner=g2d-test\n'
        obs=cycle.decode({'synthetic':text.encode()},identity,cycle_id)
        assert obs['gate_refusals']==[dict(stage='g2d-job',errno=-16,owner='g2d-test')] and not obs['XNU_executed']
        assert obs['g2d_refusal_details']==[dict(reason='job-state',item=4,state=3,value=0,owner='g2d-test')]
        old=out/'synthetic-old-plan.json';save(old,dict(schema='note10-v131-owned-xnu-cycle-v1',version='v131'))
        reject(lambda:package.validate_plan(old,sha(old)))
        rows=[dict(partition=name,file=name+'.img',sha256='1'*64,size=4096,block_node='/dev/block/sda'+str(i),remote_hash_before_and_after_match=True)
            for i,name in enumerate(sorted(package.PARTITIONS),1)]
        baseline=dict(schema='note10-v131-private-xnu-package-v1',version='v131',cycle='3'*32,build_evidence_id='4'*32,
            diagnostic_BOOT_sha256='2'*64,rollback_BOOT_sha256='1'*64,bootloader='synthetic',partitions=rows)
        ledger=dict(schema='note10-v131-owned-XNU-ledger-v1',recovery_returned=True,host_BOOT_write_attempts=1,host_reboot_attempts=1,
            internal_kexec_load_attempts_observed=1,internal_kexec_REBOOT_attempts_observed=1,cycle='3'*32,build_evidence_id='4'*32,
            normal_recovery_fallback_observed=False,status='cycle-complete-XNU-proof-limits-retained')
        backup=dict(complete=True,partition_writes=False,partitions=rows,bootloader='synthetic')
        assert package.current_and_restore(baseline,ledger,backup)[0]=='2'*64
        reject(lambda:package.current_and_restore(dict(baseline,version='v130'),ledger,backup))
        bad=json.loads(json.dumps(candidate));bad['retained_source_commit']='0'*40;reject(lambda:continuation(bad,current))
        bad=json.loads(json.dumps(candidate));bad['delta_NEW_PASS']['source_sha256'][NEW_FILES[0]]='0'*64;reject(lambda:continuation(bad,current))
        if source_pins()!=current:raise ValueError('G2D source changed during NEW batch')
        result.update(passed=True,cases=['armed callback selection','sticky allocation/freeze/resume protection','bounded task-chain and timer checks','PM/clock failure before MMIO','bounded native FIFO/all16 job readback','own enable balanced on failure/success','unexpected clock user refuses','cached proof has no late PM/MMIO','late-state/unbind/duplicate shutdown refuse','new132 contracts and bounded G2D errno decode','retained131 PASS without replay'])
    except Exception:
        import traceback
        result['error']=traceback.format_exc()
    save(out/'result.json',result)
    if result['passed']:
        candidate['delta_NEW_PASS']['result_sha256']=sha(out/'result.json');continuation(candidate,current)
        save(out/'public-g2d-terminal-continuation.json',candidate)
        (out/'public-g2d-terminal-continuation.b64').write_bytes(base64.b64encode(json.dumps(candidate,separators=(',',':')).encode())+b'\n')
    return 0 if result['passed'] else 1


if __name__=='__main__':raise SystemExit(main())
