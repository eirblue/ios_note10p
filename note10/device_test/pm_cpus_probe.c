/* SPDX-License-Identifier: GPL-2.0-only */
#include <linux/note10_pm_cpus.h>
static void n10_report_pm_cpus(unsigned int generation)
{
    struct n10_pm_cpus_sample s = {0};
    struct n10_pmu_noirq_sample p = {0};
    unsigned int copy,original,negative,error,error_negative;
    int status=n10_pm_cpus_read(&s,&p,generation),count;
    char frame[384];
    if (!s.seen) return; /* Pre-device EBUSY attempts never ran this test. */
    negative=s.original_error<0;original=negative?(unsigned int)(-(long long)s.original_error):(unsigned int)s.original_error;
    error_negative=s.error<0;error=error_negative?(unsigned int)(-(long long)s.error):(unsigned int)s.error;
    for(copy=0;copy<4;++copy){
        count=scnprintf(frame,sizeof(frame),
            "id=%s seq=%u generation=%u seen=%x bad=%x attempted=%x disabled=%x enabled=%x before=%x stopped=%x restored=%x cpu=%u phase=%u original=%x negative=%x error=%u error_negative=%x status=%u",
            N10_RESERVE_BUILD_ID,copy,s.generation,s.seen,s.bad,s.attempted,s.disabled,s.enabled,
            s.before,s.stopped,s.restored,s.cpu,s.phase,original,negative,error,error_negative,status?1:0);
        pr_info("N10NPC1 %s checksum=%08x\n",frame,n10_frame_checksum(frame,count));
        count=scnprintf(frame,sizeof(frame),
            "id=%s seq=%u generation=%u seen=%x error=%u count=%x before=%x state=%x after=%x status=%u",
            N10_RESERVE_BUILD_ID,copy,p.generation,p.seen,p.error,16,p.before,p.state,p.after,status?1:0);
        pr_info("N10NPD1 %s checksum=%08x\n",frame,n10_frame_checksum(frame,count));
    }
}
