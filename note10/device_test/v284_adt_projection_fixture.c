/* SPDX-License-Identifier: GPL-2.0-only */
/* Private candidate input; synthetic geometry only, no live RAM capability. */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "v230_boot_metadata.h"

static uint64_t little(const unsigned char *p, unsigned int count)
{ uint64_t result=0;unsigned int i;for(i=0;i<count;i++)result|=(uint64_t)p[i]<<(8U*i);return result; }
static int write_bytes(const char *path,const void *data,size_t size)
{
    FILE *stream=fopen(path,"wb");size_t written;int closed;
    if(!stream)return 1;
    written=fwrite(data,1,size,stream);closed=fclose(stream);
    return written!=size || closed!=0;
}
int main(int argc,char **argv)
{
    unsigned char adt[N10_RT_PAGE+1],args[N10_RT_ARGS_SIZE],record[N10_RT_RECORD_SIZE];
    struct n209_payload payload={0};struct n209_destination destination={0};
    struct n230_placement placement;FILE *stream;char *end;unsigned long length;size_t bytes;int closed;
    if(argc!=6)return 10;
    length=strtoul(argv[2],&end,10);
    if(!argv[2][0] || *end || !length || length>N10_RT_PAGE)return 11;
    stream=fopen(argv[1],"rb");if(!stream)return 12;
    bytes=fread(adt,1,sizeof(adt),stream);closed=ferror(stream);if(fclose(stream))closed=1;
    if(closed || bytes!=length)return 13;
    memcpy(payload.magic,"N209PAY1",8);payload.schema=1;payload.bytes=N209_PAYLOAD_BYTES;
    payload.virtual_base=UINT64_C(0xffff000090000000);payload.kernel_span=UINT64_C(0x400000);
    payload.kernel_entry_offset=payload.entry_extent_offset=UINT64_C(0x1000);payload.entry_extent_bytes=4;
    payload.pool_offset=UINT64_C(0x8000);payload.pool_bytes=N209_PAGE;
    payload.adapter_bytes=N209_PAGE;payload.adapter_record_offset=256;
    memset(payload.kernel_sha256,1,32);memset(payload.materialized_sha256,2,32);
    memset(payload.adapter_sha256,3,32);memset(payload.producer_id,4,32);memset(payload.input_binding,5,32);
    destination.base=UINT64_C(0x90000000);destination.size=N209_DESTINATION_BYTES;
    destination.generation=1;destination.page_shift=12;destination.status=1;
    memset(destination.build,'a',32);memset(destination.cookie,6,16);
    if(n230_project_metadata(&payload,&destination,adt,(n209_u32)bytes,args,sizeof(args),
                            record,sizeof(record),&placement))return 14;
    if(little(args+96,8)!=placement.adt_virtual || little(args+104,4)!=bytes ||
       little(record+16,8)!=placement.arguments_physical || little(record+24,8)!=placement.entry_physical ||
       placement.adt_physical!=destination.base+placement.layout.adt_offset ||
       placement.adt_virtual!=payload.virtual_base+placement.layout.adt_offset ||
       placement.entry_physical!=destination.base+payload.kernel_entry_offset ||
       placement.layout.args_offset!=payload.kernel_span || placement.layout.adt_bytes!=N209_ADT_MAX ||
       memcmp(record,"N10XFER1",8))return 15;
    if(write_bytes(argv[3],args,sizeof(args)) || write_bytes(argv[4],record,sizeof(record)) ||
       write_bytes(argv[5],&placement,sizeof(placement)))return 16;
    printf("{\"schema\":\"note10-v284-ADT-projection-C-v1\",\"passed\":true,\"ADT_bytes\":%lu,"
           "\"boot_args_bytes\":1152,\"record_bytes\":64,\"placement_bytes\":96,\"projection_calls\":1}\n",length);
    return 0;
}
