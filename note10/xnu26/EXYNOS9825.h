/* Initial single-CPU compile profile. Values are required inputs, not defaults.
 * Supplying values is not evidence that they describe the physical phone.
 * No Apple CPU/SoC common header is included here.
 */
#ifndef _PEXPERT_ARM64_EXYNOS9825_H
#define _PEXPERT_ARM64_EXYNOS9825_H

#if !defined(N10_BOARD_SCHEMA) || N10_BOARD_SCHEMA != 1
#error Note10 requires explicit board schema 1 and cache/page inputs
#endif
#if !defined(N10_ICACHE_LINE_LOG2) || !defined(N10_DCACHE_LINE_LOG2) || !defined(N10_MAX_CACHE_LINE_LOG2) || !defined(N10_KERNEL_PAGE_SHIFT)
#error Note10 requires explicit cache/page inputs; no hardware defaults exist
#endif
#if N10_ICACHE_LINE_LOG2 < 4 || N10_ICACHE_LINE_LOG2 > 11 || N10_DCACHE_LINE_LOG2 < 4 || N10_DCACHE_LINE_LOG2 > 11 || N10_MAX_CACHE_LINE_LOG2 < 4 || N10_MAX_CACHE_LINE_LOG2 > 11
#error Note10 cache line exponents are out of range
#endif
#if N10_MAX_CACHE_LINE_LOG2 < N10_ICACHE_LINE_LOG2 || N10_MAX_CACHE_LINE_LOG2 < N10_DCACHE_LINE_LOG2
#error Note10 maximum cache line must cover instruction and data lines
#endif
#if N10_KERNEL_PAGE_SHIFT != 12 && N10_KERNEL_PAGE_SHIFT != 14
#error Note10 compile profile supports only 4K or 16K kernel pages
#endif
#if defined(__arm64e__) || defined(CPU_HAS_APPLE_PAC) || defined(HAS_APPLE_PAC) || defined(XNU_BUILT_WITH_BTI)
#error Note10 requires a plain ARM64 kernel without PAC or BTI instrumentation
#endif
#if defined(APPLE_ARM64_ARCH_FAMILY) || defined(ARM64_BOARD_CONFIG_VMAPPLE) || USE_APPLEARMSMP || HAS_GIC_V3 || HAS_APPLE_GENERIC_TIMER
#error Note10 cannot inherit Apple CPU platform or GICv3 configuration
#endif
#if CONFIG_SPTM || XNU_MONITOR || defined(MONITOR)
#error Note10 monitor and SPTM support are not implemented
#endif

/* Software bring-up restriction; not the physical topology of SM-N976N. */
#define MAX_CPUS 1
#define MAX_CPU_CLUSTERS 1
#define MAX_L2_CLINE N10_MAX_CACHE_LINE_LOG2
#define __ARM_ARCH__ 8
#define __ARM_VMSA__ 8
#define __ARM_VFP__ 4
#define ARM_ARCH_TIMER 1
/* No legacy Apple MONITOR_SET_ENTRY interface. This says nothing about the
 * presence of Samsung EL3 firmware. PSCI/power gating remain unimplemented. */
#define NO_MONITOR 1
#if N10_KERNEL_PAGE_SHIFT == 14
#define __ARM_16K_PG__ 1
#endif

/* IO coherency, Apple monitor/PAC, cache policies and PA/VA geometry are
 * deliberately not inferred. This header is not a complete boot contract.
 */
#endif
