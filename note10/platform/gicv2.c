#include "gicv2.h"

static int valid_io(const struct n10_gic_io *io)
{ return io && io->read && io->write && io->sync; }
static int valid_count(uint32_t count)
{ return count >= 32 && count <= 1020 && (count == 1020 || !(count & 31)); }
static enum n10_gic_result check_mode(const struct n10_gic_io *io)
{
    uint32_t ctrl;
    if (!io->read(io->context,N10_GIC_CPU,0,&ctrl)) return N10_GIC_IO_ERROR;
    /* EOImodeS/NS in secure view; EOImodeNS is bit 9 in non-secure view.
     * Reject either set bit conservatively; split deactivation is not supplied.
     */
    return ctrl & ((1U << 9) | (1U << 10)) ? N10_GIC_UNSUPPORTED_MODE : N10_GIC_OK;
}
enum n10_gic_result n10_gic_probe(const struct n10_gic_io *io, struct n10_gic_info *out)
{
    if (!valid_io(io) || !out) return N10_GIC_BAD_INPUT;
    struct n10_gic_info info;
    if (!io->read(io->context,N10_GIC_DISTRIBUTOR,4,&info.typer) ||
        !io->read(io->context,N10_GIC_DISTRIBUTOR,8,&info.distributor_id) ||
        !io->read(io->context,N10_GIC_CPU,0xfc,&info.cpu_id)) return N10_GIC_IO_ERROR;
    info.irq_count = ((info.typer & 31) + 1) * 32;
    if (info.irq_count > 1020) info.irq_count = 1020;
    *out = info;
    return N10_GIC_OK;
}
enum n10_gic_result n10_gic_take(const struct n10_gic_io *io, uint32_t count, struct n10_gic_irq *out)
{
    if (!valid_io(io) || !valid_count(count) || !out) return N10_GIC_BAD_INPUT;
    enum n10_gic_result result = check_mode(io);
    if (result != N10_GIC_OK) return result;
    uint32_t raw;
    if (!io->read(io->context,N10_GIC_CPU,0x0c,&raw)) return N10_GIC_IO_ERROR;
    uint32_t intid = raw & 1023;
    if (intid >= 1020) return N10_GIC_SPECIAL;
    if ((raw & ~0x1fffU) || intid >= count) return N10_GIC_BAD_INPUT;
    if (!io->sync(io->context)) return N10_GIC_IO_ERROR;
    *out = (struct n10_gic_irq){raw,intid};
    return N10_GIC_OK;
}
enum n10_gic_result n10_gic_complete(const struct n10_gic_io *io, uint32_t count, const struct n10_gic_irq *irq)
{
    if (!valid_io(io) || !valid_count(count) || !irq || irq->intid >= count ||
        irq->intid >= 1020 || (irq->iar & ~0x1fffU) || (irq->iar & 1023) != irq->intid)
        return N10_GIC_BAD_INPUT;
    enum n10_gic_result result = check_mode(io);
    if (result != N10_GIC_OK) return result;
    if (!io->sync(io->context) || !io->write(io->context,N10_GIC_CPU,0x10,irq->iar) ||
        !io->sync(io->context)) return N10_GIC_IO_ERROR;
    return N10_GIC_OK;
}
enum n10_gic_result n10_gic_set_enabled(const struct n10_gic_io *io, uint32_t count, uint32_t irq, unsigned enabled)
{
    if (!valid_io(io) || !valid_count(count) || irq < 16 || irq >= count || enabled > 1)
        return N10_GIC_BAD_INPUT;
    uint32_t offset = (enabled ? 0x100 : 0x180) + (irq / 32) * 4;
    if (!io->write(io->context,N10_GIC_DISTRIBUTOR,offset,1U << (irq % 32)) ||
        !io->sync(io->context)) return N10_GIC_IO_ERROR;
    return N10_GIC_OK;
}
