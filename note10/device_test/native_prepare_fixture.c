/* SPDX-License-Identifier: GPL-2.0-only */
/* Pure metadata fixtures; success never attests a real PageReserved page. */
#include "native_prepare_core.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static unsigned int assertions,actions;
#define CHECK(x) do{++assertions;if(!(x)){fprintf(stderr,"line%d\n",__LINE__);exit(1);}}while(0)
static int exercise(const struct n210_request *r,const struct n210_destination *d,const struct n210_context *c,const n209_u8 *h,unsigned int *spent,struct n210_receipt *out)
{ int result=n210_prepare_once(r,d,c,h,spent,out);if(!result)++actions;return result; }
static void deny(struct n210_request *r,struct n210_destination *d,struct n210_context *c,n209_u8 *hash,unsigned int spent)
{ struct n210_receipt out;unsigned int before=actions;CHECK(exercise(r,d,c,hash,&spent,&out)!=0);CHECK(actions==before); }
int main(void)
{
    struct n209_payload p={0},decoded;struct n209_layout layout;
    struct n210_request r={0},bad;struct n210_destination d={0};struct n210_context c={0},changed;
    struct n210_receipt receipt,stale;unsigned int spent=0;n209_u8 hash[32];
    memcpy(p.magic,"N209PAY1",8);p.schema=1;p.bytes=256;p.virtual_base=0xffff000001004000ULL;
    p.kernel_span=3*N209_PAGE;p.entry_extent_bytes=16;p.pool_offset=2*N209_PAGE;p.pool_bytes=N209_PAGE;
    p.adapter_bytes=N209_PAGE;p.adapter_record_offset=256;
    memset((n209_u8 *)&p+96,1,160);memset(hash,2,32);
    memcpy(d.magic,"N210DST1",8);d.schema=1;d.bytes=96;d.region.base=N209_ADDRESS_MIN+N210_RESIDUE;
    d.region.size=N209_DESTINATION_BYTES;d.region.generation=1;d.region.page_shift=12;d.region.status=1;
    memset(d.region.build,'1',32);memset(d.region.cookie,1,16);r.destination=d;memcpy(r.payload,&p,256);
    memcpy(r.binding.magic,"N210BND1",8);r.binding.schema=1;r.binding.bytes=128;
    memset(r.binding.build,'1',32);memset(r.binding.cycle,'3',32);memcpy(r.binding.descriptor_sha256,hash,32);
    memset(c.build,'1',32);memset(c.boot,'2',32);memset(c.cycle,'3',32);
    c.return_armed=c.page_reserved=c.pid1=c.cap_sys_boot=1;
    CHECK(exercise(&r,&d,&c,hash,&spent,&receipt)==0);CHECK(n210_receipt_matches(&receipt,&c,&r)==0);
    bad=r;bad.payload[12]=128;deny(&bad,&d,&c,hash,0);
    CHECK(n209_decode_payload(r.payload,255,&decoded)!=0);CHECK(actions==1);
    bad=r;bad.destination.region.generation=2;deny(&bad,&d,&c,hash,0);
    bad=r;bad.destination.region.cookie[0]^=1;deny(&bad,&d,&c,hash,0);
    bad=r;bad.destination.region.build[0]='4';deny(&bad,&d,&c,hash,0);
    stale=receipt;stale.boot[0]='4';CHECK(n210_receipt_matches(&stale,&c,&r)!=0);CHECK(actions==1);
    bad=r;bad.binding.cycle[0]='4';deny(&bad,&d,&c,hash,0);
    changed=c;changed.page_reserved=0;deny(&r,&d,&changed,hash,0);
    changed=c;changed.return_armed=0;deny(&r,&d,&changed,hash,0);
    bad=r;bad.binding.descriptor_sha256[0]^=1;deny(&bad,&d,&c,hash,0);
    changed=c;changed.cap_sys_boot=0;deny(&r,&d,&changed,hash,0);
    deny(&r,&d,&c,hash,1);
    CHECK(n209_prepare_layout(&p,&d.region,1,NULL,NULL,&layout)!=0);CHECK(actions==1);
    CHECK(actions==1);
    printf("{\"groups\":6,\"C_variants\":14,\"C_assertions\":%u,\"metadata_successes\":%u,\"transfer_calls\":0}\n",assertions,actions);
    return 0;
}
