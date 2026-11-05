/* SPDX-License-Identifier: GPL-2.0-only */
#include <assert.h>
#include <stdio.h>
#include <string.h>
#include "v130_handoff_core.h"
#include "v130_gate_core.h"
static const char build[]="0123456789abcdef0123456789abcdef";
static int trace[8],n,fail,loads,reboots,cancels;
static int extent(void *c,unsigned int i,n130_u64 *l,n130_u64 *h)
{(void)c;if(i)return 0;*l=0x80000000;*h=0xe0000000;return 1;}
static int available(void *c,n130_u64 b,n130_u64 s){(void)c;return b>=0x80000000 && b+s<=0xe0000000;}
static int reserve(void *c,n130_u64 b,n130_u64 s){(void)c;(void)b;(void)s;return fail==5?-1:0;}
static long arm(void *c,const struct n130_wire *w){(void)c;(void)w;trace[n++]=1;return fail==1?-1:0;}
static long load(void *c,n130_u64 e,const struct n130_segment *s,n130_u64 f)
{const struct n130_wire *w=c;trace[n++]=2;loads++;assert(e==w->base+w->adapter_offset && s->bufsz==w->top_offset && s->memsz==N130_MEMORY && f==N130_ARCH);return fail==2?-2:0;}
static long reboot(void *c){(void)c;trace[n++]=3;reboots++;return fail==3?-3:0;}
static void cancel(void *c,const struct n130_wire *w){(void)c;(void)w;trace[n++]=4;cancels++;}
static n130_u64 get64(const unsigned char *b){n130_u64 r=0;int i;for(i=0;i<8;i++)r|=(n130_u64)b[i]<<(8*i);return r;}
int main(int argc,char **argv)
{
    const struct n130_reserve_ops r={extent,available,reserve};const struct n130_loader_ops ops={arm,load,reboot,cancel};
    struct n130_wire w={0},bad;unsigned char args[16384],tree[2048];n130_u64 base=0;int i;size_t bytes;FILE *stream;
    assert(argc==3);stream=fopen(argv[1],"rb");assert(stream);bytes=fread(tree,1,sizeof(tree),stream);assert(bytes && !ferror(stream) && feof(stream));fclose(stream);
    assert(!n130_reserve(&r,NULL,&base));assert((base&(N130_MEMORY-1))==N130_RESIDUE);
    fail=5;assert(n130_reserve(&r,NULL,&base)<0);fail=0;
    memcpy(w.magic,"N10XNU2",8);w.schema=2;w.bytes=224;w.base=base;w.size=N130_MEMORY;
    memset(w.cookie,1,16);memcpy(w.build,build,32);w.generation=1;w.status=1;w.page_shift=12;
    assert(!n130_descriptor(&w,build));assert(!n130_layout(&w,bytes));memset(w.kernel_sha256,2,32);memset(w.activation_sha256,3,32);
    assert(!n130_adt_owned_dram(tree,(unsigned long)bytes,&w));
    stream=fopen(argv[2],"wb");assert(stream && fwrite(tree,1,bytes,stream)==bytes);fclose(stream);
    assert(n130_adt_owned_dram(tree,(unsigned long)bytes-1,&w)<0);
    assert(!n130_parcel(&w,build));assert(w.args_offset==N130_SPAN && w.adt_offset==N130_SPAN+N130_PAGE);
    assert(!n130_boot_args(args,sizeof(args),&w));assert(get64(args+24)==N130_MEMORY && get64(args+1144)==N130_MEMORY);
    assert(get64(args+16)==base && get64(args+96)==N130_VIRTUAL+w.adt_offset && get64(args+32)==base+w.top_offset);
    bad=w;bad.base+=N130_PAGE;assert(n130_descriptor(&bad,build)<0);bad=w;bad.adapter_offset=0;assert(n130_parcel(&bad,build)<0);
    bad=w;bad.top_offset=N130_MEMORY+N130_PAGE;assert(n130_parcel(&bad,build)<0);bad=w;bad.kernel_entry_offset++;assert(n130_parcel(&bad,build)<0);
    for(i=0;i<4;i++){fail=i;n=loads=reboots=cancels=0;assert(n130_load_once(&w,build,args,&ops,&w)<0);assert(trace[0]==1);assert(loads==(i!=1));assert(reboots==(i!=1 && i!=2));assert(cancels==(i!=1));}
    assert(n130_usb_halted(0,1u<<22,2u<<12,1u<<31,1u<<31,1u<<22,3u<<12,2u<<12,1u<<31,0));
    assert(!n130_usb_halted(1u<<31,1u<<22,2u<<12,1u<<31,1u<<31,1u<<22,3u<<12,2u<<12,1u<<31,0));
    assert(!n130_usb_halted(0,0,2u<<12,1u<<31,1u<<31,1u<<22,3u<<12,2u<<12,1u<<31,0));
    assert(!n130_usb_halted(0,1u<<22,3u<<12,1u<<31,1u<<31,1u<<22,3u<<12,2u<<12,1u<<31,0));
    assert(!n130_usb_halted(0,1u<<22,2u<<12,1u<<31,1u<<31,1u<<22,3u<<12,2u<<12,1u<<31,1));
    puts("v130 new owned-congruence/full-parcel/order/errors/driver-readback PASS");return 0;
}
