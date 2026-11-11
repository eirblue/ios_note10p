# v194 controlled owned-page fetch

The v194 host check passed with one new compile and one fixture process. It loaded one previously observed 16 KiB page, called the existing fetch consumer, and completed one four-byte backing callback. The synthetic copyin service reported the expected status and left the saved frame unchanged. Three synthetic groups covered 27 cases; seven owner-denial cases made no backing callback.

The owner and map were represented by synthetic tokens. This was a controlled host fixture: it did not verify a real task or map, exercise kernel copyin at runtime, authenticate the original page, admit an executable input, install a mapping, or execute an instruction. Those authority flags remain false.

The run read three bounded metadata records and one page file. It made no other page, decoded-unit, or header reads. Tool-binary hashes and the freshly generated fixture-artifact hash were counted separately from the page read. Backend, decoder, scan, old-suite, device, CI, and publication counts were zero.
