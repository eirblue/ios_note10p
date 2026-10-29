# Paired EHLD irqsave tokens

The v46 experimental `--ehld-irqsave-audit` option is off by default and requires `--ehld-lock-audit`. Its measured configuration marker is `CONFIG_NOTE10_EHLD_IRQSAVE_AUDIT`. The builder changes only the EHLD updater's saved-token variables and arguments, plus the new default-off Kconfig definition.

The updater saves the outer main-lock token separately from each inner control-lock token. Releasing an inner lock keeps IRQs masked while the main lock remains held. Releasing the outer lock restores the original entry state. Lock order, critical-section operations, and diagnostic output remain the same.

The pinned watchdog timer, hardlockup-notifier, and panic-notifier paths identified in the source enter with IRQs disabled. Reusing one token is therefore a conditional latent defect for IRQ-enabled entry; no corresponding device failure has been observed. The source review does not establish an exhaustive caller graph.

The actual-function host model covers 31 cases, including expected rejection of the original token reuse and premature IRQ enable from an incorrect inner-unlock token. It checks lock nesting and all combinations of the other DAIF mask bits with IRQs enabled and disabled. These synthetic cases establish modeled source behavior, not IRQ-enabled hardware reachability or hardware restoration.

The added binding checks source reconstruction, configuration, model evidence, and package scope. The existing 42 evaluation rows, including 41 required checks, remain unchanged. This change adds no perf-event dereference, CPU-PM invocation, hardware probe, or runtime observation. Event lifetime, XNU execution, and iOS boot remain unverified. The v46 kernel build and one physical regression cycle completed successfully.


## Verified v46 result

Source commit `0188d99a5b958789cf0790a410800db9911b2879` passed [CI 40883405339](https://github.com/eirblue/ios_note10p/actions/runs/40883405339). Review of the actual artifact passed all 24 source/configuration/model bindings. The final source snapshot changes exactly the EHLD updater and Kconfig; the other 76 of 78 entries match the v45 baseline.

One physical diagnostic cycle passed all 41 required checks among the unchanged 42 evaluation rows. Automatic TWRP return and all five post-return partition hashes passed. After integrity verification, TWRP and panel brightness were verified at raw value 10 both before and after the cycle. Battery was 93% immediately before installation.

The 31 actual-function host cases cover modeled IRQ-on and IRQ-off entry, including the two expected negative controls. The physical regression does not establish IRQ-on entry reachability or event lifetime. No direct CPU-PM invocation, event dereference, XNU execution, or iOS boot was performed.
