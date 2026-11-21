/* SPDX-License-Identifier: GPL-2.0-only */
/* v311: the diagnostic arena lives at the base of the reserved 256 MiB window; the XNU memory image is read into the
 * window before stop_machine and described by boot_args. The image is hashed and never executed.
 * v312: the image's single LC_UNIXTHREAD entry offset is parsed in process context and stored for the stub, which only
 * reads and records the entry word (no branch).
 * v314: the record span grows by the XNU breadcrumbs: it must fit before the log end and stay disjoint from the window
 * and the cursor. v315: three 8-byte checkpoint crumbs (N315_RECORD_SPAN). */
#include <linux/cpumask.h>
#include <linux/err.h>
#include <linux/errno.h>
#include <linux/fs.h>
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

extern char __idmap_text_start[], __idmap_text_end[];
extern void n304_post_abi(void);
int n304_prepare_args(const char *build, const char *boot, const char *cycle);
int n304_enter(void);
int n312_load_image(void);

/* Only after n311_window_ok(). */
static inline union n304_storage *n311_arena(void)
{
    return (union n304_storage *)phys_to_virt(n311_window_base);
}

static inline uint32_t n311_le32(const uint8_t *p)
{
    return (uint32_t)p[0] | (uint32_t)p[1] << 8 | (uint32_t)p[2] << 16 | (uint32_t)p[3] << 24;
}

/* Reserved window: 32 MiB aligned, at or above 2 GiB, wholly inside the memblock DRAM span. */
static int n311_window_ok(uint64_t base)
{
    uint64_t dram_base = memblock_start_of_DRAM(), dram_end = memblock_end_of_DRAM();

    return n311_window_status == 1 && base == n311_window_base && !(base % N311_WINDOW_ALIGN) &&
           base >= N311_WINDOW_MIN && base >= dram_base && base < dram_end &&
           N311_WINDOW_BYTES <= dram_end - base;
}

/* Process context, once, from n302_park_write before stop_machine. Any failure (including the v312 LC_UNIXTHREAD
 * parse) returns before the transfer with image_bytes 0, so prepare/enter refuse. */
int noinline n312_load_image(void)
{
    union n304_storage *arena;
    struct file *file;
    uint8_t *dest;
    loff_t size, position = 0;
    ssize_t count;
    uint32_t entry;

    if (!n311_window_ok(n311_window_base))
        return -ENOMEM;
    arena = n311_arena();
    memset(arena, 0, sizeof(*arena));
    file = filp_open(N311_IMAGE_PATH, O_RDONLY, 0);
    if (IS_ERR(file))
        return PTR_ERR(file);
    size = i_size_read(file_inode(file));
    if (size <= 0 || !n311_image_bytes_ok(size)) {
        filp_close(file, NULL);
        return -EFBIG;
    }
    dest = phys_to_virt(n311_window_base + N311_KERNEL_OFFSET);
    while (position < size) {
        count = kernel_read(file, dest + position, size - position, &position);
        if (count <= 0)
            break;
    }
    filp_close(file, NULL);
    if (position != size || n311_le32(dest) != N311_MH_MAGIC || n311_le32(dest + 4) != N311_MH_CPU_ARM64 ||
        n311_le32(dest + 12) != N311_MH_EXECUTE || n312_entry_offset(dest, (uint32_t)size, &entry))
        return -EINVAL;
    arena->view.meta.image_hash = n311_fnv_words(dest, (uint32_t)(size / 4));
    arena->view.meta.entry_offset = entry;
    arena->view.meta.image_bytes = (uint32_t)size; /* last: nonzero means fully loaded and parsed */
    return 0;
}

int noinline n304_prepare_args(const char *build, const char *boot, const char *cycle)
{
    union n304_storage *arena;
    struct n304_metadata *meta;
    const char *compatible;
    uint64_t base = n311_window_base;
    size_t length;
    uint32_t adt_bytes, cpu;
    struct n310_offsets offsets;
    uint64_t regs[N307_CPUS];
    uint64_t mpidr = read_cpuid_mpidr() & MPIDR_HWID_BITMASK, frequency = read_sysreg(cntfrq_el0);
    uint64_t dram_base = memblock_start_of_DRAM(), dram_end = memblock_end_of_DRAM();

    BUILD_BUG_ON(sizeof(union n304_storage) != N304_ARENA_BYTES);
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
    BUILD_BUG_ON(offsetof(struct n304_metadata, image_bytes) != N311_META_IMAGE_BYTES);
    BUILD_BUG_ON(offsetof(struct n304_metadata, image_hash) != N311_META_IMAGE_HASH);
    BUILD_BUG_ON(offsetof(struct n304_metadata, entry_offset) != N312_META_ENTRY_OFFSET);
    BUILD_BUG_ON(N312_LINK_BASE != N311_VIRT_BASE + N311_KERNEL_OFFSET);
    BUILD_BUG_ON(N10_RT_WINDOW != N311_WINDOW_BYTES || N10_RT_BLOCK != N311_WINDOW_ALIGN || N10_RT_MIN_BASE != N311_WINDOW_MIN);
    BUILD_BUG_ON(N303_RECORD_BYTES != N304_RECORD_BYTES);

    /* No reservation, no arena: nothing is dereferenced before the window is confirmed. */
    if (!n311_window_ok(base))
        return -ENOMEM;
    arena = n311_arena();
    meta = &arena->view.meta;
    /* Drop any earlier ready state first; it is set again only after every check passes. */
    smp_store_release(&meta->prepared, 0);
    if (num_possible_cpus() != N307_CPUS || smp_processor_id() != 0 || dram_end <= dram_base ||
        !n311_image_bytes_ok(meta->image_bytes) || !meta->entry_offset)
        return -EINVAL;
    for (cpu = 0; cpu < N307_CPUS; ++cpu) {
        regs[cpu] = cpu_logical_map(cpu) & MPIDR_HWID_BITMASK;
        if (regs[cpu] > 0xffffffffULL)
            return -EINVAL;
    }
    if (mpidr > 0xffffffffULL ||
        regs[0] != mpidr || frequency > 0xffffffffULL ||
        !of_root || of_property_read_string(of_root, "compatible", &compatible))
        return -EINVAL;
    length = strnlen(compatible, N304_COMPAT_BYTES);
    if (length == N304_COMPAT_BYTES)
        return -EINVAL;
    adt_bytes = n310_adt(arena->view.adt, compatible, length + 1, base, regs, N307_CPUS, (uint32_t)frequency,
                         dram_base, dram_end - dram_base, &offsets);
    if (!adt_bytes || n10_rt_validate_adt(arena->view.adt, adt_bytes) ||
        n311_arguments(base, adt_bytes, meta->image_bytes, arena->view.args) ||
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
    meta->args_hash = n304_fnv(arena->view.args, N304_ARGS_BYTES);
    meta->adt_hash = n304_fnv(arena->view.adt, adt_bytes);
    smp_store_release(&meta->prepared, 1);
    return 0;
}

int noinline n304_enter(void)
{
    union n304_storage *arena;
    struct n304_metadata *meta;
    struct n303_slot slot;
    unsigned long daif, start = (unsigned long)__idmap_text_start, end = (unsigned long)__idmap_text_end;
    phys_addr_t entry = __pa_symbol(n304_post_abi), restart = __pa_symbol(__cpu_soft_restart);
    phys_addr_t low = __pa_symbol(__idmap_text_start), high = __pa_symbol(__idmap_text_end);
    phys_addr_t args = n311_window_base;

    if (!n311_window_ok(args))
        return -ENOMEM;
    arena = n311_arena();
    meta = &arena->view.meta;
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
        !n311_image_bytes_ok(meta->image_bytes) ||
        n304_fnv(arena->view.args, N304_ARGS_BYTES) != meta->args_hash ||
        n304_fnv(arena->view.adt, meta->adt_bytes) != meta->adt_hash)
        return -EINVAL;
    daif = read_sysreg(daif);
    asm volatile("msr daifset, #0xf" ::: "memory");
    if (n303_snapshot_claim(&slot) || slot.tail < N315_RECORD_SPAN)
        goto refused;
    /* Record and cursor belong to the snapshot, not to the window; they must not touch it or each other. */
    if (!n304_disjoint(slot.record, N315_RECORD_SPAN, args, N311_WINDOW_BYTES) ||
        !n304_disjoint(slot.cursor, sizeof(uint32_t), args, N311_WINDOW_BYTES) ||
        !n304_disjoint(slot.record, N315_RECORD_SPAN, slot.cursor, sizeof(uint32_t)) ||
        (slot.cursor & 3) || slot.next != (uint32_t)slot.next)
        goto refused;
    meta->record = slot.record;
    meta->cursor = slot.cursor;
    meta->next = slot.next;
    /* The physical stub reads the entire diagnostic arena and the loaded image after C and I are clear. */
    __flush_dcache_area(arena, sizeof(*arena));
    __flush_dcache_area(phys_to_virt(args + N311_KERNEL_OFFSET), meta->image_bytes);
    __flush_dcache_area(__idmap_text_start, end - start);
    flush_icache_range(start, end);
    cpu_soft_restart(0, entry, args, 0, 0);
refused:
    write_sysreg(daif, daif);
    return -EINVAL;
}
