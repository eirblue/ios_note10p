/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef N300_RETURN_DIAGNOSTIC_H
#define N300_RETURN_DIAGNOSTIC_H
#ifdef __KERNEL__
#include <linux/types.h>
typedef u32 n300_u32;
typedef u64 n300_u64;
#else
typedef unsigned int n300_u32;
typedef unsigned long long n300_u64;
#endif
#define N300_LITTLE_CLUSTER 0U
#define N300_DEFAULT_TIMEOUT 15U
struct n300_wdt_fields {
    n300_u32 present,soft_noboot,nowayout,cluster,variant,route_func,rate_clock,gate_clock;
    n300_u64 freq;
    n300_u32 multistage,device_id,timeout,max_heartbeat,active,hw_running;
};
struct n300_outer_fields {
    n300_u32 running,cycle_ok;int arm_result;
    n300_u32 pending,armed,requested;unsigned long remaining;n300_u32 spent;
};
static inline n300_u32 n300_wdt_reasons(const struct n300_wdt_fields *s)
{
    n300_u32 mask=0;
    if(!s->present)return 1U;
    if(s->soft_noboot)mask|=1U<<1;
    if(s->nowayout)mask|=1U<<2;
    if(s->cluster!=N300_LITTLE_CLUSTER)mask|=1U<<3;
    if(!s->variant)mask|=1U<<4;
    if(!s->route_func)mask|=1U<<5;
    if(!s->rate_clock)mask|=1U<<6;
    if(!s->gate_clock)mask|=1U<<7;
    if(!s->freq)mask|=1U<<8;
    if(s->multistage)mask|=1U<<9;
    if(s->device_id)mask|=1U<<10;
    if(s->timeout!=N300_DEFAULT_TIMEOUT)mask|=1U<<11;
    if(s->max_heartbeat)mask|=1U<<12;
    if(s->active)mask|=1U<<13;
    if(s->hw_running)mask|=1U<<14;
    return mask;
}
static inline n300_u32 n300_outer_reasons(const struct n300_outer_fields *s)
{
    n300_u32 mask=0;
    if(!s->running)mask|=1U;
    if(!s->cycle_ok)mask|=1U<<1;
    if(s->arm_result)mask|=1U<<2;
    if(!s->pending)mask|=1U<<3;
    if(!s->armed)mask|=1U<<4;
    if(s->requested)mask|=1U<<5;
    if(s->remaining<45000 || s->remaining>90000)mask|=1U<<6;
    if(s->spent)mask|=1U<<7;
    return mask;
}
#endif
