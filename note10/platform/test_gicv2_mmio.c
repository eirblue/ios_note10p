#include "gicv2_mmio.h"
#include <stdio.h>
#include <string.h>
static uint32_t distributor[1024], cpu[1024];
static unsigned checks;
#define CHECK(x) do { ++checks; if (!(x)) { fprintf(stderr,"line %d: %s\n",__LINE__,#x); return 1; } } while (0)
int main(void)
{
    struct n10_gic_mmio_view view={(uintptr_t)distributor,(uintptr_t)cpu,sizeof(distributor),sizeof(cpu)};
    struct n10_gic_io io={0}, original=io;
    CHECK(!n10_gic_mmio_bind(NULL,&io) && memcmp(&io,&original,sizeof(io))==0);
    struct n10_gic_mmio_view invalid=view;
    invalid.distributor=0; CHECK(!n10_gic_mmio_bind(&invalid,&io));
    invalid=view; ++invalid.cpu; CHECK(!n10_gic_mmio_bind(&invalid,&io));
    invalid=view; invalid.cpu_size=4095; CHECK(!n10_gic_mmio_bind(&invalid,&io));
    invalid=view; invalid.cpu=view.distributor+4; CHECK(!n10_gic_mmio_bind(&invalid,&io));
    invalid=view; invalid.cpu=UINTPTR_MAX-3; CHECK(!n10_gic_mmio_bind(&invalid,&io));
    CHECK(memcmp(&io,&original,sizeof(io))==0);
    CHECK(n10_gic_mmio_bind(&view,&io));
    for (unsigned i=0;i<1024;++i) { distributor[i]=0x12340000+i; cpu[i]=0x56780000+i; }
    for (uint32_t offset=0;offset<0x1100;++offset) {
        uint32_t value=0xcafebabe;
        int allowed=offset==0 || offset==4 || offset==8;
        CHECK(io.read(io.context,N10_GIC_DISTRIBUTOR,offset,&value)==allowed);
        CHECK(value==(allowed ? distributor[offset/4] : 0xcafebabe));
        value=0xcafebabe; allowed=offset==0 || offset==12 || offset==0xfc;
        CHECK(io.read(io.context,N10_GIC_CPU,offset,&value)==allowed);
        CHECK(value==(allowed ? cpu[offset/4] : 0xcafebabe));
        allowed=offset>=0x100 && offset<0x200 && !(offset&3);
        CHECK(io.write(io.context,N10_GIC_DISTRIBUTOR,offset,0)==allowed);
        CHECK(io.write(io.context,N10_GIC_CPU,offset,0)==(offset==16));
    }
    uint32_t value=7;
    CHECK(!io.read(io.context,(enum n10_gic_bank)2,0,&value) && value==7);
    CHECK(!io.read(io.context,N10_GIC_CPU,0,NULL));
    CHECK(!io.write(io.context,N10_GIC_DISTRIBUTOR,0x100,1));
    CHECK(!io.write(io.context,N10_GIC_DISTRIBUTOR,0x180,0xffff));
    CHECK(!io.write(io.context,N10_GIC_DISTRIBUTOR,0x17c,0x80000000));
    CHECK(!io.write(io.context,N10_GIC_DISTRIBUTOR,0x1fc,0xf0000000));
    CHECK(!io.write(io.context,N10_GIC_CPU,0,1)); /* cannot initialize/disable controller */
    CHECK(!io.write(io.context,N10_GIC_CPU,16,1023));
    CHECK(!io.write(io.context,N10_GIC_CPU,16,1U<<13));
    distributor[1]=31; distributor[2]=0x11112222; cpu[0xfc/4]=0x02043b;
    cpu[0]=0;
    struct n10_gic_info info;
    CHECK(n10_gic_probe(&io,&info)==N10_GIC_OK && info.irq_count==1020);
    for (uint32_t irq=16;irq<1020;++irq) {
        CHECK(n10_gic_set_enabled(&io,1020,irq,1)==N10_GIC_OK);
        CHECK(distributor[(0x100+irq/32*4)/4]==(1U<<(irq%32)));
        CHECK(n10_gic_set_enabled(&io,1020,irq,0)==N10_GIC_OK);
        CHECK(distributor[(0x180+irq/32*4)/4]==(1U<<(irq%32)));
    }
    for (unsigned source=0;source<8;++source) {
        cpu[3]=(source<<10)|7;
        struct n10_gic_irq irq;
        CHECK(n10_gic_take(&io,1020,&irq)==N10_GIC_OK);
        CHECK(n10_gic_complete(&io,1020,&irq)==N10_GIC_OK && cpu[4]==cpu[3]);
    }
    cpu[3]=1023; cpu[4]=123;
    struct n10_gic_irq irq={99,99};
    CHECK(n10_gic_take(&io,1020,&irq)==N10_GIC_SPECIAL && irq.intid==99 && cpu[4]==123);
    view.cpu_size=0;
    CHECK(!io.read(io.context,N10_GIC_CPU,0,&value) && value==7);
    CHECK(!io.write(io.context,N10_GIC_CPU,16,10));
    CHECK(!io.sync(io.context));
    printf("{\"normal_memory_buffers_only\":true,\"assertions\":%u,\"passed\":true}\n",checks);
    return 0;
}
