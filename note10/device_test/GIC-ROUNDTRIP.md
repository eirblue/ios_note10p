# Reversible GICv2 CPU-interface diagnostic

The opt-in `gic_roundtrip=true` workflow input requires PM and automatic recovery.
It runs only after the restored devices-only PM test succeeds. The default is
off. This is a Linux CPU priority-mask roundtrip, not interrupt ownership transfer
or an XNU branch.

The helper is included in the SHA-pinned Linux GICv2 MMIO driver and uses its
per-CPU base accessor, including banked/non-banked configurations. With the
online CPU set locked, each of CPUs 0–7 saves local IRQ flags and reads CTLR,
PMR, BPR and identification registers. It requires an enabled interface and a
nonzero 8-bit PMR before writing. It writes only the CPU PMR: zero, barrier and
readback, then the original value, barrier and readback. The original value is
written even when the masked readback fails. CTLR/BPR are checked unchanged and
local IRQ flags are restored on every exit. No IAR/EOI, distributor, routing,
enable or binary-point writes are performed.

The distributor control/type registers are read-only observations. The probe
does not mask all CPUs at once, stop DMA, disable MMU/cache or transfer GIC
ownership. A failed restoration remains a failed diagnostic; normal one-shot
recovery is still requested, but cannot guarantee recovery from a hard lockup.

`N10GIC1` per-CPU and `N10GIC2` summary records use the same build identity and
frame checksum as the existing diagnostic. The collector first selects the
current boot/cycle and requires the successful PM chain. It then requires at
least two intact matching GIC records per CPU and two successful summaries.
Missing records, duplicate sequences, changed state or failed readback reject
the entire test. The payload SHA256 is checked again after the GIC probe.

Actual Image markers and config determine scope. Missing metadata cannot opt
out of the new gate. Source, decoder and actual-C model hashes are checked
before packaging and device installation. Native tests execute the actual
backend and producer with banked-MMIO and CPU/IRQ stubs, including write-address
and value allowlists, restoration faults and strict real-checksum decoding.
PC models do not establish physical GIC behavior. Every new build still requires
its own physical cycle; raw logs and packed device images stay private.

On 2026-10-27 KST, source `576d134b2c75e8d952b1d50b35d424bf83bba053`
and CI run [40425216720](https://github.com/eirblue/ios_note10p/actions/runs/40425216720)
passed one physical SM-N976N cycle with screen logging disabled. All eight CPUs
reported 32 intact matching records: PMR `0xf0 -> 0 -> 0xf0`, CTLR `1` and
BPR `3` unchanged, and local IRQ flags preserved. The online mask stayed `0xff`.
The preceding devices-only PM/quiesce chain passed in one attempt with zero
USB, wake and restoration errors; all eight timer records and the staged XNU
payload SHA256 passed. The host observed the same device returning automatically
to a fresh TWRP boot and verified all five partition hashes after collection.
This verifies this reversible CPU PMR test on one cycle. DMA shutdown, interrupt
ownership transfer, MMU/cache shutdown and XNU execution remain unverified.
