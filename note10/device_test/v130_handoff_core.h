/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef N10_V130_HANDOFF_CORE_H
#define N10_V130_HANDOFF_CORE_H
#ifdef __KERNEL__
#include <linux/types.h>
typedef u64 n130_u64;typedef u32 n130_u32;typedef u8 n130_u8;
#else
#include <stdint.h>
typedef uint64_t n130_u64;typedef uint32_t n130_u32;typedef uint8_t n130_u8;
#endif
#define N130_PAGE 16384ULL
#define N130_MEMORY 33554432ULL
#define N130_MIN 0x80000000ULL
#define N130_LIMIT 0x10000000000ULL
#define N130_VIRTUAL 0xfffffff007004000ULL
#define N130_RESIDUE (N130_VIRTUAL&(N130_MEMORY-1))
#define N130_SPAN 19136512ULL
#define N130_ENTRY 11039888ULL
#define N130_ADT_MAX 1048576ULL
#define N130_ARCH (183ULL<<16)
struct n130_wire {
    n130_u8 magic[8];n130_u32 schema,bytes;
    n130_u64 base,size;n130_u8 cookie[16],build[32];
    n130_u64 kernel_span,kernel_entry_offset,args_offset,adt_offset,adt_length;
    n130_u64 adapter_offset,adapter_bytes,top_offset;
    n130_u8 activation_sha256[32],kernel_sha256[32];
    n130_u64 generation;n130_u32 status,page_shift;
};
struct n130_payload {
    n130_u8 magic[8];n130_u32 schema,bytes;
    n130_u64 kernel_span,kernel_entry,pool_offset,pool_bytes,adapter_entry,adapter_record;
    n130_u8 kernel_sha256[32],adapter_sha256[32];
};
struct n130_platform {
    n130_u8 magic[8];n130_u32 schema,bytes;
    n130_u64 mpidr,frequency,distributor,distributor_bytes,cpu_interface,cpu_interface_bytes;
    n130_u32 timer_intid,status;n130_u8 reserved[56];
};
struct n130_activation {
    n130_u8 magic[8];n130_u32 schema,bytes;n130_u64 adt_bytes;
    n130_u8 adt_sha256[32],platform_sha256[32],capture_receipt_sha256[32];n130_u64 reserved;
};
struct n130_segment {const void *buf;n130_u64 bufsz;const void *mem;n130_u64 memsz;};
struct n130_reserve_ops {
    int (*extent)(void *,unsigned int,n130_u64 *,n130_u64 *);
    int (*available)(void *,n130_u64,n130_u64);
    int (*reserve)(void *,n130_u64,n130_u64);
};
struct n130_loader_ops {
    long (*arm)(void *,const struct n130_wire *);
    long (*load)(void *,n130_u64,const struct n130_segment *,n130_u64);
    long (*reboot)(void *);
    void (*cancel)(void *,const struct n130_wire *);
};
_Static_assert(sizeof(struct n130_wire)==224,"v130 wire fixed224 bytes");
_Static_assert(sizeof(struct n130_payload)==128,"v130 private payload fixed128 bytes");
_Static_assert(sizeof(struct n130_platform)==128,"v130 probed platform fixed128 bytes");
_Static_assert(sizeof(struct n130_activation)==128,"v130 private activation fixed128 bytes");
_Static_assert(sizeof(struct n130_segment)==32,"native64 kexec segment");
int n130_reserve(const struct n130_reserve_ops *,void *,n130_u64 *);
int n130_descriptor(const struct n130_wire *,const char *);
int n130_layout(struct n130_wire *,n130_u64);
int n130_parcel(const struct n130_wire *,const char *);
int n130_payload_valid(const struct n130_payload *);
int n130_boot_args(n130_u8 *,unsigned long,const struct n130_wire *);
int n130_adt_owned_dram(n130_u8 *,unsigned long,const struct n130_wire *);
long n130_load_once(const struct n130_wire *,const char *,const void *,const struct n130_loader_ops *,void *);
#endif
