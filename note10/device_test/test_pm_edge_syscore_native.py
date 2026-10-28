"""Execute the actual syscore inventory backend against synthetic registered ops."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
from run_probe import ROOT
HERE = Path(__file__).resolve().parent
STUB = r'''
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <stddef.h>
#include <errno.h>
#define KSYM_NAME_LEN 128
struct list_head {struct list_head *next,*prev;};
struct syscore_ops {struct list_head node; int (*suspend)(void); void (*resume)(void); void (*shutdown)(void);};
static struct list_head syscore_ops_list;
static struct syscore_ops ops[65], saved[65];
static unsigned int mode, lock_held, irq_off, cpu_count=8;
static unsigned long online_mask=255;
static int syscore_ops_lock;
#define list_for_each_entry(p,h,member) for ((p)=(struct syscore_ops *)((char *)(h)->next - offsetof(struct syscore_ops,member)); &(p)->member != (h); (p)=(struct syscore_ops *)((char *)(p)->member.next - offsetof(struct syscore_ops,member)))
static int mutex_trylock(int *p) {if(mode==3 || lock_held)return 0; lock_held=1;return 1;}
static void mutex_unlock(int *p) {if(!lock_held)abort();lock_held=0;if(mode==19)irq_off=1;if(mode==20)cpu_count=7;if(mode==21)online_mask=127;}
static int irqs_disabled(void) {return irq_off;}
static unsigned int num_online_cpus(void) {return cpu_count;}
#define cpu_online_mask (&online_mask)
#define cpumask_bits(p) (p)
static int fn0(void){abort();} static void fn1(void){abort();} static void fn2(void){abort();}
static int core_kernel_text(unsigned long addr) {return mode!=4 && (addr==(unsigned long)fn0 || addr==(unsigned long)fn1 || addr==(unsigned long)fn2);}
static const char *kallsyms_lookup(unsigned long addr,unsigned long *size,unsigned long *offset,char **mod,char *name) {
 if (!lock_held) abort(); *size=4;*offset=mode==6?1:0;*mod=mode==7?"module":NULL;
 if(mode==5)return NULL;
 if(mode==8){memset(name,'x',KSYM_NAME_LEN-1);name[KSYM_NAME_LEN-1]=0;return name;}
 if(mode==9){strcpy(name,"bad name");return name;}
 strcpy(name,addr==(unsigned long)fn0?"suspend_fn":addr==(unsigned long)fn1?"resume_fn":"shutdown_fn");return name;
}
static void setup(unsigned int count) {
 unsigned int i;syscore_ops_list.next=syscore_ops_list.prev=&syscore_ops_list;
 memset(ops,0,sizeof(ops));
 for(i=0;i<count;i++) {struct list_head *n=&ops[i].node; n->next=&syscore_ops_list;n->prev=syscore_ops_list.prev;n->prev->next=n;syscore_ops_list.prev=n;ops[i].suspend=fn0;ops[i].resume=fn1;ops[i].shutdown=i%2?fn2:NULL;}
 memcpy(saved,ops,sizeof(ops));
}
'''
MAIN = r'''
int main(int argc,char **argv) {
 struct n10_edge_syscore_sample *out=calloc(2,sizeof(*out));unsigned int gen;
 if(!out)return 90;mode=atoi(argv[1]);gen=(mode==15 || mode==24)?0xffffffffU:1;
 setup(mode==1?0:mode==2?65:3);
 if(mode==10)irq_off=1;if(mode==11)cpu_count=7;if(mode==12)online_mask=127;
 n10_edge_syscore_capture(0,gen);
 if(mode==13)n10_edge_syscore_capture(0,gen);
 if(mode==14)n10_edge_syscore_capture(3,gen+1);else n10_edge_syscore_capture(3,gen);
 if(mode==16)n10_edge_syscore_capture(3,gen);
 if(mode==17)n10_edge_syscore_samples[1].entries[0].names[0][0]='X';
 if(mode==18)n10_edge_syscore_samples[1].entries[0].mask^=1;
 if(mode==22)n10_edge_syscore_samples[0].count=65;
 if(mode==23)n10_edge_syscore_capture(0,0);
 if(mode==24){n10_edge_syscore_capture(0,1);n10_edge_syscore_capture(3,1);}
 if(lock_held || memcmp(ops,saved,sizeof(ops)))return 91;
 printf("%d\n",n10_edge_syscore_read(out,mode==15?1:2));free(out);return 0;
}
'''
def run(output):
    output = Path(output).resolve()
    if not output.is_relative_to((ROOT / 'note10/private').resolve()) or output.exists():
        raise ValueError('fresh private directory required')
    output.mkdir(parents=True)
    names = ['pm_edge_syscore_contract.h', 'pm_edge_syscore_backend.c']
    srcs = {n:(HERE/n).read_bytes() for n in names}
    clean = lambda s: re.sub(r'^#include[^\n]*\n', '', s, flags=re.M)
    src = output/'syscore.c'; src.write_text(STUB + srcs[names[0]].decode() + clean(srcs[names[1]].decode()) + MAIN)
    compiler = ROOT/'host-tools/windows-build/llvm-mingw/llvm-mingw-20261006-ucrt-x86_64/bin/clang.exe' if sys.platform=='win32' else shutil.which('cc')
    exe = output/('syscore.exe' if sys.platform=='win32' else 'syscore')
    built = subprocess.run([str(compiler),'-std=c11','-O2',str(src),'-o',str(exe)],capture_output=True,timeout=60)
    (output/'compile.log').write_bytes(built.stdout+built.stderr)
    if built.returncode: raise RuntimeError('syscore actual-C compilation failed')
    outcomes=[]
    for mode in range(25):
        p=subprocess.run([str(exe),str(mode)],capture_output=True,timeout=15)
        (output/f'mode-{mode}.log').write_bytes(p.stdout+p.stderr)
        if p.returncode: raise ValueError('model execution failed '+str(mode))
        accepted=p.stdout.strip()==b'0'
        if accepted != (mode in (0,15,24)): raise ValueError('unexpected acceptance '+str(mode))
        outcomes.append({'mode':mode,'accepted':accepted})
    result={'passed':True,'cases':len(outcomes),'outcomes':outcomes,'harness_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'actual_backend_executed':True,'source_sha256':{n:hashlib.sha256(v).hexdigest() for n,v in srcs.items()}}
    (output/'result.json').write_text(json.dumps(result,indent=2)+'\n'); return result
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True)
    r=run(p.parse_args().output);print(json.dumps({'passed':r['passed'],'cases':r['cases']}))
