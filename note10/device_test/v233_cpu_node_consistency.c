/* SPDX-License-Identifier: GPL-2.0-only */
#include "v233_cpu_node_consistency.h"
#ifdef __KERNEL__
#include <linux/of.h>
#include <linux/string.h>
#include <asm/cputype.h>
#include <asm/smp_plat.h>
#if !defined(CONFIG_OF) || defined(CONFIG_OF_DYNAMIC) || defined(CONFIG_OF_OVERLAY)
#error "233 requires the reviewed static OF tree; never change config to force this"
#endif
#if !defined(CONFIG_SMP) || CONFIG_NR_CPUS != 8
#error "233 requires the reviewed eight-CPU mapping"
#endif
typedef struct device_node n233_node;
#define N233_LOGICAL(c) cpu_logical_map(c)
#define N233_NODE(c,t) of_get_cpu_node(c,t)
#define N233_PARENT(n) of_get_parent(n)
#define N233_NAME(n) of_node_full_name(n)
#define N233_PROPERTY(n,k,l) of_get_property(n,k,l)
#define N233_NUMBER(p,c) of_read_number((const __be32 *)(p),c)
#define N233_PUT(n) of_node_put(n)
#define N233_MASK MPIDR_HWID_BITMASK
#elif defined(N233_HOST_FIXTURE)
#include <string.h>
typedef struct n233_fixture_node n233_node;
#define N233_LOGICAL(c) n233_fixture_logical_map(c)
#define N233_NODE(c,t) n233_fixture_get_cpu_node(c,t)
#define N233_PARENT(n) n233_fixture_get_parent(n)
#define N233_NAME(n) n233_fixture_full_name(n)
#define N233_PROPERTY(n,k,l) n233_fixture_property(n,k,l)
#define N233_NUMBER(p,c) n233_fixture_read_number(p,c)
#define N233_PUT(n) n233_fixture_put(n)
#define N233_MASK 0xff00ffffffULL
#else
#error "233 requires kernel OF APIs or its explicit host IO shim"
#endif

static __attribute__((__noinline__)) void n233_clear_consistency(struct n233_cpu_node_consistency *out)
{
    volatile n209_u8 *raw=(volatile n209_u8 *)out;unsigned int i;
    for(i=0;i<sizeof(*out);i++)raw[i]=0;
}
__attribute__((__noinline__,__used__)) int n233_capture_cpu_node_consistency(
    const struct n231_cpu_observation *sample,struct n233_cpu_node_consistency *out)
{
    n233_node *node=0,*parent=0;const void *property;
    n209_u64 logical=0,reg=0,cells=0,size_cells;unsigned int cpu=0,thread=~0U;int length=0,error=-22;
    if(!out)return -22;
    n233_clear_consistency(out);
    if(!sample||sample->status!=1||sample->reserved||sample->linux_cpu>=8||sample->current_el!=4||
       !sample->cntfrq_el0||sample->cntfrq_el0>0xffffffffULL)return -22;
    cpu=sample->linux_cpu;logical=N233_LOGICAL(cpu);
    if((logical&~N233_MASK)||(sample->mpidr_el1&N233_MASK)!=logical)return -22;
    node=N233_NODE(cpu,&thread);if(!node||thread)goto done;
    parent=N233_PARENT(node);if(!parent||strcmp(N233_NAME(parent),"/cpus"))goto done;
    property=N233_PROPERTY(parent,"#address-cells",&length);if(!property||length!=4)goto done;
    cells=N233_NUMBER(property,1);if(cells!=1&&cells!=2)goto done;
    property=N233_PROPERTY(parent,"#size-cells",&length);if(!property||length!=4)goto done;
    size_cells=N233_NUMBER(property,1);if(size_cells)goto done;
    property=N233_PROPERTY(node,"reg",&length);if(!property||length!=(int)(4*cells))goto done;
    reg=N233_NUMBER(property,(unsigned int)cells);
    if(reg!=logical||reg>0xffffffffULL)goto done;
    error=0;
done:
    if(parent)N233_PUT(parent);
    if(node)N233_PUT(node);
    if(error)return error;
    /* Only scalars are published, after every OF reference has been released. */
    out->logical_mpidr=logical;out->firmware_reg=reg;out->linux_cpu=cpu;
    out->address_cells=(n209_u32)cells;out->reg_bytes=(n209_u32)length;out->status=1;return 0;
}

#ifdef __KERNEL__
/* Compile-only alias: no caller, allocation, destination write or log hook. */
_Static_assert(N233_POOL_OFFSET==N231_POOL_OFFSET+sizeof(struct n231_cpu_observation),"after231");
_Static_assert(N233_POOL_OFFSET%8==0&&N233_POOL_OFFSET+sizeof(struct n233_cpu_node_consistency)<=N226_STAGE_OFFSET,"disjoint existing gap");
__asm__(".globl n233_node_storage\n.set n233_node_storage,n226_source_pool+43576\n"
        ".type n233_node_storage,%object\n.size n233_node_storage,32\n");
static __used __attribute__((__noinline__)) void n233_layout_witness(void)
{
    asm volatile(".globl n233_size_node\n.equ n233_size_node,%c0\n"
                 ".globl n233_align_node\n.equ n233_align_node,%c1\n"
                 ".globl n233_status_offset\n.equ n233_status_offset,%c2\n"
                 : : "i"(sizeof(struct n233_cpu_node_consistency)),"i"(__alignof__(struct n233_cpu_node_consistency)),
                     "i"(offsetof(struct n233_cpu_node_consistency,status)));
}
#endif
