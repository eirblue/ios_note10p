"""Execute actual registered-controller observer, producer and pinned helpers."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
from prepare_iommu_pm import HERE,SOURCES,inline_helpers,HELPERS_SHA
from run_probe import ROOT
from decode_iommu_pm import decode
ID='0123456789abcdef0123456789abcdef'
STUB=r'''
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdbool.h>
#include <errno.h>
typedef unsigned int u32;
#define READ_ONCE(x) (x)
#define scnprintf snprintf
#define pr_info printf
#define N10_RESERVE_BUILD_ID "0123456789abcdef0123456789abcdef"
#define SYSMMU_STATE_DISABLED 1
#define SYSMMU_STATE_ENABLED 2
#define RPM_ACTIVE 0
#define RPM_SUSPENDED 2
struct device_driver {int identity;};
struct device {struct device_driver *driver;struct {unsigned int syscore,is_prepared,is_suspended;int runtime_status;} power;char name[300];};
struct sysmmu_drvdata {struct device *sysmmu;int activations,runtime_active,lock,no_rpm_control;bool is_suspended,hold_rpm_on_boot;int securebase;unsigned long long pgtable;};
static struct {struct device_driver driver;} exynos_sysmmu_driver;
static struct device_driver foreign;
static struct device devices[66];
static struct sysmmu_drvdata controllers[66];
static unsigned int mode,phase,refs,device_locked,spin_locked,irq,device_index;
static int device_trylock(struct device *dev){
 if(refs!=1 || device_locked || dev!=&devices[device_index])abort();
 if(mode==3)return 0;device_locked=1;return 1;
}
static void device_unlock(struct device *dev){if(!device_locked || spin_locked)abort();device_locked=0;}
static struct sysmmu_drvdata *dev_get_drvdata(struct device *dev){if(!device_locked)abort();return mode==5?NULL:&controllers[device_index];}
static const char *dev_name(struct device *dev){if(!device_locked)abort();return dev->name;}
#define spin_lock_irqsave(p,f) do{if((p)!=&controllers[device_index].lock || !device_locked || spin_locked++)abort();(f)=irq;irq=1;}while(0)
#define spin_unlock_irqrestore(p,f) do{if((p)!=&controllers[device_index].lock || !spin_locked || !irq)abort();spin_locked=0;irq=(f);}while(0)
static int driver_for_each_device(struct device_driver *driver,struct device *start,void *ctx,int(*fn)(struct device*,void*)){
 unsigned int count=mode==10?65:(mode==21?64:(mode==22?9:3));int error;
 if(driver!=&exynos_sysmmu_driver.driver || start || refs)abort();
 if(mode==1)return -EIO;if(mode==2)return 0;
 for(device_index=0;device_index<count;++device_index){
  ++refs;error=fn(&devices[device_index],ctx);--refs;
  if(device_locked || spin_locked)abort();if(error)return error;
 }
 return 0;
}
static void setup(void){
 unsigned int i;memset(devices,0,sizeof(devices));memset(controllers,0,sizeof(controllers));
 for(i=0;i<66;++i){
  devices[i].driver=mode==4?&foreign:&exynos_sysmmu_driver.driver;
  snprintf(devices[i].name,sizeof(devices[i].name),"sysmmu.%u",i);
  devices[i].power.is_prepared=phase==1;devices[i].power.is_suspended=phase==1;
  devices[i].power.syscore=i==2;devices[i].power.runtime_status=phase==1?2:0;
  controllers[i].sysmmu=mode==6?NULL:&devices[i];controllers[i].activations=1;
  controllers[i].runtime_active=1;controllers[i].is_suspended=phase==1;
  controllers[i].no_rpm_control=i%3;controllers[i].hold_rpm_on_boot=i==1;
  controllers[i].securebase=i==2;controllers[i].pgtable=i==0?4096:0;
  if(mode==7)controllers[i].activations=-1;
  if(mode==8)controllers[i].runtime_active=-1;
  if(mode==9)controllers[i].no_rpm_control=3;
  if(mode==17)controllers[i].activations=1025;
  if(mode==16 && phase==1)devices[i].name[0]='x';
  if(mode==19){controllers[i].no_rpm_control=0;controllers[i].is_suspended=0;}
  if(mode==10 || mode==21){controllers[i].runtime_active=0;controllers[i].no_rpm_control=0;controllers[i].hold_rpm_on_boot=0;devices[i].power.syscore=0;}
  if(mode==23){memset(devices[i].name,'a',80);devices[i].name[80]=0;}
  if(mode==24)strcpy(devices[i].name,"sysmmu.same");
  if(mode==20)memset(devices[i].name,'a',sizeof(devices[i].name));
 }
}
'''
MAIN=r'''
int main(int argc,char**argv){
 unsigned int begin,completed,saved_irq;struct device old_devices[66];struct sysmmu_drvdata old_data[66];
 mode=atoi(argv[1]);begin=mode==14?0xffffffffU:1;
 if(n10_iommu_pm_read(NULL,2)!=-EINVAL)return 80;
 for(phase=0;phase<3;++phase){
  setup();irq=saved_irq=mode==18?1:phase%2;
  memcpy(old_devices,devices,sizeof(devices));memcpy(old_data,controllers,sizeof(controllers));
  if(!(mode==11 && phase==1))n10_iommu_pm_capture(phase,begin+(mode==13 && phase==1));
  if(mode==12 && phase==1)n10_iommu_pm_capture(phase,begin);
  if(refs || device_locked || spin_locked || irq!=saved_irq || memcmp(old_devices,devices,sizeof(devices)) || memcmp(old_data,controllers,sizeof(controllers)))return 81;
 }
 completed=begin+1;if(!completed)completed=1;
 n10_report_iommu_pm(mode==15?begin:completed);return 0;
}
'''

def run(output,header,dma_helper):
    output=Path(output).resolve()
    if not output.is_relative_to((ROOT/'note10/private').resolve()) or output.exists():raise ValueError('Fresh private IOMMU model directory required')
    helpers=inline_helpers(Path(header).read_bytes());output.mkdir(parents=True)
    sources={n:(HERE/n).read_bytes() for n in SOURCES}
    clean=lambda text:re.sub(r'^#include[^\n]*\n','',text,flags=re.M)
    checksum=re.search(r'static u32 n10_frame_checksum[^}]+}',(HERE/'xnu_reserve.c').read_text()).group()
    compiler=ROOT/'host-tools/windows-build/llvm-mingw/llvm-mingw-20261006-ucrt-x86_64/bin/clang.exe' if sys.platform=='win32' else shutil.which('cc')
    def build(name,text):
        src=output/(name+'.c');src.write_bytes(text.encode());exe=output/(name+('.exe' if sys.platform=='win32' else ''))
        made=subprocess.run([str(compiler),'-std=c11','-O2',str(src),'-o',str(exe)],capture_output=True,timeout=60)
        (output/(name+'-compile.log')).write_bytes(made.stdout+made.stderr)
        if made.returncode:raise RuntimeError('Actual IOMMU C model compilation failed')
        return exe
    exe=build('iommu',STUB+helpers+sources['iommu_pm_contract.h'].decode()+clean(sources['iommu_pm_backend.c'].decode())+checksum+clean(sources['iommu_pm_probe.c'].decode())+MAIN)
    rows=[]
    for mode in range(25):
        ran=subprocess.run([str(exe),str(mode)],capture_output=True,timeout=15);(output/f'mode-{mode}.log').write_bytes(ran.stdout+ran.stderr)
        if ran.returncode:raise ValueError('IOMMU reference/lock/IRQ/state model failed mode '+str(mode))
        try:decode(ran.stdout.decode(),ID,1 if mode==14 else 2);accepted=True
        except ValueError:accepted=False
        if accepted!=(mode in (0,14,18,19,21)):raise ValueError('IOMMU strict decoder differs mode '+str(mode))
        rows.append(dict(mode=mode,passed=True,accepted=accepted))
    from test_dma_pm_native import STUB as DMA_STUB,MAIN as DMA_MAIN
    raw=Path(dma_helper).read_bytes()
    hook='\n#define CONFIG_NOTE10_IOMMU_PM_AUDIT\nstatic void n10_iommu_pm_capture(unsigned int phase,unsigned int generation){if(locked)abort();printf("MMUHOOK phase=%u generation=%u\\n",phase,generation);}\n'
    exe=build('hook',DMA_STUB+hook+(HERE/'dma_pm_contract.h').read_text()+clean(raw.decode())+checksum+clean((HERE/'dma_pm_probe.c').read_text())+DMA_MAIN)
    ran=subprocess.run([str(exe),'0'],capture_output=True,timeout=15);(output/'hook.log').write_bytes(ran.stdout+ran.stderr)
    if ran.returncode or re.findall(rb'MMUHOOK phase=(\d+) generation=(\d+)',ran.stdout)!=[(b'0',b'1'),(b'1',b'1'),(b'2',b'1')]:
        raise ValueError('Generated IOMMU DMA hook not executed after list unlock')
    from decode_dma_pm import decode as decode_dma
    decode_dma(ran.stdout.decode(),ID,2)
    result=dict(passed=True,cases=len(rows),outcomes=rows,source_sha256={n:hashlib.sha256(raw).hexdigest() for n,raw in sources.items()},
        pinned_helpers_sha256=HELPERS_SHA,harness_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        generated_dma_sha256=hashlib.sha256(raw).hexdigest(),actual_backend_executed=True,actual_probe_executed=True,
        pinned_helpers_executed=True,generated_dma_hook_executed=True,hardware_verified=False)
    (output/'result.json').write_bytes((json.dumps(result,indent=2)+'\n').encode());return result

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--header',type=Path,required=True);p.add_argument('--dma-helper',type=Path,required=True)
    a=p.parse_args();r=run(a.output,a.header,a.dma_helper);print(json.dumps({'passed':r['passed'],'cases':r['cases']}))
