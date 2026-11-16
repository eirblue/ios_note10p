/* SPDX-License-Identifier: GPL-2.0-only */
#include "v285_current_cpu_metadata.h"
#ifdef __KERNEL__
#include <linux/of.h>
#include <linux/spinlock.h>
#if !defined(CONFIG_OF) || defined(CONFIG_OF_DYNAMIC) || defined(CONFIG_OF_OVERLAY)
#error "285 requires the pinned static OF configuration"
#endif
typedef struct device_node n285_node;
typedef struct property n285_property;
#define N285_ROOT of_root
#define N285_LOCK(f) raw_spin_lock_irqsave(&devtree_lock,f)
#define N285_UNLOCK(f) raw_spin_unlock_irqrestore(&devtree_lock,f)
#define N285_WRITE n217_write_destination
#define N285_READ n217_read_destination
#elif defined(N285_HOST_FIXTURE)
struct n285_test_property { const char *name;int length;const void *value;struct n285_test_property *next; };
struct n285_test_node { const char *name;struct n285_test_property *properties;struct n285_test_node *child,*sibling; };
typedef struct n285_test_node n285_node;
typedef struct n285_test_property n285_property;
extern n285_node *n285_fixture_root;
extern void n285_fixture_lock(unsigned long *);
extern void n285_fixture_unlock(unsigned long);
#define N285_ROOT n285_fixture_root
#define N285_LOCK(f) n285_fixture_lock(&(f))
#define N285_UNLOCK(f) n285_fixture_unlock(f)
extern int n285_fixture_write(void *,n209_u64,const void *,unsigned int);
extern int n285_fixture_read(void *,n209_u64,void *,unsigned int);
#define N285_WRITE n285_fixture_write
#define N285_READ n285_fixture_read
#else
#error "285 snapshot requires kernel or explicit host fixture"
#endif
/* Fixed direct owner adapters, not a new callback or indirect-call capability. */
int n285_write_pages(void *opaque,n209_u64 offset,const void *source,n209_u32 bytes)
{
    const n209_u8 *raw=source;n209_u32 count;int error;
    while(bytes){count=4096U-(n209_u32)(offset%4096U);if(count>bytes)count=bytes;
        error=N285_WRITE(opaque,offset,raw,count);if(error)return error;
        offset+=count;raw+=count;bytes-=count;}
    return 0;
}
int n285_readback_pages(void *opaque,n209_u64 offset,const void *source,n209_u32 bytes,n209_u8 *page)
{
    const n209_u8 *raw=source;n209_u32 count;int error;
    while(bytes){count=4096U-(n209_u32)(offset%4096U);if(count>bytes)count=bytes;
        error=N285_READ(opaque,offset,page,count);if(error)return error;
        if(memcmp(page,raw,count))return -5;
        offset+=count;raw+=count;bytes-=count;}
    return 0;
}
static const n285_property *n285_find_property_locked(const n285_node *node,const char *name,int *bad)
{
    const n285_property *p,*found=0;unsigned int count=0,i;
    for(p=node->properties;p;p=p->next){
        if(++count>128||!p->name){*bad=1;return 0;}
        for(i=0;i<32;i++)if(p->name[i]!=name[i]||!name[i])break;
        if(i<32&&p->name[i]==name[i]){if(found){*bad=1;return 0;}found=p;}
    }
    return found;
}
static int n285_snapshot_of_locked(struct n285_cpu_snapshot *out,const struct n231_cpu_observation *s,
    const struct n233_cpu_node_consistency *n,const struct n240_query_receipt *q)
{
    n285_node *root,*cpus=0,*node;const n285_property *p;const n209_u8 *raw;
    unsigned long flags=0;unsigned int count=0,i,cells=0;int bad=0,error=-22;n209_u64 reg;
    if(!out||!s||!n||!q)return -22;
    out->count=0;
    if(s->status!=1||s->reserved||s->linux_cpu>=8||s->current_el!=4||!s->cntfrq_el0||s->cntfrq_el0>0xffffffffULL||
       n->status!=1||n->linux_cpu!=s->linux_cpu||n->logical_mpidr!=n->firmware_reg||
       (s->mpidr_el1&0xff00ffffffULL)!=n->firmware_reg||n->firmware_reg>0xffffffffULL||
       (n->address_cells!=1&&n->address_cells!=2)||n->reg_bytes!=4*n->address_cells||
       q->schema!=1||q->status!=1||q->error_code||q->cpu_enter!=s->linux_cpu||
       q->cpu_sample!=s->linux_cpu||q->cpu_before_release!=s->linux_cpu||q->pc_before||
       q->pc_after_capture!=1||q->pc_after_query!=1||q->pc_after_release)return -22;
    N285_LOCK(flags);
    root=N285_ROOT;if(!root)goto done;
    for(node=root->child;node;node=node->sibling){
        if(++count>256)goto done;
        if(node->name&&node->name[0]=='c'&&node->name[1]=='p'&&node->name[2]=='u'&&node->name[3]=='s'&&!node->name[4]){
            if(cpus)goto done;cpus=node;
        }
    }
    if(!cpus)goto done;
    p=n285_find_property_locked(cpus,"#address-cells",&bad);
    if(bad||!p||p->length!=4||!p->value)goto done;
    raw=p->value;for(i=0;i<4;i++)cells=(cells<<8)|raw[i];
    if(cells!=1&&cells!=2)goto done;
    p=n285_find_property_locked(cpus,"#size-cells",&bad);
    if(bad||!p||p->length!=4||!p->value)goto done;
    raw=p->value;if(raw[0]||raw[1]||raw[2]||raw[3])goto done;
    count=0;
    for(node=cpus->child;node;node=node->sibling){
        if(++count>64)goto done;
        p=n285_find_property_locked(node,"device_type",&bad);if(bad)goto done;
        if(!p||p->length!=4||!p->value)continue;
        raw=p->value;if(raw[0]!='c'||raw[1]!='p'||raw[2]!='u'||raw[3])continue;
        p=n285_find_property_locked(node,"reg",&bad);
        if(bad||!p||p->length!=(int)(4*cells)||!p->value||out->count>=N285_MAX_CPUS)goto done;
        raw=p->value;reg=0;for(i=0;i<4*cells;i++)reg=(reg<<8)|raw[i];
        if(reg>0xffffffffULL)goto done;
        out->affinity[out->count++]=(n209_u32)reg;
    }
    if(!out->count)goto done;
    out->selected=(n209_u32)n->firmware_reg;out->frequency=(n209_u32)s->cntfrq_el0;out->reserved=0;error=0;
done:
    N285_UNLOCK(flags);
    if(error)out->count=0;
    return error;
}
