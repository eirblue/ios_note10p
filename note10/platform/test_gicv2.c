#include "gicv2.h"
#include <stdio.h>
#include <string.h>
static unsigned checks, tokens;
#define CHECK(x) do { ++checks; if (!(x)) { fprintf(stderr,"line %d: %s\n",__LINE__,#x); return 1; } } while (0)
struct model {
    uint32_t typer, ctlr, iar, eoir, enables[32], last_offset, last_value;
    unsigned calls, fail_at, reads, writes, syncs, acknowledgements;
};
static int fail(struct model *m) { return ++m->calls == m->fail_at; }
static int read_reg(void *opaque, enum n10_gic_bank bank, uint32_t off, uint32_t *out)
{
    struct model *m = opaque;
    if (fail(m)) return 0;
    ++m->reads;
    if (bank == N10_GIC_DISTRIBUTOR && off == 4) *out = m->typer;
    else if (bank == N10_GIC_DISTRIBUTOR && off == 8) *out = 0x12345678;
    else if (bank == N10_GIC_CPU && off == 0xfc) *out = 0x02043b;
    else if (bank == N10_GIC_CPU && off == 0) *out = m->ctlr;
    else if (bank == N10_GIC_CPU && off == 12) { *out = m->iar; ++m->acknowledgements; }
    else return 0;
    return 1;
}
static int write_reg(void *opaque, enum n10_gic_bank bank, uint32_t off, uint32_t value)
{
    struct model *m = opaque;
    if (fail(m)) return 0;
    ++m->writes; m->last_offset = off; m->last_value = value;
    if (bank == N10_GIC_CPU && off == 16) m->eoir = value;
    else if (bank == N10_GIC_DISTRIBUTOR && off >= 0x100 && off < 0x180 && !(off & 3))
        m->enables[(off-0x100)/4] |= value;
    else if (bank == N10_GIC_DISTRIBUTOR && off >= 0x180 && off < 0x200 && !(off & 3))
        m->enables[(off-0x180)/4] &= ~value;
    else return 0;
    return 1;
}
static int sync_io(void *opaque)
{ struct model *m = opaque; if (fail(m)) return 0; ++m->syncs; return 1; }
int main(void)
{
    struct model m = {0};
    struct n10_gic_io io = {&m,read_reg,write_reg,sync_io};
    struct n10_gic_info info = {11,22,33,44}, sentinel = info;
    CHECK(n10_gic_probe(NULL,&info) == N10_GIC_BAD_INPUT);
    for (unsigned i = 1; i <= 3; ++i) {
        m = (struct model){.fail_at=i}; info = sentinel;
        CHECK(n10_gic_probe(&io,&info) == N10_GIC_IO_ERROR);
        CHECK(memcmp(&info,&sentinel,sizeof(info)) == 0 && !m.writes);
    }
    for (unsigned typer = 0; typer < 32; ++typer) {
        m = (struct model){.typer=typer|0xffffffe0U};
        CHECK(n10_gic_probe(&io,&info) == N10_GIC_OK);
        CHECK(info.irq_count == (typer == 31 ? 1020 : (typer+1)*32));
        CHECK(info.typer == m.typer && info.distributor_id == 0x12345678 && info.cpu_id == 0x02043b);
        CHECK(m.reads == 3 && !m.writes);
    }
    for (unsigned irq = 0; irq < 1024; ++irq) {
        unsigned sources = irq < 16 ? 8 : 1;
        for (unsigned src = 0; src < sources; ++src) {
            m = (struct model){.iar=irq|(src<<10)};
            struct n10_gic_irq result = {0xeeee,0xeeee}, before = result;
            if (irq >= 1020) {
                CHECK(n10_gic_take(&io,1020,&result) == N10_GIC_SPECIAL);
                CHECK(memcmp(&result,&before,sizeof(result)) == 0 && !m.writes && !m.syncs);
                struct n10_gic_irq special = {irq,irq};
                CHECK(n10_gic_complete(&io,1020,&special) == N10_GIC_BAD_INPUT && !m.writes);
                continue;
            }
            CHECK(n10_gic_take(&io,1020,&result) == N10_GIC_OK);
            CHECK(result.intid == irq && result.iar == m.iar && m.acknowledgements == 1);
            CHECK(m.reads == 2 && m.syncs == 1 && !m.writes);
            CHECK(n10_gic_complete(&io,1020,&result) == N10_GIC_OK);
            CHECK(m.eoir == m.iar && m.writes == 1 && m.syncs == 3);
            ++tokens;
        }
    }
    for (unsigned irq = 16; irq < 1020; ++irq) {
        m = (struct model){0};
        unsigned bank = irq / 32; uint32_t bit = 1U << (irq%32);
        m.enables[bank] = ~bit;
        CHECK(n10_gic_set_enabled(&io,1020,irq,1) == N10_GIC_OK);
        CHECK(m.enables[bank] == UINT32_MAX && !m.reads && m.writes == 1 && m.syncs == 1);
        CHECK(m.last_offset == 0x100 + bank*4 && m.last_value == bit);
        CHECK(n10_gic_set_enabled(&io,1020,irq,0) == N10_GIC_OK);
        CHECK(m.enables[bank] == ~bit && m.last_offset == 0x180 + bank*4 && m.last_value == bit);
    }
    for (unsigned mode = 9; mode <= 10; ++mode) {
        m = (struct model){.ctlr=1U<<mode};
        struct n10_gic_irq irq = {26,26}, before = irq;
        CHECK(n10_gic_take(&io,1020,&irq) == N10_GIC_UNSUPPORTED_MODE);
        CHECK(!m.acknowledgements && memcmp(&irq,&before,sizeof(irq)) == 0);
        CHECK(n10_gic_complete(&io,1020,&irq) == N10_GIC_UNSUPPORTED_MODE && !m.writes);
    }
    for (unsigned fail_at = 1; fail_at <= 3; ++fail_at) {
        m = (struct model){.iar=29,.fail_at=fail_at};
        struct n10_gic_irq irq = {123,123}, before = irq;
        CHECK(n10_gic_take(&io,1020,&irq) == N10_GIC_IO_ERROR);
        CHECK(memcmp(&irq,&before,sizeof(irq)) == 0 && !m.writes);
        CHECK(m.acknowledgements == (fail_at == 3)); /* IAR cannot be rolled back. */
    }
    for (unsigned fail_at = 1; fail_at <= 4; ++fail_at) {
        m = (struct model){.fail_at=fail_at};
        struct n10_gic_irq irq = {29,29};
        CHECK(n10_gic_complete(&io,1020,&irq) == N10_GIC_IO_ERROR);
        CHECK(m.writes == (fail_at == 4)); /* EOI may already have completed. */
    }
    m = (struct model){0};
    struct n10_gic_irq irq = {29,30};
    CHECK(n10_gic_complete(&io,1020,&irq) == N10_GIC_BAD_INPUT && !m.calls);
    CHECK(n10_gic_set_enabled(&io,1020,15,1) == N10_GIC_BAD_INPUT && !m.calls);
    CHECK(n10_gic_set_enabled(&io,1020,1020,1) == N10_GIC_BAD_INPUT && !m.calls);
    CHECK(n10_gic_set_enabled(&io,1020,29,2) == N10_GIC_BAD_INPUT && !m.calls);
    CHECK(n10_gic_take(&io,33,&irq) == N10_GIC_BAD_INPUT && !m.calls);
    m.iar = 32;
    CHECK(n10_gic_take(&io,32,&irq) == N10_GIC_BAD_INPUT && m.acknowledgements == 1);
    printf("{\"mock_registers\":true,\"ack_eoi_tokens\":%u,\"assertions\":%u,\"passed\":true}\n",tokens,checks);
    return 0;
}
