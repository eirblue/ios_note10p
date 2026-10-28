/* SPDX-License-Identifier: GPL-2.0-only */
#include <linux/note10_rcu_context_audit.h>
#define N10_RCU_BUDGET 4096U
static struct n10_rcu_sample n10_rcu_report;
static int n10_rcu_emit(const char *tag,const char *frame,int n,unsigned int *budget,int emit)
{
    unsigned int bytes;if(n<0 || n>=512)return -E2BIG;
    bytes=n+strlen(tag)+96;if(bytes>N10_RCU_BUDGET || *budget>N10_RCU_BUDGET-bytes)return -E2BIG;
    *budget+=bytes;if(emit)pr_info("%s %s checksum=%08x\n",tag,frame,n10_frame_checksum(frame,n));return 0;
}
static int n10_rcu_emit_all(int emit,int status,unsigned int generation)
{
    char frame[512];unsigned int copy,budget=0;int n,ret;
#define RCU_ROW(tag,...) do {n=snprintf(frame,sizeof(frame),__VA_ARGS__);ret=n10_rcu_emit(tag,frame,n,&budget,emit);if(ret)return ret;} while(0)
    for(copy=0;copy<2;copy++) {
        if(!status) {
            struct n10_rcu_row *r=&n10_rcu_report.row;
            RCU_ROW("N10RCM1","id=%s copy=%u generation=%u chain_count=%u watching=%u nesting_class=%u positive_headroom_two=%u nmi_nonzero=%u task_nesting_nonzero=%u task_special_nonzero=%u irq_enter_disabled=%u",N10_RESERVE_BUILD_ID,copy,generation,r->chain_count,r->watching,r->nesting_class,r->positive_headroom_two,r->nmi_nonzero,r->task_nesting_nonzero,r->task_special_nonzero,r->irq_enter_disabled);
        }
        RCU_ROW("N10RCQ1","id=%s copy=%u generation=%u status=%d row_count=%u complete=%u",N10_RESERVE_BUILD_ID,copy,generation,status,status?0:1,status?0:n10_rcu_report.completed);
    }
#undef RCU_ROW
    return 0;
}
static int n10_report_rcu_context(unsigned int completed,int outer_error)
{
    unsigned int generation=completed==1?0xffffffffU:completed-1;int ret;
    memset(&n10_rcu_report,0,sizeof(n10_rcu_report));
    ret=n10_rcu_read(&n10_rcu_report,completed);
    if(!ret && outer_error)ret=outer_error;if(!ret)ret=n10_rcu_emit_all(0,0,generation);
    if(ret){(void)n10_rcu_emit_all(1,ret,generation);return ret;}return n10_rcu_emit_all(1,0,generation);
}
