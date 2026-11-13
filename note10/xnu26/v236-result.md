# v236 Selected OF Symbol Evidence

## Result

The v236 fixture passed 1 group, 10 variants, and 10 assertions. The parser now retains every text-symbol row by name, so duplicate names among unselected local symbols do not overwrite one another. It still requires each selected function name to resolve uniquely.

The successful full Image and PID1 build produced an Image of 50,401,292 bytes, a linked extent of 57,098,240 bytes, and a PID1 ELF of 7,728 bytes. The authenticated evidence contains 99,149 text-symbol rows and 1,109 unselected duplicate-name groups. The selected inventory contains 16 functions:

- `__of_find_all_nodes`
- `__of_find_property`
- `_raw_spin_lock_irqsave`
- `_raw_spin_unlock_irqrestore`
- `arch_find_n_match_cpu_physical_id`
- `arch_match_cpu_phys_id`
- `n233_capture_cpu_node_consistency`
- `n233_clear_consistency`
- `of_find_node_by_type`
- `of_find_property`
- `of_get_cpu_node`
- `of_get_parent`
- `of_get_property`
- `of_n_addr_cells`
- `strcasecmp`
- `strcmp`

All selected-function records resolved without unknown transfers or unresolved edges. The selected-function inventory is not a whole call-chain bound. Outlined helper instruction bodies, the leaf/stack classification of `strcmp`, and preempt-scheduling boundaries remain outside the completed proof; lookup-runtime bounds are also unproven.

## Execution

The reviewed source was published to `main`. One CI dispatch completed successfully, followed by one authenticated artifact GET and one Node OPEN. No package or device action occurred. The installed v229 baseline remains current, and the battery hold remains active.

## Scope limits

This result establishes selected static symbol evidence and the bounded Image/PID1 build. It does not establish a whole OF or scheduler stack bound, runtime hook behavior, CPU-node runtime observation, or physical readiness. No device query, BOOT write, reboot, or native runtime observation occurred.