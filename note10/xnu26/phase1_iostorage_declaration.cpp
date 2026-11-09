#include <IOKit/storage/IOBlockStorageDevice.h>

#if !defined(KERNEL) || !TARGET_OS_IOS || TARGET_OS_OSX || TARGET_OS_DRIVERKIT
#error Expected the public kernel IOStorage interface for the iOS target
#endif

class Note10BlockDeclaration final : public IOBlockStorageDevice {
public:
    IOReturn doEjectMedia() override;
    IOReturn doFormatMedia(UInt64 byteCapacity) override;
    UInt32 doGetFormatCapacities(UInt64 *capacities, UInt32 capacitiesMaxCount) const override;
    char *getVendorString() override;
    char *getProductString() override;
    char *getRevisionString() override;
    char *getAdditionalDeviceInfoString() override;
    IOReturn reportBlockSize(UInt64 *blockSize) override;
    IOReturn reportEjectability(bool *isEjectable) override;
    IOReturn reportMaxValidBlock(UInt64 *maxBlock) override;
    IOReturn reportMediaState(bool *mediaPresent, bool *changedState) override;
    IOReturn reportRemovability(bool *isRemovable) override;
    IOReturn reportWriteProtection(bool *isWriteProtected) override;
    IOReturn doAsyncReadWrite(IOMemoryDescriptor *buffer, UInt64 block, UInt64 nblks,
                              IOStorageAttributes *attributes, IOStorageCompletion *completion) override;
};

static_assert(__is_abstract(IOBlockStorageDevice));
static_assert(!__is_abstract(Note10BlockDeclaration));
