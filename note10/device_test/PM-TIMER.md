# Devices-only PM and timer roundtrip (v6)

This opt-in batch requires the v5 RAM, XNU data staging and CPU/cache tests to
succeed first. A delayed system work item waits for SYSTEM_RUNNING before using
the Linux suspend framework, avoiding the initcall/freezer dependency.

The pinned suspend implementation is instrumented under pm_mutex. Only the
owning diagnostic task selects TEST_DEVICES; the previous mode is restored at
exit. Other suspend callers are refused while the diagnostic is active. A
separate guard blocks suspend_enter if the devices-test exit is missed.
Success requires exactly one devices-test phase and one resume completion,
zero blocked low-level attempts and no additional resume errors. This exercises
driver callbacks and can hang or leave the display blank. It does not prove all
DMA engines stopped. Drivers are resumed before continuing.

The payload SHA256 is checked before and after PM and after the timer test.
On every CPU, CNTKCTL_EL1 event-stream selector bits 7:4 are temporarily cleared,
read back, restored unconditionally and read back again. All eight CPUs must
return their original values and report a 26 MHz counter frequency. Linux MMU
and caches remain enabled. No GIC handoff or XNU execution occurs.

N10PMT1 summary and N10TMR1 per-CPU frames carry build ID, unique sequence and
checksum. At least two intact records per family and CPU, from the same latest
boot interval, are required alongside all v5 evidence. Older boots cannot fill
missing phases. A damaged start banner requires an exact intact panic banner
inside the same interval plus build-bound evidence; no text is repaired.

PC tests execute the actual worker/backend C with modeled PM, scheduling and
register APIs and real SHA256 (24 cases). Contract tests check the pinned source
patch and strict evidence decoder (5 cases). Physical device behavior remains
pending the manual v6 test. Use workflow inputs caps, reserve, window_access,
xnu_stage, cpu_cache and pm_timer. Installation and reboot remain manual.
