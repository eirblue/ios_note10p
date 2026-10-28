"""Native source model of GIC save, restore, notifier and init; hardware stubbed."""
import argparse,hashlib,json,subprocess,sys
from pathlib import Path
from test_fsys_pm_native import function
STUB=r"""
#include <stdint.h>
#include <stddef.h>
#include <stdbool.h>
#include <stdlib.h>
#include <stdio.h>
#include <string.h>
typedef uint32_t u32;
#define __iomem
#define __percpu
#define CONFIG_ARM_GIC_MAX_NR 1
#define CPU_PM_ENTER 1
#define CPU_PM_EXIT 2
#define CPU_PM_ENTER_FAILED 3
#define CPU_CLUSTER_PM_ENTER 4
#define CPU_CLUSTER_PM_ENTER_FAILED 5
#define CPU_CLUSTER_PM_EXIT 6
#define NOTIFY_OK 1
#define ENOMEM 12
#define WARN_ON(x) (x)
#define pr_warn_once(...) ((void)0)
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
struct n10_gic_priority {u32 words[8];bool valid,pending;};
struct gic_chip_data {u32 *saved_ppi_enable,*saved_ppi_active,*saved_ppi_conf;struct n10_gic_priority *n10_priority;};
struct notifier_block {int (*notifier_call)(struct notifier_block*,unsigned long,void*);};
static struct gic_chip_data gic_data[1];
static int cpu,irqoff=1,base_mode,alloc_calls,alloc_fail,free_calls,registered,ups,writes,reads;static void *allocated[16],*freed[16];
static u32 db[1024],cb[1024],trace_address[64],trace_value[64],read_address[64];
#define raw_cpu_ptr(p) _Generic((p),struct n10_gic_priority*:((p)+cpu),default:(p))
#define per_cpu_ptr(p,c) ((p)+(c))
#define for_each_possible_cpu(c) for((c)=0;(c)<2;(c)++)
static int irqs_disabled(void){return irqoff;}
static void *gic_data_dist_base(struct gic_chip_data *g){(void)g;return base_mode==1?NULL:db;}
static void *gic_data_cpu_base(struct gic_chip_data *g){(void)g;return base_mode==2?NULL:cb;}
static u32 readl_relaxed(void *p){uintptr_t q=(uintptr_t)p,lo=(uintptr_t)db,hi=(uintptr_t)(db+1024);if(q<lo || q>=hi || reads>=64)abort();read_address[reads++]=(u32)(q-lo);printf("read:%u\n",read_address[reads-1]);return *(u32*)p;}
static void writel_relaxed(u32 v,void *p){if(writes>=64)abort();trace_address[writes]=((uintptr_t)p>=(uintptr_t)db && (uintptr_t)p<(uintptr_t)(db+1024))?(u32)((uintptr_t)p-(uintptr_t)db):0x10000+(u32)((uintptr_t)p-(uintptr_t)cb);trace_value[writes++]=v;printf("write:%u:%u\n",trace_address[writes-1],v);*(u32*)p=v;}
static void gic_cpu_if_up(struct gic_chip_data *g){(void)g;ups++;puts("interface-up");}
static void gic_dist_save(struct gic_chip_data *g){(void)g;abort();}
static void gic_dist_restore(struct gic_chip_data *g){(void)g;abort();}
static void *allocate(size_t n){void *p;alloc_calls++;if(alloc_calls>16)abort();if(alloc_calls==alloc_fail)return NULL;p=malloc(2*n);if(p)memset(p,0xa5,2*n);allocated[alloc_calls-1]=p;return p;}
#define __alloc_percpu(n,a) allocate(n)
#define alloc_percpu(t) ((t*)allocate(sizeof(t)))
static void free_percpu(void *p){if(free_calls>=16)abort();freed[free_calls++]=p;free(p);}
static int cpu_pm_register_notifier(struct notifier_block *n){(void)n;registered++;puts("register");return 0;}
"""
MAIN=r"""
#define CHECK(x) do {if(!(x)){fprintf(stderr,"line %d\n",__LINE__);return 1;}} while(0)
static void reset_regs(void){int i;memset(db,0,sizeof(db));memset(cb,0,sizeof(cb));db[GIC_DIST_ENABLE_SET/4]=5;db[GIC_DIST_ACTIVE_SET/4]=6;db[GIC_DIST_CONFIG/4]=7;db[GIC_DIST_CONFIG/4+1]=8;for(i=0;i<8;i++)db[GIC_DIST_PRI/4+i]=0x10203040U+(u32)i;writes=ups=reads=0;}
static int verify(u32 *priority){int i;u32 addr[]={0x180,0x100,0x380,0x300,0xc00,0xc04,0x400,0x404,0x408,0x40c,0x410,0x414,0x418,0x41c,0x10004};u32 values[]={0xffffffff,5,0xffffffff,6,7,8};CHECK(writes==15 && ups==1);for(i=0;i<15;i++){CHECK(trace_address[i]==addr[i]);if(i<6)CHECK(trace_value[i]==values[i]);else if(i<14)CHECK(trace_value[i]==priority[i-6]);else CHECK(trace_value[i]==0xf0);}return 0;}
int main(int argc,char **argv){int mode=atoi(argv[1]),i,r;u32 old[8],expected[8];struct gic_chip_data *g=&gic_data[0];
 if(mode>=12 && mode<=15){alloc_fail=mode-11;r=gic_pm_init(g);
#ifdef CONFIG_NOTE10_GIC_PRIORITY_RESTORE
  CHECK(r==-ENOMEM && !registered && free_calls==alloc_fail-1);for(i=0;i<free_calls;i++)CHECK(freed[i]==allocated[alloc_fail-2-i]);
#else
  if(alloc_fail<=3){CHECK(r==-ENOMEM && !registered && free_calls==alloc_fail-1);for(i=0;i<free_calls;i++)CHECK(freed[i]==allocated[alloc_fail-2-i]);}else CHECK(r==0 && registered==1);
#endif
  return 0;}
 CHECK(gic_pm_init(g)==0 && registered==1);
#ifdef CONFIG_NOTE10_GIC_PRIORITY_RESTORE
 {struct n10_gic_priority zero={0};CHECK(!memcmp(&g->n10_priority[0],&zero,sizeof(zero)) && !memcmp(&g->n10_priority[1],&zero,sizeof(zero)));}
#endif
 reset_regs();for(i=0;i<8;i++){if(mode==2)db[GIC_DIST_PRI/4+i]=0;if(mode==3)db[GIC_DIST_PRI/4+i]=GICD_INT_DEF_PRI_X4;old[i]=db[GIC_DIST_PRI/4+i];expected[i]=GICD_INT_DEF_PRI_X4;}
 if(mode==4)base_mode=1;gic_notifier(NULL,CPU_PM_ENTER,NULL);if(mode==4){CHECK(!writes && !reads);return 0;}
 if(mode==0 || mode==1){u32 expected_reads[]={0x100,0x300,0xc00,0xc04};for(i=0;i<4;i++)CHECK(read_address[i]==expected_reads[i]);
#ifdef CONFIG_NOTE10_GIC_PRIORITY_RESTORE
  CHECK(reads==12);for(i=0;i<8;i++)CHECK(read_address[4+i]==0x400+4*i);
#else
  CHECK(reads==4);
#endif
 }
 if(mode==7)gic_notifier(NULL,CPU_PM_ENTER,NULL);
 if(mode==16){base_mode=1;gic_cpu_save(g);base_mode=0;}
 if(mode==17)irqoff=0;
 if(mode==5){int before_reads=reads;base_mode=2;gic_notifier(NULL,CPU_PM_EXIT,NULL);CHECK(!writes && reads==before_reads);base_mode=0;}
 if(mode==6){
#ifdef CONFIG_NOTE10_GIC_PRIORITY_RESTORE
 free(g->n10_priority);g->n10_priority=NULL;
#endif
 }
 if(mode==9){u32 other_expected[8];cpu=1;reset_regs();for(i=0;i<8;i++){db[GIC_DIST_PRI/4+i]=0x99887700U+i;other_expected[i]=GICD_INT_DEF_PRI_X4;}gic_cpu_save(g);
#ifdef CONFIG_NOTE10_GIC_PRIORITY_RESTORE
  for(i=0;i<8;i++)other_expected[i]=0x99887700U+i;
#endif
  writes=ups=0;gic_cpu_restore(g);CHECK(!verify(other_expected));cpu=0;reset_regs();}
 if(mode==10){struct gic_chip_data other={0};u32 other_expected[8];CHECK(gic_pm_init(&other)==0);reset_regs();for(i=0;i<8;i++){db[GIC_DIST_PRI/4+i]=0x88776600U+i;other_expected[i]=GICD_INT_DEF_PRI_X4;}gic_cpu_save(&other);
#ifdef CONFIG_NOTE10_GIC_PRIORITY_RESTORE
  for(i=0;i<8;i++)other_expected[i]=0x88776600U+i;
#endif
  writes=ups=0;gic_cpu_restore(&other);CHECK(!verify(other_expected));reset_regs();}
 for(i=0;i<8;i++)db[GIC_DIST_PRI/4+i]=0x55555555U;writes=ups=0;
#ifdef CONFIG_NOTE10_GIC_PRIORITY_RESTORE
 if(mode!=5 && mode!=6 && mode!=7 && mode!=16 && mode!=17)for(i=0;i<8;i++)expected[i]=old[i];
#endif
 {int prior_reads=reads;gic_notifier(NULL,mode==1?CPU_PM_ENTER_FAILED:CPU_PM_EXIT,NULL);CHECK(reads==prior_reads);}CHECK(!verify(expected));
 if(mode==8){for(i=0;i<8;i++)expected[i]=GICD_INT_DEF_PRI_X4;writes=ups=0;gic_cpu_restore(g);CHECK(!verify(expected));}
 if(mode==11){base_mode=1;gic_cpu_restore(g);CHECK(writes==15);}
 return 0;}
"""
CASES=('exit-nondefault','failed-nondefault','zero-priorities','default-priorities','save-missing-base','restore-missing-base','missing-allocation','duplicate-enter','single-consumption','cpu-isolation','gic-isolation','unmatched-missing-base','alloc-enable-failure','alloc-active-failure','alloc-conf-failure','alloc-priority-failure','save-missing-clears-stale','irq-on-fallback')
def generate(raw,helper):
 return STUB+function(raw,'void gic_cpu_save(')+function(raw,'void gic_cpu_restore(')+function(raw,'static int gic_notifier(')+"\nstatic struct notifier_block gic_notifier_block={gic_notifier};\n"+function(raw,'static int gic_pm_init(')+MAIN
# Helpers must precede the extracted save and restore functions.
def source(raw,helper):return STUB+'\n#ifdef CONFIG_NOTE10_GIC_PRIORITY_RESTORE\n'+helper+'\n#endif\n'+generate(raw,helper)[len(STUB):]
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--source',required=True);ap.add_argument('--helper',required=True);ap.add_argument('--baseline',required=True);ap.add_argument('--output',required=True);a=ap.parse_args();p=Path(a.source);h=Path(a.helper);out=Path(a.output);out.mkdir(parents=True,exist_ok=False);raw=p.read_text(encoding='utf8');code=source(raw,h.read_text(encoding='utf8'));cc=Path('host-tools/windows-build/llvm-mingw/llvm-mingw-20261006-ucrt-x86_64/bin/clang.exe') if sys.platform=='win32' else 'cc'
 for mode in ('orig','off','on'):
  selected=source(Path(a.baseline).read_text(encoding='utf8'),h.read_text(encoding='utf8')) if mode=='orig' else code
  c=out/(mode+'.c');c.write_text(selected,encoding='utf8');exe=out/(mode+('.exe' if sys.platform=='win32' else ''));args=[str(cc),'-std=gnu11',str(c),'-o',str(exe)];
  if mode=='on':args.insert(1,'-DCONFIG_NOTE10_GIC_PRIORITY_RESTORE')
  r=subprocess.run(args,capture_output=True,timeout=60);(out/(mode+'-compile.log')).write_bytes(r.stdout+r.stderr)
  if r.returncode:raise RuntimeError(r.stderr.decode(errors='replace'))
  for i in range(len(CASES)):
   r=subprocess.run([str(exe),str(i)],capture_output=True,timeout=20);(out/(mode+'-'+str(i)+'.log')).write_bytes(r.stdout+r.stderr)
   if r.returncode:raise RuntimeError(mode+' '+CASES[i]+': '+r.stderr.decode(errors='replace'))
 for i in range(len(CASES)):
  if (out/('orig-'+str(i)+'.log')).read_bytes()!=(out/('off-'+str(i)+'.log')).read_bytes():raise ValueError('original/final-off trace differs: '+CASES[i])
 result={'passed':True,'hardware_verified':False,'original_off_traces_equal':True,'baseline_sha256':hashlib.sha256(Path(a.baseline).read_bytes()).hexdigest(),'cases':{'orig':list(CASES),'off':list(CASES),'on':list(CASES)},'source_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'helper_sha256':hashlib.sha256(h.read_bytes()).hexdigest(),'harness_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'generated_sha256':{x.name:hashlib.sha256(x.read_bytes()).hexdigest() for x in out.glob('*.c')},'log_sha256':{x.name:hashlib.sha256(x.read_bytes()).hexdigest() for x in out.glob('*.log')}};(out/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8')
if __name__=='__main__':main()
