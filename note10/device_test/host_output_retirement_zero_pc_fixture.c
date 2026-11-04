/* SPDX-License-Identifier: GPL-2.0-only */
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h>
#define NEED(x) do { if(!(x)) { fprintf(stderr,"new retirement check failed line %d\n",__LINE__);exit(1); } } while(0)
struct allocation { unsigned char *data;size_t bytes,stores,reads;unsigned int live; };
static struct allocation allocations[8];
static size_t attempts,successes,free_calls,real_free_returns,prefill_bytes,stores,reads,free_observed_bytes,free_nonzero_bytes;
static size_t retirements,zero_calls,scan_calls,reported_bytes,refusals,copy_calls,copied_bytes;
static unsigned int malloc_failure_observed;
static void stored(const volatile unsigned char *p);
static void read_zero(const volatile unsigned char *p,unsigned char value);
#define N10_ZERO_RETIRE_PC_STORED(p) stored(p)
#define N10_ZERO_RETIRE_PC_READ(p,value) read_zero(p,value)
#include "host_output_retirement_zero_pc.h"
void *__real_malloc(size_t);
void __real_free(void *);
void *__wrap_malloc(size_t bytes)
{
    unsigned char *p;size_t i;++attempts;p=__real_malloc(bytes);
    if(!p) { malloc_failure_observed=1;return NULL; }
    NEED(bytes>0 && bytes<=4096);
    for(i=0;i<8 && allocations[i].live;++i) { }
    NEED(i<8);allocations[i]=(struct allocation){p,bytes,0,0,1};
    memset(p,0xa5,bytes);prefill_bytes+=bytes;++successes;return p;
}
static struct allocation *owned(const volatile unsigned char *p)
{
    size_t i;uintptr_t address=(uintptr_t)p;
    for(i=0;i<8;++i) if(allocations[i].live && address>=(uintptr_t)allocations[i].data &&
        address-(uintptr_t)allocations[i].data<allocations[i].bytes) return &allocations[i];
    NEED(0);return NULL;
}
static void stored(const volatile unsigned char *p)
{
    struct allocation *a=owned(p);NEED(a->stores<a->bytes && p==a->data+a->stores && a->reads==0);
    ++a->stores;++stores;
}
static void read_zero(const volatile unsigned char *p,unsigned char value)
{
    struct allocation *a=owned(p);NEED(a->stores==a->bytes && a->reads<a->bytes && p==a->data+a->reads);
    NEED(value==0);++a->reads;++reads;
}
void __wrap_free(void *pointer)
{
    struct allocation *a=owned(pointer);size_t i;const volatile unsigned char *p=pointer;
    NEED(pointer==a->data && a->stores==a->bytes && a->reads==a->bytes);
    /* Independent observation at the matching free boundary, still live. */
    for(i=0;i<a->bytes;++i) { unsigned char value=p[i];++free_observed_bytes;if(value)++free_nonzero_bytes; }
    NEED(free_nonzero_bytes==0);++free_calls;__real_free(pointer);++real_free_returns;
    /* Control metadata only from this point; never dereference freed storage. */
    a->live=0;a->data=NULL;a->bytes=0;
}
static unsigned char source[4096];
static void begin(struct n10_zero_retire_pc *c,size_t bytes,struct n10_lease_pc_token *t)
{ NEED(!n10_zero_retire_pc_begin(c,bytes,t));NEED(c->writer.owner.storage && c->writer.owner.capacity==bytes); }
static void reject(struct n10_zero_retire_pc *c,struct n10_lease_pc_token *t)
{
    size_t before_stores=stores,before_reads=reads,before_frees=free_calls;
    struct n10_zero_retire_pc_observation report=c->observation;
    struct n10_lease_pc_token token=*t;
    NEED(n10_zero_retire_pc_retire(c,t));
    NEED(stores==before_stores && reads==before_reads && free_calls==before_frees);
    NEED(c->observation.zero_calls==report.zero_calls && c->observation.scanned_bytes==report.scanned_bytes &&
        c->observation.cleanup_called==report.cleanup_called && t->owner==token.owner && t->generation==token.generation);
    ++refusals;
}
static void retire(struct n10_zero_retire_pc *c,struct n10_lease_pc_token *t,size_t bytes)
{
    uint64_t generation=t->generation;NEED(!n10_zero_retire_pc_retire(c,t));
    NEED(c->observation.capacity==bytes && c->observation.generation==generation &&
        c->observation.zero_calls==1 && c->observation.scan_calls==1 && c->observation.zero_bytes==bytes &&
        c->observation.scanned_bytes==bytes && c->observation.nonzero_bytes==0 &&
        c->observation.zero_observed_before_free && c->observation.cleanup_called && c->observation.cleanup_returned);
    NEED(!t->owner && !t->generation && !c->writer.owner.storage && !c->writer.owner.capacity && c->writer.phase==N10_WRITER_PC_IDLE);
    zero_calls+=c->observation.zero_calls;scan_calls+=c->observation.scan_calls;reported_bytes+=bytes;
    copy_calls+=c->writer.copy_calls;copied_bytes+=c->writer.written;++retirements;
}
static void full_and_borrowed(void)
{
    struct n10_zero_retire_pc c={0};struct n10_lease_pc_token producer={0},borrow={0};
    begin(&c,32,&producer);NEED(!n10_writer_pc_append(&c.writer,&producer,0,source,32));
    NEED(!n10_writer_pc_finalize(&c.writer,&producer,1)); /* existing caller assertion only */
    NEED(!n10_writer_pc_acquire(&c.writer,&producer,&borrow));reject(&c,&producer);
    NEED(!n10_writer_pc_release(&c.writer,&borrow));retire(&c,&producer,32);
}
static void partial_error(void)
{
    struct n10_zero_retire_pc c={0};struct n10_lease_pc_token t={0};size_t i;
    begin(&c,79,&t);NEED(!n10_writer_pc_append(&c.writer,&t,0,source,17));
    NEED(n10_writer_pc_append(&c.writer,&t,18,source,1));NEED(c.writer.written==17);
    for(i=17;i<79;++i)NEED(c.writer.owner.storage[i]==0xa5);
    retire(&c,&t,79);
}
static void foreign_stale_double(void)
{
    struct n10_zero_retire_pc a={0},b={0};struct n10_lease_pc_token ta={0},tb={0},bad,old;
    begin(&a,23,&ta);begin(&b,31,&tb);reject(&a,&tb);bad=ta;bad.generation=0;reject(&a,&bad);
    old=ta;retire(&a,&ta,23);reject(&a,&old);retire(&b,&tb,31);
}
static void new_generation(void)
{
    struct n10_zero_retire_pc c={0};struct n10_lease_pc_token t={0},old;
    begin(&c,41,&t);old=t;retire(&c,&t,41);begin(&c,37,&t);NEED(t.generation>old.generation);
    reject(&c,&old);retire(&c,&t,37);
}
static void bounds_and_maximum(void)
{
    struct n10_zero_retire_pc c={0};struct n10_lease_pc_token t={0};size_t before=attempts;
    NEED(n10_zero_retire_pc_begin(&c,0,&t));NEED(n10_zero_retire_pc_begin(&c,4097,&t));
    NEED(attempts==before && c.writer.owner.allocation_attempts==0);
    begin(&c,4096,&t);NEED(!n10_writer_pc_append(&c.writer,&t,0,source,4096));retire(&c,&t,4096);
}
int main(void)
{
    size_t i;for(i=0;i<sizeof(source);++i)source[i]=(unsigned char)(17*i+93);
    full_and_borrowed();partial_error();foreign_stale_double();new_generation();bounds_and_maximum();
    NEED(attempts==7 && successes==7 && free_calls==7 && real_free_returns==7 && retirements==7 && refusals==5);
    NEED(prefill_bytes==4339 && stores==4339 && reads==4339 && free_observed_bytes==4339 && free_nonzero_bytes==0);
    NEED(zero_calls==7 && scan_calls==7 && reported_bytes==4339 && copy_calls==3 && copied_bytes==4145);
    printf("{\"schema\":\"n10-host-output-retirement-zero-fixture-pc-v1\",\"passed\":true,\"cases\":5,"
        "\"owner_allocation_attempts\":%zu,\"owner_allocations\":%zu,\"matching_free_calls\":%zu,\"real_free_returns\":%zu,"
        "\"retirements\":%zu,\"refused_retirements\":%zu,\"allocator_prefill_bytes\":%zu,\"volatile_zero_stores\":%zu,"
        "\"module_scan_reads\":%zu,\"free_boundary_observed_bytes\":%zu,\"free_boundary_nonzero_bytes\":%zu,"
        "\"zero_calls\":%zu,\"scan_calls\":%zu,\"reported_capacity_bytes\":%zu,\"writer_copy_calls\":%zu,\"writer_copied_bytes\":%zu,"
        "\"max_capacity\":4096,\"zero_observed_before_free\":true,\"after_free_reads\":0,\"secure_erasure_attested\":false,"
        "\"single_threaded\":true,\"security_boundary\":false,\"ownership_attested\":false,\"global_RAM_ownership\":false,"
        "\"native_executed\":false,\"hardware_operations\":0,\"real_decoder_calls\":0,\"malloc_failure_observed\":%s}\n",
        attempts,successes,free_calls,real_free_returns,retirements,refusals,prefill_bytes,stores,reads,free_observed_bytes,free_nonzero_bytes,
        zero_calls,scan_calls,reported_bytes,copy_calls,copied_bytes,malloc_failure_observed?"true":"false");
    return 0;
}
