# Reaching the executable storage boundary

The PC integration resolved the exact sbin and launchd names to the expected directory and regular file inodes through the production C read and completion path. It reused completed blocks and kept the new reads within the fixed budget.

The file metadata declares compressed content backed by a resource fork. The plain file provider stopped at its representation guard before reading a Mach-O prefix. The compression method and resource stream descriptor remain the next bounded consumer boundary.

Executable header identity, active boot root selection, kernel storage ownership and native execution remain unproven.
