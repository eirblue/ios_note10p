"""Execute the actual persistent USB helper against deterministic queue/USB stubs."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import shutil
import re
import sys
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
STUB=r"""
#include <stdio.h>
#include <stdlib.h>
#include <stdbool.h>
#include <errno.h>
#ifndef ESTALE
#define ESTALE 116
#endif
#define READ_ONCE(x) (x)
#define WRITE_ONCE(x,v) ((x)=(v))
struct mutex { int held; };
#define DEFINE_MUTEX(x) struct mutex x={0}
static int mutex_trylock(struct mutex *m) { if(m->held)return 0;m->held=1;return 1; }
static void mutex_lock(struct mutex *m) { if(!mutex_trylock(m))abort(); }
static void mutex_unlock(struct mutex *m) {m->held=0;}
typedef struct {int value;} atomic_t;
#define ATOMIC_INIT(x) {x}
static void atomic_set(atomic_t*a,int x){a->value=x;}
static int atomic_read(atomic_t*a){return a->value;}
static void atomic_inc(atomic_t*a){++a->value;}
struct task_struct {int id;};
static struct task_struct t={1},other={2};
static struct task_struct *current=&t;
struct wakeup_source {int lock;bool active;};
#define spin_lock_irqsave(l,f) ((void)(l),(f)=0)
#define spin_unlock_irqrestore(l,f) ((void)(l),(void)(f))
struct work_struct {void(*fn)(struct work_struct*);};
#define DECLARE_WORK(n,f) struct work_struct n={f}
struct usb_notify;
struct usb_notify_dev {struct otg_notify*o_notify;int disable_state;};
struct otg_notify {struct usb_notify*u_notify;bool disable_control,is_wakelock;};
struct usb_notify {int c_type,c_status;struct {int mode;} ndev;struct{int power_role;}typec_status;int disable_state;struct usb_notify_dev udev;void*notifier_wq;struct wakeup_source ws;struct otg_notify*o_notify;};
/* Real vendor ordinals deliberately differ from normalized boolean predicates. */
#define NOTIFY_EVENT_VBUS 1
#define NOTIFY_EVENT_ENABLED 2
#define NOTIFY_EVENT_BLOCKED 5
#define NOTIFY_PERIPHERAL_MODE 2
#define NOTIFY_NONE_MODE 0
#define HNOTIFY_SINK 0
#define NOTIFY_BLOCK_TYPE_NONE 0
#define NOTIFY_BLOCK_TYPE_CLIENT 3
#define NOTIFY_EVENT_STATE 1
#define NOTIFY_EVENT_ALL_DISABLE 15
#define NOTIFY_EVENT_HOST_DISABLE 16
#define NOTIFY_EVENT_CLIENT_DISABLE 17
#define NOTIFY_EVENT_POWER_SOURCE 27
#define NOTIFY_EVENT_PD_CONTRACT 28
#define NOTIFY_EVENT_VBUSPOWER 35
#define NOTIFY_EVENT_VBUS_RESET 29
#define IS_VIRTUAL(e) ((e)&0x100)
static int check_event_type(unsigned long e){return NOTIFY_EVENT_STATE;}
static struct usb_notify u;
static struct otg_notify n;
static int mode,ticks,rsw_off,phy_busy,action_count,action_index;
static struct {int action;struct work_struct*work;} actions[12];
static struct otg_notify*get_otg_notify(void){return &n;}
static bool is_host_cable_enable(struct otg_notify*n){return false;}
static bool is_client_cable_enable(struct otg_notify*n){return u.c_status==NOTIFY_EVENT_ENABLED;}
static bool is_client_cable_block(struct otg_notify*n){return u.c_status==NOTIFY_EVENT_BLOCKED;}
static int set_notify_disable(struct usb_notify_dev*,int);
static bool queue_work(void*q,struct work_struct*w){
 if(mode==4 && action_count>2)return false;
 actions[action_count].action=-1;actions[action_count++].work=w;return true;
}
static int work_busy(struct work_struct *work){return mode==15 && action_count<=2;}
static void msleep(int ms);
int n10_exynos_usb_quiesce_check(bool off){
 if(phy_busy)return -EBUSY;
 if(mode==2 && action_count)return -EAGAIN;
 return rsw_off==off?0:-EBUSY;
}
"""
TAIL=r"""
static int set_notify_disable(struct usb_notify_dev*dev,int policy){
 int ret=n10_usb_policy_enter();if(ret)return ret;
 n10_usb_quiesce_physical(NOTIFY_EVENT_CLIENT_DISABLE);
 u.disable_state=policy;
 actions[action_count++].action=(policy==NOTIFY_BLOCK_TYPE_CLIENT);
 n10_usb_policy_exit();return 0;
}
static void msleep(int ms){
 ++ticks;
 if(mode==1 || (mode==9 && ticks<210))return;
 if(action_index<action_count){
  int i=action_index++;
  if(actions[i].action==-1)actions[i].work->fn(actions[i].work);
  else {
   bool off=actions[i].action;
   u.c_status=off?NOTIFY_EVENT_BLOCKED:NOTIFY_EVENT_ENABLED;
   u.ndev.mode=off?NOTIFY_NONE_MODE:NOTIFY_PERIPHERAL_MODE;
   u.ws.active=(!off || mode==5);
   rsw_off=off;
   if(mode==3 && off)n10_usb_quiesce_physical(NOTIFY_EVENT_VBUS);
   if(mode==6 && off)n10_usb_quiesce_transition_error(-ETIMEDOUT);
   if(mode==10 && !off)u.ndev.mode=NOTIFY_NONE_MODE;
   if(mode==12 && off)n10_usb_quiesce_phy_error(true,-EIO);
   if(mode==13 && !off)n10_usb_quiesce_phy_error(false,-EIO);
  }
 }
}
#define CHECK(x) do{if(!(x)){fprintf(stderr,"line %d: %s\n",__LINE__,#x);return 1;}}while(0)
int main(int argc,char**argv){
 struct n10_pm_result out={0};int begin,end;
 mode=atoi(argv[1]);
 n.u_notify=&u;n.disable_control=n.is_wakelock=true;
 u.o_notify=u.udev.o_notify=&n;u.c_type=NOTIFY_EVENT_VBUS;
 u.c_status=NOTIFY_EVENT_ENABLED;u.ndev.mode=NOTIFY_PERIPHERAL_MODE;u.ws.active=true;
 if(mode==8)phy_busy=1;
 if(mode==11)u.c_status=1;
 begin=n10_usb_quiesce_begin(&out);
 if(mode==14){CHECK(!n10_usb_quiesce_validate());n10_usb_quiesce_physical(NOTIFY_EVENT_VBUS);CHECK(n10_usb_quiesce_validate()==-ESTALE);}
 if(mode==7){struct n10_pm_result unrelated={0};CHECK(n10_usb_quiesce_begin(&unrelated)==-EBUSY);CHECK(!n10_usb_quiesce_end(&unrelated));CHECK(n10_usb_q_owner==current);current=&other;CHECK(set_notify_disable(&u.udev,0)==-EBUSY);current=&t;}
 end=n10_usb_quiesce_end(&out);
 if(mode==0 || mode==7)CHECK(!begin && !end && !n10_usb_q_owner && !rsw_off);
 if(mode==1 || mode==2)CHECK(begin<0 && end<0 && n10_usb_q_owner);
 if(mode==3)CHECK(begin==-ESTALE && end==-ESTALE && !n10_usb_q_owner);
 if(mode==4)CHECK(!begin && end==-EBUSY && n10_usb_q_owner);
 if(mode==5)CHECK(begin==-EBUSY && !end);
 if(mode==6)CHECK(begin==-ETIMEDOUT && !end);
 if(mode==8 || mode==11)CHECK(begin==-EBUSY && !end && !n10_usb_q_owner && !action_count);
 if(mode==9)CHECK(begin==-ETIMEDOUT && !end && !rsw_off && !n10_usb_q_owner && action_index==action_count);
 if(mode==10 || mode==13)CHECK(!begin && end==-EIO && n10_usb_q_owner);
 if(mode==12)CHECK(begin==-EIO && !end && !n10_usb_q_owner);
 if(mode==14)CHECK(!begin && end==-ESTALE && !n10_usb_q_owner);
 if(mode==15)CHECK(begin==-ETIMEDOUT && !end && !n10_usb_q_owner);
 printf("mode=%d begin=%d end=%d ticks=%d generation=%u\n",mode,begin,end,ticks,out.qgeneration);
 return 0;
}
"""
def _runtime_cases(output, compiler, otg_path):
 source=Path(otg_path).read_text()
 signature=source.index('int dwc3_otg_phy_enable(struct otg_fsm *fsm, int owner, bool on)')
 start=source.index('if (n10_usb_quiesce_owned()) {',signature)
 end=source.index('\n\t\t\t} else',start)+len('\n\t\t\t}')
 block=source[start:end]
 if 'pm_runtime_put_noidle(dev)' not in block or 'goto out;' not in block:
  raise ValueError('Generated runtime failure rollback block missing')
 text=r"""
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <errno.h>
static int failure,refs,mmio,phy=1,qos=1,latched;
static bool n10_usb_quiesce_owned(void){return true;}
static int pm_runtime_get_sync(int*dev){++refs;return failure?-EIO:1;}
static void pm_runtime_put_noidle(int*dev){--refs;}
static void n10_usb_quiesce_phy_error(bool off,int error){latched=error;}
static void pm_qos_update_request(int*req,int value){qos=value;}
static void phy_conn(int*dev,int value){phy=value;}
int main(int argc,char**argv){
 int value=0,*dev=&value,ret=0,on=1;
 struct {int pm_qos_int_val,pm_qos_int_req;} state={0},*dotg=&state;
 struct {int*usb2_generic_phy;} core={dev},*dwc=&core;
 failure=atoi(argv[1]);
"""+block+r"""
 ++mmio;
out:
 if(failure){if(ret!=-EIO || refs || mmio || phy || qos || latched!=-EIO)return 1;}
 else {if(ret || refs!=1 || mmio!=1 || latched)return 2;}
 printf("runtime_failure=%d ret=%d refs=%d mmio=%d phy=%d qos=%d\n",failure,ret,refs,mmio,phy,qos);
 return 0;
}
"""
 src=output/'runtime.c';src.write_text(text)
 exe=output/('runtime.exe' if sys.platform=='win32' else 'runtime')
 built=subprocess.run([str(compiler),'-std=c11',str(src),'-o',str(exe)],capture_output=True,timeout=60)
 (output/'runtime-compile.log').write_bytes(built.stdout+built.stderr)
 if built.returncode:raise RuntimeError('Generated runtime rollback native compile failed')
 cases=[]
 for failure in (0,1):
  ran=subprocess.run([str(exe),str(failure)],capture_output=True,timeout=60)
  cases.append({'case':'generated-runtime-get-'+str(failure),'passed':ran.returncode==0,'observation':(ran.stdout+ran.stderr).decode(errors='replace')})
 return cases,hashlib.sha256(block.encode()).hexdigest()

def run(output, usb_helper=None):
 output=Path(output).resolve()
 if not output.is_relative_to((ROOT/'note10/private').resolve()) or output.exists():
  raise ValueError('Fresh private USB native output directory required')
 output.mkdir(parents=True)
 names=('usb_notify_quiesce.c','pm_test_contract.h')
 sources={name:(HERE/name).read_bytes() for name in names}
 if usb_helper: sources['usb_notify_quiesce.c']=Path(usb_helper).read_bytes()
 stub=STUB
 vendor_sources={}
 if usb_helper:
  kernel=Path(usb_helper).parents[3]
  header=(kernel/'include/linux/usb_notify.h').read_bytes()
  from prepare_pm_quiesce import PINS
  if hashlib.sha256(header).hexdigest()!=PINS['include/linux/usb_notify.h']:
   raise ValueError('Pinned USB enum header differs')
  declarations=[]
  for enum in ('otg_notify_events','otg_notify_event_status','otg_notify_evt_type','otg_notify_block_type'):
   found=re.search(r'enum '+enum+r' \{.*?\n\};',header.decode(),re.S)
   if not found:raise ValueError('Vendor enum not found: '+enum)
   declarations.append(found.group())
  stub=re.sub(r'^#define (?:NOTIFY_EVENT_VBUS|NOTIFY_EVENT_ENABLED|NOTIFY_EVENT_BLOCKED|NOTIFY_BLOCK_TYPE_NONE|NOTIFY_BLOCK_TYPE_CLIENT|NOTIFY_EVENT_STATE|NOTIFY_EVENT_ALL_DISABLE|NOTIFY_EVENT_HOST_DISABLE|NOTIFY_EVENT_CLIENT_DISABLE|NOTIFY_EVENT_POWER_SOURCE|NOTIFY_EVENT_PD_CONTRACT|NOTIFY_EVENT_VBUSPOWER|NOTIFY_EVENT_VBUS_RESET) .*$','',stub,flags=re.M)
  stub='\n'.join(declarations)+'\n'+stub
  vendor_sources['include/linux/usb_notify.h']=hashlib.sha256(header).hexdigest()

 src=output/'usb.c';src.write_bytes((stub+sources['pm_test_contract.h'].decode()+sources['usb_notify_quiesce.c'].decode()+TAIL).encode())
 compiler=(ROOT/'host-tools/windows-build/llvm-mingw/llvm-mingw-20261006-ucrt-x86_64/bin/clang.exe'
  if sys.platform=='win32' else shutil.which('cc') or shutil.which('clang'))
 if not compiler: raise RuntimeError('Native C compiler not found')
 exe=output/('usb.exe' if sys.platform=='win32' else 'usb')
 built=subprocess.run([str(compiler),'-std=c11','-Wall','-Wextra',str(src),'-o',str(exe)],capture_output=True,timeout=60)
 (output/'compile.log').write_bytes(built.stdout+built.stderr)
 if built.returncode:raise RuntimeError('USB actual helper native compile failed')
 cases=[]
 for mode in range(16):
  ran=subprocess.run([str(exe),str(mode)],capture_output=True,timeout=60)
  cases.append({'case':mode,'passed':ran.returncode==0,'observation':(ran.stdout+ran.stderr).decode(errors='replace')})
 runtime_hash=None
 if usb_helper:
  runtime, runtime_hash=_runtime_cases(output,compiler,kernel/'drivers/usb/dwc3/otg.c')
  cases.extend(runtime)
 report={'passed':all(c['passed'] for c in cases),'cases':cases,'case_count':len(cases),
  'source_sha256':{n:hashlib.sha256(v).hexdigest() for n,v in sources.items()},
  'generated_runtime_block_sha256':runtime_hash,
  'generated_otg_sha256':hashlib.sha256((kernel/'drivers/usb/dwc3/otg.c').read_bytes()).hexdigest() if usb_helper else None,
  'generated_runtime_block_executed':bool(usb_helper),
  'vendor_sources_sha256':vendor_sources,
  'harness_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
  'actual_usb_helper_executed':True,'hardware_verified':False,'scope':'Actual usb_notify_quiesce.c, deterministic notifier FIFO/RSW/physical-event stubs; no hardware claim.'}
 (output/'result.json').write_text(json.dumps(report,indent=2)+'\n')
 return report
if __name__=='__main__':
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True);parser.add_argument('--usb-helper',type=Path)
 args=parser.parse_args();report=run(args.output,args.usb_helper)
 print(json.dumps(report,indent=2));sys.exit(0 if report['passed'] else 1)
