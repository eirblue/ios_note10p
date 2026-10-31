#ifdef CONFIG_NOTE10_PM_CPUS_TEST
#include "note10_pm_cpus_probe.c"
#endif
#ifdef CONFIG_NOTE10_PMU_SETTLE
#include "note10_pmu_settle_probe.c"
#endif
#ifdef CONFIG_NOTE10_PM_NOIRQ_TEST
#include "note10_pm_noirq_probe.c"
#endif
#ifdef CONFIG_NOTE10_ABOX_PMU_AUDIT
#include "note10_abox_pmu_probe.c"
#endif
#ifdef CONFIG_NOTE10_ABOX_PM_AUDIT
#include "note10_abox_pm_probe.c"
#endif
#ifdef CONFIG_NOTE10_IOMMU_PM_AUDIT
#include "note10_iommu_pm_probe.c"
#endif
#ifdef CONFIG_NOTE10_UFS_PM_AUDIT
#include "note10_ufs_pm_probe.c"
#endif
#ifdef CONFIG_NOTE10_DMA_PM_AUDIT
#include "note10_dma_pm_probe.c"
#endif
#ifdef CONFIG_NOTE10_GIC_ROUNDTRIP
#include "note10_gic_roundtrip_probe.c"
#endif
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
#ifdef CONFIG_NOTE10_EHLD_LOCK_AUDIT
#include "note10_ehld_lock_probe.c"
#endif

#ifdef CONFIG_NOTE10_RCU_CONTEXT_AUDIT
#include "note10_rcu_context_probe.c"
#endif

#ifdef CONFIG_NOTE10_FPSIMD_REFERENCE_AUDIT
#include "note10_fpsimd_reference_probe.c"
#endif

#ifdef CONFIG_NOTE10_PMU_CONTROL_AUDIT
#include "note10_pmu_control_probe.c"
#endif

#ifdef CONFIG_NOTE10_PMU_STATE_AUDIT
#include "note10_pmu_state_probe.c"
#endif

#ifdef CONFIG_NOTE10_CPU_PM_BRANCH_AUDIT
#include "note10_pm_branch_probe.c"
#endif

#ifdef CONFIG_NOTE10_CPU_PM_PRECONDITIONS
#include "note10_pm_pre_probe.c"
#endif
#ifdef CONFIG_NOTE10_PM_CALLBACK_INVENTORY
#include "note10_pm_callbacks_probe.c"
#endif
#ifdef CONFIG_NOTE10_PM_IRQ_TEST
#include "note10_pm_irq_probe.c"
#endif
#ifdef CONFIG_NOTE10_PM_EDGE_INVENTORY
#include "note10_pm_edge_probe.c"
#endif
#ifdef CONFIG_NOTE10_PM_POST_ARCH
#include "note10_pm_post_arch_probe.c"
#endif
#ifdef CONFIG_NOTE10_PM_CPUS_TEST
#include "note10_pm_cpus_timer_probe.c"
#endif
static void n10_pm_worker(struct work_struct *unused);
static DECLARE_DELAYED_WORK(n10_pm_work, n10_pm_worker);
#include "note10_pm_cpus_workqueue.c"

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
#ifdef CONFIG_NOTE10_EHLD_LOCK_AUDIT
    bool ehld_lock_reported=false;
#endif
#ifdef CONFIG_NOTE10_RCU_CONTEXT_AUDIT
    bool rcu_reported=false;
#endif
#ifdef CONFIG_NOTE10_FPSIMD_REFERENCE_AUDIT
    bool fps_reported=false;
#endif
#ifdef CONFIG_NOTE10_PMU_CONTROL_AUDIT
    bool control_reported=false;
#endif
#ifdef CONFIG_NOTE10_PMU_STATE_AUDIT
    bool state_reported=false;
#endif
#ifdef CONFIG_NOTE10_CPU_PM_BRANCH_AUDIT
    bool branch_reported=false;
#endif
#ifdef CONFIG_NOTE10_CPU_PM_PRECONDITIONS
    bool preconditions_reported=false;
#endif
#ifdef CONFIG_NOTE10_PM_CALLBACK_INVENTORY
    bool callbacks_reported = false;
#endif
    char frame[384], hash[65];
    (void)unused;

    if (system_state != SYSTEM_RUNNING) {
        if (++n10_pm_retries < 50) {
            n10_pm_cpus_schedule(msecs_to_jiffies(100));
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
#ifdef CONFIG_NOTE10_PM_CPUS_TEST
    n10_report_pm_cpus(pm.qgeneration);
#endif
    after = n10_online_bits();
#ifdef CONFIG_NOTE10_PM_CPUS_TEST
    if (!error && n10_timer_done && after == 255) n10_report_pm_cpu_timers(pm.qgeneration);
#endif
    n10_cpu_checkpoint(7, after);
#ifdef CONFIG_NOTE10_PM_QUIESCE
    /* Preserve failed quiesce/restore evidence as well as a successful PM run. */
    for (sequence = 0; sequence < 8; ++sequence) {
#define N10_QERR(value) ((unsigned int)((value) < 0 ? -(long long)(value) : (value)))
        int count = scnprintf(frame, sizeof(frame),
            "id=%s seq=%u attempt=%u version=1 generation=%u epoch=%u phase=%u called=%u restored=%u screen=%u display=%u usb=%u wake=%u r_usb=%u r_display=%u r_screen=%u",
            N10_RESERVE_BUILD_ID, (n10_pm_attempts - 1) * 8 + sequence,
            n10_pm_attempts, pm.qgeneration, pm.cable_epoch, pm.qphase,
            pm.pm_called, pm.quiesce_restored,
            N10_QERR(pm.screen_error), N10_QERR(pm.display_error),
            N10_QERR(pm.usb_error), N10_QERR(pm.wake_error),
            N10_QERR(pm.usb_restore_error), N10_QERR(pm.display_restore_error),
            N10_QERR(pm.screen_restore_error));
        pr_info("N10QSC1 %s checksum=%08x\n", frame, n10_frame_checksum(frame, count));
#undef N10_QERR
    }
#endif
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
#ifdef CONFIG_NOTE10_PM_QUIESCE
            pm.quiesce_restored && !pm.usb_restore_error &&
            !pm.display_restore_error && !pm.screen_restore_error &&
#endif
            pm.resume_errors_before == pm.resume_errors_after) {
            status = 6;
            if (after != before)
                goto report;
            status = 7;
            result = n10_sha256(memory, length, digest);
            if (result || memcmp(digest, expected, sizeof(expected)))
                goto report;
            if (n10_pm_attempts < 3) {
                n10_pm_cpus_schedule(msecs_to_jiffies(10000));
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
#ifdef CONFIG_NOTE10_GIC_ROUNDTRIP
    if (n10_test_gic()) goto report;
    result = n10_sha256(memory, length, digest);
    if (result || memcmp(digest, expected, sizeof(expected))) goto report;
#endif
#ifdef CONFIG_NOTE10_DMA_PM_AUDIT
    n10_report_dma_pm(pm.qgeneration);
#endif
#ifdef CONFIG_NOTE10_UFS_PM_AUDIT
    n10_report_ufs_pm(pm.qgeneration);
#endif
#ifdef CONFIG_NOTE10_IOMMU_PM_AUDIT
    n10_report_iommu_pm(pm.qgeneration);
#endif
#ifdef CONFIG_NOTE10_ABOX_PM_AUDIT
    n10_report_abox_pm(pm.qgeneration);
#endif
#ifdef CONFIG_NOTE10_ABOX_PMU_AUDIT
    n10_report_abox_pmu(pm.qgeneration);
#endif
#ifdef CONFIG_NOTE10_PM_NOIRQ_TEST
    n10_report_pm_noirq(pm.qgeneration);
#endif
#ifdef CONFIG_NOTE10_PM_POST_ARCH
    if (n10_report_post_arch(memory, pm.qgeneration)) goto report;
    result = n10_sha256(memory, length, digest);
    if (result || memcmp(digest, expected, sizeof(expected))) goto report;
#endif
#ifdef CONFIG_NOTE10_PM_EDGE_INVENTORY
    if (n10_report_pm_edge(pm.qgeneration)) goto report;
#endif
#ifdef CONFIG_NOTE10_PM_IRQ_TEST
    if (n10_report_pm_irq(pm.qgeneration)) goto report;
#endif
#ifdef CONFIG_NOTE10_PM_CALLBACK_INVENTORY
    callbacks_reported = true;
    if (n10_report_pm_callbacks(pm.qgeneration, 0)) goto report;
#endif
#ifdef CONFIG_NOTE10_CPU_PM_PRECONDITIONS
    preconditions_reported=true;
    if (n10_report_pm_preconditions(pm.qgeneration,0)) goto report;
#endif
#ifdef CONFIG_NOTE10_CPU_PM_BRANCH_AUDIT
    branch_reported=true;
    if (n10_report_pm_branch(pm.qgeneration,0)) goto report;
#endif
#ifdef CONFIG_NOTE10_PMU_STATE_AUDIT
    state_reported=true;
    if (n10_report_pmu_state(pm.qgeneration,0)) goto report;
#endif
#ifdef CONFIG_NOTE10_PMU_CONTROL_AUDIT
    control_reported=true;
    if (n10_report_pmu_control(pm.qgeneration,0)) goto report;
#endif
#ifdef CONFIG_NOTE10_FPSIMD_REFERENCE_AUDIT
    fps_reported=true;
    if (n10_report_fpsimd_reference(pm.qgeneration,0)) goto report;
#endif
#ifdef CONFIG_NOTE10_RCU_CONTEXT_AUDIT
    rcu_reported=true;
    if (n10_report_rcu_context(pm.qgeneration,0)) goto report;
#endif
#ifdef CONFIG_NOTE10_EHLD_LOCK_AUDIT
    ehld_lock_reported=true;
    if (n10_report_ehld_lock(pm.qgeneration,0)) goto report;
#endif
    status = 0;
report:
#ifdef CONFIG_NOTE10_EHLD_LOCK_AUDIT
    if (status && !ehld_lock_reported && pm.qgeneration && after==255 && num_online_cpus()==8 && !irqs_disabled())
        (void)n10_report_ehld_lock(pm.qgeneration,-EIO);
#endif
#ifdef CONFIG_NOTE10_RCU_CONTEXT_AUDIT
    if (status && !rcu_reported && pm.qgeneration && after==255 && num_online_cpus()==8 && !irqs_disabled())
        (void)n10_report_rcu_context(pm.qgeneration,-EIO);
#endif
#ifdef CONFIG_NOTE10_FPSIMD_REFERENCE_AUDIT
    if (status && !fps_reported && pm.qgeneration && after==255 && num_online_cpus()==8 && !irqs_disabled())
        (void)n10_report_fpsimd_reference(pm.qgeneration,-EIO);
#endif
#ifdef CONFIG_NOTE10_PMU_CONTROL_AUDIT
    if (status && !control_reported && pm.qgeneration && after==255 && num_online_cpus()==8 && !irqs_disabled())
        (void)n10_report_pmu_control(pm.qgeneration,-EIO);
#endif
#ifdef CONFIG_NOTE10_PMU_STATE_AUDIT
    if (status && !state_reported && pm.qgeneration && after==255 && num_online_cpus()==8 && !irqs_disabled())
        (void)n10_report_pmu_state(pm.qgeneration,-EIO);
#endif
#ifdef CONFIG_NOTE10_CPU_PM_BRANCH_AUDIT
    if (status && !branch_reported && pm.qgeneration && after==255 && num_online_cpus()==8 && !irqs_disabled())
        (void)n10_report_pm_branch(pm.qgeneration,-EIO);
#endif
#ifdef CONFIG_NOTE10_CPU_PM_PRECONDITIONS
    if (status && !preconditions_reported && pm.qgeneration && after==255 && num_online_cpus()==8 && !irqs_disabled())
        (void)n10_report_pm_preconditions(pm.qgeneration,-EIO);
#endif
#ifdef CONFIG_NOTE10_PM_CALLBACK_INVENTORY
    if (status && !callbacks_reported && pm.qgeneration && after == 255 && num_online_cpus() == 8 && !irqs_disabled())
        (void)n10_report_pm_callbacks(pm.qgeneration, -EIO);
#endif
#ifdef CONFIG_NOTE10_PM_IRQ_TEST
    if (status && error && pm.qgeneration && after == 255 && num_online_cpus() == 8 && !irqs_disabled())
        n10_report_pm_irq_failure(pm.qgeneration);
#endif
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
#ifdef CONFIG_NOTE10_PMU_SETTLE
    if (!status) n10_arm_pmu_settle(pm.qgeneration);
#endif
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
    n10_pm_cpus_schedule(msecs_to_jiffies(30000));
}
