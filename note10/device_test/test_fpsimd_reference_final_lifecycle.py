"""Exercise final composed chain/capture with a fake FPSIMD environment."""
import argparse,hashlib,json,re,subprocess,sys
from pathlib import Path
from test_pmu_control_final_lifecycle import BASE,EXTRA,MOCK
from test_pm_callbacks_producer import clean
from test_fsys_pm_native import function
from prepare_pmu_control_audit import PINS
ADD=r'''#undef current
#define CONFIG_NOTE10_FPSIMD_REFERENCE_AUDIT 1
struct fpsimd_state {int x;};static struct fpsimd_state other,*fpsimd_last_state;static int read_count;
struct fake_task {void *mm;struct {struct fpsimd_state fpsimd_state;struct {int depth;} fpsimd_kernel_state;} thread;} task,*current=&task;
#define __this_cpu_read(x) (read_count++,(x))
#define atomic_read(x) (*(x))
#define TIF_FOREIGN_FPSTATE 1
#define test_thread_flag(x) 1
static int fpsimd_cpu_pm_notifier(void){return 0;}static struct notifier_block fpsimd_cpu_pm_notifier_block;
'''
MAIN=r'''
#define CHECK(x) do{if(!(x)){fprintf(stderr,"line %d\n",__LINE__);return 1;}}while(0)
static void setup(unsigned int gen){owner=1;ready=1;n10_pm_active=&active;active.qgeneration=gen;active.qphase=1;active.pm_called=1;cpu=irq=pc=ops=0;online=count=1;pm_test_level=1;n10_pm_noirq_last=(struct n10_pm_noirq_sample){1,0,0,1,gen,1,1,1,1,1};}
int main(int argc,char **argv){struct n10_fps_sample out;int ret;mode=atoi(argv[1]);pmus[0].cpu_pm_nb.notifier_call=cpu_pm_pmu_notify;fpsimd_cpu_pm_notifier_block.notifier_call=fpsimd_cpu_pm_notifier;fpsimd_cpu_pm_notifier_block.next=&pmus[0].cpu_pm_nb;cpu_pm_notifier_chain.head=&fpsimd_cpu_pm_notifier_block;task.mm=&task;task.thread.fpsimd_kernel_state.depth=2;fpsimd_last_state=&other;setup(1);
 if(mode==5)mode=8;
 if(mode==3)cpu_pm_notifier_chain.head=&pmus[0].cpu_pm_nb;
 if(mode==4){pmus[0].cpu_pm_nb.next=&fpsimd_cpu_pm_notifier_block;}
 ret=n10_pre_capture(1);if(mode==0){CHECK(!ret);CHECK(!n10_fps_read(&out,2));CHECK(out.row.reference==2 && out.row.chain_count==2 && read_count==1);}else{CHECK(ret);CHECK(n10_fps_read(&out,2));}
 mode=0;pmus[0].cpu_pm_nb.next=0;cpu_pm_notifier_chain.head=&fpsimd_cpu_pm_notifier_block;setup(2);CHECK(!n10_pre_capture(2));CHECK(!n10_fps_read(&out,3));CHECK(out.row.reference==2);CHECK(n10_pre_capture(2));CHECK(n10_fps_read(&out,3));
 setup(3);CHECK(!n10_pre_capture(3));CHECK(!n10_fps_read(&out,4));setup(2);CHECK(n10_pre_capture(2));CHECK(n10_fps_read(&out,4));
 memset(&n10_pre_last,0,sizeof(n10_pre_last));n10_pre_bad=0;setup(0xffffffffU);CHECK(!n10_pre_capture(0xffffffffU));CHECK(!n10_fps_read(&out,1));setup(1);CHECK(!n10_pre_capture(1));CHECK(!n10_fps_read(&out,2));
 return 0;}
'''
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--source-root',required=True,type=Path);ap.add_argument('--output',required=True,type=Path);ap.add_argument('--cc',default='clang');a=ap.parse_args();root=a.source_root;out=a.output;out.mkdir(parents=True,exist_ok=False)
 names={'chain':'kernel/note10_pm_pre_chain.c','capture':'kernel/power/note10_pm_pre_capture.c','branch_chain':'kernel/note10_pm_branch_chain.c','branch_capture':'kernel/power/note10_pm_branch_capture.c','state_chain':'kernel/note10_pmu_state_chain.c','state_capture':'kernel/power/note10_pmu_state_capture.c','bridge':'drivers/perf/note10_pmu_control_bridge.c','control_chain':'kernel/note10_pmu_control_chain.c','control_capture':'kernel/power/note10_pmu_control_capture.c','fps_getter':'arch/arm64/kernel/note10_fpsimd_reference_getter.c','fps_chain':'kernel/note10_fpsimd_reference_chain.c','fps_capture':'kernel/power/note10_fpsimd_reference_capture.c'}
 def raw(n):return re.sub(r'^#include[^\n]*\n','',(root/names[n]).read_text(encoding='utf8'),flags=re.M)
 for n,digest in PINS.items():
  if n.startswith('include/linux/compiler') or n in ('include/linux/string.h','lib/string.c'):
   if hashlib.sha256((root/n).read_bytes()).hexdigest()!=digest:raise ValueError('zero pin differs')
 zero='#define barrier_data(ptr) __asm__ __volatile__("": :"r"(ptr) :"memory")\n'+function((root/'lib/string.c').read_text(),'void memzero_explicit(void *s, size_t count)\n{')+'\n'
 mock=MOCK.replace('GETTER(n10_pre_fpsimd,0)', 'int n10_pre_fpsimd(struct notifier_block *b,struct n10_precond_row *r){if(b!=&fpsimd_cpu_pm_notifier_block)return 0;r->valid=15;r->value[0]=1;r->value[1]=1;r->value[2]=2;r->value[3]=0;return 1;}')
 order=('bridge','branch_chain','branch_capture','state_chain','state_capture','control_chain','control_capture','fps_getter','fps_chain','fps_capture','chain','capture')
 code=BASE+EXTRA+ADD+zero+''.join(clean(n) for n in ('pm_preconditions_contract.h','pm_branch_contract.h','pmu_state_contract.h','pmu_control_contract.h','fpsimd_reference_contract.h'))+mock+''.join(raw(n) for n in order)+MAIN
 (out/'lifecycle.c').write_text(code,encoding='utf8',newline='\n');exe=out/('lifecycle.exe' if sys.platform=='win32' else 'lifecycle');p=subprocess.run([a.cc,'-std=gnu11','-O2',str(out/'lifecycle.c'),'-o',str(exe)],capture_output=True);(out/'compile.log').write_bytes(p.stdout+p.stderr)
 if p.returncode:raise RuntimeError(p.stderr.decode(errors='replace'))
 cases=['success','trylock','post-context','missing-fpsimd','duplicate-fpsimd','prior-getter-error']
 for i,name in enumerate(cases):
  p=subprocess.run([str(exe.resolve()),str(i)],capture_output=True);(out/(name+'.log')).write_bytes(p.stdout+p.stderr)
  if p.returncode:raise RuntimeError(name+': '+p.stderr.decode(errors='replace'))
 proof={'passed':True,'hardware_verified':False,'cases':cases,'source_sha256':{k:hashlib.sha256((root/v).read_bytes()).hexdigest() for k,v in names.items()},'harness_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'generated_sha256':hashlib.sha256(code.encode()).hexdigest(),'log_sha256':{name:hashlib.sha256((out/name).read_bytes()).hexdigest() for name in ['compile.log']+[case+'.log' for case in cases]}};(out/'result.json').write_text(json.dumps(proof,indent=2)+'\n',encoding='utf8')
if __name__=='__main__':main()
