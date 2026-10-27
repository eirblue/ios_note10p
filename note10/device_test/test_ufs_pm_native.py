"""Actual UFS observer/producer and generated DMA hook with lifetime/lock models."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
from prepare_ufs_pm import HERE,SOURCES,HCI_CALL
from run_probe import ROOT
from decode_ufs_pm import decode
ID='0123456789abcdef0123456789abcdef'
STUB=r'''
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>
#include <stdint.h>
typedef unsigned int u32;
#define N10_RESERVE_BUILD_ID "0123456789abcdef0123456789abcdef"
#define scnprintf snprintf
#define pr_info printf
#define READ_ONCE(x) (x)
#define CONFIG_NOTE10_UFS_PM_AUDIT
#define DEFINE_SPINLOCK(x) int x
#define CLKS_ON 1
#define UFS_POWERDOWN_PWR_MODE 3
#define UIC_LINK_OFF_STATE 0
#define REG_CONTROLLER_ENABLE 0x34
#define REG_UTP_TRANSFER_REQ_DOOR_BELL 0x58
#define REG_UTP_TASK_REQ_DOOR_BELL 0x78
#define ufshcd_is_system_pm(op) ((op)==1)
struct device_driver {int identity;};
struct device {struct device_driver *driver;struct {int runtime_status;} power;};
struct platform_device {struct device dev;};
struct device_node {int identity;};
struct Scsi_Host {int *host_lock;};
struct ufs_hba {
 struct device *dev;struct Scsi_Host *host;void *mmio_base;
 unsigned long outstanding_reqs,outstanding_tasks,lrb_in_use;
 unsigned int is_powered,is_irq_enabled,is_sys_suspended,pm_op_in_progress,curr_dev_pwr_mode,uic_link_state;
 struct {unsigned int state,is_suspended;} clk_gating;
};
static struct {struct device_driver driver;} exynos_ufs_driver;
static struct device_driver foreign_driver;
static struct platform_device controller;
static struct device_node dt;
static struct ufs_hba hba;
static struct Scsi_Host host;
static int host_lock;
static unsigned int mode,phase,node_refs,device_refs,device_locked,host_locked,irq,global_locked,callback_active,mmio_reads;
static struct device_node *of_find_compatible_node(void*a,void*b,const char*c){
 if(a || b || strcmp(c,"samsung,exynos-ufs"))abort();
 if(mode==1)return NULL;++node_refs;return &dt;
}
static struct platform_device *of_find_device_by_node(struct device_node*n){
 if(n!=&dt || node_refs!=1)abort();if(mode==2)return NULL;
 ++device_refs;return &controller;
}
static void of_node_put(struct device_node*n){if(n!=&dt || !node_refs--)abort();}
static int device_trylock(struct device*d){
 if(d!=&controller.dev || device_refs!=1 || device_locked)abort();
 if(mode==3)return 0;device_locked=1;return 1;
}
static void device_unlock(struct device*d){if(d!=&controller.dev || !device_locked || host_locked)abort();device_locked=0;}
static void put_device(struct device*d){if(d!=&controller.dev || device_locked || !device_refs--)abort();}
static struct ufs_hba *dev_get_drvdata(struct device*d){if(!device_locked)abort();return mode==5?NULL:&hba;}
static void model_lock(int *p,unsigned long *f){
 *f=irq;irq=1;
 if(p==&host_lock){if((!device_locked && !callback_active) || host_locked++)abort();}
 else {if(global_locked++)abort();}
}
static void model_unlock(int *p,unsigned long f){
 if(!irq)abort();if(p==&host_lock){if(!host_locked)abort();host_locked=0;}
 else{if(!global_locked)abort();global_locked=0;}irq=f;
}
#define spin_lock_irqsave(p,f) model_lock((p),&(f))
#define spin_unlock_irqrestore(p,f) model_unlock((p),(f))
static unsigned int ufshcd_readl(struct ufs_hba *p,unsigned int reg){
 if(p!=&hba || !host_locked || !global_locked || !callback_active || !irq ||
  hba.clk_gating.state!=CLKS_ON || !hba.mmio_base || !hba.is_powered ||
  hba.is_irq_enabled || !hba.pm_op_in_progress || !hba.clk_gating.is_suspended)abort();
 ++mmio_reads;
 if(reg==REG_CONTROLLER_ENABLE)return mode==27;
 if(reg==REG_UTP_TRANSFER_REQ_DOOR_BELL)return mode==28;
 if(reg==REG_UTP_TASK_REQ_DOOR_BELL)return mode==29;
 abort();return 0;
}
static void setup(void){
 memset(&controller,0,sizeof(controller));memset(&hba,0,sizeof(hba));memset(&host,0,sizeof(host));
 controller.dev.driver=mode==4?&foreign_driver:&exynos_ufs_driver.driver;
 controller.dev.power.runtime_status=phase==1?2:0;
 host.host_lock=mode==8?NULL:&host_lock;hba.host=mode==7?NULL:&host;
 hba.dev=mode==6?NULL:&controller.dev;
 hba.mmio_base=&hba;hba.is_powered=mode==23?0:1;
 hba.is_irq_enabled=phase==1?0:1;hba.is_sys_suspended=phase==1;
 hba.curr_dev_pwr_mode=phase==1?2:1;hba.uic_link_state=phase==1?2:1;
 hba.clk_gating.state=phase==1?0:1;hba.clk_gating.is_suspended=phase==1;
 if(phase==1){
  if(mode==13)hba.outstanding_reqs=1;
  if(mode==14)hba.outstanding_tasks=1;
  if(mode==15)hba.lrb_in_use=1;
  if(mode==16)hba.is_irq_enabled=1;
  if(mode==17)hba.clk_gating.state=1;
  if(mode==18)hba.uic_link_state=1;
  if(mode==22)hba.pm_op_in_progress=1;
  if(mode==24)hba.is_sys_suspended=0;
  if(mode==25)hba.clk_gating.is_suspended=0;
  if(mode==26)hba.curr_dev_pwr_mode=1;
 }
 if(mode==20){
  controller.dev.power.runtime_status=2;hba.is_irq_enabled=0;hba.is_sys_suspended=1;
  hba.curr_dev_pwr_mode=2;hba.uic_link_state=2;hba.clk_gating.state=0;hba.clk_gating.is_suspended=1;
 }
}
'''
CALLBACK_MAIN=r'''
static void invoke_callback(void){
 struct ufs_hba old=hba;
 callback_active=1;hba.is_powered=1;hba.is_irq_enabled=0;hba.pm_op_in_progress=1;
 hba.clk_gating.is_suspended=1;hba.clk_gating.state=CLKS_ON;
 hba.curr_dev_pwr_mode=UFS_POWERDOWN_PWR_MODE;hba.uic_link_state=UIC_LINK_OFF_STATE;
 if(mode==30)hba.clk_gating.state=0;
 if(mode==31)hba.is_irq_enabled=1;
 if(mode==32)hba.pm_op_in_progress=0;
 if(mode==33)hba.clk_gating.is_suspended=0;
 if(mode==34)hba.is_powered=0;
 if(mode==35)hba.uic_link_state=1;
 if(mode==36)hba.curr_dev_pwr_mode=1;
 if(mode==37)hba.mmio_base=NULL;
 if(mode==39)n10_ufs_hci_arm(NULL,1);
 if(mode==41)n10_ufs_hci_arm(&hba,3);
 pinned_callback_hook(&hba,mode==40?0:1);
 if(mode==38)pinned_callback_hook(&hba,1);
 hba=old;callback_active=0;
}
'''
MAIN=r'''
int main(int argc,char**argv){
 unsigned int begin,completed,saved_irq;struct ufs_hba old_hba;struct platform_device old_dev;struct Scsi_Host old_host;
 mode=atoi(argv[1]);begin=mode==9?0:(mode==19?0xffffffffU:1);
 if(n10_ufs_pm_read(NULL,2)!=-EINVAL)return 80;
 for(phase=0;phase<3;++phase){
  setup();irq=saved_irq=phase%2;old_hba=hba;old_dev=controller;old_host=host;
  if(phase==1 && mode!=20 && !(mode>=1 && mode<=8))invoke_callback();
  if(!(mode==10 && phase==1))n10_ufs_pm_capture(phase,begin+(mode==12 && phase==1));
  if(mode==11 && phase==1)n10_ufs_pm_capture(phase,begin);
  if(node_refs || device_refs || device_locked || host_locked || global_locked || irq!=saved_irq ||
     memcmp(&old_hba,&hba,sizeof(hba)) || memcmp(&old_dev,&controller,sizeof(controller)) || memcmp(&old_host,&host,sizeof(host)))return 81;
 }
 if((mode==0 || mode==19) && mmio_reads!=3)return 82;
 if((mode==20 || (mode>=30 && mode<=37) || mode==39 || mode==40) && mmio_reads)return 83;
 /* No completed or failed roundtrip leaves an HCI observer armed. */
 if(n10_ufs_hci_owner || n10_ufs_hci_generation)return 84;
 completed=begin+1;if(!completed)completed=1;
 n10_report_ufs_pm(mode==21?begin:completed);return 0;
}
'''

def run(output,dma_helper):
    output=Path(output).resolve();dma_helper=Path(dma_helper)
    if not output.is_relative_to((ROOT/'note10/private').resolve()) or output.exists():raise ValueError('Fresh private UFS model directory required')
    output.mkdir(parents=True)
    sources={n:(HERE/n).read_bytes() for n in SOURCES}
    clean=lambda s:re.sub(r'^#include[^\n]*\n','',s,flags=re.M)
    checksum=re.search(r'static u32 n10_frame_checksum[^}]+}',(HERE/'xnu_reserve.c').read_text()).group()
    compiler=ROOT/'host-tools/windows-build/llvm-mingw/llvm-mingw-20261006-ucrt-x86_64/bin/clang.exe' if sys.platform=='win32' else shutil.which('cc')
    def build(name,text):
        src=output/(name+'.c');src.write_bytes(text.encode());exe=output/(name+('.exe' if sys.platform=='win32' else ''))
        made=subprocess.run([str(compiler),'-std=c11','-O2',str(src),'-o',str(exe)],capture_output=True,timeout=60)
        (output/(name+'-compile.log')).write_bytes(made.stdout+made.stderr)
        if made.returncode:raise RuntimeError('Actual UFS model compilation failed: '+name)
        return exe
    hook_function='static void pinned_callback_hook(struct ufs_hba *hba,unsigned int pm_op){\n'+HCI_CALL.decode()+'}\n'
    text=STUB+sources['ufs_pm_contract.h'].decode()+clean(sources['ufs_hci_backend.c'].decode())+clean(sources['ufs_pm_backend.c'].decode())+checksum+clean(sources['ufs_pm_probe.c'].decode())+hook_function+CALLBACK_MAIN+MAIN
    exe=build('ufs',text);rows=[]
    for mode in range(42):
        ran=subprocess.run([str(exe),str(mode)],capture_output=True,timeout=15)
        (output/f'mode-{mode}.log').write_bytes(ran.stdout+ran.stderr)
        if ran.returncode:raise ValueError('UFS reference/lock/state restoration model failed mode '+str(mode))
        try:decode(ran.stdout.decode(),ID,1 if mode==19 else 2);accepted=True
        except ValueError:accepted=False
        if accepted!=(mode in (0,19)):raise ValueError('UFS strict decoder differs mode '+str(mode))
        rows.append(dict(mode=mode,passed=True,accepted=accepted))
    from test_dma_pm_native import STUB as DMA_STUB,MAIN as DMA_MAIN
    hook='\n#define CONFIG_NOTE10_UFS_PM_AUDIT\nstatic void n10_ufs_pm_capture(unsigned int phase,unsigned int generation){if(locked)abort();printf("UFSHOOK phase=%u generation=%u\\n",phase,generation);}\n'
    raw=dma_helper.read_bytes()
    text=DMA_STUB+hook+(HERE/'dma_pm_contract.h').read_text()+clean(raw.decode())+checksum+clean((HERE/'dma_pm_probe.c').read_text())+DMA_MAIN
    exe=build('hook',text);ran=subprocess.run([str(exe),'0'],capture_output=True,timeout=15)
    (output/'hook.log').write_bytes(ran.stdout+ran.stderr)
    if ran.returncode or re.findall(rb'UFSHOOK phase=(\d+) generation=(\d+)',ran.stdout)!=[(b'0',b'1'),(b'1',b'1'),(b'2',b'1')]:
        raise ValueError('Generated DMA hook failed phase/generation/unlocked-list test')
    from decode_dma_pm import decode as decode_dma
    decode_dma(ran.stdout.decode(),ID,2)
    result=dict(passed=True,cases=len(rows),outcomes=rows,source_sha256={n:hashlib.sha256(raw).hexdigest() for n,raw in sources.items()},
        generated_dma_sha256=hashlib.sha256(raw).hexdigest(),harness_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        actual_hci_backend_executed=True,pinned_hci_hook_executed=True,actual_backend_executed=True,actual_probe_executed=True,generated_dma_hook_executed=True,hardware_verified=False)
    (output/'result.json').write_bytes((json.dumps(result,indent=2)+'\n').encode());return result

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True);parser.add_argument('--dma-helper',type=Path,required=True)
    a=parser.parse_args();r=run(a.output,a.dma_helper);print(json.dumps({'passed':r['passed'],'cases':r['cases']}))
