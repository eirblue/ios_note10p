"""Compile and run the exact EHLD update function with irqsave-token mocks."""
import argparse,hashlib,json,subprocess,tempfile
from pathlib import Path
from prepare_ehld_irqsave_audit import TARGET,transform_function
DAIF_NONIRQ=(0,0x40,0x100,0x140,0x200,0x240,0x300,0x340)
CASES=('original_irqon_rejected','wrong_main_token_inner_rejected','sjtag_no_locks','empty_unlocks_outer','one_irqon','many_irqon','offline_branch','poweroff_branch','not_running_branch','mmio_branch','empty_irqoff','one_irqoff','many_irqoff','other_daif_bits','no_event_any_cpu',*(f'daif_i{irq}_{bits:03x}' for bits in DAIF_NONIRQ for irq in (0,1)))

def sha(b):return hashlib.sha256(b).hexdigest()
def extract(raw):
    transformed=transform_function(raw)
    start=transformed.index(b'void exynos_ehld_event_raw_update_allcpu(void)'); brace=transformed.index(b'{',start);d=0
    for i in range(brace,len(transformed)):
        if transformed[i:i+1]==b'{':d+=1
        elif transformed[i:i+1]==b'}':
            d-=1
            if not d:return transformed[start:i+1].decode()
    raise ValueError('unclosed function')
def harness(fn,mode):
    if mode=='wrong': fn=fn.replace('raw_spin_unlock_irqrestore(&ctrl->lock, ctrl_flags);','raw_spin_unlock_irqrestore(&ctrl->lock, main_flags);')
    return r'''#include <stdint.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdarg.h>
#include <stdlib.h>
#define MAXCPU 8
#define NUM_TRACE 4
#define PMU_OFFSET 0x100
#define PMUPCSR 0x20
#define MSB_MASKING 0x8000000000000000ULL
#define MSB_PADDING 0x100000000ULL
#define IRQ_BIT 0x80UL
struct exynos_ehld_data { unsigned data_ptr; unsigned long long time[NUM_TRACE],event[NUM_TRACE],pmpcsr[NUM_TRACE]; };
struct exynos_ehld_ctrl { int event,ehld_running; unsigned long dbg_base; struct exynos_ehld_data data; struct { int held; } lock; };
struct { int held; } ehld_main_lock;
struct { struct { int held; } lock; } ehld_main;
struct exynos_ehld_ctrl ehld_ctrl[MAXCPU];
static unsigned long daif,entry_state; static int ncpu=3,sjtag,offline[MAXCPU],power[MAXCPU],mmio_reads,lock_order,unlock_order,preempt_depth,pc_depth,failures;
static int dbg_snapshot_get_sjtag_status(void){return sjtag;}
#define per_cpu_ptr(p,c) ((struct exynos_ehld_ctrl *)(p)+(c))
static int cpu_is_offline(int c){return offline[c];}
static struct { int (*power_state)(int); } exynos_cpu;
static int mock_power(int c){return power[c];}
static unsigned long long cpu_clock(int c){return (unsigned long long)c+9;}
static void __raw_readq(unsigned long a){(void)a;mmio_reads++;}
static unsigned long long readq(unsigned long a){(void)a;mmio_reads++;return 0x1234;}
static unsigned long readl(unsigned long a){(void)a;mmio_reads++;return 0x55;}
#define __raw_readq(a) readq(a)
#define __raw_readl(a) readl(a)
static int any_ctrl_held(void){int j;for(j=0;j<MAXCPU;j++)if(ehld_ctrl[j].lock.held)return 1;return 0;}
#define raw_spin_lock_irqsave(l,f) do { if ((void *)(l)==(void *)&ehld_main.lock) { if (ehld_main.lock.held || any_ctrl_held() || preempt_depth!=0 || pc_depth!=0) failures++; } else { if (!ehld_main.lock.held || (l)->held || preempt_depth!=1 || pc_depth!=1) failures++; } (f)=daif; daif|=IRQ_BIT; (l)->held=1; lock_order++; preempt_depth++; pc_depth++; if ((void *)(l)!=(void *)&ehld_main.lock && (preempt_depth!=2 || pc_depth!=2)) failures++; if ((void *)(l)==(void *)&ehld_main.lock && (preempt_depth!=1 || pc_depth!=1)) failures++; } while(0)
#define raw_spin_unlock_irqrestore(l,f) do { if(!(l)->held) failures++; if ((void *)(l)==(void *)&ehld_main.lock) { if (any_ctrl_held() || preempt_depth!=1 || pc_depth!=1) failures++; } else { if (!ehld_main.lock.held || preempt_depth!=2 || pc_depth!=2) failures++; } (l)->held=0; unlock_order++; preempt_depth--; pc_depth--; daif=(f); if ((void *)(l)!=(void *)&ehld_main.lock) { if (!ehld_main.lock.held || any_ctrl_held() || preempt_depth!=1 || pc_depth!=1 || daif!=(entry_state|IRQ_BIT)) failures++; } else { if (ehld_main.lock.held || any_ctrl_held() || preempt_depth!=0 || pc_depth!=0 || daif!=entry_state) failures++; } } while(0)
#define for_each_possible_cpu(c) for((c)=0;(c)<ncpu;(c)++)
#define DBG_UNLOCK(a) do{(void)(a);}while(0)
#define DBG_LOCK(a) do{(void)(a);}while(0)
static void ehld_printk(int x,const char *f,...){(void)x;(void)f; if(ehld_main.lock.held && (!(daif&IRQ_BIT) || daif!=(entry_state|IRQ_BIT) || preempt_depth<1 || preempt_depth>2 || pc_depth!=preempt_depth)) failures++;}
''' + fn + r'''
int main(int argc,char **argv){
 int id=argc>1?atoi(argv[1]):-1,i,expected_locks=0,expected_mmio=0; unsigned long entry=0x35UL;
 for(i=0;i<MAXCPU;i++){ehld_ctrl[i].event=0;ehld_ctrl[i].ehld_running=1;power[i]=1;}
 ncpu=3; daif=entry;
 switch(id){
 case 0: ehld_ctrl[0].event=1; expected_locks=-1;break; /* original body must fail IRQ-on checks */
 case 1: ehld_ctrl[0].event=1; expected_locks=-1;break; /* wrong inner token must fail */
 case 2: sjtag=1;break;
 case 3: ncpu=0;expected_locks=1;break;
 case 4: ehld_ctrl[0].event=1;expected_locks=2;expected_mmio=2;break;
 case 5: for(i=0;i<3;i++)ehld_ctrl[i].event=1;expected_locks=4;expected_mmio=6;break;
 case 6: ehld_ctrl[0].event=1;offline[0]=1;expected_locks=2;break;
 case 7: ehld_ctrl[0].event=1;power[0]=0;expected_locks=2;break;
 case 8: ehld_ctrl[0].event=1;ehld_ctrl[0].ehld_running=0;expected_locks=2;break;
 case 9: ehld_ctrl[0].event=1;expected_locks=2;expected_mmio=2;break;
 case 10: daif=IRQ_BIT|0x35UL;ncpu=0;expected_locks=1;break;
 case 11: daif=IRQ_BIT|0x35UL;ehld_ctrl[0].event=1;expected_locks=2;expected_mmio=2;break;
 case 12: daif=IRQ_BIT|0x35UL;for(i=0;i<3;i++)ehld_ctrl[i].event=1;expected_locks=4;expected_mmio=6;break;
 case 13: daif=IRQ_BIT|0x15;ehld_ctrl[0].event=1;expected_locks=2;expected_mmio=2;break;
 case 14: expected_locks=1;break; /* three possible CPUs, no eligible event */
 default: if(id>=15 && id<31){static const unsigned long ds[16]={0x000UL,0x080UL,0x040UL,0x0c0UL,0x100UL,0x180UL,0x140UL,0x1c0UL,0x200UL,0x280UL,0x240UL,0x2c0UL,0x300UL,0x380UL,0x340UL,0x3c0UL};int k=id-15;daif=ds[k];ehld_ctrl[0].event=1;expected_locks=2;expected_mmio=2;}else return 8;
 }
 entry_state=daif; exynos_cpu.power_state=mock_power; exynos_ehld_event_raw_update_allcpu();
 if(id==0||id==1){if(failures==0 && daif==entry)return 1; printf("PASS expected rejection: failures=%d daif=%lx\\n",failures,daif); return 0;}
 if(lock_order!=expected_locks || unlock_order!=expected_locks || mmio_reads!=expected_mmio || preempt_depth || pc_depth || daif!=entry_state || ehld_main.lock.held || any_ctrl_held() || failures)return 2;
 printf("PASS %s locks=%d mmio=%d daif=%lx\\n",argv[1],lock_order,mmio_reads,daif);return 0;
}
'''
def run(source_root,baseline_source,output,cc):
 source_root=Path(source_root);baseline_source=Path(baseline_source);output=Path(output);output.mkdir(parents=True,exist_ok=False)
 baseline_raw=(baseline_source/TARGET).read_bytes(); patched_raw=(source_root/TARGET).read_bytes()
 expected=transform_function(baseline_raw)
 if patched_raw!=expected:raise ValueError('v46 function source is not the exact transform of v45 baseline')
 original=_extract_original(baseline_raw);fixed=_extract_original(patched_raw)
 results=[];generated={};logs={}
 for name,mode,fn in [('original_irqon_rejected','original',original),('wrong_main_token_inner_rejected','wrong',fixed)]+[(c,'fixed',fixed) for c in CASES[2:]]:
  code=harness(fn,mode); src=output/(name+'.c');exe=output/(name+'.exe');log=output/(name+'.log');src.write_text(code,encoding='utf-8',newline='\n')
  c=subprocess.run([cc,'-std=gnu11','-Werror','-O0',str(src),'-o',str(exe)],capture_output=True,text=True)
  if c.returncode:raise RuntimeError(name+' compile failed: '+c.stderr)
  r=subprocess.run([str(exe),str(CASES.index(name) if name in CASES else (0 if name.startswith('original') else 1))],capture_output=True,text=True)
  log.write_text('COMPILE\n'+c.stdout+c.stderr+'RUN\n'+r.stdout+r.stderr,encoding='utf-8',newline='\n')
  if r.returncode:raise RuntimeError(name+' model failed')
  generated[name]=sha(src.read_bytes());logs[name]=sha(log.read_bytes())
  results.append({'case':name,'compile_returncode':c.returncode,'returncode':r.returncode,'source_sha256':generated[name],'log_sha256':logs[name]})
 wrong=fixed.replace('raw_spin_unlock_irqrestore(&ctrl->lock, ctrl_flags);','raw_spin_unlock_irqrestore(&ctrl->lock, main_flags);')
 proof={'schema_version':1,'passed':True,'hardware_verified':False,'cases':[x['case'] for x in results],'case_results':results,'generated_sha256':generated,'logs_sha256':logs,'baseline_function_sha256':sha(original.encode()),'function_source_sha256':sha(fixed.encode()),'negative_function_sha256':{'original':sha(original.encode()),'wrong_main_inner':sha(wrong.encode())},'harness_sha256':sha(Path(__file__).read_bytes()),'fixed_generated_sha256':sha(harness(fixed,'fixed').encode()),'baseline_source_sha256':sha(baseline_raw),'patched_source_sha256':sha(patched_raw),'source_root':str(source_root)}
 (output/'result.json').write_text(json.dumps(proof,indent=2)+'\n',encoding='utf-8',newline='\n');return proof
def _extract_original(raw):
 start=raw.index(b'void exynos_ehld_event_raw_update_allcpu(void)');brace=raw.index(b'{',start);d=0
 for i in range(brace,len(raw)):
  if raw[i:i+1]==b'{':d+=1
  elif raw[i:i+1]==b'}':
   d-=1
   if not d:return raw[start:i+1].decode()
 raise ValueError('unclosed function')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--source-root',type=Path,required=True);p.add_argument('--baseline-source',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--cc',required=True);a=p.parse_args();print(json.dumps(run(a.source_root,a.baseline_source,a.output,a.cc),sort_keys=True))










