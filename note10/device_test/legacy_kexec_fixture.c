/* SPDX-License-Identifier: GPL-2.0-only */
/* One hosted NEW production-core process; syscalls/PMU/reservation are controlled. */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "legacy_kexec_core.c"
static unsigned int checks;
#define CHECK(x) do { ++checks; if(!(x)){fprintf(stderr,"new check failed line %d\n",__LINE__);exit(1);} } while(0)
static const char build_id[]="0123456789abcdef0123456789abcdef";
static unsigned char park[16384];
struct context { int mode,events,loads,reboots,cancels,steps;char order[32];n10_u32 regs[2];n10_u64 chosen; };
static void event(struct context *c,char v){CHECK(c->events<31);c->order[c->events++]=v;c->order[c->events]=0;}
static n10_u64 find_range(void *p,n10_u64 lo,n10_u64 hi,n10_u64 size,n10_u64 align)
{struct context *c=p;CHECK(lo==N10_KEXEC_MIN && hi==N10_KEXEC_LIMIT && size==N10_KEXEC_BYTES && align==16384);return c->chosen;}
static int is_memory(void *p,n10_u64 base,n10_u64 size)
{struct context *c=p;CHECK(base==c->chosen && size==N10_KEXEC_BYTES);return c->mode!=1;}
static int is_reserved(void *p,n10_u64 base,n10_u64 size)
{struct context *c=p;CHECK(base==c->chosen && size==N10_KEXEC_BYTES);return c->mode==2;}
static int reserve_range(void *p,n10_u64 base,n10_u64 size)
{struct context *c=p;CHECK(base==c->chosen && size==N10_KEXEC_BYTES);++c->steps;return c->mode==3?-12:0;}
static const struct n10_reserve_ops reserve_ops={find_range,is_memory,is_reserved,reserve_range};
static struct n10_destination destination(void)
{
    struct n10_destination d;memset(&d,0,sizeof(d));memcpy(d.magic,"N10KRES1",8);d.schema=1;d.bytes=128;
    d.base=0x84000000;d.size=N10_KEXEC_BYTES;memcpy(d.build,build_id,32);d.cookie[0]=7;
    d.page_shift=12;d.reserved_pages=d.valid_pages=8192;d.status=1;d.generation=1;return d;
}
static long arm(void *p,const struct n10_destination *d)
{struct context *c=p;CHECK(!n10_destination_valid(d,build_id));event(c,'A');return c->mode==1?-1:0;}
static long load(void *p,n10_u64 entry,n10_u64 count,const struct n10_kexec_segment *s,n10_u64 flags)
{
    struct context *c=p;event(c,'L');++c->loads;
    CHECK(entry==0x84000000 && count==1 && flags==N10_KEXEC_ARCH &&
          s->buf==park && s->bufsz==sizeof(park) && (n10_u64)(__UINTPTR_TYPE__)s->mem==entry && s->memsz==N10_KEXEC_BYTES);
    return c->mode==2?-12:0;
}
static long reboot_call(void *p){struct context *c=p;event(c,'R');++c->reboots;return c->mode==3?-5:0;}
static void cancel(void *p,const struct n10_destination *d)
{struct context *c=p;CHECK(d->status==1);event(c,'C');++c->cancels;}
static const struct n10_loader_ops loader_ops={arm,load,reboot_call,cancel};
static int marker_read(void *p,int which,n10_u32 *out)
{struct context *c=p;int step=c->steps++;CHECK(which==0 || which==1);if(c->mode==step+1)return -5;*out=c->regs[which];if(c->mode==6 && step==2)*out^=1;return 0;}
static int marker_write(void *p,int which,n10_u32 value)
{struct context *c=p;int step=c->steps++;CHECK(which==0 || which==1);if(c->mode==step+1)return -5;c->regs[which]=value;return 0;}
static const struct n10_marker_ops marker_ops={marker_read,marker_write};
int main(void)
{
    struct context c;struct n10_destination d,bad;struct n10_wdt_witness w,bw;
    n10_u64 output;int i;
    for(i=0;i<4;i++){
        memset(&c,0,sizeof(c));c.chosen=0x84000000;c.mode=i;output=0xdead;
        CHECK((n10_reserve_destination(&reserve_ops,&c,&output)==0)==(i==0));
        CHECK(output==(i==0?c.chosen:0xdead));CHECK(c.steps==(i==0 || i==3));
    }
    for(i=0;i<3;i++){
        memset(&c,0,sizeof(c));c.chosen=i==0?0x84000001:i==1?N10_KEXEC_LIMIT-N10_KEXEC_BYTES+16384:0;
        output=0xdead;CHECK(n10_reserve_destination(&reserve_ops,&c,&output));CHECK(output==0xdead && !c.steps);
    }
    d=destination();CHECK(!n10_destination_valid(&d,build_id));
    for(i=0;i<12;i++){
        bad=d;
        switch(i){case 0:bad.base++;break;case 1:bad.base=N10_KEXEC_LIMIT;break;
        case 2:bad.size--;break;case 3:bad.page_shift=14;break;case 4:bad.reserved_pages--;break;
        case 5:bad.valid_pages--;break;case 6:bad.status=0;break;case 7:bad.generation=0;break;
        case 8:bad.cookie[0]=0;break;case 9:bad.build[0]='a';break;case 10:bad.reserved[15]=1;break;
        case 11:bad.schema=2;break;}
        memset(&c,0,sizeof(c));CHECK(n10_loader_proof(&bad,build_id,park,sizeof(park),&loader_ops,&c));
        CHECK(c.events==0);
    }
    for(i=0;i<4;i++){
        memset(&c,0,sizeof(c));c.mode=i;
        CHECK(n10_loader_proof(&d,build_id,park,sizeof(park),&loader_ops,&c)<0);
        CHECK(!strcmp(c.order,i==1?"A":i==2?"ALC":"ALRC"));
        CHECK(c.loads==(i!=1) && c.reboots==(i==0 || i==3) && c.cancels==(i!=1));
    }
    for(i=0;i<7;i++){
        memset(&c,0,sizeof(c));c.mode=i;c.regs[0]=0xa5a51234;
        CHECK((n10_stage_marker(&marker_ops,&c,0x00ff0000,0x004e0000,0x12345674)==0)==(i==0));
        if(!i){CHECK(c.regs[0]==0xa54e1234 && c.regs[1]==0x12345674);CHECK(c.steps==5);}
    }
    memset(&w,0,sizeof(w));w.present=w.variant_bound=w.enabled=w.reset_enabled=w.pmu_route_enabled=1;
    w.clock_rate=100;w.data=5000;w.first_count=4990;w.last_count=4989;w.effective_timeout=30;
    CHECK(!n10_watchdog_qualified(&w));
    for(i=0;i<11;i++){
        bw=w;switch(i){case 0:bw.present=0;break;case 1:bw.variant_bound=0;break;
        case 2:bw.enabled=0;break;case 3:bw.reset_enabled=0;break;case 4:bw.interrupt_only=1;break;
        case 5:bw.pmu_route_enabled=0;break;case 6:bw.clock_rate=0;break;case 7:bw.data=65536;break;
        case 8:bw.last_count=bw.first_count;break;case 9:bw.last_count=0;break;case 10:bw.effective_timeout=31;break;}
        CHECK(n10_watchdog_qualified(&bw));
    }
    printf("{\"schema\":\"note10-v128-new-backend-fixture-v1\",\"passed\":true,\"checks\":%u,\"reservation_cases\":7,\"descriptor_refusals\":12,\"loader_order_cases\":4,\"marker_cases\":7,\"watchdog_refusals\":11,\"real_syscalls\":0,\"hardware_operations\":0}\n",checks);
    return 0;
}
