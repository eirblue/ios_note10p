/* SPDX-License-Identifier: GPL-2.0-only */
#include <linux/v269_watchdog_binding.h>
_Static_assert(N269_POOL_OFFSET==N240_POOL_OFFSET+sizeof(struct n240_query_receipt),"afterquery56");
_Static_assert(N269_POOL_OFFSET+sizeof(struct n269_binding)<=N226_STAGE_OFFSET,"bindinggap40");
__asm__(".globl n269_binding_storage\n.set n269_binding_storage,n226_source_pool+43664\n"
        ".type n269_binding_storage,%object\n.size n269_binding_storage,40\n");
static __always_inline void n269_emit(int error)
{
    const struct n269_binding *v=(const struct n269_binding *)(n226_source_pool+N269_POOL_OFFSET);
    pr_info("N269WDT id=%.32s boot=%.32s cycle=%.32s result=%d schema=%u state=%u error=%u cluster=%u variant=%u flags=%u watchdog_id=%u probe_cached_rate_hz=%llu reserved=%u post_shutdown=0 armed=0 autonomous_return=0 XNU=0\n",
        n210_result.build,n210_result.boot,n210_result.cycle,error,v->schema,v->state,v->error_code,v->cluster,
        v->variant,v->flags,v->watchdog_id_at_probe,(unsigned long long)v->probe_cached_rate_hz,v->reserved);
}
