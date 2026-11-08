"""One NEW authentic mailbox registrar batch; execution belongs to ROOT."""
from pathlib import Path
import argparse
import hashlib
import json
import re
import subprocess
import sys

sys.dont_write_bytecode = True
from v150_iva_mbox_register import MBOX, MBOX_SHA256, patch_native
ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'note10/private/device-test/v150-iva-mailbox-register-unlock-20261108'
INPUT = ROOT / 'note10/private/device-test/v142-iva-terminal-20261107/source-evidence' / MBOX
TOKENS = re.compile(rb'/\*.*?\*/|//[^\n]*|"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'|[{}]', re.S)


def native_register(raw):
    matches = list(re.finditer(rb'^int iva_mbox_callback_register\(uint8_t msg_hd, struct iva_mbox_cb_block \*cb\)', raw, re.M))
    if len(matches) != 1:
        raise ValueError('exact authentic native mailbox registrar required')
    start = matches[0].start()
    depth = 0
    for token in TOKENS.finditer(raw, raw.index(b'{', matches[0].end())):
        if token.group() == b'{':
            depth += 1
        elif token.group() == b'}':
            depth -= 1
            if not depth:
                return raw[start:token.end()]
    raise ValueError('unbalanced native registrar body')


PRELUDE = r'''
#include <stdint.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>
struct iva_mbox_cb_block {
 bool (*callback)(struct iva_mbox_cb_block *,uint32_t);
 struct iva_mbox_cb_block *next;uint32_t msg_hd;void *priv_data;int priority;
};
typedef struct { bool held; } spinlock_t;
struct iva_mbox_cb_head { spinlock_t lock;struct iva_mbox_cb_block *head; };
static struct iva_mbox_cb_head iva_mbox_chain;
static int n150_assertions,n150_lock_calls,n150_unlock_calls,n150_publish_calls,n150_callback_calls;
static unsigned long n150_irq_flags;
static char n150_order[64];static unsigned int n150_order_nr;
#define CHECK(c) do { ++n150_assertions;if(!(c)){fprintf(stderr,"line %d: %s\n",__LINE__,#c);exit(1);} } while(0)
static void n150_event(char c) { CHECK(n150_order_nr<63);n150_order[n150_order_nr++]=c;n150_order[n150_order_nr]=0; }
/* Synthetic ownership/flags model; no real IRQ, SMP or RCU execution. */
static unsigned long n150_lock_save(spinlock_t *lock)
{
 unsigned long saved=n150_irq_flags;
 CHECK(lock==&iva_mbox_chain.lock&&!lock->held);lock->held=true;n150_irq_flags&=~1UL;
 ++n150_lock_calls;n150_event('L');return saved;
}
static void n150_unlock_restore(spinlock_t *lock,unsigned long saved)
{
 CHECK(lock==&iva_mbox_chain.lock&&lock->held&&!(n150_irq_flags&1UL));
 lock->held=false;n150_irq_flags=saved;++n150_unlock_calls;n150_event('U');
}
#define spin_lock_irqsave(lock,flags) do { (flags)=n150_lock_save(lock); } while(0)
#define spin_unlock_irqrestore(lock,flags) n150_unlock_restore(lock,flags)
#define rcu_assign_pointer(dst,src) do { CHECK(iva_mbox_chain.lock.held&&!(n150_irq_flags&1UL));(dst)=(src);++n150_publish_calls;n150_event('P'); } while(0)
static bool n150_callback(struct iva_mbox_cb_block *cb,uint32_t msg)
{ (void)cb;(void)msg;++n150_callback_calls;CHECK(0);return false; }
'''

MAIN = r'''
static void n150_reset(unsigned long flags)
{
 memset(&iva_mbox_chain,0,sizeof(iva_mbox_chain));n150_irq_flags=flags;
 n150_lock_calls=n150_unlock_calls=n150_publish_calls=n150_callback_calls=0;
 n150_order_nr=0;n150_order[0]=0;
}
static void n150_init_cb(struct iva_mbox_cb_block *cb,int priority)
{
 memset(cb,0,sizeof(*cb));cb->callback=n150_callback;cb->priority=priority;
 cb->msg_hd=0xabcdef00U;cb->priv_data=cb;
}
static void n150_balanced(unsigned long flags,int locks,int publications)
{
 CHECK(!iva_mbox_chain.lock.held&&n150_irq_flags==flags);
 CHECK(n150_lock_calls==locks&&n150_unlock_calls==locks&&n150_publish_calls==publications&&!n150_callback_calls);
}
int main(void)
{
 struct iva_mbox_cb_block a,b,c,d,e,invalid,old_a,old_b,old_c,old_d,old_invalid;
 unsigned int mode;unsigned long flags;
 for(mode=0;mode<2;++mode){
  flags=0xa0UL|mode;n150_reset(flags);
  n150_init_cb(&invalid,4);invalid.callback=NULL;invalid.next=&invalid;
  memcpy(&old_invalid,&invalid,sizeof(invalid));
  CHECK(iva_mbox_callback_register(0x88,NULL)==-EINVAL);n150_balanced(flags,0,0);
  CHECK(iva_mbox_callback_register(0x99,&invalid)==-EINVAL);n150_balanced(flags,0,0);
  CHECK(!iva_mbox_chain.head&&memcmp(&invalid,&old_invalid,sizeof(invalid))==0&&!n150_order_nr);
  n150_init_cb(&a,10);n150_init_cb(&b,30);n150_init_cb(&c,20);n150_init_cb(&d,20);n150_init_cb(&e,25);
  CHECK(iva_mbox_callback_register(0x11,&a)==0);n150_balanced(flags,1,1);
  CHECK(iva_mbox_chain.head==&a&&!a.next&&a.msg_hd==0x11&&a.priv_data==&a);
  CHECK(iva_mbox_callback_register(0x22,&b)==0);n150_balanced(flags,2,2);
  CHECK(iva_mbox_chain.head==&b&&b.next==&a&&b.msg_hd==0x22);
  CHECK(iva_mbox_callback_register(0x33,&c)==0);n150_balanced(flags,3,3);
  CHECK(b.next==&c&&c.next==&a&&c.msg_hd==0x33);
  CHECK(iva_mbox_callback_register(0x44,&d)==0);n150_balanced(flags,4,4);
  CHECK(b.next==&c&&c.next==&d&&d.next==&a&&!a.next&&d.msg_hd==0x44);
  CHECK(strcmp(n150_order,"LPULPULPULPU")==0);
  memcpy(&old_a,&a,sizeof(a));memcpy(&old_b,&b,sizeof(b));memcpy(&old_c,&c,sizeof(c));memcpy(&old_d,&d,sizeof(d));
  CHECK(iva_mbox_callback_register(0xee,&b)==0);n150_balanced(flags,5,4);
  CHECK(iva_mbox_chain.head==&b&&memcmp(&a,&old_a,sizeof(a))==0&&memcmp(&b,&old_b,sizeof(b))==0&&memcmp(&c,&old_c,sizeof(c))==0&&memcmp(&d,&old_d,sizeof(d))==0);
  CHECK(iva_mbox_callback_register(0xff,&a)==0);n150_balanced(flags,6,4);
  CHECK(iva_mbox_chain.head==&b&&memcmp(&a,&old_a,sizeof(a))==0&&memcmp(&b,&old_b,sizeof(b))==0&&memcmp(&c,&old_c,sizeof(c))==0&&memcmp(&d,&old_d,sizeof(d))==0);
  CHECK(strcmp(n150_order,"LPULPULPULPULULU")==0);
  CHECK(iva_mbox_callback_register(0x55,&e)==0);n150_balanced(flags,7,5);
  CHECK(iva_mbox_chain.head==&b&&b.next==&e&&e.next==&c&&c.next==&d&&d.next==&a&&!a.next);
  CHECK(a.msg_hd==0x11&&b.msg_hd==0x22&&c.msg_hd==0x33&&d.msg_hd==0x44&&e.msg_hd==0x55);
  CHECK(a.priv_data==&a&&b.priv_data==&b&&c.priv_data==&c&&d.priv_data==&d&&e.priv_data==&e);
  CHECK(strcmp(n150_order,"LPULPULPULPULULULPU")==0);
 }
 printf("NEW mailbox registrar unlock PASS; assertions=%d\n",n150_assertions);return 0;
}
'''


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--mbox', required=True, type=Path)
    parser.add_argument('--cc', required=True, type=Path)
    args = parser.parse_args()
    out = args.output.absolute()
    if (not args.output.is_absolute() or out != BASE / 'new-native-mailbox-register-once' or out.resolve() != out or
            out.exists() or out.is_symlink() or not out.parent.is_dir()):
        raise ValueError('fresh canonical once150 output required')
    if (not args.mbox.is_absolute() or args.mbox != INPUT or args.mbox.resolve() != INPUT or
            args.mbox.is_symlink() or not args.mbox.is_file() or not 0 < args.mbox.stat().st_size <= 2 * 1024 * 1024):
        raise ValueError('exact ordinary pinned mailbox input required')
    if not args.cc.is_absolute() or args.cc.is_symlink() or not args.cc.is_file():
        raise ValueError('absolute ordinary compiler required')
    mbox = args.mbox.read_bytes()
    out.mkdir()
    source = out / 'native_mailbox_register_fixture.c'
    executable = out / 'native_mailbox_register_fixture.exe'
    compile_argv = [str(args.cc.resolve()), '-std=gnu89', '-Wall', '-Wextra', '-Werror',
                    '-Wno-unused-function', '-Wdeclaration-after-statement', str(source), '-o', str(executable)]
    fixture_argv = [str(executable)]
    result = dict(schema='v150-native-mailbox-register-unlock-once-v1', **{'pass': False},
                  primary_transform_count=0, negative_transform_count=0, compiler_count=0, fixture_count=0,
                  old_tests_count=0, compiler_launch_attempts=0, fixture_launch_attempts=0,
                  argv=[sys.executable, *sys.argv], compiler_argv=compile_argv, fixture_argv=fixture_argv,
                  input_mbox_sha256=MBOX_SHA256, outputs={}, authentic_native_body='iva_mbox_callback_register',
                  host_ABI_bridge='None; exact selected callback block fields and scalar API types.',
                  IRQ_SMP_RCU_execution_claim=False, physical_owner_success=False)

    def persist():
        (out / 'result.json').write_bytes((json.dumps(result, indent=2) + '\n').encode())

    persist()
    try:
        result['primary_transform_count'] = 1
        persist()
        outputs = patch_native(mbox)
        result['outputs'] = {MBOX: hashlib.sha256(outputs[MBOX]).hexdigest()}
        result['negative_transform_count'] = 1
        persist()
        try:
            patch_native(mbox + b'\n')
        except ValueError:
            pass
        else:
            raise AssertionError('exact NEW input refusal failed')
        fixture = PRELUDE.encode() + b'\n' + native_register(outputs[MBOX]) + b'\n' + MAIN.encode()
        target = out / 'native-output' / MBOX
        target.parent.mkdir(parents=True)
        target.write_bytes(outputs[MBOX])
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
        raise RuntimeError('NEW150 mailbox registrar batch failed; no automatic retry')


if __name__ == '__main__':
    main()
