/* PC-only reusable preparation. No reservation, hardware ownership or transfer. */
#ifndef N10_RUNTIME_RELOCATION_H
#define N10_RUNTIME_RELOCATION_H
#ifdef __KERNEL__
#include <linux/types.h>
#include <linux/stddef.h>
#include <linux/kernel.h>
#ifndef UINT64_C
#define UINT64_C(value) value##ULL
#endif
#ifndef UINT64_MAX
#define UINT64_MAX ((uint64_t)~0ULL)
#endif
#ifndef UINTPTR_MAX
#define UINTPTR_MAX ((uintptr_t)~0UL)
#endif
#else
#include <stdint.h>
#include <stddef.h>
#endif
#define N10_RT_PAGE UINT64_C(0x4000)
#define N10_RT_BLOCK UINT64_C(0x2000000)
#define N10_RT_WINDOW UINT64_C(0x10000000)
#define N10_RT_MIN_BASE UINT64_C(0x80000000)
#define N10_RT_LIMIT UINT64_C(0x10000000000)
#define N10_RT_ARGS_SIZE 1152U
#define N10_RT_RECORD_SIZE 64U
#define N10_RT_MAX_RANGES 16U
#define N10_RT_SYNTHETIC_ADT 1U
enum { N10_RT_OK=0, N10_RT_INVALID=-1, N10_RT_RANGE=-2, N10_RT_OVERLAP=-3,
       N10_RT_ADT=-4, N10_RT_BUFFER=-5 };
struct n10_rt_range { uint64_t start, size; };
struct n10_rt_request {
    uint64_t physical_base, window_size, image_virtual, image_size, entry_virtual;
    const uint8_t *adt;
    uint32_t adt_length, synthetic_adt;
    const uint8_t *command_line;
    uint32_t command_length;
    const struct n10_rt_range *reserved, *occupied;
    uint32_t reserved_count, occupied_count;
};
struct n10_rt_plan {
    uint64_t virtual_ram_base, physical_base, window_size, image_virtual, image_size, entry_virtual;
    uint64_t kernel_physical, entry_physical, kernel_end;
    uint64_t arguments_physical, device_tree_physical, device_tree_virtual, adapter_physical;
    uint64_t mapping_blocks, kernel_blocks, adt_length;
};
struct n10_rt_boot_fields {
    uint64_t virtual_base, physical_base, memory_size, top_of_kernel;
    uint64_t video[6];
    uint32_t machine_type;
    uint64_t device_tree_pointer;
    uint32_t device_tree_length;
    const uint8_t *command_line;
    uint32_t command_length;
    uint64_t boot_flags, memory_size_actual;
};
/* Own explicit layout, compared with the saved real-header oracle by fresh
 * ARM64 object inspection. Serialization does not cast buffers to this type. */
struct n10_rt_boot_layout {
    uint16_t Revision, Version;
    uint8_t pad0[4];
    uint64_t virtBase, physBase, memSize, topOfKernelData, Video[6];
    uint32_t machineType;
    uint8_t pad1[4];
    uint64_t deviceTreeP;
    uint32_t deviceTreeLength;
    uint8_t CommandLine[1024], pad2[4];
    uint64_t bootFlags, memSizeActual;
};
_Static_assert(sizeof(struct n10_rt_boot_layout)==N10_RT_ARGS_SIZE,"boot_args size");
int n10_rt_validate_adt(const uint8_t *, uint32_t);
int n10_rt_plan(const struct n10_rt_request *, struct n10_rt_plan *);
int n10_rt_serialize_boot_args(const struct n10_rt_boot_fields *, uint8_t *, uint64_t);
int n10_rt_serialize_record(uint64_t, uint64_t, uint8_t *, uint64_t);
/* All three outputs remain byte-identical on rejection. Inputs and output
 * spans must be valid caller-owned memory and must not overlap. */
int n10_rt_build(const struct n10_rt_request *, struct n10_rt_plan *,
                 uint8_t *, uint64_t, uint8_t *, uint64_t);
#endif
