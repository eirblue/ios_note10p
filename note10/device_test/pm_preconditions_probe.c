/* SPDX-License-Identifier: GPL-2.0-only */
/* Bounded two-copy producer, called only after CPU and IRQ restoration. */
#include <linux/note10_pm_preconditions.h>
#define N10_PRE_BUDGET 32768U
static struct n10_precond_sample n10_pre_report;
static struct n10_precond_gic_sample n10_pre_gic_report;
static int n10_pre_emit(const char *tag, const char *frame, int n, unsigned int *budget, int emit)
{
    unsigned int bytes;
    if (n<0 || n>=512)return -E2BIG;
    bytes=n+strlen(tag)+96;
    if (bytes>N10_PRE_BUDGET || *budget>N10_PRE_BUDGET-bytes)return -E2BIG;
    *budget+=bytes;
    if (emit)pr_info("%s %s checksum=%08x\n",tag,frame,n10_frame_checksum(frame,n));
    return 0;
}
static int n10_pre_emit_all(int emit,int status,unsigned int generation)
{
    char frame[512];unsigned int copy,i,budget=0;int n,ret;
#define PRE_ROW(tag,...) do { n=snprintf(frame,sizeof(frame),__VA_ARGS__);ret=n10_pre_emit(tag,frame,n,&budget,emit);if(ret)return ret; } while (0)
    for (copy=0;copy<2;copy++) {
        if (!status) {
            for (i=0;i<n10_pre_report.count;i++) {
                struct n10_precond_row *r=&n10_pre_report.row[i];
                PRE_ROW("N10PRR1","id=%s copy=%u generation=%u index=%u count=%u kind=%u priority=%d valid=%u a=%lld b=%lld c=%lld d=%lld e=%lld f=%lld g=%lld h=%lld",N10_RESERVE_BUILD_ID,copy,generation,i,n10_pre_report.count,r->kind,r->priority,r->valid,r->value[0],r->value[1],r->value[2],r->value[3],r->value[4],r->value[5],r->value[6],r->value[7]);
            }
            for (i=0;i<3;i++) {
                struct n10_precond_gic_row *r=&n10_pre_gic_report.phase[i];
                PRE_ROW("N10PRG1","id=%s copy=%u generation=%u phase=%u enable=%u active=%u config0=%u config1=%u p0=%u p1=%u p2=%u p3=%u p4=%u p5=%u p6=%u p7=%u matches=%u",N10_RESERVE_BUILD_ID,copy,generation,i,r->enable,r->active,r->config[0],r->config[1],r->priority[0],r->priority[1],r->priority[2],r->priority[3],r->priority[4],r->priority[5],r->priority[6],r->priority[7],r->restore_matches);
            }
        }
        PRE_ROW("N10PRQ1","id=%s copy=%u generation=%u status=%d count=%u complete=%u gic_complete=%u",N10_RESERVE_BUILD_ID,copy,generation,status,status?0:n10_pre_report.count,status?0:n10_pre_report.completed,status?0:n10_pre_gic_report.completed);
    }
#undef PRE_ROW
    return 0;
}
static int n10_report_pm_preconditions(unsigned int completed,int outer_error)
{
    unsigned int generation=completed==1?0xffffffffU:completed-1;int ret;
    memset(&n10_pre_report,0,sizeof(n10_pre_report));memset(&n10_pre_gic_report,0,sizeof(n10_pre_gic_report));
    ret=n10_pre_read(&n10_pre_report,completed);
    if (!ret)ret=n10_pre_gic_read(&n10_pre_gic_report,completed);
    if (!ret && outer_error)ret=outer_error;
    if (!ret)ret=n10_pre_emit_all(0,0,generation);
    if (ret) { (void)n10_pre_emit_all(1,ret,generation);return ret; }
    return n10_pre_emit_all(1,0,generation);
}
