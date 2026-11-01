"""v81 owned post-architecture FDT snapshot evidence; no pristine-input claim."""
import hashlib
from pathlib import Path
import re

HERE = Path(__file__).resolve().parent
KIND = 'early-fdt-binding'
PROFILE = KIND+'-v1'
BOUNDARY = 'post_arch_crc'
CAPACITY = 524288
FIELDS = ('fdt_capture_boundary', 'fdt_snapshot_capacity_bytes', 'raw_input_binding')
SOURCES = ('early_fdt_binding.py', 'early_fdt_binding.c', 'early_fdt_composition.c',
           'build_early_fdt_binding.py', 'test_early_fdt_binding.py', 'early_fdt_fixture.c')
API_PINS = {
    'drivers/of/fdt.c': 'e655d0f3902e4559932a8c262177a74623468caeda04b338c2de81d992593b34',
    'arch/arm64/mm/mmu.c': '18bb3b58865215b834e86aa8e44bf8f3c7f40c53428183351120958e25c43541',
    'arch/arm64/kernel/kaslr.c': '92cc0ecb325d69d5d617d7379e661a0e6975c886e6b9f70a543c4fbfc408015f',
    'crypto/sha256_generic.c': 'c85f77c45bc469f402311c9bf2a0ea4c456c64675ecf60fafa0421db25cad96f',
}


def require(value, message):
    if not value:
        raise ValueError(message)


def overlay_fdt(raw):
    """One exact guarded post-CRC hook; original admission/CRC bytes retained."""
    require(hashlib.sha256(raw).hexdigest() == API_PINS['drivers/of/fdt.c'], 'pinned FDT verifier differs')
    old = b'bool __init early_init_dt_verify(void *params)\n'
    declaration = (b'#ifdef CONFIG_NOTE10_EARLY_FDT_BINDING\n'
        b'extern void __init n10_early_fdt_capture(const void *params, unsigned int length);\n'
        b'#endif\n\n')
    anchor = (b'\tof_fdt_crc32 = crc32_be(~0, initial_boot_params,\n'
              b'\t\t\t\tfdt_totalsize(initial_boot_params));\n')
    require(raw.count(old) == raw.count(anchor) == 1, 'unique FDT hook anchors required')
    call = (b'#ifdef CONFIG_NOTE10_EARLY_FDT_BINDING\n'
            b'\tn10_early_fdt_capture(initial_boot_params, fdt_totalsize(initial_boot_params));\n'
            b'#endif\n')
    return raw.replace(old, declaration+old).replace(anchor, anchor+call)


def install(source, identity):
    from builtin_init_route import install as baseline_install
    source = Path(source)
    for name, pin in API_PINS.items():
        require(hashlib.sha256((source/name).read_bytes()).hexdigest() == pin, 'pinned early FDT API differs: '+name)
    fdt = overlay_fdt((source/'drivers/of/fdt.c').read_bytes())
    result = baseline_install(source, identity)
    replacements = {
        'drivers/misc/note10_sha256_kat.c': (HERE/'early_fdt_composition.c').read_bytes(),
        'drivers/misc/early_fdt_binding.c': (HERE/'early_fdt_binding.c').read_bytes(),
        'drivers/of/fdt.c': fdt,
    }
    kconfig = source/'drivers/misc/note10_sha256_kat.Kconfig'
    kconfig.write_bytes(kconfig.read_bytes()+b"""
config NOTE10_EARLY_FDT_BINDING
\tbool "Note10 owned post-architecture FDT snapshot diagnostic"
\tdepends on ARM64 && OF_FLATTREE && NOTE10_SHA256_KAT_RECOVERY && NOTE10_BUILTIN_INIT_ROUTE
\tdefault n
\thelp
\t  Copies at most 512KiB after existing verifier CRC. Hashes the owned
\t  bytes only after recovery is armed. Not pristine firmware or CPU state.
""")
    for name, data in replacements.items():
        (source/name).write_bytes(data)
    return {name: hashlib.sha256((source/name).read_bytes()).hexdigest() for name in (*result, *replacements)}


def linked_footprint(system_map, object_symbols, image_memory_bytes):
    wanted = {'_text', '_end', '__bss_start', '__bss_stop', 'n10_fdt_snapshot'}
    values = {}
    for line in system_map.splitlines():
        parts = line.split()
        if len(parts) == 3 and parts[2] in wanted:
            require(parts[2] not in values, 'duplicate linked footprint symbol')
            values[parts[2]] = int(parts[0], 16)
    sizes = [int(parts[1],16) for line in object_symbols.splitlines()
             if len(parts := line.split()) == 4 and parts[3] == 'n10_fdt_snapshot' and parts[2].lower() == 'b']
    require(set(values) == wanted and sizes == [CAPACITY] and
            values['_text'] < values['__bss_start'] <= values['n10_fdt_snapshot'] and
            values['n10_fdt_snapshot']+CAPACITY <= values['__bss_stop'] <= values['_end'] and
            type(image_memory_bytes) is int and image_memory_bytes == values['_end']-values['_text'],
            'exact snapshot BSS/linked Image extent unavailable')
    return dict(snapshot_capacity_bytes=CAPACITY, image_memory_bytes=image_memory_bytes,
                linked_kernel_bytes=values['_end']-values['_text'],
                bss_start_offset=values['__bss_start']-values['_text'],
                bss_end_offset=values['__bss_stop']-values['_text'],
                snapshot_offset=values['n10_fdt_snapshot']-values['_text'])


def placement_admission(footprint, kernel_address, ramdisk_address, ramdisk_bytes):
    """Only required loaded-kernel/external-ramdisk extent check; no RAM ownership."""
    require(type(footprint) is dict and footprint.get('snapshot_capacity_bytes') == CAPACITY,
            'new linked snapshot footprint required')
    extent = footprint.get('image_memory_bytes')
    require(type(extent) is int and 0 < extent <= 256*1024*1024 and
            all(type(n) is int and 0 <= n < 2**64 for n in (kernel_address,ramdisk_address,ramdisk_bytes)) and
            kernel_address+extent <= 2**64 and ramdisk_address+ramdisk_bytes <= 2**64 and ramdisk_bytes > 0,
            'bounded loaded kernel/ramdisk extents required')
    require(kernel_address+extent <= ramdisk_address or ramdisk_address+ramdisk_bytes <= kernel_address,
            'new linked kernel BSS overlaps external ramdisk')
    return dict(kernel_memory_bytes=extent, external_ramdisk_overlap=False,
                physical_RAM_ownership_established=False, all_firmware_placement_established=False)


def input_binding(result, lines):
    require(result.get('version') == 'v81' and result.get('diagnostic_kind') == KIND and
            result.get('raw_input_binding') is False and result.get('fdt_capture_boundary') == BOUNDARY and
            result.get('fdt_snapshot_capacity_bytes') == CAPACITY, 'closed FDT result scope required')
    require('CONFIG_NOTE10_EARLY_FDT_BINDING=y' in lines and
            not {'CONFIG_NOTE10_CPU_AFFINITY_BINDING=y','CONFIG_NOTE10_SHA256_STREAM_STATE=y'} & set(lines),
            'closed FDT configuration required')
    for name in SOURCES:
        require(result.get('source_sha256',{}).get('note10/device_test/'+name) == hashlib.sha256((HERE/name).read_bytes()).hexdigest(),
                'new FDT producer source differs: '+name)
    footprint = result.get('fdt_snapshot_footprint')
    require(type(footprint) is dict and footprint.get('snapshot_capacity_bytes') == CAPACITY,
            'linked FDT footprint missing')
    return dict(fdt_capture_boundary=BOUNDARY, fdt_snapshot_capacity_bytes=CAPACITY, raw_input_binding=False)


def decode(text, identity, cycle):
    from decode_reservation import checksum
    require(type(text) is str and len(text) <= 16*1024*1024 and
            re.fullmatch('[0-9a-f]{32}',identity) and re.fullmatch('[0-9a-f]{32}',cycle), 'bounded FDT log/identity required')
    lines = [line for line in text.splitlines() if 'N10FDT1' in line]
    require(len(lines) == 1, 'one FDT frame required')
    match = re.search(r'N10BOOTLINK2 boot=([0-9a-f]{32}) N10FDT1 ([^\r\n\x00]{1,383}) checksum=([0-9a-f]{8})$',lines[0])
    require(match is not None and match[1] != '0'*32, 'associated FDT frame required')
    body = match[2]
    require(body.isascii() and checksum(body.encode()) == int(match[3],16), 'FDT checksum differs')
    pairs = [word.split('=') for word in body.split(' ')]
    keys = ('id','cycle','boundary','status','error','length','sha256','raw_binding')
    require(all(len(pair)==2 for pair in pairs) and tuple(pair[0] for pair in pairs)==keys, 'closed FDT frame fields/order required')
    row = dict(pairs)
    require(row['id']==identity and row['cycle']==cycle and row['boundary']==BOUNDARY and row['raw_binding']=='0',
            'FDT build/cycle/boundary/nonclaim differs')
    require(row['status'] in ('ok','unavailable','refused','ambiguous','hash_error') and
            re.fullmatch('0|-[1-9][0-9]{0,4}',row['error']) and re.fullmatch('0|[1-9][0-9]{0,6}',row['length']),
            'FDT status/number format')
    length, error = int(row['length']), int(row['error'])
    ok = row['status']=='ok'
    require((ok and 40 <= length <= CAPACITY and error==0 and re.fullmatch('[0-9a-f]{64}',row['sha256'])) or
            (not ok and length==0 and row['sha256']=='none' and
             ((row['status']=='hash_error' and -4095<=error<0) or (row['status']!='hash_error' and error==0))),
            'FDT status/length/digest relation differs')
    return dict(observed=True, passed=ok, status=row['status'], error=error, length=length,
                sha256=row['sha256'] if ok else None, boot_identity=match[1], capture_boundary=BOUNDARY,
                raw_input_binding=False, pristine_firmware_claimed=False, historical_cpu_join=False,
                handoff_ready=False, deployment_ready=False, xnu_executed=False)


def decode_selected(data, banner, identity, cycle):
    from builtin_init_profile import decode as baseline_decode
    def selected(text, rid):
        observation = decode(text,rid,cycle)
        require(observation['passed'], 'FDT capture status='+observation['status'])
        return observation
    clipped, observation = baseline_decode(data,banner,identity,cycle,digest_decoder=selected,digest_marker=b'N10FDT1')
    require(observation['kat']['boot_identity']==observation['boot_identity'], 'FDT/recovery/route boot differs')
    return clipped, observation


def bind_saved_bytes(observation, raw, expected_sha256):
    """Explicit PC-only exact-byte equality; never binds historical CPU evidence."""
    require(type(raw) is bytes and 40 <= len(raw) <= CAPACITY and
            isinstance(expected_sha256,str) and re.fullmatch('[0-9a-f]{64}',expected_sha256), 'bounded pinned saved bytes required')
    digest = hashlib.sha256(raw).hexdigest()
    require(observation.get('observed') is True and observation.get('passed') is True and
            observation.get('capture_boundary')==BOUNDARY and
            isinstance(observation.get('boot_identity'),str) and re.fullmatch('[0-9a-f]{32}',observation['boot_identity']) and
            observation['boot_identity']!='0'*32 and observation.get('length')==len(raw) and
            observation.get('sha256')==digest==expected_sha256, 'saved bytes do not match observed boundary')
    return dict(raw_input_binding=True, boot_identity=observation['boot_identity'],
                saved_bytes=len(raw), saved_sha256=digest,
                capture_boundary=BOUNDARY, pristine_firmware_claimed=False, historical_cpu_join=False,
                placement_ready=False, handoff_ready=False)
