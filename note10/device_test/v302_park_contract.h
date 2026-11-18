/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef N302_PARK_CONTRACT_H
#define N302_PARK_CONTRACT_H
#ifdef __KERNEL__
#include <linux/n300_return_diagnostic.h>
#else
#include "v300_return_diagnostic.h"
#endif
struct n302_gate { unsigned int running,prepared,spent,armed,requested,pending,cpu0_online;unsigned long remaining; };
static inline int n302_live_wdt(const struct n300_wdt_fields *s)
{
    return s->present && !s->soft_noboot && !s->nowayout && s->cluster==0 && s->variant && s->route_func &&
        s->rate_clock && s->gate_clock && s->freq==26000000 && !s->multistage && !s->device_id &&
        s->timeout==10 && !s->max_heartbeat && s->active && !s->hw_running;
}
static inline int n302_gate_ready(const struct n302_gate *s,const struct n300_wdt_fields *w)
{
    return s->running && s->prepared==1 && s->spent==1 && s->armed && !s->requested && s->pending &&
        s->cpu0_online && s->remaining>=30000 && s->remaining<=90000 && n302_live_wdt(w);
}
static inline int n302_online_ok(n300_u64 mask,unsigned int count,unsigned int cpu,unsigned int irq_off)
{
    unsigned int bits=0;n300_u64 value=mask;
    while(value){bits+=(unsigned int)(value&1);value>>=1;}
    return cpu==0 && irq_off && (mask&1) && count>=1 && count<=64 && count==bits;
}
static inline int n302_ack_line(char *out,unsigned int remaining)
{
    const char prefix[]="N299ARM timeout=10 remaining_ms=",suffix[]=" descriptor=held keepalives=0\n";
    unsigned int i,n=0,divisor;
    if(remaining<30000 || remaining>90000)return -1;
    for(i=0;i<sizeof(prefix)-1;++i)out[n++]=prefix[i];
    for(divisor=10000;divisor;divisor/=10)out[n++]=(char)('0'+(remaining/divisor)%10);
    for(i=0;i<sizeof(suffix)-1;++i)out[n++]=suffix[i];
    out[n]=0;return (int)n;
}
#endif
