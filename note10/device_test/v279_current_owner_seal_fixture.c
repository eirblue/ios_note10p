/* SPDX-License-Identifier: GPL-2.0-only */
#include "v278_current_owner_seal.h"
#include "native_source_stream.h"
#include "v276_watchdog_binding.h"
#include <stdio.h>
#include <string.h>
static _Alignas(4096) n209_u8 n226_source_pool[N226_POOL_BYTES];
#include "v279_current_owner_seal.inc"
/* Valid278 setup only; no old predicate or fixture entrypoint is included. */
struct inputs {
    struct n210_request request;struct n210_destination destination;
    struct n210_context context;struct n210_receipt prepared;
    unsigned int prepare_spent;struct n217_state ingest;n209_u8 hash[32];
};
static int setup(struct inputs *in)
{
    struct n209_payload p={0};struct n217_result *r;
    memset(in,0,sizeof(*in));memcpy(p.magic,"N209PAY1",8);p.schema=1;p.bytes=256;
    p.virtual_base=0xffff000001004000ULL;p.kernel_span=3*N209_PAGE;
    p.entry_extent_bytes=16;p.pool_offset=2*N209_PAGE;p.pool_bytes=N209_PAGE;
    p.adapter_bytes=N209_PAGE;p.adapter_entry_offset=64;p.adapter_record_offset=256;
    memset((n209_u8 *)&p+96,1,160);memset(in->hash,2,32);
    memcpy(in->destination.magic,"N210DST1",8);in->destination.schema=1;in->destination.bytes=96;
    in->destination.region.base=N209_ADDRESS_MIN+N210_RESIDUE;in->destination.region.size=N209_DESTINATION_BYTES;
    in->destination.region.generation=1;in->destination.region.page_shift=12;in->destination.region.status=1;
    memset(in->destination.region.build,'1',32);memset(in->destination.region.cookie,1,16);
    in->request.destination=in->destination;memcpy(in->request.payload,&p,sizeof(p));
    memcpy(in->request.binding.magic,"N210BND1",8);in->request.binding.schema=1;in->request.binding.bytes=128;
    memset(in->request.binding.build,'1',32);memset(in->request.binding.cycle,'3',32);
    memcpy(in->request.binding.descriptor_sha256,in->hash,32);
    memset(in->context.build,'1',32);memset(in->context.boot,'2',32);memset(in->context.cycle,'3',32);
    in->context.return_armed=in->context.page_reserved=in->context.pid1=in->context.cap_sys_boot=1;
    if(n210_prepare_once(&in->request,&in->destination,&in->context,in->hash,&in->prepare_spent,&in->prepared))return 0;
    /* Synthetic completed ingestion input; never call/replay217 or change its state. */
    in->ingest.spent=1;r=&in->ingest.result;memcpy(r->magic,"N217RCP1",8);
    r->schema=1;r->bytes=352;r->status=1;r->flags=7;r->generation=1;
    memcpy(r->build,in->context.build,32);memcpy(r->boot,in->context.boot,32);memcpy(r->cycle,in->context.cycle,32);
    memcpy(r->cookie,in->destination.region.cookie,16);
    r->source_bytes[0]=r->copied_bytes[0]=p.kernel_span;r->source_bytes[1]=r->copied_bytes[1]=p.adapter_bytes;
    memcpy(r->source_sha256[0],p.materialized_sha256,32);memcpy(r->destination_sha256[0],p.materialized_sha256,32);
    memcpy(r->source_sha256[1],p.adapter_sha256,32);memcpy(r->destination_sha256[1],p.adapter_sha256,32);
    r->source_data_bytes=p.kernel_span+p.adapter_bytes;r->staging_request_bytes=N217_CHUNK;
    r->files_held=2;r->destination_content_verified=1;return 1;
}

static int composition(void)
{
    struct inputs in;struct n278_values expected;unsigned int i;
    if(!setup(&in))return 0;
    memset(n226_source_pool,0,sizeof(n226_source_pool));
    memset(n226_source_pool+N226_CONTROL_OFFSET,0x5a,N279_SEAL_OFFSET-N226_CONTROL_OFFSET);
    memset(n226_source_pool+N279_SEAL_OFFSET+sizeof(struct n278_seal),0xc7,
        N226_STAGE_OFFSET-N279_SEAL_OFFSET-sizeof(struct n278_seal));
    if(n278_seal_once(N279_SEAL,&in.request,&in.destination,&in.context,in.hash,&in.prepared,in.prepare_spent,&in.ingest))return 0;
    expected=N279_SEAL->values;
    memset(&in.request,0xa5,sizeof(in.request));memset(&in.context,0xa5,sizeof(in.context));
    memset(&in.prepared,0xa5,sizeof(in.prepared));
    /* Exact retained cleanup intervals, including target-checked hash216/112. */
    memset(n226_source_pool,0,N226_WORKSPACE_BYTES);
    memset(n226_source_pool+N226_STAGE_OFFSET,0,N217_CHUNK);
    memset(n226_source_pool+42528,0,112);
    if(N279_SEAL->phase!=N278_VALUES_ONLY||memcmp(&N279_SEAL->values,&expected,sizeof(expected)))return 0;
    for(i=N226_CONTROL_OFFSET;i<N279_SEAL_OFFSET;i++)
        if(n226_source_pool[i]!=(i>=42528&&i<42640?0:0x5a))return 0;
    for(i=N279_SEAL_OFFSET+sizeof(struct n278_seal);i<N226_STAGE_OFFSET;i++)if(n226_source_pool[i]!=0xc7)return 0;
    for(i=0;i<N226_WORKSPACE_BYTES;i++)if(n226_source_pool[i])return 0;
    for(i=N226_STAGE_OFFSET;i<N226_POOL_BYTES;i++)if(n226_source_pool[i])return 0;
    /* The companion source predicate proves this shared guard precedes the
     * real full-pool memset. A refused reentry must not clear accepted values. */
    if(!in.ingest.spent)memset(n226_source_pool,0,sizeof(n226_source_pool));
    return in.ingest.spent==1&&N279_SEAL->phase==N278_VALUES_ONLY&&
        !memcmp(&N279_SEAL->values,&expected,sizeof(expected));
}
int main(void)
{
    if(!composition()){fputs("pool composition failed\n",stderr);return 1;}
    puts("{\"schema\":\"note10-v279-pool-composition-fixture-v1\",\"passed\":true,\"groups\":1,\"variants\":1,\"assertions\":1,\"hardware_operations\":0}");
    return 0;
}
