/* SPDX-License-Identifier: GPL-2.0-only */
#include "v230_boot_metadata.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static struct n209_payload payload;
static struct n209_destination destination;
static struct n230_placement placement;
static _Alignas(8) unsigned char arguments[1184],record[96],tree[1152];
static unsigned int assertions,variants;
#define CHECK(x) do { assertions++; if(!(x)){fprintf(stderr,"projection assertion %u at %d\n",assertions,__LINE__);exit(1);} } while(0)

static void initialize(void)
{
    memset(&payload,0,sizeof(payload));memcpy(payload.magic,"N209PAY1",8);payload.schema=1;payload.bytes=256;
    payload.virtual_base=UINT64_C(0xffff000080000000);payload.kernel_span=19169280;
    payload.kernel_entry_offset=256;payload.entry_extent_bytes=16384;payload.pool_offset=32768;payload.pool_bytes=16384;
    payload.adapter_bytes=16384;payload.adapter_record_offset=256;
    memset((unsigned char *)&payload+96,1,160);
    memset(&destination,0,sizeof(destination));destination.base=UINT64_C(0x80000000);destination.size=33554432;
    destination.generation=1;destination.page_shift=12;destination.status=1;
    memset(destination.build,'a',32);memset(destination.cookie,1,16);
    memset(arguments,0xa5,sizeof(arguments));memset(record,0xa5,sizeof(record));memset(&placement,0xa5,sizeof(placement));
    memset(tree,0,sizeof(tree));tree[0]=1;memcpy(tree+8,"name",4);tree[40]=12;memcpy(tree+44,"device-tree",11);
}
static void hex(const unsigned char *bytes,size_t count)
{ size_t i;for(i=0;i<count;i++)printf("%02x",bytes[i]); }
static void accepted(unsigned int variant)
{
    struct n209_payload before_payload=payload;struct n209_destination before_destination=destination;
    unsigned char before_tree[sizeof(tree)],guard[16];
    memcpy(before_tree,tree,sizeof(tree));memset(guard,0xa5,sizeof(guard));variants++;
    CHECK(n230_project_metadata(&payload,&destination,tree,56,arguments+16,1152,record+16,64,&placement)==0);
    CHECK(placement.layout.args_offset==19169280 && placement.layout.adt_offset==19185664 &&
          placement.layout.adt_bytes==1048576 && placement.layout.adapter_offset==20234240 && placement.layout.top_offset==20250624);
    CHECK(placement.arguments_physical==destination.base+19169280 && placement.adt_physical==destination.base+19185664 &&
          placement.adt_virtual==payload.virtual_base+19185664 && placement.adapter_physical==destination.base+20234240 &&
          placement.entry_physical==destination.base+256 && placement.record_physical==destination.base+20234496 &&
          placement.top_physical==destination.base+20250624);
    CHECK(!memcmp(arguments,guard,16) && !memcmp(arguments+1168,guard,16) && !memcmp(record,guard,16) && !memcmp(record+80,guard,16));
    CHECK(!memcmp(&payload,&before_payload,sizeof(payload)) && !memcmp(&destination,&before_destination,sizeof(destination)) && !memcmp(tree,before_tree,sizeof(tree)));
    printf("%s{\"virtual_base\":%llu,\"physical_base\":%llu,\"top\":%llu,\"dt_virtual\":%llu,\"args_pa\":%llu,\"entry_pa\":%llu,\"args_hex\":\"",
        variant?",":"",(unsigned long long)payload.virtual_base,(unsigned long long)destination.base,
        (unsigned long long)placement.top_physical,(unsigned long long)placement.adt_virtual,
        (unsigned long long)placement.arguments_physical,(unsigned long long)placement.entry_physical);
    hex(arguments+16,1152);printf("\",\"record_hex\":\"");hex(record+16,64);printf("\"}");
}
static void rejected(unsigned int adt_bytes,unsigned char *args,unsigned long long args_cap,
    unsigned char *rec,unsigned long long rec_cap,struct n230_placement *out)
{
    struct n209_payload before_payload=payload;struct n209_destination before_destination=destination;
    struct n230_placement before_placement=placement;
    unsigned char before_args[sizeof(arguments)],before_record[sizeof(record)],before_tree[sizeof(tree)];
    memcpy(before_args,arguments,sizeof(arguments));memcpy(before_record,record,sizeof(record));memcpy(before_tree,tree,sizeof(tree));variants++;
    CHECK(n230_project_metadata(&payload,&destination,tree,adt_bytes,args,args_cap,rec,rec_cap,out)!=0);
    CHECK(!memcmp(arguments,before_args,sizeof(arguments)) && !memcmp(record,before_record,sizeof(record)) &&
          !memcmp(tree,before_tree,sizeof(tree)) && !memcmp(&placement,&before_placement,sizeof(placement)) &&
          !memcmp(&payload,&before_payload,sizeof(payload)) && !memcmp(&destination,&before_destination,sizeof(destination)));
}
#define REJECT(bytes) rejected(bytes,arguments+16,1152,record+16,64,&placement)
int main(void)
{
    printf("{\"success\":[");initialize();accepted(0);
    initialize();destination.base+=UINT64_C(0x2004000);payload.virtual_base+=UINT64_C(0x4000);accepted(1);
    printf("],");
    initialize();REJECT(55);
    initialize();tree[0]=0;REJECT(56);
    initialize();REJECT(16385);
    initialize();destination.base+=16384;REJECT(56);
    initialize();payload.virtual_base=UINT64_C(0xffffffffffffc000);REJECT(56);
    initialize();payload.kernel_span=33554432;REJECT(56);
    initialize();rejected(56,arguments+16,1151,record+16,64,&placement);
    initialize();rejected(56,arguments+16,1152,record+16,63,&placement);
    initialize();rejected(56,NULL,1152,record+16,64,&placement);
    initialize();rejected(56,arguments+16,1152,arguments+24,64,&placement);
    initialize();rejected(56,tree,1152,record+16,64,&placement);
    initialize();rejected(56,arguments+16,1152,record+16,64,(struct n230_placement *)arguments);
    initialize();rejected(56,arguments+16,1152,(unsigned char *)&payload,64,&placement);
    printf("\"groups\":1,\"variants\":%u,\"assertions\":%u}\n",variants,assertions);return 0;
}
