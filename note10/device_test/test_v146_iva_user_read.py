"""One NEW authentic get_user/body-route batch; runtime belongs to ROOT."""
from pathlib import Path
import argparse
import hashlib
import json
import re
import subprocess
import sys

sys.dont_write_bytecode = True
from v146_iva_user_read import CTRL, CTRL_SHA256, patch_native
IOCTL_ABI_SHA256 = '9fe84e259160ba29ee72d343c56ed3e4023195944e2f51cf408ba5223e71d886'
TOKENS = re.compile(rb'/\*.*?\*/|//[^\n]*|"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'|[{}]', re.S)


def function(raw, name):
    matches = list(re.finditer(rb'^static\s+(?:inline\s+)?(?:int32_t|long)\s+' +
                              name.encode() + rb'\s*\(', raw, re.M))
    if len(matches) != 1:
        raise ValueError('exact authentic function required: ' + name)
    start = matches[0].start()
    depth = 0
    for token in TOKENS.finditer(raw, raw.index(b'{', matches[0].end())):
        if token.group() == b'{':
            depth += 1
        elif token.group() == b'}':
            depth -= 1
            if depth == 0:
                return raw[start:token.end()]
    raise ValueError('unbalanced native definition')


PRELUDE = r'''
#include <stdint.h>
#include <stddef.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdarg.h>
#include <errno.h>
#define __user
#define _IOC_WRITE 1
#define _IOC_READ 2
#define _IOC_DIR(c) (((c)>>30)&3)
#define _IOC_TYPE(c) (((c)>>8)&255)
#define _IOC(d,t,n,s) (((unsigned int)(d)<<30)|((unsigned int)(s)<<16)|((t)<<8)|(n))
#define _IOW(t,n,s) _IOC(1,t,n,sizeof(s))
#define _IOR(t,n,s) _IOC(2,t,n,sizeof(s))
#define _IOWR(t,n,s) _IOC(3,t,n,sizeof(s))
struct ipc_cmd_param { int opaque; };
struct ipc_res_param { int opaque; };
@NATIVE_IOCTL@
@NATIVE_CLOCK_MACROS@
#define IS_ERR(p) ((uintptr_t)(p)>=(uintptr_t)-4095)
struct device { int tag; };
struct platform_device { struct device dev; };
struct clk { int tag; };
struct dev_pm_opp { int tag; };
struct iva_dev_data {
 struct device *dev;struct platform_device *iva_dvfs_dev;struct clk *iva_clk;
 int32_t iva_qos_rate;bool iva_bus_qos_en;
};
struct iva_proc { struct iva_dev_data *iva_data; };
/* The two selected ioctl branches never inspect the opaque memory-call ctx. */
struct n144_buffer_call;
static struct device n146_device={1};
static struct platform_device n146_dvfs={{2}};
static struct clk n146_clock={3};
static struct dev_pm_opp n146_opp={4};
static int n146_assertions,n146_user_fault,n146_reads,n146_init_calls,n146_init_result;
static int n146_opp_calls,n146_rate_logs,n146_warn_logs,n146_debug_logs,n146_clock_reads,n146_entry_traces;
static uint32_t n146_init_value;
static char n146_order[128];static int n146_order_nr;
#define CHECK(c) do { ++n146_assertions;if(!(c)){fprintf(stderr,"line %d: %s\n",__LINE__,#c);exit(1);} } while(0)
static void n146_event(char c) { CHECK(n146_order_nr<127);n146_order[n146_order_nr++]=c;n146_order[n146_order_nr]=0; }
static int n146_get_user(uint32_t *value,const uint32_t *user)
{
 ++n146_reads;n146_event('G');
 if(n146_user_fault||!user){*value=0;return -EFAULT;}
 *value=*user;return 0;
}
#define get_user(value,user) n146_get_user(&(value),(user))
static int iva_ctrl_init(struct iva_proc *proc,uint32_t value)
{ CHECK(proc->iva_data->dev==&n146_device);++n146_init_calls;n146_init_value=value;n146_event('N');return n146_init_result; }
static struct dev_pm_opp *dev_pm_opp_find_freq_ceil(struct device *dev,unsigned long *freq)
{
 ++n146_opp_calls;n146_event('O');CHECK(dev==&n146_dvfs.dev);
 if(*freq<=100)*freq=100;else if(*freq<=200)*freq=200;else if(*freq<=300)*freq=300;
 else return (struct dev_pm_opp *)(intptr_t)-ENODEV;
 return &n146_opp;
}
static unsigned long clk_get_rate(struct clk *clock)
{ CHECK(clock==&n146_clock);++n146_clock_reads;n146_event('C');return 100; }
static void n146_info(struct device *dev,const char *fmt,...)
{ CHECK(dev==&n146_device);(void)fmt;++n146_rate_logs;n146_event('I'); }
static void n146_warn(struct device *dev,const char *fmt,...)
{ CHECK(dev==&n146_device);(void)fmt;++n146_warn_logs;n146_event('W'); }
static void n146_debug(struct device *dev,const char *fmt,...)
{ CHECK(dev==&n146_device);if(strstr(fmt,"cmd(")){++n146_entry_traces;n146_event('T');}else{++n146_debug_logs;n146_event('D');} }
#define dev_info n146_info
#define dev_warn n146_warn
#define dev_dbg n146_debug
static const char *iva_ctrl_get_ioctl_str(unsigned int cmd) { (void)cmd;return "NEW146"; }
static int iva_ctrl_deinit(struct iva_proc *p,bool force) { (void)p;(void)force;CHECK(0);return 0; }
static int iva_ctrl_mcu_boot_file(struct iva_proc *p,const char *v,bool force) { (void)p;(void)v;(void)force;CHECK(0);return 0; }
static int iva_ctrl_mcu_exit(struct iva_proc *p,bool force) { (void)p;(void)force;CHECK(0);return 0; }
static int iva_ctrl_get_iva_status_usr(struct iva_dev_data *v,struct iva_status_param *p) { (void)v;(void)p;CHECK(0);return 0; }
static int iva_ipcq_send_cmd_usr(struct iva_proc *p,struct ipc_cmd_param *v) { (void)p;(void)v;CHECK(0);return 0; }
static int iva_ipcq_wait_res_usr(struct iva_proc *p,struct ipc_res_param *v) { (void)p;(void)v;CHECK(0);return 0; }
static long iva_mem_ioctl(struct iva_proc *p,unsigned int c,void *v,struct n144_buffer_call *call)
{ (void)p;(void)c;(void)v;(void)call;CHECK(0);return 0; }
'''

MAIN = r'''
static void n146_reset(struct iva_dev_data *iva)
{
 iva->dev=&n146_device;iva->iva_dvfs_dev=&n146_dvfs;iva->iva_clk=&n146_clock;
 iva->iva_qos_rate=123;iva->iva_bus_qos_en=true;
 n146_user_fault=n146_reads=n146_init_calls=n146_init_result=n146_opp_calls=0;
 n146_rate_logs=n146_warn_logs=n146_debug_logs=n146_clock_reads=n146_entry_traces=0;
 n146_init_value=0xdeadbeef;n146_order_nr=0;n146_order[0]=0;
}
static void n146_no_helper_effects(struct iva_dev_data *iva)
{
 CHECK(!n146_init_calls&&!n146_opp_calls&&!n146_rate_logs&&!n146_warn_logs&&!n146_debug_logs&&!n146_clock_reads);
 CHECK(iva->iva_qos_rate==123&&iva->iva_bus_qos_en);
}
int main(void)
{
 struct iva_dev_data iva;struct iva_proc proc;uint32_t value;unsigned int i;
 uint32_t flags[]={0,1,0xffffffffU};
 proc.iva_data=&iva;
 for(i=0;i<sizeof(flags)/sizeof(flags[0]);++i){
  n146_reset(&iva);value=flags[i];n146_user_fault=1;
  CHECK(iva_ctrl_init_usr(&proc,&value)==-EFAULT);CHECK(n146_reads==1&&strcmp(n146_order,"G")==0);n146_no_helper_effects(&iva);
  n146_reset(&iva);value=flags[i];n146_init_result=-EIO;
  CHECK(iva_ctrl_init_usr(&proc,&value)==-EIO);CHECK(n146_reads==1&&n146_init_calls==1&&n146_init_value==value&&strcmp(n146_order,"GN")==0);
 }
 n146_reset(&iva);CHECK(iva_ctrl_init_usr(&proc,NULL)==-EFAULT);n146_no_helper_effects(&iva);
 n146_reset(&iva);value=17;CHECK(iva_ctrl_init_usr(&proc,&value)==0);CHECK(n146_init_calls==1&&n146_init_value==17);
 n146_reset(&iva);value=200;n146_user_fault=1;
 CHECK(iva_ctrl_set_clk_usr(&iva,&value)==-EFAULT);CHECK(n146_reads==1&&strcmp(n146_order,"G")==0);n146_no_helper_effects(&iva);
 n146_reset(&iva);iva.iva_dvfs_dev=NULL;CHECK(iva_ctrl_set_clk_usr(&iva,NULL)==-EFAULT);n146_no_helper_effects(&iva);
 n146_reset(&iva);value=200|(1U<<24);CHECK(iva_ctrl_set_clk_usr(&iva,&value)==0);
 CHECK(n146_reads==1&&n146_opp_calls==2&&iva.iva_qos_rate==200&&iva.iva_bus_qos_en&&strcmp(n146_order,"GOOICD")==0);
 n146_reset(&iva);value=300;CHECK(iva_ctrl_set_clk_usr(&iva,&value)==0);
 CHECK(n146_opp_calls==3&&iva.iva_qos_rate==300&&!iva.iva_bus_qos_en&&strcmp(n146_order,"GOOOICD")==0);
 n146_reset(&iva);value=250;CHECK(iva_ctrl_set_clk_usr(&iva,&value)==0);
 CHECK(n146_opp_calls==4&&iva.iva_qos_rate==123&&!iva.iva_bus_qos_en&&strcmp(n146_order,"GOOOOIWCD")==0);
 n146_reset(&iva);iva.iva_dvfs_dev=NULL;value=0;CHECK(iva_ctrl_set_clk_usr(&iva,&value)==0);
 CHECK(!n146_opp_calls&&iva.iva_qos_rate==0&&!iva.iva_bus_qos_en&&strcmp(n146_order,"GICD")==0);
 n146_reset(&iva);iva.iva_dvfs_dev=NULL;value=200|(1U<<24);CHECK(iva_ctrl_set_clk_usr(&iva,&value)==0);
 CHECK(!n146_opp_calls&&iva.iva_qos_rate==123&&iva.iva_bus_qos_en&&strcmp(n146_order,"GIWCD")==0);
 n146_reset(&iva);value=0xffffffffU;CHECK(iva_ctrl_set_clk_usr(&iva,&value)==0);
 CHECK(iva.iva_qos_rate==123&&iva.iva_bus_qos_en&&n146_opp_calls==4);
 n146_reset(&iva);value=0;n146_user_fault=1;
 CHECK(n144_iva_ctrl_ioctl_body(&proc,IVA_CTRL_INIT_IVA,(uintptr_t)&value,NULL)==-EFAULT);
 CHECK(n146_reads==1&&n146_entry_traces==1&&strcmp(n146_order,"TG")==0);n146_no_helper_effects(&iva);
 n146_reset(&iva);value=300;n146_user_fault=1;
 CHECK(n144_iva_ctrl_ioctl_body(&proc,IVA_CTRL_SET_CLK,(uintptr_t)&value,NULL)==-EFAULT);
 CHECK(n146_reads==1&&n146_entry_traces==1&&strcmp(n146_order,"TG")==0);n146_no_helper_effects(&iva);
 n146_reset(&iva);value=23;n146_init_result=-EIO;
 CHECK(n144_iva_ctrl_ioctl_body(&proc,IVA_CTRL_INIT_IVA,(uintptr_t)&value,NULL)==-EIO);
 CHECK(n146_reads==1&&n146_init_calls==1&&n146_init_value==23&&strcmp(n146_order,"TGN")==0);
 n146_reset(&iva);value=100;
 CHECK(n144_iva_ctrl_ioctl_body(&proc,IVA_CTRL_SET_CLK,(uintptr_t)&value,NULL)==0);
 CHECK(n146_reads==1&&n146_opp_calls==1&&iva.iva_qos_rate==100&&strcmp(n146_order,"TGOICD")==0);
 printf("NEW native user-read guards PASS; assertions=%d\n",n146_assertions);return 0;
}
'''


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--ctrl145', required=True, type=Path)
    parser.add_argument('--native-root', required=True, type=Path)
    parser.add_argument('--cc', required=True, type=Path)
    args = parser.parse_args()
    out = args.output.resolve()
    if out.exists():
        raise ValueError('once output must not exist')
    if not IOCTL_ABI_SHA256:
        raise ValueError('FINAL ABI pin required')
    ctrl = args.ctrl145.read_bytes()
    outputs = patch_native(ctrl)
    try:
        patch_native(ctrl + b'\n')
    except ValueError:
        pass
    else:
        raise AssertionError('NEW exact input refusal failed')
    abi = (args.native_root / 'drivers/vision/iva/iva_ctrl_ioctl.h').read_bytes()
    if hashlib.sha256(abi).hexdigest() != IOCTL_ABI_SHA256:
        raise ValueError('actual ioctl ABI pin mismatch')
    raw = outputs[CTRL]
    if raw.count(b'#define BUS_CLK_FLAG_S') != 1:
        raise ValueError('exact native clock macro block required')
    clock_start = raw.index(b'#define BUS_CLK_FLAG_S')
    clock_end = raw.index(b'static int32_t iva_ctrl_set_clk_usr(', clock_start)
    clock_macros = raw[clock_start:clock_end]
    bodies = [function(raw, n) for n in ('iva_ctrl_init_usr', 'iva_ctrl_set_clk_usr')]
    ioctl = function(raw, 'n144_iva_ctrl_ioctl_body')
    if ioctl.count(b'unsigned long arg') != 1:
        raise ValueError('exact host-only ioctl argument bridge required')
    bodies.append(ioctl.replace(b'unsigned long arg', b'uintptr_t arg', 1))
    fixture = PRELUDE.encode().replace(b'@NATIVE_IOCTL@', abi[abi.index(b'#define IVA_CTRL_BOOT_FILE_NAME_LEN'):abi.index(b'#endif')])
    fixture = fixture.replace(b'@NATIVE_CLOCK_MACROS@', clock_macros)
    fixture += b'\n\n'.join(bodies) + MAIN.encode()
    out.mkdir(parents=True)
    target = out / 'native-output' / CTRL
    target.parent.mkdir(parents=True)
    target.write_bytes(outputs[CTRL])
    source = out / 'native_user_read_fixture.c'
    source.write_bytes(fixture)
    executable = out / 'native_user_read_fixture.exe'
    compile_argv = [str(args.cc.resolve()), '-std=gnu89', '-Wall', '-Wextra', '-Werror',
                    '-Wno-unused-function', '-Wdeclaration-after-statement', str(source), '-o', str(executable)]
    fixture_argv = [str(executable)]
    result = {'schema': 'v146-native-user-read-once-v1', 'pass': False,
              'primary_transform_count': 1, 'negative_transform_count': 1,
              'compiler_count': 0, 'fixture_count': 0, 'old_tests_count': 0,
              'compiler_launch_attempts': 0, 'fixture_launch_attempts': 0,
              'argv': [sys.executable, *sys.argv], 'compiler_argv': compile_argv, 'fixture_argv': fixture_argv,
              'input_ctrl145_sha256': CTRL_SHA256,
              'outputs': {CTRL: hashlib.sha256(outputs[CTRL]).hexdigest()},
              'fixture_sha256': hashlib.sha256(fixture).hexdigest(),
              'native_clock_macros_sha256': hashlib.sha256(clock_macros).hexdigest(),
              'authentic_native_functions': 3,
              'host_pointer_ABI_bridge': 'Extracted ioctl unsigned-long arg and host casts uintptr_t only; production ABI untouched.',
              'physical_owner_success': False}
    try:
        result['compiler_launch_attempts'] = 1
        compiled = subprocess.run(compile_argv, capture_output=True, text=True)
        result['compiler_count'] = 1
        result['compiler_returncode'] = compiled.returncode
        (out / 'compiler.txt').write_bytes((compiled.stdout + compiled.stderr).encode())
        if not compiled.returncode:
            result['fixture_launch_attempts'] = 1
            ran = subprocess.run(fixture_argv, capture_output=True, text=True)
            result['fixture_count'] = 1
            result['fixture_returncode'] = ran.returncode
            result['pass'] = ran.returncode == 0
            (out / 'fixture.txt').write_bytes((ran.stdout + ran.stderr).encode())
    except OSError as error:
        result['launch_error'] = str(error)
    (out / 'result.json').write_bytes((json.dumps(result, indent=2) + '\n').encode())
    if not result['pass']:
        raise RuntimeError('NEW user-read batch failed; no automatic retry')


if __name__ == '__main__':
    main()
