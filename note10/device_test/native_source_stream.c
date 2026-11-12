/* SPDX-License-Identifier: GPL-2.0-only */
#include "native_source_stream.h"
#define N226_END 1U
N226_NOINLINE int n226_stack_room(n209_u64 floor,n209_u64 top,n209_u64 sp,unsigned int chain,unsigned int guard)
{
    return top>floor&&sp>=floor&&sp<=top&&chain>0&&chain<=N226_CHAIN_CAP&&guard==N226_STACK_GUARD&&
           (n209_u64)chain+guard<=sp-floor;
}
static n209_u64 n226_le(const n209_u8 *raw,unsigned int count)
{ n209_u64 v=0;unsigned int i;for(i=0;i<count;i++)v|=(n209_u64)raw[i]<<(8*i);return v; }
static int n226_same(const void *a,const void *b,unsigned int count)
{ const n209_u8 *x=a,*y=b;unsigned int i;for(i=0;i<count;i++)if(x[i]!=y[i])return 0;return 1; }
static void n226_zero(void *out,unsigned int bytes)
{ n209_u8 *p=out;unsigned int i;for(i=0;i<bytes;i++)p[i]=0; }
static int n226_zeros(const n209_u8 *p,unsigned long count)
{ unsigned long i;for(i=0;i<count;i++)if(p[i])return 0;return 1; }
static int n226_hex(const n209_u8 *p,n209_u32 *out)
{
    unsigned int i,d;n209_u32 v=0;
    for(i=0;i<8;i++){
        if(p[i]>='0'&&p[i]<='9')d=p[i]-'0';
        else if(p[i]>='a'&&p[i]<='f')d=p[i]-'a'+10;
        else if(p[i]>='A'&&p[i]<='F')d=p[i]-'A'+10;
        else return -22;
        v=(v<<4)|d;
    }
    *out=v;return 0;
}
static N226_NOINLINE int n226_pull(struct n226_stream *s,const n209_u8 *holder,n209_u8 *out,unsigned int bytes,
                                 const struct n226_codec *codec,void *opaque)
{
    unsigned int used,got,available;int rc;
    if(!bytes||bytes>N217_CHUNK||s->raw_cursor>s->output_limit||bytes>s->output_limit-s->raw_cursor)return -22;
    while(bytes){
        if(s->flags&N226_END||s->compressed_cursor>s->member_bytes-8)return -22;
        available=(unsigned int)(s->member_bytes-8-s->compressed_cursor);used=got=0;
        rc=codec->pull(opaque,holder+N226_HEADER_BYTES+s->compressed_cursor,available,out,bytes,&used,&got);
        if(rc<0||rc>1||used>available||got>bytes||(!used&&!got&&rc!=1))return -22;
        s->compressed_cursor+=used;s->raw_cursor+=got;s->crc32=codec->crc(s->crc32,out,got);
        out+=got;bytes-=got;if(rc==1)s->flags|=N226_END;
    }
    return 0;
}
static N226_NOINLINE int n226_entry(struct n226_stream *s,const n209_u8 *holder,unsigned int entry,n209_u64 size,
                                  const struct n226_codec *codec,void *opaque)
{
    static const char *const names[]={"n10","n10/kernel.mem","n10/adapter.mem","TRAILER!!!"};
    static const unsigned int lengths[]={4,15,16,11};
    n209_u32 value;unsigned int i,pad;
    if(entry>=4||size>0xffffffffULL||n226_pull(s,holder,s->newc_header,110,codec,opaque)||
       !n226_same(s->newc_header,"070701",6))return -22;
    for(i=0;i<13;i++){
        n209_u32 wanted=0;
        if(i==0)wanted=entry+1;
        else if(i==1)wanted=entry==0?040700U:entry==3?0U:0100400U;
        else if(i==4)wanted=1;
        else if(i==6)wanted=(n209_u32)size;
        else if(i==11)wanted=lengths[entry];
        if(n226_hex(s->newc_header+6+8*i,&value)||value!=wanted)return -22;
    }
    if(n226_pull(s,holder,s->name,lengths[entry],codec,opaque)||!n226_same(s->name,names[entry],lengths[entry]))return -22;
    pad=(4-((110+lengths[entry])&3))&3;
    if(pad&&(n226_pull(s,holder,s->gzip_trailer,pad,codec,opaque)||!n226_zeros(s->gzip_trailer,pad)))return -22;
    return 0;
}
static N226_NOINLINE int n226_finish(struct n226_stream *s,const n209_u8 *holder,n209_u8 *scratch,
                                   const struct n226_codec *codec,void *opaque)
{
    unsigned int pad,chunk,used=0,got=0,available;int rc;
    if(n226_entry(s,holder,3,0,codec,opaque))return -22;
    pad=(unsigned int)((512-(s->raw_cursor&511))&511);
    while(pad){
        chunk=pad>sizeof(s->newc_header)?sizeof(s->newc_header):pad;
        if(n226_pull(s,holder,s->newc_header,chunk,codec,opaque)||!n226_zeros(s->newc_header,chunk))return -22;
        pad-=chunk;
    }
    if(s->raw_cursor!=s->output_limit)return -22;
    if(!(s->flags&N226_END)){
        if(s->compressed_cursor>s->member_bytes-8)return -22;
        available=(unsigned int)(s->member_bytes-8-s->compressed_cursor);
        rc=codec->pull(opaque,holder+N226_HEADER_BYTES+s->compressed_cursor,available,scratch,1,&used,&got);
        if(rc!=1||got||used>available)return -22;
        s->compressed_cursor+=used;s->flags|=N226_END;
    }
    if(s->compressed_cursor!=s->member_bytes-8)return -22;
    for(pad=0;pad<8;pad++)s->gzip_trailer[pad]=holder[N226_HEADER_BYTES+s->member_bytes-8+pad];
    s->trailer_crc32=(n209_u32)n226_le(s->gzip_trailer,4);s->trailer_isize=(n209_u32)n226_le(s->gzip_trailer+4,4);
    if(s->trailer_crc32!=~s->crc32||s->trailer_isize!=s->raw_cursor)return -22;
    s->parser_state=4;s->current_role=2;return 0;
}
N226_NOINLINE int n226_descriptor_digest(struct n219_sha256 *hash,const n209_u8 *payload,n209_u8 *out)
{
    if(!hash||!payload||!out)return -22;
    n219_sha256_init(hash);return n219_sha256_update(hash,payload,256)||n219_sha256_final(hash,out)?-22:0;
}
N226_NOINLINE int n226_open(struct n226_stream *s,const n209_u8 *holder,unsigned long capacity,const n209_u8 *payload,
                           struct n219_sha256 *hash,const struct n226_codec *codec,void *opaque)
{
    struct n209_payload decoded;n209_u8 digest[32];unsigned int i;
    if(!s||!holder||capacity!=N226_SOURCE_CAP||!payload||!hash||!codec||!codec->begin||!codec->pull||!codec->crc||!codec->end)return -22;
    n226_zero(s,sizeof(*s));
    if(!n226_same(holder,"N226SRC1",8)||n226_le(holder+8,4)!=1||n226_le(holder+12,4)!=96||n209_decode_payload(payload,256,&decoded))return -22;
    s->member_bytes=n226_le(holder+16,8);s->output_limit=n226_le(holder+24,8);
    if(s->member_bytes<18||s->member_bytes>N226_SOURCE_CAP-N226_HEADER_BYTES||!decoded.kernel_span||
       decoded.kernel_span>19169280ULL||decoded.kernel_span%16384||decoded.adapter_bytes!=16384||
       s->output_limit!=((decoded.kernel_span+decoded.adapter_bytes+496+511)&~511ULL)||s->output_limit>N226_RAW_CAP||
       !n226_zeros(holder+N226_HEADER_BYTES+s->member_bytes,capacity-N226_HEADER_BYTES-(unsigned long)s->member_bytes))return -22;
    if(n226_descriptor_digest(hash,payload,digest)||!n226_same(digest,holder+64,32))return -22;
    n219_sha256_init(hash);if(n219_sha256_update(hash,holder+96,(unsigned int)s->member_bytes)||n219_sha256_final(hash,digest)||!n226_same(digest,holder+32,32))return -22;
    for(i=0;i<10;i++)s->gzip_header[i]=holder[96+i];
    /* Optional gzip fields are excluded by the retained filename-empty recipe; OS/XFL are not guessed. */
    if(s->gzip_header[0]!=0x1f||s->gzip_header[1]!=0x8b||s->gzip_header[2]!=8||s->gzip_header[3]!=0)return -22;
    s->roles[0].size=decoded.kernel_span;s->roles[1].size=decoded.adapter_bytes;s->crc32=~0U;s->compressed_cursor=10;
    if(codec->begin(opaque)||n226_entry(s,holder,0,0,codec,opaque))return -22;
    s->parser_state=1;return 0;
}
N226_NOINLINE long n226_read(struct n226_stream *s,const n209_u8 *holder,unsigned int role,n209_u64 offset,void *out,
                            unsigned int bytes,const struct n226_codec *codec,void *opaque)
{
    if(!s||!holder||!out||!codec||role>=2||s->current_role!=role||offset!=s->roles[role].read||!bytes||bytes>N217_CHUNK)return -22;
    if(offset==s->roles[role].size){
        if(bytes!=1)return -22;
        if(role==0){
            if(n226_entry(s,holder,2,s->roles[1].size,codec,opaque))return -22;
            s->roles[1].offset=s->raw_cursor;s->current_role=1;s->parser_state=3;return 0;
        }
        return n226_finish(s,holder,out,codec,opaque)?-22:0;
    }
    if(offset>s->roles[role].size||bytes>s->roles[role].size-offset)return -22;
    if(role==0&&s->parser_state==1){
        if(n226_entry(s,holder,1,s->roles[0].size,codec,opaque))return -22;
        s->roles[0].offset=s->raw_cursor;s->parser_state=2;
    }
    if(n226_pull(s,holder,out,bytes,codec,opaque))return -22;
    s->roles[role].read+=bytes;return (long)bytes;
}
