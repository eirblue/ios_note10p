/* SPDX-License-Identifier: BSD-2-Clause */
#ifndef N10_EXYNOS_LEAF_MAPPER_H
#define N10_EXYNOS_LEAF_MAPPER_H
#define N10_MAP_PAGE 16384
#define N10_MAP_POOL_PAGES 10
#define N10_MAP_POOL_BYTES (N10_MAP_PAGE * N10_MAP_POOL_PAGES)
#define N10_MAP_MAX_BYTES 33554432
#define N10_MAP_TABLE_ATTR 3
#define N10_MAP_LEAF_ATTR 0x0040000000000603
#define N10_MAP_PA_LIMIT 0x10000000000
#ifndef N10_MAPPER_FIXTURE
#if !defined(ARM64_BOARD_CONFIG_EXYNOS9825) || !defined(__ARM_16K_PG__) || CONFIG_SPTM || XNU_MONITOR || __ARM_KERNEL_PROTECT__
#error unsupported Exynos leaf bootstrap configuration
#endif
#if defined(KERNEL_INTEGRITY_KTRR) || defined(KERNEL_INTEGRITY_CTRR) || defined(KERNEL_INTEGRITY_PV_CTRR)
#error unsupported bootstrap identity-map replacement policy
#endif
#if T0SZ_BOOT != 17 || T1SZ_BOOT != 17 || ARM_TT_L1_SHIFT != 36 || ARM_TT_L2_SHIFT != 25 || ARM_TT_L3_SHIFT != 14
#error exact three-level 47-bit bootstrap format required
#endif
#if TCR_IPS_VALUE != TCR_IPS_40BITS || ARM_TTE_BOOT_TABLE != N10_MAP_TABLE_ATTR
#error exact 40-bit PA/table format required
#endif
#if (((ARM_TTE_BOOT_BLOCK_LOWER | ARM_TTE_BOOT_BLOCK_UPPER) & ~ARM_TTE_TYPE_MASK) | ARM_PTE_TYPE_VALID) != N10_MAP_LEAF_ATTR
#error leaf attributes differ from source bootstrap policy
#endif
#if defined(BOOTSTRAP_TABLE_SIZE) && BOOTSTRAP_TABLE_SIZE != N10_MAP_POOL_BYTES
#error exact ten-page bootstrap pool required
#endif
#endif
#endif
