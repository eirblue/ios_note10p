/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef N10_HOST_OWNED_OUTPUT_ADAPTER_PC_H
#define N10_HOST_OWNED_OUTPUT_ADAPTER_PC_H
#include <stdlib.h>
#include "readonly_output_lease_pc.h"
#define N10_HOST_OUTPUT_PC_MAX 4096u
enum { N10_HOST_OUTPUT_PC_IDLE, N10_HOST_OUTPUT_PC_ALLOCATED, N10_HOST_OUTPUT_PC_OFFERED };
enum { N10_HOST_OUTPUT_PC_OK=0, N10_HOST_OUTPUT_PC_INVALID=-1, N10_HOST_OUTPUT_PC_NO_MEMORY=-2 };
/* Hosted PC, single-threaded, caller-disciplined control object. Initialize once
 * to zero, never copy/reset/mutate it, and keep it alive longer than all handles.
 * Identity/generation are logical checks, not unforgeable security capabilities.
 * No payload read/wipe, hardware ownership, keepalive or raw-pointer revocation. */
struct n10_host_output_pc {
    struct n10_lease_pc lease;
    unsigned char *storage;
    size_t capacity;
    uint64_t generation, allocation_attempts, allocations, frees;
    unsigned int phase, malloc_failure_observed;
};
_Static_assert(sizeof(uintptr_t)<=sizeof(uint64_t),"PC control identity fits token");
static inline uint64_t n10_host_output_pc_owner(const struct n10_host_output_pc *c)
{
    return (uint64_t)(uintptr_t)c;
}
static inline int n10_host_output_pc_begin(struct n10_host_output_pc *c,size_t capacity)
{
    unsigned char *storage;
    if (!c || c->storage || c->phase!=N10_HOST_OUTPUT_PC_IDLE || !capacity || capacity>N10_HOST_OUTPUT_PC_MAX ||
        (c->lease.phase!=N10_LEASE_PC_EMPTY && c->lease.phase!=N10_LEASE_PC_RETIRED) ||
        c->generation==UINT64_MAX || c->allocation_attempts==UINT64_MAX || c->allocations==UINT64_MAX || c->frees==UINT64_MAX)
        return N10_HOST_OUTPUT_PC_INVALID;
    ++c->generation; ++c->allocation_attempts;
    storage=malloc(capacity);
    if (!storage) { c->malloc_failure_observed=1; return N10_HOST_OUTPUT_PC_NO_MEMORY; }
    ++c->allocations; c->storage=storage; c->capacity=capacity; c->phase=N10_HOST_OUTPUT_PC_ALLOCATED;
    return N10_HOST_OUTPUT_PC_OK;
}
/* Producer write access is confined to the pre-offer phase. A caller can copy
 * this pointer; the API cannot prevent later misuse or attest initialized bytes. */
static inline int n10_host_output_pc_write_buffer(struct n10_host_output_pc *c,unsigned char **p,size_t *n)
{
    if (!c || c->phase!=N10_HOST_OUTPUT_PC_ALLOCATED || !c->storage || !p || !n) return N10_HOST_OUTPUT_PC_INVALID;
    *p=c->storage; *n=c->capacity;
    return N10_HOST_OUTPUT_PC_OK;
}
/* Internal free boundary: even a direct call cannot release a normal borrowed offer. */
static inline int n10_host_output_pc_drop_allocated(struct n10_host_output_pc *c)
{
    if (!c || !c->storage || c->frees==UINT64_MAX ||
        (c->phase!=N10_HOST_OUTPUT_PC_ALLOCATED &&
         !(c->phase==N10_HOST_OUTPUT_PC_OFFERED && c->lease.phase==N10_LEASE_PC_RETIRED))) return N10_HOST_OUTPUT_PC_INVALID;
    free(c->storage); ++c->frees;
    c->storage=NULL; c->capacity=0; c->phase=N10_HOST_OUTPUT_PC_IDLE;
    return N10_HOST_OUTPUT_PC_OK;
}
/* written/verified remain caller assertions, not payload-authenticity evidence.
 * Failed completion/setup rolls back the allocation and exposes no lease. */
static inline int n10_host_output_pc_complete(struct n10_host_output_pc *c,size_t written,unsigned int verified)
{
    struct n10_lease_pc_assertion a;
    if (!c || c->phase!=N10_HOST_OUTPUT_PC_ALLOCATED || !c->storage) return N10_HOST_OUTPUT_PC_INVALID;
    if (written!=c->capacity || verified!=1) { n10_host_output_pc_drop_allocated(c); return N10_HOST_OUTPUT_PC_INVALID; }
    a.data=c->storage; a.capacity=c->capacity; a.written=written;
    a.owner=n10_host_output_pc_owner(c); a.generation=c->generation;
    a.synthetic_owner=1; a.live=1; a.verified=verified;
    if (n10_lease_pc_offer(&c->lease,&a)) { n10_host_output_pc_drop_allocated(c); return N10_HOST_OUTPUT_PC_INVALID; }
    c->phase=N10_HOST_OUTPUT_PC_OFFERED;
    return N10_HOST_OUTPUT_PC_OK;
}
static inline int n10_host_output_pc_acquire(struct n10_host_output_pc *c,struct n10_lease_pc_token *t)
{
    if (!c || c->phase!=N10_HOST_OUTPUT_PC_OFFERED || !c->storage) return N10_HOST_OUTPUT_PC_INVALID;
    return n10_lease_pc_acquire(&c->lease,t);
}
static inline int n10_host_output_pc_view(const struct n10_host_output_pc *c,const struct n10_lease_pc_token *t,
    const unsigned char **p,size_t *n)
{
    if (!c || c->phase!=N10_HOST_OUTPUT_PC_OFFERED || !c->storage) return N10_HOST_OUTPUT_PC_INVALID;
    return n10_lease_pc_view(&c->lease,t,p,n);
}
static inline int n10_host_output_pc_release(struct n10_host_output_pc *c,const struct n10_lease_pc_token *t)
{
    if (!c || c->phase!=N10_HOST_OUTPUT_PC_OFFERED || !c->storage) return N10_HOST_OUTPUT_PC_INVALID;
    return n10_lease_pc_release(&c->lease,t);
}
static inline int n10_host_output_pc_cleanup(struct n10_host_output_pc *c)
{
    struct n10_lease_pc_token owner;
    if (!c || !c->storage) return N10_HOST_OUTPUT_PC_INVALID;
    if (c->phase==N10_HOST_OUTPUT_PC_ALLOCATED) return n10_host_output_pc_drop_allocated(c);
    if (c->phase!=N10_HOST_OUTPUT_PC_OFFERED) return N10_HOST_OUTPUT_PC_INVALID;
    owner.owner=n10_host_output_pc_owner(c); owner.generation=c->generation;
    if (n10_lease_pc_retire(&c->lease,&owner)) return N10_HOST_OUTPUT_PC_INVALID;
    return n10_host_output_pc_drop_allocated(c);
}
#endif
