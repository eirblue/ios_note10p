/* SPDX-License-Identifier: GPL-2.0-only */
#include "v278_current_owner_seal.h"
#include <stdio.h>
#include <string.h>
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
static int seal(struct n278_seal *out,const struct inputs *in)
{ return n278_seal_once(out,&in->request,&in->destination,&in->context,in->hash,&in->prepared,in->prepare_spent,&in->ingest); }
static int rejected(const struct inputs *in)
{
    struct n278_seal out={0},empty={0};
    return seal(&out,in)!=0&&out.phase==N278_REFUSED&&memcmp(&out.values,&empty.values,sizeof(out.values))==0;
}
static int create_after_scratch(struct n278_seal *out,struct n278_values *expected)
{
    struct inputs in;if(!setup(&in)||seal(out,&in))return 0;
    *expected=out->values;
    memset(&in,0xa5,sizeof(in));return 1;
}
static int copied_lifetime(void)
{
    struct n278_seal out={0};struct n278_values expected;
    return create_after_scratch(&out,&expected)&&out.phase==N278_VALUES_ONLY&&
        memcmp(&out.values,&expected,sizeof(expected))==0&&out.values.context.boot[0]=='2'&&
        out.values.request.destination.region.cookie[0]==1&&out.values.layout.adt_bytes==N209_ADT_MAX;
}
static int identity_join(void)
{
    struct inputs good,bad;if(!setup(&good))return 0;
    bad=good;bad.ingest.result.boot[0]='4';if(!rejected(&bad))return 0;
    bad=good;bad.prepared.cookie[0]^=1;if(!rejected(&bad))return 0;
    bad=good;bad.ingest.result.quarantined=1;if(!rejected(&bad))return 0;
    bad=good;bad.ingest.result.destination_sha256[1][0]^=1;if(!rejected(&bad))return 0;
    bad=good;bad.request.binding.descriptor_sha256[0]^=1;if(!rejected(&bad))return 0;
    return good.prepare_spent==1&&good.ingest.spent==1&&good.ingest.result.status==1;
}
static int bounded_layout(void)
{
    struct inputs in,bad;struct n278_seal out={0};struct n209_payload p;
    if(!setup(&in)||seal(&out,&in))return 0;
    if(out.values.layout.adapter_offset!=3*N209_PAGE+N209_PAGE+N209_ADT_MAX||
       out.values.adapter_entry!=in.destination.region.base+out.values.layout.adapter_offset+64||
       out.values.layout.top_offset>in.destination.region.size)return 0;
    bad=in;memcpy(&p,bad.request.payload,sizeof(p));p.adapter_entry_offset=p.adapter_record_offset;
    memcpy(bad.request.payload,&p,sizeof(p));if(!rejected(&bad))return 0;
    bad=in;bad.destination.region.base=~(n209_u64)0-N209_PAGE;
    bad.request.destination=bad.destination;if(!rejected(&bad))return 0;
    bad=in;memcpy(&p,bad.request.payload,sizeof(p));p.kernel_span=N209_DESTINATION_BYTES;
    memcpy(bad.request.payload,&p,sizeof(p));return rejected(&bad);
}
static int one_way(void)
{
    struct inputs in,bad;struct n278_seal invalid={0},accepted={0},before;
    if(!setup(&in))return 0;
    bad=in;bad.ingest.spent=0;if(!seal(&invalid,&bad)||invalid.phase!=N278_REFUSED)return 0;
    before=invalid;if(!seal(&invalid,&in)||invalid.phase!=before.phase||
        memcmp(&invalid.values,&before.values,sizeof(invalid.values)))return 0;
    if(seal(&accepted,&in))return 0;
    before=accepted;bad=in;bad.context.cycle[0]='9';
    return seal(&accepted,&bad)!=0&&accepted.phase==before.phase&&
        !memcmp(&accepted.values,&before.values,sizeof(accepted.values))&&
        in.prepare_spent==1&&in.ingest.spent==1&&in.ingest.result.quarantined==0;
}
static int values_are_not_readiness(void)
{
    struct inputs in;struct n278_seal out={0};
    if(!setup(&in)||seal(&out,&in))return 0;
    /* Linux return-armed may admit copied values; there is no transfer API or
     * CORE/id input, actual ADT, native mapping or hardware-return ticket. */
    return out.phase==N278_VALUES_ONLY&&out.values.context.return_armed==1&&
        out.values.ingested.source_pages_physically_pinned==0&&
        out.values.layout.adt_bytes==N209_ADT_MAX&&
        out.values.request.binding.descriptor_sha256[0]==2;
}
int main(void)
{
    static const char *names[]={"copied-lifetime","identity-join","bounded-layout","one-way","values-not-readiness"};
    int (*const cases[])(void)={copied_lifetime,identity_join,bounded_layout,one_way,values_are_not_readiness};
    unsigned int i;
    for(i=0;i<5;i++){
        if(!cases[i]()){fprintf(stderr,"case%u %s failed\n",i+1,names[i]);return 1;}
        printf("PASS %s\n",names[i]);
    }
    puts("{\"schema\":\"note10-v278-value-seal-C-fixture-v1\",\"passed\":true,\"groups\":1,\"variants\":5,\"assertions\":5,\"hardware_operations\":0,\"live_kernel_callers\":0}");
    return 0;
}
