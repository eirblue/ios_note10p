/* SPDX-License-Identifier: GPL-2.0-only */
/* Read-only observations after the owned PM and GIC tests have completed. */
struct n10_post_arch_sample {
    u64 el, mpidr, sctlr, tcr, ttbr1, mair, words, fingerprint;
    unsigned int seen;
};
static struct n10_post_arch_sample n10_post_arch[8];
static unsigned int n10_post_arch_bad;

static void n10_post_arch_cpu(void *memory)
{
    unsigned int cpu = smp_processor_id();
    struct n10_post_arch_sample *s;
    if (cpu >= 8) {
        WRITE_ONCE(n10_post_arch_bad, 1);
        return;
    }
    s = &n10_post_arch[cpu];
    ++s->seen;
    s->el = read_sysreg(CurrentEL);
    s->mpidr = read_sysreg(mpidr_el1);
    s->sctlr = read_sysreg(sctlr_el1);
    s->tcr = read_sysreg(tcr_el1);
    s->ttbr1 = read_sysreg(ttbr1_el1);
    s->mair = read_sysreg(mair_el1);
    s->words = N10_XNU_PAYLOAD_SIZE / sizeof(u64);
    s->fingerprint = n10_word_fingerprint(memory, s->words);
}

static int n10_report_post_arch(void *memory, unsigned int generation)
{
    unsigned int cpu, copy, status = !generation, bad;
    char frame[512];
    memset(n10_post_arch, 0, sizeof(n10_post_arch));
    WRITE_ONCE(n10_post_arch_bad, 0);
    if (!status) {
        cpus_read_lock();
        if (n10_online_bits() != 255 || num_online_cpus() != 8)
            status = 1;
        else {
            on_each_cpu(n10_post_arch_cpu, memory, 1);
            if (n10_online_bits() != 255 || num_online_cpus() != 8)
                status = 1;
        }
        cpus_read_unlock();
    }
    bad = READ_ONCE(n10_post_arch_bad);
    for (cpu = 0; cpu < 8; ++cpu) {
        struct n10_cpu_sample *b = &n10_cpu_samples[cpu];
        struct n10_post_arch_sample *s = &n10_post_arch[cpu];
        if (bad || b->seen != 1 || s->seen != 1 || s->el != 4 ||
            (s->sctlr & 0x1005) != 0x1005 || s->el != b->el ||
            s->mpidr != b->mpidr || s->sctlr != b->sctlr ||
            s->tcr != b->tcr || s->mair != b->mair ||
            ((s->ttbr1 ^ b->ttbr1) & 0x0000ffffffffffffULL) ||
            !s->words || s->words != b->words ||
            s->words != N10_XNU_PAYLOAD_SIZE / sizeof(u64) ||
            s->fingerprint != b->fingerprint)
            status = 1;
    }
    for (copy = 0; copy < 4; ++copy) {
        for (cpu = 0; cpu < 8; ++cpu) {
            struct n10_cpu_sample *b = &n10_cpu_samples[cpu];
            struct n10_post_arch_sample *s = &n10_post_arch[cpu];
            int count = scnprintf(frame, sizeof(frame),
                "id=%s seq=%u generation=%u cpu=%u pre_seen=%x seen=%x el=%llx mpidr=%llx sctlr=%llx tcr=%llx ttbr1=%llx mair=%llx status=%u",
                N10_RESERVE_BUILD_ID, copy, generation, cpu, b->seen, s->seen,
                (unsigned long long)s->el, (unsigned long long)s->mpidr,
                (unsigned long long)s->sctlr, (unsigned long long)s->tcr,
                (unsigned long long)s->ttbr1, (unsigned long long)s->mair, status);
            pr_info("N10PAR1 %s checksum=%08x\n", frame, n10_frame_checksum(frame, count));
            count = scnprintf(frame, sizeof(frame),
                "id=%s seq=%u generation=%u cpu=%u pre_seen=%x seen=%x words=%llu fnv=%llx status=%u",
                N10_RESERVE_BUILD_ID, copy, generation, cpu, b->seen, s->seen,
                (unsigned long long)s->words, (unsigned long long)s->fingerprint, status);
            pr_info("N10PCL1 %s checksum=%08x\n", frame, n10_frame_checksum(frame, count));
        }
    }
    return status ? -EIO : 0;
}
