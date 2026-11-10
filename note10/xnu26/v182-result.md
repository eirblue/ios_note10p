# Executable prefix from a padded APFS chunk

The initial strict PC consumer reached the end of a checksum-valid ZLIB stream and rejected the bytes remaining inside the declared APFS chunk. That original attempt remains recorded as unsupported.

A subsequent consumer applied the source-defined APFS padding rule to the retained compressed buffer. It kept the trailing bytes opaque, preserved their separate length and digest, and passed the decoded header and load commands to the existing parser. The prefix matched the retained executable identity, architecture and declared dynamic linker path.

This establishes a bounded decoded executable prefix in the recorded filesystem namespace. Whole file authentication, active boot root selection, kernel storage ownership and native execution remain unproven.
