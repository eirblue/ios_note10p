/* PC-owned data rehearsal only. Never derive a pointer from physical geometry. */
#ifndef N10_RUNTIME_RELOCATION_TRIAL_H
#define N10_RUNTIME_RELOCATION_TRIAL_H
#include "runtime_relocation.h"
struct n10_rt_trial_result {
    uint64_t kernel_offset, image_size, affected_size;
    uint64_t transient_compared, restored_compared;
    uint32_t backward, reserved;
};
/* Capacities describe valid caller-owned objects, not claimed physical spans.
 * Every nonempty input/output capacity span must be pairwise disjoint.
 * Rejection before admission preserves all outputs. After admission backup
 * holds the original full prefix even on failure; window is always restored.
 * Result is committed only after both complete comparisons succeed. */
int n10_rt_trial(const struct n10_rt_request *, uint64_t request_capacity,
    uint64_t adt_capacity, uint64_t command_capacity,
    uint64_t reserved_capacity, uint64_t occupied_capacity,
    uint8_t *window, uint64_t window_capacity,
    uint8_t *backup, uint64_t backup_capacity,
    struct n10_rt_trial_result *, uint64_t result_capacity);
#endif
