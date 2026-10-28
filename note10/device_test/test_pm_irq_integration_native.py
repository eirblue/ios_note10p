"""Execute the actual prepared CPU/noirq hook and worker with injected faults."""
import argparse, hashlib, json, re, shutil, subprocess, sys
from pathlib import Path
from run_probe import ROOT
from test_fsys_pm_native import function
from test_pm_post_arch_native import WORKER_STUB

STUB = r'''
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>
#include <stdbool.h>
typedef unsigned int u32;
#define READ_ONCE(x) (x)
#define PM_SUSPEND_MEM 3
#define N10_Q_PM_ENTERED 7
struct task_struct {int id;}; static struct task_struct task; static struct task_struct *current=&task;
struct pm_active {unsigned int qgeneration,qphase,pm_called;}; static struct pm_active active,*n10_pm_active=&active;
struct n10_pmu_noirq_sample {unsigned int generation,seen,error,before,state,after;};
static unsigned int mode,online=255,irq,disable_calls,enable_calls,pmu_calls,hook_calls;
static unsigned long online_mask_storage;
#define cpu_online_mask (&online_mask_storage)
#define cpumask_bits(x) (x)
static unsigned int num_online_cpus(void){return online==255?8:online==1?1:7;}
static unsigned int raw_smp_processor_id(void){return mode==4?1:0;}
static int irqs_disabled(void){return irq;}
static int n10_pm_noirq_ready(int state){return state==PM_SUSPEND_MEM && mode!=7;}
static int disable_nonboot_cpus(void){++disable_calls;online=mode==1?0xf1:1;online_mask_storage=online;return mode==1?-EBUSY:0;}
static void enable_nonboot_cpus(void){++enable_calls;online=255;online_mask_storage=online;}
static int n10_pmu_noirq_read(struct n10_pmu_noirq_sample *p,unsigned int g){(void)p;(void)g;return mode==6?-EIO:0;}
static void n10_pmu_cpu_capture(unsigned int g){if(g!=1 || online!=1 || irq)abort();++pmu_calls;}
static int n10_pmu_cpu_read(struct n10_pmu_noirq_sample *p,unsigned int g){(void)p;(void)g;return mode==2?-EIO:0;}
static int n10_pm_irq_capture(unsigned int g){if(g!=1 || online!=1 || irq || !pmu_calls)abort();++hook_calls;return mode==3?-EIO:0;}
'''
MAIN=r'''
int main(int argc,char **argv){int result;mode=atoi(argv[1]);active.qgeneration=1;active.qphase=N10_Q_PM_ENTERED;active.pm_called=1;online_mask_storage=online;
 result=n10_pm_cpus_roundtrip(mode==8?0:1);
 if(mode==0){if(result || hook_calls!=1 || disable_calls!=1 || enable_calls!=1)abort();}
 if(mode==1 || mode==2 || mode==4){if(!result || hook_calls || disable_calls!=1 || enable_calls!=1)abort();}
 if(mode==3){if(!result || hook_calls!=1 || disable_calls!=1 || enable_calls!=1)abort();}
 if(mode==6 || mode==7 || mode==8){if(!result || hook_calls || disable_calls || enable_calls)abort();}
 if(online!=255 || irq)abort();return 0;}
'''

def run(output,source_root):
    out=Path(output).resolve();root=Path(source_root)
    if out.exists() or not out.is_relative_to((ROOT/'note10/private').resolve()):raise ValueError('Fresh private integration directory required')
    paths={'cpu':root/'kernel/power/note10_pm_cpus.c','worker':root/'arch/arm64/mm/note10_pm_timer_roundtrip.c','noirq':root/'kernel/power/note10_pm_noirq.c','irq':root/'kernel/power/note10_pm_irq.c','gic':root/'drivers/irqchip/note10_pm_irq_gic.c'}
    cpu=paths['cpu'].read_text();worker=paths['worker'].read_text();out.mkdir(parents=True)
    clean=lambda s:re.sub(r'^#include[^\n]*\n','',s,flags=re.M)
    contract=clean((Path(__file__).parent/'pm_cpus_contract.h').read_text())
    # Keep the actual prepared caller, and synthetic PMU/hotplug/observer APIs.
    code=STUB+contract+'\nstatic struct n10_pm_cpus_sample n10_pm_cpus_last;\n'+function(cpu,'static unsigned int n10_pm_cpus_bits(')+function(cpu,'int n10_pm_cpus_roundtrip(')+MAIN
    cc=ROOT/'host-tools/windows-build/llvm-mingw/llvm-mingw-20261006-ucrt-x86_64/bin/clang.exe' if sys.platform=='win32' else shutil.which('cc')
    def build(name,source):
        c=out/(name+'.c');exe=out/(name+('.exe' if sys.platform=='win32' else ''));c.write_text(source,encoding='utf-8')
        r=subprocess.run([str(cc),'-std=c11','-O2',str(c),'-o',str(exe)],capture_output=True,timeout=60);(out/(name+'-compile.log')).write_bytes(r.stdout+r.stderr)
        if r.returncode:raise ValueError('Native compile failed: '+name)
        return exe
    enabled=build('enabled','#define CONFIG_NOTE10_PM_IRQ_TEST\n'+code)
    disabled_code=code.replace('if(mode==0){if(result || hook_calls!=1','if(mode==0){if(result || hook_calls!=0').replace('if(mode==3){if(!result || hook_calls!=1 || disable_calls!=1 || enable_calls!=1)abort();}','if(mode==3){if(result || hook_calls || disable_calls!=1 || enable_calls!=1)abort();}')
    disabled=build('disabled',disabled_code)
    noirq=paths['noirq'].read_text();noirq_contract=clean((Path(__file__).parent/'pm_noirq_contract.h').read_text())
    note_stub='\nstatic unsigned int entry_calls; static struct n10_pm_noirq_sample n10_pm_noirq_last; static int n10_pm_noirq_owned(void){return 1;} static void n10_pmu_noirq_capture(unsigned int g){++entry_calls;if(g!=1)abort();}\n'
    note_main=r'''int main(int argc,char**argv){mode=atoi(argv[1]);active.qgeneration=1;active.qphase=N10_Q_PM_ENTERED;active.pm_called=1;online_mask_storage=online;n10_pm_noirq_last.generation=1;n10_pm_noirq_last.seen=1;n10_pm_noirq_note(2,0);n10_pm_noirq_note(3,0);n10_pm_noirq_note(4,0);n10_pm_noirq_note(5,0);n10_pm_noirq_note(6,0);fprintf(stderr,"note bad=%u error=%d hook=%u enable=%u late=%u noirq=%u point=%u entry=%u\n",n10_pm_noirq_last.bad,n10_pm_noirq_last.error,hook_calls,enable_calls,n10_pm_noirq_last.late_ok,n10_pm_noirq_last.noirq_ok,n10_pm_noirq_last.point,entry_calls);if(mode==0 && (n10_pm_noirq_last.error || hook_calls!=1 || enable_calls!=1))abort();if(mode==3 && (n10_pm_noirq_last.error!=-EIO || hook_calls!=1 || enable_calls!=1))abort();return 0;}'''
    noirq_prefix=code[:code.index('int main(')]
    noirq_code=noirq_prefix+noirq_contract+note_stub+function(noirq,'void n10_pm_noirq_note(')+note_main
    ne=build('noirq','#define CONFIG_NOTE10_PM_IRQ_TEST\n#define CONFIG_NOTE10_PM_CPUS_TEST\n'+noirq_code)
    outcomes=[]
    for mode in (0,3):
        r=subprocess.run([str(ne),str(mode)],capture_output=True,timeout=15);(out/f'noirq-{mode}.log').write_bytes(r.stdout+r.stderr)
        if r.returncode:raise ValueError('Prepared noirq-to-CPU failure: '+str(mode))
        outcomes.append({'name':'noirq-'+str(mode),'mode':mode,'passed':True})
    for mode in (0,1,2,3,4,6,7,8):
        for label,exe in [('enabled',enabled),('disabled',disabled)]:
            r=subprocess.run([str(exe),str(mode)],capture_output=True,timeout=15);(out/f'{label}-{mode}.log').write_bytes(r.stdout+r.stderr)
            if r.returncode:raise ValueError('Prepared CPU caller failure: '+label+' '+str(mode))
        outcomes.append({'name':'caller-'+str(mode),'mode':mode,'passed':True})
    wstub=re.sub(r'static (?:void|int) n10_test_gic\(void\)\{[^}]*\}', 'static int n10_test_gic(void){++gic_calls;return mode==8?-5:0;}', WORKER_STUB)
    wstub+='\n#define EIO 5\nstatic int num_online_cpus(void){return 8;} static int irqs_disabled(void){return 0;} static void n10_report_pm_irq_failure(unsigned int g){(void)g;} static int edge_calls,irq_calls; static int n10_report_pm_edge(unsigned int g){(void)g;++edge_calls;return mode==10?-EIO:0;} static int n10_report_pm_irq(unsigned int g){(void)g;++irq_calls;return mode==9?-EIO:0;}\n'
    wmain=r'''int main(int argc,char**argv){mode=atoi(argv[1]);n10_pm_worker(NULL);if(mode==8 && (observer_calls || edge_calls || irq_calls))abort();return 0;}'''
    wstub='#define CONFIG_NOTE10_PM_EDGE_INVENTORY\n#define CONFIG_NOTE10_PM_IRQ_TEST\n'+wstub
    we=build('worker',wstub+function(worker,'static void n10_pm_worker(struct work_struct *unused)\n{')+wmain)
    for mode in (0,1,2,3,4,5,6,7,8,9,10):
        r=subprocess.run([str(we),str(mode)],capture_output=True,timeout=15);(out/f'worker-{mode}.log').write_bytes(r.stdout+r.stderr)
        expected=0 if mode==0 else 7 if mode in (4,5,6,8,9,10) else 6 if mode==3 else 5 if mode==2 else 4 if mode==1 else 3
        if r.returncode or not re.search(rb'N10PMT1 .* status='+str(expected).encode()+rb' checksum=',r.stdout):raise ValueError('Prepared worker failure: '+str(mode))
        outcomes.append({'name':'worker-'+str(mode),'mode':mode,'passed':True})
    result={'passed':True,'cases':len(outcomes),'outcomes':outcomes,'actual_prepared_cpu_caller_executed':True,'actual_prepared_noirq_hook_executed':True,'actual_prepared_worker_executed':True,'gic_failure_blocks_later_observers':True,'mandatory_cpu_restore_on_failures':True,'observer_and_hotplug_stubbed':True,'hardware_verified':False,'source_sha256':{k:hashlib.sha256(p.read_bytes()).hexdigest() for k,p in paths.items()},'harness_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    (out/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');return result

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--source-root',type=Path,required=True);a=p.parse_args();print(json.dumps(run(a.output,a.source_root)))
