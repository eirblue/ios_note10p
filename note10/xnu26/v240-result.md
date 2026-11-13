# v240 guarded CPU-node candidate result

The new host fixture passed 1 group, 31 variants, and 150 assertions. It used one host compile and one host process. No old tests or native inputs were read.

The single full Image/PID1 CI attempt failed in the outlined-function collector. Image and PID1 compilation/linking completed before that failure. The collector accepts only reviewed direct outlined-helper entry records; it rejected the owner call-site scope. The observed OUTLINED_FUNCTION_15 is itself an outlined helper, distinct from a similarly named helper. The failed run was not retried.

The authenticated diagnostic receive used one GET and one Node OPEN. It opened 12 selected text members and opened no binary members. The received metadata reports an Image size of 50,401,292 bytes and a linked extent of 57,098,240 bytes. Persisted layout metadata gives 41,697,280 linked non-init bytes, 6,258,688 bytes for the named native holder plus pool, a 49,152-byte fixed pool, derived growth of 6,275,072 bytes versus v225, and zero derived growth versus v229. These growth values are derived from the saved layout; the failed collector did not produce final build growth fields.

The static frame records are 64 bytes for n240_observe_current_cpu, 16 for n240_room, 32 for n231_capture_cpu_observation, 80 for n226_ingest_prepared_locked, and 800 for n210_write. A 992-byte static inventory was recorded, but it is not a recursive stack bound. Runtime headroom was not measured, runtime behavior was not observed, and whole-stack safety was not proven.

No package or device stage ran. The installed v229 baseline remains in place and the battery hold remains active.