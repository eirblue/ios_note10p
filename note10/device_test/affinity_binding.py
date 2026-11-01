"""Closed Linux logical-map observation; no hardware control or FDT joining."""
import hashlib
from pathlib import Path
import re

HERE = Path(__file__).resolve().parent
PROFILE = 'cpu-affinity-binding-v1'
KIND = 'cpu-affinity-binding'
CAPACITY = 32
HWID_MASK = 0xff00ffffff
API_PINS = {
    'arch/arm64/include/asm/smp_plat.h': '53e9dcea3c21e8339340f8fe020b7e55d16096130a6ead5529ead1915744927e',
    'include/linux/cpu.h': 'cfd98e81e72d50a9291414ec3bce5def163a7fa53971a4d885762aaf0a3c7936',
    'include/linux/smp.h': '8d1094af3b3ddde955be5dd9e8d84349583883d40df3bf73832acb4d95ca0ff0',
}
SOURCES = ('affinity_binding.py', 'cpu_affinity_binding.c', 'affinity_binding_composition.c',
           'build_cpu_affinity_binding.py', 'test_affinity_binding.py')
BEGIN = ('id', 'cycle', 'kind', 'online', 'count', 'capacity', 'fdt', 'raw_binding', 'status')
ROW = ('id', 'cycle', 'kind', 'cpu', 'map', 'mpidr', 'cntfrq', 'equal')
END = ('id', 'cycle', 'kind', 'online', 'seen', 'count', 'status', 'fdt', 'raw_binding')
EXTRA_FIELDS = ('raw_input_binding', 'original_fdt_digest_unavailable')


def require(value, message):
    if not value:
        raise ValueError(message)


def install(source, identity):
    from builtin_init_route import install as baseline_install
    source = Path(source)
    for name, digest in API_PINS.items():
        require(hashlib.sha256((source/name).read_bytes()).hexdigest() == digest,
                'pinned affinity API differs: '+name)
    result = baseline_install(source, identity)
    replacements = {
        'drivers/misc/note10_sha256_kat.c': (HERE/'affinity_binding_composition.c').read_bytes(),
        'drivers/misc/cpu_affinity_binding.c': (HERE/'cpu_affinity_binding.c').read_bytes(),
    }
    kconfig = source/'drivers/misc/note10_sha256_kat.Kconfig'
    kconfig.write_bytes(kconfig.read_bytes()+b"""
config NOTE10_CPU_AFFINITY_BINDING
\tbool "Note10 boot-associated Linux CPU logical-map observation"
\tdepends on NOTE10_SHA256_KAT_RECOVERY && NOTE10_BUILTIN_INIT_ROUTE && SMP
\tdefault n
\thelp
\t  Fixed per-CPU logical-map/MPIDR/CNTFRQ reads only. Existing recovery.
\t  No CPU shutdown, FDT snapshot, topology repair or XNU execution.
""")
    for name, data in replacements.items():
        (source/name).write_bytes(data)
    return {name: hashlib.sha256((source/name).read_bytes()).hexdigest()
            for name in (*result, *replacements)}


def input_binding(result, lines):
    """Closed new kind/source binding used by the existing package input path."""
    require(result.get('version') == 'v78' and result.get('diagnostic_kind') == KIND and
            result.get('raw_input_binding') is False and
            result.get('original_fdt_digest_unavailable') is True,
            'new affinity kind and unavailable FDT contract required')
    require({'CONFIG_NOTE10_CPU_AFFINITY_BINDING=y', 'CONFIG_SMP=y'}.issubset(lines) and
            'CONFIG_NOTE10_SHA256_STREAM_STATE=y' not in lines,
            'closed affinity option differs')
    pins = result.get('source_sha256', {})
    for name in SOURCES:
        require(pins.get('note10/device_test/'+name) == hashlib.sha256((HERE/name).read_bytes()).hexdigest(),
                'new affinity producer source differs: '+name)
    return dict(raw_input_binding=False, original_fdt_digest_unavailable=True)


def decode(text, identity, cycle):
    from decode_reservation import checksum
    require(isinstance(text, str) and len(text) <= 16*1024*1024 and
            re.fullmatch('[0-9a-f]{32}', identity) and re.fullmatch('[0-9a-f]{32}', cycle),
            'bounded affinity log and expected build/cycle required')
    lines = [line for line in text.splitlines() if 'N10AFF1' in line]
    require(3 <= len(lines) <= CAPACITY+2, 'bounded complete affinity frame batch required')
    records, boots = [], set()
    for line in lines:
        match = re.search(r'N10BOOTLINK2 boot=([0-9a-f]{32}) N10AFF1 ([^\r\n\x00]{1,383}) checksum=([0-9a-f]{8})$', line)
        require(match is not None, 'affinity frame format')
        body = match[2]
        require(body.isascii() and checksum(body.encode('ascii')) == int(match[3], 16), 'affinity checksum')
        pairs = [word.split('=') for word in body.split(' ')]
        require(all(len(pair) == 2 for pair in pairs), 'affinity key/value shape')
        keys = tuple(pair[0] for pair in pairs)
        row = dict(pairs)
        kind = row.get('kind')
        require(keys == (BEGIN if kind == 'begin' else ROW if kind == 'row' else END if kind == 'end' else ()),
                'closed affinity schema/order')
        require(row['id'] == identity and row['cycle'] == cycle, 'affinity build/cycle differs')
        boots.add(match[1]); records.append(row)
    require(len(boots) == 1 and '0'*32 not in boots, 'one nonzero affinity boot identity required')
    begin, end = records[0], records[-1]
    require(begin['kind'] == 'begin' and end['kind'] == 'end' and
            all(row['kind'] == 'row' for row in records[1:-1]), 'single ordered affinity BEGIN/ROW/END required')
    require(begin['status'] == end['status'] == '0' and begin['capacity'] == '32' and
            begin['fdt'] == end['fdt'] == 'unavailable' and
            begin['raw_binding'] == end['raw_binding'] == '0', 'affinity status/FDT scope differs')
    require(re.fullmatch('[0-9a-f]{8}', begin['online']) and
            begin['online'] == end['online'] == end['seen'], 'affinity masks differ')
    online = int(begin['online'], 16)
    expected = [cpu for cpu in range(CAPACITY) if online & (1 << cpu)]
    require(1 <= len(expected) <= CAPACITY and begin['count'] == end['count'] == str(len(expected)) and
            len(records) == len(expected)+2, 'complete bounded online set required')
    cpus = []
    for row, cpu in zip(records[1:-1], expected):
        require(row['cpu'] == str(cpu) and re.fullmatch('[0-9a-f]{16}', row['map']) and
                re.fullmatch('[0-9a-f]{16}', row['mpidr']) and
                re.fullmatch('[1-9a-f][0-9a-f]{0,7}', row['cntfrq']) and row['equal'] in ('0', '1'),
                'missing/duplicate/unexpected CPU or invalid tuple field')
        logical_map, mpidr, frequency = (int(row[key], 16) for key in ('map', 'mpidr', 'cntfrq'))
        require(logical_map != 0xffffffffffffffff and
                int(row['equal']) == int(logical_map == (mpidr & HWID_MASK)), 'invalid map/relation observation')
        cpus.append(dict(cpu=cpu, logical_map=logical_map, raw_mpidr=mpidr, cntfrq_hz=frequency,
                         map_matches_raw_affinity=bool(int(row['equal']))))
    return dict(observed=True, passed=True, boot_identity=next(iter(boots)), cpus=cpus,
                online_mask=online, mapping_mismatches=sum(not row['map_matches_raw_affinity'] for row in cpus),
                original_fdt_digest=None, raw_input_binding=False, original_fdt_digest_unavailable=True,
                cpu_shutdown_state_known=False, topology_mapping_verified=False,
                scope='current Linux logical-map/raw-register tuple observation only',
                handoff_ready=False, deployment_ready=False, xnu_executed=False)


def decode_selected(data, banner, identity, cycle):
    from builtin_init_profile import decode as baseline_decode
    observation_decoder = lambda text, rid: decode(text, rid, cycle)
    clipped, observation = baseline_decode(data, banner, identity, cycle,
        digest_decoder=observation_decoder, digest_marker=b'N10AFF1')
    require(observation['kat']['boot_identity'] == observation['boot_identity'],
            'affinity/route/recovery boot identity differs')
    # Existing container key 'kat' holds the selected diagnostic, not a SHA claim.
    return clipped, observation
