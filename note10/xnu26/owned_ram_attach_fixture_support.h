#ifndef OWNED_RAM_ATTACH_FIXTURE_SUPPORT_H
#define OWNED_RAM_ATTACH_FIXTURE_SUPPORT_H
// New factory service shims only; actual factory/nub bodies are compiled unchanged.
#include <atomic>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <mutex>
#include <cstring>
#include <new>
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
inline unsigned fixture_object_allocations=0, fixture_object_deletions=0, fixture_fail_object=0;
inline unsigned fixture_data_created=0, fixture_data_freed=0, fixture_data_retains=0, fixture_data_releases=0;
inline unsigned fixture_copy_allocations=0, fixture_copy_frees=0, fixture_starts=0;
inline bool fixture_data_init_ok=true,fixture_attach_ok=true;
inline unsigned fixture_attaches=0,fixture_detaches=0,fixture_registrations=0;
inline char fixture_order[32]={};inline unsigned fixture_order_size=0;
inline void fixture_event(char c){fixture_require(fixture_order_size<31);fixture_order[fixture_order_size++]=c;}
class OSData;
inline OSData *fixture_data_owner=nullptr;
class OSDictionary {};
class OSObject {
    mutable std::atomic<unsigned> references{1};
protected:
    virtual ~OSObject() = default;
    virtual void free() { fixture_require(!fixture_lock_depth); delete this; }
public:
    static void *operator new(std::size_t bytes) noexcept {
        const unsigned ordinal=++fixture_object_allocations;
        return ordinal==fixture_fail_object ? nullptr : std::malloc(bytes);
    }
    static void operator delete(void *p) noexcept { if(p){++fixture_object_deletions;std::free(p);} }
    unsigned fixture_references() const { return references.load(); }
    virtual void retain() const { references.fetch_add(1); }
    virtual void release() const {
        fixture_require(!fixture_lock_depth);
        if (references.fetch_sub(1)==1) const_cast<OSObject *>(this)->free();
    }
};
class OSData final : public OSObject {
    unsigned char *data=nullptr;
public:
    OSData(){++fixture_data_created;fixture_data_owner=this;}
    bool initWithBytes(const void *source,unsigned int extent){
        if(!fixture_data_init_ok)return false;
        data=static_cast<unsigned char *>(std::malloc(extent));
        if(!data)return false;
        ++fixture_copy_allocations;std::memcpy(data,source,extent);return true;
    }
    const void *getBytesNoCopy() const{return data;}
    void retain() const override{++fixture_data_retains;OSObject::retain();}
    void release() const override{++fixture_data_releases;OSObject::release();}
protected:
    void free() override{
        if(data){++fixture_copy_frees;std::free(data);data=nullptr;}
        ++fixture_data_freed;fixture_data_owner=nullptr;OSObject::free();
    }
};
class IOService : public OSObject {
    IOService *fixture_provider=nullptr;
public:
    virtual bool attach(IOService *p){++fixture_attaches;fixture_event('A');if(!fixture_attach_ok)return false;fixture_require(p&&!fixture_provider);fixture_provider=p;retain();p->retain();return true;}
    virtual void detach(IOService *p){++fixture_detaches;fixture_event('D');fixture_require(p&&p==fixture_provider);fixture_provider=nullptr;p->release();release();}
    virtual void registerService(){++fixture_registrations;}
    virtual bool init(OSDictionary *) { fixture_require(!fixture_lock_depth); return fixture_init_ok.load(); }
    virtual bool start(IOService *) { fixture_require(!fixture_lock_depth); ++fixture_starts; fixture_event('S'); return fixture_start_ok.load(); }
    virtual void stop(IOService *) { fixture_require(!fixture_lock_depth); fixture_super_stops.fetch_add(1); fixture_event('T'); }
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
    unsigned char copied[32]={};
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
