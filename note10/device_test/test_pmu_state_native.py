"""Exercise the final PMU state getter with bounded allocated stub events."""
import argparse,hashlib,json,re,subprocess
from pathlib import Path
HERE=Path(__file__).resolve().parent
PIN='0c53ebaed164b0825e78116d26611b837b67b6b44fb42735d13c54645de91f47'
STUB=r"""
#include <stdint.h>
#include <stddef.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>
typedef uint32_t u32;
#define PERF_HES_STOPPED 1
#define PERF_HES_UPTODATE 2
#define PERF_EVENT_STATE_ACTIVE 1
#define container_of(p,t,m) ((t*)((char*)(p)-offsetof(t,m)))
#define this_cpu_ptr(p) (p)
struct notifier_block {int (*notifier_call)(void);};
struct pmu {int v;};
struct hw_perf_event {int idx,state;};
struct perf_event {struct pmu *pmu;struct hw_perf_event hw;int cpu,oncpu,state;};
struct pmu_hw_events {unsigned long used_mask[1];struct perf_event *events[32];};
struct arm_pmu {struct notifier_block cpu_pm_nb;int num_events;struct pmu_hw_events *hw_events;unsigned long supported_cpus;struct pmu pmu;};
struct n10_state_row {unsigned int index,kind,num,supported;u32 used,present,owned,observed,running,stopped,uptodate,abnormal,affinity0,unbound,other,oncpu0,active;};
static struct perf_event *watched;static int mode,reads,context=1,intr;
static void inspect(const void *p) {
 uintptr_t a=(uintptr_t)p,start=(uintptr_t)watched,end=start+sizeof(*watched);
 if(watched && a>=start && a<end){reads++;if(mode==1 && p!=&watched->pmu)abort();if(mode==2 && p!=&watched->pmu && p!=&watched->hw.idx)abort();}
}
#define READ_ONCE(x) (inspect(&(x)),(x))
static int n10_pre_context(unsigned int g,int irq,unsigned int preempt){return context && g==1 && irq==1 && preempt==1;}
static int in_interrupt(void){return intr;}
static int test_bit(int i,unsigned long *p){return !!(*p & (1UL<<i));}
static int cpumask_test_cpu(int c,unsigned long *p){return c==0 && (*p&1);}
static int cpu_pm_pmu_notify(void){return 0;}
"""
MAIN=r"""
static int audited(struct arm_pmu *p,struct pmu_hw_events *hw,struct perf_event *events,struct n10_state_row *row,unsigned int generation) {
 struct arm_pmu oldp;struct pmu_hw_events oldhw;struct perf_event oldevents[32];int ret;
 memcpy(&oldp,p,sizeof oldp);memcpy(&oldhw,hw,sizeof oldhw);memcpy(oldevents,events,sizeof oldevents);
 ret=n10_state_pmu(&p->cpu_pm_nb,row,generation);
 if(memcmp(&oldp,p,sizeof oldp)||memcmp(&oldhw,hw,sizeof oldhw)||memcmp(oldevents,events,sizeof oldevents))abort();
 return ret;
}
int main(void){
 struct arm_pmu p={0};struct pmu_hw_events hw={0};struct perf_event events[32]={{0}};struct pmu foreign={0};struct n10_state_row r;int i,ret;
 p.cpu_pm_nb.notifier_call=cpu_pm_pmu_notify;p.num_events=32;p.hw_events=&hw;p.supported_cpus=1;hw.used_mask[0]=0xffffffffUL;
 for(i=0;i<32;i++){events[i].pmu=&p.pmu;events[i].hw.idx=i;events[i].cpu=-1;events[i].oncpu=-1;hw.events[i]=&events[i];}
 events[0].hw.state=PERF_HES_STOPPED;events[1].hw.state=PERF_HES_STOPPED|PERF_HES_UPTODATE;events[2].cpu=0;events[2].oncpu=0;events[2].state=PERF_EVENT_STATE_ACTIVE;events[3].oncpu=0;events[3].state=PERF_EVENT_STATE_ACTIVE;events[4].hw.state=PERF_HES_UPTODATE;events[5].hw.state=4;
 memset(&r,0,sizeof r);ret=audited(&p,&hw,events,&r,1);
 if(ret!=1||r.used!=0xffffffffU||r.observed!=0xffffffffU||r.stopped!=3||r.uptodate!=18||r.abnormal!=48||r.running!=0xffffffccU||r.unbound!=0xfffffffbU||r.affinity0!=4||r.oncpu0!=12||r.active!=12)abort();
 watched=&events[0];events[0].pmu=&foreign;mode=1;reads=0;memset(&r,0,sizeof r);
 if(audited(&p,&hw,events,&r,1)!=-EXDEV||reads!=1)abort();
 events[0].pmu=&p.pmu;events[0].hw.idx=4;mode=2;reads=0;memset(&r,0,sizeof r);
 if(audited(&p,&hw,events,&r,1)!=-EIO||reads!=2)abort();
 events[0].hw.idx=0;context=0;reads=0;memset(&r,0,sizeof r);if(audited(&p,&hw,events,&r,1)!=-EPERM||reads)abort();
 context=1;intr=1;if(audited(&p,&hw,events,&r,1)!=-EPERM||reads)abort();
 intr=0;mode=1;watched=&events[0];reads=0;hw.used_mask[0]&=~1UL;memset(&r,0,sizeof r);if(audited(&p,&hw,events,&r,1)!=1||reads||r.present!=0xfffffffeU)abort();
 watched=0;hw.used_mask[0]|=1UL;hw.events[0]=0;if(audited(&p,&hw,events,&r,1)!=-EIO)abort();
 p.num_events=33;if(audited(&p,&hw,events,&r,1)!=-EINVAL)abort();
 p.num_events=0;memset(&r,0,sizeof r);if(audited(&p,&hw,events,&r,1)!=1||r.used)abort();
 return 0;
}
"""
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--source',required=True);ap.add_argument('--out',required=True);ap.add_argument('--cc',required=True);a=ap.parse_args();root=Path(a.source);out=Path(a.out);out.mkdir(parents=True,exist_ok=False)
 header=(root/'include/linux/perf_event.h').read_bytes()
 if hashlib.sha256(header).hexdigest()!=PIN:raise ValueError('perf header pin')
 txt=header.decode(); patterns=(r'#define PERF_HES_STOPPED\s+0x01',r'#define PERF_HES_UPTODATE\s+0x02',r'PERF_EVENT_STATE_ACTIVE\s*=\s*1',r'struct pmu\s*\*pmu;',r'int\s+oncpu;',r'int\s+cpu;',r'int\s+idx;')
 for pat in patterns:
  if not re.search(pat,txt):raise ValueError('pinned field missing: '+pat)
 source=(root/'drivers/perf/note10_pmu_state_pmu.c').read_text();source='\n'.join(x for x in source.splitlines() if not x.startswith('#include'))
 c=out/'native.c';c.write_text(STUB+'\n'+source+'\n'+MAIN,encoding='utf8',newline='\n')
 exe=out/'native.exe';comp=subprocess.run([a.cc,'-std=gnu11','-Wall','-Wextra','-Werror',str(c),'-o',str(exe)],capture_output=True,check=True);run=subprocess.run([str(exe)],capture_output=True,check=True);(out/'compile.log').write_bytes(comp.stdout+comp.stderr);(out/'run.log').write_bytes(run.stdout+run.stderr)
 (out/'result.json').write_text(json.dumps({'passed':True,'hardware_verified':False,'input_objects_unchanged':True,'perf_event_header_sha256':PIN,'helper_sha256':hashlib.sha256((root/'drivers/perf/note10_pmu_state_pmu.c').read_bytes()).hexdigest(),'harness_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'generated_sha256':hashlib.sha256(c.read_bytes()).hexdigest(),'cases':['32-slots-mixed-unbound-active-and-abnormal','foreign-pmu-first-only','index-mismatch-only','context-rejected','interrupt-rejected','unused-nonnull-unread','null-event','count-33','count-0'],'note':'Synthetic structs model named fields, not kernel binary layout.'},indent=2)+'\n')
if __name__=='__main__':main()
