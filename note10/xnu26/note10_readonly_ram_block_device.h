#ifndef NOTE10_READONLY_RAM_BLOCK_DEVICE_H
#define NOTE10_READONLY_RAM_BLOCK_DEVICE_H
#include <IOKit/storage/IOBlockStorageDevice.h>
#include <IOKit/IOLocks.h>

/* Configure once before publication. owner must own a stable, immutable readable
 * span while retained. Callers keep this nub and each destination live throughout
 * each synchronous call, and serialize concurrent use of the same descriptor.
 * These entrypoints require sleepable thread context, never primary interrupts
 * or a held spin lock (the state mutex and descriptor preparation may block). */
class Note10ReadOnlyRAMBlockDevice final : public IOBlockStorageDevice {
    OSDeclareDefaultStructors(Note10ReadOnlyRAMBlockDevice)
    IOLock *stateLock;
    OSObject *backingOwner;
    const void *backing;
    UInt64 actualExtent, providerExtent, blockBytes;
    bool configured, startAttempted, stopped, ready;
    bool readyGeometry(UInt64 *, UInt64 *);
protected:
    void free() override;
public:
    bool init(OSDictionary * = nullptr) override;
    bool configureReadOnlyBacking(OSObject *, const void *, UInt64, UInt64);
    bool start(IOService *) override;
    void stop(IOService *) override;
    IOReturn doEjectMedia() override;
    IOReturn doFormatMedia(UInt64) override;
    UInt32 doGetFormatCapacities(UInt64 *, UInt32) const override;
    char *getVendorString() override;
    char *getProductString() override;
    char *getRevisionString() override;
    char *getAdditionalDeviceInfoString() override;
    IOReturn reportBlockSize(UInt64 *) override;
    IOReturn reportEjectability(bool *) override;
    IOReturn reportMaxValidBlock(UInt64 *) override;
    IOReturn reportMediaState(bool *, bool * = nullptr) override;
    IOReturn reportRemovability(bool *) override;
    IOReturn reportWriteProtection(bool *) override;
    IOReturn doAsyncReadWrite(IOMemoryDescriptor *, UInt64, UInt64,
                              IOStorageAttributes *, IOStorageCompletion *) override;
};
#endif
