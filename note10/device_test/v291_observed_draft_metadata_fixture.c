/* SPDX-License-Identifier: GPL-2.0-only */
/* Synthetic OF and owner/page adapters; no live declaration is embedded. */
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "v291_observed_draft_metadata.h"
static n209_u8 *memory;static _Alignas(4096) n209_u8 pool[49152];
static struct n210_destination destination;
static unsigned int stale,writes,reads,corrupt,locks;
static int n291_fixture_owner(void *opaque,const struct n210_destination *d)
{ (void)opaque;return stale||locks||!d||memcmp(d,&destination,sizeof(*d))?-116:0; }
#define N285_HOST_FIXTURE 1
#pragma clang diagnostic push
#pragma clang diagnostic ignored "-Wunused-function"
#include "v285_current_cpu_metadata.inc"
#pragma clang diagnostic pop
n285_node *n285_fixture_root;
void n285_fixture_lock(unsigned long *flags){*flags=0;locks++;}
void n285_fixture_unlock(unsigned long flags){(void)flags;locks--;}
int n285_fixture_write(void *opaque,n209_u64 offset,const void *raw,unsigned int bytes)
{
    if(n291_fixture_owner(opaque,&destination)||!bytes||offset>destination.region.size-bytes||offset%4096+bytes>4096)return -116;
    writes++;memcpy(memory+offset,raw,bytes);return 0;
}
int n285_fixture_read(void *opaque,n209_u64 offset,void *raw,unsigned int bytes)
{
    if(n291_fixture_owner(opaque,&destination)||!bytes||offset>destination.region.size-bytes||offset%4096+bytes>4096)return -116;
    reads++;memcpy(raw,memory+offset,bytes);if(corrupt)((n209_u8 *)raw)[0]^=1;return 0;
}
#define N291_HOST_FIXTURE 1
#include "v291_observed_draft_metadata.inc"
static void put(n209_u8 *p,n209_u64 value,unsigned int n)
{ unsigned int i;for(i=0;i<n;i++)p[i]=(n209_u8)(value>>(8*i)); }
static void setup(struct n210_request *request,struct n210_context *context,struct n210_receipt *prepared,
                  struct n278_seal *seal,n209_u64 kernel_bytes)
{
    struct n209_payload payload;unsigned int i;
    memset(pool,0,sizeof(pool));memset(memory,0xa5,(size_t)N209_DESTINATION_BYTES);
    memset(&destination,0,sizeof(destination));memcpy(destination.magic,"N210DST1",8);destination.schema=1;destination.bytes=96;
    destination.region.base=0x81004000ULL;destination.region.size=N209_DESTINATION_BYTES;
    destination.region.generation=1;destination.region.page_shift=12;destination.region.status=1;
    memset(destination.region.build,'a',32);memset(destination.region.cookie,1,16);
    memset(context,0,sizeof(*context));memset(context->build,'a',32);memset(context->boot,'b',32);memset(context->cycle,'c',32);
    context->return_armed=context->page_reserved=context->pid1=context->cap_sys_boot=1;
    memset(request,0,sizeof(*request));request->destination=destination;
    memcpy(request->payload,"N209PAY1",8);put(request->payload+8,1,4);put(request->payload+12,256,4);
    put(request->payload+16,0xfffffff001004000ULL,8);put(request->payload+24,kernel_bytes,8);
    put(request->payload+32,0,8);put(request->payload+40,0,8);put(request->payload+48,16384,8);
    put(request->payload+56,16384,8);put(request->payload+64,16384,8);put(request->payload+72,16384,8);
    put(request->payload+80,0,8);put(request->payload+88,256,8);
    for(i=96;i<256;i++)request->payload[i]=1;
    memset(request->binding.descriptor_sha256,7,32);
    memset(prepared,0,sizeof(*prepared));memcpy(prepared->magic,"N210RCP1",8);prepared->schema=1;prepared->bytes=192;prepared->status=1;
    prepared->generation=1;memcpy(prepared->cookie,destination.region.cookie,16);memset(prepared->descriptor_sha256,7,32);
    memset(seal,0,sizeof(*seal));seal->phase=N278_VALUES_ONLY;seal->values.request=*request;seal->values.context=*context;
    seal->values.prepared=*prepared;
    if(n209_decode_payload(request->payload,256,&payload)||n209_layout_bounds(&payload,&destination.region,N209_ADT_MAX,&seal->values.layout))abort();
    stale=writes=reads=corrupt=locks=0;
}

static n285_node root,nodes[8];
static n285_property rootprops[2],props[8][4];
static n209_u8 ac[4]={0,0,0,2},sc[4]={0,0,0,1},regs[8][17*12];
static void be(n209_u8 *p,n209_u64 value,unsigned int count)
{ unsigned int i;for(i=0;i<count;i++)p[count-i-1]=(n209_u8)(value>>(i*8)); }
static n209_u64 get(const n209_u8 *p,unsigned int count)
{ n209_u64 value=0;unsigned int i;for(i=0;i<count;i++)value|=(n209_u64)p[i]<<(8*i);return value; }
static int zero(const n209_u8 *p,unsigned int bytes)
{ unsigned int i;for(i=0;i<bytes;i++)if(p[i])return 0;return 1; }
static void setup_case(struct n210_request *q,struct n210_context *c,struct n210_receipt *r,struct n278_seal *s,unsigned int banks)
{
    unsigned int i;struct n290_storage *storage=(struct n290_storage *)(pool+44896);struct n285_workspace *w=(struct n285_workspace *)pool;
    setup(q,c,r,s,131072);
    if(n290_plan_storage(storage,s,q,&destination,c,r))abort();storage->phase=N290_STORAGE_PREPARED;
    memset(memory+storage->args_offset,0,(size_t)N290_STORAGE_BYTES);
    w->snapshot.count=1;w->snapshot.selected=1;w->snapshot.frequency=1000000;w->snapshot.affinity[0]=1;
    memset(&root,0,sizeof(root));memset(nodes,0,sizeof(nodes));memset(props,0,sizeof(props));memset(regs,0,sizeof(regs));
    rootprops[0]=(n285_property){"#address-cells",4,ac,&rootprops[1]};rootprops[1]=(n285_property){"#size-cells",4,sc,0};
    root.properties=rootprops;root.child=nodes;n285_fixture_root=&root;
    for(i=0;i<banks;i++){
        be(regs[i],0x80000000ULL+(banks==1?0:(n209_u64)i*0x40000000ULL),8);be(regs[i]+8,0x20000000ULL,4);
        props[i][0]=(n285_property){"device_type",7,"memory",&props[i][1]};props[i][1]=(n285_property){"reg",12,regs[i],0};
        nodes[i].properties=props[i];if(i+1<banks)nodes[i].sibling=&nodes[i+1];
    }
}
int main(int argc,char **argv)
{
    struct n210_request q;struct n210_context c;struct n210_receipt r;struct n278_seal seal;
    struct n290_storage *s=(struct n290_storage *)(pool+44896);struct n291_header *h=(struct n291_header *)s->reserved;
    struct n285_workspace *w=(struct n285_workspace *)pool;struct n291_observation golden={0};
    n209_u32 bytes=0;unsigned int wc,rc,i;int ok=1,error;FILE *file;
    if(argc!=2)return 2;memory=malloc((size_t)N209_DESTINATION_BYTES);if(!memory)return 2;
#define RUN() n291_prepare_draft_locked(s,&seal,&q,&destination,&c,&r,NULL,w,sizeof(*w))
    setup_case(&q,&c,&r,&seal,1);error=RUN();
    ok&=error==0&&h->phase==N291_EARLY_DRAFT&&h->adt_bytes>0&&(h->flags&N291_CHOSEN_READY)&&writes==4&&reads==4&&!locks;
    ok&=get(memory+s->args_offset+24,8)==N209_DESTINATION_BYTES&&get(memory+s->args_offset+1144,8)==0x20000000ULL;
    ok&=get(memory+s->args_offset+32,8)==s->base+s->end_offset&&get(memory+s->args_offset+96,8)==0xfffffff001004000ULL+s->adt_offset;
    for(i=0;i<s->args_offset;i++)if(memory[i]!=0xa5)ok=0;
    wc=writes;rc=reads;error=RUN();ok&=error==-114&&writes==wc&&reads==rc; /* repeat */
    setup_case(&q,&c,&r,&seal,8);
    props[1][1].next=&props[1][2];props[1][2]=(n285_property){"status",9,"disabled",0};
    props[2][1].next=&props[2][2];props[2][2]=(n285_property){"status",7,"future",0};
    props[3][1].next=&props[3][2];props[3][2]=(n285_property){"hotpluggable",0,0,0};
    error=RUN();ok&=error==0&&h->phase==N291_INCOMPLETE_DRAFT&&h->range_count==8&&!h->adt_bytes&&!(h->flags&N291_CHOSEN_READY);
    ok&=(h->flags&(N291_NONCONTIGUOUS|N291_DISABLED|N291_UNKNOWN_STATUS|N291_HOTPLUG))==(N291_NONCONTIGUOUS|N291_DISABLED|N291_UNKNOWN_STATUS|N291_HOTPLUG);
    ok&=writes==1&&reads==1&&zero(memory+s->args_offset,1152)&&zero(memory+s->adt_offset,16384)&&zero(memory+s->record_offset,64);
    setup_case(&q,&c,&r,&seal,1);props[0][1].length=11;error=RUN();ok&=error&&h->phase==N291_REFUSED&&!writes&&!reads; /* malformed */
    setup_case(&q,&c,&r,&seal,1);props[0][1].length=17*12;error=RUN();ok&=error&&h->phase==N291_REFUSED&&!writes&&!reads; /* cap */
    setup_case(&q,&c,&r,&seal,1);w->snapshot.affinity[0]=2;error=RUN();ok&=error&&h->phase==N291_REFUSED&&!writes&&!reads; /* CPU */
    setup_case(&q,&c,&r,&seal,1);stale=1;error=RUN();ok&=error&&h->phase==N291_REFUSED&&!writes&&!reads; /* owner */
    setup_case(&q,&c,&r,&seal,1);corrupt=1;error=RUN();ok&=error&&h->phase==N291_QUARANTINED&&s->phase==N290_QUARANTINED&&writes==1&&reads==1; /* readback */
    golden.count=1;golden.selected=1;golden.frequency=1000000;golden.flags=N291_SOURCE_OF_REG|N291_CPU_SAMPLED;
    golden.ranges[0].base=0x10000000;golden.ranges[0].size=0x20000000;
    ok&=n291_classify(&golden,0x11000000,0x2000000)==0&&n291_encode_early(&golden,w->adt,sizeof(w->adt),&bytes)==0&&bytes==464;
    assert(ok);file=fopen(argv[1],"wb");if(!file){free(memory);return 2;}
    if(fwrite(w->adt,1,bytes,file)!=bytes||fclose(file)){free(memory);return 2;}
    free(memory);puts("{\"passed\":true,\"groups\":1,\"variants\":1,\"assertions\":1,\"negative_cases\":6}");return 0;
#undef RUN
}
