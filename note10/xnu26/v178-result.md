# Reading a version file through the storage path

The PC integration followed exact directory names to SystemVersion.plist, verified its regular file inode and direct physical extent, and read the completed file through the production C read and completion path.

The standard plist parser decoded the file. Its version and build fields matched the retained firmware record. Previously completed metadata blocks were reused while new reads stayed within the fixed budget.

This establishes bounded file content consistency in the recorded filesystem namespace. Active boot root selection, whole image authentication, kernel storage ownership and native execution remain unproven.
