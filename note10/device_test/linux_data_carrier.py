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
MODE = 'image-slot-logical-v2'
COMPARE_SCHEMA_V1 = 'n10-data-compare-v1'
COMPARE_SCHEMA = 'n10-data-compare-v2'
RANGE_SCHEMA = 'n10-data-range-v1'
RANGE_SOURCES = ('linux_data_input_range.h',)
EARLY_SCHEMA = 'n10-data-early-prefix-v1'
EARLY_SOURCES = ('linux_data_early_prefix.h',)
GROWTH_SCHEMA='n10-data-growth-v1'
GROWTH_TARGET_SOURCE='e32ec501551b74b4cca5618ea25245f012656f29'
GROWTH_TARGET_BYTES=59523072
GROWTH_BUDGET_BYTES=59768832
GROWTH_FIELDS=('data_growth_schema','data_growth_target_source','data_growth_target_bytes','data_growth_budget_bytes')
GROWTH_BINDING=dict(zip(GROWTH_FIELDS,(GROWTH_SCHEMA,GROWTH_TARGET_SOURCE,GROWTH_TARGET_BYTES,GROWTH_BUDGET_BYTES)))
GROWTH_SOURCES=('linux_data_growth.h',)
COMPARE_SOURCES = ('linux_data_compare_evidence.h',)
BOOT_PAGE = 2048
SLOT_MAGIC = b'N10DATAEXPECTV2!'
SLOT_PREIMAGE = SLOT_MAGIC + bytes((2,0,0,0,64,0,0,0)) + bytes(40)
SLOT_SYMBOL = 'n10_image_expectation_slot'
SLOT_SECTION = '.rodata.n10_expectation'
LEGACY_FIELDS = ('data_carrier_stage', 'data_relative_placement_admitted', 'raw_input_binding')
FIELDS = (*LEGACY_FIELDS, 'data_expectation_mode', 'data_expectation_slot', 'image_expectation_patched')
CARRIER_FIELDS = ('data_manifest_sha256', 'data_carrier_sha256', 'data_carrier_bytes',
                  'data_payload_sha256', 'data_payload_bytes')
SOURCES = ('linux_data_carrier.py', 'linux_data_carrier.c', 'linux_data_carrier_composition.c',
           'build_linux_data_carrier.py', 'linux_data_carrier_fixture.c', 'test_linux_data_carrier.py',
           'carrier_lzma.c', 'carrier_lzma.h')
API_PINS = {'arch/arm64/kernel/setup.c': 'f80fd02832b12c48eba11b3e3148c59c6ad87d9ea2328c8c37492d107fd141d7'}
CASE_NAMES = ('test_trusted_logical_native_extent_and_authenticated_header_bounds',
              'test_v2_exact_private_patch_and_current_producer_binding',
              'test_preload_sha_length_reads_and_carrier_error_wire')
REASONS = {1:'parameter_missing',2:'parameter_invalid',4:'parameter_duplicate',
           8:'capture_missing',16:'capture_invalid',32:'capture_repeat',64:'input_missing',
           128:'global_mismatch',256:'emit_repeat',512:'sticky_invalid',1024:'image_unpatched',2048:'image_invalid',4096:'native_extent_invalid'}

TEST_SOURCES = (*SOURCES, 'sha256_kat_device_profile.py', 'builtin_init_profile.py',
                'prepare_linux_boot.py', 'build_boot_test_packages.py', 'materialize_auto_cycle.py')


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
        **{'drivers/misc/'+n: (HERE/n).read_bytes() for n in ('linux_data_carrier.c', 'carrier_lzma.c', 'carrier_lzma.h', *COMPARE_SOURCES, *RANGE_SOURCES, *EARLY_SOURCES, *GROWTH_SOURCES)}}
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


def slot_metadata(raw, system_map, object_symbols, object_sections):
    require(type(raw) is bytes and raw.count(SLOT_PREIMAGE) == 1, 'one exact generic slot required')
    names = {'_text','__start_rodata','__init_begin',SLOT_SYMBOL}
    values = {}
    for line in system_map.splitlines():
        p = line.split()
        if len(p) == 3 and p[2] in names:
            require(p[2] not in values, 'duplicate linked slot symbol')
            values[p[2]] = int(p[0],16)
    symbols = [p for line in object_symbols.splitlines() if len(p := line.split()) == 4 and p[3] == SLOT_SYMBOL]
    sections = re.findall(r'\[\s*\d+\]\s+\.rodata\.n10_expectation\s+PROGBITS\s+[0-9a-fA-F]+\s+[0-9a-fA-F]+\s+([0-9a-fA-F]+)\s+\S+\s+([A-Za-z]+)\s+\d+\s+\d+\s+\d+',object_sections)
    require(set(values) == names and len(symbols) == len(sections) == 1 and
            int(symbols[0][1],16) == 64 and symbols[0][2].lower() == 'r' and
            int(sections[0][0],16) == 64 and 'A' in sections[0][1] and not {'W','X'} & set(sections[0][1]),
            'actual readonly compiler slot provenance required')
    offset = raw.index(SLOT_PREIMAGE)
    require(values['__start_rodata'] <= values[SLOT_SYMBOL] and values[SLOT_SYMBOL]+64 <= values['__init_begin'] and
            offset == values[SLOT_SYMBOL]-values['_text'] and offset+64 <= len(raw), 'linked slot/file offset differs')
    return dict(kind=MODE,offset=offset,bytes=64,expectation_offset=offset+24,expectation_bytes=40,logical_offset=offset+56,logical_bytes=8,boot_page=BOOT_PAGE,
        preimage_sha256=sha(SLOT_PREIMAGE),symbol=SLOT_SYMBOL,symbol_bytes=64,section=SLOT_SECTION,
        readonly_flags=sections[0][1],generic=True)


def patch_image(raw, report, token, cycle_slot):
    require(report.get('data_expectation_mode') == MODE and report.get('image_expectation_patched') is False and
            report.get('image_sha256') == sha(raw), 'original generic CI Image binding required')
    slot = report['data_expectation_slot']
    keys = {'kind','offset','bytes','expectation_offset','expectation_bytes','preimage_sha256',
            'symbol','symbol_bytes','section','readonly_flags','generic','logical_offset','logical_bytes','boot_page'}
    require(type(slot) is dict and set(slot) == keys and slot['kind'] == MODE and slot['bytes'] == slot['symbol_bytes'] == 64 and
            slot['expectation_bytes'] == 40 and slot['logical_bytes'] == 8 and slot['boot_page'] == BOOT_PAGE and slot['preimage_sha256'] == sha(SLOT_PREIMAGE) and
            slot['symbol'] == SLOT_SYMBOL and slot['section'] == SLOT_SECTION and slot['generic'] is True and
            'A' in slot['readonly_flags'] and not {'W','X'} & set(slot['readonly_flags']), 'closed CI slot metadata required')
    require(type(slot['offset']) is int and 0 <= slot['offset'] <= len(raw)-64 and
            type(slot['expectation_offset']) is int and slot['expectation_offset'] == slot['offset']+24 and
            type(slot['logical_offset']) is int and slot['logical_offset'] == slot['offset']+56 and
            raw.count(SLOT_PREIMAGE) == 1 and raw[slot['offset']:slot['offset']+64] == SLOT_PREIMAGE,
            'exact generic slot preimage/span required')
    require(type(cycle_slot) is bytes and len(cycle_slot) == 32 and raw.count(cycle_slot+b'\0') == 1 and
            re.fullmatch('[0-9a-f]{32}',token or ''), 'one generic cycle slot required')
    cycle = raw.index(cycle_slot+b'\0')
    require(cycle+32 <= slot['offset'] or slot['offset']+64 <= cycle, 'disjoint data slots required')
    digest = report.get('data_carrier_sha256')
    require(type(digest) is str and re.fullmatch('[0-9a-f]{64}',digest) and digest != '0'*64, 'accepted nonplaceholder carrier identity required')
    length = report.get('data_carrier_bytes')
    require(type(length) is int and 128 <= length <= 64*1024*1024, 'accepted trusted logical length required')
    expected = bytes.fromhex(digest)+length.to_bytes(8,'little')
    result = bytearray(raw)
    result[cycle:cycle+32] = token.encode('ascii')
    start = slot['expectation_offset']
    result[start:start+40] = expected
    patched_slot = SLOT_PREIMAGE[:24]+expected
    require(result.count(patched_slot) == 1 and result[slot['offset']:slot['offset']+64] == patched_slot,
            'unique patched slot required')
    return bytes(result)


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
    checks = dict(data_scope=result.get('data_carrier_stage') == STAGE and result.get('data_expectation_mode') == MODE and
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


def input_binding(result, lines, *, elf, archive, raw_inputs, producing_sources=None):
    require(result.get('version') == 'v91' and result.get('diagnostic_kind') == KIND and
            result.get('data_carrier_stage') == STAGE and result.get('raw_input_binding') is False and
            result.get('data_expectation_mode') == MODE and type(result.get('data_expectation_slot')) is dict,
            'closed new DATA Image required')
    if producing_sources is None:
        require(result.get('data_compare_schema') == COMPARE_SCHEMA, 'new DATA comparison feature declaration required')
        require(result.get('data_early_prefix_schema') == EARLY_SCHEMA, 'new DATA early prefix declaration required')
        growth_declaration(result)
        require(result.get('readonly_PC_disabled') is True and result.get('readonly_input_slot_absent') is True,
                'normal small DATA must exclude readonly PC slot')
        require(result.get('data_input_range_schema') == RANGE_SCHEMA and
                type(result.get('data_linked_kernel_bytes')) is int and result['data_linked_kernel_bytes']>0 and
                result['data_linked_kernel_bytes'] == result.get('data_footprint',{}).get('linked_kernel_bytes'),
                'new DATA live range/accepted linked span declaration required')
        require(not {'CONFIG_NOTE10_OWNED_CONTIGUOUS_STAGING=y', 'CONFIG_NOTE10_CURRENT_OWNED_STAGING=y'} & set(lines),
                'comparison DATA forbids early owned reservation')
        for name in (*SOURCES, *COMPARE_SOURCES, *RANGE_SOURCES, *EARLY_SOURCES, *GROWTH_SOURCES):
            require(result.get('source_sha256', {}).get('note10/device_test/'+name) == sha((HERE/name).read_bytes()),
                    'DATA Image source differs: '+name)
    else:
        from current_data_reuse import require_context
        require('data_compare_schema' not in result, 'historical reuse cannot declare new comparison feature')
        require('data_early_prefix_schema' not in result, 'historical reuse cannot declare early prefix feature')
        require(not any(key in result for key in GROWTH_FIELDS),'historical reuse cannot declare growth feature')
        require(not any(key in result for key in ('data_input_range_schema','data_linked_kernel_bytes')),
                'historical reuse cannot declare live range feature')
        require_context(producing_sources).verify_sources(result,SOURCES)
    admission = relative_admission(result, lines, result['data_footprint'], elf=elf, archive=archive, raw_inputs=raw_inputs)
    require(result.get('data_relative_placement') == admission and admission['eligible'], 'DATA relative placement unresolved')
    bound = dict(data_carrier_stage=STAGE, data_relative_placement_admitted=True, raw_input_binding=False,
                data_expectation_mode=MODE,data_expectation_slot=result['data_expectation_slot'],image_expectation_patched=False)
    if producing_sources is None:
        bound['data_compare_schema'] = COMPARE_SCHEMA
        bound.update(data_input_range_schema=RANGE_SCHEMA,data_linked_kernel_bytes=result['data_linked_kernel_bytes'])
        bound['data_early_prefix_schema']=EARLY_SCHEMA
        bound.update(GROWTH_BINDING)
    return bound


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
    if build.get('data_expectation_mode') in (MODE,'image-slot-v1'):
        if build['data_expectation_mode'] != MODE:
            from sha256_kat_device_profile import V90_IMAGE_HEAD
            require(build.get('source_head') == V90_IMAGE_HEAD, 'historical Image expectation source differs')
        require(build.get('image_expectation_patched') is True, 'new expectation must be bound in private Image variant')
        return cmdline
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
    m = re.search(r'N10BOOTLINK2 boot=([0-9a-f]{32}) N10DATA1 ([^\r\n\x00]{1,447}) checksum=([0-9a-f]{8})$', lines[0])
    require(m is not None and m[1] != '0'*32 and checksum(m[2].encode('ascii')) == int(m[3],16), 'DATA boot/checksum differs')
    pairs = [part.split('=') for part in m[2].split(' ')]
    keys = ('id','cycle','kind','source','status','carrier','logical','carrier_rc','stream','payload','consumed','written','calls','digest','reasons','expectations','captures','retained','ownership','executed')
    require(all(len(p) == 2 for p in pairs) and tuple(p[0] for p in pairs) == keys, 'DATA closed schema required')
    row = dict(pairs)
    require(row['id'] == identity and row['cycle'] == cycle and row['kind'] == 'result' and row['source'] == MODE and
            row['ownership'] == row['executed'] == '0' and re.fullmatch('[0-9a-f]{64}', row['digest']), 'DATA identity/nonclaim differs')
    numbers = {}
    for key in ('carrier','logical','stream','payload','consumed','written','calls'):
        require(re.fullmatch('0|[1-9][0-9]{0,8}', row[key]), 'bounded DATA count required')
        numbers[key] = int(row[key])
    require(re.fullmatch('0|-?[1-9][0-9]{0,9}',row['carrier_rc']) and -(1<<31) <= int(row['carrier_rc']) < (1<<31), 'signed carrier crypto result required')
    numbers['carrier_rc'] = int(row['carrier_rc'])
    require(re.fullmatch('[0-9a-f]{8}',row['reasons']) and int(row['reasons'],16) <= 0x1fff and
            row['expectations'] in ('0','1') and row['captures'] in ('0','1','2') and row['retained'] in ('0','1'), 'bounded DATA guard reasons required')
    reasons = int(row['reasons'],16)
    passed = row['status'] == 'ok' and reasons == 0 and row['expectations'] == row['captures'] == row['retained'] == '1' and \
        numbers['calls'] == 1 and 0 < numbers['payload'] == numbers['written'] <= 64*1024*1024 and \
        18 <= numbers['stream'] <= numbers['logical']-128 and 128 <= numbers['logical'] <= numbers['carrier'] <= 64*1024*1024 and \
        numbers['carrier'] in (numbers['logical'],(numbers['logical']+BOOT_PAGE-1)//BOOT_PAGE*BOOT_PAGE) and numbers['carrier_rc'] == 0 and numbers['consumed'] <= numbers['stream']
    return dict(passed=passed, boot_identity=m[1], status=row['status'], **numbers, digest=row['digest'],
                reasons=reasons, reason_labels=[label for bit,label in REASONS.items() if reasons&bit],
                expectations=int(row['expectations']), expectation_source=row['source'], captures=int(row['captures']), retained=row['retained']=='1',
                owned_virtual_decode=passed, global_RAM_ownership=False, handoff_ready=False, xnu_executed=False)


def functional_phase(status):
    return {'unavailable': 'input_guards', 'carrier_crypto': 'carrier_hash',
            'carrier_mismatch': 'carrier_integrity', 'header': 'carrier_header',
            'stream_hash': 'stream_integrity', 'owned_output': 'allocation',
            'allocation': 'allocation', 'decode': 'lzma_decode',
            'payload_hash': 'payload_integrity', 'ok': 'complete'}.get(status, 'unknown')


def expected_compare_schema(expected):
    schema = None if expected is None else expected.get('data_compare_schema')
    require(schema in (None, COMPARE_SCHEMA_V1, COMPARE_SCHEMA), 'unsupported DATA comparison feature')
    if schema == COMPARE_SCHEMA_V1:
        from sha256_kat_device_profile import host_profile_origin, V99_PROFILE_ORIGIN_HEAD
        require(expected.get('source_head') == expected.get('host_profile_source_head') == V99_PROFILE_ORIGIN_HEAD,
                'v1 comparison requires exact retained v99 origin')
        host_profile_origin(expected)
    return schema


def decode_compare(text, identity, cycle, result, *, required=False, expected=None):
    from decode_reservation import checksum
    schema = expected_compare_schema(expected)
    required = required or schema is not None
    all_lines = text.splitlines()
    lines = [line for line in all_lines if 'N10DATACMP' in line]
    if not lines:
        require(not required, 'declared DATA comparison frame missing')
        return dict(schema=None, state='unsupported', comparison_observed=False)
    require(len(lines) == 1, 'one DATA comparison frame required')
    match = re.search(r'N10BOOTLINK2 boot=([0-9a-f]{32}) N10DATACMP([12]) ([^\r\n\x00]{1,415}) checksum=([0-9a-f]{8})$', lines[0])
    require(match is not None and match[1] == result['boot_identity'] and match[1] != '0'*32 and
            checksum(match[3].encode('ascii')) == int(match[4], 16), 'DATA comparison boot/checksum differs')
    version = match[2]
    require((version == '1' and schema == COMPARE_SCHEMA_V1 and len(match[3]) <= 383) or
            (version == '2' and schema in (None, COMPARE_SCHEMA) and (expected is None or schema == COMPARE_SCHEMA)),
            'DATA comparison declared version differs')
    pairs = [part.split('=') for part in match[3].split(' ')]
    keys = ('id', 'cycle', 'kind', 'source', 'phase', 'state', 'logical', 'actual', 'expected', 'equal')
    if version == '2':
        keys = (*keys, 'sampled', 'magic_match', 'prefix_zero')
    keys = (*keys, 'ownership', 'executed')
    require(all(len(part) == 2 for part in pairs) and tuple(part[0] for part in pairs) == keys,
            'DATA comparison closed schema required')
    row = dict(pairs)
    require(row['id'] == identity and row['cycle'] == cycle and row['kind'] == 'compare' and row['source'] == MODE and
            row['phase'] == 'carrier_integrity' and row['ownership'] == row['executed'] == '0',
            'DATA comparison identity/nonclaim differs')
    require(re.fullmatch('0|[1-9][0-9]{0,8}', row['logical']) and
            int(row['logical']) == result['logical'] <= 64*1024*1024 and
            all(re.fullmatch('[0-9a-f]{64}', row[key]) for key in ('actual', 'expected')),
            'DATA comparison count/digest differs')
    data_lines = [line for line in all_lines if 'N10DATA1 ' in line]
    require(len(data_lines) == 1 and text.find(lines[0]) > text.find(data_lines[0]),
            'DATA comparison result order differs')
    if row['state'] == 'compared':
        require(row['equal'] in ('0', '1') and (row['actual'] == row['expected']) == (row['equal'] == '1') and
                result['carrier_rc'] == result['reasons'] == 0 and result['expectations'] == result['captures'] == 1 and
                result['retained'] is True and 128 <= result['logical'] <= result['carrier'] <= 64*1024*1024 and
                result['carrier'] in (result['logical'], (result['logical']+BOOT_PAGE-1)//BOOT_PAGE*BOOT_PAGE),
                'DATA compared evidence inconsistent')
        statuses = ('carrier_mismatch',) if row['equal'] == '0' else (
            'header', 'stream_hash', 'allocation', 'decode', 'payload_hash', 'ok')
        require(result['status'] in statuses, 'DATA comparison phase/status differs')
    else:
        require(row['state'] == 'unavailable' and row['equal'] == 'na' and
                row['actual'] == row['expected'] == '0'*64 and result['status'] in ('unavailable', 'carrier_crypto'),
                'DATA unavailable comparison inconsistent')
        require((result['status'] == 'carrier_crypto') == (result['carrier_rc'] != 0),
                'DATA unavailable comparison crypto status differs')
    probe = dict(state='unsupported', sampled=False, bytes=0, magic_match=None, prefix_zero=None)
    if version == '2':
        require(all(row[key] in ('0', '1') for key in ('sampled', 'magic_match', 'prefix_zero')) and
                (row['sampled'] == '1') == (row['state'] == 'compared') and
                not (row['magic_match'] == row['prefix_zero'] == '1') and
                (row['sampled'] == '1' or row['magic_match'] == row['prefix_zero'] == '0'),
                'DATA prefix sample inconsistent')
        sampled = row['sampled'] == '1'
        probe = dict(state='sampled' if sampled else 'unavailable', sampled=sampled, bytes=8 if sampled else 0,
                     phase='post_carrier_hash_compare', magic_match=row['magic_match'] == '1' if sampled else None,
                     prefix_zero=row['prefix_zero'] == '1' if sampled else None)
    return dict(schema=COMPARE_SCHEMA_V1 if version == '1' else COMPARE_SCHEMA,
                state=row['state'], comparison_observed=row['state'] == 'compared', input_probe=probe,
                boot_identity=match[1], phase=row['phase'], logical=int(row['logical']),
                actual_sha256=row['actual'], expected_sha256=row['expected'],
                equal=None if row['equal'] == 'na' else row['equal'] == '1',
                global_RAM_ownership=False, xnu_executed=False)


def expected_range_schema(expected):
    if expected is None:
        return RANGE_SCHEMA, None
    schema = expected.get('data_input_range_schema')
    if 'data_input_range_schema' in expected or 'data_linked_kernel_bytes' in expected:
        from sha256_kat_device_profile import V97_PROFILE_ORIGIN_HEAD, V99_PROFILE_ORIGIN_HEAD, V100_PROFILE_ORIGIN_HEAD
        retired = (V97_PROFILE_ORIGIN_HEAD,V99_PROFILE_ORIGIN_HEAD,V100_PROFILE_ORIGIN_HEAD)
        span = expected.get('data_linked_kernel_bytes')
        require(schema == RANGE_SCHEMA and expected.get('data_compare_schema') == COMPARE_SCHEMA and
                type(span) is int and 0 < span < (1<<64) and
                expected.get('source_head') not in retired and expected.get('host_profile_source_head') not in retired,
                'live RANGE declaration/accepted span differs')
        return schema, span
    from sha256_kat_device_profile import host_profile_origin, V97_PROFILE_ORIGIN_HEAD, V99_PROFILE_ORIGIN_HEAD, V100_PROFILE_ORIGIN_HEAD
    host_profile_origin(expected)
    head = expected.get('host_profile_source_head')
    compare = expected.get('data_compare_schema')
    require((head == V100_PROFILE_ORIGIN_HEAD and compare == COMPARE_SCHEMA) or
            (head == V99_PROFILE_ORIGIN_HEAD and compare == COMPARE_SCHEMA_V1) or
            (head == V97_PROFILE_ORIGIN_HEAD and compare is None), 'new DATA live RANGE declaration missing')
    return None, None


def decode_range(text, identity, cycle, result, *, expected=None):
    from decode_reservation import checksum
    schema, accepted_span = expected_range_schema(expected)
    all_lines = text.splitlines()
    lines = [line for line in all_lines if 'N10DATARANGE' in line]
    if schema is None:
        require(not lines, 'retained producer cannot claim live RANGE evidence')
        return dict(schema=None,state='unsupported',checked=False)
    require(len(lines) == 1, 'one declared live RANGE companion required')
    match = re.search(r'N10BOOTLINK2 boot=([0-9a-f]{32}) N10DATARANGE1 ([^\r\n\x00]{1,383}) checksum=([0-9a-f]{8})$',lines[0])
    require(match is not None and match[1] == result['boot_identity'] and match[1] != '0'*32 and
            checksum(match[2].encode('ascii')) == int(match[3],16), 'live RANGE boot/checksum differs')
    pairs = [part.split('=') for part in match[2].split(' ')]
    keys = ('id','cycle','kind','source','extent','state','domain','logical','input_start','input_end',
            'kernel_start','kernel_end','logical_overlap','native_overlap','reasons','ownership','executed')
    require(all(len(part)==2 for part in pairs) and tuple(part[0] for part in pairs)==keys,
            'live RANGE closed schema required')
    row = dict(pairs)
    require(row['id']==identity and row['cycle']==cycle and row['kind']=='range' and row['source']=='live-arm64' and
            row['extent']=='native' and row['ownership']==row['executed']=='0', 'live RANGE identity/nonclaim differs')
    require(re.fullmatch('0|[1-9][0-9]{0,8}',row['logical']) and
            int(row['logical'])==result['logical']<=64*1024*1024 and re.fullmatch('[0-9a-f]{8}',row['reasons']) and
            int(row['reasons'],16)<=127, 'live RANGE count/reasons differ')
    comparison_lines = [line for line in all_lines if 'N10DATACMP' in line]
    require(len(comparison_lines)==1 and text.find(lines[0])>text.find(comparison_lines[0]), 'live RANGE order differs')
    bounds = None
    logical_overlap = native_overlap = tail_only = None
    checked = row['state']=='checked'
    endpoint_keys = ('input_start','input_end','kernel_start','kernel_end')
    if checked:
        require(row['domain']=='physical' and row['reasons']=='00000000' and
                all(re.fullmatch('[0-9a-f]{16}',row[key]) for key in endpoint_keys) and
                row['logical_overlap'] in ('0','1') and row['native_overlap'] in ('0','1'), 'live RANGE checked fields differ')
        start,end,kstart,kend = (int(row[key],16) for key in endpoint_keys)
        logical = int(row['logical'])
        require(type(accepted_span) is int and 0 < logical <= result['carrier'] <= 64*1024*1024 and
                start<end and kstart<kend and end-start==result['carrier'] and kend-kstart==accepted_span and
                start <= (1<<64)-1-logical, 'live RANGE bounds/accepted span differ')
        logical_end = start+logical
        logical_overlap = start<kend and kstart<logical_end
        native_overlap = start<kend and kstart<end
        require((row['logical_overlap']=='1')==logical_overlap and (row['native_overlap']=='1')==native_overlap and
                (not logical_overlap or native_overlap), 'live RANGE overlap flags differ')
        tail_only = native_overlap and not logical_overlap
        bounds = {key:row[key] for key in endpoint_keys}
    else:
        require(row['state']=='unavailable' and row['domain']=='none' and int(row['reasons'],16)>0 and
                all(row[key]=='na' for key in (*endpoint_keys,'logical_overlap','native_overlap')),
                'live RANGE unavailable fields differ')
    return dict(schema=RANGE_SCHEMA,state=row['state'],checked=checked,domain=row['domain'],
                logical_overlap=logical_overlap,native_overlap=native_overlap,tail_only=tail_only,
                reasons=int(row['reasons'],16),private_physical_bounds=bounds,
                global_RAM_ownership=False,hardware_translation_attested=False,xnu_executed=False)


def expected_early_schema(expected):
    if expected is None:
        return EARLY_SCHEMA
    if 'data_early_prefix_schema' in expected:
        from sha256_kat_device_profile import V97_PROFILE_ORIGIN_HEAD, V99_PROFILE_ORIGIN_HEAD, V100_PROFILE_ORIGIN_HEAD, V101_PROFILE_ORIGIN_HEAD
        retired=(V97_PROFILE_ORIGIN_HEAD,V99_PROFILE_ORIGIN_HEAD,V100_PROFILE_ORIGIN_HEAD,V101_PROFILE_ORIGIN_HEAD)
        require(expected['data_early_prefix_schema']==EARLY_SCHEMA and
                expected.get('data_compare_schema')==COMPARE_SCHEMA and expected.get('data_input_range_schema')==RANGE_SCHEMA and
                expected.get('source_head') not in retired and expected.get('host_profile_source_head') not in retired,
                'early prefix producer declaration differs')
        return EARLY_SCHEMA
    from sha256_kat_device_profile import host_profile_origin, V97_PROFILE_ORIGIN_HEAD, V99_PROFILE_ORIGIN_HEAD, V100_PROFILE_ORIGIN_HEAD, V101_PROFILE_ORIGIN_HEAD
    host_profile_origin(expected)
    require(expected.get('host_profile_source_head') in
            (V97_PROFILE_ORIGIN_HEAD,V99_PROFILE_ORIGIN_HEAD,V100_PROFILE_ORIGIN_HEAD,V101_PROFILE_ORIGIN_HEAD),
            'new DATA early prefix declaration missing')
    return None


def decode_early(text,identity,cycle,result,*,expected=None):
    from decode_reservation import checksum
    schema=expected_early_schema(expected)
    all_lines=text.splitlines()
    lines=[line for line in all_lines if 'N10DATAEARLY' in line]
    if schema is None:
        require(not lines,'retained producer cannot claim early prefix evidence')
        return dict(schema=None,state='unsupported',sampled=False)
    require(len(lines)==1,'one declared early prefix companion required')
    match=re.search(r'N10BOOTLINK2 boot=([0-9a-f]{32}) N10DATAEARLY1 ([^\r\n\x00]{1,255}) checksum=([0-9a-f]{8})$',lines[0])
    require(match is not None and match[1]==result['boot_identity'] and match[1]!='0'*32 and
            checksum(match[2].encode('ascii'))==int(match[3],16),'early prefix boot/checksum differs')
    pairs=[part.split('=') for part in match[2].split(' ')]
    keys=('id','cycle','kind','source','phase','state','captures','sampled','magic_match','prefix_zero','reasons','ownership','executed')
    require(all(len(part)==2 for part in pairs) and tuple(part[0] for part in pairs)==keys,'early prefix closed schema required')
    row=dict(pairs)
    require(row['id']==identity and row['cycle']==cycle and row['kind']=='early' and row['source']=='memblock-ram-map' and
            row['phase']=='post_paging' and row['ownership']==row['executed']=='0','early prefix identity/nonclaim differs')
    require(row['captures'] in ('0','1','2') and int(row['captures'])==result['captures'] and
            re.fullmatch('[0-9a-f]{8}',row['reasons']) and int(row['reasons'],16)<=31,'early prefix captures/reasons differ')
    prior=[line for line in all_lines if 'N10DATARANGE' in line]
    require(len(prior)==1 and text.find(lines[0])>text.find(prior[0]),'early prefix order differs')
    sampled=row['state']=='sampled'
    if sampled:
        require(row['sampled']=='1' and row['captures']=='1' and row['reasons']=='00000000' and
                row['magic_match'] in ('0','1') and row['prefix_zero'] in ('0','1') and
                not (row['magic_match']==row['prefix_zero']=='1'),'early prefix sampled fields differ')
    else:
        require(row['state']=='unavailable' and row['sampled']=='0' and row['magic_match']==row['prefix_zero']=='na' and
                int(row['reasons'],16)>0,'early prefix unavailable fields differ')
    return dict(schema=EARLY_SCHEMA,state=row['state'],phase='post_paging',sampled=sampled,
                magic_match=row['magic_match']=='1' if sampled else None,
                prefix_zero=row['prefix_zero']=='1' if sampled else None,reasons=int(row['reasons'],16),
                captures=int(row['captures']),global_RAM_ownership=False,hardware_mapping_attested=False)


def growth_declaration(row):
    require(all(row.get(key)==value and type(row.get(key)) is type(value) for key,value in GROWTH_BINDING.items()) and
            type(row.get('data_linked_kernel_bytes')) is int and
            0<row['data_linked_kernel_bytes']<GROWTH_TARGET_BYTES<=GROWTH_BUDGET_BYTES<=67108864,
            'exact growth target/budget/current linked span required')
    return dict(GROWTH_BINDING)


def growth_retained_heads():
    from sha256_kat_device_profile import (V97_PROFILE_ORIGIN_HEAD,V99_PROFILE_ORIGIN_HEAD,V100_PROFILE_ORIGIN_HEAD,
        V101_PROFILE_ORIGIN_HEAD,V102_PROFILE_ORIGIN_HEAD,V88_HOST_HEAD,V89_IMAGE_HEAD,V89_HOST_HEAD,
        V90_IMAGE_HEAD,V90_HOST_HEAD,V91_IMAGE_HEAD)
    return (V97_PROFILE_ORIGIN_HEAD,V99_PROFILE_ORIGIN_HEAD,V100_PROFILE_ORIGIN_HEAD,V101_PROFILE_ORIGIN_HEAD,
            V102_PROFILE_ORIGIN_HEAD,V88_HOST_HEAD,V89_IMAGE_HEAD,V89_HOST_HEAD,V90_IMAGE_HEAD,V90_HOST_HEAD,V91_IMAGE_HEAD)


def expected_growth_schema(expected):
    if expected is None: return GROWTH_SCHEMA
    retired=growth_retained_heads()
    if any(key in expected for key in GROWTH_FIELDS):
        growth_declaration(expected)
        require(expected.get('source_head') not in retired and expected.get('host_profile_source_head') not in retired,
                'retained source cannot declare growth evidence')
        return GROWTH_SCHEMA
    from sha256_kat_device_profile import host_profile_origin
    host_profile_origin(expected)
    require(expected.get('host_profile_source_head') in retired,'new DATA growth declaration missing')
    return None


def decode_growth(text,identity,cycle,result,*,expected=None):
    from decode_reservation import checksum
    schema=expected_growth_schema(expected)
    lines=[line for line in text.splitlines() if 'N10DATAGROWTH' in line]
    if schema is None:
        require(not lines,'retained producer cannot claim growth evidence')
        return dict(schema=None,state='unsupported',hardware_mapping_attested=False,global_RAM_ownership=False)
    require(type(expected) is dict,'growth evidence requires accepted producer linked span context')
    growth_declaration(expected)
    require(len(lines)==1,'one declared growth companion required')
    match=re.search(r'N10BOOTLINK2 boot=([0-9a-f]{32}) N10DATAGROWTH1 ([^\r\n\x00]{1,415}) checksum=([0-9a-f]{8})$',lines[0])
    require(match is not None and match[1]==result['boot_identity'] and match[1]!='0'*32 and
            checksum(match[2].encode('ascii'))==int(match[3],16),'growth boot/checksum differs')
    pairs=[part.split('=') for part in match[2].split(' ')]
    keys=('id','cycle','kind','source','stage','captures','state','current','target','budget','proposal','queries',
          'memory','map_start','reserved','initrd_overlap','reasons','ownership','executed')
    require(all(len(pair)==2 for pair in pairs) and tuple(pair[0] for pair in pairs)==keys,'growth closed schema required')
    row=dict(pairs)
    require(row['id']==identity and row['cycle']==cycle and row['kind']=='growth' and
            row['source']=='memblock-bookkeeping' and row['stage']=='post_paging' and row['ownership']==row['executed']=='0' and
            row['target']==str(GROWTH_TARGET_BYTES) and row['budget']==str(GROWTH_BUDGET_BYTES) and row['proposal']==GROWTH_TARGET_SOURCE,
            'growth identity/target/nonclaim differs')
    require(row['captures'] in ('0','1','2') and int(row['captures'])==result['captures'] and row['queries'] in ('0','3') and
            re.fullmatch('[0-9a-f]{8}',row['reasons']),'growth captures/queries/reasons differ')
    prior=[line for line in text.splitlines() if 'N10DATAEARLY' in line]
    require(len(prior)==1 and text.find(lines[0])>text.find(prior[0]),'growth companion order differs')
    flags=('memory','map_start','reserved','initrd_overlap')
    checked=row['state']=='checked';reason=int(row['reasons'],16)
    if checked:
        require(row['captures']=='1' and row['queries']=='3' and reason==0 and
                row['current']==str(expected['data_linked_kernel_bytes']) and all(row[key] in ('0','1') for key in flags),
                'growth checked source span/flags differ')
    else:
        require(row['state']=='unavailable' and row['current']=='na' and all(row[key]=='na' for key in flags) and
                ((row['captures']=='0' and reason==1 and row['queries']=='0') or
                 (row['captures']=='2' and reason==64 and row['queries']=='0') or
                 (row['captures']=='1' and ((row['queries']=='0' and reason in (2,4,8,16)) or
                                          (row['queries']=='3' and reason in (8,32))))),
                'growth unavailable states must be explicit NA')
    return dict(schema=GROWTH_SCHEMA,state=row['state'],stage='post_paging',captures=int(row['captures']),queries=int(row['queries']),
        current_linked_span=int(row['current']) if checked else None,target_linked_span=GROWTH_TARGET_BYTES,
        tested_budget=GROWTH_BUDGET_BYTES,proposal_source=GROWTH_TARGET_SOURCE,reasons=reason,
        **{key:row[key]=='1' if checked else None for key in flags},
        hardware_mapping_attested=False,global_RAM_ownership=False,future_placement_attested=False,
        larger_footprint_physically_admitted=False)


def require_functional(result, *, report_phase=False):
    prefix = ('DATA functional acceptance failed phase='+functional_phase(result['status'])+' status='
              if report_phase else 'DATA functional decode failed status=')
    require(result['passed'], prefix+result['status']+
        ' reasons=%08x' % result['reasons']+' labels='+','.join(result['reason_labels'])+
        ' carrier_rc='+str(result['carrier_rc'])+' native='+str(result['carrier'])+' logical='+str(result['logical'])+
        ' expectations='+str(result['expectations'])+' captures='+str(result['captures'])+
        ' retained='+str(int(result['retained'])))


class ComponentObservationError(ValueError):
    """Rejected observation with private component evidence; never a PASS."""
    def __init__(self, error, components):
        super().__init__(str(error))
        self.component_evidence = components


def structural_presence(text, identity, cycle, boot):
    # Exact marker presence only. This does not run or replace PID1 acceptance.
    result = {'validation': 'presence_only'}
    for name, marker, tail in (
            ('route', 'N10ROUTE2', 'route=builtin exec_attempt=1'),
            ('pid1', 'N10INIT2', 'route=builtin started=1')):
        tokens = re.findall(r'\b'+marker+r' id='+re.escape(identity)+
                            r' boot=([0-9a-f]{32}) cycle='+re.escape(cycle)+
                            ' '+tail+r'(?=\r?\n|$)', text)
        result[name+'_same_boot_markers'] = tokens.count(boot)
        result[name+'_other_boot_markers'] = len(tokens)-tokens.count(boot)
    return result


def decode_selected(data, banner, identity, cycle, *, expected=None):
    from builtin_init_profile import decode as baseline_decode
    components = dict(pid1_validation='not_checked', return_validation='not_checked',
                      return_boot_association='not_checked',
                      functional_acceptance=False, hardware_return_proven_by_frames=False)
    def selected(text, rid):
        result = decode(text, rid, cycle)
        components['data'] = result
        components['data_phase'] = functional_phase(result['status'])
        components['structural_presence'] = structural_presence(text, rid, cycle, result['boot_identity'])
        comparison = decode_compare(text, rid, cycle, result, expected=expected, required=expected is None)
        components['carrier_comparison'] = comparison
        if comparison['schema'] is not None:
            result['carrier_comparison'] = comparison
        # Preserve valid DATA/comparison/prefix components before the new gate.
        relation = decode_range(text, rid, cycle, result, expected=expected)
        components['live_input_range'] = relation
        if relation['schema'] is not None:
            result['live_input_range'] = relation
        early=decode_early(text,rid,cycle,result,expected=expected)
        components['early_input_prefix']=early
        if early['schema'] is not None:
            result['early_input_prefix']=early
        growth=decode_growth(text,rid,cycle,result,expected=expected)
        components['growth_region']=growth
        if growth['schema'] is not None:
            result['growth_region']=growth
        require_functional(result, report_phase=True)
        return result
    try:
        clipped, observed = baseline_decode(data, banner, identity, cycle, digest_decoder=selected,
                                           digest_marker=b'N10DATA1', component_evidence=components)
        require(observed['kat']['boot_identity'] == observed['boot_identity'], 'DATA/recovery/PID1 boot differs')
        if expected is not None:
            row = observed['kat']
            require(row['digest'] == expected['data_payload_sha256'] and row['payload'] == row['written'] == expected['data_payload_bytes'] and
                    row['logical'] == expected['data_carrier_bytes'], 'DATA decoded package identity differs')
    except ValueError as error:
        raise ComponentObservationError(error, components) from error
    return clipped, observed
