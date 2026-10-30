"""Focused native dispatch/notify proof; no hardware or historical model replay."""
import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path
from prepare_cpu_pm_roundtrip import function, COUNTS_STATE
from prepare_cpu_pm_notifier_trace import (BASE, PREPARED, TARGETS, SOURCES, STRUCT,
                                         OBSERVER, FRAME_FORMAT, transform)
from decode_cpu_pm_notifier_trace import SCHEMA, decode
from decode_cpu_pm_roundtrip import SCHEMA as CPR_SCHEMA, SUCCESS, COUNTS_SCHEMA, TERMINAL_SCHEMA
from decode_reservation import checksum

HERE = Path(__file__).resolve().parent
NATIVE_CASES = ('ordinary-unarmed', 'exact-head-filter', 'exact-event-filter',
                'ordered-six-enter-exit', 'stop-partial', 'matching-recursion-conflict',
                'unrelated-nested-chain', 'foreign-cpu-isolation', 'callback-field-mutation',
                'unknown-block', 'wrong-order', 'duplicate-slot', 'return-field-mutation',
                'partial-return', 'repeated-phase', 'cleanup-admission',
                'enter-failure-prefix', 'ordinary-exit-null', 'rcu-and-counts', 'bounded-overflow',
                'exit-error-no-retry', 'foreign-cpu-all-helpers')
PARSER_CASES = ('valid', 'missing-copy', 'duplicate-copy', 'checksum', 'identity',
                'generation', 'generation-wrap', 'transaction-mismatch', 'version', 'overflow', 'partial',
                'duplicate-order', 'wrong-order', 'unknown-index', 'conflict', 'roster',
                'valid-flag-lie', 'counts-missing', 'counts-partial', 'pair-missing',
                'terminal-never-passes', 'pair-terminal-conflict', 'unknown-field', 'negative-zero')


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


PREFIX = r'''
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#define CONFIG_NOTE10_CPU_PM_NOTIFIER_TRACE 1
#define CONFIG_NOTE10_CPU_PM_NOTIFIER_COUNTS 1
#define CONFIG_NOTE10_CPU_PM_FAILURE_GUARD 1
#define notrace __attribute__((no_instrument_function))
#define noinline __attribute__((noinline))
#define __used __attribute__((used))
#define NOKPROBE_SYMBOL(x)
#define READ_ONCE(x) (x)
#define rcu_dereference_raw(x) (x)
#define NOTIFY_DONE 0
#define NOTIFY_OK 1
#define NOTIFY_STOP_MASK 0x8000
#define NOTIFY_BAD (NOTIFY_STOP_MASK|2)
static unsigned int current_cpu, rcu_in, rcu_out, debug_events;
#define raw_smp_processor_id() current_cpu
#define rcu_irq_enter_irqson() (rcu_in++)
#define rcu_irq_exit_irqson() (rcu_out++)
#define dbg_snapshot_print_notifier_call(a,b,c) (debug_events++)
#define DSS_FLAG_IN 0
#define DSS_FLAG_OUT 1
struct notifier_block {
 int (*notifier_call)(struct notifier_block *, unsigned long, void *);
 struct notifier_block *next; int priority;
};
struct atomic_notifier_head { struct notifier_block *head; };
static struct atomic_notifier_head cpu_pm_notifier_chain;
enum cpu_pm_event { CPU_PM_ENTER=1, CPU_PM_ENTER_FAILED=2, CPU_PM_EXIT=3 };
static int notifier_to_errno(int ret) { ret &= ~NOTIFY_STOP_MASK; return ret > NOTIFY_OK ? NOTIFY_OK-ret : 0; }
'''
BRIDGE = r'''
static unsigned int null_counters;
static int __atomic_notifier_call_chain(struct atomic_notifier_head *head,
 unsigned long event, void *data, int nr_to_call, int *nr_calls)
{
 if (!nr_calls) null_counters++;
 return notifier_call_chain(&head->head,event,data,nr_to_call,nr_calls);
}
'''
DRIVER = r'''
static struct notifier_block nodes[7], other;
static unsigned int mode, nested, calls, cleanup_calls, callback_exit_calls;
static int callback(struct notifier_block *, unsigned long, void *);
static int changed(struct notifier_block *nb, unsigned long event, void *v)
{ return callback(nb,event,v); }
static int callback(struct notifier_block *nb, unsigned long event, void *v)
{
 calls++;
 if (event==CPU_PM_ENTER_FAILED) cleanup_calls++;
 if (event==CPU_PM_EXIT) callback_exit_calls++;
 if (event==CPU_PM_ENTER && nb==&nodes[1] && mode==4) return NOTIFY_STOP_MASK|1;
 if (event==CPU_PM_ENTER && nb==&nodes[1] && mode==16) return NOTIFY_BAD;
 if (event==CPU_PM_EXIT && nb==&nodes[1] && mode==20) return NOTIFY_BAD;
 if (nb==&nodes[0] && !nested && mode==5) {
  int count=0; nested=1;
  notifier_call_chain(&cpu_pm_notifier_chain.head,event,v,1,&count);
  nested=0;
 }
 if (nb==&nodes[0] && !nested && mode==6) {
  struct notifier_block *head=&other; int count=0; nested=1;
  notifier_call_chain(&head,event,v,-1,&count); nested=0;
 }
 if (nb==&nodes[0] && !nested && mode==7) {
  int count=0; nested=1; current_cpu=1;
  notifier_call_chain(&cpu_pm_notifier_chain.head,event,v,1,&count);
  current_cpu=0; nested=0;
 }
 if (nb==&nodes[0] && mode==12) nb->notifier_call=changed;
 return NOTIFY_OK;
}
static void setup(unsigned int which)
{
 unsigned int i;
 current_cpu=rcu_in=rcu_out=debug_events=null_counters=0;
 mode=which; nested=calls=cleanup_calls=callback_exit_calls=0;
 n10_cpu_pm_counts_owned=n10_cpu_pm_counts_armed=n10_cpu_pm_counts_claimed=0;
 n10_cpu_pm_counts_conflict=n10_cpu_pm_counts_enter_seen=n10_cpu_pm_counts_exit_seen=0;
 n10_cpu_pm_counts_enter_nr_calls=n10_cpu_pm_counts_exit_nr_calls=0;
 memset(nodes,0,sizeof(nodes)); memset(&other,0,sizeof(other));
 for(i=0;i<7;i++) { nodes[i].notifier_call=callback; nodes[i].next=i<5?&nodes[i+1]:NULL; }
 other.notifier_call=callback; cpu_pm_notifier_chain.head=&nodes[0];
 n10_dispatch_begin(42);
 for(i=0;i<6;i++) n10_dispatch_seed(i,&nodes[i]);
}
static void arm(unsigned int phase)
{ n10_dispatch_arm(&cpu_pm_notifier_chain.head,phase?CPU_PM_EXIT:CPU_PM_ENTER,phase); }
static void chain(unsigned int phase,int limit)
{
 int count=0; unsigned int event=phase?CPU_PM_EXIT:CPU_PM_ENTER;
 arm(phase); notifier_call_chain(&cpu_pm_notifier_chain.head,event,NULL,limit,&count);
 n10_dispatch_disarm(&cpu_pm_notifier_chain.head,event);
}
static int wiped(void)
{
 unsigned int i;
 if(n10_dispatch.head || n10_dispatch.armed || n10_dispatch.sample.generation) return 0;
 for(i=0;i<6;i++) if(n10_dispatch.blocks[i] || n10_dispatch.callbacks[i]) return 0;
 return 1;
}
#define REQUIRE(x) do { if(!(x)) { fprintf(stderr,"assertion line %d\n",__LINE__); return 1; } } while(0)
static int run(unsigned int which)
{
 struct n10_cpu_pm_dispatch_sample out; unsigned int i; int count=0,ret;
 setup(which);
 if(which==0) {
  ret=notifier_call_chain(&cpu_pm_notifier_chain.head,CPU_PM_ENTER,NULL,-1,&count);
  REQUIRE(ret==NOTIFY_OK && count==6 && calls==6 && debug_events==12);
  n10_dispatch_finish(&out); REQUIRE(!out.valid && !out.entered[0]);
 } else if(which==1 || which==2) {
  struct notifier_block *head=&nodes[0]; arm(0);
  ret=notifier_call_chain(which==1?&head:&cpu_pm_notifier_chain.head,
   which==1?CPU_PM_ENTER:CPU_PM_EXIT,NULL,-1,&count);
  REQUIRE(ret==NOTIFY_OK && count==6);
  n10_dispatch_disarm(&cpu_pm_notifier_chain.head,CPU_PM_ENTER);
  n10_dispatch_finish(&out); REQUIRE(!out.valid && !out.entered[0] && !out.conflict);
 } else if(which==8 || which==9 || which==10 || which==11) {
  if(which==8) nodes[1].notifier_call=changed;
  if(which==9) { nodes[0].next=&nodes[6]; nodes[6].next=&nodes[2]; }
  if(which==10) { cpu_pm_notifier_chain.head=&nodes[1]; nodes[1].next=&nodes[0]; nodes[0].next=&nodes[2]; }
  if(which==11) { n10_dispatch.blocks[1]=&nodes[0]; }
  chain(0,-1); chain(1,-1); n10_dispatch_finish(&out); REQUIRE(!out.valid);
 } else if(which==13) {
  arm(0); n10_dispatch_observe(&cpu_pm_notifier_chain.head,CPU_PM_ENTER,&nodes[0],0);
  n10_dispatch_disarm(&cpu_pm_notifier_chain.head,CPU_PM_ENTER);
  n10_dispatch_finish(&out); REQUIRE(!out.valid && out.conflict && out.entered[0]==1 && !out.returned[0]);
 } else if(which==14) {
  chain(0,-1); chain(0,-1); chain(1,-1); n10_dispatch_finish(&out); REQUIRE(!out.valid && out.conflict);
 } else if(which==15) {
  n10_dispatch_finish(&out); REQUIRE(!out.valid && !out.phases);
 } else if(which==16 || which==17 || which==18 || which==20) {
  if(which!=17) { n10_cpu_pm_counts_owned=1; n10_cpu_pm_counts_armed=CPU_PM_ENTER; }
  if(which==17) { ret=cpu_pm_exit(); REQUIRE(!ret && null_counters==1 && callback_exit_calls==6); }
  else {
   ret=cpu_pm_enter();
   if(which==16) REQUIRE(ret==-1 && cleanup_calls==1 && !callback_exit_calls && null_counters==1 && n10_cpu_pm_counts_enter_nr_calls==2);
   else {
    REQUIRE(!ret && n10_cpu_pm_counts_enter_nr_calls==6);
    n10_cpu_pm_counts_claimed=0;n10_cpu_pm_counts_armed=CPU_PM_EXIT;
    ret=cpu_pm_exit();
    if(which==20) REQUIRE(ret==-1 && n10_cpu_pm_counts_exit_nr_calls==2 && callback_exit_calls==2 && !cleanup_calls && !null_counters);
    else REQUIRE(!ret && n10_cpu_pm_counts_exit_nr_calls==6 && !null_counters);
   }
  }
  REQUIRE(rcu_in==rcu_out && rcu_in==(which==17?1:2));
  n10_dispatch_finish(&out); REQUIRE(out.valid==(which==18));
 } else if(which==21) {
  unsigned char saved[sizeof(n10_dispatch)];
  struct n10_cpu_pm_dispatch_sample zero;
  struct notifier_block *foreign_head=&other;
  arm(0);memcpy(saved,&n10_dispatch,sizeof(n10_dispatch));
  memset(&out,0xa5,sizeof(out));memset(&zero,0,sizeof(zero));
  current_cpu=1;
  n10_dispatch_begin(99);
  n10_dispatch_seed(0,&other);
  n10_dispatch_arm(&foreign_head,CPU_PM_EXIT,1);
  n10_dispatch_observe(&cpu_pm_notifier_chain.head,CPU_PM_ENTER,&nodes[0],0);
  n10_dispatch_observe(&cpu_pm_notifier_chain.head,CPU_PM_ENTER,&nodes[0],1);
  n10_dispatch_disarm(&cpu_pm_notifier_chain.head,CPU_PM_ENTER);
  n10_dispatch_finish(&out);
  REQUIRE(!memcmp(saved,&n10_dispatch,sizeof(n10_dispatch)) && !memcmp(&out,&zero,sizeof(out)));
  current_cpu=0;
  n10_dispatch_disarm(&cpu_pm_notifier_chain.head,CPU_PM_ENTER);
  n10_dispatch_finish(&out);REQUIRE(!out.valid);
 } else if(which==19) {
  arm(0);
  for(i=0;i<7;i++) {
   n10_dispatch_observe(&cpu_pm_notifier_chain.head,CPU_PM_ENTER,&nodes[0],0);
   n10_dispatch_observe(&cpu_pm_notifier_chain.head,CPU_PM_ENTER,&nodes[0],1);
  }
  n10_dispatch_disarm(&cpu_pm_notifier_chain.head,CPU_PM_ENTER);
  n10_dispatch_finish(&out); REQUIRE(!out.valid && out.conflict && out.entered[0]==6 && out.returned[0]==6);
 } else {
  chain(0,-1); chain(1,-1); n10_dispatch_finish(&out);
  if(which==3 || which==6 || which==7) REQUIRE(out.valid && out.entry_order[0]==0x123456 && out.return_order[1]==0x123456);
  else if(which==4) REQUIRE(!out.valid && out.entered[0]==2 && out.returned[0]==2 && out.entered[1]==6);
  else REQUIRE(!out.valid && out.conflict);
 }
 REQUIRE(wiped()); return 0;
}
'''


def native_source(prepared):
    notifier = prepared['kernel/notifier.c']
    start = notifier.index(b'#ifdef CONFIG_NOTE10_CPU_PM_NOTIFIER_TRACE\n')
    end = notifier.index(b'\n#endif\n', notifier.index(b'void notrace n10_dispatch_finish', start)) + len(b'\n#endif\n')
    observer = b'\n'.join(line for line in notifier[start:end].splitlines()
                          if not line.startswith(b'#include '))
    chain = function(notifier, b'static int notifier_call_chain(')[2]
    cpu = prepared['kernel/cpu_pm.c']
    functions = b'\n'.join(function(cpu, sig)[2] for sig in
                           (b'static int cpu_pm_notify(', b'int cpu_pm_enter(void)', b'int cpu_pm_exit(void)'))
    names = ','.join(json.dumps(name) for name in NATIVE_CASES)
    main = '\nint main(void) { unsigned int i; const char *names[]={' + names + '};\n'
    main += 'for(i=0;i<sizeof(names)/sizeof(names[0]);i++) { if(run(i))return 1; printf("PASS|%s\\n",names[i]); } return 0; }\n'
    return (PREFIX.encode() + STRUCT + observer + b'\n' + chain + BRIDGE.encode() +
            COUNTS_STATE + functions + DRIVER.encode() + main.encode())


def disabled_source(prepared):
    common = native_source(prepared).split(DRIVER.encode(), 1)[0]
    common = common.replace(b'#define CONFIG_NOTE10_CPU_PM_NOTIFIER_TRACE 1\n', b'')
    return common + b'''
static unsigned int calls;
static int callback(struct notifier_block *nb, unsigned long event, void *v)
{ calls++; return NOTIFY_OK; }
int main(void) {
 struct notifier_block nodes[6]; unsigned int i;
 memset(nodes,0,sizeof(nodes));
 for(i=0;i<6;i++) { nodes[i].notifier_call=callback;nodes[i].next=i<5?&nodes[i+1]:NULL; }
 cpu_pm_notifier_chain.head=&nodes[0];
 if(cpu_pm_enter() || cpu_pm_exit() || calls!=12 || rcu_in!=2 || rcu_out!=2 || null_counters!=1)return 1;
 puts("PASS|trace-disabled-original-semantics");return 0;
}
'''


def frame(tag, row, schema):
    body = ' '.join(key + '=' + str(row[key]) for key in schema)
    return tag + ' ' + body + ' checksum=%08x\n' % checksum(body.encode('ascii'))


def evidence(generation=42, trace_changes=None, counts_changes=None, terminal=False):
    ident = 'a' * 32
    cpr = {key: 1 if key in SUCCESS else 0 for key in CPR_SCHEMA}
    cpr.update(id=ident, generation=generation, roster=6)
    counts = {key: 0 for key in COUNTS_SCHEMA}
    counts.update(id=ident, generation=generation, attempted=1, roster=6, roster_valid=1,
                  enter_calls=1, exit_calls=1, enter_nr_calls=6, exit_nr_calls=6,
                  enter_seen=1, exit_seen=1, capture_valid=1, caller_invoked=1)
    trace = dict(zip(SCHEMA, (ident, 0, generation, generation, 1, 6, 3, 0, 1, 6, 6,
                              0x123456, 0x123456, 6, 6, 0x123456, 0x123456)))
    term = {key: 0 for key in TERMINAL_SCHEMA}
    if terminal:
        term.update(id=ident, generation=generation, attempted=1, recorded=1, completed=1,
                    caller_invoked=1, stage=2, helper_error=-16, probe_error=-16)
        counts.update(enter_calls=0, exit_calls=0, enter_nr_calls=0, exit_nr_calls=0,
                      enter_seen=0, exit_seen=0, capture_valid=0, terminal_stage=2,
                      terminal_helper_error=-16, terminal_probe_error=-16)
        trace.update(valid=0, phases=0, en=0, er=0, ee=0, re=0, xn=0, xr=0, xe=0, rx=0)
    counts.update(counts_changes or {})
    trace.update(trace_changes or {})
    rows = []
    for copy in (0, 1):
        rows.append(frame('N10CPT1' if terminal else 'N10CPR1',
                          dict(term if terminal else cpr, copy=copy),
                          TERMINAL_SCHEMA if terminal else CPR_SCHEMA))
        rows.append(frame('N10CPN1', dict(counts, copy=copy), COUNTS_SCHEMA))
        rows.append(frame('N10CPD1', dict(trace, copy=copy), SCHEMA))
    return ''.join(rows)


def parser_cases():
    results = {}; vectors = {}
    for name in PARSER_CASES:
        text = evidence(); identity = 'a' * 32; generation = 42
        wanted = name in ('valid', 'generation-wrap')
        changes = {'transaction-mismatch': {'transaction': 41}, 'version': {'version': 2}, 'overflow': {'en': 7},
                   'partial': {'er': 5}, 'duplicate-order': {'ee': 0x113456},
                   'wrong-order': {'xe': 0x213456}, 'unknown-index': {'re': 0x123457},
                   'conflict': {'conflict': 1}, 'roster': {'roster': 5},
                   'valid-flag-lie': {'valid': 0}, 'negative-zero': {'valid': '-0'}}
        if name in changes: text = evidence(trace_changes=changes[name])
        elif name == 'missing-copy': text = ''.join(line+'\n' for line in text.splitlines() if not line.startswith('N10CPD1 id='+identity+' copy=1 '))
        elif name == 'duplicate-copy': text += next(line+'\n' for line in text.splitlines() if line.startswith('N10CPD1'))
        elif name == 'checksum': text = text.replace('N10CPD1 id=a', 'N10CPD1 id=b', 1)
        elif name == 'identity': identity = 'b' * 32
        elif name == 'generation': generation = 43
        elif name == 'generation-wrap': generation = 0xffffffff; text = evidence(generation)
        elif name == 'counts-missing': text = ''.join(line+'\n' for line in text.splitlines() if not line.startswith('N10CPN1'))
        elif name == 'counts-partial': text = evidence(counts_changes={'exit_nr_calls': 5})
        elif name == 'pair-missing': text = ''.join(line+'\n' for line in text.splitlines() if not line.startswith('N10CPR1'))
        elif name == 'terminal-never-passes': text = evidence(terminal=True)
        elif name == 'pair-terminal-conflict': text += evidence(terminal=True)
        elif name == 'unknown-field': text = text.replace(' version=1 ', ' version=1 pointer=0 ')
        vectors[name] = {'text': text, 'identity': identity, 'generation': generation}
        try: accepted = decode(text, identity, generation)['trace_passed']
        except ValueError: accepted = False
        if accepted is not wanted: raise AssertionError('unexpected dispatch decoder verdict: ' + name)
        results[name] = True
    return results, vectors


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--artifact', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--cc', default='clang')
    args = parser.parse_args()
    if args.output.exists() or args.output.is_symlink(): raise ValueError('fresh trace proof output required')
    before = {name: (args.artifact / BASE / name).read_bytes() for name in TARGETS}
    after = {name: (args.artifact / PREPARED / name).read_bytes() for name in TARGETS}
    if transform(before) != after: raise ValueError('trace model requires exact production transform')
    # Removing only new observer calls must recover the original generic function.
    chain = function(after['kernel/notifier.c'], b'static int notifier_call_chain(')[2]
    for returning in (0, 1):
        hook = ('#ifdef CONFIG_NOTE10_CPU_PM_NOTIFIER_TRACE\n\t\tn10_dispatch_observe(nl, val, nb, %d);\n#endif\n' % returning).encode()
        chain = chain.replace(hook, b'')
        if returning == 1: chain = chain.replace(b'\n' + hook.rstrip(b'\n'), b'')
    if chain != function(before['kernel/notifier.c'], b'static int notifier_call_chain(')[2]:
        raise ValueError('original notifier dispatch statements changed')
    for signature in (b'static int cpu_pm_notify(', b'int cpu_pm_enter(void)', b'int cpu_pm_exit(void)'):
        composed = function(after['kernel/cpu_pm.c'], signature)[2]
        restored = re.sub(br'#ifdef CONFIG_NOTE10_CPU_PM_NOTIFIER_TRACE\n.*?#endif\n', b'', composed, flags=re.S)
        if restored != function(before['kernel/cpu_pm.c'], signature)[2]:
            raise ValueError('original CPU_PM notify/API statements changed')
    args.output.mkdir(parents=True)
    source = native_source(after)
    generated = args.output / 'dispatch-native.c'; generated.write_bytes(source)
    # Filename follows compiler target host, while validators select by presence.
    import os
    executable = args.output / ('dispatch-native.exe' if os.name == 'nt' else 'dispatch-native')
    compiled = subprocess.run([args.cc, '-std=gnu99', '-O0', str(generated), '-o', str(executable)], capture_output=True)
    (args.output / 'compile.log').write_bytes(compiled.stdout + compiled.stderr)
    if compiled.returncode: raise ValueError('dispatch native compile failed')
    completed = subprocess.run([str(executable.resolve())], capture_output=True)
    (args.output / 'native.log').write_bytes(completed.stdout)
    if completed.returncode or completed.stderr: raise ValueError('dispatch native cases failed')
    if completed.stdout.decode('ascii').splitlines() != ['PASS|' + name for name in NATIVE_CASES]:
        raise ValueError('dispatch native case transcript differs')
    off_source = disabled_source(after)
    off_generated = args.output/'dispatch-disabled.c'; off_generated.write_bytes(off_source)
    off_executable = args.output/('dispatch-disabled.exe' if os.name=='nt' else 'dispatch-disabled')
    off_compile = subprocess.run([args.cc,'-std=gnu99','-O0',str(off_generated),'-o',str(off_executable)],capture_output=True)
    (args.output/'disabled-compile.log').write_bytes(off_compile.stdout+off_compile.stderr)
    if off_compile.returncode:raise ValueError('disabled dispatch source compile failed')
    off_run = subprocess.run([str(off_executable.resolve())],capture_output=True)
    (args.output/'disabled-native.log').write_bytes(off_run.stdout)
    if off_run.returncode or off_run.stderr or off_run.stdout.decode('ascii').splitlines()!=['PASS|trace-disabled-original-semantics']:
        raise ValueError('disabled dispatch native behavior differs')
    if b'N10CPDC1' in off_executable.read_bytes():raise ValueError('disabled dispatch marker remains compiled')
    results, vectors = parser_cases()
    (args.output / 'parser-vectors.json').write_text(json.dumps(vectors, indent=2)+'\n', encoding='utf8', newline='\n')
    (args.output / 'parser.log').write_text(''.join('PASS|'+name+'\n' for name in PARSER_CASES), encoding='ascii', newline='\n')
    # Every formatted scalar is bounded; even uint32 maxima fit the existing frame.
    max_frame = FRAME_FORMAT.replace('%s', 'a'*32).replace('%u', '4294967295')
    if len(max_frame) >= 512: raise ValueError('dispatch companion frame exceeds existing limit')
    proof = {'passed': True, 'synthetic_only': True, 'hardware_verified': False,
             'native_cases': list(NATIVE_CASES), 'parser_cases': list(PARSER_CASES),
             'parser_results': results, 'source_sha256': {n: sha(after[n]) for n in TARGETS},
             'baseline_sha256': {n: sha(before[n]) for n in TARGETS},
             'sources_sha256': {n: sha((HERE/n).read_bytes()) for n in SOURCES},
             'generated_sha256': sha(source), 'executable_sha256': sha(executable.read_bytes()),
             'compile_log_sha256': sha((args.output/'compile.log').read_bytes()),
             'native_log_sha256': sha((args.output/'native.log').read_bytes()),
             'parser_log_sha256': sha((args.output/'parser.log').read_bytes()),
             'parser_vectors_sha256': sha((args.output/'parser-vectors.json').read_bytes()),
             'disabled_source_sha256':sha(off_source),
             'disabled_executable_sha256':sha(off_executable.read_bytes()),
             'disabled_compile_log_sha256':sha((args.output/'disabled-compile.log').read_bytes()),
             'disabled_native_log_sha256':sha((args.output/'disabled-native.log').read_bytes()),
             'disabled_marker_absent':True,
             'max_frame_length': len(max_frame), 'original_callback_operand_preserved': True,
             'original_notify_enter_exit_preserved': True, 'old_models_reexecuted': False}
    (args.output / 'result.json').write_text(json.dumps(proof, indent=2)+'\n', encoding='utf8', newline='\n')


if __name__ == '__main__':
    main()
