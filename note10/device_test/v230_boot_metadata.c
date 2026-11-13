/* SPDX-License-Identifier: GPL-2.0-only */
#include "v230_boot_metadata.h"

static int n230_span(const void *p,n209_u64 bytes)
{ return p && bytes && bytes<=UINTPTR_MAX-(uintptr_t)p; }
static int n230_overlap(const void *a,n209_u64 as,const void *b,n209_u64 bs)
{
    uintptr_t av=(uintptr_t)a,bv=(uintptr_t)b;
    return av<bv+bs && bv<av+as;
}
static void n230_copy(void *dst,const void *src,n209_u64 bytes)
{
    volatile n209_u8 *d=dst;const volatile n209_u8 *s=src;n209_u64 i;
    for(i=0;i<bytes;i++)d[i]=s[i];
}

int n230_project_metadata(const struct n209_payload *payload,const struct n209_destination *destination,
    const n209_u8 *adt,n209_u32 adt_bytes,n209_u8 *args,n209_u64 args_capacity,
    n209_u8 *record,n209_u64 record_capacity,struct n230_placement *out)
{
    struct n230_placement candidate;
    struct n10_rt_boot_fields fields={0};
    n209_u8 args_bytes[N10_RT_ARGS_SIZE],record_bytes[N10_RT_RECORD_SIZE];
    const void *inputs[3]={payload,destination,adt};
    n209_u64 input_sizes[3]={sizeof(*payload),sizeof(*destination),adt_bytes};
    void *outputs[3]={args,record,out};
    n209_u64 output_sizes[3]={N10_RT_ARGS_SIZE,N10_RT_RECORD_SIZE,sizeof(*out)};
    unsigned int i,j;int error;
    if(!adt_bytes || adt_bytes>N10_RT_PAGE || args_capacity<N10_RT_ARGS_SIZE || record_capacity<N10_RT_RECORD_SIZE)
        return N10_RT_BUFFER;
    for(i=0;i<3;i++)if(!n230_span(inputs[i],input_sizes[i]) || !n230_span(outputs[i],output_sizes[i]))return N10_RT_BUFFER;
    for(i=0;i<3;i++) {
        for(j=0;j<3;j++)if(n230_overlap(outputs[i],output_sizes[i],inputs[j],input_sizes[j]))return N10_RT_BUFFER;
        for(j=i+1;j<3;j++)if(n230_overlap(outputs[i],output_sizes[i],outputs[j],output_sizes[j]))return N10_RT_BUFFER;
    }
    /* Ingestion placed the adapter after the full 1MiB gap, not actual ADT size. */
    error=n209_layout_bounds(payload,destination,N209_ADT_MAX,&candidate.layout);
    if(error)return error;
    error=n10_rt_validate_adt(adt,adt_bytes);if(error)return error;
    candidate.arguments_physical=destination->base+candidate.layout.args_offset;
    candidate.adt_physical=destination->base+candidate.layout.adt_offset;
    candidate.adt_virtual=payload->virtual_base+candidate.layout.adt_offset;
    candidate.adapter_physical=destination->base+candidate.layout.adapter_offset;
    candidate.entry_physical=destination->base+payload->kernel_entry_offset;
    candidate.record_physical=candidate.adapter_physical+payload->adapter_record_offset;
    candidate.top_physical=destination->base+candidate.layout.top_offset;
    fields.virtual_base=payload->virtual_base;fields.physical_base=destination->base;
    fields.memory_size=destination->size;fields.top_of_kernel=candidate.top_physical;
    fields.device_tree_pointer=candidate.adt_virtual;fields.device_tree_length=adt_bytes;
    fields.memory_size_actual=destination->size;
    error=n10_rt_serialize_boot_args(&fields,args_bytes,sizeof(args_bytes));if(error)return error;
    error=n10_rt_serialize_record(candidate.arguments_physical,candidate.entry_physical,record_bytes,sizeof(record_bytes));if(error)return error;
    n230_copy(args,args_bytes,sizeof(args_bytes));n230_copy(record,record_bytes,sizeof(record_bytes));
    n230_copy(out,&candidate,sizeof(candidate));return 0;
}

#ifdef __KERNEL__
/* Computed ABS witnesses avoid allocating measurement arrays. Never called. */
static __used noinline void n230_layout_witness(void)
{
    asm volatile(".globl n230_size_placement\n.equ n230_size_placement,%c0\n"
                 ".globl n230_align_placement\n.equ n230_align_placement,%c1\n"
                 ".globl n230_offset_addresses\n.equ n230_offset_addresses,%c2\n"
                 ".globl n230_offset_top\n.equ n230_offset_top,%c3\n"
                 : : "i"(sizeof(struct n230_placement)),"i"(__alignof__(struct n230_placement)),
                     "i"(offsetof(struct n230_placement,arguments_physical)),"i"(offsetof(struct n230_placement,top_physical)));
}
#endif
