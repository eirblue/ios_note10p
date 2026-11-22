# v330 reaches the IOPanicPlatform::start checkpoint after a one-shot SPI disable: objective met

**Safety, return and objective PASS.** Source `798f55581cdd65bc3771223fb8189060379b353a` built successfully on the first attempt in CI run `45034701985`. The v330 fixture (2 groups, 4 variants, 4 assertions) passed; earlier checks were not replayed. The v321 device tree and validator, the v316 stub and the v316 Linux sources were reused unchanged. The only public change is the record tag `N330PS20`, so the cycle ran a new reviewed build and no spent build was replayed. **The predicted `IOPanicPlatform::start` checkpoint was reached.** Core 0 stopped at that checkpoint and in no interrupt identification slot.

In v329 core 0 stopped in the slot for ID 502, an SPI. A read-only analysis afterwards matched ID 502 (SPI 470 in device-tree numbering) to local timer 0 of the Exynos multi-core timer, which Linux uses as CPU 0's tick. Linux's last programmed tick expires while XNU runs and raises a level-triggered interrupt that nothing clears. That identification is offline analysis, not device evidence. The device tree also lists a few hundred other SPIs that Linux may leave enabled and routed to CPU 0, so fixing one source per build would not end.

v330 bundles:

- **One-shot SPI disable.** The owner approved revising the earlier "no new distributor writes by our patch" decision for this one change. A private patch extends the v329 pre-unmask stub. After the PMU quiesce, and still with interrupts masked before XNU's first unmask, it writes all ones once to each GIC distributor clear-enable register `GICD_ICENABLER1` to `GICD_ICENABLERn`, through XNU's own distributor mapping:
  - `n` comes from XNU's own probed interrupt line count, so every SPI (ID 32 and above) is disabled
  - register 0 is not written, so SGIs and PPIs, including XNU's timer interrupt 30, are unchanged
  - pending state, priorities, targets and the CPU interfaces are not changed

  It then continues into `ml_set_interrupts_enabled`. It makes no other device write.
- **Filter and markers kept.** The v328 filter (interrupt 30 serviced by XNU, any other ID spins at its slot without acknowledge), the v329 PMU quiesce, the FIQ, SError, synchronous-exception and earlier markers, and the `IOPanicPlatform::start` checkpoint all remain.
- **Caveats.**
  - Code-signing trust is not enforced, because trust caches are not loaded.
  - Randomness is predictable, the per-CPU random contexts are dummies, and no integrity cryptography is provided.
  - XNU acknowledges and ends interrupt 30 at the GIC CPU interface. CPU 0's PMU state and the distributor's SPI enables, as left by Linux, are discarded. The watchdog reset restores the GIC for the normal return.
  - This build is for diagnostic boots only.
- **Unchanged.** Everything else is identical to v329.
- **Offline prediction.** The emulator added interrupt 502 as pending from the start, on top of the v329 PMU and timer models.
  - In that emulation the stub disabled every SPI before the unmask, neither 502 nor 173 was delivered, one timer interrupt was serviced by XNU, and XNU stopped at the `IOPanicPlatform::start` checkpoint.
  - A counter-run without the SPI disable reproduced the v329 stop in slot 502.
  - The emulator models only the timer, the PMU interrupt and interrupt 502. No other interrupt source is modeled.

On the device, the stub ran every check, committed the `N330PS2T` record and branched to XNU. The record, bound to the current build, boot and cycle, matched the precomputed values exactly.

After the reset, the log read back from the previous boot held all three v315 breadcrumbs, in order, directly after the record. The builder code was 0. The boot loader's next log block reported a cluster-0 watchdog reset, with core 0 stopped at the `IOPanicPlatform::start` checkpoint, as predicted. Normal TWRP returned in a distinct boot epoch about 57 seconds after the actor started, within the 240-second bound. All five partition integrity checks passed, and the recovery setting and panel brightness both read back 10. The cycle used one BOOT write, one host reboot, one actor invocation and one XNU branch; RECOVERY writes and rollback BOOT writes were zero.

**What this shows.** With the SPIs disabled at the distributor before XNU's first unmask, no interrupt identification slot was reached, and XNU's bootstrap ran on through IOKit matching to the masked `IOPanicPlatform::start` checkpoint. XNU stops there because no platform expert matches this board.

**What this does not show.**

- How many timer interrupts XNU serviced on the device. The filter leaves no trace for ID 30.
- That the SPI disable alone made the difference. The device leaves no direct trace of the stub; the result matches the prediction, which is consistent with it having worked.
- That no SGI or PPI other than 30 can arrive later. Those are not covered by the disable and would show as their slot.
- That any device XNU later needs works. All SPIs now stay disabled until XNU itself enables them.

Next is the platform-expert decision: either a platform expert for this board inside the image, or a non-fatal diagnostic path past `IOPanicPlatform::start`. Both need an owner decision. Interrupt policy for devices XNU will use, IOKit platform matching, trust-cache handling and independent native return remain unproven.
