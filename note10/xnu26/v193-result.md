# v193 launchd entry rights observation

The v193 PC-only check passed after reading one 72-byte window from the retained launchd header. It observed the entry segment’s initial and maximum protection as read and execute, with write absent. One synthetic group passed six guards for unsupported rights, segment geometry, entry-page placement, and short reads.

The check read three bounded JSON records and made one open, seek, and read. It did not reread the complete header or any decoded page, admit a new input, authenticate the original page, or verify the owning task and map. Mapping, launch, and instruction-execution authority remain false; the observation does not establish runtime protection or physical readiness.

The six new synthetic guards passed. Backend, decoder, scan, compiler, old-suite reruns, CI, publication, and device-operation counts were zero. The v190 physical cycle remains pending; v189 remains the installed physical baseline.
