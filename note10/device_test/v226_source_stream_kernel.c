/* SPDX-License-Identifier: GPL-2.0-only */
/* Included after225shared owner callbacks. Candidate only: PC controller cannot boot it. */
#include <linux/crc32.h>
#include <linux/sched/task_stack.h>
#include <asm/stack_pointer.h>
#include "native_source_stream.h"
#if defined(CONFIG_HIGHMEM) || defined(HASHED_PAGE_VIRTUAL) || defined(WANT_PAGE_VIRTUAL) || defined(CONFIG_DEBUG_VM) || defined(CONFIG_DEBUG_VIRTUAL)
#error "226 requires existing direct lowmem page pointer without deep debug calls"
#endif
extern const n209_u8 n226_source_slot[N226_SOURCE_CAP];
/* An opaque assembler object prevents folding the locally patched zero placeholder. */
__asm__(".pushsection .rodata.n226_source,\"a\",%progbits\n"
        ".balign 4096\n.globl n226_source_slot\n.type n226_source_slot,%object\n"
        "n226_source_slot:\n.zero 6209536\n.size n226_source_slot,6209536\n.popsection\n");
static n209_u8 n226_source_pool[N226_POOL_BYTES] __aligned(PAGE_SIZE) __section(".bss.n226_source_pool");
__asm__(".globl n226_control_storage\n.set n226_control_storage,n226_source_pool+42312\n"
        ".type n226_control_storage,%object\n.size n226_control_storage,688\n"
        ".globl n226_stream_storage\n.set n226_stream_storage,n226_source_pool+42736\n"
        ".type n226_stream_storage,%object\n.size n226_stream_storage,264\n");
struct n226_control { struct n219_kernel_context owner;z_stream codec;struct n226_stream source; };
struct n226_stack_stats { n209_u64 floor,top,sp,headroom;n209_u32 chain_cap,guard,error,ready; };
_Static_assert(sizeof(struct inflate_workspace)==42312,"workspace42312");
_Static_assert(sizeof(z_stream)==96,"zstream96");
_Static_assert(sizeof(struct n219_kernel_context)==328,"owner328");
_Static_assert(sizeof(struct n226_control)==688,"control688");
_Static_assert(offsetof(struct n226_control,owner)==0,"owner prefix0");
_Static_assert(__alignof__(struct n226_control)==8,"controlalign8");
_Static_assert(offsetof(struct n226_control,codec)==328,"codec328");
_Static_assert(offsetof(struct n226_control,source)==424,"source424");
_Static_assert(N226_CONTROL_OFFSET+sizeof(struct n226_control)==N226_REQUEST_OFFSET,"control/Q disjoint");
_Static_assert(N226_REQUEST_OFFSET%8==0&&N226_REQUEST_OFFSET+sizeof(struct n217_request)<=N226_STAGE_OFFSET,"Q496 in gap");
_Static_assert(sizeof(struct n226_stack_stats)==48&&N226_REQUEST_OFFSET+sizeof(struct n217_request)==N226_STATS_OFFSET,"stats48 after Q");
_Static_assert(N226_STATS_OFFSET+sizeof(struct n226_stack_stats)<=N226_STAGE_OFFSET,"stats fit gap");
_Static_assert(N226_STAGE_OFFSET%PAGE_SIZE==0&&N226_STAGE_OFFSET+N217_CHUNK==N226_POOL_BYTES,"stage4096");
_Static_assert(THREAD_SIZE==16384&&sizeof(unsigned long)==8,"reviewed ARM64 task stack");
static struct n226_control *n226_control(void)
{ return (struct n226_control *)(n226_source_pool+N226_CONTROL_OFFSET); }
static N226_NOINLINE int n226_codec_begin(void *opaque)
{
    struct n226_control *ctx=opaque;memset(&ctx->codec,0,sizeof(ctx->codec));ctx->codec.workspace=n226_source_pool;
    if(zlib_inflate_workspacesize()!=N226_WORKSPACE_BYTES)return -EINVAL;
    return zlib_inflateInit2(&ctx->codec,-15);
}
static N226_NOINLINE int n226_codec_pull(void *opaque,const n209_u8 *in,unsigned int input,n209_u8 *out,unsigned int output,
                                       unsigned int *used,unsigned int *got)
{
    struct n226_control *ctx=opaque;int error;ctx->codec.next_in=in;ctx->codec.avail_in=input;
    ctx->codec.next_out=out;ctx->codec.avail_out=output;error=zlib_inflate(&ctx->codec,0);
    *used=input-(unsigned int)ctx->codec.avail_in;*got=output-(unsigned int)ctx->codec.avail_out;
    return error==Z_STREAM_END?1:error==Z_OK?0:-EINVAL;
}
static N226_NOINLINE n209_u32 n226_codec_crc(n209_u32 seed,const n209_u8 *raw,unsigned int bytes)
{ return crc32_le(seed,raw,bytes); }
static N226_NOINLINE void n226_codec_end(void *opaque)
{ struct n226_control *ctx=opaque;if(ctx->codec.state)(void)zlib_inflateEnd(&ctx->codec); }
static const struct n226_codec n226_codec={n226_codec_begin,n226_codec_pull,n226_codec_crc,n226_codec_end};
static N226_NOINLINE int n226_hold(void *opaque,unsigned int role,n209_u64 bytes,void **held,n209_u64 *token)
{
    struct n226_control *ctx=opaque;if(role>=2||ctx->source.roles[role].size!=bytes)return -EINVAL;
    *held=&ctx->source.roles[role];*token=(n209_u64)(unsigned long)*held;return 0;
}
static N226_NOINLINE long n226_source_read(void *opaque,void *held,n209_u64 offset,void *raw,unsigned int bytes)
{
    struct n226_control *ctx=opaque;unsigned int role;
    if(held==&ctx->source.roles[0])role=0;else if(held==&ctx->source.roles[1])role=1;else return -EINVAL;
    return n226_read(&ctx->source,n226_source_slot,role,offset,raw,bytes,&n226_codec,ctx);
}
static N226_NOINLINE void n226_put(void *opaque,void *held)
{
    /* These are fixed readonly-member handles, never VFS files or reclaimable pages. */
    (void)opaque;(void)held;
}
static N226_NOINLINE int n226_prepare_hash(const n209_u8 *payload,n209_u8 *out)
{
    if(!n226_stack_room((n209_u64)(unsigned long)(end_of_stack(current)+1),
        (n209_u64)(unsigned long)task_stack_page(current)+THREAD_SIZE,current_stack_pointer,N226_CHAIN_CAP,N226_STACK_GUARD))return -EOVERFLOW;
    return n226_descriptor_digest(&n226_control()->owner.hash,payload,out);
}
static __always_inline void n226_emit(int error)
{
    const struct n217_result *result=&n217_kernel_state.result;
    const struct n226_stack_stats *stats=(const struct n226_stack_stats *)(n226_source_pool+N226_STATS_OFFSET);
    pr_info("N226SRC id=%.32s boot=%.32s cycle=%.32s result=%d source_kind=rodata native_source=%u destination_hash_verified=%u copied_kernel=%llu copied_adapter=%llu quarantined=%u headroom=%llu chain_cap=8192 stack_guard=4096 source_pinned=0 mapping_verified=0 XNU=0\n",
        n210_result.build,n210_result.boot,n210_result.cycle,error,
        !error&&result->status==1&&result->destination_content_verified==1,
        !error&&result->destination_content_verified==1,
        (unsigned long long)result->copied_bytes[0],(unsigned long long)result->copied_bytes[1],result->quarantined,
        (unsigned long long)stats->headroom);
}
static N226_NOINLINE int n226_ingest_prepared_locked(const struct n210_request *prepared,const struct n210_context *context)
{
    static const struct n217_io io={n217_owner,n226_hold,n226_source_read,n226_put,n219_hash_begin,n219_hash_update,n219_hash_end,
                                   n217_write_destination,n217_read_destination,n217_clear_destination};
    struct n226_control *ctx;struct n217_request *request;struct n226_stack_stats *stats;int error;
    /* n210_write owns n210_lock once; calling a locking217/219 entry here would deadlock. */
    lockdep_assert_held(&n210_lock);
    if(n217_kernel_state.spent)return -EALREADY;
    memset(n226_source_pool,0,sizeof(n226_source_pool));ctx=n226_control();request=(struct n217_request *)(n226_source_pool+N226_REQUEST_OFFSET);
    stats=(struct n226_stack_stats *)(n226_source_pool+N226_STATS_OFFSET);
    stats->floor=(n209_u64)(unsigned long)(end_of_stack(current)+1);
    stats->top=(n209_u64)(unsigned long)task_stack_page(current)+THREAD_SIZE;stats->sp=current_stack_pointer;
    stats->headroom=stats->sp>=stats->floor&&stats->sp<=stats->top?stats->sp-stats->floor:0;
    stats->chain_cap=N226_CHAIN_CAP;stats->guard=N226_STACK_GUARD;
    if(!n226_stack_room(stats->floor,stats->top,stats->sp,stats->chain_cap,stats->guard)){error=-EOVERFLOW;goto early;}
    stats->ready=1;
    memcpy(request->magic,"N217SRC1",8);request->schema=1;request->bytes=496;memcpy(&request->prepared,prepared,sizeof(*prepared));
    memcpy(&ctx->owner.base.identity,context,sizeof(*context));
    memcpy(&ctx->owner.base.destination,&n210_destination,96);
    if(ctx->owner.base.identity.page_reserved!=1||ctx->owner.base.identity.pid1!=1||
       ctx->owner.base.identity.cap_sys_boot!=1||n210_result.status!=1||n217_owner(ctx,&n210_destination)){error=-EPERM;goto early;}
    error=n226_open(&ctx->source,n226_source_slot,N226_SOURCE_CAP,request->prepared.payload,&ctx->owner.hash,&n226_codec,ctx);
    if(error)goto early;
    error=n217_consume(request,&ctx->owner.base.destination,&ctx->owner.base.identity,&n210_result,&n217_kernel_state,&io,ctx,
                       n226_source_pool+N226_STAGE_OFFSET,N217_CHUNK);
    goto done;
 early:
    n217_kernel_state.spent=1;memset(&n217_kernel_state.result,0,sizeof(n217_kernel_state.result));
    memcpy(n217_kernel_state.result.magic,"N217RCP1",8);n217_kernel_state.result.schema=1;n217_kernel_state.result.bytes=352;
    n217_kernel_state.result.status=2;n217_kernel_state.result.error_code=(n209_u32)-error;
 done:
    stats->error=(n209_u32)-error;n226_codec_end(ctx);memzero_explicit(n226_source_pool,N226_WORKSPACE_BYTES);
    memzero_explicit(n226_source_pool+N226_STAGE_OFFSET,N217_CHUNK);memzero_explicit(&ctx->owner.hash,sizeof(ctx->owner.hash));return error;
}
