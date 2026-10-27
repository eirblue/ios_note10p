"""Execute actual list audit and frame producer; reject mutation and bad evidence."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
from prepare_dma_pm import HERE,SOURCES
from run_probe import ROOT
from decode_dma_pm import decode
ID='0123456789abcdef0123456789abcdef'
STUB=r'''
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>
#include <stddef.h>
#include <stdint.h>
typedef unsigned int u32;
#define N10_RESERVE_BUILD_ID "0123456789abcdef0123456789abcdef"
#define scnprintf snprintf
#define pr_info printf
#define ARRAY_SIZE(x) (sizeof(x)/sizeof((x)[0]))
#define READ_ONCE(x) (x)
#define RPM_ACTIVE 0
#define RPM_SUSPENDED 1
struct list_head {struct list_head *next,*prev;};
struct device {
 struct {struct list_head entry;unsigned int is_suspended,direct_complete,syscore,is_prepared;int runtime_status;} power;
 unsigned long long *dma_mask,coherent_dma_mask;
 const char *name;
};
static struct list_head dpm_list,dpm_prepared_list,dpm_suspended_list,dpm_late_early_list,dpm_noirq_list;
static struct device devices[4097];
static unsigned long long dma_mask=~0ULL;
static unsigned int locked,mode;
static int dpm_list_mtx;
#define to_device(p) ((struct device*)((char*)(p)-offsetof(struct device,power.entry)))
#define list_for_each(p,h) for((p)=(h)->next;(p)!=(h);(p)=(p)->next)
static void mutex_lock(int*p){if(locked++)abort();}
static void mutex_unlock(int*p){if(--locked)abort();}
static const char *dev_name(struct device*d){if(!locked)abort();return d->name;}
static void reset(struct list_head*h){h->next=h->prev=h;}
static void append(struct list_head*h,struct list_head*p){p->next=h;p->prev=h->prev;h->prev->next=p;h->prev=p;}
static void setup(unsigned int phase){
 unsigned int i,n=mode==1?4097:24;
 struct list_head *heads[]={&dpm_list,&dpm_prepared_list,&dpm_suspended_list,&dpm_late_early_list,&dpm_noirq_list};
 reset(&dpm_list);reset(&dpm_prepared_list);reset(&dpm_suspended_list);reset(&dpm_late_early_list);reset(&dpm_noirq_list);
 memset(devices,0,sizeof(devices));
 for(i=0;i<n;++i){
  struct device*d=&devices[i];d->name=i%2?"dma-platform":"bus-device";
  if(i%2)d->dma_mask=&dma_mask;
  if(i%3==0)d->coherent_dma_mask=0xffffffff;
  d->power.runtime_status=i%3==0?RPM_SUSPENDED:(i%3==1?RPM_ACTIVE:2);
  if(phase==1){d->power.is_prepared=1;d->power.is_suspended=1;}
  if(mode==9 && phase==1 && i==1){d->power.is_suspended=0;d->power.direct_complete=1;}
  if(mode==10 && phase==1 && i==1)d->power.is_suspended=0;
  if(mode==7 && phase==2 && i==1)d->power.is_prepared=1;
  if(mode==8 && phase==2 && i==1)d->power.is_suspended=1;
  if(mode==6 && phase==2 && i==1)d->name="changed-device";
  append(phase==1?heads[i%5]:&dpm_list,&d->power.entry);
 }
}
'''
MAIN=r'''
int main(int argc,char**argv){
 unsigned int phase,generation,completed;struct device copy[4097];
 mode=atoi(argv[1]);generation=mode==2?0:(mode==14?0xffffffffU:1);
 if(n10_dma_pm_read(NULL,2)!=-EINVAL)return 80;
 for(phase=0;phase<3;++phase){
  setup(phase);memcpy(copy,devices,sizeof(devices));
  if(!(mode==3 && phase==1))n10_dma_pm_capture(phase,generation+(mode==5 && phase==1));
  if(mode==4 && phase==1)n10_dma_pm_capture(phase,generation);
  if(mode==12 && phase==0)n10_dma_pm_capture(phase,generation);
  if(locked || memcmp(copy,devices,sizeof(devices)))return 81;
 }
 if(mode==11)n10_dma_pm_samples[1].runtime_active++;
 completed=generation+1;if(!completed)completed=1;
 n10_report_dma_pm(mode==13?generation:completed);return 0;
}
'''

def run(output):
    output=Path(output).resolve()
    if not output.is_relative_to((ROOT/'note10/private').resolve()) or output.exists():raise ValueError('Fresh private DMA model directory required')
    output.mkdir(parents=True)
    sources={n:(HERE/n).read_bytes() for n in SOURCES}
    clean=lambda s:re.sub(r'^#include[^\n]*\n','',s,flags=re.M)
    checksum=re.search(r'static u32 n10_frame_checksum[^}]+}',(HERE/'xnu_reserve.c').read_text()).group()
    text=STUB+sources['dma_pm_contract.h'].decode()+clean(sources['dma_pm_backend.c'].decode())+checksum+clean(sources['dma_pm_probe.c'].decode())+MAIN
    src=output/'dma.c';src.write_bytes(text.encode())
    compiler=ROOT/'host-tools/windows-build/llvm-mingw/llvm-mingw-20261006-ucrt-x86_64/bin/clang.exe' if sys.platform=='win32' else shutil.which('cc')
    exe=output/('dma.exe' if sys.platform=='win32' else 'dma')
    built=subprocess.run([str(compiler),'-std=c11','-O2',str(src),'-o',str(exe)],capture_output=True,timeout=60)
    (output/'compile.log').write_bytes(built.stdout+built.stderr)
    if built.returncode:raise RuntimeError('DMA actual-C model compilation failed')
    rows=[]
    for mode in range(15):
        ran=subprocess.run([str(exe),str(mode)],capture_output=True,timeout=15)
        (output/f'mode-{mode}.log').write_bytes(ran.stdout+ran.stderr)
        if ran.returncode:raise ValueError('DMA read-only backend model failed mode '+str(mode))
        try:decode(ran.stdout.decode(),ID,1 if mode==14 else 2);accepted=True
        except ValueError:accepted=False
        if accepted!=(mode in (0,9,10,14)):raise ValueError('DMA strict decoder differs mode '+str(mode))
        rows.append(dict(mode=mode,accepted=accepted,passed=True))
    result=dict(passed=True,cases=len(rows),outcomes=rows,source_sha256={n:hashlib.sha256(raw).hexdigest() for n,raw in sources.items()},
        harness_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),actual_backend_executed=True,actual_probe_executed=True,strict_decoder_verified=True,hardware_verified=False)
    (output/'result.json').write_bytes((json.dumps(result,indent=2)+'\n').encode());return result

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True)
    r=run(parser.parse_args().output);print(json.dumps({'passed':r['passed'],'cases':r['cases']}))
