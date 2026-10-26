# Devices-only PM and timer roundtrip (v6)

## Owned driver quiesce before PM (2026-10-27)

Kernel and XNU porting take priority; the screen console provides supporting
diagnostics. The v8 physical test returned EBUSY at all three attempts before
filesystem sync began. The pinned Samsung `intr_sync` checks the active wakeup
count before starting I/O. Delaying retries and pausing the screen worker did
not release the USB and DECON driver wake locks.

`CONFIG_NOTE10_PM_QUIESCE` is separate from the screen console and defaults off.
The opt-in PM build enables it to stop DECON through its normal power API and
temporarily block the USB peripheral through the existing CLIENT policy. It
preserves physical cable state, waits for the notifier queue and targeted OTG
worker, and checks FSM, PHY ownership, runtime PM and wake-lock state. Vendor
disconnect, PHY, runtime-PM and bus-idle errors must remain errors; software
role flags alone cannot establish a successful stop. Existing sync, wakeup,
notifier, freezer and TEST_DEVICES checks remain in use.

Every exit requests reverse restoration of USB, display and screen logging.
INIT is a boot handoff marker: after normal power down it is restored through
the normal API to operational ON. Driver reinitialization can replace the
bootloader logo. A failed or incomplete restoration prevents a passing result
and prevents another EBUSY retry. Generation, physical cable epoch and bounded
completion checks reject late work and concurrent role changes.

Checksummed `N10QSC1` records preserve each attempt's ownership generation,
phase, PM call, restoration and individual error results. A build declaring
quiesce version 1 requires intact same-boot quiesce records as well as the
existing PM, CPU and timer evidence. Source hashes, generated driver hashes,
four configuration models and actual helper fault models are checked before
installation. These PC models stub kernel APIs and do not prove hardware.

A successful TEST_DEVICES roundtrip covers the normal preparation and driver
suspend/resume callbacks. It does not enter late/noirq/syscore suspend or prove
all DMA engines stopped, GIC ownership transfer, MMU/cache shutdown, or actual
XNU/iOS execution. Physical validation of this new quiesce path is pending.

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

## v6 prepared manual test

[Kernel run 40211700065](https://github.com/eirblue/ios_note10p/actions/runs/40211700065)
passed with the opt-in PM/timer diagnostic, 21 CPU/cache model cases, 24 PM/timer
actual-C model cases and 5 pinned-patch/decoder contract tests. A private BOOT
diagnostic and original-BOOT rollback pair was staged in TWRP RAM and passed
ZIP hash, native updater syntax and five current partition baseline checks.
The current BOOT baseline is the completed v5 diagnostic. Physical v6 device
PM behavior, timer restoration and recovery reentry still await manual testing.
No installation or reboot was performed by the preparation tools.

## v6 device results and v7 changes (2026-10-26)

Both manual v6 attempts returned EBUSY before the device suspend phase. The
same-boot checksummed PM summary reported zero devices/resume/timer counts;
wakeup sources caused the Samsung interruptible filesystem-sync path to abort.
The second capture established RAM reservation, write/read/scrub and XNU data
staging, but lacked enough intact CPU 4 records, so the overall test failed.
All five partition hashes matched the expected baseline. No evidence is repaired
or borrowed from the other attempt.

The v7 worker waits 30 seconds after the successful initcall prerequisites,
checks timer clear/restore first, then calls the guarded devices-only PM test.
Only a clean pre-device EBUSY can be retried, at 10-second intervals with at
most three total attempts. Each retry rechecks the CPU online mask and payload
SHA256. Active wakeup sources are respected; no wake lock is released or ignored.
Timer registers are restored before the first PM attempt and are not rewritten
by retries. Timer records can be preserved even when PM fails, while full PM
success still requires complete devices/resume evidence and unchanged SHA256.

CPU and timer snapshots now have 32 interleaved rounds across all eight CPUs.
The minimum remains two intact records for every CPU. N10TRY1 records identify
each attempt; N10BND1 repeats the actual Linux banner with build ID, sequence
and checksum. If the latest start banner is damaged, at least two exact matching
banner bindings within that interval are required for this new build contract.
Conflicting, duplicate, wrong-ID or earlier-interval copies cannot corroborate it.

Local validation executes 32 actual PM/timer C cases, 21 CPU/cache C cases,
8 source/decoder contracts and 18 collector cases. The PM framework and hardware
register APIs remain modeled; v7 hardware behavior awaits manual testing.

## v7 kernel build

[Kernel run 40240561031](https://github.com/eirblue/ios_note10p/actions/runs/40240561031)
passed from source ffc31fb, including the 21 CPU/cache and 32 PM/timer actual-C
model cases and 8 pinned-source/decoder contract cases. A private diagnostic
and original-BOOT rollback pair was created, staged in TWRP RAM and verified
against ZIP hashes, native updater syntax and the five current partition hashes.
Final device readiness is pending charging; no agent installation or reboot
occurred. Physical v7 PM/timer results and recovery reentry remain unverified.
