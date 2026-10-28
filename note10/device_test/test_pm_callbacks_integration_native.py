"""Execute final prepared worker -> CPU helper -> failure producer chain."""
import argparse,hashlib,json,re,subprocess,sys
from pathlib import Path
from test_fsys_pm_native import function
from test_pm_post_arch_native import WORKER_STUB
from test_pm_callbacks_producer import MOCK
from decode_pm_callbacks import decode
HERE=Path(__file__).resolve().parent
ADD=r'''
#include <errno.h>
#define CONFIG_NOTE10_PM_CALLBACK_INVENTORY 1
#define CONFIG_NOTE10_PM_IRQ_TEST 1
#define READ_ONCE(x) (x)
#define PM_SUSPEND_MEM 3
#define N10_Q_PM_ENTERED 7
static unsigned int online=255,enable_calls,disable_calls,cb_calls;
static unsigned long online_mask=255;
#define cpu_online_mask (&online_mask)
#define cpumask_bits(p) (p)
static int num_online_cpus(void){return online==255?8:online==1?1:0;}
static int irqs_disabled(void){return 0;}
static int raw_smp_processor_id(void){return 0;}
struct active_type {unsigned int qgeneration,qphase,pm_called;} active={1,7,1},*n10_pm_active=&active;
struct n10_pmu_noirq_sample {unsigned int generation;};
static int n10_pm_noirq_ready(int s){return s==3;}
static int disable_nonboot_cpus(void){disable_calls++;online=online_mask=1;return 0;}
static void enable_nonboot_cpus(void){enable_calls++;online=online_mask=mode==13?254:255;}
static int n10_pmu_noirq_read(struct n10_pmu_noirq_sample *p,unsigned int g){(void)p;(void)g;return mode==19?-EIO:0;}
static void n10_pmu_cpu_capture(unsigned int g){(void)g;}
static int n10_pmu_cpu_read(struct n10_pmu_noirq_sample *p,unsigned int g){(void)p;(void)g;return mode==18?-EIO:0;}
static int n10_pm_irq_capture(unsigned int g){(void)g;return mode==17?-EIO:0;}
static int n10_cb_capture(unsigned int phase,unsigned int g){if(phase!=1||g!=1||online!=1)abort();cb_calls++;return (mode>=12 && mode<=16)?-EBUSY:0;}
static void n10_report_pm_irq_failure(unsigned int g){(void)g;}
static int n10_report_pm_irq(unsigned int g){(void)g;return 0;}
static int n10_report_pm_edge(unsigned int g){(void)g;return 0;}
'''
def clean(n):return '\n'.join(x for x in (HERE/n).read_text(encoding='utf-8-sig').splitlines() if not x.startswith('#include'))+'\n'
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--source-root',required=True);ap.add_argument('--output',required=True);a=ap.parse_args();root=Path(a.source_root);out=Path(a.output);out.mkdir(parents=True,exist_ok=True);cpu=(root/'kernel/power/note10_pm_cpus.c').read_text();worker=(root/'arch/arm64/mm/note10_pm_timer_roundtrip.c').read_text()
 stub=WORKER_STUB.replace('static int n10_pm_devices_test(struct n10_pm_result*p){++pm_calls;p->qgeneration=2;p->devices=mode==2?0:1;p->resumed=1;return mode==1?-5:0;}','static int n10_pm_devices_test(struct n10_pm_result *p);').replace('static u32 n10_frame_checksum(const char*p,int n){(void)p;(void)n;return 0;}','static u32 n10_frame_checksum(const char*p,int n){u32 h=2166136261U;while(n--)h=(h^(unsigned char)*p++)*16777619U;return h;}')
 mock=MOCK.replace('if(mode){','if(mode>=12 && mode<=16){').replace('family[1].attempted','family[mode==13?1:(mode==12?0:mode-13)].attempted').replace('family[1].error','family[mode==13?1:(mode==12?0:mode-13)].error').replace('if(mode>=12 && mode<=16){','if(mode>=17 && mode<=19){p[1].seen=0;return -EIO;}if(mode>=12 && mode<=16){')
 cpu_contract=clean('pm_cpus_contract.h'); code=stub+ADD+clean('pm_callbacks_contract.h')+cpu_contract+'\nstatic struct n10_pm_cpus_sample n10_pm_cpus_last;\n'+function(cpu,'static unsigned int n10_pm_cpus_bits(')+function(cpu,'int n10_pm_cpus_roundtrip(')+mock+clean('pm_callbacks_probe.c')+'''\nstatic int n10_pm_devices_test(struct n10_pm_result *p){int r;++pm_calls;p->qgeneration=2;p->devices=1;p->resumed=1;r=n10_pm_cpus_roundtrip(1);if(mode==13 && r!=-EBUSY)abort();return r;}\n'''+function(worker,'static void n10_pm_worker(struct work_struct *unused)\n{')+'''\nint main(int argc,char **argv){mode=atoi(argv[1]);n10_pm_worker(NULL);if(cb_calls!=(mode>=17?0:1) || disable_calls!=(mode==19?0:1) || enable_calls!=(mode==19?0:1) || online!=(mode==13?254:255))abort();return 0;}\n'''
 src=out/'integration.c';src.write_text(code,encoding='utf-8');cc=Path('host-tools/windows-build/llvm-mingw/llvm-mingw-20261006-ucrt-x86_64/bin/clang.exe') if sys.platform=='win32' else 'cc';exe=out/('integration.exe' if sys.platform=='win32' else 'integration');r=subprocess.run([str(cc),'-std=gnu11','-O2',str(src),'-o',str(exe)],capture_output=True,timeout=60);(out/'compile.log').write_bytes(r.stdout+r.stderr)
 if r.returncode:raise RuntimeError(r.stderr.decode(errors='replace'))
 disabled=code.replace('#define CONFIG_NOTE10_PM_CALLBACK_INVENTORY 1','#undef CONFIG_NOTE10_PM_CALLBACK_INVENTORY').replace('if(mode==13 && r!=-EBUSY)abort();','if(mode==13 && r!=-EIO)abort();').replace('if(cb_calls!=(mode>=17?0:1) || disable_calls!=(mode==19?0:1) || enable_calls!=(mode==19?0:1) || online!=(mode==13?254:255))abort();','if(cb_calls || disable_calls!=1 || enable_calls!=1 || online!=(mode==13?254:255))abort();')
 ds=out/'integration-disabled.c';ds.write_text(disabled,encoding='utf-8');de=out/('integration-disabled.exe' if sys.platform=='win32' else 'integration-disabled');r=subprocess.run([str(cc),'-std=gnu11','-O2',str(ds),'-o',str(de)],capture_output=True,timeout=60);(out/'disabled-compile.log').write_bytes(r.stdout+r.stderr)
 if r.returncode:raise RuntimeError(r.stderr.decode(errors='replace'))
 for mode in (0,13):
  r=subprocess.run([str(de),str(mode)],capture_output=True,timeout=20)
  (out/f'disabled-{mode}.log').write_bytes(r.stdout+r.stderr)
  if r.returncode:raise RuntimeError('Feature-off mode '+str(mode)+' failed')
 for mode in (0,9,12,13,14,15,16,17,18,19):
  r=subprocess.run([str(exe),str(mode)],capture_output=True,timeout=20);(out/f'mode-{mode}.log').write_bytes(r.stdout+r.stderr)
  if r.returncode:raise RuntimeError(f'worker mode {mode} failed')
  text=r.stdout.decode(errors='replace')
  if mode==0:decode(text,'0123456789abcdef0123456789abcdef',2)
  elif mode in (9,12,14,15,16,17,18,19):
   if 'N10CBQ1' not in text:raise RuntimeError('Failure producer absent')
   try:decode(text,'0123456789abcdef0123456789abcdef',2)
   except ValueError:pass
   else:raise RuntimeError('Failure accepted')
 (out/'result.json').write_text(json.dumps({'generated_c_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (src,ds)},'log_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(out.glob('*.log'))},'harness_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'passed':True,'dependencies_sha256':{n:hashlib.sha256((HERE/n).read_bytes()).hexdigest() for n in ('pm_cpus_contract.h','pm_callbacks_contract.h','pm_callbacks_probe.c','test_pm_post_arch_native.py','test_fsys_pm_native.py','test_pm_callbacks_producer.py','decode_pm_callbacks.py')},'source_sha256':{k:hashlib.sha256((root/p).read_bytes()).hexdigest() for k,p in {'cpu':'kernel/power/note10_pm_cpus.c','worker':'arch/arm64/mm/note10_pm_timer_roundtrip.c','probe':'arch/arm64/mm/note10_pm_callbacks_probe.c'}.items()},'outcomes':[{'case':n,'passed':True} for n in ('success','later_gic_failure','family0_failure','capture_and_restore_failure','family1_failure','family2_failure','family3_failure','irq_failure','pmu_cpu_failure','pmu_pre_failure','off_success','off_restore_failure')],'actual_prepared_cpu_caller':True,'actual_prepared_worker':True,'actual_producer':True,'feature_off_prior_restore_error':True,'four_family_failure_paths':True,'irq_failure_skips_callback':True,'pmu_failure_skips_callback':True,'later_gic_failure_blocks_success':True,'failure_cpu_restored':True,'failure_stdout_rejected':True,'hardware_verified':False},indent=2)+'\n',encoding='utf-8');print('prepared worker/cpu/producer chain passed')
if __name__=='__main__':main()
