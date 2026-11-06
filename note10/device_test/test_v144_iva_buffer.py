"""One NEW authentic native-body batch. Runtime is exclusively ROOT-owned."""
from pathlib import Path
import argparse
import hashlib
import json
import re
import subprocess
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
from v144_iva_buffer import CTRL, MEM, HEADER, HELPER, NATIVE_SHA256, patch_native

TOKENS = re.compile(rb'/\*.*?\*/|//[^\n]*|"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'|[{}]', re.S)


def function(raw, name):
    matches = list(re.finditer(rb'^(?:static\s+)?(?:struct iva_mem_map\s*\*|long\s+|int\s+)' +
                              name.encode() + rb'\s*\(', raw, re.M))
    if len(matches) != 1:
        raise ValueError('exact authentic native definition required: ' + name)
    start = matches[0].start()
    depth = 0
    for token in TOKENS.finditer(raw, raw.index(b'{', matches[0].end())):
        if token.group() == b'{':
            depth += 1
        elif token.group() == b'}':
            depth -= 1
            if depth == 0:
                return raw[start:token.end()]
    raise ValueError('unbalanced native function')


def host_ioctl_body(raw):
    """Host-only LLP64 bridge: native AArch64 unsigned-long arg is pointer-wide."""
    if raw.count(b'unsigned long arg') != 1:
        raise ValueError('exact native ioctl argument declaration required')
    return raw.replace(b'unsigned long arg', b'uintptr_t arg', 1)


DMA_SHIM = r'''
#ifndef TEST_DMA_H
#define TEST_DMA_H
#include <stdbool.h>
#include <stddef.h>
struct dma_buf_ops { int tag; };
struct dma_buf { const struct dma_buf_ops *ops; size_t size; int refs; };
void dma_buf_put(struct dma_buf *buf);
#endif
'''
ERR_SHIM = r'''
#include <stdint.h>
#define IS_ERR(p) ((uintptr_t)(p) >= (uintptr_t)-4095)
#define IS_ERR_OR_NULL(p) (!(p) || IS_ERR(p))
'''

PRELUDE = r'''
#include <stdint.h>
#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <stdarg.h>
#include "v144_iva_buffer.h"
#define __user
#define EINVAL 22
#define ENOTTY 25
#define _IOC_WRITE 1
#define _IOC_READ 2
#define _IOC_DIR(c) (((c) >> 30) & 3)
#define _IOC_TYPE(c) (((c) >> 8) & 255)
#define _IOC(d,t,n,s) (((unsigned int)(d)<<30) | ((unsigned int)(s)<<16) | ((t)<<8) | (n))
#define _IOW(t,n,s) _IOC(_IOC_WRITE,t,n,sizeof(s))
#define _IOR(t,n,s) _IOC(_IOC_READ,t,n,sizeof(s))
#define _IOWR(t,n,s) _IOC(3,t,n,sizeof(s))
#define CMD(n) _IOWR(IVA_CTRL_MAGIC,n,struct iva_ion_param)
struct ipc_cmd_param { int unused; };
struct ipc_res_param { int unused; };
@NATIVE_IOCTL@
#define IVA_MEM_GET_SHARED_FD(fd) ((fd) & ~(1 << 24))
#define IVA_ALLOC_TYPE_IMPORTED 2
#define SET_IVA_ALLOC_TYPE(f,t) ((f) |= ((t) & 3))
struct device { int live; };
struct iva_dev_data { struct device *dev; };
struct iva_proc { struct iva_dev_data *iva_data; int mem_map_lock; int h_mem_map; int mem_map_nr; };
struct file { void *private_data; };
struct iva_mem_map {
 int shared_fd; struct dma_buf *dmabuf; void *attachment; void *sg_table;
 unsigned long io_va; uint32_t req_size,act_size; int flags;
 struct { int refcount; } map_ref; struct device *dev; int h_node;
};
const struct dma_buf_ops ion_dma_buf_ops = { 1 };
static const struct dma_buf_ops foreign_ops = { 1 };
static struct dma_buf ion,foreign,other;
static struct dma_buf *fd_object;
static struct iva_proc *owner;
static struct iva_mem_map *published;
static int n144_gets,n144_puts,foreign_puts,allocs,frees,maps,locks,logs,dead;
static int fail_alloc,fail_map,fail_copy_in,fail_copy_out,recycle,kill_on_put;
static int perf_complete,expect_perf,checks;
#define CHECK(c) do { ++checks; if (!(c)) { fprintf(stderr,"line %d: %s\n",__LINE__,#c); exit(1); } } while (0)
static void native_log(struct device *d,const char *format,...)
{ CHECK(!dead && d && d->live); ++logs; (void)format; }
#define dev_dbg native_log
#define dev_warn native_log
#define dev_err native_log
#define dev_info native_log
static void mutex_lock(int *lock) { CHECK(!dead && !*lock); *lock=1; ++locks; }
static void mutex_unlock(int *lock) { CHECK(!dead && *lock); *lock=0; --locks; }
static void refcount_set(int *ref,int n) { *ref=n; }
static void publish(struct iva_mem_map *m) { CHECK(!published); published=m; }
#define hash_add(table,node,fd) publish(iva_map_node)
static struct iva_mem_map *iva_mem_alloc_map_node(struct iva_dev_data *iva)
{ CHECK(!dead && iva==owner->iva_data); ++allocs; return fail_alloc?NULL:calloc(1,sizeof(struct iva_mem_map)); }
static void iva_mem_free_map_node(struct iva_dev_data *iva,struct iva_mem_map *m)
{ CHECK(!dead && iva==owner->iva_data); ++frees; free(m); }
static struct dma_buf *dma_buf_get(int fd)
{
 struct dma_buf *result=fd_object;
 CHECK(!dead && fd==7); ++n144_gets;
 if (result && !IS_ERR(result)) ++result->refs;
 if (recycle) fd_object=&other;
 return result;
}
void dma_buf_put(struct dma_buf *buf)
{
 CHECK(buf && !IS_ERR(buf) && buf->refs>0); --buf->refs; ++n144_puts;
 if (buf->ops != &ion_dma_buf_ops) {
  ++foreign_puts;
  CHECK(!locks && !published && (!expect_perf || perf_complete));
  if (kill_on_put) {
   free(owner->iva_data->dev); free(owner->iva_data); free(owner);
   owner=NULL; dead=1;
  }
 }
}
static struct iva_mem_map *iva_mem_find_proc_map_with_fd_nolock(struct iva_proc *proc,int fd)
{ CHECK(!dead && proc==owner && proc->mem_map_lock); return published && published->shared_fd==fd?published:NULL; }
static int iva_mem_get_ion_iova(struct iva_proc *proc,struct iva_mem_map *m)
{
 CHECK(!dead && proc==owner && m->dmabuf->ops==&ion_dma_buf_ops);
 CHECK(m->dmabuf==&ion); ++maps; m->io_va=0x123400; return fail_map?-5:0;
}
static void iva_mem_cancel_imported_ion_buf(struct iva_proc *proc,struct iva_mem_map *m)
{ CHECK(proc==owner); dma_buf_put(m->dmabuf); published=NULL; --proc->mem_map_nr; iva_mem_free_map_node(proc->iva_data,m); }
static int copy_from_user(void *to,const void *from,size_t n)
{ CHECK(!dead); if(fail_copy_in)return 3; memcpy(to,from,n); return 0; }
static int copy_to_user(void *to,const void *from,size_t n)
{ CHECK(!dead); if(fail_copy_out)return 4; memcpy(to,from,n); return 0; }
#define MEM_STUB(name) static int name(struct iva_proc *p,struct iva_ion_param *a) { CHECK(!dead && p==owner); (void)a; return 37; }
MEM_STUB(iva_mem_put_ion_iova_param)
MEM_STUB(iva_mem_ion_alloc_param)
MEM_STUB(iva_mem_ion_free_param)
MEM_STUB(iva_mem_ion_sync_for_cpu_param)
MEM_STUB(iva_mem_ion_sync_for_device_param)
static const char *iva_ctrl_get_ioctl_str(unsigned int cmd) { (void)cmd; return "fixture"; }
static int iva_ctrl_init_usr(struct iva_proc *p,uint32_t *v) { CHECK(p==owner); (void)v; return 31; }
static int iva_ctrl_deinit(struct iva_proc *p,bool f) { CHECK(p==owner); (void)f; return 32; }
static int iva_ctrl_mcu_boot_file(struct iva_proc *p,const char *s,bool f) { CHECK(p==owner); (void)s;(void)f;return 33; }
static int iva_ctrl_mcu_exit(struct iva_proc *p,bool f) { CHECK(p==owner);(void)f;return 34; }
static int iva_ctrl_get_iva_status_usr(struct iva_dev_data *v,struct iva_status_param *p) { CHECK(v==owner->iva_data);(void)p;return 35; }
static int iva_ipcq_send_cmd_usr(struct iva_proc *p,struct ipc_cmd_param *v) { CHECK(p==owner);(void)v;return 36; }
static int iva_ipcq_wait_res_usr(struct iva_proc *p,struct ipc_res_param *v) { CHECK(p==owner);(void)v;return 38; }
static int iva_ctrl_set_clk_usr(struct iva_dev_data *v,uint32_t *p) { CHECK(v==owner->iva_data);(void)p;return 39; }
/* Extra compiled authentic conditional tail proves deferred release ordering. */
#define ENABLE_MEASURE_IVA_PERF
struct timeval { long tv_sec,tv_usec; };
static void do_gettimeofday(struct timeval *v) { CHECK(!dead); v->tv_sec=0;v->tv_usec=0; }
static int iva_timeval_diff_us(struct timeval *a,struct timeval *b) { (void)a;(void)b;perf_complete=1;return 0; }
'''

MAIN = r'''
static void reset(void)
{
 CHECK(!locks);
 if (published) { CHECK(published->dmabuf==&ion); --ion.refs; free(published); published=NULL; }
 if(owner) { free(owner->iva_data->dev);free(owner->iva_data);free(owner); }
 owner=calloc(1,sizeof(*owner)); owner->iva_data=calloc(1,sizeof(*owner->iva_data));
 owner->iva_data->dev=calloc(1,sizeof(struct device)); owner->iva_data->dev->live=1;
 ion.ops=&ion_dma_buf_ops;ion.size=8192;ion.refs=0;
 foreign.ops=&foreign_ops;foreign.size=16384;foreign.refs=0;
 other.ops=&foreign_ops;other.size=4096;other.refs=0;
 fd_object=&ion; n144_gets=n144_puts=foreign_puts=allocs=frees=maps=logs=dead=0;
 fail_alloc=fail_map=fail_copy_in=fail_copy_out=recycle=kill_on_put=0;
 perf_complete=expect_perf=0;
}
static long call(unsigned int cmd,struct iva_ion_param *p)
{ struct file f; f.private_data=owner; expect_perf=0; return iva_ctrl_ioctl_selected(&f,cmd,(uintptr_t)p); }
int main(void)
{
 struct iva_ion_param p; struct n144_buffer_call ctx; struct dma_buf *held;
 unsigned int commands[]={IVA_CTRL_INIT_IVA,IVA_CTRL_DEINIT_IVA,IVA_CTRL_BOOT_MCU,IVA_CTRL_EXIT_MCU,
 IVA_CTRL_GET_STATUS,IVA_IPC_QUEUE_SEND_CMD,IVA_IPC_QUEUE_RECEIVE_RSP,IVA_CTRL_SET_CLK,
 IVA_ION_PUT_IOVA,IVA_ION_ALLOC,IVA_ION_FREE,IVA_ION_SYNC_FOR_CPU,IVA_ION_SYNC_FOR_DEVICE};
 int returns[]={31,32,33,34,35,36,38,39,0,0,0,0,0}; unsigned int i;
 memset(&p,0,sizeof(p));p.shared_fd=7;
 reset();CHECK(call(IVA_ION_GET_IOVA,&p)==0);CHECK(n144_gets==1 && maps==1 && n144_puts==0 && ion.refs==1);
 CHECK(p.iova==0x123400 && p.size==8192 && owner->mem_map_nr==1);
 CHECK(call(IVA_ION_GET_IOVA,&p)==0);CHECK(n144_gets==1 && maps==2);
 reset();p.shared_fd=(1<<24)|7;CHECK(call(IVA_ION_GET_IOVA,&p)==0);CHECK(n144_gets==1 && published->shared_fd==p.shared_fd);p.shared_fd=7;
 reset();fd_object=&foreign;kill_on_put=1;CHECK(call(IVA_ION_GET_IOVA,&p)==-EINVAL);
 CHECK(dead && !owner && n144_gets==1 && foreign_puts==1 && foreign.refs==0 && allocs==1 && frees==1 && maps==0);
 reset();fd_object=&foreign;kill_on_put=1;expect_perf=1;
 {struct file f;f.private_data=owner;CHECK(iva_ctrl_ioctl(&f,IVA_ION_GET_IOVA,(uintptr_t)&p)==-EINVAL);}
 CHECK(dead && perf_complete && foreign_puts==1 && !owner);
 reset();fd_object=&foreign;recycle=1;CHECK(call(IVA_ION_GET_IOVA,&p)==-EINVAL);
 CHECK(n144_gets==1 && foreign_puts==1 && other.refs==0 && maps==0);
 reset();recycle=1;CHECK(call(IVA_ION_GET_IOVA,&p)==0);CHECK(n144_gets==1 && published->dmabuf==&ion && other.refs==0);
 reset();fd_object=(struct dma_buf *)(intptr_t)-9;CHECK(call(IVA_ION_GET_IOVA,&p)==-EINVAL);CHECK(n144_gets==1 && n144_puts==0 && frees==1);
 reset();fd_object=NULL;CHECK(call(IVA_ION_GET_IOVA,&p)==-EINVAL);CHECK(n144_puts==0 && frees==1);
 reset();fail_alloc=1;CHECK(call(IVA_ION_GET_IOVA,&p)==-EINVAL);CHECK(n144_gets==0 && n144_puts==0);
 reset();fail_map=1;CHECK(call(IVA_ION_GET_IOVA,&p)==-5);CHECK(n144_gets==1 && maps==1 && n144_puts==1 && ion.refs==0 && !published);
 reset();fail_copy_in=1;CHECK(call(IVA_ION_GET_IOVA,&p)==3);CHECK(n144_gets==0 && allocs==0);
 reset();fail_copy_out=1;CHECK(call(IVA_ION_GET_IOVA,&p)==4);CHECK(ion.refs==1 && maps==1 && n144_gets==1);
 reset();CHECK(call(CMD(99),&p)==-ENOTTY);CHECK(!n144_gets && !n144_puts);
 reset();expect_perf=0;{struct file f;f.private_data=owner;CHECK(iva_ctrl_ioctl(&f,0,(uintptr_t)&p)==-EINVAL);CHECK(iva_ctrl_ioctl(&f,IVA_ION_GET_IOVA,0)==-EINVAL);}CHECK(!n144_gets && !n144_puts);
 for(i=0;i<sizeof(commands)/sizeof(commands[0]);++i) { reset();CHECK(call(commands[i],&p)==returns[i]);CHECK(!n144_gets && !n144_puts && !maps); }
 reset();n144_buffer_call_init(&ctx);fd_object=&foreign;
 CHECK(iva_mem_import_ion_buf(owner,7,&ctx)==NULL);CHECK(ctx.foreign_put==&foreign && ctx.refused_history && foreign.refs==1);
 held=ctx.foreign_put;CHECK(iva_mem_import_ion_buf(owner,7,&ctx)==NULL);CHECK(n144_gets==1 && allocs==1 && ctx.foreign_put==held);
 n144_buffer_call_finish(&ctx);CHECK(foreign_puts==1 && !ctx.active && !ctx.foreign_put);
 n144_buffer_call_finish(&ctx);CHECK(foreign_puts==1);CHECK(iva_mem_import_ion_buf(owner,7,&ctx)==NULL);CHECK(n144_gets==1);
 reset();CHECK(iva_mem_import_ion_buf(owner,7,NULL)==NULL);CHECK(!n144_gets && !allocs);
 n144_buffer_call_init(&ctx);ctx.foreign_put=(struct dma_buf *)(intptr_t)-7;n144_buffer_call_finish(&ctx);
 CHECK(!n144_puts && !ctx.active && ctx.refused_history);n144_buffer_call_finish(NULL);
 reset();n144_buffer_call_init(&ctx);ctx.refused_history=true;CHECK(iva_mem_import_ion_buf(owner,7,&ctx)==NULL);CHECK(!n144_gets && !allocs);
 reset();free(owner->iva_data->dev);free(owner->iva_data);free(owner);owner=NULL;
 printf("NEW native ION boundary PASS; assertions=%d\n",checks);return 0;
}
'''


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--native-root', required=True, type=Path)
    parser.add_argument('--ctrl142', required=True, type=Path)
    parser.add_argument('--cc', required=True, type=Path)
    args = parser.parse_args()
    out = args.output.resolve()
    if out.exists():
        raise ValueError('one-shot output must not exist')
    inputs = {name: (args.ctrl142 if name == CTRL else args.native_root / name).read_bytes()
              for name in NATIVE_SHA256}
    abi = (args.native_root / 'drivers/vision/iva/iva_ctrl_ioctl.h').read_bytes()
    abi_pin = hashlib.sha256(abi).hexdigest()
    if abi_pin != '9fe84e259160ba29ee72d343c56ed3e4023195944e2f51cf408ba5223e71d886':
        raise ValueError('native ioctl ABI pin mismatch')
    abi = abi[abi.index(b'#define IVA_CTRL_BOOT_FILE_NAME_LEN'):abi.index(b'#endif')]
    helper = (HERE / 'v144_iva_buffer.h').read_bytes()
    outputs = patch_native(inputs, helper)
    # NEW transform refusal contracts, no accepted142/143 execution.
    refusals = 0
    for bad in ({}, {**inputs, CTRL: inputs[CTRL] + b'\n'}):
        try:
            patch_native(bad, helper)
        except ValueError:
            refusals += 1
    try:
        patch_native(inputs, helper + b'\n')
    except ValueError:
        refusals += 1
    if refusals != 3:
        raise AssertionError('transform did not fail closed')
    out.mkdir(parents=True)
    for name, data in outputs.items():
        target = out / 'native-output' / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    shim = out / 'include' / 'linux'
    shim.mkdir(parents=True)
    (shim / 'dma-buf.h').write_bytes(DMA_SHIM.encode())
    (shim / 'err.h').write_bytes(ERR_SHIM.encode())
    (out / 'include' / 'v144_iva_buffer.h').write_bytes(helper)
    bodies = [function(outputs[MEM], name) for name in (
        'iva_mem_import_ion_buf', 'iva_mem_get_ion_iova_param', 'iva_mem_ioctl')]
    bodies += [host_ioctl_body(function(outputs[CTRL], name)) for name in (
        'n144_iva_ctrl_ioctl_body', 'iva_ctrl_ioctl')]
    selected = b'\n\n'.join(bodies[-2:])
    selected = selected.replace(b'n144_iva_ctrl_ioctl_body', b'n144_native_selected_body')
    selected = selected.replace(b'iva_ctrl_ioctl(', b'iva_ctrl_ioctl_selected(')
    fixture = out / 'native_buffer_fixture.c'
    fixture.write_bytes(PRELUDE.encode().replace(b'@NATIVE_IOCTL@', abi) + b'\n\n'.join(bodies) +
                        b'\n#undef ENABLE_MEASURE_IVA_PERF\n' + selected + MAIN.encode())
    executable = out / 'native_buffer_fixture.exe'
    compile_argv = [str(args.cc.resolve()), '-std=gnu89', '-Wall', '-Wextra', '-Werror',
                    '-Wno-unused-function', '-Wdeclaration-after-statement', '-I', str(out / 'include'), str(fixture), '-o', str(executable)]
    compiled = subprocess.run(compile_argv, capture_output=True, text=True)
    (out / 'compiler.txt').write_bytes((compiled.stdout + compiled.stderr).encode())
    if compiled.returncode:
        raise RuntimeError('NEW fixture compiler failed; no retry')
    fixture_argv = [str(executable)]
    ran = subprocess.run(fixture_argv, capture_output=True, text=True)
    (out / 'fixture.txt').write_bytes((ran.stdout + ran.stderr).encode())
    result = {'schema': 'v144-new-native-ion-boundary-once-v1', 'pass': ran.returncode == 0,
              'compiler_count': 1, 'fixture_count': 1, 'primary_transform_count': 1,
              'negative_transform_count': refusals, 'old_tests_count': 0,
              'argv': [sys.executable, *sys.argv], 'compiler_argv': compile_argv, 'fixture_argv': fixture_argv,
              'inputs': NATIVE_SHA256, 'native_ioctl_abi_sha256': abi_pin,
              'outputs': {k: hashlib.sha256(v).hexdigest() for k, v in outputs.items()},
              'fixture_sha256': hashlib.sha256(fixture.read_bytes()).hexdigest(),
              'authentic_functions': 5, 'ctrl_conditional_variants': 2,
              'host_pointer_ABI_bridges': ['Only extracted native ioctl arg declarations unsigned long -> uintptr_t; host caller casts uintptr_t. Production output unchanged.'],
              'runtime_returncode': ran.returncode}
    (out / 'result.json').write_bytes((json.dumps(result, indent=2) + '\n').encode())
    if ran.returncode:
        raise RuntimeError('NEW fixture failed; no retry')


if __name__ == '__main__':
    main()
