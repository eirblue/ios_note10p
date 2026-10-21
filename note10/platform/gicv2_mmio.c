#include "gicv2_mmio.h"
#if !defined(__aarch64__) || __BYTE_ORDER__ != __ORDER_LITTLE_ENDIAN__
#error This adapter requires little-endian AArch64
#endif
static int valid_range(uintptr_t base, size_t size)
{ return base && !(base & 3) && size >= 0x1000 && base <= UINTPTR_MAX-(size-1); }
static int valid_view(const struct n10_gic_mmio_view *v)
{
    if (!v || !valid_range(v->distributor,v->distributor_size) || !valid_range(v->cpu,v->cpu_size)) return 0;
    return v->distributor < v->cpu ? v->distributor_size <= v->cpu-v->distributor :
                                   v->cpu_size <= v->distributor-v->cpu;
}
static volatile uint32_t *word(const struct n10_gic_mmio_view *v, enum n10_gic_bank bank, uint32_t offset)
{
    if (!valid_view(v) || (offset & 3)) return 0;
    uintptr_t base; size_t size;
    if (bank == N10_GIC_DISTRIBUTOR) { base=v->distributor; size=v->distributor_size; }
    else if (bank == N10_GIC_CPU) { base=v->cpu; size=v->cpu_size; }
    else return 0;
    if (offset > size-4) return 0;
    return (volatile uint32_t *)(base+offset);
}
static int read_word(void *context, enum n10_gic_bank bank, uint32_t offset, uint32_t *out)
{
    if (!out) return 0;
    if (bank == N10_GIC_DISTRIBUTOR ? offset!=0 && offset!=4 && offset!=8 :
        bank != N10_GIC_CPU || (offset!=0 && offset!=12 && offset!=0xfc)) return 0;
    volatile uint32_t *p=word(context,bank,offset);
    if (!p) return 0;
    *out=*p;
    return 1;
}
static int write_word(void *context, enum n10_gic_bank bank, uint32_t offset, uint32_t value)
{
    if (bank == N10_GIC_DISTRIBUTOR) {
        if (offset<0x100 || offset>=0x200) return 0;
        if ((offset==0x100 || offset==0x180) && (value&0xffff)) return 0; /* no SGI enable changes */
        if ((offset==0x17c || offset==0x1fc) && (value&0xf0000000U)) return 0; /* special IDs */
    } else if (bank != N10_GIC_CPU || offset!=16 || (value&~0x1fffU) || (value&1023)>=1020) return 0;
    volatile uint32_t *p=word(context,bank,offset);
    if (!p) return 0;
    *p=value;
    return 1;
}
static int synchronize(void *context)
{
    if (!valid_view(context)) return 0;
    __asm__ volatile("dsb sy\n\tisb" ::: "memory");
    return 1;
}
int n10_gic_mmio_bind(const struct n10_gic_mmio_view *view, struct n10_gic_io *out)
{
    if (!out || !valid_view(view)) return 0;
    *out=(struct n10_gic_io){(void *)view,read_word,write_word,synchronize};
    return 1;
}
