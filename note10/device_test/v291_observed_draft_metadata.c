/* SPDX-License-Identifier: GPL-2.0-only */
#include "v291_observed_draft_metadata.h"
#ifdef __KERNEL__
#include <linux/string.h>
#else
#include <string.h>
#endif
static void n291_put(n209_u8 *out,n209_u64 value,n209_u32 bytes)
{ n209_u32 i;for(i=0;i<bytes;i++)out[i]=(n209_u8)(value>>(8U*i)); }
int n291_classify(struct n291_observation *o,n209_u64 owner_base,n209_u64 owner_bytes)
{
    struct n291_range item;n209_u64 end,chain;n209_u32 i,j,covered=0;
    if(!o||!o->count||o->count>N291_MAX_RANGES||o->frequency<1000000U||o->frequency>0x7fffffffU||
       !owner_bytes||owner_base>~(n209_u64)0-owner_bytes)return -22;
    o->flags&=~N291_CHOSEN_READY;o->union_base=o->union_size=0;
    for(i=0;i<o->count;i++){
        if(!o->ranges[i].size||o->ranges[i].base>~(n209_u64)0-o->ranges[i].size)return -22;
        item=o->ranges[i];j=i;while(j&&o->ranges[j-1].base>item.base){o->ranges[j]=o->ranges[j-1];j--;}o->ranges[j]=item;
    }
    chain=o->ranges[0].base;end=chain+o->ranges[0].size;
    for(i=1;i<o->count;i++){
        if(o->ranges[i].base<end)return -22; /* overlap/duplicate is hard-invalid */
        if(o->ranges[i].base!=end){
            if(owner_base>=chain&&owner_base+owner_bytes<=end)covered=1;
            o->flags|=N291_NONCONTIGUOUS;chain=o->ranges[i].base;
        }
        end=o->ranges[i].base+o->ranges[i].size;
    }
    if(owner_base>=chain&&owner_base+owner_bytes<=end)covered=1;
    if(!covered)o->flags|=N291_OWNER_OUTSIDE;
    if(!(o->flags&N291_INCOMPLETE_FLAGS)){
        o->union_base=o->ranges[0].base;o->union_size=end-o->union_base;o->flags|=N291_CHOSEN_READY;
    }
    return 0;
}
static int n291_property(n209_u8 *out,n209_u32 *at,const char *name,const n209_u8 *value,n209_u32 bytes)
{
    n209_u32 n=0,padded=(bytes+3U)&~3U;while(n<32&&name[n])n++;
    if(n==32||*at>16384||36U+padded>16384U-*at)return -22;
    memset(out+*at,0,36U+padded);memcpy(out+*at,name,n);n291_put(out+*at+32,bytes,4);
    memcpy(out+*at+36,value,bytes);*at+=36U+padded;return 0;
}
int n291_encode_early(const struct n291_observation *o,n209_u8 *out,n209_u32 capacity,n209_u32 *bytes)
{
    n209_u32 at=8,n=4,shift;char name[13];n209_u8 reg[4],freq[4],dram[16];int error;
    if(!o||!out||!bytes||capacity<16384||!(o->flags&N291_CHOSEN_READY)||(o->flags&N291_INCOMPLETE_FLAGS)||
       o->frequency<1000000||o->frequency>0x7fffffff||!o->union_size||o->union_base>~(n209_u64)0-o->union_size)return -22;
    memset(out,0,16384);n291_put(out,1,4);n291_put(out+4,2,4);
#define P(k,v,z) do{error=n291_property(out,&at,k,(const n209_u8 *)(v),z);if(error)return error;}while(0)
    P("name","device-tree",12);n291_put(out+at,1,4);n291_put(out+at+4,1,4);at+=8;P("name","cpus",5);
    n291_put(out+at,5,4);at+=8;memcpy(name,"cpu@",4);
    for(shift=28;shift&&!(o->selected>>shift);shift-=4){}
    do{name[n++]="0123456789abcdef"[(o->selected>>shift)&15];if(!shift)break;shift-=4;}while(1);name[n++]=0;
    n291_put(reg,o->selected,4);n291_put(freq,o->frequency,4);
    P("name",name,n);P("device_type","cpu",4);P("reg",reg,4);P("state","running",8);P("timebase-frequency",freq,4);
    n291_put(out+at,3,4);at+=8;P("name","chosen",7);n291_put(dram,o->union_base,8);n291_put(dram+8,o->union_size,8);
    P("dram-base",dram,8);P("dram-size",dram+8,8);
#undef P
    *bytes=at;return 0;
}
int n291_encode_inventory(const struct n291_observation *o,n209_u64 generation,n209_u8 *out,n209_u32 capacity,n209_u32 *bytes)
{
    n209_u32 i,size;if(!o||!out||!bytes||!o->count||o->count>N291_MAX_RANGES)return -22;
    size=80+24*o->count;if(size>capacity)return -22;memset(out,0,size);memcpy(out,"N291OBS1",8);
    n291_put(out+8,1,4);n291_put(out+12,size,4);n291_put(out+16,o->flags,4);n291_put(out+20,o->count,4);
    n291_put(out+24,o->selected,4);n291_put(out+28,o->frequency,4);n291_put(out+32,generation,8);
    n291_put(out+40,o->address_cells,4);n291_put(out+44,o->size_cells,4);n291_put(out+48,o->scanned_nodes,4);n291_put(out+52,o->unsupported,4);
    n291_put(out+56,o->union_base,8);n291_put(out+64,o->union_size,8);
    for(i=0;i<o->count;i++){n209_u8 *p=out+80+24*i;n291_put(p,o->ranges[i].base,8);n291_put(p+8,o->ranges[i].size,8);n291_put(p+16,o->ranges[i].node_ordinal,4);n291_put(p+20,o->ranges[i].tuple_ordinal,4);}
    *bytes=size;return 0;
}
#ifdef __KERNEL__
static __used __attribute__((__noinline__)) void n291_layout_witness(void)
{
    asm volatile(".globl n291_size_header\n.equ n291_size_header,%c0\n"
                 ".globl n291_size_observation\n.equ n291_size_observation,%c1\n"
                 ".globl n291_header_pool_offset\n.equ n291_header_pool_offset,%c2\n"
                 ".globl n291_packet_offset\n.equ n291_packet_offset,%c3\n"
                 : : "i"(sizeof(struct n291_header)),"i"(sizeof(struct n291_observation)),
                     "i"(N290_STORAGE_OFFSET+N291_HEADER_OFFSET),"i"(N291_PACKET_OFFSET));
}
#endif
