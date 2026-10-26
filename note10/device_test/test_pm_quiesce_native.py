"""Compile and execute actual PM/DECON C with deterministic kernel API stubs.

These host tests exercise control flow, not physical hardware behavior.
"""
import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path
from run_probe import ROOT

HERE = Path(__file__).resolve().parent
STUB = r'''
#include <errno.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#ifndef ESTALE
#define ESTALE 116
#endif
#define READ_ONCE(x) (x)
#define DEFINE_MUTEX(x) int x
#define IS_DECON_OFF_STATE(d) ((d)->state == DECON_STATE_OFF)
struct task_struct { int id; };
static struct task_struct task_a={1}, task_b={2};
static struct task_struct *current=&task_a;
static int pm_mutex, mutex_depth, mode;
static int wake_print_calls;
static int pause_state, usb_active, wake_ok=1, pm_result, pm_calls, validate_before_error, validate_after_error;
static int pause_on_calls, pause_off_calls, usb_begin_calls, usb_end_calls;
static int decon_power_off_calls, decon_power_on_calls;
static int fail_screen_on, fail_screen_off, fail_usb_begin, fail_usb_end;
static int fail_display_off, fail_display_on, partial_display_off;
static int idle_result, missing_device, power_no_change, resume_bad, partial_same_state;
static struct n10_pm_result *n10_pm_active;
static struct task_struct *n10_pm_owner;
static struct { unsigned int failed_resume; } suspend_stats;
static char events[128];
static void event(char c) { size_t n=strlen(events); if (n+1>=sizeof(events)) abort(); events[n]=c; events[n+1]=0; }
static void no_pm_lock(void) { if (pm_mutex) abort(); }
static void mutex_lock(int *m) { if (*m) abort(); *m=1; ++mutex_depth; }
static int mutex_trylock(int *m) { if (*m) return 0; *m=1; ++mutex_depth; return 1; }
static void mutex_unlock(int *m) { if (!*m || !mutex_depth) abort(); *m=0; --mutex_depth; }
enum decon_state { DECON_STATE_OFF=0, DECON_STATE_INIT=1, DECON_STATE_ON=2, DECON_STATE_HIBER=3, DECON_STATE_BAD=4 };
enum decon_out_type { DECON_OUT_DSI=1 };
enum { DISP_PWR_OFF=0, DISP_PWR_NORMAL=1 };
struct atomic_stub { int value; };
static int atomic_read(struct atomic_stub *a) { return a->value; }
struct decon_device {
    int id; void *lcd_info; struct { int out_type; } dt;
    int *out_sd[1], *dsim_sd[1]; enum decon_state state;
    int cur_using_dpp, eint_status;
    struct { struct atomic_stub remaining_frame; } up;
};
static int out_token, dsim_token, lcd_token;
static struct decon_device device={.id=0,.lcd_info=&lcd_token,.dt={DECON_OUT_DSI},
    .out_sd={&out_token},.dsim_sd={&dsim_token},.state=DECON_STATE_ON,.eint_status=1};
static struct decon_device *get_decon_drvdata(int id) { return id==0 && !missing_device?&device:NULL; }
static int decon_update_pwr_state(struct decon_device *d, int state) {
    no_pm_lock();
    if (state==DISP_PWR_OFF) {
        event('D'); ++decon_power_off_calls;
        event('I'); if (idle_result) return idle_result;
        if (partial_same_state) { d->eint_status=0; if (partial_same_state==2) partial_same_state=0; return -EIO; }
        if (fail_display_off && !partial_display_off) return -EIO;
        if (!power_no_change) { d->state=DECON_STATE_OFF; d->eint_status=0; }
        return fail_display_off?-EIO:0;
    }
    event('d'); ++decon_power_on_calls;
    if (fail_display_on) return -EIO;
    d->state=DECON_STATE_ON; d->eint_status=resume_bad?0:1; return 0;
}
static int decon_reg_wait_idle_status_framecnt(int id, int frames) {
    no_pm_lock(); event('I'); if (id!=0 || frames!=3) abort(); return idle_result;
}
static int n10_screen_pause(bool paused) {
    no_pm_lock();
    if (!n10_pm_active || n10_pm_owner!=current) abort();
    if (paused) { event('S'); ++pause_on_calls; pause_state=1; if (fail_screen_on) return -EIO; }
    else { event('s'); ++pause_off_calls; if (fail_screen_off) return -EIO; pause_state=0; }
    return 0;
}
'''
USB_PM = r'''
static int n10_usb_quiesce_begin(struct n10_pm_result *out) {
    no_pm_lock(); event('U'); ++usb_begin_calls;
    out->qphase=N10_Q_USB_BLOCKED; usb_active=1; return fail_usb_begin?-EIO:0;
}
static int n10_usb_quiesce_end(struct n10_pm_result *out) {
    no_pm_lock(); event('u'); ++usb_end_calls; out->qphase=N10_Q_RESTORE_USB;
    if (fail_usb_end) return -EIO;
    usb_active=0; return 0;
}
static int n10_usb_quiesce_validate(void) {
    no_pm_lock(); event('V');
    if (!usb_active) abort();
    return pm_calls?validate_after_error:validate_before_error;
}
static void pm_print_active_wakeup_sources(void) { no_pm_lock(); ++wake_print_calls; }
static int pm_get_wakeup_count(unsigned int *count, bool block) {
    no_pm_lock(); event('W'); if (block) abort(); *count=42; return wake_ok;
}
#define PM_SUSPEND_MEM 3
static int pm_suspend(int state) {
    no_pm_lock(); event('P'); ++pm_calls;
    if (state!=PM_SUSPEND_MEM || !n10_pm_active || n10_pm_owner!=current || mutex_depth) abort();
#ifdef CONFIG_NOTE10_SCREEN_LOG
    if (!pause_state) abort();
#endif
#ifdef CONFIG_NOTE10_PM_QUIESCE
    if (!usb_active || device.state!=DECON_STATE_OFF) abort();
#endif
    n10_pm_active->devices=1; n10_pm_active->resumed=1; return pm_result;
}
'''
MAIN = r'''
#define CHECK(x) do { if (!(x)) { fprintf(stderr,"assertion line=%d mode=%d events=%s: %s\n",__LINE__,mode,events,#x); return 1; } } while (0)
int main(int argc, char **argv) {
    struct n10_pm_result r; int ret;
    if (argc!=2) return 90;
    mode=atoi(argv[1]); memset(&r,0,sizeof(r));
    if (mode==1) fail_display_off=1;
    if (mode==2) fail_usb_begin=1;
    if (mode==3) wake_ok=0;
    if (mode==4) pm_result=-EIO;
    if (mode==5) fail_usb_end=1;
    if (mode==6) fail_display_on=1;
    if (mode==7) fail_screen_off=1;
    if (mode==8) n10_pm_owner=&task_b;
    if (mode==9) device.state=DECON_STATE_INIT;
    if (mode==10) device.state=DECON_STATE_BAD;
    if (mode==11) fail_screen_on=1;
    if (mode==12) device.state=DECON_STATE_OFF;
    if (mode==13) idle_result=-ETIMEDOUT;
    if (mode==14) { fail_display_off=1; partial_display_off=1; }
    if (mode==15) device.up.remaining_frame.value=1;
    if (mode==16) device.cur_using_dpp=1;
    if (mode==17) power_no_change=1;
    if (mode==18) resume_bad=1;
    if (mode==19) device.state=DECON_STATE_HIBER;
    if (mode==20) missing_device=1;
#ifdef CONFIG_NOTE10_PM_QUIESCE
    if (mode==21) n10_decon_q_lock=1;
    if (mode==22) { n10_decon_q_active=true; n10_decon_q_owner=&task_b; }
#endif
    if (mode==23) { fail_usb_begin=1; fail_usb_end=1; fail_display_on=1; fail_screen_off=1; }
    if (mode==24) { n10_pm_active=&r; n10_pm_owner=&task_b; }
    if (mode==26) partial_same_state=1;
    if (mode==27) partial_same_state=2;
    if (mode==28) device.id=1;
    if (mode==29) device.lcd_info=NULL;
    if (mode==30) device.dt.out_type=0;
    if (mode==31) device.out_sd[0]=NULL;
    if (mode==32) device.dsim_sd[0]=NULL;
    if (mode==35) validate_before_error=-ESTALE;
    if (mode==36) validate_after_error=-ESTALE;
#ifdef CONFIG_NOTE10_PM_QUIESCE
    if (mode==33) {
        CHECK(!n10_decon_quiesce_begin(&r));
        CHECK(n10_decon_quiesce_owned());
        current=&task_b;
        CHECK(!n10_decon_quiesce_owned());
        CHECK(n10_decon_quiesce_begin(&r)==-EBUSY);
        CHECK(n10_decon_quiesce_end(&r)==-EPERM);
        CHECK(n10_decon_q_active && n10_decon_q_owner==&task_a && device.state==DECON_STATE_OFF);
        current=&task_a;
        CHECK(!n10_decon_quiesce_end(&r));
        CHECK(!n10_decon_q_active && !n10_decon_q_owner && device.state==DECON_STATE_ON && !mutex_depth);
        printf("direct helper foreign owner rejected and original owner restored\n"); return 0;
    }
    if (mode==37) {
        struct n10_pm_result competitor={0};
        CHECK(!n10_decon_quiesce_begin(&r));
        CHECK(r.decon_cookie);
        CHECK(n10_decon_quiesce_begin(&competitor)==-EBUSY);
        CHECK(!competitor.decon_cookie);
        CHECK(!n10_decon_quiesce_end(&competitor));
        CHECK(n10_decon_q_active && n10_decon_q_owner==current && device.state==DECON_STATE_OFF);
        competitor.decon_cookie=r.decon_cookie+1;
        CHECK(!n10_decon_quiesce_end(&competitor));
        CHECK(n10_decon_q_active && device.state==DECON_STATE_OFF);
        CHECK(!n10_decon_quiesce_end(&r));
        CHECK(!n10_decon_q_active && device.state==DECON_STATE_ON && !mutex_depth);
        printf("same task distinct result cannot unwind existing owner\n"); return 0;
    }
    if (mode==34) {
        CHECK(n10_decon_quiesce_begin(NULL)==-EBUSY);
        CHECK(!n10_decon_q_active && !n10_decon_q_owner && !strlen(events)); return 0;
    }
#endif
    if (mode==25) { CHECK(n10_pm_devices_test(NULL)==-EINVAL); CHECK(!strlen(events)); return 0; }
    ret=n10_pm_devices_test(&r);
    CHECK(!pm_mutex);
    CHECK(r.pm_called==(unsigned)pm_calls);
    if (mode!=8 && mode!=24) CHECK(!n10_pm_active && !n10_pm_owner);
    if (mode==8 || mode==24) { CHECK(ret==-EBUSY && !strlen(events)); CHECK(n10_pm_owner==&task_b); return 0; }
#ifdef CONFIG_NOTE10_PM_QUIESCE
    CHECK(!mutex_depth || mode==21);
    if (mode==0 || mode==9 || mode==12) {
        CHECK(!ret && r.pm_called && r.quiesce_restored && !r.error);
        CHECK(usb_begin_calls==1 && usb_end_calls==1);
        CHECK(device.state==(mode==12?DECON_STATE_OFF:DECON_STATE_ON));
#ifdef CONFIG_NOTE10_SCREEN_LOG
        CHECK(!strcmp(events,mode==12?"SUWVPVus":"SDIUWVPVuds"));
#else
        CHECK(!strcmp(events,mode==12?"UWVPVu":"DIUWVPVud"));
#endif
    } else {
        CHECK(ret<0 && r.error<0);
        if (mode==1) CHECK(r.display_error==-EIO && !pm_calls && !decon_power_on_calls && r.display_restore_error && !r.quiesce_restored);
        if (mode==2) CHECK(r.usb_error==-EIO && usb_end_calls==1 && r.quiesce_restored && !pm_calls);
        if (mode==3) CHECK(r.wake_error==-EBUSY && !pm_calls && r.quiesce_restored && wake_print_calls==1);
        if (mode==4) CHECK(ret==-EIO && pm_calls && r.quiesce_restored);
        if (mode==5) CHECK(r.usb_restore_error==-EIO && !r.quiesce_restored && pm_calls);
        if (mode==6 || mode==18) CHECK(r.display_restore_error==-EIO && !r.quiesce_restored && pm_calls);
        if (mode==7) CHECK(r.screen_restore_error==-EIO && !r.quiesce_restored && pm_calls);
        if (mode==10 || mode==19 || mode==20 || mode==21 || mode==22 || (mode>=28 && mode<=32)) {
            CHECK(!pm_calls && !decon_power_off_calls && !usb_begin_calls);
            if (mode!=22) CHECK(!n10_decon_q_active);
            if (mode==22) CHECK(n10_decon_q_owner==&task_b);
        }
        if (mode==11) CHECK(r.screen_error==-EIO && !pm_calls && pause_off_calls==1 && !usb_begin_calls);
        if (mode==13) CHECK(r.display_error==-ETIMEDOUT && !pm_calls && device.state==DECON_STATE_ON);
        if (mode==14) CHECK(r.display_error==-EIO && decon_power_on_calls==1 && !pm_calls && r.quiesce_restored);
        if (mode==15 || mode==16 || mode==17) CHECK(r.display_error==-EBUSY && !pm_calls && !usb_begin_calls);
        if (mode==35) CHECK(ret==-ESTALE && r.usb_error==-ESTALE && !pm_calls && r.quiesce_restored);
        if (mode==36) CHECK(ret==-ESTALE && r.usb_error==-ESTALE && pm_calls && r.quiesce_restored);
        if (mode==27) CHECK(r.display_error==-EIO && !pm_calls && r.quiesce_restored && device.eint_status && decon_power_off_calls==2 && decon_power_on_calls==1);
        if (mode==26) CHECK(r.display_error==-EIO && !pm_calls && (!r.quiesce_restored || device.eint_status));
        if (mode==23) CHECK(r.usb_restore_error && r.display_restore_error && r.screen_restore_error && !r.quiesce_restored);
    }
    if (usb_begin_calls) CHECK(usb_end_calls==1);
    if (decon_power_off_calls && mode!=17 && mode!=1 && mode!=26 && mode!=13) CHECK(decon_power_on_calls==1);
    if (usb_end_calls && decon_power_on_calls) CHECK(strchr(events,'u')<strchr(events,'d'));
    if (decon_power_on_calls && pause_off_calls) CHECK(strchr(events,'d')<strchr(events,'s'));
#else
    CHECK(!ret && pm_calls==1 && !usb_begin_calls && !decon_power_off_calls);
#ifdef CONFIG_NOTE10_SCREEN_LOG
    CHECK(!strcmp(events,"SPs"));
#else
    CHECK(!strcmp(events,"P"));
#endif
#endif
    printf("mode=%d ret=%d pm=%u restored=%u events=%s\n",mode,ret,r.pm_called,r.quiesce_restored,events);
    return 0;
}
'''


def _clean(source):
    return re.sub(r'^#include[^\n]*\n', '', source, flags=re.M)



def _driver_error_blocks(path, output, compiler):
    """Execute unchanged generated driver error blocks, preserving their order.

    This narrow harness does not claim to execute the complete DECON driver.
    """
    raw = Path(path).read_bytes()
    source = raw.decode()
    signature = 'int _decon_disable(struct decon_device *decon, enum decon_state state)'
    if source.count(signature) != 1:
        raise ValueError('Generated DECON disable signature differs')
    start = source.index(signature)
    masked = re.sub(r'/\*.*?\*/|//[^\n]*|"(?:\\.|[^"\\])*"', lambda m:' '*len(m[0]), source, flags=re.S)
    opening = masked.index('{', start)
    depth, end = 1, opening+1
    while depth:
        if end >= len(masked):
            raise ValueError('Unterminated generated DECON disable function')
        depth += (masked[end]=='{')-(masked[end]=='}')
        end += 1
    function = source[start:end]
    if function.count('int n10_stop_error = 0;') != 1:
        raise ValueError('Generated DECON stop error local missing')
    def block(first,last):
        if function.count(first)!=1:
            raise ValueError('Generated DECON block anchor differs: '+first)
        a=function.index(first)
        b=function.index(last,a)
        return function[a:b]
    idle = block('\tidle_status = decon_reg_wait_idle_status_framecnt(', '\tdecon_to_psr_info(')
    stop = block('\tret = decon_reg_stop(', '\n#ifdef PROFILE_DECON_DISABLE')
    # The OFF fast path has another output-state call; use the one after DPP stop.
    tail=function[function.index('\tdecon_dpp_stop('):]
    first='\tret = decon_set_out_sd_state(decon, state);'
    a=tail.index(first)
    out=tail[a:tail.index('\n#ifdef PROFILE_DECON_DISABLE',a)]
    if 'n10_stop_error' not in stop or 'n10_stop_error && !ret' not in out:
        raise ValueError('Generated DECON error preservation blocks missing')
    driver_stub=r"""
#include <errno.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#define CONFIG_NOTE10_PM_QUIESCE 1
#define REQ_DSI_DUMP 0
#define decon_err(...) ((void)0)
struct decon_mode_info { int unused; };
enum decon_state { DECON_STATE_OFF };
struct lcd { int fps; };
struct decon_device { int id; struct { int out_idx[1]; } dt; struct lcd *lcd_info; };
static int owned=1,idle_error,stop_error,out_error,stop_calls,out_calls;
static bool n10_decon_quiesce_owned(void) { return owned; }
static int decon_reg_wait_idle_status_framecnt(int id,int n) { (void)id; (void)n; return idle_error; }
static int decon_reg_stop(int id,int idx,struct decon_mode_info *p,bool reset,int fps) {
    (void)id;(void)idx;(void)p;(void)reset;(void)fps; ++stop_calls; return stop_error;
}
static void decon_dump(struct decon_device *d,int kind) { (void)d;(void)kind; }
static int decon_set_out_sd_state(struct decon_device *d,enum decon_state s) { (void)d;(void)s; ++out_calls; return out_error; }
static int exercise(struct decon_device *decon,enum decon_state state) {
    struct decon_mode_info psr;
    int ret=0,idle_status=0,n10_stop_error=0;
"""
    driver_main=r"""
int main(int argc,char **argv) {
    struct lcd lcd={60}; struct decon_device d={.lcd_info=&lcd};
    int m,ret,want=0;
    if (argc!=2) return 90;
    m=atoi(argv[1]);
    if (m==0 || m==1 || m==4) stop_error=-EIO;
    if (m==1 || m==3) owned=0;
    if (m==2 || m==3) idle_error=-ETIMEDOUT;
    if (m==4) out_error=-ENODEV;
    if (m==0) want=-EIO;
    if (m==2) want=-ETIMEDOUT;
    if (m==4) want=-ENODEV;
    ret=exercise(&d,DECON_STATE_OFF);
    if (ret!=want || (m==2 && (stop_calls || out_calls)) || (m!=2 && (stop_calls!=1 || out_calls!=1))) {
        fprintf(stderr,"driver mode=%d ret=%d want=%d stop=%d out=%d\n",m,ret,want,stop_calls,out_calls); return 1;
    }
    printf("driver-error-block mode=%d ret=%d stop=%d out=%d\n",m,ret,stop_calls,out_calls); return 0;
}
"""
    cpath=output/'generated-driver-error-blocks.c'
    cpath.write_text(driver_stub+idle+stop+out+'\nreturn ret;\n}\n'+driver_main,encoding='utf-8')
    exe=output/('generated-driver-error-blocks'+('.exe' if sys.platform=='win32' else ''))
    built=subprocess.run([str(compiler),'-std=c11','-O2','-Wall','-Wextra','-Werror',str(cpath),'-o',str(exe)],capture_output=True,timeout=60)
    (output/'generated-driver-compile.log').write_bytes(built.stdout+built.stderr)
    if built.returncode:
        raise RuntimeError('Generated DECON driver error blocks compilation failed')
    cases=[]
    for mode in range(6):
        ran=subprocess.run([str(exe),str(mode)],capture_output=True,timeout=15)
        (output/f'generated-driver-mode-{mode}.log').write_bytes(ran.stdout+ran.stderr)
        cases.append({'configuration':'generated-driver-error-blocks','case':mode,'passed':ran.returncode==0,'exit':ran.returncode,'observation':(ran.stdout+ran.stderr).decode(errors='replace').strip()})
    binding={'source_path':str(Path(path).resolve()),'source_sha256':hashlib.sha256(raw).hexdigest(),
             'function_sha256':hashlib.sha256(function.encode()).hexdigest(),
             'blocks_sha256':hashlib.sha256((idle+stop+out).encode()).hexdigest(),
             'scope':'Unchanged generated _decon_disable idle/stop/output-state error blocks; complete driver not executed.'}
    return cases,binding


def run(output, decon_core=None):
    output = Path(output).resolve()
    private = (ROOT / 'note10/private').resolve()
    if not output.is_relative_to(private) or output.exists():
        raise ValueError('Fresh private PM quiesce output directory required')
    output.mkdir(parents=True)
    names = ('pm_devices_backend.c', 'pm_decon_quiesce.c', 'pm_test_contract.h', 'pm_quiesce_core.h')
    sources = {name: (HERE / name).read_bytes() for name in names}
    compiler = (ROOT / 'host-tools/windows-build/llvm-mingw/llvm-mingw-20261006-ucrt-x86_64/bin/clang.exe'
                if sys.platform == 'win32' else shutil.which('clang') or shutil.which('cc'))
    if not compiler:
        raise RuntimeError('Native C compiler not found')
    cases, failures = [], []
    for quiesce, screen in ((1,1), (1,0), (0,1), (0,0)):
        label = f'quiesce-{quiesce}-screen-{screen}'
        defines = ('#define CONFIG_NOTE10_PM_QUIESCE 1\n' if quiesce else '') + ('#define CONFIG_NOTE10_SCREEN_LOG 1\n' if screen else '')
        text = STUB + sources['pm_test_contract.h'].decode() + sources['pm_quiesce_core.h'].decode() + defines + USB_PM
        if quiesce:
            text += _clean(sources['pm_decon_quiesce.c'].decode())
        text += _clean(sources['pm_devices_backend.c'].decode()) + MAIN
        src = output / (label+'.c')
        src.write_text(text, encoding='utf-8')
        exe = output / (label+('.exe' if sys.platform == 'win32' else ''))
        built = subprocess.run([str(compiler), '-std=c11', '-O2', '-Wall', '-Wextra', '-Werror', '-Wno-unused-function', '-Wno-unused-variable', '-Wno-unused-but-set-variable', '-Wno-unused-but-set-global', '-Wno-unused-label', str(src), '-o', str(exe)], capture_output=True, timeout=60)
        (output / (label+'-compile.log')).write_bytes(built.stdout+built.stderr)
        if built.returncode:
            failures.append(label+': compilation failed')
            continue
        modes = list(range(38)) if quiesce else [0,8,24,25]
        if not screen:
            modes = [m for m in modes if m not in (7,11,23)]
        for mode in modes:
            ran = subprocess.run([str(exe), str(mode)], capture_output=True, timeout=15)
            (output / f'{label}-mode-{mode}.log').write_bytes(ran.stdout+ran.stderr)
            case = {'configuration':label, 'case':mode, 'passed':ran.returncode==0, 'exit':ran.returncode, 'observation':(ran.stdout+ran.stderr).decode(errors='replace').strip()}
            cases.append(case)
            if ran.returncode:
                failures.append(f'{label}: mode {mode} exit {ran.returncode}')
    driver_binding=None
    if decon_core is not None:
        driver_cases,driver_binding=_driver_error_blocks(decon_core,output,compiler)
        cases.extend(driver_cases)
        failures.extend(f"generated-driver mode {c['case']} failed" for c in driver_cases if not c['passed'])
    report = {'passed':not failures, 'cases':cases, 'failures':failures,
              'source_sha256':{name:hashlib.sha256(data).hexdigest() for name,data in sources.items()},
              'harness_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'compiler':str(compiler), 'case_count':len(cases), 'generated_driver_error_blocks':driver_binding,
              'generated_decon_executed':driver_binding is not None,
              'generated_decon_sha256':driver_binding['source_sha256'] if driver_binding else None,
              'actual_backend_executed':any(c['configuration'].startswith('quiesce-') for c in cases), 'actual_decon_helper_executed':any(c['configuration'].startswith('quiesce-1') for c in cases),
              'device_operations':[], 'hardware_verified':False,
              'scope':'Actual pm_devices_backend.c and pm_decon_quiesce.c control flow; deterministic kernel API stubs, not physical hardware.'}
    (output/'result.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--decon-core',type=Path,help='Prepared generated decon_core.c for narrow actual driver error-block tests')
    args=parser.parse_args()
    report=run(args.output,args.decon_core)
    print(json.dumps({'passed':report['passed'],'cases':len(report['cases']),'failures':report['failures']}))
    raise SystemExit(0 if report['passed'] else 1)
