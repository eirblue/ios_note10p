"""Execute prepared PM-edge hooks, composed suspend flow, and worker gate."""
import argparse, hashlib, json, re, shutil, subprocess, sys
from pathlib import Path
from run_probe import ROOT
from prepare_pm_noirq import HERE, FINAL_SHA
from test_fsys_pm_native import function
from test_pm_noirq_native import STUB, PMU_STUB, MAIN
from test_pm_post_arch_native import WORKER_STUB

CLEAN = lambda s: re.sub(r'^#include[^\n]*\n', '', s, flags=re.M)
EXTRA = r'''
struct list_head { int dummy; }; static struct list_head dpm_list,dpm_prepared_list,dpm_suspended_list,dpm_late_early_list,dpm_noirq_list;
static unsigned int dpm_list_mtx, list_locked, edge_seen[4], edge_gen, edge_bad, online=255, hotplug;
struct device { void *dma_mask; unsigned long coherent_dma_mask; struct { int is_suspended,direct_complete,syscore,is_prepared,runtime_status; } power; };
#define ARRAY_SIZE(x) (sizeof(x)/sizeof((x)[0]))
#define list_for_each(entry,head) for ((entry)=NULL; (entry)!=NULL; )
#define to_device(entry) ((struct device *)(entry))
#define RPM_ACTIVE 0
#define RPM_SUSPENDED 1
static const char *dev_name(struct device *d){(void)d;return "device";}
static void n10_edge_dma_capture(unsigned int p,unsigned int g){
 if(list_locked || irq || online!=255 || hotplug || p>3 || !g) abort();
 if(p==0 && edge_gen!=g){memset(edge_seen,0,sizeof(edge_seen));edge_bad=0;edge_gen=g;}
 if(g!=edge_gen || edge_seen[p]++ || (p && edge_seen[p-1]!=1))edge_bad=1;
}
static void n10_edge_iommu_capture(unsigned int p,unsigned int g){if(list_locked || irq || online!=255 || hotplug || g!=edge_gen || edge_seen[p]!=1)abort();}
static void n10_edge_syscore_capture(unsigned int p,unsigned int g){if(list_locked || irq || online!=255 || hotplug || (p!=0 && p!=3) || g!=edge_gen)abort();}
static void n10_edge_capture(unsigned int p,unsigned int g);
'''
MUTEX = r'''
static void mutex_lock(unsigned int*p){if(p==&dpm_list_mtx){if(list_locked || irq)abort();list_locked=1;}else{if(pm_mutex || irq)abort();pm_mutex=1;}}
static void mutex_unlock(unsigned int*p){if(p==&dpm_list_mtx){if(!list_locked)abort();list_locked=0;}else{if(!pm_mutex)abort();pm_mutex=0;}}
'''

PRODUCER_STUB = r'''
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>
#include <stdint.h>
typedef unsigned int u32;
#define N10_RESERVE_BUILD_ID "0123456789abcdef0123456789abcdef"
#define pr_info printf
static unsigned int mode;
'''
PRODUCER_READERS = r'''
int n10_edge_dma_read(struct n10_edge_dma_sample *a,unsigned int g){unsigned int i;for(i=0;i<4;i++){a[i].generation=g-1;a[i].seen=1;a[i].phase=i;a[i].total=1;a[i].dma=1;a[i].names_xor=7;a[i].names_sum=7;a[i].uncovered=1;a[i].active=1;}if(mode==8){a[0].active=0;a[0].runtime_suspended=1;}return mode==1?-EIO:0;}
int n10_edge_iommu_read(struct n10_edge_iommu_sample *a,unsigned int g){unsigned int i;for(i=0;i<4;i++){a[i].generation=g-1;a[i].seen=1;a[i].phase=i;a[i].total=1;a[i].names_xor=9;a[i].names_sum=9;}if(mode==8)a[0].active=1;return mode==2?-EIO:0;}
int n10_edge_syscore_read(struct n10_edge_syscore_sample *a,unsigned int g){unsigned int i,j,k;for(i=0;i<2;i++){a[i].generation=g-1;a[i].seen=1;a[i].phase=i*3;a[i].count=mode==7?64:1;for(j=0;j<a[i].count;j++){a[i].entries[j].mask=7;for(k=0;k<3;k++){memset(a[i].entries[j].names[k],mode==7?'a':'b',mode==7?63:1);a[i].entries[j].names[k][mode==7?63:1]=0;}}}return mode==3?-EIO:0;}
int n10_dma_pm_read(struct n10_dma_pm_sample *a,unsigned int g){unsigned int i;for(i=0;i<3;i++){a[i].generation=g-1;a[i].total=1;a[i].dma=1;a[i].names_xor=7;a[i].names_sum=7;}if(mode==6)a[0].total++;return mode==4?-EIO:0;}
int n10_iommu_pm_read(struct n10_iommu_pm_sample *a,unsigned int g){unsigned int i;for(i=0;i<3;i++){a[i].generation=g-1;a[i].total=1;a[i].names_xor=9;a[i].names_sum=9;}return mode==5?-EIO:0;}
'''
PRODUCER_MAIN = r'''
int main(int argc,char **argv){int ret;mode=atoi(argv[1]);ret=n10_report_pm_edge(2);if((mode==0 || mode==8)?ret!=0:ret!=-EIO)abort();return 0;}
'''

def run(output, source_root, raw_suspend, header):
    out=Path(output).resolve(); root=Path(source_root)
    if out.exists() or not out.is_relative_to((ROOT/'note10/private').resolve()): raise ValueError('Fresh private integration output required')
    paths={'suspend':root/'kernel/power/suspend.c','dma':root/'drivers/base/power/note10_dma_pm.c','noirq':root/'kernel/power/note10_pm_noirq.c','edge':root/'drivers/base/power/note10_pm_edge_dma.c','worker':root/'arch/arm64/mm/note10_pm_timer_roundtrip.c'}
    paths.update({'kconfig':root/'kernel/power/Kconfig','pm_main':root/'drivers/base/power/main.c','iommu_driver':root/'drivers/iommu/exynos-iommu.c','syscore':root/'drivers/base/syscore.c'})
    raw={k:p.read_text(encoding='utf-8') for k,p in paths.items()}
    if hashlib.sha256(paths['suspend'].read_bytes()).hexdigest()!=FINAL_SHA: raise ValueError('Guarded suspend differs')
    from prepare_pm_diagnostic import SUSPEND_SHA
    if hashlib.sha256(Path(raw_suspend).read_bytes()).hexdigest()!=SUSPEND_SHA: raise ValueError('Pinned original suspend differs')
    out.mkdir(parents=True)
    stub=STUB
    for name in ('static void mutex_lock(', 'static void mutex_unlock(', 'static void n10_dma_pm_capture('): stub=stub.replace(function(stub,name),'')
    prefix=stub[:stub.index('static void s2idle_begin')]
    hdr=Path(header).read_text(); start=hdr.index('struct platform_suspend_ops {'); ops=hdr[start:hdr.index('};',start)+2]
    prefix+=ops+'\nstatic struct platform_suspend_ops ops;\nstatic const struct platform_suspend_ops*suspend_ops;\n'
    prefix+=(HERE/'pm_test_contract.h').read_text()+(HERE/'pm_quiesce_core.h').read_text()
    prefix+='\nstatic struct n10_pm_result*n10_pm_active;\nstatic struct task_struct*n10_pm_owner;\n'+EXTRA+MUTEX
    prefix+=CLEAN((HERE/'dma_pm_contract.h').read_text())+'\nvoid n10_dma_pm_capture(unsigned int,unsigned int);\n'+stub[stub.index('static void s2idle_begin'):]
    decl=''.join(CLEAN((HERE/n).read_text()) for n in ('abox_pmu_contract.h','pm_noirq_contract.h'))
    prefix=prefix.replace('static int dpm_suspend_start',decl+'\nstatic int dpm_suspend_start')
    original=Path(raw_suspend).read_text()
    wrappers=''.join(function(original,s) for s in ['static bool sleep_state_supported(', 'static int platform_suspend_prepare(', 'static int platform_suspend_prepare_late(', 'static int platform_suspend_prepare_noirq(', 'static void platform_resume_noirq(', 'static void platform_resume_early(', 'static void platform_resume_finish(', 'static int platform_suspend_begin(', 'static void platform_resume_end(', 'static void platform_recover(', 'static bool platform_suspend_again('])
    selector=raw['suspend'][raw['suspend'].index('#ifdef CONFIG_NOTE10_PM_NOIRQ_TEST\n\t\tpm_test_level = TEST_PLATFORM;'):]; selector=selector[:selector.index('#endif')+6]
    prefix+=wrappers+'static void select_level(void){\n'+selector+'\n}\n'
    edge=function(raw['edge'],'void n10_edge_capture(').replace('void n10_edge_capture(', 'static void n10_edge_capture(')
    bodies=function(raw['suspend'],'static int suspend_enter(')+function(raw['suspend'],'int suspend_devices_and_enter(')
    main=MAIN.replace('n10_report_pm_noirq(mode==26?completed+1:completed);','')
    main=main.replace('return 0;\n}', '''
#ifdef CONFIG_NOTE10_PM_EDGE_INVENTORY
 if(mode==0 || mode==19){if(edge_bad || edge_seen[0]!=1 || edge_seen[1]!=1 || edge_seen[2]!=1 || edge_seen[3]!=1)abort();}
 if(mode==1 && (edge_seen[0]!=1 || edge_seen[1] || edge_seen[2] || edge_seen[3]!=1))abort();
 if(mode==2 && (edge_seen[0]!=1 || edge_seen[1]!=1 || edge_seen[2] || edge_seen[3]!=1))abort();
#else
 if(edge_seen[0] || edge_seen[1] || edge_seen[2] || edge_seen[3])abort();
#endif
 return 0;\n}''')
    # CPU roundtrip callback traps inventory even while simulating CPU0-only context.
    cpu='int n10_pm_cpus_roundtrip(unsigned int g){(void)g;hotplug=1;online=1;online=255;hotplug=0;return 0;}\n'
    compiler=ROOT/'host-tools/windows-build/llvm-mingw/llvm-mingw-20261006-ucrt-x86_64/bin/clang.exe' if sys.platform=='win32' else shutil.which('cc')
    def build(name,code):
        p=out/(name+'.c'); p.write_text(code,encoding='utf-8'); exe=out/(name+('.exe' if sys.platform=='win32' else ''))
        r=subprocess.run([str(compiler),'-std=c11','-O2',str(p),'-o',str(exe)],capture_output=True,timeout=60);(out/(name+'-compile.log')).write_bytes(r.stdout+r.stderr)
        if r.returncode: raise ValueError('Integration compilation failed: '+name)
        return exe
    # Existing noirq backend calls CPU callback through its declaration.
    prefix=prefix.replace('static int dpm_suspend_start','int n10_pm_cpus_roundtrip(unsigned int);\nstatic int dpm_suspend_start')
    code=prefix+edge+CLEAN(raw['dma'])+PMU_STUB+cpu+CLEAN(raw['noirq'])+bodies+main
    enabled=build('enabled','#define CONFIG_NOTE10_PM_NOIRQ_TEST\n#define CONFIG_NOTE10_PM_CPUS_TEST\n#define CONFIG_NOTE10_PM_EDGE_INVENTORY\n'+code)
    disabled=build('disabled','#define CONFIG_NOTE10_PM_NOIRQ_TEST\n#define CONFIG_NOTE10_PM_CPUS_TEST\n'+code)
    rows=[]
    for mode in (0,1,2,19):
        outputs=[]
        for name,exe in [('enabled',enabled),('disabled',disabled)]:
            r=subprocess.run([str(exe),str(mode)],capture_output=True,timeout=15);(out/f'{name}-{mode}.log').write_bytes(r.stdout+r.stderr)
            if r.returncode: raise ValueError('Prepared hook flow failed: '+name+' '+str(mode))
            outputs.append(r.stdout)
        if outputs[0]!=outputs[1]: raise ValueError('Disabled edge profile changed suspend behavior: '+str(mode))
        rows.append({'name':'suspend-flow-'+str(mode),'mode':mode,'passed':True})
    # Compile actual worker and verify the emitted status, including a failed edge report.
    wstub=WORKER_STUB+'\nstatic int edge_calls; static int n10_report_pm_edge(unsigned int g){if(g!=2)abort();++edge_calls;return mode==8?-5:0;}\n'
    wmain='''int main(int argc,char**argv){mode=atoi(argv[1]);n10_pm_worker(NULL);if(edge_calls!=(mode==0 || mode==8))abort();return 0;}'''
    worker=build('worker','#define CONFIG_NOTE10_PM_EDGE_INVENTORY\n'+wstub+function(raw['worker'],'static void n10_pm_worker(struct work_struct *unused)\n{')+wmain)
    for mode in range(9):
        r=subprocess.run([str(worker),str(mode)],capture_output=True,timeout=15);(out/f'worker-{mode}.log').write_bytes(r.stdout+r.stderr)
        expected=0 if mode==0 else 7 if mode in (4,5,6,8) else 6 if mode==3 else 5 if mode==2 else 4 if mode==1 else 3
        if r.returncode or not re.search(rb'N10PMT1 .* status='+str(expected).encode()+rb' checksum=',r.stdout): raise ValueError('Worker edge gate failed: '+str(mode))
        rows.append({'name':'worker-'+str(mode),'mode':mode,'passed':True})
    contracts=''.join(CLEAN((HERE/n).read_text()) for n in ('dma_pm_contract.h','iommu_pm_contract.h','pm_edge_dma_contract.h','pm_edge_iommu_contract.h','pm_edge_syscore_contract.h'))
    checksum=re.search(r'static u32 n10_frame_checksum[^}]+}',(HERE/'xnu_reserve.c').read_text()).group()
    producer_path=root/'arch/arm64/mm/note10_pm_edge_probe.c'
    producer=build('producer',PRODUCER_STUB+contracts+PRODUCER_READERS+checksum+CLEAN(producer_path.read_text())+PRODUCER_MAIN)
    for mode in range(9):
        r=subprocess.run([str(producer),str(mode)],capture_output=True,timeout=15);(out/f'producer-{mode}.log').write_bytes(r.stdout+r.stderr)
        if r.returncode: raise ValueError('Producer execution failed '+str(mode))
        data=r.stdout.decode()
        if mode in (0,8):
            if data.count('N10EOK1 ')!=2 or 'status=1' in data or data.count('N10EDG1 ')!=8: raise ValueError('Producer success records differ '+str(mode))
        else:
            bit=1 << (mode-1) if mode<=7 else 0
            if data.count('N10EER1 ')!=8 or data.count('status=1')!=2 or 'N10EDG1 ' in data or ('failures=%x'%bit) not in data: raise ValueError('Producer failure records differ '+str(mode))
        rows.append({'name':'producer-'+str(mode),'mode':mode,'passed':True})
    paths['producer']=producer_path
    result={'passed':True,'cases':len(rows),'outcomes':rows,'actual_prepared_dma_hook_executed':True,'actual_prepared_noirq_hook_executed':True,'actual_suspend_caller_and_enter_executed':True,'actual_prepared_worker_executed':True,'producer_log_sha256':{'producer-'+str(n)+'.log':hashlib.sha256((out/('producer-'+str(n)+'.log')).read_bytes()).hexdigest() for n in range(9)},'actual_prepared_producer_executed':True,'producer_reader_fixtures_stubbed':True,'edge_backend_collectors_stubbed':True,'prepared_source_may_be_synthetic_fixture':True,'disabled_profile_matches_enabled_flow':True,'hardware_verified':False,'source_sha256':{k:hashlib.sha256(p.read_bytes()).hexdigest() for k,p in paths.items()},'harness_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    (out/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');return result

if __name__=='__main__':
    p=argparse.ArgumentParser()
    for n in ('output','source-root','raw-suspend','header'): p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args(); print(json.dumps(run(a.output,a.source_root,a.raw_suspend,a.header)))
