/* SPDX-License-Identifier: GPL-2.0-only */
/* Included after the unchanged217 neutral callbacks; no runtime caller. */
#include "native_source_sha256.h"
struct n219_kernel_context { struct n217_kernel_context base;struct n219_sha256 hash; };
_Static_assert(offsetof(struct n219_kernel_context,base)==0,"neutral217context prefix");
static struct n217_state n219_kernel_state;
static int n219_hash_begin(void *opaque)
{ n219_sha256_init(&((struct n219_kernel_context *)opaque)->hash);return 0; }
static int n219_hash_update(void *opaque,const void *raw,unsigned int bytes)
{ return n219_sha256_update(&((struct n219_kernel_context *)opaque)->hash,raw,bytes); }
static int n219_hash_end(void *opaque,n209_u8 *out)
{ return n219_sha256_final(&((struct n219_kernel_context *)opaque)->hash,out); }
/* Independent spent states do not establish global no-replay across APIs.
 * A future caller must select219only and prove217unreachable, or add a reviewed
 * shared destination-consumption seam. There is no caller in this version. */
int __used n219_ingest_current(const struct n217_request *request,struct n217_result *result)
{
    static const struct n217_io io={n217_owner,n217_hold,n217_read,n217_put,n219_hash_begin,n219_hash_update,n219_hash_end,
                                   n217_write_destination,n217_read_destination,n217_clear_destination};
    struct n219_kernel_context ctx;n209_u8 *stage=NULL;int error;
    if(!result)return -EINVAL;
    if(!mutex_trylock(&n210_lock))return -EBUSY;
    if(n219_kernel_state.spent){mutex_unlock(&n210_lock);return -EALREADY;}
    memset(&ctx,0,sizeof(ctx));error=n210_linux_context(&ctx.base.identity);
    ctx.base.identity.page_reserved=n210_pages();ctx.base.identity.pid1=task_pid_nr(current)==1;ctx.base.identity.cap_sys_boot=capable(CAP_SYS_BOOT);
    if(error||ctx.base.identity.page_reserved!=1||ctx.base.identity.pid1!=1||ctx.base.identity.cap_sys_boot!=1||n210_result.status!=1){error=-EPERM;goto early;}
    memcpy(&ctx.base.destination,&n210_destination,96);
    stage=(n209_u8 *)get_zeroed_page(GFP_KERNEL);if(!stage){error=-ENOMEM;goto early;}
    error=n217_consume(request,&ctx.base.destination,&ctx.base.identity,&n210_result,&n219_kernel_state,&io,&ctx,stage,N217_CHUNK);
    goto done;
 early:
    n219_kernel_state.spent=1;memset(&n219_kernel_state.result,0,sizeof(n219_kernel_state.result));
    memcpy(n219_kernel_state.result.magic,"N217RCP1",8);n219_kernel_state.result.schema=1;n219_kernel_state.result.bytes=352;
    n219_kernel_state.result.status=2;n219_kernel_state.result.error_code=(n209_u32)-error;
 done:
    memcpy(result,&n219_kernel_state.result,sizeof(*result));
    if(stage){memzero_explicit(stage,N217_CHUNK);free_page((unsigned long)stage);}
    memzero_explicit(&ctx.hash,sizeof(ctx.hash));mutex_unlock(&n210_lock);return error;
}
const unsigned char n219_size_sha_state[sizeof(struct n219_sha256)] __used={0};
const unsigned char n219_size_kernel_context[sizeof(struct n219_kernel_context)] __used={0};
struct n219_cpio_dir_layout { struct list_head list;char *name;time_t mtime; };
_Static_assert(sizeof(struct n219_cpio_dir_layout)==32,"pinned stock dir_entry field layout");
const unsigned char n219_size_cpio_dir[sizeof(struct n219_cpio_dir_layout)] __used={0};
