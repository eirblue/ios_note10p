/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef NOTE10_V233_CPU_NODE_CONSISTENCY_H
#define NOTE10_V233_CPU_NODE_CONSISTENCY_H
#include "v231_cpu_observation.h"
#define N233_POOL_OFFSET 43576U
struct n233_cpu_node_consistency {
    n209_u64 logical_mpidr,firmware_reg;
    n209_u32 linux_cpu,address_cells,reg_bytes,status;
};
_Static_assert(sizeof(struct n233_cpu_node_consistency)==32,"node record32");
_Static_assert(__alignof__(struct n233_cpu_node_consistency)==8,"node align8");
_Static_assert(offsetof(struct n233_cpu_node_consistency,logical_mpidr)==0,"logical0");
_Static_assert(offsetof(struct n233_cpu_node_consistency,firmware_reg)==8,"reg8");
_Static_assert(offsetof(struct n233_cpu_node_consistency,linux_cpu)==16,"cpu16");
_Static_assert(offsetof(struct n233_cpu_node_consistency,address_cells)==20,"cells20");
_Static_assert(offsetof(struct n233_cpu_node_consistency,reg_bytes)==24,"bytes24");
_Static_assert(offsetof(struct n233_cpu_node_consistency,status)==28,"status28");
/* Disjoint caller-owned input/output; no runtime caller is installed by233. */
int n233_capture_cpu_node_consistency(const struct n231_cpu_observation *,struct n233_cpu_node_consistency *);
#ifdef N233_HOST_FIXTURE
struct n233_fixture_node;
n209_u64 n233_fixture_logical_map(unsigned int);
struct n233_fixture_node *n233_fixture_get_cpu_node(unsigned int,unsigned int *);
struct n233_fixture_node *n233_fixture_get_parent(struct n233_fixture_node *);
const char *n233_fixture_full_name(struct n233_fixture_node *);
const void *n233_fixture_property(struct n233_fixture_node *,const char *,int *);
n209_u64 n233_fixture_read_number(const void *,unsigned int);
void n233_fixture_put(struct n233_fixture_node *);
#endif
#endif
