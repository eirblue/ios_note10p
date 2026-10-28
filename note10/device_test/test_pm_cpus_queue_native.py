"""Execute the real scheduling adapter with enabled/disabled CPU scope."""
import hashlib,json,shutil,subprocess,sys
from pathlib import Path
from prepare_pm_cpus import HERE
from run_probe import ROOT
STUB=r'''
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#define WQ_UNBOUND 2
#define WQ_MEM_RECLAIM 4
struct workqueue_struct {int id;};
static struct workqueue_struct queue;
static unsigned int mode,allocations,queued,legacy,work;
#define n10_pm_work work
static struct workqueue_struct *alloc_workqueue(const char*name,unsigned int flags,unsigned int max){
 if(strcmp(name,"n10_pm_cpus") || flags!=(WQ_UNBOUND|WQ_MEM_RECLAIM) || max!=1)abort();++allocations;return mode==1?NULL:&queue;
}
static bool queue_delayed_work(struct workqueue_struct*q,unsigned int*w,unsigned long delay){
 if(q!=&queue || w!=&work || (delay!=30000 && delay!=10000 && delay!=100))abort();++queued;return mode!=2;
}
static bool schedule_delayed_work(unsigned int*w,unsigned long delay){if(w!=&work)abort();++legacy;return mode!=2;}
'''
MAIN=r'''
int main(int argc,char**argv){unsigned int r[3];mode=atoi(argv[1]);r[0]=n10_pm_cpus_schedule(30000);r[1]=n10_pm_cpus_schedule(10000);r[2]=n10_pm_cpus_schedule(100);
printf("{\"allocations\":%u,\"queued\":%u,\"legacy\":%u,\"successes\":%u}\n",allocations,queued,legacy,r[0]+r[1]+r[2]);return 0;}
'''
def run(output):
    out=Path(output).resolve()
    if out.exists() or not out.is_relative_to((ROOT/'note10/private').resolve()):raise ValueError('Fresh private CPU queue model required')
    out.mkdir(parents=True);compiler=ROOT/'host-tools/windows-build/llvm-mingw/llvm-mingw-20261006-ucrt-x86_64/bin/clang.exe' if sys.platform=='win32' else shutil.which('cc');rows=[]
    for enabled in (False,True):
        name='enabled' if enabled else 'disabled';p=out/(name+'.c');p.write_bytes((('#define CONFIG_NOTE10_PM_CPUS_TEST\n' if enabled else '')+STUB+(HERE/'pm_cpus_workqueue.c').read_text()+MAIN).encode());exe=out/(name+('.exe' if sys.platform=='win32' else ''))
        made=subprocess.run([str(compiler),'-std=c11','-O2',str(p),'-o',str(exe)],capture_output=True);(out/(name+'-compile.log')).write_bytes(made.stdout+made.stderr)
        if made.returncode:raise ValueError('CPU queue adapter compilation failed')
        for mode in range(3):
            ran=subprocess.run([str(exe),str(mode)],capture_output=True,timeout=15);(out/f'{name}-{mode}.log').write_bytes(ran.stdout+ran.stderr)
            if ran.returncode:raise ValueError('CPU queue flags/call invariant failed')
            row=json.loads(ran.stdout);expected=dict(allocations=3 if mode==1 else 1,queued=0 if mode==1 else 3,legacy=0,successes=3 if mode==0 else 0) if enabled else dict(allocations=0,queued=0,legacy=3,successes=0 if mode==2 else 3)
            if row!=expected:raise ValueError('CPU queue allocation/retry behavior differs')
            rows.append(dict(enabled=enabled,mode=mode,passed=True))
    result=dict(passed=True,cases=6,outcomes=rows,actual_scheduler_adapter_executed=True,unbound_nonfreezable_queue_required=True,disabled_path_uses_original_queue=True,hardware_verified=False,source_sha256=hashlib.sha256((HERE/'pm_cpus_workqueue.c').read_bytes()).hexdigest(),harness_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    (out/'result.json').write_bytes((json.dumps(result,indent=2)+'\n').encode());return result
