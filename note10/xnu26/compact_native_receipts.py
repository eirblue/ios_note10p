"""Validate original current-link ownership metadata before dropping compiler detail."""
import hashlib
import json
from pathlib import PurePosixPath
import re

from current_native_kernel import digest, EXTRAS

RAW_MAX = 32 * 1024 * 1024
COMPACT_MAX = 8 * 1024 * 1024
CORE = ('source', 'category', 'passed', 'source_sha256', 'object_path', 'object_sha256',
        'producer_id', 'input_binding')
CODES = {'compact_input_shape', 'compact_context_binding', 'compact_inventory_binding',
         'compact_duplicate_receipt', 'compact_source_binding', 'compact_object_owner',
         'compact_assembly_binding', 'compact_storage_binding', 'compact_filelist_binding', 'compact_output_limit'}
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


def project(raw, current, storage, link, filelist, producer):
    require(type(raw) is bytes and 0 < len(raw) <= RAW_MAX, 'compact_input_shape')
    rows = json.loads(raw, object_pairs_hook=unique)
    require(type(rows) is list and len(rows) == 1071 and all(type(row) is dict for row in rows), 'compact_input_shape')
    require(current['kind'] == 'v84-current-native' and current['producer_id'] == digest(current['producer']) and
            current['input_binding'] == digest(current['bindings']) and
            current['producer']['source_commit'] == producer['source_head'], 'compact_context_binding')
    inventory = current['inventory']
    require(type(inventory) is list and len(inventory) == 1067 and
            digest([{k: row[k] for k in ('source','component','kind','source_sha256')} for row in inventory]) ==
            producer['memdev_integration']['native_manifest_sha256'], 'compact_inventory_binding')
    expected = {row['source']: row for row in inventory}
    require(len(expected) == 1067 and not set(expected) & set(EXTRAS) and
            set(current['dependencies']) == set(EXTRAS), 'compact_inventory_binding')
    categories = {name: 'native' for name in expected} | EXTRAS
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
                        for source, _, source_sha in storage_units(PurePosixPath('/source-proof'))}
    require(len(expected_storage) == 6 and list(expected_storage) == ['@storage/'+name for name in STORAGE] and
            type(units) is list and len(units) == 6 and
            [row['source'] for row in units] == ['@storage/'+name for name in STORAGE] and
            binding['binding'] == digest(binding['proof']) == producer['storage_binding_sha256'] and
            binding['proof']['producer_id'] == current['producer_id'] and
            binding['proof']['input_binding'] == current['input_binding'], 'compact_storage_binding')
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
            type(link['object_count']) is int and link['object_count'] == 1077 and len(paths) == 1077 and
            filelist.decode('utf-8').splitlines() == [row['object_path'] for row in rows + units] and
            hashlib.sha256(filelist).hexdigest() == link['filelist_sha256'], 'compact_filelist_binding')
    compact = [{key: row[key] for key in (*CORE, *(['assembly_input'] if 'assembly_input' in row else []))} for row in rows]
    value = dict(schema='note10-v174-compact-native-object-receipts-v1', raw_bytes=len(raw),
                 raw_sha256=hashlib.sha256(raw).hexdigest(), units=compact)
    output = (json.dumps(value, sort_keys=True, indent=2)+'\n').encode()
    require(len(output) <= COMPACT_MAX, 'compact_output_limit')
    return compact, output
