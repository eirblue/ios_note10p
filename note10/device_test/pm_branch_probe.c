/* SPDX-License-Identifier: GPL-2.0-only */
/* Worker-only reporting, derives GIC lane masks from existing snapshots. */
#include <linux/note10_pm_branch.h>
#include <linux/note10_pm_preconditions.h>
#include <linux/irqchip/arm-gic.h>
#define N10_BRA_BUDGET 24576U
static struct n10_branch_sample n10_bra_report;
static struct n10_precond_gic_sample n10_bra_gic;
static u32 n10_bra_lanes(const struct n10_precond_gic_row *g)
{
    u32 mask=0;unsigned int i,j;
    for(i=0;i<8;i++)for(j=0;j<4;j++)
        if(((g->priority[i]>>(8*j))&255U)!=((GICD_INT_DEF_PRI_X4>>(8*j))&255U))mask|=1U<<(4*i+j);
    return mask;
}
static int n10_bra_emit(const char *tag,const char *frame,int n,unsigned int *budget,int emit)
{
    unsigned int bytes;if(n<0 || n>=512)return -E2BIG;
    bytes=n+strlen(tag)+96;if(bytes>N10_BRA_BUDGET || *budget>N10_BRA_BUDGET-bytes)return -E2BIG;
    *budget+=bytes;if(emit)pr_info("%s %s checksum=%08x\n",tag,frame,n10_frame_checksum(frame,n));return 0;
}
static int n10_bra_emit_all(int emit,int status,unsigned int generation)
{
    char frame[512];unsigned int copy,i,budget=0;int n,ret;
#define BRA_ROW(tag,...) do {n=snprintf(frame,sizeof(frame),__VA_ARGS__);ret=n10_bra_emit(tag,frame,n,&budget,emit);if(ret)return ret;} while(0)
    for(copy=0;copy<2;copy++) {
        if(!status) {
            for(i=0;i<n10_bra_report.count;i++) {
                struct n10_branch_row *r=&n10_bra_report.row[i];
                BRA_ROW("N10BRAR1","id=%s copy=%u generation=%u index=%u count=%u kind=%u num=%u supported=%u used=%u nonnull=%u match=%u reset=%u start=%u stop=%u",N10_RESERVE_BUILD_ID,copy,generation,i,n10_bra_report.count,r->kind,r->num,r->supported,r->used,r->nonnull,r->match,r->reset,r->start,r->stop);
            }
            for(i=0;i<3;i++) {
                struct n10_precond_gic_row *g=&n10_bra_gic.phase[i];u32 lanes=n10_bra_lanes(g);
                BRA_ROW("N10BRAG1","id=%s copy=%u generation=%u phase=%u lanes=%u enabled=%u active=%u matches=%u",N10_RESERVE_BUILD_ID,copy,generation,i,lanes,lanes&g->enable,lanes&g->active,g->restore_matches);
            }
        }
        BRA_ROW("N10BRAQ1","id=%s copy=%u generation=%u status=%d count=%u complete=%u gic_complete=%u",N10_RESERVE_BUILD_ID,copy,generation,status,status?0:n10_bra_report.count,status?0:n10_bra_report.completed,status?0:n10_bra_gic.completed);
    }
#undef BRA_ROW
    return 0;
}
static int n10_report_pm_branch(unsigned int completed,int outer_error)
{
    unsigned int generation=completed==1?0xffffffffU:completed-1;int ret;
    memset(&n10_bra_report,0,sizeof(n10_bra_report));memset(&n10_bra_gic,0,sizeof(n10_bra_gic));
    ret=n10_branch_read(&n10_bra_report,completed);if(!ret)ret=n10_pre_gic_read(&n10_bra_gic,completed);
    if(!ret && outer_error)ret=outer_error;if(!ret)ret=n10_bra_emit_all(0,0,generation);
    if(ret){(void)n10_bra_emit_all(1,ret,generation);return ret;}return n10_bra_emit_all(1,0,generation);
}
