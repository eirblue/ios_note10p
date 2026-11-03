/* SPDX-License-Identifier: GPL-2.0-only */
#include <stdio.h>
#include <openssl/crypto.h>
#include <openssl/opensslv.h>
#include "host_output_content_verification_pc.h"
#define CHECK(x) do { if (!(x)) { fprintf(stderr,"new verifier check failed at line %d\n",__LINE__); return 1; } } while (0)
static unsigned char source[256];
static const unsigned char expected_32[32]={0x3d,0x61,0x76,0x67,0x70,0xa9,0x22,0x85,0x89,0xda,0xeb,0xd9,0xca,0x03,0x89,0x94,0x10,0xf3,0x22,0x7f,0x13,0x2c,0x33,0x4c,0x84,0x6f,0xcf,0x6f,0xf9,0xcf,0x13,0xb4};
static const unsigned char expected_64[32]={0x32,0x34,0xce,0x6f,0xf0,0x61,0xaa,0xdc,0x6e,0x5c,0x12,0xc4,0x48,0xf4,0x83,0x60,0x17,0x47,0x24,0x77,0x58,0x15,0xe0,0x89,0xe0,0x85,0x4f,0x79,0x7d,0xfb,0x51,0x0a};
static const unsigned char expected_79[32]={0x5e,0xb2,0x80,0xf3,0xb9,0x64,0x83,0xd6,0x53,0x51,0xa3,0x5b,0x20,0xcd,0x81,0x5a,0xc3,0x59,0x64,0x03,0x9a,0xcb,0x00,0x70,0x60,0x0f,0x58,0x46,0x02,0xbf,0xf0,0x4c};
static uint64_t attempts,allocations,frees,copies,copied_bytes,seal_attempts,hash_calls,hashed_bytes,provider_successes,matches,mismatches,finalizations;
static unsigned int malloc_failure_seen,provider_error_seen;
static int begin(struct n10_verify_pc *v,size_t n,const unsigned char *expected,struct n10_lease_pc_token *t)
{
    int rc=n10_verify_pc_begin(v,n,expected,32,t);
    if(v->writer.owner.malloc_failure_observed) malloc_failure_seen=1;
    return rc;
}
static int seal(struct n10_verify_pc *v,const struct n10_lease_pc_token *t)
{
    int rc=n10_verify_pc_seal(v,t);
    if(v->provider_error) provider_error_seen=1;
    return rc;
}
/* Aggregate completed generations/groups only; failures mark incomplete. */
static void account_generation(const struct n10_verify_pc *v)
{
    copies+=v->writer.copy_calls; copied_bytes+=v->writer.written;
    seal_attempts+=v->seal_attempts; hash_calls+=v->hash_calls; hashed_bytes+=v->hashed_bytes;
    provider_successes+=v->provider_success; matches+=v->digest_match;
    if(v->provider_success && !v->digest_match) ++mismatches;
    finalizations+=v->internal_finalizations;
}
static void account_owner(const struct n10_verify_pc *v)
{ attempts+=v->writer.owner.allocation_attempts; allocations+=v->writer.owner.allocations; frees+=v->writer.owner.frees; }
static int real_match(void)
{
    struct n10_verify_pc v={0}; struct n10_lease_pc_token t={0},borrow={0}; const unsigned char *p=NULL; size_t n=0;
    CHECK(!begin(&v,64,expected_64,&t)); CHECK(!n10_verify_pc_append(&v,&t,0,source,17));
    CHECK(!n10_verify_pc_append(&v,&t,17,source+17,47)); CHECK(!seal(&v,&t));
    CHECK(v.hash_calls==1 && v.hashed_bytes==64 && v.digest_match==1 && v.internal_finalizations==1);
    CHECK(!n10_verify_pc_acquire(&v,&t,&borrow)); CHECK(!n10_verify_pc_view(&v,&borrow,&p,&n));
    CHECK(n==64 && !memcmp(p,source,n)); p=NULL;
    CHECK(n10_verify_pc_cleanup(&v,&t)); CHECK(v.writer.owner.frees==0);
    CHECK(!n10_verify_pc_release(&v,&borrow)); CHECK(!n10_verify_pc_cleanup(&v,&t));
    account_generation(&v); account_owner(&v); return 0;
}
static int expected_snapshot(void)
{
    struct n10_verify_pc v={0}; struct n10_lease_pc_token t={0}; unsigned char caller_expected[32];
    memcpy(caller_expected,expected_79,sizeof(caller_expected)); CHECK(!begin(&v,79,caller_expected,&t));
    caller_expected[0]^=0x80; CHECK(v.expected[0]==expected_79[0]);
    CHECK(!n10_verify_pc_append(&v,&t,0,source,79)); CHECK(!seal(&v,&t));
    CHECK(v.digest_match==1 && v.hash_calls==1); CHECK(!n10_verify_pc_cleanup(&v,&t));
    account_generation(&v); account_owner(&v); return 0;
}
static int actual_mismatch(void)
{
    struct n10_verify_pc v={0}; struct n10_lease_pc_token t={0},borrow={0};
    CHECK(!begin(&v,113,expected_64,&t)); CHECK(!n10_verify_pc_append(&v,&t,0,source,113));
    CHECK(seal(&v,&t)); CHECK(v.provider_success==1 && v.digest_match==0 && v.hash_calls==1);
    CHECK(v.phase==N10_VERIFY_PC_ATTEMPTED && v.writer.owner.phase==N10_HOST_OUTPUT_PC_ALLOCATED && v.writer.owner.frees==0);
    CHECK(n10_verify_pc_acquire(&v,&t,&borrow)); CHECK(n10_verify_pc_append(&v,&t,0,source,1));
    CHECK(seal(&v,&t)); CHECK(v.hash_calls==1 && v.seal_attempts==1 && v.internal_finalizations==0);
    CHECK(!n10_verify_pc_cleanup(&v,&t)); CHECK(n10_verify_pc_cleanup(&v,&t));
    account_generation(&v); account_owner(&v); return 0;
}
static int incomplete_no_hash(void)
{
    struct n10_verify_pc v={0}; struct n10_lease_pc_token t={0};
    CHECK(n10_verify_pc_begin(&v,32,NULL,32,&t)); CHECK(n10_verify_pc_begin(&v,32,expected_32,31,&t));
    CHECK(v.writer.owner.allocation_attempts==0);
    CHECK(!begin(&v,32,expected_32,&t)); CHECK(!n10_verify_pc_append(&v,&t,0,source,8));
    CHECK(seal(&v,&t)); CHECK(v.hash_calls==0 && v.seal_attempts==0 && v.phase==N10_VERIFY_PC_OPEN);
    CHECK(v.writer.owner.frees==0); CHECK(!n10_verify_pc_cleanup(&v,&t)); CHECK(seal(&v,&t));
    CHECK(v.hash_calls==0); account_generation(&v); account_owner(&v); return 0;
}
static int sealed_and_stale(void)
{
    struct n10_verify_pc v={0}; struct n10_lease_pc_token old={0},fresh={0};
    CHECK(!begin(&v,32,expected_32,&old)); CHECK(!n10_verify_pc_append(&v,&old,0,source,32)); CHECK(!seal(&v,&old));
    CHECK(seal(&v,&old)); CHECK(n10_verify_pc_append(&v,&old,0,source,1));
    CHECK(v.hash_calls==1 && v.seal_attempts==1); CHECK(!n10_verify_pc_cleanup(&v,&old)); account_generation(&v);
    CHECK(!begin(&v,32,expected_32,&fresh)); CHECK(fresh.generation>old.generation);
    CHECK(!n10_verify_pc_append(&v,&fresh,0,source,32)); CHECK(seal(&v,&old)); CHECK(v.hash_calls==0);
    CHECK(!seal(&v,&fresh)); CHECK(!n10_verify_pc_cleanup(&v,&fresh));
    account_generation(&v); account_owner(&v); return 0;
}
static void json_string(const char *text)
{
    const unsigned char *p=(const unsigned char *)text; putchar('"');
    for(;*p;++p) { if(*p=='"' || *p=='\\') printf("\\%c",*p); else if(*p<32) printf("\\u%04x",(unsigned int)*p); else putchar(*p); }
    putchar('"');
}
int main(void)
{
    unsigned int i,cases=1; int failed;
    for(i=0;i<sizeof(source);++i) source[i]=(unsigned char)((17*i+93)&255);
    failed=real_match();
    if(!failed) { ++cases; failed=expected_snapshot(); }
    if(!failed) { ++cases; failed=actual_mismatch(); }
    if(!failed) { ++cases; failed=incomplete_no_hash(); }
    if(!failed) { ++cases; failed=sealed_and_stale(); }
    printf("{\"schema\":\"n10-host-output-content-verification-fixture-pc-v1\",\"passed\":%s,\"cases\":%u,\"counters_complete\":%s,\"owner_allocation_attempts\":%llu,\"owner_allocations\":%llu,\"owner_frees\":%llu,\"payload_copy_calls\":%llu,\"copied_bytes\":%llu,\"seal_attempts\":%llu,\"hash_calls\":%llu,\"hashed_bytes\":%llu,\"provider_successes\":%llu,\"digest_matches\":%llu,\"digest_mismatches\":%llu,\"internal_finalizations\":%llu,\"provider_errors_observed\":%llu,\"malloc_failure_observed\":%s,",
        failed?"false":"true",cases,failed?"false":"true",(unsigned long long)attempts,(unsigned long long)allocations,(unsigned long long)frees,
        (unsigned long long)copies,(unsigned long long)copied_bytes,(unsigned long long)seal_attempts,(unsigned long long)hash_calls,(unsigned long long)hashed_bytes,
        (unsigned long long)provider_successes,(unsigned long long)matches,(unsigned long long)mismatches,(unsigned long long)finalizations,(unsigned long long)provider_error_seen,malloc_failure_seen?"true":"false");
    printf("\"provider_internal_allocations_counted\":false,\"provider\":{\"api\":\"OpenSSL SHA256\",\"digest_bytes\":32,\"compile_version_text\":"); json_string(OPENSSL_VERSION_TEXT);
    printf(",\"compile_version_number\":%lu,\"runtime_version_text\":",(unsigned long)OPENSSL_VERSION_NUMBER); json_string(OpenSSL_version(OPENSSL_VERSION));
    printf(",\"runtime_version_number\":%lu},\"single_threaded\":true,\"expected_digest_caller_selected\":true,\"source_readability_attested\":false,\"immutable_memory_attested\":false,\"authenticity_attested\":false,\"security_boundary\":false,\"ownership_attested\":false,\"zeroization_proven\":false,\"real_decoder_calls\":0,\"hardware_operations\":0}\n",OpenSSL_version_num());
    return failed?1:0;
}
