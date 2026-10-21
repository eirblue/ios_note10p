# Android PAC hint interception experiment

`test_hint_intercept.c` tests actual CPU execution and signal-frame return on SM-N976N.
It uses freshly allocated synthetic AArch64 instructions, never an Apple binary or firmware image.
It is an Android test harness, not an XNU exception handler or a Mach-O rewriter.

## Method

- Construct a small function with PACIASP, XPACLRI, PACIASP, AUTIASP and a normal RET.
- Make one original page and one copy whose four hint sites contain `BRK #0x4e10`.
- Write pages while RW, flush the instruction cache, then change them to RX before execution.
- For the copied function, handle SIGTRAP only at the four registered sites with the expected BRK word.
- Dispatch through a validated immutable site table, which feeds the registered original instruction
  and saved general-purpose registers/SP/PC to `n10_step_pac` (see [HINT-SITES.md](HINT-SITES.md)).
- Verify the modeled LR, preserve other registers and signal-frame PSTATE, and resume at PC+4.
- Check signing changes LR and both strip and authentication restore its original value.
- Return through the original LR and check the function result. Restore affinity and the signal handler;
  unmap both pages on normal completion.

The experiment supplies public test keys and the existing restricted 48-bit lower-range QARMA5 profile.
This profile is not a validated Apple ARM64e_X1 PAC ABI.
The native sequence is a no-trap baseline; it does not independently measure each hint's effects.

## Actual result

On all eight available SM-N976N cores, 64 iterations per core:

```json
{"cores":8,"native_hint_calls":512,"patched_calls":512,"handled_brk_traps":2048,"signed_lr_changes":1024,"passed":true}
```

The temporary executable was removed from `/data/local/tmp` after testing.
Host results and executable hash are recorded in `note10/private/hint-intercept-test-result.json`
and `note10/private/hint-intercept-build.json`.

## Remaining integration

This establishes that explicit BRK instrumentation can invoke the model and return correctly in
an Android process on the target CPUs. It does not intercept unmodified iOS code.
Private image manifests and portable slide-aware site lookup are now available as research components.
There is no production kernel site registry, signed-code policy, dyld-cache coverage,
executable-page lifecycle, XNU exception integration, or validated Apple key lifecycle.
Kernel exception context and synchronization need separate implementation; this signal handler is test-only.
The three legacy hint forms exercised here do not establish coverage for all thirteen supported hint forms,
new ARM64e_X1 instructions, or architectural PSTATE/BTI effects.

Build with `./note10/compat/build.ps1`. Device execution is deliberately a separate operation.

Primary references:

- [Linux AArch64 signal context](https://github.com/torvalds/linux/blob/master/arch/arm64/include/uapi/asm/sigcontext.h)
  defines the saved general registers, SP, PC and PSTATE.
- [Arm instruction set reference](https://documentation-service.arm.com/static/6245c734b059dc5ff9a8bdab)
  describes BRK as generating a breakpoint instruction exception.
