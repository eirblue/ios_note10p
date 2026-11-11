# v191 dyld and launchd entry-page check

The corrected v191 PC-only composition passed. It evaluated the 16 KiB pages containing the dyld interpreter entry and launchd executable entry against their file-backed text segments and completed decoded units, and checked the file-to-virtual page relationship. The launchd page was contained by its text section. The interpreter page crossed its text-section boundary but remained within the validated file-backed segment and decoded unit. This was a metadata check; it did not read either page's payload bytes, install a mapping, or transfer control.

One synthetic group rejected eight inconsistent page and authority cases. The composition read five bounded JSON metadata inputs. It reused the earlier v185 launchd-entry metadata result without rerunning v185.

The first v191 metadata invocation stopped at an overstrict paired-prefix byte-accounting guard. Its failure record is preserved. After the guard was corrected, one fresh composition passed and read the five required JSON inputs again. Across both attempts, there were ten metadata reads and no binary-content reads, decoder calls, backend executions, CI runs, device operations, mapping installation, or instruction execution.

This result validates a bounded metadata join. It does not authenticate the whole file, prove runtime mapping, establish physical readiness, or demonstrate XNU execution.