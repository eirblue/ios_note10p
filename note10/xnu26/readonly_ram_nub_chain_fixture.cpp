#include "readonly_ram_nub_chain_fixture_support.h"
#include "note10_readonly_ram_block_device.h"

struct Owner final:OSObject {
    std::atomic<unsigned> retains{0},releases{0};
    void retain() const override { const_cast<Owner *>(this)->retains.fetch_add(1); OSObject::retain(); }
    void release() const override { const_cast<Owner *>(this)->releases.fetch_add(1); OSObject::release(); }
};
struct Request {
    Owner *owner;
    Note10ReadOnlyRAMBlockDevice *device;
    IOService *transport;
    unsigned callbacks=0;
    IOReturn status=99;
    UInt64 bytes=99;
    bool returned=false,beforeReturn=false,stopAndRelease=false;
};
static void completion(void *target,void *,IOReturn status,UInt64 bytes) {
    auto &request=*static_cast<Request *>(target);
    chain_require(!chain_lock_depth && request.owner->releases.load()==0);
    ++request.callbacks; request.status=status; request.bytes=bytes; request.beforeReturn=!request.returned;
    if (request.stopAndRelease) {
        request.device->stop(request.transport);
        request.device->release();
        chain_require(request.owner->releases.load()==0);
    }
}
struct Call {
    IOReturn result;
    unsigned providerCallbacks,callerCompletions;
};
static Call invoke(Note10ReadOnlyRAMBlockDevice *device,IOMemoryDescriptor &descriptor,
                   UInt64 lba,UInt64 count,Request &request) {
    IOStorageCompletion done{&request,completion,nullptr};
    IOReturn result=device->doAsyncReadWrite(&descriptor,lba,count,nullptr,&done);
    request.returned=true;
    unsigned providerCallbacks=request.callbacks,callerCompletions=0;
    // Exact executeRequest completion decision, not a replacement PIO/core.
    if (result!=kIOReturnSuccess) {
        ++callerCompletions; IOStorage::complete(&done,result,0);
    }
    return {result,providerCallbacks,callerCompletions};
}
struct Recorded {
    const char *name;
    IOReturn result,status;
    UInt64 bytes;
    unsigned prepares,writes,completes,providerCallbacks,callerCompletions,callbacks;
    bool beforeReturn;
};
static Recorded records[7];
static unsigned cases=0;
static bool output_matches(const uint8_t *out,const uint8_t *source,unsigned copied) {
    if (out[0]!=0xa5 || out[17]!=0xa5) return false;
    for (unsigned i=0;i<16;++i) if (out[1+i]!=(i<copied?source[i]:0xa5)) return false;
    return true;
}
static void record(bool ok,const char *name,const Call &call,const IOMemoryDescriptor &descriptor,const Request &request) {
    if (!ok) { std::fprintf(stderr,"FAIL|%s\n",name); std::abort(); }
    chain_require(cases<7 && chain_completion_calls==1);
    records[cases++]={name,call.result,request.status,request.bytes,descriptor.prepares,descriptor.writes,
                     descriptor.completes,call.providerCallbacks,call.callerCompletions,request.callbacks,request.beforeReturn};
}
static void run_case(unsigned index) {
    Owner owner; IOService transport;
    uint8_t backing[35],out[18];
    for (unsigned i=0;i<35;++i) backing[i]=static_cast<uint8_t>(0x21+7*i);
    std::memset(out,0xa5,sizeof(out)); chain_completion_calls=0;
    auto *device=new Note10ReadOnlyRAMBlockDevice;
    chain_require(device->init() && device->configureReadOnlyBacking(&owner,backing,35,8) && device->start(&transport));
    UInt64 maximum=99; chain_require(device->reportMaxValidBlock(&maximum)==0 && maximum==3);
    UInt64 length=index==4?15:(index==5?8:16);
    IOMemoryDescriptor descriptor(length,out+1,16,&owner.releases);
    if (index==1) descriptor.writeLimit=8;
    if (index==2) descriptor.prepareStatus=kIOReturnNotReady;
    if (index==3) descriptor.completeStatus=kIOReturnIOError;
    Request request{&owner,device,&transport}; request.stopAndRelease=index==6;
    Call call=invoke(device,descriptor,index==5?4:2,index==5?1:2,request);
    const bool copied16=output_matches(out,backing+16,16);
    const bool full=call.result==0 && call.providerCallbacks==1 && call.callerCompletions==0 && request.callbacks==1 &&
        request.beforeReturn && descriptor.prepares==1 && descriptor.writes==1 && descriptor.completes==1;
    if (index==0) record(full && request.status==0 && request.bytes==16 && copied16 &&
        descriptor.observedSource==backing+16 && descriptor.requested==16,
        "real-nonzero-complete-extent-copy",call,descriptor,request);
    if (index==1) record(full && request.status==kIOReturnUnderrun && request.bytes==8 && descriptor.written==8 &&
        output_matches(out,backing+16,8),"real-descriptor-short-mapping",call,descriptor,request);
    if (index==2) record(call.result==0 && call.providerCallbacks==1 && call.callerCompletions==0 && request.callbacks==1 &&
        request.beforeReturn && request.status==kIOReturnNotReady && request.bytes==0 && descriptor.prepares==1 &&
        descriptor.writes==0 && descriptor.completes==0 && output_matches(out,backing+16,0),
        "real-prepare-failure-mapping",call,descriptor,request);
    if (index==3) record(full && request.status==kIOReturnIOError && request.bytes==16 && copied16,
        "real-complete-failure-mapping",call,descriptor,request);
    if (index==4 || index==5) record(call.result==kIOReturnBadArgument && call.providerCallbacks==0 && call.callerCompletions==1 &&
        request.callbacks==1 && !request.beforeReturn && request.status==kIOReturnBadArgument && request.bytes==0 &&
        descriptor.prepares==0 && descriptor.writes==0 && descriptor.completes==0 && descriptor.observedSource==nullptr &&
        output_matches(out,backing+16,0),index==4?"real-length-admission-rejection":"real-partial-tail-not-exposed",call,descriptor,request);
    if (index==6) record(full && request.status==0 && request.bytes==16 && copied16 && owner.releases==1,
        "real-chain-completion-lifetime",call,descriptor,request);
    if (index!=6) { device->stop(&transport); device->release(); }
    chain_require(owner.retains==1 && owner.releases==1);
}
int main() {
    for (unsigned index=0;index<7;++index) run_case(index);
    chain_require(cases==7);
    std::printf("{\"schema\":\"note10-v203-real-pio-nub-chain-fixture-v1\",\"passed\":true,\"groups\":3,\"cases\":7,\"group_cases\":[1,3,3],\"synthetic_descriptor\":true,\"records\":[");
    for (unsigned i=0;i<cases;++i) {
        const auto &row=records[i];
        std::printf("%s{\"name\":\"%s\",\"return_status\":%d,\"completion_status\":%d,\"bytes\":%llu,\"prepare_calls\":%u,\"write_calls\":%u,\"complete_calls\":%u,\"provider_callbacks\":%u,\"caller_completions\":%u,\"callbacks\":%u,\"before_return\":%s}",
            i?",":"",row.name,static_cast<int>(row.result),static_cast<int>(row.status),static_cast<unsigned long long>(row.bytes),
            row.prepares,row.writes,row.completes,row.providerCallbacks,row.callerCompletions,row.callbacks,row.beforeReturn?"true":"false");
    }
    std::puts("]}"); return 0;
}
