"""One NEW authentic registrar batch; execution belongs to ROOT."""
from pathlib import Path
import argparse
import hashlib
import json
import subprocess
import sys

sys.dont_write_bytecode = True
from v145_iva_sidecar import TOKENS
from v153_iommu_fault_register import IOMMU, IOMMU_SHA256, NEW_STRUCT, EDITS, patch_native

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'note10/private/device-test/v153-iommu-fault-registration-once-20261109'
INPUT = ROOT / 'note10/private/device-test/v152-iva-fault-token-drain-20261109/new-native-fault-token-once/native-output' / IOMMU


def body(raw, signature):
    if raw.count(signature) != 1:
        raise ValueError('one exact native definition required')
    start = raw.index(signature)
    depth = 0
    for token in TOKENS.finditer(raw, raw.index(b'{', start + len(signature))):
        if token.group() == b'{':
            depth += 1
        elif token.group() == b'}':
            depth -= 1
            if not depth:
                return raw[start:token.end()]
    raise ValueError('unbalanced native body')


PRELUDE = r'''
#include <stdbool.h>
#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>
#include <stdarg.h>
struct list_head { struct list_head *next,*prev; };
struct device { struct { void *iommu; } archdata;void *driver_data; };
struct iommu_domain { int tag; };
typedef int (*iommu_fault_handler_t)(struct iommu_domain *,struct device *,unsigned long,int,void *);
struct notifier_block { int (*notifier_call)(struct notifier_block *,unsigned long,void *); };
struct atomic_notifier_head { struct notifier_block *record;int count; };
struct sysmmu_drvdata { struct atomic_notifier_head fault_notifiers; };
struct owner_fault_info { struct device *master;struct notifier_block nb; };
struct exynos_iommu_owner { bool lock;struct list_head sysmmu_list;iommu_fault_handler_t fault_handler;void *token; };
#define GFP_ATOMIC 1
#define has_sysmmu(dev) ((dev)->archdata.iommu != NULL)
#define container_of(ptr,type,member) ((type *)((char *)(ptr)-offsetof(type,member)))
#define list_for_each_entry(pos,head,member) \
 for((pos)=container_of((head)->next,struct sysmmu_list_data,member);&(pos)->member!=(head);(pos)=container_of((pos)->member.next,struct sysmmu_list_data,member))
static int n153_assertions;
#define CHECK(c) do { ++n153_assertions;if(!(c)){fprintf(stderr,"line %d: %s\n",__LINE__,#c);exit(1);} } while(0)
'''

LEAVES = r'''
static struct exynos_iommu_owner n153_owner;
static struct device n153_master,n153_sysmmu[2];
static struct sysmmu_drvdata n153_drv[2];
static struct sysmmu_list_data n153_entries[2];
static struct owner_fault_info n153_pool[2];
static int n153_locks,n153_unlocks,n153_alloc_attempts,n153_allocated,n153_registered,n153_fail_at,n153_gets,n153_logs;
static int n153_old_token,n153_new_token;
static int n153_handler_a(struct iommu_domain *domain,struct device *dev,unsigned long address,int flags,void *token)
{ (void)domain;(void)dev;(void)address;(void)flags;(void)token;CHECK(0);return 0; }
static int n153_handler_b(struct iommu_domain *domain,struct device *dev,unsigned long address,int flags,void *token)
{ (void)domain;(void)dev;(void)address;(void)flags;(void)token;CHECK(0);return 0; }
static int sysmmu_fault_notifier(struct notifier_block *nb,unsigned long address,void *data)
{ (void)nb;(void)address;(void)data;CHECK(0);return 0; }
/* Deterministic writer-lock/allocation model; no real IRQ/SMP/RCU execution. */
static unsigned long n153_lock(bool *lock)
{ CHECK(lock==&n153_owner.lock&&!*lock);*lock=true;++n153_locks;return 0x153UL; }
static void n153_unlock(bool *lock,unsigned long flags)
{ CHECK(lock==&n153_owner.lock&&*lock&&flags==0x153UL);*lock=false;++n153_unlocks; }
#define spin_lock_irqsave(lock,flags) do { (flags)=n153_lock(lock); } while(0)
#define spin_unlock_irqrestore(lock,flags) n153_unlock(lock,flags)
static void *kzalloc(size_t bytes,int flags)
{
 CHECK(n153_owner.lock&&bytes==sizeof(struct owner_fault_info)&&flags==GFP_ATOMIC);++n153_alloc_attempts;
 if(n153_fail_at==n153_alloc_attempts)return NULL;
 CHECK(n153_allocated<2);memset(&n153_pool[n153_allocated],0,sizeof(n153_pool[0]));return &n153_pool[n153_allocated++];
}
static struct sysmmu_drvdata *dev_get_drvdata(struct device *dev)
{
 CHECK(n153_owner.lock&&(dev==&n153_sysmmu[0]||dev==&n153_sysmmu[1]));++n153_gets;return dev->driver_data;
}
static const char *dev_name(struct device *dev)
{ CHECK(dev==&n153_master||dev==&n153_sysmmu[0]||dev==&n153_sysmmu[1]);return "fixture"; }
static void dev_info(struct device *dev,const char *format,...)
{ CHECK(dev==&n153_master);(void)format;++n153_logs; }
static int atomic_notifier_chain_register(struct atomic_notifier_head *head,struct notifier_block *nb)
{
 unsigned int index;
 CHECK(n153_owner.lock&&(head==&n153_drv[0].fault_notifiers||head==&n153_drv[1].fault_notifiers));
 index=head==&n153_drv[0].fault_notifiers?0U:1U;
 CHECK(!n153_entries[index].fault_notifier_registered&&!head->record&&!head->count);
 CHECK(nb->notifier_call==sysmmu_fault_notifier&&container_of(nb,struct owner_fault_info,nb)->master==&n153_master);
 head->record=nb;++head->count;++n153_registered;return 0;
}
'''

MAIN = r'''
static void n153_reset(void)
{
 unsigned int i;struct list_head *head=&n153_owner.sysmmu_list;
 memset(&n153_owner,0,sizeof(n153_owner));memset(&n153_master,0,sizeof(n153_master));
 memset(n153_entries,0,sizeof(n153_entries));memset(n153_sysmmu,0,sizeof(n153_sysmmu));memset(n153_drv,0,sizeof(n153_drv));
 n153_master.archdata.iommu=&n153_owner;head->next=&n153_entries[0].node;head->prev=&n153_entries[1].node;
 for(i=0;i<2;++i){
  CHECK(!n153_entries[i].fault_notifier_registered);n153_entries[i].sysmmu=&n153_sysmmu[i];n153_sysmmu[i].driver_data=&n153_drv[i];
  n153_entries[i].node.prev=i?&n153_entries[0].node:head;n153_entries[i].node.next=i?head:&n153_entries[1].node;
 }
 n153_locks=n153_unlocks=n153_alloc_attempts=n153_allocated=n153_registered=n153_fail_at=n153_gets=n153_logs=0;
}
static void n153_balanced(int locks,int attempts,int registered)
{
 CHECK(!n153_owner.lock&&n153_locks==locks&&n153_unlocks==locks);
 CHECK(n153_alloc_attempts==attempts&&n153_registered==registered&&n153_allocated==registered&&n153_gets==registered);
}
int main(void)
{
 struct notifier_block *first,*second;unsigned long flags;
 n153_reset();
 CHECK(exynos_iommu_add_fault_handler(&n153_master,n153_handler_a,&n153_old_token)==0);n153_balanced(1,2,2);
 CHECK(n153_entries[0].fault_notifier_registered&&n153_entries[1].fault_notifier_registered);
 CHECK(n153_drv[0].fault_notifiers.count==1&&n153_drv[1].fault_notifiers.count==1&&n153_logs==2);
 CHECK(n153_owner.fault_handler==n153_handler_a&&n153_owner.token==&n153_old_token);
 first=n153_drv[0].fault_notifiers.record;second=n153_drv[1].fault_notifiers.record;CHECK(first!=second);
 CHECK(exynos_iommu_add_fault_handler(&n153_master,n153_handler_b,&n153_new_token)==0);n153_balanced(2,2,2);
 CHECK(n153_owner.fault_handler==n153_handler_b&&n153_owner.token==&n153_new_token&&n153_logs==2);
 CHECK(n153_drv[0].fault_notifiers.record==first&&n153_drv[1].fault_notifiers.record==second);
 /* Model clear's NULL publication only; do not execute/retest the old clear/drain. */
 spin_lock_irqsave(&n153_owner.lock,flags);n153_owner.fault_handler=NULL;n153_owner.token=NULL;spin_unlock_irqrestore(&n153_owner.lock,flags);
 CHECK(n153_entries[0].fault_notifier_registered&&n153_entries[1].fault_notifier_registered);
 CHECK(exynos_iommu_add_fault_handler(&n153_master,n153_handler_a,&n153_old_token)==0);n153_balanced(4,2,2);
 CHECK(n153_owner.fault_handler==n153_handler_a&&n153_owner.token==&n153_old_token&&n153_logs==2);
 CHECK(n153_drv[0].fault_notifiers.record==first&&n153_drv[1].fault_notifiers.record==second);
 n153_reset();n153_fail_at=2;
 CHECK(exynos_iommu_add_fault_handler(&n153_master,n153_handler_a,&n153_old_token)==-ENOMEM);n153_balanced(1,2,1);
 CHECK(n153_entries[0].fault_notifier_registered&&!n153_entries[1].fault_notifier_registered);
 CHECK(n153_drv[0].fault_notifiers.count==1&&!n153_drv[1].fault_notifiers.count&&n153_logs==1);
 CHECK(n153_owner.fault_handler==n153_handler_a&&n153_owner.token==&n153_old_token);first=n153_drv[0].fault_notifiers.record;
 n153_fail_at=0;
 CHECK(exynos_iommu_add_fault_handler(&n153_master,n153_handler_b,&n153_new_token)==0);n153_balanced(2,3,2);
 CHECK(n153_entries[0].fault_notifier_registered&&n153_entries[1].fault_notifier_registered);
 CHECK(n153_drv[0].fault_notifiers.record==first&&n153_drv[0].fault_notifiers.count==1&&n153_drv[1].fault_notifiers.count==1);
 CHECK(n153_owner.fault_handler==n153_handler_b&&n153_owner.token==&n153_new_token&&n153_logs==2);
 n153_reset();n153_master.archdata.iommu=NULL;n153_owner.fault_handler=n153_handler_a;n153_owner.token=&n153_old_token;
 CHECK(exynos_iommu_add_fault_handler(&n153_master,n153_handler_b,&n153_new_token)==-ENODEV);n153_balanced(0,0,0);
 CHECK(n153_owner.fault_handler==n153_handler_a&&n153_owner.token==&n153_old_token&&n153_logs==1);
 CHECK(!n153_entries[0].fault_notifier_registered&&!n153_entries[1].fault_notifier_registered);
 printf("NEW native fault registration once PASS; assertions=%d\n",n153_assertions);return 0;
}
'''


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--cc', required=True, type=Path)
    args = parser.parse_args()
    out = args.output.absolute()
    if (not args.output.is_absolute() or out != BASE / 'new-native-registration-once' or out.resolve() != out or
            out.exists() or out.is_symlink() or not out.parent.is_dir()):
        raise ValueError('fresh canonical once153 output required')
    if (INPUT.resolve() != INPUT or INPUT.is_symlink() or not INPUT.is_file() or
            not 0 < INPUT.stat().st_size <= 2 * 1024 * 1024):
        raise ValueError('exact ordinary composed152 IOMMU input required')
    if not args.cc.is_absolute() or args.cc.is_symlink() or not args.cc.is_file():
        raise ValueError('absolute ordinary compiler required')
    native = INPUT.read_bytes()
    out.mkdir()
    source = out / 'native_fault_registration_fixture.c'
    executable = out / 'native_fault_registration_fixture.exe'
    compile_argv = [str(args.cc.resolve()), '-std=gnu89', '-Wall', '-Wextra', '-Werror',
                    '-Wdeclaration-after-statement', str(source), '-o', str(executable)]
    fixture_argv = [str(executable)]
    result = dict(schema='v153-native-fault-registration-once-v1', **{'pass': False},
                  primary_transform_count=0, negative_transform_count=0, compiler_count=0, fixture_count=0,
                  old_tests_count=0, compiler_launch_attempts=0, fixture_launch_attempts=0,
                  argv=[sys.executable, *sys.argv], compiler_argv=compile_argv, fixture_argv=fixture_argv,
                  input_iommu152_sha256=IOMMU_SHA256, outputs={},
                  authentic_native_body='exynos_iommu_add_fault_handler', authentic_private_struct='sysmmu_list_data',
                  real_IRQ_SMP_RCU_execution_claim=False, hardware_DMA_terminal_claim=False, physical_owner_success=False)

    def persist():
        (out / 'result.json').write_bytes((json.dumps(result, indent=2) + '\n').encode())

    persist()
    try:
        result['primary_transform_count'] = 1
        persist()
        outputs = patch_native(native)
        changed = outputs[IOMMU]
        result['outputs'] = {IOMMU: hashlib.sha256(changed).hexdigest()}
        restored = changed
        for old, new in reversed(EDITS):
            if restored.count(new) != 1:
                raise AssertionError('unique focused native output delta required')
            restored = restored.replace(new, old, 1)
        if restored != native:
            raise AssertionError('unrelated native snapshot/clear/constructor bytes changed')
        constructor_signature = b'static int exynos_iommu_of_xlate('
        constructor = body(changed, constructor_signature)
        allocation = b'list_data = devm_kzalloc(sysmmu, sizeof(*list_data), GFP_KERNEL);'
        if (changed.count(allocation) != 1 or changed.count(b'sizeof(*list_data)') != 1 or
                constructor.count(allocation) != 1 or b'fault_notifier_registered' in constructor or
                constructor != body(native, constructor_signature)):
            raise AssertionError('sole zeroed private-entry constructor must remain unchanged')
        result['negative_transform_count'] = 1
        persist()
        try:
            patch_native(native + b'\n')
        except ValueError:
            pass
        else:
            raise AssertionError('altered native input must be refused')
        signature = b'struct sysmmu_list_data {'
        if changed.count(signature) != 1:
            raise AssertionError('one authentic private entry struct required')
        start = changed.index(signature)
        private_struct = changed[start:changed.index(b'};', start) + 2]
        if private_struct != NEW_STRUCT:
            raise AssertionError('exact private registration flag required')
        registrar = body(changed, b'int exynos_iommu_add_fault_handler(')
        fixture = PRELUDE.encode() + b'\n' + private_struct + b'\n' + LEAVES.encode() + b'\n' + registrar + b'\n' + MAIN.encode()
        target = out / 'native-output' / IOMMU
        target.parent.mkdir(parents=True)
        target.write_bytes(changed)
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
        raise RuntimeError('NEW153 native registration batch failed; no automatic retry')


if __name__ == '__main__':
    main()
