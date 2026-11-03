/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef N10_HOST_OUTPUT_WRITER_PC_H
#define N10_HOST_OUTPUT_WRITER_PC_H
#include <string.h>
#include "host_owned_output_adapter_pc.h"
enum { N10_WRITER_PC_IDLE, N10_WRITER_PC_WRITING, N10_WRITER_PC_FROZEN };
/* Single-threaded, caller-disciplined PC writer. Initialize once to zero, never
 * mutate/reset/copy active control state; keep control alive longer than handles. Source
 * readability/initialized C object extent and verification are NOT attested. */
struct n10_writer_pc {
    struct n10_host_output_pc owner;
    size_t written;
    uint64_t generation, copy_calls;
    unsigned int phase;
};
static inline int n10_writer_pc_current(const struct n10_writer_pc *w,const struct n10_lease_pc_token *t)
{
    return w && t && w->phase!=N10_WRITER_PC_IDLE && w->generation==w->owner.generation &&
        t->generation==w->generation && t->owner==n10_host_output_pc_owner(&w->owner);
}
static inline int n10_writer_pc_begin(struct n10_writer_pc *w,size_t capacity,struct n10_lease_pc_token *t)
{
    int rc;
    if (!w || !t || w->phase!=N10_WRITER_PC_IDLE) return N10_HOST_OUTPUT_PC_INVALID;
    rc=n10_host_output_pc_begin(&w->owner,capacity);
    if (rc) return rc;
    w->written=0; w->copy_calls=0; w->generation=w->owner.generation; w->phase=N10_WRITER_PC_WRITING;
    t->owner=n10_host_output_pc_owner(&w->owner); t->generation=w->generation;
    return N10_HOST_OUTPUT_PC_OK;
}
static inline int n10_writer_pc_append(struct n10_writer_pc *w,const struct n10_lease_pc_token *t,
    size_t offset,const unsigned char *source,size_t count)
{
    unsigned char *destination; size_t capacity;
    uintptr_t source_start,source_end,owned_start,owned_end,n,full;
    /* State/generation checks precede allocation-pointer work. */
    if (!n10_writer_pc_current(w,t) || w->phase!=N10_WRITER_PC_WRITING ||
        w->owner.phase!=N10_HOST_OUTPUT_PC_ALLOCATED) return N10_HOST_OUTPUT_PC_INVALID;
    capacity=w->owner.capacity;
    if (w->written>capacity || offset!=w->written || !count || !source ||
        count>capacity-w->written || w->copy_calls==UINT64_MAX) return N10_HOST_OUTPUT_PC_INVALID;
    if (n10_host_output_pc_write_buffer(&w->owner,&destination,&capacity)) return N10_HOST_OUTPUT_PC_INVALID;
    source_start=(uintptr_t)source; owned_start=(uintptr_t)destination;
    n=(uintptr_t)count; full=(uintptr_t)capacity;
    if ((size_t)n!=count || (size_t)full!=capacity || n>UINTPTR_MAX-source_start || full>UINTPTR_MAX-owned_start)
        return N10_HOST_OUTPUT_PC_INVALID;
    /* Both half-open ends are checked before comparing the FULL owned range. */
    source_end=source_start+n; owned_end=owned_start+full;
    if (source_start<owned_end && owned_start<source_end) return N10_HOST_OUTPUT_PC_INVALID;
    memcpy(destination+w->written,source,count);
    w->written+=count; ++w->copy_calls;
    return N10_HOST_OUTPUT_PC_OK;
}
/* Exact unsigned assertion1 only; it remains caller supplied, not authenticity.
 * Incomplete/false requests leave the partial allocation available, with no
 * carried complete()/rollback/free call. */
static inline int n10_writer_pc_finalize(struct n10_writer_pc *w,const struct n10_lease_pc_token *t,unsigned int verified)
{
    int rc;
    if (!n10_writer_pc_current(w,t) || w->phase!=N10_WRITER_PC_WRITING ||
        w->owner.phase!=N10_HOST_OUTPUT_PC_ALLOCATED || !w->owner.capacity ||
        w->written!=w->owner.capacity || verified!=1) return N10_HOST_OUTPUT_PC_INVALID;
    rc=n10_host_output_pc_complete(&w->owner,w->written,verified);
    w->phase=rc?N10_WRITER_PC_IDLE:N10_WRITER_PC_FROZEN;
    return rc;
}
static inline int n10_writer_pc_acquire(struct n10_writer_pc *w,const struct n10_lease_pc_token *producer,struct n10_lease_pc_token *borrower)
{
    if (!n10_writer_pc_current(w,producer) || w->phase!=N10_WRITER_PC_FROZEN) return N10_HOST_OUTPUT_PC_INVALID;
    return n10_host_output_pc_acquire(&w->owner,borrower);
}
static inline int n10_writer_pc_view(const struct n10_writer_pc *w,const struct n10_lease_pc_token *borrower,
    const unsigned char **p,size_t *n)
{
    if (!n10_writer_pc_current(w,borrower) || w->phase!=N10_WRITER_PC_FROZEN) return N10_HOST_OUTPUT_PC_INVALID;
    return n10_host_output_pc_view(&w->owner,borrower,p,n);
}
static inline int n10_writer_pc_release(struct n10_writer_pc *w,const struct n10_lease_pc_token *borrower)
{
    if (!n10_writer_pc_current(w,borrower) || w->phase!=N10_WRITER_PC_FROZEN) return N10_HOST_OUTPUT_PC_INVALID;
    return n10_host_output_pc_release(&w->owner,borrower);
}
static inline int n10_writer_pc_cleanup(struct n10_writer_pc *w,const struct n10_lease_pc_token *producer)
{
    int rc;
    if (!n10_writer_pc_current(w,producer)) return N10_HOST_OUTPUT_PC_INVALID;
    rc=n10_host_output_pc_cleanup(&w->owner);
    if (!rc) w->phase=N10_WRITER_PC_IDLE;
    return rc;
}
#endif
