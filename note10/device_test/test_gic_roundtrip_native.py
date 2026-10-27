"""Actual GIC backend/probe with explicit banked MMIO/IRQ/CPU stubs."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
from prepare_gic_roundtrip import HERE,SOURCES
from run_probe import ROOT
from decode_gic_roundtrip import decode
ID='0123456789abcdef0123456789abcdef'
STUB=r'''
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>
#include <stdbool.h>
#include <stdint.h>
typedef unsigned int u32;
#define __iomem
#define N10_RESERVE_BUILD_ID "0123456789abcdef0123456789abcdef"
#define GIC_CPU_CTRL 0
#define GIC_CPU_PRIMASK 4
#define GIC_CPU_BINPOINT 8
#define GIC_CPU_IDENT 12
#define GIC_DIST_CTRL 0
#define GIC_DIST_CTR 4
#define dsb(x) do{}while(0)
#define isb() do{}while(0)
#define scnprintf snprintf
#define pr_info printf
static unsigned int bank[8][4],dist[2],writes[8],original[8];
static unsigned int current_cpu,online=255,mode,locked,irq;
static struct {void *domain;} gic_data[1];
static void *gic_data_cpu_base(void*g){return mode==6 && current_cpu==2?NULL:bank[current_cpu];}
static void *gic_data_dist_base(void*g){return dist;}
static unsigned int smp_processor_id(void){return current_cpu;}
static unsigned int irqs_disabled(void){return irq;}
#define local_irq_save(f) do{(f)=irq;irq=1;}while(0)
#define local_irq_restore(f) do{irq=(mode==11 && current_cpu==2)?!(f):(f);}while(0)
static unsigned int readl_relaxed(void*p){
 unsigned int *q=p;
 if(q==bank[current_cpu] || q==bank[current_cpu]+1 || q==bank[current_cpu]+2 || q==bank[current_cpu]+3){
  unsigned int index=q-bank[current_cpu];
  if(current_cpu==2 && writes[current_cpu]){
   if(index==1 && writes[current_cpu]==1 && mode==1)return 1;
   if(index==1 && writes[current_cpu]==2 && mode==2)return 0;
   if(index==0 && mode==13)return bank[current_cpu][0]^1;
   if(index==2 && mode==14)return bank[current_cpu][2]^1;
  }
 }else if(q!=dist && q!=dist+1)abort();
 return *q;
}
static void writel_relaxed(unsigned int value,void*p){
 if(!irq || p!=&bank[current_cpu][1])abort();
 if((writes[current_cpu]==0 && value!=0) || (writes[current_cpu]==1 && value!=original[current_cpu]) || writes[current_cpu]>1)abort();
 ++writes[current_cpu];*(unsigned int*)p=value;
}
static void cpus_read_lock(void){if(locked++)abort();}
static void cpus_read_unlock(void){if(--locked)abort();}
static unsigned int num_online_cpus(void){return mode==7?7:8;}
#define for_each_online_cpu(c) for((c)=0;(c)<(mode==12?10:8);++(c)) if(online&(1U<<(c)))
static void on_each_cpu(void(*fn)(void*),void*p,int wait){
 if(!locked || !wait)abort();
 for(current_cpu=0;current_cpu<8;++current_cpu){
  if(mode==10 && current_cpu==4)continue;
  irq=(mode==17)?1:current_cpu%2;fn(p);
  if(mode==9 && current_cpu==2)fn(p);
 }
 if(mode==18)online=127;
}
static unsigned long long n10_online_bits(void){return online;}
'''
MAIN=r'''
int main(int argc,char**argv){
 unsigned int i;struct n10_gic_sample tmp[8];
 mode=atoi(argv[1]);gic_data[0].domain=mode==8?NULL:&dist;
 if(mode==12)online=0x27f;
 for(i=0;i<8;++i){bank[i][0]=1;bank[i][1]=original[i]=240-16*(i%4);bank[i][2]=i%3;bank[i][3]=0x20243b;}
 dist[0]=1;dist[1]=0x467;
 if(mode==3)bank[2][0]=0;
 if(mode==4)dist[0]=0;
 if(mode==5)bank[2][1]=original[2]=0;
 if(mode==16)bank[2][1]=original[2]=256;
 if(mode==15)for(i=0;i<8;++i)bank[i][1]=original[i]=128;
 if(n10_gic_roundtrip(NULL,8)!=-EINVAL || n10_gic_roundtrip(tmp,7)!=-EINVAL)return 80;
 n10_test_gic();
 if(locked || dist[0]!=(mode==4?0:1) || dist[1]!=0x467)return 81;
 for(i=0;i<8;++i){
  unsigned int want=2;
  if(mode==7 || mode==8 || mode==12 || mode==4 || (i==2 && (mode==3 || mode==5 || mode==6 || mode==16)) || (i==4 && mode==10))want=0;
  if(writes[i]!=want || bank[i][1]!=original[i])return 82;
 }
 return 0;
}
'''

def run(output):
    output=Path(output).resolve()
    if not output.is_relative_to((ROOT/'note10/private').resolve()) or output.exists():raise ValueError('Fresh private GIC model directory required')
    output.mkdir(parents=True)
    sources={n:(HERE/n).read_bytes() for n in SOURCES}
    clean=lambda s:re.sub(r'^#include[^\n]*\n','',s,flags=re.M)
    checksum=re.search(r'static u32 n10_frame_checksum[^}]+}',(HERE/'xnu_reserve.c').read_text()).group()
    text=STUB+sources['gic_roundtrip_contract.h'].decode()+clean(sources['gic_roundtrip_backend.c'].decode())+checksum+clean(sources['gic_roundtrip_probe.c'].decode())+MAIN
    src=output/'gic.c';src.write_bytes(text.encode())
    compiler=ROOT/'host-tools/windows-build/llvm-mingw/llvm-mingw-20261006-ucrt-x86_64/bin/clang.exe' if sys.platform=='win32' else shutil.which('cc')
    exe=output/('gic.exe' if sys.platform=='win32' else 'gic')
    built=subprocess.run([str(compiler),'-std=c11','-O2',str(src),'-o',str(exe)],capture_output=True,timeout=60)
    (output/'compile.log').write_bytes(built.stdout+built.stderr)
    if built.returncode:raise RuntimeError('GIC actual-C model compilation failed')
    rows=[]
    for mode in range(19):
        ran=subprocess.run([str(exe),str(mode)],capture_output=True,timeout=15)
        (output/f'mode-{mode}.log').write_bytes(ran.stdout+ran.stderr)
        if ran.returncode:raise ValueError('GIC restoration/write allowlist model failed mode '+str(mode))
        try:decode(ran.stdout.decode(),ID);accepted=True
        except ValueError:accepted=False
        if accepted!=(mode in (0,15,17)):raise ValueError('GIC strict decoder differs for mode '+str(mode))
        rows.append(dict(mode=mode,accepted=accepted,passed=True))
    result=dict(passed=True,cases=len(rows),outcomes=rows,source_sha256={n:hashlib.sha256(raw).hexdigest() for n,raw in sources.items()},
        harness_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),actual_backend_executed=True,actual_probe_executed=True,strict_decoder_verified=True,hardware_verified=False)
    (output/'result.json').write_bytes((json.dumps(result,indent=2)+'\n').encode());return result

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True)
    r=run(parser.parse_args().output);print(json.dumps({'passed':r['passed'],'cases':r['cases']}))
