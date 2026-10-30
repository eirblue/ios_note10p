/* Caller-owned init scratch only. Numeric physical addresses are data. */
#ifdef __KERNEL__
#include <asm/thread_info.h>
#endif
static const unsigned long n10_scratch_thread_size __used = THREAD_SIZE;
static const char n10_scratch_marker[] __used = "N10XSO1";
static const uint8_t n10_scratch_tree[56] = {
    1,0,0,0,0,0,0,0,
    'n','a','m','e',0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,
    12,0,0,0,'d','e','v','i','c','e','-','t','r','e','e',0
};
static struct {
    uint8_t args[16+N10_RT_ARGS_SIZE+16];
    uint8_t record[16+N10_RT_RECORD_SIZE+16];
    uint8_t adt[16+56+16];
    struct n10_rt_request request;
    struct n10_rt_plan plan;
} n10_scratch __initdata;

static int __init noinline n10_scratch_build(unsigned long reserved,
    unsigned long count,unsigned long invalid)
{
    unsigned int i;
    if(n10_window_status!=1 || !count || PAGE_SHIFT<12 || PAGE_SHIFT>16 ||
       count!=(N10_RT_WINDOW>>PAGE_SHIFT) || reserved!=count || invalid)
        return -1;
    zero_bytes(&n10_scratch,sizeof(n10_scratch));
    for(i=0;i<sizeof(n10_scratch.args);i++)n10_scratch.args[i]=0xa5;
    for(i=0;i<sizeof(n10_scratch.record);i++)n10_scratch.record[i]=0xa5;
    for(i=0;i<sizeof(n10_scratch.adt);i++)n10_scratch.adt[i]=0xa5;
    copy_bytes(n10_scratch.adt+16,n10_scratch_tree,56);
    n10_scratch.request.physical_base=n10_window_base;
    n10_scratch.request.window_size=N10_RT_WINDOW;
    n10_scratch.request.image_virtual=N10_RTP_IMAGE_VA;
    n10_scratch.request.image_size=N10_RTP_IMAGE_SIZE;
    n10_scratch.request.entry_virtual=N10_RTP_ENTRY_VA;
    n10_scratch.request.adt=n10_scratch.adt+16;
    n10_scratch.request.adt_length=56;
    n10_scratch.request.synthetic_adt=N10_RT_SYNTHETIC_ADT;
    return n10_rt_build(&n10_scratch.request,&n10_scratch.plan,
        n10_scratch.args+16,N10_RT_ARGS_SIZE,
        n10_scratch.record+16,N10_RT_RECORD_SIZE);
}

/* Independent byte oracle: all unlisted boot_args and record bytes are zero. */
static uint8_t __init noinline n10_scratch_expected(unsigned int at,int record)
{
    uint64_t value=0;unsigned int start=0,size=0;
    uint64_t base=(uint64_t)n10_window_base;
    if(record) {
        if(at<8)return ((const uint8_t *)"N10XFER1")[at];
        if(at>=8 && at<12){start=8;size=4;value=1;}
        if(at>=12 && at<16){start=12;size=4;value=64;}
        if(at>=16 && at<24){start=16;size=8;value=base;}
        if(at>=24 && at<32){start=24;size=8;value=base+N10_RTP_ENTRY_OFFSET;}
    } else {
        if(at==0 || at==2)return 2;
        if(at>=8 && at<16){start=8;size=8;value=N10_RTP_VIRTUAL_BASE;}
        if(at>=16 && at<24){start=16;size=8;value=base;}
        if(at>=24 && at<32){start=24;size=8;value=N10_RT_WINDOW;}
        if(at>=32 && at<40){start=32;size=8;value=base+N10_RTP_END_OFFSET;}
        if(at>=96 && at<104){start=96;size=8;value=N10_RTP_VIRTUAL_BASE+N10_RT_PAGE;}
        if(at>=104 && at<108){start=104;size=4;value=56;}
        if(at>=1144 && at<1152){start=1144;size=8;value=N10_RT_WINDOW;}
    }
    return size?(uint8_t)(value>>(8*(at-start))):0;
}

static int __init noinline n10_scratch_check(void)
{
    unsigned int i;
    const struct n10_rt_plan *p=&n10_scratch.plan;
    uint64_t base=(uint64_t)n10_window_base;
    if(p->physical_base!=base || p->window_size!=N10_RT_WINDOW ||
       p->virtual_ram_base!=N10_RTP_VIRTUAL_BASE || p->image_virtual!=N10_RTP_IMAGE_VA ||
       p->image_size!=N10_RTP_IMAGE_SIZE || p->entry_virtual!=N10_RTP_ENTRY_VA ||
       p->kernel_physical!=base+N10_RTP_KERNEL_OFFSET ||
       p->entry_physical!=base+N10_RTP_ENTRY_OFFSET || p->kernel_end!=base+N10_RTP_END_OFFSET ||
       p->arguments_physical!=base || p->device_tree_physical!=base+N10_RT_PAGE ||
       p->device_tree_virtual!=N10_RTP_VIRTUAL_BASE+N10_RT_PAGE ||
       p->adapter_physical!=base+2*N10_RT_PAGE || p->mapping_blocks!=7 ||
       p->kernel_blocks!=2 || p->adt_length!=56)return -2;
    for(i=0;i<16;i++) {
        if(n10_scratch.args[i]!=0xa5 || n10_scratch.args[16+1152+i]!=0xa5 ||
           n10_scratch.record[i]!=0xa5 || n10_scratch.record[16+64+i]!=0xa5 ||
           n10_scratch.adt[i]!=0xa5 || n10_scratch.adt[16+56+i]!=0xa5)return -3;
    }
    for(i=0;i<1152;i++)if(n10_scratch.args[16+i]!=n10_scratch_expected(i,0))return -4;
    for(i=0;i<64;i++)if(n10_scratch.record[16+i]!=n10_scratch_expected(i,1))return -5;
    for(i=0;i<56;i++)if(n10_scratch.adt[16+i]!=n10_scratch_tree[i])return -6;
    return 0;
}

static void __init noinline n10_scratch_report(int status)
{
    char frame[768];unsigned int copy;
    for(copy=0;copy<2;copy++) {
        int length=scnprintf(frame,sizeof(frame),
            "id=%s copy=%u phase=late-init generation=1 pm_completion_claimed=0 status=%d base=%llx size=%llx payload_sha=%s geometry_sha=%s args_size=1152 record_size=64 adt_size=56 args_fnv=%08x record_fnv=%08x adt_fnv=%08x checked=%u canaries=%u synthetic=1 scratch_materialized=%u reserved_materialized=0 ownership=0 executed=0",
            N10_RESERVE_BUILD_ID,copy,status,(unsigned long long)n10_window_base,
            (unsigned long long)N10_RT_WINDOW,N10_OBS_PAYLOAD_SHA,N10_OBS_GEOMETRY_SHA,
            status?0:n10_frame_checksum((char *)n10_scratch.args+16,1152),
            status?0:n10_frame_checksum((char *)n10_scratch.record+16,64),
            status?0:n10_frame_checksum((char *)n10_scratch.adt+16,56),
            status?0:1,status?0:1,status?0:1);
        if(length<=0 || (unsigned int)length>=sizeof(frame)-1) {
            pr_err("N10XSO1 rejected-truncated-report\n");return;
        }
        pr_info("N10XSO1 %s checksum=%08x\n",frame,n10_frame_checksum(frame,length));
    }
}
static void __init noinline n10_observe_runtime_scratch(unsigned long reserved,
    unsigned long count,unsigned long invalid)
{
    int status=n10_scratch_build(reserved,count,invalid);
    if(!status)status=n10_scratch_check();
    n10_scratch_report(status);
    zero_bytes(&n10_scratch,sizeof(n10_scratch));
}
