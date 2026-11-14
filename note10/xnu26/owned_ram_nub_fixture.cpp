#include "owned_ram_nub_fixture_support.h"
#include "note10_owned_ram_nub.h"
#include "note10_iostorage_pio_bridge.h"
#include <climits>

static unsigned completed=0,bridge_calls=0;
static void verdict(bool ok,const char *name){
    if(!ok){std::fprintf(stderr,"FAIL|%u|%s\n",completed,name);std::fflush(stderr);std::abort();}
    ++completed;std::printf("PASS|%s\n",name);std::fflush(stdout);
}
static void reset(){
    fixture_require(fixture_data_owner==nullptr&&fixture_locks_allocated.load()==fixture_locks_freed.load());
    fixture_object_allocations=fixture_object_deletions=fixture_fail_object=0;
    fixture_data_created=fixture_data_freed=fixture_data_retains=fixture_data_releases=0;
    fixture_copy_allocations=fixture_copy_frees=fixture_starts=bridge_calls=0;
    fixture_data_init_ok=true;fixture_init_ok=true;fixture_lock_ok=true;fixture_start_ok=true;
}
IOReturn note10_iostorage_pio_read(const void *backing,UInt64 extent,UInt64 block,
    IOMemoryDescriptor *buffer,UInt64 lba,UInt64 count,const IOStorageCompletion *done){
    fixture_require(!fixture_lock_depth&&fixture_data_owner&&backing==fixture_data_owner->getBytesNoCopy());
    fixture_require(extent==32&&block==8&&lba==0&&count==4);
    ++bridge_calls;std::memcpy(buffer->copied,backing,32);done->action(done->target,done->parameter,kIOReturnSuccess,32);return kIOReturnSuccess;
}
struct Completion {unsigned calls=0;IOReturn result=99;UInt64 bytes=0;};
static void finish(void *target,void *,IOReturn result,UInt64 bytes){auto *c=static_cast<Completion *>(target);++c->calls;c->result=result;c->bytes=bytes;}
int main(){
    unsigned char source[32],expected[32];for(unsigned i=0;i<32;++i)source[i]=expected[i]=static_cast<unsigned char>(i+1);
    reset();auto *device=note10_create_owned_readonly_ram_nub(source,32,8,32);UInt64 block=0;
    bool ok=device&&fixture_data_owner&&fixture_data_owner->fixture_references()==1&&fixture_data_retains==1&&fixture_data_releases==1&&fixture_starts==0&&fixture_object_allocations==2&&fixture_copy_allocations==1;
    ok=ok&&device->reportBlockSize(&block)==kIOReturnNotReady;
    std::memset(source,0,sizeof(source));IOService transport;IOMemoryDescriptor output;Completion status;IOStorageCompletion completion{&status,finish,nullptr};
    ok=ok&&device->start(&transport)&&device->doAsyncReadWrite(&output,0,4,nullptr,&completion)==kIOReturnSuccess&&status.calls==1&&status.result==kIOReturnSuccess&&status.bytes==32&&bridge_calls==1&&std::memcmp(output.copied,expected,32)==0;
    if(device){device->stop(&transport);device->release();}
    ok=ok&&fixture_data_owner==nullptr&&fixture_data_freed==1&&fixture_copy_frees==1&&fixture_data_releases==2&&fixture_object_deletions==2;
    verdict(ok,"private_copy_isolated_owned_and_initially_unstarted");
    reset();device=note10_create_owned_readonly_ram_nub(source,32,8,31);verdict(!device&&fixture_object_allocations==0,"requested_copy_limit_before_allocation");
    reset();device=note10_create_owned_readonly_ram_nub(source,static_cast<UInt64>(UINT_MAX)+1,8,static_cast<UInt64>(UINT_MAX)+1);verdict(!device&&fixture_object_allocations==0,"OSData_width_before_allocation");
    reset();ok=!note10_create_owned_readonly_ram_nub(nullptr,32,8,32)&&!note10_create_owned_readonly_ram_nub(source,0,8,32)&&!note10_create_owned_readonly_ram_nub(source,32,0,32)&&!note10_create_owned_readonly_ram_nub(source,7,8,32)&&!note10_create_owned_readonly_ram_nub(reinterpret_cast<const void *>(UINTPTR_MAX-7),16,8,16)&&fixture_object_allocations==0;
    verdict(ok,"invalid_source_geometry_before_allocation");
    reset();fixture_fail_object=1;device=note10_create_owned_readonly_ram_nub(source,32,8,32);verdict(!device&&fixture_object_allocations==1&&fixture_object_deletions==0&&fixture_data_created==0&&fixture_data_owner==nullptr,"OSData_object_allocation_failure");
    reset();fixture_data_init_ok=false;device=note10_create_owned_readonly_ram_nub(source,32,8,32);verdict(!device&&fixture_object_allocations==1&&fixture_object_deletions==1&&fixture_data_created==1&&fixture_data_freed==1&&fixture_data_releases==1&&fixture_copy_allocations==0&&fixture_data_owner==nullptr,"OSData_initialization_failure_cleanup");
    reset();fixture_fail_object=2;device=note10_create_owned_readonly_ram_nub(source,32,8,32);verdict(!device&&fixture_object_allocations==2&&fixture_object_deletions==1&&fixture_data_freed==1&&fixture_copy_allocations==fixture_copy_frees&&fixture_data_releases==1&&fixture_data_owner==nullptr,"nub_object_allocation_failure_cleanup");
    reset();fixture_lock_ok=false;device=note10_create_owned_readonly_ram_nub(source,32,8,32);verdict(!device&&fixture_object_allocations==2&&fixture_object_deletions==2&&fixture_data_freed==1&&fixture_copy_allocations==fixture_copy_frees&&fixture_data_releases==1&&fixture_data_owner==nullptr&&fixture_locks_allocated.load()==fixture_locks_freed.load(),"nub_initialization_failure_cleanup");
    std::printf("RESULT|{\"groups\":1,\"variants\":8,\"assertions\":8}\n");return 0;
}
