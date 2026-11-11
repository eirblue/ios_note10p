#include "note10_readonly_ram_block_device.h"
#include "note10_iostorage_pio_bridge.h"
#if !defined(KERNEL) || !TARGET_OS_IOS || TARGET_OS_OSX || TARGET_OS_DRIVERKIT
#error Expected public iOS kernel interfaces
#endif
#define super IOBlockStorageDevice
OSDefineMetaClassAndStructors(Note10ReadOnlyRAMBlockDevice, IOBlockStorageDevice)
static_assert(!__is_abstract(Note10ReadOnlyRAMBlockDevice));

bool Note10ReadOnlyRAMBlockDevice::init(OSDictionary *properties)
{
    stateLock = nullptr; backingOwner = nullptr; backing = nullptr;
    actualExtent = providerExtent = blockBytes = 0;
    configured = startAttempted = stopped = ready = false;
    if (!super::init(properties)) return false;
    stateLock = IOLockAlloc();
    return stateLock != nullptr;
}

bool Note10ReadOnlyRAMBlockDevice::configureReadOnlyBacking(
    OSObject *owner, const void *bytes, UInt64 extent, UInt64 block)
{
    if (!stateLock || !owner || !bytes || !block || extent < block ||
        extent > UINTPTR_MAX - reinterpret_cast<uintptr_t>(bytes)) return false;
    IOLockLock(stateLock);
    const bool accepted = !configured && !startAttempted && !stopped;
    if (accepted) {
        owner->retain();
        backingOwner = owner; backing = bytes; actualExtent = extent;
        providerExtent = (extent / block) * block; blockBytes = block;
        configured = true;
    }
    IOLockUnlock(stateLock);
    return accepted;
}

bool Note10ReadOnlyRAMBlockDevice::start(IOService *provider)
{
    if (!stateLock || !provider) return false;
    IOLockLock(stateLock);
    const bool allowed = configured && !startAttempted && !stopped;
    if (allowed) startAttempted = true;
    IOLockUnlock(stateLock);
    if (!allowed) return false;
    const bool started = super::start(provider);
    IOLockLock(stateLock);
    ready = started && !stopped;
    const bool accepted = ready && providerExtent <= actualExtent;
    IOLockUnlock(stateLock);
    return accepted;
}

void Note10ReadOnlyRAMBlockDevice::stop(IOService *provider)
{
    if (!stateLock) return;
    IOLockLock(stateLock);
    const bool forward = !stopped;
    ready = false; stopped = true;
    IOLockUnlock(stateLock);
    if (forward) super::stop(provider);
}

void Note10ReadOnlyRAMBlockDevice::free()
{
    // Each read holds self through inline completion, so final free has no reader.
    OSObject *owner = backingOwner;
    backingOwner = nullptr; backing = nullptr; ready = false;
    if (owner) owner->release();
    if (stateLock) { IOLockFree(stateLock); stateLock = nullptr; }
    super::free();
}

bool Note10ReadOnlyRAMBlockDevice::readyGeometry(UInt64 *block, UInt64 *maximum)
{
    if (!stateLock) return false;
    IOLockLock(stateLock);
    const bool accepted = ready && providerExtent <= actualExtent;
    if (accepted) {
        if (block) *block = blockBytes;
        if (maximum) *maximum = providerExtent / blockBytes - 1;
    }
    IOLockUnlock(stateLock);
    return accepted;
}

IOReturn Note10ReadOnlyRAMBlockDevice::doEjectMedia() { return kIOReturnUnsupported; }
IOReturn Note10ReadOnlyRAMBlockDevice::doFormatMedia(UInt64) { return kIOReturnNotWritable; }
UInt32 Note10ReadOnlyRAMBlockDevice::doGetFormatCapacities(UInt64 *, UInt32) const { return 0; }
char *Note10ReadOnlyRAMBlockDevice::getVendorString() { static char text[] = "Note10"; return text; }
char *Note10ReadOnlyRAMBlockDevice::getProductString() { static char text[] = "Read-only RAM"; return text; }
char *Note10ReadOnlyRAMBlockDevice::getRevisionString() { static char text[] = "1"; return text; }
char *Note10ReadOnlyRAMBlockDevice::getAdditionalDeviceInfoString() { static char text[] = ""; return text; }
IOReturn Note10ReadOnlyRAMBlockDevice::reportBlockSize(UInt64 *out)
{
    if (!out) return kIOReturnBadArgument;
    return readyGeometry(out, nullptr) ? kIOReturnSuccess : kIOReturnNotReady;
}
IOReturn Note10ReadOnlyRAMBlockDevice::reportMaxValidBlock(UInt64 *out)
{
    if (!out) return kIOReturnBadArgument;
    return readyGeometry(nullptr, out) ? kIOReturnSuccess : kIOReturnNotReady;
}
IOReturn Note10ReadOnlyRAMBlockDevice::reportEjectability(bool *out)
{
    if (!out) return kIOReturnBadArgument;
    if (!readyGeometry(nullptr, nullptr)) return kIOReturnNotReady;
    *out = false; return kIOReturnSuccess;
}
IOReturn Note10ReadOnlyRAMBlockDevice::reportRemovability(bool *out)
{ return reportEjectability(out); }
IOReturn Note10ReadOnlyRAMBlockDevice::reportWriteProtection(bool *out)
{
    if (!out) return kIOReturnBadArgument;
    if (!readyGeometry(nullptr, nullptr)) return kIOReturnNotReady;
    *out = true; return kIOReturnSuccess;
}
IOReturn Note10ReadOnlyRAMBlockDevice::reportMediaState(bool *present, bool *changed)
{
    if (!present) return kIOReturnBadArgument;
    if (!readyGeometry(nullptr, nullptr)) return kIOReturnNotReady;
    *present = true; if (changed) *changed = false;
    return kIOReturnSuccess;
}

IOReturn Note10ReadOnlyRAMBlockDevice::doAsyncReadWrite(
    IOMemoryDescriptor *buffer, UInt64 lba, UInt64 count,
    IOStorageAttributes *attributes, IOStorageCompletion *completion)
{
    (void)attributes;
    if (!buffer || !completion || !completion->action) return kIOReturnBadArgument;
    if (buffer->getDirection() != kIODirectionIn) return kIOReturnNotWritable;
    if (!stateLock) return kIOReturnNotReady;
    retain();
    IOLockLock(stateLock);
    const bool accepted = ready && providerExtent <= actualExtent;
    const void *bytes = backing;
    const UInt64 extent = providerExtent, block = blockBytes;
    IOLockUnlock(stateLock);
    // No state lock spans descriptor work or a reentrant client completion.
    const IOReturn result = accepted ?
        note10_iostorage_pio_read(bytes, extent, block, buffer, lba, count, completion) : kIOReturnNotReady;
    release();
    return result;
}
#undef super
