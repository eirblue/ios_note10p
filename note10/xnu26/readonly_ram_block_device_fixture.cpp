#include "readonly_ram_block_device_fixture_support.h"
#include "note10_readonly_ram_block_device.h"
#include "note10_iostorage_pio_bridge.h"
#include <chrono>
#include <condition_variable>
#include <cstring>
#include <thread>

static unsigned cases=0;
static void check(bool ok,const char *name) {
    if (!ok) { std::fprintf(stderr,"FAIL|%s\n",name); std::abort(); }
    ++cases;
}
struct Owner final : OSObject {
    std::atomic<unsigned> retains{0}, releases{0};
    void retain() const override { const_cast<Owner *>(this)->retains.fetch_add(1); OSObject::retain(); }
    void release() const override { const_cast<Owner *>(this)->releases.fetch_add(1); OSObject::release(); }
};
struct Request {
    std::atomic<unsigned> completions{0};
    IOReturn status=99; UInt64 bytes=99;
    Note10ReadOnlyRAMBlockDevice *device=nullptr;
    IOService *transport=nullptr;
    bool stop=false, drop_reference=false;
};
static void completion(void *target,void *,IOReturn status,UInt64 bytes) {
    fixture_require(!fixture_lock_depth);
    auto &request=*static_cast<Request *>(target);
    request.status=status; request.bytes=bytes; request.completions.fetch_add(1);
    if (request.stop) request.device->stop(request.transport);
    if (request.drop_reference) request.device->release();
}
static IOStorageCompletion complete_to(Request &request) { return {&request,completion,nullptr}; }
struct Bridge {
    std::mutex mutex; std::condition_variable cv;
    unsigned calls=0, entered=0; bool paused=false, resume=false;
    IOReturn returned=kIOReturnSuccess, completed=kIOReturnSuccess;
    UInt64 completed_bytes=16;
    const void *backing=nullptr; UInt64 extent=0, block=0,lba=0,count=0;
    IOMemoryDescriptor *descriptor=nullptr;
} bridge;
static void reset_bridge() {
    std::lock_guard<std::mutex> lock(bridge.mutex);
    bridge.calls=bridge.entered=0; bridge.paused=bridge.resume=false;
    bridge.returned=bridge.completed=kIOReturnSuccess; bridge.completed_bytes=16;
}
IOReturn note10_iostorage_pio_read(const void *backing,UInt64 extent,UInt64 block,
    IOMemoryDescriptor *buffer,UInt64 lba,UInt64 count,const IOStorageCompletion *done) {
    fixture_require(!fixture_lock_depth);
    IOReturn returned,status; UInt64 bytes;
    {
        std::unique_lock<std::mutex> lock(bridge.mutex);
        ++bridge.calls; ++bridge.entered; bridge.backing=backing; bridge.extent=extent; bridge.block=block;
        bridge.descriptor=buffer; bridge.lba=lba; bridge.count=count; bridge.cv.notify_all();
        if (bridge.paused) fixture_require(bridge.cv.wait_for(lock,std::chrono::seconds(5),[]{return bridge.resume;}));
        returned=bridge.returned; status=bridge.completed; bytes=bridge.completed_bytes;
    }
    if (returned==kIOReturnSuccess) done->action(done->target,done->parameter,status,bytes);
    return returned;
}
static Note10ReadOnlyRAMBlockDevice *fresh() {
    auto *device=new Note10ReadOnlyRAMBlockDevice;
    fixture_require(device->init()); return device;
}
static Note10ReadOnlyRAMBlockDevice *running(Owner &owner,const void *data,IOService &transport) {
    auto *device=fresh(); fixture_require(device->configureReadOnlyBacking(&owner,data,35,8));
    fixture_require(device->start(&transport)); return device;
}
static IOReturn call(Note10ReadOnlyRAMBlockDevice *device,IOMemoryDescriptor &buffer,Request &request) {
    auto done=complete_to(request); return device->doAsyncReadWrite(&buffer,1,2,nullptr,&done);
}
int main() {
    unsigned char data[35]={}; IOService transport; Owner owner; IOMemoryDescriptor input;
    fixture_init_ok=false; auto *bad=new Note10ReadOnlyRAMBlockDevice;
    check(!bad->init(),"super-init-failure"); bad->release(); fixture_init_ok=true;
    fixture_lock_ok=false; bad=new Note10ReadOnlyRAMBlockDevice;
    check(!bad->init(),"lock-allocation-failure"); bad->release(); fixture_lock_ok=true;
    auto *device=fresh(); UInt64 number=123; bool flag=true,changed=true;
    check(device->reportBlockSize(&number)==kIOReturnNotReady && number==123,"unready-report-no-write");
    check(!device->start(&transport),"unconfigured-start-denied");
    check(!device->configureReadOnlyBacking(nullptr,data,35,8) && !device->configureReadOnlyBacking(&owner,nullptr,35,8),"null-backing-denied");
    check(!device->configureReadOnlyBacking(&owner,data,7,8) && !device->configureReadOnlyBacking(&owner,data,35,0),"empty-geometry-denied");
    check(!device->configureReadOnlyBacking(&owner,reinterpret_cast<void *>(UINTPTR_MAX-7),16,8),"pointer-overflow-denied");
    check(device->configureReadOnlyBacking(&owner,data,35,8) && owner.retains==1,"configure-retains-owner-once");
    check(!device->configureReadOnlyBacking(&owner,data,32,8) && owner.retains==1,"duplicate-config-no-retain");
    fixture_start_ok=false; check(!device->start(&transport),"super-start-failure"); fixture_start_ok=true;
    check(!device->start(&transport),"start-attempt-not-retried"); device->release();
    check(owner.releases==1,"owner-released-on-free");
    device=running(owner,data,transport);
    check(device->reportBlockSize(&number)==0 && number==8 && device->reportMaxValidBlock(&number)==0 && number==3,"complete-block-capacity");
    check(device->reportEjectability(&flag)==0 && !flag && device->reportRemovability(&flag)==0 && !flag && device->reportWriteProtection(&flag)==0 && flag,"readonly-fixed-media-reports");
    check(device->reportMediaState(&flag,&changed)==0 && flag && !changed && device->reportMediaState(&flag,nullptr)==0 && flag,"optional-media-change-output");
    changed=true; check(device->reportMediaState(nullptr,&changed)==kIOReturnBadArgument && changed && device->reportBlockSize(nullptr)==kIOReturnBadArgument,"null-report-no-write");
    char *empty=device->getAdditionalDeviceInfoString();
    check(empty && !empty[0] && empty==device->getAdditionalDeviceInfoString() && device->getVendorString()[0] && device->getProductString()[0] && device->getRevisionString()[0],"four-stable-string-overrides");
    check(device->doEjectMedia()==kIOReturnUnsupported && device->doFormatMedia(0)==kIOReturnNotWritable && device->doGetFormatCapacities(&number,1)==0,"no-writable-media-methods");
    reset_bridge(); Request request;
    check(call(device,input,request)==0 && request.completions==1 && request.bytes==16 && bridge.calls==1 &&
          bridge.backing==data && bridge.extent==32 && bridge.block==8 && bridge.lba==1 && bridge.count==2 && bridge.descriptor==&input,"read-entry-exact-bridge-and-inline-completion");
    reset_bridge(); IOMemoryDescriptor output(kIODirectionOut), both(kIODirectionInOut), none(0); Request denied;
    check(call(device,output,denied)==kIOReturnNotWritable && call(device,both,denied)==kIOReturnNotWritable && call(device,none,denied)==kIOReturnNotWritable && bridge.calls==0 && denied.completions==0,"directions-denied-before-bridge");
    auto done=complete_to(denied); IOStorageCompletion missing{nullptr,nullptr,nullptr};
    check(device->doAsyncReadWrite(nullptr,0,1,nullptr,&done)==kIOReturnBadArgument && device->doAsyncReadWrite(&input,0,1,nullptr,nullptr)==kIOReturnBadArgument && device->doAsyncReadWrite(&input,0,1,nullptr,&missing)==kIOReturnBadArgument && bridge.calls==0,"malformed-entry-before-bridge");
    reset_bridge(); bridge.returned=kIOReturnBadArgument; Request failed;
    auto error=call(device,input,failed); if (error!=0) completion(&failed,nullptr,error,0);
    check(error==kIOReturnBadArgument && bridge.calls==1 && failed.completions==1,"caller-completes-rejection-only");
    reset_bridge(); bridge.completed=kIOReturnUnderrun; bridge.completed_bytes=8; Request short_read;
    error=call(device,input,short_read); if (error!=0) completion(&short_read,nullptr,error,0);
    check(error==0 && short_read.completions==1 && short_read.status==kIOReturnUnderrun && short_read.bytes==8,"admitted-short-no-double-completion");
    reset_bridge(); bridge.completed=kIOReturnIOError; bridge.completed_bytes=0; Request backing_error;
    error=call(device,input,backing_error); if (error!=0) completion(&backing_error,nullptr,error,0);
    check(error==0 && backing_error.completions==1 && backing_error.status==kIOReturnIOError,"admitted-error-no-double-completion");
    unsigned stops=fixture_super_stops.load();
    reset_bridge(); Request reentrant; reentrant.device=device; reentrant.transport=&transport; reentrant.stop=true;
    check(call(device,input,reentrant)==0 && reentrant.completions==1,"completion-reenters-stop-without-lock");
    device->stop(&transport);
    check(fixture_super_stops==stops+1,"terminal-stop-forwards-once");
    number=123; changed=true; flag=false; Request after_stop;
    check(call(device,input,after_stop)==kIOReturnNotReady && after_stop.completions==0 && bridge.calls==1 && !device->start(&transport) && device->reportMediaState(&flag,&changed)==kIOReturnNotReady && !flag && changed && device->reportMaxValidBlock(&number)==kIOReturnNotReady && number==123,"stop-closes-reads-and-reports");
    device->release();
    device=running(owner,data,transport); reset_bridge(); bridge.paused=true;
    Request paused; paused.device=device; paused.transport=&transport;
    std::thread reader([&]{fixture_require(call(device,input,paused)==0);});
    { std::unique_lock<std::mutex> lock(bridge.mutex); fixture_require(bridge.cv.wait_for(lock,std::chrono::seconds(5),[]{return bridge.entered==1;})); }
    unsigned releases=owner.releases.load(); device->stop(&transport); Request late;
    check(call(device,input,late)==kIOReturnNotReady && late.completions==0,"concurrent-stop-rejects-later-read");
    device->release(); check(owner.releases==releases,"inflight-self-holds-backing-owner");
    { std::lock_guard<std::mutex> lock(bridge.mutex); bridge.resume=true; bridge.cv.notify_all(); }
    reader.join();
    check(paused.completions==1 && owner.releases==releases+1,"admitted-read-finishes-after-stop-final-free");
    device=running(owner,data,transport); reset_bridge(); Request final_callback;
    final_callback.device=device; final_callback.transport=&transport; final_callback.stop=true; final_callback.drop_reference=true;
    releases=owner.releases.load();
    check(call(device,input,final_callback)==0 && final_callback.completions==1 && owner.releases==releases+1,"callback-last-client-release-safe");
    device=running(owner,data,transport); reset_bridge(); Request one,two; IOMemoryDescriptor independent;
    std::thread first([&]{fixture_require(call(device,input,one)==0);});
    std::thread second([&]{fixture_require(call(device,independent,two)==0);}); first.join(); second.join();
    check(one.completions==1 && two.completions==1 && bridge.calls==2,"independent-concurrent-descriptors");
    device->stop(&transport); device->release();
    check(owner.retains==owner.releases && fixture_locks_allocated==fixture_locks_freed,"all-lifetime-and-locks-balanced");
    std::printf("{\"schema\":\"note10-v202-readonly-ram-nub-host-fixture-v1\",\"passed\":true,\"groups\":2,\"cases\":%u,\"synthetic_IOKit\":true}\n",cases);
    return 0;
}
