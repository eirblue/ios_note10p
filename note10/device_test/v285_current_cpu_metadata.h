/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef NOTE10_V285_CURRENT_CPU_METADATA_H
#define NOTE10_V285_CURRENT_CPU_METADATA_H
#include "v278_current_owner_seal.h"
#include "v230_boot_metadata.h"
#include "v240_guarded_query.h"
#define N285_MAX_CPUS 32U
#define N285_HEADER_OFFSET 1312U
struct n285_cpu_snapshot {
    n209_u32 count,selected,frequency,reserved;
    n209_u32 affinity[N285_MAX_CPUS];
};
/* STAGED only. Acceptance also requires the matching current VALUES_ONLY seal. */
struct n285_header {
    n209_u8 magic[8];n209_u32 schema,bytes;
    n209_u8 build[32],boot[32],cycle[32],cookie[16];
    n209_u64 generation,base,size,args_offset,adt_offset;
    n209_u32 adt_bytes,flags;n209_u8 reserved[80];
};
struct n285_workspace {
    n209_u8 adt[16384],args[1152],record[64];
    struct n230_placement placement;
    struct n209_payload payload;
    struct n285_header header;
    struct n285_cpu_snapshot snapshot;
    n209_u8 padding[2128],readback[4096];
};
_Static_assert(sizeof(struct n285_header)==256,"staged header256");
_Static_assert(sizeof(struct n285_cpu_snapshot)==144,"snapshot144");
_Static_assert(offsetof(struct n285_workspace,args)==16384,"args after ADT");
_Static_assert(offsetof(struct n285_workspace,record)==17536,"shadow64");
_Static_assert(offsetof(struct n285_workspace,placement)==17600,"placement96");
_Static_assert(offsetof(struct n285_workspace,payload)==17696,"payload256");
_Static_assert(offsetof(struct n285_workspace,header)==17952,"header256");
_Static_assert(offsetof(struct n285_workspace,snapshot)==18208,"snapshot144");
_Static_assert(offsetof(struct n285_workspace,readback)==20480,"readback page");
_Static_assert(sizeof(struct n285_workspace)==24576,"workspace24576");
_Static_assert(sizeof(struct n285_workspace)<=42312,"freed inflate workspace only");
/* Called only by the locked owner AFTER codec_end. No seal is accepted here.
 * Writes arguments/ADT and non-installed shadow values only; all I/O is through
 * the retained owner. A returned success still requires final n278_seal_once. */
int n285_write_pages(void *,n209_u64,const void *,n209_u32);
int n285_readback_pages(void *,n209_u64,const void *,n209_u32,n209_u8 *);
int n285_prepare_metadata(const struct n210_request *,const struct n210_destination *,
    const struct n210_context *,void *,struct n285_workspace *,unsigned int);
#endif
