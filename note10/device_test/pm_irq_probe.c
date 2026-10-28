/* SPDX-License-Identifier: GPL-2.0-only */
/* Only called by the restored worker, never in the CPU0-only interval. */
#include <linux/note10_pm_irq.h>
#define N10_IRQ_LOG_BUDGET 16384U
#define N10_IRQ_LOG_OVERHEAD 96U
static struct n10_pm_irq_sample n10_irq_report;
static int n10_irq_emit(const char *tag,char *frame,int count,unsigned int *budget,int emit)
{
    unsigned int bytes;
    if (count<0 || count>=512) return -E2BIG;
    bytes=count+strlen(tag)+N10_IRQ_LOG_OVERHEAD;
    if (*budget>N10_IRQ_LOG_BUDGET-bytes) return -E2BIG;
    *budget+=bytes;
    if (emit) pr_info("%s %s checksum=%08x\n",tag,frame,n10_frame_checksum(frame,count));
    return 0;
}
static int n10_irq_emit_success(int emit)
{
    unsigned int copy,phase,budget=0;int n,ret;char frame[512];
#define N10_IRQ_ROW(tag,...) do { n=snprintf(frame,sizeof(frame),__VA_ARGS__); \
    ret=n10_irq_emit(tag,frame,n,&budget,emit);if(ret)return ret; } while (0)
    for(copy=0;copy<2;++copy) {
        for(phase=0;phase<3;++phase) {
            struct n10_irq_arch_sample *a=&n10_irq_report.arch[phase];
            struct n10_irq_gic_sample *g=&n10_irq_report.gic[phase];
            N10_IRQ_ROW("N10IAR1","id=%s seq=%u phase=%u generation=%u seen=%x el=%llx mpidr=%llx sctlr=%llx tcr=%llx ttbr1=%llx mair=%llx",
                N10_RESERVE_BUILD_ID,copy*3+phase,phase,n10_irq_report.generation,a->seen,
                (unsigned long long)a->el,(unsigned long long)a->mpidr,(unsigned long long)a->sctlr,
                (unsigned long long)a->tcr,(unsigned long long)a->ttbr1,(unsigned long long)a->mair);
            N10_IRQ_ROW("N10ITR1","id=%s seq=%u phase=%u generation=%u cpu=%u online=%x count=%u irq=%u preempt=%x daif=%llx cntkctl=%llx cntfrq=%llx",
                N10_RESERVE_BUILD_ID,copy*3+phase,phase,n10_irq_report.generation,a->cpu,a->online,a->count,a->irq,a->preempt,
                (unsigned long long)a->daif,(unsigned long long)a->cntkctl,(unsigned long long)a->cntfrq);
            N10_IRQ_ROW("N10IGR1","id=%s seq=%u phase=%u generation=%u seen=%x cpu=%u online=%x count=%u irq=%u preempt=%x ctlr=%x pmr=%x bpr=%x iidr=%x dist=%x typer=%x",
                N10_RESERVE_BUILD_ID,copy*3+phase,phase,n10_irq_report.generation,g->seen,g->cpu,g->online,g->count,g->irq,g->preempt,
                g->cpu_ctlr,g->pmr,g->bpr,g->iidr,g->dist_ctlr,g->typer);
        }
        N10_IRQ_ROW("N10IQR1","id=%s seq=%u generation=%u seen=%x bad=%x attempted=%x restored=%x complete=%x pre_before=%x pre_after=%x saved=%lx error=0 status=0",
            N10_RESERVE_BUILD_ID,copy,n10_irq_report.generation,n10_irq_report.seen,n10_irq_report.bad,n10_irq_report.attempted,
            n10_irq_report.restored,n10_irq_report.completed,n10_irq_report.preempt_before,n10_irq_report.preempt_after,n10_irq_report.saved_flags);
    }
#undef N10_IRQ_ROW
    return 0;
}
static void n10_irq_emit_failure(unsigned int completed)
{
    unsigned int copy,budget=0;char frame[512];
    for(copy=0;copy<2;++copy) {
        int n=snprintf(frame,sizeof(frame),"id=%s seq=%u generation=%u seen=%x bad=%x attempted=%x restored=%x complete=%x pre_before=%x pre_after=%x saved=%lx error=%u status=1",
            N10_RESERVE_BUILD_ID,copy,completed,n10_irq_report.seen,n10_irq_report.bad,n10_irq_report.attempted,
            n10_irq_report.restored,n10_irq_report.completed,n10_irq_report.preempt_before,n10_irq_report.preempt_after,
            n10_irq_report.saved_flags,(unsigned int)(n10_irq_report.error<0 ? -n10_irq_report.error : n10_irq_report.error));
        n10_irq_emit("N10IQR1",frame,n,&budget,1);
    }
}
static int n10_report_pm_irq(unsigned int completed)
{
    int error;
    memset(&n10_irq_report,0,sizeof(n10_irq_report));
    error=n10_pm_irq_read(&n10_irq_report,completed);
    if (!error) error=n10_irq_emit_success(0);
    if (error) { n10_irq_emit_failure(completed);return -EIO; }
    return n10_irq_emit_success(1);
}
static void n10_report_pm_irq_failure(unsigned int completed)
{
    memset(&n10_irq_report,0,sizeof(n10_irq_report));
    if (completed) (void)n10_pm_irq_read(&n10_irq_report,completed);
    n10_irq_emit_failure(completed);
}
