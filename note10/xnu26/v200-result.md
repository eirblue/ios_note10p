# v200: compact native kernel link

The new metadata fixture passed 28 cases across three groups. The reviewed source was published at commit `64d4612ef10dd06caa97f7f178b64d7f3ddadf5a`; CI run `42989095288` completed successfully with a full static native kernel link. Producer metadata reports 1,078 linked units and 1,079 target compiler jobs, including one auxiliary genassym compile; IIG completed 19 of 19 generations and MIG completed 106 of 106. The final link succeeded.

Authenticated producer metadata verified the three-source symbol chain from the synchronous exception handler to the USER64 fetch caller and native copyin implementation. The first receiver attempt authenticated and extracted the artifact but rejected the producer metadata because an empty undefined-symbol list was compared with a numeric zero. A scoped semantic continuation accepted the existing extracted metadata after six focused predicate cases and one join. It performed no second artifact download or extraction and did not read or rehash kernel contents. The original receiver failure remains recorded.

This is static link and symbol-provenance evidence. It does not establish runtime copyin behavior, task-map ownership, firmware ABI compatibility, activation, or physical device behavior. No device operation occurred; the installed physical baseline remains v189.
