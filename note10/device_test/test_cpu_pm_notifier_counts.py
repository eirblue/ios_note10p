"""Synthetic-only focused proof for guarded CPU_PM notifier nr_calls capture."""
import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path

from prepare_cpu_pm_roundtrip import TARGETS, function, transform, validate_transform
from test_cpu_pm_roundtrip import PREFIX, extract_helper
from decode_cpu_pm_roundtrip import COUNTS_SCHEMA, decode_counts
from decode_reservation import checksum

HERE = Path(__file__).resolve().parent
CASES = (
    'success-six-plus-six',
    'enter-failure-prefix-preserved',
    'exit-error-no-retry',
    'stop-count-is-partial',
    'nested-reentry-invalidates-capture',
    'foreign-cpu-events-do-not-claim-latch',
    'ordinary-exit-keeps-null-counter',
    'success-and-terminal-frame-budget',
    'counts-success', 'counts-terminal-never-passes', 'counts-generation-wrap',
    'counts-missing-copy-rejected', 'counts-id-rejected', 'counts-generation-rejected',
    'counts-checksum-rejected', 'counts-copy-conflict-rejected',
    'counts-overflow-rejected', 'counts-roster-rejected', 'counts-negative-zero-rejected',
    'counts-cpr-cross-binding-rejected',
)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def strip_function(source, signature):
    if isinstance(source, str):
        signature = signature.decode('ascii') if isinstance(signature, bytes) else signature
        left, right = '{', '}'
    elif isinstance(source, bytes):
        signature = signature.encode('ascii') if isinstance(signature, str) else signature
        left, right = b'{', b'}'
    else:
        raise TypeError('source must be text or bytes')
    if source.count(signature) != 1:
        shown = signature.decode('ascii') if isinstance(signature, bytes) else signature
        raise ValueError('expected one function: ' + shown)
    start = source.index(signature)
    brace = source.index(left, start)
    depth = 0
    for pos in range(brace, len(source)):
        if source[pos:pos + 1] == left:
            depth += 1
        elif source[pos:pos + 1] == right:
            depth -= 1
            if depth == 0:
                return source[:start] + source[pos + 1:]
    shown = signature.decode('ascii') if isinstance(signature, bytes) else signature
    raise ValueError('unterminated function: ' + shown)


def extract_roundtrip_helper(raw):
    marker = b'static unsigned int n10_cpu_pm_roundtrip_active;'
    active = raw.find(marker)
    start = raw.rfind(b'#ifdef CONFIG_NOTE10_CPU_PM_ROUNDTRIP', 0, active)
    if active < 0 or start < 0:
        raise ValueError('guarded roundtrip helper is missing')
    depth = 0
    pos = start
    for line in raw[start:].splitlines(keepends=True):
        directive = line.strip()
        if directive.startswith((b'#ifdef ', b'#ifndef ', b'#if ')):
            depth += 1
        elif directive == b'#endif':
            depth -= 1
            if depth == 0:
                return raw[start:pos + len(line)]
        pos += len(line)
    raise ValueError('unterminated guarded roundtrip helper')


def sample_definition():
    old = (b'struct n10_cpu_pm_roundtrip_sample { unsigned int generation,attempted,chain_lock_acquired,chain_lock_released,roster_count,roster_valid,pre_snapshot_valid,post_snapshot_valid,cpu_before,online_before,online_count_before,enter_calls,exit_calls,enter_succeeded,exit_succeeded,daif_stable,timer_stable,gic_stable,ehld_before,ehld_after,context_stable,passed,terminal_attempted,terminal_recorded,terminal_completed,caller_invoked,terminal_stage; int terminal_outer_error,terminal_helper_error,enter_error,exit_error,error; };')
    new = (b'struct n10_cpu_pm_roundtrip_sample { unsigned int generation,attempted,chain_lock_acquired,chain_lock_released,roster_count,roster_valid,pre_snapshot_valid,post_snapshot_valid,cpu_before,online_before,online_count_before,enter_calls,exit_calls,enter_succeeded,exit_succeeded,daif_stable,timer_stable,gic_stable,ehld_before,ehld_after,context_stable,passed,terminal_attempted,terminal_recorded,terminal_completed,caller_invoked,terminal_stage,notifier_count_capture_valid,notifier_count_conflict,enter_nr_calls_seen,exit_nr_calls_seen; int terminal_outer_error,terminal_helper_error,enter_error,exit_error,error,enter_nr_calls,exit_nr_calls; };')
    return old, new


def validate_frame_budget(prepared_probe):
    text = prepared_probe.decode('ascii')
    if 'if (n<0 || n>=512)return -E2BIG;' not in text:
        raise ValueError('pinned emitter length guard is absent')
    formats = {}
    for tag in ('N10CPN1', 'N10CPT1'):
        start = text.index('n=snprintf(frame,sizeof(frame),', text.index('static int n10_pre_emit_counts')) if tag == 'N10CPN1' else text.index('n=snprintf(frame,sizeof(frame),"id=%s copy=%u generation=%u attempted=%u recorded=')
        match = re.search(r'"([^"]+)"', text[start:])
        if not match:
            raise ValueError('frame format missing: ' + tag)
        fmt = match.group(1)
        # Respect actual field domains: the pair counters and flags are bounded,
        # while generation and signed errno fields use their full integer widths.
        bounds = {
            'copy': '1', 'generation': '4294967295', 'attempted': '1',
            'roster': '6', 'roster_valid': '1', 'enter_calls': '1',
            'exit_calls': '1', 'enter_nr_calls': '6', 'exit_nr_calls': '6',
            'enter_seen': '1', 'exit_seen': '1', 'capture_valid': '1',
            'conflict': '1', 'enter_error': '-2147483648',
            'exit_error': '-2147483648', 'error': '-2147483648',
            'caller_invoked': '1', 'terminal_stage': '5',
            'terminal_helper_error': '-2147483648',
            'terminal_probe_error': '-2147483648',
            'terminal_outer_error': '-2147483648',
            'recorded': '1', 'completed': '1', 'stage': '5',
            'outer_error': '-2147483648', 'helper_error': '-2147483648',
            'probe_error': '-2147483648',
        }
        fields = re.findall(r'(\w+)=%([sud])', fmt)
        def max_value(match):
            field, conversion = fields[max_value.index]
            max_value.index += 1
            if conversion == 's':
                return 'x' * 32
            if field not in bounds:
                raise ValueError('unbounded frame field: ' + field)
            return bounds[field]
        max_value.index = 0
        rendered = re.sub(r'%[sud]', max_value, fmt)
        if re.search(r'%(?!%)', re.sub(r'%%', '', rendered)):
            raise ValueError('unhandled frame format conversion: ' + tag)
        n = len(rendered)
        if n >= 512 or n + len(tag) + 96 > 32768:
            raise ValueError('maximum frame exceeds existing emitter budget: ' + tag)
        formats[tag] = n
    return formats


def count_frame(values, alter_checksum=False):
    body=' '.join(key+'='+str(values[key]) for key in COUNTS_SCHEMA)
    digest=checksum(body.encode('ascii')) ^ int(alter_checksum)
    return 'N10CPN1 '+body+' checksum=%08x\n' % digest


def parser_case_transcripts():
    identity='a'*32; generation=42
    values={
        'id':identity,'copy':0,'generation':generation,'attempted':1,'roster':6,
        'roster_valid':1,'enter_calls':1,'exit_calls':1,'enter_nr_calls':6,
        'exit_nr_calls':6,'enter_seen':1,'exit_seen':1,'capture_valid':1,
        'conflict':0,'enter_error':0,'exit_error':0,'error':0,
        'caller_invoked':1,'terminal_stage':0,'terminal_helper_error':0,
        'terminal_probe_error':0,'terminal_outer_error':0,
    }
    pair={'generation':generation,'attempted':1,'roster_count':6,'enter_calls':1,'exit_calls':1}
    def copies(base, second=None, bad=False):
        first=dict(base,copy=0);other=dict(base if second is None else second,copy=1)
        return count_frame(first,bad)+count_frame(other)
    success=decode_counts(copies(values),identity,generation,pair=pair)
    if success['counts_passed'] is not True: raise AssertionError('valid notifier-count pair rejected')

    terminal_values=dict(values,attempted=0,roster=0,roster_valid=0,enter_calls=0,
        exit_calls=0,enter_nr_calls=0,exit_nr_calls=0,enter_seen=0,exit_seen=0,
        capture_valid=0,caller_invoked=0,terminal_stage=1,terminal_outer_error=-5)
    terminal={'generation':generation,'attempted':0,'caller_invoked':False,'stage':1,
        'helper_error':0,'probe_error':0,'outer_error':-5,'enter_calls':0,
        'exit_calls':0,'enter_error':0,'exit_error':0}
    terminal_result=decode_counts(copies(terminal_values),identity,generation,terminal=terminal)
    if terminal_result['counts_passed'] is not False: raise AssertionError('terminal companion passed count row')

    wrap=dict(values,generation=0xffffffff)
    decode_counts(copies(wrap),identity,0xffffffff,pair={**pair,'generation':0xffffffff})
    tests=(
        ('counts-missing-copy-rejected', count_frame(dict(values,copy=0)), identity, generation, pair, None),
        ('counts-id-rejected', copies(values), 'b'*32, generation, pair, None),
        ('counts-generation-rejected', copies(values), identity, generation+1, pair, None),
        ('counts-checksum-rejected', count_frame(dict(values,copy=0),True)+count_frame(dict(values,copy=1)), identity, generation, pair, None),
        ('counts-copy-conflict-rejected', copies(values,dict(values,conflict=1)), identity, generation, pair, None),
        ('counts-overflow-rejected', copies(dict(values,enter_nr_calls=7)), identity, generation, pair, None),
        ('counts-roster-rejected', copies(dict(values,roster=7)), identity, generation, pair, None),
        ('counts-negative-zero-rejected', copies(dict(values,enter_error='-0')), identity, generation, pair, None),
        ('counts-cpr-cross-binding-rejected', copies(values), identity, generation,
         {**pair,'roster_count':5}, None),
    )
    lines=['PASS|counts-success|6|6','PASS|counts-terminal-never-passes|0',
           'PASS|counts-generation-wrap|4294967295']
    for name,text,ident,gen,expected_pair,expected_terminal in tests:
        try: decode_counts(text,ident,gen,pair=expected_pair,terminal=expected_terminal)
        except ValueError: lines.append('PASS|'+name)
        else: raise AssertionError('invalid notifier-count evidence accepted: '+name)
    return lines


def write_parser_only_proof(output):
    output=Path(output)
    if output.exists():raise ValueError('fresh parser-only proof path required')
    output.mkdir(parents=True)
    transcripts=parser_case_transcripts()
    proof={'passed':True,'synthetic_only':True,'hardware_verified':False,
           'cases':[line.split('|',2)[1] for line in transcripts],
           'transcripts':transcripts,
           'decoder_sha256':sha((HERE/'decode_cpu_pm_roundtrip.py').read_bytes()),
           'harness_sha256':sha(Path(__file__).read_bytes()),
           'native_or_hardware_execution':False}
    raw=(json.dumps(proof,indent=2)+'\n').encode('utf-8')
    (output/'result.json').write_bytes(raw)
    return sha(raw)


def compile_legacy_helper(prepared_cpu, output, cc):
    output=Path(output);output.mkdir(parents=True,exist_ok=False)
    helper=extract_helper(prepared_cpu)
    generated=output/'legacy-roundtrip-helper.c'
    source=(PREFIX+'\n'+helper.decode('ascii')+
            '\nint main(void) { struct n10_cpu_pm_roundtrip_sample out={0}; '
            'return n10_cpu_pm_roundtrip(active_gen,&prior_sample,&out)==0; }\n')
    generated.write_text(source,encoding='ascii',newline='\n')
    executable=output/('legacy-roundtrip-helper.exe' if __import__('os').name=='nt' else 'legacy-roundtrip-helper')
    result=subprocess.run([cc,'-std=gnu11','-Wall','-Werror','-Wno-unused-function',
                           '-Wno-unused-variable','-Wno-unused-but-set-variable',
                           str(generated),'-o',str(executable)],capture_output=True,timeout=120)
    log=output/'compile.log';log.write_bytes(result.stdout+result.stderr)
    if result.returncode:raise RuntimeError('legacy CPU_PM helper compile-only check failed')
    proof={'passed':True,'compiled_only':True,'executed':False,
           'extracted_helper_sha256':sha(helper),'generated_sha256':sha(generated.read_bytes()),
           'compile_log_sha256':sha(log.read_bytes()),
           'executable_sha256':sha(executable.read_bytes())}
    (output/'result.json').write_text(json.dumps(proof,indent=2)+'\n',encoding='utf-8',newline='\n')
    return proof


def native_source(prepared_cpu):
    prefix = PREFIX
    old_struct, new_struct = sample_definition()
    if prefix.count(old_struct.decode()) != 1:
        raise ValueError('focused harness sample structure anchor differs')
    prefix = prefix.replace(old_struct.decode(), new_struct.decode(), 1)
    old_block = 'struct notifier_block { int (*notifier_call)(void); int priority; struct notifier_block *next; unsigned int kind; };'
    new_block = 'struct notifier_block; struct notifier_block { int (*notifier_call)(struct notifier_block *, unsigned long, void *); int priority; struct notifier_block *next; unsigned int kind; };'
    if prefix.count(old_block) != 1:
        raise ValueError('focused harness notifier block anchor differs')
    prefix = prefix.replace(old_block, new_block, 1)
    prefix = strip_function(prefix, b'static int cpu_pm_enter(void)')
    prefix = strip_function(prefix, b'static int cpu_pm_exit(void)')
    fake_callback = 'blocks[i].notifier_call=(int(*)(void))(uintptr_t)(i+1);'
    if prefix.count(fake_callback) != 1:
        raise ValueError('focused harness callback registration anchor differs')
    prefix = prefix.replace(fake_callback, 'blocks[i].notifier_call=counting_callback;', 1)

    callback_code = r'''
#define CONFIG_NOTE10_CPU_PM_NOTIFIER_COUNTS 1
#define CONFIG_NOTE10_CPU_PM_FAILURE_GUARD 1
#define CONFIG_NOTE10_CPU_PM_ROUNDTRIP 1
#define NOTIFY_DONE 0x0000
#define NOTIFY_OK 0x0001
#define NOTIFY_STOP_MASK 0x8000
#define NOTIFY_STOP (NOTIFY_STOP_MASK | NOTIFY_OK)
#define NOTIFY_BAD (NOTIFY_STOP_MASK | 0x0002)
/* Pinned include/linux/cpu_pm.h values: PREPARE=0, ENTER=1,
 * ENTER_FAILED=2, EXIT=3, EXIT_POST=4. */
enum cpu_pm_event { CPU_PM_PREPARE=0, CPU_PM_ENTER=1, CPU_PM_ENTER_FAILED=2,
                    CPU_PM_EXIT=3, CPU_PM_EXIT_POST=4 };
static unsigned int count_mode, callback_enter_count, callback_exit_count;
static unsigned int callback_enter_failed_count, callback_nested_once;
static unsigned int callback_foreign_enter_once, callback_foreign_exit_once;
static unsigned int event_enter_count, event_exit_count, event_enter_failed_count;
static unsigned int rcu_irq_enter_count, rcu_irq_exit_count, rcu_read_lock_count, rcu_read_unlock_count;
static unsigned int null_exit_counter_count;
static int cpu_pm_enter(void);
int cpu_pm_exit(void);
int n10_cpu_pm_roundtrip(unsigned int, const struct n10_precond_sample *,
                         struct n10_cpu_pm_roundtrip_sample *);
static void reset_counts(void) {
    callback_enter_count=callback_exit_count=0;
    callback_enter_failed_count=callback_nested_once=0;
    callback_foreign_enter_once=callback_foreign_exit_once=0;
    event_enter_count=event_exit_count=event_enter_failed_count=0;
    rcu_irq_enter_count=rcu_irq_exit_count=rcu_read_lock_count=rcu_read_unlock_count=0;
    null_exit_counter_count=0;
}
static void rcu_irq_enter_irqson(void) { rcu_irq_enter_count++; }
static void rcu_irq_exit_irqson(void) { rcu_irq_exit_count++; }
static void rcu_read_lock(void) { rcu_read_lock_count++; }
static void rcu_read_unlock(void) { rcu_read_unlock_count++; }
static int notifier_to_errno(int ret) { ret &= ~NOTIFY_STOP_MASK; return ret > NOTIFY_OK ? NOTIFY_OK - ret : 0; }
static int __atomic_notifier_call_chain(void *unused, unsigned long event, void *v,
                                       int nr_to_call, int *nr_calls)
{
    int ret=NOTIFY_DONE;
    struct notifier_block *nb=cpu_pm_notifier_chain.head, *next_nb;
    (void)unused;
    rcu_read_lock();
    while (nb && nr_to_call) {
        next_nb=nb->next;
        ret=nb->notifier_call(nb,event,v);
        if (nr_calls) (*nr_calls)++;
        if (ret & NOTIFY_STOP_MASK) break;
        nb=next_nb;
        nr_to_call--;
    }
    rcu_read_unlock();
    return ret;
}
static int counting_callback(struct notifier_block *nb, unsigned long event, void *v)
{
    (void)v;
    if (event==CPU_PM_ENTER) {
        callback_enter_count++;
        if (count_mode==6 && !callback_foreign_enter_once && nb==&blocks[0]) {
            callback_foreign_enter_once=1; cpu_id=1; (void)cpu_pm_enter(); cpu_id=0;
        }
        if (count_mode==5 && !callback_nested_once && nb==&blocks[0]) {
            callback_nested_once=1;
            (void)cpu_pm_enter();
        }
        if (count_mode==1 && nb==&blocks[2]) return NOTIFY_BAD;
        if (count_mode==3 && nb==&blocks[2]) return NOTIFY_STOP;
        ehld_running=0;
    } else if (event==CPU_PM_ENTER_FAILED) {
        callback_enter_failed_count++;
    } else if (event==CPU_PM_EXIT) {
        callback_exit_count++;
        if (count_mode==6 && !callback_foreign_exit_once && nb==&blocks[0]) {
            callback_foreign_exit_once=1; cpu_id=1; (void)cpu_pm_exit(); cpu_id=0;
        }
        ehld_running=1;
        if (count_mode==2 && nb==&blocks[2]) return NOTIFY_BAD;
    }
    return NOTIFY_OK;
}
'''
    # Insert declarations before reset_case, where the callback is installed.
    reset_anchor = 'static void reset_case(unsigned int m)'
    if prefix.count(reset_anchor) != 1:
        raise ValueError('focused harness reset anchor differs')
    prefix = prefix.replace(reset_anchor, callback_code + '\n' + reset_anchor, 1)

    from prepare_cpu_pm_roundtrip import COUNTS_STATE
    state_start = prepared_cpu.index(COUNTS_STATE)
    state = prepared_cpu[state_start:state_start + len(COUNTS_STATE)]
    functions = []
    for signature in (b'static int cpu_pm_notify(', b'int cpu_pm_enter(void)', b'int cpu_pm_exit(void)'):
        _, _, body = function(prepared_cpu, signature)
        functions.append(body.decode('ascii'))
    helper = extract_roundtrip_helper(prepared_cpu).decode('ascii')
    helper = re.sub(r'(?m)^#include <[^>]+>\n', '', helper)
    main = r'''
int main(void) {
    struct n10_cpu_pm_roundtrip_sample out={0};
    int ret;
    reset_case(0);
    reset_counts();
    count_mode=0;
    ret=n10_cpu_pm_roundtrip(active_gen,&prior_sample,&out);
    if (ret || !out.passed || out.enter_calls!=1 || out.exit_calls!=1 ||
        !out.notifier_count_capture_valid || out.notifier_count_conflict ||
        !out.enter_nr_calls_seen || !out.exit_nr_calls_seen ||
        out.enter_nr_calls!=6 || out.exit_nr_calls!=6 ||
        callback_enter_count!=6 || callback_exit_count!=6 ||
        rcu_irq_enter_count!=rcu_irq_exit_count ||
        rcu_read_lock_count!=rcu_read_unlock_count ||
        n10_cpu_pm_counts_owned || n10_cpu_pm_counts_armed || n10_cpu_pm_counts_claimed)
        return 1;
    printf("PASS|success|%u|%u|%u|%u\n",out.enter_nr_calls,out.exit_nr_calls,
           out.enter_calls,out.exit_calls);

    reset_case(0); memset(&out,0,sizeof(out)); count_mode=1;
    reset_counts();
    n10_cpu_pm_roundtrip_active=0; n10_cpu_pm_roundtrip_seen=0;
    ret=n10_cpu_pm_roundtrip(active_gen,&prior_sample,&out);
    if (!ret || out.enter_calls!=1 || out.exit_calls!=0 || out.enter_error>=0 ||
        out.enter_nr_calls!=3 || out.exit_nr_calls!=0 ||
        callback_enter_failed_count!=2 || callback_exit_count!=0 ||
        !out.enter_nr_calls_seen || out.exit_nr_calls_seen ||
        !out.notifier_count_capture_valid || n10_cpu_pm_counts_owned || n10_cpu_pm_counts_armed)
        return 2;
    printf("PASS|enter-failure-prefix|%u|%u|%u|%d\n",out.enter_nr_calls,
           callback_enter_failed_count,out.exit_calls,out.enter_error);

    reset_case(0); memset(&out,0,sizeof(out)); count_mode=2;
    reset_counts();
    n10_cpu_pm_roundtrip_active=0; n10_cpu_pm_roundtrip_seen=0;
    ret=n10_cpu_pm_roundtrip(active_gen,&prior_sample,&out);
    if (!ret || out.enter_nr_calls!=6 || out.exit_nr_calls!=3 ||
        out.enter_calls!=1 || out.exit_calls!=1 || out.exit_error>=0 ||
        callback_exit_count!=3 || event_exit_count!=1 || n10_cpu_pm_counts_owned)
        return 3;
    printf("PASS|exit-error-no-retry|%u|%u|%u\n",out.enter_nr_calls,
           out.exit_nr_calls,event_exit_count);

    reset_case(0); memset(&out,0,sizeof(out)); count_mode=3;
    reset_counts();
    n10_cpu_pm_roundtrip_active=0; n10_cpu_pm_roundtrip_seen=0;
    ret=n10_cpu_pm_roundtrip(active_gen,&prior_sample,&out);
    if (ret || !out.passed || out.enter_nr_calls!=3 || out.exit_nr_calls!=6 ||
        !out.notifier_count_capture_valid || out.notifier_count_conflict)
        return 4;
    printf("PASS|stop-partial-count|%u|%u|%u\n",out.enter_nr_calls,
           out.exit_nr_calls,out.passed);

    reset_case(0); memset(&out,0,sizeof(out)); count_mode=5;
    reset_counts();
    n10_cpu_pm_roundtrip_active=0; n10_cpu_pm_roundtrip_seen=0;
    ret=n10_cpu_pm_roundtrip(active_gen,&prior_sample,&out);
    if (ret || !out.passed || out.enter_nr_calls!=6 || out.exit_nr_calls!=6 ||
        !out.notifier_count_conflict || out.notifier_count_capture_valid ||
        n10_cpu_pm_counts_owned || n10_cpu_pm_counts_armed || n10_cpu_pm_counts_claimed)
        return 5;
    printf("PASS|reentry-conflict|%u|%u|%u\n",out.enter_nr_calls,
           out.exit_nr_calls,out.notifier_count_conflict);

    reset_case(0); memset(&out,0,sizeof(out)); count_mode=6;
    reset_counts(); n10_cpu_pm_roundtrip_active=0; n10_cpu_pm_roundtrip_seen=0;
    ret=n10_cpu_pm_roundtrip(active_gen,&prior_sample,&out);
    if (ret || !out.passed || !out.notifier_count_capture_valid ||
        out.notifier_count_conflict || out.enter_nr_calls!=6 || out.exit_nr_calls!=6 ||
        !callback_foreign_enter_once || !callback_foreign_exit_once ||
        callback_enter_count!=12 || callback_exit_count!=12 || null_exit_counter_count!=1 ||
        n10_cpu_pm_counts_owned || n10_cpu_pm_counts_armed || n10_cpu_pm_counts_claimed)
        return 7;
    printf("PASS|foreign-cpu-events|%u|%u|%u|%u\n",out.enter_nr_calls,
           out.exit_nr_calls,null_exit_counter_count,out.notifier_count_capture_valid);

    reset_case(0); memset(&out,0,sizeof(out)); count_mode=0;
    reset_counts();
    n10_cpu_pm_counts_owned=0; n10_cpu_pm_counts_armed=0;
    n10_cpu_pm_counts_exit_seen=0; n10_cpu_pm_counts_exit_nr_calls=0;
    (void)cpu_pm_exit();
    if (n10_cpu_pm_counts_exit_seen || n10_cpu_pm_counts_exit_nr_calls ||
        !null_exit_counter_count || n10_cpu_pm_counts_owned || n10_cpu_pm_counts_armed)
        return 6;
    printf("PASS|ordinary-exit-null|%u\n",null_exit_counter_count);
    return 0;
}
'''
    # Track API event and NULL counter behavior in the actual notifier wrapper.
    # Instrument only the harness stub, never the production functions.
    chain_stub_anchor = 'static int __atomic_notifier_call_chain(void *unused, unsigned long event, void *v,\n                                       int nr_to_call, int *nr_calls)\n{\n    int ret=NOTIFY_DONE;'
    chain_stub_replacement = chain_stub_anchor.replace(
        '    int ret=NOTIFY_DONE;',
        '    int ret=NOTIFY_DONE;\n    if (event==CPU_PM_ENTER) event_enter_count++;\n    else if (event==CPU_PM_EXIT) { event_exit_count++; if (!nr_calls) null_exit_counter_count++; }\n    else if (event==CPU_PM_ENTER_FAILED) event_enter_failed_count++;')
    if callback_code not in prefix:
        raise ValueError('focused callback stub insertion failed')
    # Replace only in the generated prefix. The function itself is part of the synthetic harness.
    prefix = prefix.replace(chain_stub_anchor, chain_stub_replacement, 1)
    return prefix + '\n' + state.decode('ascii') + '\n' + '\n'.join(functions) + '\n' + helper + '\n' + main


def build_proof(baseline_source, output, cc):
    baseline_source, output = Path(baseline_source), Path(output)
    if output.exists():
        raise ValueError('fresh proof output required')
    old = {name: (baseline_source / name).read_bytes() for name in TARGETS}
    prepared = transform(old)
    if not validate_transform(old, prepared):
        raise ValueError('production CPU_PM transform does not validate')
    output.mkdir(parents=True)
    for name, raw in prepared.items():
        path = output / 'transformed' / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
    cpu = prepared['kernel/cpu_pm.c']
    frame_lengths = validate_frame_budget(prepared['arch/arm64/mm/note10_pm_pre_probe.c'])
    legacy_proof=compile_legacy_helper(cpu,output/'legacy-helper-compile-only',cc)
    generated = output / 'notifier-counts-native.c'
    generated.write_text(native_source(cpu), encoding='ascii', newline='\n')
    executable = output / ('notifier-counts-native.exe' if __import__('os').name == 'nt' else 'notifier-counts-native')
    result = subprocess.run([cc, '-std=gnu11', '-Wall', '-Werror',
                             '-Wno-unused-variable', '-Wno-unused-but-set-variable',
                             '-Wno-unused-function',
                             str(generated), '-o', str(executable)],
                            capture_output=True, timeout=120)
    compile_log = output / 'compile.log'
    compile_log.write_bytes(result.stdout + result.stderr)
    if result.returncode:
        raise RuntimeError('notifier-count native compile failed')
    run = subprocess.run([str(executable)], capture_output=True, timeout=30)
    raw = run.stdout + run.stderr
    (output / 'native.log').write_bytes(raw)
    lines = raw.decode('ascii', errors='replace').strip().splitlines()
    lines.append('PASS|frame-budget|%u|%u' % (frame_lengths['N10CPN1'], frame_lengths['N10CPT1']))
    lines.extend(parser_case_transcripts())
    if run.returncode or len(lines) != len(CASES) or any(not line.startswith('PASS|') for line in lines):
        raise RuntimeError('notifier-count focused native case failed')
    proof = {
        'passed': True,
        'synthetic_only': True,
        'hardware_verified': False,
        'cases': list(CASES),
        'transcripts': lines,
        'transform_source_sha256': {name: sha(raw) for name, raw in prepared.items()},
        'baseline_target_sha256': {name: sha(raw) for name, raw in old.items()},
        'generated_sha256': sha(generated.read_bytes()),
        'compile_log_sha256': sha(compile_log.read_bytes()),
        'native_log_sha256': sha(raw),
        'count_marker_present': b'N10CPNC1' in cpu,
        'max_valid_frame_lengths': frame_lengths,
        'legacy_helper_extraction_compile_only':legacy_proof,
        'existing_pair_and_terminal_markers_preserved': b'N10CPMRT1' in cpu and b'N10CPT1' in prepared['arch/arm64/mm/note10_pm_pre_probe.c'],
        'old_native_and_decoder_models_reexecuted': False,
    }
    (output / 'result.json').write_text(json.dumps(proof, indent=2) + '\n', encoding='utf-8', newline='\n')
    return proof


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--baseline-source')
    parser.add_argument('--output')
    parser.add_argument('--cc')
    parser.add_argument('--parser-only',action='store_true')
    parser.add_argument('--proof-output')
    args = parser.parse_args()
    if args.parser_only:
        if not args.proof_output:parser.error('--parser-only requires --proof-output')
        proof_sha=write_parser_only_proof(args.proof_output)
        print(json.dumps({'passed':True,'synthetic_only':True,'hardware_verified':False,
                          'parser_cases':len(parser_case_transcripts()),'proof_sha256':proof_sha}))
        return
    if not args.baseline_source or not args.output or not args.cc:
        parser.error('--baseline-source, --output and --cc are required')
    proof = build_proof(args.baseline_source, args.output, args.cc)
    print(json.dumps({'passed': proof['passed'], 'synthetic_only': True,
                      'hardware_verified': False, 'cases': len(proof['cases']),
                      'proof_sha256': sha((Path(args.output) / 'result.json').read_bytes())}))


if __name__ == '__main__':
    main()
