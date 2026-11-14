#include "note10_owned_ram_nub.h"
#include <libkern/c++/OSData.h>
#include <limits.h>
#include <stdint.h>

Note10ReadOnlyRAMBlockDevice *note10_create_owned_readonly_ram_nub(
    const void *source, UInt64 extent, UInt64 block_bytes, UInt64 requested_copy_limit)
{
    if (!source || !extent || !block_bytes || extent < block_bytes ||
        extent > requested_copy_limit || extent > UINT_MAX ||
        extent > UINTPTR_MAX - reinterpret_cast<uintptr_t>(source)) return nullptr;
    OSData *owner = new OSData;
    if (!owner) return nullptr;
    if (!owner->initWithBytes(source, static_cast<unsigned int>(extent))) {
        owner->release(); return nullptr;
    }
    auto *device = new Note10ReadOnlyRAMBlockDevice;
    if (!device) { owner->release(); return nullptr; }
    if (!device->init() || !device->configureReadOnlyBacking(
            owner, owner->getBytesNoCopy(), extent, block_bytes)) {
        device->release(); owner->release(); return nullptr;
    }
    owner->release();
    return device;
}
