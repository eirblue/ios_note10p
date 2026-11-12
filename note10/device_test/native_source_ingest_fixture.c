/* SPDX-License-Identifier: GPL-2.0-only */
/* Real host SHA256, synthetic IO only; no physical-owner attestation. */
#include <windows.h>
#include <bcrypt.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "native_source_ingest.h"
struct fixture {
    unsigned char kernel[65536],adapter[16384],stage[4096],hash_object[4096];unsigned char *destination;
    struct n217_request request;struct n210_destination owner;struct n210_context context;struct n210_receipt prepared;
    struct n217_state state;BCRYPT_ALG_HANDLE algorithm;BCRYPT_HASH_HANDLE hash;
    int writer,alias,short_read,extra,bad_owner,corrupt,fail_after,lose_after;unsigned int holds,puts,writes,clears;
};
static unsigned int assertions,variants;
#define CHECK(value) do{assertions++;if(!(value)){fprintf(stderr,"ingest assertion %u line%d\n",assertions,__LINE__);exit(1);}}while(0)
static int hash_begin(void *opaque)
{
    struct fixture *f=opaque;if(f->hash){BCryptDestroyHash(f->hash);f->hash=NULL;}
    return BCryptCreateHash(f->algorithm,&f->hash,f->hash_object,sizeof(f->hash_object),NULL,0,0)?-1:0;
}
static int hash_update(void *opaque,const void *raw,unsigned int bytes)
{ struct fixture *f=opaque;return BCryptHashData(f->hash,(PUCHAR)raw,(ULONG)bytes,0)?-1:0; }
static int hash_end(void *opaque,n209_u8 *out)
{ struct fixture *f=opaque;return BCryptFinishHash(f->hash,out,32,0)?-1:0; }
static void digest(struct fixture *f,const void *raw,unsigned int bytes,n209_u8 *out)
{ if(hash_begin(f)||hash_update(f,raw,bytes)||hash_end(f,out)){fputs("host SHA256 failure\n",stderr);exit(1);} }
static int owner(void *opaque,const struct n210_destination *d)
{
    struct fixture *f=opaque;
    return f->bad_owner||(f->lose_after&&f->writes>=(unsigned int)f->lose_after)||memcmp(d,&f->owner,96)?-116:0;
}
static int hold(void *opaque,unsigned int role,n209_u64 bytes,void **handle,n209_u64 *inode)
{
    struct fixture *f=opaque;if(role>=2||f->writer||bytes!=(role?16384:65536))return -1;
    *handle=(void *)(uintptr_t)(role+1);*inode=f->alias?1:role+1;f->holds++;return 0;
}
static long read_source(void *opaque,void *handle,n209_u64 offset,void *out,unsigned int bytes)
{
    struct fixture *f=opaque;unsigned int role=(unsigned int)(uintptr_t)handle-1;unsigned int size=role?16384:65536;
    const unsigned char *raw=role?f->adapter:f->kernel;
    if(offset==size)return f->extra?1:0;
    if(offset>size||bytes>size-offset)return -1;
    if(f->short_read&&offset==0)return (long)bytes-1;
    memcpy(out,raw+(size_t)offset,bytes);return (long)bytes;
}
static void put(void *opaque,void *handle)
{ struct fixture *f=opaque;(void)handle;f->puts++; }
static int write_destination(void *opaque,n209_u64 offset,const void *raw,unsigned int bytes)
{
    struct fixture *f=opaque;if(offset>N209_DESTINATION_BYTES-bytes||(f->fail_after&&f->writes>=(unsigned int)f->fail_after))return -1;
    memcpy(f->destination+(size_t)offset,raw,bytes);f->writes++;return 0;
}
static int read_destination(void *opaque,n209_u64 offset,void *raw,unsigned int bytes)
{
    struct fixture *f=opaque;if(offset>N209_DESTINATION_BYTES-bytes)return -1;
    memcpy(raw,f->destination+(size_t)offset,bytes);if(f->corrupt&&offset==0)((unsigned char *)raw)[0]^=1;return 0;
}
static int clear_destination(void *opaque,n209_u64 offset,n209_u64 bytes)
{
    struct fixture *f=opaque;if(owner(f,&f->owner)||offset>N209_DESTINATION_BYTES-bytes)return -1;
    memset(f->destination+(size_t)offset,0,(size_t)bytes);f->clears++;return 0;
}
static const struct n217_io io={owner,hold,read_source,put,hash_begin,hash_update,hash_end,write_destination,read_destination,clear_destination};
static void reset(struct fixture *f)
{
    struct n209_payload payload;BCRYPT_ALG_HANDLE algorithm=f->algorithm;unsigned char *destination=f->destination;
    if(f->hash)BCryptDestroyHash(f->hash);memset(f,0,sizeof(*f));f->algorithm=algorithm;f->destination=destination;
    memset(destination,0,(size_t)N209_DESTINATION_BYTES);memset(f->kernel,'K',sizeof(f->kernel));memset(f->adapter,'A',sizeof(f->adapter));
    memcpy(f->owner.magic,"N210DST1",8);f->owner.schema=1;f->owner.bytes=96;
    f->owner.region.base=0x81004000ULL;f->owner.region.size=N209_DESTINATION_BYTES;f->owner.region.generation=1;
    f->owner.region.page_shift=12;f->owner.region.status=1;memset(f->owner.region.build,'a',32);memset(f->owner.region.cookie,'c',16);
    memset(f->context.build,'a',32);memset(f->context.boot,'b',32);memset(f->context.cycle,'c',32);
    f->context.return_armed=f->context.page_reserved=f->context.pid1=f->context.cap_sys_boot=1;
    memset(&payload,0,sizeof(payload));memcpy(payload.magic,"N209PAY1",8);payload.schema=1;payload.bytes=256;
    payload.virtual_base=0x1004000ULL;payload.kernel_span=65536;payload.kernel_entry_offset=0;payload.entry_extent_offset=0;payload.entry_extent_bytes=16384;
    payload.pool_offset=32768;payload.pool_bytes=16384;payload.adapter_bytes=16384;payload.adapter_entry_offset=0;payload.adapter_record_offset=64;
    memset(payload.kernel_sha256,0x21,32);memset(payload.producer_id,'p',32);memset(payload.input_binding,'i',32);
    digest(f,f->kernel,sizeof(f->kernel),payload.materialized_sha256);digest(f,f->adapter,sizeof(f->adapter),payload.adapter_sha256);
    memcpy(f->request.magic,"N217SRC1",8);f->request.schema=1;f->request.bytes=496;f->request.prepared.destination=f->owner;
    memcpy(f->request.prepared.payload,&payload,256);memcpy(f->request.prepared.binding.magic,"N210BND1",8);
    f->request.prepared.binding.schema=1;f->request.prepared.binding.bytes=128;
    memcpy(f->request.prepared.binding.build,f->context.build,32);memcpy(f->request.prepared.binding.cycle,f->context.cycle,32);
    digest(f,f->request.prepared.payload,256,f->request.prepared.binding.descriptor_sha256);
    memcpy(f->prepared.magic,"N210RCP1",8);f->prepared.schema=1;f->prepared.bytes=192;f->prepared.status=1;f->prepared.flags=3;
    f->prepared.generation=1;memcpy(f->prepared.build,f->context.build,32);memcpy(f->prepared.boot,f->context.boot,32);memcpy(f->prepared.cycle,f->context.cycle,32);
    memcpy(f->prepared.cookie,f->owner.region.cookie,16);memcpy(f->prepared.descriptor_sha256,f->request.prepared.binding.descriptor_sha256,32);
}
static int consume(struct fixture *f)
{ return n217_consume(&f->request,&f->owner,&f->context,&f->prepared,&f->state,&io,f,f->stage,sizeof(f->stage)); }
int main(void)
{
    struct fixture *f=calloc(1,sizeof(*f));unsigned int mode;ULONG object_bytes=0,returned=0;int error;
    if(!f)return 1;f->destination=malloc((size_t)N209_DESTINATION_BYTES);if(!f->destination)return 1;
    if(BCryptOpenAlgorithmProvider(&f->algorithm,BCRYPT_SHA256_ALGORITHM,NULL,0))return 1;
    if(BCryptGetProperty(f->algorithm,BCRYPT_OBJECT_LENGTH,(PUCHAR)&object_bytes,sizeof(object_bytes),&returned,0)||
       returned!=sizeof(object_bytes)||!object_bytes||object_bytes>sizeof(f->hash_object))return 1;
    /* Six new groups, twelve isolated synthetic variants. */
    variants++;reset(f);CHECK(consume(f)==0);CHECK(f->state.result.status==1&&f->state.result.files_held==2&&f->puts==0);
    CHECK(f->state.result.destination_content_verified==1&&f->state.result.source_pages_physically_pinned==0);
    CHECK(!memcmp(f->state.result.source_sha256,f->state.result.destination_sha256,64));
    for(mode=0;mode<2;mode++){variants++;reset(f);if(mode)f->alias=1;else f->writer=1;CHECK(consume(f)!=0);CHECK(f->writes==0&&f->puts==f->holds);}
    for(mode=0;mode<3;mode++){variants++;reset(f);if(mode==0)f->kernel[0]^=1;else if(mode==1)f->short_read=1;else f->extra=1;
        CHECK(consume(f)!=0);CHECK(f->state.result.status==2&&f->puts==f->holds);}
    for(mode=0;mode<2;mode++){variants++;reset(f);if(mode)f->context.page_reserved=0;else f->request.prepared.destination.region.cookie[0]^=1;
        CHECK(consume(f)!=0);CHECK(f->writes==0&&f->holds==0);}
    variants++;reset(f);f->corrupt=1;CHECK(consume(f)!=0);CHECK(f->clears==2&&f->state.result.destination_content_verified==0);
    variants++;reset(f);CHECK(consume(f)==0);error=consume(f);CHECK(error==-114&&f->state.result.status==1);
    variants++;reset(f);f->fail_after=2;CHECK(consume(f)!=0);CHECK(f->clears==1&&f->puts==2&&f->destination[0]==0);
    variants++;reset(f);f->lose_after=2;CHECK(consume(f)!=0);CHECK(f->state.result.quarantined==1&&f->clears==0&&f->destination[0]=='K'&&f->puts==2);
    printf("{\"groups\":6,\"variants\":%u,\"assertions\":%u,\"physical_runtime_verified\":false,\"device_authorized\":false}\n",variants,assertions);
    if(f->hash)BCryptDestroyHash(f->hash);BCryptCloseAlgorithmProvider(f->algorithm,0);free(f->destination);free(f);return 0;
}
