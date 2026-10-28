"""Execute the post-PM per-CPU readback producer without register writes."""
import hashlib,json,re,shutil,subprocess,sys
from pathlib import Path
from prepare_pm_cpus import HERE
from run_probe import ROOT
from decode_pm_cpus import decode_timers
STUB=r'''
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <stdint.h>
typedef uint64_t u64;typedef unsigned int u32;
#define N10_RESERVE_BUILD_ID "0123456789abcdef0123456789abcdef"
#define pr_info printf
#define scnprintf snprintf
static unsigned int tm,cpu,locked,calls;
static int n10_timer_done=1;
static struct {u64 restored;unsigned int seen;} n10_timers[8];
static void cpus_read_lock(void){if(locked)abort();locked=1;}
static void cpus_read_unlock(void){if(!locked)abort();locked=0;}
static unsigned int n10_online_bits(void){if(!locked)abort();return tm==13?254:255;}
static unsigned int num_online_cpus(void){return tm==13?7:8;}
static unsigned int smp_processor_id(void){if(!locked)abort();return tm==12?8:cpu;}
static u64 reg_cntkctl_el1(void){return n10_timers[cpu].restored ^ (tm>=1 && tm<=8 && cpu==tm-1?16:0);}
static u64 reg_cntfrq_el0(void){return tm==9 && cpu==3?24000000:26000000;}
#define read_sysreg(name) reg_##name()
static void on_each_cpu(void(*fn)(void*),void*ctx,int wait){
 unsigned int i;if(!locked || !wait)abort();++calls;
 for(i=0;i<8;++i){if(tm==10 && i==7)continue;cpu=i;fn(ctx);if(tm==11 && i==7)fn(ctx);}
}
'''
MAIN=r'''
int main(int argc,char**argv){
 unsigned int i;tm=atoi(argv[1]);for(i=0;i<8;++i){n10_timers[i].seen=1;n10_timers[i].restored=214+i*256;}
 if(tm==14)n10_timers[3].seen=0;if(tm==16)n10_timer_done=0;
 n10_report_pm_cpu_timers(tm==15?0:tm==17?1:2);
 if(locked || calls!=(tm==13 || tm==15 || tm==16?0:1))abort();return 0;
}
'''
def run(output):
    out=Path(output).resolve()
    if out.exists() or not out.is_relative_to((ROOT/'note10/private').resolve()):raise ValueError('Fresh private CPU timer model required')
    out.mkdir(parents=True);probe=(HERE/'pm_cpus_timer_probe.c').read_text()
    checksum=re.search(r'static u32 n10_frame_checksum[^}]+}',(HERE/'xnu_reserve.c').read_text()).group()
    p=out/'cpu-timers.c';p.write_bytes((STUB+checksum+probe+MAIN).encode());exe=out/('cpu-timers.exe' if sys.platform=='win32' else 'cpu-timers')
    compiler=ROOT/'host-tools/windows-build/llvm-mingw/llvm-mingw-20261006-ucrt-x86_64/bin/clang.exe' if sys.platform=='win32' else shutil.which('cc')
    made=subprocess.run([str(compiler),'-std=c11','-O2',str(p),'-o',str(exe)],capture_output=True,timeout=60);(out/'compile.log').write_bytes(made.stdout+made.stderr)
    if made.returncode:raise ValueError('CPU timer readback model compilation failed')
    rows=[]
    for mode in range(18):
        ran=subprocess.run([str(exe),str(mode)],capture_output=True,timeout=15);(out/f'mode-{mode}.log').write_bytes(ran.stdout+ran.stderr)
        if ran.returncode:raise ValueError('CPU timer lock/callback invariant failed '+str(mode))
        try:decode_timers(ran.stdout.decode(),'0123456789abcdef0123456789abcdef',1 if mode==17 else 2);accepted=True
        except ValueError:accepted=False
        if accepted!=(mode in (0,17)):raise ValueError('CPU timer readback acceptance differs '+str(mode))
        rows.append(dict(mode=mode,passed=True,accepted=accepted))
    result=dict(passed=True,cases=18,outcomes=rows,actual_readback_producer_executed=True,
        each_cpu_mismatch_refused=True,no_register_writes=True,hardware_verified=False,
        producer_sha256=hashlib.sha256((HERE/'pm_cpus_timer_probe.c').read_bytes()).hexdigest(),
        harness_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    (out/'result.json').write_bytes((json.dumps(result,indent=2)+'\n').encode());return result
