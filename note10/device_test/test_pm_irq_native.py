"""Execute actual CPU0 IRQ transaction and GIC read-only observer with faults."""
import argparse,hashlib,json,re,shutil,subprocess,sys
from pathlib import Path
from run_probe import ROOT
from decode_pm_irq import decode
HERE=Path(__file__).resolve().parent
STUB=r'''
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h>
#include <errno.h>
typedef uint64_t u64;typedef uint32_t u32;
#define __iomem
#define N10_RESERVE_BUILD_ID "0123456789abcdef0123456789abcdef"
#define pr_info printf
#define PSR_I_BIT 0x80UL
#define PM_SUSPEND_MEM 1
#define GIC_CPU_CTRL 0
#define GIC_CPU_PRIMASK 4
#define GIC_CPU_BINPOINT 8
#define GIC_CPU_IDENT 0xfc
#define GIC_DIST_CTRL 0
#define GIC_DIST_CTR 4
static unsigned int mode,owner=1,irq,preempt,save_count,restore_count,disable_count,enable_count,phase,read_count,pm_mutex;
static unsigned long online=1,daif=0x140;
static unsigned int cpu_bank[64]={ [0]=1,[1]=128,[2]=2,[63]=0x20243b },dist_bank[2]={1,0x467};
static struct {void *domain;} gic_data[1];
static struct {unsigned int qgeneration;} active;
static typeof(active) *n10_pm_active=&active;
static int n10_pm_noirq_ready(int state){return owner && state==1 && !irq;}
static unsigned int raw_smp_processor_id(void){return (mode==4 || mode==61)?1:0;}
static unsigned int num_online_cpus(void){return (mode==3 || mode==62)?2:1;}
#define cpu_online_mask (&online)
#define cpumask_bits(p) (p)
static unsigned int preempt_count(void){return preempt;}
static int irqs_disabled(void){return irq;}
static int preemptible(void){return preempt==0 && !irq;}
static void preempt_disable(void){if(preempt++ || disable_count++)abort();}
static void preempt_enable(void){if(!preempt || enable_count++)abort();--preempt;if(mode==20)++preempt;}
#define local_irq_save(f) do {if(irq || preempt!=1 || save_count++)abort();(f)=daif^(mode==14?1:0);irq=mode==25?0:1;daif|=PSR_I_BIT;phase=1;} while(0)
#define local_irq_restore(f) do {if(restore_count++ || preempt!=1)abort();daif=(f);if(mode==13)daif^=PSR_I_BIT;irq=!!(daif&PSR_I_BIT);phase=2;} while(0)
static void *gic_data_cpu_base(void*d){return (mode==6 || (mode==22 && phase==1) || (mode==23 && phase==2))?NULL:cpu_bank;}
static void *gic_data_dist_base(void*d){return mode==7?NULL:dist_bank;}
static unsigned int readl_relaxed(void *p){
 unsigned int index,i,*q=p;void *allowed[]={ (char *)cpu_bank+GIC_CPU_CTRL,(char *)cpu_bank+GIC_CPU_PRIMASK,
  (char *)cpu_bank+GIC_CPU_BINPOINT,(char *)cpu_bank+GIC_CPU_IDENT,(char *)dist_bank+GIC_DIST_CTRL,(char *)dist_bank+GIC_DIST_CTR };
 if(preempt!=1 || irq!=(phase==1))abort();++read_count;
 for(i=0;i<6 && p!=allowed[i];++i){} if(i==6)abort();index=i;
 if(mode==12 && phase==1 && index==2)return *q+1;
 if(mode==16 && phase==2 && index==3)return *q+1;
 if(mode>=41 && mode<53 && phase==1+(mode-41)/6 && index==(mode-41)%6)return *q^1;
 return *q;
}
static u64 regs(unsigned int reg){
 static const u64 values[]={0,4,0x80000000,0x1005,0x11,0x1234000012345000ULL,0xff,0xb6,26000000};
 u64 v=reg?values[reg]:daif;
 if(mode==11 && phase==1 && reg==1)v=0;
 if((mode==15 || mode==22) && phase==2 && reg==4)v++;
 if(mode==21 && phase==0 && reg==1)v=0;
 if(mode>=27 && mode<41 && phase==1+(mode-27)/7 && reg==2+(mode-27)%7)v^=1;
 return v;
}
#define daif_reg 0
#define CurrentEL 1
#define mpidr_el1 2
#define sctlr_el1 3
#define tcr_el1 4
#define ttbr1_el1 5
#define mair_el1 6
#define cntkctl_el1 7
#define cntfrq_el0 8
#define read_sysreg(r) regs(r##_reg)
#define CurrentEL_reg CurrentEL
#define mpidr_el1_reg mpidr_el1
#define sctlr_el1_reg sctlr_el1
#define tcr_el1_reg tcr_el1
#define ttbr1_el1_reg ttbr1_el1
#define mair_el1_reg mair_el1
#define cntkctl_el1_reg cntkctl_el1
#define cntfrq_el0_reg cntfrq_el0
static void mutex_lock(unsigned int *p){if((*p)++)abort();}
static void mutex_unlock(unsigned int *p){if(!*p)abort();--*p;}
'''
MAIN=r'''
int main(int argc,char**argv){
 int error;unsigned int gen;struct n10_pm_irq_sample out,old;
 mode=atoi(argv[1]);gen=(mode==19 || mode==55)?0xffffffffU:mode==54?2:1;active.qgeneration=gen;
 if(mode>=58 && mode<=63){
  struct n10_irq_gic_sample sample={0};int r;gic_data[0].domain=dist_bank;preempt=1;
  if(mode==58)r=n10_irq_gic_capture(0,NULL);
  else if(mode==59){r=n10_irq_gic_capture(0,&sample);if(r || read_count!=6)abort();r=n10_irq_gic_capture(0,&sample);}
  else {if(mode==63)online=3;r=n10_irq_gic_capture(mode==60?1:0,&sample);}
  if(!r || (mode!=59 && read_count))abort();printf("standalone=%d reads=%u\n",r,read_count);return 0;
 }
 gic_data[0].domain=mode==5?NULL:dist_bank;if(mode==1)owner=0;if(mode==2)preempt=1;
 if(mode==8)cpu_bank[0]=0;if(mode==9)cpu_bank[1]=0;if(mode==10)dist_bank[0]=0;
 if(mode==24)gen=active.qgeneration=0;
 error=n10_pm_irq_capture(gen);
 if(mode==17){if(error)abort();error=n10_pm_irq_capture(gen);}
 if(mode==18 || mode==54 || mode==56 || mode==57){
  if(error)abort();old=n10_pm_irq_last;owner=mode==18?0:1;active.qgeneration=mode==54?1:2;if(mode==57)online=3;
  save_count=restore_count=disable_count=enable_count=0;error=n10_pm_irq_capture(mode==56?3:active.qgeneration);old.bad=1;
  if(!error || memcmp(&n10_pm_irq_last,&old,sizeof(old)) || save_count || restore_count || disable_count || enable_count)abort();
 }
 if(mode==53 || mode==55){
  if(error)abort();save_count=restore_count=disable_count=enable_count=0;phase=0;active.qgeneration=mode==55?1:2;
  error=n10_pm_irq_capture(active.qgeneration);if(error || n10_pm_irq_last.generation!=active.qgeneration || n10_pm_irq_read(&out,active.qgeneration+1))abort();
 }
 if(mode==26){struct n10_irq_gic_sample x={0};if(n10_irq_gic_capture(3,&x)!=-EINVAL)abort();error=-EIO;}
 if(mode!=2 && mode!=20 && preempt)abort();
 if(save_count!=restore_count || save_count>1 || disable_count!=enable_count || disable_count>1)abort();
 if(((mode>=27 && mode<53) || mode==11 || mode==12 || mode==13 || mode==14 || mode==15 || mode==16 || mode==20 || mode==22 || mode==23 || mode==25) && (save_count!=1 || restore_count!=1))abort();
 if((mode==1 || mode==2 || mode==3 || mode==4 || mode==5 || mode==6 || mode==7 || mode==8 || mode==9 || mode==10 || mode==21 || mode==24) && save_count)abort();
 if(mode==0 && (error || read_count!=18 || n10_pm_irq_read(&out,2)))abort();
 if(mode==19 && (error || n10_pm_irq_read(&out,1)))abort();
 if(mode==22 && n10_pm_irq_last.error!=-ENODEV)abort();
 if(mode==0 || mode==19)if(n10_report_pm_irq(mode==19?1:2))abort();
 if(mode==11)n10_report_pm_irq_failure(2);
 if(mode!=0 && mode!=19 && mode!=53 && mode!=55 && !error)abort();
 printf("result=%d save=%u restore=%u reads=%u\n",error,save_count,restore_count,read_count);return 0;
}
'''
def run(output):
 out=Path(output).resolve()
 if out.exists() or not out.is_relative_to((ROOT/'note10/private').resolve()):raise ValueError('fresh private model directory required')
 out.mkdir(parents=True);names=('pm_irq_contract.h','pm_irq_backend.c','pm_irq_gic_backend.c','pm_irq_probe.c');raw={n:(HERE/n).read_bytes() for n in names}
 clean=lambda s:re.sub(r'^#include[^\n]*\n','',s,flags=re.M)
 checksum=re.search(r'static u32 n10_frame_checksum[^}]+}',(HERE/'xnu_reserve.c').read_text()).group()
 src=out/'irq.c';src.write_text(STUB+clean(raw[names[0]].decode())+clean(raw[names[2]].decode())+clean(raw[names[1]].decode())+checksum+clean(raw[names[3]].decode())+MAIN,encoding='utf-8')
 compiler=ROOT/'host-tools/windows-build/llvm-mingw/llvm-mingw-20261006-ucrt-x86_64/bin/clang.exe' if sys.platform=='win32' else shutil.which('cc')
 exe=out/('irq.exe' if sys.platform=='win32' else 'irq');p=subprocess.run([str(compiler),'-std=gnu11','-O2',str(src),'-o',str(exe)],capture_output=True,timeout=60);(out/'compile.log').write_bytes(p.stdout+p.stderr)
 if p.returncode:raise ValueError('actual IRQ/GIC C compilation failed')
 rows=[]
 for mode in range(64):
  p=subprocess.run([str(exe),str(mode)],capture_output=True,timeout=15);(out/f'mode-{mode}.log').write_bytes(p.stdout+p.stderr)
  if p.returncode:raise ValueError('IRQ/GIC invariant failed: '+str(mode))
  if mode in (0,19):
   baseline={'cpus':{0:{'snapshot':{'mpidr':0x80000000,'sctlr':0x1005,'tcr':0x11,'ttbr1':0x1234000012345000,'mair':0xff}}}}
   timers={'cpus':{0:{'after':0xb6,'freq':26000000}}}
   if not decode(p.stdout.decode(),'0123456789abcdef0123456789abcdef',1 if mode==19 else 2,baseline,timers)['cpu0_irq_arch_timer']:raise ValueError('actual IRQ producer decode failed')
  rows.append({'mode':mode,'passed':True,'accepted':mode in (0,19,53,55)})
 result={'passed':True,'cases':len(rows),'outcomes':rows,'actual_irq_transaction_executed':True,'actual_gic_observer_executed':True,'actual_producer_executed':True,'strict_decoder_verified':True,'exact_read_allowlist':True,'no_gic_writes':True,'hardware_verified':False,'source_sha256':{n:hashlib.sha256(x).hexdigest() for n,x in raw.items()},'harness_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
 (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');return result
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);r=run(p.parse_args().output);print(json.dumps({'passed':r['passed'],'cases':r['cases']}))
