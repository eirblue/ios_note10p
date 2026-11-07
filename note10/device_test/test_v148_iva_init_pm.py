"""One NEW authentic native init-body batch; all runtime belongs to ROOT."""
from pathlib import Path
import argparse
import hashlib
import json
import re
import subprocess
import sys

sys.dont_write_bytecode = True
from v148_iva_init_pm import CTRL, CTRL_SHA256, patch_native
TOKENS = re.compile(rb'/\*.*?\*/|//[^\n]*|"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'|[{}]', re.S)


def native_init(raw):
    matches = list(re.finditer(rb'^static int32_t iva_ctrl_init\(struct iva_proc \*proc, bool en_hwa\)', raw, re.M))
    if len(matches) != 1:
        raise ValueError('exact authentic native init body required')
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
#include <stddef.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdarg.h>
#include <errno.h>
struct kref { unsigned int refcount; };
struct device { int usage_count;int runtime_status;int runtime_error; };
struct clk { int tag; };
struct iva_dev_data {
 struct device *dev;struct clk *iva_clk;struct kref glob_init_ref;
 bool en_hwa_req;unsigned long state;
};
struct iva_proc { struct iva_dev_data *iva_data;struct kref init_ref; };
static struct device n148_dev;
static struct clk n148_clock={1};
static int n148_assertions,n148_api_return,n148_get_calls,n148_noidle_calls,n148_direct_calls;
static int n148_get_unless_calls,n148_kref_init_calls,n148_reset_calls;
static int n148_error_logs,n148_info_logs,n148_debug_logs,n148_clock_reads;
static char n148_order[128];static unsigned int n148_order_nr;
#define CHECK(c) do { ++n148_assertions;if(!(c)){fprintf(stderr,"line %d: %s\n",__LINE__,#c);exit(1);} } while(0)
static void n148_event(char c) { CHECK(n148_order_nr<127);n148_order[n148_order_nr++]=c;n148_order[n148_order_nr]=0; }
static bool kref_get_unless_zero(struct kref *ref)
{ ++n148_get_unless_calls;if(!ref->refcount)return false;++ref->refcount;return true; }
static void kref_init(struct kref *ref) { ++n148_kref_init_calls;ref->refcount=1;n148_event('K'); }
static unsigned int kref_read(const struct kref *ref) { return ref->refcount; }
static void refcount_set(unsigned int *ref,unsigned int value)
{ CHECK(value==0);++n148_reset_calls;*ref=value;n148_event('R'); }
/* Instrument the pinned target API accounting, not hardware/callback state. */
static int pm_runtime_get_sync(struct device *dev)
{ CHECK(dev==&n148_dev);++n148_get_calls;++dev->usage_count;n148_event('G');return n148_api_return; }
static void pm_runtime_put_noidle(struct device *dev)
{ CHECK(dev==&n148_dev&&dev->usage_count>0);++n148_noidle_calls;--dev->usage_count;n148_event('B'); }
static int32_t __iva_ctrl_init(struct device *dev)
{ CHECK(dev==&n148_dev);++n148_direct_calls;n148_event('N');return n148_api_return; }
static unsigned long clk_get_rate(struct clk *clock)
{ CHECK(clock==&n148_clock);++n148_clock_reads;n148_event('C');return 400000; }
static void n148_error(struct device *dev,const char *fmt,...)
{ CHECK(dev==&n148_dev);(void)fmt;++n148_error_logs;n148_event('E'); }
static void n148_info(struct device *dev,const char *fmt,...)
{ CHECK(dev==&n148_dev);(void)fmt;++n148_info_logs;n148_event('I'); }
static void n148_debug(struct device *dev,const char *fmt,...)
{ CHECK(dev==&n148_dev);(void)fmt;++n148_debug_logs;n148_event('D'); }
#define dev_err n148_error
#define dev_info n148_info
#define dev_dbg n148_debug
'''

MAIN = r'''
struct n148_variant { bool pm;int32_t(*init)(struct iva_proc*,bool); };
static const struct n148_variant n148_variants[]={ {true,p_iva_ctrl_init},{false,n_iva_ctrl_init} };
static void n148_reset(struct iva_dev_data *iva,struct iva_proc *proc,int usage)
{
 memset(iva,0,sizeof(*iva));memset(proc,0,sizeof(*proc));iva->dev=&n148_dev;iva->iva_clk=&n148_clock;
 iva->en_hwa_req=true;iva->state=0x1234;proc->iva_data=iva;
 n148_dev.usage_count=usage;n148_dev.runtime_status=7;n148_dev.runtime_error=-9;
 n148_api_return=n148_get_calls=n148_noidle_calls=n148_direct_calls=0;
 n148_get_unless_calls=n148_kref_init_calls=n148_reset_calls=0;
 n148_error_logs=n148_info_logs=n148_debug_logs=n148_clock_reads=0;
 n148_order_nr=0;n148_order[0]=0;
}
static void n148_status_unchanged(struct iva_dev_data *iva)
{ CHECK(n148_dev.runtime_status==7&&n148_dev.runtime_error==-9&&iva->state==0x1234); }
static void n148_api_counts(const struct n148_variant *v,int calls,int balance)
{ CHECK(n148_get_calls==(v->pm?calls:0)&&n148_direct_calls==(v->pm?0:calls)&&n148_noidle_calls==(v->pm?balance:0)); }
int main(void)
{
 struct iva_dev_data iva;struct iva_proc proc;const struct n148_variant *v;
 unsigned int i,j;int usages[]={0,5};int errors[]={-EIO,-EINVAL,-EAGAIN};
 for(i=0;i<sizeof(n148_variants)/sizeof(n148_variants[0]);++i){
  v=&n148_variants[i];
  for(j=0;j<sizeof(errors)/sizeof(errors[0]);++j){
   n148_reset(&iva,&proc,usages[j%2]);n148_api_return=errors[j];
   CHECK(v->init(&proc,false)==errors[j]);n148_api_counts(v,1,1);
   CHECK(n148_dev.usage_count==usages[j%2]&&!proc.init_ref.refcount&&!iva.glob_init_ref.refcount&&!iva.en_hwa_req);
   CHECK(n148_get_unless_calls==2&&n148_kref_init_calls==1&&n148_reset_calls==1&&n148_error_logs==1&&!n148_info_logs&&!n148_debug_logs&&!n148_clock_reads);
   CHECK(strcmp(n148_order,v->pm?"KGBER":"KNER")==0);n148_status_unchanged(&iva);
  }
  n148_reset(&iva,&proc,0);n148_api_return=0;
  CHECK(v->init(&proc,true)==0);n148_api_counts(v,1,0);
  CHECK(proc.init_ref.refcount==1&&iva.glob_init_ref.refcount==1&&iva.en_hwa_req&&n148_dev.usage_count==(v->pm?1:0));
  CHECK(n148_kref_init_calls==2&&!n148_reset_calls&&!n148_error_logs&&n148_debug_logs==2&&n148_clock_reads==1);
  CHECK(strcmp(n148_order,v->pm?"KGKCDD":"KNKCDD")==0);n148_status_unchanged(&iva);
  if(v->pm){
   n148_reset(&iva,&proc,3);n148_api_return=1;CHECK(v->init(&proc,false)==0);n148_api_counts(v,1,0);
   CHECK(proc.init_ref.refcount==1&&iva.glob_init_ref.refcount==1&&n148_dev.usage_count==4&&!iva.en_hwa_req&&!n148_error_logs);
   CHECK(strcmp(n148_order,"KGKCDD")==0);n148_status_unchanged(&iva);
  }
  n148_reset(&iva,&proc,6);proc.init_ref.refcount=2;iva.glob_init_ref.refcount=4;n148_api_return=-EIO;
  CHECK(v->init(&proc,false)==0);n148_api_counts(v,0,0);
  CHECK(proc.init_ref.refcount==3&&iva.glob_init_ref.refcount==4&&iva.en_hwa_req&&n148_dev.usage_count==6);
  CHECK(n148_get_unless_calls==1&&!n148_kref_init_calls&&!n148_reset_calls&&n148_info_logs==1&&n148_debug_logs==1&&!n148_clock_reads&&strcmp(n148_order,"ID")==0);n148_status_unchanged(&iva);
  n148_reset(&iva,&proc,6);iva.glob_init_ref.refcount=3;n148_api_return=-EIO;
  CHECK(v->init(&proc,false)==0);n148_api_counts(v,0,0);
  CHECK(proc.init_ref.refcount==1&&iva.glob_init_ref.refcount==4&&iva.en_hwa_req&&n148_dev.usage_count==6);
  CHECK(n148_get_unless_calls==2&&n148_kref_init_calls==1&&!n148_reset_calls&&n148_info_logs==1&&n148_debug_logs==1&&!n148_clock_reads&&strcmp(n148_order,"KID")==0);n148_status_unchanged(&iva);
 }
 printf("NEW failed get_sync balance PASS; assertions=%d\n",n148_assertions);return 0;
}
'''


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--ctrl147', required=True, type=Path)
    parser.add_argument('--cc', required=True, type=Path)
    args = parser.parse_args()
    out = args.output.resolve()
    if out.exists():
        raise ValueError('fresh once output required')
    ctrl = args.ctrl147.read_bytes()
    outputs = patch_native(ctrl)
    try:
        patch_native(ctrl + b'\n')
    except ValueError:
        pass
    else:
        raise AssertionError('exact NEW input refusal failed')
    body = native_init(outputs[CTRL])
    fixture = PRELUDE.encode()
    for prefix, pm in [('p_', True), ('n_', False)]:
        fixture += b'\n#define CONFIG_PM 1\n' if pm else b'\n#undef CONFIG_PM\n'
        fixture += body.replace(b'iva_ctrl_init(', prefix.encode()+b'iva_ctrl_init(', 1) + b'\n'
    fixture += MAIN.encode()
    out.mkdir(parents=True)
    target = out / 'native-output' / CTRL
    target.parent.mkdir(parents=True)
    target.write_bytes(outputs[CTRL])
    source = out / 'native_init_pm_fixture.c'
    source.write_bytes(fixture)
    executable = out / 'native_init_pm_fixture.exe'
    compile_argv = [str(args.cc.resolve()), '-std=gnu89', '-Wall', '-Wextra', '-Werror',
                    '-Wno-unused-function', '-Wdeclaration-after-statement', str(source), '-o', str(executable)]
    fixture_argv = [str(executable)]
    result = {'schema':'v148-native-init-pm-accounting-once-v1', 'pass':False,
              'primary_transform_count':1, 'negative_transform_count':1,
              'compiler_count':0, 'fixture_count':0, 'old_tests_count':0,
              'compiler_launch_attempts':0, 'fixture_launch_attempts':0,
              'argv':[sys.executable,*sys.argv], 'compiler_argv':compile_argv, 'fixture_argv':fixture_argv,
              'input_ctrl147_sha256':CTRL_SHA256,
              'outputs':{CTRL:hashlib.sha256(outputs[CTRL]).hexdigest()},
              'fixture_sha256':hashlib.sha256(fixture).hexdigest(),
              'authentic_native_body':'iva_ctrl_init', 'CONFIG_PM_variants':[True,False],
              'host_ABI_bridge':'None needed: no user-pointer unsigned-long transport in selected init body.',
              'PM_callback_execution_claim':False, 'physical_owner_success':False}
    try:
        result['compiler_launch_attempts']=1
        compiled=subprocess.run(compile_argv,capture_output=True,text=True)
        result.update(compiler_count=1,compiler_returncode=compiled.returncode)
        (out/'compiler.txt').write_bytes((compiled.stdout+compiled.stderr).encode())
        if not compiled.returncode:
            result['fixture_launch_attempts']=1
            ran=subprocess.run(fixture_argv,capture_output=True,text=True)
            result.update(fixture_count=1,fixture_returncode=ran.returncode,**{'pass':ran.returncode==0})
            (out/'fixture.txt').write_bytes((ran.stdout+ran.stderr).encode())
    except OSError as error:
        result['launch_error']=str(error)
    (out/'result.json').write_bytes((json.dumps(result,indent=2)+'\n').encode())
    if not result['pass']:
        raise RuntimeError('NEW148 accounting batch failed; no automatic retry')


if __name__ == '__main__':
    main()
