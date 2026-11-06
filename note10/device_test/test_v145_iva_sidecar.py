"""One future NEW authentic-body sidecar batch; execution belongs to ROOT."""
from pathlib import Path
import argparse
import hashlib
import json
import subprocess
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
from v145_iva_sidecar import CTRL, HELPER, CTRL_SHA256, patch_native, function_span

# Finalize these only from the actual successful144 result and retained ABI pin.
BUFFER_HELPER_SHA256 = 'ca9bc9f95a4828b6c12895c3e15d4d0818a92b01699084842e3efb60b7f62d30'
IOCTL_ABI_SHA256 = '9fe84e259160ba29ee72d343c56ed3e4023195944e2f51cf408ba5223e71d886'


PRELUDE = r'''
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdarg.h>
#include <errno.h>
#define CONFIG_SOC_EXYNOS9820 1
#define CONFIG_EXYNOS_IVA 1
#define CONFIG_ION_EXYNOS 1
#define CONFIG_64BIT 1
#define CONFIG_IVA_VER 30
#define CONFIG_EXYNOS_IOVMM 1
#define CONFIG_PM_SLEEP 1
#define ENABLE_MMAP_US
#define IVA_PM_QOS_IVA 1
#define IVA_CTL_QOS_DEV
#define IVA_PM_QOS_DEV 2
#define __user
#define GFP_KERNEL 0
#define IORESOURCE_MEM 0
#define IORESOURCE_IRQ 1
#define IVA_MBOX_IRQ_NOT_DEFINED -1
#define MISC_DYNAMIC_MINOR 255
#define IVA_CTL_ALLOC_LOCALLY_F 1
#define VMCU_MEM_SIZE 8192
#define SHMEM_SIZE 4096
#define EXTEND_VMCU_MEM_SIZE 16384
#define EXTEND_SHMEM_SIZE 8192
#define WAKE_LOCK_SUSPEND 0
#define PAGE_SHIFT 12
#define THIS_MODULE NULL
#define _IOC_WRITE 1
#define _IOC_READ 2
#define _IOC_DIR(c) (((c) >> 30) & 3)
#define _IOC_TYPE(c) (((c) >> 8) & 255)
#define _IOC(d,t,n,s) (((unsigned int)(d)<<30)|((unsigned int)(s)<<16)|((t)<<8)|(n))
#define _IOW(t,n,s) _IOC(1,t,n,sizeof(s))
#define _IOR(t,n,s) _IOC(2,t,n,sizeof(s))
#define _IOWR(t,n,s) _IOC(3,t,n,sizeof(s))
struct ipc_cmd_param { int opaque; };
struct ipc_res_param { int opaque; };
@NATIVE_IOCTL@
#define IS_ERR(p) ((uintptr_t)(p)>=(uintptr_t)-4095)
#define PTR_ERR(p) ((long)(intptr_t)(p))
typedef uint64_t u64;
struct list_head { struct list_head *next,*prev; };
#define container_of(p,t,m) ((t *)((char *)(p)-offsetof(t,m)))
#define LIST_HEAD(name) struct list_head name={&(name),&(name)}
static void INIT_LIST_HEAD(struct list_head *h) { h->next=h;h->prev=h; }
static bool list_empty(const struct list_head *h) { return h->next==h; }
static void list_add(struct list_head *n,struct list_head *h) { n->next=h->next;n->prev=h;h->next->prev=n;h->next=n; }
static void list_del(struct list_head *n) { n->prev->next=n->next;n->next->prev=n->prev; }
static void list_del_init(struct list_head *n) { list_del(n);INIT_LIST_HEAD(n); }
#define list_entry(p,t,m) container_of(p,t,m)
#define list_for_each(n,h) for(n=(h)->next;n!=(h);n=n->next)
#define list_for_each_entry(p,h,m) for(p=list_entry((h)->next,__typeof__(*p),m); &p->m!=(h); p=list_entry(p->m.next,__typeof__(*p),m))
#define DEFINE_SPINLOCK(name) SRWLOCK name=SRWLOCK_INIT
static volatile LONG spin_held;
#define spin_lock_irqsave(l,f) do { (f)=0;AcquireSRWLockExclusive(l);InterlockedIncrement(&spin_held); } while(0)
#define spin_unlock_irqrestore(l,f) do { (void)(f);InterlockedDecrement(&spin_held);ReleaseSRWLockExclusive(l); } while(0)
struct kref { volatile LONG refcount; };
static volatile LONG assertions;
#define CHECK(c) do { InterlockedIncrement(&assertions);if(!(c)){fprintf(stderr,"line %d: %s\n",__LINE__,#c);ExitProcess(1);} } while(0)
static void kref_init(struct kref *r) { r->refcount=1; }
static void kref_get(struct kref *r) { CHECK(r->refcount>0);InterlockedIncrement(&r->refcount); }
static int kref_put(struct kref *r,void(*release)(struct kref *)) { CHECK(r->refcount>0);if(!InterlockedDecrement(&r->refcount)){release(r);return 1;}return 0; }
static void refcount_set(volatile LONG *r,int n) { *r=n; }
struct task_struct { volatile LONG refs;const char *comm;int pid;struct task_struct *group_leader; };
static struct task_struct fixture_task={1,"NEW145",7,&fixture_task};
static struct task_struct *current=&fixture_task;
static int task_gets,task_puts,task_finals;
static bool task_final_unbind;
static void get_task_struct(struct task_struct *t) { CHECK(t==current);++task_gets;InterlockedIncrement(&t->refs); }
static void put_task_struct(struct task_struct *t);
struct device { SRWLOCK mutex;volatile LONG held;DWORD owner;volatile LONG refs;void *drvdata; };
struct platform_device { struct device dev; };
struct inode { int unused; };
struct file { void *private_data; };
struct vm_area_struct { unsigned long vm_start,vm_end,vm_pgoff,vm_page_prot; };
struct file_operations {
 void *owner;int(*open)(struct inode*,struct file*);int(*release)(struct inode*,struct file*);
 long(*unlocked_ioctl)(struct file*,unsigned int,uintptr_t);
 long(*compat_ioctl)(struct file*,unsigned int,uintptr_t);
 int(*mmap)(struct file*,struct vm_area_struct*);
};
struct miscdevice { int minor;const char *name;const struct file_operations *fops;struct device *parent; };
struct clk { int unused; };
struct resource { unsigned long start,end;const char *name; };
struct iva_dev_data {
 struct device *dev;struct miscdevice misc;struct clk *iva_clk;struct resource *iva_res;void *iva_va;
 int proc_mutex;struct list_head proc_head;int flags;unsigned long state;
 unsigned int mcu_mem_size,mcu_shmem_size;bool mcu_split_sram,iva_bus_qos_en;
 int mbox_irq_nr,iva_qos_iva,iva_qos_dev,iva_qos_rate,iva_wake_lock;
};
struct iva_proc {
 struct iva_dev_data *iva_data;struct task_struct *tsk;int pid,tid;
 struct list_head proc_node;struct kref init_ref,boot_ref;
};
static struct iva_dev_data *g_iva_data;
static struct platform_device board;
static struct resource native_resource={0x100000,0x10ffff,"IVA"};
static struct clk native_clk;
static struct iva_proc *devres_proc;
static struct iva_dev_data native_storage;
static struct miscdevice *published_misc;
static bool native_live,foreign_pending,foreign_unbind,block_ioctl;
static int stage,alloc_fail,open_alloc_fail,remap_fail,try_open_during_probe;
static int alloc_calls,heap_frees,native_open_calls,native_release_calls;
static int native_ioctl_calls,native_mmap_calls,foreign_puts,misc_registers,misc_deregisters;
static int probe_open_result,hardware_actions;static char order[256];static int order_nr;
static HANDLE ioctl_entered,ioctl_continue,remove_started,remove_done;
static void event(char c) { CHECK(order_nr<255);order[order_nr++]=c;order[order_nr]=0; }
static bool held(struct device *d) { return d->held && d->owner==GetCurrentThreadId(); }
static void device_lock(struct device *d) { AcquireSRWLockExclusive(&d->mutex);CHECK(!d->held);d->owner=GetCurrentThreadId();InterlockedExchange(&d->held,1); }
static bool device_trylock(struct device *d) { if(!TryAcquireSRWLockExclusive(&d->mutex))return false;CHECK(!d->held);d->owner=GetCurrentThreadId();InterlockedExchange(&d->held,1);return true; }
static void device_unlock(struct device *d) { CHECK(held(d));InterlockedExchange(&d->held,0);d->owner=0;ReleaseSRWLockExclusive(&d->mutex); }
static struct device *get_device(struct device *d) { InterlockedIncrement(&d->refs);return d; }
static void put_device(struct device *d) { CHECK(!spin_held && d->refs>1);InterlockedDecrement(&d->refs); }
static void *dev_get_drvdata(struct device *d) { return d->drvdata; }
static void dev_set_drvdata(struct device *d,void *p) { d->drvdata=p; }
#define platform_get_drvdata(p) dev_get_drvdata(&(p)->dev)
#define platform_set_drvdata(p,v) dev_set_drvdata(&(p)->dev,v)
static void *kzalloc(size_t n,int flags) { (void)flags;++alloc_calls;if(alloc_fail==alloc_calls)return NULL;return calloc(1,n); }
static void kfree(void *p) { CHECK(!spin_held);++heap_frees;free(p); }
static void mutex_init(int *m) { *m=0; }
static void mutex_lock(int *m) { CHECK(!*m);*m=1; }
static void mutex_unlock(int *m) { CHECK(*m);*m=0; }
static void native_check(struct iva_dev_data *iva) { CHECK(native_live && iva==&native_storage && held(&board.dev)); }
static void native_log(struct device *d,const char *fmt,...) { CHECK(d==&board.dev && held(d));(void)fmt; }
#define dev_dbg native_log
#define dev_warn native_log
#define dev_err native_log
#define dev_info native_log
static void *devm_kzalloc(struct device *d,size_t n,int flags)
{ (void)flags;CHECK(held(d) && n==sizeof(native_storage));if(stage==2)return NULL;memset(&native_storage,0,n);native_live=true;return &native_storage; }
static void *devm_kmalloc(struct device *d,size_t n,int flags)
{ (void)flags;CHECK(held(d)&&native_live&&!devres_proc);++native_open_calls;if(open_alloc_fail)return NULL;devres_proc=malloc(n);return devres_proc; }
static void devm_kfree(struct device *d,void *p)
{ CHECK(held(d));if(p==&native_storage){CHECK(!published_misc);native_live=false;event('F');}else{CHECK(p==devres_proc);free(p);devres_proc=NULL;++native_release_calls;event('v');} }
static struct resource *platform_get_resource(struct platform_device *p,int type,int n)
{ CHECK(held(&p->dev));(void)type;(void)n;return stage==1?NULL:&native_resource; }
static int platform_get_irq(struct platform_device *p,int n) { CHECK(held(&p->dev));(void)n;return 3; }
static unsigned long resource_size(struct resource *r) { return r->end-r->start+1; }
static const char *dev_name(struct device *d) { (void)d;return "nativeIVA"; }
static struct clk *devm_clk_get(struct device *d,const char *n) { CHECK(held(d));(void)n;return stage==3?(struct clk*)(intptr_t)-9:&native_clk; }
static void devm_clk_put(struct device *d,struct clk *c) { CHECK(held(d)&&c==&native_clk);++hardware_actions;event('c'); }
static struct resource *devm_request_mem_region(struct device *d,unsigned long s,unsigned long n,const char *name)
{ CHECK(held(d));(void)s;(void)n;(void)name;return stage==4?NULL:&native_resource; }
static void devm_release_mem_region(struct device *d,unsigned long s,unsigned long n) { CHECK(held(d));(void)s;(void)n;event('r'); }
static void *devm_ioremap(struct device *d,unsigned long s,unsigned long n) { CHECK(held(d));(void)s;(void)n;return stage==5?NULL:(void*)(uintptr_t)0x400000; }
static void devm_iounmap(struct device *d,void *p) { CHECK(held(d)&&p==(void*)(uintptr_t)0x400000);event('u'); }
static void iva_ctl_parse_of_dt(struct device *d,struct iva_dev_data *v) { CHECK(held(d));v->mcu_mem_size=8192;v->mcu_shmem_size=4096; }
static int iva_mem_create_ion_client(struct iva_dev_data *v) { native_check(v);return stage==6?-6:0; }
static int iva_pmu_probe(struct iva_dev_data *v) { native_check(v);++hardware_actions;event('P');return stage==7?-7:0; }
static int iva_mcu_probe(struct iva_dev_data *v) { native_check(v);++hardware_actions;event('M');return stage==8?-8:0; }
static void iva_pmu_remove(struct iva_dev_data *v) { native_check(v);++hardware_actions;event('p'); }
static void iva_mcu_remove(struct iva_dev_data *v) { native_check(v);CHECK(!published_misc);++hardware_actions;event('m'); }
static int iva_mem_destroy_ion_client(struct iva_dev_data *v) { native_check(v);event('i');return 0; }
static int misc_register(struct miscdevice *m)
{ CHECK(held(m->parent)&&!published_misc);++misc_registers;event('S');if(stage==9)return -9;published_misc=m;if(try_open_during_probe){struct file f;f.private_data=m;probe_open_result=m->fops->open(NULL,&f);}return 0; }
static void misc_deregister(struct miscdevice *m) { CHECK(held(m->parent)&&published_misc==m);published_misc=NULL;++misc_deregisters;event('s'); }
static void pm_runtime_enable(struct device *d) { CHECK(held(d));++hardware_actions;event('E'); }
static void pm_runtime_disable(struct device *d) { CHECK(held(d));++hardware_actions;event('e'); }
#define iovmm_set_fault_handler(d,f,v) do { CHECK(held(d));(void)(v); } while(0)
static int iovmm_activate(struct device *d) { CHECK(held(d));++hardware_actions;event('A');return stage==10?-10:0; }
static void iovmm_deactivate(struct device *d) { CHECK(held(d));++hardware_actions;event('a'); }
static int iva_sysfs_init(struct device *d) { CHECK(held(d));return 0; }
static void iva_sysfs_deinit(struct device *d) { CHECK(held(d));event('y'); }
static void pm_qos_add_request(int *request,int class_id,int n) { (void)request;(void)class_id;(void)n; }
static void wake_lock_init(int *lock,int kind,const char *n) { (void)lock;(void)kind;(void)n; }
static void wake_lock_destroy(int *lock) { (void)lock; }
static void iva_mem_init_proc_mem(struct iva_proc *p) { CHECK(p==devres_proc);event('N'); }
static void iva_mem_deinit_proc_mem(struct iva_proc *p) { CHECK(p==devres_proc);event('d'); }
static int iva_ctrl_mcu_exit(struct iva_proc *p,bool forced) { native_check(p->iva_data);CHECK(p==devres_proc);(void)forced;event('x');return 0; }
static int iva_ctrl_deinit(struct iva_proc *p,bool forced) { native_check(p->iva_data);CHECK(p==devres_proc);(void)forced;event('q');return 0; }
static unsigned long pgprot_noncached(unsigned long p) { return p|1; }
static int remap_pfn_range(struct vm_area_struct *v,unsigned long start,unsigned long pfn,unsigned long size,unsigned long protection)
{ CHECK(native_live&&held(&board.dev));(void)v;(void)start;(void)pfn;(void)size;(void)protection;++native_mmap_calls;return remap_fail?-5:0; }
struct dma_buf_ops { int tag; };
struct dma_buf { const struct dma_buf_ops *ops;size_t size;int refs; };
void dma_buf_put(struct dma_buf *buf);
#include "v144_iva_buffer.h"
const struct dma_buf_ops ion_dma_buf_ops={1};
static const struct dma_buf_ops foreign_ops={2};
static struct dma_buf foreign={&foreign_ops,4096,0};
static int iva_mem_ioctl(struct iva_proc *proc,unsigned int cmd,void *p,struct n144_buffer_call *call)
{
 native_check(proc->iva_data);CHECK(proc==devres_proc);(void)cmd;(void)p;++native_ioctl_calls;
 if(block_ioctl){CHECK(SetEvent(ioctl_entered));CHECK(WaitForSingleObject(ioctl_continue,10000)==WAIT_OBJECT_0);}
 if(foreign_pending){CHECK(!call->foreign_put);++foreign.refs;call->foreign_put=&foreign;call->refused_history=true;return -EINVAL;}
 return 41;
}
static const char *iva_ctrl_get_ioctl_str(unsigned int cmd) { (void)cmd;return "fixture"; }
static int iva_ctrl_init_usr(struct iva_proc *p,uint32_t *v) { native_check(p->iva_data);(void)v;return 0; }
static int iva_ctrl_mcu_boot_file(struct iva_proc *p,const char *v,bool f) { native_check(p->iva_data);(void)v;(void)f;return 0; }
static int iva_ctrl_get_iva_status_usr(struct iva_dev_data *v,struct iva_status_param *p) { native_check(v);(void)p;return 0; }
static int iva_ipcq_send_cmd_usr(struct iva_proc *p,struct ipc_cmd_param *v) { native_check(p->iva_data);(void)v;return 0; }
static int iva_ipcq_wait_res_usr(struct iva_proc *p,struct ipc_res_param *v) { native_check(p->iva_data);(void)v;return 0; }
static int iva_ctrl_set_clk_usr(struct iva_dev_data *v,uint32_t *p) { native_check(v);(void)p;return 0; }
'''

MAIN = r'''
static void core_devres_drain(void)
{
 CHECK(held(&board.dev));
 if(devres_proc){free(devres_proc);devres_proc=NULL;}
 board.dev.drvdata=NULL;
}
static int core_probe(void) { int r;device_lock(&board.dev);r=iva_ctl_probe(&board);if(!r)CHECK(g_iva_data==platform_get_drvdata(&board));if(r)core_devres_drain();device_unlock(&board.dev);return r; }
static int core_remove(void) { int r;device_lock(&board.dev);r=iva_ctl_remove(&board);CHECK(g_iva_data==NULL);core_devres_drain();device_unlock(&board.dev);return r; }
static void put_task_struct(struct task_struct *t)
{
 CHECK(t==current && t->refs>0 && !board.dev.held && !spin_held);
 ++task_puts;event('t');
 if(!InterlockedDecrement(&t->refs)){++task_finals;if(task_final_unbind)CHECK(core_remove()==0);}
}
void dma_buf_put(struct dma_buf *buf)
{
 CHECK(buf==&foreign && foreign.refs==1 && !board.dev.held && !spin_held);
 --foreign.refs;++foreign_puts;
 if(foreign_unbind)CHECK(core_remove()==0);
}
static struct file opened(void)
{ struct file f;CHECK(published_misc);f.private_data=published_misc;CHECK(iva_ctrl_open(NULL,&f)==0);return f; }
static void reset_counters(void)
{
 CHECK(list_empty(&n145_bindings)&&board.dev.refs==1&&!devres_proc&&!published_misc&&!native_live&&!board.dev.held);
 stage=alloc_fail=open_alloc_fail=remap_fail=try_open_during_probe=0;alloc_calls=heap_frees=0;
 task_gets=task_puts=task_finals=native_open_calls=native_release_calls=native_ioctl_calls=native_mmap_calls=foreign_puts=0;
 misc_registers=misc_deregisters=hardware_actions=order_nr=0;order[0]=0;foreign_pending=foreign_unbind=block_ioctl=task_final_unbind=false;
 CHECK(fixture_task.refs==1 && !foreign.refs);
}
static DWORD WINAPI ioctl_thread(void *arg)
{ struct file *f=arg;struct iva_ion_param p;memset(&p,0,sizeof(p));CHECK(iva_ctrl_ioctl(f,IVA_ION_GET_IOVA,(uintptr_t)&p)==41);return 0; }
static DWORD WINAPI remove_thread(void *arg)
{ (void)arg;CHECK(SetEvent(remove_started));CHECK(core_remove()==0);CHECK(SetEvent(remove_done));return 0; }
int main(void)
{
 struct file f,second;struct iva_ion_param p;struct vm_area_struct vma;
 struct n145_file *oldctx;struct n145_binding *oldbinding;struct iva_dev_data *address;
 HANDLE worker,remover;unsigned long history;int i;
 InitializeSRWLock(&board.dev.mutex);board.dev.refs=1;memset(&p,0,sizeof(p));
 for(i=1;i<=10;++i){reset_counters();stage=i;CHECK(core_probe()<0);CHECK(list_empty(&n145_bindings));CHECK(!published_misc&&!native_live);CHECK(!task_gets&&!task_puts);CHECK(misc_deregisters==(i==10));if(i==10)CHECK(strcmp(order,"PMSEAesmpiurcF")==0);}
 reset_counters();alloc_fail=1;CHECK(core_probe()==-ENOMEM);CHECK(!misc_registers&&!hardware_actions);
 reset_counters();try_open_during_probe=1;CHECK(core_probe()==0);CHECK(probe_open_result==-EBUSY&&!task_gets);CHECK(core_remove()==0);
 reset_counters();CHECK(core_probe()==0);alloc_fail=alloc_calls+1;f.private_data=published_misc;CHECK(iva_ctrl_open(NULL,&f)==-ENOMEM);CHECK(!task_gets&&!native_open_calls);alloc_fail=0;
 open_alloc_fail=1;f.private_data=published_misc;CHECK(iva_ctrl_open(NULL,&f)==-ENOMEM);CHECK(!task_gets);open_alloc_fail=0;
 f=opened();CHECK(task_gets==1&&fixture_task.refs==2);second.private_data=published_misc;CHECK(iva_ctrl_open(NULL,&second)==-EMFILE);CHECK(task_gets==1);
 CHECK(iva_ctrl_ioctl(&f,IVA_ION_GET_IOVA,(uintptr_t)&p)==41);CHECK(native_ioctl_calls==1);
 memset(&vma,0,sizeof(vma));vma.vm_start=0x200000;vma.vm_end=0x201000;vma.vm_pgoff=native_resource.start>>PAGE_SHIFT;
 CHECK(iva_ctrl_mmap(&f,&vma)==0);CHECK(native_mmap_calls==1);CHECK(n145_lifetime_history&N145_MMAP_SUCCESS);
 remap_fail=1;CHECK(iva_ctrl_mmap(&f,&vma)==-5);CHECK(native_mmap_calls==2);remap_fail=0;
 vma.vm_pgoff=0;CHECK(iva_ctrl_mmap(&f,&vma)==-EPERM);CHECK(native_mmap_calls==2);
 CHECK(iva_ctrl_release(NULL,&f)==0);CHECK(task_puts==1&&native_release_calls==1&&fixture_task.refs==1);CHECK(strstr(order,"xqdvt")!=NULL);CHECK(core_remove()==0);
 reset_counters();CHECK(core_probe()==0);f=opened();oldctx=f.private_data;oldbinding=oldctx->binding;address=oldbinding->native;
 CHECK(core_remove()==0);CHECK(!oldctx->native&&oldctx->task_owner==N145_CTX_OWNED);CHECK(task_puts==0&&fixture_task.refs==2&&board.dev.refs==2);
 CHECK(iva_ctrl_ioctl(&f,IVA_ION_GET_IOVA,(uintptr_t)&p)==-ENODEV);CHECK(!native_ioctl_calls);
 CHECK(iva_ctrl_mmap(&f,&vma)==-ENODEV);CHECK(!native_mmap_calls);
 CHECK(core_probe()==0);CHECK(platform_get_drvdata(&board)==address);
 {struct n145_binding *current_binding;device_lock(&board.dev);current_binding=n145_binding_get(&board.dev);CHECK(current_binding&&current_binding!=oldbinding);n145_binding_put(current_binding);device_unlock(&board.dev);}
 CHECK(iva_ctrl_ioctl(&f,IVA_ION_GET_IOVA,(uintptr_t)&p)==-ENODEV);CHECK(iva_ctrl_release(NULL,&f)==0);CHECK(task_puts==1&&native_release_calls==0);CHECK(core_remove()==0);
 reset_counters();CHECK(core_probe()==0);f=opened();CHECK(fixture_task.refs==2);--fixture_task.refs;task_final_unbind=true;
 CHECK(iva_ctrl_release(NULL,&f)==0);CHECK(task_puts==1&&task_finals==1&&fixture_task.refs==0&&!native_live&&board.dev.refs==1);fixture_task.refs=1;
 reset_counters();CHECK(core_probe()==0);f=opened();foreign_pending=foreign_unbind=true;
 CHECK(iva_ctrl_ioctl(&f,IVA_ION_GET_IOVA,(uintptr_t)&p)==-EINVAL);CHECK(foreign_puts==1&&!foreign.refs&&!native_live);CHECK(task_puts==0);CHECK(iva_ctrl_release(NULL,&f)==0);CHECK(task_puts==1);
 reset_counters();CHECK(core_probe()==0);f=opened();block_ioctl=true;
 ioctl_entered=CreateEvent(NULL,TRUE,FALSE,NULL);ioctl_continue=CreateEvent(NULL,TRUE,FALSE,NULL);remove_started=CreateEvent(NULL,TRUE,FALSE,NULL);remove_done=CreateEvent(NULL,TRUE,FALSE,NULL);
 CHECK(ioctl_entered&&ioctl_continue&&remove_started&&remove_done);
 worker=CreateThread(NULL,0,ioctl_thread,&f,0,NULL);CHECK(worker&&WaitForSingleObject(ioctl_entered,10000)==WAIT_OBJECT_0);
 remover=CreateThread(NULL,0,remove_thread,NULL,0,NULL);CHECK(remover&&WaitForSingleObject(remove_started,10000)==WAIT_OBJECT_0);
 CHECK(WaitForSingleObject(remove_done,100)==WAIT_TIMEOUT && native_live);CHECK(SetEvent(ioctl_continue));
 CHECK(WaitForSingleObject(worker,10000)==WAIT_OBJECT_0&&WaitForSingleObject(remover,10000)==WAIT_OBJECT_0);CHECK(!native_live&&!devres_proc);
 CloseHandle(worker);CloseHandle(remover);CloseHandle(ioctl_entered);CloseHandle(ioctl_continue);CloseHandle(remove_started);CloseHandle(remove_done);
 CHECK(iva_ctrl_release(NULL,&f)==0);CHECK(task_puts==1&&native_release_calls==0);
 /* VFS model: mmap keeps a file reference; only final fput calls release. */
 reset_counters();CHECK(core_probe()==0);f=opened();vma.vm_pgoff=native_resource.start>>PAGE_SHIFT;
 CHECK(iva_ctrl_mmap(&f,&vma)==0);CHECK(core_remove()==0);CHECK(f.private_data&&task_puts==0);
 CHECK(iva_ctrl_release(NULL,&f)==0);CHECK(task_puts==1&&fixture_task.refs==1&&board.dev.refs==1);
 history=n145_lifetime_history;CHECK(history&N145_MMAP_ATTEMPT);CHECK(history&N145_MMAP_SUCCESS);CHECK(history&N145_DETACHED);
 reset_counters();CHECK(n145_lifetime_history==history);CHECK(!spin_held);
 /* Ownership mismatch deliberately quarantines; never native-close or guess put. */
 CHECK(core_probe()==0);f=opened();oldctx=f.private_data;oldctx->task_owner=N145_CONSUMED;
 CHECK(iva_ctrl_ioctl(&f,IVA_ION_GET_IOVA,(uintptr_t)&p)==-ENODEV);CHECK(oldctx->quarantined);
 CHECK(core_remove()==0);CHECK(iva_ctrl_release(NULL,&f)==-EIO);CHECK(!task_puts&&!native_release_calls&&fixture_task.refs==2);
 CHECK(n145_lifetime_history&N145_UNSAFE);CHECK(!board.dev.held&&!spin_held);
 printf("NEW native sidecar PASS; assertions=%ld\n",assertions);return 0;
}
'''


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--ctrl144', required=True, type=Path)
    parser.add_argument('--native-root', required=True, type=Path)
    parser.add_argument('--cc', required=True, type=Path)
    args = parser.parse_args()
    out = args.output.resolve()
    if out.exists():
        raise ValueError('one-shot output must not exist')
    if not BUFFER_HELPER_SHA256 or not IOCTL_ABI_SHA256:
        raise ValueError('await actual ROOT144 PASS and FINAL pins')
    ctrl = args.ctrl144.read_bytes()
    buffer = (HERE / 'v144_iva_buffer.h').read_bytes()
    abi = (args.native_root / 'drivers/vision/iva/iva_ctrl_ioctl.h').read_bytes()
    if hashlib.sha256(buffer).hexdigest() != BUFFER_HELPER_SHA256 or hashlib.sha256(abi).hexdigest() != IOCTL_ABI_SHA256:
        raise ValueError('retained exact helper/ABI pin mismatch')
    helper = (HERE / 'v145_iva_sidecar.inc').read_bytes()
    outputs = patch_native(ctrl, helper)
    refusals = 0
    for bad_ctrl, bad_helper in [(ctrl + b'\n', helper), (ctrl, helper + b'\n')]:
        try:
            patch_native(bad_ctrl, bad_helper)
        except ValueError:
            refusals += 1
    if refusals != 2:
        raise AssertionError('NEW transform refusal contract')
    raw = outputs[CTRL]
    def body(name):
        start, end = function_span(raw, name)
        return raw[start:end]
    bodies = [body(n) for n in ('n145_native_mmap', 'n145_native_open', 'n145_native_release')]
    ioctl = body('n144_iva_ctrl_ioctl_body')
    if ioctl.count(b'unsigned long arg') != 1 or helper.count(b'unsigned long arg') != 1:
        raise ValueError('exact host pointer bridge sites required')
    bodies.append(ioctl.replace(b'unsigned long arg', b'uintptr_t arg', 1))
    host_helper = helper.replace(b'unsigned long arg', b'uintptr_t arg', 1)
    fops_start = raw.index(b'static const struct file_operations iva_ctl_fops = {')
    fops_end = raw.index(b'};', fops_start) + 2
    fixture = PRELUDE.encode().replace(b'@NATIVE_IOCTL@', abi[abi.index(b'#define IVA_CTRL_BOOT_FILE_NAME_LEN'):abi.index(b'#endif')])
    fixture += b'\n\n'.join(bodies) + b'\n#include "v145_iva_sidecar.inc"\n' + raw[fops_start:fops_end]
    fixture += b'\n' + body('n145_native_probe') + b'\n' + body('n145_native_remove') + MAIN.encode()
    out.mkdir(parents=True)
    include = out / 'include'
    for leaf in ['device.h','kref.h','list.h','slab.h','spinlock.h','sched/task.h','dma-buf.h','err.h']:
        p = include / 'linux' / leaf
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(b'/* Instrumented kernel types supplied by NEW fixture prelude. */\n')
    (include / 'v145_iva_sidecar.inc').write_bytes(host_helper)
    (include / 'v144_iva_buffer.h').write_bytes(buffer)
    for name, data in outputs.items():
        p = out / 'native-output' / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)
    source = out / 'native_sidecar_fixture.c'
    source.write_bytes(fixture)
    executable = out / 'native_sidecar_fixture.exe'
    compile_argv = [str(args.cc.resolve()), '-std=gnu89', '-Wall', '-Wextra', '-Werror',
                    '-Wno-unused-function', '-Wdeclaration-after-statement', '-I', str(include), str(source), '-o', str(executable)]
    fixture_argv = [str(executable)]
    result = {'schema': 'v145-new-native-sidecar-once-v1', 'pass': False,
              'compiler_count': 0, 'fixture_count': 0, 'primary_transform_count': 1,
              'compiler_launch_attempts': 0, 'fixture_launch_attempts': 0,
              'negative_transform_count': refusals, 'old_tests_count': 0,
              'argv': [sys.executable, *sys.argv], 'compiler_argv': compile_argv, 'fixture_argv': fixture_argv,
              'ctrl144_sha256': CTRL_SHA256,
              'outputs': {k: hashlib.sha256(v).hexdigest() for k, v in outputs.items()},
              'fixture_sha256': hashlib.sha256(fixture).hexdigest(), 'authentic_native_bodies': 6,
              'host_helper_sha256': hashlib.sha256(host_helper).hexdigest(),
              'real_file_entry_wrappers': 6, 'threaded_remove_race': True,
              'runtime_returncode': None, 'physical_owner_success': False,
              'host_pointer_ABI_bridges': ['Only host copies: n144 body and145 wrapper unsigned-long ioctl arg -> uintptr_t, caller casts and stub fops arg likewise uintptr_t; production ABI untouched.']}
    try:
        result['compiler_launch_attempts'] = 1
        compiled = subprocess.run(compile_argv, capture_output=True, text=True)
        result['compiler_count'] = 1
        result['compiler_returncode'] = compiled.returncode
        (out / 'compiler.txt').write_bytes((compiled.stdout + compiled.stderr).encode())
        if not compiled.returncode:
            result['fixture_launch_attempts'] = 1
            ran = subprocess.run(fixture_argv, capture_output=True, text=True)
            result['fixture_count'] = 1
            result['runtime_returncode'] = ran.returncode
            (out / 'fixture.txt').write_bytes((ran.stdout + ran.stderr).encode())
            result['pass'] = ran.returncode == 0
    except OSError as error:
        result['launch_error'] = str(error)
    (out / 'result.json').write_bytes((json.dumps(result, indent=2) + '\n').encode())
    if not result['pass']:
        raise RuntimeError('NEW fixture failed; no retry')


if __name__ == '__main__':
    main()
