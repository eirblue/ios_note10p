"""Run actual v42 backend with bounded synthetic register/lock stubs."""
import argparse,hashlib,json,subprocess
from pathlib import Path
from prepare_pmu_control_audit import PINS
STUB=r"""
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>
typedef uint32_t u32;typedef uint64_t u64;
#define MIDR_CPU_MODEL_MASK 0xff0ffff0U
#define MIDR_CORTEX_A55 0x410fd050U
#define MIDR_VARIANT(x) (((x)>>20)&15)
#define MIDR_REVISION(x) ((x)&15)
#define ARMV8_PMU_PMCR_N_SHIFT 11
#define ARMV8_PMU_PMCR_N_MASK 31
#define ARMV8_IDX_TO_COUNTER(x) (((x)-1)&31)
struct perf_event {int unused;};struct arm_pmu;
struct pmu_hw_events {unsigned long used_mask[1];int pmu_lock;};
struct arm_pmu {int num_events;struct pmu_hw_events *hw_events;unsigned long supported_cpus;void (*start)(struct arm_pmu *);void (*stop)(struct arm_pmu *);void (*reset)(void *);void (*enable)(struct perf_event *);void (*disable)(struct perf_event *);u32 (*read_counter)(struct perf_event *);void (*write_counter)(struct perf_event *,u32);};
struct n10_ctl_row {unsigned int index,chain_count,kind,num;u32 used_sw,visible_phys,used_phys;unsigned int current_el,model_match,variant,revision,pmuver,fgt;u32 pmcr,cntenset,intenset;};
static int depth=1,irq=1,intr,lock_busy,locked,idreads,controls,fail_nested;static u64 el=4,midr=0x411fd050,dfr=0x400,mmfr,pmcr,cnt,ints;
#define READ_ONCE(x) (x)
#define this_cpu_ptr(p) (p)
static int n10_pre_context(unsigned int g,int i,unsigned int p){return g==1 && irq && i==1 && (unsigned)depth==p && !(p==2 && fail_nested);}
static int in_interrupt(void){return intr;}
static int cpumask_test_cpu(int c,unsigned long *mask){return c==0 && (*mask&1);}
static int test_bit(int n,unsigned long *bits){return !!(*bits & (1UL<<n));}
static int raw_spin_trylock(int *p){if(lock_busy)return 0;if(*p||locked)abort();*p=1;locked=1;depth++;return 1;}
static void raw_spin_unlock(int *p){if(!*p||!locked||depth!=2)abort();*p=0;locked=0;depth--;}
static void armv8pmu_start(struct arm_pmu *p){(void)p;abort();}static void armv8pmu_stop(struct arm_pmu *p){(void)p;abort();}static void armv8pmu_reset(void *p){(void)p;abort();}
static void armv8pmu_enable_event(struct perf_event *p){(void)p;abort();}static void armv8pmu_disable_event(struct perf_event *p){(void)p;abort();}
static u32 armv8pmu_read_counter(struct perf_event *p){(void)p;abort();}static void armv8pmu_write_counter(struct perf_event *p,u32 v){(void)p;(void)v;abort();}
static u64 readreg(const char *name){
 if(!strcmp(name,"CurrentEL")){idreads++;return el;}if(!strcmp(name,"midr_el1")){idreads++;return midr;}if(!strcmp(name,"id_aa64dfr0_el1")){idreads++;return dfr;}if(!strcmp(name,"id_aa64mmfr0_el1")){idreads++;return mmfr;}
 if(!locked||depth!=2||!irq)abort();controls++;
 if(!strcmp(name,"pmcr_el0"))return pmcr;if(!strcmp(name,"pmcntenset_el0"))return cnt;if(!strcmp(name,"pmintenset_el1"))return ints;abort();
}
#define read_sysreg(name) readreg(#name)
"""
MAIN=r"""
static int audited(struct arm_pmu *p,struct n10_ctl_row *r,unsigned int g){
 struct arm_pmu old;struct pmu_hw_events hw;struct pmu_hw_events *ptr=p->hw_events;int ret;
 memcpy(&old,p,sizeof old);if(ptr)memcpy(&hw,ptr,sizeof hw);
 ret=n10_ctl_backend(p,r,g);
 if(memcmp(&old,p,sizeof old) || (ptr && memcmp(&hw,ptr,sizeof hw)))abort();
 return ret;
}
#define CHECK(x) do { if(!(x)) return __LINE__; } while(0)
int main(void){struct pmu_hw_events hw={0};struct arm_pmu p={0},before;struct pmu_hw_events oldhw;struct n10_ctl_row r;int ret;
 p.num_events=32;p.hw_events=&hw;p.supported_cpus=1;p.start=armv8pmu_start;p.stop=armv8pmu_stop;p.reset=armv8pmu_reset;p.enable=armv8pmu_enable_event;p.disable=armv8pmu_disable_event;p.read_counter=armv8pmu_read_counter;p.write_counter=armv8pmu_write_counter;
 hw.used_mask[0]=0x80000003UL;pmcr=31UL<<11;before=p;oldhw=hw;memset(&r,0,sizeof r);ret=audited(&p,&r,1);
 CHECK(!ret && idreads==4 && controls==3 && r.used_sw==0x80000003U && r.used_phys==0xc0000001U && r.visible_phys==0xffffffffU && !r.cntenset && !r.intenset);
 CHECK(!memcmp(&before,&p,sizeof p)&&!memcmp(&oldhw,&hw,sizeof hw)&&!locked&&depth==1&&irq);
 idreads=controls=0;mmfr=1ULL<<60;CHECK(audited(&p,&r,1)==-ENODEV && idreads==4 && controls==0);mmfr=1ULL<<56;idreads=controls=0;CHECK(audited(&p,&r,1)==-ENODEV && idreads==4 && controls==0);mmfr=0;
 idreads=controls=0;midr++;CHECK(audited(&p,&r,1)==-ENODEV && idreads==4 && controls==0);midr--;
 idreads=controls=0;dfr=0x500;CHECK(audited(&p,&r,1)==-ENODEV && controls==0);dfr=0x400;
 idreads=controls=0;el=8;CHECK(audited(&p,&r,1)==-ENODEV && controls==0);el=4;
 idreads=controls=0;lock_busy=1;CHECK(audited(&p,&r,1)==-EBUSY && controls==0 && depth==1 && irq);lock_busy=0;fail_nested=1;controls=0;CHECK(audited(&p,&r,1)==-EPERM && controls==0 && depth==1 && !locked && irq);fail_nested=0;
 idreads=controls=0;pmcr=0;CHECK(audited(&p,&r,1)==-EIO && controls==1 && depth==1 && !locked);pmcr=1ULL<<32;
 controls=0;CHECK(audited(&p,&r,1)==-EIO && controls==1 && depth==1 && !locked);pmcr=31UL<<11;
 controls=0;cnt=1ULL<<32;CHECK(audited(&p,&r,1)==-EIO && controls==3 && depth==1 && !locked);cnt=0;ints=1ULL<<32;controls=0;CHECK(audited(&p,&r,1)==-EIO && controls==3 && depth==1 && !locked);ints=0;
 controls=0;p.start=0;CHECK(audited(&p,&r,1)==-ENODEV && controls==0);p.start=armv8pmu_start;p.supported_cpus=0;controls=0;idreads=0;CHECK(audited(&p,&r,1)==-EINVAL && controls==0 && idreads==0);p.supported_cpus=1;p.hw_events=0;controls=0;idreads=0;CHECK(audited(&p,&r,1)==-EINVAL && controls==0 && idreads==0);p.hw_events=&hw;
 controls=0;p.num_events=0;CHECK(audited(&p,&r,1)==-EINVAL && controls==0);p.num_events=33;CHECK(audited(&p,&r,1)==-EINVAL && controls==0);p.num_events=1;pmcr=0;hw.used_mask[0]=1;memset(&r,0,sizeof r);controls=0;CHECK(!audited(&p,&r,1) && controls==3 && r.used_phys==0x80000000U && r.visible_phys==0x80000000U);
 controls=0;irq=0;CHECK(audited(&p,&r,1)==-EPERM && controls==0);CHECK(depth==1 && !locked);
 return 0;}
"""
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--source',required=True);ap.add_argument('--cc',required=True);ap.add_argument('--output',required=True);a=ap.parse_args();out=Path(a.output);out.mkdir(parents=True,exist_ok=False)
 root=Path(a.source).parents[3]
 pin_names=('arch/arm64/kernel/perf_event.c','arch/arm64/include/asm/perf_event.h','arch/arm64/include/asm/cputype.h')
 for n in pin_names:
  raw=(root/n).read_bytes()
  if n=='arch/arm64/kernel/perf_event.c':
   suffix=b'\n#ifdef CONFIG_NOTE10_PMU_CONTROL_AUDIT\n#include "note10_pmu_control_backend.c"\n#endif\n'
   if not raw.endswith(suffix):raise ValueError('backend include differs')
   raw=raw[:-len(suffix)]
  if hashlib.sha256(raw).hexdigest()!=PINS[n]:raise ValueError('backend pin differs: '+n)
 asm=(root/'arch/arm64/include/asm/perf_event.h').read_text();cpu=(root/'arch/arm64/include/asm/cputype.h').read_text()
 if not all(x in asm for x in ('ARMV8_PMU_MAX_COUNTERS\t32','ARMV8_PMU_PMCR_N_SHIFT\t11','ARMV8_PMU_PMCR_N_MASK\t0x1f')) or 'ARM_CPU_PART_CORTEX_A55' not in cpu or 'MIDR_CPU_MODEL_MASK' not in cpu:raise ValueError('pinned constants differ')
 helper=Path(a.source).read_text(encoding='utf8');helper='\n'.join(x for x in helper.splitlines() if not x.startswith('#include'));src=out/'native.c';src.write_text(STUB+'\n'+helper+'\n'+MAIN,encoding='utf8',newline='\n');exe=out/'native.exe'
 c=subprocess.run([a.cc,'-std=gnu11','-Wall','-Wextra','-Werror',str(src),'-o',str(exe)],capture_output=True);(out/'compile.log').write_bytes(c.stdout+c.stderr)
 if c.returncode:raise RuntimeError(c.stderr.decode(errors='replace'))
 r=subprocess.run([str(exe)],capture_output=True);(out/'run.log').write_bytes(r.stdout+r.stderr)
 if r.returncode:raise RuntimeError('backend model failed at line '+str(r.returncode))
 result={'passed':True,'hardware_verified':False,'input_objects_unchanged_every_call':True,'pinned_sha256':{n:PINS[n] for n in pin_names},'cases':['count32-map','no-input-mutation','mmfr-high','fgt-nonzero','wrong-midr','wrong-pmuver','wrong-el','lock-busy','nested-context','pmcr-n','pmcr-width','enable-width','interrupt-width','wrong-backend','unsupported-cpu','null-hw','count0','count33','count1-map','bad-context'],'helper_sha256':hashlib.sha256(Path(a.source).read_bytes()).hexdigest(),'harness_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'generated_sha256':hashlib.sha256(src.read_bytes()).hexdigest()}
 (out/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8',newline='\n')
if __name__=='__main__':main()
