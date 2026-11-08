"""One NEW authentic native init-state batch; execution belongs to ROOT."""
from pathlib import Path
import argparse
import hashlib
import json
import re
import subprocess
import sys

sys.dont_write_bytecode = True
from v149_iva_init_state import CTRL, CTRL_SHA256, patch_native
ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'note10/private/device-test/v149-iva-init-state-rollback-20261108'
INPUT = ROOT / 'note10/private/device-test/v148-iva-pm-init-accounting-20261107/new-native-init-pm-accounting-once/native-output' / CTRL
TOKENS = re.compile(rb'/\*.*?\*/|//[^\n]*|"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'|[{}]', re.S)


def native_init(raw):
    matches = list(re.finditer(rb'^static int32_t __iva_ctrl_init\(struct device \*dev\)', raw, re.M))
    if len(matches) != 1:
        raise ValueError('exact authentic native __iva_ctrl_init body required')
    start = matches[0].start()
    depth = 0
    for token in TOKENS.finditer(raw, raw.index(b'{', matches[0].end())):
        if token.group() == b'{':
            depth += 1
        elif token.group() == b'}':
            depth -= 1
            if not depth:
                return raw[start:token.end()]
    raise ValueError('unbalanced native init body')


PRELUDE = r'''
#include <stdint.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdarg.h>
#include <errno.h>
#undef ENABLE_FPGA_REG_ACCESS
#undef CONFIG_EXYNOS_IMA
#undef CONFIG_EXYNOS_IMA_MODULE
#define IVA_ST_INIT_DONE 0
struct clk { int tag; };
struct device { void *driver_data; };
struct iva_dev_data {
 struct device *dev;struct clk *iva_clk;unsigned long state;bool en_hwa_req;int mcu_ipcq;
};
static struct device n149_dev;
static struct clk n149_clock={1};
static int n149_assertions,n149_clock_result,n149_clock_calls,n149_rate_calls,n149_set_calls,n149_clear_calls;
static int n149_pmu_calls,n149_mbox_calls,n149_pending_calls,n149_error_logs,n149_warn_logs;
static char n149_order[64];static unsigned int n149_order_nr;
#define CHECK(c) do { ++n149_assertions;if(!(c)){fprintf(stderr,"line %d: %s\n",__LINE__,#c);exit(1);} } while(0)
static void n149_event(char c) { CHECK(n149_order_nr<63);n149_order[n149_order_nr++]=c;n149_order[n149_order_nr]=0; }
static struct iva_dev_data *dev_get_drvdata(struct device *dev)
{ CHECK(dev==&n149_dev);return dev->driver_data; }
static bool test_and_set_bit(int bit,unsigned long *state)
{ bool old;CHECK(bit==IVA_ST_INIT_DONE);old=!!(*state&(1UL<<bit));*state|=1UL<<bit;++n149_set_calls;n149_event('S');return old; }
static void clear_bit(int bit,unsigned long *state)
{ CHECK(bit==IVA_ST_INIT_DONE&&(*state&(1UL<<bit)));*state&=~(1UL<<bit);++n149_clear_calls;n149_event('R'); }
static int clk_prepare_enable(struct clk *clock)
{ CHECK(clock==&n149_clock);++n149_clock_calls;n149_event('C');return n149_clock_result; }
static unsigned long clk_get_rate(struct clk *clock)
{ CHECK(clock==&n149_clock);++n149_rate_calls;n149_event('G');return 400000; }
static void iva_pmu_init(struct iva_dev_data *iva,bool en_hwa)
{ CHECK(iva==n149_dev.driver_data&&en_hwa&&!!(iva->state&1UL));++n149_pmu_calls;n149_event('P'); }
static int iva_mbox_init(struct iva_dev_data *iva)
{ CHECK(iva==n149_dev.driver_data);++n149_mbox_calls;n149_event('M');return 0; }
static void iva_ipcq_init_pending_mail(int *ipcq)
{ struct iva_dev_data *iva=n149_dev.driver_data;CHECK(ipcq==&iva->mcu_ipcq);++n149_pending_calls;n149_event('Q'); }
static void n149_debug(struct device *dev,const char *fmt,...)
{ CHECK(dev==&n149_dev);(void)fmt; }
static void n149_error(struct device *dev,const char *fmt,...)
{ CHECK(dev==&n149_dev);(void)fmt;++n149_error_logs;n149_event('E'); }
static void n149_warn(struct device *dev,const char *fmt,...)
{ CHECK(dev==&n149_dev);(void)fmt;++n149_warn_logs; }
#define dev_dbg n149_debug
#define dev_err n149_error
#define dev_warn n149_warn
'''

MAIN = r'''
static void n149_reset(struct iva_dev_data *iva,unsigned long state,bool clock)
{
 memset(iva,0,sizeof(*iva));iva->dev=&n149_dev;iva->iva_clk=clock?&n149_clock:NULL;
 iva->state=state;iva->en_hwa_req=true;n149_dev.driver_data=iva;
 n149_clock_result=n149_clock_calls=n149_rate_calls=n149_set_calls=n149_clear_calls=0;
 n149_pmu_calls=n149_mbox_calls=n149_pending_calls=n149_error_logs=n149_warn_logs=0;
 n149_order_nr=0;n149_order[0]=0;
}
int main(void)
{
 struct iva_dev_data iva;int errors[]={-EIO,-EINVAL,-EAGAIN};unsigned int i;
 unsigned long unrelated=(1UL<<1)|(1UL<<4);
 for(i=0;i<sizeof(errors)/sizeof(errors[0]);++i){
  n149_reset(&iva,unrelated,true);n149_clock_result=errors[i];
  CHECK(__iva_ctrl_init(&n149_dev)==errors[i]);
  CHECK(iva.state==unrelated&&iva.en_hwa_req&&iva.iva_clk==&n149_clock);
  CHECK(n149_set_calls==1&&n149_clear_calls==1&&n149_clock_calls==1&&!n149_rate_calls);
  CHECK(!n149_pmu_calls&&!n149_mbox_calls&&!n149_pending_calls&&n149_error_logs==1&&!n149_warn_logs);
  CHECK(strcmp(n149_order,"SCER")==0);
  n149_clock_result=0;CHECK(__iva_ctrl_init(&n149_dev)==0);
  CHECK(iva.state==(unrelated|1UL)&&n149_clock_calls==2&&n149_rate_calls==1);
  CHECK(n149_set_calls==2&&n149_clear_calls==1&&n149_pmu_calls==1&&n149_mbox_calls==1&&n149_pending_calls==1);
  CHECK(strcmp(n149_order,"SCERSCGPMQ")==0&&n149_error_logs==1);
  CHECK(__iva_ctrl_init(&n149_dev)==0);
  CHECK(iva.state==(unrelated|1UL)&&n149_clock_calls==2&&n149_rate_calls==1&&n149_clear_calls==1);
  CHECK(n149_set_calls==3&&n149_pmu_calls==1&&n149_mbox_calls==1&&n149_pending_calls==1&&n149_warn_logs==1);
  CHECK(strcmp(n149_order,"SCERSCGPMQS")==0);
 }
 n149_reset(&iva,unrelated,true);CHECK(__iva_ctrl_init(&n149_dev)==0);
 CHECK(iva.state==(unrelated|1UL)&&n149_clock_calls==1&&n149_rate_calls==1&&!n149_clear_calls);
 CHECK(n149_pmu_calls==1&&n149_mbox_calls==1&&n149_pending_calls==1&&!n149_error_logs&&!n149_warn_logs);
 CHECK(strcmp(n149_order,"SCGPMQ")==0);
 n149_reset(&iva,unrelated|1UL,true);n149_clock_result=-EIO;
 CHECK(__iva_ctrl_init(&n149_dev)==0);
 CHECK(iva.state==(unrelated|1UL)&&n149_set_calls==1&&!n149_clear_calls&&!n149_clock_calls&&!n149_rate_calls);
 CHECK(!n149_pmu_calls&&!n149_mbox_calls&&!n149_pending_calls&&!n149_error_logs&&n149_warn_logs==1);
 CHECK(strcmp(n149_order,"S")==0);
 n149_reset(&iva,unrelated,false);CHECK(__iva_ctrl_init(&n149_dev)==0);
 CHECK(iva.state==(unrelated|1UL)&&!iva.iva_clk&&!n149_clock_calls&&!n149_rate_calls&&!n149_clear_calls);
 CHECK(n149_set_calls==1&&n149_pmu_calls==1&&n149_mbox_calls==1&&n149_pending_calls==1&&!n149_error_logs&&!n149_warn_logs);
 CHECK(strcmp(n149_order,"SPMQ")==0);
 printf("NEW native init-state rollback PASS; assertions=%d\n",n149_assertions);return 0;
}
'''


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--ctrl148', required=True, type=Path)
    parser.add_argument('--cc', required=True, type=Path)
    args = parser.parse_args()
    out = args.output.absolute()
    if (not args.output.is_absolute() or out != BASE / 'new-native-init-state-once' or out.resolve() != out or
            out.exists() or out.is_symlink() or not out.parent.is_dir()):
        raise ValueError('fresh canonical once149 output required')
    if (not args.ctrl148.is_absolute() or args.ctrl148 != INPUT or args.ctrl148.resolve() != INPUT or
            args.ctrl148.is_symlink() or not args.ctrl148.is_file() or not 0 < args.ctrl148.stat().st_size <= 2 * 1024 * 1024):
        raise ValueError('exact ordinary148 composed ctrl input required')
    if not args.cc.is_absolute() or args.cc.is_symlink() or not args.cc.is_file():
        raise ValueError('absolute ordinary compiler required')
    ctrl = args.ctrl148.read_bytes()
    out.mkdir()
    source = out / 'native_init_state_fixture.c'
    executable = out / 'native_init_state_fixture.exe'
    compile_argv = [str(args.cc.resolve()), '-std=gnu89', '-Wall', '-Wextra', '-Werror',
                    '-Wno-unused-function', '-Wdeclaration-after-statement', str(source), '-o', str(executable)]
    fixture_argv = [str(executable)]
    result = dict(schema='v149-native-init-state-rollback-once-v1', **{'pass': False},
                  primary_transform_count=0, negative_transform_count=0, compiler_count=0, fixture_count=0,
                  old_tests_count=0, compiler_launch_attempts=0, fixture_launch_attempts=0,
                  argv=[sys.executable, *sys.argv], compiler_argv=compile_argv, fixture_argv=fixture_argv,
                  input_ctrl148_sha256=CTRL_SHA256, outputs={}, authentic_native_body='__iva_ctrl_init',
                  IMA_enabled=False, FPGA_enabled=False, host_ABI_bridge='None; selected body uses no userspace pointer transport.',
                  PM_callback_execution_claim=False, hardware_clock_execution_claim=False, physical_owner_success=False)

    def persist():
        (out / 'result.json').write_bytes((json.dumps(result, indent=2) + '\n').encode())

    persist()
    try:
        result['primary_transform_count'] = 1
        persist()
        outputs = patch_native(ctrl)
        result['outputs'] = {CTRL: hashlib.sha256(outputs[CTRL]).hexdigest()}
        result['negative_transform_count'] = 1
        persist()
        try:
            patch_native(ctrl + b'\n')
        except ValueError:
            pass
        else:
            raise AssertionError('exact NEW input refusal failed')
        fixture = PRELUDE.encode() + b'\n' + native_init(outputs[CTRL]) + b'\n' + MAIN.encode()
        target = out / 'native-output' / CTRL
        target.parent.mkdir(parents=True)
        target.write_bytes(outputs[CTRL])
        source.write_bytes(fixture)
        result['fixture_sha256'] = hashlib.sha256(fixture).hexdigest()
        result['compiler_launch_attempts'] = 1
        persist()
        compiled = subprocess.run(compile_argv, capture_output=True, text=True, cwd=ROOT, timeout=120)
        result.update(compiler_count=1, compiler_returncode=compiled.returncode)
        (out / 'compiler.txt').write_bytes((compiled.stdout + compiled.stderr).encode())
        if not compiled.returncode:
            result['fixture_launch_attempts'] = 1
            persist()
            ran = subprocess.run(fixture_argv, capture_output=True, text=True, cwd=ROOT, timeout=30)
            result.update(fixture_count=1, fixture_returncode=ran.returncode, **{'pass': ran.returncode == 0})
            (out / 'fixture.txt').write_bytes((ran.stdout + ran.stderr).encode())
    except BaseException as error:
        result.update(error_type=type(error).__name__, error=str(error)[:512])
        raise
    finally:
        persist()
    if not result['pass']:
        raise RuntimeError('NEW149 native init-state batch failed; no automatic retry')


if __name__ == '__main__':
    main()
