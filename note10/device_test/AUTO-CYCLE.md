# Note10 diagnostic cycle preparation

Status (2026-10-26): full Linux CI run 40325362180 succeeded. The first
physical automatic install → diagnostic boot → recovery → log capture completed.
The kernel's request was observed at uptime 93.16 seconds and TWRP returned
with a new boot ID. Normal-restart last_kmsg persistence and all five post-return
partition hashes were checked. RAM/XNU-data/CPU/cache and eight timer register
roundtrips passed; the PM device phase aborted with EBUSY in all three attempts.
The whole diagnostic did not pass, so repetition commissioning remains disabled.
The original v7 kernel cannot be used for automatic recovery.

## Flow

Prepare immutable plan and per-cycle BOOT/ZIP pairs → inspect exact plan hash →
explicit single-cycle execution → TWRP CLI install → verify BOOT and four other
partitions → System boot → kernel requests recovery after 90 seconds → wait for
the same device in TWRP with a new recovery boot ID → preserve logs → check
current-cycle evidence and all five partitions → record a verified single cycle.

The opt-in kernel uses a dedicated non-freezable workqueue and calls the pinned
Samsung recovery restart route once. It does not depend on diagnostic ADB.
The 90-second request is a deadline, not a diagnostic success claim. Only the
full RAM/XNU-data/CPU/cache/PM/timer evidence can establish a diagnostic pass.
A kernel hard lockup, stuck shutdown driver or firmware issue can prevent
recovery; the PC stops after 240 seconds and does not resend install/reboot.
A manual recovery step may still be needed.

Every cycle has a fresh 128-bit token in a fixed 32-byte volatile kernel data
slot and N10RET1 records. Packaging copies the compiled template, changes only
those 32 bytes, and verifies exact equality against the template plus token.
The original compiled template stays unarmed. BOOT command-line propagation
is not required. Missing or malformed tokens prevent arming. The collector
requires at least two intact arm records and discards everything before the
current cycle arm. This prevents an earlier successful boot of the same Image
from filling missing diagnostic records. No raw bytes are repaired.

## Preparation commands (no device access)

1. Build with the existing PM/timer inputs and the new `auto_return=true` input.
   It defaults to false. Uploading this local source or dispatching CI is a
   separate action; neither was performed by this preparation task.
2. Download the successful artifact and create its minimal-init model report
   using `test_minimal_init.py ELF --report REPORT`, as for v7 preparation.
3. Run `auto_cycle.py prepare` with these explicit paths:

   - `--kernel-build`: downloaded handoff-kernel directory
   - `--backup`: verified five-partition backup
   - `--twrp`: pinned reference TWRP image
   - `--mkbootimg`: pinned AOSP mkbootimg script
   - `--current-packages`: verified diagnostic pair currently in BOOT
   - `--output`: fresh directory under note10/private
   - `--cycles 1`: first plan; at most five are supported later

   Preparation prints the plan path and SHA256. It creates distinct cycle tokens
   and BOOT payloads, and chains each installer's expected current BOOT to its
   predecessor. It does not call ADB.
4. `auto_cycle.py inspect --plan PLAN --plan-sha256 SHA` rechecks the exact plan,
   artifacts, package digests, BOOT cycle tokens and embedded kernel identity.
   Inspection does not contact a device.

## Execution after connection and explicit start

The execution command is `auto_cycle.py run` with `--plan`, `--plan-sha256`, a
fresh private `--output`, and `--execute`. Without `--execute` it refuses before
constructing ADB. The default `--limit 1` performs one automatic roundtrip.

The initial device must be the paired SM-N976N in root TWRP, with at least 30%
battery and the exact five-partition baseline. The CLI must be `/sbin/twrp`.
The device serial is bound for the whole run; journals store its hash. Installer
errors, low battery, changed partitions, stale recovery boot IDs, missing cycle
records, diagnostic failures and timeouts stop the run. Ctrl+C records a stopped
journal. There is no automatic rollback or repeated reboot on failure.

Multiple cycles require a prior successful single-cycle journal, supplied with
`--verified-roundtrip` and its reviewed `--roundtrip-sha256`. That proof must
match the exact compiled template Image, original backup and connected device.
Only verified 32-byte token variants of that template share commissioning proof.
A new compiled template requires another single-cycle commissioning run. Even then the explicit limit
cannot exceed the finite prepared plan, and every cycle must pass before the
next starts. A stopped plan is not automatically resumed; prepare a new plan
against the installed BOOT after reviewing the captured result.

## Checks and limits

- Actual auto-return C: ten modeled cases, including no token, malformed token,
  queue allocation/scheduling errors, init not finishing, delayed running state,
  duplicate arm, unexpectedly returning restart and one-shot enforcement.
- Host/source/evidence/data-slot contracts: twenty-three cases using in-memory ADB substitutes.
- Collector regression: nineteen cases including old-success-before-new-arm
  rejection. Reservation integration includes the opt-in auto-return path.
- Kernel/PM/register/restart APIs are modeled. These results do not establish
  physical recovery selection, normal-restart log persistence or hard-lockup
  recovery. The first real roundtrip remains required.

Public references used for design: [TWRP command-line guide](https://twrp.me/faq/openrecoveryscript.html),
[pinned Samsung recovery restart](https://github.com/corsicanu/android_kernel_samsung_universal9820/blob/55f042627bb7030c93550faafa117674d32b21d1/drivers/samsung/sec_reboot.c),
and [pinned restart log dump](https://github.com/corsicanu/android_kernel_samsung_universal9820/blob/55f042627bb7030c93550faafa117674d32b21d1/kernel/reboot.c).
Raw logs, device identifiers, addresses, backups and ZIPs stay private.
