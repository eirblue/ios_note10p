/* SPDX-License-Identifier: GPL-2.0-only */
/* Actual226 parser + retained core/SHA + pinned kernel rawinflate; synthetic IO only. */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <linux/zlib.h>
#include "native_source_stream.h"
struct fixture {
    struct n226_stream source;z_stream z;void *workspace;n209_u8 *holder,*destination,stage[4096];
    struct n217_state state;struct n217_request request;struct n210_destination owner;
    struct n210_context context;struct n210_receipt prepared;struct n219_sha256 hash;
    unsigned int writes,clears,puts;int lose,corrupt;
};
static unsigned int assertions,variants;
#define CHECK(ok) do{assertions++;if(!(ok)){fprintf(stderr,"226 assertion%u line%d\n",assertions,__LINE__);exit(1);}}while(0)
static int begin(void *opaque)
{ struct fixture *f=opaque;memset(&f->z,0,sizeof(f->z));memset(f->workspace,0,(size_t)zlib_inflate_workspacesize());f->z.workspace=f->workspace;return zlib_inflateInit2(&f->z,-15); }
static int pull(void *opaque,const n209_u8 *in,unsigned int input,n209_u8 *out,unsigned int output,unsigned int *used,unsigned int *got)
{
    struct fixture *f=opaque;int rc;f->z.next_in=in;f->z.avail_in=input;f->z.next_out=out;f->z.avail_out=output;
    rc=zlib_inflate(&f->z,0);*used=input-(unsigned int)f->z.avail_in;*got=output-(unsigned int)f->z.avail_out;
    return rc==Z_STREAM_END?1:rc==Z_OK?0:-1;
}
static n209_u32 crc(n209_u32 value,const n209_u8 *raw,unsigned int bytes)
{ unsigned int i,j;for(i=0;i<bytes;i++){value^=raw[i];for(j=0;j<8;j++)value=(value>>1)^(0xedb88320U&(0U-(value&1)));}return value; }
static void end(void *opaque)
{ struct fixture *f=opaque;if(f->z.state)(void)zlib_inflateEnd(&f->z); }
static const struct n226_codec codec={begin,pull,crc,end};
static int owner(void *opaque,const struct n210_destination *d)
{ struct fixture *f=opaque;return memcmp(d,&f->owner,96)||(f->lose&&f->writes)?-116:0; }
static int hold(void *opaque,unsigned int role,n209_u64 bytes,void **held,n209_u64 *token)
{ struct fixture *f=opaque;if(role>=2||bytes!=f->source.roles[role].size)return -1;*held=&f->source.roles[role];*token=role+1;return 0; }
static long read_source(void *opaque,void *held,n209_u64 at,void *out,unsigned int bytes)
{ struct fixture *f=opaque;unsigned int role;if(held==&f->source.roles[0])role=0;else if(held==&f->source.roles[1])role=1;else return -1;return n226_read(&f->source,f->holder,role,at,out,bytes,&codec,f); }
static void put(void *opaque,void *held)
{ struct fixture *f=opaque;(void)held;f->puts++; }
static int hash_begin(void *opaque)
{ n219_sha256_init(&((struct fixture *)opaque)->hash);return 0; }
static int hash_update(void *opaque,const void *raw,unsigned int bytes)
{ return n219_sha256_update(&((struct fixture *)opaque)->hash,raw,bytes); }
static int hash_end(void *opaque,n209_u8 *out)
{ return n219_sha256_final(&((struct fixture *)opaque)->hash,out); }
static int write_destination(void *opaque,n209_u64 offset,const void *raw,unsigned int bytes)
{ struct fixture *f=opaque;if(bytes>N209_DESTINATION_BYTES||offset>N209_DESTINATION_BYTES-bytes)return -1;memcpy(f->destination+(size_t)offset,raw,bytes);f->writes++;return 0; }
static int read_destination(void *opaque,n209_u64 offset,void *raw,unsigned int bytes)
{ struct fixture *f=opaque;if(bytes>N209_DESTINATION_BYTES||offset>N209_DESTINATION_BYTES-bytes)return -1;memcpy(raw,f->destination+(size_t)offset,bytes);if(f->corrupt&&offset==0)((n209_u8 *)raw)[0]^=1;return 0; }
static int clear_destination(void *opaque,n209_u64 offset,n209_u64 bytes)
{ struct fixture *f=opaque;if(owner(f,&f->owner)||bytes>N209_DESTINATION_BYTES||offset>N209_DESTINATION_BYTES-bytes)return -1;memset(f->destination+(size_t)offset,0,(size_t)bytes);f->clears++;return 0; }
static const struct n217_io io={owner,hold,read_source,put,hash_begin,hash_update,hash_end,write_destination,read_destination,clear_destination};
static void read_file(const char *directory,const char *name,void *out,size_t cap,size_t exact)
{
    char path[4096];FILE *stream;size_t got;int tail;
    if(snprintf(path,sizeof(path),"%s/%s",directory,name)<0||(stream=fopen(path,"rb"))==NULL)exit(2);
    got=fread(out,1,cap,stream);tail=fgetc(stream);if(ferror(stream)||tail!=EOF||(exact&&got!=exact)||!got)exit(2);fclose(stream);
}
static void reset(struct fixture *f,const char *directory,unsigned int variant)
{
    n209_u8 *holder=f->holder,*destination=f->destination;void *workspace=f->workspace;char name[32];
    end(f);memset(f,0,sizeof(*f));f->holder=holder;f->destination=destination;f->workspace=workspace;
    memset(holder,0,N226_SOURCE_CAP);memset(destination,0,(size_t)N209_DESTINATION_BYTES);
    snprintf(name,sizeof(name),"case%u.bin",variant);read_file(directory,name,holder,N226_SOURCE_CAP,0);
    read_file(directory,"payload.bin",f->request.prepared.payload,256,256);
    memcpy(f->owner.magic,"N210DST1",8);f->owner.schema=1;f->owner.bytes=96;f->owner.region.base=0x81004000ULL;
    f->owner.region.size=N209_DESTINATION_BYTES;f->owner.region.generation=1;f->owner.region.page_shift=12;f->owner.region.status=1;
    memset(f->owner.region.build,'a',32);memset(f->owner.region.cookie,'c',16);f->request.prepared.destination=f->owner;
    memset(f->context.build,'a',32);memset(f->context.boot,'b',32);memset(f->context.cycle,'c',32);
    f->context.return_armed=f->context.page_reserved=f->context.pid1=f->context.cap_sys_boot=1;
    memcpy(f->request.magic,"N217SRC1",8);f->request.schema=1;f->request.bytes=496;
    memcpy(f->request.prepared.binding.magic,"N210BND1",8);f->request.prepared.binding.schema=1;f->request.prepared.binding.bytes=128;
    memcpy(f->request.prepared.binding.build,f->context.build,32);memcpy(f->request.prepared.binding.cycle,f->context.cycle,32);
    if(n226_descriptor_digest(&f->hash,f->request.prepared.payload,f->request.prepared.binding.descriptor_sha256))exit(2);
    memcpy(f->prepared.magic,"N210RCP1",8);f->prepared.schema=1;f->prepared.bytes=192;f->prepared.status=1;f->prepared.flags=3;
    f->prepared.generation=1;memcpy(f->prepared.build,f->context.build,32);memcpy(f->prepared.boot,f->context.boot,32);
    memcpy(f->prepared.cycle,f->context.cycle,32);memcpy(f->prepared.cookie,f->owner.region.cookie,16);
    memcpy(f->prepared.descriptor_sha256,f->request.prepared.binding.descriptor_sha256,32);
}
static int attempt(struct fixture *f)
{
    if(f->state.spent)return -114;
    if(n226_open(&f->source,f->holder,N226_SOURCE_CAP,f->request.prepared.payload,&f->hash,&codec,f)){f->state.spent=1;return -22;}
    return n217_consume(&f->request,&f->owner,&f->context,&f->prepared,&f->state,&io,f,f->stage,4096);
}
static int cleared(struct fixture *f)
{ unsigned int i;for(i=0;i<65536;i++)if(f->destination[i])return 0;return 1; }
int main(int argc,char **argv)
{
    struct fixture *f;unsigned int v,written;n209_u8 digest[32];
    if(argc!=2)return 2;f=calloc(1,sizeof(*f));if(!f)return 2;
    f->holder=calloc(1,N226_SOURCE_CAP);f->destination=calloc(1,(size_t)N209_DESTINATION_BYTES);f->workspace=malloc((size_t)zlib_inflate_workspacesize());
    if(!f->holder||!f->destination||!f->workspace)return 2;
    for(v=0;v<14;v++){
        variants++;reset(f,argv[1],v);
        if(v==0){
            CHECK(n226_descriptor_digest(&f->hash,f->request.prepared.payload,digest)==0&&memcmp(digest,f->holder+64,32)==0);
            CHECK(attempt(f)==0);CHECK(f->state.result.status==1&&f->state.result.destination_content_verified==1);
            CHECK(f->source.parser_state==4&&f->source.current_role==2&&f->state.result.source_data_bytes==81920);
            CHECK(f->puts==0&&f->state.result.source_pages_physically_pinned==0&&f->stage[1]=='A'&&f->stage[4095]=='A');
        }else if(v==1){CHECK(attempt(f)!=0);CHECK(f->clears>0);CHECK(f->state.spent&&f->state.result.status==2&&cleared(f));}
        else if(v==2||v==3){CHECK(attempt(f)!=0);CHECK(f->state.spent);}
        else if(v==4||v==5){CHECK(attempt(f)!=0);CHECK(!f->state.result.copied_bytes[0]&&f->puts==2);}
        else if(v==6){CHECK(attempt(f)!=0);CHECK(f->state.spent&&!f->writes);}
        else if(v==7){f->lose=1;CHECK(attempt(f)!=0);CHECK(f->state.result.quarantined==1);CHECK(f->writes==1&&!f->clears);}
        else if(v==8){f->corrupt=1;CHECK(attempt(f)!=0);CHECK(f->clears>0);CHECK(f->state.result.status==2&&cleared(f));}
        else if(v==9){CHECK(n226_open(&f->source,f->holder,N226_SOURCE_CAP,f->request.prepared.payload,&f->hash,&codec,f)==0);CHECK(n226_read(&f->source,f->holder,1,0,f->stage,4096,&codec,f)<0);}
        else if(v==10){CHECK(attempt(f)==0);written=f->writes;CHECK(attempt(f)==-114);CHECK(f->writes==written&&f->state.result.status==1);}
        else if(v==11){CHECK(attempt(f)!=0);CHECK(f->state.spent&&!f->writes);}
        else if(v==12){CHECK(n226_stack_room(0x1008,0x5000,0x4800,8192,4096)==1);}
        else{CHECK(n226_stack_room(0x1008,0x5000,0x4007,8192,4096)==0&&n226_stack_room(0x1008,0x5000,0x5001,8192,4096)==0);}
    }
    printf("{\"groups\":1,\"variants\":%u,\"assertions\":%u}\n",variants,assertions);
    end(f);free(f->workspace);free(f->holder);free(f->destination);free(f);return 0;
}
