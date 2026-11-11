# v204 read-only RAM nub native-link result

The v204 synthetic fixture passed 43 cases in three groups. The one accepted CI run (43016946791) completed successfully and linked the opt-in native kernel with 1,078 inputs. Static provenance verified the read-only RAM storage nub, PIO bridge, C read core, lock aliases, and checked user-instruction fetch path in the linked result.

The authenticated artifact download and extraction each occurred once. The first receiver pass stopped at its final source-map comparison because local CRLF hashes differed from the Git commit’s LF hashes; the committed source map matched the observed CI map. A separate, reviewed semantic continuation then passed six source-binding guards and the remaining metadata join. It read bounded JSON metadata, checked the current kernel file by its recorded identity and size, and relied on the original authenticated streamed-extraction digest. It did not reread or rehash kernel bytes, redownload the artifact, or repeat extraction.

This is static build and artifact-provenance evidence. It does not establish runtime IOKit registration, a live backing owner, runtime copyin or task-map behavior, firmware ABI compatibility, or kernel execution on a device. The physical baseline remains v189; no device actions occurred in v204.
