"""One NEW synchronous-deinit authentic-body batch, PM/nonPM in one binary."""
from pathlib import Path
import argparse
import hashlib
import json
import re
import subprocess
import sys

sys.dont_write_bytecode = True
from v147_iva_deinit import CTRL, CTRL_SHA256, patch_native, function_span
KREF_SHA256 = '741e9be0a201e55cb944ff27fd09d6b7b84c141acd1ea3b121fc9f8dbcc7ab3b'
IOCTL_ABI_SHA256 = '9fe84e259160ba29ee72d343c56ed3e4023195944e2f51cf408ba5223e71d886'
FUNCTIONS = ('iva_ctrl_release_global_init_ref', 'iva_ctrl_release_proc_init_ref',
             'iva_ctrl_deinit', 'iva_ctrl_deinit_forced',
             'n144_iva_ctrl_ioctl_body', 'n145_native_release')

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
#define __maybe_unused
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
#define IVA_ST_INIT_DONE 0
struct list_head { struct list_head *next,*prev; };
#define container_of(p,t,m) ((t*)((char*)(p)-offsetof(t,m)))
#define list_entry(p,t,m) container_of(p,t,m)
#define list_for_each(n,h) for(n=(h)->next;n!=(h);n=n->next)
static void INIT_LIST_HEAD(struct list_head *h) { h->next=h;h->prev=h; }
static void list_add(struct list_head *n,struct list_head *h) { n->next=h->next;n->prev=h;h->next->prev=n;h->next=n; }
static void list_del(struct list_head *n) { n->prev->next=n->next;n->next->prev=n->prev; }
struct kref { unsigned int refcount; };
struct device { int tag; };
struct task_struct { const char *comm; };
struct iva_dev_data { struct device *dev;struct kref glob_init_ref;unsigned long state;int proc_mutex;struct list_head proc_head; };
struct iva_proc { struct iva_dev_data *iva_data;struct kref init_ref;struct list_head proc_node;struct task_struct *tsk;int pid,tid; };
struct n144_buffer_call;
static struct device n147_device={1};
static struct task_struct n147_task={"NEW147"};
static int n147_assertions,n147_api_value,n147_pm_calls,n147_direct_calls;
static int n147_dec_calls,n147_sub_calls,n147_logs,n147_exit_calls,n147_mem_calls,n147_free_calls,n147_zero_seen;
static const struct kref *n147_zero_ref;
static char n147_order[64];static int n147_order_nr;
#define CHECK(c) do { ++n147_assertions;if(!(c)){fprintf(stderr,"line %d: %s\n",__LINE__,#c);exit(1);} } while(0)
static void n147_event(char c) { CHECK(n147_order_nr<63);n147_order[n147_order_nr++]=c;n147_order[n147_order_nr]=0; }
static unsigned int kref_read(const struct kref *ref) { if(ref==n147_zero_ref)++n147_zero_seen;return ref->refcount; }
static bool refcount_sub_and_test(unsigned int n,unsigned int *ref) { CHECK(n&&*ref>=n);++n147_sub_calls;*ref-=n;return !*ref; }
static bool refcount_dec_and_test(unsigned int *ref) { CHECK(*ref>0);++n147_dec_calls;--*ref;return !*ref; }
static bool test_bit(int bit,const unsigned long *value) { return !!(*value&(1UL<<bit)); }
static int pm_runtime_put_sync(struct device *dev) { CHECK(dev==&n147_device);++n147_pm_calls;n147_event('P');return n147_api_value; }
static int32_t __iva_ctrl_deinit(struct device *dev) { CHECK(dev==&n147_device);++n147_direct_calls;n147_event('N');return n147_api_value; }
static void n147_log(struct device *dev,const char *fmt,...) { CHECK(dev==&n147_device);(void)fmt;++n147_logs; }
#define dev_info n147_log
#define dev_dbg n147_log
#define dev_warn n147_log
#define dev_err n147_log
static void mutex_lock(int *m) { CHECK(!*m);*m=1; }
static void mutex_unlock(int *m) { CHECK(*m);*m=0; }
static int iva_ctrl_mcu_exit(struct iva_proc *p,bool forced) { CHECK(p->iva_data->dev==&n147_device&&forced);++n147_exit_calls;n147_event('X');return -EIO; }
static void iva_mem_deinit_proc_mem(struct iva_proc *p) { CHECK(p->iva_data->dev==&n147_device);++n147_mem_calls;n147_event('M'); }
static void devm_kfree(struct device *dev,void *p) { CHECK(dev==&n147_device&&p);++n147_free_calls;n147_event('F'); }
static const char *iva_ctrl_get_ioctl_str(unsigned int cmd) { (void)cmd;return "NEW147"; }
static int32_t iva_ctrl_init_usr(struct iva_proc *p,uint32_t *v) { (void)p;(void)v;CHECK(0);return 0; }
static int iva_ctrl_mcu_boot_file(struct iva_proc *p,const char *v,bool f) { (void)p;(void)v;(void)f;CHECK(0);return 0; }
static int iva_ctrl_get_iva_status_usr(struct iva_dev_data *v,struct iva_status_param *p) { (void)v;(void)p;CHECK(0);return 0; }
static int iva_ipcq_send_cmd_usr(struct iva_proc *p,struct ipc_cmd_param *v) { (void)p;(void)v;CHECK(0);return 0; }
static int iva_ipcq_wait_res_usr(struct iva_proc *p,struct ipc_res_param *v) { (void)p;(void)v;CHECK(0);return 0; }
static int32_t iva_ctrl_set_clk_usr(struct iva_dev_data *v,uint32_t *p) { (void)v;(void)p;CHECK(0);return 0; }
static long iva_mem_ioctl(struct iva_proc *p,unsigned int c,void *v,struct n144_buffer_call *call)
{ (void)p;(void)c;(void)v;(void)call;CHECK(0);return 0; }
'''

MAIN = r'''
struct n147_variant {
 bool pm;int32_t(*deinit)(struct iva_proc*,bool);void(*forced)(struct iva_dev_data*);
 long(*ioctl)(struct iva_proc*,unsigned int,uintptr_t,struct n144_buffer_call*);
 int(*close)(struct iva_proc*);
};
static const struct n147_variant n147_variants[]={
 {true,p_iva_ctrl_deinit,p_iva_ctrl_deinit_forced,p_n144_iva_ctrl_ioctl_body,p_n145_native_release},
 {false,n_iva_ctrl_deinit,n_iva_ctrl_deinit_forced,n_n144_iva_ctrl_ioctl_body,n_n145_native_release}
};
static void n147_reset(struct iva_dev_data *iva,struct iva_proc *a,struct iva_proc *b)
{
 memset(iva,0,sizeof(*iva));memset(a,0,sizeof(*a));memset(b,0,sizeof(*b));
 iva->dev=&n147_device;iva->state=1;iva->glob_init_ref.refcount=1;INIT_LIST_HEAD(&iva->proc_head);
 a->iva_data=b->iva_data=iva;a->tsk=b->tsk=&n147_task;a->pid=1;a->tid=2;b->pid=3;b->tid=4;
 a->init_ref.refcount=1;INIT_LIST_HEAD(&a->proc_node);INIT_LIST_HEAD(&b->proc_node);
 n147_api_value=n147_pm_calls=n147_direct_calls=n147_dec_calls=n147_sub_calls=n147_logs=0;
 n147_exit_calls=n147_mem_calls=n147_free_calls=n147_zero_seen=n147_order_nr=0;
 n147_zero_ref=NULL;n147_order[0]=0;
}
static void n147_one_api(const struct n147_variant *v)
{ CHECK(n147_pm_calls==(v->pm?1:0)&&n147_direct_calls==(v->pm?0:1)); }
int main(void)
{
 struct iva_dev_data iva;struct iva_proc a,b;const struct n147_variant *v;
 unsigned int i,j;int result;int values[]={-EINVAL,0,7};uint32_t argument=0;
 for(i=0;i<sizeof(n147_variants)/sizeof(n147_variants[0]);++i){
  v=&n147_variants[i];
  n147_reset(&iva,&a,&b);a.init_ref.refcount=0;iva.glob_init_ref.refcount=0;
  CHECK(v->deinit(&a,false)==0);CHECK(!n147_sub_calls&&!n147_dec_calls&&!n147_pm_calls&&!n147_direct_calls);
  n147_reset(&iva,&a,&b);a.init_ref.refcount=2;n147_api_value=-EIO;
  CHECK(v->deinit(&a,false)==0);CHECK(a.init_ref.refcount==1&&iva.glob_init_ref.refcount==1&&n147_sub_calls==1&&!n147_dec_calls&&!n147_pm_calls&&!n147_direct_calls&&n147_logs>0);
  n147_reset(&iva,&a,&b);iva.glob_init_ref.refcount=2;n147_api_value=-EIO;
  CHECK(v->deinit(&a,false)==0);CHECK(!a.init_ref.refcount&&iva.glob_init_ref.refcount==1&&n147_dec_calls==1&&!n147_pm_calls&&!n147_direct_calls&&n147_logs>0);
  n147_reset(&iva,&a,&b);iva.state=0;n147_api_value=-EIO;
  CHECK(v->deinit(&a,false)==0);CHECK(!a.init_ref.refcount&&!iva.glob_init_ref.refcount&&n147_dec_calls==1&&!n147_pm_calls&&!n147_direct_calls&&n147_logs>0);
  for(j=0;j<(v->pm?3U:2U);++j){
   n147_reset(&iva,&a,&b);n147_api_value=values[j];result=v->deinit(&a,false);
   CHECK(result==(values[j]<0?values[j]:0));n147_one_api(v);
   CHECK(n147_sub_calls==1&&n147_dec_calls==1&&!a.init_ref.refcount&&!iva.glob_init_ref.refcount);
   CHECK(v->deinit(&a,false)==0);n147_one_api(v);CHECK(n147_sub_calls==1&&n147_dec_calls==1);
  }
  n147_reset(&iva,&a,&b);a.init_ref.refcount=3;n147_api_value=-EIO;
  CHECK(v->deinit(&a,true)==-EIO);CHECK(!a.init_ref.refcount&&!iva.glob_init_ref.refcount&&n147_sub_calls==1&&n147_dec_calls==1);n147_one_api(v);
  n147_reset(&iva,&a,&b);n147_api_value=-EIO;
  CHECK(v->ioctl(&a,IVA_CTRL_DEINIT_IVA,(uintptr_t)&argument,NULL)==-EIO);n147_one_api(v);
  n147_reset(&iva,&a,&b);n147_api_value=0;
  CHECK(v->ioctl(&a,IVA_CTRL_DEINIT_IVA,(uintptr_t)&argument,NULL)==0);n147_one_api(v);
  n147_reset(&iva,&a,&b);n147_api_value=-EIO;list_add(&a.proc_node,&iva.proc_head);
  CHECK(v->close(&a)==0);n147_one_api(v);CHECK(n147_exit_calls==1&&n147_mem_calls==1&&n147_free_calls==1);
  CHECK(strcmp(n147_order,v->pm?"XPMF":"XNMF")==0&&iva.proc_head.next==&iva.proc_head);
  n147_reset(&iva,&a,&b);n147_api_value=-EIO;list_add(&b.proc_node,&iva.proc_head);list_add(&a.proc_node,&iva.proc_head);n147_zero_ref=&b.init_ref;
  v->forced(&iva);n147_one_api(v);CHECK(n147_zero_seen==1&&n147_sub_calls==1&&n147_dec_calls==1&&!a.init_ref.refcount&&!b.init_ref.refcount);
 }
 printf("NEW synchronous deinit API PASS; assertions=%d\n",n147_assertions);return 0;
}
'''


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--ctrl146', required=True, type=Path)
    parser.add_argument('--native-root', required=True, type=Path)
    parser.add_argument('--kref-header', required=True, type=Path)
    parser.add_argument('--cc', required=True, type=Path)
    args = parser.parse_args()
    out = args.output.resolve()
    if out.exists():
        raise ValueError('fresh once output required')
    ctrl = args.ctrl146.read_bytes()
    outputs = patch_native(ctrl)
    try:
        patch_native(ctrl + b'\n')
    except ValueError:
        pass
    else:
        raise AssertionError('NEW exact input refusal failed')
    kref = args.kref_header.read_bytes()
    if hashlib.sha256(kref).hexdigest() != KREF_SHA256:
        raise ValueError('actual target kref contract pin mismatch')
    if b'if (refcount_dec_and_test(&kref->refcount))' not in kref:
        raise ValueError('actual target kref decrement primitive missing')
    abi = (args.native_root / 'drivers/vision/iva/iva_ctrl_ioctl.h').read_bytes()
    if hashlib.sha256(abi).hexdigest() != IOCTL_ABI_SHA256:
        raise ValueError('actual ioctl ABI pin mismatch')
    source = outputs[CTRL]
    bodies = []
    for name in FUNCTIONS:
        start, end = function_span(source, name)
        body = source[start:end]
        if name == 'n144_iva_ctrl_ioctl_body':
            if body.count(b'unsigned long arg') != 1:
                raise ValueError('exact host ioctl argument bridge required')
            body = body.replace(b'unsigned long arg', b'uintptr_t arg', 1)
        bodies.append(body)
    names = re.compile(rb'\b(?:' + b'|'.join(n.encode() for n in FUNCTIONS) + rb')\b')
    fixture = PRELUDE.encode().replace(b'@NATIVE_IOCTL@', abi[abi.index(b'#define IVA_CTRL_BOOT_FILE_NAME_LEN'):abi.index(b'#endif')])
    for prefix, pm in [('p_', True), ('n_', False)]:
        fixture += b'\n#define CONFIG_PM 1\n' if pm else b'\n#undef CONFIG_PM\n'
        fixture += names.sub(lambda match: prefix.encode() + match.group(), b'\n\n'.join(bodies))
    fixture += MAIN.encode()
    out.mkdir(parents=True)
    target = out / 'native-output' / CTRL
    target.parent.mkdir(parents=True)
    target.write_bytes(source)
    file = out / 'native_deinit_fixture.c'
    file.write_bytes(fixture)
    executable = out / 'native_deinit_fixture.exe'
    compiler_argv = [str(args.cc.resolve()), '-std=gnu89', '-Wall', '-Wextra', '-Werror',
                     '-Wno-unused-function', '-Wdeclaration-after-statement', str(file), '-o', str(executable)]
    fixture_argv = [str(executable)]
    result = {'schema': 'v147-native-deinit-errno-once-v1', 'pass': False,
              'primary_transform_count': 1, 'negative_transform_count': 1,
              'compiler_count': 0, 'fixture_count': 0, 'old_tests_count': 0,
              'compiler_launch_attempts': 0, 'fixture_launch_attempts': 0,
              'argv': [sys.executable, *sys.argv], 'compiler_argv': compiler_argv, 'fixture_argv': fixture_argv,
              'input_ctrl146_sha256': CTRL_SHA256, 'target_kref_header_sha256': KREF_SHA256,
              'outputs': {CTRL: hashlib.sha256(source).hexdigest()},
              'fixture_sha256': hashlib.sha256(fixture).hexdigest(),
              'authentic_native_bodies': list(FUNCTIONS), 'CONFIG_PM_variants': [True, False],
              'host_bridge': 'Host-only function-name prefixes and ioctl arg/casts uintptr_t; production ABI unchanged.',
              'callback_execution_claim': False, 'physical_owner_success': False}
    try:
        result['compiler_launch_attempts'] = 1
        compiled = subprocess.run(compiler_argv, capture_output=True, text=True)
        result.update(compiler_count=1, compiler_returncode=compiled.returncode)
        (out / 'compiler.txt').write_bytes((compiled.stdout + compiled.stderr).encode())
        if not compiled.returncode:
            result['fixture_launch_attempts'] = 1
            ran = subprocess.run(fixture_argv, capture_output=True, text=True)
            result.update(fixture_count=1, fixture_returncode=ran.returncode, **{'pass': ran.returncode == 0})
            (out / 'fixture.txt').write_bytes((ran.stdout + ran.stderr).encode())
    except OSError as error:
        result['launch_error'] = str(error)
    (out / 'result.json').write_bytes((json.dumps(result, indent=2) + '\n').encode())
    if not result['pass']:
        raise RuntimeError('NEW147 batch failed; no automatic retry')


if __name__ == '__main__':
    main()
