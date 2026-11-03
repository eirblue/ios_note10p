/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef N10_READONLY_OUTPUT_LEASE_PC_H
#define N10_READONLY_OUTPUT_LEASE_PC_H
#include <stddef.h>
#include <stdint.h>
/* Single-threaded PC logical protocol only. Caller assertions and copied tokens
 * are forgeable; this is neither an ownership attestation nor a security boundary.
 * No payload access, allocation, keepalive, cleanup or raw-pointer revocation. */
enum n10_lease_pc_phase { N10_LEASE_PC_EMPTY, N10_LEASE_PC_READY,
    N10_LEASE_PC_BORROWED, N10_LEASE_PC_RELEASED, N10_LEASE_PC_RETIRED };
struct n10_lease_pc_assertion {
    const unsigned char *data;
    size_t capacity, written;
    uint64_t owner, generation;
    unsigned int synthetic_owner, live, verified;
};
struct n10_lease_pc_token { uint64_t owner, generation; };
struct n10_lease_pc {
    const unsigned char *data;
    size_t length;
    uint64_t owner, generation;
    enum n10_lease_pc_phase phase;
};
/* State must start zero-initialized. One total borrow per offered generation.
 * A later offer requires retirement and a strictly greater generation; callers
 * must not reset or externally mutate state while relying on this protocol. */
static inline int n10_lease_pc_offer(struct n10_lease_pc *s,
    const struct n10_lease_pc_assertion *a)
{
    uintptr_t length;
    if (!s || !a || (s->phase!=N10_LEASE_PC_EMPTY && s->phase!=N10_LEASE_PC_RETIRED) ||
        !a->data || !a->capacity || a->written!=a->capacity || !a->owner || !a->generation ||
        a->synthetic_owner!=1 || a->live!=1 || a->verified!=1 || a->generation<=s->generation) return -1;
    length=(uintptr_t)a->capacity;
    if ((size_t)length!=a->capacity || length>UINTPTR_MAX-(uintptr_t)a->data) return -1;
    s->data=a->data; s->length=a->written; s->owner=a->owner;
    s->generation=a->generation; s->phase=N10_LEASE_PC_READY;
    return 0;
}
static inline int n10_lease_pc_matches(const struct n10_lease_pc *s,
    const struct n10_lease_pc_token *t)
{
    return s && t && t->owner==s->owner && t->generation==s->generation;
}
static inline int n10_lease_pc_acquire(struct n10_lease_pc *s,struct n10_lease_pc_token *t)
{
    if (!s || !t || s->phase!=N10_LEASE_PC_READY) return -1;
    t->owner=s->owner; t->generation=s->generation; s->phase=N10_LEASE_PC_BORROWED;
    return 0;
}
static inline int n10_lease_pc_view(const struct n10_lease_pc *s,
    const struct n10_lease_pc_token *t,const unsigned char **data,size_t *length)
{
    if (!n10_lease_pc_matches(s,t) || s->phase!=N10_LEASE_PC_BORROWED || !data || !length) return -1;
    *data=s->data; *length=s->length;
    return 0;
}
static inline int n10_lease_pc_release(struct n10_lease_pc *s,const struct n10_lease_pc_token *t)
{
    if (!n10_lease_pc_matches(s,t) || s->phase!=N10_LEASE_PC_BORROWED) return -1;
    s->phase=N10_LEASE_PC_RELEASED;
    return 0;
}
static inline int n10_lease_pc_retire(struct n10_lease_pc *s,const struct n10_lease_pc_token *t)
{
    if (!n10_lease_pc_matches(s,t) || (s->phase!=N10_LEASE_PC_READY && s->phase!=N10_LEASE_PC_RELEASED)) return -1;
    s->data=NULL; s->length=0; s->phase=N10_LEASE_PC_RETIRED;
    return 0;
}
#endif
