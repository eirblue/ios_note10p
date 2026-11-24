/* SPDX-License-Identifier: GPL-2.0-only */
/* v345 host fixture (new cases only): the N345PS20 kernel and host record format tags with the unchanged 250-byte record,
 * the N345PS2T validator with the unchanged N315 crumbs (an N344PS2T record is rejected), the v345 64 MiB window with
 * the v344 4 GiB limit (the last accepted base is 0xfc000000, 0xfe000000 is refused; the handoff page below 4 GiB:
 * n311_arguments and n310_adt refuse otherwise), memSizeActual = 64 MiB, and the v343 contract kept unchanged: n310_adt
 * with the memory-map TrustCache property {H - 0x11000, 68512} (RAMDisk dropped, nProps 4) and the /chosen/note10-ufs,
 * note10-wdt nodes (size 3076 + align4(compatible)) accepted by n10_rt_validate_adt, the refusal of a base below the
 * TrustCache offset, the S0 record read at H - 0x14000 and its refusals, and the boot_args CommandLine
 * "-v n10diag=305 rd=n10ufs0 n10wdt_deadline=120". Synthetic values only: synthetic window base, image size, DRAM span,
 * cpu regs, record fields and a synthetic S0 record (LBA range, WTDAT); no real kernel bytes, entry, address, register,
 * partition or watchdog value. */
#include <stdint.h>
#include <stdio.h>
/* Synthetic S0 record standing in for the private loader image tail; n310_adt reads it through N343_S0_RECORD_AT. */
static uint8_t s0_record[32];
static uint64_t s0_record_pa;
static const uint8_t *s0_record_at(uint64_t pa)
{
    s0_record_pa = pa;
    return s0_record;
}
#define N343_S0_RECORD_AT(pa) s0_record_at(pa)
#include "v345_abi_contract.h"
#include "v345_host_record_validate.h"

#define BASE 0x90000000ULL           /* synthetic 32 MiB-aligned window base >= 2 GiB */
#define MPIDR 0x81000010ULL          /* synthetic raw MPIDR: affinity 0x10 */
#define ADT_NODES 16U
#define ADT_FNV 0xc1cb3618U          /* synthetic record field */
#define ARGS_FNV 0xaee810a3U         /* synthetic record field */
#define IMAGE_FNV 0x4e154d31U        /* synthetic image word-FNV (record field) */
#define IMAGE_TICKS 0x1234U          /* synthetic MMU-off hash ticks */
#define ENTRY 0x4010U                /* synthetic entry offset */
#define ENTRY_WORD 0x14000001U       /* synthetic 'b .+4' at the entry */
#define FIXTURE_GROUPS 3
#define FIXTURE_VARIANTS 9
#define EXPECTED_CHECKS 9
#define SYN_IMAGE_BYTES 0x100000U    /* synthetic loaded-image size (16 KiB multiple) */
#define SYN_FREQUENCY 26000000U      /* synthetic cpu0 timebase frequency */
#define BUILD_ID "11111111111111111111111111111111"
#define BOOT_ID "22222222222222222222222222222222"
#define ATTEMPT_ID "33333333333333333333333333333333"

static int checks;

#define CHECK(condition)                                                  \
    do {                                                                  \
        if (!(condition)) {                                               \
            fprintf(stderr, "v345 fixture failed at line %d\n", __LINE__); \
            return 1;                                                     \
        }                                                                 \
        ++checks;                                                         \
    } while (0)

static void put_hex(char *field, size_t digits, uint64_t value)
{
    static const char hex[] = "0123456789abcdef";

    while (digits) {
        field[--digits] = hex[value & 15];
        value >>= 4;
    }
}

static uint64_t get64(const uint8_t *in)
{
    uint64_t value = 0;

    for (int i = 7; i >= 0; --i)
        value = value << 8 | in[i];
    return value;
}

/* Synthetic S0 record: magic, version, first, last, WTDAT, FNV-1a of bytes [0, 28) xor flip (flip != 0 = bad check). */
static void make_s0(uint32_t magic, uint32_t version, uint64_t first, uint64_t last, uint32_t wtdat, uint32_t flip)
{
    const uint64_t fields[5] = {magic, version, first, last, wtdat};
    const int widths[5] = {4, 4, 8, 8, 4};
    uint32_t check;
    int at = 0;

    for (int f = 0; f < 5; ++f)
        for (int i = 0; i < widths[f]; ++i)
            s0_record[at++] = (uint8_t)(fields[f] >> 8 * i);
    check = n304_fnv(s0_record, N343_S0_CHECK_OFFSET) ^ flip;
    for (int i = 0; i < 4; ++i)
        s0_record[N343_S0_CHECK_OFFSET + i] = (uint8_t)(check >> 8 * i);
}

static int memmem_absent(const uint8_t *raw, uint32_t size, const char *needle)
{
    size_t length = strlen(needle);

    for (uint32_t i = 0; i + length <= size; ++i)
        if (!memcmp(raw + i, needle, length))
            return 0;
    return 1;
}

static void make_record(char *record, const char *tag)
{
    char text[N304_HOST_RECORD_BYTES + 1];

    snprintf(text, sizeof(text), N304_HOST_FORMAT, BUILD_ID, BOOT_ID, ATTEMPT_ID);
    memcpy(record, text, N304_HOST_RECORD_BYTES);
    memcpy(record, tag, 7);
    put_hex(record + N304_HOST_REG_OFFSET, 16, BASE);
    put_hex(record + N304_HOST_REG_OFFSET + N304_HOST_REG_STRIDE, 16, MPIDR);
    put_hex(record + N304_HOST_REG_OFFSET + 2 * N304_HOST_REG_STRIDE, 16, (uint64_t)IMAGE_TICKS << 32 | IMAGE_FNV);
    put_hex(record + N304_HOST_REG_OFFSET + 3 * N304_HOST_REG_STRIDE, 16, (uint64_t)ENTRY << 32 | ENTRY_WORD);
    put_hex(record + N304_HOST_ARGS_HASH_OFFSET, 8, ARGS_FNV);
    put_hex(record + N304_HOST_ADT_HASH_OFFSET, 8, ADT_FNV);
    put_hex(record + N304_HOST_ADT_LENGTH_OFFSET, 2, ADT_NODES);
    put_hex(record + N304_HOST_SCTLR_OFFSET, 16, 0x30d00800);
    record[N304_HOST_EL_OFFSET] = '1';
    record[N304_HOST_DAIF_OFFSET] = 'f';
    record[N304_HOST_COMMIT_OFFSET] = N304_HOST_COMMITTED;
    put_hex(record + N304_HOST_CSUM_OFFSET, 8, n306_host_body_checksum(record));
}

int main(void)
{
    char text[N304_RECORD_BYTES + 1], host[N304_HOST_RECORD_BYTES + 1];
    char record[N304_HOST_RECORD_BYTES], altered[N304_HOST_RECORD_BYTES];
    static const char crumbs[] = "N315E1-\nN315B20\nN315M3-\n[0:";
    struct n306_host_record_expected expected = {.x0 = BASE, .mpidr_aff = 0x10, .args_hash = ARGS_FNV,
                                                 .adt_hash = ADT_FNV, .adt_nodes = ADT_NODES, .image_hash = IMAGE_FNV,
                                                 .entry_offset = ENTRY, .entry_word = ENTRY_WORD};
    int code = -2;
    static uint8_t adt[N307_ADT_STORAGE], args[N304_ARGS_BYTES];
    static const char compatible[] = "synthetic,note10-test";
    static const uint64_t regs[N307_CPUS] = {0, 1, 2, 3, 0x100, 0x101, 0x200, 0x201};
    const uint64_t handoff = BASE + N311_KERNEL_OFFSET + SYN_IMAGE_BYTES;
    struct n310_offsets offsets;
    uint32_t size, map, trust, ufs, wdt;

    /* Group 1: kernel and host record format tags N345PS20; the record length stays 250. */
    CHECK(snprintf(text, sizeof(text), N304_FORMAT, BUILD_ID, BOOT_ID, ATTEMPT_ID) == N304_RECORD_BYTES &&
          N304_RECORD_BYTES == 250 && !memcmp(text, "N345PS20", 8));
    CHECK(snprintf(host, sizeof(host), N304_HOST_FORMAT, BUILD_ID, BOOT_ID, ATTEMPT_ID) == N304_HOST_RECORD_BYTES &&
          N304_HOST_RECORD_BYTES == 250 && !memcmp(host, "N345PS20", 8) && !memcmp(text, host, sizeof(host)));

    /* Group 2: N345PS2T validator with the unchanged N315 crumbs; an N344PS2T record is not a v345 witness. */
    memcpy(expected.build, BUILD_ID, sizeof(expected.build));
    memcpy(expected.boot, BOOT_ID, sizeof(expected.boot));
    memcpy(expected.attempt, ATTEMPT_ID, sizeof(expected.attempt));
    make_record(record, "N345PS2");
    CHECK(n306_host_record_valid(record, sizeof(record), &expected) &&
          n315_crumb_trace(crumbs, sizeof(crumbs) - 1, &code) == 7 && code == 0);
    make_record(altered, "N344PS2");
    CHECK(!n306_host_record_valid(altered, sizeof(altered), &expected));

    /* Group 3: v343 contract. memory-map{name, BootArgs, DeviceTree, TrustCache} with TrustCache = {H - 0x11000, 68512}
     * right after DeviceTree, then note10-platform (352 bytes), note10-ufs (6 props, 284 bytes) and note10-wdt (3 props,
     * 148 bytes) before cpus; the ADT size is 3076 + align4(compatible) and the walk validator accepts it; a base below the
     * TrustCache offset is refused; the boot_args CommandLine is the 45-byte v343 line and topOfKernelData = H + 16 KiB.
     * partition-lba/armed-wtdat come from the S0 record read at H - 0x14000. */
    make_s0(N343_S0_MAGIC, N343_S0_VERSION, 0x1000, 0x3fffff, 0x1234, 0);
    size = n310_adt(adt, compatible, sizeof(compatible), handoff, regs, N307_CPUS, SYN_FREQUENCY,
                    0x80000000ULL, 0x400000000ULL, &offsets);
    map = offsets.bootargs - 36 - 48 - 8; /* memory-map node header: before its 48-byte name property */
    trust = offsets.devtree + 16;         /* TrustCache property right after the DeviceTree value */
    ufs = trust + 52 + 352;               /* after the TrustCache property and the note10-platform node */
    wdt = ufs + 284;
    CHECK(size == 3076 + ((sizeof(compatible) + 3) & ~3U) && s0_record_pa == handoff - 0x14000 &&
          n10_rt_validate_adt(adt, size) == N10_RT_OK &&
          get64(adt + map) == 4 && !memcmp(adt + map + 8, "name", 5) && !memcmp(adt + map + 44, "memory-map", 11) &&
          get64(adt + offsets.devtree) == handoff + N306_ADT_OFFSET && get64(adt + offsets.devtree + 8) == size &&
          !memcmp(adt + trust, "TrustCache\0", 11) && adt[trust + 32] == 16 && !adt[trust + 33] &&
          get64(adt + trust + 36) == handoff - 0x11000 && get64(adt + trust + 44) == 68512 &&
          get64(adt + trust + 52) == 7 && memmem_absent(adt, size, "RAMDisk"));
    CHECK(get64(adt + ufs) == 6 && !memcmp(adt + ufs + 44, "note10-ufs", 11) &&
          !memcmp(adt + ufs + 56, "hci-reg", 8) && get64(adt + ufs + 92) == 0x13d60000 && get64(adt + ufs + 100) == 0x200 &&
          !memcmp(adt + ufs + 108, "nexus-reg", 10) && get64(adt + ufs + 144) == 0x13d61140 &&
          !memcmp(adt + ufs + 152, "prdt-entry-size", 16) && adt[ufs + 188] == 128 &&
          !memcmp(adt + ufs + 192, "prdt-length-bias", 17) && adt[ufs + 228] == 16 &&
          !memcmp(adt + ufs + 232, "partition-lba", 14) && get64(adt + ufs + 268) == 0x1000 &&
          get64(adt + ufs + 276) == 0x3fffff &&
          get64(adt + wdt) == 3 && !memcmp(adt + wdt + 44, "note10-wdt", 11) &&
          !memcmp(adt + wdt + 56, "reg", 4) && get64(adt + wdt + 92) == 0x10050000 && get64(adt + wdt + 100) == 0x10 &&
          !memcmp(adt + wdt + 108, "armed-wtdat", 12) && get64(adt + wdt + 144) == (0x1234ULL | 1ULL << 32) &&
          !memcmp(adt + wdt + 148 + 44, "cpus", 5) &&
          n310_adt(adt, compatible, sizeof(compatible), 0x8000, regs, N307_CPUS, SYN_FREQUENCY, 0, 0x400000000ULL,
                   &offsets) == 0);
    CHECK(n311_arguments(BASE, size, SYN_IMAGE_BYTES, args) == N10_RT_OK && N305_COMMAND_BYTES == 45 &&
          get64(args + 1144) == 0x4000000 && /* v345: memSizeActual = the 64 MiB window */
          !memcmp(args + N305_CMDLINE, "-v n10diag=305 rd=n10ufs0 n10wdt_deadline=120", N305_COMMAND_BYTES + 1) &&
          get64(args + N305_TOP) == handoff + N316_HANDOFF_BYTES &&
          get64(args + N305_TOP) - (handoff - 0x11000) == 0x15000);
    /* S0 record refusals (bad magic, version, check; zero, inverted, > 32-bit LBA; WTDAT > 16 bits); WTDAT 0 accepted. */
#define ADT_WITH(magic, version, first, last, wtdat, flip)                                          \
    (make_s0(magic, version, first, last, wtdat, flip),                                           \
     n310_adt(adt, compatible, sizeof(compatible), handoff, regs, N307_CPUS, SYN_FREQUENCY, 0x80000000ULL, \
              0x400000000ULL, &offsets))
    CHECK(!ADT_WITH(N343_S0_MAGIC ^ 1, N343_S0_VERSION, 0x1000, 0x3fffff, 0x1234, 0) &&
          !ADT_WITH(N343_S0_MAGIC, N343_S0_VERSION + 1, 0x1000, 0x3fffff, 0x1234, 0) &&
          !ADT_WITH(N343_S0_MAGIC, N343_S0_VERSION, 0x1000, 0x3fffff, 0x1234, 1) &&
          !ADT_WITH(N343_S0_MAGIC, N343_S0_VERSION, 0, 0x3fffff, 0x1234, 0) &&
          !ADT_WITH(N343_S0_MAGIC, N343_S0_VERSION, 0x2000, 0x1000, 0x1234, 0) &&
          !ADT_WITH(N343_S0_MAGIC, N343_S0_VERSION, 0x1000, 0x100000000ULL, 0x1234, 0) &&
          !ADT_WITH(N343_S0_MAGIC, N343_S0_VERSION, 0x1000, 0x3fffff, 0x10000, 0) &&
          ADT_WITH(N343_S0_MAGIC, N343_S0_VERSION, 0x1000, 0x1000, 0, 0) == size &&
          get64(adt + ufs + 268) == 0x1000 && get64(adt + ufs + 276) == 0x1000 &&
          get64(adt + wdt + 144) == 1ULL << 32);
    /* v345 64 MiB window under the v344 limit: base 0xfc000000 (window ending exactly at 4 GiB) is accepted, 0xfe000000
     * (ending above it) and 4 GiB are refused by n311_arguments; n310_adt accepts the last handoff page below 4 GiB and
     * refuses one at 4 GiB. */
    make_s0(N343_S0_MAGIC, N343_S0_VERSION, 0x1000, 0x3fffff, 0x1234, 0);
    CHECK(N344_WINDOW_LIMIT == 0x100000000ULL && N311_WINDOW_BYTES == 0x4000000 &&
          n311_arguments(0xfc000000ULL, size, SYN_IMAGE_BYTES, args) == N10_RT_OK &&
          n311_arguments(0xfe000000ULL, size, SYN_IMAGE_BYTES, args) != N10_RT_OK &&
          n311_arguments(0x100000000ULL, size, SYN_IMAGE_BYTES, args) != N10_RT_OK &&
          n310_adt(adt, compatible, sizeof(compatible), 0xffffc000ULL, regs, N307_CPUS, SYN_FREQUENCY, 0x80000000ULL,
                   0x400000000ULL, &offsets) == size &&
          n310_adt(adt, compatible, sizeof(compatible), 0x100000000ULL, regs, N307_CPUS, SYN_FREQUENCY, 0x80000000ULL,
                   0x400000000ULL, &offsets) == 0);

    if (checks != EXPECTED_CHECKS || FIXTURE_VARIANTS != EXPECTED_CHECKS || FIXTURE_GROUPS != 3) {
        fprintf(stderr, "v345 fixture check count %d\n", checks);
        return 1;
    }
    puts("v345 tag fixture PASS");
    return 0;
}
