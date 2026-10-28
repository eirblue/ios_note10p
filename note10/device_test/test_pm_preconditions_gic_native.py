"""Test exact actual GIC observer read addresses and phase behavior."""
import argparse,hashlib,json,subprocess,sys
from pathlib import Path
from test_pm_callbacks_producer import clean
HERE=Path(__file__).resolve().parent
STUB=r'''
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <errno.h>
typedef unsigned int u32;
typedef long long s64;
#define __iomem
#define GIC_DIST_ENABLE_SET 0x100
#define GIC_DIST_ACTIVE_SET 0x300
#define GIC_DIST_CONFIG 0xc00
#define GIC_DIST_PRI 0x400
#define GIC_CPU_CTRL_EOImodeNS 0x200
#define GICC_DIS_BYPASS_MASK 0x1e0
#define GICC_ENABLE 1
#define GICC_INT_PRI_THRESHOLD 0xf0
#define GICD_INT_DEF_PRI_X4 0xa0a0a0a0U
static char fake_dist[4096];static int irq,pc,phase,reads,mode,hist[3][12];static unsigned long online=1;
struct gic {int domain;};static struct gic gic_data[1]={{1}};static int supports_deactivate;
#define raw_smp_processor_id() 0
#define num_online_cpus() 1
#define cpu_online_mask (&online)
#define cpumask_bits(p) (p)
#define preempt_count() pc
#define irqs_disabled() irq
#define static_key_true(p) (*(p))
#define gic_data_dist_base(p) ((void *)fake_dist)
static u32 readl_relaxed(void *p){int off=(char*)p-fake_dist;int index=off==0x100?0:off==0x300?1:(off>=0xc00 && off<=0xc04 && !(off%4))?2+(off-0xc00)/4:(off>=0x400 && off<=0x41c && !(off%4))?4+(off-0x400)/4:-1;if(index<0 || pc!=1 || irq!=(phase==1))abort();++hist[phase][index];++reads;if(off==0x300)return phase;if(off>=0x400 && off<=0x41c)return mode==1 && phase==1?0:GICD_INT_DEF_PRI_X4;return 0;}
'''
MAIN=r'''
#define CHECK(x) do {if(!(x)){fprintf(stderr,"line %d\n",__LINE__);return 1;}}while(0)
int main(int argc,char **argv){int i;u32 ctlr=GICC_ENABLE,pmr=GICC_INT_PRI_THRESHOLD;struct n10_precond_gic_row row[3]={{0}};mode=atoi(argv[1]);pc=1;if(mode==2){supports_deactivate=1;ctlr|=GIC_CPU_CTRL_EOImodeNS;}if(mode==3)ctlr|=0x20;if(mode==4)pmr=0;if(mode==5)ctlr=0;for(phase=0;phase<3;phase++){irq=phase==1;CHECK(!n10_pre_gic_regs(phase,&row[phase],ctlr,pmr));CHECK(row[phase].active==(unsigned)phase);CHECK(row[phase].restore_matches==(unsigned)!((mode==1 && phase==1)||mode==4||mode==5));for(i=0;i<12;i++)CHECK(hist[phase][i]==1);}CHECK(reads==36);return 0;}
'''
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--output',required=True);o=Path(ap.parse_args().output);o.mkdir(parents=True,exist_ok=False)
 src=o/'gic.c';src.write_text(STUB+clean('pm_preconditions_contract.h')+clean('pm_preconditions_gic_regs.c')+MAIN,encoding='utf-8')
 cc=Path('host-tools/windows-build/llvm-mingw/llvm-mingw-20261006-ucrt-x86_64/bin/clang.exe') if sys.platform=='win32' else 'cc';exe=o/('gic.exe' if sys.platform=='win32' else 'gic');r=subprocess.run([str(cc),'-std=gnu11',str(src),'-o',str(exe)],capture_output=True,timeout=60);(o/'compile.log').write_bytes(r.stdout+r.stderr)
 if r.returncode:raise RuntimeError(r.stderr.decode(errors='replace'))
 for mode in range(6):
  r=subprocess.run([str(exe),str(mode)],capture_output=True,timeout=20);(o/f'mode-{mode}.log').write_bytes(r.stdout+r.stderr)
  if r.returncode:raise RuntimeError(r.stderr.decode(errors='replace'))
 names=('pm_preconditions_contract.h','pm_preconditions_gic_regs.c')
 (o/'result.json').write_text(json.dumps({'passed':True,'hardware_verified':False,'cases':['baseline','priority-mismatch','deactivate','bypass','pmr-mismatch','control-mismatch'],'exact_read_allowlist':True,'no_gic_writes':True,'read_count':36,'source_sha256':{n:hashlib.sha256((HERE/n).read_bytes()).hexdigest() for n in names},'harness_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'generated_c_sha256':hashlib.sha256(src.read_bytes()).hexdigest(),'log_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in o.glob('*.log')}},indent=2)+'\n',encoding='utf-8')
if __name__=='__main__':main()
