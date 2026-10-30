/* Included only by the opt-in reservation-only PC component translation unit.
 * Uses current-boot reservation variables, a local plan and synthetic ADT.
 * No payload pointer, serialization, materialization or handoff operation. */
#include "runtime_relocation.h"
#include "note10_xnu_runtime_geometry.h"

static const char n10_xnu_runtime_marker[] __used = "N10XRP1";
static void __init n10_runtime_plan_report(int status,
    unsigned long long kernel, unsigned long long entry, unsigned long long end,
    unsigned int mapped, unsigned int spans)
{
    unsigned int copy;
    char frame[256];
    for(copy=0;copy<2;copy++) {
        int length=scnprintf(frame,sizeof(frame),
            "id=%s copy=%u status=%d kernel=%llx entry=%llx end=%llx mapped=%u spans=%u synthetic=1 materialized=0",
            N10_RESERVE_BUILD_ID,copy,status,kernel,entry,end,mapped,spans);
        pr_info("N10XRP1 %s checksum=%08x\n",frame,n10_frame_checksum(frame,length));
    }
}
static int __init noinline n10_xnu_runtime_plan_check(unsigned long reserved,
    unsigned long count,unsigned long invalid)
{
    static const uint8_t synthetic_tree[56]={
        1,0,0,0,0,0,0,0,
        'n','a','m','e',0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,
        12,0,0,0,'d','e','v','i','c','e','-','t','r','e','e',0
    };
    struct n10_rt_request request={0};
    struct n10_rt_plan plan;
    uint64_t base;
    int status;
    if(n10_window_status!=1) {status=-1;goto rejected;}
    base=(uint64_t)n10_window_base;
    if(base<N10_RT_MIN_BASE || base%N10_RT_BLOCK || base>N10_RT_LIMIT-N10_RT_WINDOW) {
        status=-2;goto rejected;
    }
    if(PAGE_SHIFT<12 || PAGE_SHIFT>16 || !count ||
       count!=(N10_RT_WINDOW>>PAGE_SHIFT) || reserved!=count || invalid) {
        status=-3;goto rejected;
    }
    request.physical_base=base;request.window_size=N10_RT_WINDOW;
    request.image_virtual=N10_RTP_IMAGE_VA;request.image_size=N10_RTP_IMAGE_SIZE;
    request.entry_virtual=N10_RTP_ENTRY_VA;
    request.adt=synthetic_tree;request.adt_length=sizeof(synthetic_tree);
    request.synthetic_adt=N10_RT_SYNTHETIC_ADT;
    if(n10_rt_plan(&request,&plan)) {status=-4;goto rejected;}
    if(plan.physical_base!=base || plan.window_size!=N10_RT_WINDOW ||
       plan.virtual_ram_base!=N10_RTP_VIRTUAL_BASE ||
       plan.image_virtual!=N10_RTP_IMAGE_VA || plan.image_size!=N10_RTP_IMAGE_SIZE ||
       plan.entry_virtual!=N10_RTP_ENTRY_VA ||
       plan.kernel_physical!=base+N10_RTP_KERNEL_OFFSET ||
       plan.entry_physical!=base+N10_RTP_ENTRY_OFFSET ||
       plan.kernel_end!=base+N10_RTP_END_OFFSET ||
       plan.arguments_physical!=base || plan.device_tree_physical!=base+N10_RT_PAGE ||
       plan.adapter_physical!=base+2*N10_RT_PAGE ||
       plan.device_tree_virtual!=N10_RTP_VIRTUAL_BASE+N10_RT_PAGE ||
       plan.adt_length!=sizeof(synthetic_tree) || plan.mapping_blocks!=7 || plan.kernel_blocks!=2 ||
       plan.kernel_end>base+N10_RT_WINDOW) {
        status=-5;goto rejected;
    }
    n10_runtime_plan_report(0,N10_RTP_KERNEL_OFFSET,N10_RTP_ENTRY_OFFSET,
        N10_RTP_END_OFFSET,7,2);
    return 0;
rejected:
    /* Never publish any failed or unvalidated local-plan contents. */
    n10_runtime_plan_report(status,0,0,0,0,0);
    return status;
}
