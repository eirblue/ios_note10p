/* SPDX-License-Identifier: GPL-2.0-only */
/* Included after the unchanged n210 owner in the same owner TU. No caller. */
#include <linux/fs.h>
#include <linux/highmem.h>
#include <linux/magic.h>
#include <linux/shmem_fs.h>
#include <linux/slab.h>
#include <linux/zlib.h>
#include "../../../lib/zlib_inflate/inftrees.h"
#include "../../../lib/zlib_inflate/inflate.h"
#include "../../../lib/zlib_inflate/infutil.h"
#include "native_source_ingest.h"
struct n217_kernel_context { struct n210_destination destination;struct n210_context identity;struct shash_desc *hash; };
static struct n217_state n217_kernel_state;
static int n217_owner(void *opaque,const struct n210_destination *destination)
{
    struct n217_kernel_context *ctx=opaque;struct n210_context now;
    if(memcmp(destination,&ctx->destination,96)||memcmp(destination,&n210_destination,96)||!READ_ONCE(n210_reserved))return -ESTALE;
    memset(&now,0,sizeof(now));
    if(n210_linux_context(&now)||now.return_armed!=1||memcmp(now.build,ctx->identity.build,32)||
       memcmp(now.boot,ctx->identity.boot,32)||memcmp(now.cycle,ctx->identity.cycle,32))return -ESTALE;
    return 0;
}
static int n217_hold(void *opaque,unsigned int role,n209_u64 bytes,void **held,n209_u64 *token)
{
    static const char * const paths[2]={"/n10/kernel.mem","/n10/adapter.mem"};
    struct file *file;struct inode *inode;int error;(void)opaque;
    if(role>=2)return -EINVAL;
    file=filp_open(paths[role],O_RDONLY|O_NOFOLLOW|O_LARGEFILE,0);
    if(IS_ERR(file))return PTR_ERR(file);
    inode=file_inode(file);
    if(!S_ISREG(inode->i_mode)||(inode->i_sb->s_magic!=RAMFS_MAGIC&&inode->i_sb->s_magic!=TMPFS_MAGIC)){
        filp_close(file,NULL);return -EINVAL;
    }
    error=deny_write_access(file);
    if(error){filp_close(file,NULL);return error;}
    if(i_size_read(inode)<0||(n209_u64)i_size_read(inode)!=bytes){allow_write_access(file);filp_close(file,NULL);return -EINVAL;}
    *held=file;*token=(n209_u64)(unsigned long)inode;return 0;
}
static long n217_read(void *opaque,void *held,n209_u64 offset,void *buffer,unsigned int bytes)
{ loff_t at=(loff_t)offset;(void)opaque;return (long)kernel_read(held,buffer,bytes,&at); }
static void n217_put(void *opaque,void *held)
{ (void)opaque;allow_write_access(held);filp_close(held,NULL); }
static int n217_hash_begin(void *opaque)
{ return crypto_shash_init(((struct n217_kernel_context *)opaque)->hash); }
static int n217_hash_update(void *opaque,const void *raw,unsigned int bytes)
{ return crypto_shash_update(((struct n217_kernel_context *)opaque)->hash,raw,bytes); }
static int n217_hash_end(void *opaque,n209_u8 *out)
{ return crypto_shash_final(((struct n217_kernel_context *)opaque)->hash,out); }
static int n217_page_io(void *opaque,n209_u64 offset,void *buffer,unsigned int bytes,int write,int clear)
{
    struct n217_kernel_context *ctx=opaque;struct page *page;void *mapped;unsigned long pfn;
    if(n217_owner(ctx,&ctx->destination)||offset>=N209_DESTINATION_BYTES||!bytes||bytes>N217_CHUNK||
       bytes>N209_DESTINATION_BYTES-offset||offset%PAGE_SIZE+bytes>PAGE_SIZE)return -ESTALE;
    pfn=PHYS_PFN(ctx->destination.region.base+offset);
    if(!pfn_valid(pfn))return -ESTALE;
    page=pfn_to_page(pfn);if(!PageReserved(page))return -ESTALE;
    mapped=kmap(page);if(!mapped)return -ENOMEM;
    if(clear)memset((char *)mapped+offset%PAGE_SIZE,0,bytes);
    else if(write)memcpy((char *)mapped+offset%PAGE_SIZE,buffer,bytes);
    else memcpy(buffer,(char *)mapped+offset%PAGE_SIZE,bytes);
    kunmap(page);return 0;
}
static int n217_write_destination(void *opaque,n209_u64 offset,const void *raw,unsigned int bytes)
{ return n217_page_io(opaque,offset,(void *)raw,bytes,1,0); }
static int n217_read_destination(void *opaque,n209_u64 offset,void *raw,unsigned int bytes)
{ return n217_page_io(opaque,offset,raw,bytes,0,0); }
static int n217_clear_destination(void *opaque,n209_u64 offset,n209_u64 bytes)
{
    unsigned int count;int error;
    while(bytes){count=(unsigned int)min_t(n209_u64,bytes,N217_CHUNK);error=n217_page_io(opaque,offset,NULL,count,1,1);
        if(error)return error;offset+=count;bytes-=count;}
    return 0;
}
/* Deliberately no registration, syscall, sysfs, module or PID1 caller in217. */
int __used n217_ingest_current(const struct n217_request *request,struct n217_result *result)
{
    static const struct n217_io io={n217_owner,n217_hold,n217_read,n217_put,n217_hash_begin,n217_hash_update,n217_hash_end,
                                   n217_write_destination,n217_read_destination,n217_clear_destination};
    struct n217_kernel_context ctx;struct crypto_shash *tfm=NULL;n209_u8 *stage=NULL;unsigned int desc_bytes=0;int error;
    if(!result)return -EINVAL;
    if(!mutex_trylock(&n210_lock))return -EBUSY;
    if(n217_kernel_state.spent){mutex_unlock(&n210_lock);return -EALREADY;}
    memset(&ctx,0,sizeof(ctx));error=n210_linux_context(&ctx.identity);
    ctx.identity.page_reserved=n210_pages();ctx.identity.pid1=task_pid_nr(current)==1;ctx.identity.cap_sys_boot=capable(CAP_SYS_BOOT);
    if(error||ctx.identity.page_reserved!=1||ctx.identity.pid1!=1||ctx.identity.cap_sys_boot!=1||n210_result.status!=1){error=-EPERM;goto early;}
    memcpy(&ctx.destination,&n210_destination,96);
    tfm=crypto_alloc_shash("sha256",0,0);
    if(IS_ERR(tfm)){error=PTR_ERR(tfm);tfm=NULL;goto early;}
    if(crypto_shash_digestsize(tfm)!=32||crypto_shash_descsize(tfm)>4096-sizeof(struct shash_desc)){error=-E2BIG;goto early;}
    desc_bytes=sizeof(struct shash_desc)+crypto_shash_descsize(tfm);
    ctx.hash=kmalloc(desc_bytes,GFP_KERNEL);stage=(n209_u8 *)get_zeroed_page(GFP_KERNEL);
    if(!ctx.hash||!stage){error=-ENOMEM;goto early;}
    ctx.hash->tfm=tfm;ctx.hash->flags=0;
    error=n217_consume(request,&ctx.destination,&ctx.identity,&n210_result,&n217_kernel_state,&io,&ctx,stage,N217_CHUNK);
    goto done;
 early:
    n217_kernel_state.spent=1;memset(&n217_kernel_state.result,0,sizeof(n217_kernel_state.result));
    memcpy(n217_kernel_state.result.magic,"N217RCP1",8);n217_kernel_state.result.schema=1;n217_kernel_state.result.bytes=352;
    n217_kernel_state.result.status=2;n217_kernel_state.result.error_code=(n209_u32)-error;
 done:
    memcpy(result,&n217_kernel_state.result,sizeof(*result));
    if(stage){memzero_explicit(stage,N217_CHUNK);free_page((unsigned long)stage);}
    if(ctx.hash){memzero_explicit(ctx.hash,desc_bytes);kfree(ctx.hash);}
    if(tfm)crypto_free_shash(tfm);
    mutex_unlock(&n210_lock);return error;
}
/* Target-derived type evidence only, never allocator-resident cost claims. */
#define N217_SIZE(name,type) const unsigned char n217_size_##name[sizeof(type)] __used={0}
N217_SIZE(request,struct n217_request);
N217_SIZE(result,struct n217_result);
N217_SIZE(state,struct n217_state);
N217_SIZE(kernel_context,struct n217_kernel_context);
N217_SIZE(file,struct file);
N217_SIZE(inode,struct inode);
N217_SIZE(dentry,struct dentry);
N217_SIZE(shmem_inode,struct shmem_inode_info);
N217_SIZE(radix_node,struct radix_tree_node);
N217_SIZE(zstream,z_stream);
N217_SIZE(inflate_workspace,struct inflate_workspace);
N217_SIZE(shash_desc,struct shash_desc);
#undef N217_SIZE
