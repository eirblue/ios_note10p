#include "runtime_relocation_trial.h"
/* Fixture builds may insert an observer before comparison; production has no
 * callback, injection API, writable global, or external observer dependency. */
#ifndef N10_TRIAL_OBSERVE
#define N10_TRIAL_OBSERVE(window, offset, size, affected) ((void)0)
#endif
static int span(const void *p, uint64_t n)
{
    return n ? p && n<=UINTPTR_MAX-(uintptr_t)p : !p;
}
static int intersects(const void *a,uint64_t an,const void *b,uint64_t bn)
{
    uintptr_t x=(uintptr_t)a,y=(uintptr_t)b;
    return an && bn && x<y+bn && y<x+an;
}
static void copy(volatile uint8_t *d,const volatile uint8_t *s,uint64_t n)
{
    uint64_t i;for(i=0;i<n;i++)d[i]=s[i];
}
int n10_rt_trial(const struct n10_rt_request *in,uint64_t ic,
    uint64_t ac,uint64_t cc,uint64_t rc,uint64_t oc,
    uint8_t *window,uint64_t wc,uint8_t *backup,uint64_t bc,
    struct n10_rt_trial_result *out,uint64_t outc)
{
    const void *p[8];uint64_t n[8],i,j,offset,affected;
    struct n10_rt_plan plan;struct n10_rt_trial_result result;
    int status=0;
    if(ic<sizeof(*in) || !span(in,ic) || outc<sizeof(*out) ||
       !span(out,outc) || !wc || !bc || !span(window,wc) || !span(backup,bc))return N10_RT_BUFFER;
    if(in->reserved_count>N10_RT_MAX_RANGES || in->occupied_count>N10_RT_MAX_RANGES ||
       in->adt_length>ac || in->command_length>cc ||
       (uint64_t)in->reserved_count*sizeof(*in->reserved)>rc ||
       (uint64_t)in->occupied_count*sizeof(*in->occupied)>oc ||
       !span(in->adt,ac) || !span(in->command_line,cc) ||
       !span(in->reserved,rc) || !span(in->occupied,oc))return N10_RT_BUFFER;
    p[0]=in;n[0]=ic;p[1]=in->adt;n[1]=ac;p[2]=in->command_line;n[2]=cc;
    p[3]=in->reserved;n[3]=rc;p[4]=in->occupied;n[4]=oc;
    p[5]=window;n[5]=wc;p[6]=backup;n[6]=bc;p[7]=out;n[7]=outc;
    for(i=0;i<8;i++)for(j=i+1;j<8;j++)if(intersects(p[i],n[i],p[j],n[j]))return N10_RT_BUFFER;
    status=n10_rt_plan(in,&plan);if(status)return status;
    if(plan.physical_base!=in->physical_base || plan.window_size!=in->window_size ||
       plan.image_size!=in->image_size || plan.kernel_physical<plan.physical_base ||
       plan.kernel_end<plan.kernel_physical)return N10_RT_RANGE;
    offset=plan.kernel_physical-plan.physical_base;
    affected=plan.kernel_end-plan.physical_base;
    if(offset>plan.window_size || plan.image_size>plan.window_size-offset ||
       affected!=offset+plan.image_size || affected>wc || affected>bc ||
       plan.image_size>wc)return N10_RT_BUFFER;
    /* Admission complete. No output mutation above this line. */
    copy(backup,window,affected);
    result.kernel_offset=offset;result.image_size=plan.image_size;
    result.affected_size=affected;result.backward=offset && offset<plan.image_size;
    result.reserved=0;result.transient_compared=plan.image_size;
    result.restored_compared=affected;
    if(result.backward) {
        i=plan.image_size;while(i){i--;((volatile uint8_t *)window)[offset+i]=((volatile uint8_t *)window)[i];}
    } else copy(window+offset,window,plan.image_size);
    N10_TRIAL_OBSERVE(window,offset,plan.image_size,affected);
    for(i=0;i<plan.image_size;i++)if(window[offset+i]!=backup[i])status=N10_RT_INVALID;
    /* Unconditional common restoration for every admitted operation. */
    copy(window,backup,affected);
    for(i=0;i<affected;i++)if(window[i]!=backup[i])status=N10_RT_INVALID;
    if(status)return status;
    copy((volatile uint8_t *)out,(const volatile uint8_t *)&result,sizeof(result));
    return N10_RT_OK;
}
