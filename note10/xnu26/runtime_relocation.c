#include "runtime_relocation.h"

/* Volatile byte loops avoid implicit freestanding memcpy/memset dependencies. */
static void zero_bytes(void *destination, uint64_t size)
{
    volatile uint8_t *out=(volatile uint8_t *)destination;
    uint64_t i;
    for(i=0;i<size;i++) out[i]=0;
}
static void copy_bytes(void *destination, const void *source, uint64_t size)
{
    volatile uint8_t *out=(volatile uint8_t *)destination;
    const volatile uint8_t *in=(const volatile uint8_t *)source;
    uint64_t i;
    for(i=0;i<size;i++) out[i]=in[i];
}
static int add64(uint64_t a, uint64_t b, uint64_t *out)
{
    if(b>UINT64_MAX-a) return 0;
    *out=a+b;return 1;
}
static int overlap(uint64_t a,uint64_t as,uint64_t b,uint64_t bs)
{
    uint64_t ae,be;
    if(!add64(a,as,&ae)||!add64(b,bs,&be)) return 1;
    return as && bs && a<be && b<ae;
}
static int pointer_overlap(const void *a,uint64_t as,const void *b,uint64_t bs)
{
    if(!as || !bs)return 0;
    if(!a || !b)return 1;
    return overlap((uint64_t)(uintptr_t)a,as,(uint64_t)(uintptr_t)b,bs);
}
static int pointer_span(const void *p,uint64_t size)
{
    return p && size && size<=UINTPTR_MAX-(uintptr_t)p;
}
static int same(const uint8_t *a,const uint8_t *b,uint32_t n)
{
    uint32_t i;for(i=0;i<n;i++)if(a[i]!=b[i])return 0;return 1;
}
static uint32_t le32(const uint8_t *p)
{
    return (uint32_t)p[0]|((uint32_t)p[1]<<8)|((uint32_t)p[2]<<16)|((uint32_t)p[3]<<24);
}
static void put16(uint8_t *p,uint16_t value)
{
    p[0]=(uint8_t)value;p[1]=(uint8_t)(value>>8);
}
static void put32(uint8_t *p,uint32_t value)
{
    uint32_t i;for(i=0;i<4;i++)p[i]=(uint8_t)(value>>(8*i));
}
static void put64(uint8_t *p,uint64_t value)
{
    uint32_t i;for(i=0;i<8;i++)p[i]=(uint8_t)(value>>(8*i));
}
static int name_byte(uint8_t value)
{
    return value>=33 && value<=126 && value!='/';
}
static int gic_name(const uint8_t *p,uint32_t n)
{
    static const uint8_t forbidden[11]={'g','i','c','-','h','a','n','d','o','f','f'};
    return n==11 && same(p,forbidden,11);
}
struct adt_cursor {const uint8_t *raw;uint32_t size,at,nodes;};
struct adt_name {uint32_t at,size;};
static int take(struct adt_cursor *c,uint32_t count,uint32_t *start)
{
    if(c->at>c->size || count>c->size-c->at)return 0;
    *start=c->at;c->at+=count;return 1;
}
static int adt_node(struct adt_cursor *c,uint32_t depth,struct adt_name *node_name)
{
    uint32_t start,props,children,i,j,key_at,length,value_at,pad,name_seen=0;
    uint32_t keys[32];struct adt_name child_names[32];
    if(depth>8 || c->nodes>=32 || !take(c,8,&start))return 0;
    c->nodes++;props=le32(c->raw+start);children=le32(c->raw+start+4);
    if(!props || props>32 || children>32)return 0;
    for(i=0;i<props;i++) {
        uint32_t key_length=0;
        if(!take(c,36,&key_at))return 0;
        while(key_length<32 && c->raw[key_at+key_length]) {
            if(!name_byte(c->raw[key_at+key_length]))return 0;
            key_length++;
        }
        if(!key_length || key_length==32 || gic_name(c->raw+key_at,key_length))return 0;
        for(j=key_length;j<32;j++)if(c->raw[key_at+j])return 0;
        for(j=0;j<i;j++)if(same(c->raw+keys[j],c->raw+key_at,32))return 0;
        keys[i]=key_at;length=le32(c->raw+key_at+32);
        if(length>c->size || !take(c,length,&value_at))return 0;
        pad=(4-(length&3))&3;
        if(!take(c,pad,&start))return 0;
        for(j=0;j<pad;j++)if(c->raw[start+j])return 0;
        if(key_length==4 && same(c->raw+key_at,(const uint8_t *)"name",4)) {
            if(name_seen || length<2 || length>64 || c->raw[value_at+length-1])return 0;
            for(j=0;j+1<length;j++)if(!name_byte(c->raw[value_at+j]))return 0;
            if(gic_name(c->raw+value_at,length-1))return 0;
            node_name->at=value_at;node_name->size=length;name_seen=1;
        }
    }
    if(!name_seen)return 0;
    for(i=0;i<children;i++) {
        if(!adt_node(c,depth+1,&child_names[i]))return 0;
        for(j=0;j<i;j++)if(child_names[j].size==child_names[i].size &&
            same(c->raw+child_names[j].at,c->raw+child_names[i].at,child_names[i].size))return 0;
    }
    return 1;
}
int n10_rt_validate_adt(const uint8_t *raw,uint32_t size)
{
    struct adt_cursor cursor;struct adt_name name;
    if(!size || size>N10_RT_PAGE || !pointer_span(raw,size))return N10_RT_ADT;
    cursor.raw=raw;cursor.size=size;cursor.at=0;cursor.nodes=0;
    return adt_node(&cursor,0,&name) && cursor.at==size ? N10_RT_OK : N10_RT_ADT;
}
static int command_ok(const uint8_t *line,uint32_t count)
{
    uint32_t i;
    if(count>1023 || (count && !pointer_span(line,count)))return 0;
    for(i=0;i<count;i++)if(line[i]<32 || line[i]>126)return 0;
    return 1;
}
int n10_rt_plan(const struct n10_rt_request *in,struct n10_rt_plan *out)
{
    struct n10_rt_plan p;uint64_t end,virtual_end,offset,image_end,mapped_end;
    uint32_t group,i,j;struct n10_rt_range allocations[4];
    if(!pointer_span(in,sizeof(*in)) || !pointer_span(out,sizeof(*out)) || in->synthetic_adt!=N10_RT_SYNTHETIC_ADT ||
       in->reserved_count>N10_RT_MAX_RANGES || in->occupied_count>N10_RT_MAX_RANGES ||
       (in->reserved_count && !pointer_span(in->reserved,(uint64_t)in->reserved_count*sizeof(*in->reserved))) ||
       (in->occupied_count && !pointer_span(in->occupied,(uint64_t)in->occupied_count*sizeof(*in->occupied))) ||
       !command_ok(in->command_line,in->command_length))return N10_RT_INVALID;
    if(in->physical_base<N10_RT_MIN_BASE || in->physical_base%N10_RT_BLOCK || in->window_size!=N10_RT_WINDOW ||
       !add64(in->physical_base,in->window_size,&end) || end>N10_RT_LIMIT ||
       !in->image_size || in->image_size%N10_RT_PAGE || in->image_virtual%N10_RT_PAGE ||
       in->image_virtual<UINT64_C(0xffff000000000000) || in->entry_virtual%4 ||
       !add64(in->image_virtual,in->image_size,&image_end) ||
       in->entry_virtual<in->image_virtual || image_end-in->entry_virtual<4 || in->entry_virtual>=image_end)
        return N10_RT_RANGE;
    if(n10_rt_validate_adt(in->adt,in->adt_length))return N10_RT_ADT;
    zero_bytes(&p,sizeof(p));p.virtual_ram_base=in->image_virtual&~(N10_RT_BLOCK-1);
    if(!add64(p.virtual_ram_base,in->window_size,&virtual_end))return N10_RT_RANGE;
    offset=in->image_virtual-p.virtual_ram_base;
    if(offset>in->window_size || in->image_size>in->window_size-offset)return N10_RT_RANGE;
    p.physical_base=in->physical_base;p.window_size=in->window_size;
    p.image_virtual=in->image_virtual;p.image_size=in->image_size;p.entry_virtual=in->entry_virtual;
    if(!add64(in->physical_base,offset,&p.kernel_physical) ||
       !add64(in->physical_base,in->entry_virtual-p.virtual_ram_base,&p.entry_physical) ||
       !add64(p.kernel_physical,in->image_size,&p.kernel_end))return N10_RT_RANGE;
    p.arguments_physical=in->physical_base;p.device_tree_physical=in->physical_base+N10_RT_PAGE;
    p.adapter_physical=in->physical_base+2*N10_RT_PAGE;
    p.device_tree_virtual=p.virtual_ram_base+N10_RT_PAGE;p.adt_length=in->adt_length;
    p.mapping_blocks=(in->window_size-offset)/N10_RT_BLOCK;
    p.kernel_blocks=(p.kernel_end-in->physical_base+N10_RT_BLOCK-1)/N10_RT_BLOCK;
    mapped_end=in->physical_base+p.mapping_blocks*N10_RT_BLOCK;
    if(!p.mapping_blocks || p.kernel_end>mapped_end || p.kernel_end>end ||
       p.adapter_physical+N10_RT_PAGE>in->physical_base+N10_RT_BLOCK)return N10_RT_RANGE;
    allocations[0].start=p.kernel_physical;allocations[0].size=p.image_size;
    allocations[1].start=p.arguments_physical;allocations[1].size=N10_RT_PAGE;
    allocations[2].start=p.device_tree_physical;allocations[2].size=N10_RT_PAGE;
    allocations[3].start=p.adapter_physical;allocations[3].size=N10_RT_PAGE;
    for(i=0;i<4;i++)for(j=i+1;j<4;j++)if(overlap(allocations[i].start,allocations[i].size,allocations[j].start,allocations[j].size))return N10_RT_OVERLAP;
    for(group=0;group<2;group++) {
        const struct n10_rt_range *blocked=group?in->occupied:in->reserved;
        uint32_t count=group?in->occupied_count:in->reserved_count;
        for(i=0;i<count;i++) {
            uint64_t blocked_end;
            if(!blocked[i].size || !add64(blocked[i].start,blocked[i].size,&blocked_end) || blocked_end>N10_RT_LIMIT)return N10_RT_RANGE;
            for(j=0;j<4;j++)if(overlap(blocked[i].start,blocked[i].size,allocations[j].start,allocations[j].size))return N10_RT_OVERLAP;
        }
    }
    if(pointer_overlap(out,sizeof(*out),in,sizeof(*in)) ||
       pointer_overlap(out,sizeof(*out),in->adt,in->adt_length) ||
       pointer_overlap(out,sizeof(*out),in->command_line,in->command_length) ||
       pointer_overlap(out,sizeof(*out),in->reserved,(uint64_t)in->reserved_count*sizeof(*in->reserved)) ||
       pointer_overlap(out,sizeof(*out),in->occupied,(uint64_t)in->occupied_count*sizeof(*in->occupied)))return N10_RT_BUFFER;
    copy_bytes(out,&p,sizeof(p));return N10_RT_OK;
}
int n10_rt_serialize_boot_args(const struct n10_rt_boot_fields *f,uint8_t *out,uint64_t capacity)
{
    uint8_t bytes[N10_RT_ARGS_SIZE];uint64_t end,virtual_end,dt_end;uint32_t i;
    if(!pointer_span(f,sizeof(*f)) || capacity<N10_RT_ARGS_SIZE || !pointer_span(out,N10_RT_ARGS_SIZE))return N10_RT_BUFFER;
    if(!f->memory_size || f->physical_base%N10_RT_PAGE || f->virtual_base%N10_RT_PAGE ||
       f->memory_size%N10_RT_PAGE || f->top_of_kernel%N10_RT_PAGE ||
       (f->virtual_base-f->physical_base)%N10_RT_BLOCK ||
       !add64(f->physical_base,f->memory_size,&end) || end>N10_RT_LIMIT ||
       !add64(f->virtual_base,f->memory_size,&virtual_end) ||
       f->top_of_kernel<=f->physical_base || f->top_of_kernel>end ||
       !f->device_tree_pointer || !f->device_tree_length || f->device_tree_length>N10_RT_PAGE ||
       !add64(f->device_tree_pointer,f->device_tree_length,&dt_end) ||
       f->device_tree_pointer<f->virtual_base || dt_end>virtual_end ||
       f->memory_size_actual<f->memory_size || f->memory_size_actual>N10_RT_LIMIT-f->physical_base ||
       !command_ok(f->command_line,f->command_length) ||
       pointer_overlap(out,N10_RT_ARGS_SIZE,f,sizeof(*f)) ||
       pointer_overlap(out,N10_RT_ARGS_SIZE,f->command_line,f->command_length))return N10_RT_INVALID;
    zero_bytes(bytes,sizeof(bytes));put16(bytes,2);put16(bytes+2,2);
    put64(bytes+8,f->virtual_base);put64(bytes+16,f->physical_base);put64(bytes+24,f->memory_size);
    put64(bytes+32,f->top_of_kernel);
    for(i=0;i<6;i++)put64(bytes+40+8*i,f->video[i]);
    put32(bytes+88,f->machine_type);put64(bytes+96,f->device_tree_pointer);put32(bytes+104,f->device_tree_length);
    if(f->command_length)copy_bytes(bytes+108,f->command_line,f->command_length);
    put64(bytes+1136,f->boot_flags);put64(bytes+1144,f->memory_size_actual);
    copy_bytes(out,bytes,sizeof(bytes));return N10_RT_OK;
}
int n10_rt_serialize_record(uint64_t args,uint64_t entry,uint8_t *out,uint64_t capacity)
{
    uint8_t bytes[N10_RT_RECORD_SIZE];
    if(capacity<N10_RT_RECORD_SIZE || !pointer_span(out,N10_RT_RECORD_SIZE))return N10_RT_BUFFER;
    if(!args || !entry || args%N10_RT_PAGE || entry%4 || args>=N10_RT_LIMIT || entry>=N10_RT_LIMIT)return N10_RT_RANGE;
    zero_bytes(bytes,sizeof(bytes));copy_bytes(bytes,"N10XFER1",8);
    put32(bytes+8,1);put32(bytes+12,N10_RT_RECORD_SIZE);put64(bytes+16,args);put64(bytes+24,entry);
    copy_bytes(out,bytes,sizeof(bytes));return N10_RT_OK;
}
int n10_rt_build(const struct n10_rt_request *in,struct n10_rt_plan *out,
                 uint8_t *args,uint64_t args_capacity,uint8_t *record,uint64_t record_capacity)
{
    struct n10_rt_plan plan;struct n10_rt_boot_fields fields;
    uint8_t args_bytes[N10_RT_ARGS_SIZE],record_bytes[N10_RT_RECORD_SIZE];int result;
    uint32_t i,j;const void *dest[3];uint64_t sizes[3];
    if(!in || !pointer_span(out,sizeof(*out)) || !pointer_span(args,N10_RT_ARGS_SIZE) ||
       !pointer_span(record,N10_RT_RECORD_SIZE) || args_capacity<N10_RT_ARGS_SIZE || record_capacity<N10_RT_RECORD_SIZE)return N10_RT_BUFFER;
    result=n10_rt_plan(in,&plan);if(result)return result;
    dest[0]=out;sizes[0]=sizeof(*out);dest[1]=args;sizes[1]=N10_RT_ARGS_SIZE;dest[2]=record;sizes[2]=N10_RT_RECORD_SIZE;
    for(i=0;i<3;i++) {
        for(j=i+1;j<3;j++)if(pointer_overlap(dest[i],sizes[i],dest[j],sizes[j]))return N10_RT_BUFFER;
        if(pointer_overlap(dest[i],sizes[i],in,sizeof(*in)) || pointer_overlap(dest[i],sizes[i],in->adt,in->adt_length) ||
           pointer_overlap(dest[i],sizes[i],in->command_line,in->command_length) ||
           pointer_overlap(dest[i],sizes[i],in->reserved,(uint64_t)in->reserved_count*sizeof(*in->reserved)) ||
           pointer_overlap(dest[i],sizes[i],in->occupied,(uint64_t)in->occupied_count*sizeof(*in->occupied)))return N10_RT_BUFFER;
    }
    zero_bytes(&fields,sizeof(fields));fields.virtual_base=plan.virtual_ram_base;fields.physical_base=plan.physical_base;
    fields.memory_size=plan.window_size;fields.top_of_kernel=plan.kernel_end;
    fields.device_tree_pointer=plan.device_tree_virtual;fields.device_tree_length=(uint32_t)plan.adt_length;
    fields.command_line=in->command_line;fields.command_length=in->command_length;fields.memory_size_actual=plan.window_size;
    result=n10_rt_serialize_boot_args(&fields,args_bytes,sizeof(args_bytes));if(result)return result;
    result=n10_rt_serialize_record(plan.arguments_physical,plan.entry_physical,record_bytes,sizeof(record_bytes));if(result)return result;
    copy_bytes(out,&plan,sizeof(plan));copy_bytes(args,args_bytes,sizeof(args_bytes));copy_bytes(record,record_bytes,sizeof(record_bytes));
    return N10_RT_OK;
}
