"""Execute final prepared worker with the real precondition log producer."""
import argparse,hashlib,json,subprocess,sys
from pathlib import Path
from test_fsys_pm_native import function
from test_pm_post_arch_native import WORKER_STUB
from test_pm_callbacks_producer import clean
from test_pm_preconditions_producer import MOCK
from decode_pm_preconditions import decode
HERE=Path(__file__).resolve().parent
ADD=r'''
#include <errno.h>
typedef long long s64;
#define CONFIG_NOTE10_CPU_PM_PRECONDITIONS 1
static int num_online_cpus(void){return 8;}
static int irqs_disabled(void){return 0;}
'''
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--source-root',required=True);ap.add_argument('--output',required=True);a=ap.parse_args();root=Path(a.source_root);out=Path(a.output);out.mkdir(parents=True,exist_ok=False);worker=root/'arch/arm64/mm/note10_pm_timer_roundtrip.c';raw=worker.read_text(encoding='utf-8')
 stub=WORKER_STUB.replace('static u32 n10_frame_checksum(const char*p,int n){(void)p;(void)n;return 0;}','static u32 n10_frame_checksum(const char*p,int n){u32 h=2166136261U;while(n--)h=(h^(unsigned char)*p++)*16777619U;return h;}')
 code=stub+ADD+clean('pm_preconditions_contract.h')+MOCK.replace('mode==1?-EIO:0','mode==10?-EIO:0')+clean('pm_preconditions_probe.c')+function(raw,'static void n10_pm_worker(struct work_struct *unused)\n{')+'\nint main(int argc,char**argv){mode=atoi(argv[1]);n10_pm_worker(NULL);return 0;}\n'
 src=out/'worker.c';src.write_text(code,encoding='utf-8');cc=Path('host-tools/windows-build/llvm-mingw/llvm-mingw-20261006-ucrt-x86_64/bin/clang.exe') if sys.platform=='win32' else 'cc';exe=out/('worker.exe' if sys.platform=='win32' else 'worker');r=subprocess.run([str(cc),'-std=gnu11',str(src),'-o',str(exe)],capture_output=True,timeout=60);(out/'compile.log').write_bytes(r.stdout+r.stderr)
 if r.returncode:raise RuntimeError(r.stderr.decode(errors='replace'))
 for mode in (0,1,10):
  r=subprocess.run([str(exe),str(mode)],capture_output=True,timeout=20);(out/f'mode-{mode}.log').write_bytes(r.stdout+r.stderr)
  if r.returncode:raise RuntimeError('worker failed')
  text=r.stdout.decode();
  if mode==0:decode(text,'0123456789abcdef0123456789abcdef',2)
  else:
   if 'N10PRQ1' not in text:raise RuntimeError('missing failure report')
   try:decode(text,'0123456789abcdef0123456789abcdef',2)
   except ValueError:continue
   raise RuntimeError('failure accepted')
 names=('pm_preconditions_contract.h','pm_preconditions_probe.c','decode_pm_preconditions.py','test_pm_preconditions_producer.py','test_pm_post_arch_native.py','test_fsys_pm_native.py','test_pm_callbacks_producer.py')
 result={'passed':True,'hardware_verified':False,'cases':['success','outer-error','capture-error'],'source_sha256':hashlib.sha256(worker.read_bytes()).hexdigest(),'dependencies_sha256':{n:hashlib.sha256((HERE/n).read_bytes()).hexdigest() for n in names},'harness_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'generated_c_sha256':hashlib.sha256(src.read_bytes()).hexdigest(),'log_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in out.glob('*.log')}};(out/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
if __name__=='__main__':main()
