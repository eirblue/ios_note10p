"""Compile the real v45 getter/lifecycle against strict lock/context fakes."""
import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path

CASES = [
    'busy-no-running-read', 'success-int-min', 'success-minus-one',
    'success-zero', 'success-one', 'success-int-max',
    'busy-bad-generation', 'busy-bad-index-kind-mask',
    'duplicate-target', 'post-lock-context-unwind', 'missing-target',
    'busy-bad-index', 'busy-bad-kind', 'old-below-int-min', 'old-above-int-max',
]
PRELUDE = r'''
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <limits.h>
typedef int64_t s64;
#define N10_PRECOND_CAP 32
#define N10_PRE_EHLD 6
#define EPERM 1
#define EIO 5
struct notifier_block { int (*notifier_call)(struct notifier_block *, unsigned long, void *); };
struct n10_precond_row { int priority; unsigned int kind, valid; s64 value[8]; };
struct n10_precond_sample { unsigned int generation, seen, bad, completed, count; int error; struct n10_precond_row row[N10_PRECOND_CAP]; };
struct exynos_ehld_ctrl { int ehld_running; int lock; };
static struct exynos_ehld_ctrl g_ctrl;
static struct notifier_block ehld_nb;
static int n10_ehld_c2_pm_notifier(struct notifier_block *n, unsigned long e, void *d) { return 0; }
#define exynos_ehld_c2_pm_notifier n10_ehld_c2_pm_notifier
#define exynos_ehld_c2_pm_nb ehld_nb
#define ehld_ctrl g_ctrl
#define this_cpu_ptr(p) (&g_ctrl)
static unsigned int gen=9, pc=1, irqs=1, tries, unlocks, reads, fail_after_lock;
static int force_busy;
static int in_interrupt(void) { return 0; }
static unsigned int preempt_count(void) { return pc; }
static int n10_pre_context(unsigned int g, int irq_off, unsigned int preempt) {
    return g==gen && irq_off==1 && irqs==1 && preempt==pc;
}
#define READ_ONCE(x) ({ if ((void *)&(x)==(void *)&g_ctrl.ehld_running) reads++; (x); })
static int raw_spin_trylock(int *p) { tries++; if (force_busy) return 0; if (*p) return 0; *p=1; pc++; if (fail_after_lock) gen++; return 1; }
static void raw_spin_unlock(int *p) { unlocks++; *p=0; pc--; }
'''
MAIN = r'''
#define CHECK(x) do { if (!(x)) { fprintf(stderr,"check:%d\n",__LINE__); return 1; } } while (0)
static int one(int mode, s64 old, int raw, int expected_error) {
    struct n10_precond_sample pre={0}; struct n10_ehld_lock_sample out={0};
    int ret; gen=9; pc=1; irqs=1; tries=unlocks=reads=0; force_busy=(mode==0 || mode==6 || mode==7 || mode==11 || mode==12); fail_after_lock=(mode==9); g_ctrl.lock=0; g_ctrl.ehld_running=raw;
    ehld_nb.notifier_call=n10_ehld_c2_pm_notifier; pre.generation=gen;pre.seen=1;pre.count=3;pre.row[1].kind=N10_PRE_EHLD;pre.row[1].valid=3;pre.row[1].value[0]=old;
    n10_ehld_lock_begin(gen);
    if(mode==6) pre.generation++;
    if(mode==7) { pre.row[1].valid=1; }
    if(mode==10) pre.row[1].kind=1;
    if(mode==12) pre.row[1].kind=1;
    if(mode==13) pre.row[1].value[0]=(s64)INT_MIN-1;
    if(mode==14) pre.row[1].value[0]=(s64)INT_MAX+1;
    ret=n10_ehld_lock_collect(&ehld_nb,&pre,mode==11?2:1,gen);
    if(mode==8) { CHECK(ret==0); ret=n10_ehld_lock_collect(&ehld_nb,&pre,1,gen); expected_error=1; }
    if(mode==10 || mode==11 || mode==12) { CHECK(ret==0); CHECK(n10_ehld_lock_complete(&pre,gen)!=0); return 0; }
    if(expected_error) { CHECK(ret!=0); CHECK(unlocks==((mode==9 || mode==8)?1:0)); if(mode==9){CHECK(tries==1 && reads==0);} else if(mode==8){CHECK(tries==1 && reads==1);} else {CHECK(tries==0 && reads==0);} return 0; }
    CHECK(ret==0); CHECK(n10_ehld_lock_complete(&pre,gen)==0); n10_ehld_lock_finish(0);
    CHECK(n10_ehld_lock_copy(&out,gen+1)==0);
    CHECK(pc==1 && irqs==1 && out.row.chain_count==3 && out.row.index==1);
    CHECK(out.row.lock_available==(unsigned)!force_busy);
    CHECK(out.row.running_valid==(unsigned)!force_busy);
    CHECK(tries==1 && reads==(unsigned)!force_busy);
    CHECK(unlocks==(unsigned)!force_busy);
    if(!force_busy) CHECK(out.row.running==(unsigned)!!old);
    return 0;
}
int main(int argc,char **argv) {
    int m=atoi(argv[1]);
    if(m==0) return one(0,-1,1,0);
    if(m==1) return one(1,INT_MIN,1,0);
    if(m==2) return one(2,-1,7,0);
    if(m==3) return one(3,0,0,0);
    if(m==4) return one(4,1,-9,0);
    if(m==5) return one(5,INT_MAX,42,0);
    if(m==6) return one(6,1,1,1);
    if(m==7) return one(7,1,1,1);
    if(m==8) return one(8,1,1,1);
    if(m==9) return one(9,1,1,1);
    if(m==10) return one(10,1,1,1);
    if(m==11) return one(11,1,1,1);
    if(m==12) return one(12,1,1,1);
    if(m==13) return one(13,(s64)INT_MIN-1,1,1);
    return one(14,(s64)INT_MAX+1,1,1);
}
'''

def source(path):
    return re.sub(r'^#include[^\n]*\n', '', path.read_text(encoding='utf-8'), flags=re.M)

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--source-root', required=True, type=Path)
    p.add_argument('--output', required=True, type=Path)
    p.add_argument('--cc', required=True)
    a = p.parse_args()
    root, out = a.source_root, a.output
    out.mkdir(parents=True, exist_ok=False)
    code = PRELUDE + source(root/'include/linux/note10_ehld_lock_audit.h') + source(root/'drivers/soc/samsung/debug/note10_ehld_lock_getter.c') + source(root/'kernel/note10_ehld_lock_chain.c') + MAIN
    cfile=out/'model.c'; exe=out/('model.exe' if __import__('sys').platform=='win32' else 'model')
    cfile.write_text(code,encoding='utf-8',newline='\n')
    c=subprocess.run([a.cc,'-std=gnu11','-O2',str(cfile),'-o',str(exe)],capture_output=True)
    (out/'compile.log').write_bytes(c.stdout+c.stderr)
    if c.returncode: raise RuntimeError('compile failed; see compile.log')
    for i,name in enumerate(CASES):
        result=subprocess.run([str(exe.resolve()),str(i)],capture_output=True)
        (out/(name+'.log')).write_bytes(result.stdout+result.stderr)
        if result.returncode: raise RuntimeError(name+' failed')
    h=lambda f:hashlib.sha256(f.read_bytes()).hexdigest()
    paths=('include/linux/note10_ehld_lock_audit.h','drivers/soc/samsung/debug/note10_ehld_lock_getter.c','kernel/note10_ehld_lock_chain.c')
    proof={'passed':True,'hardware_verified':False,'cases':CASES,'source_sha256':{n:h(root/n) for n in paths},'harness_sha256':h(Path(__file__)),'generated_sha256':h(cfile),'logs_sha256':{f.name:h(f) for f in out.glob('*.log')}}
    (out/'result.json').write_text(json.dumps(proof,indent=2)+'\n',encoding='utf-8',newline='\n')

if __name__=='__main__': main()
