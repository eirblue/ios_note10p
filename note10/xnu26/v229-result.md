# v229 bounded native ingestion

One target Image/PID1 CI passed: Image 50,401,292 bytes and linked extent 57,098,240 bytes, within the 57 MiB cap.

The physical cycle reported 19,185,664 bytes ingested into the existing reserved destination: kernel 19,169,280 bytes and adapter 16,384 bytes. The kernel receipt confirmed destination hash verification, result zero, and no quarantine. Runtime stack headroom was 14,920 bytes against the required 12,288 bytes.

One BOOT write and one host reboot were consumed. Normal paired TWRP return, all five partition checks, and TWRP/panel raw brightness 10 were verified. v229 is the installed baseline.

This is a bounded kernel-reported ingestion/readback result. The named RO holder and fixed pool total 6,258,688 bytes; measured linked non-init growth is 6,275,072 bytes, including 16,384 bytes of code/alignment. These figures are not additive. Runtime allocator/whole-OS RAM measurement, physical source pinning, native mapping, global no-replay behavior, and XNU execution remain unproven.
