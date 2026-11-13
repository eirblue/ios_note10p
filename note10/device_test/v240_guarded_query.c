/* SPDX-License-Identifier: GPL-2.0-only */
#include "v240_guarded_query.h"
#define N240_NOINLINE __attribute__((__noinline__))
#ifdef __KERNEL__
#include <linux/interrupt.h>
#include <linux/smp.h>
#include <linux/sched/task_stack.h>
#include <asm/stack_pointer.h>
#define N240_CONTEXT() (task_pid_nr(current)==1&&!in_interrupt()&&!irqs_disabled())
#define N240_PC() ((n209_u32)preempt_count())
#define N240_GET() get_cpu()
#define N240_PUT() put_cpu()
#define N240_CPU() raw_smp_processor_id()
#define N240_CAPTURE(s) n231_capture_cpu_observation(s)
#define N240_NODE(s,n) n233_capture_cpu_node_consistency(s,n)
static N240_NOINLINE int n240_room(n209_u64 *headroom)
{
    n209_u64 floor=(n209_u64)(unsigned long)(end_of_stack(current)+1);
    n209_u64 top=(n209_u64)(unsigned long)task_stack_page(current)+THREAD_SIZE;
    n209_u64 sp=current_stack_pointer;
    *headroom=sp>=floor&&sp<=top?sp-floor:0;
    return n226_stack_room(floor,top,sp,N226_CHAIN_CAP,N226_STACK_GUARD);
}
#define N240_ROOM(h) n240_room(h)
#elif defined(N240_HOST_FIXTURE)
extern int n240_fixture_context(void);
extern n209_u32 n240_fixture_pc(void);
extern unsigned int n240_fixture_get(void);
extern void n240_fixture_put(void);
extern unsigned int n240_fixture_cpu(void);
extern int n240_fixture_capture(struct n231_cpu_observation *);
extern int n240_fixture_node(const struct n231_cpu_observation *,struct n233_cpu_node_consistency *);
extern int n240_fixture_room(n209_u64 *);
#define N240_CONTEXT() n240_fixture_context()
#define N240_PC() n240_fixture_pc()
#define N240_GET() n240_fixture_get()
#define N240_PUT() n240_fixture_put()
#define N240_CPU() n240_fixture_cpu()
#define N240_CAPTURE(s) n240_fixture_capture(s)
#define N240_NODE(s,n) n240_fixture_node(s,n)
#define N240_ROOM(h) n240_fixture_room(h)
#else
#error "240 is kernel candidate or explicit host IO shim only"
#endif

N240_NOINLINE void n240_invalidate_observations(struct n231_cpu_observation *sample,
    struct n233_cpu_node_consistency *node,struct n240_query_receipt *receipt,int error)
{
    unsigned int i;
    if(sample){volatile n209_u8 *raw=(volatile n209_u8 *)sample;for(i=0;i<sizeof(*sample);i++)raw[i]=0;}
    if(node){volatile n209_u8 *raw=(volatile n209_u8 *)node;for(i=0;i<sizeof(*node);i++)raw[i]=0;}
    if(receipt&&receipt->schema==1){receipt->status=0;receipt->error_code=error<0?(n209_u32)-error:22U;}
}
static N240_NOINLINE void n240_clear_receipt(struct n240_query_receipt *receipt)
{
    volatile n209_u8 *raw=(volatile n209_u8 *)receipt;unsigned int i;
    for(i=0;i<sizeof(*receipt);i++)raw[i]=0;
    receipt->schema=1;receipt->cpu_enter=receipt->cpu_sample=receipt->cpu_before_release=~0U;
}
N240_NOINLINE int n240_observe_current_cpu(struct n231_cpu_observation *sample,
    struct n233_cpu_node_consistency *node,struct n240_query_receipt *receipt)
{
    int error=-22;
    if(receipt)n240_clear_receipt(receipt);
    n240_invalidate_observations(sample,node,receipt,error);
    if(!sample||!node||!receipt)return error;
    receipt->pc_before=N240_PC();
    if(!N240_CONTEXT()||receipt->pc_before){error=-1;goto failed;}
    if(!N240_ROOM(&receipt->pre_headroom)){error=-75;goto failed;}
    receipt->cpu_enter=N240_GET();
    /* Only this acquisition is owned here. No count repair or looped enable. */
    if(receipt->cpu_enter>=8||N240_PC()!=1){error=-71;goto release;}
    error=N240_CAPTURE(sample);if(error>0)error=-22;
    receipt->cpu_sample=sample->linux_cpu;receipt->pc_after_capture=N240_PC();
    if(error)goto release;
    if(receipt->pc_after_capture!=1||sample->status!=1||sample->linux_cpu!=receipt->cpu_enter){error=-71;goto release;}
    error=N240_NODE(sample,node);if(error>0)error=-22;
    if(!error&&(node->status!=1||node->linux_cpu!=sample->linux_cpu)){error=-71;}
release:
    receipt->cpu_before_release=N240_CPU();receipt->pc_after_query=N240_PC();
    if(receipt->pc_after_query!=1||receipt->cpu_before_release!=receipt->cpu_enter)error=-71;
    N240_PUT();
    receipt->pc_after_release=N240_PC();
    if(receipt->pc_after_release)error=-71;
    if(error)goto failed;
    if(!N240_ROOM(&receipt->post_headroom)){error=-75;goto failed;}
    receipt->error_code=0;receipt->status=1;return 0;
failed:
    n240_invalidate_observations(sample,node,receipt,error);return error;
}

#ifdef __KERNEL__
_Static_assert(N240_POOL_OFFSET==N233_POOL_OFFSET+sizeof(struct n233_cpu_node_consistency),"after node32");
_Static_assert(N240_POOL_OFFSET%8==0&&N240_POOL_OFFSET+sizeof(struct n240_query_receipt)<=N226_STAGE_OFFSET,"receipt before stage");
__asm__(".globl n240_query_storage\n.set n240_query_storage,n226_source_pool+43608\n"
        ".type n240_query_storage,%object\n.size n240_query_storage,56\n");
static __used N240_NOINLINE void n240_layout_witness(void)
{
    asm volatile(".globl n240_size_query\n.equ n240_size_query,%c0\n"
                 ".globl n240_align_query\n.equ n240_align_query,%c1\n"
                 ".globl n240_pre_room_offset\n.equ n240_pre_room_offset,%c2\n"
                 : : "i"(sizeof(struct n240_query_receipt)),"i"(__alignof__(struct n240_query_receipt)),
                     "i"(offsetof(struct n240_query_receipt,pre_headroom)));
}
static __always_inline void n240_emit(int error)
{
    const struct n240_query_receipt *q=(const struct n240_query_receipt *)(n226_source_pool+N240_POOL_OFFSET);
    const struct n231_cpu_observation *s=(const struct n231_cpu_observation *)(n226_source_pool+N231_POOL_OFFSET);
    const struct n233_cpu_node_consistency *n=(const struct n233_cpu_node_consistency *)(n226_source_pool+N233_POOL_OFFSET);
    unsigned int valid=!error&&q->schema==1&&q->status==1&&s->status==1&&n->status==1;
    pr_info("N240NODE id=%.32s boot=%.32s cycle=%.32s result=%d phase=linux-pid1-pre-ingest valid=%u cpu_enter=%u cpu_sample=%u cpu_before_release=%u pc_before=%u pc_after_capture=%u pc_after_query=%u pc_after_release=%u pre_headroom=%llu post_headroom=%llu node_cpu=%u address_cells=%u reg_bytes=%u firmware_reg=%llx FDT_bound=0 handoff_cpu_selected=0 post_shutdown=0 XNU=0\n",
        n210_result.build,n210_result.boot,n210_result.cycle,error,valid,q->cpu_enter,q->cpu_sample,q->cpu_before_release,
        q->pc_before,q->pc_after_capture,q->pc_after_query,q->pc_after_release,(unsigned long long)q->pre_headroom,
        (unsigned long long)q->post_headroom,n->linux_cpu,n->address_cells,n->reg_bytes,(unsigned long long)n->firmware_reg);
}
#endif
