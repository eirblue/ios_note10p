/* SPDX-License-Identifier: GPL-2.0-only */
#include "native_prepare_core.h"
static int equal(const void *a,const void *b,unsigned int count)
{ const n209_u8 *x=a,*y=b; unsigned int i; for(i=0;i<count;i++)if(x[i]!=y[i])return 0; return 1; }
static void copy(void *a,const void *b,unsigned int count)
{ n209_u8 *x=a;const n209_u8 *y=b;unsigned int i;for(i=0;i<count;i++)x[i]=y[i]; }
static int hex32(const n209_u8 *p)
{ unsigned int i,nonzero=0;for(i=0;i<32;i++){if(!((p[i]>='0'&&p[i]<='9')||(p[i]>='a'&&p[i]<='f')))return 0;nonzero|=p[i]!='0';}return nonzero!=0; }
int n210_request_valid(const struct n210_request *r,const struct n210_destination *destination,
                       const struct n210_context *context,const n209_u8 *hash)
{
    struct n209_payload p;struct n209_layout prospective;unsigned int i;
    if(!r||!destination||!context||!hash || !equal(destination->magic,"N210DST1",8) || destination->schema!=1 || destination->bytes!=96 ||
       !equal(&r->destination,destination,96) || !hex32(context->build)||!hex32(context->boot)||!hex32(context->cycle) ||
       !equal(destination->region.build,context->build,32) || destination->region.base%N209_DESTINATION_BYTES!=N210_RESIDUE ||
       !equal(r->binding.magic,"N210BND1",8)||r->binding.schema!=1||r->binding.bytes!=128 ||
       !equal(r->binding.build,context->build,32)||!equal(r->binding.cycle,context->cycle,32) ||
       !equal(r->binding.descriptor_sha256,hash,32))return -22;
    for(i=0;i<16;i++)if(r->binding.reserved[i])return -22;
    if(n209_decode_payload(r->payload,256,&p))return -22;
    /* Worst-case prospective ADT capacity only; nothing is materialized. */
    return n209_layout_bounds(&p,&destination->region,N209_ADT_MAX,&prospective);
}
int n210_prepare_once(const struct n210_request *r,const struct n210_destination *destination,
                      const struct n210_context *context,const n209_u8 *hash,unsigned int *spent,
                      struct n210_receipt *out)
{
    struct n210_receipt receipt={0};
    if(!spent||!out||!context)return -22;
    if(*spent)return -114;
    *spent=1; /* Invalid first requests also consume the sole preparation. */
    if(context->return_armed!=1||context->page_reserved!=1||context->pid1!=1||context->cap_sys_boot!=1 ||
       n210_request_valid(r,destination,context,hash))return -1;
    copy(receipt.magic,"N210RCP1",8);receipt.schema=1;receipt.bytes=192;receipt.status=1;
    receipt.generation=destination->region.generation;receipt.flags=3;
    copy(receipt.build,context->build,32);copy(receipt.boot,context->boot,32);copy(receipt.cycle,context->cycle,32);
    copy(receipt.cookie,destination->region.cookie,16);copy(receipt.descriptor_sha256,hash,32);
    *out=receipt;return 0;
}
int n210_receipt_matches(const struct n210_receipt *p,const struct n210_context *c,const struct n210_request *r)
{
    if(!p||!c||!r||!equal(p->magic,"N210RCP1",8)||p->schema!=1||p->bytes!=192||p->status!=1||p->reserved||
       p->tail_reserved||p->flags!=3||p->generation!=r->destination.region.generation||
       !equal(p->build,c->build,32)||!equal(p->boot,c->boot,32)||!equal(p->cycle,c->cycle,32)||
       !equal(p->cookie,r->destination.region.cookie,16)||!equal(p->descriptor_sha256,r->binding.descriptor_sha256,32))return -22;
    return 0;
}
