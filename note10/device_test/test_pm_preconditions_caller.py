"""Exercise final prepared CPU caller with feature enabled, disabled and failed."""
import argparse,hashlib,json,subprocess,sys
from pathlib import Path
from test_fsys_pm_native import function
from test_pm_irq_integration_native import STUB
from test_pm_callbacks_producer import clean
HERE=Path(__file__).resolve().parent
EXTRA=r'''
static int pre_calls;
static int n10_pre_capture(unsigned int g){if(g!=1 || online!=1 || irq || !hook_calls)abort();++pre_calls;return mode==9?-EIO:0;}
'''
MAIN=r'''
int main(int argc,char **argv){int r;mode=atoi(argv[1]);active.qgeneration=1;active.qphase=N10_Q_PM_ENTERED;active.pm_called=1;online_mask_storage=online;r=n10_pm_cpus_roundtrip(1);
#ifdef CONFIG_NOTE10_CPU_PM_PRECONDITIONS
 if(mode==0 && (r || pre_calls!=1))abort();if(mode==9 && (r!=-EIO || pre_calls!=1))abort();
#else
 if((mode==0 || mode==9) && (r || pre_calls))abort();
#endif
 if(mode==3 && (r!=-EIO || pre_calls))abort();if(mode==1 && (r!=-EBUSY || pre_calls))abort();if(disable_calls!=1 || enable_calls!=1 || online!=255 || irq)abort();return 0;}
'''
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--source-root',required=True);ap.add_argument('--output',required=True);a=ap.parse_args();root=Path(a.source_root);o=Path(a.output);o.mkdir(parents=True,exist_ok=False);cpu=root/'kernel/power/note10_pm_cpus.c';raw=cpu.read_text(encoding='utf-8');code=STUB+EXTRA+clean('pm_cpus_contract.h')+'\nstatic struct n10_pm_cpus_sample n10_pm_cpus_last;\n'+function(raw,'static unsigned int n10_pm_cpus_bits(')+function(raw,'int n10_pm_cpus_roundtrip(')+MAIN
 cc=Path('host-tools/windows-build/llvm-mingw/llvm-mingw-20261006-ucrt-x86_64/bin/clang.exe') if sys.platform=='win32' else 'cc'
 for label,defines in [('enabled','#define CONFIG_NOTE10_CPU_PM_PRECONDITIONS\n#define CONFIG_NOTE10_PM_IRQ_TEST\n'),('disabled','#define CONFIG_NOTE10_PM_IRQ_TEST\n')]:
  src=o/(label+'.c');exe=o/(label+('.exe' if sys.platform=='win32' else ''));src.write_text(defines+code,encoding='utf-8');r=subprocess.run([str(cc),'-std=gnu11',str(src),'-o',str(exe)],capture_output=True,timeout=60);(o/(label+'-compile.log')).write_bytes(r.stdout+r.stderr)
  if r.returncode:raise RuntimeError(r.stderr.decode(errors='replace'))
  for mode in (0,1,3,9):
   r=subprocess.run([str(exe),str(mode)],capture_output=True,timeout=20);(o/(label+'-'+str(mode)+'.log')).write_bytes(r.stdout+r.stderr)
   if r.returncode:raise RuntimeError(label+' '+str(mode))
 (o/'result.json').write_text(json.dumps({'passed':True,'hardware_verified':False,'cases':['enabled-success','enabled-partial-stop','enabled-irq-error','enabled-pre-error','disabled-success','disabled-partial-stop','disabled-irq-error','disabled-pre-error'],'mandatory_cpu_restore_on_failures':True,'source_sha256':hashlib.sha256(cpu.read_bytes()).hexdigest(),'harness_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'generated_c_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in o.glob('*.c')},'log_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in o.glob('*.log')}},indent=2)+'\n',encoding='utf-8')
if __name__=='__main__':main()
