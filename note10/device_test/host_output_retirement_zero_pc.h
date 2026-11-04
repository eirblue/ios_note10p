/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef N10_HOST_OUTPUT_RETIREMENT_ZERO_PC_H
#define N10_HOST_OUTPUT_RETIREMENT_ZERO_PC_H
#include "host_output_writer_pc.h"
/* Hosted PC only, single-threaded and caller disciplined. Control and writable
 * token must remain independent live C objects, not copied/reset/mutated or placed
 * inside payload storage. Logical tokens are forgeable, not security capabilities.
 * Volatile stores and observed bytes BEFORE free do not attest bytes AFTER free,
 * secure erasure, allocator internals, hardware/global RAM or a target handoff. */
struct n10_zero_retire_pc_observation {
    size_t capacity,zero_bytes,scanned_bytes,nonzero_bytes;
    uint64_t generation;
    unsigned int zero_calls,scan_calls,zero_observed_before_free,cleanup_called,cleanup_returned;
};
struct n10_zero_retire_pc {
    struct n10_writer_pc writer;
    struct n10_zero_retire_pc_observation observation;
};
#ifndef N10_ZERO_RETIRE_PC_STORED
#define N10_ZERO_RETIRE_PC_STORED(p) do { } while(0)
#endif
#ifndef N10_ZERO_RETIRE_PC_READ
#define N10_ZERO_RETIRE_PC_READ(p,value) do { } while(0)
#endif
static inline int n10_zero_retire_pc_begin(struct n10_zero_retire_pc *c,size_t capacity,struct n10_lease_pc_token *producer)
{
    int rc;
    if(!c || !producer) return N10_HOST_OUTPUT_PC_INVALID;
    rc=n10_writer_pc_begin(&c->writer,capacity,producer);
    if(!rc) c->observation=(struct n10_zero_retire_pc_observation){0};
    return rc;
}
static inline int n10_zero_retire_pc_retire(struct n10_zero_retire_pc *c,struct n10_lease_pc_token *producer)
{
    struct n10_writer_pc *w;struct n10_zero_retire_pc_observation out={0};
    volatile unsigned char *p;size_t i;int rc;
    if(!c || !n10_writer_pc_current(&c->writer,producer)) return N10_HOST_OUTPUT_PC_INVALID;
    w=&c->writer;
    /* Reject borrowed/foreign/stale/duplicate state BEFORE touching payload. */
    if(w->phase==N10_WRITER_PC_WRITING) {
        if(w->owner.phase!=N10_HOST_OUTPUT_PC_ALLOCATED ||
            (w->owner.lease.phase!=N10_LEASE_PC_EMPTY && w->owner.lease.phase!=N10_LEASE_PC_RETIRED)) return N10_HOST_OUTPUT_PC_INVALID;
    } else if(w->phase==N10_WRITER_PC_FROZEN) {
        if(w->owner.phase!=N10_HOST_OUTPUT_PC_OFFERED ||
            (w->owner.lease.phase!=N10_LEASE_PC_READY && w->owner.lease.phase!=N10_LEASE_PC_RELEASED) ||
            !n10_lease_pc_matches(&w->owner.lease,producer) || w->owner.lease.data!=w->owner.storage ||
            w->owner.lease.length!=w->owner.capacity) return N10_HOST_OUTPUT_PC_INVALID;
    } else return N10_HOST_OUTPUT_PC_INVALID;
    if(!w->owner.storage || !w->owner.capacity || w->owner.capacity>N10_HOST_OUTPUT_PC_MAX ||
        w->written>w->owner.capacity || w->owner.frees==UINT64_MAX ||
        (uintptr_t)w->owner.storage>UINTPTR_MAX-w->owner.capacity) return N10_HOST_OUTPUT_PC_INVALID;
    out.capacity=w->owner.capacity;out.generation=w->generation;p=w->owner.storage;
    out.zero_calls=1;
    for(i=0;i<out.capacity;++i) { p[i]=0;++out.zero_bytes;N10_ZERO_RETIRE_PC_STORED(p+i); }
    out.scan_calls=1;
    for(i=0;i<out.capacity;++i) {
        unsigned char value=p[i];++out.scanned_bytes;if(value)++out.nonzero_bytes;
        N10_ZERO_RETIRE_PC_READ(p+i,value);
    }
    out.zero_observed_before_free=out.nonzero_bytes==0;
    out.cleanup_called=1;rc=n10_writer_pc_cleanup(w,producer);out.cleanup_returned=rc==0;
    if(!rc) { producer->owner=0;producer->generation=0; }
    c->observation=out;
    return !rc && out.zero_observed_before_free ? N10_HOST_OUTPUT_PC_OK : N10_HOST_OUTPUT_PC_INVALID;
}
#endif
