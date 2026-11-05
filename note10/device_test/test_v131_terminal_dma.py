"""One NEW actual-source gate/contract batch; retained core/platform/PASS are not replayed."""
import argparse
import base64
import json
from pathlib import Path
import re
import subprocess
from v130_contract import ROOT,ordinary,private,read,save,sha,hexid
from v131_build import source_pins,continuation,NEW_FILES,SCOPE,RETAINED_COMMIT,SETTINGS
import v131_prepare as prepare
RETAINED_PARTIAL_PINS={'result.json': '30ccb70230c7df086c8de050a6972cfe2b7c06f068a86bcd966457fb570d5740', 'fixture.log': 'b5faf7d8bbb19f2c17dccc19d78dfd7d1510900a9a9c5bd030e5214d0e932393', 'test_source': '39e52668a7b36a14436223c69bf67d1b47ecec2932e0a752db51a621b275d3f4'}


def retained_partial(path,current):
    path=ordinary(path)
    if sha(path)!=RETAINED_PARTIAL_PINS['result.json'] or sha(ordinary(path.parent/'fixture.log'))!=RETAINED_PARTIAL_PINS['fixture.log']:
        raise ValueError('exact original failed-boundary evidence required')
    prior=read(path);expected=dict(current)
    expected['note10/device_test/test_v131_terminal_dma.py']=RETAINED_PARTIAL_PINS['test_source']
    if (prior.get('schema')!='note10-v131-terminal-dma-result-v1' or prior.get('passed') is not False or
        prior.get('compiler_invocations')!=1 or prior.get('fixture_processes')!=1 or
        prior.get('current_source_sha256')!=expected or prior.get('source_sha256')!={name:expected[name] for name in NEW_FILES}):
        raise ValueError('partial observations cannot migrate across production source changes')
    return dict(result_sha256=RETAINED_PARTIAL_PINS['result.json'],fixture_log_sha256=RETAINED_PARTIAL_PINS['fixture.log'],
        original_test_source_sha256=RETAINED_PARTIAL_PINS['test_source'],replayed=False,
        observed_before_failure=['unknown catalog lookup refuses','mismatched UFS hba device refuses','pre-arm UFS refuses','initial ready record accepted'])


def function(raw,name):
    pattern=r'(?m)^(?:static )?(?:inline )?(?:int|void|bool) '+re.escape(name)+r'\([^\n]*\)\n\{'
    matches=list(re.finditer(pattern,raw))
    if len(matches)!=1:raise ValueError('actual unique function required: '+name)
    start=matches[0].start();at=raw.index('{',start)+1;depth=1
    while depth and at<len(raw):depth+=(raw[at]=='{')-(raw[at]=='}');at+=1
    if depth:raise ValueError('actual function is not closed')
    return raw[start:at]+'\n'


def without_includes(raw):return '\n'.join(line for line in raw.splitlines() if not line.startswith('#include'))+'\n'


def fixture(output,stock):
    registry=without_includes(output['arch/arm64/mm/v131_dma_registry.inc'].decode())
    ufs=without_includes(output['drivers/scsi/ufs/v130_ufs.inc'].decode())
    iommu=without_includes(output['drivers/iommu/v130_iommu.inc'].decode())
    shutdown=function(output['drivers/scsi/ufs/ufshcd.c'].decode(),'ufshcd_shutdown')
    pl330=without_includes(output['drivers/dma/v130_pl330.inc'].decode())
    native=stock['drivers/iommu/exynos-iommu.h'].decode()
    predicates=''.join(function(native,name) for name in ('is_sysmmu_runtime_active','is_runtime_active_or_enabled','is_sysmmu_active'))
    prefix=r'''#include <assert.h>
#include <errno.h>
#include <stddef.h>
#include <stdbool.h>
#include <stdio.h>
#include <string.h>
#include <stdarg.h>
#if !defined(CONFIG_NOTE10_XNU_KEXEC_HANDOFF) || CONFIG_NOTE10_XNU_KEXEC_HANDOFF != 1
#error "Compile the actual native shutdown hook with the reviewed handoff profile"
#endif
#define N10_KEXEC_BUILD_ID "0123456789abcdef0123456789abcdef"
#define READ_ONCE(x) (x)
#define WRITE_ONCE(x,v) ((x)=(v))
#define ARRAY_SIZE(x) (sizeof(x)/sizeof((x)[0]))
typedef struct {int id;} spinlock_t;
static unsigned int locks;static int data_locks,logs;
static void lock(spinlock_t *p){assert(!(locks&(1U<<p->id)));if(p->id==2){assert(locks&(1U<<1));data_locks++;}locks|=1U<<p->id;}
static void unlock(spinlock_t *p){assert(locks&(1U<<p->id));locks&=~(1U<<p->id);}
#define DEFINE_SPINLOCK(n) spinlock_t n={3}
#define spin_lock_irqsave(p,f) do{(f)=0;lock(p);}while(0)
#define spin_unlock_irqrestore(p,f) do{(void)(f);unlock(p);}while(0)
#define spin_lock(p) lock(p)
#define spin_unlock(p) unlock(p)
struct list_head {struct list_head *next,*prev;};
static void init_list(struct list_head *h){h->next=h->prev=h;}
static void add(struct list_head *h,struct list_head *n){n->next=h;n->prev=h->prev;h->prev->next=n;h->prev=n;}
#define container_of(p,t,m) ((t *)((char *)(p)-offsetof(t,m)))
#define list_empty(h) ((h)->next==(h))
#define list_for_each_entry(p,h,m) for(p=container_of((h)->next,__typeof__(*p),m);&(p)->m!=(h);p=container_of((p)->m.next,__typeof__(*p),m))
struct device_driver {int unused;};
struct device {struct device_driver *driver;void *data;const char *name;};
static void *dev_get_drvdata(struct device *d){return d->data;}
static const char *dev_name(struct device *d){return d->name;}
static void message(const char *format,...){(void)format;logs++;}
#define pr_emerg(...) message(__VA_ARGS__)
#define dev_err(...) ((void)0)
static int n130_arm_state=2;
static struct {struct device *device;int result;} n130_dma[128];
static unsigned int n130_dma_count;
int n131_dma_status(struct device *);
void n131_gate_refused(const char *,int,struct device *);
struct SEC_UFS_op_count {int HW_RESET_count;};struct SEC_UFS_UIC_err_count {int UIC_err;};
struct SEC_UFS_UTP_count {int UTP_err;};struct SEC_UFS_QUERY_count {int Query_err;};
struct SEC_UFS_counting {struct SEC_UFS_op_count op_count;struct SEC_UFS_UIC_err_count UIC_err_count;struct SEC_UFS_UTP_count UTP_count;struct SEC_UFS_QUERY_count query_count;};
struct ufs_host {int medium_err_cnt,hw_err_cnt;};
enum {UFS_ACTIVE_PWR_MODE=1,UFS_POWERDOWN_PWR_MODE=3,UIC_LINK_OFF_STATE=0,UIC_LINK_ACTIVE_STATE=1,UFS_SHUTDOWN_PM=2};
struct ufs_hba {struct device *dev;int curr_dev_pwr_mode,uic_link_state;struct SEC_UFS_counting SEC_err_info;struct ufs_host *host;};
#define ufshcd_is_ufs_dev_poweroff(h) ((h)->curr_dev_pwr_mode==UFS_POWERDOWN_PWR_MODE)
#define ufshcd_is_link_off(h) ((h)->uic_link_state==UIC_LINK_OFF_STATE)
static int suspend_result,resume_result,pm_suspended,suspend_calls;
static int pm_runtime_suspended(struct device *d){(void)d;return pm_suspended;}
static int ufshcd_runtime_resume(struct ufs_hba *h){(void)h;return resume_result;}
static int ufshcd_suspend(struct ufs_hba *h,int mode){assert(mode==UFS_SHUTDOWN_PM);suspend_calls++;if(!suspend_result){h->curr_dev_pwr_mode=UFS_POWERDOWN_PWR_MODE;h->uic_link_state=UIC_LINK_OFF_STATE;}return suspend_result;}
static struct {struct device_driver driver;} exynos_ufs_driver;
static int platform_bus_type;static struct device *ufs_device;
static int bus_for_each_dev(void *bus,void *start,void *arg,int (*call)(struct device *,void *)){assert(bus==&platform_bus_type && !start);return call(ufs_device,arg);}
struct sysmmu_drvdata {spinlock_t lock;int activations,runtime_active,no_rpm_control,is_suspended;};
struct sysmmu_list_data {struct list_head node;struct device *sysmmu;};
struct exynos_iommu_owner {struct exynos_iommu_owner *next;spinlock_t lock;struct device *master;struct list_head sysmmu_list;};
static struct exynos_iommu_owner *sysmmu_owner_list;
enum {SYSMMU_USE_RUNTIME_ACTIVE=0,SYSMMU_STATE_DISABLED,SYSMMU_STATE_ENABLED};
struct dma_chan {struct list_head device_node;int client_count;};
struct dma_device {struct device *dev;struct list_head channels;int (*device_alloc_chan_resources)(struct dma_chan *);};
struct dma_pl330_chan {struct dma_chan chan;void *thread;int active;struct list_head submitted_list,work_list,completed_list;};
static struct dma_pl330_chan *to_pchan(struct dma_chan *c){return container_of(c,struct dma_pl330_chan,chan);}
struct thread {int state,req_running;};
struct pl330_dmac {struct dma_device ddma;spinlock_t lock;int n130_ever_allocated;struct thread *manager,*channels;struct list_head req_done;struct {unsigned int num_chan;} pcfg;int tasks;};
struct amba_device {struct device dev;unsigned int irq[2];};
#define AMBA_NR_IRQS 2
#define PL330_STATE_STOPPED 0
static int _state(struct thread *t){return t->state;}
static int pl330_alloc_chan_resources(struct dma_chan *c){(void)c;return 0;}
static int pm_runtime_get_sync(struct device *d){(void)d;return 0;}
static void pm_runtime_put_noidle(struct device *d){(void)d;}
static void pm_runtime_forbid(struct device *d){(void)d;}
static void disable_irq(unsigned int n){(void)n;}
static void synchronize_irq(unsigned int n){(void)n;}
static void tasklet_kill(int *t){(void)t;}
'''
    # Native SEC diagnostic variables are intentionally retained; dev_err stub consumes none.
    cases=r'''int main(void)
{
    struct ufs_host host={0};struct ufs_hba hba={0};
    struct device ufsdev={&exynos_ufs_driver.driver,&hba,"ufs"},unknown={NULL,NULL,"unproven"};
    struct sysmmu_drvdata data={{2},1,1,0,0};struct device sysmmu={NULL,&data,"sysmmu"};
    struct sysmmu_list_data item;struct exynos_iommu_owner owner={0};
    struct amba_device amba={{NULL,NULL,"pdma"},{0,0}};
    struct thread manager={PL330_STATE_STOPPED,-1},channel={PL330_STATE_STOPPED,-1};
    struct pl330_dmac controller={0};
    hba.dev=&ufsdev;hba.host=&host;ufs_device=&ufsdev;
    /* Earlier assertions are retained from the exact failed-run boundary.
     * Only initialize the ready cache needed by the corrected errno case. */
    (void)n130_dma_record(&ufsdev,0);
    hba.curr_dev_pwr_mode=UFS_ACTIVE_PWR_MODE;hba.uic_link_state=UIC_LINK_ACTIVE_STATE;
    suspend_result=-ETIMEDOUT;
    assert(n130_ufs_prepare()==-ETIMEDOUT && n131_dma_status(&ufsdev)==-ETIMEDOUT && !n130_dma_ready(&ufsdev));
    suspend_result=0;assert(!n130_ufs_prepare() && n130_dma_ready(&ufsdev));
    {int before=suspend_calls;assert(!n130_ufs_prepare() && suspend_calls==before && n131_dma_status(&ufsdev)==0);}
    hba.curr_dev_pwr_mode=UFS_ACTIVE_PWR_MODE;hba.uic_link_state=UIC_LINK_ACTIVE_STATE;pm_suspended=1;resume_result=-EIO;
    assert(n130_ufs_prepare()==-EIO && n131_dma_status(&ufsdev)==-EIO);pm_suspended=0;resume_result=0;
    assert(!n130_ufs_prepare());
    owner.lock.id=1;owner.master=&unknown;init_list(&owner.sysmmu_list);item.sysmmu=&sysmmu;add(&owner.sysmmu_list,&item.node);sysmmu_owner_list=&owner;
    assert(n130_iommu_prepare()==-ENOENT && n130_iommu_final()==-EBUSY && data_locks==1 && !locks);
    data.activations=0;data.runtime_active=0;data.is_suspended=1;
    assert(n130_iommu_prepare()==-ENOENT && !locks); /* No inactive unknown-owner bypass. */
    owner.master=&ufsdev;assert(!n130_iommu_prepare() && !n130_iommu_final() && !locks);
    assert(n130_dma_record(&ufsdev,-EINPROGRESS)==-EINPROGRESS);
    assert(n130_iommu_prepare()==-EINPROGRESS && n130_iommu_final()==-EBUSY);
    assert(!n130_dma_record(&ufsdev,0));sysmmu.data=NULL;
    assert(n130_iommu_prepare()==-ENODEV && !locks);sysmmu.data=&data;
    controller.ddma.dev=&amba.dev;controller.ddma.device_alloc_chan_resources=pl330_alloc_chan_resources;
    init_list(&controller.ddma.channels);init_list(&controller.req_done);controller.lock.id=4;
    controller.manager=&manager;controller.channels=&channel;controller.pcfg.num_chan=1;
    channel.state=1;assert(n130_pl330_quiet(&controller.ddma)==-EBUSY && n131_dma_status(&amba.dev)==-ENOENT);
    channel.state=PL330_STATE_STOPPED;assert(!n130_pl330_quiet(&controller.ddma) && n130_dma_ready(&amba.dev));
    owner.master=&amba.dev;assert(!n130_iommu_prepare());
    n130_dma_count=ARRAY_SIZE(n130_dma);assert(n130_dma_record(&unknown,0)==-ENOSPC && n131_dma_status(&unknown)==-ENOENT);
    assert(logs && !locks);puts("NEW terminal DMA gates PASS");return 0;
}
'''
    return prefix+predicates+registry+shutdown+ufs+iommu+pl330+cases


def reject(call):
    try:call()
    except ValueError:return
    raise AssertionError('successor admission did not reject')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--scope',required=True,choices=[SCOPE]);p.add_argument('--source-evidence',type=Path,required=True)
    p.add_argument('--source128',type=Path,required=True);p.add_argument('--retained-pass',type=Path,required=True)
    p.add_argument('--retained-partial-result',type=Path,required=True)
    p.add_argument('--retained-pass-sha256',required=True);p.add_argument('--cc',required=True,type=Path);p.add_argument('--output',required=True,type=Path)
    a=p.parse_args();out=private(a.output);prior=ordinary(a.retained_pass);cc=ordinary(a.cc)
    if out.exists() or sha(prior)!=hexid(a.retained_pass_sha256):p.error('fresh NEW output and exact retained final130 context required')
    current=source_pins();delta={name:current[name] for name in NEW_FILES};partial=retained_partial(a.retained_partial_result,current)
    candidate=dict(schema='note10-v131-public-terminal-dma-continuation-v1',scope=SCOPE,passed=True,retained_source_commit=RETAINED_COMMIT,
        retained_host_power_PASS=read(prior),delta_NEW_PASS=dict(schema='note10-v131-terminal-dma-pass-v1',scope=SCOPE,passed=True,result_sha256='0'*64,source_sha256=delta),source_sha256=current)
    out.mkdir(parents=True);save(out/'attempt.json',dict(schema='note10-v131-terminal-dma-attempt-v1',scope=SCOPE,source_sha256=delta))
    result=dict(schema='note10-v131-terminal-dma-result-v1',scope=SCOPE,passed=False,source_sha256=delta,current_source_sha256=current,
        compiler_invocations=0,fixture_processes=0,old_tests_replayed=0,retained_partial_observations=partial,
        fixture_profile='CONFIG_'+prepare.OPTION+'=1',raw_kernel_reads=0,adapter_reads=0,compressions=0,Image_reads=0,Image_builds=0,device_operations=[])
    try:
        continuation(candidate,current)
        if SETTINGS.get(prepare.OPTION)!='y':raise ValueError('fixture requires actual production handoff profile enabled')
        stock={name:ordinary(a.source_evidence/name).read_bytes() for name in prepare.PINS}
        rendered=prepare.render(stock,'0123456789abcdef0123456789abcdef',a.source128)
        # Assert the new call boundary lands on actual shared shutdown out path.
        shutdown=function(rendered['drivers/scsi/ufs/ufshcd.c'].decode(),'ufshcd_shutdown')
        assert shutdown.index('out:')<shutdown.index('n130_dma_record')<shutdown.index('/* allow force shutdown')
        assert 'ret ? ret :' in shutdown
        kernel=rendered['arch/arm64/mm/v130_kernel.c'].decode()
        assert '#include "v131_dma_registry.inc"' in kernel and 'N10XNU130' not in kernel
        assert kernel.index('n130_usb_prepare()')<kernel.index('n130_ufs_prepare()')<kernel.index('n130_iommu_prepare()')
        path=out/'new-terminal-dma.c';path.write_text(fixture(rendered,stock),encoding='utf-8',newline='\n')
        executable=out/('new-terminal-dma.exe' if cc.suffix.lower()=='.exe' else 'new-terminal-dma')
        result['compiler_invocations']=1
        with (out/'compile.log').open('wb') as stream:
            subprocess.run([str(cc),'-std=gnu11','-O2','-Wall','-Wextra','-Werror','-Wno-unused-variable','-DCONFIG_'+prepare.OPTION+'=1',str(path),'-o',str(executable)],cwd=ROOT,stdout=stream,stderr=subprocess.STDOUT,check=True,timeout=60)
        result['fixture_processes']=1
        with (out/'fixture.log').open('wb') as stream:subprocess.run([str(executable)],cwd=ROOT,stdout=stream,stderr=subprocess.STDOUT,check=True,timeout=15)
        # Fresh version routing rejects old plans/approvals; no transport call occurs.
        import v131_cycle as cycle
        import v131_package as package
        assert cycle.LEDGER_SCHEMA=='note10-v131-owned-XNU-ledger-v1'
        assert cycle.APPROVAL_SCHEMA=='note10-v131-physical-approval-v1'
        assert package.PLAN_SCHEMA=='note10-v131-owned-xnu-cycle-v1'
        assert package.INPUTS_SCHEMA=='note10-v131-package-inputs-v1'
        identity='0123456789abcdef0123456789abcdef';cycle_id='fedcba9876543210fedcba9876543210'
        begin='N10XNU131 id='+identity+' cycle='+cycle_id+' stage=begin\n'
        refusal='N10XNU131 id='+identity+' stage=iommu-owner errno=-2 owner=unproven\n'
        observation=cycle.decode({'synthetic':(begin+refusal).encode()},identity,cycle_id)
        assert observation['gate_refusals']==[dict(stage='iommu-owner',errno=-2,owner='unproven')]
        assert not observation['physical_XNU_entry_observed'] and not observation['XNU_executed']
        assert cycle.decode({'synthetic':refusal.encode()},identity,cycle_id)['gate_refusals']==[]
        assert cycle.decode({'synthetic':(begin+refusal.replace(identity,'0'*32)).encode()},identity,cycle_id)['gate_refusals']==[]
        old_input=out/'synthetic-old-inputs.json';save(old_input,dict(schema='note10-v130-package-inputs-v1',inputs={}))
        reject(lambda:package.contract(old_input,sha(old_input)))
        old_plan=out/'synthetic-old-plan.json';save(old_plan,dict(schema='note10-v130-owned-xnu-cycle-v1',version='v130'))
        reject(lambda:package.validate_plan(old_plan,sha(old_plan)))
        rows=[dict(partition=name,file=name+'.img',sha256='1'*64,size=4096,block_node='/dev/block/sda'+str(i),remote_hash_before_and_after_match=True)
            for i,name in enumerate(sorted(package.PARTITIONS),1)]
        baseline=dict(schema='note10-v130-private-xnu-package-v1',version='v130',cycle='3'*32,build_evidence_id='4'*32,
            diagnostic_BOOT_sha256='2'*64,rollback_BOOT_sha256='1'*64,bootloader='synthetic',partitions=rows)
        ledger=dict(schema='note10-v130-owned-XNU-ledger-v1',recovery_returned=True,host_BOOT_write_attempts=1,host_reboot_attempts=1,
            cycle='3'*32,build_evidence_id='4'*32,normal_recovery_fallback_observed=False,status='cycle-complete-XNU-proof-limits-retained',
            internal_kexec_load_attempts_observed=1,internal_kexec_REBOOT_attempts_observed=1)
        backup=dict(complete=True,partition_writes=False,partitions=rows,bootloader='synthetic')
        assert package.current_and_restore(baseline,ledger,backup)[0]=='2'*64
        reject(lambda:package.current_and_restore(dict(baseline,version='v129'),ledger,backup))
        reject(lambda:package.current_and_restore(baseline,dict(ledger,host_BOOT_write_attempts=2),backup))
        reject(lambda:package.current_and_restore(baseline,dict(ledger,host_BOOT_write_attempts=True),backup))
        for key in ('passed','retained_source_commit'):
            bad=json.loads(json.dumps(candidate));bad[key]=False if key=='passed' else '0'*40;reject(lambda:continuation(bad,current))
        bad=json.loads(json.dumps(candidate));bad['delta_NEW_PASS']['source_sha256'][NEW_FILES[0]]='0'*64;reject(lambda:continuation(bad,current))
        bad=json.loads(json.dumps(candidate));bad['retained_host_power_PASS']['passed']=True;reject(lambda:continuation(bad,current))
        if source_pins()!=current:raise ValueError('successor sources changed during NEW batch')
        result.update(passed=True,cases=['actual shutdown errno/fresh cache/early out','no missing/pending/overflow terminal proof','owner then controller locks','inactive unknown owner refuses','missing controller refuses','PL330 proof recorded only after genuine STOPPED checks','fresh v131 schemas','exact retained source33 and new PASS binding'])
    except Exception:
        import traceback
        result['error']=traceback.format_exc()
    save(out/'result.json',result)
    if result['passed']:
        candidate['delta_NEW_PASS']['result_sha256']=sha(out/'result.json');continuation(candidate,current)
        save(out/'public-terminal-dma-continuation.json',candidate)
        (out/'public-terminal-dma-continuation.b64').write_bytes(base64.b64encode(json.dumps(candidate,separators=(',',':')).encode())+b'\n')
    return 0 if result['passed'] else 1


if __name__=='__main__':raise SystemExit(main())
