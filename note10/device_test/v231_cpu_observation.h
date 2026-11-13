/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef NOTE10_V231_CPU_OBSERVATION_H
#define NOTE10_V231_CPU_OBSERVATION_H
#include "native_parcel_core.h"
#define N231_POOL_OFFSET 43544U
struct n231_cpu_observation {
    n209_u64 mpidr_el1,cntfrq_el0;
    n209_u32 linux_cpu,current_el,status,reserved;
};
_Static_assert(sizeof(struct n231_cpu_observation)==32,"observation32");
_Static_assert(__alignof__(struct n231_cpu_observation)==8,"observation align8");
_Static_assert(offsetof(struct n231_cpu_observation,mpidr_el1)==0,"mpidr0");
_Static_assert(offsetof(struct n231_cpu_observation,cntfrq_el0)==8,"cntfrq8");
_Static_assert(offsetof(struct n231_cpu_observation,linux_cpu)==16,"cpu16");
_Static_assert(offsetof(struct n231_cpu_observation,current_el)==20,"el20");
_Static_assert(offsetof(struct n231_cpu_observation,status)==24,"status24");
_Static_assert(offsetof(struct n231_cpu_observation,reserved)==28,"reserved28");
/* One Linux-context sample only; no future CPU selection or FDT association. */
int n231_capture_cpu_observation(struct n231_cpu_observation *);
#ifdef N231_HOST_FIXTURE
unsigned int n231_fixture_get_cpu(void);
n209_u64 n231_fixture_read(unsigned int);
void n231_fixture_put_cpu(void);
#endif
#endif
