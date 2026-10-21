#ifndef NOTE10_GICV2_MMIO_H
#define NOTE10_GICV2_MMIO_H
#include <stddef.h>
#include "gicv2.h"
/* Virtual addresses of caller-owned Device-mapped windows, not physical DT
 * addresses. Keep view immutable and alive while callbacks are published.
 * Caller supplies mapping/fault containment and interrupt/CPU synchronization.
 */
struct n10_gic_mmio_view {
    uintptr_t distributor, cpu;
    size_t distributor_size, cpu_size;
};
/* Validates ranges and binds callbacks; performs no register access.
 * out must not alias view. Invalid inputs preserve out.
 */
int n10_gic_mmio_bind(const struct n10_gic_mmio_view *view, struct n10_gic_io *out);
#endif
