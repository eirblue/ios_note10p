"""Only new genuine-driver dependency, target, and import-association guards."""
from copy import deepcopy
import struct
import phase1_genuine_storage_driver as driver


def names():
    return ([driver.CLASS_VTABLE, driver.CLASS_META, *[prefix + 'v' for prefix in driver.METHODS]],
            [*driver.LOCK_IMPORTS, '_io_rate_update', '__ZN24IOUserBlockStorageDevice10gMetaClassE',
             '__ZN24IOUserBlockStorageDevice20getPerfControlClientEv'])


def sample_result():
    defined, undefined = names()
    sources = {name: 'a' * 64 for name in driver.FILES}
    record = dict(schema=driver.SCHEMA, feature=driver.MODE, source_head='b' * 40, run_id=1, run_attempt=1,
        passed=True, stage='complete', source_sha256=sources, target=driver.TARGET, all_imports_resolved=False,
        authority=dict(driver.AUTHORITY), archive_fetch_attempts=1, family_members_staged=7,
        old_header_dependencies_staged=5, source_text_GETs=4, IIG_attempts=1, IIG_returncode=0,
        target_object_compile_attempts=1, compiler_returncode=0, new_object_raw_reads=1, new_object_nm_views=2,
        tool_hash_reads=2, old_suites_executed=0, kernel_builds=0, kernel_links=0, device_operations=0,
        generated_impl_compiled=False, object_target_verified=True, object_bytes=512, object_sha256='c' * 64,
        generated_header_sha256='d' * 64, family_input_sha256={n: v[1] for n, v in driver.FAMILY_MEMBERS.items()},
        XNU_input_sha256={n: v[1] for n, v in driver.XNU_TEXT.items()}, IIG_framework=driver.FRAMEWORK,
        personality=deepcopy(driver.PERSONALITY), object_target=dict(cpu=0x100000c, subtype=0, filetype=1,
        platform=2, minimum_os=driver.MIN_OS), defined_external_symbols=defined, undefined_external_symbols=undefined,
        method_symbols={prefix: prefix + 'v' for prefix in driver.METHODS},
        public_sdk_baseline_sha256=driver.sdk.CLOSURE_PUBLIC_SDK_SHA256,
        sdk_reused_header_sha256=dict(driver.REUSED_HEADERS),
        sdk_new_header_sha256={name: 'e' * 64 for name in driver.SDK_DELTA}, tool_sha256=dict(driver.TOOLS))
    return record, 'b' * 40, 1, sources


def sample_origins():
    members = {}
    for symbol in ('_IOLockAlloc', '_IOLockFree', '_lck_mtx_lock', '_lck_mtx_unlock'):
        source = 'osfmk/kern/lock_mtx.c' if symbol.startswith('_lck_') else 'iokit/Kernel/IOLocks.cpp'
        members[symbol] = dict(source=source, source_sha256=driver.LOCK_PINS[source], category='native',
                               object_path='/old/' + symbol + '.o', object_sha256='f' * 64)
    proof = dict(schema='note10-v204-readonly-ram-nub-symbol-provenance-v1', passed=True,
        object_provenance_verified=True, final_symbols_verified=True, native_kernel_contains_new_nub=True,
        lock_alias_addresses_verified=True, registered_provider=False, transport_instantiated=False,
        runtime_backing_owner_verified=False, runtime_IOKit_verified=False, firmware_abi_verified=False,
        native_activation=False, kernel_executed=False, physical_ready=False, new_device_input_admitted=False,
        lock_aliases=dict(driver.LOCK_ALIASES), export_sha256=driver.EXPORT_SHA, members=members,
        final_symbol_counts={name: 1 for name in driver.LOCK_IMPORTS})
    retained = dict(source_head='05018bdb34fef65b1c8f040bf487e4e5e7ae464f', run_id=43016946791,
        kernel_retained=True, underlying_provenance_verified=True, fresh_kernel_hash=False,
        fresh_kernel_bytes_verified=False, readonly_ram_nub=proof)
    return names()[1], retained


def run():
    counts = [0, 0, 0]

    def check(group, condition):
        assert condition
        counts[group] += 1

    def denied(group, function):
        try:
            function()
        except ValueError:
            counts[group] += 1
        else:
            raise AssertionError('new driver guard failed to reject')

    value = dict(IOKitPersonalities={'IOBlockStorageDriver': deepcopy(driver.PERSONALITY)})
    check(0, driver.validate_personality(value) == driver.PERSONALITY)
    for key, replacement in [('IOClass', 'FakeDriver'), ('IOProviderClass', 'IOService'),
                             ('IOPropertyMatch', {'device-type': 'Wrong'})]:
        bad = deepcopy(value)
        bad['IOKitPersonalities']['IOBlockStorageDriver'][key] = replacement
        denied(0, lambda bad=bad: driver.validate_personality(bad))
    bad = deepcopy(value); bad['IOKitPersonalities']['IOBlockStorageDriver']['unreviewed'] = True
    denied(0, lambda: driver.validate_personality(bad))
    denied(0, lambda: driver.validate_personality({}))
    check(0, len(driver.FAMILY_MEMBERS) == 7 and 'Info.plist' in driver.FAMILY_MEMBERS and
          'IORequest.h' not in driver.FAMILY_MEMBERS and len(driver.sdk.HEADERS) == 5)
    check(0, set(driver.XNU_TEXT) == {'DriverKit/IOService.iig', 'DriverKit/IOMemoryDescriptor.iig',
                                    'DriverKit/OSObject.iig', 'DriverKit/IOReturn.h'} and
          driver.FAMILY_DEFINITION in driver.FAMILY_MEMBERS and driver.FRAMEWORK == 'BlockStorageDeviceDriverKit')

    raw = struct.pack('<8I', 0xfeedfacf, 0x100000c, 0, 1, 1, 24, 0, 0) + struct.pack('<6I', 0x32, 24, 2, driver.MIN_OS, 0, 0)
    check(1, driver.target_header(raw)['minimum_os'] == driver.MIN_OS)
    for offset, replacement in [(44, driver.MIN_OS - 1), (40, 1), (12, 2)]:
        bad = bytearray(raw); struct.pack_into('<I', bad, offset, replacement)
        denied(1, lambda bad=bad: driver.target_header(bytes(bad)))
    defined, undefined = names()
    check(1, len(driver.caller_symbols(defined, undefined)) == 3)
    denied(1, lambda: driver.symbol_names(b'_same\n_same\n', 0))
    denied(1, lambda: driver.symbol_names(b'invalid token\n', 0))
    denied(1, lambda: driver.caller_symbols([n for n in defined if n != driver.CLASS_VTABLE], undefined))
    denied(1, lambda: driver.caller_symbols([n for n in defined if not n.startswith(driver.METHODS[0])], undefined))
    denied(1, lambda: driver.caller_symbols(defined, [n for n in undefined if n != '__ZN24IOUserBlockStorageDevice10gMetaClassE']))
    denied(1, lambda: driver.caller_symbols(defined, [n for n in undefined if n != '_IOLockAlloc']))
    denied(1, lambda: driver.symbol_names(b'_valid\n', False))

    check(2, driver.validate_result(*sample_result()) is None)
    item = sample_result(); item[0]['source_sha256'] = dict(item[3], **{driver.FILES[0]: '0' * 64})
    denied(2, lambda: driver.validate_result(*item))
    item = sample_result(); item[0]['source_head'] = 'c' * 40
    denied(2, lambda: driver.validate_result(*item))
    item = sample_result(); item[0]['IIG_attempts'] = True
    denied(2, lambda: driver.validate_result(*item))
    item = sample_result(); item[0]['IIG_framework'] = 'DriverKit'
    denied(2, lambda: driver.validate_result(*item))
    item = sample_result(); item[0]['authority']['new_driver_linked_in_native_kernel'] = True
    denied(2, lambda: driver.validate_result(*item))
    association = driver.shared_import_origins(*sample_origins())
    check(2, len(association['existing_static_origin_associations']) == 4 and association['additional_unlinked_imports'] and
          association['all_imports_resolved'] is False and association['concrete_nub_dispatch_verified'] is False)
    item = sample_origins(); item[1]['readonly_ram_nub']['members']['_IOLockAlloc']['source'] = 'fake.c'
    denied(2, lambda: driver.shared_import_origins(*item))
    item = sample_origins(); item[1]['readonly_ram_nub']['lock_aliases']['_IOLockLock'] = '_shim'
    denied(2, lambda: driver.shared_import_origins(*item))
    item = sample_origins(); item[1]['readonly_ram_nub']['native_kernel_contains_new_nub'] = False
    denied(2, lambda: driver.shared_import_origins(*item))
    item = sample_origins(); item[1]['readonly_ram_nub']['runtime_backing_owner_verified'] = True
    denied(2, lambda: driver.shared_import_origins(*item))
    item = sample_result(); item[0]['all_imports_resolved'] = True
    denied(2, lambda: driver.validate_result(*item))
    return dict(groups=3, cases=sum(counts), group_cases=counts, host_C_Cpp_compiles=0, old_suites=0)
