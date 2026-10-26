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
from decode_pm_timer import decode,decode_stages,decode_quiescence

HERE=Path(__file__).resolve().parent
PM_STUB=r'''
#undef read_sysreg
static bool pm_va_valid(const void *p) {(void)p;return true;}
#define virt_addr_valid(p) pm_va_valid(p)
static const char linux_banner[]="Linux version fixture\n";
static void pm_cpus_lock(void) {if(mode==31)online=15;}
#define cpus_read_lock pm_cpus_lock
static u64 timer_values[8];
static unsigned int timer_writes[8],scheduled,pm_calls;
static unsigned int delays[64];
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
    (void)work;if(scheduled>=64)exit(78);delays[scheduled++]=(unsigned int)delay;return 1;
}
#define SYSTEM_RUNNING 3
static int system_state=SYSTEM_RUNNING;
#define EINVAL 22
#define EBUSY 16
#define EOWNERDEAD 130
#define PM_SUSPEND_MEM 3
struct task_struct {int unused;};
static struct task_struct task;
#define current (&task)
#define CONFIG_NOTE10_SCREEN_LOG 1
static int pm_mutex,mutex_depth,pm_test_level;
static bool screen_paused;
static unsigned int screen_pauses,screen_resumes;
int n10_screen_pause(bool paused) {
    if(mutex_depth||paused==screen_paused)exit(81);
    screen_paused=paused;
    if(paused)++screen_pauses;else ++screen_resumes;
    return 0;
}
static struct {unsigned int failed_resume;} suspend_stats;
static struct task_struct *n10_pm_owner;
static struct n10_pm_result *n10_pm_active;
static void mutex_lock(int *p) {(void)p;if(mutex_depth++)exit(71);}
static void mutex_unlock(int *p) {(void)p;if(--mutex_depth)exit(72);}
static int pm_suspend(int state) {
    int old;
    ++pm_calls;
    if(!screen_paused||state!=PM_SUSPEND_MEM||n10_pm_owner!=current||!n10_pm_active||mutex_depth)exit(73);
    mutex_lock(&pm_mutex);old=pm_test_level;n10_pm_active->old_level=(unsigned int)old;
    if(old) {n10_pm_active->new_level=(unsigned int)old;mutex_unlock(&pm_mutex);return -EBUSY;}
    pm_test_level=4;
    if((mode==24&&pm_calls<3)||(mode>=25&&mode<=30)) {
        if(mode==26)buffer[0]^=1;
        if(mode==27)online=7;
        if(mode==28)++suspend_stats.failed_resume;
        if(mode==29)n10_pm_active->blocked=1;
        if(mode==30)n10_pm_active->devices=1;
        n10_pm_active->stage=11;
        pm_test_level=old;n10_pm_active->new_level=(unsigned int)old;
        mutex_unlock(&pm_mutex);return -EBUSY;
    }
    n10_pm_active->stage=21;
    n10_pm_active->devices=mode==5?0:1;
    n10_pm_active->resumed=mode==23?0:1;
    n10_pm_active->blocked=mode==14?1:0;
    if(mode==12)++suspend_stats.failed_resume;
    if(mode==6)online=7;
    if(mode==7)buffer[0]^=1;
    pm_test_level=mode==22?4:old;
    n10_pm_active->new_level=(unsigned int)pm_test_level;
    mutex_unlock(&pm_mutex);return mode==4?-5:0;
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
    for(unsigned int i=0;i<scheduled&&i<64;++i)n10_pm_worker(NULL);
    unsigned int writes=0;
    for(int i=0;i<8;++i) {
        writes+=timer_writes[i];
        if(mode==8&&(timer_writes[i]!=2||timer_values[i]!=0xf5ULL+((u64)i<<8)))return 75;
    }
    if(screen_paused||screen_pauses!=pm_calls||screen_resumes!=pm_calls)return 82;
    if(mutex_depth||n10_pm_active||(mode!=21&&n10_pm_owner))return 74;
    if(down_calls||up_calls||flush_calls)return 76;
    if(delays[0]!=30000)return 79;
    if(mode==24||mode==25) {
        if(scheduled!=3||pm_calls!=3||delays[1]!=10000||delays[2]!=10000||writes!=16)return 80;
    }
    printf("PMMODEL calls=%u writes=%u level=%d scheduled=%u\n",pm_calls,writes,pm_test_level,scheduled);
    free(buffer);return 0;
}
'''


QUIESCE_STUB=r"""
static unsigned int usb_begins,usb_ends,display_begins,display_ends;
static bool usb_quiet,display_quiet;
static void assert_pm_unlocked(void) {if(mutex_depth)exit(83);}
int n10_decon_quiesce_begin(struct n10_pm_result *out) {
    (void)out;assert_pm_unlocked();++display_begins;display_quiet=true;return 0;
}
int n10_decon_quiesce_end(struct n10_pm_result *out) {
    (void)out;assert_pm_unlocked();++display_ends;display_quiet=false;return 0;
}
int n10_usb_quiesce_begin(struct n10_pm_result *out) {
    assert_pm_unlocked();++usb_begins;usb_quiet=true;
    out->qgeneration=usb_begins;out->cable_epoch=17;return 0;
}
int n10_usb_quiesce_end(struct n10_pm_result *out) {
    (void)out;assert_pm_unlocked();++usb_ends;usb_quiet=false;
    return mode==103||mode==106?-5:0;
}
int n10_usb_quiesce_validate(void) {assert_pm_unlocked();return usb_quiet?0:-EBUSY;}
static bool pm_get_wakeup_count(unsigned int *count,bool block) {
    assert_pm_unlocked();if(block||!usb_quiet||!display_quiet)exit(84);*count=17;return mode!=102;
}
static void pm_print_active_wakeup_sources(void) {assert_pm_unlocked();}
"""
QUIESCE_MAIN=r"""
int main(int argc,char **argv) {
    FILE *file;unsigned int wanted,writes=0;
    if(argc!=3)return 61;
    mode=atoi(argv[1]);file=fopen(argv[2],"rb");if(!file)return 62;
    buffer=malloc(N10_XNU_PAYLOAD_SIZE);if(!buffer)return 63;
    if(fread(buffer,1,N10_XNU_PAYLOAD_SIZE,file)!=N10_XNU_PAYLOAD_SIZE)return 64;
    fclose(file);
    for(int i=0;i<8;++i)timer_values[i]=0xf5ULL+((u64)i<<8);
    n10_start_pm_timer();
    for(unsigned int i=0;i<scheduled&&i<64;++i)n10_pm_worker(NULL);
    wanted=mode==101||mode==102?3:1;
    if(scheduled!=wanted||pm_calls!=(mode==102?0:wanted))return 85;
    if(screen_paused||screen_pauses!=wanted||screen_resumes!=wanted)return 86;
    if(usb_quiet||display_quiet||usb_begins!=wanted||usb_ends!=wanted||display_begins!=wanted||display_ends!=wanted)return 87;
    if(mutex_depth||n10_pm_active||n10_pm_owner||down_calls||up_calls||flush_calls)return 88;
    for(int i=0;i<8;++i) {
        writes+=timer_writes[i];
        if(timer_values[i]!=0xf5ULL+((u64)i<<8))return 89;
    }
    if(writes!=16||delays[0]!=30000)return 90;
    for(unsigned int i=1;i<scheduled;++i)if(delays[i]!=10000)return 91;
    printf("QSCMODEL calls=%u writes=%u scheduled=%u attempts=%u\n",pm_calls,writes,scheduled,n10_pm_attempts);
    free(buffer);return 0;
}
"""


def _quiescence_evidence(payload,output,compiler,macros,cpu_source,sources,chain):
    clean=lambda data:re.sub(r'^#include[^\n]*\n','',data.decode(),flags=re.M)
    core=(HERE/'pm_quiesce_core.h').read_bytes()
    stubs=PM_STUB.replace('    return 0;\n}\nstatic struct {unsigned int failed_resume;}',
        '    return (!paused&&(mode==104||mode==107))?-5:0;\n}\nstatic struct {unsigned int failed_resume;}')
    if stubs==PM_STUB:raise ValueError('PM screen fault stub anchor differs')
    stubs=stubs.replace('(mode==24&&pm_calls<3)',
        '((mode==24||mode==101)&&pm_calls<3)||mode==103||mode==104')
    stubs=stubs.replace('return mode==4?-5:0;','return (mode==4||mode==105)?-5:0;')
    source=output/'quiesce-evidence.c'
    source.write_text(STUB+macros+sources['pm_test_contract.h'].decode()+core.decode()+
        '\n#define CONFIG_NOTE10_PM_QUIESCE 1\n'+stubs+QUIESCE_STUB+clean(cpu_source)+
        clean(sources['pm_devices_backend.c'])+clean(sources['pm_timer_roundtrip.c'])+QUIESCE_MAIN)
    exe=output/('quiesce-evidence.exe' if sys.platform=='win32' else 'quiesce-evidence')
    built=subprocess.run([str(compiler),'-std=c11','-O2','-Wall','-Wextra','-Werror','-Wno-sign-compare',
        '-Wno-unused-function',str(source),'-lbcrypt' if sys.platform=='win32' else '-lcrypto','-o',str(exe)],capture_output=True,timeout=60)
    (output/'quiesce-evidence-compile.log').write_bytes(built.stdout+built.stderr)
    if built.returncode:raise RuntimeError('PM quiesce evidence actual-C compilation failed')
    from decode_reservation import checksum
    from decode_cpu_cache import frames
    names=('id','seq','attempt','version','generation','epoch','phase','called','restored','screen','display','usb','wake','r_usb','r_display','r_screen')
    cases=[]
    labels=('success','clean-ebusy-retry','pre-pm-wake-busy','usb-restore-failure-no-retry',
            'screen-restore-failure-no-retry','pm-error','usb-restore-failure-after-pm-success','screen-restore-failure-after-pm-success')
    for mode,label in enumerate(labels,100):
        ran=subprocess.run([str(exe.resolve()),str(mode),str(payload.resolve())],capture_output=True,timeout=60)
        (output/f'quiesce-mode-{mode}.txt').write_bytes(ran.stdout+ran.stderr)
        if ran.returncode:raise ValueError(f'Actual worker quiesce disposition failed {label}: {ran.returncode}')
        text=ran.stdout.decode()
        records=re.findall(r'N10QSC1 ([^\r\n]*) checksum=([0-9a-f]{8})',text)
        wanted=3 if mode in (101,102) else 1
        if len(records)!=wanted*8 or any(checksum(body.encode())!=int(total,16) for body,total in records):
            raise ValueError('Actual worker quiesce record checksum/count differs')
        observation=decode_quiescence(text,IDENTITY,require_success=False)
        qrows=frames(text,'N10QSC1',names,IDENTITY,24)
        stages=decode_stages(text,IDENTITY)
        tries=frames(text,'N10TRY1',('id','seq','attempt','error','devices','resume','blocked','oldlevel','newlevel','resume_errors'),IDENTITY,24)
        if len(observation['attempts'])!=wanted or len(stages)!=wanted or len(tries)!=wanted*8:
            raise ValueError('Actual QSC/PMS/TRY attempt sets differ')
        final=observation['attempts'][wanted]['result']
        if final['generation']!=wanted or final['epoch']!=17 or final['called']!=(mode!=102):
            raise ValueError('Actual quiesce ownership/call evidence differs')
        if final['restored']!=(mode not in (103,104,106,107)):
            raise ValueError('Actual quiesce restoration evidence differs')
        if mode in (103,106) and final['r_usb']!=5:raise ValueError('USB restore error not emitted')
        if mode in (104,107) and final['r_screen']!=5:raise ValueError('Screen restore error not emitted')
        if mode==102 and final['wake']!=16:raise ValueError('Pre-PM active wake error not emitted')
        if mode==101:
            for attempt in (1,2):
                q=observation['attempts'][attempt]['result']
                if q['restored']!=1 or any(q[k] for k in ('r_usb','r_display','r_screen')):
                    raise ValueError('Worker retried without complete cleanup')
        try:decode(chain+text,IDENTITY,hashlib.sha256(payload.read_bytes()).hexdigest(),payload.stat().st_size,require_quiesce=True);accepted=True
        except ValueError:accepted=False
        if accepted!=(mode in (100,101)):raise ValueError('Strict decoder differs from actual quiesce worker disposition')
        if accepted:decode_quiescence(text,IDENTITY,require_success=True)
        counts=re.search(r'QSCMODEL calls=(\d+) writes=(\d+) scheduled=(\d+) attempts=(\d+)',text)
        if not counts:raise ValueError('Missing actual quiesce worker counts')
        calls,writes,scheduled,attempts=map(int,counts.groups())
        cases.append({'mode':mode,'name':label,'passed':True,'accepted':accepted,'pm_calls':calls,
            'timer_writes':writes,'scheduled':scheduled,'attempts':attempts,'final_quiescence':final,
            'real_frame_checksums_verified':True,'strict_decoder_require_quiesce':True})
    return cases,hashlib.sha256(core).hexdigest()


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
    statuses=[0,1,2,3,4,5,6,7,8,8,8,8,5,8,5,9,3,9,7,2,4,4,5,5,0,4,7,6,4,4,4,6]
    early={1,2,3,8,9,10,11,13,15,16,17,19,21,31};cases=[]
    for mode,status in enumerate(statuses):
        result=subprocess.run([str(exe.resolve()),str(mode),str(payload.resolve())],capture_output=True,timeout=60)
        (output/f'mode-{mode}.txt').write_bytes(result.stdout+result.stderr)
        if result.returncode:raise ValueError(f'PM model disposition failed in mode {mode}: {result.returncode}')
        text=result.stdout.decode()
        from collect_reservation import select_latest_boot
        _,binding=select_latest_boot(('<5>[    0.000000] Linux version damaged\n'+text).encode(),
            'Linux version fixture',boot_binding_id=IDENTITY)
        if not binding['exact_checksummed_banner_binding']:raise ValueError('Actual boot binding differs')
        records=re.findall(r'N10PMT1 ([^\r\n]*) checksum=([0-9a-f]{8})',text)
        from decode_reservation import checksum
        if len(records)!=32 or any(checksum(body.encode())!=int(total,16) or
            not body.endswith('status='+str(status)) for body,total in records):raise ValueError('PM model summary differs')
        from decode_cpu_cache import frames
        attempts=frames(text,'N10TRY1',('id','seq','attempt','error','devices','resume','blocked','oldlevel','newlevel','resume_errors'),IDENTITY,24)
        wanted=0 if mode in early-{21} else (3 if mode in {24,25} else 1)
        if len(attempts)!=wanted*8 or any(row['attempt']!=row['seq']//8+1 for row in attempts.values()):
            raise ValueError('Attempt frame count or sequence differs')
        stages=frames(text,'N10PMS1',('id','seq','attempt','stage','error'),IDENTITY,24)
        if len(stages)!=wanted*8:raise ValueError('PM stage frame count differs')
        if wanted and len(decode_stages(text,IDENTITY))!=wanted:raise ValueError('PM stage decode differs')
        counts=re.search(r'PMMODEL calls=(\d+) writes=(\d+) level=(\d+) scheduled=(\d+)',text)
        if not counts:raise ValueError('Missing modeled PM counts')
        calls,writes,level,scheduled=map(int,counts.groups())
        if calls!=(0 if mode in early else (3 if mode in {24,25} else 1)):raise ValueError('PM attempt count differs')
        if mode not in {20,22} and level:raise ValueError('PM test level leaked')
        if mode in {1,2,3,16,19,31} and writes:raise ValueError('Failed prerequisite modified timer registers')
        try:decode(chain+text,IDENTITY,digest,len(raw));accepted=True
        except ValueError:accepted=False
        if accepted!=(mode in {0,24}):raise ValueError('PM decoder differs from actual C disposition')
        if mode==0 and (writes!=16 or scheduled!=1):raise ValueError('Missing timer clear/restore operations')
        cases.append(dict(mode=mode,status=status,pm_calls=calls,timer_writes=writes,level_after=level,accepted=accepted))
    quiesce_cases,quiesce_core_sha=_quiescence_evidence(payload,output,compiler,macros,cpu_source,sources,chain)
    report={'passed':True,'source_sha256':hashlib.sha256(sources['pm_timer_roundtrip.c']).hexdigest(),
        'backend_source_sha256':hashlib.sha256(sources['pm_devices_backend.c']).hexdigest(),
        'contract_sha256':hashlib.sha256(sources['pm_test_contract.h']).hexdigest(),
        'cpu_source_sha256':previous['source_sha256'],'payload_sha256':digest,'payload_size':len(raw),'cases':cases,'bounded_retry_cases':8,'timer_precedes_pm':True,'first_delay_ms':30000,'max_pm_attempts':3,
        'screen_pause_verified':True,'quiesce_evidence_cases':quiesce_cases,'quiesce_evidence_verified':True,
        'quiesce_core_sha256':quiesce_core_sha,'hardware_verified':False,'device_operations':[],
        'scope':'Actual worker/backend C; modeled PM framework, scheduling, registers and faults; real SHA256'}
    (output/'result.json').write_text(json.dumps(report,indent=2))
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('payload','cpu-model','output'):parser.add_argument('--'+name,type=Path,required=True)
    result=test(**vars(parser.parse_args()))
    print(json.dumps({'passed':result['passed'],'cases':len(result['cases'])}))
