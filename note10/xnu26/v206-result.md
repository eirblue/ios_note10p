# v206 Storage Header Inventory

The v206 source was published at commit `b49379f2485319d75f97c4303c1c1eeac7c2d83e`. CI run `43043467109` completed successfully. Its first-stage synthetic fixture passed 28 focused cases across three groups (8, 12, 8). The earlier Windows-host fixture attempt failed with case completion unobserved; that spent failure is preserved and was not replayed.

The bounded inventory completed coverage of 15 required header names and 23 source probes across seven configured SDK, private-header, and compiler-resource roots. It observed 45 unique header files, totaling 785,437 source bytes. One required header, `IOKit/perfcontrol/IOPerfControl.h`, was not found in those queried roots; no required header was rejected or left unobserved.

This result is an inventory only. It did not admit a header interface or close a compile recipe, and it performed no IIG generation, compiler translation, object build, kernel link, or device action. The inventory does not establish runtime registration, provider ownership, or firmware behavior.
