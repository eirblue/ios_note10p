"""Trace the pinned GIC restore branch against synthetic register stubs."""
import argparse,hashlib,json,subprocess,sys
from pathlib import Path
from test_fsys_pm_native import function
STUB=r'''
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
typedef uint32_t u32;
#define __iomem
#define WARN_ON(x) (x)
#define DIV_ROUND_UP(n,d) (((n)+(d)-1)/(d))
#define GICD_INT_EN_CLR_X32 0xffffffffU
#define GICD_INT_DEF_PRI_X4 0xa0a0a0a0U
#define GICC_INT_PRI_THRESHOLD 0xf0
#define GIC_DIST_ENABLE_CLEAR 0x180
#define GIC_DIST_ENABLE_SET 0x100
#define GIC_DIST_ACTIVE_CLEAR 0x380
#define GIC_DIST_ACTIVE_SET 0x300
#define GIC_DIST_CONFIG 0xc00
#define GIC_DIST_PRI 0x400
#define GIC_CPU_PRIMASK 0x4
#define raw_cpu_ptr(p) (p)
static char db[4096],cb[4096];static int writes,ups,mode;static u32 enable[]={5},active[]={6},conf[]={7,8};
struct gic_chip_data {u32 *saved_ppi_enable,*saved_ppi_active,*saved_ppi_conf;};
static void *gic_data_dist_base(struct gic_chip_data *g){(void)g;return mode==1?0:db;}
static void *gic_data_cpu_base(struct gic_chip_data *g){(void)g;return mode==2?0:cb;}
static void writel_relaxed(u32 v,void *p){int expected_addr[]={0x180,0x100,0x380,0x300,0xc00,0xc04,0x400,0x404,0x408,0x40c,0x410,0x414,0x418,0x41c,0x4};u32 expected_val[]={0xffffffffU,5,0xffffffffU,6,7,8,0xa0a0a0a0U,0xa0a0a0a0U,0xa0a0a0a0U,0xa0a0a0a0U,0xa0a0a0a0U,0xa0a0a0a0U,0xa0a0a0a0U,0xa0a0a0a0U,0xf0};if(writes>=15 || p!=(void*)((writes==14?cb:db)+expected_addr[writes]) || v!=expected_val[writes])abort();writes++;}
static void gic_cpu_if_up(struct gic_chip_data *g){(void)g;if(writes!=15)abort();ups++;}
'''
MAIN=r'''
int main(int argc,char**argv){struct gic_chip_data g={enable,active,conf};mode=atoi(argv[1]);gic_cpu_restore(mode==3?0:&g);if(mode==0){if(writes!=15 || ups!=1)abort();}else if(writes || ups)abort();return 0;}
'''
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--source',required=True);ap.add_argument('--output',required=True);a=ap.parse_args();p=Path(a.source);o=Path(a.output);o.mkdir(parents=True,exist_ok=False);src=o/'gic-branch.c';src.write_text(STUB+function(p.read_text(encoding='utf-8'),'void gic_cpu_restore(')+MAIN,encoding='utf-8');cc=Path('host-tools/windows-build/llvm-mingw/llvm-mingw-20261006-ucrt-x86_64/bin/clang.exe') if sys.platform=='win32' else 'cc';exe=o/('gic-branch.exe' if sys.platform=='win32' else 'gic-branch');r=subprocess.run([str(cc),'-std=gnu11',str(src),'-o',str(exe)],capture_output=True,timeout=60);(o/'compile.log').write_bytes(r.stdout+r.stderr)
 if r.returncode:raise RuntimeError(r.stderr.decode(errors='replace'))
 cases=('restore-write-sequence','missing-distributor','missing-interface','null-gic')
 for i,n in enumerate(cases):
  r=subprocess.run([str(exe),str(i)],capture_output=True,timeout=20);(o/f'case-{i}.log').write_bytes(r.stdout+r.stderr)
  if r.returncode:raise RuntimeError(n+' failed')
 d={'passed':True,'hardware_verified':False,'actual_pinned_branch_body':True,'callbacks_invoked_on_hardware':False,'cases':list(cases),'source_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'harness_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'generated_c_sha256':hashlib.sha256(src.read_bytes()).hexdigest(),'log_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in o.glob('*.log')}};(o/'result.json').write_text(json.dumps(d,indent=2)+'\n',encoding='utf-8')
if __name__=='__main__':main()
