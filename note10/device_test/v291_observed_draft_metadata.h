/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef NOTE10_V291_OBSERVED_DRAFT_METADATA_H
#define NOTE10_V291_OBSERVED_DRAFT_METADATA_H
#include "v290_preparation_storage.h"
#include "v285_current_cpu_metadata.h"
#define N291_MAX_RANGES 16U
#define N291_PACKET_CAP 512U
#define N291_PACKET_OFFSET 256U
#define N291_HEADER_OFFSET 120U
#define N291_OBS_OFFSET 18352U
#define N291_WIRE_OFFSET 18864U
#define N291_WALK_OFFSET 19376U
#define N291_NONCONTIGUOUS 1U
#define N291_DISABLED 2U
#define N291_UNKNOWN_STATUS 4U
#define N291_HOTPLUG 8U
#define N291_UNSUPPORTED 16U
#define N291_OWNER_OUTSIDE 32U
#define N291_CHOSEN_READY 64U
#define N291_SOURCE_OF_REG 65536U
#define N291_CPU_SAMPLED 131072U
#define N291_INCOMPLETE_FLAGS 63U
enum n291_phase { N291_EMPTY,N291_REFUSED,N291_WRITING,N291_INCOMPLETE_DRAFT,N291_EARLY_DRAFT,N291_QUARANTINED };
struct n291_header {
    n209_u32 phase,flags,inventory_bytes,adt_bytes,range_count,selected_affinity,frequency,reserved;
    n209_u64 owner_generation;
};
struct n291_range { n209_u64 base,size;n209_u32 node_ordinal,tuple_ordinal; };
struct n291_observation {
    n209_u32 count,selected,frequency,flags,address_cells,size_cells,scanned_nodes,unsupported;
    n209_u64 union_base,union_size;
    struct n291_range ranges[N291_MAX_RANGES];
};
_Static_assert(sizeof(struct n291_header)==40&&__alignof__(struct n291_header)==8,"draft header40/8");
_Static_assert(offsetof(struct n291_header,phase)==0&&offsetof(struct n291_header,flags)==4&&
    offsetof(struct n291_header,inventory_bytes)==8&&offsetof(struct n291_header,adt_bytes)==12&&
    offsetof(struct n291_header,range_count)==16&&offsetof(struct n291_header,selected_affinity)==20&&
    offsetof(struct n291_header,frequency)==24&&offsetof(struct n291_header,reserved)==28&&
    offsetof(struct n291_header,owner_generation)==32,"native LE header field offsets");
_Static_assert(offsetof(struct n290_storage,reserved)==N291_HEADER_OFFSET,"existing reserved tail120");
_Static_assert(sizeof(((struct n290_storage *)0)->reserved)==40,"no descriptor growth");
_Static_assert(sizeof(struct n291_range)==24&&sizeof(struct n291_observation)==432,"bounded observations");
_Static_assert(offsetof(struct n285_workspace,padding)==N291_OBS_OFFSET,"old padding begins18352");
_Static_assert(N291_WIRE_OFFSET==N291_OBS_OFFSET+512&&N291_WALK_OFFSET==N291_WIRE_OFFSET+512,"disjoint scratch slices");
_Static_assert(N291_WALK_OFFSET+768<=offsetof(struct n285_workspace,readback),"walk before readback");
_Static_assert(N291_PACKET_OFFSET+N291_PACKET_CAP<N209_PAGE,"packet after noninstalled record only");
int n291_classify(struct n291_observation *,n209_u64,n209_u64);
int n291_encode_early(const struct n291_observation *,n209_u8 *,n209_u32,n209_u32 *);
int n291_encode_inventory(const struct n291_observation *,n209_u64,n209_u8 *,n209_u32,n209_u32 *);
#endif
