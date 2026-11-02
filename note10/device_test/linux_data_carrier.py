"""Closed Linux DATA input/decode profile; no loader or hardware authorization."""
import hashlib
import json
import os
from pathlib import Path
import re

HERE = Path(__file__).resolve().parent
KIND = 'linux-data-carrier'
PROFILE = KIND+'-v1'
STAGE = 'late_linux_owned_virtual_decode'
FIELDS = ('data_carrier_stage', 'data_relative_placement_admitted', 'raw_input_binding')
CARRIER_FIELDS = ('data_manifest_sha256', 'data_carrier_sha256', 'data_carrier_bytes',
                  'data_payload_sha256', 'data_payload_bytes')
SOURCES = ('linux_data_carrier.py', 'linux_data_carrier.c', 'linux_data_carrier_composition.c',
           'build_linux_data_carrier.py', 'linux_data_carrier_fixture.c', 'test_linux_data_carrier.py',
           'carrier_lzma.c', 'carrier_lzma.h')
API_PINS = {'arch/arm64/kernel/setup.c': 'f80fd02832b12c48eba11b3e3148c59c6ad87d9ea2328c8c37492d107fd141d7'}
CASE_NAMES = ('test_data_guard_reasons_and_parser_error_wire',)
REASONS = {1:'parameter_missing',2:'parameter_invalid',4:'parameter_duplicate',
           8:'capture_missing',16:'capture_invalid',32:'capture_repeat',64:'input_missing',
           128:'global_mismatch',256:'emit_repeat',512:'sticky_invalid'}

TEST_SOURCES = (*SOURCES, 'sha256_kat_device_profile.py', 'builtin_init_profile.py',
                'prepare_linux_boot.py', 'build_boot_test_packages.py')


def require(value, message):
    if not value:
        raise ValueError(message)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def overlay_setup(raw):
    require(sha(raw) == API_PINS['arch/arm64/kernel/setup.c'], 'pinned DATA setup differs')
    old = b'void __init setup_arch(char **cmdline_p)\n'
    declaration = (b'#ifdef CONFIG_NOTE10_DATA_CARRIER\n#include <linux/initrd.h>\n'
        b'extern void __init n10_data_capture(unsigned long start, unsigned long end);\n#endif\n\n')
    hook = b'\tpaging_init();\n'
    require(raw.count(old) == raw.count(hook) == 1, 'unique post-paging DATA hook required')
    return raw.replace(old, declaration+old, 1).replace(hook, hook+
        b'#ifdef CONFIG_NOTE10_DATA_CARRIER\n\tn10_data_capture(initrd_start, initrd_end);\n#endif\n', 1)


def install(source, identity):
    from builtin_init_route import install as baseline_install
    source = Path(source)
    setup = overlay_setup((source/'arch/arm64/kernel/setup.c').read_bytes())
    result = baseline_install(source, identity)
    replacements = {'arch/arm64/kernel/setup.c': setup,
        'drivers/misc/note10_sha256_kat.c': (HERE/'linux_data_carrier_composition.c').read_bytes(),
        **{'drivers/misc/'+n: (HERE/n).read_bytes() for n in ('linux_data_carrier.c', 'carrier_lzma.c', 'carrier_lzma.h')}}
    config = source/'drivers/misc/note10_sha256_kat.Kconfig'
    config.write_bytes(config.read_bytes()+b'''
config NOTE10_DATA_CARRIER
\tbool "Note10 readonly DATA carrier late decode"
\tdepends on ARM64 && BLK_DEV_INITRD && NOTE10_SHA256_KAT_RECOVERY && NOTE10_BUILTIN_INIT_ROUTE
\tdefault n
\thelp
\t  Captures existing native initrd bounds only. Decodes authenticated DATA
\t  after recovery is armed, into ordinary Linux data pages. Never executes it.
''')
    for name, raw in replacements.items():
        (source/name).write_bytes(raw)
    return {name: sha((source/name).read_bytes()) for name in (*result, *replacements)}


def linked_footprint(system_map, symbols, size, offset, flags):
    wanted = {'_text', '_end', '__bss_start', '__bss_stop', 'n10_data'}
    values = {}
    for line in system_map.splitlines():
        parts = line.split()
        if len(parts) == 3 and parts[2] in wanted:
            require(parts[2] not in values, 'duplicate DATA symbol')
            values[parts[2]] = int(parts[0], 16)
    sizes = [int(p[1], 16) for line in symbols.splitlines() if len(p := line.split()) == 4 and
             p[2].lower() == 'b' and p[3] == 'n10_data']
    require(set(values) == wanted and len(sizes) == 1 and 0 < sizes[0] <= 128 and
            values['_text'] < values['__bss_start'] <= values['n10_data'] and
            values['n10_data']+sizes[0] <= values['__bss_stop'] <= values['_end'] and
            type(size) is int and size == values['_end']-values['_text'], 'DATA linked footprint unavailable')
    return dict(data_state_bytes=sizes[0], linked_kernel_bytes=size, image_text_offset=offset, image_flags=flags)


def relative_admission(result, lines, footprint, *, elf, archive, raw_inputs):
    from early_fdt_binding import ACCEPTED_BASELINE, placement_config_sha256, fixed_route_relation
    config = [l for l in lines if not l.startswith('CONFIG_NOTE10_DATA_CARRIER=') and
              l != '# CONFIG_NOTE10_DATA_CARRIER is not set']
    relation = None
    try:
        relation = fixed_route_relation(elf, archive, result, raw_inputs)
    except ValueError:
        pass
    checks = dict(data_scope=result.get('data_carrier_stage') == STAGE and
        'CONFIG_NOTE10_DATA_CARRIER=y' in lines and not
        {'CONFIG_NOTE10_NATIVE_MEMORY_OBSERVATION=y', 'CONFIG_NOTE10_EARLY_FDT_BINDING=y',
         'CONFIG_NOTE10_CPU_AFFINITY_BINDING=y', 'CONFIG_NOTE10_SHA256_STREAM_STATE=y'} & set(lines),
        linked_span_contained=type(footprint.get('linked_kernel_bytes')) is int and
            0 < footprint['linked_kernel_bytes'] <= ACCEPTED_BASELINE['linked_kernel_bytes'],
        file_bytes_contained=type(result.get('image_bytes')) is int and
            0 < result['image_bytes'] <= ACCEPTED_BASELINE['image_file_bytes'],
        same_header=footprint.get('image_text_offset') == ACCEPTED_BASELINE['header']['text_offset'] and
            footprint.get('image_flags') == ACCEPTED_BASELINE['header']['flags'],
        same_config=placement_config_sha256(config) == ACCEPTED_BASELINE['config_sha256'],
        same_route=all(result.get('source_sha256', {}).get(k) == v for k, v in ACCEPTED_BASELINE['route_sources'].items()) and
            result.get('guarded_init_main_sha256') == ACCEPTED_BASELINE['route_artifacts']['guarded_init_main_sha256'] and relation is not None,
        state_bounded=type(footprint.get('data_state_bytes')) is int and 0 < footprint['data_state_bytes'] <= 128)
    return dict(eligible=all(checks.values()), checks=checks, route_relation=relation,
                observed_runtime_base=False, absolute_FDT_extent_known=False, global_RAM_ownership=False)


def input_binding(result, lines, *, elf, archive, raw_inputs):
    require(result.get('version') == 'v89' and result.get('diagnostic_kind') == KIND and
            result.get('data_carrier_stage') == STAGE and result.get('raw_input_binding') is False,
            'closed new DATA Image required')
    for name in SOURCES:
        require(result.get('source_sha256', {}).get('note10/device_test/'+name) == sha((HERE/name).read_bytes()),
                'DATA Image source differs: '+name)
    admission = relative_admission(result, lines, result['data_footprint'], elf=elf, archive=archive, raw_inputs=raw_inputs)
    require(result.get('data_relative_placement') == admission and admission['eligible'], 'DATA relative placement unresolved')
    return dict(data_carrier_stage=STAGE, data_relative_placement_admitted=True, raw_input_binding=False)


def private_input_record(manifest_raw, raw):
    require(0 < len(manifest_raw) <= 2*1024*1024 and 128 < len(raw) <= 64*1024*1024, 'bounded private carrier required')
    m = json.loads(manifest_raw)
    require(m.get('purpose') == 'fixed-data-carrier-host-preparation' and m.get('accepted') is True and
            m.get('decoder_calls') == 1 and m.get('carrier_admitted') is False and
            m.get('deployment_ready') is False and m.get('device_operations') == [] and
            m.get('xnu_executed') is False and m.get('carrier_bytes') == len(raw) and
            m.get('carrier_sha256') == sha(raw) and m.get('decoded_bytes') == m.get('payload_bytes') and
            m.get('decoded_sha256') == m.get('payload_sha256') and m.get('decode', {}).get('status') == 0,
            'accepted functional carrier binding differs')
    require(type(m.get('payload_bytes')) is int and 0 < m['payload_bytes'] <= 64*1024*1024 and
            re.fullmatch('[0-9a-f]{64}', m.get('payload_sha256', '')), 'bounded accepted payload identity required')
    return dict(data_manifest_sha256=sha(manifest_raw), data_carrier_sha256=sha(raw), data_carrier_bytes=len(raw),
                data_payload_sha256=m['payload_sha256'], data_payload_bytes=m['payload_bytes'])


def bounded_private_read(path, cap):
    path = Path(path)
    require(path.is_file() and not path.is_symlink() and 0 < path.stat().st_size <= cap, 'bounded private DATA input required')
    with path.open('rb') as stream:
        raw = stream.read(cap+1)
    require(0 < len(raw) <= cap, 'private DATA input exceeds cap')
    return raw


def attach_carrier(root, manifest_path, expected):
    from sha256_kat_device_profile import private
    root, path = private(root), private(manifest_path)
    require(path.name == 'carrier-manifest.json' and path.is_file() and not path.is_symlink() and
            path.stat().st_size <= 2*1024*1024, 'private accepted carrier manifest required')
    meta = bounded_private_read(path,2*1024*1024)
    require(sha(meta) == expected, 'approved carrier manifest changed')
    data = private(path.parent/'carrier.data')
    require(data.is_file() and not data.is_symlink() and 128 < data.stat().st_size <= 64*1024*1024,
            'bounded private carrier input required')
    raw = bounded_private_read(data,64*1024*1024)
    fields = private_input_record(meta, raw)
    for name, value in (('carrier.data', raw), ('carrier-manifest.json', meta),
                         ('data-input.json', (json.dumps(fields, sort_keys=True)+'\n').encode())):
        with (root/name).open('xb') as target:
            target.write(value)
    return fields


def carrier_fields(root):
    root = Path(root)
    for name, cap in (('data-input.json',65536),('carrier-manifest.json',2*1024*1024),('carrier.data',64*1024*1024)):
        path = root/name
        require(path.is_file() and not path.is_symlink() and 0 < path.stat().st_size <= cap, 'bounded retained DATA input required')
    expected = json.loads(bounded_private_read(root/'data-input.json',65536))
    require(set(expected) == set(CARRIER_FIELDS), 'closed private DATA fields required')
    meta = bounded_private_read(root/'carrier-manifest.json',2*1024*1024)
    raw = bounded_private_read(root/'carrier.data',64*1024*1024)
    fields = private_input_record(meta, raw)
    require(fields == expected, 'private DATA input changed')
    return fields


def data_cmdline(original, digest):
    require(type(original) is str and 'n10.data_sha' not in original and
            re.fullmatch('[0-9a-f]{64}', digest or ''), 'one new DATA private expectation required')
    value = original+' n10.data_sha='+digest
    require(len(value.encode('ascii')) <= 1535, 'DATA BOOT cmdline exceeds unchanged cap')
    return value


def package_data(build, reference, cmdline, raw):
    require(build.get('device_profile') == PROFILE and build['data_carrier_bytes'] == len(reference) == len(raw) and
            sha(raw) == build['data_carrier_sha256'], 'DATA fixed extent/accepted identity differs')
    return data_cmdline(cmdline, build['data_carrier_sha256'])


def test_source_pins():
    return {name: sha((HERE/name).read_bytes()) for name in TEST_SOURCES}


def retained_pass(record):
    # Caller assertions are not authenticated CI-result provenance.
    # Future reuse requires a separately reviewed actual-result binding.
    raise ValueError('retained PASS disabled: no authenticated actual-result gate')


def decode(text, identity, cycle):
    from decode_reservation import checksum
    lines = [line for line in text.splitlines() if 'N10DATA1' in line]
    require(len(lines) == 1, 'one DATA result required')
    m = re.search(r'N10BOOTLINK2 boot=([0-9a-f]{32}) N10DATA1 ([^\r\n\x00]{1,383}) checksum=([0-9a-f]{8})$', lines[0])
    require(m is not None and m[1] != '0'*32 and checksum(m[2].encode('ascii')) == int(m[3],16), 'DATA boot/checksum differs')
    pairs = [part.split('=') for part in m[2].split(' ')]
    keys = ('id','cycle','kind','status','carrier','stream','payload','consumed','written','calls','digest','reasons','params','captures','retained','ownership','executed')
    require(all(len(p) == 2 for p in pairs) and tuple(p[0] for p in pairs) == keys, 'DATA closed schema required')
    row = dict(pairs)
    require(row['id'] == identity and row['cycle'] == cycle and row['kind'] == 'result' and
            row['ownership'] == row['executed'] == '0' and re.fullmatch('[0-9a-f]{64}', row['digest']), 'DATA identity/nonclaim differs')
    numbers = {}
    for key in ('carrier','stream','payload','consumed','written','calls'):
        require(re.fullmatch('0|[1-9][0-9]{0,8}', row[key]), 'bounded DATA count required')
        numbers[key] = int(row[key])
    require(re.fullmatch('[0-9a-f]{8}',row['reasons']) and int(row['reasons'],16) <= 0x3ff and
            row['params'] in ('0','1','2') and row['captures'] in ('0','1','2') and row['retained'] in ('0','1'), 'bounded DATA guard reasons required')
    reasons = int(row['reasons'],16)
    passed = row['status'] == 'ok' and numbers['calls'] == 1 and 0 < numbers['payload'] == numbers['written'] <= 64*1024*1024 and \
        18 <= numbers['stream'] <= numbers['carrier']-128 and numbers['carrier'] <= 64*1024*1024 and numbers['consumed'] <= numbers['stream']
    return dict(passed=passed, boot_identity=m[1], status=row['status'], **numbers, digest=row['digest'],
                reasons=reasons, reason_labels=[label for bit,label in REASONS.items() if reasons&bit],
                parameters=int(row['params']), captures=int(row['captures']), retained=row['retained']=='1',
                owned_virtual_decode=passed, global_RAM_ownership=False, handoff_ready=False, xnu_executed=False)


def require_functional(result):
    require(result['passed'], 'DATA functional decode failed status='+result['status']+
        ' reasons=%08x' % result['reasons']+' labels='+','.join(result['reason_labels'])+
        ' params='+str(result['parameters'])+' captures='+str(result['captures'])+
        ' retained='+str(int(result['retained'])))


def decode_selected(data, banner, identity, cycle, *, expected=None):
    from builtin_init_profile import decode as baseline_decode
    def selected(text, rid):
        result = decode(text, rid, cycle)
        require_functional(result)
        return result
    clipped, observed = baseline_decode(data, banner, identity, cycle, digest_decoder=selected, digest_marker=b'N10DATA1')
    require(observed['kat']['boot_identity'] == observed['boot_identity'], 'DATA/recovery/PID1 boot differs')
    if expected is not None:
        row = observed['kat']
        require(row['digest'] == expected['data_payload_sha256'] and row['payload'] == row['written'] == expected['data_payload_bytes'] and
                row['carrier'] == expected['data_carrier_bytes'], 'DATA decoded package identity differs')
    return clipped, observed
