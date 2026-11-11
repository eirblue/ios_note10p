# v195 controlled initial-interpreter fetch

The v195 host check passed through the existing instruction-fetch consumer with a synthetic task/map owner. It loaded one previously observed 16 KiB interpreter page, derived the 72-byte segment-rights window from that in-memory page, and completed one four-byte backing callback. The observed initial and maximum protections were read and execute, with write absent; the saved frame was unchanged. Five focused guards covered entry-role, page-role, interpreter-link, executable-entry, and segment-role mismatches. All passed; the earlier 27-case fixture was not replayed.

This was a controlled host fixture. Its synthetic owner tokens do not verify a real task or map, and the host copyin service does not demonstrate kernel copyin at runtime. The page remains unauthenticated against an original image. No executable input was admitted, no native activation or mapping was installed, and no instruction was executed.

The run used one compile and one fixture process, five bounded metadata records, one 16 KiB page-file read, and one four-byte backing callback. It made no other page, decoded-unit, or header-file reads. Tool hashes and the generated fixture-artifact hash were separately counted. Backend, decoder, scan, old-suite, device, CI, and publication counts were zero.
