/* SPDX-License-Identifier: GPL-2.0-only */
/* One observation only. No CPU/control/cache/PM writes or FDT access. */
#define N10_AFFINITY_CAPACITY 32U
struct n10_affinity_sample {
    unsigned int cpu, seen;
    u64 logical_map, mpidr, cntfrq;
};
static struct n10_affinity_sample n10_affinity_samples[N10_AFFINITY_CAPACITY];

static void n10_affinity_sample_cpu(void *unused)
{
    unsigned int cpu = smp_processor_id();
    struct n10_affinity_sample *sample;
    (void)unused;
    if (cpu >= N10_AFFINITY_CAPACITY)
        return;
    sample = &n10_affinity_samples[cpu];
    sample->cpu = cpu;
    sample->logical_map = READ_ONCE(cpu_logical_map(cpu));
    sample->mpidr = read_sysreg(mpidr_el1);
    sample->cntfrq = read_sysreg(cntfrq_el0);
    ++sample->seen;
}

static void n10_affinity_emit(const char *body)
{
    pr_info("N10AFF1 %s checksum=%08x\n", body,
            n10_frame_checksum(body, strlen(body)));
}

static int n10_affinity_init(void)
{
    unsigned int cpu, count = 0, observed = 0;
    u32 online = 0, seen = 0;
    int status = 0;
    char frame[384];
    const char *cycle = n10_cycle_valid() ? (const char *)n10_cycle :
                        "00000000000000000000000000000000";
    memset(n10_affinity_samples, 0, sizeof(n10_affinity_samples));
    /* Process context only. Synchronous IPI/lock acquisition has no hard timeout.
     * Recovery retains its independent queue; no new actuator is introduced. */
    cpus_read_lock();
    for_each_online_cpu(cpu) {
        if (cpu >= N10_AFFINITY_CAPACITY) {
            status = -ERANGE;
            goto unlock;
        }
        online |= 1U << cpu;
        ++count;
    }
    if (!count) {
        status = -ENODEV;
        goto unlock;
    }
    on_each_cpu(n10_affinity_sample_cpu, NULL, 1);
    for (cpu = 0; cpu < N10_AFFINITY_CAPACITY; ++cpu) {
        struct n10_affinity_sample *sample = &n10_affinity_samples[cpu];
        if (!(online & (1U << cpu))) {
            if (sample->seen)
                status = -EINVAL;
            continue;
        }
        if (sample->seen != 1 || sample->cpu != cpu ||
            sample->logical_map == INVALID_HWID || !sample->cntfrq ||
            sample->cntfrq > 0xffffffffULL) {
            status = -EINVAL;
            continue;
        }
        seen |= 1U << cpu;
        ++observed;
    }
unlock:
    cpus_read_unlock();
    /* Formatting/logging only after unlock, never inside an IPI callback. */
    scnprintf(frame, sizeof(frame),
        "id=%s cycle=%s kind=begin online=%08x count=%u capacity=32 fdt=unavailable raw_binding=0 status=%d",
        N10_RESERVE_BUILD_ID, cycle, online, count, status);
    n10_affinity_emit(frame);
    for (cpu = 0; cpu < N10_AFFINITY_CAPACITY; ++cpu) {
        struct n10_affinity_sample *sample = &n10_affinity_samples[cpu];
        if (!(seen & (1U << cpu)))
            continue;
        scnprintf(frame, sizeof(frame),
            "id=%s cycle=%s kind=row cpu=%u map=%016llx mpidr=%016llx cntfrq=%llx equal=%u",
            N10_RESERVE_BUILD_ID, cycle, cpu,
            (unsigned long long)sample->logical_map,
            (unsigned long long)sample->mpidr,
            (unsigned long long)sample->cntfrq,
            (unsigned int)(sample->logical_map == (sample->mpidr & MPIDR_HWID_BITMASK)));
        n10_affinity_emit(frame);
    }
    scnprintf(frame, sizeof(frame),
        "id=%s cycle=%s kind=end online=%08x seen=%08x count=%u status=%d fdt=unavailable raw_binding=0",
        N10_RESERVE_BUILD_ID, cycle, online, seen, observed, status);
    n10_affinity_emit(frame);
    return 0;
}
