# v228 source-stream candidate

The new section-transform fixture passed two assertions. One target Image and PID1 compiled with zero return codes, and the strict compiled pool placement check accepted the BSS/NOBITS layout.

Overall CI failed at the assembly leaf proof. The three symbol-filtered disassembly logs contained no function labels or instruction bytes despite defined ELF symbol extents, so the complete extent check correctly rejected them. A fresh v229 producer captures those exact address ranges while retaining the strict proof requirements.

No v228 native package or hardware test ran. The installed baseline remains v225; native input RAM, ingestion, mapping, and XNU execution have no new physical approval or proof.
