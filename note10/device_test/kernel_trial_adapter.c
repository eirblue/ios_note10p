/* Uninvoked real-TU component entry. No __init lifetime or live boot hook. */
#include "runtime_relocation_trial.h"
__attribute__((__noinline__,__used__,__section__(".text.n10_kernel_trial_adapter")))
int n10_kernel_trial_adapter(const struct n10_rt_request *request,uint64_t request_capacity,
    uint64_t adt_capacity,uint64_t command_capacity,uint64_t reserved_capacity,uint64_t occupied_capacity,
    uint8_t *window,uint64_t window_capacity,uint8_t *backup,uint64_t backup_capacity,
    struct n10_rt_trial_result *result,uint64_t result_capacity)
{
    return n10_rt_trial(request,request_capacity,adt_capacity,command_capacity,reserved_capacity,occupied_capacity,
                        window,window_capacity,backup,backup_capacity,result,result_capacity);
}
