# CPU0 PMU software-state audit

The default-off audit records bounded software state for used CPU0 PMU event slots during the existing owned notifier-chain observation. It does not invoke CPU-PM callbacks, access counter or interrupt-controller registers, or change event state. The notifier-chain lock protects notifier and PMU membership; the event reads additionally rely on the supported affected-CPU perf lifetime and IRQ-off task-context contract. Reentrant CPU-PM, direct slot mutation, NMI/FIQ mutation, hotplug, teardown and IRQ enabling during this observation are outside that contract.

For each used slot the audit checks the PMU association before reading the slot index and remaining event fields. Software-running means exactly zero hardware-state flags. STOPPED is a valid observation and is distinct from future callback eligibility; affinity, current CPU and generic ACTIVE state are separate fields. An empty or absent PMU observation establishes no eligibility. These software observations do not establish physical counter enablement or safe execution of a CPU-PM callback.

The synthetic source and protocol models are PC-side checks; they do not demonstrate PMU restoration on hardware. The diagnostic does not directly execute CPU-PM or run XNU.
