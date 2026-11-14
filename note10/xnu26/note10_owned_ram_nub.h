#ifndef NOTE10_OWNED_RAM_NUB_H
#define NOTE10_OWNED_RAM_NUB_H
#include "note10_readonly_ram_block_device.h"

/* Source must remain readable/stable throughout this sleepable-thread call.
 * requested_copy_limit bounds requested bytes, not allocator/object overhead.
 * Returns one owned reference to a configured, UNSTARTED nub; caller releases it.
 * No start/publication/boot hook or hardware memory authority is supplied. */
Note10ReadOnlyRAMBlockDevice *note10_create_owned_readonly_ram_nub(
    const void *source, UInt64 extent, UInt64 block_bytes, UInt64 requested_copy_limit);
#endif
