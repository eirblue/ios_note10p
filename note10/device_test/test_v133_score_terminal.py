"""One NEW SCORE lifetime/native-stop batch; accepted132 PASS is retained."""
import argparse
import base64
import json
from pathlib import Path
import re
import subprocess
from v130_contract import ROOT,ordinary,private,read,save,sha,hexid,digest
from v133_build import source_pins,continuation,NEW_FILES,SCOPE,RETAINED_COMMIT,SETTINGS
import v133_prepare as prepare

TEST_SOURCE_PATH='note10/device_test/test_v133_score_terminal.py'
INITIAL_TEST_SHA256='9357ac5da07680135d5d7f59bdfeb1bdd373d10caad179c07ae861894abe5282'
PARTIAL_RESULT_SHA256='6bf58d24ce8b0ecff01337fef4f7e21d17fbd1e8b4e532e4613eac4cccd9a9dd'
PARTIAL_FILES={'compile.log':'59ec2c3a3b3a4ab9992560284c63042125562ef2cdbc08f733b47c379dbaecea',
    'attempt.json':'92606353f37442eed6cb3c48b49d2c61ed6373f197165442c5370b9b5be9fe7b',
    'new-score-terminal.c':'9d23b54aa53f77b4ad99359b0dd6ca79e041e125232616f721677968e8828733'}
# Pinned Linux55f042 arm64 asm/Kbuild selects generic-y errno.h.
LINUX_ERRNO_SOURCE_SHA256='fb7b5a504015f3a9074c641e7371b250d867d751d90e4a22a8ac17fced3d50af'
PORTABLE_ERRNO=r"""/* Pinned Linux asm-generic errno.h: ESHUTDOWN108, including Windows host. */
#ifndef ESHUTDOWN
#define ESHUTDOWN 108
#elif ESHUTDOWN != 108
#error "SCORE synthetic errno must match pinned Linux ESHUTDOWN108"
#endif
"""
OLD_DENIED='{assert(score.n133_shutdown_seen && score.n133_shutdown_result==error && n131_dma_status(score.dev)==error && n133_score_prepare()==error && !score.core.device_lock.held);}'
NEW_DENIED='{assert(last_stage && !strncmp(last_stage,"score-",6));assert(score.n133_shutdown_seen && score.n133_shutdown_result==error && n131_dma_status(score.dev)==error && n133_score_prepare()==error && !score.core.device_lock.held);assert(!strcmp(last_stage,"score-cached"));}'
COMPLETED_PRECOMPILE_CHECKS=('original132 PASS/continuation admission','actual enabled SETTINGS profile','pinned stock/render closure',
    'both native core-locked get admissions','all28 sysfs and3 profiler wrapper boundaries','boot guard and IRQ initialization order',
    'qualified shutdown dispatch','runtime resume has no boot/firmware/SCQ path','native halt/core/DMA predicates and G2D-SCORE-IOMMU order',
    'actual generated C fixture materialized')


def retained_partial(path,expected,current):
    path=ordinary(path);raw=path.read_bytes()
    if hexid(expected)!=PARTIAL_RESULT_SHA256 or digest(raw)!=PARTIAL_RESULT_SHA256:raise ValueError('exact retained133 failed-compile result required')
    row=json.loads(raw);old=row.get('current_source_sha256',{})
    if (row.get('schema')!='note10-v133-score-terminal-result-v1' or row.get('scope')!=SCOPE or row.get('passed') is not False or
        type(row.get('compiler_invocations')) is not int or row['compiler_invocations']!=1 or
        type(row.get('fixture_processes')) is not int or row['fixture_processes']!=0 or
        row.get('old_tests_replayed')!=0 or row.get('device_operations')!=[] or
        'CalledProcessError' not in row.get('error','') or set(old)!=set(current) or
        old.get(TEST_SOURCE_PATH)!=INITIAL_TEST_SHA256 or current[TEST_SOURCE_PATH]==INITIAL_TEST_SHA256 or
        any(current[n]!=pin for n,pin in old.items() if n!=TEST_SOURCE_PATH) or
        row.get('source_sha256')!={n:old[n] for n in NEW_FILES}):raise ValueError('retained boundary must be compile1/process0 with unchanged production55')
    saved={};references={}
    for name,pin in PARTIAL_FILES.items():
        item=ordinary(path.parent/name);data=item.read_bytes()
        if digest(data)!=pin:raise ValueError('retained initial source/log/attempt differs: '+name)
        saved[name]=data;references[name]=dict(path=str(item),sha256=pin)
    attempt=json.loads(saved['attempt.json'])
    if attempt!={'schema':'note10-v133-score-terminal-attempt-v1','scope':SCOPE,'source_sha256':row['source_sha256']}:raise ValueError('retained original attempt identity differs')
    return saved['new-score-terminal.c'],dict(result_path=str(path),result_sha256=PARTIAL_RESULT_SHA256,
        files=references,original_source_sha256=old,compiler_invocations=1,fixture_processes=0,
        completed_precompile_checks=list(COMPLETED_PRECOMPILE_CHECKS),unchanged_source_files=55)


def portability_source(raw):
    errno=b'#include <errno.h>\n';denied=OLD_DENIED.encode('ascii')
    if raw.count(errno)!=1 or raw.count(denied)!=1:raise ValueError('exact saved fixture portability anchors differ')
    return raw.replace(errno,errno+PORTABLE_ERRNO.encode('ascii'),1).replace(denied,NEW_DENIED.encode('ascii'),1)


def function(raw,name):
    matches=list(re.finditer(r'(?m)^(?:static )?(?:inline )?(?:int|void|bool|u32|ssize_t) '+re.escape(name)+r'\([^)]*\)\n\{',raw))
    if len(matches)!=1:raise ValueError('unique actual SCORE function required: '+name)
    start=matches[0].start();at=raw.index('{',start)+1;depth=1
    while depth and at<len(raw):depth+=(raw[at]=='{')-(raw[at]=='}');at+=1
    if depth:raise ValueError('actual SCORE function boundary missing')
    return raw[start:at]+'\n'


def macro(raw,name):
    rows=[line for line in raw.splitlines() if re.match(r'#define\s+'+re.escape(name)+r'\s',line)]
    if len(rows)!=1:raise ValueError('actual SCORE macro differs: '+name)
    return rows[0]+'\n'


def without_includes(raw):return '\n'.join(line for line in raw.splitlines() if not line.startswith('#include'))+'\n'


def fixture(rendered,stock):
    base='drivers/vision/score/';system=base+'hardware/v3/'
    regs=stock[system+'score_regs.h'].decode();header=rendered[system+'score_system.h'].decode()
    native=stock[base+'score_device.c'].decode();clocks=stock[system+'v3_1/score_clk.c'].decode()
    constants=''.join(macro(regs,n) for n in ('TS_SWI_STATUS','BR1_SWI_STATUS','BR2_SWI_STATUS','TS_CACHE_STATUS','BR_CACHE_STATUS','TS_INTR_ENABLE','BR1_INTR_ENABLE','BR2_INTR_ENABLE','DMA0_QUEUE_STATUS','DMA1_QUEUE_STATUS','DMA2_QUEUE_STATUS','DMA3_QUEUE_STATUS'))
    constants+=''.join(macro(header,n) for n in ('CHECK_RETRY_COUNT','CHECK_RETRY_DELAY'))
    device_h=rendered[base+'score_device.h'].decode();scq_h=stock[system+'score_scq.h'].decode()
    enums=''.join(re.findall(r'enum score_device_state\s*\{[^}]+\};',device_h))+''.join(re.findall(r'enum score_scq_state\s*\{[^}]+\};',scq_h))
    includes=r"""#include <assert.h>
#include <errno.h>
#include <stdbool.h>
#include <stdint.h>
#include <stddef.h>
#include <stdio.h>
#include <string.h>
#include <stdarg.h>
#include <sys/types.h>
typedef int64_t loff_t;
"""
    prefix=r"""typedef uint32_t u32;
#define BIT(n) (1U<<(n))
#define ARRAY_SIZE(a) (sizeof(a)/sizeof((a)[0]))
#define N10_KEXEC_BUILD_ID "0123456789abcdef0123456789abcdef"
#define READ_ONCE(x) (x)
#define IS_ERR_OR_NULL(p) (!(p))
#define IS_ERR(p) (!(p))
#define PTR_ERR(p) ((void)(p),-ENODEV)
#define SCORE_MAX_FRAME 128
#define score_enter() ((void)0)
#define score_leave() ((void)0)
#define score_err(...) ((void)0)
struct rw_semaphore {int readers,writer;};
static int down_read_trylock(struct rw_semaphore *p){if(p->writer)return 0;p->readers++;return 1;}
static void up_read(struct rw_semaphore *p){assert(p->readers>0);p->readers--;}
static int down_write_trylock(struct rw_semaphore *p){if(p->writer || p->readers)return 0;p->writer=1;return 1;}
static void up_write(struct rw_semaphore *p){assert(p->writer);p->writer=0;}
struct mutex {int held;};
static int mutex_trylock(struct mutex *p){if(p->held)return 0;p->held=1;return 1;}
static void mutex_unlock(struct mutex *p){assert(p->held);p->held=0;}
typedef struct {int held;} spinlock_t;
static void lock(spinlock_t *p){assert(!p->held);p->held=1;}
static void unlock(spinlock_t *p){assert(p->held);p->held=0;}
#define DEFINE_SPINLOCK(n) spinlock_t n={0}
#define spin_lock_irqsave(p,f) do{(f)=0;lock(p);}while(0)
#define spin_unlock_irqrestore(p,f) do{(void)(f);unlock(p);}while(0)
struct list_head {struct list_head *next,*prev;};
static void init_list(struct list_head *p){p->next=p->prev=p;}
#define list_empty(p) ((p)->next==(p))
static int bitmap_empty(const unsigned long *p,unsigned int bits){unsigned int i;for(i=0;i<bits/(8*sizeof(*p));i++)if(p[i])return 0;return 1;}
typedef struct {int value;} atomic_t;
#define atomic_read(p) ((p)->value)
struct timer_list {int pending;};
#define timer_pending(p) ((p)->pending)
struct device_driver {int unused;};
struct device {struct device_driver *driver;void *data;const char *name;int native_locked;};
struct platform_device {struct device dev;};
struct device_attribute {int unused;};struct file {int unused;};struct kobject {int unused;};struct bin_attribute {int unused;};
static struct {struct device_driver driver;} score_driver;
static struct platform_device pdev;static int platform_bus_type;
static int device_trylock(struct device *p){if(p->native_locked)return 0;p->native_locked=1;return 1;}
static void device_unlock(struct device *p){assert(p->native_locked);p->native_locked=0;}
static void *dev_get_drvdata(struct device *p){return p->data;}
static const char *dev_name(struct device *p){return p->name;}
static int bus_for_each_dev(void *bus,void *start,void *arg,int (*call)(struct device *,void *)){assert(bus==&platform_bus_type && !start);return call(&pdev.dev,arg);}
struct kthread_worker {int marker;};
struct clk {int enabled,id;};
struct score_frame_manager {
    struct list_head entire_list,ready_list,process_list,pending_list,complete_list;
    unsigned int entire_count,ready_count,process_count,pending_count,complete_count;
    unsigned int process_high_count,process_normal_count,pending_high_count,pending_normal_count;
    unsigned int all_count,normal_count,abnormal_count;unsigned long frame_map[(SCORE_MAX_FRAME+8*sizeof(unsigned long)-1)/(8*sizeof(unsigned long))];bool block;spinlock_t slock;
};
struct score_interface {struct device *dev;int irq0;struct score_frame_manager framemgr;};
struct score_scq {unsigned int state,count,high_count,normal_count;struct kthread_worker write_worker;void *write_task;};
struct score_mmu {spinlock_t free_slock;struct list_head free_list;int free_count;struct kthread_worker unmap_worker;void *unmap_task;};
struct score_print {int init;struct timer_list timer;};
struct n133_score_detail {const char *reason;unsigned int item;u32 state;int value;u32 aux;};
struct score_system {struct device *dev;struct score_interface interface;struct score_scq scq;struct score_mmu mmu;struct score_print print;void *sfr;size_t sfr_size;spinlock_t cache_slock,n133_boot_lock;bool n133_terminal,n133_ever_booted;};
struct score_clk {struct clk *clkm,*clks;};
struct score_pm {int qos_count;};
struct score_core {struct mutex device_lock;spinlock_t ctx_slock;struct list_head ctx_list;int ctx_count;};
struct score_device {struct device *dev;struct platform_device *pdev;atomic_t open_count;unsigned int state;struct score_system system;struct score_clk clk;struct score_pm pm;struct score_core core;struct rw_semaphore n133_user_lock;bool n133_user_frozen;bool n133_terminal,n133_ever_opened,n133_shutdown_seen;int n133_shutdown_result;};
static struct score_device score;static struct {struct score_system *system;} profiler;static int user_native_calls;static struct clk clocks[2];static u32 registers[0x60008/4];
static int pm_error,clock_error,clock_error_id,pm_gets,pm_puts,pm_disabled,pm_enabled,powered;
static int irq_disabled,irq_syncs,flushes,mmio_reads,writes,delays,clock_gets,clock_disables,foreign_gate,logs;
static int qos_error,qos_calls,qos_open,translations,already_active;static const char *last_stage,*last_reason;
static unsigned int last_item,last_state,last_aux;static int last_value;
static int n130_arm_state=2;
static struct {struct device *device;int result;} n130_dma[128];static unsigned int n130_dma_count;
static void message(const char *fmt,...)
{
    va_list ap;va_start(ap,fmt);(void)va_arg(ap,const char *);
    if(strstr(fmt," score reason=")){
        last_reason=va_arg(ap,const char *);last_item=va_arg(ap,unsigned int);last_state=va_arg(ap,u32);
        last_value=va_arg(ap,int);last_aux=va_arg(ap,u32);assert(!strcmp(va_arg(ap,const char *),"score-test"));
    }else{last_stage=va_arg(ap,const char *);(void)va_arg(ap,int);(void)va_arg(ap,const char *);}
    va_end(ap);logs++;
}
#define pr_emerg(...) message(__VA_ARGS__)
static void score_frame_manager_block(struct score_frame_manager *fm){assert(fm->slock.held);fm->block=true;}
static void disable_irq_nosync(int irq){assert(irq==55 && score.core.device_lock.held);irq_disabled=1;}
static void synchronize_irq(int irq){assert(irq==55 && irq_disabled);irq_syncs++;}
static void kthread_flush_worker(struct kthread_worker *w){assert(irq_syncs && score.n133_terminal && !score.n133_ever_opened);assert(w==&score.system.scq.write_worker || w==&score.system.mmu.unmap_worker);flushes++;}
static int score_pm_qos_set_default(struct score_pm *p,int value){assert(p==&score.pm && value==p->qos_count-1);qos_calls++;return qos_error;}
static int score_pm_open(struct score_pm *p){assert(p==&score.pm);qos_open++;return 0;}
static void score_pm_close(struct score_pm *p){assert(p==&score.pm);qos_open--;}
static int clk_prepare_enable(struct clk *p){assert(powered && p && p->id>=0 && p->id<2);clock_gets++;if(clock_error && p->id==clock_error_id)return clock_error;p->enabled++;return 0;}
static void clk_disable(struct clk *p){assert(p && p->enabled>0 && pm_disabled);p->enabled--;clock_disables++;}
static void clk_disable_unprepare(struct clk *p){assert(p && p->enabled>0);p->enabled--;clock_disables++;}
static int __clk_is_enabled(struct clk *p){assert(p);return p->enabled || (powered && foreign_gate==p->id+1);}
static int iovmm_activate(struct device *p){assert(p==score.dev && powered);translations++;return 0;}
static int score_device_runtime_resume(struct device *p);
static int pm_runtime_enabled(struct device *p){assert(p==score.dev);return pm_enabled;}
static int pm_runtime_suspended(struct device *p){assert(p==score.dev);return !powered;}
static int pm_runtime_get_sync(struct device *p){int error;assert(irq_syncs && score.core.device_lock.held && score.system.n133_terminal);pm_gets++;if(already_active){powered=1;return 1;}if(pm_error)return pm_error;powered=1;error=score_device_runtime_resume(p);return error;}
static void pm_runtime_put_noidle(struct device *p){assert(p==score.dev);pm_puts++;}
static void pm_runtime_disable(struct device *p){assert(p==score.dev && powered);pm_disabled++;pm_enabled=0;}
static u32 readl(void *p){uintptr_t off=(uintptr_t)p-(uintptr_t)score.system.sfr;assert(powered && clocks[0].enabled && clocks[1].enabled && irq_syncs && score.system.cache_slock.held && off%4==0 && off/4<ARRAY_SIZE(registers));mmio_reads++;return registers[off/4];}
static void writel(u32 value,void *p){uintptr_t off=(uintptr_t)p-(uintptr_t)score.system.sfr;assert(powered && clocks[0].enabled && clocks[1].enabled && irq_syncs && score.system.cache_slock.held);assert(value==1 && (off==TS_SWI_STATUS || off==BR1_SWI_STATUS || off==BR2_SWI_STATUS));writes++;}
static void udelay(unsigned int value){assert(value==CHECK_RETRY_DELAY);delays++;}
static ssize_t show_sysfs_system_sfr_n133_native(struct device *dev,struct device_attribute *attr,char *buf)
{(void)attr;(void)buf;assert(dev==score.dev && score.n133_user_lock.readers>0);user_native_calls++;return 7;}
static ssize_t score_profiler_read_n133_native(struct file *filp,struct kobject *kobj,struct bin_attribute *bin_attr,char *buffer,loff_t pos,size_t size)
{(void)filp;(void)kobj;(void)bin_attr;(void)buffer;(void)pos;(void)size;assert(score.n133_user_lock.readers>0);user_native_calls++;return 9;}

"""
    bodies=function(device_h,'n133_score_user_enter')+function(device_h,'n133_score_user_exit')+function(device_h,'n133_score_open_locked')+function(header,'n133_score_boot_enter')
    bodies+=''.join(function(clocks,n) for n in ('__score_clk_on','__score_clk_off','score_clk_open','score_clk_close'))
    bodies+=function(native,'score_device_runtime_resume')
    bodies+=function(rendered[system+'score_sysfs.c'].decode(),'show_sysfs_system_sfr')
    bodies+=function(rendered[system+'score_profiler.c'].decode(),'score_profiler_read')
    registry=without_includes(rendered['arch/arm64/mm/v131_dma_registry.inc'].decode())
    provider=without_includes(rendered[base+'v133_score.inc'].decode())
    copies='#define N133_SCORE_HARDWARE_TU\n'+provider+'\n#undef N133_SCORE_HARDWARE_TU\n'+provider
    cases=r"""static void fresh(void)
{
    struct score_frame_manager *fm;memset(&score,0,sizeof(score));memset(registers,0,sizeof(registers));memset(clocks,0,sizeof(clocks));memset(n130_dma,0,sizeof(n130_dma));n130_dma_count=0;
    pdev.dev.native_locked=0;pdev.dev.driver=&score_driver.driver;pdev.dev.data=&score;pdev.dev.name="score-test";score.dev=&pdev.dev;score.pdev=&pdev;score.state=BIT(SCORE_DEVICE_STATE_CLOSE);
    score.system.dev=score.dev;score.system.sfr=registers;score.system.sfr_size=sizeof(registers);score.system.interface.dev=score.dev;score.system.interface.irq0=55;
    score.system.scq.state=BIT(SCORE_SCQ_STATE_CLOSE);score.system.scq.write_task=&score;score.system.mmu.unmap_task=&score;
    init_list(&score.core.ctx_list);init_list(&score.system.mmu.free_list);fm=&score.system.interface.framemgr;
    init_list(&fm->entire_list);init_list(&fm->ready_list);init_list(&fm->process_list);init_list(&fm->pending_list);init_list(&fm->complete_list);
    score.clk.clkm=&clocks[0];score.clk.clks=&clocks[1];clocks[0].id=0;clocks[1].id=1;score.pm.qos_count=6;
    pm_error=clock_error=clock_error_id=pm_gets=pm_puts=pm_disabled=powered=irq_disabled=irq_syncs=flushes=mmio_reads=writes=delays=clock_gets=clock_disables=foreign_gate=logs=0;
    qos_error=qos_calls=qos_open=translations=already_active=user_native_calls=0;profiler.system=&score.system;pm_enabled=1;n130_arm_state=2;last_stage=last_reason=NULL;last_item=last_state=last_aux=0;last_value=0;
}
static void denied(int error)
{assert(score.n133_shutdown_seen && score.n133_shutdown_result==error && n131_dma_status(score.dev)==error && n133_score_prepare()==error && !score.core.device_lock.held);}
int main(void)
{
    unsigned int index;char user_buffer[8];
    fresh();assert(show_sysfs_system_sfr(score.dev,NULL,user_buffer)==7 && !score.n133_user_lock.readers);
    assert(score_profiler_read(NULL,NULL,NULL,user_buffer,0,sizeof(user_buffer))==9 && user_native_calls==2 && !score.n133_user_lock.readers);
    n133_score_shutdown(&pdev);assert(!n131_dma_status(score.dev));
    assert(show_sysfs_system_sfr(score.dev,NULL,user_buffer)==-ESHUTDOWN && score_profiler_read(NULL,NULL,NULL,user_buffer,0,sizeof(user_buffer))==-ESHUTDOWN && user_native_calls==2 && !score.n133_user_lock.readers);
    fresh();assert(n133_score_user_enter(&score));n133_score_shutdown(&pdev);assert(n131_dma_status(score.dev)==-EBUSY && !pm_gets && !score.n133_user_frozen && !strcmp(last_reason,"user-access-busy"));n133_score_user_exit(&score);
    fresh();score.n133_user_lock.writer=1;assert(!n133_score_user_enter(&score));score.n133_user_lock.writer=0;
    fresh();assert(mutex_trylock(&score.core.device_lock));assert(n133_score_open_locked(&score));mutex_unlock(&score.core.device_lock);
    n133_score_shutdown(&pdev);denied(-EBUSY);assert(!pm_gets && !strcmp(last_reason,"open-history"));
    fresh();assert(n133_score_boot_enter(&score.system));n133_score_shutdown(&pdev);denied(-EBUSY);assert(!pm_gets && !strcmp(last_reason,"boot-history"));
    fresh();score.system.interface.framemgr.all_count=1;n133_score_shutdown(&pdev);denied(-EBUSY);assert(!pm_gets && !strcmp(last_reason,"frame-history"));
    fresh();score.system.print.timer.pending=1;n133_score_shutdown(&pdev);denied(-EBUSY);assert(!pm_gets && !strcmp(last_reason,"print-timer"));
    fresh();score.system.interface.irq0=0;n133_score_shutdown(&pdev);denied(-ENODEV);assert(!pm_gets && !irq_disabled);
    fresh();powered=1;n133_score_shutdown(&pdev);denied(-EBUSY);assert(!pm_gets && !mmio_reads && !strcmp(last_reason,"pm-not-suspended"));
    fresh();clocks[0].enabled=1;n133_score_shutdown(&pdev);denied(-EBUSY);assert(!pm_gets && !clock_disables && clocks[0].enabled==1);
    fresh();qos_error=-EINVAL;n133_score_shutdown(&pdev);denied(-EINVAL);assert(qos_calls==1 && !pm_gets && last_value==-EINVAL);
    fresh();pm_error=-ETIMEDOUT;n133_score_shutdown(&pdev);denied(-ETIMEDOUT);assert(pm_gets==1 && pm_puts==1 && !clock_gets && !mmio_reads && last_value==-ETIMEDOUT);
    fresh();already_active=1;n133_score_shutdown(&pdev);denied(-EBUSY);assert(pm_puts==1 && !clock_disables && !mmio_reads && !strcmp(last_reason,"pm-already-active"));
    fresh();clock_error=-EIO;n133_score_shutdown(&pdev);denied(-EIO);assert(clock_gets==1 && !clock_disables && !mmio_reads && last_value==-EIO);
    fresh();registers[TS_CACHE_STATUS/4]=7;registers[TS_INTR_ENABLE/4]=9;n133_score_shutdown(&pdev);denied(-ETIMEDOUT);
    assert(mmio_reads==2*CHECK_RETRY_COUNT && delays==CHECK_RETRY_COUNT && writes==1 && clock_disables==2 && last_state==7 && last_value==9 && !strcmp(last_reason,"ts-halt"));
    fresh();registers[BR2_INTR_ENABLE/4]=5;n133_score_shutdown(&pdev);denied(-ETIMEDOUT);
    assert(mmio_reads==2+3*CHECK_RETRY_COUNT && last_item==1 && last_aux==5 && !strcmp(last_reason,"baron-halt"));
    for(index=0;index<4;index++){
        const unsigned int dma[]={DMA0_QUEUE_STATUS,DMA1_QUEUE_STATUS,DMA2_QUEUE_STATUS,DMA3_QUEUE_STATUS};
        fresh();registers[dma[index]/4]=0x1001;n133_score_shutdown(&pdev);denied(-ETIMEDOUT);
        assert(mmio_reads==5+(int)index+CHECK_RETRY_COUNT && last_item==index && last_state==0x1001 && last_aux==dma[index] && !strcmp(last_reason,"dma-busy"));
    }
    fresh();score.system.sfr_size=BR_CACHE_STATUS;n133_score_shutdown(&pdev);denied(-ENODEV);assert(!mmio_reads && clock_disables==2 && !strcmp(last_reason,"mmio-extent"));
    fresh();foreign_gate=2;n133_score_shutdown(&pdev);denied(-EBUSY);assert(clock_disables==2 && last_item==1 && !strcmp(last_reason,"dsps-clock-user"));
    fresh();n133_score_shutdown(&pdev);assert(!score.n133_shutdown_result && score.n133_shutdown_seen && !n131_dma_status(score.dev));
    assert(mmio_reads==9 && writes==3 && !delays && pm_gets==1 && qos_open==1 && translations==1 && clock_gets==2 && clock_disables==2 && pm_disabled==1 && !logs);
    assert(score.n133_user_frozen && !n133_score_user_enter(&score) && !score.n133_user_lock.readers && score.n133_terminal && score.system.n133_terminal && !n133_score_boot_enter(&score.system));
    assert(mutex_trylock(&score.core.device_lock));assert(!n133_score_open_locked(&score));mutex_unlock(&score.core.device_lock);
    {int before=mmio_reads,gets=pm_gets;assert(!n133_score_prepare() && !n133_score_prepare() && mmio_reads==before && pm_gets==gets && !pdev.dev.native_locked);}
    score.system.interface.framemgr.pending_count=1;assert(n133_score_prepare()==-EBUSY);
    fresh();n133_score_shutdown(&pdev);pdev.dev.native_locked=1;assert(n133_score_prepare()==-EBUSY);pdev.dev.native_locked=0;assert(!n133_score_prepare());
    fresh();n133_score_shutdown(&pdev);pdev.dev.driver=NULL;assert(n133_score_prepare()==-ENODEV);
    fresh();n133_score_shutdown(&pdev);n133_score_shutdown(&pdev);denied(-EALREADY);assert(pm_gets==1 && clock_disables==2);
    fresh();score.core.device_lock.held=1;n133_score_shutdown(&pdev);assert(n131_dma_status(score.dev)==-EBUSY && !pm_gets);score.core.device_lock.held=0;
    fresh();score.dev=NULL;n133_score_shutdown(&pdev);assert(n131_dma_status(&pdev.dev)==-ENOENT && !pm_gets);
    puts("NEW SCORE terminal provider PASS");return 0;
}
"""
    return portability_source((includes+enums+'\n'+constants+prefix+registry+bodies+copies+cases).encode('utf-8')).decode('utf-8')


def reject(call):
    try:call()
    except ValueError:return
    raise AssertionError('SCORE successor admission did not reject')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--scope',required=True,choices=[SCOPE]);p.add_argument('--source-evidence',type=Path,required=True)
    p.add_argument('--source128',type=Path,required=True);p.add_argument('--retained-pass',type=Path,required=True)
    p.add_argument('--retained-partial-result',type=Path,required=True);p.add_argument('--retained-partial-result-sha256',required=True)
    p.add_argument('--retained-pass-sha256',required=True);p.add_argument('--cc',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();out=private(a.output);prior=ordinary(a.retained_pass);cc=ordinary(a.cc)
    if out.exists() or sha(prior)!=hexid(a.retained_pass_sha256):p.error('fresh NEW SCORE output and exact accepted132 PASS required')
    current=source_pins();delta={n:current[n] for n in NEW_FILES}
    candidate=dict(schema='note10-v133-public-score-terminal-continuation-v1',scope=SCOPE,passed=True,retained_source_commit=RETAINED_COMMIT,
        retained_g2d_terminal_PASS=read(prior),delta_NEW_PASS=dict(schema='note10-v133-score-terminal-pass-v1',scope=SCOPE,passed=True,result_sha256='0'*64,source_sha256=delta),source_sha256=current)
    out.mkdir(parents=True);save(out/'attempt.json',dict(schema='note10-v133-score-terminal-attempt-v1',scope=SCOPE,source_sha256=delta))
    result=dict(schema='note10-v133-score-terminal-result-v1',scope=SCOPE,passed=False,source_sha256=delta,current_source_sha256=current,
        compiler_invocations=0,fixture_processes=0,old_tests_replayed=0,raw_kernel_reads=0,adapter_reads=0,compressions=0,Image_reads=0,Image_builds=0,device_operations=[])
    try:
        saved_source,boundary=retained_partial(a.retained_partial_result,a.retained_partial_result_sha256,current)
        result.update(remaining_only=True,retained_partial=boundary,completed_precompile_checks_retained=True,
            precompile_checks_replayed=0,fixture_generation_replayed=0)
        source=out/'new-score-terminal.c';source.write_bytes(portability_source(saved_source))
        executable=out/('new-score-terminal.exe' if cc.suffix.lower()=='.exe' else 'new-score-terminal')
        names=(prepare.OPTION,'EXYNOS_SCORE','EXYNOS_SCORE_V3','PM','COMMON_CLK','PM_DEVFREQ','EXYNOS_IOVMM')
        argv=[str(cc),'-std=gnu11','-O2','-Wall','-Wextra','-Werror','-DSCORE_EVT1=1',*['-DCONFIG_'+n+'=1' for n in names],str(source),'-o',str(executable)]
        result['compiler_invocations']=1
        with (out/'compile.log').open('wb') as stream:subprocess.run(argv,cwd=ROOT,stdout=stream,stderr=subprocess.STDOUT,check=True,timeout=60)
        result['fixture_processes']=1
        with (out/'fixture.log').open('wb') as stream:subprocess.run([str(executable)],cwd=ROOT,stdout=stream,stderr=subprocess.STDOUT,check=True,timeout=15)
        continuation(candidate,current) # New corrected source identity; prior precompile checks remain retained.
        import v133_cycle as cycle
        import v133_package as package
        assert package.INPUTS_SCHEMA=='note10-v133-package-inputs-v1' and cycle.LEDGER_SCHEMA=='note10-v133-owned-XNU-ledger-v1'
        identity='0123456789abcdef0123456789abcdef';cycle_id='fedcba9876543210fedcba9876543210'
        text='N10XNU133 id='+identity+' cycle='+cycle_id+' stage=begin\nN10XNU133 id='+identity+' stage=score-halt errno=-110 owner=score-test\n'
        text+='N10XNU133 id='+identity+' score reason=dma-busy item=3 state=4097 value=100 aux=16908 owner=score-test\n'
        obs=cycle.decode({'synthetic':text.encode()},identity,cycle_id)
        assert obs['gate_refusals']==[dict(stage='score-halt',errno=-110,owner='score-test')] and not obs['XNU_executed']
        assert obs['score_refusal_details']==[dict(reason='dma-busy',item=3,state=4097,value=100,aux=16908,owner='score-test')]
        old=out/'synthetic-old-plan.json';save(old,dict(schema='note10-v132-owned-xnu-cycle-v1',version='v132'))
        reject(lambda:package.validate_plan(old,sha(old)))
        rows=[dict(partition=name,file=name+'.img',sha256='1'*64,size=4096,block_node='/dev/block/sda'+str(i),remote_hash_before_and_after_match=True)
            for i,name in enumerate(sorted(package.PARTITIONS),1)]
        baseline=dict(schema='note10-v132-private-xnu-package-v1',version='v132',cycle='3'*32,build_evidence_id='4'*32,diagnostic_BOOT_sha256='2'*64,rollback_BOOT_sha256='1'*64,bootloader='synthetic',partitions=rows)
        ledger=dict(schema='note10-v132-owned-XNU-ledger-v1',recovery_returned=True,host_BOOT_write_attempts=1,host_reboot_attempts=1,internal_kexec_load_attempts_observed=1,internal_kexec_REBOOT_attempts_observed=1,cycle='3'*32,build_evidence_id='4'*32,normal_recovery_fallback_observed=False,status='cycle-complete-XNU-proof-limits-retained')
        backup=dict(complete=True,partition_writes=False,partitions=rows,bootloader='synthetic')
        assert package.current_and_restore(baseline,ledger,backup)[0]=='2'*64
        reject(lambda:package.current_and_restore(dict(baseline,version='v131'),ledger,backup))
        bad=json.loads(json.dumps(candidate));bad['retained_source_commit']='0'*40;reject(lambda:continuation(bad,current))
        bad=json.loads(json.dumps(candidate));bad['delta_NEW_PASS']['source_sha256'][NEW_FILES[0]]='0'*64;reject(lambda:continuation(bad,current))
        if source_pins()!=current:raise ValueError('SCORE source changed during NEW batch')
        result.update(passed=True,cases=['native open/sysfs power/boot sticky lifetime and admission','all28 sysfs and3 profiler callbacks frozen/drained with actual representative wrappers','native lock/IRQ/worker/state refusal','exact native resume does not boot','owned PM/clock and errno boundaries','bounded TS/BARON cache+interrupt halt','all4 DMA native busybit12 and same-read detail','foreign gate user and resource extent refuse','cached exact-device proof has no PM/MMIO','duplicate/unbind/late state refuse','fresh133 contracts and bounded decode','retained132 PASS without replay'])
    except Exception:
        import traceback
        result['error']=traceback.format_exc()
    save(out/'result.json',result)
    if result['passed']:
        candidate['delta_NEW_PASS']['result_sha256']=sha(out/'result.json');continuation(candidate,current)
        save(out/'public-score-terminal-continuation.json',candidate)
        (out/'public-score-terminal-continuation.b64').write_text(base64.b64encode(json.dumps(candidate,sort_keys=True,separators=(',',':')).encode()).decode(),encoding='ascii',newline='\n')
    return 0 if result['passed'] else 1

if __name__=='__main__':raise SystemExit(main())
