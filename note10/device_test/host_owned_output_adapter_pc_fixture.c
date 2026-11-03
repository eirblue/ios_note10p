/* SPDX-License-Identifier: GPL-2.0-only */
#include <stdio.h>
#include "host_owned_output_adapter_pc.h"
#define CHECK(x) do { if (!(x)) { fprintf(stderr,"new adapter check failed at line %d\n",__LINE__); return 1; } } while (0)
static uint64_t attempts,allocations,frees;
static unsigned int malloc_failure_seen;
static int begin(struct n10_host_output_pc *c,size_t n)
{
    int rc=n10_host_output_pc_begin(c,n);
    if(c->malloc_failure_observed) malloc_failure_seen=1;
    return rc;
}
/* These aggregate only completed groups; main marks counters incomplete on failure. */
static void account(const struct n10_host_output_pc *c)
{
    attempts+=c->allocation_attempts; allocations+=c->allocations; frees+=c->frees;
}
static int initialize(struct n10_host_output_pc *c)
{
    unsigned char *p=NULL; size_t i,n=0;
    CHECK(!n10_host_output_pc_write_buffer(c,&p,&n));
    for(i=0;i<n;++i) p[i]=(unsigned char)(i+1);
    /* Do not keep a producer pointer across offer/retirement. */
    p=NULL;
    return 0;
}
static int real_lifecycle(void)
{
    struct n10_host_output_pc c={0}; struct n10_lease_pc_token t={0};
    const unsigned char *p=NULL; size_t i,n=0;
    CHECK(!begin(&c,32)); CHECK(c.allocations==1 && c.frees==0);
    CHECK(!initialize(&c)); CHECK(!n10_host_output_pc_complete(&c,32,1));
    CHECK(!n10_host_output_pc_acquire(&c,&t)); CHECK(!n10_host_output_pc_view(&c,&t,&p,&n));
    CHECK(n==32); for(i=0;i<n;++i) CHECK(p[i]==(unsigned char)(i+1)); p=NULL;
    CHECK(n10_host_output_pc_cleanup(&c)); CHECK(c.frees==0);
    CHECK(!n10_host_output_pc_release(&c,&t)); CHECK(n10_host_output_pc_acquire(&c,&t));
    CHECK(!n10_host_output_pc_cleanup(&c)); CHECK(c.frees==1 && c.storage==NULL);
    CHECK(n10_host_output_pc_cleanup(&c)); CHECK(c.frees==1);
    CHECK(n10_host_output_pc_view(&c,&t,&p,&n)); CHECK(n10_host_output_pc_release(&c,&t));
    account(&c); return 0;
}
static int allocation_boundaries(void)
{
    struct n10_host_output_pc c={0};
    CHECK(begin(&c,0)); CHECK(begin(&c,N10_HOST_OUTPUT_PC_MAX+1)); CHECK(c.allocation_attempts==0);
    CHECK(!begin(&c,N10_HOST_OUTPUT_PC_MAX)); CHECK(begin(&c,16)); CHECK(c.allocation_attempts==1);
    CHECK(!n10_host_output_pc_cleanup(&c)); CHECK(n10_host_output_pc_cleanup(&c));
    CHECK(c.allocations==1 && c.frees==1); account(&c); return 0;
}
static int completion_and_setup_rollback(void)
{
    struct n10_host_output_pc short_write={0},unverified={0},setup_fault={0};
    struct n10_lease_pc_token t={0};
    CHECK(!begin(&short_write,32)); CHECK(n10_host_output_pc_complete(&short_write,31,1));
    CHECK(short_write.frees==1 && short_write.storage==NULL); CHECK(n10_host_output_pc_acquire(&short_write,&t));
    CHECK(n10_host_output_pc_cleanup(&short_write)); CHECK(short_write.frees==1);
    CHECK(!begin(&unverified,32)); CHECK(n10_host_output_pc_complete(&unverified,32,0));
    CHECK(unverified.frees==1 && unverified.storage==NULL); CHECK(n10_host_output_pc_acquire(&unverified,&t));
    CHECK(!begin(&setup_fault,32));
    /* Deliberate logical-state fault injection, not a legitimate API action or
     * an ownership/security test: force the carried offer function to refuse. */
    setup_fault.lease.phase=N10_LEASE_PC_READY;
    CHECK(n10_host_output_pc_complete(&setup_fault,32,1)); CHECK(setup_fault.frees==1 && setup_fault.storage==NULL);
    CHECK(n10_host_output_pc_acquire(&setup_fault,&t)); CHECK(t.owner==0 && t.generation==0);
    CHECK(n10_host_output_pc_cleanup(&setup_fault)); CHECK(setup_fault.frees==1);
    account(&short_write); account(&unverified); account(&setup_fault); return 0;
}
static int generation_lifetime(void)
{
    struct n10_host_output_pc c={0},last_generation={0}; struct n10_lease_pc_token old={0},fresh={0};
    const unsigned char *p=NULL; size_t n=0;
    CHECK(!begin(&c,32)); CHECK(!initialize(&c)); CHECK(!n10_host_output_pc_complete(&c,32,1));
    CHECK(!n10_host_output_pc_acquire(&c,&old)); CHECK(!n10_host_output_pc_release(&c,&old)); CHECK(!n10_host_output_pc_cleanup(&c));
    CHECK(!begin(&c,32)); CHECK(c.generation==2); CHECK(!initialize(&c)); CHECK(!n10_host_output_pc_complete(&c,32,1));
    CHECK(!n10_host_output_pc_acquire(&c,&fresh)); CHECK(fresh.generation>old.generation);
    CHECK(n10_host_output_pc_view(&c,&old,&p,&n)); CHECK(p==NULL && n==0);
    CHECK(n10_host_output_pc_release(&c,&old)); CHECK(!n10_host_output_pc_release(&c,&fresh)); CHECK(!n10_host_output_pc_cleanup(&c));
    /* Model the terminal counter value without 2^64 operations; never reset an
     * actual live instance or depend on malloc address reuse/dangling pointers. */
    last_generation.generation=UINT64_MAX;
    CHECK(begin(&last_generation,32)); CHECK(last_generation.allocation_attempts==0 && last_generation.generation==UINT64_MAX);
    CHECK(c.allocations==2 && c.frees==2); account(&c); account(&last_generation); return 0;
}
static int cross_instance(void)
{
    struct n10_host_output_pc left={0},right={0}; struct n10_lease_pc_token a={0},b={0};
    const unsigned char *p=NULL; size_t n=0;
    CHECK(!begin(&left,32)); CHECK(!begin(&right,32)); CHECK(!initialize(&left)); CHECK(!initialize(&right));
    CHECK(!n10_host_output_pc_complete(&left,32,1)); CHECK(!n10_host_output_pc_complete(&right,32,1));
    CHECK(!n10_host_output_pc_acquire(&left,&a)); CHECK(!n10_host_output_pc_acquire(&right,&b));
    CHECK(a.owner!=b.owner && a.generation==b.generation);
    CHECK(n10_host_output_pc_view(&left,&b,&p,&n)); CHECK(n10_host_output_pc_release(&right,&a));
    CHECK(n10_host_output_pc_cleanup(&left)); CHECK(n10_host_output_pc_cleanup(&right));
    CHECK(left.frees==0 && right.frees==0);
    CHECK(!n10_host_output_pc_release(&left,&a)); CHECK(!n10_host_output_pc_release(&right,&b));
    CHECK(!n10_host_output_pc_cleanup(&left)); CHECK(!n10_host_output_pc_cleanup(&right));
    account(&left); account(&right); return 0;
}
int main(void)
{
    unsigned int cases=1; int failed=real_lifecycle();
    if (!failed) { ++cases; failed=allocation_boundaries(); }
    if (!failed) { ++cases; failed=completion_and_setup_rollback(); }
    if (!failed) { ++cases; failed=generation_lifetime(); }
    if (!failed) { ++cases; failed=cross_instance(); }
    printf("{\"schema\":\"n10-host-owned-output-adapter-fixture-pc-v1\",\"passed\":%s,\"cases\":%u,\"counters_complete\":%s,\"allocation_attempts\":%llu,\"allocations\":%llu,\"frees\":%llu,\"malloc_failure_observed\":%s,\"single_threaded\":true,\"caller_discipline_required\":true,\"ownership_attested\":false,\"security_boundary\":false,\"payload_zeroization_proven\":false,\"real_decoder_calls\":0,\"hardware_operations\":0}\n",
        failed?"false":"true",cases,failed?"false":"true",(unsigned long long)attempts,(unsigned long long)allocations,(unsigned long long)frees,malloc_failure_seen?"true":"false");
    return failed?1:0;
}
