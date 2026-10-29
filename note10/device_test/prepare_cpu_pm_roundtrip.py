"""Build the bounded opt-in single-CPU CPU_PM roundtrip source transform."""
import hashlib
import re
import shutil
from pathlib import Path

TARGETS = (
    'kernel/cpu_pm.c',
    'kernel/power/note10_pm_pre_capture.c',
    'include/linux/note10_pm_preconditions.h',
    'arch/arm64/mm/note10_pm_pre_probe.c',
    'kernel/power/Kconfig',
)
KCONFIG = TARGETS[-1]
OPTION = 'CONFIG_NOTE10_CPU_PM_ROUNDTRIP'
SCHEMA_VERSION = 1
BLOCK = (b'\nconfig NOTE10_CPU_PM_ROUNDTRIP\n'
         b'\tbool "Experimental single-CPU CPU PM roundtrip"\n'
         b'\tdepends on NOTE10_EHLD_RUNNING_LOCK_AUDIT\n'
         b'\tdepends on NOTE10_PM_IRQ_TEST && NOTE10_CPU_PM_PRECONDITIONS\n'
         b'\tdefault n\n')


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def replace_unique(raw, old, new, label):
    if raw.count(old) != 1:
        raise ValueError('expected exactly one ' + label)
    return raw.replace(old, new, 1)


def function(raw, signature):
    if raw.count(signature) != 1:
        raise ValueError('function signature must be unique: ' + signature.decode())
    start = raw.index(signature)
    brace = raw.index(b'{', start)
    depth = 0
    for pos in range(brace, len(raw)):
        if raw[pos:pos + 1] == b'{':
            depth += 1
        elif raw[pos:pos + 1] == b'}':
            depth -= 1
            if depth == 0:
                return start, pos + 1, raw[start:pos + 1]
    raise ValueError('unterminated function: ' + signature.decode())


CPU_PM_HELPER = b'''\n#ifdef CONFIG_NOTE10_CPU_PM_ROUNDTRIP
/* Included in cpu_pm.c: inspect the private registration chain without
 * exporting notifier pointers or invoking callbacks directly. */
#include <linux/note10_pm_preconditions.h>
#include <linux/note10_pm_irq.h>
#include <linux/note10_ehld_lock_audit.h>
#include <linux/cpu.h>
#include <linux/preempt.h>
#include <linux/irqflags.h>
#include <asm/sysreg.h>
#include <asm/ptrace.h>
static unsigned int n10_cpu_pm_roundtrip_active;
static unsigned int n10_cpu_pm_roundtrip_seen;
static int (*const n10_cpu_pm_roundtrip_getters[])(struct notifier_block *, struct n10_precond_row *) = {
    n10_pre_gic, n10_pre_timer, n10_pre_fpsimd, n10_pre_sugov, n10_pre_pmu, n10_pre_ehld
};

static int n10_cpu_pm_roundtrip_context(unsigned int generation, unsigned int preempt)
{
    return generation && n10_pre_context(generation, 1, preempt) &&
        raw_smp_processor_id() == 0 && num_online_cpus() == 1 &&
        cpumask_bits(cpu_online_mask)[0] == 1 && irqs_disabled() &&
        preempt_count() == preempt;
}

static int n10_cpu_pm_roundtrip_row_equal(const struct n10_precond_gic_row *a,
                                           const struct n10_precond_gic_row *b)
{
    unsigned int i;
    if (a->enable != b->enable || a->active != b->active ||
        a->config[0] != b->config[0] || a->config[1] != b->config[1])
        return 0;
    for (i = 0; i < 8; i++)
        if (a->priority[i] != b->priority[i]) return 0;
    return 1;
}

static int n10_cpu_pm_roundtrip_row_contract(unsigned int kind,
                                              const struct n10_precond_row *row)
{
    if (!row || row->kind != kind) return 0;
    switch (kind) {
    case N10_PRE_GIC:
    case N10_PRE_TIMER:
        return row->valid == 0;
    case N10_PRE_FPSIMD:
        return row->valid == 15;
    case N10_PRE_SUGOV:
        return row->valid == 3 && row->value[1] == 0;
    case N10_PRE_PMU:
        return row->valid == 31 && row->value[0] == 1;
    case N10_PRE_EHLD:
        return row->valid == 3 && row->value[0] == 1 && row->value[1] == 1;
    default:
        return 0;
    }
}

int n10_cpu_pm_roundtrip(unsigned int generation,
                         const struct n10_precond_sample *prior,
                         struct n10_cpu_pm_roundtrip_sample *out)
{
    struct notifier_block *node, *ehld = NULL;
    struct n10_precond_gic_row gic_before = {0}, gic_after = {0};
    struct n10_ehld_lock_row ehld_before = {0}, ehld_after = {0};
    struct n10_irq_gic_sample ctl_before = {0}, ctl_after = {0};
    unsigned long flags;
    unsigned int index = 0, i;
    u64 daif_before, daif_after, cntkctl_before, cntkctl_after;
    int error = 0, enter_error = 0, exit_error = 0;
    int enter_calls = 0, exit_calls = 0;
    unsigned int terminal_attempted, caller_invoked;
    int terminal_outer_error;

    if (!out) return -EINVAL;
    terminal_attempted=out->terminal_attempted;
    caller_invoked=out->caller_invoked;
    terminal_outer_error=out->terminal_outer_error;
    memset(out, 0, sizeof(*out));
    out->generation = generation;
    out->terminal_attempted=terminal_attempted;
    out->caller_invoked=caller_invoked;
    out->terminal_outer_error=terminal_outer_error;
    if (n10_cpu_pm_roundtrip_active || n10_cpu_pm_roundtrip_seen)
        return out->error = -EALREADY;
    n10_cpu_pm_roundtrip_active = 1;
    n10_cpu_pm_roundtrip_seen = 1;
    out->attempted = 1;
    if (!prior || !n10_cpu_pm_roundtrip_context(generation, 0) ||
        preempt_count() != 0 || !irqs_disabled() ||
        prior->generation != generation || prior->seen != 1 ||
        prior->completed != 0 || prior->bad || prior->error ||
        prior->count != ARRAY_SIZE(n10_cpu_pm_roundtrip_getters))
        { error = -EPERM; goto done; }

    for (i = 0; i < ARRAY_SIZE(n10_cpu_pm_roundtrip_getters); i++) {
        if (prior->row[i].kind != i + 1 || prior->row[i].priority != 0 ||
            !n10_cpu_pm_roundtrip_row_contract(i + 1, &prior->row[i])) {
            error = -EIO;
            goto done;
        }
    }
    if (prior->row[3].valid != 3 || prior->row[3].value[1] != 0 ||
        prior->row[4].valid != 31 || prior->row[4].value[0] != 1 ||
        prior->row[5].valid != 3 || prior->row[5].value[0] != 1 ||
        prior->row[5].value[1] != 1) {
        error = -EAGAIN;
        goto done;
    }

    if (!spin_trylock_irqsave(&cpu_pm_notifier_chain.lock, flags)) {
        error = -EBUSY;
        goto done;
    }
    out->chain_lock_acquired = 1;
    if (!n10_cpu_pm_roundtrip_context(generation, 1)) {
        error = -EPERM;
        goto chain_unlock;
    }
    node = rcu_dereference_raw(cpu_pm_notifier_chain.head);
    while (node) {
        struct n10_precond_row row = {0};
        unsigned int matches = 0, kind = 0;
        int ret;
        if (index >= ARRAY_SIZE(n10_cpu_pm_roundtrip_getters)) {
            error = -E2BIG;
            break;
        }
        for (i = 0; i < ARRAY_SIZE(n10_cpu_pm_roundtrip_getters); i++) {
            ret = n10_cpu_pm_roundtrip_getters[i](node, &row);
            if (ret < 0) { error = ret; break; }
            if (ret) { matches++; kind = i + 1; }
        }
        if (error) break;
        row.kind = kind;
        if (matches != 1 || kind != index + 1 ||
            READ_ONCE(node->priority) != 0 ||
            prior->row[index].kind != kind || prior->row[index].priority != 0 ||
            !n10_cpu_pm_roundtrip_row_contract(kind, &row)) {
            error = -EIO;
            break;
        }
        if (kind == N10_PRE_SUGOV &&
            (prior->row[index].valid != 3 || prior->row[index].value[1] != 0 ||
             row.valid != 3 || row.value[1] != 0)) {
            error = -EAGAIN;
            break;
        }
        if (kind == N10_PRE_PMU &&
            (prior->row[index].valid != 31 || prior->row[index].value[0] != 1 ||
             row.valid != 31 || row.value[0] != 1)) {
            error = -EAGAIN;
            break;
        }
        if (kind == N10_PRE_EHLD) {
            if (prior->row[index].valid != 3 || prior->row[index].value[0] != 1 ||
                prior->row[index].value[1] != 1 || row.valid != 3 ||
                row.value[0] != 1 || row.value[1] != 1) {
                error = -EAGAIN;
                break;
            }
            ehld = node;
        }
        index++;
        node = rcu_dereference_raw(node->next);
    }
    if (!error && (node || index != ARRAY_SIZE(n10_cpu_pm_roundtrip_getters) || !ehld))
        error = -EIO;
chain_unlock:
    spin_unlock_irqrestore(&cpu_pm_notifier_chain.lock, flags);
    out->chain_lock_released = 1;
    if (error) goto done;
    out->roster_count = index;
    out->roster_valid = 1;
    if (!n10_cpu_pm_roundtrip_context(generation, 0)) {
        error = -EPERM;
        goto done;
    }

    preempt_disable();
    if (!n10_cpu_pm_roundtrip_context(generation, 1)) error = -EPERM;
    ehld_before.index = 5;
    if (!error) error = n10_ehld_lock_get(&ehld_before, ehld, prior, 5, generation);
    if (!error && (ehld_before.lock_available != 1 || ehld_before.running_valid != 1 ||
                   ehld_before.running != 1)) error = -EBUSY;
    preempt_enable();
    if (error) goto done;

    preempt_disable();
    if (!n10_cpu_pm_roundtrip_context(generation, 1)) error = -EPERM;
    if (!error) error = n10_irq_gic_capture(1, &ctl_before);
    if (!error) error = n10_pre_gic_regs(1, &gic_before,
                                         ctl_before.cpu_ctlr, ctl_before.pmr);
    daif_before = read_sysreg(daif);
    cntkctl_before = read_sysreg(cntkctl_el1);
    preempt_enable();
    if (error) goto done;
    if (!n10_cpu_pm_roundtrip_context(generation, 0) || !(daif_before & PSR_I_BIT)) {
        error = -EPERM;
        goto done;
    }
    out->pre_snapshot_valid = 1;
    out->cpu_before = raw_smp_processor_id();
    out->online_before = (unsigned int)cpumask_bits(cpu_online_mask)[0];
    out->online_count_before = num_online_cpus();

    enter_calls++;
    enter_error = cpu_pm_enter();
    if (!enter_error) {
        out->enter_succeeded = 1;
        /* No probe or state check between the successful enter and its exit. */
        exit_calls++;
        exit_error = cpu_pm_exit();
        if (!exit_error) out->exit_succeeded = 1;
    }
    out->enter_calls = enter_calls;
    out->exit_calls = exit_calls;
    out->enter_error = enter_error;
    out->exit_error = exit_error;
    daif_after = read_sysreg(daif);
    preempt_disable();
    if (!n10_cpu_pm_roundtrip_context(generation, 1)) error = -EPERM;
    if (!error) error = n10_irq_gic_capture(1, &ctl_after);
    if (!error) error = n10_pre_gic_regs(1, &gic_after,
                                         ctl_after.cpu_ctlr, ctl_after.pmr);
    cntkctl_after = read_sysreg(cntkctl_el1);
    preempt_enable();
    if (error) goto done;
    out->post_snapshot_valid = 1;
    out->daif_stable = daif_before == daif_after;
    out->timer_stable = cntkctl_before == cntkctl_after;
    out->gic_stable = n10_cpu_pm_roundtrip_row_equal(&gic_before, &gic_after) &&
        ctl_before.cpu_ctlr == ctl_after.cpu_ctlr && ctl_before.pmr == ctl_after.pmr &&
        ctl_before.bpr == ctl_after.bpr && ctl_before.iidr == ctl_after.iidr &&
        ctl_before.dist_ctlr == ctl_after.dist_ctlr && ctl_before.typer == ctl_after.typer;
    out->ehld_before = (unsigned int)prior->row[5].value[0];
    preempt_disable();
    if (!n10_cpu_pm_roundtrip_context(generation, 1)) error = -EPERM;
    ehld_after.index = 5;
    if (!error) error = n10_ehld_lock_get(&ehld_after, ehld, prior, 5, generation);
    preempt_enable();
    if (error || ehld_after.lock_available != 1 || ehld_after.running_valid != 1 ||
        ehld_after.running != 1) {
        error = -EIO;
        goto done;
    }
    out->ehld_before = ehld_before.running;
    out->ehld_after = ehld_after.running;
    out->context_stable = n10_cpu_pm_roundtrip_context(generation, 0) &&
        out->cpu_before == raw_smp_processor_id() &&
        out->online_before == (unsigned int)cpumask_bits(cpu_online_mask)[0] &&
        out->online_count_before == num_online_cpus();
    if (enter_error || exit_error || !out->enter_succeeded || !out->exit_succeeded ||
        !out->daif_stable || !out->timer_stable || !out->gic_stable ||
        out->ehld_after != 1 || !out->context_stable)
        error = -EIO;
done:
    out->error = error;
    out->passed = error == 0 && out->attempted == 1 && out->roster_valid == 1 &&
        out->pre_snapshot_valid == 1 && out->post_snapshot_valid == 1 &&
        out->enter_calls == 1 && out->exit_calls == 1;
    n10_cpu_pm_roundtrip_active = 0;
    return error;
}
static const char n10_cpu_pm_roundtrip_marker[] __used = "N10CPMRT1";
#endif
'''


def _replace_once(raw, anchor, replacement, label):
    return replace_unique(raw, anchor, replacement, label)


def transform(files):
    if set(files) != set(TARGETS) or any(not isinstance(v, bytes) for v in files.values()):
        raise ValueError('exact v49 source input set required')
    out = dict(files)
    cpu = out['kernel/cpu_pm.c']
    anchor = b'#include "note10_pm_pre_chain.c"\n#endif'
    cpu = _replace_once(cpu, anchor, anchor[:-len(b'#endif')] + b'#endif\n' + CPU_PM_HELPER, 'CPU_PM guard include')
    out['kernel/cpu_pm.c'] = cpu

    header_name = 'include/linux/note10_pm_preconditions.h'
    header = out[header_name]
    record = (b'struct n10_cpu_pm_roundtrip_sample {\n'
              b' unsigned int generation, attempted, chain_lock_acquired, chain_lock_released;\n'
              b' unsigned int roster_count, roster_valid, pre_snapshot_valid, post_snapshot_valid;\n'
              b' unsigned int cpu_before, online_before, online_count_before;\n'
              b' unsigned int enter_calls, exit_calls, enter_succeeded, exit_succeeded;\n'
              b' unsigned int daif_stable, timer_stable, gic_stable, ehld_before, ehld_after, context_stable, passed;\n'
              b' unsigned int terminal_attempted, terminal_recorded, terminal_completed;\n'
              b' unsigned int caller_invoked, terminal_stage;\n'
              b' int terminal_outer_error, terminal_helper_error, terminal_probe_error;\n'
              b' int enter_error, exit_error, error;\n'
              b'};\n')
    struct_anchor = b'struct n10_precond_sample { unsigned int generation, seen, bad, completed, count; int error; struct n10_precond_row row[N10_PRECOND_CAP]; };'
    header = replace_unique(header, struct_anchor, record + struct_anchor, 'precondition roundtrip record')
    proto_anchor = b'int n10_pre_chain(struct n10_precond_sample *, unsigned int generation);'
    header = replace_unique(header, proto_anchor, proto_anchor + b'\n#ifdef CONFIG_NOTE10_CPU_PM_ROUNDTRIP\nint n10_cpu_pm_roundtrip(unsigned int, const struct n10_precond_sample *, struct n10_cpu_pm_roundtrip_sample *);\nint n10_pre_roundtrip_terminal_read(struct n10_cpu_pm_roundtrip_sample *, unsigned int completed);\n#endif', 'roundtrip prototype')
    sample_anchor = struct_anchor
    header = _replace_once(header, sample_anchor, sample_anchor[:-2] + b'\n#ifdef CONFIG_NOTE10_CPU_PM_ROUNDTRIP\n    struct n10_cpu_pm_roundtrip_sample roundtrip;\n#endif\n};', 'roundtrip sample field')
    out[header_name] = header

    capture_name = 'kernel/power/note10_pm_pre_capture.c'
    capture = out[capture_name]
    include_anchor = b'#include <linux/note10_pm_preconditions.h>'
    capture = _replace_once(capture, include_anchor, include_anchor + b'\n#ifdef CONFIG_NOTE10_CPU_PM_ROUNDTRIP\n#include <linux/irqflags.h>\n#include <asm/sysreg.h>\n#include <asm/ptrace.h>\n#endif', 'capture includes')
    invoke_anchor = b'    s->error=n10_pre_chain(s,generation);s->completed=1;'
    invoke = (b'''    s->roundtrip.generation=generation;
    s->roundtrip.terminal_attempted=1;
    s->error=n10_pre_chain(s,generation);
#ifdef CONFIG_NOTE10_CPU_PM_ROUNDTRIP
    if (s->error) {
        s->roundtrip.terminal_stage=1;
        s->roundtrip.terminal_outer_error=s->error;
    } else {
        unsigned long roundtrip_flags;
        u64 roundtrip_daif = read_sysreg(daif);
        int roundtrip_error;
        if (roundtrip_daif & PSR_I_BIT || preempt_count() || !preemptible()) {
            roundtrip_error=-EPERM;
            s->roundtrip.terminal_stage=0;
            s->roundtrip.terminal_outer_error=roundtrip_error;
        }
        else {
            local_irq_save(roundtrip_flags);
            if (!irqs_disabled() || preempt_count()) {
                roundtrip_error=-EPERM;
                s->roundtrip.terminal_stage=0;
                s->roundtrip.terminal_outer_error=roundtrip_error;
            } else {
                s->roundtrip.caller_invoked=1;
                roundtrip_error=n10_cpu_pm_roundtrip(generation,s,&s->roundtrip);
                s->roundtrip.terminal_helper_error=roundtrip_error;
                if (roundtrip_error) {
                    if (!s->roundtrip.enter_calls && !s->roundtrip.exit_calls)
                        s->roundtrip.terminal_stage=2;
                    else if (s->roundtrip.enter_calls && s->roundtrip.enter_error)
                        s->roundtrip.terminal_stage=3;
                    else if (s->roundtrip.enter_calls && s->roundtrip.exit_calls && s->roundtrip.exit_error)
                        s->roundtrip.terminal_stage=4;
                    else s->roundtrip.terminal_stage=5;
                }
            }
            local_irq_restore(roundtrip_flags);
            if (read_sysreg(daif)!=roundtrip_daif) {
                roundtrip_error=-EIO;
                s->roundtrip.terminal_outer_error=roundtrip_error;
                if (!s->roundtrip.terminal_stage) s->roundtrip.terminal_stage=5;
            }
        }
        if (roundtrip_error && !s->error) s->error=roundtrip_error;
    }
#endif
    s->completed=1;''').replace(b'\n+', b'\n')
    capture = _replace_once(capture, invoke_anchor, invoke, 'roundtrip capture call')
    final_context_anchor = b'''    if (!n10_pre_context(generation,0,0) || !preemptible()) {
        if (!s->error)s->error=-EIO;
    }'''
    final_context = b'''    if (!n10_pre_context(generation,0,0) || !preemptible()) {
        if (!s->error)s->error=-EIO;
#ifdef CONFIG_NOTE10_CPU_PM_ROUNDTRIP
        if (!s->roundtrip.terminal_outer_error) s->roundtrip.terminal_outer_error=-EIO;
        if (!s->roundtrip.terminal_stage)
            s->roundtrip.terminal_stage=s->roundtrip.caller_invoked ? 5 : 0;
#endif
    }
#ifdef CONFIG_NOTE10_CPU_PM_ROUNDTRIP
    if (s->roundtrip.terminal_attempted) {
        if (!s->roundtrip.terminal_stage)
            s->roundtrip.terminal_stage=s->error ? (s->roundtrip.caller_invoked ? 5 : 0) : 0;
        s->roundtrip.terminal_recorded=1;
        s->roundtrip.terminal_completed=1;
    }
#endif'''
    capture = replace_unique(capture, final_context_anchor, final_context,
                             'terminal final context publication')
    terminal_read_anchor = b'''int n10_pre_gic_step(unsigned int generation, unsigned int phase, u32 ctlr, u32 pmr)'''
    terminal_reader = b'''#ifdef CONFIG_NOTE10_CPU_PM_ROUNDTRIP
int n10_pre_roundtrip_terminal_read(struct n10_cpu_pm_roundtrip_sample *out,
                                    unsigned int completed)
{
    unsigned int generation;
    if (!out || !completed || irqs_disabled()) return -EINVAL;
    generation=completed-1;
    if (!generation) generation=0xffffffffU;
    mutex_lock(&pm_mutex);
    if (n10_pre_last.generation!=generation || n10_pre_last.seen!=1 ||
        n10_pre_last.completed!=1 || n10_pre_last.roundtrip.generation!=generation ||
        n10_pre_last.roundtrip.terminal_attempted!=1 ||
        n10_pre_last.roundtrip.terminal_recorded!=1 ||
        n10_pre_last.roundtrip.terminal_completed!=1) {
        mutex_unlock(&pm_mutex);
        return -EIO;
    }
    memcpy(out,&n10_pre_last.roundtrip,sizeof(*out));
    mutex_unlock(&pm_mutex);
    if (out->terminal_stage>5) return -EIO;
    if (!out->terminal_stage && out->attempted && out->caller_invoked && out->passed &&
        !out->error && out->enter_calls==1 && out->exit_calls==1)
        return 0;
    if (((out->terminal_stage<=1) && (out->attempted || out->caller_invoked)) ||
        ((out->terminal_stage>=2) && !out->caller_invoked)) return -EIO;
    return 0;
}
#endif
'''
    capture = replace_unique(capture, terminal_read_anchor,
                             terminal_reader + terminal_read_anchor,
                             'roundtrip terminal getter')
    out[capture_name] = capture

    probe_name = 'arch/arm64/mm/note10_pm_pre_probe.c'
    probe = out[probe_name]
    terminal_anchor = b'#define N10_PRE_BUDGET 32768U'
    terminal_helper = b'''#ifdef CONFIG_NOTE10_CPU_PM_ROUNDTRIP
static const char n10_cpu_pm_terminal_marker[] __used = "N10CPT1";
static struct n10_cpu_pm_roundtrip_sample n10_pre_terminal_report;
static int n10_pre_emit(const char *, const char *, int, unsigned int *, int);
static int n10_pre_emit_terminal(unsigned int completed, unsigned int generation, int probe_error)
{
    char frame[512]; unsigned int copy,budget=0; int n,ret;
    memset(&n10_pre_terminal_report,0,sizeof(n10_pre_terminal_report));
    ret=n10_pre_roundtrip_terminal_read(&n10_pre_terminal_report,completed);
    if (ret || !n10_pre_terminal_report.terminal_recorded ||
        !n10_pre_terminal_report.terminal_completed ||
        n10_pre_terminal_report.generation!=generation) return ret ? ret : -EIO;
    n10_pre_terminal_report.terminal_probe_error=probe_error;
    if (probe_error && !n10_pre_terminal_report.terminal_stage &&
        n10_pre_terminal_report.attempted && n10_pre_terminal_report.caller_invoked)
        n10_pre_terminal_report.terminal_stage=5;
    for (copy=0;copy<2;copy++) {
        n=snprintf(frame,sizeof(frame),"id=%s copy=%u generation=%u attempted=%u recorded=%u completed=%u caller_invoked=%u stage=%u outer_error=%d helper_error=%d probe_error=%d enter_calls=%u exit_calls=%u enter_error=%d exit_error=%d",N10_RESERVE_BUILD_ID,copy,generation,n10_pre_terminal_report.attempted,n10_pre_terminal_report.terminal_recorded,n10_pre_terminal_report.terminal_completed,n10_pre_terminal_report.caller_invoked,n10_pre_terminal_report.terminal_stage,n10_pre_terminal_report.terminal_outer_error,n10_pre_terminal_report.terminal_helper_error,n10_pre_terminal_report.terminal_probe_error,n10_pre_terminal_report.enter_calls,n10_pre_terminal_report.exit_calls,n10_pre_terminal_report.enter_error,n10_pre_terminal_report.exit_error);
        ret=n10_pre_emit("N10CPT1",frame,n,&budget,1); if(ret)return ret;
    }
    return 0;
}
#endif
'''
    probe = replace_unique(probe, terminal_anchor,
                           terminal_helper + terminal_anchor,
                           'roundtrip terminal producer')
    row_anchor = b'            for (i=0;i<3;i++) {'
    # Emit the normalized paired-call result once in each existing bounded copy.
    report_anchor = b'            for (i=0;i<3;i++) {'
    report = (b'''#ifdef CONFIG_NOTE10_CPU_PM_ROUNDTRIP
            PRE_ROW("N10CPR1","id=%s copy=%u generation=%u attempted=%u roster=%u roster_valid=%u pre=%u post=%u enter_calls=%u exit_calls=%u enter_ok=%u exit_ok=%u daif=%u timer=%u gic=%u ehld_before=%u ehld_after=%u context=%u passed=%u error=%d enter_error=%d exit_error=%d",N10_RESERVE_BUILD_ID,copy,generation,n10_pre_report.roundtrip.attempted,n10_pre_report.roundtrip.roster_count,n10_pre_report.roundtrip.roster_valid,n10_pre_report.roundtrip.pre_snapshot_valid,n10_pre_report.roundtrip.post_snapshot_valid,n10_pre_report.roundtrip.enter_calls,n10_pre_report.roundtrip.exit_calls,n10_pre_report.roundtrip.enter_succeeded,n10_pre_report.roundtrip.exit_succeeded,n10_pre_report.roundtrip.daif_stable,n10_pre_report.roundtrip.timer_stable,n10_pre_report.roundtrip.gic_stable,n10_pre_report.roundtrip.ehld_before,n10_pre_report.roundtrip.ehld_after,n10_pre_report.roundtrip.context_stable,n10_pre_report.roundtrip.passed,n10_pre_report.roundtrip.error,n10_pre_report.roundtrip.enter_error,n10_pre_report.roundtrip.exit_error);
#endif
            for (i=0;i<3;i++) {''').replace(b'\n+', b'\n')
    probe = _replace_once(probe, report_anchor, report, 'roundtrip producer row')
    report_end_anchor=b'''    ret=n10_pre_read(&n10_pre_report,completed);
    if (!ret)ret=n10_pre_gic_read(&n10_pre_gic_report,completed);
    if (!ret && outer_error)ret=outer_error;
    if (!ret)ret=n10_pre_emit_all(0,0,generation);
    if (ret) { (void)n10_pre_emit_all(1,ret,generation);return ret; }
    return n10_pre_emit_all(1,0,generation);
}'''
    report_end = b'''    ret=n10_pre_read(&n10_pre_report,completed);
    if (!ret)ret=n10_pre_gic_read(&n10_pre_gic_report,completed);
    if (!ret && outer_error)ret=outer_error;
    if (!ret)ret=n10_pre_emit_all(0,0,generation);
    if (ret) {
#ifdef CONFIG_NOTE10_CPU_PM_ROUNDTRIP
            (void)n10_pre_emit_terminal(completed,generation,ret);
#endif
        (void)n10_pre_emit_all(1,ret,generation);return ret;
    }
    return n10_pre_emit_all(1,0,generation);
}'''
    probe = replace_unique(probe, report_end_anchor, report_end,
                           'roundtrip terminal error reporting')
    out[probe_name] = probe

    config = out[KCONFIG]
    if b'config NOTE10_CPU_PM_ROUNDTRIP' in config or BLOCK.strip() in config:
        raise ValueError('CPU PM roundtrip Kconfig symbol already exists')
    out[KCONFIG] = config + BLOCK
    return out


def validate_transform(baseline, prepared):
    if not isinstance(baseline, dict) or set(baseline) != set(TARGETS):
        raise ValueError('exact CPU PM roundtrip transform inputs required')
    if transform(baseline) != prepared:
        raise ValueError('prepared CPU PM roundtrip source differs from production transform')
    return True


def validate_map(source, baseline_map):
    source = Path(source)
    if not isinstance(baseline_map, dict) or len(baseline_map) != 78:
        raise ValueError('exact v48 78-source map required')
    for name, digest in baseline_map.items():
        rel = Path(name)
        path = source / rel
        if rel.is_absolute() or rel.as_posix() != name or '..' in rel.parts or path.is_symlink() or not path.is_file() or not re.fullmatch(r'[0-9a-f]{64}', digest):
            raise ValueError('invalid v48 source map entry')
    actual = {name: sha((source / name).read_bytes()) for name in baseline_map}
    if actual != baseline_map:
        raise ValueError('actual v48 source differs')
    return source


def prepare(source, enabled, baseline_map):
    if enabled is not True:
        raise ValueError('v49 preparation requires explicit opt-in')
    source = validate_map(source, baseline_map)
    old = {name: (source / name).read_bytes() for name in TARGETS}
    transformed = transform(old)
    if set(transformed) != set(TARGETS):
        raise ValueError('v49 transform target set differs')
    # All source and Kconfig checks have completed before the first write.
    for name in TARGETS:
        (source / name).write_bytes(transformed[name])
    return {
        'cpu_pm_roundtrip': True,
        'cpu_pm_roundtrip_version': SCHEMA_VERSION,
        'cpu_pm_roundtrip_baseline_sha256': {name: baseline_map[name] for name in TARGETS},
        'cpu_pm_roundtrip_prepared_sha256': {name: sha(transformed[name]) for name in TARGETS},
    }


def snapshot(source, output, baseline_map):
    source, output = Path(source), Path(output)
    if output.exists() or output.is_symlink():
        raise ValueError('roundtrip snapshot destination exists or unsafe')
    if not isinstance(baseline_map, dict) or len(baseline_map) != 78:
        raise ValueError('exact v48 78-source map required')
    expected = set(baseline_map)
    for name in expected:
        rel = Path(name)
        path = source / rel
        if rel.is_absolute() or rel.as_posix() != name or '..' in rel.parts or path.is_symlink() or not path.is_file():
            raise ValueError('unsafe source snapshot path')
    output.mkdir(parents=True)
    for name in sorted(expected):
        dst = output / name
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source / name, dst)
    if {p.relative_to(output).as_posix() for p in output.rglob('*') if p.is_file()} != expected:
        raise ValueError('v49 snapshot file set differs')
    actual = {name: sha((output / name).read_bytes()) for name in sorted(expected)}
    changed = {name for name in expected if actual[name] != baseline_map[name]}
    if changed != set(TARGETS):
        raise ValueError('v49 snapshot must change exactly the authorized five sources')
    return actual
