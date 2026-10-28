# Guarded device late/noirq diagnostic

The v28 physical cycle passed all 16 evaluations. FSYS0A stayed on, while its
original power-off callback, USB predicate and control call each ran zero times.
The pinned suspend core returns at TEST_DEVICES before device late/noirq, where
the generic power-domain core can reach genpd_sync_power_off().

v29 adds default-off CONFIG_NOTE10_PM_NOIRQ_TEST to the existing advanced UFS
profile. Only the bound diagnostic owner, MEM state, active quiesce generation
and enabled local interrupts may extend to TEST_PLATFORM. Runtime platform
prepare, prepare_late, wake and finish callbacks must all be absent. CPU disable,
syscore and platform sleep entry remain blocked even if the test stop is missed.
The caller returns through the original device resume path without suspend_again.
Normal device late/noirq and reverse callbacks do run; this is a physical power
management test, not just a new software marker.

N10PNQ1 records entry and completion, N10PNR1 binds the original PM result and
early/noirq restore failure counters, and N10PND1 records a separate 16-domain
configuration/status/configuration snapshot. Each lane requires consistent
checksummed duplicate frames and the same transaction generation. A restoration
failure becomes EIO so an EBUSY retry cannot hide it. The noirq snapshot uses 48
existing PMU_ALIVE reads with no device locks or peripheral reads. Its prerequisites
include successful regular-stage PMU samples from the same generation. The
existing three PMU snapshots and v3 evidence remain separate.

The PC checks passed 254 regression tests, 45 actual suspend caller/enter C
scenarios, 63 noirq PMU scenarios, 88 existing PMU scenarios and 24 original FSYS
callback scenarios. They cover every new read fault, invalid ownership/state,
platform callback rejection, counter changes, generation wrap and unchanged
default-off behavior. CI and the single v29 physical cycle passed.

The bundled cycle requires two additional evaluations: pm_late_noirq and
noirq_pmu_domains, alongside the previous 16. Sequential domain bits and balanced
software callbacks cannot establish complete DMA shutdown, secure-world state,
GIC/MMU/cache handoff or execution of XNU/iOS. Screen logging stays disabled.

## v29 physical result, 2026-10-28

Source `9ccbc059f4333c4fa4d2d44ab7d7ca42abc206d1`, CI
[`40611852128`](https://github.com/eirblue/ios_note10p/actions/runs/40611852128)
passed the single new-build physical cycle with all 18 evaluations. Automatic
TWRP return and five post-test partition hashes passed. Battery was 35% before
installation. Raw logs, device identifiers and images remain private.

Late and noirq each entered and returned successfully once. The diagnostic
stop was reached once, with no blocked fall-through, platform callbacks or PM
error. Early/noirq resume error counters stayed 0/0. Four consistent frames per
new lane bound these observations to the same transaction.

The regular pre-suspend domain masks were 0x4000/0x4000/0x4000: FSYS0A on.
The separate noirq configuration/status/configuration masks were all 0x0000:
all 16 sampled domains off at their individual read times. The restored regular
sample was 0xffff/0xffff/0xffff. The FSYS trace recorded one entry, exit, USB
predicate allowance, original control call and completion; denial, skip and
control errors were all zero. There were no extra predicate or power requests.

This establishes the guarded late/noirq roundtrip and the bounded domain
observations for one physical boot. It does not prove globally stopped DMA or
XNU execution. The next read-only observer should distinguish immediate resume
state from a later settled state before attributing the all-on mask to a leak.
