# Following a stored directory reference

The PC integration followed a stored directory entry to its exact inode through the production C read and completion path. Twelve bounded block reads supplied the volume mapping and filesystem nodes. The inode had the expected directory mode and parent.

Every completed block carried a checksum and object identity check. The owned file remained live through each completion, and the input file identity stayed stable across the session.

The result establishes this directory reference in the recorded filesystem namespace. Active boot root selection, kernel storage ownership, filesystem mounting and native execution remain unproven.
