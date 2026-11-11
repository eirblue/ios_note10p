# v201: current native handoff model

The PC-only consumer passed six metadata-denial checks, then constructed and loaded one handoff from the current v200 linked inputs. It read and verified the current kernel and adapter contents once each. The model covered 1,078 linked inputs and materialized four buffers totaling 19,218,432 bytes; all four buffers were consumed once. The kernel portion of the model occupied 19,169,280 bytes.

The addresses and descriptor used here are synthetic PC reference values. They do not represent device addresses or a live mapping. The earlier v200 result correctly recorded that it had not re-read or rehashed the kernel; v201 performed one current read and hash for this model.

No compiler, CI, artifact download, extraction, runtime copyin, task-map ownership, firmware check, native activation, or device operation occurred. The result does not establish physical device behavior.
