"""One NEW authentic fault-token drain batch; execution belongs to ROOT."""
from pathlib import Path
import argparse
import hashlib
import json
import subprocess
import sys

sys.dont_write_bytecode = True
from v145_iva_sidecar import TOKENS
from v152_iva_fault_drain import (IOMMU, LOCAL_HEADER, IOVMM, PUBLIC_HEADER, CTRL,
                                 NATIVE_SHA256, EDITS, NEW_NOTIFIER, CLEAR, WRAPPER,
                                 LOCAL_DECL, PUBLIC_DECL, DISABLED, patch_native)

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'note10/private/device-test/v152-iva-fault-token-drain-20261109'
PROVIDER = ROOT / 'note10/private/device-test/v151-iva-diagnostic-mmap-deny-20261109/provider-discovery/sources'
INPUTS = {name: PROVIDER / name for name in NATIVE_SHA256}
INPUTS[CTRL] = ROOT / 'note10/private/device-test/v151-iva-diagnostic-mmap-deny-20261109/new-native-mmap-deny-once/native-output' / CTRL


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
struct device { struct { void *iommu; } archdata; };
struct iommu_domain { int tag; };
typedef int (*iommu_fault_handler_t)(struct iommu_domain *,struct device *,unsigned long,int,void *);
struct notifier_block { int tag; };
struct owner_fault_info { struct device *master;struct notifier_block nb; };
struct exynos_iommu_owner {
 bool lock;struct iommu_domain *domain;struct device *master;
 iommu_fault_handler_t fault_handler;void *token;
};
#define container_of(ptr,type,member) ((type *)((char *)(ptr)-offsetof(type,member)))
#define has_sysmmu(dev) ((dev)->archdata.iommu != NULL)
static struct exynos_iommu_owner n152_owner;
static struct device n152_master;
static struct iommu_domain n152_domain;
static int n152_assertions,n152_locks,n152_unlocks,n152_syncs,n152_old_calls,n152_new_calls,n152_wrapper_calls;
static int n152_old_token,n152_new_token,n152_fault=7,n152_pending_readers;
static bool n152_replace_on_unlock,n152_clearing;
static iommu_fault_handler_t n152_pending_handler;
static void *n152_pending_token;
#define CHECK(c) do { ++n152_assertions;if(!(c)){fprintf(stderr,"line %d: %s\n",__LINE__,#c);exit(1);} } while(0)
static int n152_old_handler(struct iommu_domain *domain,struct device *master,unsigned long address,int flags,void *token)
{
 CHECK(!n152_owner.lock&&domain==&n152_domain&&master==&n152_master);
 CHECK(address==0x1234UL&&flags==7&&token==&n152_old_token);++n152_old_calls;return -17;
}
static int n152_new_handler(struct iommu_domain *domain,struct device *master,unsigned long address,int flags,void *token)
{
 CHECK(!n152_owner.lock&&domain==&n152_domain&&master==&n152_master);
 CHECK(address==0x1234UL&&flags==7&&token==&n152_new_token);++n152_new_calls;return 19;
}
/* Deterministic ownership/reader model only; no real RCU, IRQ or SMP execution. */
static unsigned long n152_lock(bool *lock)
{ CHECK(lock==&n152_owner.lock&&!*lock);*lock=true;++n152_locks;return 0x152UL; }
static void n152_unlock(bool *lock,unsigned long flags)
{
 CHECK(lock==&n152_owner.lock&&*lock&&flags==0x152UL);*lock=false;++n152_unlocks;
 if(n152_clearing)CHECK(!n152_owner.fault_handler&&!n152_owner.token);
 if(n152_replace_on_unlock){
  n152_replace_on_unlock=false;n152_owner.fault_handler=n152_new_handler;n152_owner.token=&n152_new_token;
 }
}
#define spin_lock_irqsave(lock,flags) do { (flags)=n152_lock(lock); } while(0)
#define spin_unlock_irqrestore(lock,flags) n152_unlock(lock,flags)
static void synchronize_rcu(void)
{
 CHECK(n152_clearing&&!n152_owner.lock&&!n152_owner.fault_handler&&!n152_owner.token);++n152_syncs;
 if(n152_pending_handler){
  CHECK(n152_pending_readers==1);
  n152_pending_handler(&n152_domain,&n152_master,0x1234UL,n152_fault,n152_pending_token);
  n152_pending_handler=NULL;n152_pending_token=NULL;n152_pending_readers=0;
 }
 CHECK(!n152_pending_readers);n152_clearing=false;
}
'''

BRIDGE = r'''
void exynos_iommu_clear_fault_handler(struct device *master)
{ ++n152_wrapper_calls;n152_actual_clear(master); }
'''

MAIN = r'''
static void n152_reset(struct owner_fault_info *info)
{
 memset(&n152_owner,0,sizeof(n152_owner));memset(&n152_master,0,sizeof(n152_master));
 n152_master.archdata.iommu=&n152_owner;n152_owner.master=&n152_master;n152_owner.domain=&n152_domain;
 n152_owner.fault_handler=n152_old_handler;n152_owner.token=&n152_old_token;info->master=&n152_master;
 n152_locks=n152_unlocks=n152_syncs=n152_old_calls=n152_new_calls=n152_wrapper_calls=0;
 n152_replace_on_unlock=n152_clearing=false;n152_pending_readers=0;n152_pending_handler=NULL;n152_pending_token=NULL;
}
static void n152_balanced(int locks,int syncs)
{ CHECK(!n152_owner.lock&&n152_locks==locks&&n152_unlocks==locks&&n152_syncs==syncs); }
int main(void)
{
 struct owner_fault_info info;
 n152_reset(&info);
 CHECK(sysmmu_fault_notifier(&info.nb,0x1234UL,&n152_fault)==0);n152_balanced(1,0);
 CHECK(n152_old_calls==1&&!n152_new_calls);
 n152_reset(&info);n152_replace_on_unlock=true;
 CHECK(sysmmu_fault_notifier(&info.nb,0x1234UL,&n152_fault)==0);n152_balanced(1,0);
 CHECK(n152_old_calls==1&&!n152_new_calls&&n152_owner.fault_handler==n152_new_handler&&n152_owner.token==&n152_new_token);
 CHECK(sysmmu_fault_notifier(&info.nb,0x1234UL,&n152_fault)==0);n152_balanced(2,0);
 CHECK(n152_old_calls==1&&n152_new_calls==1);
 n152_reset(&info);n152_owner.fault_handler=NULL;
 CHECK(sysmmu_fault_notifier(&info.nb,0x1234UL,NULL)==0);n152_balanced(1,0);
 CHECK(!n152_old_calls&&!n152_new_calls&&n152_owner.token==&n152_old_token);
 n152_reset(&info);n152_master.archdata.iommu=NULL;
 CHECK(sysmmu_fault_notifier(&info.nb,0x1234UL,NULL)==0);n152_actual_clear(&n152_master);n152_balanced(0,0);
 CHECK(!n152_old_calls&&!n152_new_calls&&n152_owner.fault_handler==n152_old_handler&&n152_owner.token==&n152_old_token);
 n152_reset(&info);n152_clearing=true;n152_actual_clear(&n152_master);n152_balanced(1,1);
 CHECK(!n152_owner.fault_handler&&!n152_owner.token&&!n152_old_calls&&!n152_clearing);
 CHECK(sysmmu_fault_notifier(&info.nb,0x1234UL,NULL)==0);n152_balanced(2,1);
 CHECK(!n152_old_calls&&!n152_new_calls);
 n152_reset(&info);
 /* Model an old reader that already cached a coherent pair before NULL publication. */
 n152_pending_handler=n152_owner.fault_handler;n152_pending_token=n152_owner.token;n152_pending_readers=1;
 n152_clearing=true;iovmm_clear_fault_handler(&n152_master);n152_balanced(1,1);
 CHECK(n152_wrapper_calls==1&&n152_old_calls==1&&!n152_pending_readers&&!n152_pending_handler);
 CHECK(!n152_owner.fault_handler&&!n152_owner.token);
 CHECK(sysmmu_fault_notifier(&info.nb,0x1234UL,NULL)==0);n152_balanced(2,1);
 CHECK(n152_old_calls==1&&!n152_new_calls);
 n152_disabled_stub();n152_balanced(2,1);CHECK(n152_wrapper_calls==1);
 printf("NEW native fault-token drain PASS; assertions=%d\n",n152_assertions);return 0;
}
'''


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--cc', required=True, type=Path)
    args = parser.parse_args()
    out = args.output.absolute()
    if (not args.output.is_absolute() or out != BASE / 'new-native-fault-token-once' or out.resolve() != out or
            out.exists() or out.is_symlink() or not out.parent.is_dir()):
        raise ValueError('fresh canonical once152 output required')
    for path in INPUTS.values():
        if (path.resolve() != path or path.is_symlink() or not path.is_file() or
                not 0 < path.stat().st_size <= 2 * 1024 * 1024):
            raise ValueError('exact ordinary pinned native input required')
    if not args.cc.is_absolute() or args.cc.is_symlink() or not args.cc.is_file():
        raise ValueError('absolute ordinary compiler required')
    native = {name: path.read_bytes() for name, path in INPUTS.items()}
    out.mkdir()
    source = out / 'native_fault_token_fixture.c'
    executable = out / 'native_fault_token_fixture.exe'
    compile_argv = [str(args.cc.resolve()), '-std=gnu89', '-Wall', '-Wextra', '-Werror',
                    '-Wdeclaration-after-statement', str(source), '-o', str(executable)]
    fixture_argv = [str(executable)]
    result = dict(schema='v152-native-fault-token-drain-once-v1', **{'pass': False},
                  primary_transform_count=0, negative_transform_count=0, compiler_count=0, fixture_count=0,
                  old_tests_count=0, compiler_launch_attempts=0, fixture_launch_attempts=0,
                  argv=[sys.executable, *sys.argv], compiler_argv=compile_argv, fixture_argv=fixture_argv,
                  input_native_sha256=NATIVE_SHA256, outputs={},
                  authentic_native_bodies=['sysmmu_fault_notifier', 'exynos_iommu_clear_fault_handler', 'iovmm_clear_fault_handler'],
                  real_RCU_IRQ_SMP_execution_claim=False, hardware_DMA_terminal_claim=False, physical_owner_success=False)

    def persist():
        (out / 'result.json').write_bytes((json.dumps(result, indent=2) + '\n').encode())

    persist()
    try:
        result['primary_transform_count'] = 1
        persist()
        outputs = patch_native(native)
        result['outputs'] = {name: hashlib.sha256(raw).hexdigest() for name, raw in outputs.items()}
        for name, raw in outputs.items():
            restored = raw[:-len(b'\n' + WRAPPER + b'\n')] if name == IOVMM else raw
            for old, new in reversed(EDITS.get(name, ())):
                if restored.count(new) != 1:
                    raise AssertionError('unique focused output delta required')
                restored = restored.replace(new, old, 1)
            if restored != native[name]:
                raise AssertionError('unrelated native bytes changed')
        set_signature = b'int exynos_iommu_add_fault_handler('
        if body(outputs[IOMMU], set_signature) != body(native[IOMMU], set_signature):
            raise AssertionError('existing registration body changed')
        for name, declaration in ((LOCAL_HEADER, LOCAL_DECL), (PUBLIC_HEADER, PUBLIC_DECL), (PUBLIC_HEADER, DISABLED)):
            if outputs[name].count(declaration) != 1:
                raise AssertionError('exact header declaration/stub required')
        if (outputs[CTRL].count(b'iovmm_clear_fault_handler(dev);') != 2 or
                b'err_iovmm:\n\tiovmm_clear_fault_handler(dev);\n\tpm_runtime_disable(dev);' not in outputs[CTRL] or
                b'#ifdef CONFIG_EXYNOS_IOVMM\n\tiovmm_clear_fault_handler(dev);\n\tiovmm_deactivate(dev);' not in outputs[CTRL]):
            raise AssertionError('exact IVA clear-before-teardown placements required')
        result['negative_transform_count'] = 1
        persist()
        altered = dict(native)
        altered[IOMMU] += b'\n'
        try:
            patch_native(altered)
        except ValueError:
            pass
        else:
            raise AssertionError('altered native input must be refused')
        notifier = body(outputs[IOMMU], b'static int sysmmu_fault_notifier(')
        clear = body(outputs[IOMMU], b'void exynos_iommu_clear_fault_handler(')
        wrapper = body(outputs[IOVMM], b'void iovmm_clear_fault_handler(')
        if notifier != NEW_NOTIFIER or clear != CLEAR[CLEAR.index(b'void exynos_iommu_clear_fault_handler('):] or wrapper != WRAPPER:
            raise AssertionError('exact authentic selected bodies required')
        fixture = PRELUDE.encode() + b'\n' + LOCAL_DECL + PUBLIC_DECL + notifier
        fixture += b'\n#define exynos_iommu_clear_fault_handler n152_actual_clear\n' + clear
        fixture += b'\n#undef exynos_iommu_clear_fault_handler\n' + BRIDGE.encode() + wrapper
        fixture += b'\n' + DISABLED + b'static void n152_disabled_stub(void)\n{\n iovmm_clear_fault_handler((struct device *)1);\n}\n#undef iovmm_clear_fault_handler\n'
        fixture += MAIN.encode()
        for name, raw in outputs.items():
            target = out / 'native-output' / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(raw)
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
        raise RuntimeError('NEW152 native fault-token batch failed; no automatic retry')


if __name__ == '__main__':
    main()
