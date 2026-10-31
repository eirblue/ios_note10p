/* Read-only target compiler ABI oracle. No runtime code or mutable state. */
#include "runtime_relocation_trial.h"
#define FIELD(type, member) offsetof(struct type, member), sizeof(((struct type *)0)->member)
__attribute__((used,section(".n10_abi")))
const uint64_t n10_trial_abi[]={
    UINT64_C(0x4e31304142493031),1,
    sizeof(struct n10_rt_request),sizeof(struct n10_rt_trial_result),sizeof(void *),sizeof(int),
    (uint64_t)(int64_t)N10_RT_OK,(uint64_t)(int64_t)N10_RT_INVALID,(uint64_t)(int64_t)N10_RT_BUFFER,
    FIELD(n10_rt_request,physical_base),FIELD(n10_rt_request,window_size),
    FIELD(n10_rt_request,image_virtual),FIELD(n10_rt_request,image_size),FIELD(n10_rt_request,entry_virtual),
    FIELD(n10_rt_request,adt),FIELD(n10_rt_request,adt_length),FIELD(n10_rt_request,synthetic_adt),
    FIELD(n10_rt_request,command_line),FIELD(n10_rt_request,command_length),
    FIELD(n10_rt_request,reserved),FIELD(n10_rt_request,occupied),
    FIELD(n10_rt_request,reserved_count),FIELD(n10_rt_request,occupied_count),
    FIELD(n10_rt_trial_result,kernel_offset),FIELD(n10_rt_trial_result,image_size),
    FIELD(n10_rt_trial_result,affected_size),FIELD(n10_rt_trial_result,transient_compared),
    FIELD(n10_rt_trial_result,restored_compared),FIELD(n10_rt_trial_result,backward),FIELD(n10_rt_trial_result,reserved)
};
