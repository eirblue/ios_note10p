"""Execute the actual dispatcher in a synthetic PM owner/generation fixture."""
import argparse,hashlib,json,subprocess,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
STUB=r'''
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>
#define N10_Q_PM_ENTERED 6
#define PM_SUSPEND_MEM 1
#define KSYM_NAME_LEN 128
#define READ_ONCE(x) (x)
static int task,other,irq,preempt,ready=1,pm_mutex,cpu,symbol_fault;
#define current (&task)
static void *n10_pm_owner=&task;
static struct {unsigned int pm_called,qgeneration,qphase;} active={1,1,6},*n10_pm_active=&active;
static unsigned long online=255;
#define cpu_online_mask (&online)
#define cpumask_bits(p) (p)
static int raw_smp_processor_id(void){return cpu;}
static int irqs_disabled(void){return irq;}
static int preemptible(void){return !preempt && !irq;}
static int num_online_cpus(void){return online==255?8:online==1?1:0;}
static int n10_pm_noirq_ready(int x){return x==1 && ready;}
static int core_kernel_text(unsigned long a){return symbol_fault!=1 && (a==1 || a==2);}
static const char *kallsyms_lookup(unsigned long a,unsigned long *size,unsigned long *offset,char **mod,char *buf){(void)a;*size=4;*offset=symbol_fault==2?1:0;if(symbol_fault==3)*mod="module";if(symbol_fault==4){memset(buf,'x',97);buf[97]=0;return buf;}return "builtin_callback";}
static void mutex_lock(int *m){if((*m)++)abort();}
static void mutex_unlock(int *m){if(!*m)abort();--*m;}
'''
BACKENDS=r'''
static int failure=-1,calls[4],same_name_fixture;
#define MAKE_BACKEND(name,n) int name(struct n10_cb_family *f){++calls[n];if(failure==n)return -EBUSY;f->count=(n>=2);if(n==2)f->entry[0].a=1;if(same_name_fixture && n==2){f->entry[0].callback[0]=1;f->entry[0].callback[1]=2;}if(same_name_fixture && n==3)f->entry[0].callback[0]=1;return 0;}
MAKE_BACKEND(n10_cb_cpu_pm,0)
MAKE_BACKEND(n10_cb_irq,1)
MAKE_BACKEND(n10_cb_clocksource,2)
MAKE_BACKEND(n10_cb_clockevent,3)
'''
MAIN=r'''
static struct n10_cb_phase out[3],saved[3];static char symbols[N10_CB_SYMBOLS][N10_CB_NAME];static unsigned int count;static int bad;
#define CHECK(x) do{if(!(x)){fprintf(stderr,"failed line %d\n",__LINE__);return 1;}}while(0)
int main(int argc,char **argv){int mode=atoi(argv[1]),r;unsigned int g=mode==6?0xffffffffU:1;active.qgeneration=g;
 if(mode>=10&&mode<14)failure=mode-10;if(mode==7)same_name_fixture=1;if(mode>=20 && mode<=23){same_name_fixture=1;symbol_fault=mode-19;}
 r=n10_cb_capture(0,g);
 if(mode>=20 && mode<=23){CHECK(r && n10_cb_bad && n10_cb_phases[0].error);return 0;}
 if(failure>=0){CHECK(r==-EBUSY);CHECK(n10_cb_phases[0].family[failure].attempted==1);CHECK(n10_cb_phases[0].family[failure].error==-EBUSY);if(failure<3)CHECK(n10_cb_phases[0].family[failure+1].attempted==0);return 0;}
 CHECK(!r);online=1;CHECK(!n10_cb_capture(1,g));online=255;CHECK(!n10_cb_capture(2,g));CHECK(!n10_cb_read(out,g+1?g+1:1,symbols,&count,&bad));memcpy(saved,out,sizeof(out));
 if(mode==7){CHECK(count==2 && !strcmp(symbols[0],symbols[1]));CHECK(out[0].family[2].entry[0].symbol[0]==1 && out[0].family[2].entry[0].symbol[1]==2 && out[0].family[3].entry[0].symbol[0]==1);return 0;}
 if(mode==0)return 0;
 if(mode==1)r=n10_cb_capture(2,g);
 else if(mode==2){n10_pm_owner=&other;r=n10_cb_capture(0,g);n10_pm_owner=&task;}
 else if(mode==3){active.qgeneration=g+1;irq=1;r=n10_cb_capture(0,g+1);irq=0;}
 else if(mode==4){active.qgeneration=g+1;r=n10_cb_capture(0,g);}
 else if(mode==5)r=n10_cb_capture(3,g);
 else if(mode==8){online=1;cpu=1;r=n10_cb_capture(1,g);cpu=0;online=255;}
 else if(mode==6){active.qgeneration=1;r=n10_cb_capture(0,1);CHECK(!r);CHECK(n10_cb_phases[0].generation==1&&!n10_cb_bad);return 0;}
 else return 2;
 CHECK(r);CHECK(!memcmp(saved,n10_cb_phases,sizeof(saved)));CHECK(n10_cb_read(out,g+1?g+1:1,symbols,&count,&bad));
 active.qgeneration=g+1;CHECK(!n10_cb_capture(0,g+1));CHECK(!n10_cb_bad && n10_cb_phases[0].generation==g+1);return 0;}
'''
def clean(name):
 return '\n'.join(x for x in (HERE/name).read_text(encoding='utf-8-sig').splitlines() if not x.startswith('#include'))+'\n'
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--output',required=True);out=Path(ap.parse_args().output);out.mkdir(parents=True,exist_ok=True)
 src=out/'dispatcher.c';src.write_text(STUB+clean('pm_callbacks_contract.h')+BACKENDS+clean('pm_callbacks_backend.c')+MAIN,encoding='utf-8')
 compiler=Path('host-tools/windows-build/llvm-mingw/llvm-mingw-20261006-ucrt-x86_64/bin/clang.exe') if sys.platform=='win32' else 'cc';exe=out/('dispatcher.exe' if sys.platform=='win32' else 'dispatcher')
 result=subprocess.run([str(compiler),'-std=gnu11','-O2',str(src),'-o',str(exe)],capture_output=True,timeout=60);(out/'compile.log').write_bytes(result.stdout+result.stderr)
 if result.returncode: raise RuntimeError('Dispatcher native compile failed: '+result.stderr.decode(errors='replace'))
 outcomes=[]
 for mode in (0,1,2,3,4,5,6,7,8,10,11,12,13,20,21,22,23):
  p=subprocess.run([str(exe),str(mode)],capture_output=True,timeout=20);(out/f'mode-{mode}.log').write_bytes(p.stdout+p.stderr);outcomes.append({'mode':mode,'passed':p.returncode==0});
  if p.returncode:raise RuntimeError('Dispatcher native mode '+str(mode)+': '+p.stderr.decode(errors='replace'))
 (out/'result.json').write_text(json.dumps({'source_sha256':{n:hashlib.sha256((HERE/n).read_bytes()).hexdigest() for n in ('pm_callbacks_contract.h','pm_callbacks_backend.c')},'generated_c_sha256':hashlib.sha256(src.read_bytes()).hexdigest(),'log_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(out.glob('*.log'))},'harness_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'passed':True,'cases':len(outcomes),'outcomes':outcomes,'actual_dispatcher':True,'hardware_verified':False},indent=2)+'\n',encoding='utf-8')
 print('dispatcher modes passed:',len(outcomes))
if __name__=='__main__':main()
