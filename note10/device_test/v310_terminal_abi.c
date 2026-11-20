/* SPDX-License-Identifier: GPL-2.0-only */
/* Diagnostic arena with the eight-CPU, memory-map, /chosen DRAM-span, /defaults ADT and post-MMU telemetry over the existing snapshot channel. */
#include <linux/cpumask.h>
#include <linux/errno.h>
#include <linux/kernel.h>
#include <linux/memblock.h>
#include <linux/n303_mmuoff_contract.h>
#include <linux/of.h>
#include <linux/string.h>
#include <asm/cacheflush.h>
#include <asm/cputype.h>
#include <asm/smp_plat.h>
#include <asm/memory.h>
#include <asm/mmu_context.h>
#include <asm/sysreg.h>
#include "cpu-reset.h"
#include "n304_abi_contract.h"

extern char _text[], _end[], __idmap_text_start[], __idmap_text_end[];
extern void n304_post_abi(void);
int n304_prepare_args(const char *build, const char *boot, const char *cycle);
int n304_enter(void);

static union n304_storage n304_arena __aligned(N304_ARENA_BYTES);

int noinline n304_prepare_args(const char *build, const char *boot, const char *cycle)
{
    struct n304_metadata *meta = &n304_arena.view.meta;
    const char *compatible;
    uint64_t base = __pa_symbol(&n304_arena);
    size_t length;
    uint32_t adt_bytes, cpu;
    struct n310_offsets offsets;
    uint64_t regs[N307_CPUS];
    uint64_t mpidr = read_cpuid_mpidr() & MPIDR_HWID_BITMASK, frequency = read_sysreg(cntfrq_el0);
    uint64_t dram_base = memblock_start_of_DRAM(), dram_end = memblock_end_of_DRAM();

    BUILD_BUG_ON(sizeof(n304_arena) != N304_ARENA_BYTES);
    BUILD_BUG_ON(N10_RT_PAGE != N304_ARENA_BYTES || N10_RT_ARGS_SIZE != N304_ARGS_BYTES);
    BUILD_BUG_ON(offsetof(union n304_storage, view.args) != 0);
    BUILD_BUG_ON(offsetof(union n304_storage, view.adt) != N306_ADT_OFFSET);
    BUILD_BUG_ON(offsetof(union n304_storage, view.meta) != N304_META_OFFSET);
    BUILD_BUG_ON(offsetof(struct n304_metadata, self) != N304_SELF);
    BUILD_BUG_ON(offsetof(struct n304_metadata, record) != N304_RECORD);
    BUILD_BUG_ON(offsetof(struct n304_metadata, cursor) != N304_CURSOR);
    BUILD_BUG_ON(offsetof(struct n304_metadata, next) != N304_NEXT);
    BUILD_BUG_ON(offsetof(struct n304_metadata, adt_bytes) != N304_ADT_BYTES);
    BUILD_BUG_ON(offsetof(struct n304_metadata, args_hash) != N304_ARGS_HASH);
    BUILD_BUG_ON(offsetof(struct n304_metadata, adt_hash) != N304_ADT_HASH);
    BUILD_BUG_ON(offsetof(struct n304_metadata, text) != N304_TEXT);
    BUILD_BUG_ON(offsetof(struct n304_metadata, cpu_reg_offset) != N306_META_REG_OFF);
    BUILD_BUG_ON(offsetof(struct n304_metadata, timebase_offset) != N306_META_TBF_OFF);
    BUILD_BUG_ON(N306_MPIDR_MASK != MPIDR_HWID_BITMASK);
    BUILD_BUG_ON(offsetof(struct n304_metadata, bootargs_map_offset) != N307_META_BOOTARGS_OFF);
    BUILD_BUG_ON(offsetof(struct n304_metadata, devtree_map_offset) != N307_META_DEVTREE_OFF);
    BUILD_BUG_ON(offsetof(struct n304_metadata, dram_base_offset) != N309_META_DRAM_OFF);
    BUILD_BUG_ON(offsetof(struct n304_metadata, defaults_offset) != N310_META_DEFAULTS_OFF);
    BUILD_BUG_ON(N303_RECORD_BYTES != N304_RECORD_BYTES);

    /* Drop any earlier ready state first; it is set again only after every check passes. */
    smp_store_release(&meta->prepared, 0);
    if (num_possible_cpus() != N307_CPUS || smp_processor_id() != 0 || dram_end <= dram_base)
        return -EINVAL;
    for (cpu = 0; cpu < N307_CPUS; ++cpu) {
        regs[cpu] = cpu_logical_map(cpu) & MPIDR_HWID_BITMASK;
        if (regs[cpu] > 0xffffffffULL)
            return -EINVAL;
    }
    if (!n304_owned_span(__pa_symbol(_text), __pa_symbol(_end), base) || mpidr > 0xffffffffULL ||
        regs[0] != mpidr || frequency > 0xffffffffULL ||
        !of_root || of_property_read_string(of_root, "compatible", &compatible))
        return -EINVAL;
    length = strnlen(compatible, N304_COMPAT_BYTES);
    if (length == N304_COMPAT_BYTES)
        return -EINVAL;
    adt_bytes = n310_adt(n304_arena.view.adt, compatible, length + 1, base, regs, N307_CPUS, (uint32_t)frequency,
                         dram_base, dram_end - dram_base, &offsets);
    if (!adt_bytes || n10_rt_validate_adt(n304_arena.view.adt, adt_bytes) ||
        n304_arguments(base, adt_bytes, n304_arena.view.args) ||
        scnprintf(meta->text, sizeof(meta->text), N304_FORMAT, build, boot, cycle) != N304_RECORD_BYTES)
        return -EINVAL;
    meta->self = base;
    meta->adt_bytes = adt_bytes;
    meta->cpu_reg_offset = offsets.reg;
    meta->timebase_offset = offsets.timebase;
    meta->bootargs_map_offset = offsets.bootargs;
    meta->devtree_map_offset = offsets.devtree;
    meta->dram_base_offset = offsets.dram;
    meta->defaults_offset = offsets.defaults;
    meta->args_hash = n304_fnv(n304_arena.view.args, N304_ARGS_BYTES);
    meta->adt_hash = n304_fnv(n304_arena.view.adt, adt_bytes);
    smp_store_release(&meta->prepared, 1);
    return 0;
}

int noinline n304_enter(void)
{
    struct n304_metadata *meta = &n304_arena.view.meta;
    struct n303_slot slot;
    unsigned long daif, start = (unsigned long)__idmap_text_start, end = (unsigned long)__idmap_text_end;
    phys_addr_t entry = __pa_symbol(n304_post_abi), restart = __pa_symbol(__cpu_soft_restart);
    phys_addr_t low = __pa_symbol(__idmap_text_start), high = __pa_symbol(__idmap_text_end);
    phys_addr_t args = __pa_symbol(&n304_arena);

    if (!smp_load_acquire(&meta->prepared) || meta->self != args || read_sysreg(CurrentEL) != 4 ||
        !(read_sysreg(sctlr_el1) & 1) || end <= start || end - start > 4096 ||
        entry < low || entry >= high || restart < low || restart >= high)
        return -EINVAL;
    if (num_online_cpus() > 8)
        return -EBUSY;
    /* One-shot: any failure after this point requires a fresh n304_prepare_args(). */
    if (cmpxchg(&meta->prepared, 1, 0) != 1)
        return -EPERM;
    if (meta->adt_bytes < N306_ADT_MIN_BYTES || meta->adt_bytes > N307_ADT_MAX_BYTES || meta->adt_bytes % 4 ||
        n304_fnv(n304_arena.view.args, N304_ARGS_BYTES) != meta->args_hash ||
        n304_fnv(n304_arena.view.adt, meta->adt_bytes) != meta->adt_hash)
        return -EINVAL;
    daif = read_sysreg(daif);
    asm volatile("msr daifset, #0xf" ::: "memory");
    if (n303_snapshot_claim(&slot))
        goto refused;
    /* Record and cursor belong to the snapshot, not to the v304 arena; they must not touch it or each other. */
    if (!n304_disjoint(slot.record, N304_RECORD_BYTES, args, N304_ARENA_BYTES) ||
        !n304_disjoint(slot.cursor, sizeof(uint32_t), args, N304_ARENA_BYTES) ||
        !n304_disjoint(slot.record, N304_RECORD_BYTES, slot.cursor, sizeof(uint32_t)) ||
        (slot.cursor & 3) || slot.next != (uint32_t)slot.next)
        goto refused;
    meta->record = slot.record;
    meta->cursor = slot.cursor;
    meta->next = slot.next;
    /* The physical stub reads the entire diagnostic arena after C and I are clear. */
    __flush_dcache_area(&n304_arena, sizeof(n304_arena));
    __flush_dcache_area(__idmap_text_start, end - start);
    flush_icache_range(start, end);
    cpu_soft_restart(0, entry, args, 0, 0);
refused:
    write_sysreg(daif, daif);
    return -EINVAL;
}
