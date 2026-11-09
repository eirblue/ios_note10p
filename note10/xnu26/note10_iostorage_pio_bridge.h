#ifndef NOTE10_IOSTORAGE_PIO_BRIDGE_H
#define NOTE10_IOSTORAGE_PIO_BRIDGE_H

#include <IOKit/storage/IOStorage.h>

/* The caller supplies a readable immutable backing span and serializes access
 * to the destination descriptor. Both must remain valid through the copy.
 * An admitted request calls the completion action inline before returning
 * kIOReturnSuccess. Rejection returns an error without calling the action. */
IOReturn note10_iostorage_pio_read(const void *backing, UInt64 extent_bytes, UInt64 block_bytes,
                                  IOMemoryDescriptor *buffer, UInt64 lba, UInt64 count,
                                  const IOStorageCompletion *completion);

#endif
