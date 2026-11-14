"""Validate original current-link ownership metadata before dropping compiler detail."""
import hashlib
import json
from pathlib import PurePosixPath
import re

from current_native_kernel import digest, EXTRAS

RAW_MAX = 32 * 1024 * 1024
FETCH_RAW_MAX = 64 * 1024 * 1024
COMPACT_MAX = 8 * 1024 * 1024
CORE = ('source', 'category', 'passed', 'source_sha256', 'object_path', 'object_sha256',
        'producer_id', 'input_binding')
CODES = {'compact_input_shape', 'compact_context_binding', 'compact_inventory_binding',
         'compact_duplicate_receipt', 'compact_source_binding', 'compact_object_owner',
         'compact_assembly_binding', 'compact_storage_binding', 'compact_filelist_binding', 'compact_output_limit',
         'compact_fetch_binding'}
STORAGE = ('IOStorage.cpp', 'IOBlockStorageDevice.cpp', 'phase1_iostorage_provider_object.cpp',
           'note10_iostorage_pio_bridge.cpp', 'note10_iostorage_read_range.c', 'note10_iostorage_read_request.c')


def require(condition, code):
    if not condition:
        raise ValueError(code)


def unique(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, 'compact_input_shape')
        result[key] = value
    return result


def hex64(value):
    return type(value) is str and re.fullmatch('[0-9a-f]{64}', value) is not None


def validate_rows(rows, current, storage, link, filelist, producer, *, user_exception_fetch=False, readonly_ram_nub=False):
    from phase1_readonly_ram_block_device import enabled, NUB_SOURCE, profile, SDK_DELTA
    require(type(readonly_ram_nub) is bool and enabled(current) is readonly_ram_nub, 'compact_context_binding')
    selected_storage = tuple(PurePosixPath(NUB_SOURCE).name if name == 'phase1_iostorage_provider_object.cpp' and readonly_ram_nub else name for name in STORAGE)
    require(type(user_exception_fetch) is bool, 'compact_input_shape')
    extras = dict(EXTRAS)
    if user_exception_fetch:
        from prepare_user_exception_fetch import UNIT, admit_provenance
        try:
            admit_provenance(current)
        except ValueError:
            raise ValueError('compact_fetch_binding') from None
        provider_path = PurePosixPath(current['dependencies'][UNIT]['path'])
        require(provider_path.is_absolute() and '..' not in provider_path.parts and
                provider_path.as_posix() == current['dependencies'][UNIT]['path'] and
                provider_path.parts[-3:] == ('note10', 'xnu26', 'note10_user_instruction_fetch.c'),
                'compact_source_binding')
        extras[UNIT] = 'port'
    else:
        require('user_exception_fetch' not in current['producer'], 'compact_context_binding')
    from phase1_owned_ram_kernel_integration import enabled as factory_enabled, UNIT as FACTORY_UNIT
    factory_selected=factory_enabled(current)
    if factory_selected:
        extras[FACTORY_UNIT]='port'
        selected_storage=(selected_storage[0],'IOMedia.cpp',*selected_storage[1:])
    row_count, linked_count = (1073,1080) if factory_selected else (1072, 1078) if user_exception_fetch else (1071, 1077)
    require(type(rows) is list and len(rows) == row_count and all(type(row) is dict for row in rows), 'compact_input_shape')
    require(current['kind'] == 'v84-current-native' and current['producer_id'] == digest(current['producer']) and
            current['input_binding'] == digest(current['bindings']) and
            current['producer']['source_commit'] == producer['source_head'], 'compact_context_binding')
    inventory = current['inventory']
    require(type(inventory) is list and len(inventory) == 1067 and
            digest([{k: row[k] for k in ('source','component','kind','source_sha256')} for row in inventory]) ==
            producer['memdev_integration']['native_manifest_sha256'], 'compact_inventory_binding')
    expected = {row['source']: row for row in inventory}
    require(len(expected) == 1067 and not set(expected) & set(extras) and
            set(current['dependencies']) == set(extras), 'compact_inventory_binding')
    categories = {name: 'native' for name in expected} | extras
    sources = {name: row['source_sha256'] for name, row in expected.items()}
    sources.update({name: row['source_sha256'] for name, row in current['dependencies'].items()})
    seen, paths = set(), set()
    owner = PurePosixPath(current['producer']['objects_root'])
    require(owner.is_absolute() and '..' not in owner.parts, 'compact_object_owner')
    for row in rows:
        require(set(CORE) <= set(row), 'compact_input_shape')
        name = row['source']
        require(type(name) is str and name not in seen, 'compact_duplicate_receipt')
        require(re.fullmatch(r'[@A-Za-z0-9_.+/-]{1,192}', name) and not name.startswith('/') and
                '..' not in name.split('/'), 'compact_source_binding')
        require(name in categories and row['category'] == categories[name] and row['passed'] is True and
                hex64(row['source_sha256']) and row['source_sha256'] == sources[name] and hex64(row['object_sha256']) and
                row['producer_id'] == current['producer_id'] and row['input_binding'] == current['input_binding'],
                'compact_source_binding')
        path = row['object_path']
        require(type(path) is str and 0 < len(path) <= 4096 and PurePosixPath(path).is_absolute() and
                PurePosixPath(path).as_posix() == path and '..' not in PurePosixPath(path).parts and
                PurePosixPath(path).is_relative_to(owner) and PurePosixPath(path) != owner and path not in paths,
                'compact_object_owner')
        if name in expected and expected[name]['kind'] == 'assembly':
            require(hex64(current.get('assembly_input')) and row.get('assembly_input') == current['assembly_input'],
                    'compact_assembly_binding')
        if 'assembly_input' in row:
            require(hex64(row['assembly_input']), 'compact_assembly_binding')
        seen.add(name)
        paths.add(path)
    require(seen == set(categories), 'compact_source_binding')
    units = storage['units']
    binding = storage['binding']
    from phase1_iostorage_kernel_link import storage_units
    expected_storage = {'@storage/'+source.name: source_sha
                        for source, _, source_sha in storage_units(PurePosixPath('/source-proof'), readonly_ram_nub, media=factory_selected)}
    require(len(expected_storage) == (7 if factory_selected else 6) and list(expected_storage) == ['@storage/'+name for name in selected_storage] and
            type(units) is list and len(units) == (7 if factory_selected else 6) and
            [row['source'] for row in units] == ['@storage/'+name for name in selected_storage] and
            binding['binding'] == digest(binding['proof']) == producer['storage_binding_sha256'] and
            binding['proof']['producer_id'] == current['producer_id'] and
            binding['proof']['input_binding'] == current['input_binding'], 'compact_storage_binding')
    require((binding['proof'].get('readonly_ram_nub') == profile() and
             binding['proof'].get('readonly_ram_sdk_delta_sha256') == SDK_DELTA) if readonly_ram_nub else
            not ({'readonly_ram_nub', 'readonly_ram_sdk_delta_sha256'} & set(binding['proof'])), 'compact_storage_binding')
    for row in units:
        require(row['passed'] is True and row['category'] == 'storage' and
                row['producer_id'] == current['producer_id'] and row['input_binding'] == current['input_binding'] and
                row['storage_binding'] == binding['binding'] and hex64(row['source_sha256']) and
                row['source_sha256'] == expected_storage[row['source']] and
                hex64(row['object_sha256']) and row['object_sha256'] == producer['storage_object_sha256'][row['source']] and
                type(row['object_path']) is str and row['object_path'] not in paths and
                PurePosixPath(row['object_path']).is_absolute() and '..' not in PurePosixPath(row['object_path']).parts and
                PurePosixPath(row['object_path']).as_posix() == row['object_path'] and
                PurePosixPath(row['object_path']).name == PurePosixPath(row['source']).stem+'.o', 'compact_storage_binding')
        paths.add(row['object_path'])
    require(link['producer_id'] == current['producer_id'] and link['input_binding'] == current['input_binding'] and
            link['link_succeeded'] is True and type(link['returncode']) is int and link['returncode'] == 0 and
            type(link['object_count']) is int and link['object_count'] == linked_count and len(paths) == linked_count and
            filelist.decode('utf-8').splitlines() == [row['object_path'] for row in rows + units] and
            hashlib.sha256(filelist).hexdigest() == link['filelist_sha256'], 'compact_filelist_binding')


def project(raw, current, storage, link, filelist, producer, *, user_exception_fetch=False, readonly_ram_nub=False):
    limit = FETCH_RAW_MAX if user_exception_fetch else RAW_MAX
    require(type(raw) is bytes and 0 < len(raw) <= limit, 'compact_input_shape')
    rows = json.loads(raw, object_pairs_hook=unique)
    validate_rows(rows, current, storage, link, filelist, producer, user_exception_fetch=user_exception_fetch, readonly_ram_nub=readonly_ram_nub)
    compact = [{key: row[key] for key in (*CORE, *(['assembly_input'] if 'assembly_input' in row else []))} for row in rows]
    from phase1_owned_ram_kernel_integration import enabled as factory_enabled
    value = dict(schema='note10-v261-compact-native-object-receipts-v1' if factory_enabled(current) else
                 'note10-v204-compact-native-object-receipts-v1' if readonly_ram_nub else
                 'note10-v200-compact-native-object-receipts-v1' if user_exception_fetch else
                 'note10-v174-compact-native-object-receipts-v1', raw_bytes=len(raw),
                 raw_sha256=hashlib.sha256(raw).hexdigest(), units=compact)
    output = (json.dumps(value, sort_keys=True, indent=2)+'\n').encode()
    require(len(output) <= COMPACT_MAX, 'compact_output_limit')
    return compact, output
