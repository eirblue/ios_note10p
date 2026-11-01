"""v81 memblock-owned post-paging FDT snapshot evidence; no pristine-input claim."""
import hashlib
from pathlib import Path
import re

HERE = Path(__file__).resolve().parent
KIND = 'early-fdt-binding'
PROFILE = KIND+'-v1'
BOUNDARY = 'post_paging_reservations'
REVISION = 1
ALLOCATION = 'memblock-owned'
CAPACITY = 524288
FIELDS = ('fdt_capture_boundary', 'fdt_snapshot_capacity_bytes', 'raw_input_binding',
          'fdt_capture_revision', 'fdt_allocation_form', 'fdt_relative_placement_admitted',
          'fdt_effective_host_admission')
SOURCES = ('early_fdt_binding.py', 'early_fdt_binding.c', 'early_fdt_composition.c',
           'build_early_fdt_binding.py', 'test_early_fdt_binding.py', 'early_fdt_fixture.c')
API_PINS = {
    'arch/arm64/kernel/setup.c': 'f80fd02832b12c48eba11b3e3148c59c6ad87d9ea2328c8c37492d107fd141d7',
    'mm/memblock.c': '4f0bf30f9b0f81ff7e13446454d8a8f35e25129012b4fa63725c0f8b6f5c2c2f',
    'include/linux/bootmem.h': '1aa11b110d8e4ae3e6363a44dd2ca08b696ed013fe88d970c29076a1de440513',

    'drivers/of/fdt.c': 'e655d0f3902e4559932a8c262177a74623468caeda04b338c2de81d992593b34',
    'arch/arm64/mm/mmu.c': '18bb3b58865215b834e86aa8e44bf8f3c7f40c53428183351120958e25c43541',
    'arch/arm64/kernel/kaslr.c': '92cc0ecb325d69d5d617d7379e661a0e6975c886e6b9f70a543c4fbfc408015f',
    'crypto/sha256_generic.c': 'c85f77c45bc469f402311c9bf2a0ea4c456c64675ecf60fafa0421db25cad96f',
}


# Exact a77 Image source closure, independent from newly published host code.
IMAGE_SOURCE_HEAD = 'a77f1eca32d1888f3266f49412dda9f0129f8719'
IMAGE_SHA256 = '845b98c9ce2ad9d2aa9866e8f858a11e85337f2a48581d6f57ab481f8141f9e4'
IMAGE_SOURCE_PINS = {'note10/device_test/early_fdt_binding.py': '51a3dce472787ffe739c2458ad0505bad0eb43964ef031e3ff78a0a70beec5f9', 'note10/device_test/early_fdt_binding.c': 'dbf817822ef3f08b1c82eef95b6ff7f34f4b202f132b0163886df6eaf2ce269d', 'note10/device_test/early_fdt_composition.c': 'a8641ee893b9a93acbc68343b3b3edb55787562f7d186d323d54214e7bcd712e', 'note10/device_test/build_early_fdt_binding.py': '7a3c6182ff7d452c419fdea833a0b51f94ed726b7d06d1db1bd12c11bc3cd058', 'note10/device_test/test_early_fdt_binding.py': '2444d3d20b7cc42e705cb89c1d04de72599f7da2a5d1b9282636f3b9990ce1fa', 'note10/device_test/early_fdt_fixture.c': 'b58eb61da8570d60c8f8836447097fcdeb5ab8d295d3e740e50c3360f30a40f4'}
ELF_BYTES = 1216
CPIO_BYTES = 2048
TEMP_NAME_OFFSET = 785
TEMP_NAME_BYTES = 10
INIT_PAYLOAD_OFFSET = 476
ELF_CANONICAL_SHA256 = 'bb3f12a24c65d8c8787244404fea2e1a37ecb2e600ea47214ebd810f8a5d42be'
CPIO_CANONICAL_SHA256 = '1bb2f915f08a17eec5116626acecb2dfc4e4956ed40bf626b6586a271c4ca98c'

def require(value, message):
    if not value:
        raise ValueError(message)


def overlay_setup(raw):
    """One guarded post-paging hook; original verifier/CRC are untouched."""
    require(hashlib.sha256(raw).hexdigest() == API_PINS['arch/arm64/kernel/setup.c'], 'pinned setup source differs')
    old = b'void __init setup_arch(char **cmdline_p)\n'
    declaration = (b'#ifdef CONFIG_NOTE10_EARLY_FDT_BINDING\n'
        b'extern void __init n10_post_paging_fdt_capture(const void *params, unsigned int length);\n'
        b'#endif\n\n')
    anchor = b'\tpaging_init();\n'
    require(raw.count(old) == raw.count(anchor) == 1, 'unique setup hook anchors required')
    call = (b'#ifdef CONFIG_NOTE10_EARLY_FDT_BINDING\n'
            b'\tn10_post_paging_fdt_capture(initial_boot_params,\n'
            b'\t\tinitial_boot_params ? of_get_flat_dt_size() : 0);\n'
            b'#endif\n')
    return raw.replace(old,declaration+old).replace(anchor,anchor+call)


def install(source, identity):
    from builtin_init_route import install as baseline_install
    source = Path(source)
    for name, pin in API_PINS.items():
        require(hashlib.sha256((source/name).read_bytes()).hexdigest() == pin, 'pinned early FDT API differs: '+name)
    setup = overlay_setup((source/'arch/arm64/kernel/setup.c').read_bytes())
    result = baseline_install(source, identity)
    replacements = {
        'drivers/misc/note10_sha256_kat.c': (HERE/'early_fdt_composition.c').read_bytes(),
        'drivers/misc/early_fdt_binding.c': (HERE/'early_fdt_binding.c').read_bytes(),
        'arch/arm64/kernel/setup.c': setup,
    }
    kconfig = source/'drivers/misc/note10_sha256_kat.Kconfig'
    kconfig.write_bytes(kconfig.read_bytes()+b"""
config NOTE10_EARLY_FDT_BINDING
\tbool "Note10 memblock-owned post-paging FDT snapshot diagnostic"
\tdepends on ARM64 && OF_FLATTREE && HAVE_MEMBLOCK && NO_BOOTMEM && NOTE10_SHA256_KAT_RECOVERY && NOTE10_BUILTIN_INIT_ROUTE
\tdefault n
\thelp
\t  Copies at most 512KiB after paging/reservations. Hashes owned
\t  bytes only after recovery is armed. Not pristine firmware or CPU state.
""")
    for name, data in replacements.items():
        (source/name).write_bytes(data)
    return {name: hashlib.sha256((source/name).read_bytes()).hexdigest() for name in (*result, *replacements)}


# Carried accepted v78 producer/System.map/config/route data; no old Image reader.
CONFIG_PATH_OR_TASK_KEYS = ('CONFIG_LOCALVERSION', 'CONFIG_INITRAMFS_SOURCE', 'CONFIG_NOTE10_CPU_AFFINITY_BINDING', 'CONFIG_NOTE10_EARLY_FDT_BINDING')
ACCEPTED_BASELINE = {'source_head': '24f0fb9c4680517d6b0411a9985847c42b692376', 'producer_result_sha256': '2001c4a8f42ddca3f867b2e5d461fe977fc96db6adcb9a43e46dce80bbcbd2cb', 'system_map_sha256': 'fa1b8a0848667e5a63c6341a82bc029cf5b6f7142595fe2334a7baf1332e0e27', 'linked_kernel_bytes': 55132160, 'image_file_bytes': 46413836, 'header': {'text_offset': 524288, 'flags': 10}, 'config_sha256': '2870aaf268c22be009a1c7bad680115918ff88edbf59ce2df03ee3d08f5e3042', 'route_sources': {'note10/device_test/builtin_minimal_init.S': 'ca8ad494643331a3065b25f0e62330dce4c7385a354bac71e75a972627a6ad60', 'note10/device_test/builtin_init_route.c': '2fb12577bfd332cd83c3e497aa5930c275983e0f9139d22f53b009b0a9249d74', 'note10/device_test/builtin_init_route.py': '46b100dc95f11e344c11b8cb3fba5d34d17b2884385923426a42246699fda43d', 'note10/device_test/auto_return.c': '9ec43d3d17f12fe90d2ab36e4712537b7f8275f6f27b6536bbef826f9692037d', 'note10/device_test/sha256_kat_recovery_work.c': 'a39e955e0a104251434fed69e137687e0f24876f63e1f496f401d95acf119859'}, 'route_artifacts': {'guarded_init_main_sha256': '564068e2b756204e9ec80e801ff2a7999026197635dba46d7c5304091f87bea6', 'minimal_init_elf_sha256': '7c300fe3b5725da0f8556ff5e2515a1466cd6408acf7b1ccadc5bda067e60a49', 'initramfs_cpio_sha256': '5a6ddf6eb3692c4db62dd4536acae53a78c55505a1b7dc5456d32a53770d9e60'}}


def placement_config_sha256(lines):
    values = {}
    for line in lines:
        if line.startswith('CONFIG_') and '=' in line:
            key, value = line.split('=',1)
        elif line.startswith('# CONFIG_') and line.endswith(' is not set'):
            key, value = line[2:-11], 'n'
        else:
            continue
        require(key not in values, 'duplicate placement configuration')
        values[key] = value
    for key in CONFIG_PATH_OR_TASK_KEYS:
        values.pop(key,None)
    import json
    return hashlib.sha256(json.dumps(values,sort_keys=True,separators=(',',':')).encode()).hexdigest()


def linked_footprint(system_map, object_symbols, image_memory_bytes, text_offset, flags):
    wanted = {'_text','_end','__bss_start','__bss_stop','n10_fdt_snapshot'}
    values = {}
    for line in system_map.splitlines():
        parts = line.split()
        if len(parts)==3 and parts[2] in wanted:
            require(parts[2] not in values, 'duplicate linked footprint symbol')
            values[parts[2]]=int(parts[0],16)
    storage = {}
    for line in object_symbols.splitlines():
        parts=line.split()
        if len(parts)==4 and parts[2].lower() in ('b','d') and parts[3].startswith('n10_fdt_'):
            require(parts[3] not in storage, 'duplicate snapshot state symbol')
            storage[parts[3]]=int(parts[1],16)
    require(set(values)==wanted and storage.get('n10_fdt_snapshot')==8 and 8<=sum(storage.values())<=64 and
            values['_text']<values['__bss_start']<=values['n10_fdt_snapshot'] and
            values['n10_fdt_snapshot']+8<=values['__bss_stop']<=values['_end'] and
            type(image_memory_bytes) is int and image_memory_bytes==values['_end']-values['_text'] and
            type(text_offset) is int and 0<=text_offset<2**64 and type(flags) is int and 0<=flags<2**64,
            'exact tiny memblock pointer state/linked Image extent unavailable')
    return dict(snapshot_capacity_bytes=CAPACITY,allocation_form=ALLOCATION,
                snapshot_pointer_bytes=8,snapshot_state_bytes=sum(storage.values()),
                image_memory_bytes=image_memory_bytes,linked_kernel_bytes=values['_end']-values['_text'],
                bss_start_offset=values['__bss_start']-values['_text'],
                bss_end_offset=values['__bss_stop']-values['_text'],
                snapshot_pointer_offset=values['n10_fdt_snapshot']-values['_text'],
                image_text_offset=text_offset,image_flags=flags)


def relative_placement_admission(result, lines, footprint):
    """Conservative retained-envelope continuity, not observed physical base."""
    baseline=ACCEPTED_BASELINE
    checks={
        'revised_owned_boundary':type(result.get('fdt_capture_revision')) is int and result['fdt_capture_revision']==REVISION and
            result.get('fdt_capture_boundary')==BOUNDARY and result.get('fdt_allocation_form')==ALLOCATION,
        'linked_span_contained':type(footprint.get('linked_kernel_bytes')) is int and
            0<footprint['linked_kernel_bytes']<=baseline['linked_kernel_bytes'],
        'file_bytes_contained':type(result.get('image_bytes')) is int and
            0<result['image_bytes']<=baseline['image_file_bytes'],
        'same_header_load_contract':footprint.get('image_text_offset')==baseline['header']['text_offset'] and
            footprint.get('image_flags')==baseline['header']['flags'],
        'same_placement_configuration':placement_config_sha256(lines)==baseline['config_sha256'],
        'same_builtin_recovery_route':all(result.get('source_sha256',{}).get(k)==v for k,v in baseline['route_sources'].items()) and
            all(result.get(k)==v for k,v in baseline['route_artifacts'].items()),
        'supported_memblock_backend':{'CONFIG_HAVE_MEMBLOCK=y','CONFIG_NO_BOOTMEM=y','CONFIG_ARM64_4K_PAGES=y'}.issubset(lines),
        'tiny_state_allocation':footprint.get('allocation_form')==ALLOCATION and footprint.get('snapshot_pointer_bytes')==8 and
            type(footprint.get('snapshot_state_bytes')) is int and 8<=footprint['snapshot_state_bytes']<=64,
    }
    return dict(eligible=all(checks.values()),checks=checks,baseline_source_head=baseline['source_head'],
                baseline_producer_result_sha256=baseline['producer_result_sha256'],
                claim='no new relative linked coverage under unchanged normal Linux loader contract',
                observed_runtime_base=False,absolute_FDT_extent_known=False,global_RAM_ownership=False)


def fixed_route_relation(elf, archive, result, raw_inputs):
    """Fixed supported layout only; normalize this one nonloadable filename in RAM."""
    require(type(elf) is bytes and len(elf)==ELF_BYTES and type(archive) is bytes and len(archive)==CPIO_BYTES,
            'exact tiny route layout required')
    require(type(raw_inputs) is dict, 'same-buffer raw route measurements required')
    stop=TEMP_NAME_OFFSET+TEMP_NAME_BYTES
    name=elf[TEMP_NAME_OFFSET:stop]
    require(re.fullmatch(rb'cc[A-Za-z0-9]{6}\.o',name) and elf[stop:stop+1]==b'\0',
            'one fixed temporary STT_FILE name required')
    require(archive[INIT_PAYLOAD_OFFSET:INIT_PAYLOAD_OFFSET+ELF_BYTES]==elf,
            'current CPIO init payload differs from exact current ELF')
    normalized=bytearray(elf);normalized[TEMP_NAME_OFFSET:stop]=bytes(TEMP_NAME_BYTES)
    require(hashlib.sha256(normalized).hexdigest()==ELF_CANONICAL_SHA256,
            'ELF bytes outside the sole nonloadable filename changed')
    normalized=bytearray(archive)
    normalized[INIT_PAYLOAD_OFFSET+TEMP_NAME_OFFSET:INIT_PAYLOAD_OFFSET+stop]=bytes(TEMP_NAME_BYTES)
    require(hashlib.sha256(normalized).hexdigest()==CPIO_CANONICAL_SHA256,
            'CPIO layout/metadata/padding/current payload changed')
    # These same-buffer measurements already come from intrinsic PID1 binding.
    for key,file_key in (('minimal_init_elf_sha256','minimal-init.elf'),('initramfs_cpio_sha256','initramfs.cpio')):
        actual=raw_inputs.get(key)
        require(isinstance(actual,str) and re.fullmatch('[0-9a-f]{64}',actual) and
                result.get(key)==actual==result.get('files_sha256',{}).get(file_key),
                'exact current raw route hashes differ')
    return dict(kind='fixed-nonloadable-STT_FILE-relation-v1',elf_canonical_sha256=ELF_CANONICAL_SHA256,
                cpio_canonical_sha256=CPIO_CANONICAL_SHA256,
                current_elf_sha256=raw_inputs['minimal_init_elf_sha256'],
                current_cpio_sha256=raw_inputs['initramfs_cpio_sha256'],raw_artifact_equality_claimed=False)


def input_binding(result, lines, *, elf, archive, raw_inputs):
    require(result.get('version')=='v81' and result.get('diagnostic_kind')==KIND and
            result.get('raw_input_binding') is False and result.get('fdt_capture_boundary')==BOUNDARY and
            result.get('fdt_snapshot_capacity_bytes')==CAPACITY and
            type(result.get('fdt_capture_revision')) is int and result['fdt_capture_revision']==REVISION and
            result.get('fdt_allocation_form')==ALLOCATION, 'closed revised FDT scope required')
    require(result.get('ci_context',{}).get('GITHUB_SHA')==IMAGE_SOURCE_HEAD and
            result.get('image_sha256')==IMAGE_SHA256 and result.get('passed') is True and result.get('Image_built') is True,
            'exact successful a77 memblock Image required')
    require('CONFIG_NOTE10_EARLY_FDT_BINDING=y' in lines and
            not {'CONFIG_NOTE10_CPU_AFFINITY_BINDING=y','CONFIG_NOTE10_SHA256_STREAM_STATE=y'} & set(lines),
            'closed FDT configuration required')
    require(all(result.get('source_sha256',{}).get(k)==v for k,v in IMAGE_SOURCE_PINS.items()),
            'frozen Image-producing FDT source closure differs')
    footprint=result.get('fdt_snapshot_footprint')
    require(type(footprint) is dict and footprint.get('snapshot_capacity_bytes')==CAPACITY,
            'linked FDT footprint missing')
    producer_admission=relative_placement_admission(result,lines,footprint)
    require(result.get('fdt_relative_placement')==producer_admission, 'immutable producer admission changed')
    relation=fixed_route_relation(elf,archive,result,raw_inputs)
    core_route=all(result.get('source_sha256',{}).get(k)==v for k,v in ACCEPTED_BASELINE['route_sources'].items()) and \
        result.get('guarded_init_main_sha256')==ACCEPTED_BASELINE['route_artifacts']['guarded_init_main_sha256']
    checks=dict(producer_admission['checks'])
    checks['same_builtin_recovery_route']=core_route  # Fixed relation above protects remaining route bytes.
    require(all(checks.values()), 'effective host relative placement continuity unresolved')
    effective=dict(kind='v81-revision2-effective-host-admission',eligible=True,
        image_source_head=IMAGE_SOURCE_HEAD,producer_reported_eligible=producer_admission['eligible'],
        checks=checks,route_relation=relation,observed_runtime_base=False,absolute_FDT_extent_known=False,
        global_RAM_ownership=False)
    return dict(fdt_capture_boundary=BOUNDARY,fdt_snapshot_capacity_bytes=CAPACITY,raw_input_binding=False,
                fdt_capture_revision=REVISION,fdt_allocation_form=ALLOCATION,
                fdt_relative_placement_admitted=True,fdt_effective_host_admission=effective)


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
