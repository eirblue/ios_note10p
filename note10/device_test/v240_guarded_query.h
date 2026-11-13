/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef N240_GUARDED_QUERY_H
#define N240_GUARDED_QUERY_H
#include "v233_cpu_node_consistency.h"
#define N240_POOL_OFFSET 43608U
struct n240_query_receipt {
    n209_u32 schema,status,error_code,cpu_enter,cpu_sample,cpu_before_release;
    n209_u32 pc_before,pc_after_capture,pc_after_query,pc_after_release;
    n209_u64 pre_headroom,post_headroom;
};
_Static_assert(sizeof(struct n240_query_receipt)==56,"query receipt56");
_Static_assert(__alignof__(struct n240_query_receipt)==8,"query receipt align8");
_Static_assert(offsetof(struct n240_query_receipt,cpu_enter)==12,"cpu enter12");
_Static_assert(offsetof(struct n240_query_receipt,pc_before)==24,"pc before24");
_Static_assert(offsetof(struct n240_query_receipt,pre_headroom)==40,"pre headroom40");
_Static_assert(offsetof(struct n240_query_receipt,post_headroom)==48,"post headroom48");
int n240_observe_current_cpu(struct n231_cpu_observation *,struct n233_cpu_node_consistency *,struct n240_query_receipt *);
void n240_invalidate_observations(struct n231_cpu_observation *,struct n233_cpu_node_consistency *,struct n240_query_receipt *,int);
#endif
