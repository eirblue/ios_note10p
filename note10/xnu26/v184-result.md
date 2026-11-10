# v184 dyld entry buffer result

- The new synthetic fixture passed all three groups (47 cases total). It read no actual input.
- The actual composition passed with one read of the previously admitted 65,536-byte buffer, one mapper call, and one entry-buffer extraction. It resolved PC `0x30f0` to file offset `12528` in `__TEXT,__text` and produced the requested four-byte buffer.
- The separate admission read was already spent before this run; v184 did not repeat it. One earlier fixture process stopped during preflight because the bounded owner-ACK file cap was too small. The cap-only correction was reviewed; that failed preflight performed no fixture cases or input read and was not replayed.
- Image reads, backend work, decoding, old tests, compilation, CI, device operations, and instruction execution were all zero. The result does not authenticate the whole file, establish runtime memory mapping, or prove physical readiness.
- N184 retention review covered v181, newly eligible at cutoff 181. All eight generated binary candidates are retained as consumed evidence or shared dependencies; no files were deleted.
