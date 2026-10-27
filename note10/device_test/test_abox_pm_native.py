"""Actual ABOX observer/producer and exact generated callback event blocks."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
from prepare_abox_pm import HERE,SOURCES,PATCHED_SHA,ENABLE_EVENT,BEGIN_EVENT,IPC_EVENT,END_EVENT,WORK_BEGIN,WORK_GET,WORK_GATE,WORK_END,QUEUE_PUT,QUEUE_GET,EVENT_BLOCKS,event_digest
from run_probe import ROOT
from decode_abox_pm import decode
ID='0123456789abcdef0123456789abcdef'
STUB=r'''
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdbool.h>
#include <errno.h>
typedef unsigned int u32;
#define READ_ONCE(x) (*(volatile __typeof__(x) *)&(x))
#define atomic_read(p) (*(p))
#define scnprintf snprintf
#define pr_info printf
#define DEFINE_SPINLOCK(x) int x
#define CONFIG_NOTE10_ABOX_PM_AUDIT
#define CALLIOPE_DISABLED 0
#define CALLIOPE_ENABLED 3
#define RPM_SUSPENDING 3
#define ABOX_IPC_QUEUE_SIZE 128
#define N10_RESERVE_BUILD_ID "0123456789abcdef0123456789abcdef"
struct device_driver {int identity;};
struct device {struct device_driver *driver;struct {int runtime_status,usage_count,child_count,runtime_error;unsigned int disable_depth,is_prepared,is_suspended;} power;};
struct platform_device {struct device dev;};
struct device_node {int identity;};
struct abox_data {struct platform_device *pdev;bool enabled,restored;unsigned int calliope_state,calliope_version,audio_mode,cpu_gear,if_count,rdma_count,wdma_count;int ipc_queue_start,ipc_queue_end,ipc_queue_lock,ipc_work;};
static struct {struct device_driver driver;} samsung_abox_driver;
static struct device_driver foreign_driver;
static struct platform_device controller,other;
static struct device_node node;
static struct abox_data box;
static unsigned int mode,phase,node_refs,device_refs,device_locked,ipc_locked,event_locked,irq,ipc_calls,pm_get_calls,pm_put_calls,gate_calls;
static struct device_node *of_find_compatible_node(void*a,void*b,const char*c){if(a || b || strcmp(c,"samsung,abox"))abort();if(mode==1)return NULL;++node_refs;return &node;}
static struct platform_device *of_find_device_by_node(struct device_node*p){if(p!=&node || node_refs!=1)abort();if(mode==2)return NULL;++device_refs;return &controller;}
static void of_node_put(struct device_node*p){if(p!=&node || !node_refs--)abort();}
static void put_device(struct device*p){if(p!=&controller.dev || device_locked || !device_refs--)abort();}
static int device_trylock(struct device*p){if(p!=&controller.dev || device_locked || device_refs!=1)abort();if(mode==3)return 0;device_locked=1;return 1;}
static void device_unlock(struct device*p){if(!device_locked || ipc_locked || event_locked)abort();device_locked=0;}
static struct abox_data *dev_get_drvdata(struct device*p){if(!device_locked)abort();return mode==5?NULL:&box;}
static void lock_model(int*p,unsigned long*f){*f=irq;irq=1;if(p==&box.ipc_queue_lock){if(!device_locked || ipc_locked++ || event_locked)abort();}else{if(event_locked++ || ipc_locked)abort();}}
static void unlock_model(int*p,unsigned long f){if(!irq)abort();if(p==&box.ipc_queue_lock){if(!ipc_locked)abort();ipc_locked=0;}else{if(!event_locked)abort();event_locked=0;}irq=f;}
#define spin_lock_irqsave(p,f) lock_model((p),&(f))
#define spin_unlock_irqrestore(p,f) unlock_model((p),(f))
static int abox_cpu_pm_ipc(struct abox_data*d,bool resume){if(d!=&box || resume)abort();++ipc_calls;return mode==17?-EIO:0;}
static int work_pending(int*p){if(p!=&box.ipc_work || !device_locked)abort();return *p;}
static int pm_runtime_get_sync(struct device*p){if(p!=&controller.dev)abort();++pm_get_calls;return mode==26?-EIO:1;}
static int abox_can_calliope_ipc(struct device*p,struct abox_data*d){if(p!=&controller.dev || d!=&box)abort();++gate_calls;return mode!=27;}
static void pm_runtime_put_autosuspend(struct device*p){if(p!=&controller.dev)abort();++pm_put_calls;}
static void setup(void){
 memset(&controller,0,sizeof(controller));memset(&box,0,sizeof(box));
 controller.dev.driver=mode==4?&foreign_driver:&samsung_abox_driver.driver;
 box.pdev=mode==6?NULL:&controller;box.if_count=1;box.rdma_count=4;box.wdma_count=4;
 controller.dev.power.runtime_status=2;controller.dev.power.is_prepared=phase==1;controller.dev.power.is_suspended=phase==1;
 if(mode==7)box.calliope_state=4;
 if(mode==8)box.ipc_queue_start=128;
 if(mode==9)box.if_count=9;
 if(mode==10)box.rdma_count=17;
 if(mode==11)box.wdma_count=17;
 if(mode==18)controller.dev.power.usage_count=-1;
 if(mode==19){box.enabled=1;box.calliope_state=3;controller.dev.power.runtime_status=0;controller.dev.power.usage_count=1;}
 if(mode==20)box.ipc_queue_end=1;
 if(mode==21)controller.dev.power.runtime_status=4;
 if(mode==24)controller.dev.power.usage_count=1;
 if(mode==31)box.ipc_work=1;
 box.cpu_gear=12;
}
'''
MAIN=r'''
int main(int argc,char**argv){
 unsigned int begin,completed,saved_irq;struct platform_device old_dev;struct abox_data old_box;
 mode=atoi(argv[1]);begin=mode==15?0xffffffffU:1;
 setup();irq=0;
 if(mode==22)n10_abox_note(&other.dev,1,0);
 else {
  int enable_result=mode==17?-EAGAIN:0;
  if(event_enable(&controller.dev,enable_result)!=enable_result)return 82;
  if(event_disable(&controller.dev,&box,mode==17?3:0)!=0)return 83;
  if(ipc_calls!=(mode==17?1:0))return 84;
 }
 if(mode>=25){
  if(mode==25)n10_abox_note(&controller.dev,5,0);
  else if(mode==26 || mode==27 || mode==28 || mode==29){
   event_worker(&controller.dev,&box);
   if(pm_get_calls!=1 || gate_calls!=1 || pm_put_calls!=1)return 86;
   if(mode==28){n10_abox_note(&controller.dev,5,0);n10_abox_note(&controller.dev,6,1);n10_abox_note(&controller.dev,7,1);}
  }else if(mode==30){event_queue_put(&box,-EBUSY);event_queue_get(&box,-ENODATA);}
  else if(mode==32){n10_abox_history.worker_starts=1;n10_abox_history.worker_stage=5;}
  else if(mode==33)n10_abox_history.can_ipc=1;
  else if(mode==34)n10_abox_history.pm_get_negative=1;
  else if(mode==35){n10_abox_history.worker_starts=0xffffffffU;n10_abox_history.worker_finishes=0xffffffffU;event_worker(&controller.dev,&box);if(event_queue_put(&box,0)!=0 || event_queue_get(&box,0)!=0)return 87;}
 }
 if(n10_abox_pm_read(NULL,2)!=-EINVAL)return 80;
 for(phase=0;phase<3;++phase){
  setup();irq=saved_irq=mode==23?1:phase%2;old_box=box;old_dev=controller;
  if(!(mode==12 && phase==1))n10_abox_pm_capture(phase,begin+(mode==14 && phase==1));
  if(mode==13 && phase==1)n10_abox_pm_capture(phase,begin);
  if(node_refs || device_refs || device_locked || ipc_locked || event_locked || irq!=saved_irq || memcmp(&old_box,&box,sizeof(box)) || memcmp(&old_dev,&controller,sizeof(controller)))return 81;
 }
 completed=begin+1;if(!completed)completed=1;n10_report_abox_pm(mode==16?begin:completed);return 0;
}
'''

def run(output,driver,dma_helper):
    output=Path(output).resolve();driver=Path(driver).read_bytes()
    if not output.is_relative_to((ROOT/'note10/private').resolve()) or output.exists():raise ValueError('Fresh private ABOX model output required')
    if hashlib.sha256(driver).hexdigest()!=PATCHED_SHA or any(driver.count(block)!=1 for block in EVENT_BLOCKS):
        raise ValueError('Actual generated ABOX event blocks differ')
    output.mkdir(parents=True);sources={n:(HERE/n).read_bytes() for n in SOURCES}
    clean=lambda text:re.sub(r'^#include[^\n]*\n','',text,flags=re.M)
    checksum=re.search(r'static u32 n10_frame_checksum[^}]+}',(HERE/'xnu_reserve.c').read_text()).group()
    compiler=ROOT/'host-tools/windows-build/llvm-mingw/llvm-mingw-20261006-ucrt-x86_64/bin/clang.exe' if sys.platform=='win32' else shutil.which('cc')
    def build(name,text):
        src=output/(name+'.c');src.write_bytes(text.encode());exe=output/(name+('.exe' if sys.platform=='win32' else ''))
        made=subprocess.run([str(compiler),'-std=c11','-O2',str(src),'-o',str(exe)],capture_output=True,timeout=60)
        (output/(name+'-compile.log')).write_bytes(made.stdout+made.stderr)
        if made.returncode:raise RuntimeError('Actual ABOX C model compilation failed')
        return exe
    hooks='static int event_enable(struct device*dev,int ret){\n'+ENABLE_EVENT.decode()+'return ret;\n}\n'
    hooks+='static int event_disable(struct device*dev,struct abox_data*data,unsigned int state){\n'+BEGIN_EVENT.decode()+IPC_EVENT.decode()+'\n'+END_EVENT.decode()+'return 0;\n}\n'
    hooks+='static void event_worker(struct device*dev,struct abox_data*data){\n#ifdef CONFIG_NOTE10_ABOX_PM_AUDIT\nbool n10_can;\n#endif\n'+WORK_BEGIN.decode()+WORK_GET.decode()+'\n'+WORK_GATE.decode()+'\n; }\npm_runtime_put_autosuspend(dev);\n'+WORK_END.decode()+'}\n'
    hooks+='static int event_queue_put(struct abox_data*data,int ret){\n'+QUEUE_PUT.decode()+'return ret;\n}\n'
    hooks+='static int event_queue_get(struct abox_data*data,int ret){\n'+QUEUE_GET.decode()+'return ret;\n}\n'
    exe=build('abox',STUB+sources['abox_pm_contract.h'].decode()+clean(sources['abox_pm_backend.c'].decode())+checksum+clean(sources['abox_pm_probe.c'].decode())+hooks+MAIN)
    rows=[]
    for mode in range(36):
        ran=subprocess.run([str(exe),str(mode)],capture_output=True,timeout=15);(output/f'mode-{mode}.log').write_bytes(ran.stdout+ran.stderr)
        if ran.returncode:raise ValueError('ABOX reference/lock/IRQ/state or unchanged callback result failed mode '+str(mode))
        try:
            observation=decode(ran.stdout.decode(),ID,1 if mode==15 else 2);accepted=True
            if observation['abox_driver_idle_state_observed']!=(mode in (0,15,23,27,29,30,35)):raise ValueError('ABOX idle interpretation differs')
            expected={25:dict(worker_starts=1,worker_stage=1,worker_inflight=1),
                26:dict(worker_starts=1,worker_finishes=1,worker_stage=4,pm_get_result=5,pm_get_negative=1),
                27:dict(gate_seen=1,can_ipc=0,worker_finishes=1),
                28:dict(worker_starts=2,worker_finishes=1,worker_stage=3,worker_inflight=1,can_ipc=1),
                29:dict(worker_stage=4,worker_inflight=0,pm_get_result=1,can_ipc=1),
                30:dict(put_busy=1,get_empty=1),31:dict(work_pending=1),35:dict(puts=1,gets=1,worker_starts=0,worker_finishes=0,worker_stage=4,gate_seen=1)}
            snapshot=observation['phases'][1]['snapshot']
            if any(snapshot[k]!=v for k,v in expected.get(mode,{}).items()):raise ValueError('ABOX worker/queue interpretation differs')
        except ValueError:accepted=False
        if accepted!=(mode in (0,15,17,18,19,20,23,24,25,26,27,28,29,30,31,35)):raise ValueError('ABOX strict decoder differs mode '+str(mode))
        rows.append(dict(mode=mode,passed=True,accepted=accepted))
    disabled=build('disabled',STUB.replace('#define CONFIG_NOTE10_ABOX_PM_AUDIT','')+sources['abox_pm_contract.h'].decode()+hooks+'int main(void){mode=17;setup();if(event_enable(&controller.dev,-EIO)!=-EIO || event_disable(&controller.dev,&box,3)!=0 || ipc_calls!=1)return 85;event_worker(&controller.dev,&box);if(pm_get_calls!=1 || gate_calls!=1 || pm_put_calls!=1 || event_queue_put(&box,-EBUSY)!=-EBUSY || event_queue_get(&box,-ENODATA)!=-ENODATA)return 88;return 0;}')
    off=subprocess.run([str(disabled)],capture_output=True,timeout=15);(output/'disabled.log').write_bytes(off.stdout+off.stderr)
    if off.returncode:raise ValueError('Default-off ABOX callback result changed')
    from test_dma_pm_native import STUB as DMA_STUB,MAIN as DMA_MAIN
    raw=Path(dma_helper).read_bytes();hook='\n#define CONFIG_NOTE10_ABOX_PM_AUDIT\nstatic void n10_abox_pm_capture(unsigned int phase,unsigned int generation){if(locked)abort();printf("ABXHOOK phase=%u generation=%u\\n",phase,generation);}\n'
    exe=build('hook',DMA_STUB+hook+(HERE/'dma_pm_contract.h').read_text()+clean(raw.decode())+checksum+clean((HERE/'dma_pm_probe.c').read_text())+DMA_MAIN)
    ran=subprocess.run([str(exe),'0'],capture_output=True,timeout=15);(output/'hook.log').write_bytes(ran.stdout+ran.stderr)
    if ran.returncode or re.findall(rb'ABXHOOK phase=(\d+) generation=(\d+)',ran.stdout)!=[(b'0',b'1'),(b'1',b'1'),(b'2',b'1')]:raise ValueError('ABOX generated unlocked PM hook differs')
    from decode_dma_pm import decode as decode_dma
    decode_dma(ran.stdout.decode(),ID,2)
    result=dict(passed=True,cases=len(rows),outcomes=rows,source_sha256={n:hashlib.sha256(raw).hexdigest() for n,raw in sources.items()},
        patched_driver_sha256=PATCHED_SHA,event_blocks_sha256=event_digest(),generated_dma_sha256=hashlib.sha256(raw).hexdigest(),
        harness_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),actual_backend_executed=True,actual_probe_executed=True,
        generated_event_blocks_executed=True,generated_worker_blocks_executed=True,generated_queue_blocks_executed=True,default_off_blocks_executed=True,generated_dma_hook_executed=True,hardware_verified=False)
    (output/'result.json').write_bytes((json.dumps(result,indent=2)+'\n').encode());return result

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--driver',type=Path,required=True);p.add_argument('--dma-helper',type=Path,required=True)
    a=p.parse_args();r=run(a.output,a.driver,a.dma_helper);print(json.dumps({'passed':r['passed'],'cases':r['cases']}))
