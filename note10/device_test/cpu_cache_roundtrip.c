/* SPDX-License-Identifier: GPL-2.0-only */
/* Opt-in Linux CPU offline/online and cached-payload coherence diagnostic.
 * Runs only after successful reservation, RAM test and XNU data staging.
 * Does not stop DMA, disable caches/MMU, touch GIC or branch to XNU.
 */
#include <linux/cpu.h>
#include <linux/cpumask.h>
#include <asm/cacheflush.h>
#include <asm/barrier.h>
#include <asm/sysreg.h>

struct n10_cpu_sample {
    u64 el, mpidr, sctlr, tcr, ttbr1, mair, cntkctl, cntfrq, words, fingerprint;
    unsigned int seen;
};
static struct n10_cpu_sample n10_cpu_samples[8];

static void n10_cpu_checkpoint(unsigned int phase, u64 online)
{
    unsigned int sequence;
    char frame[128];
    for (sequence = 0; sequence < 2; ++sequence) {
        int count = scnprintf(frame, sizeof(frame), "id=%s phase=%u online=%llx seq=%u",
            N10_RESERVE_BUILD_ID, phase, (unsigned long long)online, sequence);
        pr_info("N10HOP1 %s checksum=%08x\n", frame, n10_frame_checksum(frame, count));
    }
}

static u64 n10_online_bits(void)
{
    unsigned int cpu;
    u64 bits = 0;
    for_each_online_cpu(cpu) {
        if (cpu >= 8)
            return ~0ULL;
        bits |= 1ULL << cpu;
    }
    return bits;
}

/* Supplementary full-word read check; SHA256 remains the payload identity. */
static u64 n10_word_fingerprint(const u64 *memory, size_t words)
{
    size_t i;
    u64 value = 14695981039346656037ULL;
    for (i = 0; i < words; ++i)
        value = (value ^ READ_ONCE(memory[i])) * 1099511628211ULL;
    return value;
}

static void n10_sample_cpu(void *memory)
{
    unsigned int cpu = smp_processor_id();
    struct n10_cpu_sample *sample;
    if (cpu >= 8)
        return;
    sample = &n10_cpu_samples[cpu];
    sample->el = read_sysreg(CurrentEL);
    sample->mpidr = read_sysreg(mpidr_el1);
    sample->sctlr = read_sysreg(sctlr_el1);
    sample->tcr = read_sysreg(tcr_el1);
    sample->ttbr1 = read_sysreg(ttbr1_el1);
    sample->mair = read_sysreg(mair_el1);
    sample->cntkctl = read_sysreg(cntkctl_el1);
    sample->cntfrq = read_sysreg(cntfrq_el0);
    sample->words = N10_XNU_PAYLOAD_SIZE / sizeof(u64);
    sample->fingerprint = n10_word_fingerprint(memory, sample->words);
    ++sample->seen;
}

static unsigned int n10_test_cpu_cache(void)
{
    const size_t length = N10_XNU_PAYLOAD_SIZE;
    const size_t words = N10_XNU_PAYLOAD_SIZE / sizeof(u64);
    u8 expected[32] = N10_XNU_PAYLOAD_SHA256_BYTES;
    u8 digest[32];
    u8 *memory = phys_to_virt(n10_window_base);
    u64 before = 0, stopped = 0, restored = 0, fingerprint = 0;
    unsigned int status = 1, sequence, cpu, clean = 0, sampled = 0;
    bool freeze_attempted = false;
    int result, i;
    char frame[512], hash[65];

    if (n10_window_status != 1 || !n10_window_base ||
        (n10_window_base & (N10_WINDOW_ALIGN - 1)) ||
        n10_window_base > N10_WINDOW_LIMIT - N10_WINDOW_SIZE ||
        !length || length > N10_WINDOW_SIZE || length % PAGE_SIZE ||
        !virt_addr_valid(memory) || !virt_addr_valid(memory + length - 1) ||
        virt_to_phys(memory) != n10_window_base ||
        virt_to_phys(memory + length - 1) != n10_window_base + length - 1)
        goto report;
    before = n10_online_bits();
    status = 2;
    if (before != 0xff)
        goto report;
    status = 3;
    result = n10_sha256(memory, length, digest);
    if (result || memcmp(digest, expected, sizeof(expected)))
        goto report;
    fingerprint = n10_word_fingerprint((u64 *)memory, words);

    /* Pinned kernel requires enable_nonboot_cpus even after freeze failure. */
    n10_cpu_checkpoint(1, before);
    freeze_attempted = true;
    result = disable_nonboot_cpus();
    stopped = n10_online_bits();
    n10_cpu_checkpoint(2, stopped);
    status = 4;
    if (result)
        goto restore;
    status = 5;
    if (stopped != 1)
        goto restore;
    __flush_dcache_area(memory, length);
    dsb(sy);
    clean = 1;
    n10_cpu_checkpoint(3, stopped);
    status = 6;
    result = n10_sha256(memory, length, digest);
    if (result || memcmp(digest, expected, sizeof(expected)))
        goto restore;
    status = 0;
restore:
    if (freeze_attempted) {
        enable_nonboot_cpus();
        freeze_attempted = false;
    }
    restored = n10_online_bits();
    n10_cpu_checkpoint(4, restored);
    if (restored != before)
        status = 7;
    if (status)
        goto report;
    memset(n10_cpu_samples, 0, sizeof(n10_cpu_samples));
    /* Keep the restored online set stable while synchronous callbacks run. */
    cpus_read_lock();
    if (n10_online_bits() != before) {
        cpus_read_unlock();
        status = 7;
        goto report;
    }
    on_each_cpu(n10_sample_cpu, memory, 1);
    cpus_read_unlock();
    n10_cpu_checkpoint(5, n10_online_bits());
    for (cpu = 0; cpu < 8; ++cpu) {
        struct n10_cpu_sample *sample = &n10_cpu_samples[cpu];
        if (sample->seen != 1 || sample->words != words ||
            sample->fingerprint != fingerprint || sample->el != 4 ||
            sample->cntfrq != 26000000 || (sample->sctlr & 0x1005) != 0x1005)
            status = 8;
        else
            ++sampled;
    }
    if (status)
        goto report;
    result = n10_sha256(memory, length, digest);
    if (result || memcmp(digest, expected, sizeof(expected)))
        status = 9;
report:
    for (i = 0; i < sizeof(digest); ++i)
        snprintf(hash + 2 * i, 3, "%02x", status ? 0 : digest[i]);
    hash[64] = '\0';
    for (sequence = 0; sequence < 32; ++sequence) {
        int count = scnprintf(frame, sizeof(frame),
            "id=%s seq=%u before=%llx stopped=%llx restored=%llx cpus=%u words=%llu fnv=%llx sha256=%s clean=%u status=%u",
            N10_RESERVE_BUILD_ID, sequence, (unsigned long long)before,
            (unsigned long long)stopped, (unsigned long long)restored, sampled,
            (unsigned long long)words, (unsigned long long)fingerprint, hash, clean, status);
        pr_info("N10QUI1 %s checksum=%08x\n", frame, n10_frame_checksum(frame, count));
    }
    if (status)
        return status;
    for (sequence = 0; sequence < 32; ++sequence) {
        for (cpu = 0; cpu < 8; ++cpu) {
            struct n10_cpu_sample *sample = &n10_cpu_samples[cpu];
            int count = scnprintf(frame, sizeof(frame),
                "id=%s seq=%u cpu=%u el=%llx mpidr=%llx sctlr=%llx tcr=%llx ttbr1=%llx mair=%llx cntkctl=%llx cntfrq=%llx words=%llu fnv=%llx",
                N10_RESERVE_BUILD_ID, sequence, cpu,
                (unsigned long long)sample->el, (unsigned long long)sample->mpidr,
                (unsigned long long)sample->sctlr, (unsigned long long)sample->tcr,
                (unsigned long long)sample->ttbr1, (unsigned long long)sample->mair,
                (unsigned long long)sample->cntkctl, (unsigned long long)sample->cntfrq,
                (unsigned long long)sample->words, (unsigned long long)sample->fingerprint);
            pr_info("N10CPU2 %s checksum=%08x\n", frame, n10_frame_checksum(frame, count));
        }
    }
    return 0;
}
