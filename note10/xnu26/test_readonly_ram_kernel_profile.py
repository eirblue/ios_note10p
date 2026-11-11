"""Only new selector, genuine-origin, and retained-profile metadata checks."""
import ast
from copy import deepcopy
from pathlib import Path, PurePosixPath

import current_native_kernel as native
import phase1_iostorage_declaration as sdk
import phase1_iostorage_kernel_link as storage_link
import phase1_readonly_ram_block_device as ram


def sample():
    current = dict(producer={ram.PROFILE_KEY: ram.profile()}, bindings={ram.PROFILE_KEY: native.digest(ram.profile())})
    current.update(producer_id=native.digest(current['producer']), input_binding=native.digest(current['bindings']))
    storage_proof = dict(producer_id=current['producer_id'], input_binding=current['input_binding'],
                         readonly_ram_nub=ram.profile(), readonly_ram_sdk_delta_sha256=ram.SDK_DELTA)
    current['storage'] = dict(proof=storage_proof, binding=native.digest(storage_proof))
    rows, defined, references, by_source = [], {}, {}, {}
    for symbol, (source, source_sha, category) in ram.origin_specs().items():
        if source not in by_source:
            row = dict(source=source, source_sha256=source_sha, category=category, passed=True,
                       object_path='/current/' + source.replace('/', '_') + '.o', object_sha256='a' * 64,
                       producer_id=current['producer_id'], input_binding=current['input_binding'])
            if category == 'storage':
                row['storage_binding'] = current['storage']['binding']
            by_source[source] = row
            rows.append(row)
        defined[symbol] = [by_source[source]['object_path']]
    for caller, callee in ram.edges():
        references.setdefault(callee, []).append(defined[caller][0])
    # Existing VM aliases coexist with the new pair; they are not new nub providers.
    aliases = dict(ram.LOCK_ALIASES, _mach_vm_map='_mach_vm_map_external', _vm_map='_vm_map_external')
    return current, rows, defined, references, aliases, {'config/IOKit.exports': ram.EXPORT_SHA}


def bind(values):
    proof = ram.begin()
    ram.bind_origins(*values, proof)
    return proof


def retained():
    values = sample()
    current, rows, _, _, aliases, exports = values
    proof = bind(values)
    counts = {name: 1 for name in (*ram.origin_specs(), *ram.LOCK_ALIASES)}
    proof.update(passed=True, final_symbols_verified=True, native_kernel_contains_new_nub=True,
                 lock_alias_addresses_verified=True,
                 final_symbol_counts=counts, linked_objects=1078)
    storage = dict(binding=current['storage'], units=[row for row in rows if row['category'] == 'storage'])
    state = dict(readonly_ram_nub=proof, alias_evidence=dict(aliases=aliases, source_exports_sha256=exports))
    producer = dict(readonly_ram_nub=deepcopy(proof))
    return current, [row for row in rows if row['category'] == 'native'], storage, state, producer, dict(object_count=1078)


def final_sample():
    values = sample()
    current = values[0]
    current.update(inventory=[], dependencies={name: {} for name in native.EXTRAS})
    addresses = {symbol: index for index, symbol in enumerate(ram.origin_specs(), 1)}
    addresses.update({name: addresses[target] for name, target in ram.LOCK_ALIASES.items()})
    text = '\n'.join(f'{value:016x} T {name}' for name, value in addresses.items())
    return text, dict(link_succeeded=True, returncode=0, object_count=10), current, bind(values)


def run():
    counts = [0, 0, 0]

    def check(group, condition):
        assert condition
        counts[group] += 1

    def denied(group, function):
        try:
            function()
        except (ValueError, KeyError, TypeError):
            counts[group] += 1
        else:
            raise AssertionError('new profile denial did not reject')

    old = ram.selected_sources()
    new = ram.selected_sources(True)
    check(0, sdk.PROVIDER_SOURCE in old and ram.NUB_SOURCE not in old)
    check(0, sdk.PROVIDER_SOURCE not in new and all(new[k] == v for k, v in ram.NUB_PINS.items()))
    check(0, ram.enabled(dict(producer={}, bindings={})) is False)
    check(0, ram.enabled(sample()[0]) is True)
    denied(0, lambda: ram.selected_sources(1))
    denied(0, lambda: storage_link.builder.build(None, None, readonly_ram_nub=True))
    for field in ('producer', 'bindings'):
        item = sample()[0]
        del item[field][ram.PROFILE_KEY]
        denied(0, lambda item=item: ram.enabled(item))
    item = sample()[0]
    item['producer'][ram.PROFILE_KEY] = dict(ram.profile(), provider=sdk.PROVIDER_SOURCE)
    denied(0, lambda: ram.enabled(item))
    old_units = storage_link.storage_units(PurePosixPath('/proof'))
    new_units = storage_link.storage_units(PurePosixPath('/proof'), True)
    check(0, len(old_units) == len(new_units) == 6 and old_units[2][0].name == Path(sdk.PROVIDER_SOURCE).name and
          new_units[2][0].name == Path(ram.NUB_SOURCE).name and old_units[:2] == new_units[:2] and old_units[3:] == new_units[3:])
    tree = ast.parse((ram.PORT / 'phase1_iostorage_kernel_link.py').read_bytes())
    calls = [node for node in ast.walk(tree) if isinstance(node, ast.Call)]
    check(0, any(isinstance(node.func, ast.Attribute) and node.func.attr == 'build' and
                 any(k.arg == 'readonly_ram_nub' and isinstance(k.value, ast.Attribute) and
                     k.value.attr == 'readonly_ram_nub' for k in node.keywords) for node in calls))

    check(1, bind(sample())['object_provenance_verified'] is True)
    # These mutations each affect a new origin/alias/reference predicate, not old core functionality.
    for symbol in ('_IOLockAlloc', '_IOLockFree', ram.META_INSTANCE, ram.BASE_VTABLE):
        item = deepcopy(sample())
        path = item[2][symbol][0]
        next(row for row in item[1] if row['object_path'] == path)['source_sha256'] = 'b' * 64
        denied(1, lambda item=item: bind(item))
    for symbol in (ram.NUB_VTABLE, ram.NUB_META):
        item = deepcopy(sample())
        item[2][symbol].append('/shim.o')
        denied(1, lambda item=item: bind(item))
    item = deepcopy(sample()); item[4]['_IOLockLock'] = '_shim'
    denied(1, lambda: bind(item))
    item = deepcopy(sample()); item[5]['config/IOKit.exports'] = 'b' * 64
    denied(1, lambda: bind(item))
    item = deepcopy(sample()); item[2]['_IOLockLock'] = [item[2][ram.NUB_READ][0]]
    denied(1, lambda: bind(item))
    item = deepcopy(sample())
    path = item[2]['_lck_mtx_unlock'][0]
    next(row for row in item[1] if row['object_path'] == path)['source'] = 'shim.c'
    denied(1, lambda: bind(item))
    for caller, callee in ram.edges()[:4]:
        item = deepcopy(sample()); item[3][callee].remove(item[2][caller][0])
        denied(1, lambda item=item: bind(item))
    item = deepcopy(sample()); item[1].append(dict(item[1][0], object_path='/probe.o', source='@storage/phase1_iostorage_provider_object.cpp'))
    denied(1, lambda: bind(item))
    item = deepcopy(sample()); item[1][0]['storage_binding'] = 'b' * 64
    denied(1, lambda: bind(item))

    check(2, ram.verify_profile(*retained()) is None)
    for key in ('registered_provider', 'native_activation', 'physical_ready'):
        item = deepcopy(retained())
        item[3][ram.PROFILE_KEY][key] = True
        item[4][ram.PROFILE_KEY][key] = True
        denied(2, lambda item=item: ram.verify_profile(*item))
    item = deepcopy(retained()); item[2]['binding']['proof']['readonly_ram_sdk_delta_sha256'] = {}
    denied(2, lambda: ram.verify_profile(*item))
    item = deepcopy(retained()); item[3][ram.PROFILE_KEY]['final_symbol_counts'][ram.NUB_VTABLE] = True
    item[4][ram.PROFILE_KEY] = deepcopy(item[3][ram.PROFILE_KEY])
    denied(2, lambda: ram.verify_profile(*item))
    item = deepcopy(retained()); item[3][ram.PROFILE_KEY]['members'][ram.NUB_READ]['source'] = '@storage/probe.cpp'
    item[4][ram.PROFILE_KEY] = deepcopy(item[3][ram.PROFILE_KEY])
    denied(2, lambda: ram.verify_profile(*item))
    item = deepcopy(retained()); item[3]['alias_evidence']['aliases']['_IOLockUnlock'] = '_shim'
    denied(2, lambda: ram.verify_profile(*item))
    item = deepcopy(retained()); del item[0]['bindings'][ram.PROFILE_KEY]
    denied(2, lambda: ram.verify_profile(*item))
    item = deepcopy(retained()); item[0]['producer'][ram.PROFILE_KEY]['schema'] = 'old-profile'
    denied(2, lambda: ram.verify_profile(*item))
    item = final_sample()
    check(2, ram.final_symbols(*item) is None and item[3]['lock_alias_addresses_verified'] is True)
    text, linked, current, proof = final_sample()
    wrong = '\n'.join('ffff T _IOLockLock' if line.endswith(' _IOLockLock') else line for line in text.splitlines())
    denied(2, lambda: ram.final_symbols(wrong, linked, current, proof))
    denied(2, lambda: ram.final_symbols(text + '\nffff T ' + ram.NUB_VTABLE, linked, current, proof))
    missing = '\n'.join(line for line in text.splitlines() if not line.endswith(' ' + ram.BASE_VTABLE))
    denied(2, lambda: ram.final_symbols(missing, linked, current, proof))
    denied(2, lambda: ram.final_symbols(text + '\nffff T __ZTV26Note10RAMBlockProviderProbe', linked, current, proof))
    return dict(groups=3, cases=sum(counts), group_cases=counts, host_C_compiles=0, old_suites=0)
