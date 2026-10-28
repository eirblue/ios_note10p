"""Actual delayed PMU API/gate and scheduler with controlled reads and time."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
from run_probe import ROOT
from prepare_abox_pmu import HERE,PINS,FINAL_CORE_SHA,validate_domains
from prepare_pmu_settle import SOURCES
from test_abox_pmu_native import STUB
from decode_pmu_settle import decode
from pmu_domain_table import DOMAINS
ACCEPTED=(0,176,177,180,181)
IDENTITY='0123456789abcdef0123456789abcdef'
EXTRA=r'''
#define CONFIG_NOTE10_PM_NOIRQ_TEST
static unsigned int nq_lane,nq_reads,st_active,st_mode,st_reads,pm_mutex;
static unsigned int pm_test_level;
#define TEST_NONE 0
#define PM_SUSPEND_MEM 3
#define N10_Q_PM_ENTERED 6
#define READ_ONCE(x) (x)
static void *n10_pm_owner,*n10_pm_active;
static struct {int failed_resume_early,failed_resume_noirq;} suspend_stats;
static int irqs_disabled(void){return irq;}
static void mutex_lock(unsigned int*p){if(pm_mutex || irq)abort();pm_mutex=1;}
static int mutex_trylock(unsigned int*p){if(irq)abort();if(pm_mutex)return 0;pm_mutex=1;return 1;}
static void mutex_unlock(unsigned int*p){if(!pm_mutex)abort();pm_mutex=0;}
static int regmap_read(struct regmap*m,unsigned int offset,unsigned int*out){
 static const unsigned int table[16][2]=DOMAIN_ARRAY;
 unsigned int n;
 if(!nq_lane)return regular_regmap_read(m,offset,out);
 n=st_active?st_reads%48:nq_reads;
 if(m!=&map || refs[0] || refs[1] || refs[2] || locks[0] || locks[1] || locks[2] || node_refs || properties || n>=48 || offset!=table[n/3][n%3==1])abort();
 if(st_active){
  if(!pm_mutex || irq)abort();++st_reads;
  if((st_mode>=1 && st_mode<=144 && st_reads==st_mode) || (st_mode==179 && st_reads==1))return -EIO;
  *out=st_mode==177?0:st_mode==181?(st_reads&1):0xffffffffU;
 }else{++nq_reads;*out=0;}
 return 0;
}
'''
MAIN=r'''
static struct n10_pm_noirq_sample n10_pm_noirq_last;
static void baseline(unsigned int generation){
 unsigned int p;nq_lane=0;mode=0;st_active=0;
 for(p=0;p<3;++p){setup();n10_abox_pmu_capture(p,generation);if(reads!=54)abort();}
 setup();nq_lane=1;nq_reads=0;n10_pmu_noirq_capture(generation);if(nq_reads!=48)abort();
 memset(&n10_pm_noirq_last,0,sizeof(n10_pm_noirq_last));
 n10_pm_noirq_last.generation=generation;n10_pm_noirq_last.seen=1;n10_pm_noirq_last.finished=1;
 n10_pm_noirq_last.stage=7;n10_pm_noirq_last.state=3;n10_pm_noirq_last.phase=6;
 n10_pm_noirq_last.late=n10_pm_noirq_last.late_ok=n10_pm_noirq_last.noirq=n10_pm_noirq_last.noirq_ok=n10_pm_noirq_last.point=1;
 st_active=1;
}
'''
DRIVER=r'''
int main(int argc,char**argv){
 unsigned int generation,completed,index,i,saved;int ret=-1;struct n10_pmu_settle_sample out;
 st_mode=atoi(argv[1]);generation=st_mode==176?0xffffffffU:1;baseline(generation);
 completed=generation+1;if(!completed)completed=1;index=0;
 if(st_mode==145)n10_pm_owner=(void*)1;
 if(st_mode==146)n10_pm_active=(void*)1;
 if(st_mode==147)pm_test_level=3;
 if(st_mode==148)n10_pm_noirq_last.bad=1;
 if(st_mode==149)n10_pm_noirq_last.finished=0;
 if(st_mode==150)n10_pm_noirq_last.stage=6;
 if(st_mode==151)n10_pm_noirq_last.state=1;
 if(st_mode==152)n10_pm_noirq_last.phase=5;
 if(st_mode==153)n10_pm_noirq_last.point=0;
 if(st_mode==154)n10_pm_noirq_last.error=-5;
 if(st_mode==155)n10_pm_noirq_last.original_error=-16;
 if(st_mode==156)n10_pm_noirq_last.pre_early=1;
 if(st_mode==157)suspend_stats.failed_resume_early=1;
 if(st_mode==158)suspend_stats.failed_resume_noirq=1;
 if(st_mode==159)n10_abox_pmu_samples[2].seen=0;
 if(st_mode==160)++n10_abox_pmu_samples[2].generation;
 if(st_mode==161)n10_pmu_noirq_last.error=1;
 if(st_mode==162)pmureg=NULL;
 if(st_mode==163)pmureg=(void*)-1;
 if(st_mode==164)completed=0;
 if(st_mode==165)++completed;
 if(st_mode==166)index=1;
 if(st_mode==167)irq=1;
 if(st_mode==169)n10_pm_noirq_last.generation=0;
 if(st_mode==170)n10_pm_noirq_last.late=0;
 if(st_mode==171)n10_pm_noirq_last.noirq_ok=0;
 if(st_mode==172)n10_pm_noirq_last.seen=2;
 if(st_mode==173)n10_pm_noirq_last.blocked=1;
 if(st_mode==174)n10_pm_noirq_last.ops_mask=1;
 if(st_mode==175)++n10_pm_noirq_last.generation;
 if(st_mode==182)index=3;
 if(st_mode==183)pm_mutex=1;
 saved=irq;memset(&out,0,sizeof(out));
 for(i=index;i<3 || i==index;++i){ret=n10_pm_settle_capture(st_mode==168?NULL:&out,completed,i);if(ret || i>=2)break;}
 if(st_mode==178){ret=n10_pm_settle_capture(&out,completed,2);if(st_reads!=144)abort();}
 if(st_mode==179){ret=n10_pm_settle_capture(&out,completed,0);if(st_reads!=1)abort();}
 if(st_mode==180){baseline(5);for(i=0;i<3;++i){ret=n10_pm_settle_capture(&out,6,i);if(ret)abort();}}
 if(irq!=saved || pm_mutex!=(st_mode==183) || refs[0] || refs[1] || refs[2] || locks[0] || locks[1] || locks[2] || node_refs)abort();
 printf("{\"mode\":%u,\"ret\":%d,\"reads\":%u,\"before\":%u,\"state\":%u,\"after\":%u}\n",st_mode,ret,st_reads,out.before,out.state,out.after);return 0;
}
'''
WORKER_STUB=r'''
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <errno.h>
#include <limits.h>
typedef unsigned int u32;
typedef int atomic_t;
#define ATOMIC_INIT(x) (x)
static int atomic_cmpxchg(atomic_t*p,int old,int n){int v=*p;if(v==old)*p=n;return v;}
#define N10_RESERVE_BUILD_ID "0123456789abcdef0123456789abcdef"
#define pr_info printf
#define scnprintf snprintf
struct work_struct {int unused;};
struct delayed_work {void(*fn)(struct work_struct*);};
#define DECLARE_DELAYED_WORK(n,f) struct delayed_work n={f}
static unsigned long jiffies,due;
static unsigned int wm,scheduled,schedules,captures,completed;
static unsigned long msecs_to_jiffies(unsigned int x){return x;}
static unsigned int jiffies_to_msecs(unsigned long x){return x;}
static int schedule_delayed_work(struct delayed_work*w,unsigned long delay){
 ++schedules;if(scheduled || (wm==3 && schedules==1) || (wm==4 && schedules==2))return 0;
 if(!delay)abort();due=jiffies+delay;scheduled=1;return 1;
}
'''
WORKER_DRIVER=r'''
static int n10_pm_settle_capture(struct n10_pmu_settle_sample*s,unsigned int generation,unsigned int index){
 if(generation!=completed || index!=captures++)abort();memset(s,0,sizeof(*s));
 s->generation=generation==1?0xffffffffU:generation-1;s->completed=generation;s->index=index;
 if((wm==5 && index==0)||(wm==6 && index==1)){s->error=4;return -EIO;}
 if(wm==12 && index==2)jiffies+=30001;
 s->before=s->state=s->after=index==0?0xffff:index==1?0x4000:0;return 0;
}
'''
WORKER_MAIN=r'''
int main(int argc,char**argv){
 unsigned int loops=0;wm=atoi(argv[1]);completed=wm==8?1:2;
 if(wm==11)jiffies=ULONG_MAX-500;
 n10_arm_pmu_settle(completed);if(wm==9)n10_arm_pmu_settle(completed);
 while(scheduled){
  if(++loops>6)abort();scheduled=0;jiffies=due;
  if(wm==1 && loops==1)--jiffies;
  if(wm==2 && loops==2)jiffies+=1000;
  if(wm==7 && loops==1)jiffies+=30000;
  n10_settle_worker(NULL);
 }
 if(wm==10)n10_settle_worker(NULL);
 printf("WORKER captures=%u schedules=%u\n",captures,schedules);return 0;
}
'''

def run(output,core_driver,pmu_source,domain_source):
    output=Path(output).resolve();core=Path(core_driver).read_bytes();pmu=Path(pmu_source).read_bytes();domain=Path(domain_source).read_bytes()
    if output.exists() or not output.is_relative_to((ROOT/'note10/private').resolve()):raise ValueError('Fresh private settle model required')
    if hashlib.sha256(core).hexdigest()!=FINAL_CORE_SHA or hashlib.sha256(pmu).hexdigest()!=PINS['drivers/soc/samsung/exynos-pmu.c'] or hashlib.sha256(domain).hexdigest()!=PINS['drivers/soc/samsung/cal-if/exynos9820/flexpmu_cal_local_exynos9820.h']:raise ValueError('Pinned settle core/API/CAL differs')
    validate_domains(domain.decode());output.mkdir(parents=True)
    clean=lambda s:re.sub(r'^#include[^\n]*\n','',s,flags=re.M)
    read_api=re.search(rb'int exynos_pmu_read\([^}]+\}',pmu).group().decode();getter=re.search(rb'struct regmap \*exynos_get_pmu_regmap\([^}]+\}',pmu).group().decode()
    extra=EXTRA.replace('DOMAIN_ARRAY','{'+','.join('{0x%x,0x%x}'%(c,s) for _,c,s in DOMAINS)+'}')
    header=clean((HERE/'abox_pmu_contract.h').read_text())+clean((HERE/'pm_noirq_contract.h').read_text())+clean((HERE/'pmu_settle_contract.h').read_text())
    stub=STUB.replace('static int regmap_read(','static int regular_regmap_read(')
    common=stub+extra+read_api+getter+header+'void n10_fsys_pm_read(struct n10_fsys_pm_sample*out){memset(out,0,sizeof(*out));out->registered=1;}\n'+clean((HERE/'abox_pmu_backend.c').read_text())+clean((HERE/'pmu_settle_backend.c').read_text())+MAIN+clean((HERE/'pmu_settle_gate.c').read_text())
    compiler=ROOT/'host-tools/windows-build/llvm-mingw/llvm-mingw-20261006-ucrt-x86_64/bin/clang.exe' if sys.platform=='win32' else shutil.which('cc')
    def build(name,code):
        p=output/(name+'.c');p.write_bytes(code.encode());exe=output/(name+('.exe' if sys.platform=='win32' else ''))
        made=subprocess.run([str(compiler),'-std=c11','-O2',str(p),'-o',str(exe)],capture_output=True,timeout=60);(output/(name+'-compile.log')).write_bytes(made.stdout+made.stderr)
        if made.returncode:raise ValueError('Settle C model compilation failed: '+name)
        return exe
    exe=build('settle',common+DRIVER);rows=[]
    for mode in range(184):
        ran=subprocess.run([str(exe),str(mode)],capture_output=True,timeout=15);(output/f'pmu-{mode}.log').write_bytes(ran.stdout+ran.stderr)
        if ran.returncode:raise ValueError('Settle lifetime/IRQ/lock invariant failed mode '+str(mode))
        row=json.loads(ran.stdout);accepted=row['ret']==0
        expected=mode if 1<=mode<=144 else 144 if mode in (0,176,177,178,181) else 288 if mode==180 else 1 if mode==179 else 0
        if accepted!=(mode in ACCEPTED) or row['reads']!=expected:raise ValueError('Settle acceptance/read count differs mode '+str(mode))
        if accepted and tuple(row[k] for k in ('before','state','after'))!=((0,0,0) if mode==177 else (0x5555,0xaaaa,0x5555) if mode==181 else (0xffff,0xffff,0xffff)):raise ValueError('Settle PMU masks differ')
        rows.append(dict(mode=mode,passed=True,accepted=accepted,reads=expected))
    checksum=re.search(r'static u32 n10_frame_checksum[^}]+}',(HERE/'xnu_reserve.c').read_text()).group()
    wh=clean((HERE/'pmu_settle_contract.h').read_text()).replace('int n10_pm_settle_capture(','static int n10_pm_settle_capture(')
    worker=build('worker',WORKER_STUB+wh+WORKER_DRIVER+checksum+clean((HERE/'pmu_settle_probe.c').read_text())+WORKER_MAIN);worker_rows=[]
    for mode in range(13):
        ran=subprocess.run([str(worker),str(mode)],capture_output=True,timeout=15);(output/f'worker-{mode}.log').write_bytes(ran.stdout+ran.stderr)
        if ran.returncode:raise ValueError('Settle actual worker scheduling invariant failed mode '+str(mode))
        try:decode(ran.stdout.decode(),IDENTITY,1 if mode==8 else 2);accepted=True
        except ValueError:accepted=False
        if accepted!=(mode in (0,1,2,8,9,10,11)):raise ValueError('Settle worker evidence differs mode '+str(mode))
        worker_rows.append(dict(mode=mode,passed=True,accepted=accepted))
    missing=build('missing-config',common.replace('#define CONFIG_EXYNOS_PMU','')+r'''
int main(void){struct n10_pmu_settle_sample out;unsigned int p;setup();
for(p=0;p<3;++p){n10_abox_pmu_samples[p].seen=1;n10_abox_pmu_samples[p].generation=1;n10_abox_pmu_samples[p].phase=p;n10_abox_pmu_samples[p].count=2;}
n10_pmu_noirq_last.generation=1;n10_pmu_noirq_last.seen=1;pm_mutex=1;st_active=1;
return n10_pmu_settle_capture(&out,2,0)!=-EIO || out.error!=2 || st_reads || reads;}
''')
    ran=subprocess.run([str(missing)],capture_output=True,timeout=15);(output/'missing-config.log').write_bytes(ran.stdout+ran.stderr)
    if ran.returncode:raise ValueError('Disabled PMU stub accepted in timed lane')
    result=dict(passed=True,cases=184,outcomes=rows,worker_cases=13,worker_outcomes=worker_rows,
        actual_pmu_api_and_gate_executed=True,actual_delayed_worker_executed=True,all_144_read_faults_refused=True,
        no_pm_owner_or_device_locks_in_read_lane=True,default_power_requests_unchanged=True,generation_wrap_and_reset_executed=True,
        missing_config_refused_without_reads=True,
        pm_mutex_contention_refused_without_wait=True,last_read_completion_deadline_checked=True,
        hardware_verified=False,source_sha256={n:hashlib.sha256((HERE/n).read_bytes()).hexdigest() for n in SOURCES},
        regular_backend_sha256=hashlib.sha256((HERE/'abox_pmu_backend.c').read_bytes()).hexdigest(),
        noirq_backend_sha256=hashlib.sha256((HERE/'pm_noirq_backend.c').read_bytes()).hexdigest(),
        core_sha256=FINAL_CORE_SHA,pmu_api_sha256=PINS['drivers/soc/samsung/exynos-pmu.c'],cal_sha256=PINS['drivers/soc/samsung/cal-if/exynos9820/flexpmu_cal_local_exynos9820.h'],
        harness_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    (output/'result.json').write_bytes((json.dumps(result,indent=2)+'\n').encode());return result

if __name__=='__main__':
    p=argparse.ArgumentParser()
    for n in ('output','core-driver','pmu-source','domain-source'):p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();r=run(a.output,a.core_driver,a.pmu_source,a.domain_source);print(json.dumps(dict(passed=r['passed'],cases=r['cases'],worker_cases=r['worker_cases'])))
