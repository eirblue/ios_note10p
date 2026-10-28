/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef NOTE10_PM_CALLBACKS_H
#define NOTE10_PM_CALLBACKS_H
#define N10_CB_PHASES 3
#define N10_CB_FAMILIES 4
#define N10_CB_MAX 64
#define N10_CB_NAME 97
#define N10_CB_SYMBOLS 128
struct n10_cb_entry {
    char name[N10_CB_NAME];
    unsigned long callback[5];
    unsigned int symbol[5];
    unsigned long mask;
    unsigned int a, b, c, d;
    int x, y, priority;
};
struct n10_cb_family {
    unsigned int count, attempted;
    int error;
    struct n10_cb_entry entry[N10_CB_MAX];
};
struct n10_cb_phase {
    unsigned int seen, generation, phase;
    int error;
    struct n10_cb_family family[N10_CB_FAMILIES];
};
int n10_cb_cpu_pm(struct n10_cb_family *out);
int n10_cb_irq(struct n10_cb_family *out);
int n10_cb_clocksource(struct n10_cb_family *out);
int n10_cb_clockevent(struct n10_cb_family *out);
int n10_cb_capture(unsigned int phase, unsigned int generation);
int n10_cb_read(struct n10_cb_phase *out, unsigned int completed, char symbols[N10_CB_SYMBOLS][N10_CB_NAME], unsigned int *count, int *bad);
int n10_cb_name(char *dst, const char *src);
#endif
