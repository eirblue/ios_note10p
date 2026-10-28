"""Execute the new four-phase DMA backend against actual synthetic PM lists."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
from run_probe import ROOT
from test_dma_pm_native import STUB as BASE
HERE=Path(__file__).resolve().parent
STUB=BASE.replace('is_suspended,direct_complete,syscore,is_prepared;', 'is_suspended,direct_complete,syscore,is_prepared,is_late_suspended,is_noirq_suspended;')
STUB=STUB.replace('static void mutex_lock(int*p){if(locked++)abort();}', 'static int mutex_trylock(int*p){if(mode==20 || locked)return 0;locked=1;return 1;}')
STUB=STUB.replace('if(phase==1){d->power.is_prepared=1;d->power.is_suspended=1;}', 'if(phase==1 || phase==2){d->power.is_prepared=1;d->power.is_suspended=1;d->power.is_late_suspended=1;d->power.is_noirq_suspended=phase==2;}')
STUB += r'''
static void n10_edge_iommu_capture(unsigned int phase, unsigned int generation) {(void)phase;(void)generation;}
static void n10_edge_syscore_capture(unsigned int phase, unsigned int generation) {(void)phase;(void)generation;}
static unsigned int online_count=8,irq_off;static unsigned long online_mask=255;
static unsigned int num_online_cpus(void){return online_count;}
static int irqs_disabled(void){return irq_off;}
#define cpu_online_mask (&online_mask)
#define cpumask_bits(p) (p)
'''
MAIN=r'''
int main(int argc,char**argv){
 unsigned int phase,gen; struct device copy[4097];struct n10_edge_dma_sample out[4];
 mode=atoi(argv[1]);gen=(mode==14 || mode==28)?0xffffffffU:1;
 for(phase=0;phase<4;++phase){
  setup(phase); if(mode==21 && phase==2)devices[1].power.is_noirq_suspended=0;
  if(mode==22 && phase==2)devices[1].power.is_late_suspended=0;
  if(mode==23 && phase==0)devices[1].power.is_late_suspended=1;
  if(mode==24 && phase==0)irq_off=1;if(mode==25 && phase==0)online_count=7;
  memcpy(copy,devices,sizeof(devices));
  if(!(mode==3 && phase==1))n10_edge_dma_capture(phase,gen+(mode==5 && phase==1));
  if(mode==4 && phase==1)n10_edge_dma_capture(phase,gen);
  if(locked || memcmp(copy,devices,sizeof(devices)))return 81;
 }
 if(mode==26)n10_edge_dma_samples[1].active++;
 if(mode==29)n10_edge_dma_samples[1].exception_direct++;
 if(mode==30)n10_edge_dma_samples[0].prepared++;
 if(mode==27)n10_edge_dma_capture(0,0);
 if(mode==28)for(phase=0;phase<4;++phase){setup(phase);n10_edge_dma_capture(phase,1);}
 printf("%d\n",n10_edge_dma_read(out,mode==14?1:2));return 0;
}
'''
def run(output):
    output=Path(output).resolve()
    if not output.is_relative_to((ROOT/'note10/private').resolve()) or output.exists():raise ValueError('fresh private directory required')
    output.mkdir(parents=True)
    names=('pm_edge_dma_contract.h','pm_edge_dma_backend.c');sources={n:(HERE/n).read_bytes() for n in names}
    clean=lambda s:re.sub(r'^#include[^\n]*\n','',s,flags=re.M)
    src=output/'dma.c';src.write_text(STUB+sources[names[0]].decode()+clean(sources[names[1]].decode())+MAIN)
    compiler=ROOT/'host-tools/windows-build/llvm-mingw/llvm-mingw-20261006-ucrt-x86_64/bin/clang.exe' if sys.platform=='win32' else shutil.which('cc')
    exe=output/('dma.exe' if sys.platform=='win32' else 'dma')
    built=subprocess.run([str(compiler),'-std=c11','-O2',str(src),'-o',str(exe)],capture_output=True,timeout=60)
    (output/'compile.log').write_bytes(built.stdout+built.stderr)
    if built.returncode:raise RuntimeError('DMA actual-C compilation failed')
    modes=[0,1,3,4,5,6,14,20,21,22,23,24,25,26,27,28,29,30];accept={0,14,21,28};outcomes=[]
    for mode in modes:
        p=subprocess.run([str(exe),str(mode)],capture_output=True,timeout=15)
        (output/f'mode-{mode}.log').write_bytes(p.stdout+p.stderr)
        if p.returncode:raise ValueError('model execution failed '+str(mode))
        accepted=p.stdout.strip()==b'0'
        if accepted!=(mode in accept):raise ValueError('unexpected acceptance '+str(mode))
        outcomes.append({'mode':mode,'accepted':accepted})
    result={'passed':True,'cases':len(outcomes),'outcomes':outcomes,'harness_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'actual_backend_executed':True,'source_sha256':{n:hashlib.sha256(v).hexdigest() for n,v in sources.items()}}
    (output/'result.json').write_text(json.dumps(result,indent=2)+'\n');return result
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);r=run(p.parse_args().output);print(json.dumps({'passed':r['passed'],'cases':r['cases']}))
