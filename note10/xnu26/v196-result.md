# v196: Biased entry frame fetch

The host validation passed after a test-only correction. The first compile attempt failed on signedness checks before starting the fixture or reading the page; that failure remains recorded. The corrected run compiled once and passed 16 synthetic cases across three groups. Twelve negative cases preserved the output frame and made no fetch or backing read.

The positive case used an explicitly declared model bias of 32 KiB. It loaded one retained 16 KiB page, produced the modeled entry frame, and called the existing fetch consumer once. The backing callback returned four bytes and the frame remained unchanged. This is a controlled host model; it does not establish a live task-map owner, kernel copyin, executable input admission, native activation, an installed mapping, or launch authorization.

No device operation, CI run, publication action, backend, decoder, scan, or old-suite rerun occurred in this test sequence. The v189 installed physical baseline remains unchanged.
