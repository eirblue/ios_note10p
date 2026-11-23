/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef N304_ABI_CONTRACT_H
#define N304_ABI_CONTRACT_H

#define N304_ARENA_BYTES 16384
#define N304_ARGS_BYTES 1152
/* v306: multi-node ADT at a new arena offset; [1152,1408) stays zero. */
#define N306_ADT_OFFSET 2048
#define N307_ADT_STORAGE 4096 /* v317: 2048 -> 4096 for the 256-byte /chosen random-seed; ADT [2048, 6144) of the 16 KiB arena/handoff page */
#define N306_ADT_MIN_BYTES 108
#define N307_ADT_MAX_BYTES 4096 /* v307 record n= is the walked node count; v317: 2048 -> 4096 (names kept so the v316 stub/C are reused) */
#define N304_COMPAT_BYTES 64
#define N304_META_OFFSET 1408
#define N304_SELF 0
#define N304_RECORD 8
#define N304_CURSOR 16
#define N304_NEXT 24
#define N304_ADT_BYTES 32
#define N304_ARGS_HASH 36
#define N304_ADT_HASH 40
#define N304_TEXT 48

#define N304_RECORD_BYTES 250
#define N304_BODY_OFFSET 9
#define N304_BODY_BYTES 229
#define N304_REG_OFFSET 117
#define N304_ARGS_HASH_OFFSET 187
#define N304_ADT_HASH_OFFSET 198
#define N304_ADT_LENGTH_OFFSET 209
#define N304_SCTLR_OFFSET 218
#define N304_EL_OFFSET 237
#define N304_CSUM_OFFSET 241
#define N304_COMMIT_OFFSET 7
#define N304_FORMAT "N335PS20 id=%s b=%s c=%s r=0000000000000000,0000000000000000,0000000000000000,0000000000000000 a=00000000 d=00000000 n=00 q=0 s=0000000000000000 e=0 f=00000000\n"
#define N304_DAIF_OFFSET 214

/* v305: populated XNU CommandLine and boot_args field offsets checked by the stub.
 * Offsets follow struct n10_rt_boot_layout in runtime_relocation.h. */
#define N305_COMMAND "-v n10diag=305"
#define N305_COMMAND_BYTES 14
#define N305_VIRT 8
#define N305_PHYS 16
#define N305_MEMSIZE 24
#define N305_TOP 32
#define N305_MACHINE 88
#define N305_CMDLINE 108
#define N305_CMDLINE_BYTES 1024
#define N305_BOOTFLAGS 1136
#define N305_MEMACTUAL 1144

/* v306: Video[6] at boot_args+40, cpu0 property offsets stored after the record text,
 * and the Linux arm64 MPIDR_HWID_BITMASK used for the cpu0 reg cross-check. */
#define N306_VIDEO 40
#define N306_META_REG_OFF 300
#define N306_META_TBF_OFF 304
#define N306_MPIDR_MASK 0xff00ffffff

/* v307: eight cpu nodes and /chosen/memory-map BootArgs/DeviceTree value offsets. */
#define N307_CPUS 8
#define N307_META_BOOTARGS_OFF 308
#define N307_META_DEVTREE_OFF 312

/* v309: /chosen dram-base/dram-size LE64 value offset (ADT-relative) and the base-to-size value stride. */
#define N309_META_DRAM_OFF 316
#define N309_DRAM_NAME_STRIDE 44

/* v310: root-level /defaults{name="defaults"} node start (ADT-relative); it is the last 56 bytes of the ADT. */
#define N310_META_DEFAULTS_OFF 320
#define N310_DEFAULTS_NODE_BYTES 56

/* v311: 256 MiB memblock window at B (32 MiB aligned, >= 2 GiB). The arena sits at B and the XNU memory image
 * (read from N311_IMAGE_PATH before stop_machine) at B + N311_KERNEL_OFFSET. Plain integers: shared with the stub. */
#define N311_WINDOW_BYTES 0x10000000
#define N311_WINDOW_ALIGN 0x2000000
#define N311_WINDOW_MIN 0x80000000
#define N311_VIRT_BASE 0xfffffe0006000000 /* v319: slid XNU link VA 0xfffffe0007004000 rounded down to 32 MiB */
#define N311_KERNEL_OFFSET 0x1004000 /* the stub materializes it with mov/movk (too wide for an add immediate) */
#define N311_IMAGE_PATH "/tmp/n10-v311-kernel.mem"
#define N311_MH_MAGIC 0xfeedfacf
#define N311_MH_CPU_ARM64 0x0100000c
#define N311_MH_EXECUTE 2
#define N311_META_IMAGE_BYTES 324
#define N311_META_IMAGE_HASH 328

/* v312: LC_UNIXTHREAD entry target. Linux parses it once (n312_entry_offset) and stores entry_offset = pc - link base;
 * the MMU-off stub loads the 32-bit word at B + N311_KERNEL_OFFSET + entry_offset and records it in r[3]. v313 branches
 * to it once after the record commit. */
#define N312_LINK_BASE 0xfffffe0007004000ULL /* = N311_VIRT_BASE + N311_KERNEL_OFFSET; the private image is slid to this base; C only (ULL) */
#define N312_LC_SEGMENT_64 0x19
#define N312_LC_UNIXTHREAD 0x5
#define N312_THREAD_FLAVOR 6 /* ARM_THREAD_STATE64 */
#define N312_THREAD_COUNT 68
#define N312_THREAD_PC_OFFSET 272 /* 16 + 256 within the command */
#define N312_THREAD_CMD_MIN 288
#define N312_SEGMENT_CMD_MIN 72
#define N312_VM_PROT_EXECUTE 4
#define N312_META_ENTRY_OFFSET 332

/* v313: pre-branch gates. The entry word must be an unconditional B (XNU _start is 'b start_first_cpu'), CPU0 must
 * support the 16 KiB granule (ID_AA64MMFR0_EL1.TGran16 [23:20] is 1 or 2) and the window end must lie below 2^39 (XNU
 * bootstrap V=P map). After the N313PS2T commit the stub executes 'isb; mov x0, x19; br x18' with
 * x18 = B + N311_KERNEL_OFFSET + entry_offset. Plain integers: shared with the stub. */
#define N313_B_OPCODE_MASK 0xfc000000
#define N313_B_OPCODE 0x14000000
#define N313_MMFR0_TGRAN16_SHIFT 20
#define N313_PA_LIMIT_SHIFT 39

/* v315: three 8-byte XNU checkpoint crumbs follow the record. They are written after the branch by the private XNU-side
 * patch, only at [next, next + N315_CRUMB_BYTES) and only while the live dss cursor is next, next + 8 or next + 16 (then
 * advanced by 8); Linux keeps the whole span inside the dss log and disjoint from the cursor and the window, and the stub
 * cleans it with the record. */
#define N315_CRUMB_BYTES 24
#define N315_RECORD_SPAN (N304_RECORD_BYTES + N315_CRUMB_BYTES) /* 274: record + three 8-byte XNU checkpoint crumbs */
/* v315: boot_args memSize. XNU's Exynos bootstrap builder maps memSize - kernel offset bytes from the image PA and refuses
 * more than 32 MiB, so memSize = N311_KERNEL_OFFSET + 32 MiB. memSizeActual stays N311_WINDOW_BYTES. Plain integer:
 * shared with the stub. */
#define N315_BOOT_MEMSIZE 0x3004000 /* N311_KERNEL_OFFSET + 32 MiB */
/* v316: XNU handoff page H = B + N311_KERNEL_OFFSET + image_bytes, right after the loaded image and inside XNU's bootstrap
 * map. Linux copies the checked arena boot_args to H + 0 and the ADT to H + N306_ADT_OFFSET; the stub proves the copy and
 * branches with x0 = H. Plain integer: shared with the stub. */
#define N316_HANDOFF_BYTES 0x4000 /* XNU handoff page right after the image: boot_args at +0, ADT at +N306_ADT_OFFSET; topOfKernelData = its end */
/* v317: /chosen random-seed (public synthetic constant seed[i] = 1 + i % 255, no zero byte) after dram-size. */
#define N317_SEED_BYTES 256 /* /chosen random-seed length XNU early_random_init requires */
/* v321: /chosen/note10-platform GIC handoff contract required by the XNU pe_note10_init_irq (public Exynos 9825
 * GIC-400 SoC constants): GICD/GICC base and size, timer PPI (CNTPNSIRQ) and contract version. */
#define N321_GICD_BASE 0x10101000
#define N321_GICC_BASE 0x10102000
#define N321_GIC_SIZE 0x1000
#define N321_TIMER_INTID 30
#define N321_PLATFORM_VERSION 1

#ifndef __ASSEMBLY__
#include "runtime_relocation.h"

#ifndef __KERNEL__
/* v313 (host C only; the 4.14 gnu89 kernel build has no static_assert): the window base and the XNU virtual base are
 * multiples of the 32 MiB L2 block of the 16 KiB granule. */
_Static_assert(N311_WINDOW_ALIGN % 0x2000000 == 0, "window align is a 32 MiB multiple");
_Static_assert(N311_VIRT_BASE % 0x2000000 == 0, "virtual base is a 32 MiB multiple");
/* v319: mirror of the XNU bootstrap builder VA rule (VA >> 47 == 0x1ffff) for the start and end of the 32 MiB map. */
_Static_assert((N311_VIRT_BASE >> 47) == 0x1ffff, "virtual base inside the TTBR1 half");
_Static_assert(((N311_VIRT_BASE + N311_KERNEL_OFFSET + 0x2000000 - 1) >> 47) == 0x1ffff, "bootstrap map end inside the TTBR1 half");
/* v314: the private XNU patch hard-codes these two meta offsets relative to B (meta.cursor, meta.next). */
_Static_assert(N304_META_OFFSET + N304_CURSOR == 1424, "meta.cursor at B + 1424");
_Static_assert(N304_META_OFFSET + N304_NEXT == 1432, "meta.next at B + 1432");
/* v315: boot memSize is a 16 KiB multiple, maps exactly 32 MiB from the image PA and stays inside the window. */
_Static_assert(N315_BOOT_MEMSIZE % 0x4000 == 0, "boot memSize is a 16 KiB multiple");
_Static_assert(N315_BOOT_MEMSIZE - N311_KERNEL_OFFSET == 0x2000000, "boot memSize maps 32 MiB from the image");
_Static_assert(N315_BOOT_MEMSIZE <= N311_WINDOW_BYTES, "boot memSize inside the window");
/* v316: the handoff page is one arena-sized page and holds args at +0 and the ADT storage at +N306_ADT_OFFSET. */
_Static_assert(N316_HANDOFF_BYTES == N304_ARENA_BYTES, "handoff page is one 16 KiB page");
_Static_assert(N306_ADT_OFFSET + N307_ADT_STORAGE <= N316_HANDOFF_BYTES, "ADT copy fits the handoff page");
/* v317: the largest n310_adt (64-byte compatible) fits the ADT storage. v321: 2592 with /chosen/note10-platform. */
_Static_assert(2592 + N304_COMPAT_BYTES <= N307_ADT_STORAGE, "largest ADT fits the storage");
#endif

struct n304_metadata {
    uint64_t self, record, cursor, next;
    uint32_t adt_bytes, args_hash, adt_hash, prepared;
    char text[N304_RECORD_BYTES + 1];
    uint32_t cpu_reg_offset, timebase_offset; /* relative to the ADT start */
    uint32_t bootargs_map_offset, devtree_map_offset; /* memory-map values, ADT-relative */
    uint32_t dram_base_offset; /* v309: /chosen dram-base value, ADT-relative; dram-size follows at +44 */
    uint32_t defaults_offset; /* v310: /defaults node start, ADT-relative */
    uint32_t image_bytes, image_hash; /* v311: loaded XNU image size and word-FNV (0 bytes = not loaded) */
    uint32_t entry_offset; /* v312: LC_UNIXTHREAD pc - N312_LINK_BASE (0 = not parsed) */
};

union n304_storage {
    struct {
        uint8_t args[N304_ARGS_BYTES];
        uint8_t unused[N304_META_OFFSET - N304_ARGS_BYTES];
        struct n304_metadata meta;
        uint8_t gap[N306_ADT_OFFSET - N304_META_OFFSET - sizeof(struct n304_metadata)];
        uint8_t adt[N307_ADT_STORAGE];
    } view;
    uint8_t arena[N304_ARENA_BYTES];
};

/* v311: defined in n311_xnu_window.c; uint64_t is phys_addr_t's type on arm64. */
extern uint64_t n311_window_base;
extern int n311_window_status;

static inline int n304_disjoint(uint64_t a, uint64_t alen, uint64_t b, uint64_t blen)
{ 
    return a + alen > a && b + blen > b && (a + alen <= b || b + blen <= a);
}

static inline void n306_put32(uint8_t *out, uint32_t value)
{
    out[0] = (uint8_t)value;
    out[1] = (uint8_t)(value >> 8);
    out[2] = (uint8_t)(value >> 16);
    out[3] = (uint8_t)(value >> 24);
}

static inline uint32_t n306_node(uint8_t *out, uint32_t at, uint32_t props, uint32_t children)
{
    n306_put32(out + at, props);
    n306_put32(out + at + 4, children);
    return at + 8;
}

/* XNU property: 32-byte NUL-padded name, u32 length, value zero-padded to 4. */
static inline uint32_t n306_prop(uint8_t *out, uint32_t at, const char *name,
                                 const void *value, uint32_t length)
{
    const uint8_t *bytes = value;
    uint32_t i;

    for (i = 0; name[i]; ++i)
        out[at + i] = (uint8_t)name[i];
    n306_put32(out + at + 32, length);
    for (i = 0; i < length; ++i)
        out[at + 36 + i] = bytes[i];
    return at + 36 + ((length + 3) & ~3U);
}

struct n310_offsets {
    uint32_t reg, timebase, bootargs, devtree, dram, defaults;
};

static inline void n306_put64(uint8_t *out, uint64_t value)
{
    n306_put32(out, (uint32_t)value);
    n306_put32(out + 4, (uint32_t)(value >> 32));
}

/* root{name, compatible} -> chosen{name, dram-base, dram-size, random-seed (v317)} -> memory-map{name, BootArgs, DeviceTree},
 * chosen -> note10-platform{name, compatible, version, gic-handoff, gic-reg, timer-intid, timebase-frequency} (v321);
 * root -> cpus{name} -> cpu0{name, device_type, reg, timebase-frequency, state=running},
 * cpu1..cpu7{name, device_type, reg, state=waiting}; root -> defaults{name} (v310, last). dram-base/dram-size are LE64; the span must be nonzero,
 * 16 KiB-aligned, non-wrapping and contain the arena. Returns the byte size, or 0 on a rejected input. */
static inline uint32_t n310_adt(uint8_t *out, const char *compatible, uint32_t count, uint64_t base,
                                const uint64_t *regs, uint32_t cpus, uint32_t frequency,
                                uint64_t dram_base, uint64_t dram_size, struct n310_offsets *offsets)
{
    uint8_t value[32];
    char name[5] = {'c', 'p', 'u', '0', 0};
    uint32_t i, at, size;

    if (!compatible || count < 2 || count > N304_COMPAT_BYTES || compatible[count - 1] ||
        !regs || cpus != N307_CPUS || !offsets)
        return 0;
    for (i = 0; i + 1 < count; ++i)
        if (compatible[i] < 33 || compatible[i] > 126)
            return 0;
    for (i = 0; i < cpus; ++i)
        if (regs[i] > 0xffffffffULL)
            return 0;
    if (!dram_size || dram_base % N304_ARENA_BYTES || dram_size % N304_ARENA_BYTES ||
        dram_base + dram_size < dram_base || dram_base > base || base + N304_ARENA_BYTES < base ||
        base + N304_ARENA_BYTES > dram_base + dram_size)
        return 0;
    size = 2592 + ((count + 3) & ~3U); /* independent of every value, so DeviceTree can carry it (v317: v316 1948, plus 36 + 256 for random-seed; v321: plus 352 for /chosen/note10-platform) */
    if (size > N307_ADT_STORAGE)
        return 0;
    for (i = 0; i < size; ++i)
        out[i] = 0;
    at = n306_node(out, 0, 2, 3);
    at = n306_prop(out, at, "name", "device-tree", 12);
    at = n306_prop(out, at, "compatible", compatible, count);
    at = n306_node(out, at, 4, 2);
    at = n306_prop(out, at, "name", "chosen", 7);
    n306_put64(value, dram_base);
    offsets->dram = at + 36;
    at = n306_prop(out, at, "dram-base", value, 8);
    n306_put64(value, dram_size);
    at = n306_prop(out, at, "dram-size", value, 8);
    for (i = 0; i < N317_SEED_BYTES; ++i) /* v317: value bytes written in place; n306_prop copies them onto themselves */
        out[at + 36 + i] = (uint8_t)(1 + i % 255);
    at = n306_prop(out, at, "random-seed", out + at + 36, N317_SEED_BYTES);
    at = n306_node(out, at, 3, 0);
    at = n306_prop(out, at, "name", "memory-map", 11);
    n306_put64(value, base);
    n306_put64(value + 8, N304_ARGS_BYTES);
    offsets->bootargs = at + 36;
    at = n306_prop(out, at, "BootArgs", value, 16);
    n306_put64(value, base + N306_ADT_OFFSET);
    n306_put64(value + 8, size);
    offsets->devtree = at + 36;
    at = n306_prop(out, at, "DeviceTree", value, 16);
    /* v321: /chosen/note10-platform (second /chosen child): timebase-frequency is the cpu0 frequency. */
    at = n306_node(out, at, 7, 0);
    at = n306_prop(out, at, "name", "note10-platform", 16);
    at = n306_prop(out, at, "compatible", "samsung,exynos9825-note10", 26);
    n306_put32(value, N321_PLATFORM_VERSION);
    at = n306_prop(out, at, "version", value, 4);
    n306_put32(value, 1);
    at = n306_prop(out, at, "gic-handoff", value, 4);
    n306_put64(value, N321_GICD_BASE);
    n306_put64(value + 8, N321_GIC_SIZE);
    n306_put64(value + 16, N321_GICC_BASE);
    n306_put64(value + 24, N321_GIC_SIZE);
    at = n306_prop(out, at, "gic-reg", value, 32);
    n306_put32(value, N321_TIMER_INTID);
    at = n306_prop(out, at, "timer-intid", value, 4);
    n306_put32(value, frequency);
    at = n306_prop(out, at, "timebase-frequency", value, 4);
    at = n306_node(out, at, 1, N307_CPUS);
    at = n306_prop(out, at, "name", "cpus", 5);
    for (i = 0; i < N307_CPUS; ++i) {
        name[3] = (char)('0' + i);
        at = n306_node(out, at, i ? 4 : 5, 0);
        at = n306_prop(out, at, "name", name, 5);
        at = n306_prop(out, at, "device_type", "cpu", 4);
        n306_put32(value, (uint32_t)regs[i]);
        if (!i)
            offsets->reg = at + 36;
        at = n306_prop(out, at, "reg", value, 4);
        if (!i) {
            n306_put32(value, frequency);
            offsets->timebase = at + 36;
            at = n306_prop(out, at, "timebase-frequency", value, 4);
        }
        at = n306_prop(out, at, "state", i ? "waiting" : "running", 8);
    }
    offsets->defaults = at;
    at = n306_node(out, at, 1, 0);
    at = n306_prop(out, at, "name", "defaults", 9);
    return at == size ? size : 0;
}

/* v311: valid loaded-image size (nonzero, 16 KiB multiple). v315: it ends inside the boot memSize (32 MiB from the image).
 * v316: the image and the handoff page that follows it end inside the boot memSize. */
static inline int n311_image_bytes_ok(uint64_t image_bytes)
{
    return image_bytes && !(image_bytes % N304_ARENA_BYTES) &&
           image_bytes <= (uint64_t)N315_BOOT_MEMSIZE - N311_KERNEL_OFFSET - N316_HANDOFF_BYTES;
}

/* v311: boot_args for the image at base + N311_KERNEL_OFFSET. v315: memSize = N315_BOOT_MEMSIZE (the bootstrap builder
 * maps memSize - kernel offset <= 32 MiB); memSizeActual stays the 256 MiB window. v316: topOfKernelData is the end of the
 * handoff page H = base + N311_KERNEL_OFFSET + image_bytes and deviceTreeP is the KVA of the ADT copy at H + N306_ADT_OFFSET
 * (KVA = virtBase + (PA - physBase)). */
static inline int n311_arguments(uint64_t base, uint32_t adt_bytes, uint32_t image_bytes, uint8_t *out)
{
    const struct n10_rt_boot_fields fields = {
        .virtual_base = N311_VIRT_BASE,
        .physical_base = base,
        .memory_size = N315_BOOT_MEMSIZE,
        .top_of_kernel = base + N311_KERNEL_OFFSET + image_bytes + N316_HANDOFF_BYTES,
        .device_tree_pointer = N311_VIRT_BASE + N311_KERNEL_OFFSET + image_bytes + N306_ADT_OFFSET,
        .device_tree_length = adt_bytes,
        .command_line = (const uint8_t *)N305_COMMAND,
        .command_length = N305_COMMAND_BYTES,
        .memory_size_actual = N311_WINDOW_BYTES,
    };

    if (!n311_image_bytes_ok(image_bytes) || base % N311_WINDOW_ALIGN || base < N311_WINDOW_MIN)
        return N10_RT_INVALID;
    return n10_rt_serialize_boot_args(&fields, out, N304_ARGS_BYTES);
}

static inline uint32_t n304_fnv(const uint8_t *bytes, uint32_t count)
{
    uint32_t value = 0x811c9dc5U;

    while (count--)
        value = (value ^ *bytes++) * 0x01000193U;
    return value;
}

/* v311: FNV-1a over little-endian 32-bit words (the stub's MMU-off image hash). */
static inline uint32_t n311_fnv_words(const uint8_t *bytes, uint32_t words)
{
    uint32_t value = 0x811c9dc5U;

    for (; words--; bytes += 4)
        value = (value ^ ((uint32_t)bytes[0] | (uint32_t)bytes[1] << 8 | (uint32_t)bytes[2] << 16 |
                          (uint32_t)bytes[3] << 24)) * 0x01000193U;
    return value;
}

static inline uint32_t n312_le32(const uint8_t *p)
{
    return (uint32_t)p[0] | (uint32_t)p[1] << 8 | (uint32_t)p[2] << 16 | (uint32_t)p[3] << 24;
}

static inline uint64_t n312_le64(const uint8_t *p)
{
    return (uint64_t)n312_le32(p) | (uint64_t)n312_le32(p + 4) << 32;
}

/* v312: bounded Mach-O load-command walk over a loaded image. Exactly one LC_UNIXTHREAD (cmdsize >= 288, flavor 6,
 * count 68); its pc must be >= N312_LINK_BASE, offset nonzero, 4-aligned and <= image_bytes - 4, and lie in exactly one
 * executable LC_SEGMENT_64. Every read is bounds-checked against 32 + sizeofcmds <= image_bytes first. Returns 0 and
 * *out = pc - N312_LINK_BASE, or -1 (no allocation, no write on failure). */
static inline int n312_entry_offset(const uint8_t *image, uint32_t image_bytes, uint32_t *out)
{
    uint32_t ncmds, i, off, size, cmd, pass, threads = 0, segments = 0;
    uint64_t end, pc = 0, entry = 0, vmaddr, vmsize;

    if (!image || !out || image_bytes < 32)
        return -1;
    ncmds = n312_le32(image + 16);
    end = 32 + (uint64_t)n312_le32(image + 20);
    if (end > image_bytes)
        return -1;
    for (pass = 0; pass < 2; ++pass) {
        for (i = 0, off = 32; i < ncmds; ++i, off += size) {
            if (off + 8ULL > end)
                return -1;
            cmd = n312_le32(image + off);
            size = n312_le32(image + off + 4);
            if (size < 8 || size % 8 || off + (uint64_t)size > end)
                return -1;
            if (!pass && cmd == N312_LC_UNIXTHREAD) {
                if (size < N312_THREAD_CMD_MIN || n312_le32(image + off + 8) != N312_THREAD_FLAVOR ||
                    n312_le32(image + off + 12) != N312_THREAD_COUNT)
                    return -1;
                pc = n312_le64(image + off + N312_THREAD_PC_OFFSET);
                ++threads;
            } else if (pass && cmd == N312_LC_SEGMENT_64) {
                if (size < N312_SEGMENT_CMD_MIN)
                    return -1;
                vmaddr = n312_le64(image + off + 24);
                vmsize = n312_le64(image + off + 32);
                if (pc >= vmaddr && pc - vmaddr < vmsize && (n312_le32(image + off + 60) & N312_VM_PROT_EXECUTE))
                    ++segments;
            }
        }
        if (!pass) {
            if (threads != 1 || pc < N312_LINK_BASE)
                return -1;
            entry = pc - N312_LINK_BASE;
            if (!entry || entry % 4 || entry > image_bytes - 4ULL)
                return -1;
        }
    }
    if (segments != 1)
        return -1;
    *out = (uint32_t)entry;
    return 0;
}
#endif
#endif
