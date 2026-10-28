/* SPDX-License-Identifier: GPL-2.0-only */
#include <linux/note10_pmu_control_audit.h>
#define N10_PCT_BUDGET 4096U
static struct n10_ctl_sample n10_pct_report;
static int n10_pct_emit(const char *tag,const char *frame,int n,unsigned int *budget,int emit)
{
    unsigned int bytes;if(n<0 || n>=512)return -E2BIG;
    bytes=n+strlen(tag)+96;if(bytes>N10_PCT_BUDGET || *budget>N10_PCT_BUDGET-bytes)return -E2BIG;
    *budget+=bytes;if(emit)pr_info("%s %s checksum=%08x\n",tag,frame,n10_frame_checksum(frame,n));return 0;
}
static int n10_pct_emit_all(int emit,int status,unsigned int generation)
{
    char frame[512];unsigned int copy,budget=0;int n,ret;
#define PCT_ROW(tag,...) do {n=snprintf(frame,sizeof(frame),__VA_ARGS__);ret=n10_pct_emit(tag,frame,n,&budget,emit);if(ret)return ret;} while(0)
    for(copy=0;copy<2;copy++) {
        if(!status) {
            struct n10_ctl_row *r=&n10_pct_report.row;
            PCT_ROW("N10PCTR1","id=%s copy=%u generation=%u index=%u chain_count=%u kind=%u num=%u used_sw=%u visible_phys=%u used_phys=%u current_el=%u model_match=%u variant=%u revision=%u pmuver=%u fgt=%u pmcr=%u cntenset=%u intenset=%u",N10_RESERVE_BUILD_ID,copy,generation,r->index,r->chain_count,r->kind,r->num,r->used_sw,r->visible_phys,r->used_phys,r->current_el,r->model_match,r->variant,r->revision,r->pmuver,r->fgt,r->pmcr,r->cntenset,r->intenset);
        }
        PCT_ROW("N10PCTQ1","id=%s copy=%u generation=%u status=%d row_count=%u complete=%u",N10_RESERVE_BUILD_ID,copy,generation,status,status?0:1,status?0:n10_pct_report.completed);
    }
#undef PCT_ROW
    return 0;
}
static int n10_report_pmu_control(unsigned int completed,int outer_error)
{
    unsigned int generation=completed==1?0xffffffffU:completed-1;int ret;
    memset(&n10_pct_report,0,sizeof(n10_pct_report));
    ret=n10_ctl_read(&n10_pct_report,completed);
    if(!ret && outer_error)ret=outer_error;if(!ret)ret=n10_pct_emit_all(0,0,generation);
    if(ret){(void)n10_pct_emit_all(1,ret,generation);return ret;}return n10_pct_emit_all(1,0,generation);
}
