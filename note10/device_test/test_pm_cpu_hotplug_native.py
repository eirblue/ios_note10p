"""Execute pinned original CPU hotplug functions with per-CPU failures."""
import hashlib,json,subprocess,sys,shutil
from pathlib import Path
from prepare_pm_cpus import HERE,PINS
from run_probe import ROOT
from test_fsys_pm_native import function
STUB=r'''
#include <stdio.h>
#include <stdlib.h>
#include <errno.h>
#define CONFIG_PM_SLEEP_SMP
#define pr_info(...) ((void)0)
#define pr_err(...) ((void)0)
#define pr_warn(...) ((void)0)
#define trace_suspend_resume(...) ((void)0)
#define dbg_snapshot_suspend(...) ((void)0)
#define CPUHP_OFFLINE 0
#define CPUHP_ONLINE 1
#define KOBJ_ONLINE 1
#define BUG_ON(x) do{if(x){puts("BUG");exit(73);}}while(0)
struct cpumask {unsigned int bits;};
struct device {unsigned int kobj;};
static struct cpumask online,storage;
#define cpu_online_mask (&online)
#define frozen_cpus (&storage)
static struct device devices[8];
static unsigned int mode,locked,downs,ups,wakes,begin_hooks,end_hooks,uevents;
static int cpu_hotplug_disabled;
static int cpu_online(int cpu){return cpu>=0 && cpu<8 && (online.bits&(1U<<cpu));}
static int cpumask_first(const struct cpumask*m){int i;for(i=0;i<8;++i)if(m->bits&(1U<<i))return i;return 8;}
static void cpumask_clear(struct cpumask*m){m->bits=0;}
static void cpumask_set_cpu(int cpu,struct cpumask*m){m->bits|=1U<<cpu;}
static int cpumask_empty(struct cpumask*m){return !m->bits;}
#define for_each_online_cpu(cpu) for((cpu)=0;(cpu)<8;++(cpu))if(cpu_online(cpu))
#define for_each_cpu(cpu,m) for((cpu)=0;(cpu)<8;++(cpu))if((m)->bits&(1U<<(cpu)))
static unsigned int num_online_cpus(void){unsigned int n=0,i;for(i=0;i<8;++i)n+=!!(online.bits&(1U<<i));return n;}
static void cpu_maps_update_begin(void){if(locked)abort();locked=1;}
static void cpu_maps_update_done(void){if(!locked)abort();locked=0;}
static int pm_wakeup_pending(void){if(!locked)abort();++wakes;return mode>=8 && mode<=14 && wakes==mode-7;}
static int _cpu_down(int cpu,int frozen,int stage){
 if(!locked || !frozen || stage!=CPUHP_OFFLINE || !cpu_online(cpu))abort();++downs;
 if(mode>=1 && mode<=7 && downs==mode)return -EIO;
 if(!(mode==27 && cpu==7))online.bits&=~(1U<<cpu);return 0;
}
static int _cpu_up(int cpu,int frozen,int stage){
 if(!locked || !frozen || stage!=CPUHP_ONLINE || cpu_online(cpu))abort();++ups;
 if(mode>=15 && mode<=21 && ups==mode-14)return -EIO;
 online.bits|=1U<<cpu;return 0;
}
static void __cpu_hotplug_enable(void){if(!locked || cpu_hotplug_disabled<1)abort();--cpu_hotplug_disabled;}
static void arch_enable_nonboot_cpus_begin(void){if(!locked)abort();++begin_hooks;}
static void arch_enable_nonboot_cpus_end(void){if(!locked)abort();++end_hooks;}
static struct device *get_cpu_device(int cpu){return mode==26?NULL:&devices[cpu];}
static void kobject_uevent(unsigned int*kobj,int event){if(!locked || event!=KOBJ_ONLINE)abort();++uevents;}
'''
MAIN=r'''
int main(int argc,char**argv){
 unsigned int before,stopped;int ret,prior;
 mode=atoi(argv[1]);online.bits=mode==22?0xfe:mode==23?1:mode==24?0:0xff;
 cpu_hotplug_disabled=prior=mode==25?2:0;before=online.bits;
 ret=disable_nonboot_cpus();stopped=online.bits;
 if(locked || cpu_hotplug_disabled!=prior+1)abort();
 enable_nonboot_cpus();
 if(locked || cpu_hotplug_disabled!=prior || storage.bits || begin_hooks!=end_hooks)abort();
 printf("{\"mode\":%u,\"before\":%u,\"stopped\":%u,\"restored\":%u,\"ret\":%d,\"downs\":%u,\"ups\":%u}\n",mode,before,stopped,online.bits,ret,downs,ups);return 0;
}
'''
def run(output,cpu_source,cpu_header):
    out=Path(output).resolve()
    if out.exists() or not out.is_relative_to((ROOT/'note10/private').resolve()):raise ValueError('Fresh private CPU hotplug model required')
    raw=Path(cpu_source).read_bytes();header=Path(cpu_header).read_bytes();pins=PINS
    if hashlib.sha256(raw).hexdigest()!=pins['kernel/cpu.c'] or hashlib.sha256(header).hexdigest()!=pins['include/linux/cpu.h']:raise ValueError('Original CPU hotplug source differs')
    raw=raw.decode();header=header.decode();out.mkdir(parents=True)
    stub=STUB;main=MAIN
    code=stub+function(raw,'int freeze_secondary_cpus(')+function(raw,'void enable_nonboot_cpus(')+function(header,'static inline int disable_nonboot_cpus(')+main
    p=out/'cpu-hotplug.c';p.write_bytes(code.encode());exe=out/('cpu-hotplug.exe' if sys.platform=='win32' else 'cpu-hotplug')
    cc=ROOT/'host-tools/windows-build/llvm-mingw/llvm-mingw-20261006-ucrt-x86_64/bin/clang.exe' if sys.platform=='win32' else shutil.which('cc')
    made=subprocess.run([str(cc),'-std=c11','-O2',str(p),'-o',str(exe)],capture_output=True);(out/'compile.log').write_bytes(made.stdout+made.stderr);assert made.returncode==0
    rows=[]
    for mode in range(28):
     ran=subprocess.run([str(exe),str(mode)],capture_output=True,timeout=15);(out/f'mode-{mode}.log').write_bytes(ran.stdout+ran.stderr)
     if mode==27:
      assert ran.returncode==73 and b'BUG' in ran.stdout;rows.append(dict(mode=mode,passed=True,original_online_count_bug_guard_observed=True));continue
     assert ran.returncode==0,(mode,ran.returncode)
     row=json.loads(ran.stdout)
     if 1<=mode<=7:assert row['ret']==-5 and row['downs']==mode and row['ups']==mode-1 and row['restored']==255
     elif 8<=mode<=14:assert row['ret']==-16 and row['downs']==mode-8 and row['ups']==mode-8 and row['restored']==255
     elif 15<=mode<=21:assert row['ret']==0 and row['downs']==7 and row['ups']==7 and row['restored']==(255^(1<<(mode-14)))
     else:assert row['ret']==0 and row['restored']==row['before']
     row['passed']=True;rows.append(row)
    result=dict(passed=True,cases=28,source_sha256=pins,actual_original_freeze_and_enable_executed=True,
     failed_freeze_always_requires_enable=True,void_enable_can_leave_a_cpu_offline=True,
     online_masks_required_for_diagnostic_acceptance=True,hardware_verified=False,outcomes=rows)
    (out/'result.json').write_bytes((json.dumps(result,indent=2)+'\n').encode());return result
