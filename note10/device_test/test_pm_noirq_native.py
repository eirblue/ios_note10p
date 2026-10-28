"""Run complete composed PM caller/enter bodies with forbidden-entry traps."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
from prepare_pm_noirq import HERE,SOURCES,BASE_SHA,FINAL_SHA,CALL_EXTEND
from test_fsys_pm_native import function
from decode_pm_noirq import decode
from run_probe import ROOT
IDENTITY='0123456789abcdef0123456789abcdef'
ACCEPTED=(0,19,23,28,30,36,42)
STUB=r'''
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdbool.h>
#include <stdint.h>
#include <errno.h>
typedef unsigned int u32;
typedef int suspend_state_t;
#define PM_SUSPEND_ON 0
#define PM_SUSPEND_TO_IDLE 1
#define PM_SUSPEND_MEM 3
#define TEST_NONE 0
#define TEST_CORE 1
#define TEST_CPUS 2
#define TEST_PLATFORM 3
#define TEST_DEVICES 4
#define PMSG_SUSPEND 1
#define PMSG_RESUME 2
#define MAX_SUSPEND_ABORT_LEN 64
#define REC_FAILED_NUM 2
#define CONFIG_NOTE10_DMA_PM_AUDIT
#define N10_RESERVE_BUILD_ID "0123456789abcdef0123456789abcdef"
#define READ_ONCE(x) (x)
#define pr_info printf
#define scnprintf snprintf
#define pr_err(...) ((void)0)
#define trace_suspend_resume(...) ((void)0)
#define dbg_snapshot_suspend(...) ((void)0)
#define log_suspend_abort_reason(...) ((void)0)
#define suspend_test_start() ((void)0)
#define suspend_test_finish(...) ((void)0)
#define BUG_ON(x) do{if(x)abort();}while(0)
struct task_struct {int id;};
static struct task_struct task,foreign;
#define current (&task)
static unsigned int mode,irq,pm_mutex,late_suspended,device_irq_off;
static unsigned int late_calls,noirq_calls,early_calls,resume_noirq_calls,resume_end_calls,regular_calls;
static unsigned int cpu_calls,syscore_calls,enter_calls,again_calls,platform_calls,dma_calls[3],captures;
static int pm_test_level,pm_suspend_target_state,events_check_enabled;
static struct {int failed_resume_early,failed_resume_noirq,last_failed_dev;char failed_devs[2][32];} suspend_stats;
static int irqs_disabled(void){return irq;}
static void mutex_lock(unsigned int*p){if(pm_mutex || irq)abort();pm_mutex=1;}
static void mutex_unlock(unsigned int*p){if(!pm_mutex)abort();pm_mutex=0;}
static int forbidden_enter(suspend_state_t state){++enter_calls;abort();}
static int forbidden_prepare(void){++platform_calls;abort();}
static void forbidden_restore(void){++platform_calls;abort();}
static int failing_begin(suspend_state_t state){return -5;}
static bool again_true(void){++again_calls;return true;}
struct platform_s2idle_ops {int(*begin)(void);int(*prepare)(void);void(*restore)(void);void(*end)(void);};
static struct platform_s2idle_ops *s2idle_ops;
static int disable_nonboot_cpus(void){++cpu_calls;abort();}
static void enable_nonboot_cpus(void){++cpu_calls;abort();}
static void arch_suspend_disable_irqs(void){++cpu_calls;abort();}
static void arch_suspend_enable_irqs(void){++cpu_calls;abort();}
static int syscore_suspend(void){++syscore_calls;abort();}
static void syscore_resume(void){++syscore_calls;abort();}
static int pm_wakeup_pending(void){return 0;}
static void pm_get_active_wakeup_sources(char*p,int n){}
static void s2idle_begin(void){if(n10_pm_active)abort();}
static void s2idle_loop(void){abort();}
static void suspend_console(void){}
static void resume_console(void){}
static int suspend_test(int level){return level==pm_test_level && !(mode==6 && level==TEST_PLATFORM);}
static void n10_dma_pm_capture(unsigned int phase,unsigned int generation){if(phase>=3 || !pm_mutex)abort();++dma_calls[phase];}
static int dpm_suspend_start(int msg){if(msg!=PMSG_SUSPEND || !pm_mutex)abort();++regular_calls;return mode==18?-EBUSY:0;}
static int dpm_suspend_late(int msg){
 if(msg!=PMSG_SUSPEND || !pm_mutex || device_irq_off || late_suspended)abort();++late_calls;
#ifdef CONFIG_NOTE10_PM_NOIRQ_TEST
 if(mode==22)n10_pm_noirq_note(2,0);
#endif
 if(mode==43){++suspend_stats.failed_resume_early;return -EBUSY;}if(mode==1)return -EBUSY;late_suspended=1;return 0;
}
static int dpm_suspend_noirq(int msg){
 if(msg!=PMSG_SUSPEND || !pm_mutex || !late_suspended || device_irq_off)abort();++noirq_calls;
 if(mode==44){++suspend_stats.failed_resume_noirq;return -EBUSY;}if(mode==2)return -EBUSY;device_irq_off=1;
#ifdef CONFIG_NOTE10_PM_NOIRQ_TEST
 if(mode==21)n10_pm_noirq_note(99,0);
#endif
 return 0;
}
static void dpm_resume_noirq(int msg){if(msg!=PMSG_RESUME || !pm_mutex || !device_irq_off)abort();++resume_noirq_calls;device_irq_off=0;if(mode==4)++suspend_stats.failed_resume_noirq;}
static void dpm_resume_early(int msg){if(msg!=PMSG_RESUME || !pm_mutex || !late_suspended || device_irq_off)abort();++early_calls;late_suspended=0;if(mode==5)++suspend_stats.failed_resume_early;if(mode==25)suspend_stats.failed_resume_early=-1;}
static void dpm_resume_end(int msg){if(msg!=PMSG_RESUME || !pm_mutex || device_irq_off || late_suspended)abort();++resume_end_calls;}
'''
PMU_STUB=r'''
static struct n10_pmu_noirq_sample pmu_sample;
void n10_pmu_noirq_capture(unsigned int generation){
 if(!pm_mutex || irq || !late_suspended || !device_irq_off || !generation || captures++)abort();
 pmu_sample=(struct n10_pmu_noirq_sample){generation,1,mode==3?5:0,mode==42?0:0x4000,mode==42?0:0x4000,mode==42?0:0x4000};
 if(mode==27)pmu_sample.seen=2;
}
int n10_pmu_noirq_read(struct n10_pmu_noirq_sample*out,unsigned int completed){
 unsigned int next=pmu_sample.generation+1;if(!next)next=1;
 if(!pm_mutex)abort();*out=pmu_sample;
 return !out->generation || next!=completed || out->error || out->seen!=1?-EIO:0;
}
'''
MAIN=r'''
int main(int argc,char**argv){
 struct n10_pm_result out={0};unsigned int completed,saved_irq;int ret;
 mode=atoi(argv[1]);irq=saved_irq=mode==34;
 out.pm_called=1;out.qphase=N10_Q_PM_ENTERED;out.qgeneration=mode==19?0xffffffffU:1;
 n10_pm_active=&out;n10_pm_owner=current;ops.enter=forbidden_enter;suspend_ops=&ops;
 if(mode==7)ops.prepare=forbidden_prepare;
 if(mode==8)ops.prepare_late=forbidden_prepare;
 if(mode==9)ops.wake=forbidden_restore;
 if(mode==10)ops.finish=forbidden_restore;
 if(mode==11)suspend_ops=NULL;
 if(mode==12)n10_pm_owner=&foreign;
 if(mode==13)out.qphase=5;
 if(mode==14)out.qgeneration=0;
 if(mode==15)out.pm_called=0;
 if(mode==17)n10_pm_active=NULL;
 if(mode==23){suspend_stats.failed_resume_early=7;suspend_stats.failed_resume_noirq=9;}
 if(mode==24)suspend_stats.failed_resume_early=-1;
 if(mode==29)ops.begin=failing_begin;
 if(mode==30)ops.suspend_again=again_true;
 if(mode==35)ops.enter=NULL;
 select_level();if(mode==17)pm_test_level=TEST_DEVICES;
 if(mode==31)pm_test_level=TEST_CPUS;
 pm_mutex=1;
#ifdef CONFIG_NOTE10_PM_NOIRQ_TEST
 if(mode==20){n10_pm_noirq_last.seen=1;n10_pm_noirq_last.generation=out.qgeneration;}
 if(mode==32){bool wakeup=false;ret=suspend_enter(PM_SUSPEND_MEM,&wakeup);}
 else if(mode==33){bool wakeup=false;n10_pm_noirq_begin(PM_SUSPEND_MEM);pm_test_level=TEST_NONE;ret=suspend_enter(PM_SUSPEND_MEM,&wakeup);n10_pm_noirq_finish(ret);}
 else
#endif
 ret=suspend_devices_and_enter(mode==16?PM_SUSPEND_TO_IDLE:PM_SUSPEND_MEM);
#ifdef CONFIG_NOTE10_PM_NOIRQ_TEST
 if((mode==4 || mode==5 || mode==25 || mode==43 || mode==44) && ret!=-EIO)abort();
#endif
 if(irq!=saved_irq || late_suspended || device_irq_off || cpu_calls || syscore_calls || enter_calls || platform_calls || again_calls)abort();
 printf("SEM ret=%d devices=%u resumed=%u blocked=%u regular=%u late=%u noirq=%u rearly=%u rnoirq=%u rend=%u dma=%u%u%u target=%d irq=%u\n",ret,out.devices,out.resumed,out.blocked,regular_calls,late_calls,noirq_calls,early_calls,resume_noirq_calls,resume_end_calls,dma_calls[0],dma_calls[1],dma_calls[2],pm_suspend_target_state,irq);
#ifdef CONFIG_NOTE10_PM_NOIRQ_TEST
 if(mode==37)n10_pm_noirq_last.point=0;
 if(mode==38)n10_pm_noirq_note(6,0);
 if(mode==39)n10_pm_noirq_finish(0);
 if(mode==40)pmu_sample.generation+=2;
 if(mode==41)++n10_pm_noirq_last.post_early;
#endif
 pm_mutex=0;completed=out.qgeneration+1;if(!completed)completed=1;
#ifdef CONFIG_NOTE10_PM_NOIRQ_TEST
 if(mode==28 && n10_pm_noirq_read(NULL,&pmu_sample,completed)!=-EINVAL)abort();
 if(mode==36 && n10_pm_noirq_read(&n10_pm_noirq_last,&pmu_sample,0)!=-EINVAL)abort();
 n10_pm_active=NULL;n10_pm_owner=NULL;
 n10_report_pm_noirq(mode==26?completed+1:completed);
 if(irq!=saved_irq || pm_mutex || cpu_calls || syscore_calls || enter_calls)abort();
#endif
 return 0;
}
'''

def run(output,suspend_source,raw_suspend,header,core_driver,pmu_source,domain_source):
    output=Path(output).resolve();source=Path(suspend_source).read_bytes();raw=Path(raw_suspend).read_bytes();header=Path(header).read_text()
    if output.exists() or not output.is_relative_to((ROOT/'note10/private').resolve()):raise ValueError('Fresh private noirq output required')
    if hashlib.sha256(source).hexdigest()!=FINAL_SHA or source.count(CALL_EXTEND)!=1:raise ValueError('Actual final noirq source differs')
    from prepare_pm_diagnostic import SUSPEND_SHA
    if hashlib.sha256(raw).hexdigest()!=SUSPEND_SHA:raise ValueError('Pinned original PM core differs')
    source=source.decode();raw=raw.decode();output.mkdir(parents=True)
    clean=lambda s:re.sub(r'^#include[^\n]*\n','',s,flags=re.M)
    contract=(HERE/'pm_test_contract.h').read_text()+(HERE/'pm_quiesce_core.h').read_text()
    prefix=STUB[:STUB.index('static void s2idle_begin')]
    start=header.index('struct platform_suspend_ops {');ops=header[start:header.index('};',start)+2]
    prefix+=ops+'\nstatic struct platform_suspend_ops ops;\nstatic const struct platform_suspend_ops*suspend_ops;\n'
    prefix+=contract+'\nstatic struct n10_pm_result*n10_pm_active;\nstatic struct task_struct*n10_pm_owner;\n'+STUB[STUB.index('static void s2idle_begin'):]
    wrappers=''.join(function(raw,s) for s in ['static bool sleep_state_supported(', 'static int platform_suspend_prepare(', 'static int platform_suspend_prepare_late(', 'static int platform_suspend_prepare_noirq(', 'static void platform_resume_noirq(', 'static void platform_resume_early(', 'static void platform_resume_finish(', 'static int platform_suspend_begin(', 'static void platform_resume_end(', 'static void platform_recover(', 'static bool platform_suspend_again('])
    selector=source[source.index('#ifdef CONFIG_NOTE10_PM_NOIRQ_TEST\n\t\tpm_test_level = TEST_PLATFORM;'):];selector=selector[:selector.index('#endif')+len('#endif')]
    prefix+=wrappers+'static void select_level(void){\n'+selector+'\n}\n'
    declarations=clean((HERE/'abox_pmu_contract.h').read_text())+clean((HERE/'pm_noirq_contract.h').read_text())
    # The callback stubs reference the real header declarations before the helper.
    prefix=prefix.replace('static int dpm_suspend_start',declarations+'\nstatic int dpm_suspend_start')
    checksum=re.search(r'static u32 n10_frame_checksum[^}]+}',(HERE/'xnu_reserve.c').read_text()).group()
    bodies=function(source,'static int suspend_enter(')+function(source,'int suspend_devices_and_enter(')
    base=Path(suspend_source).with_name('suspend-base.c').read_bytes()
    if hashlib.sha256(base).hexdigest()!=BASE_SHA:raise ValueError('Noirq base composition differs')
    base=base.decode();baseline_bodies=function(base,'static int suspend_enter(')+function(base,'int suspend_devices_and_enter(')
    compiler=ROOT/'host-tools/windows-build/llvm-mingw/llvm-mingw-20261006-ucrt-x86_64/bin/clang.exe' if sys.platform=='win32' else shutil.which('cc')
    def build(name,code):
        p=output/(name+'.c');p.write_bytes(code.encode());exe=output/(name+('.exe' if sys.platform=='win32' else ''))
        made=subprocess.run([str(compiler),'-std=c11','-O2',str(p),'-o',str(exe)],capture_output=True,timeout=60)
        (output/(name+'-compile.log')).write_bytes(made.stdout+made.stderr)
        if made.returncode:raise ValueError('Noirq complete PM model compilation failed: '+name)
        return exe
    enabled=build('enabled','#define CONFIG_NOTE10_PM_NOIRQ_TEST\n'+prefix+PMU_STUB+clean((HERE/'pm_noirq_backend.c').read_text())+checksum+clean((HERE/'pm_noirq_probe.c').read_text())+bodies+MAIN)
    disabled=build('disabled',prefix+bodies+MAIN)
    baseline=build('baseline',prefix+baseline_bodies+MAIN)
    rows=[]
    for mode in range(45):
        outputs=[]
        for name,exe in [('enabled',enabled),('disabled',disabled),('baseline',baseline)]:
            ran=subprocess.run([str(exe),str(mode)],capture_output=True,timeout=15)
            (output/f'{name}-{mode}.log').write_bytes(ran.stdout+ran.stderr)
            if ran.returncode:raise ValueError('Forbidden entry, unwind or IRQ invariant failed '+name+' mode '+str(mode))
            outputs.append(ran.stdout.decode())
        if outputs[1]!=outputs[2]:raise ValueError('Disabled noirq composition changed original callback behavior mode '+str(mode))
        try:observation=decode(outputs[0],IDENTITY,1 if mode==19 else 2);accepted=True
        except ValueError:accepted=False
        if accepted!=(mode in ACCEPTED):raise ValueError('Noirq strict evidence differs mode '+str(mode))
        rows.append(dict(mode=mode,passed=True,accepted=accepted))
    from test_pm_noirq_pmu_native import run as run_pmu
    pmu=run_pmu(output.parent/'pm-noirq-pmu-model',core_driver,pmu_source,domain_source)
    result=dict(pmu_noirq_model=pmu,passed=True,flow_cases=45,flow_outcomes=rows,source_sha256={n:hashlib.sha256((HERE/n).read_bytes()).hexdigest() for n in SOURCES},
        final_suspend_sha256=FINAL_SHA,base_suspend_sha256=BASE_SHA,harness_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        actual_suspend_enter_executed=True,actual_suspend_devices_caller_executed=True,legacy_disabled_path_matches_base=True,
        no_cpu_syscore_or_platform_entry=True,platform_callback_mask_refused=True,resume_error_deltas_checked=True,resume_failure_nonretryable=True,
        generation_wrap_executed=True,hardware_verified=False)
    (output/'result.json').write_bytes((json.dumps(result,indent=2)+'\n').encode());return result

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--suspend-source',type=Path,required=True);p.add_argument('--raw-suspend',type=Path,required=True);p.add_argument('--header',type=Path,required=True);p.add_argument('--core-driver',type=Path,required=True);p.add_argument('--pmu-source',type=Path,required=True);p.add_argument('--domain-source',type=Path,required=True)
    a=p.parse_args();r=run(a.output,a.suspend_source,a.raw_suspend,a.header,a.core_driver,a.pmu_source,a.domain_source);print(json.dumps(dict(passed=r['passed'],cases=r['flow_cases'],pmu_cases=r['pmu_noirq_model']['cases'])))
