# v286 PC validation result

The v286 Linux image and PID1 compiled, but its producer verifier did not pass the restore-tail predicate for `n217_page_io`. The predicate compared the entire function suffix after the outlined restore call with the expected two-instruction `pop80; RET` window. The captured control flow contains reachable basic blocks after the unique RET that branch back through the shared restore helper and epilogue.

The v286 verification attempt and its artifact transfer were spent. No retry was performed. No device RPC, BOOT write, reboot, recovery write, or XNU transfer occurred. This result does not establish device readiness, carrier eligibility, or hardware handoff.
