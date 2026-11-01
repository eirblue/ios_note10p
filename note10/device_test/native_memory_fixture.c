/* SPDX-License-Identifier: GPL-2.0-only */
/* Synthetic decoded tuples and API trace only; no actual kernel/FDT scanner. */
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdarg.h>
#include <string.h>
#define N10_MEMORY_HOST_TEST 1
#define __used __attribute__((used))
#define __init
#define BUILD_BUG_ON(expr) _Static_assert(!(expr), "permanent metadata budget")
typedef uint32_t u32;
typedef uint64_t u64;
#define N10_SHA256_KAT_ID "11111111111111111111111111111111"
static const char n10_cycle[]="22222222222222222222222222222222";
static int early=1;
static int scnprintf(char *out,size_t cap,const char *format,...)
{ int n;va_list args;assert(!early);va_start(args,format);n=vsnprintf(out,cap,format,args);va_end(args);assert(n>=0&&(size_t)n<cap);return n; }
static u32 n10_frame_checksum(const char *p,unsigned int n)
{ u32 v=2166136261U;while(n--)v=(v^(unsigned char)*p++)*16777619U;return v; }
#define pr_info(format,...) printf("N10BOOTLINK2 boot=33333333333333333333333333333333 " format,##__VA_ARGS__)
#include "native_memory_observation.c"
static char trace[1024];static unsigned int trace_len;
static unsigned int added,hotplugged,tuple_count=3;
static int use_usable,hot=1,exit_error;
static u64 tuples[20][2];
int dt_root_addr_cells=2,dt_root_size_cells=1;
static const void *initial_boot_params=(void *)1;
static void event(char value) { assert(trace_len+1<sizeof(trace));trace[trace_len++]=value;trace[trace_len]=0; }
static int fdt_next_node(const void *blob,int offset,int *depth)
{ (void)blob;event('N');if(offset<0){*depth=0;return 0;}if(exit_error){*depth=0;return exit_error;}*depth=-1;return 20; }
static const char *fdt_get_name(const void *blob,int offset,int *length)
{(void)blob;(void)offset;(void)length;event('G');return "synthetic";}
static const u64 *of_get_flat_dt_prop(unsigned long node,const char *name,int *length)
{
    (void)node;if(length)*length=(int)(tuple_count*16);
    if(!strcmp(name,"linux,usable-memory")){event('U');return use_usable?&tuples[0][0]:NULL;}
    if(!strcmp(name,"reg")){event('R');return &tuples[0][0];}
    assert(!strcmp(name,"hotpluggable"));event('H');return hot?(const u64 *)1:NULL;
}
static void early_init_dt_add_memory_arch(u64 base,u64 size)
{assert(size);(void)base;event('A');++added;}
static int early_init_dt_mark_hotplug_memory_arch(u64 base,u64 size)
{assert(size);(void)base;event('T');++hotplugged;return 0;}
int early_init_dt_scan_memory(unsigned long node,const char *uname,int depth,void *data);
#include "synthetic-native-seams.c"
static int other(unsigned long node,const char *name,int depth,void *data)
{(void)node;(void)name;(void)depth;(void)data;event('O');return 7;}
int main(int argc,char **argv)
{
    unsigned int i;int rc=0;
    assert(argc==2);tuples[0][0]=0x1003;tuples[0][1]=0x2007;
    tuples[1][0]=0x8000;tuples[1][1]=0;tuples[2][0]=0xf000;tuples[2][1]=0x1000;
    if(!strcmp(argv[1],"usable"))use_usable=1;
    if(!strcmp(argv[1],"no-hotplug"))hot=0;
    if(!strcmp(argv[1],"width"))dt_root_addr_cells=3;
    if(!strcmp(argv[1],"negative-exit"))exit_error=-9;
    if(!strcmp(argv[1],"no-blob"))initial_boot_params=NULL;
    if(!strcmp(argv[1],"overflow")){
        tuple_count=18;for(i=0;i<tuple_count;++i){tuples[i][0]=0x1000ULL*(i+1);tuples[i][1]=0x1000;}
    }
    if(!strcmp(argv[1],"no-end"))n10_memory_begin(1,1);
    else if(!strcmp(argv[1],"saturated")){
        n10_memory_begin(1,1);n10_memory.seen=~0U;n10_memory_row(1,1,1);n10_memory_end(0,20,-1,0);
    }else if(!strcmp(argv[1],"other"))rc=of_scan_flat_dt(other,NULL);
    else{
        rc=of_scan_flat_dt(early_init_dt_scan_memory,NULL);
        if(!strcmp(argv[1],"repeat"))rc=of_scan_flat_dt(early_init_dt_scan_memory,NULL);
    }
    early=0;n10_memory_emit();
    printf("{\"trace\":\"%s\",\"added\":%u,\"hotplugged\":%u,\"rc\":%d,\"state_bytes\":%zu}\n",
           trace,added,hotplugged,rc,sizeof(n10_memory));
    return 0;
}
