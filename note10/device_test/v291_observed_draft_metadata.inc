/* SPDX-License-Identifier: GPL-2.0-only */
#include "v291_observed_draft_metadata.h"
#ifdef __KERNEL__
#define N291_OWNER n217_owner
#define N291_LOCKED() lockdep_assert_held(&n210_lock)
#define N291_PUBLISH(h,p) WRITE_ONCE((h)->phase,p)
#elif defined(N291_HOST_FIXTURE)
#define N291_OWNER n291_fixture_owner
#define N291_LOCKED() ((void)0)
#define N291_PUBLISH(h,p) ((h)->phase=p)
#else
#error "291 requires kernel or explicit host fixture"
#endif
struct n291_walk { n285_node *node,*parent;n209_u32 depth,reserved; };
_Static_assert(sizeof(struct n291_walk)==24&&N291_WALK_OFFSET+sizeof(struct n291_walk)*32<=20480,"bounded existing-padding walk");
static __attribute__((__always_inline__)) inline n209_u64 n291_be(const n209_u8 *p,unsigned int bytes)
{ n209_u64 value=0;unsigned int i;for(i=0;i<bytes;i++)value=(value<<8)|p[i];return value; }
static __attribute__((__noinline__)) int n291_status(const n285_property *p,n209_u32 *flags)
{
    const n209_u8 *s;int i;
    if(!p)return 0;if(!p->value||p->length<2||p->length>32)return -22;s=p->value;
    if(s[p->length-1])return -22;
    for(i=0;i<p->length-1;i++)if(s[i]<32||s[i]>126)return -22;
    if((p->length==3&&!memcmp(s,"ok",3))||(p->length==5&&!memcmp(s,"okay",5)))return 0;
    if(p->length==9&&!memcmp(s,"disabled",9))*flags|=N291_DISABLED;else *flags|=N291_UNKNOWN_STATUS;
    return 0;
}
static __attribute__((__noinline__)) int n291_collect_locked(struct n291_observation *o,const struct n285_cpu_snapshot *cpu,struct n291_walk *walk)
{
    n285_node *node,*root,*parent=0;const n285_property *p;const n209_u8 *raw;
    unsigned long irq=0;unsigned int i,selected=0,depth=0,used=0,stride,at,address_cells,size_cells;int bad=0,error=-22;
    if(!o||!cpu||!walk||!cpu->count||cpu->count>N285_MAX_CPUS||cpu->reserved||cpu->frequency<1000000||cpu->frequency>0x7fffffff)return -22;
    for(i=0;i<cpu->count;i++)if(cpu->affinity[i]==cpu->selected)selected++;
    if(selected!=1)return -22;
    memset(o,0,sizeof(*o));o->selected=cpu->selected;o->frequency=cpu->frequency;o->flags=N291_SOURCE_OF_REG|N291_CPU_SAMPLED;
    N285_LOCK(irq);root=N285_ROOT;if(!root)goto done;
    p=n285_find_property_locked(root,"#address-cells",&bad);
    if(bad||!p||!p->value||p->length!=4)goto done;o->address_cells=(n209_u32)n291_be(p->value,4);
    p=n285_find_property_locked(root,"#size-cells",&bad);
    if(bad||!p||!p->value||p->length!=4)goto done;o->size_cells=(n209_u32)n291_be(p->value,4);
    if((o->address_cells!=1&&o->address_cells!=2)||(o->size_cells!=1&&o->size_cells!=2))goto done;
    stride=4*(o->address_cells+o->size_cells);node=root;
    while(node){
        if(++o->scanned_nodes>4096||depth>32)goto done;
        p=n285_find_property_locked(node,"device_type",&bad);if(bad)goto done;
        if(p&&p->value&&p->length==7&&!memcmp(p->value,"memory",7)){
            p=n285_find_property_locked(node,"status",&bad);if(bad||n291_status(p,&o->flags))goto done;
            p=n285_find_property_locked(node,"hotpluggable",&bad);if(bad)goto done;if(p)o->flags|=N291_HOTPLUG;
            address_cells=o->address_cells;size_cells=o->size_cells;
            if(depth!=1){
                if(!parent)goto done;
                p=n285_find_property_locked(parent,"#address-cells",&bad);
                if(bad||!p||!p->value||p->length!=4)goto done;address_cells=(unsigned int)n291_be(p->value,4);
                p=n285_find_property_locked(parent,"#size-cells",&bad);
                if(bad||!p||!p->value||p->length!=4)goto done;size_cells=(unsigned int)n291_be(p->value,4);
                if((address_cells!=1&&address_cells!=2)||(size_cells!=1&&size_cells!=2))goto done;
                o->flags|=N291_UNSUPPORTED;
            }
            stride=4*(address_cells+size_cells);p=n285_find_property_locked(node,"reg",&bad);
            if(bad||!p||!p->value||p->length<=0||(unsigned int)p->length%stride)goto done;
            if((unsigned int)p->length/stride>N291_MAX_RANGES-o->count-o->unsupported)goto done;raw=p->value;
            for(at=0;at<(unsigned int)p->length;at+=stride){
                n209_u64 base=n291_be(raw+at,4*address_cells),size=n291_be(raw+at+4*address_cells,4*size_cells);
                if(!size||base>~(n209_u64)0-size)goto done;
                if(depth!=1)o->unsupported++; /* Count validated untranslated tuples; never label them physical. */
                else{
                    struct n291_range *range=&o->ranges[o->count++];range->base=base;range->size=size;
                    range->node_ordinal=o->scanned_nodes;range->tuple_ordinal=at/stride;
                }
            }
        }
        if(node->child){
            if(used==32)goto done;
            walk[used].node=node->sibling;walk[used].parent=parent;walk[used++].depth=depth;parent=node;node=node->child;depth++;
        }else if(node->sibling)node=node->sibling;
        else{
            node=0;while(used&&!node){used--;node=walk[used].node;parent=walk[used].parent;depth=walk[used].depth;}
        }
    }
    error=0;
 done:
    N285_UNLOCK(irq);return error;
}
static __attribute__((__noinline__)) int n291_prepare_draft_locked(struct n290_storage *storage,const struct n278_seal *seal,
    const struct n210_request *request,const struct n210_destination *destination,const struct n210_context *context,
    const struct n210_receipt *prepared,void *opaque,struct n285_workspace *w,unsigned int capacity)
{
    struct n290_storage expected={0};struct n10_rt_boot_fields fields={0};struct n291_header *h;
    struct n291_observation *o;n209_u8 *packet;struct n291_walk *walk;n209_u32 i,bytes=0,inventory=0;int error;
    N291_LOCKED();if(!storage||!w||capacity<sizeof(*w))return -22;
    h=(struct n291_header *)storage->reserved;
    if(storage->phase!=N290_STORAGE_PREPARED||h->phase!=N291_EMPTY)return -114;
    for(i=0;i<sizeof(*h);i++)if(((n209_u8 *)h)[i]){h->phase=N291_REFUSED;return -22;}
    h->phase=N291_REFUSED;
    if(N291_OWNER(opaque,destination))return -116;
    error=n290_plan_storage(&expected,seal,request,destination,context,prepared);if(error)return error;
    expected.phase=N290_STORAGE_PREPARED;
    if(memcmp(storage,&expected,N291_HEADER_OFFSET))return -116;
    o=(struct n291_observation *)((n209_u8 *)w+N291_OBS_OFFSET);packet=(n209_u8 *)w+N291_WIRE_OFFSET;
    walk=(struct n291_walk *)((n209_u8 *)w+N291_WALK_OFFSET);
    error=n291_collect_locked(o,&w->snapshot,walk);if(error)return error;
    error=n291_classify(o,storage->base,storage->size);if(error)return error;
    error=n291_encode_inventory(o,storage->generation,packet,N291_PACKET_CAP,&inventory);if(error)return error;
    if(o->flags&N291_CHOSEN_READY){
        error=n291_encode_early(o,w->adt,sizeof(w->adt),&bytes);if(error)return error;
        error=n209_decode_payload(request->payload,sizeof(request->payload),&w->payload);if(error)return error;
        fields.virtual_base=w->payload.virtual_base;fields.physical_base=storage->base;fields.memory_size=storage->size;
        fields.memory_size_actual=o->union_size;fields.top_of_kernel=storage->base+storage->end_offset;
        fields.device_tree_pointer=w->payload.virtual_base+storage->adt_offset;fields.device_tree_length=bytes;
        error=n10_rt_serialize_boot_args(&fields,w->args,sizeof(w->args));if(error)return error;
        error=n10_rt_serialize_record(storage->base+storage->args_offset,storage->base+w->payload.kernel_entry_offset,w->record,sizeof(w->record));if(error)return error;
    }
    h->phase=N291_WRITING;h->flags=o->flags;h->inventory_bytes=inventory;h->adt_bytes=bytes;
    h->range_count=o->count;h->selected_affinity=o->selected;h->frequency=o->frequency;h->owner_generation=storage->generation;
#define WRITE_READ(off,src,len) do{if(N291_OWNER(opaque,destination)){error=-116;goto bad;} \
    error=n285_write_pages(opaque,off,src,len);if(error)goto bad; \
    if(N291_OWNER(opaque,destination)){error=-116;goto bad;} \
    error=n285_readback_pages(opaque,off,src,len,w->readback);if(error)goto bad;}while(0)
    WRITE_READ(storage->record_offset+N291_PACKET_OFFSET,packet,inventory);
    if(bytes){WRITE_READ(storage->adt_offset,w->adt,bytes);WRITE_READ(storage->args_offset,w->args,sizeof(w->args));WRITE_READ(storage->record_offset,w->record,sizeof(w->record));}
#undef WRITE_READ
    if(N291_OWNER(opaque,destination)){error=-116;goto bad;}
    N291_PUBLISH(h,bytes?N291_EARLY_DRAFT:N291_INCOMPLETE_DRAFT);return 0;
 bad:
    storage->phase=N290_QUARANTINED;h->flags&=~N291_CHOSEN_READY;h->adt_bytes=0;h->phase=N291_QUARANTINED;return error;
}
