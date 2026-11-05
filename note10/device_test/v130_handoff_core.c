/* SPDX-License-Identifier: GPL-2.0-only */
#ifdef __KERNEL__
#include <linux/v130_handoff_core.h>
#else
#include "v130_handoff_core.h"
#endif
static int same(const void *a,const void *b,unsigned long n)
{const n130_u8 *x=a,*y=b;unsigned long i;for(i=0;i<n;i++)if(x[i]!=y[i])return 0;return 1;}
static int nonzero(const n130_u8 *p,unsigned long n)
{unsigned long i;unsigned int value=0;for(i=0;i<n;i++)value|=p[i];return value!=0;}
static n130_u64 aligned(n130_u64 value){return (value+N130_PAGE-1)&~(N130_PAGE-1);}
int n130_reserve(const struct n130_reserve_ops *ops,void *context,n130_u64 *out)
{
    unsigned int i;n130_u64 low,high,base;int found;
    if(!ops || !ops->extent || !ops->available || !ops->reserve || !out)return -22;
    for(i=0;i<4096;i++){
        found=ops->extent(context,i,&low,&high);if(found<0)return found;if(!found)break;
        if(high>N130_LIMIT)high=N130_LIMIT;
        if(low<N130_MIN)low=N130_MIN;
        if(high<=low || high<N130_MEMORY+N130_RESIDUE)continue;
        base=((high-N130_MEMORY-N130_RESIDUE)&~(N130_MEMORY-1))+N130_RESIDUE;
        if(base<low || base>N130_LIMIT-N130_MEMORY || !ops->available(context,base,N130_MEMORY))continue;
        if(ops->reserve(context,base,N130_MEMORY))return -12;
        *out=base;return 0;
    }
    return -12;
}
int n130_descriptor(const struct n130_wire *w,const char *build)
{
    unsigned long i;
    if(!w || !build || !same(w->magic,"N10XNU2",8) || w->schema!=2 || w->bytes!=224 ||
       w->size!=N130_MEMORY || w->base<N130_MIN || w->base>N130_LIMIT-N130_MEMORY ||
       (w->base&(N130_MEMORY-1))!=N130_RESIDUE || w->page_shift!=12 || w->generation!=1 ||
       w->status!=1 || !same(w->build,build,32) || !nonzero(w->cookie,16))return -22;
    for(i=0;i<32;i++)if(!((build[i]>='0' && build[i]<='9') || (build[i]>='a' && build[i]<='f')))return -22;
    return 0;
}
int n130_layout(struct n130_wire *w,n130_u64 length)
{
    if(!w || !length || length>N130_ADT_MAX)return -22;
    w->kernel_span=N130_SPAN;w->kernel_entry_offset=N130_ENTRY;
    w->args_offset=N130_SPAN;w->adt_offset=N130_SPAN+N130_PAGE;w->adt_length=length;
    w->adapter_offset=aligned(w->adt_offset+length);w->adapter_bytes=N130_PAGE;
    w->top_offset=w->adapter_offset+N130_PAGE;
    return w->top_offset<=N130_MEMORY?0:-22;
}
int n130_parcel(const struct n130_wire *w,const char *build)
{
    struct n130_wire expected;
    if(n130_descriptor(w,build))return -22;
    expected=*w;
    if(n130_layout(&expected,w->adt_length) || !same(&expected,w,sizeof(*w)) ||
       !nonzero(w->activation_sha256,32) || !nonzero(w->kernel_sha256,32))return -22;
    return 0;
}
int n130_payload_valid(const struct n130_payload *p)
{
    return p && same(p->magic,"N10PAYL1",8) && p->schema==1 && p->bytes==128 && p->kernel_span==N130_SPAN &&
        p->kernel_entry==N130_ENTRY && p->pool_offset==13025280 && p->pool_bytes==163840 &&
        p->adapter_entry==0 && p->adapter_record%64==0 && p->adapter_record<=N130_PAGE-64 &&
        nonzero(p->kernel_sha256,32) && nonzero(p->adapter_sha256,32)?0:-22;
}
static void put(n130_u8 *p,n130_u64 value,unsigned int n)
{unsigned int i;for(i=0;i<n;i++)p[i]=(n130_u8)(value>>(8*i));}
int n130_boot_args(n130_u8 *out,unsigned long bytes,const struct n130_wire *w)
{
    unsigned long i;
    if(!out || bytes<1152 || !w || w->adt_length>0xffffffffULL || !w->adt_length || w->top_offset>N130_MEMORY ||
       (N130_VIRTUAL-w->base)%(N130_MEMORY) || w->base>N130_LIMIT-N130_MEMORY)return -22;
    for(i=0;i<1152;i++)out[i]=0;
    put(out,2,2);put(out+2,2,2);put(out+8,N130_VIRTUAL,8);put(out+16,w->base,8);
    put(out+24,N130_MEMORY,8);put(out+32,w->base+w->top_offset,8);
    put(out+96,N130_VIRTUAL+w->adt_offset,8);put(out+104,w->adt_length,4);
    /* Deliberately restricted first-entry size, not full-board RAM authority. */
    put(out+1144,N130_MEMORY,8);return 0;
}
static n130_u32 get32(const n130_u8 *p)
{return (n130_u32)p[0]|((n130_u32)p[1]<<8)|((n130_u32)p[2]<<16)|((n130_u32)p[3]<<24);}
static int key(const n130_u8 *p,const char *value)
{unsigned int i;for(i=0;i<32;i++){if(p[i]!=(n130_u8)value[i])return 0;if(!value[i])return 1;}return 0;}
static int adt_node(n130_u8 *tree,unsigned long bytes,unsigned long *at,unsigned int depth,
                    unsigned int *nodes,unsigned int *found,const struct n130_wire *w)
{
    n130_u32 properties,children,length;unsigned int i;int chosen=0;unsigned long value;
    if(depth>32 || ++*nodes>4096 || *at>bytes || bytes-*at<8)return -22;
    properties=get32(tree+*at);children=get32(tree+*at+4);*at+=8;
    if(!properties || properties>1024 || children>4096)return -22;
    for(i=0;i<properties;i++){
        if(*at>bytes || bytes-*at<36)return -22;
        length=get32(tree+*at+32);value=*at+36;
        if(length>bytes-value || length>N130_ADT_MAX || (length+3ULL)>bytes-value+3ULL)return -22;
        if(i==0){
            if(!key(tree+*at,"name") || !length || length>64 || tree[value+length-1])return -22;
            chosen=depth==1 && length==7 && same(tree+value,"chosen",7);
        }
        if(chosen && key(tree+*at,"dram-base")){
            if(length!=8 || (*found&1))return -22;
            put(tree+value,w->base,8);*found|=1;
        }
        if(chosen && key(tree+*at,"dram-size")){
            if(length!=8 || (*found&2))return -22;
            put(tree+value,N130_MEMORY,8);*found|=2;
        }
        *at=value+((length+3UL)&~3UL);
        if(*at>bytes)return -22;
    }
    for(i=0;i<children;i++)if(adt_node(tree,bytes,at,depth+1,nodes,found,w))return -22;
    return 0;
}
int n130_adt_owned_dram(n130_u8 *tree,unsigned long bytes,const struct n130_wire *w)
{
    unsigned long at=0;unsigned int nodes=0,found=0;
    if(!tree || !w || !bytes || bytes>N130_ADT_MAX || bytes!=w->adt_length)return -22;
    if(adt_node(tree,bytes,&at,0,&nodes,&found,w) || at!=bytes || found!=3)return -22;
    return 0;
}
long n130_load_once(const struct n130_wire *w,const char *build,const void *parcel,
                    const struct n130_loader_ops *ops,void *context)
{
    struct n130_segment s;long error;
    if(n130_parcel(w,build) || !parcel || !ops || !ops->arm || !ops->load || !ops->reboot || !ops->cancel)return -22;
    s.buf=parcel;s.bufsz=w->top_offset;s.mem=(const void *)(__UINTPTR_TYPE__)w->base;s.memsz=N130_MEMORY;
    error=ops->arm(context,w);if(error)return error;
    error=ops->load(context,w->base+w->adapter_offset,&s,N130_ARCH);
    if(error){ops->cancel(context,w);return error;}
    error=ops->reboot(context);ops->cancel(context,w);return error?error:-5;
}
