"""Compile and execute the actual post-PM producer with injected failures."""
import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path
from prepare_pm_post_arch import HERE, SOURCES
from run_probe import ROOT
from decode_pm_post_arch import decode

IDENTITY = '0123456789abcdef0123456789abcdef'
STUB = r'''
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <stdint.h>
typedef uint64_t u64;typedef unsigned int u32;
#define EIO 5
#define N10_XNU_PAYLOAD_SIZE 64ULL
#define N10_RESERVE_BUILD_ID "0123456789abcdef0123456789abcdef"
#define pr_info printf
#define scnprintf snprintf
#define WRITE_ONCE(x,v) ((x)=(v))
#define READ_ONCE(x) (x)
struct n10_cpu_sample {u64 el,mpidr,sctlr,tcr,ttbr1,mair,cntkctl,cntfrq,words,fingerprint;unsigned int seen;};
static struct n10_cpu_sample n10_cpu_samples[8];
static unsigned int mode,cpu,locked,calls,mask_reads;
static void cpus_read_lock(void){if(locked)abort();locked=1;}
static void cpus_read_unlock(void){if(!locked)abort();locked=0;}
static unsigned int n10_online_bits(void){if(!locked)abort();++mask_reads;return (mode==27 && mask_reads==1)||(mode==28 && mask_reads==2)?254:255;}
static unsigned int num_online_cpus(void){return mode==29?7:8;}
static unsigned int smp_processor_id(void){if(!locked)abort();return mode==24?8:cpu;}
static u64 reg_CurrentEL(void){return mode==18 && cpu==3?0:4;}
static u64 reg_mpidr_el1(void){return n10_cpu_samples[cpu].mpidr ^ (mode==19 && cpu==3?1:0);}
static u64 reg_sctlr_el1(void){return n10_cpu_samples[cpu].sctlr ^ ((mode>=10 && mode<=17 && cpu==mode-10)?1:mode==34 && cpu==3?4:0);}
static u64 reg_tcr_el1(void){return n10_cpu_samples[cpu].tcr ^ (mode==20 && cpu==3?1:0);}
static u64 reg_ttbr1_el1(void){return n10_cpu_samples[cpu].ttbr1 ^ (mode==1?0x1234000000000000ULL:mode==21 && cpu==3?2:0);}
static u64 reg_mair_el1(void){return n10_cpu_samples[cpu].mair ^ (mode==22 && cpu==3?1:0);}
#define read_sysreg(name) reg_##name()
static u64 n10_word_fingerprint(const u64 *m,size_t words){
 size_t i;u64 x=14695981039346656037ULL;
 for(i=0;i<words;++i)x=(x^m[i])*1099511628211ULL;
 return x ^ ((mode>=2 && mode<=9 && cpu==mode-2)?1:0);
}
static void on_each_cpu(void(*fn)(void*),void *arg,int wait){
 unsigned int i;if(!locked || !wait)abort();++calls;
 for(i=0;i<8;++i){if(mode==26 && i==7)continue;cpu=i;fn(arg);if(mode==25 && i==7)fn(arg);}
}
'''
MAIN = r'''
int main(int argc,char **argv){
 unsigned int i;u64 mem[8]={1,2,3,4,5,6,7,8},fingerprint;
 mode=atoi(argv[1]);fingerprint=n10_word_fingerprint(mem,8);
 for(i=0;i<8;++i)n10_cpu_samples[i]=(struct n10_cpu_sample){4,0x80000000ULL+i,0x1005,0xabc,0x1234000012345000ULL,0xff,0,26000000,8,fingerprint,1};
 if(mode==23)n10_cpu_samples[3].mair^=1;
 if(mode==31)n10_cpu_samples[3].seen=0;
 if(mode==32)n10_cpu_samples[3].words=7;
 if(mode==33)n10_cpu_samples[3].fingerprint^=1;
 if(mode==35)n10_cpu_samples[3].el=0;
 if(mode==36)n10_cpu_samples[3].ttbr1^=1;
 n10_report_post_arch(mem,mode==30?0:2);
 if(locked || calls!=(mode==27||mode==29||mode==30?0:1))abort();
 return 0;
}
'''


WORKER_STUB = r'''
#include <stdio.h>
#include <string.h>
#include <stdint.h>
#include <stdbool.h>
#include <stdlib.h>
typedef uint64_t u64;typedef unsigned int u32;typedef unsigned char u8;
#define CONFIG_NOTE10_PM_CPUS_TEST 1
#define CONFIG_NOTE10_PM_POST_ARCH 1
#define CONFIG_NOTE10_GIC_ROUNDTRIP 1
#define N10_RESERVE_BUILD_ID "0123456789abcdef0123456789abcdef"
#define N10_XNU_PAYLOAD_SIZE 64ULL
#define N10_XNU_PAYLOAD_SHA256_BYTES {0}
#define N10_WINDOW_ALIGN 8ULL
#define N10_WINDOW_SIZE 1024ULL
#define N10_WINDOW_LIMIT 4096ULL
#define PAGE_SIZE 8
#define EBUSY 16
#define SYSTEM_RUNNING 1
#define scnprintf snprintf
#define pr_info printf
struct work_struct {int dummy;};
struct n10_pm_result {unsigned int qgeneration,devices,resumed,blocked,old_level,new_level,resume_errors_before,resume_errors_after,stage;int error;};
struct n10_timer_sample {u64 before,cleared,restored,frequency;unsigned int seen;};
static struct n10_timer_sample n10_timers[8];
static struct work_struct n10_pm_work;
static bool n10_timer_done=1;
static unsigned int n10_pm_retries,n10_pm_attempts;
static int system_state=SYSTEM_RUNNING,mode,sha_count,observer_calls,gic_calls,pm_calls,schedule_calls;
static u64 n10_window_base=1024;
static int n10_window_status=1;
static u8 memory[64];
static void *phys_to_virt(u64 p){(void)p;return memory;}
static int virt_addr_valid(const void *p){(void)p;return 1;}
static u64 virt_to_phys(const void *p){return n10_window_base+(const u8*)p-memory;}
static u64 n10_online_bits(void){return mode==3 && pm_calls?254:255;}
static int n10_sha256(const void*p,size_t n,u8*d){(void)p;(void)n;memset(d,0,32);++sha_count;return (mode==4&&sha_count==4)||(mode==5&&sha_count==5)||(mode==7&&sha_count==1)?-1:0;}
static void cpus_read_lock(void){}
static void cpus_read_unlock(void){}
static void on_each_cpu(void(*f)(void*),void*a,int wait){(void)f;(void)a;(void)wait;}
static void n10_timer_cpu(void*p){(void)p;}
static void n10_cpu_checkpoint(unsigned int p,u64 m){(void)p;(void)m;}
static int n10_pm_devices_test(struct n10_pm_result*p){++pm_calls;p->qgeneration=2;p->devices=mode==2?0:1;p->resumed=1;return mode==1?-5:0;}
static void n10_report_pm_cpus(unsigned int g){(void)g;}
static void n10_report_pm_cpu_timers(unsigned int g){(void)g;}
static void n10_test_gic(void){++gic_calls;}
static int n10_report_post_arch(void*p,unsigned int g){(void)p;if(g!=2)abort();++observer_calls;return mode==6?-5:0;}
static void n10_pm_cpus_schedule(unsigned long d){(void)d;++schedule_calls;}
#define msecs_to_jiffies(n) (n)
static u32 n10_frame_checksum(const char*p,int n){(void)p;(void)n;return 0;}
'''
WORKER_MAIN = r'''
int main(int argc,char**argv){int wanted,success;mode=atoi(argv[1]);n10_pm_worker(NULL);
 wanted=mode==0||mode==5||mode==6;success=mode==0;
 if(observer_calls!=wanted || gic_calls!=(mode==0||mode==4||mode==5||mode==6))abort();
 if(schedule_calls || (mode==7?pm_calls!=0:pm_calls!=1))abort();
 printf("WORKER_RESULT observer=%d gic=%d sha=%d success=%d\n",observer_calls,gic_calls,sha_count,success);return 0;}
'''


def run_worker(worker, out, compiler):
    raw = Path(worker).read_bytes()
    text = raw.decode()
    marker = 'static void n10_pm_worker(struct work_struct *unused)\n{'
    if text.count(marker) != 1: raise ValueError('Prepared PM worker definition differs')
    start=text.index(marker); brace=text.index('{',start); depth=0; end=None
    for i in range(brace,len(text)):
        if text[i]=='{': depth+=1
        elif text[i]=='}':
            depth-=1
            if not depth: end=i+1;break
    if end is None: raise ValueError('Prepared worker body is incomplete')
    body=text[start:end]
    source=out/'prepared-worker.c';source.write_bytes((WORKER_STUB+body+WORKER_MAIN).encode())
    exe=out/('prepared-worker.exe' if sys.platform=='win32' else 'prepared-worker')
    built=subprocess.run([str(compiler),'-std=c11','-O2',str(source),'-o',str(exe)],capture_output=True,timeout=60)
    (out/'worker-compile.log').write_bytes(built.stdout+built.stderr)
    if built.returncode: raise ValueError('Prepared PM worker model compilation failed')
    rows=[]
    for mode in range(8):
        ran=subprocess.run([str(exe),str(mode)],capture_output=True,timeout=15)
        (out/f'worker-{mode}.log').write_bytes(ran.stdout+ran.stderr)
        if ran.returncode: raise ValueError('Prepared worker disposition failed: '+str(mode))
        text=ran.stdout.decode();expected=0 if mode==0 else 7 if mode in (4,5,6) else 6 if mode==3 else 5 if mode==2 else 4 if mode==1 else 3
        if not re.search(r'N10PMT1 .* status='+str(expected)+r' checksum=',text):
            raise ValueError('Prepared worker status differs: '+str(mode))
        rows.append(dict(mode=mode,passed=True,accepted=mode==0))
    return dict(cases=8,outcomes=rows,worker_sha256=hashlib.sha256(raw).hexdigest(),
                actual_prepared_worker_executed=True,pm_failure_blocks_observer=True,
                before_and_after_sha_failures_refused=True,observer_failure_refused=True)


def run(output, worker):
    out = Path(output).resolve()
    if out.exists() or not out.is_relative_to((ROOT/'note10/private').resolve()):
        raise ValueError('Fresh private post-PM model required')
    out.mkdir(parents=True)
    checksum = re.search(r'static u32 n10_frame_checksum[^}]+}', (HERE/'xnu_reserve.c').read_text()).group()
    code = STUB + checksum + (HERE/'pm_post_arch_probe.c').read_text() + MAIN
    source = out/'post-arch.c'; source.write_bytes(code.encode())
    exe = out/('post-arch.exe' if sys.platform == 'win32' else 'post-arch')
    compiler = ROOT/'host-tools/windows-build/llvm-mingw/llvm-mingw-20261006-ucrt-x86_64/bin/clang.exe' if sys.platform == 'win32' else shutil.which('cc')
    built = subprocess.run([str(compiler),'-std=c11','-O2',str(source),'-o',str(exe)],capture_output=True,timeout=60)
    (out/'compile.log').write_bytes(built.stdout+built.stderr)
    if built.returncode: raise ValueError('Post-PM native producer compilation failed')
    fingerprint = 14695981039346656037
    for value in range(1,9): fingerprint = ((fingerprint ^ value) * 1099511628211) & ((1<<64)-1)
    baseline = {'cpus':{i:{'snapshot':dict(el=4,mpidr=0x80000000+i,sctlr=0x1005,tcr=0xabc,
        ttbr1=0x1234000012345000,mair=0xff,words=8,fnv=fingerprint)} for i in range(8)}}
    rows=[]
    for mode in range(37):
        ran=subprocess.run([str(exe),str(mode)],capture_output=True,timeout=15)
        (out/f'mode-{mode}.log').write_bytes(ran.stdout+ran.stderr)
        if ran.returncode: raise ValueError('Post-PM callback/lock invariant failed: '+str(mode))
        try:
            decode(ran.stdout.decode(), IDENTITY, 0 if mode==30 else 2, baseline, 64);accepted=True
        except ValueError: accepted=False
        if accepted != (mode in (0,1)):
            raise ValueError('Post-PM fault acceptance differs: '+str(mode))
        rows.append(dict(mode=mode,passed=True,accepted=accepted))
    worker_model=run_worker(worker,out,compiler)
    result=dict(passed=True,cases=37,outcomes=rows,worker_model=worker_model,actual_producer_executed=True,
        asid_only_change_accepted=True,per_cpu_faults_refused=True,no_register_writes=True,
        online_set_locked=True,hardware_verified=False,
        source_sha256={n:hashlib.sha256((HERE/n).read_bytes()).hexdigest() for n in SOURCES})
    (out/'result.json').write_bytes((json.dumps(result,indent=2)+'\n').encode())
    return result


if __name__ == '__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--worker',type=Path,required=True)
    a=p.parse_args();r=run(a.output,a.worker);print(json.dumps({'passed':r['passed'],'cases':r['cases']}))
