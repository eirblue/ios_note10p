# v197: Reference ARM64 object inspection

One Clang invocation produced three Apple ARM64 target object files for the new page gate, model-frame producer, and declaration-only probe. The bounded inspector passed 39 focused checks in three groups (13, 18, and 8). It read each new object once, totaling 2,480 bytes. No prior object or page input was read, and the objects were not linked or executed.

The probe reports a controlled LP64, non-PAC reference declaration layout and symbolic object edges. The callsite references the declared frame producer and the retained fetch function. `_copyin`, `_memcpy`, and `_memset` remain unresolved imports.

This evidence does not establish firmware headers or ABI, a linked dependency closure, runtime ownership or mapping, ASLR selection, activation, launch, input admission, or physical behavior. No CI or device action occurred.
