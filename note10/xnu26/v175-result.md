# Actual file bytes through the read path

The PC integration read one 4 KiB block from a retained image through the production C range and request helpers. The read and inline completion ran once each. The file stayed open through completion and closed before the completed bytes reached the parser.

Existing APFS byte parsers verified the transferred buffer and decoded the recorded directory entry. A modified copy failed its checksum check without another image read.

This establishes a bounded host data path. Kernel storage ownership, the Apple descriptor runtime, active boot root selection, filesystem mounting and native execution remain unproven.
