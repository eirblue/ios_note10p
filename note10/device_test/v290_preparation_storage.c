/* SPDX-License-Identifier: GPL-2.0-only */
#include "v290_preparation_storage.h"
#ifdef __KERNEL__
#include <linux/string.h>
#else
#include <string.h>
#endif
int n290_plan_storage(struct n290_storage *out,const struct n278_seal *seal,const struct n210_request *request,
    const struct n210_destination *destination,const struct n210_context *context,const struct n210_receipt *prepared)
{
    struct n209_payload payload;struct n209_layout layout;
    if(!out)return -22;
    if(out->phase!=N290_EMPTY)return -114;
    memset(out,0,sizeof(*out));out->phase=N290_REFUSED;
    if(!seal||!request||!destination||!context||!prepared||seal->phase!=N278_VALUES_ONLY||
       memcmp(&seal->values.request,request,sizeof(*request))||
       memcmp(&seal->values.context,context,sizeof(*context))||
       memcmp(&seal->values.prepared,prepared,sizeof(*prepared))||
       memcmp(&request->destination,destination,sizeof(*destination))||
       memcmp(prepared->descriptor_sha256,request->binding.descriptor_sha256,32)||
       memcmp(prepared->cookie,destination->region.cookie,16)||
       prepared->generation!=destination->region.generation||
       n209_decode_payload(request->payload,sizeof(request->payload),&payload)||
       n209_layout_bounds(&payload,&destination->region,N209_ADT_MAX,&layout)||
       memcmp(&layout,&seal->values.layout,sizeof(layout))||layout.top_offset%N209_PAGE||
       layout.top_offset>destination->region.size||N290_STORAGE_BYTES>destination->region.size-layout.top_offset)return -22;
    out->generation=destination->region.generation;out->base=destination->region.base;out->size=destination->region.size;
    out->prior_top=layout.top_offset;out->args_offset=layout.top_offset;
    out->adt_offset=out->args_offset+N209_PAGE;out->record_offset=out->adt_offset+N209_PAGE;
    out->end_offset=out->record_offset+N209_PAGE;
    memcpy(out->cookie,destination->region.cookie,16);
    memcpy(out->descriptor_sha256,seal->values.prepared.descriptor_sha256,32);
    out->phase=N290_INITIALIZING;return 0;
}
#ifdef __KERNEL__
static __used __attribute__((__noinline__)) void n290_layout_witness(void)
{
    asm volatile(".globl n290_size_storage\n.equ n290_size_storage,%c0\n"
                 ".globl n290_align_storage\n.equ n290_align_storage,%c1\n"
                 ".globl n290_offset_digest\n.equ n290_offset_digest,%c2\n"
                 ".globl n290_pool_offset\n.equ n290_pool_offset,%c3\n"
                 : : "i"(sizeof(struct n290_storage)),"i"(__alignof__(struct n290_storage)),
                     "i"(offsetof(struct n290_storage,descriptor_sha256)),"i"(N290_STORAGE_OFFSET));
}
#endif
