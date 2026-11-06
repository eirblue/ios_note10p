"""One NEW aggregate DPU ownership/lifetime/ACK/protocol batch; no old suites."""
import argparse
import json
from pathlib import Path
import re
import subprocess
import sys
sys.dont_write_bytecode=True
from v130_contract import ROOT,private,ordinary,digest,hexid,save
from v135_metadata import encode_public
import v138_prepare as prepare
import v138_build as build
import v138_package as package
import v138_cycle as cycle
HERE=Path(__file__).resolve().parent
CURRENT_HEADER_SHA='848c2a2e0a262d970e60e201fbcbea7cac82d374ef665da4c666283f27595f54'
PRIOR_FILE_SHA='3d7a1e9123f01ee9529417f496ac685e91f6fbc10f0f1a2ce8d5ba514c8c9e2a'
PRIOR_RESULT_SHA='31232f7eef785434ba8a5a6fcc9953cb6b30b001dbbb37c28988a5ff4db78ba7'
TYPE_PINS={'drivers/video/fbdev/exynos/dpu20/cal_9820/regs-decon.h': '1ad3d6fe2a637d045de4ff4f675a586339c1838cf0172053e3d5ff3bd8a87f56', 'drivers/video/fbdev/exynos/dpu20/cal_9820/regs-dpp.h': '25b34bfd038b40add1b87603e748683868f73bf8a1bf5cbc92dabbda84541917', 'drivers/video/fbdev/exynos/dpu20/cal_9820/decon_cal.h': 'f8c49aff72a3087084f37ad5fc8bfbec82a78f4e3135acb922471b1090b03e1b', 'drivers/video/fbdev/exynos/dpu20/panels/decon_lcd.h': '89be066d47fb5fe2c9487ab736ccf643b37758270bdef2e3717c74f9168f7c54'}
C_PREFIX=r'''
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stddef.h>
#include <string.h>
#include <errno.h>
#undef ESHUTDOWN
#define ESHUTDOWN 108
#undef EHOSTDOWN
#define EHOSTDOWN 112
#undef ETIMEDOUT
#define ETIMEDOUT 110
#undef EALREADY
#define EALREADY 114
typedef uint32_t u32;
typedef uint64_t u64;
typedef int64_t s64;
typedef uintptr_t resource_size_t;
#define __maybe_unused __attribute__((unused))
#define ARRAY_SIZE(a) (sizeof(a)/sizeof((a)[0]))
#define READ_ONCE(x) (x)
#define WRITE_ONCE(x,v) ((x)=(v))
#define smp_store_release(p,v) (*(p)=(v))
#define smp_load_acquire(p) (*(p))
#define pr_emerg(...) ((void)0)
#define N10_KEXEC_BUILD_ID "0123456789abcdef0123456789abcdef"
struct task_struct {int id;};
static struct task_struct first_task={1},foreign_task={2};
static struct task_struct *fixture_task=&first_task;
static struct task_struct *get_current(void){return fixture_task;}
/* N138_CURRENT_MACRO */
static bool fixture_interrupt;
static bool in_interrupt(void){return fixture_interrupt;}
static s64 fixture_time;
static s64 ktime_get_ns(void){return fixture_time;}
static void udelay(unsigned int us){fixture_time+=(s64)us*1000;}
struct mutex {bool held;};
#define DEFINE_MUTEX(n) struct mutex n={false}
static int mutex_trylock(struct mutex *p){if(p->held)return 0;p->held=true;return 1;}
static void mutex_lock(struct mutex *p){assert(mutex_trylock(p));}
static void mutex_unlock(struct mutex *p){assert(p->held);p->held=false;}
typedef struct {bool held;} spinlock_t;
#define DEFINE_SPINLOCK(n) spinlock_t n={false}
#define spin_lock_irqsave(p,f) do{assert(!(p)->held);(f)=0;(p)->held=true;}while(0)
#define spin_unlock_irqrestore(p,f) do{assert((p)->held);(void)(f);(p)->held=false;}while(0)
#define spin_trylock_irqsave(p,f) ({bool available=!(p)->held;(f)=0;if(available)(p)->held=true;available;})
struct list_head {bool empty;};
static bool list_empty(const struct list_head *p){return p->empty;}
struct kthread_work {int unused;};
struct kthread_worker {spinlock_t lock;struct list_head work_list,delayed_work_list;struct kthread_work *current_work;};
struct timer_list {bool pending;};
static int del_timer(struct timer_list *p){p->pending=false;return 1;}
static bool timer_pending(struct timer_list *p){return p->pending;}
struct work_struct {bool pending,busy;};
struct delayed_work {struct work_struct work;};
static bool cancel_work(struct work_struct *p){p->pending=false;return true;}
static bool cancel_delayed_work(struct delayed_work *p){return cancel_work(&p->work);}
static unsigned int work_busy(struct work_struct *p){return p->pending || p->busy;}
static unsigned int irq_disables;
static void disable_irq_nosync(unsigned int irq){assert(irq>0);irq_disables++;}
#define atomic_read(p) (*(p))
struct device_driver {int id;};
struct device_node {const char *compatible;int alias;bool available;u32 attr,port;};
struct resource {resource_size_t start,end;};
struct device {struct device_driver *driver;struct device_node *of_node;void *data;int references,usage;bool core_locked,active;};
struct platform_device {struct device dev;struct resource mem[3],irq[3];};
static struct platform_device devices[12];
static struct device_node nodes[13];
static unsigned int node_count,core_lock_calls,core_unlock_calls;
static struct device *get_device(struct device *dev){assert(dev);dev->references++;return dev;}
static bool device_trylock(struct device *dev){core_lock_calls++;if(dev->core_locked)return false;dev->core_locked=true;return true;}
static void device_unlock(struct device *dev){assert(dev->core_locked);core_unlock_calls++;dev->core_locked=false;}
static void *dev_get_drvdata(struct device *dev){assert(dev->core_locked);return dev->data;}
static const char *dev_name(struct device *dev){(void)dev;return "synthetic";}
static struct platform_device *to_platform_device(struct device *dev){return (struct platform_device *)dev;}
#define IORESOURCE_MEM 1
#define IORESOURCE_IRQ 2
static struct resource *platform_get_resource(struct platform_device *p,unsigned int kind,unsigned int index)
{assert(p->dev.core_locked);if(index>=3)return NULL;return kind==IORESOURCE_MEM?&p->mem[index]:&p->irq[index];}
static resource_size_t resource_size(struct resource *p){return p->end-p->start+1;}
static bool of_device_is_available(struct device_node *node){return node && node->available;}
static int of_alias_get_id(struct device_node *node,const char *alias){(void)alias;return node->alias;}
static void of_node_put(struct device_node *node){(void)node;}
static struct device_node *next_node(struct device_node *previous,const char *compatible)
{unsigned int index=previous?(unsigned int)(previous-nodes)+1:0;for(;index<node_count;index++)if(!strcmp(nodes[index].compatible,compatible))return &nodes[index];return NULL;}
#define for_each_compatible_node(n,t,c) for((n)=next_node(NULL,(c));(n);(n)=next_node((n),(c)))
static int of_property_read_u32(struct device_node *node,const char *name,u32 *value)
{if(!strcmp(name,"attr"))*value=node->attr;else if(!strcmp(name,"port"))*value=node->port;else return -EINVAL;return 0;}
static int pm_runtime_get_if_in_use(struct device *dev)
{assert(dev->core_locked);if(dev->active && dev->usage>0){dev->usage++;return 1;}return 0;}
static void pm_runtime_put_noidle(struct device *dev){assert(dev->usage>0);dev->usage--;}
#define IS_ERR_OR_NULL(p) (!(p) || (uintptr_t)(p)>(uintptr_t)-4096)
static bool test_bit(unsigned int bit,const unsigned long *value){return (*value&(1UL<<bit))!=0;}
/* N138_NATIVE_ENUMS */
#include "regs-decon.h"
#include "regs-dpp.h"
struct decon_mode_info {enum decon_psr_mode psr_mode;enum decon_trig_mode trig_mode;enum decon_out_type out_type;enum decon_dsi_mode dsi_mode;};
struct decon_lcd {unsigned int fps;};
struct update {struct mutex lock;struct list_head list;void *thread;struct kthread_worker worker;int remaining_frame;};
struct hibernation {bool enabled;struct mutex lock;struct kthread_worker worker;int remaining_hiber;};
struct decon_device {int id,state;struct device *dev;struct {int out_type,psr_mode,trig_mode,dsi_mode,out_idx[2];} dt;struct {void *regs,*ss_regs;int irq;} res;
 struct mutex pwr_state_lock,lock,pm_lock;struct {struct mutex lock;} cursor;struct update up;struct hibernation hiber,doze_hiber;
 unsigned long prev_used_dpp,cur_using_dpp,dpp_err_stat;u32 prev_protection_bitmask;bool up_list_saved;struct decon_lcd *lcd_info;};
struct dpp_config {u32 token;};
struct v4l2_subdev {void *data;};
struct dpp_device {int id,port,state;unsigned long attr;struct device *dev;struct v4l2_subdev sd;struct mutex lock;
 struct {void *dma_regs,*regs,*dma_com_regs;int dma_irq,irq;} res;struct {struct timer_list op_timer;} d;
 struct dpp_config *dpp_config,n138_saved_config;};
struct displayport_device {struct device *dev;int state;struct {void *link_regs,*phy_regs;int irq;} res;
 struct mutex hpd_lock,training_lock,cmd_lock,aux_lock,hdcp2_lock;void *dp_wq,*hdcp2_wq;
 struct delayed_work hpd_plug_work,hpd_unplug_work,hpd_irq_work,hdcp13_work,hdcp22_work,hdcp13_integrity_check_work,notifier_register_work;};
struct dsim_device {int id,state;struct device *dev;struct {void *regs,*phy_regs,*phy_regs_ex;int irq;} res;struct mutex cmd_lock;
 void *wq;struct timer_list cmd_timer;struct work_struct wr_timeout_work;};
static struct decon_device decons[3],*decon_drvdata[3];
static struct dpp_device dpps[6],*dpp_drvdata[7];
static struct displayport_device dp,*displayport_drvdata;
static struct dsim_device dsim,*dsim_drvdata[2];
static struct decon_lcd lcds[3];
static struct {struct device_driver driver;} decon_driver={{1}},dpp_driver={{2}},displayport_driver={{3}},dsim_driver={{4}};
static void *v4l2_get_subdevdata(struct v4l2_subdev *sd){return sd->data;}
static unsigned int configurations;
static int dpp_set_config(struct dpp_device *dpp){assert(dpp->lock.held);dpp->state=DPP_STATE_ON;configurations++;return 0;}
static void decon_to_psr_info(struct decon_device *decon,struct decon_mode_info *psr)
{psr->psr_mode=(enum decon_psr_mode)decon->dt.psr_mode;psr->trig_mode=(enum decon_trig_mode)decon->dt.trig_mode;psr->out_type=(enum decon_out_type)decon->dt.out_type;psr->dsi_mode=(enum decon_dsi_mode)decon->dt.dsi_mode;}
#define PMUCAL_READ 0
struct pmucal_seq {u32 access_type;uintptr_t base_pa;void *base_va;u32 offset,mask;};
struct pmucal_dbg_info {u32 emul_offset,emul_bit,emul_en,emul_enabled;};
struct pmucal_pd {u32 id;const char *name;struct pmucal_seq *status;u32 num_status;struct pmucal_dbg_info *dbg;};
static struct pmucal_pd pmucal_pd_list[7];
static unsigned int pmucal_pd_list_size=7;
static struct pmucal_seq status3;
static struct pmucal_dbg_info debug3;
static u32 pmu[0x3000/4];
static unsigned int pmu_reads,mmio_reads,mmio_writes,dpp_resets,decon_resets,pll_wakes,shared_te_clears;
static u32 readl(void *address){uintptr_t offset=(uintptr_t)address-(uintptr_t)pmu;assert(offset<sizeof(pmu));pmu_reads++;return *(u32 *)address;}
static int recorded_result,last_gate_error;
static int n130_dma_record(struct device *owner,int error){assert(owner==dp.dev);recorded_result=error;return error;}
static void n131_gate_refused(const char *stage,int error,struct device *owner){assert(stage);(void)owner;last_gate_error=error;}
static int downstream_error;
static int n130_iommu_prepare(void){return downstream_error;}
#include "native-cal.inc"
#include "v138-display.c"
static u32 idma_enable[6],dpp_enable[6],decon_control[3];
static bool hold_idma_reset,hold_dpp_reset,hold_decon_run,hold_decon_reset,allow_instant;
static bool deny_read,deny_write;
static unsigned int deny_family=N138_DPP;
static unsigned int sabotage_shared;
static bool fixture_write(unsigned int family,unsigned int id,u32 reg)
{
 bool allowed;
 if(deny_write && family==deny_family){deny_write=false;allowed=n138_access_begin(99,id);}
 else allowed=family==N138_DPP?n138_dpp_write_begin(id,reg):n138_access_begin(family,id);
 if(!allowed)return false;
 mmio_writes++;n138_user_end();return true;
}
static u32 fixture_read(unsigned int family,unsigned int id,u32 value)
{
 bool allowed;
 if(deny_read && family==deny_family){deny_read=false;allowed=n138_access_begin(99,id);}
 else allowed=n138_access_begin(family,id);
 if(!allowed)return 0; /* Deliberately dangerous zero: sticky fault must win. */
 if(family==N138_DPP)assert((n136_reserved_domains&8) &&
   ((n138_slots[10].pm_owned && dsim.state==DSIM_STATE_ON && dsim.dev->usage>0) ||
    (n138_slots[9].pm_owned && dp.state==DISPLAYPORT_STATE_ON && dp.dev->usage>0)));
 mmio_reads++;n138_user_end();return value;
}
static u32 dma_read(u32 id,u32 reg){assert(reg==IDMA_ENABLE);return fixture_read(N138_DPP,id,hold_idma_reset?idma_enable[id]:0);}
static u32 dpp_read(u32 id,u32 reg){assert(reg==DPP_ENABLE);return fixture_read(N138_DPP,id,hold_dpp_reset?dpp_enable[id]:0);}
static void idma_reg_set_sw_reset(u32 id){if(fixture_write(N138_DPP,id,IDMA_ENABLE)){idma_enable[id]=IDMA_SRESET;dpp_resets++;}}
static void dpp_reg_set_sw_reset(u32 id){if(fixture_write(N138_DPP,id,DPP_ENABLE))dpp_enable[id]=DPP_SRSET;}
static void idma_reg_clear_irq(u32 id,u32 value){(void)value;(void)fixture_write(N138_DPP,id,IDMA_IRQ);}
static void idma_reg_set_irq_mask_all(u32 id,u32 value){(void)value;(void)fixture_write(N138_DPP,id,IDMA_IRQ);}
static void dpp_reg_clear_irq(u32 id,u32 value){(void)value;(void)fixture_write(N138_DPP,id,DPP_IRQ);}
static void dpp_reg_set_irq_mask_all(u32 id,u32 value){(void)value;(void)fixture_write(N138_DPP,id,DPP_IRQ);}
static void odma_reg_clear_irq(u32 id,u32 value){(void)id;(void)value;assert(false);}
static void odma_reg_set_irq_mask_all(u32 id,u32 value){(void)id;(void)value;assert(false);}
static void odma_reg_set_sw_reset(u32 id){(void)id;assert(false);}
static void wb_mux_reg_set_sw_reset(u32 id){(void)id;assert(false);}
static int odma_reg_wait_sw_reset_status(u32 id){(void)id;assert(false);return -ENODEV;}
static int wb_mux_reg_wait_sw_reset_status(u32 id){(void)id;assert(false);return -ENODEV;}
#define dpp_err(...) ((void)0)
static u32 decon_reg_get_run_status(u32 id){return fixture_read(N138_DECON,id,decon_control[id]&GLOBAL_CONTROL_RUN_STATUS)?1:0;}
static u32 decon_read(u32 id,u32 reg){assert(reg==GLOBAL_CONTROL);return fixture_read(N138_DECON,id,decon_control[id]);}
static void decon_write_mask(u32 id,u32 reg_id,u32 val,u32 mask)
{
 struct task_struct *saved_task=fixture_task;bool saved_irq=fixture_interrupt,allowed;
 if(reg_id==CLOCK_CONTROL_0){
  if(sabotage_shared==1)mask^=CLOCK_CONTROL_0_TE_QACTIVE_PLL_ON;
  if(sabotage_shared==2)n138_shared_te_end();
  if(sabotage_shared==3)fixture_interrupt=true;
  if(sabotage_shared==4)fixture_task=&foreign_task;
 }
 allowed=/* N138_SHARED_GATE */;
 fixture_task=saved_task;fixture_interrupt=saved_irq;
 if(!allowed)return;
 mmio_writes++;n138_user_end();
 if(reg_id==GLOBAL_CONTROL){decon_resets++;decon_control[id]=(decon_control[id]&~mask)|(val&mask);if(!hold_decon_reset)decon_control[id]&=~GLOBAL_CONTROL_SRESET;}
 else if(reg_id==PLL_SLEEP_CONTROL)pll_wakes++;
 else {assert(reg_id==CLOCK_CONTROL_0);shared_te_clears++;}
}
#define decon_err(...) ((void)0)
#define decon_info(...) ((void)0)
static int decon_reg_wait_run_is_off_timeout(u32 id,unsigned long timeout);
static void decon_reg_set_int(u32 id,struct decon_mode_info *psr,u32 value){(void)psr;(void)value;(void)fixture_write(N138_DECON,id,GLOBAL_CONTROL);}
static int decon_reg_stop_perframe(u32 id,u32 dsi,struct decon_mode_info *psr,u32 fps)
{(void)dsi;if(fixture_write(N138_DECON,id,GLOBAL_CONTROL) && !hold_decon_run)decon_control[id]&=~GLOBAL_CONTROL_RUN_STATUS;
 if(psr->out_type==DECON_OUT_DP)(void)fixture_write(N138_DP,0,0);
 return decon_reg_wait_run_is_off_timeout(id,(1000/fps*12/10+5)*1000);}
static int decon_reg_stop_inst(u32 id,u32 dsi,struct decon_mode_info *psr,u32 fps)
{bool previous=hold_decon_run;int error;if(allow_instant)hold_decon_run=false;error=decon_reg_stop_perframe(id,dsi,psr,fps);hold_decon_run=previous;return error;}
static void decon_reg_clear_int_all(u32 id){(void)fixture_write(N138_DECON,id,GLOBAL_CONTROL);}
/* N138_CHANGED_NATIVE_POLLS */
#define N138_DECON_NATIVE
#define N138_DPP_NATIVE
#define N138_DP_NATIVE
#define N138_DSIM_NATIVE
#define N138_DECON_CAL
#define N138_DPP_CAL
#include "v138_display_native.inc"
/* N138_CHANGED_AFTER_SHUTDOWN */
'''
C_MAIN=r'''
static void memory(struct resource *res,resource_size_t start,resource_size_t bytes)
{res->start=start;res->end=start+bytes-1;}
static void worker(struct kthread_worker *value)
{memset(value,0,sizeof(*value));value->work_list.empty=true;value->delayed_work_list.empty=true;}
static void native_device(unsigned int slot,const char *compatible,int alias,struct device_driver *driver,void *object)
{
 unsigned int index;struct device *dev=&devices[slot].dev;
 nodes[slot]=(struct device_node){compatible,alias,true,0,0};
 dev->driver=driver;dev->of_node=&nodes[slot];dev->data=object;dev->references=1;dev->core_locked=true;
 for(index=0;index<3;index++)memory(&devices[slot].irq[index],400+slot*3+index,1);
}
static void register_native(unsigned int family,unsigned int id,struct device *dev,void *object,bool finish)
{
 assert(dev->core_locked);
 assert(n138_probe(family,id,dev,object,family==N138_DPP?&((struct dpp_device *)object)->sd:NULL)==0);
 assert(n138_resources(family,id,object)==0);
 if(finish){assert(n138_ready(family,id,object)==0);n138_probe_result(dev,true);dev->core_locked=false;}
}
static void setup(bool domain_on,bool complete_primary)
{
 static const u32 dma[]={0x19071000,0x19076000,0x19072000,0x19075000,0x19073000,0x19074000};
 static const u32 dppbase[]={0x19021000,0x19026000,0x19022000,0x19024000,0x19023000,0x19025000};
 static const unsigned long attrs[]={0x50007,0x5007f,0x50007,0x50017,0x50016,0x50036};
 static u32 mapped[12];unsigned int index;
 fixture_task=&first_task;fixture_interrupt=false;fixture_time=0;
 memset(n138_slots,0,sizeof(n138_slots));memset(n138_dpp_writer,0,sizeof(n138_dpp_writer));
 memset(n138_contexts,0,sizeof(n138_contexts));n138_aborting=false;
 n138_active=n138_history=0;n138_closed=n138_seen=n138_complete=n138_cal_reserved=false;
 n138_final_seen=false;n138_final_result=n138_result=-ENODEV;n138_fault_errno=0;n138_core_owner=NULL;
 n138_proof_task=NULL;n138_selected_family=n138_selected_id=-1;n138_link_access=n138_shared_te=false;n138_polls=0;n138_deadline=0;
 memset(&n138_detail,0,sizeof(n138_detail));memset(&n138_witness,0,sizeof(n138_witness));n138_lock.held=false;
 n136_closed_domains=n136_reserved_domains=0;n136_cal_lock.held=false;n136_cal_state_lock.held=false;
 memset(pmu,0,sizeof(pmu));status3=(struct pmucal_seq){PMUCAL_READ,0x15860000,pmu,0x1e04,1};
 debug3=(struct pmucal_dbg_info){0x1e0c,0,0,0};
 pmucal_pd_list[3]=(struct pmucal_pd){3,"blkpwr_dpu",&status3,1,&debug3};
 pmu[0x1e00/4]=pmu[0x1e04/4]=domain_on?1:0;
 memset(devices,0,sizeof(devices));memset(nodes,0,sizeof(nodes));node_count=12;
 for(index=0;index<12;index++)nodes[index].compatible="absent";
 memset(decons,0,sizeof(decons));memset(decon_drvdata,0,sizeof(decon_drvdata));
 memset(dpps,0,sizeof(dpps));memset(dpp_drvdata,0,sizeof(dpp_drvdata));
 memset(&dp,0,sizeof(dp));memset(&dsim,0,sizeof(dsim));memset(dsim_drvdata,0,sizeof(dsim_drvdata));
 irq_disables=core_lock_calls=core_unlock_calls=configurations=0;
 pmu_reads=mmio_reads=mmio_writes=dpp_resets=decon_resets=pll_wakes=shared_te_clears=0;
 recorded_result=last_gate_error=downstream_error=0;
 memset(idma_enable,0,sizeof(idma_enable));memset(dpp_enable,0,sizeof(dpp_enable));memset(decon_control,0,sizeof(decon_control));
 hold_idma_reset=hold_dpp_reset=hold_decon_run=hold_decon_reset=allow_instant=false;deny_read=deny_write=false;deny_family=N138_DPP;sabotage_shared=0;
 for(index=0;index<6;index++){
  struct dpp_device *dpp=&dpps[index];unsigned int slot=3+index;
  native_device(slot,"samsung,exynos9-dpp",(int)index,&dpp_driver.driver,dpp);
  dpp->id=(int)index;dpp->port=(int)(index/2);dpp->dev=&devices[slot].dev;dpp->attr=attrs[index];dpp->state=DPP_STATE_ON;
  dpp->sd.data=dpp;dpp_drvdata[index]=dpp;nodes[slot].attr=(u32)attrs[index];nodes[slot].port=index/2;
  memory(&devices[slot].mem[0],dma[index],0x1000);memory(&devices[slot].mem[1],dppbase[index],0x1000);
  dpp->res.dma_regs=dpp->res.regs=&mapped[slot];dpp->res.dma_irq=(int)devices[slot].irq[0].start;dpp->res.irq=(int)devices[slot].irq[1].start;
  if(index==0){memory(&devices[slot].mem[2],0x19070000,0x110);dpp->res.dma_com_regs=&mapped[slot];}
  register_native(N138_DPP,index,dpp->dev,dpp,true);
 }
 native_device(9,"samsung,exynos-displayport",0,&displayport_driver.driver,&dp);dp.dev=&devices[9].dev;displayport_drvdata=&dp;
 memory(&devices[9].mem[0],0x130b0000,0xffff);memory(&devices[9].mem[1],0x10ae0000,0x20cc);
 dp.res.link_regs=dp.res.phy_regs=&mapped[9];dp.res.irq=(int)devices[9].irq[0].start;dp.dp_wq=dp.hdcp2_wq=&mapped[9];dp.state=DISPLAYPORT_STATE_INIT;
 dp.notifier_register_work.work.pending=true;register_native(N138_DP,0,dp.dev,&dp,true);
 native_device(10,"samsung,exynos9-dsim",0,&dsim_driver.driver,&dsim);dsim.dev=&devices[10].dev;dsim_drvdata[0]=&dsim;
 memory(&devices[10].mem[0],0x19080000,0x300);memory(&devices[10].mem[1],0x19161000,0x800);memory(&devices[10].mem[2],0x19160000,0x100);
 dsim.res.regs=dsim.res.phy_regs=dsim.res.phy_regs_ex=&mapped[10];dsim.res.irq=(int)devices[10].irq[0].start;dsim.wq=&mapped[10];
 dsim.state=DSIM_STATE_ON;dsim.dev->active=true;dsim.dev->usage=domain_on?1:0;register_native(N138_DSIM,0,dsim.dev,&dsim,true);
 for(index=0;index<3;index+=2){
  struct decon_device *decon=&decons[index];native_device(index,"samsung,exynos9-decon",(int)index,&decon_driver.driver,decon);
  decon->id=(int)index;decon->dev=&devices[index].dev;decon_drvdata[index]=decon;
  decon->state=DECON_STATE_ON;decon->dt.out_type=index?DECON_OUT_DP:DECON_OUT_DSI;decon->dt.psr_mode=index?DECON_VIDEO_MODE:DECON_MIPI_COMMAND_MODE;
  memory(&devices[index].mem[0],index?0x19050000:0x19030000,0x10000);decon->res.regs=decon->res.ss_regs=&mapped[index];decon->res.irq=800+(int)index;
  worker(&decon->up.worker);decon->up.list.empty=true;decon->up.thread=&mapped[index];lcds[index].fps=60;decon->lcd_info=&lcds[index];
  register_native(N138_DECON,index,decon->dev,decon,index || complete_primary);
 }
}
static void borrow_primary(void)
{
 struct dpp_config request={7};
 assert(n138_owned_config(&decons[0],&dpps[0].sd,&request)==0);
 assert(dpps[0].dpp_config==&dpps[0].n138_saved_config && dpps[0].dpp_config!=&request);
 request.token=99;assert(dpps[0].dpp_config->token==7);
 decons[0].cur_using_dpp=decons[0].prev_used_dpp=1;
 assert(!n138_dpp_writer[0] && !dpps[0].lock.held && !n138_active);
}
static void all_core_unlocked(void)
{unsigned int i;for(i=0;i<12;i++)assert(!devices[i].dev.core_locked);}
static int released_resource(void){assert(n138_history&4);return 7;}
int main(void)
{
 unsigned int i,before;struct dpp_config request={11};struct decon_mode_info psr={DECON_MIPI_COMMAND_MODE,DECON_HW_TRIG,DECON_OUT_DSI,DSI_MODE_SINGLE};
 assert(current==&first_task);
 /* Exact current probe task may configure only after validated resources;
  * terminal proof still waits for the actual native return callback. */
 setup(true,false);borrow_primary();
 assert(n138_slots[0].lifetime==N138_RESOURCES && !n138_slots[0].probe_completed);
 assert(n138_ready(N138_DECON,0,&decons[0])==0);n138_probe_result(decons[0].dev,true);decons[0].dev->core_locked=false;
 assert(n138_slots[0].probe_completed && n138_slots[3].borrower==&decons[0]);
 setup(true,false);fixture_task=&foreign_task;
 assert(n138_owned_config(&decons[0],&dpps[0].sd,&request)==-EPERM && !configurations);
 fixture_task=&first_task;n138_probe_result(decons[0].dev,false);decons[0].dev->core_locked=false;
 assert(n138_slots[0].lifetime==N138_INVALID && n138_display_prepare()==-EBUSY && !mmio_reads && !mmio_writes);
 setup(true,false);n138_slots[0].lifetime=N138_PROBING;
 assert(n138_owned_config(&decons[0],&dpps[0].sd,&request)==-EPERM && !configurations);
 setup(true,false);borrow_primary();n138_probe_result(decons[0].dev,false);decons[0].dev->core_locked=false;
 decons[0].dev->data=NULL;n138_slots[0].object=(void *)(uintptr_t)1;
 assert(n138_display_prepare()==-EBUSY && !mmio_reads && !mmio_writes);
 /* Atomic admitted-before, unknown resources, lease and secure histories. */
 setup(true,true);assert(n138_user_begin());assert(n138_display_prepare()==-EBUSY);
 assert(n138_user_begin());n138_user_end();
 fixture_interrupt=true;assert(!n138_user_begin());fixture_interrupt=false;
 fixture_task=&foreign_task;assert(!n138_user_begin());fixture_task=&first_task;
 n138_user_end();assert(!n138_active && !mmio_writes && !n138_witness.committed);
 setup(true,true);nodes[12]=(struct device_node){"samsung,exynos9-dpp",6,true,0,0};node_count=13;
 assert(n138_display_prepare()==-ENODEV && !mmio_writes);all_core_unlocked();
 setup(true,true);dpps[0].res.irq++;
 assert(n138_display_prepare()==-ENODEV && !irq_disables && !mmio_writes);all_core_unlocked();
 setup(true,true);assert(N138_INVALIDATE_BEFORE(released_resource())==7);
 assert(n138_display_prepare()==-EBUSY && !mmio_reads && !mmio_writes);
 setup(true,true);borrow_primary();assert(n138_owned_config(&decons[2],&dpps[0].sd,&request)==-EPERM);
 assert(n138_slots[3].borrower==&decons[0] && n138_display_prepare()==-EBUSY && !mmio_writes);
 setup(true,true);dpps[0].dev->core_locked=true;
 assert(n138_owned_config(&decons[0],&dpps[0].sd,&request)==-EBUSY && dpps[0].dev->core_locked && !configurations);
 dpps[0].dev->core_locked=false;all_core_unlocked();
 setup(true,true);borrow_primary();decons[2].cur_using_dpp=1;
 assert(n138_display_prepare()==-EPERM && !mmio_writes);all_core_unlocked();
 setup(true,true);assert(n138_secure_begin());n138_user_end();assert(n138_display_prepare()==-EBUSY && !mmio_writes);
 /* No software OFF inference: all six unborrowed driver-owned channels
  * receive their native ACK on a live-domain route. */
 setup(true,true);for(i=0;i<6;i++)dpps[i].state=DPP_STATE_OFF;
 decon_control[0]=GLOBAL_CONTROL_RUN_STATUS;
 assert(n138_display_prepare()==0 && dpp_resets==6 && decon_resets==1 && pll_wakes==1 && recorded_result==0);
 assert(n138_witness.type==N138_DPU_NATIVE_STOP_FROZEN && n138_witness.domains==8);
 assert(!dp.notifier_register_work.work.pending && dsim.dev->usage==1 && dsim.dev->references==2);
 all_core_unlocked();for(i=0;i<6;i++)assert(n138_slots[3+i].stopped);
 assert(n138_display_final()==0);before=core_lock_calls;
 assert(n138_display_final()==0 && core_lock_calls==before);
 fixture_task=&foreign_task;assert(n138_display_final()==-EPERM && n138_display_unwind()==-EPERM);
 fixture_task=&first_task;assert(n138_display_unwind()==0);all_core_unlocked();assert(!n138_user_begin());
 setup(true,true);dp.state=DISPLAYPORT_STATE_ON;dp.dev->active=true;dp.dev->usage=1;decon_control[2]=GLOBAL_CONTROL_RUN_STATUS;
 assert(n138_display_prepare()==0 && shared_te_clears==1 && dpp_resets==6 && dsim.dev->usage==1 && dp.dev->usage==1);
 for(i=1;i<=4;i++){
  setup(true,true);borrow_primary();dp.state=DISPLAYPORT_STATE_ON;dp.dev->active=true;dp.dev->usage=1;
  decon_control[2]=GLOBAL_CONTROL_RUN_STATUS;sabotage_shared=i;
  assert(n138_display_prepare()==-EACCES && !shared_te_clears && !dpp_resets && !n138_witness.committed);
  assert(n138_slots[3].borrower==&decons[0] && !strcmp(n138_detail.reason,"proof-access-denied"));
 }
 /* Completed PMU OFF skips every DPU/DP SFR, regardless software states. */
 setup(false,true);assert(n138_display_prepare()==0 && pmu_reads==3 && !mmio_reads && !mmio_writes);
 assert(n138_witness.type==N138_DPU_DOMAIN_OFF_FROZEN);
 setup(true,true);pmu[0x1e04/4]=0;assert(n138_display_prepare()==-EIO && !mmio_reads && !mmio_writes);
 setup(false,true);debug3.emul_enabled=1;assert(n138_display_prepare()==-EBUSY && !mmio_reads && !mmio_writes);
 setup(true,true);dsim.dev->usage=0;assert(n138_display_prepare()==-EHOSTDOWN && !mmio_reads && !mmio_writes);
 setup(true,true);dsim.state=DSIM_STATE_INIT;assert(n138_display_prepare()==-EHOSTDOWN && !mmio_reads && !mmio_writes);
 setup(true,true);dp.hpd_plug_work.work.busy=true;assert(n138_display_prepare()==-EBUSY && !mmio_writes);
 setup(true,true);decons[0].up.remaining_frame=1;assert(n138_display_prepare()==-EBUSY && !mmio_writes);
 /* First native errno and bounded same-read detail, no next-channel reset. */
 setup(true,true);borrow_primary();hold_decon_run=true;decon_control[0]=GLOBAL_CONTROL_RUN_STATUS;
 assert(n138_display_prepare()==-EBUSY && !dpp_resets && !strcmp(n138_detail.reason,"decon-run-off"));
 assert(n138_slots[3].borrower==&decons[0] && n138_detail.state==1 && last_gate_error==-EBUSY);
 setup(true,true);hold_decon_run=allow_instant=hold_decon_reset=true;decon_control[0]=GLOBAL_CONTROL_RUN_STATUS;
 assert(n138_display_prepare()==-EBUSY && !dpp_resets && !strcmp(n138_detail.reason,"decon-reset"));
 setup(true,true);borrow_primary();hold_idma_reset=true;
 assert(n138_display_prepare()==-ETIMEDOUT && dpp_resets==1 && fixture_time<=250000000);
 assert(n138_slots[3].borrower==&decons[0] && !n138_slots[3].stopped && !n138_witness.committed);
 setup(true,true);deny_read=true;deny_family=N138_DECON;
 assert(n138_display_prepare()==-EACCES && !dpp_resets && !n138_complete && !strcmp(n138_detail.reason,"proof-access-denied"));
 setup(true,true);borrow_primary();deny_read=true;
 assert(n138_display_prepare()==-EACCES && !n138_slots[3].stopped && n138_slots[3].borrower==&decons[0] && !n138_witness.committed);
 setup(true,true);borrow_primary();deny_write=true;
 assert(n138_display_prepare()==-EACCES && !dpp_resets && !n138_complete && n138_slots[3].borrower==&decons[0]);
 /* IRQ cannot inherit a proof task's privilege; foreign native stop entry
  * refuses before it can interpret a denied read as a reset-clear ACK. */
 setup(true,true);n138_closed=true;n138_proof_task=current;n138_selected_family=N138_DPP;n138_selected_id=0;
 fixture_interrupt=true;assert(!n138_access_begin(N138_DPP,0) && !n138_user_begin());
 assert(n138_native_dpp_stop(0,dpps[0].attr)==-EPERM && n138_native_decon_stop(0,&psr,60)==-EPERM);
 fixture_interrupt=false;assert(!mmio_reads && !mmio_writes);
 setup(true,true);n138_closed=true;n138_proof_task=current;n138_selected_family=N138_DECON;n138_selected_id=2;
 n138_slots[0].stopped=n138_slots[0].device_locked=true;
 assert(n138_shared_te_begin()==-EPERM && n138_history && !n138_shared_te && !mmio_reads && !mmio_writes);
 /* Core unbind cannot turn a pinned struct device into a private/devres pin. */
 setup(true,true);assert(n138_display_prepare()==0);n138_detach(dp.dev);dp.dev->driver=NULL;dp.dev->data=NULL;n138_slots[9].object=(void *)(uintptr_t)1;
 assert(n138_display_final()==-EPERM);all_core_unlocked();
 setup(true,true);assert(n138_display_prepare()==0);n138_slots[0].generation++;
 assert(n138_display_final()==-ENODEV);all_core_unlocked();
 setup(true,true);assert(n138_display_prepare()==0);dp.dev->core_locked=true;
 assert(n138_display_final()==-EBUSY && dp.dev->core_locked);dp.dev->core_locked=false;all_core_unlocked();
 setup(true,true);borrow_primary();assert(n138_display_prepare()==0);downstream_error=-EIO;
 assert(n130_after_shutdown()==-EIO);all_core_unlocked();
 assert(n138_closed && n136_cal_frozen(N138_DPU_DOMAINS) && n138_slots[3].borrower==&decons[0]);
 assert(n138_display_unwind()==0 && current==&first_task);return 0;
}
'''


KERNEL_SEED=b'''int n130_before_device_shutdown(void)
{
    int result=n130_dmaengine_prepare();
    if(result)n131_gate_refused("dma-provider",result,NULL);
    return result;
}
void n130_terminal_recovery(void)
{
    machine_restart("recovery");
}
int n130_after_shutdown(void)
{
    int result=0;
    if(!result)result=n130_iommu_prepare();
    return result;
}
int n10_kexec_final_return(const struct kimage *image)
{
    int result=0;
    if(result){n131_gate_refused("final",result,NULL);WRITE_ONCE(n130_arm_state,4);return result;}
    return result;
}
'''


def affected_render(stock):
    """One NEW overlay delta, with immutable137 boundary inputs as dependencies.

    Do not replay the accepted137/136 complete overlay renderer or its tests.
    The real CI uses prepare.install and the complete retained source chain.
    """
    cal=prepare.retained.cal_source((HERE/'v136_cal.inc').read_bytes())
    seed={name:stock[name] for name in prepare.NATIVE_PINS}
    seed.update({prepare.retained.CAL_PATH:cal,
        'include/linux/v130_kernel_api.h':(HERE/'v130_kernel_api.h').read_bytes(),
        'arch/arm64/mm/v130_kernel.c':KERNEL_SEED,
        'kernel/kexec_core.c':stock['kernel/kexec_core.c'],
        'arch/arm64/Kconfig':b' depends on EXYNOS_NPU && NPU_HARDWARE && NPU_INTERFACE && !NPU_LOOPBACK && !NPU_ZEBU_EMULATION\n'})
    original=prepare.retained.render
    prepare.retained.render=lambda inputs,identity,source128:dict(seed)
    try:return prepare.render(stock,'a'*32,HERE)
    finally:prepare.retained.render=original


def new_host_cases(output):
    # NEW source-qualified config/entry boundaries only, not old suites.
    prepare.profile(build.SETTINGS)
    wrong=dict(build.SETTINGS,EXYNOS_MIPI_DSIM='n')
    try:prepare.profile(wrong)
    except ValueError:pass
    else:raise AssertionError('new DSIM profile guard absent')
    for name in ('decon_core.c','cursor.c','decon_dsi.c'):
        raw=output[prepare.BASE+name]
        assert b'DPP_WIN_CONFIG, &dpp_config' not in raw
        assert b'n138_owned_config(decon,sd,&dpp_config)' in raw
    assert b'N138_INVALIDATE_BEFORE(kfree(dpp))' in output[prepare.BASE+'dpp_drv.c']
    for name in ('decon_probe','dpp_probe','displayport_probe','dsim_probe'):
        source_name={'decon_probe':'decon_core.c','dpp_probe':'dpp_drv.c','displayport_probe':'displayport_drv.c','dsim_probe':'dsim_drv.c'}[name]
        text,row=prepare.selected(output[prepare.BASE+source_name],name)
        wrapper=text[row[0]:row[2]]
        assert wrapper.index('n138_probe_result(&pdev->dev,n138_answer==0)')<wrapper.index('n138_user_end()')
    raw=output['arch/arm64/mm/v130_kernel.c']
    text,row=prepare.selected(raw,'n130_before_device_shutdown');body=text[row[0]:row[2]]
    assert body.index('n130_dmaengine_prepare()')<body.index('n138_display_prepare()')<body.index('return result;')
    text,row=prepare.selected(raw,'n130_after_shutdown');body=text[row[0]:row[2]]
    assert body.index('n138_display_final()')<body.index('n130_iommu_prepare()')<body.index('n138_display_unwind()')<body.index('return result;')
    assert b'(void)n138_display_unwind();\n#endif\n\tmutex_unlock(&kexec_mutex);' in output['kernel/kexec_core.c']
    api=output['include/linux/v130_kernel_api.h']
    assert all(('int '+name+'(void);').encode() in api for name in ('n138_display_prepare','n138_display_final','n138_display_unwind'))
    loader=build.pid1_source()
    assert set(re.findall(rb'N10XNU[0-9]+',loader))=={b'N10XNU138'}
    build_source=(HERE/'v138_build.py').read_text()
    assert build_source.index('        loader=pid1_source()')<build_source.index("(out/'v138_loader.c').write_bytes(loader)")<build_source.index("result['PID1_source_sha256']=digest(loader)")<build_source.index("'00-new-PID1'")
    workflow=(ROOT/build.WORKFLOW).read_text()
    assert '  v138-displayport-terminal:' in workflow and 'note10/device_test/v138_build.py' in workflow
    identity,cycle_id='a'*32,'b'*32
    prefix='N10XNU138 id='+identity+' cycle='+cycle_id+' stage='
    lines=prefix+'begin\n'+'N10XNU138 id='+identity+' terminal witness=6 domains=8 owner=synthetic\n'
    lines+='N10XNU138 id='+identity+' stage=display-dpp-reset errno=-110 owner=synthetic\n'
    lines+='N10XNU138 id='+identity+' display reason=idma-reset item=0 state=16777216 value=-110 aux=0 owner=synthetic\n'
    decoded=cycle.decode({'new':lines.encode()},identity,cycle_id)
    assert decoded['terminal_witness_commits']==[dict(type=6,domains=8,owner='synthetic')]
    assert decoded['gate_refusals']==[dict(stage='display-dpp-reset',errno=-110,owner='synthetic')]
    assert decoded['display_refusal_details'][0]['reason']=='idma-reset'
    assert not decoded['physical_XNU_entry_observed'] and not decoded['full_XNU_boot_observed']
    final='N10XNU138 id='+identity+' final_qualified=1 EL1_preserved=1 actual_XNU_pending=1\n'
    for barrier in ('N10XNU137 id='+identity+' cycle='+cycle_id+' stage=begin',
                    'N10XNU138 id='+'c'*32+' cycle='+cycle_id+' stage=begin',
                    'N10XNU138 id='+identity+' cycle='+'c'*32+' stage=begin',
                    prefix+'begin JUNK'):
        result=cycle.decode({'new':(lines+barrier+'\n'+final).encode()},identity,cycle_id)
        assert not result['final_hook_qualified_observed'] and not result['previous_boot_build_cycle_observed']
    overlong=lines.replace('reason=idma-reset','reason='+'a'*41)
    assert not cycle.decode({'new':overlong.encode()},identity,cycle_id)['display_refusal_details']
    invalid=lines.replace('witness=6 domains=8','witness=6 domains=64')
    assert not cycle.decode({'new':invalid.encode()},identity,cycle_id)['terminal_witness_commits']
    witness_lines=''.join('N10XNU138 id='+identity+' terminal witness='+str(kind)+' domains='+str(domains)+' owner=synthetic\n' for kind,domains in ((4,48),(3,6),(5,64),(6,8)))
    assert len(cycle.decode({'new':(prefix+'begin\n'+witness_lines).encode()},identity,cycle_id)['terminal_witness_commits'])==4
    # The newly advanced physical baseline is137/source79, not synthetic136.
    rows=[dict(partition=name,file=name+'.img',remote_hash_before_and_after_match=True,size=4096,block_node='/dev/block/sdz'+str(index+1),sha256='1'*64) for index,name in enumerate(sorted(package.PARTITIONS))]
    backup=dict(complete=True,partition_writes=False,partitions=rows,bootloader='synthetic')
    current=dict(schema='note10-v137-private-xnu-package-v1',version='v137',source_sha256=build.RETAINED_SOURCE_SHA256,
        cycle='a'*32,build_evidence_id='b'*32,rollback_BOOT_sha256='1'*64,diagnostic_BOOT_sha256='2'*64,partitions=rows,bootloader='synthetic')
    ledger=dict(schema='note10-v137-owned-XNU-ledger-v1',recovery_returned=True,host_BOOT_write_attempts=1,host_reboot_attempts=1,
        internal_kexec_load_attempts_observed=1,internal_kexec_REBOOT_attempts_observed=1,cycle=current['cycle'],build_evidence_id=current['build_evidence_id'],
        normal_recovery_fallback_observed=False,status='cycle-complete-XNU-proof-limits-retained')
    assert package.current_and_restore(current,ledger,backup)[0]=='2'*64
    for changed in (dict(current,schema='note10-v136-private-xnu-package-v1',version='v136'),dict(current,source_sha256={})):
        try:package.current_and_restore(changed,ledger,backup)
        except ValueError:pass
        else:raise AssertionError('new physical137 source role widened')


def native_pair(raw,name):
    text,row=prepare.selected(raw,name);wrapper=text[row[0]:row[2]]
    prototype=text[row[0]:row[1]].rstrip()+';\n'
    text,row=prepare.selected(raw,name+'_n138_native')
    return prototype+text[row[0]:row[2]]+'\n'+wrapper+'\n'


def enum_source(stock,path,name):
    raw=stock[path].decode()
    match=re.search(r'(?m)^enum '+re.escape(name)+r'\s*\{[^}]*\};',raw)
    if not match:raise ValueError('exact selected native enum absent: '+name)
    return match.group()+'\n'


def fixture_source(output,stock):
    enums=''
    for file_name,names in (
        ('decon.h',('decon_state',)),('dpp.h',('dpp_state','dpp_attr')),
        ('displayport.h',('displayport_state',)),('dsim.h',('dsim_state',)),
        ('cal_9820/decon_cal.h',('decon_trig_mode','decon_out_type','decon_dsi_mode')),
        ('panels/decon_lcd.h',('decon_psr_mode',))):
        for name in names:enums+=enum_source(stock,prepare.BASE+file_name,name)
    polls=''
    for file_name,names in (
        ('cal_9820/dpp_reg.c',('idma_reg_wait_sw_reset_status','dpp_reg_wait_sw_reset_status','dpp_reg_deinit')),
        ('cal_9820/decon_reg.c',('decon_reg_wait_run_is_off_timeout','decon_reg_reset','decon_reg_set_pll_wakeup','decon_reg_set_te_qactive_pll_mode'))):
        for name in names:polls+=native_pair(output[prepare.BASE+file_name],name)
    text,row=prepare.selected(output['arch/arm64/mm/v130_kernel.c'],'n130_after_shutdown')
    after=text[row[0]:row[2]]
    text,row=prepare.selected(output[prepare.BASE+'decon.h'],'decon_write_mask')
    guards=re.findall(r'(?m)^    if\(!(.+)\)return;$',text[row[0]:row[2]])
    if len(guards)!=1:raise ValueError('exact generated shared-RMW access predicate required')
    return (C_PREFIX.replace('/* N138_CURRENT_MACRO */','#define current get_current()')
        .replace('/* N138_NATIVE_ENUMS */',enums)
        .replace('/* N138_SHARED_GATE */',guards[0])
        .replace('/* N138_CHANGED_NATIVE_POLLS */',polls)
        .replace('/* N138_CHANGED_AFTER_SHUTDOWN */',after)+C_MAIN).encode()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('output','cc','retained-context','stock-source'):parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--retained-context-sha256',required=True);args=parser.parse_args()
    out=private(args.output);source_root=args.stock_source.absolute()
    if out.exists() or source_root!=source_root.resolve() or not source_root.is_dir():parser.error('fresh output and canonical selected public source directory required')
    prior_raw=ordinary(args.retained_context).read_bytes()
    if args.retained_context_sha256!=PRIOR_FILE_SHA or digest(prior_raw)!=hexid(args.retained_context_sha256):raise ValueError('exact accepted137 metadata required')
    previous=json.loads(prior_raw)
    if digest(json.dumps(previous,sort_keys=True,separators=(',',':')).encode())!=build.RETAINED_CONTEXT_SHA256 or previous['delta_NEW_PASS']['result_sha256']!=PRIOR_RESULT_SHA:
        raise ValueError('retained137 PASS binding differs')
    required=dict(prepare.NATIVE_PINS,**TYPE_PINS)
    required['kernel/kexec_core.c']=prepare.PINS['kernel/kexec_core.c']
    stock={}
    for name,pin in required.items():
        path=ordinary(source_root/name)
        if not path.is_relative_to(source_root):raise ValueError('selected source escapes root')
        raw=path.read_bytes()
        if digest(raw)!=pin:raise ValueError('selected new native source pin differs: '+name)
        stock[name]=raw
    current_source=build.source_pins();out.mkdir(parents=True)
    result=dict(schema='note10-v138-display-terminal-result-v1',scope=build.SCOPE,passed=False,
        source_sha256={name:current_source[name] for name in build.NEW_FILES},retained137_result_sha256=PRIOR_RESULT_SHA,
        retained137_source_map_sha256='e7b75fe507bb16856ad22b3dac696861f807ec6002d9c7d0994b14a1578fd8c1',
        retained_kernel_current_header_sha256=CURRENT_HEADER_SHA,retained_current_header_reads=0,
        NEW_overlay_delta_render_invocations=0,retained_overlay_render_invocations=0,NEW_host_invocations=0,
        compiler_invocations=0,fixture_processes=0,old_tests_replayed=0,Image_reads=0,raw_kernel_reads=0,
        adapter_reads=0,compressions=0,device_operations=[])
    def persist():(out/'result.json').write_bytes((json.dumps(result,indent=2)+'\n').encode())
    try:
        result['NEW_overlay_delta_render_invocations']=1;persist();output=affected_render(stock)
        # Durable private compile-input checkpoint BEFORE any fixture extraction.
        directory=out/'rendered-inputs';directory.mkdir();saved={}
        for name,raw in output.items():
            path=directory/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw)
            saved[name]=digest(raw)
        checkpoint=dict(schema='note10-v138-new-render-checkpoint-v1',source_sha256=current_source,
            mode='NEW delta over source-qualified minimal137 boundary seed; retained render0',fragments=saved)
        checkpoint_raw=(json.dumps(checkpoint,indent=2)+'\n').encode();(directory/'MANIFEST.json').write_bytes(checkpoint_raw)
        result.update(NEW_overlay_delta_passed=True,checkpoint_file='rendered-inputs/MANIFEST.json',checkpoint_sha256=digest(checkpoint_raw));persist()
        result['NEW_host_invocations']=1;persist();new_host_cases(output);result['NEW_host_cases_passed']=True;persist()
        generated=fixture_source(output,stock);source=out/'new-display-terminal.c';source.write_bytes(generated)
        result.update(generated_C_file=source.name,generated_C_sha256=digest(generated));persist()
        include=out/'include/linux';include.mkdir(parents=True)
        headers=('device.h','interrupt.h','ktime.h','of.h','pm_runtime.h','sched.h','spinlock.h','string.h','v130_kernel_api.h',
            'note10_legacy_kexec_build.h','err.h','of_address.h','platform_device.h','workqueue.h','mutex.h','smp.h','printk.h','types.h','errno.h')
        for name in headers:(include/name).write_bytes(b'/* synthetic selected native dependency */\n')
        (include/'v138_display.h').write_bytes(output['include/linux/v138_display.h'])
        (include/'v136_terminal.h').write_bytes((HERE/'v136_terminal.h').read_bytes())
        (out/'native-cal.inc').write_bytes(output[prepare.retained.CAL_PATH])
        (out/'v138-display.c').write_bytes(output[prepare.BASE+'v138_display.c'])
        (out/'v138_display_native.inc').write_bytes(output[prepare.BASE+'v138_display_native.inc'])
        for name in ('regs-decon.h','regs-dpp.h'):(out/name).write_bytes(stock[prepare.BASE+'cal_9820/'+name])
        macros=['-DCONFIG_'+key+'=1' for key,value in build.SETTINGS.items() if value=='y']
        executable=out/('new-display-terminal.exe' if sys.platform=='win32' else 'new-display-terminal')
        command=[str(ordinary(args.cc)),'-std=gnu11','-O2','-Wall','-Wextra','-Werror','-Wstrict-prototypes','-Wno-unused-function','-ferror-limit=0',*macros,'-I',str(out/'include'),str(source),'-o',str(executable)]
        result['compiler_invocations']=1;persist()
        with (out/'compile.log').open('xb') as log:subprocess.run(command,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=90)
        result['fixture_processes']=1;persist()
        with (out/'fixture.log').open('xb') as log:subprocess.run([str(executable)],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=20)
        result['passed']=True;result_raw=(json.dumps(result,indent=2)+'\n').encode()
        delta=dict(schema='note10-v138-displayport-terminal-pass-v1',scope=build.SCOPE,passed=True,result_sha256=digest(result_raw),source_sha256=result['source_sha256'])
        candidate=dict(schema='note10-v138-public-terminal-continuation-v1',scope=build.SCOPE,passed=True,retained_source_commit=build.RETAINED_COMMIT,
            retained_terminal_PASS=previous,delta_NEW_PASS=delta,source_sha256=current_source)
        build.continuation(candidate,current_source);encoded=encode_public(candidate)
        (out/'result.json').write_bytes(result_raw);save(out/'public-display-terminal-continuation.json',candidate)
        (out/'public-display-terminal-continuation.txt').write_bytes((encoded+'\n').encode('ascii'))
    except BaseException:
        import traceback
        result['error']=traceback.format_exc();persist();raise
    print(json.dumps(dict(passed=True,compiler_invocations=1,fixture_processes=1,old_tests_replayed=0)))


if __name__=='__main__':main()
