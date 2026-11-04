/* SPDX-License-Identifier: GPL-2.0-only */
/* Included in sec_reboot.c; all PMU symbols come from that pinned source. */
#include <linux/legacy_kexec_return.h>
static int n10_marker_read(void *p,int which,n10_u32 *value)
{(void)p;return exynos_pmu_read(which?SEC_DEBUG_PANIC_INFORM:SEC_DEBUG_MAGIC_INFORM,value);}
static int n10_marker_write(void *p,int which,n10_u32 value)
{(void)p;return exynos_pmu_write(which?SEC_DEBUG_PANIC_INFORM:SEC_DEBUG_MAGIC_INFORM,value);}
int n10_sec_stage_kexec_recovery(void)
{
    static const struct n10_marker_ops ops={n10_marker_read,n10_marker_write};
    return n10_stage_marker(&ops,NULL,0xffU<<SEC_REBOOT_END_OFFSET,
                           (u32)SEC_REBOOT_NORMAL<<SEC_REBOOT_END_OFFSET,SEC_RESET_REASON_RECOVERY);
}
