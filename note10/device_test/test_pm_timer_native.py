"""Actual PM backend/worker C with modeled kernel APIs and real payload SHA."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
from run_probe import ROOT
from test_cpu_cache_native import STUB,prefix,IDENTITY
from decode_pm_timer import decode

HERE=Path(__file__).resolve().parent
PM_STUB=r'''
#undef read_sysreg
static bool pm_va_valid(const void *p) {(void)p;return true;}
#define virt_addr_valid(p) pm_va_valid(p)
static u64 timer_values[8];
static unsigned int timer_writes[8],scheduled,pm_calls;
static u64 pm_reg(const char *reg) {
    if(!strcmp(reg,"cntfrq_el0"))return mode==10&&current_cpu==4?19200000:26000000;
    return timer_values[current_cpu];
}
static void pm_write(u64 value) {
    unsigned int count=++timer_writes[current_cpu];
    if(mode==8&&current_cpu==3&&count==1)return;
    timer_values[current_cpu]=value;
    if(mode==9&&current_cpu==2&&count==2)timer_values[current_cpu]^=0x1000;
}
#define read_sysreg(reg) pm_reg(#reg)
#define write_sysreg(value,reg) pm_write(value)
#define isb() __asm__ volatile("" ::: "memory")
struct work_struct {int unused;};
struct delayed_work {int unused;};
#define DECLARE_DELAYED_WORK(name,fn) struct delayed_work name={0}
#define msecs_to_jiffies(n) (n)
static int schedule_delayed_work(struct delayed_work *work,unsigned long delay) {
    (void)work;(void)delay;++scheduled;return 1;
}
#define SYSTEM_RUNNING 3
static int system_state=SYSTEM_RUNNING;
#define EINVAL 22
#define EBUSY 16
#define PM_SUSPEND_MEM 3
struct task_struct {int unused;};
static struct task_struct task;
#define current (&task)
static int pm_mutex,mutex_depth,pm_test_level;
static struct {unsigned int failed_resume;} suspend_stats;
static struct task_struct *n10_pm_owner;
static struct n10_pm_result *n10_pm_active;
static void mutex_lock(int *p) {(void)p;if(mutex_depth++)exit(71);}
static void mutex_unlock(int *p) {(void)p;if(--mutex_depth)exit(72);}
static int pm_suspend(int state) {
    int old;
    ++pm_calls;
    if(state!=PM_SUSPEND_MEM||n10_pm_owner!=current||!n10_pm_active||mutex_depth)exit(73);
    mutex_lock(&pm_mutex);old=pm_test_level;n10_pm_active->old_level=(unsigned int)old;
    if(old) {n10_pm_active->new_level=(unsigned int)old;mutex_unlock(&pm_mutex);return -EBUSY;}
    pm_test_level=4;
    n10_pm_active->devices=mode==5?0:1;
    n10_pm_active->resumed=mode==23?0:1;
    n10_pm_active->blocked=mode==14?1:0;
    if(mode==12)++suspend_stats.failed_resume;
    if(mode==6)online=7;
    if(mode==7)buffer[0]^=1;
    pm_test_level=mode==22?4:old;
    n10_pm_active->new_level=(unsigned int)pm_test_level;
    mutex_unlock(&pm_mutex);return mode==4?-16:0;
}
'''
MAIN=r'''
int main(int argc,char **argv) {
    FILE *file;
    if(argc!=3)return 61;
    mode=atoi(argv[1]);file=fopen(argv[2],"rb");if(!file)return 62;
    buffer=malloc(N10_XNU_PAYLOAD_SIZE);if(!buffer)return 63;
    if(fread(buffer,1,N10_XNU_PAYLOAD_SIZE,file)!=N10_XNU_PAYLOAD_SIZE)return 64;
    fclose(file);
    for(int i=0;i<8;++i)timer_values[i]=0xf5ULL+((u64)i<<8);
    if(mode==1)system_state=0;
    if(mode==2)online=7;
    if(mode==3)buffer[0]^=1;
    if(mode==19)n10_window_base+=4096;
    if(mode==20)pm_test_level=4;
    if(mode==21)n10_pm_owner=(void *)(uintptr_t)2;
    n10_start_pm_timer();
    for(int i=0;i<(mode==1?50:1);++i)n10_pm_worker(NULL);
    unsigned int writes=0;
    for(int i=0;i<8;++i) {
        writes+=timer_writes[i];
        if(mode==8&&(timer_writes[i]!=2||timer_values[i]!=0xf5ULL+((u64)i<<8)))return 75;
    }
    if(mutex_depth||n10_pm_active||(mode!=21&&n10_pm_owner))return 74;
    if(down_calls||up_calls||flush_calls)return 76;
    printf("PMMODEL calls=%u writes=%u level=%d scheduled=%u\n",pm_calls,writes,pm_test_level,scheduled);
    free(buffer);return 0;
}
'''


def test(payload,cpu_model,output):
    if not output.resolve().is_relative_to((ROOT/'note10/private').resolve()) or output.exists():
        raise ValueError('Fresh private PM model output required')
    raw=payload.read_bytes();digest=hashlib.sha256(raw).hexdigest()
    previous=json.loads((cpu_model/'result.json').read_text())
    cpu_source=(HERE/'cpu_cache_roundtrip.c').read_bytes()
    if (previous.get('passed') is not True or previous['payload_sha256']!=digest or
        previous['source_sha256']!=hashlib.sha256(cpu_source).hexdigest()):raise ValueError('CPU prerequisite model differs')
    output.mkdir(parents=True)
    sources={name:(HERE/name).read_bytes() for name in ('pm_timer_roundtrip.c','pm_devices_backend.c','pm_test_contract.h')}
    macros='#define N10_XNU_PAYLOAD_SIZE '+str(len(raw))+'ULL\n'
    macros+='#define N10_XNU_PAYLOAD_SHA256_BYTES {'+','.join('0x'+digest[i:i+2] for i in range(0,64,2))+'}\n'
    clean=lambda data:re.sub(r'^#include[^\n]*\n','',data.decode(),flags=re.M)
    # CPU hotplug is a verified prerequisite, not rerun in this PM worker model.
    source=output/'model.c'
    source.write_text(STUB+macros+sources['pm_test_contract.h'].decode()+PM_STUB+
        clean(cpu_source)+clean(sources['pm_devices_backend.c'])+clean(sources['pm_timer_roundtrip.c'])+MAIN)
    compiler=(ROOT/'host-tools/windows-build/llvm-mingw/llvm-mingw-20261006-ucrt-x86_64/bin/clang.exe'
              if sys.platform=='win32' else shutil.which('cc'))
    exe=output/('model.exe' if sys.platform=='win32' else 'model')
    result=subprocess.run([str(compiler),'-std=c11','-O2','-Wall','-Wextra','-Werror','-Wno-sign-compare',
        '-Wno-unused-function',str(source),'-lbcrypt' if sys.platform=='win32' else '-lcrypto','-o',str(exe)],capture_output=True,timeout=60)
    (output/'compile.log').write_bytes(result.stdout+result.stderr)
    if result.returncode:raise RuntimeError('PM actual-C model compilation failed; see compile.log')
    chain=prefix(digest,len(raw))+(cpu_model/'mode-0.txt').read_text()
    statuses=[0,1,2,3,4,5,6,7,8,8,8,8,5,8,5,9,3,7,9,2,4,4,5,5]
    early={1,2,3,16,19,21};cases=[]
    for mode,status in enumerate(statuses):
        result=subprocess.run([str(exe.resolve()),str(mode),str(payload.resolve())],capture_output=True,timeout=60)
        (output/f'mode-{mode}.txt').write_bytes(result.stdout+result.stderr)
        if result.returncode:raise ValueError(f'PM model disposition failed in mode {mode}: {result.returncode}')
        text=result.stdout.decode();records=re.findall(r'N10PMT1 ([^\r\n]*) checksum=([0-9a-f]{8})',text)
        from decode_reservation import checksum
        if len(records)!=32 or any(checksum(body.encode())!=int(total,16) or
            not body.endswith('status='+str(status)) for body,total in records):raise ValueError('PM model summary differs')
        counts=re.search(r'PMMODEL calls=(\d+) writes=(\d+) level=(\d+) scheduled=(\d+)',text)
        if not counts:raise ValueError('Missing modeled PM counts')
        calls,writes,level,scheduled=map(int,counts.groups())
        if calls!=(0 if mode in early else 1):raise ValueError('Failed prerequisite invoked PM')
        if mode not in {20,22} and level:raise ValueError('PM test level leaked')
        if status in {1,2,3,4,5,6,7} and writes:raise ValueError('Failed prerequisite modified timer registers')
        try:decode(chain+text,IDENTITY,digest,len(raw));accepted=True
        except ValueError:accepted=False
        if accepted!=(mode==0):raise ValueError('PM decoder differs from actual C disposition')
        if mode==0 and (writes!=16 or scheduled!=1):raise ValueError('Missing timer clear/restore operations')
        cases.append(dict(mode=mode,status=status,pm_calls=calls,timer_writes=writes,level_after=level,accepted=accepted))
    report={'passed':True,'source_sha256':hashlib.sha256(sources['pm_timer_roundtrip.c']).hexdigest(),
        'backend_source_sha256':hashlib.sha256(sources['pm_devices_backend.c']).hexdigest(),
        'contract_sha256':hashlib.sha256(sources['pm_test_contract.h']).hexdigest(),
        'cpu_source_sha256':previous['source_sha256'],'payload_sha256':digest,'payload_size':len(raw),'cases':cases,
        'hardware_verified':False,'device_operations':[],
        'scope':'Actual worker/backend C; modeled PM framework, scheduling, registers and faults; real SHA256'}
    (output/'result.json').write_text(json.dumps(report,indent=2))
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('payload','cpu-model','output'):parser.add_argument('--'+name,type=Path,required=True)
    result=test(**vars(parser.parse_args()))
    print(json.dumps({'passed':result['passed'],'cases':len(result['cases'])}))
