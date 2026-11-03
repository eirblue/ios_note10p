/* SPDX-License-Identifier: GPL-2.0-only */
#include <stdio.h>
#include "host_output_writer_pc.h"
#define CHECK(x) do { if (!(x)) { fprintf(stderr,"new writer check failed at line %d\n",__LINE__); return 1; } } while (0)
static unsigned char source[4096];
static uint64_t attempts,allocations,frees,copies,copied_bytes;
static unsigned int malloc_failure_seen;
static int begin(struct n10_writer_pc *w,size_t n,struct n10_lease_pc_token *t)
{
    int rc=n10_writer_pc_begin(w,n,t);
    if(w->owner.malloc_failure_observed) malloc_failure_seen=1;
    return rc;
}
/* Aggregate completed generations/groups only; failures mark counters incomplete. */
static void account_copies(const struct n10_writer_pc *w) { copies+=w->copy_calls; copied_bytes+=w->written; }
static void account_owner(const struct n10_writer_pc *w) { attempts+=w->owner.allocation_attempts; allocations+=w->owner.allocations; frees+=w->owner.frees; }
static int full_content(const struct n10_writer_pc *w)
{
    /* Never inspect an unwritten tail or a retired allocation. */
    CHECK(w->phase==N10_WRITER_PC_WRITING && w->written==w->owner.capacity && w->owner.storage);
    CHECK(!memcmp(w->owner.storage,source,w->written)); return 0;
}
static int valid_prefix(void)
{
    struct n10_writer_pc w={0}; struct n10_lease_pc_token t={0},borrow={0};
    const unsigned char *p=NULL; size_t n=0;
    CHECK(!begin(&w,32,&t)); CHECK(!n10_writer_pc_append(&w,&t,0,source,7));
    CHECK(!n10_writer_pc_append(&w,&t,7,source+7,25)); CHECK(w.copy_calls==2 && w.written==32);
    CHECK(!full_content(&w)); CHECK(!n10_writer_pc_finalize(&w,&t,1)); CHECK(!n10_writer_pc_acquire(&w,&t,&borrow));
    CHECK(!n10_writer_pc_view(&w,&borrow,&p,&n)); CHECK(n==32 && !memcmp(p,source,n)); p=NULL;
    CHECK(n10_writer_pc_cleanup(&w,&t)); CHECK(w.owner.frees==0);
    CHECK(!n10_writer_pc_release(&w,&borrow)); CHECK(!n10_writer_pc_cleanup(&w,&t));
    account_copies(&w); account_owner(&w); return 0;
}
static int invalid_ranges(void)
{
    struct n10_writer_pc w={0}; struct n10_lease_pc_token t={0}; unsigned char *owned=NULL; size_t capacity=0;
    CHECK(!begin(&w,16,&t)); CHECK(!n10_writer_pc_append(&w,&t,0,source,4));
    CHECK(n10_writer_pc_append(&w,&t,4,NULL,1)); CHECK(n10_writer_pc_append(&w,&t,4,source,0));
    CHECK(n10_writer_pc_append(&w,&t,4,source,SIZE_MAX)); CHECK(n10_writer_pc_append(&w,&t,SIZE_MAX,source,1));
    CHECK(n10_writer_pc_append(&w,&t,6,source,1)); CHECK(n10_writer_pc_append(&w,&t,0,source,1));
    CHECK(n10_writer_pc_append(&w,&t,4,source,13));
    CHECK(!n10_host_output_pc_write_buffer(&w.owner,&owned,&capacity)); CHECK(capacity==16);
    /* This initialized prefix is a readable source, but belongs to the FULL
     * owned allocation and must be refused even for adjacent copy intervals. */
    CHECK(n10_writer_pc_append(&w,&t,4,owned,4)); owned=NULL;
    CHECK(w.written==4 && w.copy_calls==1 && !memcmp(w.owner.storage,source,4));
    CHECK(!n10_writer_pc_append(&w,&t,4,source+4,12)); CHECK(!full_content(&w));
    CHECK(!n10_writer_pc_finalize(&w,&t,1)); CHECK(!n10_writer_pc_cleanup(&w,&t));
    account_copies(&w); account_owner(&w); return 0;
}
static int exact_finalize(void)
{
    struct n10_writer_pc w={0}; struct n10_lease_pc_token t={0};
    CHECK(!begin(&w,8,&t)); CHECK(!n10_writer_pc_append(&w,&t,0,source,3));
    CHECK(n10_writer_pc_finalize(&w,&t,1)); CHECK(n10_writer_pc_finalize(&w,&t,0));
    CHECK(w.written==3 && w.copy_calls==1 && w.owner.frees==0 && w.owner.phase==N10_HOST_OUTPUT_PC_ALLOCATED);
    CHECK(!n10_writer_pc_append(&w,&t,3,source+3,5)); CHECK(!full_content(&w));
    CHECK(n10_writer_pc_finalize(&w,&t,0)); CHECK(n10_writer_pc_finalize(&w,&t,2));
    CHECK(w.written==8 && w.copy_calls==2 && w.owner.frees==0 && w.owner.phase==N10_HOST_OUTPUT_PC_ALLOCATED);
    CHECK(!n10_writer_pc_finalize(&w,&t,1)); CHECK(!n10_writer_pc_cleanup(&w,&t));
    account_copies(&w); account_owner(&w); return 0;
}
static int frozen_and_stale(void)
{
    struct n10_writer_pc w={0}; struct n10_lease_pc_token old={0},fresh={0},borrow={0};
    CHECK(!begin(&w,8,&old)); CHECK(!n10_writer_pc_append(&w,&old,0,source,8)); CHECK(!n10_writer_pc_finalize(&w,&old,1));
    CHECK(n10_writer_pc_append(&w,&old,0,source,1)); CHECK(!n10_writer_pc_acquire(&w,&old,&borrow));
    CHECK(n10_writer_pc_append(&w,&old,0,source,1)); CHECK(!n10_writer_pc_release(&w,&borrow));
    CHECK(n10_writer_pc_append(&w,&old,0,source,1)); CHECK(!n10_writer_pc_cleanup(&w,&old));
    CHECK(n10_writer_pc_append(&w,&old,0,source,1)); CHECK(w.written==8 && w.copy_calls==1); account_copies(&w);
    CHECK(!begin(&w,8,&fresh)); CHECK(fresh.generation>old.generation);
    CHECK(n10_writer_pc_append(&w,&old,0,source,1)); CHECK(n10_writer_pc_finalize(&w,&old,1));
    CHECK(w.written==0 && w.copy_calls==0);
    CHECK(!n10_writer_pc_append(&w,&fresh,0,source,8)); CHECK(!full_content(&w));
    CHECK(!n10_writer_pc_finalize(&w,&fresh,1)); CHECK(!n10_writer_pc_cleanup(&w,&fresh));
    account_copies(&w); account_owner(&w); return 0;
}
static int abort_and_maximum(void)
{
    struct n10_writer_pc w={0}; struct n10_lease_pc_token t={0},borrow={0};
    const unsigned char *p=NULL; size_t n=0;
    CHECK(!begin(&w,16,&t)); CHECK(!n10_writer_pc_append(&w,&t,0,source,4)); CHECK(n10_writer_pc_finalize(&w,&t,1));
    CHECK(w.owner.frees==0); CHECK(!n10_writer_pc_cleanup(&w,&t)); account_copies(&w);
    CHECK(!begin(&w,4096,&t)); CHECK(!n10_writer_pc_append(&w,&t,0,source,sizeof(source)));
    CHECK(!full_content(&w)); CHECK(!n10_writer_pc_finalize(&w,&t,1)); CHECK(!n10_writer_pc_acquire(&w,&t,&borrow));
    CHECK(!n10_writer_pc_view(&w,&borrow,&p,&n)); CHECK(n==sizeof(source) && !memcmp(p,source,n)); p=NULL;
    CHECK(!n10_writer_pc_release(&w,&borrow)); CHECK(!n10_writer_pc_cleanup(&w,&t));
    account_copies(&w); account_owner(&w); return 0;
}
int main(void)
{
    unsigned int i,cases=1; int failed;
    for(i=0;i<sizeof(source);++i) source[i]=(unsigned char)(i+1);
    failed=valid_prefix();
    if(!failed) { ++cases; failed=invalid_ranges(); }
    if(!failed) { ++cases; failed=exact_finalize(); }
    if(!failed) { ++cases; failed=frozen_and_stale(); }
    if(!failed) { ++cases; failed=abort_and_maximum(); }
    printf("{\"schema\":\"n10-host-output-writer-fixture-pc-v1\",\"passed\":%s,\"cases\":%u,\"counters_complete\":%s,\"allocation_attempts\":%llu,\"allocations\":%llu,\"frees\":%llu,\"copy_calls\":%llu,\"copied_bytes\":%llu,\"malloc_failure_observed\":%s,\"single_threaded\":true,\"source_readability_attested\":false,\"verification_authenticity_attested\":false,\"ownership_attested\":false,\"security_boundary\":false,\"zeroization_proven\":false,\"real_decoder_calls\":0,\"hardware_operations\":0}\n",
        failed?"false":"true",cases,failed?"false":"true",(unsigned long long)attempts,(unsigned long long)allocations,(unsigned long long)frees,
        (unsigned long long)copies,(unsigned long long)copied_bytes,malloc_failure_seen?"true":"false");
    return failed?1:0;
}
