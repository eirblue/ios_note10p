/* SPDX-License-Identifier: GPL-2.0-only */
/* Restored worker emits a preflighted, bounded, duplicated inventory. */
#include <linux/note10_pm_callbacks.h>
#define N10_CB_BUDGET 131072U
#define N10_CB_OVERHEAD 96U
static struct n10_cb_phase n10_cb_report[3];
static char n10_cb_report_symbols[N10_CB_SYMBOLS][N10_CB_NAME];
static unsigned int n10_cb_report_symbol_count;
static int n10_cb_report_bad;
static int n10_cb_emit(const char *tag, char *frame, int length, unsigned int *budget, int emit)
{
    /* The 96-byte overhead includes tag, checksum, spaces, newline and printk metadata. */
    unsigned int bytes;
    if (length < 0 || length >= 512) return -E2BIG;
    bytes = length + strlen(tag) + N10_CB_OVERHEAD;
    if (bytes > N10_CB_BUDGET || *budget > N10_CB_BUDGET - bytes) return -E2BIG;
    *budget += bytes;
    if (emit) pr_info("%s %s checksum=%08x\n", tag, frame, n10_frame_checksum(frame, length));
    return 0;
}
static int n10_cb_emit_all(int emit, int status, unsigned int generation)
{
    char frame[512]; unsigned int copy, p, f, i, budget = 0; int n, ret;
#define ROW(tag, ...) do { n = snprintf(frame, sizeof(frame), __VA_ARGS__); ret = n10_cb_emit(tag, frame, n, &budget, emit); if (ret) return ret; } while (0)
    for (copy=0; copy<2; ++copy) {
        if (status) for (p=0; p<3; ++p) for (f=0; f<4; ++f) {
            struct n10_cb_family *family=&n10_cb_report[p].family[f];
            ROW("N10CBR1", "id=%s copy=%u generation=%u phase=%u family=%u attempted=%u error=%d count=%u", N10_RESERVE_BUILD_ID, copy, generation, p, f, family->attempted, family->error, family->count);
        }
        if (!status) {
            for (i=0; i<n10_cb_report_symbol_count; ++i)
                ROW("N10CBS1", "id=%s copy=%u generation=%u index=%u count=%u name=%s", N10_RESERVE_BUILD_ID, copy, generation, i+1, n10_cb_report_symbol_count, n10_cb_report_symbols[i]);
            for (p=0; p<3; ++p) for (f=0; f<4; ++f) {
                struct n10_cb_family *family = &n10_cb_report[p].family[f];
                for (i=0; i<(family->count ? family->count : 1); ++i) {
                    struct n10_cb_entry empty = {0};
                    struct n10_cb_entry *e = family->count ? &family->entry[i] : &empty;
                    ROW("N10CBR1", "id=%s copy=%u generation=%u phase=%u family=%u index=%u count=%u name=%s a=%u b=%u c=%u d=%u mask=%lx x=%d y=%d priority=%d s0=%u s1=%u s2=%u s3=%u s4=%u", N10_RESERVE_BUILD_ID, copy, generation,p,f,i,family->count,e->name[0] ? e->name : "-",e->a,e->b,e->c,e->d,e->mask,e->x,e->y,e->priority,e->symbol[0],e->symbol[1],e->symbol[2],e->symbol[3],e->symbol[4]);
                }
            }
        }
        ROW("N10CBQ1", "id=%s copy=%u generation=%u status=%d symbols=%u seen0=%u seen1=%u seen2=%u error0=%d error1=%d error2=%d bad=%d", N10_RESERVE_BUILD_ID, copy, generation, status, status ? 0 : n10_cb_report_symbol_count, n10_cb_report[0].seen, n10_cb_report[1].seen, n10_cb_report[2].seen, n10_cb_report[0].error, n10_cb_report[1].error, n10_cb_report[2].error, n10_cb_report_bad);
    }
#undef ROW
    return 0;
}
static int n10_report_pm_callbacks(unsigned int completed, int outer_error)
{
    unsigned int generation = completed == 1 ? 0xffffffffU : completed - 1;
    int ret = n10_cb_read(n10_cb_report, completed, n10_cb_report_symbols, &n10_cb_report_symbol_count, &n10_cb_report_bad);
    if (n10_cb_report[0].generation != generation) {
        memset(n10_cb_report, 0, sizeof(n10_cb_report));
        memset(n10_cb_report_symbols, 0, sizeof(n10_cb_report_symbols));
        n10_cb_report_symbol_count = 0;
        if (!ret) ret = -EIO;
    }
    if (!ret && outer_error) ret = outer_error;
    if (!ret) ret = n10_cb_emit_all(0, 0, generation);
    if (ret) { (void)n10_cb_emit_all(1, ret, generation); return ret; }
    return n10_cb_emit_all(1, 0, generation);
}
