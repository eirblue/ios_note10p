/* Conservative platform policy, not a measurement of Samsung eFuses.
 * Like XNU's non-Apple x86 fallback, unknown hardware gets production
 * restrictions. This does not report OEM unlock/Knox state or enable debug.
 */
#if defined(ARM64_BOARD_CONFIG_EXYNOS9825)
#include <mach/boolean.h>
#include <machine/machine_routines.h>

boolean_t
ml_device_is_prod_fused(void)
{
    return TRUE;
}
#endif
