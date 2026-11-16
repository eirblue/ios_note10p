/* SPDX-License-Identifier: GPL-2.0-only */
#include "v285_current_cpu_metadata.h"
#ifdef __KERNEL__
#include <linux/string.h>
#else
#include <string.h>
#endif

/* Canonical property writer; all names and node shape are fixed here. */
static int n285_put_property(n209_u8 *out,n209_u32 *at,const char *name,
                             const n209_u8 *value,n209_u32 bytes)
{
    n209_u32 i,n=0,padded=(bytes+3U)&~3U;
    while(name[n]&&n<32U)n++;
    if(n==32U||*at>16384U||36U+padded>16384U-*at)return -22;
    memset(out+*at,0,36U+padded);memcpy(out+*at,name,n);
    for(i=0;i<4;i++)out[*at+32U+i]=(n209_u8)(bytes>>(8U*i));
    memcpy(out+*at+36U,value,bytes);*at+=36U+padded;return 0;
}
static int n285_encode_cpu_adt(struct n285_workspace *w,n209_u32 *bytes)
{
    n209_u32 i,j,at=0,value,count=w->snapshot.count;char name[13];
    n209_u8 reg[4],frequency[4];int error;
    if(!count||count>N285_MAX_CPUS||!w->snapshot.frequency||w->snapshot.reserved)return -22;
    for(i=1;i<count;i++){
        value=w->snapshot.affinity[i];j=i;
        while(j&&w->snapshot.affinity[j-1]>value){w->snapshot.affinity[j]=w->snapshot.affinity[j-1];j--;}
        w->snapshot.affinity[j]=value;
    }
    for(i=1;i<count;i++)if(w->snapshot.affinity[i]==w->snapshot.affinity[i-1])return -22;
    for(i=0,j=0;i<count;i++)if(w->snapshot.affinity[i]==w->snapshot.selected)j++;
    if(j!=1)return -22;
    memset(w->adt,0,sizeof(w->adt));w->adt[0]=1;w->adt[4]=1;at=8;
    error=n285_put_property(w->adt,&at,"name",(const n209_u8 *)"device-tree",12);if(error)return error;
    w->adt[at]=1;w->adt[at+4]=(n209_u8)count;at+=8;
    error=n285_put_property(w->adt,&at,"name",(const n209_u8 *)"cpus",5);if(error)return error;
    for(i=0;i<count;i++){
        n209_u32 n=0,shift,affinity=w->snapshot.affinity[i];
        memcpy(name,"cpu@",4);n=4;
        for(shift=28;shift&&!(affinity>>shift);shift-=4){}
        do{name[n++]="0123456789abcdef"[(affinity>>shift)&15U];if(!shift)break;shift-=4;}while(1);
        name[n++]=0;w->adt[at]=(n209_u8)(affinity==w->snapshot.selected?5:3);at+=8;
        error=n285_put_property(w->adt,&at,"name",(const n209_u8 *)name,n);if(error)return error;
        error=n285_put_property(w->adt,&at,"device_type",(const n209_u8 *)"cpu",4);if(error)return error;
        for(j=0;j<4;j++){reg[j]=(n209_u8)(affinity>>(8*j));frequency[j]=(n209_u8)(w->snapshot.frequency>>(8*j));}
        error=n285_put_property(w->adt,&at,"reg",reg,4);if(error)return error;
        if(affinity==w->snapshot.selected){
            error=n285_put_property(w->adt,&at,"state",(const n209_u8 *)"running",8);if(error)return error;
            error=n285_put_property(w->adt,&at,"timebase-frequency",frequency,4);if(error)return error;
        }
    }
    *bytes=at;return 0;
}
int n285_prepare_metadata(const struct n210_request *request,const struct n210_destination *destination,
    const struct n210_context *context,void *opaque,
    struct n285_workspace *w,unsigned int capacity)
{
    n209_u32 bytes;int error;struct n285_header *h;
    if(!request||!destination||!context||!w||capacity<sizeof(*w))return -22;
    error=n209_decode_payload(request->payload,sizeof(request->payload),&w->payload);if(error)return error;
    error=n285_encode_cpu_adt(w,&bytes);if(error)return error;
    error=n230_project_metadata(&w->payload,&destination->region,w->adt,bytes,w->args,sizeof(w->args),
                                w->record,sizeof(w->record),&w->placement);if(error)return error;
    /* Each write is in the existing args page or first ADT page. No adapter write. */
    if(w->placement.layout.adt_offset!=w->placement.layout.args_offset+N209_PAGE||
       w->placement.layout.adapter_offset<w->placement.layout.adt_offset+N209_ADT_MAX||
       N285_HEADER_OFFSET+sizeof(w->header)>N209_PAGE)return -22;
    h=&w->header;memset(h,0,sizeof(*h));memcpy(h->magic,"N285STG1",8);h->schema=1;h->bytes=sizeof(*h);
    memcpy(h->build,context->build,32);memcpy(h->boot,context->boot,32);memcpy(h->cycle,context->cycle,32);
    memcpy(h->cookie,destination->region.cookie,16);h->generation=destination->region.generation;
    h->base=destination->region.base;h->size=destination->region.size;
    h->args_offset=w->placement.layout.args_offset;h->adt_offset=w->placement.layout.adt_offset;
    h->adt_bytes=bytes;h->flags=3; /* sampled-only and non-installed shadow; never standalone valid */
    memset(w->readback,0,sizeof(w->readback));
    error=n285_write_pages(opaque,h->args_offset+N285_HEADER_OFFSET,w->readback,sizeof(*h));if(error)return error;
    error=n285_write_pages(opaque,h->adt_offset,w->adt,bytes);if(error)return error;
    error=n285_write_pages(opaque,h->args_offset,w->args,sizeof(w->args));if(error)return error;
    error=n285_write_pages(opaque,h->args_offset+1152,w->record,sizeof(w->record));if(error)return error;
    error=n285_write_pages(opaque,h->args_offset+1216,&w->placement,sizeof(w->placement));if(error)return error;
    error=n285_write_pages(opaque,h->args_offset+N285_HEADER_OFFSET,h,sizeof(*h));if(error)return error;
    error=n285_readback_pages(opaque,h->adt_offset,w->adt,bytes,w->readback);if(error)return error;
    error=n285_readback_pages(opaque,h->args_offset,w->args,sizeof(w->args),w->readback);if(error)return error;
    error=n285_readback_pages(opaque,h->args_offset+1152,w->record,sizeof(w->record),w->readback);if(error)return error;
    error=n285_readback_pages(opaque,h->args_offset+1216,&w->placement,sizeof(w->placement),w->readback);if(error)return error;
    return n285_readback_pages(opaque,h->args_offset+N285_HEADER_OFFSET,h,sizeof(*h),w->readback);
}
#ifdef __KERNEL__
static __used __attribute__((__noinline__)) void n285_layout_witness(void)
{
    asm volatile(".globl n285_size_workspace\n.equ n285_size_workspace,%c0\n"
                 ".globl n285_align_workspace\n.equ n285_align_workspace,%c1\n"
                 ".globl n285_offset_snapshot\n.equ n285_offset_snapshot,%c2\n"
                 ".globl n285_offset_readback\n.equ n285_offset_readback,%c3\n"
                 : : "i"(sizeof(struct n285_workspace)),"i"(__alignof__(struct n285_workspace)),
                     "i"(offsetof(struct n285_workspace,snapshot)),"i"(offsetof(struct n285_workspace,readback)));
}
#endif
