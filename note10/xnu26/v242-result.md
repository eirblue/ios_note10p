# v242 current query proof fixture result

The v242 proof-only fixture failed on its first new case. The 30-variant group was planned; no case completed and no assertion passed. The recorded assertion error was `current35 includes distinct owner and OF names`.

The source-level cause is a fixture-data omission. The synthetic `property_local_joins` rows supplied only a `name` record, while the existing `query_inventory` path expects `row.symbol.symbol`. The first property row therefore raised `KeyError('symbol')`. The production parser is unchanged.

This is a local analysis-fixture failure. No v242 proof attempt, target build, CI dispatch, GET/OPEN, package, or device action occurred. The target remains the already authenticated v241 build; its compiled node-caller count is one, while runtime observation and whole-query-stack proof remain false. The v229 installed baseline and battery hold remain in place. The spent v242 fixture was not retried.
