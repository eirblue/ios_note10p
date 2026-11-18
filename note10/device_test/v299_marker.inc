/* Same selected SEC recovery channel, with the existing readback algorithm. */
#include <linux/n299_return_contract.h>
static int n299_marker_read(void *unused,int which,u32 *value)
{(void)unused;return exynos_pmu_read(which?SEC_DEBUG_PANIC_INFORM:SEC_DEBUG_MAGIC_INFORM,value);}
static int n299_marker_write(void *unused,int which,u32 value)
{(void)unused;return exynos_pmu_write(which?SEC_DEBUG_PANIC_INFORM:SEC_DEBUG_MAGIC_INFORM,value);}
int n299_sec_prepare_recovery(void)
{
    static const struct n299_marker_ops ops={n299_marker_read,n299_marker_write};
    return n299_stage_marker(&ops,NULL,0xffU<<SEC_REBOOT_END_OFFSET,
                            (u32)SEC_REBOOT_NORMAL<<SEC_REBOOT_END_OFFSET,SEC_RESET_REASON_RECOVERY);
}
