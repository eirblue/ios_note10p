"""One NEW typed terminal/admission/accessibility batch; retain old PASS unchanged."""
import argparse,json,re,subprocess,sys
from pathlib import Path
sys.dont_write_bytecode=True
from v130_contract import ROOT,private,ordinary,sha,digest,read,save,hexid
import v136_prepare as prepare
import v136_cycle as cycle
import v136_package as package
from v135_metadata import encode_public
from v136_build import SETTINGS,NEW_FILES,SCOPE,RETAINED_COMMIT,RETAINED_SOURCE_SHA256,RETAINED_CONTEXT_SHA256,source_pins,continuation,retained_continuation
HERE=Path(__file__).resolve().parent
ORIGINAL_TEST_SHA='21c5399d0116bf23b5a6a1ec35120becf13402446faf78b04f9f1825d17bf128'
ORIGINAL_HOST_RESULT_SHA='5c2f5c5d88498e32e898bd972b8a189bee0400c73c21a9c13d9713cc6bafcbdc'
PREVIOUS_TEST_SHA='2cf8e314d360d276390ada61fa6241f18a756884e942193b2221fb4cafa29d07'
PREVIOUS_SOURCE_MAP_SHA='5d9b52bc0aa671228586e13473de795545b1b79758b12bfc74e8e1dc60f546fa'
PREVIOUS_FIXTURE_RESULT_SHA='42f7aac9c695ebaf06a18fb91e14a3e60cf3d2c729d35c3f4f55fdd7a1fbe928'
ORIGINAL_SOURCE_MAP_SHA='5d4996e62d19e16fa7df307b148d35ee3a45bc74844121a09c2629bb455f7b2d'
FIXTURE_SHA='401e6eaa81aa0797f66eee0b9cd4e2f7cf1d34eef4688b82daa7f93f49417269'


def extract(raw,name):
    """Extract one C definition, balancing nested callback declarators too."""
    text=raw.decode()
    head=re.compile(r'(?m)^(?:(?:static|inline)\s+)*(?:unsigned\s+int|ssize_t|irqreturn_t|bool|u32|void|int|long)\s+'+re.escape(name)+r'\s*\(')
    token=re.compile(r'/\*.*?\*/|//[^\n]*|"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'|[(){}]',re.S)
    definitions=[]
    for match in head.finditer(text):
        depth=1;closing=None
        for part in token.finditer(text,match.end()):
            if part.group()=='(':depth+=1
            elif part.group()==')':depth-=1
            if not depth:closing=part.end();break
        if closing is None:raise ValueError('C parameter extent absent: '+name)
        at=closing
        while at<len(text) and text[at].isspace():at+=1
        # A forward declaration is not the later definition to replace.
        if at==len(text) or text[at]!='{':continue
        depth=1;end=None
        for part in token.finditer(text,at+1):
            if part.group()=='{':depth+=1
            elif part.group()=='}':depth-=1
            if not depth:end=part.end();break
        if end is None:raise ValueError('C body extent absent: '+name)
        definitions.append(text[match.start():end])
    if len(definitions)!=1:raise ValueError('one exact C definition required: '+name)
    return definitions[0]


def selected_cal_wrapper(raw):
    # Both native source branches intentionally define the same public name.
    # Compile the enabled handoff branch, never pick the first duplicate.
    marker=b'#ifdef CONFIG_NOTE10_XNU_KEXEC_HANDOFF\n#include "v136_cal.inc"\n'
    fallback=b'\n#else\nint cal_pd_control(unsigned int id,int on){return n136_cal_pd_native(id,on);}\n#endif\n'
    if SETTINGS.get('NOTE10_XNU_KEXEC_HANDOFF')!='y' or raw.count(marker)!=1:
        raise ValueError('exact enabled CAL handoff branch required')
    selected=raw.split(marker,1)[1]
    if not selected.endswith(fallback) or selected.count(fallback)!=1:
        raise ValueError('exact native CAL fallback boundary required')
    return extract(selected[:-len(fallback)],'cal_pd_control')


def replace(text,name,new):
    original=extract(text.encode(),name)
    if text.count(original)!=1:raise ValueError('fixture function not unique: '+name)
    return text.replace(original,new,1)


SUPPORT=r'''
#define WRITE_ONCE(x,v) ((x)=(v))
#define smp_store_release(p,v) (*(p)=(v))
#define smp_load_acquire(p) (*(p))
#define DEFINE_MUTEX(n) struct mutex n={0}
#define DECLARE_RWSEM(n) struct rw_semaphore n={0}
#define __iomem
#define platform_get_drvdata(p) dev_get_drvdata(&(p)->dev)
#define NPU_MAX_SESSION 32
#define PMUCAL_READ 0
#define G2D_MAX_JOBS 16
#define G2D_DEVICE_STATE_SUSPEND 1
#define G2D_JOB_STATE_DONE 0
#define test_bit(n,p) ((*(p)&(1UL<<(n)))!=0)
#define set_bit(n,p) (*(p)|=1UL<<(n))
static void mutex_lock(struct mutex *p){assert(mutex_trylock(p));}
static bool cal_reserved(unsigned int mask);
static u32 pmu[0x3000/4];static int pmu_reads,gpowered,gforbid,gfifo_reads,gjob_reads,pushes;
static int share_after_dma,share_after_job;
struct pmucal_seq {u32 access_type;uintptr_t base_pa;void *base_va;u32 offset,mask;};
struct pmucal_dbg_info {u32 emul_offset,emul_bit,emul_en,emul_enabled;};
struct pmucal_pd {u32 id;char *name;struct pmucal_seq *status;u32 num_status;struct pmucal_dbg_info *dbg;};
static struct pmucal_pd pmucal_pd_list[7];static unsigned int pmucal_pd_list_size=7;
static struct pmucal_seq status_seq[7];static struct pmucal_dbg_info debug_seq[7];
static int native_pd_calls;
static int n132_handoff_active(void){return n130_arm_state==2;}
static int n136_cal_pd_native(unsigned int id,int on){(void)id;(void)on;native_pd_calls++;return 0;}
static struct clk gclock,nclock;
struct g2d_task {struct g2d_task *next;unsigned long state;struct timer_list fence_timer,hw_timer;int flags;long ktime_begin,ktime_end;struct {unsigned int job_id;} sec;};
struct g2d_device {struct device *dev;spinlock_t lock_task,n136_io_lock;unsigned long state;bool n132_terminal,n132_ever_allocated,n136_ever_pushed,n132_shutdown_seen,n136_io_frozen,n136_ever_dumped;int n132_shutdown_result;unsigned int n132_irq;struct n136_witness n136_witness;struct g2d_task *tasks;struct list_head tasks_active,tasks_prepared;void *schedule_workq,*reg;struct clk *clock;};
static struct {struct device_driver driver;} g2d_driver,npu_driver;
static struct platform_device gpdev,npdev;
static struct g2d_device gdev;static struct g2d_task jobs[16];
static void flush_workqueue(void *p){assert(p==gdev.schedule_workq && gdev.n132_terminal);}
static void pm_runtime_forbid(struct device *d){assert(d==gdev.dev);gforbid=1;}
static int g2d_hw_fifo_idle(struct g2d_device *d){assert(d==&gdev && cal_reserved(N136_G2D_DOMAINS) && gpowered && gclock.enabled);gfifo_reads++;return 1;}
static u32 g2d_hw_get_job_state(struct g2d_device *d,unsigned int i){assert(d==&gdev && i<16 && gfifo_reads);gjob_reads++;if(share_after_job && i==15)foreign_gate=3;return 0;}
static void g2d_hw_push_task(struct g2d_device *d,struct g2d_task *t){assert(d->lock_task.held && t);pushes++;}
#define ktime_get() 1L
#define ktime_us_delta(a,b) ((a)-(b))
#define g2d_stamp_task(...) ((void)0)
#define IS_HWFC(x) ((x)&1)
#define hwfc_set_valid_buffer(...) ((void)0)
struct npu_iomem_area {void *vaddr;u32 paddr;size_t size;};
struct npu_memory {struct device *dev;atomic_t refcount;spinlock_t map_lock,alloc_lock;struct list_head map_list,alloc_list;u32 map_count,alloc_count;};
struct npu_system {struct platform_device *pdev;struct npu_iomem_area pmu_npu,mbox_sfr;struct clk *npu_clk;unsigned long resume_steps,resume_soc_steps;struct npu_memory memory;};
struct npu_vertex_refcount {atomic_t refcount;};
struct npu_vertex {struct mutex lock;struct npu_vertex_refcount open_cnt,start_cnt;};
struct npu_sessionmgr {struct mutex mlock;atomic_t session_cnt;void *session[32];};
struct npu_proto_drv {struct npu_device *npu_device;int state;unsigned long open_steps;void *if_session_ctx,*if_mbox_ctx;struct {struct list_head entry_list;} session_ref;};
struct npu_device {struct device *dev;unsigned long state,err_state;struct npu_system system;struct npu_vertex vertex;struct npu_proto_drv *proto_drv;struct npu_sessionmgr sessionmgr;};
static struct npu_device ndev;static struct npu_proto_drv npu_proto_drv;
#define PROTO_DRV_STATE_PROBED 1
static int get_state(void){return npu_proto_drv.state;}
struct mailbox_sfr {int unused;};
static struct {volatile struct mailbox_sfr *sfr;void *addr,*mbox_hdr;} interface;
static void *wq;static struct {int busy;} work_report;
#define work_busy(p) ((p)->busy)
'''


MAIN=r'''
static void cal_fresh(void)
{
 static const u32 off[]={0,0x1d00,0x1d80,0,0x1e80,0x1f00,0x2300};
 static char *name[]={NULL,"blkpwr_npu0","blkpwr_npu1",NULL,"blkpwr_dspm","blkpwr_dsps","blkpwr_g2d"};unsigned int i;
 memset(pmu,0,sizeof(pmu));memset(pmucal_pd_list,0,sizeof(pmucal_pd_list));memset(status_seq,0,sizeof(status_seq));memset(debug_seq,0,sizeof(debug_seq));
 n136_cal_lock.held=0;n136_closed_domains=n136_reserved_domains=0;pmu_reads=native_pd_calls=0;
 for(i=1;i<=6;i++)if(i!=3){status_seq[i]=(struct pmucal_seq){PMUCAL_READ,0x15860000,pmu,off[i]+4,1};debug_seq[i].emul_offset=off[i]+12;pmucal_pd_list[i]=(struct pmucal_pd){i,name[i],&status_seq[i],1,&debug_seq[i]};}
}
static void domain_on(unsigned int offset){pmu[offset/4]=pmu[(offset+4)/4]=1;}
static void score_fresh(int on)
{fresh();cal_fresh();reset_reads=0;share_after_dma=share_after_job=0;if(on){domain_on(0x1e80);domain_on(0x1f00);}}
static void g2d_fresh(int on)
{
 unsigned int i;score_fresh(0);memset(&gdev,0,sizeof(gdev));memset(jobs,0,sizeof(jobs));memset(&gclock,0,sizeof(gclock));
 gpdev.dev=(struct device){&g2d_driver.driver,&gdev,"g2d-test",0};gdev.dev=&gpdev.dev;gdev.n132_irq=66;gdev.clock=&gclock;gclock.id=2;gdev.reg=jobs;gdev.schedule_workq=&gdev;gdev.tasks=jobs;
 init_list(&gdev.tasks_active);init_list(&gdev.tasks_prepared);for(i=0;i<15;i++)jobs[i].next=&jobs[i+1];gpowered=gforbid=gfifo_reads=gjob_reads=pushes=0;if(on)domain_on(0x2300);
}
static void npu_fresh(void)
{
 score_fresh(0);memset(&ndev,0,sizeof(ndev));memset(&npu_proto_drv,0,sizeof(npu_proto_drv));memset(&nclock,0,sizeof(nclock));memset(&interface,0,sizeof(interface));
 npdev.dev=(struct device){&npu_driver.driver,&ndev,"npu-test",0};ndev.dev=&npdev.dev;ndev.system.pdev=&npdev;ndev.system.pmu_npu=(struct npu_iomem_area){pmu+0x1d00/4,0x15861d00,0x100};
 ndev.system.npu_clk=&nclock;nclock.id=3;ndev.system.memory.dev=ndev.dev;init_list(&ndev.system.memory.map_list);init_list(&ndev.system.memory.alloc_list);
 ndev.proto_drv=&npu_proto_drv;npu_proto_drv.npu_device=&ndev;npu_proto_drv.state=PROTO_DRV_STATE_PROBED;init_list(&npu_proto_drv.session_ref.entry_list);
 ndev.system.mbox_sfr.vaddr=&work_report;interface.sfr=(volatile struct mailbox_sfr *)&work_report;work_report.busy=0;wq=&work_report;
 n136_npu_owner=NULL;n136_npu_history=0;n136_npu_is_ready=n136_npu_frozen=n136_npu_seen=false;n136_npu_result=-ENODEV;memset(&n136_npu_witness,0,sizeof(n136_npu_witness));n136_npu_users=(struct rw_semaphore){0};
 assert(!n136_npu_register(&ndev));n136_npu_ready(&ndev);
}
int main(void)
{
 struct n136_detail detail={0};struct n136_witness witness={0};unsigned int i;int before;
 /* CAL admission interleavings, authoritative ON/OFF and no power writes. */
 cal_fresh();n136_cal_lock.held=1;assert(n136_cal_begin(N136_NPU_DOMAINS,&detail)==-EBUSY && !pmu_reads);n136_cal_lock.held=0;
 assert(!n136_cal_begin(N136_NPU_DOMAINS,&detail) && pmu_reads==6);
 assert(cal_pd_control(0xb1380001,1)==-ESHUTDOWN && cal_pd_control(0xb1380002,0)==-ESHUTDOWN && !native_pd_calls);
 assert(!cal_pd_control(0xb1380007,1) && native_pd_calls==1);n136_cal_end(N136_NPU_DOMAINS,true);
 assert(n136_cal_begin(N136_NPU_DOMAINS,&detail)==-EALREADY);assert(!n136_witness_commit(&witness,&pdev.dev,N136_NPU_DOMAINS_OFF_FROZEN,N136_NPU_DOMAINS));
 assert(!n136_witness_valid(&witness,&npdev.dev,N136_NPU_DOMAINS_OFF_FROZEN,N136_NPU_DOMAINS));
 cal_fresh();domain_on(0x1d00);assert(n136_cal_begin(N136_NPU_DOMAINS,&detail)==-EIO && !strcmp(detail.reason,"domain-mixed"));
 cal_fresh();pmu[0x1d00/4]=1;assert(n136_cal_begin(N136_NPU_DOMAINS,&detail)==-EIO && !strcmp(detail.reason,"domain-transition"));
 cal_fresh();pmu[0x1d0c/4]=1;assert(n136_cal_begin(N136_NPU_DOMAINS,&detail)==-EBUSY && !strcmp(detail.reason,"cal-emulation"));
 cal_fresh();debug_seq[1].emul_en=1;assert(n136_cal_begin(N136_NPU_DOMAINS,&detail)==-EBUSY && !pmu_reads);
 cal_fresh();status_seq[1].mask=15;assert(n136_cal_begin(N136_NPU_DOMAINS,&detail)==-ENODEV && !pmu_reads);
 cal_fresh();domain_on(0x2300);assert(n136_cal_begin(N136_G2D_DOMAINS,&detail)==1);n136_cal_end(N136_G2D_DOMAINS,false);assert(!cal_pd_control(0xb1380006,0));
 /* NEW physical accessibility split: OFF has no PM/SFR action; ON uses
  * retained native stop as setup for the new typed/no-rearm boundary. */
 score_fresh(0);n133_score_shutdown(&pdev);assert(!score.n133_shutdown_result && score.n136_witness.type==N136_SCORE_DOMAINS_OFF_FROZEN && !writes && !pm_gets && !mmio_reads);
 before=pmu_reads;assert(!n133_score_prepare() && pmu_reads==before);
 score_fresh(1);n133_score_shutdown(&pdev);assert(!score.n133_shutdown_result && score.n136_witness.type==N136_SCORE_RESET_DMA_FROZEN && clock_disables==2 && reset_reads>0);
 assert(!n136_score_writer_enter(&score.system) && !score.system.n136_ever_rearmed);
 score_fresh(1);assert(n136_score_writer_enter(&score.system));n133_score_shutdown(&pdev);assert(score.n133_shutdown_result==-EBUSY && !writes && !pm_gets);
 score_fresh(1);clocks[0].enabled=1;n133_score_shutdown(&pdev);assert(score.n133_shutdown_result==-EBUSY && !pm_gets && !writes);
 score_fresh(1);foreign_gate=1;n133_score_shutdown(&pdev);assert(score.n133_shutdown_result==-EBUSY && !writes && clock_disables==2 && !score.n136_witness.committed);
 score_fresh(1);share_after_dma=1;n133_score_shutdown(&pdev);assert(score.n133_shutdown_result==-EBUSY && !score.n136_witness.committed);
 score_fresh(0);domain_on(0x1e80);n133_score_shutdown(&pdev);assert(score.n133_shutdown_result==-EIO && !pm_gets && !writes);
 g2d_fresh(0);n132_g2d_shutdown(&gpdev);assert(!gdev.n132_shutdown_result && gdev.n136_witness.type==N136_G2D_DOMAIN_OFF_FROZEN && !pm_gets && !gfifo_reads);
 assert(!n136_g2d_io_enter(&gdev) && !gdev.n136_ever_dumped);
 g2d_fresh(1);assert(n136_g2d_io_enter(&gdev));n132_g2d_shutdown(&gpdev);assert(gdev.n132_shutdown_result==-EBUSY && !gfifo_reads);
 g2d_fresh(1);n132_g2d_shutdown(&gpdev);assert(!gdev.n132_shutdown_result && gdev.n136_witness.type==N136_G2D_FINITE_JOBS_FROZEN && !gclock.enabled && gfifo_reads>0 && gjob_reads>0);
 lock(&gdev.lock_task);for(i=0;i<2;i++){jobs[0].flags=i;assert(g2d_device_run(&gdev,&jobs[0])==-ESHUTDOWN && !pushes);}unlock(&gdev.lock_task);
 g2d_fresh(1);lock(&gdev.lock_task);assert(!g2d_device_run(&gdev,&jobs[0]) && gdev.n136_ever_pushed && pushes==1);unlock(&gdev.lock_task);n132_g2d_shutdown(&gpdev);assert(gdev.n132_shutdown_result==-EBUSY && !gfifo_reads);
 g2d_fresh(1);foreign_gate=3;n132_g2d_shutdown(&gpdev);assert(gdev.n132_shutdown_result==-EBUSY && !gfifo_reads && !gclock.enabled);
 g2d_fresh(1);share_after_job=1;n132_g2d_shutdown(&gpdev);assert(gdev.n132_shutdown_result==-EBUSY && !gdev.n136_witness.committed);
 g2d_fresh(0);pmu[0x2300/4]=1;n132_g2d_shutdown(&gpdev);assert(gdev.n132_shutdown_result==-EIO && !gfifo_reads && !pm_gets);
 /* NPU new cold-only provider, history races and bounded first failure. */
 npu_fresh();n136_npu_shutdown(&npdev);assert(!n136_npu_result && n136_npu_witness.type==N136_NPU_DOMAINS_OFF_FROZEN && !pm_gets && !writes && pmu_reads==6);
 before=pmu_reads;assert(!n136_npu_prepare() && pmu_reads==before);assert(!n136_npu_event(N136_RESUME) && !n136_npu_event(N136_DEBUG));
 assert(!n136_npu_event(N136_FAULT) && n131_dma_status(ndev.dev)==-EIO && n136_npu_prepare()==-EIO && pmu_reads==before);
 for(i=1;i<=N136_MEMORY;i<<=1){npu_fresh();assert(n136_npu_event(i));n136_npu_shutdown(&npdev);assert(n136_npu_result==-EBUSY && !pmu_reads && !strcmp(last_reason,"lifetime-history"));}
 npu_fresh();n136_npu_is_ready=false;assert(!n136_npu_event(N136_FAULT));n136_npu_ready(&ndev);n136_npu_shutdown(&npdev);assert(n136_npu_result==-EBUSY && !pmu_reads);
 npu_fresh();assert(n136_npu_user_begin());n136_npu_shutdown(&npdev);assert(n136_npu_result==-EBUSY && !pmu_reads);n136_npu_user_end();
 npu_fresh();ndev.system.memory.map_count=1;n136_npu_shutdown(&npdev);assert(n136_npu_result==-EBUSY && !pmu_reads && !strcmp(last_reason,"mapped-buffer") && last_state==1 && last_value==0);
 npu_fresh();ndev.sessionmgr.session[2]=&ndev;n136_npu_shutdown(&npdev);assert(n136_npu_result==-EBUSY && last_item==2);
 npu_fresh();domain_on(0x1d00);domain_on(0x1d80);n136_npu_shutdown(&npdev);assert(n136_npu_result==-EBUSY && !pm_gets && !writes);
 npu_fresh();nclock.enabled=1;n136_npu_shutdown(&npdev);assert(n136_npu_result==-EBUSY && !pmu_reads);
 npu_fresh();n136_cal_lock.held=1;n136_npu_shutdown(&npdev);assert(n136_npu_result==-EBUSY && !pmu_reads);n136_cal_lock.held=0;
 npu_fresh();work_report.busy=1;n136_npu_shutdown(&npdev);assert(n136_npu_result==-EBUSY && !pmu_reads);
 npu_fresh();ndev.dev=&pdev.dev;n136_npu_shutdown(&npdev);assert(!n136_npu_seen && !pmu_reads);
 npu_fresh();n136_npu_shutdown(&npdev);n136_npu_witness.type=N136_SCORE_RESET_DMA_FROZEN;assert(n136_npu_prepare()==-EPERM);
 npu_fresh();n136_npu_shutdown(&npdev);n136_npu_detach(&ndev);assert(n136_npu_prepare()==-EBUSY);
 assert(last_stage && logs>0);puts("NEW typed terminal/accessibility/admission PASS");return 0;
}
'''


def fixture(raw,output):
    if digest(raw)!=FIXTURE_SHA:raise ValueError('accepted135 C scaffold bytes differ')
    old=raw.decode();text=old[:old.index('#define N133_SCORE_HARDWARE_TU')]
    text=text.replace('static int reset_busy_samples,reset_stuck,reset_reads;','static int reset_reads;')
    text=text.replace('typedef uint32_t u32;','typedef uint32_t u32;\n#include "v136_terminal.h"')
    text=text.replace('bool n133_terminal,n133_ever_booted;','bool n133_terminal,n133_ever_booted,n136_ever_rearmed;')
    text=text.replace('struct score_device {','struct score_device {struct n136_witness n136_witness;')
    text=text.replace('static struct score_device score;',SUPPORT+'\nstatic struct score_device score;')
    # SUPPORT refers only to types here; declarations using fixture globals are
    # moved below their original declarations before any native helper body.
    start=text.index(SUPPORT);text=text[:start]+text[start+len(SUPPORT):]
    at=text.index('static void message(');text=text[:at]+SUPPORT+'\n'+text[at:]
    text=text.replace('strstr(fmt," score reason=")','(strstr(fmt," score reason=") || strstr(fmt," npu reason="))')
    text=text.replace('assert(!strcmp(va_arg(ap,const char *),"score-test"));','assert(va_arg(ap,const char *)!=NULL);')
    text=text.replace('}else{last_stage=', '}else if(strstr(fmt," terminal witness=")){(void)va_arg(ap,unsigned int);(void)va_arg(ap,unsigned int);(void)va_arg(ap,const char *);\n    }else{last_stage=')
    text=text.replace('}else{last_stage=', '}else if(strstr(fmt," g2d reason=")){last_reason=va_arg(ap,const char *);last_item=va_arg(ap,unsigned int);last_state=(u32)va_arg(ap,unsigned long);last_value=va_arg(ap,int);(void)va_arg(ap,const char *);\n    }else{last_stage=')
    text=replace(text,'bus_for_each_dev','''static int bus_for_each_dev(void *bus,void *start,void *arg,int (*call)(struct device *,void *))
{int error;assert(bus==&platform_bus_type && !start);error=call(&pdev.dev,arg);if(!error && gpdev.dev.driver)error=call(&gpdev.dev,arg);if(!error && npdev.dev.driver)error=call(&npdev.dev,arg);return error;}''')
    # The device declarations must precede the generic bus iterator.
    text=text.replace('static struct platform_device pdev;', 'static struct platform_device pdev,gpdev,npdev;')
    text=text.replace('static struct platform_device gpdev,npdev;','')
    text=replace(text,'__clk_is_enabled','static int __clk_is_enabled(struct clk *p){(void)p;return 0;}\nstatic unsigned int __clk_get_enable_count(struct clk *p){return p->enabled+((p->id<2 && powered && foreign_gate==p->id+1) || (p->id==2 && gpowered && foreign_gate==3));}')
    text=replace(text,'clk_prepare_enable','static int clk_prepare_enable(struct clk *p){assert(p && (p->id==2?gpowered:powered));clock_gets++;if(clock_error && p->id==clock_error_id)return clock_error;p->enabled++;return 0;}')
    text=replace(text,'clk_disable','static void clk_disable(struct clk *p){assert(p && p->enabled>0 && (p->id==2?gforbid:pm_disabled));p->enabled--;clock_disables++;}')
    text=replace(text,'disable_irq_nosync','static void disable_irq_nosync(int irq){assert(irq==55 || irq==66);irq_disabled=1;}')
    text=replace(text,'synchronize_irq','static void synchronize_irq(int irq){assert((irq==55 || irq==66) && irq_disabled);irq_syncs++;}')
    text=replace(text,'pm_runtime_suspended','static int pm_runtime_suspended(struct device *p){return p==gdev.dev?!gpowered:!powered;}')
    text=replace(text,'pm_runtime_get_sync','''static int pm_runtime_get_sync(struct device *p)
{int error;pm_gets++;if(p==gdev.dev){assert(cal_reserved(N136_G2D_DOMAINS));gpowered=1;return 0;}assert(cal_reserved(N136_SCORE_DOMAINS));if(pm_error)return pm_error;powered=1;error=score_device_runtime_resume(p);return error;}''')
    text=replace(text,'readl','''static u32 readl(void *p)
{uintptr_t v=(uintptr_t)p,base=(uintptr_t)pmu,off;if(v>=base && v<base+sizeof(pmu)){pmu_reads++;return *(u32 *)p;}
 off=v-(uintptr_t)score.system.sfr;assert(cal_reserved(N136_SCORE_DOMAINS) && powered && clocks[0].enabled && clocks[1].enabled && irq_syncs && score.system.cache_slock.held);mmio_reads++;
 if(off==SW_RESET){reset_reads++;return 0;}assert(off==DMA0_QUEUE_STATUS || off==DMA1_QUEUE_STATUS || off==DMA2_QUEUE_STATUS || off==DMA3_QUEUE_STATUS);if(share_after_dma && off==DMA3_QUEUE_STATUS)foreign_gate=1;return registers[off/4];}''')
    text=replace(text,'writel','''static void writel(u32 value,void *p){assert(cal_reserved(N136_SCORE_DOMAINS) && (uintptr_t)p-(uintptr_t)score.system.sfr==SW_RESET && value==1);writes++;}''')
    # Only the changed providers and common writer helper are compiled here;
    # old main, old assertion batches and old host checks are discarded.
    text+='\n#include "v136_cal.inc"\n'
    text+='\n'+selected_cal_wrapper(output['drivers/soc/samsung/cal-if/cal-if.c'])+'\n'
    text+='static bool cal_reserved(unsigned int mask){return (n136_reserved_domains&mask)==mask;}\n'
    text+=extract(output['drivers/vision/score/hardware/v3/score_system.h'],'n136_score_writer_enter')+'\n'
    text+=extract(output['drivers/gpu/exynos/g2d/g2d.h'],'n136_g2d_io_enter')+'\n'
    text+='#define N133_SCORE_HARDWARE_TU\n'+output['drivers/vision/score/hardware/v3/v133_score.inc'].decode()+'\n#undef N133_SCORE_HARDWARE_TU\n'+output['drivers/vision/score/v133_score.inc'].decode()+'\n'
    text+=output['drivers/gpu/exynos/g2d/v132_g2d.inc'].decode()+'\n'
    text+=extract(output['drivers/gpu/exynos/g2d/g2d_drv.c'],'g2d_device_run')+'\n'
    text+=extract(output['drivers/vision/npu/npu-protodrv.c'],'n136_npu_protocol_cold')+'\n'
    text+=extract(output['drivers/vision/npu/interface/hardware/npu-interface.c'],'n136_npu_interface_cold')+'\n'
    text+='\n#include "v136_npu.inc"\n'+extract(raw,'fresh')+'\n'+MAIN
    return text


def reject(call):
    try:call()
    except ValueError:return
    raise AssertionError('NEW invalid input accepted')


def host_cases(output,result):
    prepare.profile(SETTINGS)
    for key in ('NPU_LOOPBACK','NPU_ZEBU_EMULATION'):reject(lambda key=key:prepare.profile(dict(SETTINGS,**{key:'y'})))
    reject(lambda:prepare.profile(dict(SETTINGS,NPU_HARDWARE='n')))
    reject(lambda:prepare.profile(dict(SETTINGS,PMUCAL_DBG='n')))
    kernel=output['arch/arm64/mm/v130_kernel.c']
    assert kernel.index(b'result=n133_score_prepare()')<kernel.index(b'result=n136_npu_prepare()')<kernel.index(b'result=n130_iommu_prepare()')
    for name in ('drivers/vision/score/v133_score.inc','drivers/gpu/exynos/g2d/v132_g2d.inc'):
        assert b'__clk_is_enabled(' not in output[name]
    wake=extract(output['drivers/vision/score/hardware/v3/score_system.c'],'score_system_wakeup')
    scq=extract(output['drivers/vision/score/hardware/v3/score_scq.c'],'score_scq_write')
    assert wake.index('n136_score_writer_enter')<wake.index('writel') and scq.index('n136_score_writer_enter')<scq.index('score_enter')
    execute=extract(output['drivers/gpu/exynos/g2d/g2d_task.c'],'g2d_execute_task')
    assert execute.index('n136_ever_pushed=true')<execute.index('g2d_secure_enable')
    assert b'n136_unittest_open' in output['drivers/vision/npu/npu-debug.c'] and b'if(!N136_DEBUG_ADMIT())' in output['drivers/vision/npu/npu-util-memdump.c']
    identity,cycle_id='a'*32,'b'*32
    raw=('N10XNU136 id='+identity+' cycle='+cycle_id+' stage=begin\nN10XNU136 id='+identity+' stage=npu-power-off errno=-16 owner=synthetic-npu\nN10XNU136 id='+identity+' npu reason=domains-on item=1 state=1 value=0 aux=0 owner=synthetic-npu\n').encode()
    decoded=cycle.decode({'synthetic':raw},identity,cycle_id)
    assert decoded['gate_refusals'][0]['stage']=='npu-power-off' and decoded['npu_refusal_details'][0]['reason']=='domains-on'
    typed=cycle.decode({'synthetic':raw+('N10XNU136 id='+identity+' terminal witness=3 domains=6 owner=synthetic-npu\nN10XNU136 id='+identity+' terminal witness=1 domains=6 owner=synthetic-npu\n').encode()},identity,cycle_id)
    assert typed['terminal_witness_commits']==[dict(type=3,domains=6,owner='synthetic-npu')]
    assert not typed['physical_XNU_entry_observed'] and not typed['full_XNU_boot_observed']
    result['NEW_host_cases']='actual profile, NEW writer-before-MMIO placement, producer/consumer136 NPU fields; immutable135/134 host cases not replayed'


def retained_host_result(path,expected,current):
    path=ordinary(path);raw=path.read_bytes()
    if digest(raw)!=hexid(expected) or expected!=ORIGINAL_HOST_RESULT_SHA:raise ValueError('exact preserved initial136 partial result required')
    partial=json.loads(raw);old=partial.get('source_sha256',{});test_name='note10/device_test/test_v136_terminal.py'
    if (partial.get('schema')!='note10-v136-terminal-result-v1' or partial.get('scope')!=SCOPE or partial.get('passed') is not False or
        partial.get('NEW_overlay_render_completed') is not True or
        partial.get('NEW_host_cases')!='actual profile, NEW writer-before-MMIO placement, producer/consumer136 NPU fields; immutable135/134 host cases not replayed' or
        partial.get('retained_fixture_sha256')!=FIXTURE_SHA or partial.get('device_operations')!=[] or
        any(type(partial.get(k)) is not int or partial[k]!=0 for k in ('compiler_invocations','fixture_processes','old_tests_replayed','Image_reads','raw_kernel_reads','adapter_reads','compressions')) or
        type(old) is not dict or set(old)!=set(NEW_FILES) or old.get(test_name)!=ORIGINAL_TEST_SHA or
        any(old[k]!=current[k] for k in NEW_FILES if k!=test_name) or
        not isinstance(partial.get('error'),str) or partial['error'].splitlines()[-1]!='ValueError: native function absent: bus_for_each_dev'):
        raise ValueError('only completed initial render/host phases and unexecuted C batch may continue')
    old_full=dict(RETAINED_SOURCE_SHA256,**old)
    if digest(json.dumps(old_full,sort_keys=True,separators=(',',':')).encode())!=ORIGINAL_SOURCE_MAP_SHA:raise ValueError('initial source73 scope differs')
    return {'result_sha256':expected,'source_map_sha256':ORIGINAL_SOURCE_MAP_SHA,'source_sha256':old,
            'NEW_overlay_render_completed':True,'NEW_host_cases':partial['NEW_host_cases'],
            'compiler_invocations':0,'fixture_processes':0,'host_cases_passed':True,'original_test_passed':False}


def retained_fixture_result(path,expected,current,carried):
    raw=ordinary(path).read_bytes()
    if expected!=PREVIOUS_FIXTURE_RESULT_SHA or digest(raw)!=hexid(expected):raise ValueError('exact second failed fixture result required')
    row=json.loads(raw);previous=dict(current);previous['note10/device_test/test_v136_terminal.py']=PREVIOUS_TEST_SHA
    if (row.get('schema')!='note10-v136-terminal-result-v1' or row.get('scope')!=SCOPE or row.get('passed') is not False or
        row.get('source_sha256')!={k:previous[k] for k in NEW_FILES} or row.get('retained_host_phase')!=carried or
        row.get('remaining_overlay_render_completed') is not True or row.get('initial_failed_result_preserved') is not True or
        row.get('initial_failed_result_sha256')!=ORIGINAL_HOST_RESULT_SHA or row.get('device_operations')!=[] or
        row.get('NEW_host_cases')!=carried['NEW_host_cases'] or row.get('NEW_overlay_render_completed') is not True or
        row.get('retained_fixture_sha256')!=FIXTURE_SHA or
        any(type(row.get(k)) is not int or row[k]!=v for k,v in dict(overlay_render_invocations=2,host_cases_invocations=1,passed_host_cases_replayed=0,compiler_invocations=0,fixture_processes=0,old_tests_replayed=0,Image_reads=0,raw_kernel_reads=0,adapter_reads=0,compressions=0).items()) or
        not isinstance(row.get('error'),str) or row['error'].splitlines()[-1]!='ValueError: one exact C definition required: cal_pd_control' or
        digest(json.dumps(previous,sort_keys=True,separators=(',',':')).encode())!=PREVIOUS_SOURCE_MAP_SHA):
        raise ValueError('second failure must be precompiler CAL extraction only')
    return dict(result_sha256=expected,source_map_sha256=PREVIOUS_SOURCE_MAP_SHA,source_sha256=row['source_sha256'],overlay_render_invocations=2,host_cases_invocations=1,compiler_invocations=0,fixture_processes=0)


def persist_checkpoint(out,output,raw,current,carried,previous):
    # Write every source fragment before the first fixture extractor can fail.
    folder=out/'overlay-checkpoint';folder.mkdir();entries={}
    for index,(name,data) in enumerate(sorted(output.items())):
        if not isinstance(name,str) or not isinstance(data,bytes):raise ValueError('source-only overlay checkpoint types differ')
        path=folder/(str(index)+'.source');path.write_bytes(data)
        entries[name]=dict(file=path.name,sha256=digest(data),bytes=len(data))
    (folder/'retained-fixture.c').write_bytes(raw)
    row=dict(schema='note10-v136-compile-input-checkpoint-v1',source_sha256=current,retained_host_phase=carried,retained_fixture_generation=previous,
             overlay_render_invocations=3,host_cases_invocations=1,compiler_invocations=0,fixture_processes=0,retained_fixture_sha256=FIXTURE_SHA,fragments=entries)
    encoded=(json.dumps(row,indent=2)+'\n').encode();path=folder/'checkpoint.json';path.write_bytes(encoded)
    return path,digest(encoded)


def load_checkpoint(path,expected,current,carried,previous):
    path=ordinary(path);encoded=path.read_bytes()
    if len(encoded)>2*1024*1024 or digest(encoded)!=hexid(expected):raise ValueError('checkpoint metadata bytes differ')
    row=json.loads(encoded);old=row.get('source_sha256',{});test_name='note10/device_test/test_v136_terminal.py'
    if (row.get('schema')!='note10-v136-compile-input-checkpoint-v1' or type(old) is not dict or set(old)!=set(current) or
        any(old[k]!=current[k] for k in current if k!=test_name) or row.get('retained_host_phase')!=carried or
        row.get('retained_fixture_generation')!=previous or row.get('retained_fixture_sha256')!=FIXTURE_SHA or
        any(type(row.get(k)) is not int or row[k]!=v for k,v in dict(overlay_render_invocations=3,host_cases_invocations=1,compiler_invocations=0,fixture_processes=0).items())):
        raise ValueError('checkpoint native/host/failed-generation provenance differs')
    fragments=row.get('fragments');output={};total=0
    if type(fragments) is not dict or not 1<=len(fragments)<=1024:raise ValueError('checkpoint fragment count differs')
    seen=set()
    for name,entry in fragments.items():
        if type(name) is not str or type(entry) is not dict or set(entry)!={'file','sha256','bytes'} or not re.fullmatch(r'[0-9]+\.source',entry['file']):raise ValueError('checkpoint fragment role differs')
        child=ordinary(path.parent/entry['file'])
        if child.parent!=path.parent or child in seen or type(entry['bytes']) is not int or not 0<=entry['bytes']<=8*1024*1024 or child.stat().st_size!=entry['bytes']:raise ValueError('checkpoint source extent differs')
        seen.add(child);data=child.read_bytes();total+=len(data)
        if total>64*1024*1024 or digest(data)!=hexid(entry['sha256']):raise ValueError('checkpoint source bytes differ')
        output[name]=data
    raw=ordinary(path.parent/'retained-fixture.c').read_bytes()
    if digest(raw)!=FIXTURE_SHA:raise ValueError('checkpoint retained fixture differs')
    return output,raw


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('output','cc','retained-fixture','retained-context','source128','resume-host-result','resume-fixture-result'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--stock-roots',type=Path,nargs='+',required=True)
    p.add_argument('--retained-context-sha256',required=True);p.add_argument('--resume-host-result-sha256',required=True)
    p.add_argument('--resume-fixture-result-sha256',required=True)
    p.add_argument('--resume-overlay-checkpoint',type=Path);p.add_argument('--resume-overlay-checkpoint-sha256');a=p.parse_args()
    if bool(a.resume_overlay_checkpoint)!=bool(a.resume_overlay_checkpoint_sha256):p.error('checkpoint path and SHA required together')
    out=private(a.output)
    if out.exists():p.error('one fresh136 output required')
    original_folder=ordinary(a.resume_host_result).parent
    if out==original_folder or out.is_relative_to(original_folder) or original_folder.is_relative_to(out):raise ValueError('remaining output must be disjoint from preserved initial result')
    prior_path=ordinary(a.retained_context)
    if sha(prior_path)!=a.retained_context_sha256:raise ValueError('retained135 PASS file differs')
    prior=read(prior_path);retained_continuation(prior,RETAINED_SOURCE_SHA256)
    if digest(json.dumps(prior,sort_keys=True,separators=(',',':')).encode())!=RETAINED_CONTEXT_SHA256:raise ValueError('retained135 canonical PASS differs')
    current=source_pins();carried=retained_host_result(a.resume_host_result,a.resume_host_result_sha256,current)
    previous=retained_fixture_result(a.resume_fixture_result,a.resume_fixture_result_sha256,current,carried)
    for path in (ordinary(a.resume_fixture_result),ordinary(a.resume_overlay_checkpoint) if a.resume_overlay_checkpoint else None):
        if path and (out==path.parent or out.is_relative_to(path.parent) or path.parent.is_relative_to(out)):raise ValueError('fresh output must be disjoint from retained failures/checkpoint')
    out.mkdir(parents=True);result=dict(schema='note10-v136-terminal-result-v1',scope=SCOPE,passed=False,compiler_invocations=0,fixture_processes=0,old_tests_replayed=0,source_sha256={k:v for k,v in current.items() if k in NEW_FILES},retained_fixture_sha256=FIXTURE_SHA,device_operations=[],Image_reads=0,raw_kernel_reads=0,adapter_reads=0,compressions=0,
        retained_host_phase=carried,retained_fixture_generation=previous,test_script_invocations=3,second_failed_result_preserved=True,second_failed_result_sha256=PREVIOUS_FIXTURE_RESULT_SHA,initial_failed_result_preserved=True,initial_failed_result_sha256=ORIGINAL_HOST_RESULT_SHA,
        NEW_overlay_render_completed=True,NEW_host_cases=carried['NEW_host_cases'],host_cases_invocations=1,passed_host_cases_replayed=0,overlay_render_invocations=2)
    try:
        if a.resume_overlay_checkpoint:
            output,raw=load_checkpoint(a.resume_overlay_checkpoint,a.resume_overlay_checkpoint_sha256,current,carried,previous)
            checkpoint_path=ordinary(a.resume_overlay_checkpoint);checkpoint_sha=a.resume_overlay_checkpoint_sha256
            result['overlay_checkpoint_reused']=True
        else:
            stock={}
            for name in prepare.PINS:
                candidates=[base.resolve()/name for base in a.stock_roots if (base/name).is_file()]
                if not candidates:raise ValueError('NEW native overlay input absent: '+name)
                stock[name]=ordinary(candidates[0]).read_bytes()
            raw=ordinary(a.retained_fixture).read_bytes()
            if digest(raw)!=FIXTURE_SHA:raise ValueError('accepted135 C scaffold differs')
            result['overlay_render_invocations']=3
            output=prepare.render(stock,'a'*32,a.source128.resolve())
            checkpoint_path,checkpoint_sha=persist_checkpoint(out,output,raw,current,carried,previous)
            result['overlay_checkpoint_reused']=False
        result['overlay_render_invocations']=3;result['remaining_overlay_render_completed']=True
        result['overlay_checkpoint_file']=str(checkpoint_path.relative_to(out)) if checkpoint_path.is_relative_to(out) else str(checkpoint_path)
        result['overlay_checkpoint_sha256']=checkpoint_sha
        # Persist the checkpoint binding before any extraction/fixture assembly.
        save(out/'result.json',result)
        generated=fixture(raw,output);source=out/'new-terminal.c';generated_raw=generated.encode();source.write_bytes(generated_raw)
        result['generated_C_file']='new-terminal.c';result['generated_C_sha256']=digest(generated_raw)
        (out/'result.json').write_text(json.dumps(result,indent=2)+'\n',newline='\n')
        include=out/'include/linux';include.mkdir(parents=True)
        for name in ('types.h','errno.h','mutex.h','spinlock.h','smp.h','device.h','printk.h','string.h','bitmap.h','interrupt.h','timer.h','clk-provider.h','rwsem.h','v130_kernel_api.h','note10_legacy_kexec_build.h'): (include/name).write_text('/* synthetic native dependency */\n',newline='\n')
        (include/'v136_terminal.h').write_bytes((HERE/'v136_terminal.h').read_bytes())
        executable=out/('new-terminal.exe' if sys.platform=='win32' else 'new-terminal')
        macros=['-DCONFIG_'+key+'=1' for key,value in SETTINGS.items() if value=='y']
        command=[str(ordinary(a.cc)),'-std=gnu11','-O2','-Wall','-Wextra','-Werror','-Wno-unused-function','-ferror-limit=0','-DSCORE_EVT1=1',*macros,'-I',str(out/'include'),'-I',str(HERE),str(source),'-o',str(executable)]
        result['compiler_invocations']=1
        with (out/'compile.log').open('wb') as log:subprocess.run(command,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=60)
        result['fixture_processes']=1
        with (out/'fixture.log').open('wb') as log:subprocess.run([str(executable)],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=15)
        result['passed']=True;raw_result=(json.dumps(result,indent=2)+'\n').encode();current=source_pins()
        delta=dict(schema='note10-v136-npu-terminal-pass-v1',scope=SCOPE,passed=True,result_sha256=digest(raw_result),source_sha256=result['source_sha256'])
        candidate=dict(schema='note10-v136-public-terminal-continuation-v1',scope=SCOPE,passed=True,retained_source_commit=RETAINED_COMMIT,retained_terminal_PASS=prior,delta_NEW_PASS=delta,source_sha256=current)
        continuation(candidate,current);encoded=encode_public(candidate)
        (out/'result.json').write_bytes(raw_result);save(out/'public-terminal-continuation.json',candidate);(out/'public-terminal-continuation.txt').write_text(encoded+'\n',encoding='ascii',newline='\n')
    except BaseException:
        import traceback
        result.update(error=traceback.format_exc());(out/'result.json').write_text(json.dumps(result,indent=2)+'\n',newline='\n');raise
    print(json.dumps({'passed':True,'compiler_invocations':1,'fixture_processes':1,'old_tests_replayed':0}))


if __name__=='__main__':main()
