"""Actual ABOX observer/producer and exact generated callback event blocks."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
from prepare_abox_pm import HERE,SOURCES,PATCHED_SHA,ENABLE_EVENT,BEGIN_EVENT,IPC_EVENT,END_EVENT,WORK_BEGIN,WORK_GET,WORK_GATE,WORK_END,QUEUE_PUT,QUEUE_GET,EVENT_BLOCKS,FW_EVENT,NOTIFY_BEGIN,NOTIFY_READY,NOTIFY_GATE,NOTIFY_SUSPEND,NOTIFY_BAD,NOTIFY_DONE,QOS_GET,QOS_PUT,QOS_WORK_BEGIN,QOS_WORK_END,QOS_PATCHED_SHA,QOS_TARGET_SHA,PROBE_GET,LATE_BODY,event_digest
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
#define __init
#define pr_err printf
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
#define ABOX_CPU_GEAR_ABSOLUTE 0xABC0ABC0U
#define DEFAULT_CPU_GEAR_ID 0xAB0CDEFAU
#define ARRAY_SIZE(a) (sizeof(a)/sizeof((a)[0]))
#define PM_SUSPEND_PREPARE 1
#define NOTIFY_DONE 0
#define NOTIFY_BAD 0x8002
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
static struct abox_data *p_abox_data;
static unsigned int late_calls;
struct abox_qos_req {unsigned int id,val;};
enum abox_qos_class {ABOX_QOS_AUD,ABOX_QOS_OTHER};
struct pm_qos_request {int active,value;};
struct abox_qos {unsigned int val;struct abox_qos_req req_array[64];struct pm_qos_request pm_qos;enum abox_qos_class qos_class;};
static struct abox_qos abox_qos_aud,other_qos[5];
static struct abox_qos *abox_qos_array[]={&abox_qos_aud,&other_qos[0],&other_qos[1],&other_qos[2],&other_qos[3],&other_qos[4]};
struct work_struct {int unused;};
static int abox_qos_lock,abox_qos_work;
static struct device *dev_abox;
static unsigned int qos_locked,qpm_get_calls,q_busy_calls;
static unsigned int mode,phase,node_refs,device_refs,device_locked,ipc_locked,event_locked,irq,ipc_calls,pm_get_calls,pm_put_calls,gate_calls,clearable_calls,suspend_calls;
static struct device_node *of_find_compatible_node(void*a,void*b,const char*c){if(a || b || strcmp(c,"samsung,abox"))abort();if(mode==1)return NULL;++node_refs;return &node;}
static struct platform_device *of_find_device_by_node(struct device_node*p){if(p!=&node || node_refs!=1)abort();if(mode==2)return NULL;++device_refs;return &controller;}
static void of_node_put(struct device_node*p){if(p!=&node || !node_refs--)abort();}
static void put_device(struct device*p){if(p!=&controller.dev || device_locked || !device_refs--)abort();}
static int device_trylock(struct device*p){if(p!=&controller.dev || device_locked || device_refs!=1)abort();if(mode==3)return 0;device_locked=1;return 1;}
static void device_unlock(struct device*p){if(!device_locked || ipc_locked || event_locked || qos_locked)abort();device_locked=0;}
static struct abox_data *dev_get_drvdata(struct device*p){if(!device_locked)abort();return mode==5?NULL:&box;}
static void lock_model(int*p,unsigned long*f){*f=irq;irq=1;if(p==&box.ipc_queue_lock){if(!device_locked || ipc_locked++ || event_locked)abort();}else if(p==&abox_qos_lock){if(!device_locked || qos_locked++ || ipc_locked || event_locked)abort();}else{if(event_locked++ || ipc_locked || qos_locked)abort();}}
static void unlock_model(int*p,unsigned long f){if(!irq)abort();if(p==&box.ipc_queue_lock){if(!ipc_locked)abort();ipc_locked=0;}else if(p==&abox_qos_lock){if(!qos_locked)abort();qos_locked=0;}else{if(!event_locked)abort();event_locked=0;}irq=f;}
#define spin_lock_irqsave(p,f) lock_model((p),&(f))
#define spin_unlock_irqrestore(p,f) unlock_model((p),(f))
static int abox_cpu_pm_ipc(struct abox_data*d,bool resume){if(d!=&box || resume)abort();++ipc_calls;return mode==17?-EIO:0;}
static int work_pending(int*p){if((p!=&box.ipc_work && p!=&abox_qos_work) || !device_locked || qos_locked)abort();return *p;}
static int pm_runtime_get_sync(struct device*p){if(p!=&controller.dev)abort();++pm_get_calls;return mode==26?-EIO:1;}
static int abox_can_calliope_ipc(struct device*p,struct abox_data*d){if(p!=&controller.dev || d!=&box)abort();++gate_calls;return mode!=27;}
static void pm_runtime_mark_last_busy(struct device*p){if(p!=&controller.dev)abort();++q_busy_calls;}
static int pm_runtime_put_autosuspend(struct device*p){if(p!=&controller.dev || ((mode==54 || mode==55 || mode==56 || mode==60) && q_busy_calls!=1))abort();++pm_put_calls;return mode==56?-EIO:0;}
static int pm_runtime_get(struct device*p){if(p!=&controller.dev)abort();++qpm_get_calls;if(mode>=66)++p->power.usage_count;return mode==55?-EIO:mode==67?-115:0;}
static int pm_runtime_put_sync_suspend(struct device*p){if(p!=&controller.dev)abort();++late_calls;--p->power.usage_count;return mode==71?-EBUSY:mode==78?(-2147483647-1):0;}
static int abox_is_clearable(struct device*p,struct abox_data*d){if(p!=&controller.dev || d!=&box)abort();++clearable_calls;return mode!=39;}
static int pm_runtime_suspend(struct device*p){if(p!=&controller.dev)abort();++suspend_calls;return mode==41?-EBUSY:0;}
static int pm_qos_request_active(struct pm_qos_request*p){return p->active;}
static void pm_qos_add_request(struct pm_qos_request*p,enum abox_qos_class c,int v){p->active=1;p->value=v;}
static void pm_qos_update_request(struct pm_qos_request*p,int v){p->value=v;}
static int pm_qos_request(enum abox_qos_class c){return abox_qos_aud.pm_qos.value;}
static void setup(void){
 memset(&controller,0,sizeof(controller));memset(&box,0,sizeof(box));memset(&abox_qos_aud,0,sizeof(abox_qos_aud));memset(other_qos,0,sizeof(other_qos));for(unsigned int i=0;i<5;++i)other_qos[i].qos_class=ABOX_QOS_OTHER;abox_qos_work=0;dev_abox=&controller.dev;
 controller.dev.driver=mode==4?&foreign_driver:&samsung_abox_driver.driver;
 p_abox_data=&box;
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
 if(mode==46){abox_qos_aud.req_array[0]=(struct abox_qos_req){DEFAULT_CPU_GEAR_ID,100};abox_qos_aud.val=100;controller.dev.power.usage_count=1;controller.dev.power.runtime_status=0;}
 if(mode==47){abox_qos_aud.req_array[0]=(struct abox_qos_req){DEFAULT_CPU_GEAR_ID,0};abox_qos_aud.val=100;abox_qos_work=1;}
 if(mode==48){abox_qos_aud.req_array[0]=(struct abox_qos_req){ABOX_CPU_GEAR_ABSOLUTE,80};abox_qos_aud.val=80;}
 if(mode==49){for(unsigned int i=0;i<64;++i)abox_qos_aud.req_array[i].id=i+1;}
 if(mode==50)abox_qos_aud.req_array[1]=(struct abox_qos_req){7,1};
 if(mode==51){abox_qos_aud.req_array[0]=(struct abox_qos_req){7,1};abox_qos_aud.req_array[1]=(struct abox_qos_req){7,2};}
 if(mode==52)dev_abox=&other.dev;
 if(mode==53)dev_abox=NULL;
 if(mode==57){abox_qos_aud.req_array[0]=(struct abox_qos_req){42,120};abox_qos_work=1;}
 if(mode==61){abox_qos_aud.req_array[0]=(struct abox_qos_req){42,0xffffffffU};abox_qos_aud.val=0xffffffffU;}

}
'''
MAIN=r'''
int main(int argc,char**argv){
 unsigned int begin,completed,saved_irq;struct platform_device old_dev;struct abox_data old_box;struct abox_qos old_qos;int old_qos_work;
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
 if(mode>=36){
  if(mode==36 || mode==37 || mode==38 || mode==45){int raw=mode==36?-EAGAIN:mode==37?-EIO:mode==45?(-2147483647-1):0;int expected=raw==-EAGAIN?0:raw;if(event_firmware(&controller.dev,raw)!=expected)return 89;}
  if(mode>=39 && mode<=42){int action=mode==42?2:PM_SUSPEND_PREPARE;int expected=mode==41?NOTIFY_BAD:NOTIFY_DONE;if(event_notifier(&controller.dev,&box,action)!=expected || clearable_calls!=(mode==42?0:1) || suspend_calls!=((mode==40 || mode==41)?1:0))return 90;}
  if(mode==43)n10_abox_history.notify_stage=7;
 }
 if(mode==54 || mode==55 || mode==56 || mode==60){
  if(mode==60){n10_abox_history.qos_gets=0xffffffffU;n10_abox_history.qos_puts=0xffffffffU;}
  abox_qos_aud.req_array[0]=(struct abox_qos_req){DEFAULT_CPU_GEAR_ID,100};abox_qos_apply(&abox_qos_aud);abox_qos_aud.req_array[0].val=0;abox_qos_apply(&abox_qos_aud);if(qpm_get_calls!=1 || pm_put_calls!=1 || q_busy_calls!=1)return 92;
 }
 if(mode==46){abox_qos_apply(&abox_qos_aud);if(qpm_get_calls || pm_put_calls)return 94;}
 if(mode==62){struct abox_qos q={0};q.qos_class=ABOX_QOS_OTHER;q.req_array[0]=(struct abox_qos_req){42,100};abox_qos_apply(&q);if(qpm_get_calls || pm_put_calls || q.val!=100)return 95;}
 if(mode==63)n10_abox_history.qos_worker_inflight=2;
 if(mode==64)event_qos_worker_begin();
 if(mode==65)abox_qos_work_func(NULL);
 if(mode>=66){
  if(mode==68){memset(&n10_abox_history,0,sizeof(n10_abox_history));n10_abox_event_device=NULL;p_abox_data=NULL;if(samsung_abox_late_initcall()!=0 || late_calls)return 97;}
  if(mode==69){box.pdev=NULL;if(samsung_abox_late_initcall()!=0 || late_calls)return 98;box.pdev=&controller;}
  if(mode==72)n10_abox_history.probe_get_count=0xffffffffU;
  if(mode==73)controller.dev.power.usage_count=-1;
  if(mode<=73 || mode==78){
   event_probe_get(&controller.dev);
   if(qpm_get_calls!=1)return 99;
   if(mode==70 || mode==71 || mode==78){if(samsung_abox_late_initcall()!=0 || late_calls!=1 || controller.dev.power.usage_count)return 100;}
  }
  if(mode==74)n10_abox_late_state(4);
  if(mode==77)n10_abox_lifecycle(&other.dev,0,0,0,1);
 }
 if(n10_abox_pm_read(NULL,2)!=-EINVAL)return 80;
 for(phase=0;phase<3;++phase){
  setup();irq=saved_irq=mode==23?1:phase%2;old_box=box;old_dev=controller;old_qos=abox_qos_aud;old_qos_work=abox_qos_work;
  if(!(mode==12 && phase==1))n10_abox_pm_capture(phase,begin+(mode==14 && phase==1));
  if(mode==13 && phase==1)n10_abox_pm_capture(phase,begin);
  if(node_refs || device_refs || device_locked || ipc_locked || event_locked || qos_locked || irq!=saved_irq || memcmp(&old_box,&box,sizeof(box)) || memcmp(&old_dev,&controller,sizeof(controller)) || memcmp(&old_qos,&abox_qos_aud,sizeof(old_qos)) || old_qos_work!=abox_qos_work)return 81;
 }
 if(mode==58)n10_abox_samples[1].qos_seen=0;
 if(mode==76)n10_abox_samples[1].probe_get_negative=1;
 completed=begin+1;if(!completed)completed=1;n10_report_abox_pm(mode==16?begin:completed);return 0;
}
'''

def run(output,driver,dma_helper):
    output=Path(output).resolve();qos_driver=Path(driver).with_name('abox_qos.c').read_bytes();driver=Path(driver).read_bytes()
    if hashlib.sha256(qos_driver).hexdigest()!=QOS_PATCHED_SHA or any(qos_driver.count(b)!=1 for b in (QOS_GET,QOS_PUT,QOS_WORK_BEGIN,QOS_WORK_END)):raise ValueError('Prepared QoS driver differs')
    start=qos_driver.index(b'static unsigned int abox_qos_target(');end=qos_driver.index(b'static void abox_qos_apply(',start);qos_target=qos_driver[start:end]
    if hashlib.sha256(qos_target).hexdigest()!=QOS_TARGET_SHA:raise ValueError('Pinned QoS target helper differs')
    apply_end=qos_driver.index(b'static void abox_qos_work_func(',end);qos_apply=qos_driver[end:apply_end];worker_end=qos_driver.index(b'static DECLARE_WORK(',apply_end);qos_worker=qos_driver[apply_end:worker_end]
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
    start=driver.index(b'static int __init samsung_abox_late_initcall(');end=driver.index(b'late_initcall(samsung_abox_late_initcall);',start);late=driver[start:end]
    if driver.count(PROBE_GET)!=1 or driver.count(LATE_BODY)!=1:raise ValueError('Lifecycle blocks differ')
    hooks='static void event_probe_get(struct device*dev){\n'+PROBE_GET.decode()+'\n}\n'+late.decode()
    hooks+='static int event_enable(struct device*dev,int ret){\n'+ENABLE_EVENT.decode()+'return ret;\n}\n'
    hooks+='static int event_disable(struct device*dev,struct abox_data*data,unsigned int state){\n'+BEGIN_EVENT.decode()+IPC_EVENT.decode()+'\n'+END_EVENT.decode()+'return 0;\n}\n'
    hooks+='static void event_worker(struct device*dev,struct abox_data*data){\n#ifdef CONFIG_NOTE10_ABOX_PM_AUDIT\nbool n10_can;\n#endif\n'+WORK_BEGIN.decode()+WORK_GET.decode()+'\n'+WORK_GATE.decode()+'\n; }\npm_runtime_put_autosuspend(dev);\n'+WORK_END.decode()+'}\n'
    hooks+='static int event_queue_put(struct abox_data*data,int ret){\n'+QUEUE_PUT.decode()+'return ret;\n}\n'
    hooks+='static int event_queue_get(struct abox_data*data,int ret){\n'+QUEUE_GET.decode()+'return ret;\n}\n'
    hooks+='static int event_firmware(struct device*dev,int ret){\n'+FW_EVENT.decode()+'if(ret==-EAGAIN)ret=0;return ret;\n}\n'
    hooks+='static int event_notifier(struct device*dev,struct abox_data*data,unsigned long action){int ret;\n#ifdef CONFIG_NOTE10_ABOX_PM_AUDIT\nbool n10_clearable;\n#endif\nswitch(action){case PM_SUSPEND_PREPARE:\n'+NOTIFY_BEGIN.decode()+NOTIFY_READY.decode()+NOTIFY_GATE.decode()+'\nret=pm_runtime_suspend(dev);\n'+NOTIFY_SUSPEND.decode()+'if(ret<0){\n'+NOTIFY_BAD.decode()+'return NOTIFY_BAD;} }break;default:break;}\n'+NOTIFY_DONE.decode()+'return NOTIFY_DONE;}\n'
    hooks+='static void event_qos_get(void){\n'+QOS_GET.decode()+'\n}\nstatic void event_qos_put(void){\n'+QOS_PUT.decode()+'\n}\n'
    hooks+='static void event_qos_worker_begin(void){\n'+QOS_WORK_BEGIN.decode()+'}\n'
    exe=build('abox',STUB+sources['abox_pm_contract.h'].decode()+qos_target.decode()+clean(sources['abox_qos_pm_backend.c'].decode())+clean(sources['abox_pm_backend.c'].decode())+checksum+clean(sources['abox_pm_probe.c'].decode())+qos_apply.decode()+qos_worker.decode()+hooks+MAIN)
    rows=[]
    for mode in range(79):
        ran=subprocess.run([str(exe),str(mode)],capture_output=True,timeout=15);(output/f'mode-{mode}.log').write_bytes(ran.stdout+ran.stderr)
        if ran.returncode:raise ValueError('ABOX reference/lock/IRQ/state or unchanged callback result failed mode '+str(mode))
        text=ran.stdout.decode()
        if mode==44:text='\n'.join(line for line in text.splitlines() if not (line.startswith('N10ABR1 ') and 'phase=1 ' in line))
        if mode==75:text='\n'.join(line for line in text.splitlines() if not (line.startswith('N10ABL1 ') and 'phase=1 ' in line))
        if mode==59:text='\n'.join(line for line in text.splitlines() if not (line.startswith('N10ABQ1 ') and 'phase=1 ' in line))
        try:
            observation=decode(text,ID,1 if mode==15 else 2);accepted=True
        except ValueError:accepted=False
        if accepted:
            if observation['abox_driver_idle_state_observed']!=(mode in (0,15,23,27,29,30,35,38,39,40,42,49,54,60,62,65,66,67,68,69,70,71,72,73,78)):raise ValueError('ABOX idle interpretation differs')
            expected={25:dict(worker_starts=1,worker_stage=1,worker_inflight=1),
                26:dict(worker_starts=1,worker_finishes=1,worker_stage=4,pm_get_result=5,pm_get_negative=1),
                27:dict(gate_seen=1,can_ipc=0,worker_finishes=1),
                28:dict(worker_starts=2,worker_finishes=1,worker_stage=3,worker_inflight=1,can_ipc=1),
                29:dict(worker_stage=4,worker_inflight=0,pm_get_result=1,can_ipc=1),
                30:dict(put_busy=1,get_empty=1),31:dict(work_pending=1),35:dict(puts=1,gets=1,worker_starts=0,worker_finishes=0,worker_stage=4,gate_seen=1),
                36:dict(fw_downloads=1,fw_result=11,fw_negative=1),37:dict(fw_result=5,fw_negative=1),
                38:dict(fw_downloads=1,fw_result=0,fw_negative=0),39:dict(notify_prepares=1,notify_stage=6,clearable_seen=1,clearable=0,suspend_calls=0,notify_done=1),
                40:dict(clearable=1,suspend_calls=1,suspend_result=0,notify_stage=6,notify_done=1),
                41:dict(clearable=1,suspend_calls=1,suspend_result=16,suspend_negative=1,notify_stage=5,notify_bad=1,notify_done=0),42:dict(notify_prepares=0,notify_stage=0),45:dict(fw_result=0x80000000,fw_negative=1),
                46:dict(qos_registered=1,qos_active=1,qos_target=100,qos_applied=100,qos_default=100,qos_first_id=0xAB0CDEFA),
                47:dict(qos_target=0,qos_applied=100,qos_work_pending=1,qos_active=0),
                48:dict(qos_absolute=80,qos_target=80,qos_active=1),49:dict(qos_registered=64,qos_active=0),
                54:dict(qos_gets=1,qos_puts=1,qos_get_negative=0,qos_put_negative=0),55:dict(qos_get_result=5,qos_get_negative=1),
                56:dict(qos_put_result=5,qos_put_negative=1),57:dict(qos_first_id=42,qos_target=120,qos_applied=0,qos_work_pending=1),
                60:dict(qos_gets=0,qos_puts=0),61:dict(qos_target=0xffffffff,qos_applied=0xffffffff,qos_first_value=0xffffffff),64:dict(qos_worker_starts=1,qos_worker_inflight=1),65:dict(qos_worker_starts=1,qos_worker_finishes=1,qos_worker_inflight=0)}
            expected.update({66:dict(probe_get_count=1,probe_get_before=0,probe_get_after=1,late_state=0),
                67:dict(probe_get_count=1,probe_get_result=115,probe_get_negative=1,probe_get_after=1),
                68:dict(late_state=1,late_put_count=0,probe_get_count=1),69:dict(late_state=2,late_put_count=0),
                70:dict(late_state=3,late_put_count=1,late_put_before=1,late_put_after=0),
                71:dict(late_state=3,late_put_count=1,late_put_result=16,late_put_negative=1,late_put_after=0),
                72:dict(probe_get_count=0,probe_get_after=1),73:dict(probe_get_before=1,probe_get_before_negative=1,probe_get_after=0),
                78:dict(late_state=3,late_put_result=0x80000000,late_put_negative=1)})
            snapshot=observation['phases'][1]['snapshot']
            if any(snapshot[k]!=v for k,v in expected.get(mode,{}).items()):raise ValueError('ABOX worker/queue interpretation differs')
        if accepted!=(mode in (0,15,17,18,19,20,23,24,25,26,27,28,29,30,31,35,36,37,38,39,40,41,42,45,46,47,48,49,54,55,56,57,60,61,62,64,65,66,67,68,69,70,71,72,73,78)):raise ValueError('ABOX strict decoder differs mode '+str(mode))
        rows.append(dict(mode=mode,passed=True,accepted=accepted))
    disabled=build('disabled',STUB.replace('#define CONFIG_NOTE10_ABOX_PM_AUDIT','')+sources['abox_pm_contract.h'].decode()+qos_target.decode()+qos_apply.decode()+qos_worker.decode()+hooks+'int main(void){mode=17;setup();if(event_enable(&controller.dev,-EIO)!=-EIO || event_disable(&controller.dev,&box,3)!=0 || ipc_calls!=1)return 85;event_worker(&controller.dev,&box);if(pm_get_calls!=1 || gate_calls!=1 || pm_put_calls!=1 || event_queue_put(&box,-EBUSY)!=-EBUSY || event_queue_get(&box,-ENODATA)!=-ENODATA)return 88;mode=41;if(event_firmware(&controller.dev,-EAGAIN)!=0 || event_notifier(&controller.dev,&box,PM_SUSPEND_PREPARE)!=NOTIFY_BAD || clearable_calls!=1 || suspend_calls!=1)return 91;mode=54;abox_qos_aud.req_array[0]=(struct abox_qos_req){DEFAULT_CPU_GEAR_ID,100};abox_qos_apply(&abox_qos_aud);abox_qos_aud.req_array[0].val=0;abox_qos_apply(&abox_qos_aud);if(qpm_get_calls!=1 || pm_put_calls!=2)return 93;abox_qos_work_func(NULL);if(qpm_get_calls!=1 || pm_put_calls!=2)return 96;mode=70;setup();event_probe_get(&controller.dev);if(controller.dev.power.usage_count!=1 || samsung_abox_late_initcall()!=0 || late_calls!=1 || controller.dev.power.usage_count)return 101;mode=68;p_abox_data=NULL;if(samsung_abox_late_initcall()!=0 || late_calls!=1)return 102;return 0;}')
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
        patched_driver_sha256=PATCHED_SHA,patched_qos_driver_sha256=QOS_PATCHED_SHA,qos_target_sha256=QOS_TARGET_SHA,event_blocks_sha256=event_digest(),generated_dma_sha256=hashlib.sha256(raw).hexdigest(),
        harness_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),generated_lifecycle_blocks_executed=True,actual_late_initcall_executed=True,actual_backend_executed=True,actual_probe_executed=True,
        generated_event_blocks_executed=True,generated_worker_blocks_executed=True,generated_queue_blocks_executed=True,generated_prepare_blocks_executed=True,actual_qos_backend_executed=True,actual_qos_apply_executed=True,actual_qos_worker_executed=True,generated_qos_blocks_executed=True,default_off_blocks_executed=True,generated_dma_hook_executed=True,hardware_verified=False)
    (output/'result.json').write_bytes((json.dumps(result,indent=2)+'\n').encode());return result

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--driver',type=Path,required=True);p.add_argument('--dma-helper',type=Path,required=True)
    a=p.parse_args();r=run(a.output,a.driver,a.dma_helper);print(json.dumps({'passed':r['passed'],'cases':r['cases']}))
