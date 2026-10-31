/* SPDX-License-Identifier: GPL-2.0-only */
/* Bounded two-copy producer, called only after CPU and IRQ restoration. */
#include <linux/note10_pm_preconditions.h>
#ifdef CONFIG_NOTE10_CPU_PM_ROUNDTRIP
static const char n10_cpu_pm_terminal_marker[] __used = "N10CPT1";
static struct n10_cpu_pm_roundtrip_sample n10_pre_terminal_report;
static int n10_pre_emit(const char *, const char *, int, unsigned int *, int);
#ifdef CONFIG_NOTE10_CPU_PM_NOTIFIER_COUNTS
static const char n10_cpu_pm_counts_marker[] __used = "N10CPNC1";
static int n10_pre_emit_counts(unsigned int copy,
                               const struct n10_cpu_pm_roundtrip_sample *s,
                               unsigned int generation, unsigned int *budget)
{
    char frame[512];
    int n;
    n=snprintf(frame,sizeof(frame),
        "id=%s copy=%u generation=%u attempted=%u roster=%u roster_valid=%u enter_calls=%u exit_calls=%u enter_nr_calls=%d exit_nr_calls=%d enter_seen=%u exit_seen=%u capture_valid=%u conflict=%u enter_error=%d exit_error=%d error=%d caller_invoked=%u terminal_stage=%u terminal_helper_error=%d terminal_probe_error=%d terminal_outer_error=%d",
        N10_RESERVE_BUILD_ID,copy,generation,s->attempted,s->roster_count,s->roster_valid,
        s->enter_calls,s->exit_calls,s->enter_nr_calls,s->exit_nr_calls,
        s->enter_nr_calls_seen,s->exit_nr_calls_seen,s->notifier_count_capture_valid,
        s->notifier_count_conflict,s->enter_error,s->exit_error,s->error,s->caller_invoked,
        s->terminal_stage,s->terminal_helper_error,s->terminal_probe_error,s->terminal_outer_error);
    return n10_pre_emit("N10CPN1",frame,n,budget,1);
}
#endif
#ifdef CONFIG_NOTE10_CPU_PM_NOTIFIER_TRACE
static int n10_pre_emit_dispatch(unsigned int copy,
 const struct n10_cpu_pm_roundtrip_sample *s, unsigned int generation, unsigned int *budget, int emit)
{
 char frame[512]; int n;
 n=snprintf(frame,sizeof(frame),"id=%s copy=%u generation=%u transaction=%u version=1 roster=%u phases=%u conflict=%u valid=%u en=%u er=%u ee=%u re=%u xn=%u xr=%u xe=%u rx=%u",N10_RESERVE_BUILD_ID,copy,generation,s->dispatch.generation,s->dispatch.roster,s->dispatch.phases,s->dispatch.conflict,s->dispatch.valid,s->dispatch.entered[0],s->dispatch.returned[0],s->dispatch.entry_order[0],s->dispatch.return_order[0],s->dispatch.entered[1],s->dispatch.returned[1],s->dispatch.entry_order[1],s->dispatch.return_order[1]);
 return n10_pre_emit("N10CPD1",frame,n,budget,emit);
}
#endif
static int n10_pre_emit_terminal(unsigned int completed, unsigned int generation, int probe_error)
{
    char frame[512]; unsigned int copy,budget=0; int n,ret;
    memset(&n10_pre_terminal_report,0,sizeof(n10_pre_terminal_report));
    ret=n10_pre_roundtrip_terminal_read(&n10_pre_terminal_report,completed);
    if (ret || !n10_pre_terminal_report.terminal_recorded ||
        !n10_pre_terminal_report.terminal_completed ||
        n10_pre_terminal_report.generation!=generation) return ret ? ret : -EIO;
    n10_pre_terminal_report.terminal_probe_error=probe_error;
    if (probe_error && !n10_pre_terminal_report.terminal_stage &&
        n10_pre_terminal_report.attempted && n10_pre_terminal_report.caller_invoked)
        n10_pre_terminal_report.terminal_stage=5;
    for (copy=0;copy<2;copy++) {
        n=snprintf(frame,sizeof(frame),"id=%s copy=%u generation=%u attempted=%u recorded=%u completed=%u caller_invoked=%u stage=%u outer_error=%d helper_error=%d probe_error=%d enter_calls=%u exit_calls=%u enter_error=%d exit_error=%d",N10_RESERVE_BUILD_ID,copy,generation,n10_pre_terminal_report.attempted,n10_pre_terminal_report.terminal_recorded,n10_pre_terminal_report.terminal_completed,n10_pre_terminal_report.caller_invoked,n10_pre_terminal_report.terminal_stage,n10_pre_terminal_report.terminal_outer_error,n10_pre_terminal_report.terminal_helper_error,n10_pre_terminal_report.terminal_probe_error,n10_pre_terminal_report.enter_calls,n10_pre_terminal_report.exit_calls,n10_pre_terminal_report.enter_error,n10_pre_terminal_report.exit_error);
        ret=n10_pre_emit("N10CPT1",frame,n,&budget,1); if(ret)return ret;
#ifdef CONFIG_NOTE10_CPU_PM_NOTIFIER_COUNTS
        ret=n10_pre_emit_counts(copy,&n10_pre_terminal_report,generation,&budget); if(ret)return ret;
#ifdef CONFIG_NOTE10_CPU_PM_NOTIFIER_TRACE
        ret=n10_pre_emit_dispatch(copy,&n10_pre_terminal_report,generation,&budget,1); if(ret)return ret;
#endif
#endif
    }
    return 0;
}
#endif
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
#ifdef CONFIG_NOTE10_CPU_PM_ROUNDTRIP
            PRE_ROW("N10CPR1","id=%s copy=%u generation=%u attempted=%u roster=%u roster_valid=%u pre=%u post=%u enter_calls=%u exit_calls=%u enter_ok=%u exit_ok=%u daif=%u timer=%u gic=%u ehld_before=%u ehld_after=%u context=%u passed=%u error=%d enter_error=%d exit_error=%d",N10_RESERVE_BUILD_ID,copy,generation,n10_pre_report.roundtrip.attempted,n10_pre_report.roundtrip.roster_count,n10_pre_report.roundtrip.roster_valid,n10_pre_report.roundtrip.pre_snapshot_valid,n10_pre_report.roundtrip.post_snapshot_valid,n10_pre_report.roundtrip.enter_calls,n10_pre_report.roundtrip.exit_calls,n10_pre_report.roundtrip.enter_succeeded,n10_pre_report.roundtrip.exit_succeeded,n10_pre_report.roundtrip.daif_stable,n10_pre_report.roundtrip.timer_stable,n10_pre_report.roundtrip.gic_stable,n10_pre_report.roundtrip.ehld_before,n10_pre_report.roundtrip.ehld_after,n10_pre_report.roundtrip.context_stable,n10_pre_report.roundtrip.passed,n10_pre_report.roundtrip.error,n10_pre_report.roundtrip.enter_error,n10_pre_report.roundtrip.exit_error);
#ifdef CONFIG_NOTE10_CPU_PM_NOTIFIER_COUNTS
            PRE_ROW("N10CPN1","id=%s copy=%u generation=%u attempted=%u roster=%u roster_valid=%u enter_calls=%u exit_calls=%u enter_nr_calls=%d exit_nr_calls=%d enter_seen=%u exit_seen=%u capture_valid=%u conflict=%u enter_error=%d exit_error=%d error=%d caller_invoked=%u terminal_stage=%u terminal_helper_error=%d terminal_probe_error=%d terminal_outer_error=%d",N10_RESERVE_BUILD_ID,copy,generation,n10_pre_report.roundtrip.attempted,n10_pre_report.roundtrip.roster_count,n10_pre_report.roundtrip.roster_valid,n10_pre_report.roundtrip.enter_calls,n10_pre_report.roundtrip.exit_calls,n10_pre_report.roundtrip.enter_nr_calls,n10_pre_report.roundtrip.exit_nr_calls,n10_pre_report.roundtrip.enter_nr_calls_seen,n10_pre_report.roundtrip.exit_nr_calls_seen,n10_pre_report.roundtrip.notifier_count_capture_valid,n10_pre_report.roundtrip.notifier_count_conflict,n10_pre_report.roundtrip.enter_error,n10_pre_report.roundtrip.exit_error,n10_pre_report.roundtrip.error,n10_pre_report.roundtrip.caller_invoked,n10_pre_report.roundtrip.terminal_stage,n10_pre_report.roundtrip.terminal_helper_error,n10_pre_report.roundtrip.terminal_probe_error,n10_pre_report.roundtrip.terminal_outer_error);
#endif
#endif
#ifdef CONFIG_NOTE10_CPU_PM_NOTIFIER_TRACE
            ret=n10_pre_emit_dispatch(copy,&n10_pre_report.roundtrip,generation,&budget,emit); if(ret)return ret;
#endif
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
    if (ret) {
#ifdef CONFIG_NOTE10_CPU_PM_ROUNDTRIP
            (void)n10_pre_emit_terminal(completed,generation,ret);
#endif
        (void)n10_pre_emit_all(1,ret,generation);return ret;
    }
    return n10_pre_emit_all(1,0,generation);
}
