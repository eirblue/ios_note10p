/* SPDX-License-Identifier: GPL-2.0-only */
/* Synthetic owner/page adapters only; never a live reservation. */
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "v290_preparation_storage.h"
static n209_u8 *memory;
static _Alignas(4096) n209_u8 pool[49152];
static struct n210_destination destination;
static unsigned int stale,clears,reads,corrupt;
static int n290_fixture_owner(void *opaque,const struct n210_destination *d)
{ (void)opaque;return stale||!d||memcmp(d,&destination,sizeof(*d))?-116:0; }
static int n290_fixture_clear(void *opaque,n209_u64 offset,n209_u64 bytes)
{
    (void)opaque;if(bytes!=4096||offset>destination.region.size-bytes)return -22;
    clears++;memset(memory+offset,0,(size_t)bytes);return 0;
}
static int n290_fixture_read(void *opaque,n209_u64 offset,void *raw,unsigned int bytes)
{
    (void)opaque;if(bytes!=4096||offset>destination.region.size-bytes)return -22;
    reads++;memcpy(raw,memory+offset,bytes);if(corrupt)((n209_u8 *)raw)[0]=1;return 0;
}
#define N290_HOST_FIXTURE 1
#include "v290_preparation_storage.inc"
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
    stale=clears=reads=corrupt=0;
}
int main(void)
{
    struct n210_request request;struct n210_context context;struct n210_receipt prepared;struct n278_seal seal;
    struct n290_storage *s=(struct n290_storage *)(pool+44896);n209_u8 *scratch=pool+20480;
    n209_u64 i;unsigned int c,r;int ok=1,error;
    memory=malloc((size_t)N209_DESTINATION_BYTES);if(!memory)return 2;
    setup(&request,&context,&prepared,&seal,131072);
    error=n290_prepare_storage_locked(s,&seal,&request,&destination,&context,&prepared,NULL,scratch,4096);
    ok&=error==0&&s->phase==N290_STORAGE_PREPARED&&s->flags==0&&s->end_offset-s->args_offset==49152&&clears==12&&reads==12;
    ok&=s->prior_top==seal.values.layout.top_offset&&s->end_offset<=destination.region.size&&seal.phase==N278_VALUES_ONLY;
    ok&=!memcmp(s->descriptor_sha256,prepared.descriptor_sha256,32)&&!memcmp(s->cookie,destination.region.cookie,16);
    for(i=0;i<N209_DESTINATION_BYTES;i++)if(memory[i]!=(n209_u8)(i>=s->args_offset&&i<s->end_offset?0:0xa5))ok=0;
    c=clears;r=reads;error=n290_prepare_storage_locked(s,&seal,&request,&destination,&context,&prepared,NULL,scratch,4096);
    ok&=error==-114&&clears==c&&reads==r; /* repeat */
    setup(&request,&context,&prepared,&seal,131072);stale=1;
    error=n290_prepare_storage_locked(s,&seal,&request,&destination,&context,&prepared,NULL,scratch,4096);
    ok&=error&&s->phase==N290_REFUSED&&!clears&&!reads; /* owner-stale */
    setup(&request,&context,&prepared,&seal,N209_DESTINATION_BYTES-N209_ADT_MAX-2*N209_PAGE);
    error=n290_prepare_storage_locked(s,&seal,&request,&destination,&context,&prepared,NULL,scratch,4096);
    ok&=error&&s->phase==N290_REFUSED&&!clears&&!reads; /* no-tail-room */
    setup(&request,&context,&prepared,&seal,131072);corrupt=1;
    error=n290_prepare_storage_locked(s,&seal,&request,&destination,&context,&prepared,NULL,scratch,4096);
    ok&=error&&s->phase==N290_QUARANTINED&&clears==12&&reads==1&&seal.phase==N278_VALUES_ONLY; /* readback-failure */
    assert(ok);free(memory);
    puts("{\"passed\":true,\"groups\":1,\"variants\":1,\"assertions\":1,\"negative_cases\":4}");return 0;
}
