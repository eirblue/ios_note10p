# v243 conditional query proof

The corrected v243 synthetic fixture passed all 31 cases and assertions. The v242 fixture failure remains recorded and was not retried.

One conditional text proof evaluated the unchanged v241 target at source head e07129664f1475b9576c45aa0ec44511ea6e9f53 (CI run 43413072923). The v243 analysis source is 378de3f8a977492c87a3ad7d9930c0be0a627fb4; the proof core retains the v242 schema. No new target kernel was built.

The proof reports a 576-byte conditional bound across 35 captured query bodies, for the interval from the successful pre-room sample to before outer release. The compiled outer-span predicate is present, with one compiled node caller and a 32-byte capture frame. The 8192-byte cap and 4096-byte guard are limits used by the proof.

The bound assumes normal ABI and valid arguments and the stated outer preemption-count condition. The outer-release scheduler call remains reachable and its stack bound is unknown. Atomic duration, IRQ/NMI bounds, the whole guarded caller/kernel stack, runtime admission, and runtime observation are not proven.

There were no CI dispatches, artifact GET/OPEN operations, package runs, or device queries for v243. The installed v229 baseline remains, with the battery hold in effect.
