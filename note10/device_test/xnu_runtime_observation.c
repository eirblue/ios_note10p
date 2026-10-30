/* Synchronous late-init computation only; never materializes this layout. */
#include "note10_xnu_observation_geometry.h"
static const char n10_runtime_observation_marker[] __used="N10XPO1";
static void __init noinline n10_observe_runtime_plan(unsigned long reserved,
    unsigned long count,unsigned long invalid)
{
    int status=n10_xnu_runtime_plan_check(reserved,count,invalid);
    unsigned int copy;
    char frame[1024];
    for(copy=0;copy<2;copy++) {
        int length=scnprintf(frame,sizeof(frame),
            "id=%s copy=%u phase=late-init plan_generation=1 pm_completion_claimed=0 status=%d base=%llx size=%llx payload_sha=%s payload_size=%u geometry_sha=%s virt=%llx image=%llx entry=%llx kernel_offset=%llx entry_offset=%llx end_offset=%llx mapped=%u spans=%u synthetic=1 materialized=0 ownership=0",
            N10_RESERVE_BUILD_ID,copy,status,(unsigned long long)n10_window_base,
            (unsigned long long)N10_RT_WINDOW,N10_OBS_PAYLOAD_SHA,N10_OBS_PAYLOAD_SIZE,
            N10_OBS_GEOMETRY_SHA,(unsigned long long)N10_RTP_VIRTUAL_BASE,
            (unsigned long long)N10_RTP_IMAGE_VA,(unsigned long long)N10_RTP_ENTRY_VA,
            status?0ULL:(unsigned long long)N10_RTP_KERNEL_OFFSET,
            status?0ULL:(unsigned long long)N10_RTP_ENTRY_OFFSET,
            status?0ULL:(unsigned long long)N10_RTP_END_OFFSET,status?0:7,status?0:2);
        if(length<=0 || (unsigned int)length>=sizeof(frame)-1) {
            pr_err("N10XPO1 rejected-truncated-report\n");
            return; /* Reporting only; the caller's armed recovery remains live. */
        }
        pr_info("N10XPO1 %s checksum=%08x\n",frame,n10_frame_checksum(frame,length));
    }
}
