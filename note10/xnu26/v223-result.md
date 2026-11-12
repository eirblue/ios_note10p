# v223 result

[v223 CI](https://github.com/eirblue/ios_note10p/actions/runs/43254016690) succeeded at source `3b8eb848e2e0bf27b278374677aa89bff5109bbd`. The new compiler-output stack-path checks passed (1 group, 8 variants, 8 assertions); v222 wire, v221 metadata and v220 macro results were carried without replay.

Authenticated evidence confirmed the actual `.tmp_init.su` sidecar and same-Image owner type/frame evidence. Image size was 50,466,828 bytes, linked extent 57,114,624 bytes and freestanding PID1 7,704 bytes. Image and linked extent remained below 59,768,832 bytes.

The sole local package attempt failed before BOOT construction. The inherited compositor required the cycle marker to precede the metadata slot. Recorded offsets instead place the slot at [33,436,616, 39,728,072) and the 33-byte marker at [46,259,304, 46,259,337), both within the 50,466,828-byte Image. These intervals are disjoint; their ordering caused the guard to reject them. Marker contents, uniqueness and fresh slot zeros were not evaluated after that rejection and are not claimed.

No package or plan was created. No battery/device queries, BOOT writes or reboots occurred; the installed physical baseline remains v208. Fresh v224 will bound both intervals and admit either disjoint ordering while retaining the existing content checks. v223 will not be retried.

The selected scope remains 256-byte descriptor plus 128-byte binding metadata in a 6 MiB slot, the existing 32 MiB reservation and zero native-input allocation. Fresh successful CI, measured class2 growth ACK and independent physical review remain required before device access. No native-ingestion or XNU runtime proof is claimed.
