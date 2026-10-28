/* Paired same-CPU, IRQ-disabled CPU-PM entry/failed contract only. */
static void n10_pmu_failure_clear(struct pmu_hw_events *hw)
{
    int i;
    hw->n10_failure_valid = false;
    hw->n10_failure_pending = false;
    for (i = 0; i < ARMPMU_MAX_HWEVENTS; i++)
        hw->n10_failure_events[i] = NULL;
}

static void n10_pmu_failure_capture(struct arm_pmu *pmu, struct pmu_hw_events *hw)
{
    int i;
    if (hw->n10_failure_pending) {
        n10_pmu_failure_clear(hw);
        hw->n10_failure_pending = true;
        return;
    }
    n10_pmu_failure_clear(hw);
    hw->n10_failure_pending = true;
    if (!irqs_disabled() || pmu->num_events < 0 || pmu->num_events > ARMPMU_MAX_HWEVENTS)
        return;
    for (i = 0; i < pmu->num_events; i++) {
        struct perf_event *event;
        if (!test_bit(i, hw->used_mask))
            continue;
        event = hw->events[i];
        if (!event) {
            n10_pmu_failure_clear(hw);
            hw->n10_failure_pending = true;
            return;
        }
        if (!(event->hw.state & PERF_HES_STOPPED))
            hw->n10_failure_events[i] = event;
    }
    hw->n10_failure_valid = true;
}

static void n10_pmu_failure_recover(struct arm_pmu *pmu, struct pmu_hw_events *hw)
{
    int i;
    bool valid = hw->n10_failure_valid;
    hw->n10_failure_valid = false; /* consume before any callback */
    if (!valid || !irqs_disabled() || pmu->num_events < 0 || pmu->num_events > ARMPMU_MAX_HWEVENTS)
        goto clear;
    for (i = 0; i < ARMPMU_MAX_HWEVENTS; i++) {
        struct perf_event *saved = hw->n10_failure_events[i];
        if (saved && (i >= pmu->num_events || !test_bit(i, hw->used_mask) ||
                      hw->events[i] != saved))
            goto clear;
        if (saved && (!(saved->hw.state & PERF_HES_STOPPED) ||
                      !(saved->hw.state & PERF_HES_UPTODATE)))
            goto clear;
    }
    for (i = 0; i < pmu->num_events; i++) {
        struct perf_event *event = hw->n10_failure_events[i];
        if (event)
            RCU_NONIDLE(armpmu_start(event, PERF_EF_RELOAD));
    }
clear:
    if (!valid)
        pr_warn_once("N10PMUFR1: missing PMU failed-entry snapshot\n");
    n10_pmu_failure_clear(hw);
}
