#ifndef NOTE10_GICV2_H
#define NOTE10_GICV2_H
#include <stdint.h>
/* Register offsets only. The caller supplies owned, correctly mapped GICv2
 * distributor/CPU interfaces. There are no direct MMIO pointers in this module.
 */
enum n10_gic_bank { N10_GIC_DISTRIBUTOR, N10_GIC_CPU };
typedef int (*n10_gic_read_fn)(void *, enum n10_gic_bank, uint32_t, uint32_t *);
typedef int (*n10_gic_write_fn)(void *, enum n10_gic_bank, uint32_t, uint32_t);
/* Caller implements appropriate device/CPU ordering; success means completed.
 * Called after IAR read, before EOI and after an enable/disable/EOI write.
 */
typedef int (*n10_gic_sync_fn)(void *);
struct n10_gic_io {
    void *context;
    n10_gic_read_fn read;
    n10_gic_write_fn write;
    n10_gic_sync_fn sync;
};
struct n10_gic_info { uint32_t typer, distributor_id, cpu_id, irq_count; };
struct n10_gic_irq { uint32_t iar, intid; };
enum n10_gic_result {
    N10_GIC_OK, N10_GIC_BAD_INPUT, N10_GIC_IO_ERROR,
    N10_GIC_SPECIAL, N10_GIC_UNSUPPORTED_MODE
};
/* Read-only register snapshot; this does not prove silicon identity or usable
 * security-group ownership. Output is unchanged on a read failure.
 */
enum n10_gic_result n10_gic_probe(const struct n10_gic_io *, struct n10_gic_info *);
/* Already initialized EOImode=0 only. Both EOImode bits must read zero in the
 * caller's security view. No CTLR writes, distributor reset or group changes.
 * IAR reads acknowledge hardware: an I/O/sync failure is not rollback-safe.
 */
enum n10_gic_result n10_gic_take(const struct n10_gic_io *, uint32_t irq_count, struct n10_gic_irq *);
/* Exact acknowledged token, same CPU, interrupt nesting/order enforced by caller.
 * Special IDs 1020..1023 must never be completed with EOIR.
 */
enum n10_gic_result n10_gic_complete(const struct n10_gic_io *, uint32_t irq_count, const struct n10_gic_irq *);
/* PPIs and SPIs only. SGI enable state, priority, routing and trigger setup are
 * outside scope. A write/sync failure can leave hardware partially changed.
 */
enum n10_gic_result n10_gic_set_enabled(const struct n10_gic_io *, uint32_t irq_count, uint32_t intid, unsigned enabled);
#endif
