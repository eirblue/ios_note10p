/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef N10_HOST_OUTPUT_CONTENT_VERIFICATION_PC_H
#define N10_HOST_OUTPUT_CONTENT_VERIFICATION_PC_H
#include <openssl/sha.h>
#include "host_output_writer_pc.h"
enum { N10_VERIFY_PC_IDLE, N10_VERIFY_PC_OPEN, N10_VERIFY_PC_ATTEMPTED, N10_VERIFY_PC_SEALED };
/* Single-threaded PC wrapper only. Control/token/raw-pointer mutation remains
 * possible; C callers must use this API exclusively and keep control alive.
 * Expected digest selection/readability is a caller obligation, not authenticity.
 * API snapshot/freeze does not make memory immutable or provide isolation. */
struct n10_verify_pc {
    struct n10_writer_pc writer;
    unsigned char expected[32];
    uint64_t generation, hash_calls, hashed_bytes;
    unsigned int phase, seal_attempts, provider_success, digest_match, provider_error, internal_finalizations;
};
static inline int n10_verify_pc_current(const struct n10_verify_pc *v,const struct n10_lease_pc_token *t)
{
    return v && t && v->phase!=N10_VERIFY_PC_IDLE && v->generation==v->writer.generation && n10_writer_pc_current(&v->writer,t);
}
static inline int n10_verify_pc_begin(struct n10_verify_pc *v,size_t capacity,const unsigned char *expected,
    size_t expected_bytes,struct n10_lease_pc_token *producer)
{
    unsigned char snapshot[32]; int rc;
    if (!v || !producer || v->phase!=N10_VERIFY_PC_IDLE || !expected || expected_bytes!=sizeof(snapshot)) return N10_HOST_OUTPUT_PC_INVALID;
    /* Copy to local snapshot before allocation/token writes; source/control alias
     * must not change the meaning of the original readable32-byte input. */
    memcpy(snapshot,expected,sizeof(snapshot));
    rc=n10_writer_pc_begin(&v->writer,capacity,producer);
    if (rc) return rc;
    memcpy(v->expected,snapshot,sizeof(snapshot));
    v->generation=v->writer.generation; v->hash_calls=0; v->hashed_bytes=0;
    v->seal_attempts=0; v->provider_success=0; v->digest_match=0; v->provider_error=0; v->internal_finalizations=0;
    v->phase=N10_VERIFY_PC_OPEN;
    return N10_HOST_OUTPUT_PC_OK;
}
static inline int n10_verify_pc_append(struct n10_verify_pc *v,const struct n10_lease_pc_token *producer,
    size_t offset,const unsigned char *source,size_t count)
{
    if (!n10_verify_pc_current(v,producer) || v->phase!=N10_VERIFY_PC_OPEN) return N10_HOST_OUTPUT_PC_INVALID;
    return n10_writer_pc_append(&v->writer,producer,offset,source,count);
}
/* NO caller verified flag. Each complete generation gets at most one actual
 * hash attempt. Invalid/incomplete/stale requests read no output bytes. */
static inline int n10_verify_pc_seal(struct n10_verify_pc *v,const struct n10_lease_pc_token *producer)
{
    unsigned char digest[32],*output; size_t capacity; int rc;
    if (!n10_verify_pc_current(v,producer) || v->phase!=N10_VERIFY_PC_OPEN ||
        v->writer.phase!=N10_WRITER_PC_WRITING || v->writer.owner.phase!=N10_HOST_OUTPUT_PC_ALLOCATED ||
        !v->writer.owner.capacity || v->writer.written!=v->writer.owner.capacity) return N10_HOST_OUTPUT_PC_INVALID;
    /* Freeze before pointer acquisition/provider call: errors/mismatch cannot
     * restore append, replace the snapshot, retry seal or expose a borrower. */
    v->phase=N10_VERIFY_PC_ATTEMPTED; v->seal_attempts=1;
    if (n10_host_output_pc_write_buffer(&v->writer.owner,&output,&capacity)) return N10_HOST_OUTPUT_PC_INVALID;
    ++v->hash_calls; v->hashed_bytes=capacity;
    if (!SHA256(output,capacity,digest)) { v->provider_error=1; return N10_HOST_OUTPUT_PC_INVALID; }
    v->provider_success=1;
    if (memcmp(digest,v->expected,sizeof(digest))) return N10_HOST_OUTPUT_PC_INVALID;
    v->digest_match=1; ++v->internal_finalizations;
    rc=n10_writer_pc_finalize(&v->writer,producer,1);
    if (!rc) v->phase=N10_VERIFY_PC_SEALED;
    return rc;
}
static inline int n10_verify_pc_acquire(struct n10_verify_pc *v,const struct n10_lease_pc_token *producer,struct n10_lease_pc_token *borrower)
{
    if (!n10_verify_pc_current(v,producer) || v->phase!=N10_VERIFY_PC_SEALED) return N10_HOST_OUTPUT_PC_INVALID;
    return n10_writer_pc_acquire(&v->writer,producer,borrower);
}
static inline int n10_verify_pc_view(const struct n10_verify_pc *v,const struct n10_lease_pc_token *borrower,const unsigned char **p,size_t *n)
{
    if (!n10_verify_pc_current(v,borrower) || v->phase!=N10_VERIFY_PC_SEALED) return N10_HOST_OUTPUT_PC_INVALID;
    return n10_writer_pc_view(&v->writer,borrower,p,n);
}
static inline int n10_verify_pc_release(struct n10_verify_pc *v,const struct n10_lease_pc_token *borrower)
{
    if (!n10_verify_pc_current(v,borrower) || v->phase!=N10_VERIFY_PC_SEALED) return N10_HOST_OUTPUT_PC_INVALID;
    return n10_writer_pc_release(&v->writer,borrower);
}
static inline int n10_verify_pc_cleanup(struct n10_verify_pc *v,const struct n10_lease_pc_token *producer)
{
    int rc;
    if (!n10_verify_pc_current(v,producer)) return N10_HOST_OUTPUT_PC_INVALID;
    rc=n10_writer_pc_cleanup(&v->writer,producer);
    if (!rc) v->phase=N10_VERIFY_PC_IDLE;
    return rc;
}
#endif
