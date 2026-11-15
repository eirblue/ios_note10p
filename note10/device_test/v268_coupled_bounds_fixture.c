/* SPDX-License-Identifier: GPL-2.0-only */
/* Own synthetic admission data/codec only; no real payload or inflate proof. */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <native_source_stream.h>
_Static_assert(N226_SOURCE_CAP==6237242,"exact new holder");
_Static_assert(N226_KERNEL_CAP==19283968ULL,"exact new kernel cap");
_Static_assert(N226_RAW_CAP==19300864ULL,"exact new raw cap");
#define CHECK(x) do { if(!(x)){fprintf(stderr,"new bound failed at %d\n",__LINE__);return 1;} } while(0)
struct own_codec { unsigned int at; n209_u8 directory[116]; };
static n209_u8 *holder;
static n209_u8 payload[256];
static struct n226_stream state;
static struct n219_sha256 hash;
static struct own_codec codec;
static void little(n209_u8 *p,n209_u64 value,unsigned int count)
{ unsigned int i;for(i=0;i<count;i++)p[i]=(n209_u8)(value>>(i*8)); }
static void hex8(n209_u8 *p,unsigned int value)
{ static const char digits[]="0123456789abcdef";unsigned int i;for(i=0;i<8;i++)p[7-i]=(n209_u8)digits[(value>>(i*4))&15]; }
static int begin(void *opaque)
{ ((struct own_codec *)opaque)->at=0;return 0; }
static int pull(void *opaque,const n209_u8 *in,unsigned int available,n209_u8 *out,unsigned int bytes,unsigned int *used,unsigned int *got)
{
    struct own_codec *c=opaque;(void)in;(void)available;
    if(c->at>sizeof(c->directory)||bytes>sizeof(c->directory)-c->at)return -1;
    memcpy(out,c->directory+c->at,bytes);c->at+=bytes;*used=0;*got=bytes;return 0;
}
static n209_u32 crc(n209_u32 seed,const n209_u8 *data,unsigned int bytes)
{ (void)data;(void)bytes;return seed; }
static void end(void *opaque){(void)opaque;}
static const struct n226_codec mock={begin,pull,crc,end};
static int open_case(n209_u64 span,n209_u64 raw)
{
    n209_u8 digest[32];unsigned int i;
    memset(holder,0,N226_SOURCE_CAP);memset(payload,0,sizeof(payload));
    memcpy(payload,"N209PAY1",8);little(payload+8,1,4);little(payload+12,256,4);little(payload+24,span,8);little(payload+72,16384,8);
    memcpy(holder,"N226SRC1",8);little(holder+8,1,4);little(holder+12,96,4);little(holder+16,18,8);little(holder+24,raw,8);
    holder[96]=0x1f;holder[97]=0x8b;holder[98]=8;
    n219_sha256_init(&hash);if(n219_sha256_update(&hash,holder+96,18)||n219_sha256_final(&hash,digest))return -1;memcpy(holder+32,digest,32);
    if(n226_descriptor_digest(&hash,payload,digest))return -1;memcpy(holder+64,digest,32);
    memset(&codec,0,sizeof(codec));memcpy(codec.directory,"070701",6);
    for(i=0;i<13;i++)hex8(codec.directory+6+i*8,i==0||i==4?1:i==1?040700:i==11?4:0);
    memcpy(codec.directory+110,"n10",4);
    return n226_open(&state,holder,N226_SOURCE_CAP,payload,&hash,&mock,&codec);
}
int main(void)
{
    holder=calloc(1,N226_SOURCE_CAP);CHECK(holder!=NULL);
    printf("N267CAPS source=%u kernel=%llu raw=%llu\n",(unsigned)N226_SOURCE_CAP,(unsigned long long)N226_KERNEL_CAP,(unsigned long long)N226_RAW_CAP);fflush(stdout);
    CHECK(open_case(N226_KERNEL_CAP,N226_RAW_CAP)==0);
    CHECK(state.roles[0].size==N226_KERNEL_CAP);
    CHECK(open_case(N226_KERNEL_CAP+16384,N226_RAW_CAP+16384)!=0);
    CHECK(open_case(N226_KERNEL_CAP-1,N226_RAW_CAP)!=0);
    puts("N267CASE kernel-span=PASS");fflush(stdout);
    CHECK(open_case(N226_KERNEL_CAP,N226_RAW_CAP+512)!=0);
    CHECK(open_case(N226_KERNEL_CAP-16384,N226_RAW_CAP)!=0);
    CHECK(open_case(N226_KERNEL_CAP-16384,N226_RAW_CAP-16384)==0);
    puts("N267CASE raw-header=PASS");fflush(stdout);
    free(holder);return 0;
}
