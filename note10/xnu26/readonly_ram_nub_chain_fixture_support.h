#ifndef READONLY_RAM_NUB_CHAIN_FIXTURE_SUPPORT_H
#define READONLY_RAM_NUB_CHAIN_FIXTURE_SUPPORT_H
// Controlled host declarations/descriptor only, never a genuine SDK runtime.
#include <algorithm>
#include <atomic>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <mutex>
using UInt64=uint64_t; using UInt32=uint32_t; using IOByteCount=uint64_t; using IOReturn=int32_t;
constexpr IOReturn kIOReturnSuccess=0,kIOReturnBadArgument=-1,kIOReturnNotReady=-2,
    kIOReturnUnsupported=-3,kIOReturnNotWritable=-4,kIOReturnUnderrun=-5,kIOReturnIOError=-6;
constexpr UInt32 kIODirectionIn=1,kIODirectionOut=2,kIODirectionInOut=3;
#define TARGET_OS_IOS 1
#define TARGET_OS_OSX 0
#define TARGET_OS_DRIVERKIT 0
#define OSDeclareDefaultStructors(name)
#define OSDefineMetaClassAndStructors(name, base)
inline thread_local unsigned chain_lock_depth=0;
inline unsigned chain_completion_calls=0;
inline void chain_require(bool ok) {
    if (!ok) { std::fputs("chain invariant failed\n",stderr); std::abort(); }
}
class OSDictionary {};
class OSObject {
    mutable std::atomic<unsigned> references{1};
protected:
    virtual ~OSObject()=default;
    virtual void free() { chain_require(!chain_lock_depth); delete this; }
public:
    virtual void retain() const { references.fetch_add(1); }
    virtual void release() const {
        chain_require(!chain_lock_depth);
        if (references.fetch_sub(1)==1) const_cast<OSObject *>(this)->free();
    }
};
class IOService:public OSObject {
public:
    virtual bool init(OSDictionary *) { chain_require(!chain_lock_depth); return true; }
    virtual bool start(IOService *) { chain_require(!chain_lock_depth); return true; }
    virtual void stop(IOService *) { chain_require(!chain_lock_depth); }
};
struct IOStorageAttributes {};
struct IOStorageCompletion {
    void *target;
    void (*action)(void *,void *,IOReturn,UInt64);
    void *parameter;
};
class IOMemoryDescriptor {
    UInt64 length;
    uint8_t *destination;
    UInt64 capacity;
    const std::atomic<unsigned> *ownerReleases;
    void checkOwner() const { chain_require(!chain_lock_depth && ownerReleases->load()==0); }
public:
    unsigned prepares=0,writes=0,completes=0;
    IOReturn prepareStatus=kIOReturnSuccess,completeStatus=kIOReturnSuccess;
    UInt64 writeLimit=UINT64_MAX,requested=0,written=0;
    const void *observedSource=nullptr;
    IOMemoryDescriptor(UInt64 bytes,uint8_t *out,UInt64 cap,const std::atomic<unsigned> *released)
        :length(bytes),destination(out),capacity(cap),ownerReleases(released) {}
    UInt64 getLength() const { return length; }
    UInt32 getDirection() const { return kIODirectionIn; }
    IOReturn prepare(UInt32 direction) {
        checkOwner(); chain_require(direction==kIODirectionIn); ++prepares; return prepareStatus;
    }
    IOByteCount writeBytes(IOByteCount offset,const void *source,IOByteCount bytes) {
        checkOwner(); chain_require(prepares==1 && prepareStatus==0 && offset==0 && source);
        ++writes; observedSource=source; requested=bytes; written=std::min(bytes,writeLimit);
        chain_require(written<=capacity); std::memcpy(destination,source,static_cast<size_t>(written));
        return written;
    }
    IOReturn complete(UInt32 direction) {
        checkOwner(); chain_require(direction==kIODirectionIn && prepares==1 && prepareStatus==0);
        ++completes; return completeStatus;
    }
};
class IOStorage {
public:
    static void complete(IOStorageCompletion *completion,IOReturn status,UInt64 bytes=0) {
        chain_require(!chain_lock_depth && completion && completion->action); ++chain_completion_calls;
        completion->action(completion->target,completion->parameter,status,bytes);
    }
};
class IOBlockStorageDevice:public IOService {
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
inline IOLock *IOLockAlloc() { chain_require(!chain_lock_depth); return new IOLock; }
inline void IOLockFree(IOLock *lock) { chain_require(!chain_lock_depth); delete lock; }
inline void IOLockLock(IOLock *lock) { lock->mutex.lock(); ++chain_lock_depth; }
inline void IOLockUnlock(IOLock *lock) { chain_require(chain_lock_depth==1); --chain_lock_depth; lock->mutex.unlock(); }
#endif
