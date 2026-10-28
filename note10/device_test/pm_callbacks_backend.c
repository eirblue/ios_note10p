/* SPDX-License-Identifier: GPL-2.0-only */
/* Included in suspend.c, where the actual owner and active generation live. */
#include <linux/note10_pm_callbacks.h>
#include <linux/cpu.h>
#include <linux/kallsyms.h>
static struct n10_cb_phase n10_cb_phases[N10_CB_PHASES];
static char n10_cb_symbols[N10_CB_SYMBOLS][N10_CB_NAME];
static unsigned long n10_cb_addresses[N10_CB_SYMBOLS];
static unsigned int n10_cb_symbol_count;
static int n10_cb_bad;
static int n10_cb_reject(int error)
{
    if (!n10_cb_bad) n10_cb_bad = error;
    return error;
}
int n10_cb_name(char *dst, const char *src)
{
    unsigned int i;
    if (!src) return -EINVAL;
    for (i = 0; i < N10_CB_NAME; ++i) {
        unsigned char c = src[i];
        if (!c) { if (!i || (i == 1 && dst[0] == '-')) return -EINVAL; dst[i] = 0; return 0; }
        if (i == N10_CB_NAME - 1 || c < 33 || c > 126 || c == '=' || c == ',') return -EINVAL;
        dst[i] = c;
    }
    return -E2BIG;
}
static int n10_cb_symbol(unsigned long address, unsigned int *id)
{
    char buf[KSYM_NAME_LEN], name[N10_CB_NAME], *module = NULL;
    const char *found; unsigned long size = 0, offset = ~0UL;
    unsigned int i;
    if (!address) { *id = 0; return 0; }
    if (!core_kernel_text(address)) return -EINVAL;
    found = kallsyms_lookup(address, &size, &offset, &module, buf);
    if (!found || module || offset || !size || n10_cb_name(name, found)) return -EINVAL;
    for (i = 0; i < n10_cb_symbol_count; ++i)
        if (address == n10_cb_addresses[i]) { *id = i + 1; return 0; }
    if (n10_cb_symbol_count == N10_CB_SYMBOLS) return -E2BIG;
    n10_cb_addresses[n10_cb_symbol_count] = address;
    strcpy(n10_cb_symbols[n10_cb_symbol_count], name);
    *id = ++n10_cb_symbol_count;
    return 0;
}
int n10_cb_capture(unsigned int phase, unsigned int generation)
{
    struct n10_cb_phase *p; unsigned int f, i, c, mask;
    int ret = 0;
    if (!n10_pm_active || n10_pm_owner != current || !generation ||
        n10_pm_active->pm_called != 1 || n10_pm_active->qgeneration != generation || n10_pm_active->qphase != N10_Q_PM_ENTERED || phase >= 3)
        return n10_cb_reject(-EPERM);
    mask = phase == 1 ? 1 : 255;
    if (irqs_disabled() || !preemptible() || num_online_cpus() != (phase == 1 ? 1 : 8) ||
        cpumask_bits(cpu_online_mask)[0] != mask || (phase == 1 && (raw_smp_processor_id() != 0 || !n10_pm_noirq_ready(PM_SUSPEND_MEM))))
        return n10_cb_reject(-EINVAL);
    if (phase == 0 && n10_cb_phases[0].seen && n10_cb_phases[0].generation != generation) {
        unsigned int delta = generation - n10_cb_phases[0].generation;
        if (!delta || delta >= 0x80000000U) return n10_cb_reject(-EPERM);
        memset(n10_cb_phases, 0, sizeof(n10_cb_phases));
        memset(n10_cb_symbols, 0, sizeof(n10_cb_symbols)); memset(n10_cb_addresses, 0, sizeof(n10_cb_addresses)); n10_cb_symbol_count = 0; n10_cb_bad = 0;
    }
    p = &n10_cb_phases[phase];
    if (p->seen) return n10_cb_reject(-EIO);
    if (phase && (n10_cb_phases[phase-1].seen != 1 ||
        n10_cb_phases[phase-1].generation != generation || n10_cb_phases[phase-1].error || n10_cb_bad)) return n10_cb_reject(-EIO);
    p->seen = 1; p->phase = phase; p->generation = generation;
    p->family[0].attempted = 1; ret = n10_cb_cpu_pm(&p->family[0]); p->family[0].error = ret;
    if (!ret) { p->family[1].attempted = 1; ret = n10_cb_irq(&p->family[1]); p->family[1].error = ret; }
    if (!ret) { p->family[2].attempted = 1; ret = n10_cb_clocksource(&p->family[2]); p->family[2].error = ret; }
    if (!ret) { p->family[3].attempted = 1; ret = n10_cb_clockevent(&p->family[3]); p->family[3].error = ret; }
    if (!ret) for (f=0; f<N10_CB_FAMILIES && !ret; ++f)
        for (i=0; i<p->family[f].count && !ret; ++i)
            for (c=0; c<5 && !ret; ++c)
                ret = n10_cb_symbol(p->family[f].entry[i].callback[c], &p->family[f].entry[i].symbol[c]);
    if (!ret && (irqs_disabled() || !preemptible() || num_online_cpus() != (phase == 1 ? 1 : 8) || cpumask_bits(cpu_online_mask)[0] != mask || (phase == 1 && raw_smp_processor_id() != 0))) ret = -EIO;
    p->error = ret;
    if (ret) n10_cb_reject(ret);
    return ret;
}
int n10_cb_read(struct n10_cb_phase *out, unsigned int completed, char symbols[N10_CB_SYMBOLS][N10_CB_NAME], unsigned int *count, int *bad)
{
    unsigned int i, next;
    if (!out || !symbols || !count || !bad || !completed || irqs_disabled()) return -EINVAL;
    mutex_lock(&pm_mutex); memcpy(out, n10_cb_phases, sizeof(n10_cb_phases)); memcpy(symbols, n10_cb_symbols, sizeof(n10_cb_symbols)); *count = n10_cb_symbol_count; *bad = n10_cb_bad; mutex_unlock(&pm_mutex);
    next = out[0].generation + 1; if (!next) next = 1;
    if (*bad || !out[0].generation || next != completed) return -EIO;
    for (i=0; i<3; ++i) {
        unsigned int family;
        if (out[i].seen != 1 || out[i].phase != i || out[i].generation != out[0].generation || out[i].error) return -EIO;
        for (family=0; family<4; ++family)
            if (out[i].family[family].attempted != 1 || out[i].family[family].error) return -EIO;
    }
    return 0;
}

