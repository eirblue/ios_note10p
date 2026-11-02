/* SPDX-License-Identifier: GPL-2.0-only */
/* New fixed-capacity path only; portable decoder deliberately controlled, never executed. */
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h>
#include <openssl/sha.h>
#include "carrier_lzma.h"
#include "current_owned_capacity.h"
#define N10_DATA_HOST_TEST
#define N10_DATA_IMAGE_EXPECTATION 1
#define N10_DATA_CONTIGUOUS 1
#define __init
#define __used __attribute__((used))
#define READ_ONCE(x) (*(volatile __typeof__(x) *)&(x))
static unsigned long initrd_start,initrd_end,first,last;
static unsigned char *arena,*owned;
static unsigned int allocations,frees,core_calls,hashes,cleared=1,reserves,early;
static unsigned int fail_workspace,fail_core,fail_payload;
#define n10_data_linear(x) ((x)>=first && (x)<last)
#define n10_data_pa(x) ((uint64_t)(x))
#define n10_data_va(x) ((unsigned long)(x))
#define n10_data_clear(p,n) memset((p),0,(n))
static void *workspace;
static void *allocate(size_t n) { allocations++;if(fail_workspace)return NULL;workspace=malloc(n);return workspace; }
static void release(void *p) { unsigned char *b=p;for(unsigned int i=0;i<N10_LZMA_WORKSPACE;i++)if(b[i])cleared=0;frees++;free(p); }
#define n10_data_alloc(n) allocate(n)
#define n10_data_free(p) release(p)
static int n10_data_hash(const void *p,size_t n,unsigned char out[32])
{ hashes++;if(fail_payload && hashes==3)return -5;return SHA256(p,n,out)?0:-1; }
static uint64_t reserve(size_t n,size_t a)
{ reserves++;if(n!=N10_OWNED_BYTES || a!=16384u)abort();return (uint64_t)(uintptr_t)owned; }
#define n10_owned_reserve(n,a) reserve(n,a)
#define n10_owned_va(p) ((unsigned long)(p))
#define n10_owned_pa(p) ((uint64_t)(p))
#define n10_owned_linear(p) ((p)>=(unsigned long)owned && (p)<(unsigned long)owned+N10_OWNED_BYTES)
#include "owned_contiguous_staging.c"
int n10_lzma_alone_decode(const uint8_t *input,size_t bytes,uint8_t *output,size_t capacity,
    void *work,size_t workbytes,struct n10_lzma_result *r)
{
    (void)input;core_calls++;
    if(output!=owned || capacity!=N10_OWNED_BYTES || work!=workspace || workbytes!=N10_LZMA_WORKSPACE)abort();
    memset(output,0,capacity);r->version=1;r->consumed=bytes;r->written=capacity;
    r->status=fail_core?-6:0;return r->status;
}
#include "linux_data_carrier.c"
int main(int argc,char **argv)
{
    if(argc!=3)return 2;
    FILE *f=fopen(argv[1],"rb");if(!f)return 2;
    if(fseek(f,0,SEEK_END))return 2;long n=ftell(f);
    if(n<=128 || n>1024*1024 || fseek(f,0,SEEK_SET))return 2;
    unsigned char *data=malloc((size_t)n);if(!data || fread(data,1,(size_t)n,f)!=(size_t)n)return 2;fclose(f);
    arena=aligned_alloc(16384u,N10_OWNED_BYTES+32768u);if(!arena)return 2;owned=arena+16384u;
    memset(arena,0xa7,N10_OWNED_BYTES+32768u);n10_owned_capture();
    early=1;for(size_t i=0;i<N10_OWNED_BYTES+32768u;i++)if(arena[i]!=0xa7)early=0;
    if(hashes || allocations || core_calls)abort();
    if(!strcmp(argv[2],"capacity_changed"))n10_owned.capacity--;
    fail_workspace=!strcmp(argv[2],"workspace_fail");fail_core=!strcmp(argv[2],"core_fail");fail_payload=!strcmp(argv[2],"payload_hash_fail");
    initrd_start=first=(unsigned long)data;initrd_end=last=first+(unsigned long)n;n10_data_capture(first,last);
    struct n10_data_outcome outcome;n10_data_run(&outcome);
    unsigned int guards=1,zero=1;
    for(size_t i=0;i<16384u;i++)if(arena[i]!=0xa7 || owned[N10_OWNED_BYTES+i]!=0xa7)guards=0;
    for(size_t i=0;i<N10_OWNED_BYTES;i++)if(owned[i])zero=0;
    printf("{\"status\":\"%s\",\"capacity\":%u,\"reserved\":%u,\"early\":%u,\"calls\":%u,\"written\":%llu,\"allocations\":%u,\"frees\":%u,\"workspace_cleared\":%u,\"output_cleared\":%u,\"guards\":%u,\"state_bytes\":%zu}\n",
        outcome.status,n10_owned.capacity,reserves,early,core_calls,(unsigned long long)outcome.written,allocations,frees,cleared,zero,guards,sizeof(n10_owned)+sizeof(n10_data));
    free(arena);free(data);return guards?0:1;
}
