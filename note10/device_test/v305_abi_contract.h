/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef N304_ABI_CONTRACT_H
#define N304_ABI_CONTRACT_H

#define N304_ARENA_BYTES 16384
#define N304_ARGS_BYTES 1152
#define N304_ADT_OFFSET 1152
#define N304_ADT_STORAGE 256
#define N304_ADT_MIN_BYTES 104
#define N304_ADT_MAX_BYTES 164
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
#define N304_FORMAT "N304PS20 id=%s b=%s c=%s r=0000000000000000,0000000000000000,0000000000000000,0000000000000000 a=00000000 d=00000000 n=00 q=0 s=0000000000000000 e=0 f=00000000\n"
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

#ifndef __ASSEMBLY__
#include "runtime_relocation.h"

struct n304_metadata {
    uint64_t self, record, cursor, next;
    uint32_t adt_bytes, args_hash, adt_hash, prepared;
    char text[N304_RECORD_BYTES + 1];
};

union n304_storage {
    struct {
        uint8_t args[N304_ARGS_BYTES];
        uint8_t adt[N304_ADT_STORAGE];
        struct n304_metadata meta;
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

static inline uint32_t n304_adt(uint8_t *out, const char *compatible, uint32_t count)
{
    static const char name[] = "linux-diagnostic";
    uint32_t i, size;

    if (!compatible || count < 2 || count > N304_COMPAT_BYTES || compatible[count - 1])
        return 0;
    for (i = 0; i + 1 < count; ++i)
        if (compatible[i] < 33 || compatible[i] > 126)
            return 0;
    size = 100 + ((count + 3) & ~3U);
    for (i = 0; i < size; ++i)
        out[i] = 0;
    out[0] = 2;                         /* One node, two properties, no children. */
    out[8] = 'n'; out[9] = 'a'; out[10] = 'm'; out[11] = 'e';
    out[40] = sizeof(name);
    for (i = 0; i < sizeof(name); ++i)
        out[44 + i] = name[i];
    for (i = 0; i < 10; ++i)
        out[64 + i] = "compatible"[i];
    out[96] = count;
    for (i = 0; i < count; ++i)
        out[100 + i] = compatible[i];
    return size;
}

static inline int n304_arguments(uint64_t base, uint32_t adt_bytes, uint8_t *out)
{
    const struct n10_rt_boot_fields fields = {
        .virtual_base = base,
        .physical_base = base,
        .memory_size = N304_ARENA_BYTES,
        .top_of_kernel = base + N304_ARENA_BYTES,
        .device_tree_pointer = base + N304_ADT_OFFSET,
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
