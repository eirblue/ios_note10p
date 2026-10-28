/* SPDX-License-Identifier: GPL-2.0-only */
#include <linux/note10_pmu_state_audit.h>
#define N10_STA_BUDGET 24576U
static struct n10_state_sample n10_sta_report;
static int n10_sta_emit(const char *tag,const char *frame,int n,unsigned int *budget,int emit)
{
    unsigned int bytes;if(n<0 || n>=512)return -E2BIG;
    bytes=n+strlen(tag)+96;if(bytes>N10_STA_BUDGET || *budget>N10_STA_BUDGET-bytes)return -E2BIG;
    *budget+=bytes;if(emit)pr_info("%s %s checksum=%08x\n",tag,frame,n10_frame_checksum(frame,n));return 0;
}
static int n10_sta_emit_all(int emit,int status,unsigned int generation)
{
    char frame[512];unsigned int copy,i,budget=0;int n,ret;
#define STA_ROW(tag,...) do {n=snprintf(frame,sizeof(frame),__VA_ARGS__);ret=n10_sta_emit(tag,frame,n,&budget,emit);if(ret)return ret;} while(0)
    for(copy=0;copy<2;copy++) {
        if(!status) for(i=0;i<n10_sta_report.count;i++) {
            struct n10_state_row *r=&n10_sta_report.row[i];
            STA_ROW("N10STAR1","id=%s copy=%u generation=%u index=%u count=%u kind=%u num=%u supported=%u used=%u present=%u owned=%u observed=%u running=%u stopped=%u uptodate=%u abnormal=%u affinity0=%u unbound=%u other=%u oncpu0=%u active=%u",N10_RESERVE_BUILD_ID,copy,generation,i,n10_sta_report.count,r->kind,r->num,r->supported,r->used,r->present,r->owned,r->observed,r->running,r->stopped,r->uptodate,r->abnormal,r->affinity0,r->unbound,r->other,r->oncpu0,r->active);
        }
        STA_ROW("N10STAQ1","id=%s copy=%u generation=%u status=%d count=%u complete=%u",N10_RESERVE_BUILD_ID,copy,generation,status,status?0:n10_sta_report.count,status?0:n10_sta_report.completed);
    }
#undef STA_ROW
    return 0;
}
static int n10_report_pmu_state(unsigned int completed,int outer_error)
{
    unsigned int generation=completed==1?0xffffffffU:completed-1;int ret;
    memset(&n10_sta_report,0,sizeof(n10_sta_report));
    ret=n10_state_read(&n10_sta_report,completed);
    if(!ret && outer_error)ret=outer_error;if(!ret)ret=n10_sta_emit_all(0,0,generation);
    if(ret){(void)n10_sta_emit_all(1,ret,generation);return ret;}return n10_sta_emit_all(1,0,generation);
}
