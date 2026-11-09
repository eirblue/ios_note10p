#include <IOKit/IOMemoryDescriptor.h>

#include "note10_iostorage_pio_bridge.h"
#include "note10_iostorage_read_range.h"
#include "note10_iostorage_read_request.h"

#if !defined(KERNEL) || !TARGET_OS_IOS || TARGET_OS_OSX || TARGET_OS_DRIVERKIT
#error Expected the public kernel IOStorage interface for the iOS target
#endif

static_assert(sizeof(IOByteCount) == sizeof(uint64_t));
static_assert(static_cast<uint32_t>(kIODirectionIn) == NOTE10_IOSTORAGE_READ_DIRECTION);

struct Note10PIORead {
    const unsigned char *backing;
    IOMemoryDescriptor *buffer;
    IOStorageCompletion completion;
    IOReturn descriptor_status;
};

extern "C" {

static bool
copy_to_descriptor(void *context, uint64_t offset, uint64_t length, uint64_t *actual_bytes)
{
    auto &read = *static_cast<Note10PIORead *>(context);
    read.descriptor_status = read.buffer->prepare(kIODirectionIn);
    if (read.descriptor_status != kIOReturnSuccess)
        return false;

    *actual_bytes = read.buffer->writeBytes(0, read.backing + offset, length);
    read.descriptor_status = read.buffer->complete(kIODirectionIn);
    return read.descriptor_status == kIOReturnSuccess;
}

static void
finish_pio_read(void *context, note10_iostorage_read_status status, uint64_t actual_bytes)
{
    const auto &read = *static_cast<const Note10PIORead *>(context);
    IOReturn result = read.descriptor_status;
    if (result == kIOReturnSuccess) {
        if (status == NOTE10_IOSTORAGE_READ_SHORT)
            result = kIOReturnUnderrun;
        else if (status == NOTE10_IOSTORAGE_READ_ERROR)
            result = kIOReturnIOError;
    }

    auto completion = read.completion;
    IOStorage::complete(&completion, result, actual_bytes);
}

}

IOReturn
note10_iostorage_pio_read(const void *backing, UInt64 extent_bytes, UInt64 block_bytes,
                         IOMemoryDescriptor *buffer, UInt64 lba, UInt64 count,
                         const IOStorageCompletion *completion)
{
    if (!backing || !buffer || !completion || !completion->action ||
        extent_bytes > UINTPTR_MAX - reinterpret_cast<uintptr_t>(backing))
        return kIOReturnBadArgument;

    Note10PIORead read = {static_cast<const unsigned char *>(backing), buffer,
                          *completion, kIOReturnSuccess};
    const bool admitted = note10_iostorage_read_request(extent_bytes, block_bytes, lba, count,
                                                        buffer->getLength(), buffer->getDirection(),
                                                        copy_to_descriptor, finish_pio_read, &read);
    return admitted ? kIOReturnSuccess : kIOReturnBadArgument;
}
