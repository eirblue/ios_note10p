"""One NEW authentic native mmap-denial batch; execution belongs to ROOT."""
from pathlib import Path
import argparse
import hashlib
import json
import subprocess
import sys

sys.dont_write_bytecode = True
from v145_iva_sidecar import HELPER_SHA256, function_span
from v151_iva_mmap_deny import CTRL, CTRL_SHA256, DENIED, patch_native

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'note10/private/device-test/v151-iva-diagnostic-mmap-deny-20261109'
INPUT = ROOT / 'note10/private/device-test/v149-iva-init-state-rollback-20261108/new-native-init-state-once/native-output' / CTRL
HELPER = ROOT / 'note10/device_test/v145_iva_sidecar.inc'

PRELUDE = r'''
#include <stdint.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>
struct device { bool held;void *driver_data; };
struct task_struct { int tag; };
struct iva_dev_data { int tag; };
struct iva_proc { struct iva_dev_data *iva_data;struct task_struct *tsk; };
struct vm_area_struct { unsigned long sentinel; };
struct file { void *private_data; };
enum n145_task_owner { N145_NATIVE_OWNED,N145_CTX_OWNED,N145_TASK_DEFERRED,N145_CONSUMED };
struct n145_binding {
 struct device *dev;struct iva_dev_data *native;
 bool registered,attached,closing;unsigned long history;
};
struct n145_file {
 struct n145_binding *binding;struct iva_proc *native;struct task_struct *task;
 enum n145_task_owner task_owner;bool quarantined;
};
static struct device n151_dev;
static unsigned long n145_lifetime_history;
static int n145_registry_lock;
static bool n151_registry_held;
static int n151_assertions,n151_locks,n151_unlocks,n151_spinlocks,n151_spinunlocks;
static int n151_native_calls,n151_mode;
#define CHECK(c) do { ++n151_assertions;if(!(c)){fprintf(stderr,"line %d: %s\n",__LINE__,#c);exit(1);} } while(0)
static void device_lock(struct device *dev)
{ CHECK(dev==&n151_dev&&!dev->held);dev->held=true;++n151_locks; }
static void device_unlock(struct device *dev)
{ CHECK(dev==&n151_dev&&dev->held&&!n151_registry_held);dev->held=false;++n151_unlocks; }
static void *dev_get_drvdata(struct device *dev)
{ CHECK(dev==&n151_dev&&dev->held);return dev->driver_data; }
/* Synthetic lock ownership only; no real device mutex, IRQ or SMP execution. */
static unsigned long n151_spin_lock(int *lock)
{ CHECK(lock==&n145_registry_lock&&n151_dev.held&&!n151_registry_held);n151_registry_held=true;++n151_spinlocks;return 0x151UL; }
static void n151_spin_unlock(int *lock,unsigned long flags)
{ CHECK(lock==&n145_registry_lock&&n151_registry_held&&flags==0x151UL);n151_registry_held=false;++n151_spinunlocks; }
#define spin_lock_irqsave(lock,flags) do { (flags)=n151_spin_lock(lock); } while(0)
#define spin_unlock_irqrestore(lock,flags) n151_spin_unlock(lock,flags)
'''

BRIDGE = r'''
static int n145_native_mmap(struct iva_proc *proc,struct vm_area_struct *vma)
{
 CHECK(n151_dev.held&&!n151_registry_held);++n151_native_calls;
 if(n151_mode)return n151_enabled_mmap(proc,vma);
 return n151_disabled_mmap(proc,vma);
}
'''

MAIN = r'''
static void n151_reset(struct n145_binding *binding,struct n145_file *ctx,
                       struct iva_proc *proc,struct iva_dev_data *iva,struct task_struct *task,
                       unsigned long history)
{
 memset(&n151_dev,0,sizeof(n151_dev));memset(binding,0,sizeof(*binding));memset(ctx,0,sizeof(*ctx));
 n151_dev.driver_data=iva;binding->dev=&n151_dev;binding->native=iva;
 binding->registered=true;binding->attached=true;binding->history=history;
 proc->iva_data=iva;proc->tsk=task;ctx->binding=binding;ctx->native=proc;ctx->task=task;
 ctx->task_owner=N145_NATIVE_OWNED;n145_lifetime_history=history;
 n151_native_calls=n151_locks=n151_unlocks=n151_spinlocks=n151_spinunlocks=0;n151_registry_held=false;
}
static void n151_balanced(int locks,int calls)
{
 CHECK(!n151_dev.held&&!n151_registry_held&&n151_locks==locks&&n151_unlocks==locks);
 CHECK(n151_spinlocks==n151_spinunlocks&&n151_native_calls==calls);
}
int main(void)
{
 struct n145_binding binding;struct n145_file ctx;struct iva_proc proc;
 struct iva_dev_data iva;struct task_struct task;struct file file;struct vm_area_struct vma;
 unsigned long sticky=N145_MMAP_SUCCESS|N145_UNSAFE;int mode;
 vma.sentinel=0xabcdefUL;
 CHECK(n151_enabled_mmap(NULL,NULL)==-EOPNOTSUPP);
 CHECK(n151_disabled_mmap(NULL,NULL)==-EOPNOTSUPP);
 CHECK(n151_enabled_mmap((struct iva_proc *)(uintptr_t)1,(struct vm_area_struct *)(uintptr_t)1)==-EOPNOTSUPP);
 CHECK(n151_disabled_mmap((struct iva_proc *)(uintptr_t)1,(struct vm_area_struct *)(uintptr_t)1)==-EOPNOTSUPP);
 for(mode=0;mode<2;++mode){
  n151_mode=mode;n151_reset(&binding,&ctx,&proc,&iva,&task,0);file.private_data=&ctx;
  CHECK(iva_ctrl_mmap(&file,&vma)==-EOPNOTSUPP);n151_balanced(1,1);
  CHECK(binding.history==N145_MMAP_ATTEMPT&&n145_lifetime_history==N145_MMAP_ATTEMPT);
  CHECK(vma.sentinel==0xabcdefUL&&ctx.native==&proc&&proc.iva_data==&iva);
  CHECK(iva_ctrl_mmap(&file,NULL)==-EOPNOTSUPP);n151_balanced(2,2);
  CHECK(binding.history==N145_MMAP_ATTEMPT&&n145_lifetime_history==N145_MMAP_ATTEMPT);
  n151_reset(&binding,&ctx,&proc,&iva,&task,sticky);
  CHECK(iva_ctrl_mmap(&file,(struct vm_area_struct *)(uintptr_t)1)==-EOPNOTSUPP);n151_balanced(1,1);
  CHECK(binding.history==(sticky|N145_MMAP_ATTEMPT)&&n145_lifetime_history==(sticky|N145_MMAP_ATTEMPT));
  n151_reset(&binding,&ctx,&proc,&iva,&task,0);
  binding.attached=false;binding.closing=true;binding.native=NULL;ctx.native=NULL;
  CHECK(iva_ctrl_mmap(&file,(struct vm_area_struct *)(uintptr_t)1)==-ENODEV);n151_balanced(1,0);
  CHECK(binding.history==N145_MMAP_ATTEMPT&&n145_lifetime_history==N145_MMAP_ATTEMPT);
  n151_reset(&binding,&ctx,&proc,&iva,&task,0);ctx.quarantined=true;
  CHECK(iva_ctrl_mmap(&file,NULL)==-ENODEV);n151_balanced(1,0);
  CHECK(binding.history==N145_MMAP_ATTEMPT&&n145_lifetime_history==N145_MMAP_ATTEMPT);
  n151_reset(&binding,&ctx,&proc,&iva,&task,sticky);file.private_data=NULL;
  CHECK(iva_ctrl_mmap(&file,NULL)==-ENODEV);n151_balanced(0,0);
  CHECK(binding.history==sticky&&n145_lifetime_history==sticky);
 }
 CHECK(vma.sentinel==0xabcdefUL);
 printf("NEW native mmap denial PASS; assertions=%d\n",n151_assertions);return 0;
}
'''


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--ctrl149', required=True, type=Path)
    parser.add_argument('--cc', required=True, type=Path)
    args = parser.parse_args()
    out = args.output.absolute()
    if (not args.output.is_absolute() or out != BASE / 'new-native-mmap-deny-once' or out.resolve() != out or
            out.exists() or out.is_symlink() or not out.parent.is_dir()):
        raise ValueError('fresh canonical once151 output required')
    if (not args.ctrl149.is_absolute() or args.ctrl149 != INPUT or args.ctrl149.resolve() != INPUT or
            args.ctrl149.is_symlink() or not args.ctrl149.is_file() or not 0 < args.ctrl149.stat().st_size <= 2 * 1024 * 1024):
        raise ValueError('exact ordinary149 composed ctrl input required')
    if not args.cc.is_absolute() or args.cc.is_symlink() or not args.cc.is_file():
        raise ValueError('absolute ordinary compiler required')
    ctrl = args.ctrl149.read_bytes()
    helper = HELPER.read_bytes()
    if hashlib.sha256(helper).hexdigest() != HELPER_SHA256:
        raise ValueError('exact unchanged145 sidecar required')
    out.mkdir()
    source = out / 'native_mmap_deny_fixture.c'
    executable = out / 'native_mmap_deny_fixture.exe'
    compile_argv = [str(args.cc.resolve()), '-std=gnu89', '-Wall', '-Wextra', '-Werror',
                    '-Wdeclaration-after-statement', str(source), '-o', str(executable)]
    fixture_argv = [str(executable)]
    result = dict(schema='v151-native-mmap-deny-once-v1', **{'pass': False},
                  primary_transform_count=0, negative_transform_count=0, compiler_count=0, fixture_count=0,
                  old_tests_count=0, compiler_launch_attempts=0, fixture_launch_attempts=0,
                  argv=[sys.executable, *sys.argv], compiler_argv=compile_argv, fixture_argv=fixture_argv,
                  input_ctrl149_sha256=CTRL_SHA256, unchanged145_sidecar_sha256=HELPER_SHA256, outputs={},
                  authentic_native_body='n145_native_mmap',
                  authentic_unchanged145_bodies=['n145_history', 'n145_file_attached', 'iva_ctrl_mmap'],
                  ENABLE_MMAP_US_configurations=[False, True],
                  host_ABI_bridge='None; pointer arguments retain native types; preprocessor aliases select two identical native bodies.',
                  hardware_MMIO_DMA_execution_claim=False, physical_owner_success=False)

    def persist():
        (out / 'result.json').write_bytes((json.dumps(result, indent=2) + '\n').encode())

    persist()
    try:
        result['primary_transform_count'] = 1
        persist()
        outputs = patch_native(ctrl)
        result['outputs'] = {CTRL: hashlib.sha256(outputs[CTRL]).hexdigest()}
        start, end = function_span(ctrl, 'n145_native_mmap')
        if outputs[CTRL] != ctrl[:start] + DENIED + ctrl[end:]:
            raise AssertionError('only exact mmap body may change')
        native_start, native_end = function_span(outputs[CTRL], 'n145_native_mmap')
        native = outputs[CTRL][native_start:native_end]
        if native != DENIED:
            raise AssertionError('native denial must ignore arguments without mapping calls')
        result['negative_transform_count'] = 1
        persist()
        try:
            patch_native(ctrl + b'\n')
        except ValueError:
            pass
        else:
            raise AssertionError('exact NEW input refusal failed')
        macros_start = helper.index(b'#define N145_UNSAFE ')
        macros_end = helper.index(b'static LIST_HEAD(n145_bindings);', macros_start)
        fixture = PRELUDE.encode() + b'\n' + helper[macros_start:macros_end]
        fixture += b'\n#define ENABLE_MMAP_US\n#define n145_native_mmap n151_enabled_mmap\n' + native
        fixture += b'\n#undef n145_native_mmap\n#undef ENABLE_MMAP_US\n#define n145_native_mmap n151_disabled_mmap\n' + native
        fixture += b'\n#undef n145_native_mmap\n' + BRIDGE.encode()
        fixture += b'\n' + helper[helper.index(b'static void n145_history('):helper.index(b'\nstatic void n145_binding_free(')]
        fixture += b'\n' + helper[helper.index(b'static bool n145_file_attached('):helper.index(b'\nstatic int iva_ctrl_open(')]
        begin, finish = function_span(helper, 'iva_ctrl_mmap')
        fixture += b'\n' + helper[begin:finish] + b'\n'
        fixture += MAIN.encode()
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
        raise RuntimeError('NEW151 native mmap denial batch failed; no automatic retry')


if __name__ == '__main__':
    main()
