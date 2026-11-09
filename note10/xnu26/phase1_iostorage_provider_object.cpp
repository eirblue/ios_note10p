#include <IOKit/storage/IOBlockStorageDevice.h>

#include "note10_iostorage_pio_bridge.h"

#if !defined(N10_RAM_PROVIDER_OBJECT_PROBE) || !defined(KERNEL) || !TARGET_OS_IOS || TARGET_OS_OSX || TARGET_OS_DRIVERKIT
#error This source is for the public iOS kernel SDK object probe only
#endif

class Note10RAMBlockProviderProbe final : public IOBlockStorageDevice {
    OSDeclareAbstractStructors(Note10RAMBlockProviderProbe)

public:
    bool start(IOService *) override { return false; }
    IOReturn doEjectMedia() override { return kIOReturnUnsupported; }
    IOReturn doFormatMedia(UInt64) override { return kIOReturnNotWritable; }
    UInt32 doGetFormatCapacities(UInt64 *, UInt32) const override { return 0; }
    char *getVendorString() override { return nullptr; }
    char *getProductString() override { return nullptr; }
    char *getRevisionString() override { return nullptr; }
    char *getAdditionalDeviceInfoString() override { return nullptr; }
    IOReturn reportBlockSize(UInt64 *) override { return kIOReturnNotReady; }
    IOReturn reportEjectability(bool *) override { return kIOReturnNotReady; }
    IOReturn reportMaxValidBlock(UInt64 *) override { return kIOReturnNotReady; }
    IOReturn reportMediaState(bool *, bool *) override { return kIOReturnNotReady; }
    IOReturn reportRemovability(bool *) override { return kIOReturnNotReady; }
    IOReturn reportWriteProtection(bool *) override { return kIOReturnNotReady; }
    IOReturn doAsyncReadWrite(IOMemoryDescriptor *, UInt64, UInt64,
                              IOStorageAttributes *, IOStorageCompletion *) override
    {
        return kIOReturnNotReady;
    }
};

// Emit the real SDK metaclass and vtable with metaclass allocation disabled.
OSDefineMetaClassAndAbstractStructors(Note10RAMBlockProviderProbe, IOBlockStorageDevice)
static_assert(!__is_abstract(Note10RAMBlockProviderProbe));

// Keep the PIO import observable without wiring an active request entry.
[[gnu::used]] static IOReturn
probe_ram_pio_import(const void *backing, UInt64 extent, UInt64 block_bytes,
                     IOMemoryDescriptor *buffer, UInt64 lba, UInt64 count,
                     const IOStorageCompletion *completion)
{
    return note10_iostorage_pio_read(backing, extent, block_bytes, buffer, lba, count, completion);
}
