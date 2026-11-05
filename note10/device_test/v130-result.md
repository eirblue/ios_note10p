# v130 sanitized physical result

- Reviewed source: `980bf90040b8312451f2ea67932a389951cf3b24`.
- CI: run `42025876494`, successful; one accepted Image artifact, 54,835,212 bytes.
- New v130 grouped gate batch: passed once; no old test replay; one private kernel input stream and one gzip compression; no device operations in the test batch.
- Physical cycle: one BOOT write, one host reboot, one internal kexec load and reboot; returned to TWRP; five-partition integrity passed.
- Outcome limit: final handoff gate and physical XNU entry were not proven; full XNU boot and formal watchdog reset cause were not proven. v130 cycle is spent and must not be replayed.
