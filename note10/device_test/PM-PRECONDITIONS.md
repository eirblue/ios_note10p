# CPU0 PM preconditions and GIC restore inputs

This default-off diagnostic adds two required evaluations to the existing 33: CPU0 PM software context and banked GIC restore inputs. The existing maximum compatible profile enables it. The observations use the existing owned CPU0 stop and IRQ snapshots; they do not add a PM entry or CPU hotplug cycle.

The software collector checks the owner, generation, PM/noirq state, CPU and IRQ context before, during and after a bounded trylock of the CPU-PM notifier registration chain. It copies limited memory-only fields while the registration lock protects client lifetime. Unknown clients remain unclassified. The GIC observer extends the existing three snapshots with a fixed read-only register set; it performs no GIC writes. A restore-default comparison is an observation, not permission to execute CPU-PM. Failed or incomplete captures are rejected, and the protocol requires two matching checksummed copies.

Source pins, 27 prepared files, configuration, Image markers and model evidence are bound through packaging and precheck. Synthetic models exercise getter and lifecycle conditions, GIC read allowlists, caller restoration, worker/producer behavior, source composition and proof omission. These models do not establish physical behavior. An earlier CI attempt exposed a process-state inspection race in the concurrency test; the check was corrected before the successful build.

## v37 physical result (2026-10-29)

Source `b7cf1afb8eb0b33d87805239cb3bf48b25e54e95` passed [kernel CI 40716543231](https://github.com/eirblue/ios_note10p/actions/runs/40716543231). One physical diagnostic cycle passed all 35 evaluations, including both new observations. Automatic return to TWRP and all five post-test partition hash checks passed; battery immediately before installation was 90%. A GIC restore-default mismatch was observed and recorded as an observation, without treating it as a failed capture or an eligibility decision.

The physical diagnostic did not invoke CPU-PM. XNU execution, iOS boot and global DMA shutdown remain unverified. Device-specific callback inventories, memory fields, register words and raw logs remain private.
