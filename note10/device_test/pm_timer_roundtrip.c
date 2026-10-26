/* SPDX-License-Identifier: GPL-2.0-only */
/* Deferred devices-only PM test and per-CPU event-stream register roundtrip.
 * No low-level sleep, MMU/cache shutdown, GIC handoff or XNU branch.
 */
#include <linux/workqueue.h>
#include <linux/jiffies.h>
#include <linux/uts.h>
#include <linux/note10_pm_contract.h>

struct n10_timer_sample { u64 before, cleared, restored, frequency; unsigned int seen; };
static struct n10_timer_sample n10_timers[8];
static unsigned int n10_pm_retries, n10_pm_attempts;
static bool n10_timer_done;
static void n10_pm_worker(struct work_struct *unused);
static DECLARE_DELAYED_WORK(n10_pm_work, n10_pm_worker);

static void n10_timer_cpu(void *unused)
{
    unsigned int cpu = smp_processor_id();
    struct n10_timer_sample *sample;
    (void)unused;
    if (cpu >= 8)
        return;
    sample = &n10_timers[cpu];
    sample->before = read_sysreg(cntkctl_el1);
    write_sysreg(sample->before & ~0xf0ULL, cntkctl_el1);
    isb();
    sample->cleared = read_sysreg(cntkctl_el1);
    /* Restore the original value even when the clear/readback disagrees. */
    write_sysreg(sample->before, cntkctl_el1);
    isb();
    sample->restored = read_sysreg(cntkctl_el1);
    sample->frequency = read_sysreg(cntfrq_el0);
    ++sample->seen;
}

static void n10_pm_worker(struct work_struct *unused)
{
    struct n10_pm_result pm = {0};
    u8 expected[32] = N10_XNU_PAYLOAD_SHA256_BYTES, digest[32];
    u8 *memory = phys_to_virt(n10_window_base);
    const size_t length = N10_XNU_PAYLOAD_SIZE;
    u64 before = 0, after = 0;
    unsigned int status = 1, cpu, sequence, timers = 0;
    int result, error = 0, i;
    char frame[384], hash[65];
    (void)unused;

    if (system_state != SYSTEM_RUNNING) {
        if (++n10_pm_retries < 50) {
            schedule_delayed_work(&n10_pm_work, msecs_to_jiffies(100));
            return;
        }
        goto report;
    }
    before = n10_online_bits();
    status = 2;
    if (before != 255 || n10_window_status != 1 || !n10_window_base ||
        (n10_window_base & (N10_WINDOW_ALIGN - 1)) ||
        n10_window_base > N10_WINDOW_LIMIT - N10_WINDOW_SIZE ||
        !length || length > N10_WINDOW_SIZE || length % PAGE_SIZE ||
        !virt_addr_valid(memory) || !virt_addr_valid(memory + length - 1) ||
        virt_to_phys(memory) != n10_window_base ||
        virt_to_phys(memory + length - 1) != n10_window_base + length - 1)
        goto report;
    status = 3;
    result = n10_sha256(memory, length, digest);
    if (result || memcmp(digest, expected, sizeof(expected)))
        goto report;
    if (!n10_timer_done) {
        memset(n10_timers, 0, sizeof(n10_timers));
        cpus_read_lock();
        if (n10_online_bits() != before) {
            cpus_read_unlock();
            status = 6;
            goto report;
        }
        on_each_cpu(n10_timer_cpu, NULL, 1);
        cpus_read_unlock();
        status = 8;
        for (cpu = 0; cpu < 8; ++cpu) {
            struct n10_timer_sample *sample = &n10_timers[cpu];
            if (sample->seen == 1 && sample->cleared == (sample->before & ~0xf0ULL) &&
                sample->restored == sample->before && sample->frequency == 26000000)
                ++timers;
        }
        if (timers != 8)
            goto report;
        n10_timer_done = true;
    } else {
        timers = 8;
    }
    status = 9;
    result = n10_sha256(memory, length, digest);
    if (result || memcmp(digest, expected, sizeof(expected)))
        goto report;
    ++n10_pm_attempts;
    n10_cpu_checkpoint(6, before);
    error = n10_pm_devices_test(&pm);
    after = n10_online_bits();
    n10_cpu_checkpoint(7, after);
    for (sequence = 0; sequence < 8; ++sequence) {
        int count = scnprintf(frame, sizeof(frame),
            "id=%s seq=%u attempt=%u error=%u devices=%u resume=%u blocked=%u oldlevel=%u newlevel=%u resume_errors=%u",
            N10_RESERVE_BUILD_ID, (n10_pm_attempts - 1) * 8 + sequence, n10_pm_attempts,
            (unsigned int)(error < 0 ? -(long long)error : error), pm.devices, pm.resumed,
            pm.blocked, pm.old_level, pm.new_level,
            pm.resume_errors_after - pm.resume_errors_before);
        pr_info("N10TRY1 %s checksum=%08x\n", frame, n10_frame_checksum(frame, count));
    }
    for (sequence = 0; sequence < 8; ++sequence) {
        int count = scnprintf(frame, sizeof(frame),
            "id=%s seq=%u attempt=%u stage=%u error=%u",
            N10_RESERVE_BUILD_ID, (n10_pm_attempts - 1) * 8 + sequence,
            n10_pm_attempts, pm.stage,
            (unsigned int)(error < 0 ? -(long long)error : error));
        pr_info("N10PMS1 %s checksum=%08x\n", frame, n10_frame_checksum(frame, count));
    }
    status = 4;
    if (error || pm.error) {
        /* Respect wakeup-source aborts. Retry only a clean pre-device EBUSY,
         * after checking that the online set and payload are still intact.
         */
        if (error == -EBUSY && pm.error == -EBUSY && !pm.devices && !pm.resumed &&
            !pm.blocked && !pm.old_level && !pm.new_level &&
            pm.resume_errors_before == pm.resume_errors_after) {
            status = 6;
            if (after != before)
                goto report;
            status = 7;
            result = n10_sha256(memory, length, digest);
            if (result || memcmp(digest, expected, sizeof(expected)))
                goto report;
            if (n10_pm_attempts < 3) {
                schedule_delayed_work(&n10_pm_work, msecs_to_jiffies(10000));
                return;
            }
            status = 4;
        }
        goto report;
    }
    status = 5;
    if (pm.devices != 1 || pm.resumed != 1 || pm.blocked || pm.old_level || pm.new_level ||
        pm.resume_errors_before != pm.resume_errors_after)
        goto report;
    status = 6;
    if (after != before)
        goto report;
    status = 7;
    result = n10_sha256(memory, length, digest);
    if (result || memcmp(digest, expected, sizeof(expected)))
        goto report;
    status = 0;
report:
    for (i = 0; i < sizeof(digest); ++i)
        snprintf(hash + 2 * i, 3, "%02x", status ? 0 : digest[i]);
    hash[64] = '\0';
    for (sequence = 0; sequence < 32; ++sequence) {
        int count = scnprintf(frame, sizeof(frame),
            "id=%s seq=%u before=%llx after=%llx devices=%u resume=%u blocked=%u oldlevel=%u newlevel=%u resume_errors=%u timers=%u error=%u sha256=%s status=%u",
            N10_RESERVE_BUILD_ID, sequence, (unsigned long long)before,
            (unsigned long long)after, pm.devices, pm.resumed, pm.blocked,
            pm.old_level, pm.new_level, pm.resume_errors_after - pm.resume_errors_before,
            timers, (unsigned int)(error < 0 ? -(long long)error : error), hash, status);
        pr_info("N10PMT1 %s checksum=%08x\n", frame, n10_frame_checksum(frame, count));
    }
    if (!n10_timer_done)
        return;
    for (sequence = 0; sequence < 32; ++sequence) {
        for (cpu = 0; cpu < 8; ++cpu) {
            struct n10_timer_sample *sample = &n10_timers[cpu];
            int count = scnprintf(frame, sizeof(frame),
                "id=%s seq=%u cpu=%u before=%llx cleared=%llx restored=%llx freq=%llx status=0",
                N10_RESERVE_BUILD_ID, sequence, cpu, (unsigned long long)sample->before,
                (unsigned long long)sample->cleared, (unsigned long long)sample->restored,
                (unsigned long long)sample->frequency);
            pr_info("N10TMR1 %s checksum=%08x\n", frame, n10_frame_checksum(frame, count));
        }
    }
}

static void n10_start_pm_timer(void)
{
    unsigned int sequence;
    size_t length = strlen(linux_banner);
    char frame[384];
    while (length && (linux_banner[length - 1] == '\n' || linux_banner[length - 1] == '\r'))
        --length;
    for (sequence = 0; sequence < 16; ++sequence) {
        int count = scnprintf(frame, sizeof(frame), "id=%s seq=%u banner=%.*s",
            N10_RESERVE_BUILD_ID, sequence, (int)length, linux_banner);
        pr_info("N10BND1 %s checksum=%08x\n", frame, n10_frame_checksum(frame, count));
    }
    schedule_delayed_work(&n10_pm_work, msecs_to_jiffies(30000));
}
