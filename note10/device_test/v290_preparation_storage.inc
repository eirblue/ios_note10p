/* SPDX-License-Identifier: GPL-2.0-only */
#include "v290_preparation_storage.h"
#ifdef __KERNEL__
#define N290_STORAGE ((struct n290_storage *)(n226_source_pool+N290_STORAGE_OFFSET))
_Static_assert(N290_STORAGE_OFFSET==N279_SEAL_OFFSET+sizeof(struct n278_seal),"after immutable seal");
_Static_assert(N290_STORAGE_OFFSET+sizeof(struct n290_storage)==N226_STAGE_OFFSET,"before wiped stage");
#define N290_OWNER n217_owner
#define N290_CLEAR n217_clear_destination
#define N290_READ n217_read_destination
#define N290_LOCKED() lockdep_assert_held(&n210_lock)
#define N290_PUBLISH(s) WRITE_ONCE((s)->phase,N290_STORAGE_PREPARED)
__asm__(".globl n290_storage_alias\n.set n290_storage_alias,n226_source_pool+44896\n"
        ".type n290_storage_alias,%object\n.size n290_storage_alias,160\n");
#elif defined(N290_HOST_FIXTURE)
#define N290_OWNER n290_fixture_owner
#define N290_CLEAR n290_fixture_clear
#define N290_READ n290_fixture_read
#define N290_LOCKED() ((void)0)
#define N290_PUBLISH(s) ((s)->phase=N290_STORAGE_PREPARED)
#else
#error "290 storage adapter requires kernel or explicit host fixture"
#endif
static __attribute__((__noinline__)) int n290_readback_zero(void *opaque,const struct n210_destination *destination,
    n209_u64 offset,n209_u8 *scratch)
{
    unsigned int i;int error;
    if(N290_OWNER(opaque,destination))return -116;
    error=N290_READ(opaque,offset,scratch,N217_CHUNK);if(error)return error;
    for(i=0;i<N217_CHUNK;i++)if(scratch[i])return -5;
    return 0;
}
static __attribute__((__noinline__)) int n290_prepare_storage_locked(struct n290_storage *storage,const struct n278_seal *seal,
    const struct n210_request *request,const struct n210_destination *destination,const struct n210_context *context,
    const struct n210_receipt *prepared,void *opaque,n209_u8 *scratch,unsigned int scratch_bytes)
{
    n209_u64 at;int error;N290_LOCKED();
    if(!storage)return -22;
    if(storage->phase!=N290_EMPTY)return -114;
    if(!scratch||scratch_bytes!=N217_CHUNK||N290_OWNER(opaque,destination)){
        storage->phase=N290_REFUSED;return -116;
    }
    error=n290_plan_storage(storage,seal,request,destination,context,prepared);if(error)return error;
    for(at=storage->args_offset;at<storage->end_offset;at+=N217_CHUNK){
        if(N290_OWNER(opaque,destination)){error=-116;goto bad;}
        error=N290_CLEAR(opaque,at,N217_CHUNK);if(error)goto bad;
    }
    for(at=storage->args_offset;at<storage->end_offset;at+=N217_CHUNK){
        error=n290_readback_zero(opaque,destination,at,scratch);if(error)goto bad;
    }
    if(N290_OWNER(opaque,destination)){error=-116;goto bad;}
    N290_PUBLISH(storage);return 0;
 bad:
    storage->phase=N290_QUARANTINED;return error;
}
