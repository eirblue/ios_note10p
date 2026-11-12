"""Genuine-native source representation only; never a physical ownership grant."""
import hashlib
import struct

PAGE = 16384
MAX_KERNEL = 32 * 1024 * 1024
MAX_ADAPTER = 1024 * 1024
WIRE = struct.Struct('<8sII10Q32s32s32s32s32s')
assert WIRE.size == 256
PRODUCER_SCHEMA = 'note10-v204-readonly-ram-nub-kernel-artifact-result-v1'
MANIFEST_SCHEMA = 'note10-v204-readonly-ram-nub-native-handoff-build-v1'
AUTHORITY = dict(physical_ready=False, physical_reservation_verified=False, device_authorized=False,
                 hardware_verified=False, lifetime_verified=False, return_qualified=False, device_operations=[])


def require(ok, reason):
    if not ok:
        raise ValueError(reason)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def hexadecimal(value, width=64):
    require(type(value) is str and len(value) == width and value != '0'*width and
            all(c in '0123456789abcdef' for c in value), 'typed nonzero hexadecimal identity required')
    return value


def validate_origin(producer, manifest, expected):
    keys = {'source_head', 'run_id', 'run_attempt', 'kernel_sha256', 'kernel_bytes', 'producer_id', 'input_binding'}
    require(type(expected) is dict and set(expected) == keys and type(producer) is dict and type(manifest) is dict,
            'exact separately reviewed genuine-native origin binding required')
    require(producer.get('schema') == PRODUCER_SCHEMA and manifest.get('schema') == MANIFEST_SCHEMA and
            producer.get('PC_only') is not True and manifest.get('purpose') != 'synthetic-pc-model' and
            producer.get('passed') is True and producer.get('runtime_executed') is False and
            producer.get('physical_ready') is False and manifest.get('physical_reservation_verified') is False and
            manifest.get('deployment_ready') is False and manifest.get('hardware_verified') is False and
            manifest.get('device_operations') == [], 'synthetic/PC source or promoted origin authority forbidden')
    hexadecimal(expected['source_head'], 40)
    for name in ('kernel_sha256', 'producer_id', 'input_binding'):
        hexadecimal(expected[name])
    require(type(expected['run_id']) is int and expected['run_id'] > 0 and type(expected['run_attempt']) is int and
            expected['run_attempt'] == 1 and type(expected['kernel_bytes']) is int and 32 <= expected['kernel_bytes'] <= MAX_KERNEL,
            'bounded exact native run and kernel extent required')
    expected_producer = dict(source_head=expected['source_head'], run_id=expected['run_id'], run_attempt=1,
                             kernel_sha256=expected['kernel_sha256'], kernel_bytes=expected['kernel_bytes'])
    expected_manifest = dict(source_commit=expected['source_head'], run_id=expected['run_id'], run_attempt=1,
                             output_sha256=expected['kernel_sha256'], output_size=expected['kernel_bytes'],
                             producer_id=expected['producer_id'], input_binding=expected['input_binding'])
    require(all(type(producer.get(k)) is type(v) and producer[k] == v for k, v in expected_producer.items()) and
            all(type(manifest.get(k)) is type(v) and manifest[k] == v for k, v in expected_manifest.items()),
            'actual native producer/manifest/private expectation disagree')


def parse_kernel(raw):
    require(type(raw) is bytes and 32 <= len(raw) <= MAX_KERNEL, 'bounded immutable Mach-O bytes required')
    magic, cpu, subtype, kind, count, size, _, _ = struct.unpack_from('<8I', raw)
    require((magic, cpu, subtype, kind) == (0xfeedfacf, 0x100000c, 0, 2) and
            1 <= count <= 4096 and 32+size <= len(raw), 'closed arm64 MH_EXECUTE header required')
    at, segments, pools, entry, symtab = 32, [], [], None, None
    for _ in range(count):
        require(at+8 <= 32+size, 'truncated Mach-O command')
        command, length = struct.unpack_from('<II', raw, at)
        require(length >= 8 and length % 8 == 0 and at+length <= 32+size and
                command not in (0xc, 0x80000018, 0x8000001f, 0x80000020, 0x80000023), 'invalid/dynamic Mach-O command')
        if command == 0x19:
            require(length >= 72, 'truncated segment command')
            name = raw[at+8:at+24].split(b'\0', 1)[0].decode('ascii')
            va, span, offset, file_bytes, maximum, initial, sections, _ = struct.unpack_from('<4Q4I', raw, at+24)
            require(length == 72+80*sections and file_bytes <= span and offset+file_bytes <= len(raw) and va+span <= 1 << 64 and
                    0 <= initial <= 7 and 0 <= maximum <= 7 and initial & maximum == initial and initial & 6 != 6,
                    'segment/section bounds or permissions differ')
            segment = dict(name=name, virtual_address=va, virtual_size=span, file_offset=offset,
                           file_size=file_bytes, initial_protection=initial)
            require(not span or not any(s['virtual_address'] < va+span and va < s['virtual_address']+s['virtual_size']
                    for s in segments if s['virtual_size']), 'overlapping kernel segments')
            segments.append(segment)
            for index in range(sections):
                section = struct.unpack_from('<16s16sQQ8I', raw, at+72+80*index)
                if section[0].rstrip(b'\0') == b'__n10bt':
                    address, extent, alignment, flags = section[2], section[3], section[5], section[8]
                    require(section[1].rstrip(b'\0') == b'__DATA' and name == '__DATA' and initial == 3 and
                            flags & 255 == 1 and alignment >= 14 and extent > 0 and address % PAGE == extent % PAGE == 0 and
                            va <= address < address+extent <= va+span, 'actual writable zero-fill bootstrap pool required')
                    pools.append((address, extent))
        elif command == 5:
            require(entry is None and length == 288 and struct.unpack_from('<II', raw, at+8) == (6, 68), 'one ARM64 thread entry required')
            entry = struct.unpack_from('<Q', raw, at+16+256)[0]
        elif command == 2:
            require(symtab is None and length == 24, 'one bounded symbol table required')
            symtab = struct.unpack_from('<4I', raw, at+8)
        at += length
    selected = [s for s in segments if s['virtual_size']]
    require(at == 32+size and selected and entry is not None and symtab is not None and len(pools) == 1, 'complete native entry/pool/symbol geometry required')
    base = min(s['virtual_address'] for s in selected)
    end = max(s['virtual_address']+s['virtual_size'] for s in selected)
    span = (end-base+PAGE-1)//PAGE*PAGE
    executable = [s for s in segments if s['initial_protection'] & 4 and s['virtual_address'] <= entry and
                  entry+4 <= s['virtual_address']+s['file_size']]
    require(base % PAGE == 0 and 0 < span <= MAX_KERNEL and entry % 4 == 0 and len(executable) == 1,
            'current native entry must be file-backed executable within bounded materialization')
    symoff, symbols_count, stroff, strings_bytes = symtab
    require(0 < symbols_count <= 1000000 and symoff+16*symbols_count <= len(raw) and stroff+strings_bytes <= len(raw), 'bounded symbols/strings required')
    names, wanted = {}, {'__start', '_bootstrap_pagetables', '_n10_exynos_bootstrap_map'}
    strings = raw[stroff:stroff+strings_bytes]
    for index in range(symbols_count):
        name_at, kind, section_index, _, value = struct.unpack_from('<IBBHQ', raw, symoff+16*index)
        if kind & 0xe0:
            continue
        require(name_at < len(strings), 'symbol name outside strings')
        stop = strings.find(b'\0', name_at)
        require(stop >= 0, 'unterminated symbol name')
        name = strings[name_at:stop].decode('ascii')
        if name in wanted:
            require(kind & 0xe == 0xe and section_index > 0 and name not in names, 'unique defined entry/pool/mapper symbols required')
            names[name] = value
    pool, pool_bytes = pools[0]
    require(set(names) == wanted and names['__start'] == entry and names['_bootstrap_pagetables'] == pool and
            any(s['initial_protection'] & 4 and s['virtual_address'] <= names['_n10_exynos_bootstrap_map'] <
                s['virtual_address']+s['file_size'] for s in segments), 'actual entry/pool/mapper provenance required')
    return dict(virtual_base=base, kernel_span=span, kernel_entry_offset=entry-base,
                entry_extent_offset=executable[0]['virtual_address']-base, entry_extent_bytes=executable[0]['file_size'],
                pool_offset=pool-base, pool_bytes=pool_bytes, segments=segments)


def produce(raw, adapter_raw, producer, manifest, expected, expected_adapter_sha,
            materialize_kernel, materialize_adapter, counts):
    validate_origin(producer, manifest, expected)
    counts['kernel_hashes'] += 1
    kernel_sha = digest(raw)
    require(len(raw) == expected['kernel_bytes'] and kernel_sha == expected['kernel_sha256'], 'current native kernel content differs')
    geometry = parse_kernel(raw)
    require(type(adapter_raw) is bytes and 64 <= len(adapter_raw) <= MAX_ADAPTER, 'bounded immutable adapter ELF required')
    counts['adapter_hashes'] += 1
    require(digest(adapter_raw) == hexadecimal(expected_adapter_sha), 'adapter content differs')
    counts['kernel_materializations'] += 1
    base, memory = materialize_kernel(raw, geometry['segments'])
    require(type(memory) is bytes and base == geometry['virtual_base'] and len(memory) == geometry['kernel_span'], 'neutral kernel materializer ABI differs')
    counts['adapter_materializations'] += 1
    adapter, entry, record = materialize_adapter(adapter_raw)
    require(type(adapter) is bytes and len(adapter) == PAGE and type(entry) is type(record) is int and
            entry % 4 == 0 and 0 <= entry <= PAGE-4 and record % 64 == 0 and 0 <= record <= PAGE-64,
            'neutral adapter materializer ABI differs')
    memory_sha, adapter_sha = digest(memory), digest(adapter)
    fields = [geometry[k] for k in ('virtual_base', 'kernel_span', 'kernel_entry_offset', 'entry_extent_offset',
              'entry_extent_bytes', 'pool_offset', 'pool_bytes')]+[len(adapter), entry, record]
    descriptor = WIRE.pack(b'N209PAY1', 1, WIRE.size, *fields, bytes.fromhex(kernel_sha), bytes.fromhex(memory_sha),
                           bytes.fromhex(adapter_sha), bytes.fromhex(expected['producer_id']), bytes.fromhex(expected['input_binding']))
    metadata = dict(schema='note10-current-native-source-parcel-v1', purpose='current-native-source-candidate',
                    source_head=expected['source_head'], run_id=expected['run_id'], run_attempt=1,
                    producer_id=expected['producer_id'], input_binding=expected['input_binding'], kernel_input_bytes=len(raw),
                    kernel_input_sha256=kernel_sha, kernel_materialized_bytes=len(memory), kernel_materialized_sha256=memory_sha,
                    adapter_input_bytes=len(adapter_raw), adapter_input_sha256=expected_adapter_sha, adapter_sha256=adapter_sha,
                    descriptor_bytes=len(descriptor), descriptor_sha256=digest(descriptor),
                    geometry={k: v for k, v in geometry.items() if k != 'segments'}, adapter_entry_offset=entry, adapter_record_offset=record,
                    bootargs_materialized=False, ADT_materialized=False, actual_destination_bound=False, **AUTHORITY)
    return dict(kernel=memory, adapter=adapter, descriptor=descriptor, metadata=metadata)
