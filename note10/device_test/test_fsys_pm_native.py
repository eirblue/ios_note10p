"""Execute the complete original/patched power-off callback; compare semantics."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
from prepare_fsys_pm import HERE,PINS,instrument,validate_otg
from run_probe import ROOT

STUB=r'''
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdbool.h>
#include <stddef.h>
#include <limits.h>
typedef unsigned int u32;
#define CONFIG_USB_DWC3_EXYNOS
#define CONFIG_USB_PORT_POWER_OPTIMIZATION
#define DEFINE_SPINLOCK(x) int x
#define unlikely(x) (x)
#define container_of(p,t,m) ((t*)((char*)(p)-offsetof(t,m)))
#define EXYNOS_PD_PREFIX ""
#define ASL1 0
#define DEBUG_PRINT_INFO(...) ((void)0)
#define pr_info(...) ((void)0)
#define pr_debug(...) ((void)0)
#define pr_err(...) ((void)0)
#define pr_auto(...) ((void)0)
struct generic_pm_domain {const char *name;};
struct exynos_pm_domain {
 struct generic_pm_domain genpd;const char*name;unsigned int cal_pdid;
 int access_lock;int(*pd_control)(unsigned int,int);bool(*power_down_ok)(void);
 bool power_down_skipped;
};
static unsigned int mode,irq,spin,mutex,otg_calls,control_calls,forced,pre,post,other_calls;
static unsigned int otg_connection,is_otg_only;
#define spin_lock_irqsave(p,f) do{if(spin)abort();(f)=irq;irq=1;spin=1;}while(0)
#define spin_unlock_irqrestore(p,f) do{if(!spin || !irq)abort();spin=0;irq=(f);}while(0)
static void mutex_lock(int*p){if(mutex || spin)abort();mutex=1;}
static void mutex_unlock(int*p){if(!mutex || spin)abort();mutex=0;}
static int cal_pd_control(unsigned int id,int on){
 if(!mutex || spin || on || id!=0xb138000eU)abort();++control_calls;
 if(mode==3)return -5;if((mode==4 || mode==5)&&control_calls==1)return -4;
 if(mode==5)return -5;if(mode==16)return INT_MIN;if(mode==17)return 5;return 0;
}
static int foreign_control(unsigned int id,int on){++other_calls;return 0;}
static bool foreign_predicate(void){++other_calls;return true;}
static void exynos_pd_power_off_pre(struct exynos_pm_domain*p){if(!mutex || spin)abort();++pre;}
static void exynos_pd_power_off_post(struct exynos_pm_domain*p){if(!mutex || spin)abort();++post;}
static void exynos_pd_prepare_forced_off(struct exynos_pm_domain*p){if(!mutex || spin)abort();++forced;}
static void sec_debug_set_extra_info_epd(char*p){if(!mutex || spin)abort();}
'''
MAIN=r'''
int main(int argc,char**argv){
 struct exynos_pm_domain pd={0};int ret=99;unsigned int saved_irq;
 mode=atoi(argv[1]);irq=saved_irq=mode==15;
 pd.name=pd.genpd.name="pd-fsys0a";pd.cal_pdid=0xb138000eU;
 pd.pd_control=cal_pd_control;pd.power_down_ok=exynos_pd_power_down_ok_usb;
#ifdef CONFIG_NOTE10_ABOX_PMU_AUDIT
 if(mode!=12)n10_fsys_note(&pd,1,0);
 if(mode==11)n10_fsys_note(&pd,1,0);
 if(mode==13)n10_fsys_history.entries=~0U;
 if(mode==23){struct exynos_pm_domain duplicate=pd;n10_fsys_note(&duplicate,6,0);}
#endif
 if(mode==6)pd.pd_control=NULL;
 if(mode==8)pd.name="foreign";
 if(mode==9)pd.power_down_ok=foreign_predicate;
 if(mode==10 || mode==20)pd.pd_control=foreign_control;
 if(mode==7){pd.cal_pdid=42;pd.pd_control=foreign_control;}
 otg_connection=(mode==1 || mode==18 || mode==19);is_otg_only=mode==18;
 if(mode)ret=exynos_pd_power_off(&pd.genpd);
 if(mode==14){otg_connection=1;ret=exynos_pd_power_off(&pd.genpd);}
 if(mode==18){ret=exynos_pd_power_off(&pd.genpd);}
 if(mode==19){otg_connection=0;ret=exynos_pd_power_off(&pd.genpd);}
 if(irq!=saved_irq || spin || mutex)abort();
 printf("{\"ret\":%d,\"otg\":%u,\"control\":%u,\"other\":%u,\"forced\":%u,\"pre\":%u,\"post\":%u,\"skipped\":%u}\n",ret,otg_calls,control_calls,other_calls,forced,pre,post,pd.power_down_skipped);
#ifdef CONFIG_NOTE10_ABOX_PMU_AUDIT
 {struct n10_fsys_pm_sample s;
  if(mode==22)n10_fsys_note(&pd,99,0);
  n10_fsys_pm_read(&s);
  if(!s.invalid && s.entries!=s.exits)abort();
  if(mode==21){s.registered=0;n10_fsys_pm_read(&s);}
  if(irq!=saved_irq || spin || mutex)abort();
  printf("{\"registered\":%u,\"invalid\":%u,\"entries\":%u,\"gates\":%u,\"allowed\":%u,\"denied\":%u,\"skipped\":%u,\"controls\":%u,\"control_errors\":%u,\"completed\":%u,\"last_result\":%u,\"last_negative\":%u,\"last_skipped\":%u}\n",s.registered,s.invalid,s.entries,s.gates,s.allowed,s.denied,s.skipped,s.controls,s.control_errors,s.completed,s.last_result,s.last_negative,s.last_skipped);
 }
#endif
 return 0;
}
'''

def function(raw,signature):
    start=raw.index(signature)
    if signature=='static int exynos_pd_power_off(':return raw[start:raw.index('\n#ifdef CONFIG_OF',start)]
    i=raw.index('{',start);depth=1;j=i+1
    while depth:
        if raw[j]=='{':depth+=1
        if raw[j]=='}':depth-=1
        j+=1
    return raw[start:j]+'\n'

def run(output,pd_driver,otg_source):
    output=Path(output);driver=Path(pd_driver).read_bytes();otg=Path(otg_source).read_bytes()
    if output.exists():raise ValueError('Fresh FSYS model output required')
    # Recover and verify the original source via the known private input alongside caller.
    original=Path(pd_driver).with_name('exynos-pd-original.c').read_bytes()
    if hashlib.sha256(original).hexdigest()!=PINS['drivers/soc/samsung/exynos-pd.c'] or driver!=instrument(original):raise ValueError('Actual prepared power-domain callback differs')
    validate_otg(otg)
    original=original.decode();driver=driver.decode();otg=otg.decode()
    predicate=function(original,'static bool exynos_pd_power_down_ok_usb(')
    otg_body=function(otg,'u32 otg_is_connect(').replace('otg_is_connect','original_otg_is_connect')
    constants='\n'.join(re.findall(r'^#define OTG_(?:NO_CONNECT|CONNECT_ONLY|DEVICE_CONNECT)\s+\d+',otg,re.M))+'\n'
    wrapper='u32 otg_is_connect(void){if(!mutex || spin)abort();++otg_calls;return original_otg_is_connect();}\n'
    contract=(HERE/'abox_pmu_contract.h').read_text();helper=re.sub(r'^#include[^\n]*\n','',(HERE/'fsys_pm_backend.c').read_text(),flags=re.M)
    output.mkdir(parents=True);compiler=ROOT/'host-tools/windows-build/llvm-mingw/llvm-mingw-20261006-ucrt-x86_64/bin/clang.exe' if sys.platform=='win32' else shutil.which('cc')
    def build(name,code):
        p=output/(name+'.c');p.write_bytes(code.encode());exe=output/(name+('.exe' if sys.platform=='win32' else ''))
        made=subprocess.run([str(compiler),'-std=c11','-O2',str(p),'-o',str(exe)],capture_output=True,timeout=60);(output/(name+'-compile.log')).write_bytes(made.stdout+made.stderr)
        if made.returncode:raise ValueError('FSYS actual-C compilation failed')
        return exe
    common=STUB+constants+otg_body+wrapper+predicate
    enabled=build('enabled','#define CONFIG_NOTE10_ABOX_PMU_AUDIT\n'+common+contract+helper+function(driver,'static int exynos_pd_power_off(')+MAIN)
    baseline=build('baseline',common+function(original,'static int exynos_pd_power_off(')+MAIN)
    disabled=build('disabled',common+function(driver,'static int exynos_pd_power_off(')+MAIN)
    outcomes=[]
    for mode in range(24):
        rows=[]
        for name,exe in [('enabled',enabled),('baseline',baseline),('disabled',disabled)]:
            ran=subprocess.run([str(exe),str(mode)],capture_output=True,timeout=15);(output/f'{name}-{mode}.log').write_bytes(ran.stdout+ran.stderr)
            if ran.returncode:raise ValueError('FSYS callback lock/IRQ invariant failed mode '+str(mode))
            rows.append([json.loads(l) for l in ran.stdout.decode().splitlines()])
        if rows[0][0]!=rows[1][0] or rows[1]!=rows[2]:raise ValueError('Original power/control/predicate semantics changed mode '+str(mode))
        h=rows[0][1];valid=h['registered']==1 and not h['invalid'];expected=mode not in (6,8,9,10,11,12,13,20,22,23)
        if valid!=expected:raise ValueError('FSYS identity/overflow/registration differed mode '+str(mode))
        if valid and mode not in (7,23):
            sem=rows[0][0]
            if h['gates']!=sem['otg'] or h['controls']!=sem['control'] or h['last_skipped']!=sem['skipped']:raise ValueError('FSYS trace differs from actual callback')
            if mode==16 and (h['last_result']!=0x80000000 or h['last_negative']!=1):raise ValueError('FSYS signed result overflow')
        outcomes.append(dict(mode=mode,passed=True,valid_observation=valid))
    result=dict(passed=True,cases=24,outcomes=outcomes,actual_complete_power_off_callback_executed=True,original_callback_semantics_preserved=True,
                disabled_path_original_callback_preserved=True,actual_usb_predicate_executed=True,actual_otg_predicate_executed=True,no_extra_predicate_calls=True,hardware_verified=False,
                prepared_driver_sha256=hashlib.sha256(driver.encode()).hexdigest(),harness_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    (output/'result.json').write_bytes((json.dumps(result,indent=2)+'\n').encode());return result
