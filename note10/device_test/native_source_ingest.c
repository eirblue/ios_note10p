/* SPDX-License-Identifier: GPL-2.0-only */
#include "native_source_ingest.h"
static int n217_equal(const void *a,const void *b,unsigned int count)
{ const n209_u8 *x=a,*y=b;unsigned int i;for(i=0;i<count;i++)if(x[i]!=y[i])return 0;return 1; }
static void n217_copy(void *a,const void *b,unsigned int count)
{ n209_u8 *x=a;const n209_u8 *y=b;unsigned int i;for(i=0;i<count;i++)x[i]=y[i]; }
static void n217_zero(void *a,unsigned int count)
{ n209_u8 *x=a;unsigned int i;for(i=0;i<count;i++)x[i]=0; }
static int n217_hex(const n209_u8 *p)
{ unsigned int i,n=0;for(i=0;i<32;i++){if(!((p[i]>='0'&&p[i]<='9')||(p[i]>='a'&&p[i]<='f')))return 0;n|=p[i]!='0';}return n!=0; }
int n217_consume(const struct n217_request *r,const struct n210_destination *d,const struct n210_context *c,
                 const struct n210_receipt *prepared,struct n217_state *state,const struct n217_io *io,
                 void *opaque,n209_u8 *stage,unsigned int stage_bytes)
{
    struct n209_payload payload;struct n209_layout layout;struct n217_result *out;
    n209_u64 size[2],offset[2],at;const n209_u8 *expected[2];n209_u8 descriptor_hash[32];
    unsigned int role,count;int error=-22,quarantine=0;
    if(!state)return -22;
    if(state->spent)return -114;
    state->spent=1;n217_zero(&state->result,sizeof(state->result));out=&state->result;
    state->held[0]=state->held[1]=0;state->inode[0]=state->inode[1]=0;
    n217_copy(out->magic,"N217RCP1",8);out->schema=1;out->bytes=352;out->status=2;
    if(!r||!d||!c||!prepared||!io||!stage||stage_bytes!=N217_CHUNK||!io->owner||!io->hold||!io->read||!io->put||
       !io->hash_begin||!io->hash_update||!io->hash_end||!io->write_destination||!io->read_destination||!io->clear_destination)goto bad;
    if(!n217_equal(r->magic,"N217SRC1",8)||r->schema!=1||r->bytes!=496||
       !n217_equal(&r->prepared.destination,d,sizeof(*d))||!n217_equal(d->magic,"N210DST1",8)||d->schema!=1||d->bytes!=96||
       c->return_armed!=1||c->page_reserved!=1||c->pid1!=1||c->cap_sys_boot!=1||!n217_hex(c->build)||!n217_hex(c->boot)||!n217_hex(c->cycle)||
       !n217_equal(d->region.build,c->build,32)||!n217_equal(r->prepared.binding.magic,"N210BND1",8)||
       r->prepared.binding.schema!=1||r->prepared.binding.bytes!=128||!n217_equal(r->prepared.binding.build,c->build,32)||
       !n217_equal(r->prepared.binding.cycle,c->cycle,32))goto bad;
    for(role=0;role<16;role++)if(r->prepared.binding.reserved[role])goto bad;
    if(io->hash_begin(opaque)||io->hash_update(opaque,r->prepared.payload,256)||io->hash_end(opaque,descriptor_hash))goto bad;
    if(!n217_equal(descriptor_hash,r->prepared.binding.descriptor_sha256,32)||!n217_equal(prepared->magic,"N210RCP1",8)||
       prepared->schema!=1||prepared->bytes!=192||prepared->status!=1||prepared->flags!=3||prepared->reserved||prepared->tail_reserved||
       prepared->generation!=d->region.generation||!n217_equal(prepared->build,c->build,32)||!n217_equal(prepared->boot,c->boot,32)||
       !n217_equal(prepared->cycle,c->cycle,32)||!n217_equal(prepared->cookie,d->region.cookie,16)||!n217_equal(prepared->descriptor_sha256,descriptor_hash,32)||
       n209_decode_payload(r->prepared.payload,256,&payload)||n209_layout_bounds(&payload,&d->region,N209_ADT_MAX,&layout))goto bad;
    size[0]=payload.kernel_span;size[1]=payload.adapter_bytes;offset[0]=0;offset[1]=layout.adapter_offset;
    expected[0]=payload.materialized_sha256;expected[1]=payload.adapter_sha256;
    out->generation=d->region.generation;n217_copy(out->build,c->build,32);n217_copy(out->boot,c->boot,32);
    n217_copy(out->cycle,c->cycle,32);n217_copy(out->cookie,d->region.cookie,16);
    out->source_bytes[0]=size[0];out->source_bytes[1]=size[1];out->source_data_bytes=size[0]+size[1];out->staging_request_bytes=N217_CHUNK;
    error=-5;
    if(io->owner(opaque,d))goto failed;
    for(role=0;role<2;role++){
        if(io->hold(opaque,role,size[role],&state->held[role],&state->inode[role])||!state->held[role]||!state->inode[role])goto failed;
        if(role&&state->inode[0]==state->inode[1])goto failed;
    }
    for(role=0;role<2;role++){
        if(io->hash_begin(opaque))goto failed;
        for(at=0;at<size[role];at+=count){
            count=(unsigned int)(size[role]-at>N217_CHUNK?N217_CHUNK:size[role]-at);
            if(io->read(opaque,state->held[role],at,stage,count)!=(long)count||io->hash_update(opaque,stage,count)||
               io->owner(opaque,d)||io->write_destination(opaque,offset[role]+at,stage,count))goto failed;
            out->copied_bytes[role]+=count;
        }
        if(io->read(opaque,state->held[role],size[role],stage,1)!=0||io->hash_end(opaque,out->source_sha256[role])||
           !n217_equal(out->source_sha256[role],expected[role],32))goto failed;
    }
    for(role=0;role<2;role++){
        if(io->hash_begin(opaque))goto failed;
        for(at=0;at<size[role];at+=count){
            count=(unsigned int)(size[role]-at>N217_CHUNK?N217_CHUNK:size[role]-at);
            if(io->owner(opaque,d)||io->read_destination(opaque,offset[role]+at,stage,count)||io->hash_update(opaque,stage,count))goto failed;
        }
        if(io->hash_end(opaque,out->destination_sha256[role])||!n217_equal(out->destination_sha256[role],expected[role],32))goto failed;
    }
    if(io->owner(opaque,d))goto failed;
    out->status=1;out->flags=7;out->files_held=2;out->destination_content_verified=1;
    return 0;
 failed:
    if(out->copied_bytes[0]||out->copied_bytes[1]){
        if(io->owner(opaque,d))quarantine=1;
        else for(role=0;role<2;role++)if(out->copied_bytes[role]&&
            (io->owner(opaque,d)||io->clear_destination(opaque,offset[role],out->copied_bytes[role]))){quarantine=1;break;}
    }
    for(role=0;role<2;role++)if(state->held[role]){io->put(opaque,state->held[role]);state->held[role]=0;}
    out->quarantined=(n209_u32)quarantine;if(quarantine)out->status=3;
 bad:
    out->error_code=(n209_u32)-error;return error;
}
