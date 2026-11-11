#ifndef READONLY_RAM_BLOCK_DEVICE_FIXTURE_SUPPORT_H
#define READONLY_RAM_BLOCK_DEVICE_FIXTURE_SUPPORT_H
// Synthetic call-boundary declarations only. Never included in the SDK job.
#include <atomic>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <mutex>
using UInt64 = uint64_t; using UInt32 = uint32_t; using IOReturn = int32_t;
constexpr IOReturn kIOReturnSuccess=0, kIOReturnBadArgument=-1, kIOReturnNotReady=-2,
    kIOReturnUnsupported=-3, kIOReturnNotWritable=-4, kIOReturnUnderrun=-5, kIOReturnIOError=-6;
constexpr UInt32 kIODirectionIn=1, kIODirectionOut=2, kIODirectionInOut=3;
#define TARGET_OS_IOS 1
#define TARGET_OS_OSX 0
#define TARGET_OS_DRIVERKIT 0
#define OSDeclareDefaultStructors(name)
#define OSDefineMetaClassAndStructors(name, base)
inline thread_local unsigned fixture_lock_depth=0;
inline std::atomic<bool> fixture_init_ok{true}, fixture_start_ok{true}, fixture_lock_ok{true};
inline std::atomic<unsigned> fixture_locks_allocated{0}, fixture_locks_freed{0}, fixture_super_stops{0};
inline void fixture_require(bool ok) { if (!ok) { std::fputs("fixture invariant failed\n",stderr); std::abort(); } }
class OSDictionary {};
class OSObject {
    mutable std::atomic<unsigned> references{1};
protected:
    virtual ~OSObject() = default;
    virtual void free() { fixture_require(!fixture_lock_depth); delete this; }
public:
    virtual void retain() const { references.fetch_add(1); }
    virtual void release() const {
        fixture_require(!fixture_lock_depth);
        if (references.fetch_sub(1)==1) const_cast<OSObject *>(this)->free();
    }
};
class IOService : public OSObject {
public:
    virtual bool init(OSDictionary *) { fixture_require(!fixture_lock_depth); return fixture_init_ok.load(); }
    virtual bool start(IOService *) { fixture_require(!fixture_lock_depth); return fixture_start_ok.load(); }
    virtual void stop(IOService *) { fixture_require(!fixture_lock_depth); fixture_super_stops.fetch_add(1); }
};
struct IOStorageAttributes {};
struct IOStorageCompletion {
    void *target;
    void (*action)(void *,void *,IOReturn,UInt64);
    void *parameter;
};
class IOMemoryDescriptor {
    UInt32 direction;
public:
    explicit IOMemoryDescriptor(UInt32 value=kIODirectionIn) : direction(value) {}
    UInt32 getDirection() const { return direction; }
};
class IOBlockStorageDevice : public IOService {
public:
    virtual IOReturn doEjectMedia()=0;
    virtual IOReturn doFormatMedia(UInt64)=0;
    virtual UInt32 doGetFormatCapacities(UInt64 *,UInt32) const=0;
    virtual char *getVendorString()=0;
    virtual char *getProductString()=0;
    virtual char *getRevisionString()=0;
    virtual char *getAdditionalDeviceInfoString()=0;
    virtual IOReturn reportBlockSize(UInt64 *)=0;
    virtual IOReturn reportEjectability(bool *)=0;
    virtual IOReturn reportMaxValidBlock(UInt64 *)=0;
    virtual IOReturn reportMediaState(bool *,bool * = nullptr)=0;
    virtual IOReturn reportRemovability(bool *)=0;
    virtual IOReturn reportWriteProtection(bool *)=0;
    virtual IOReturn doAsyncReadWrite(IOMemoryDescriptor *,UInt64,UInt64,IOStorageAttributes *,IOStorageCompletion *)=0;
};
struct IOLock { std::mutex mutex; };
inline IOLock *IOLockAlloc() {
    fixture_require(!fixture_lock_depth);
    if (!fixture_lock_ok.load()) return nullptr;
    fixture_locks_allocated.fetch_add(1); return new IOLock;
}
inline void IOLockFree(IOLock *lock) { fixture_require(!fixture_lock_depth); fixture_locks_freed.fetch_add(1); delete lock; }
inline void IOLockLock(IOLock *lock) { lock->mutex.lock(); ++fixture_lock_depth; }
inline void IOLockUnlock(IOLock *lock) { fixture_require(fixture_lock_depth==1); --fixture_lock_depth; lock->mutex.unlock(); }
#endif
