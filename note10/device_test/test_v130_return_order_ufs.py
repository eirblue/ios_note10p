"""One NEW return-phase/UFS-visibility/continuation batch; no old fixtures or private payload stages."""
import argparse
import ast
import base64
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
from v130_contract import ROOT,ordinary,private,sha,read,save,hexid
from v130_build import source_pins,return_order_context,RETURN_SCOPE,RETURN_FILES,PID1_FIX_SOURCE_COMMIT
import v130_prepare as prepare
HERE=Path(__file__).resolve().parent


def function(raw,name):
    found=list(re.finditer(r'(?m)^(?:int|void) '+re.escape(name)+r'\([^\n]*\)\n\{',raw))
    if len(found)!=1:raise ValueError('unique actual new function boundary required: '+name)
    start=found[0].start();at=raw.index('{',start);depth=1;at+=1
    while depth and at<len(raw):
        depth+=(raw[at]=='{')-(raw[at]=='}');at+=1
    if depth:raise ValueError('actual new function closing boundary missing')
    return raw[start:at]+'\n'


def enum(raw,name):
    found=re.findall(r'enum '+re.escape(name)+r'\s*\{[^}]+\};',raw)
    if len(found)!=1:raise ValueError('actual source/header enum boundary differs: '+name)
    return found[0]+'\n'


def fixture(kernel,ufs,ufshcd_header,ufs_header,hook):
    prefix=r'''#include <assert.h>
#include <errno.h>
#include <setjmp.h>
#include <stddef.h>
#include <stdio.h>
#include <string.h>
struct kimage { int unused; }; struct n10_wdt_witness { int ok; };
static struct kimage image;static const struct kimage *n130_pending_image;
static int n130_return_owner,n130_arm_state,n130_deadline;
static int markers,wdts,qualified,dmas,sync_cancel,async_cancel,resets,phase,race;
static jmp_buf escape;
int n130_recovery_claim(void);
#define READ_ONCE(x) (x)
#define WRITE_ONCE(x,v) ((x)=(v))
#define pr_emerg(...) ((void)0)
#define BUG() longjmp(escape,2)
'''
    types=enum(kernel,'n130_return_phase')
    stubs=r'''static int cas(int *p,int old,int wanted)
{int value;if(p==&n130_return_owner && wanted==N130_HARDWARE && race==3){race=0;assert(n130_recovery_claim()==-EBUSY);}value=*p;if(value==old)*p=wanted;if(p==&n130_return_owner && wanted==N130_HARDWARE && value==old && race==4){race=0;assert(n130_recovery_claim()==-EBUSY);}return value;}
#define cmpxchg(p,a,b) cas(p,a,b)
static int exchange(int *p,int wanted){int old=*p;*p=wanted;return old;}
#define xchg(p,v) exchange(p,v)
static int n10_kexec_check_image(const struct kimage *p){return p==&image && n130_arm_state==1?0:-EPERM;}
static int n10_sec_stage_kexec_recovery(void)
{markers++;if(n130_return_owner==N130_ARMING && race==1){race=0;assert(n130_recovery_claim()==-EBUSY);}return phase==1?-EIO:0;}
static int n10_wdt_stage_kexec_return(struct n10_wdt_witness *w)
{wdts++;if(race==2){race=0;assert(n130_recovery_claim()==-EBUSY);}w->ok=1;return phase==2?-EIO:0;}
static int n10_watchdog_qualified(const struct n10_wdt_witness *w){qualified=w->ok && phase!=3;return qualified?0:-EIO;}
static int cancel_delayed_work(void *work){(void)work;async_cancel++;n130_deadline=0;return 0;}
static int cancel_delayed_work_sync(void *work){(void)work;assert(qualified && n130_return_owner==N130_HARDWARE);sync_cancel++;n130_deadline=0;return 0;}
static int n130_dmaengine_prepare(void){assert(qualified && n130_return_owner==N130_HARDWARE && sync_cancel==1);dmas++;return phase==4?-EIO:0;}
static void machine_restart(const char *reason){assert(!strcmp(reason,"recovery"));resets++;longjmp(escape,1);}
'''
    bodies=''.join(function(kernel,name) for name in ('n130_recovery_claim','n130_before_shutdown','n130_before_device_shutdown','n130_terminal_recovery'))
    ufs_types=enum(ufs_header,'ufs_dev_pwr_mode')+enum(ufshcd_header,'uic_link_state')
    link=re.findall(r'(?m)^#define ufshcd_is_link_off[^\n]+',ufshcd_header)
    if len(link)!=1:raise ValueError('actual header-visible UFS link predicate differs')
    ufs_prefix=r'''struct device_driver {int unused;};struct ufs_hba {enum ufs_dev_pwr_mode curr_dev_pwr_mode;enum uic_link_state uic_link_state;};
struct device {struct device_driver *driver;struct ufs_hba *hba;};struct platform_driver {struct device_driver driver;};
static struct platform_driver exynos_ufs_driver;static int platform_bus_type,ready;
static struct ufs_hba hba;static struct device ufs_device;
static void *dev_get_drvdata(struct device *device){return device->hba;}
static int n130_dma_ready(struct device *device){assert(device==&ufs_device);return ready;}
static int ufshcd_shutdown(struct ufs_hba *p){assert(p==&hba);return 0;}
static int bus_for_each_dev(void *bus,void *start,void *data,int (*callback)(struct device *,void *))
{assert(bus==&platform_bus_type && !start);return callback(&ufs_device,data);}
'''
    ufs_body='\n'.join(line for line in ufs.splitlines() if not line.startswith('#include'))+'\n'
    consumer='static void actual_pre_device_hook(char *cmd)\n{\n'+hook+'\n}\n'
    suffix=r'''static void fresh(void)
{n130_pending_image=NULL;n130_return_owner=N130_IDLE;n130_arm_state=1;n130_deadline=1;markers=wdts=qualified=dmas=sync_cancel=async_cancel=resets=phase=race=0;}
static void started(void)
{assert(!n130_before_shutdown(&image));assert(n130_return_owner==N130_IDLE && n130_deadline==1 && markers==1 && !wdts && !dmas && !sync_cancel && !async_cancel);}
static void run_hook(int failure)
{int jumped=setjmp(escape);if(!jumped){actual_pre_device_hook(NULL);assert(!failure);}else{assert(failure && resets==1 && n130_arm_state==4 && n130_return_owner==N130_RECOVERY && !n130_pending_image);}}
int main(void)
{
 int i;
 fresh();started();run_hook(0);assert(qualified && dmas==1 && sync_cancel==1 && !n130_deadline && n130_return_owner==N130_HARDWARE);
 fresh();started();assert(!n130_recovery_claim());assert(n130_return_owner==N130_RECOVERY && async_cancel==1);run_hook(1);assert(!wdts && !dmas && !sync_cancel);
 for(i=1;i<=3;i++){fresh();started();race=i;run_hook(1);assert(!dmas && !sync_cancel && !async_cancel);if(i==1)assert(!wdts);else assert(wdts==1);}
 fresh();started();race=4;run_hook(0);assert(dmas==1 && sync_cancel==1 && n130_return_owner==N130_HARDWARE);
 for(i=1;i<=4;i++){fresh();started();phase=i;run_hook(1);assert(dmas==(i==4));assert(sync_cancel==(i==4));}
 fresh();phase=1;assert(n130_before_shutdown(&image)==-EIO && !n130_pending_image && n130_return_owner==N130_IDLE && n130_deadline==1 && !wdts && !dmas);
 fresh();actual_pre_device_hook("recovery");assert(!wdts && !dmas && !sync_cancel);
 ufs_device.driver=&exynos_ufs_driver.driver;ufs_device.hba=&hba;ready=1;hba.curr_dev_pwr_mode=UFS_POWERDOWN_PWR_MODE;hba.uic_link_state=UIC_LINK_OFF_STATE;n130_ufs_count=0;assert(!n130_ufs_prepare());
 n130_ufs_count=0;hba.curr_dev_pwr_mode=UFS_ACTIVE_PWR_MODE;assert(n130_ufs_prepare()==-EIO);
 n130_ufs_count=0;hba.curr_dev_pwr_mode=UFS_POWERDOWN_PWR_MODE;hba.uic_link_state=UIC_LINK_ACTIVE_STATE;assert(n130_ufs_prepare()==-EIO);
 n130_ufs_count=0;hba.uic_link_state=UIC_LINK_OFF_STATE;ready=0;assert(n130_ufs_prepare()==-EIO);
 puts("NEW actual return-phase ownership/deadline races and cross-TU UFS off predicate PASS");return 0;
}
'''
    return (prefix+types+stubs+bodies+ufs_types+link[0]+'\n'+ufs_prefix+ufs_body+consumer+suffix).encode()


def reject(call):
    try:call()
    except ValueError:return
    raise AssertionError('new return-order continuation rejection did not reject')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--scope',required=True,choices=[RETURN_SCOPE]);p.add_argument('--compiler',required=True,type=Path)
    p.add_argument('--compiler-arg',action='append',default=[]);p.add_argument('--stock-source',required=True,type=Path)
    p.add_argument('--retained-continuation-pass',required=True,type=Path);p.add_argument('--retained-pass-sha256',required=True)
    p.add_argument('--output',required=True,type=Path);a=p.parse_args();out=private(a.output);compiler=ordinary(a.compiler)
    retained=ordinary(a.retained_continuation_pass)
    if out.exists() or sha(retained)!=hexid(a.retained_pass_sha256):p.error('fresh output and exact retained6b PASS required')
    current=source_pins();delta={name:current[name] for name in RETURN_FILES}
    candidate=dict(schema='note10-v130-public-return-order-pass-v1',scope=RETURN_SCOPE,passed=True,retained_source_commit=PID1_FIX_SOURCE_COMMIT,
        retained_continuation_PASS=read(retained),delta_NEW_PASS=dict(schema='note10-v130-return-order-ufs-delta-pass-v1',scope=RETURN_SCOPE,passed=True,result_sha256='0'*64,source_sha256=delta),source_sha256=current)
    return_order_context(candidate,current);out.mkdir(parents=True)
    save(out/'attempt.json',dict(schema='note10-v130-return-order-ufs-attempt-v1',scope=RETURN_SCOPE,source_sha256=delta))
    result=dict(schema='note10-v130-return-order-ufs-delta-result-v1',scope=RETURN_SCOPE,passed=False,source_sha256=delta,current_source_sha256=current,
        retained_source_commit=PID1_FIX_SOURCE_COMMIT,compiler_invocations=0,fixture_processes=0,old_tests_replayed=0,
        raw_kernel_reads=0,adapter_reads=0,compressions=0,Image_reads=0,Image_builds=0,device_operations=[])
    try:
        stock={name:(a.stock_source/name).read_bytes() for name in prepare.PINS}
        source128=ROOT/'note10/private/device-test/v128-legacy-kexec-recovery-proof-20261105/frozen-source'
        rendered=prepare.render(stock,'0123456789abcdef0123456789abcdef',source128)
        reboot=rendered['kernel/reboot.c'].decode();start=reboot.index('void kernel_restart_prepare(char *cmd)');finish=reboot.index('EXPORT_SYMBOL(register_reboot_notifier)',start)
        phase=reboot[start:finish]
        assert phase.index('blocking_notifier_call_chain')<phase.index('freeze_processes()')<phase.index('usermodehelper_disable()')<phase.index('n130_before_device_shutdown()')<phase.index('device_shutdown()')
        hook=re.search(r'    if \(!cmd && n130_before_device_shutdown\(\)\) \{[^}]+\}',phase).group()
        build=ast.parse((HERE/'v130_build.py').read_bytes());image_calls=[n for n in ast.walk(build) if isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id=='run' and n.args and isinstance(n.args[0],ast.List) and any(isinstance(e,ast.Constant) and e.value=='Image' for e in n.args[0].elts)]
        assert len(image_calls)==1 and any(isinstance(e,ast.Constant) and e.value=='-k' for e in image_calls[0].args[0].elts)
        bad=json.loads(json.dumps(candidate));bad['retained_source_commit']='0'*40;reject(lambda:return_order_context(bad,current))
        unapproved=dict(current);unapproved['note10/device_test/v130_gic.inc']='0'*64
        bad=json.loads(json.dumps(candidate));bad['source_sha256']=unapproved;reject(lambda:return_order_context(bad,unapproved))
        bad=json.loads(json.dumps(candidate));bad['delta_NEW_PASS']['source_sha256']['note10/device_test/v130_ufs.inc']='0'*64;reject(lambda:return_order_context(bad,current))
        generated=fixture((HERE/'v130_kernel.c').read_text(),(HERE/'v130_ufs.inc').read_text(),stock['drivers/scsi/ufs/ufshcd.h'].decode(),stock['drivers/scsi/ufs/ufs.h'].decode(),hook)
        source=out/'actual-return-ufs.c';source.write_bytes(generated);exe=out/('fixture.exe' if sys.platform=='win32' else 'fixture')
        command=[str(compiler),*a.compiler_arg,'-std=c11','-O2','-Wall','-Wextra','-Werror',str(source),'-o',str(exe)]
        save(out/'compiler-command.json',dict(argv=command,compiler_sha256=sha(compiler),fixture_sha256=hashlib.sha256(generated).hexdigest()))
        result['compiler_invocations']=1
        with (out/'compile.log').open('wb') as stream:subprocess.run(command,cwd=ROOT,check=True,stdout=stream,stderr=subprocess.STDOUT,timeout=120)
        result['fixture_processes']=1
        with (out/'fixture.log').open('wb') as stream:subprocess.run([str(exe)],cwd=ROOT,check=True,stdout=stream,stderr=subprocess.STDOUT,timeout=30)
        if current!=source_pins():raise ValueError('new return-order source changed')
        result.update(passed=True,source_phase_and_atomic_interleavings_tested=True,UFS_header_visibility_tested=True,single_Image_make_keep_going=True,
            original_PASS_chain_rewritten=False,prior29_fully_retested=False,physical_ready=False)
    except Exception:
        import traceback
        result['error']=traceback.format_exc()
    save(out/'result.json',result)
    if result['passed']:
        candidate['delta_NEW_PASS']['result_sha256']=sha(out/'result.json');return_order_context(candidate,current)
        save(out/'public-return-order-pass.json',candidate)
        (out/'public-return-order-pass.b64').write_bytes(base64.b64encode(json.dumps(candidate,separators=(',',':')).encode())+b'\n')
    return 0 if result['passed'] else 1

if __name__=='__main__':raise SystemExit(main())
