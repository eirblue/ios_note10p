/* SPDX-License-Identifier: GPL-2.0-only */
/* Included in pinned drivers/base/syscore.c; never execute registered ops. */
#include <linux/note10_pm_edge_syscore.h>
#include <linux/kallsyms.h>
#include <linux/cpu.h>
#include <linux/interrupt.h>
#include <linux/kernel.h>
static struct n10_edge_syscore_sample n10_edge_syscore_samples[2];

static int n10_edge_syscore_symbol(unsigned long addr, char *out)
{
    char namebuf[KSYM_NAME_LEN], *modname = NULL;
    const char *name;
    unsigned long size = 0, offset = ~0UL;
    unsigned int i;
    if (!core_kernel_text(addr)) return -EINVAL;
    name = kallsyms_lookup(addr, &size, &offset, &modname, namebuf);
    if (!name || modname || offset || !size) return -EINVAL;
    for (i = 0; i < N10_EDGE_SYMBOL_MAX; ++i) {
        unsigned char c = name[i];
        if (!c) { if (!i) return -EINVAL; out[i] = 0; return 0; }
        if (c < 33 || c > 126 || c == '=') return -EINVAL;
        out[i] = c;
    }
    return -E2BIG;
}

void n10_edge_syscore_capture(unsigned int phase, unsigned int generation)
{
    struct n10_edge_syscore_sample *s;
    struct syscore_ops *ops;
    unsigned int slot;
    if (phase != 0 && phase != 3) return;
    slot = phase == 0 ? 0 : 1;
    if (!slot && n10_edge_syscore_samples[0].seen && n10_edge_syscore_samples[0].generation != generation) {
        unsigned int delta = generation - n10_edge_syscore_samples[0].generation;
        if (!generation || !delta || delta >= 0x80000000U) {
            n10_edge_syscore_samples[0].error = 9; return;
        }
        memset(n10_edge_syscore_samples, 0, sizeof(n10_edge_syscore_samples));
    }
    s = &n10_edge_syscore_samples[slot];
    if (s->seen++) { s->error = 1; return; }
    s->generation = generation; s->phase = phase;
    if (!generation || (slot && (n10_edge_syscore_samples[0].seen != 1 ||
        n10_edge_syscore_samples[0].generation != generation ||
        n10_edge_syscore_samples[0].error))) { s->error = 2; return; }
    if (irqs_disabled() || num_online_cpus() != 8 ||
        cpumask_bits(cpu_online_mask)[0] != 0xffUL) { s->error = 3; return; }
    if (!mutex_trylock(&syscore_ops_lock)) { s->error = 4; return; }
    list_for_each_entry(ops, &syscore_ops_list, node) {
        struct n10_edge_syscore_entry *e;
        unsigned long callbacks[3];
        unsigned int i;
        if (s->count == N10_EDGE_SYSCORE_MAX) { s->error = 5; break; }
        e = &s->entries[s->count++];
        callbacks[0] = (unsigned long)ops->suspend;
        callbacks[1] = (unsigned long)ops->resume;
        callbacks[2] = (unsigned long)ops->shutdown;
        for (i = 0; i < 3; ++i) {
            if (!callbacks[i]) continue;
            e->mask |= 1U << i;
            if (n10_edge_syscore_symbol(callbacks[i], e->names[i])) {
                s->error = 6; break;
            }
        }
        if (s->error) break;
    }
    if (!s->count) s->error = 7;
    mutex_unlock(&syscore_ops_lock);
    if (irqs_disabled() || num_online_cpus() != 8 ||
        cpumask_bits(cpu_online_mask)[0] != 0xffUL) s->error = 8;
}

int n10_edge_syscore_read(struct n10_edge_syscore_sample *out, unsigned int completed)
{
    unsigned int next, i;
    if (!out || !completed) return -EINVAL;
    memcpy(out, n10_edge_syscore_samples, sizeof(n10_edge_syscore_samples));
    next = out[0].generation + 1; if (!next) next = 1;
    if (!out[0].generation || next != completed) return -EIO;
    for (i = 0; i < 2; ++i)
        if (out[i].seen != 1 || out[i].error || out[i].phase != i * 3 ||
            out[i].generation != out[0].generation || !out[i].count ||
            out[i].count > N10_EDGE_SYSCORE_MAX) return -EIO;
    if (out[0].count != out[1].count ||
        memcmp(out[0].entries, out[1].entries,
               out[0].count * sizeof(out[0].entries[0]))) return -EIO;
    return 0;
}
