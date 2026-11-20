/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef N304_ABI_CONTRACT_H
#define N304_ABI_CONTRACT_H

#define N304_ARENA_BYTES 16384
#define N304_ARGS_BYTES 1152
/* v306: multi-node ADT at a new arena offset; [1152,1408) stays zero. */
#define N306_ADT_OFFSET 2048
#define N307_ADT_STORAGE 2048
#define N306_ADT_MIN_BYTES 108
#define N307_ADT_MAX_BYTES 2048 /* v307 record n= is the walked node count */
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
#define N304_FORMAT "N307PS20 id=%s b=%s c=%s r=0000000000000000,0000000000000000,0000000000000000,0000000000000000 a=00000000 d=00000000 n=00 q=0 s=0000000000000000 e=0 f=00000000\n"
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

#ifndef __ASSEMBLY__
#include "runtime_relocation.h"

struct n304_metadata {
    uint64_t self, record, cursor, next;
    uint32_t adt_bytes, args_hash, adt_hash, prepared;
    char text[N304_RECORD_BYTES + 1];
    uint32_t cpu_reg_offset, timebase_offset; /* relative to the ADT start */
    uint32_t bootargs_map_offset, devtree_map_offset; /* memory-map values, ADT-relative */
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

static inline int n304_owned_span(uint64_t start, uint64_t end, uint64_t base)
{
    return base && !(base % N304_ARENA_BYTES) && start <= base && base <= end &&
           N304_ARENA_BYTES <= end - base &&
           base <= N10_RT_LIMIT - N304_ARENA_BYTES;
}

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

struct n307_offsets {
    uint32_t reg, timebase, bootargs, devtree;
};

static inline void n306_put64(uint8_t *out, uint64_t value)
{
    n306_put32(out, (uint32_t)value);
    n306_put32(out + 4, (uint32_t)(value >> 32));
}

/* root{name, compatible} -> chosen{name} -> memory-map{name, BootArgs, DeviceTree};
 * root -> cpus{name} -> cpu0{name, device_type, reg, timebase-frequency, state=running},
 * cpu1..cpu7{name, device_type, reg, state=waiting}. Returns the byte size, or 0 on a rejected input. */
static inline uint32_t n307_adt(uint8_t *out, const char *compatible, uint32_t count, uint64_t base,
                                const uint64_t *regs, uint32_t cpus, uint32_t frequency,
                                struct n307_offsets *offsets)
{
    uint8_t value[16];
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
    size = 1804 + ((count + 3) & ~3U); /* independent of every value, so DeviceTree can carry it */
    if (size > N307_ADT_STORAGE)
        return 0;
    for (i = 0; i < size; ++i)
        out[i] = 0;
    at = n306_node(out, 0, 2, 2);
    at = n306_prop(out, at, "name", "device-tree", 12);
    at = n306_prop(out, at, "compatible", compatible, count);
    at = n306_node(out, at, 1, 1);
    at = n306_prop(out, at, "name", "chosen", 7);
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
    return at == size ? size : 0;
}

static inline int n304_arguments(uint64_t base, uint32_t adt_bytes, uint8_t *out)
{
    const struct n10_rt_boot_fields fields = {
        .virtual_base = base,
        .physical_base = base,
        .memory_size = N304_ARENA_BYTES,
        .top_of_kernel = base + N304_ARENA_BYTES,
        .device_tree_pointer = base + N306_ADT_OFFSET,
        .device_tree_length = adt_bytes,
        .command_line = (const uint8_t *)N305_COMMAND,
        .command_length = N305_COMMAND_BYTES,
        .memory_size_actual = N304_ARENA_BYTES,
    };

    return n10_rt_serialize_boot_args(&fields, out, N304_ARGS_BYTES);
}

static inline uint32_t n304_fnv(const uint8_t *bytes, uint32_t count)
{
    uint32_t value = 0x811c9dc5U;

    while (count--)
        value = (value ^ *bytes++) * 0x01000193U;
    return value;
}
#endif
#endif
