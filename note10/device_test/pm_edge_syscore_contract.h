/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef NOTE10_PM_EDGE_SYSCORE_H
#define NOTE10_PM_EDGE_SYSCORE_H
#define N10_EDGE_SYSCORE_MAX 64
#define N10_EDGE_SYMBOL_MAX 64
struct n10_edge_syscore_entry {
    unsigned int mask;
    char names[3][N10_EDGE_SYMBOL_MAX];
};
struct n10_edge_syscore_sample {
    unsigned int generation, phase, seen, error, count;
    struct n10_edge_syscore_entry entries[N10_EDGE_SYSCORE_MAX];
};
void n10_edge_syscore_capture(unsigned int phase, unsigned int generation);
int n10_edge_syscore_read(struct n10_edge_syscore_sample *out, unsigned int completed);
#endif
