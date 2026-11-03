"""Closed KAT-only bindings. Reuse existing packer/writer/journal; no new actuator."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
from types import MappingProxyType
import shutil
import subprocess
import sys
import uuid

PROFILE = 'sha256-kat-recovery-v1'
BUILTIN_PROFILE = 'sha256-kat-builtin-init-v2'
STREAM_PROFILE = 'sha256-stream-state-v1'
AFFINITY_PROFILE = 'cpu-affinity-binding-v1'
FDT_PROFILE = 'early-fdt-binding-v1'
NATIVE_PROFILE = 'native-memory-observation-v1'
DATA_PROFILE = 'linux-data-carrier-v1'
ROOT = Path(__file__).resolve().parents[2]
SLOT = b'N10_CYCLE_SLOT_UNSET_0123456789A'
FIELDS = ('device_profile', 'profile_sha256', 'build_evidence_id', 'kernel_banner', 'accepted_result_sha256',
          'source_head', 'image_root_receipt_sha256', 'root_reader_result_sha256',
          'host_profile_source_head', 'host_profile_source_sha256')
HOST_SOURCES = ('sha256_kat_device_profile.py', 'test_sha256_kat_device_profile.py',
                'materialize_auto_cycle.py', 'prepare_linux_boot.py', 'build_boot_test_packages.py',
                'stage_phase2.py', 'auto_cycle.py','current_data_reuse.py','test_current_data_reuse.py')
PLAN_KEYS = {'schema', 'kind', 'device_profile', 'kernel_build', 'backup', 'backup_manifest_sha256',
             'build_result_sha256', 'image_sha256', 'identity', 'current_packages',
             'current_package_result_sha256', 'reference_twrp', 'mkbootimg',
             'minimum_battery', 'return_timeout_seconds', 'stages'}
STAGE_KEYS = {'index', 'cycle', 'kernel_build', 'image_sha256', 'build_result_sha256',
              'packages', 'package_result_sha256'}
LEGACY = ('early_xnu_reservation', 'builtin_cpu_diagnostic', 'builtin_idle_init',
          'window_access_diagnostic', 'xnu_payload_stage_diagnostic', 'cpu_cache_roundtrip_diagnostic',
          'pm_timer_diagnostic', 'cpu_pm_roundtrip', 'cpu_pm_notifier_counts', 'cpu_pm_notifier_trace')


def require(value, message):
    if not value:
        raise ValueError(message)


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def save(path, value):
    Path(path).write_text(json.dumps(value, indent=2, sort_keys=True)+'\n', encoding='utf8')


def private(path):
    path = Path(path).resolve()
    base = (ROOT/'note10/private').resolve()
    require(path != base and path.is_relative_to(base), 'private child path required')
    return path


def selected(row):
    marker = row.get('device_profile')
    require(marker in (None, PROFILE, BUILTIN_PROFILE, STREAM_PROFILE, AFFINITY_PROFILE, FDT_PROFILE, NATIVE_PROFILE, DATA_PROFILE), 'unknown device profile')
    return marker in (PROFILE, BUILTIN_PROFILE, STREAM_PROFILE, AFFINITY_PROFILE, FDT_PROFILE, NATIVE_PROFILE, DATA_PROFILE)


def no_legacy(row):
    require(not any(row.get(k) for k in LEGACY), 'KAT profile cannot claim legacy evaluations')
    for key, value in row.items():
        if key.endswith(('_diagnostic', '_audit', '_restore')) and key != 'auto_return_diagnostic':
            require(not value, 'KAT profile contains unrelated diagnostic scope: '+key)


def physical_input_scope(result):
    from readonly_stage_witness import refuse
    refuse(result)
    from kernel_readonly_span_candidate import is_candidate as is_type3
    if is_type3(result):
        from kernel_readonly_span_candidate import physical_input_scope as type3_scope
        type3_scope(result)
    require(result.get('PC_only') is not True and result.get('data_expectation_mode')!='kernel-readonly-slot-v1' and
            result.get('version')!='v103' and result.get('diagnostic_kind') not in
            ('owned-contiguous-staging-pc','current-owned-staging-pc','readonly-input-pc','kernel-readonly-span-pc') and
            not any(key in result for key in ('readonly_input_schema','readonly_input_slot','readonly_pc_contract','kernel_readonly_span_schema')),
            'PC-only candidate cannot create a physical template/package')


def raw_binding(root, expected_result, expected_source, *, producing_sources=None, readonly_origin=None):
    root = private(root)
    if readonly_origin is not None:
        require(readonly_origin==expected_source and readonly_origin in (V105_CANDIDATE_ORIGIN_HEAD,__import__('kernel_readonly_span_candidate').NATIVE_HEAD) and producing_sources is None,'exact read-side native candidate origin only')
    else:
        require(expected_source!=V105_CANDIDATE_ORIGIN_HEAD,'retained candidate cannot construct a new template')
    require(re.fullmatch('[0-9a-f]{64}', expected_result or '') and
            re.fullmatch('[0-9a-f]{40}', expected_source or ''), 'exact accepted result/source pins required')
    require(sha(root/'result.json') == expected_result, 'accepted CI result changed')
    result = read(root/'result.json')
    physical_input_scope(result)
    if producing_sources is not None:
        from current_data_reuse import require_context
        require_context(producing_sources).require_result(root,expected_result,expected_source,result)
    stream = result.get('version') == 'v73'
    affinity = result.get('version') == 'v78'
    fdt = result.get('version') == 'v81'
    type3=result.get('version')=='v107' and result.get('diagnostic_kind')=='kernel-readonly-span-candidate'
    if type3:
        from kernel_readonly_span_candidate import producer_contract as type3_producer,NATIVE_HEAD,NATIVE_RESULT_SHA256
        require(readonly_origin==expected_source==NATIVE_HEAD and expected_result==NATIVE_RESULT_SHA256,'exact accepted native107 read-side result required')
        type3_producer(result,expected_source,historical_origin=readonly_origin)
    kernel_ro = result.get('version')=='v105'
    require(readonly_origin is None or kernel_ro and readonly_origin==V105_CANDIDATE_ORIGIN_HEAD and result.get('diagnostic_kind')=='kernel-readonly-candidate' or type3,
            'retained read-side exception is candidate-only')
    data = result.get('version') in ('v88','v89','v90','v91','v105','v107')
    native = result.get('version') == 'v82'
    builtin = result.get('version') in ('v72', 'v73', 'v78', 'v81', 'v82', 'v88', 'v89', 'v90', 'v91', 'v105', 'v107')
    marker = DATA_PROFILE if data else NATIVE_PROFILE if native else FDT_PROFILE if fdt else AFFINITY_PROFILE if affinity else STREAM_PROFILE if stream else BUILTIN_PROFILE if builtin else PROFILE
    require(result.get('version') in ('v71', 'v72', 'v73', 'v78', 'v81', 'v82', 'v88', 'v89', 'v90', 'v91', 'v105', 'v107') and result.get('passed') is True and
            result.get('Image_built') is True and result.get('BOOT_built') is False and
            result.get('cycle_slot_patched') is False and result.get('kernel_or_provider_executed') is False and
            result.get('ci_context', {}).get('GITHUB_SHA') == expected_source and
            result.get('kernel_commit') == '55f042627bb7030c93550faafa117674d32b21d1' and
            result.get('make_target') == 'Image' and
            result.get('integration_object') == 'drivers/misc/note10_sha256_kat.o',
            'accepted new Image result scope differs')
    require(not stream or result.get('diagnostic_kind') == 'sha256-stream-state', 'new stream task required')
    require(not affinity or result.get('diagnostic_kind') == 'cpu-affinity-binding', 'new affinity task required')
    require(not fdt or result.get('diagnostic_kind') == 'early-fdt-binding', 'new FDT task required')
    require(not native or result.get('diagnostic_kind') == 'native-memory-observation', 'new native task required')
    require(not data or result.get('diagnostic_kind') == ('kernel-readonly-span-candidate' if type3 else 'kernel-readonly-candidate' if kernel_ro else 'linux-data-carrier'), 'new DATA task required')
    for name, digest in result['files_sha256'].items():
        path = root/name
        require(not Path(name).is_absolute() and '..' not in Path(name).parts and
                path.resolve().is_relative_to(root) and path.is_file() and not path.is_symlink() and
                sha(path) == digest, 'accepted Image input changed: '+name)
    for name, digest in result['source_sha256'].items():
        require(not Path(name).is_absolute() and '..' not in Path(name).parts and
                (root/'source'/name).resolve().is_relative_to(root/'source') and
                sha(root/'source'/name) == digest, 'accepted source changed: '+name)
    image = (root/'Image').read_bytes()
    require(sha(root/'Image') == result['image_sha256'] and len(image) == result['image_bytes'] and
            image[56:60] == b'ARM\x64' and image.count(SLOT+b'\0') == 1, 'Image/unique unarmed cycle slot differs')
    identity = result['build_evidence_id']
    require(re.fullmatch('[0-9a-f]{32}', identity or '') and identity.encode() in image and
            all(x in image for x in (b'N10RET1', b'N10DATARO3' if type3 else b'N10DATARO1' if kernel_ro else b'N10DATA1' if data else b'N10MEMARGS1' if native else b'N10FDT1' if fdt else b'N10AFF1' if affinity else b'N10SHASTREAM1' if stream else b'N10SHA1')) and
            (not stream or b'N10SHA1' not in image) and
            (not (affinity or fdt) or not any(marker in image for marker in (b'N10SHA1', b'N10SHASTREAM1'))) and
            (not fdt or b'N10AFF1' not in image) and
            (not native or not any(x in image for x in (b'N10SHA1',b'N10SHASTREAM1',b'N10AFF1',b'N10FDT1'))) and
            (not data or not any(x in image for x in (b'N10SHA1',b'N10SHASTREAM1',b'N10AFF1',b'N10FDT1',b'N10MEMARGS1'))), 'Image evidence identity differs')
    banners = re.findall((rb'Linux version 4\.14\.113-v107-readonly-span-candidate [^\x00\r\n]+' if type3 else rb'Linux version 4\.14\.113-v105-kernel-readonly [^\x00\r\n]+' if kernel_ro else rb'Linux version 4\.14\.113-v91-trusted-logical [^\x00\r\n]+' if result.get('version') == 'v91' else rb'Linux version 4\.14\.113-v90-image-expectation [^\x00\r\n]+' if result.get('version') == 'v90' else rb'Linux version 4\.14\.113-v89-data-guard [^\x00\r\n]+' if result.get('version') == 'v89' else rb'Linux version 4\.14\.113-v88-linux-data [^\x00\r\n]+' if data else rb'Linux version 4\.14\.113-v82-native-memory [^\x00\r\n]+' if native else rb'Linux version 4\.14\.113-v81-early-fdt [^\x00\r\n]+' if fdt else rb'Linux version 4\.14\.113-v78-cpu-affinity [^\x00\r\n]+' if affinity else rb'Linux version 4\.14\.113-v73-sha256-stream [^\x00\r\n]+' if stream else rb'Linux version 4\.14\.113-v72-builtin-init [^\x00\r\n]+' if builtin else rb'Linux version 4\.14\.113-v71-sha256-recovery [^\x00\r\n]+'), image)
    require(len(banners) == 1, 'unique actual profile kernel banner required')
    config = root/'prerequisites/objects/.config'
    required = {'CONFIG_NOTE10_SHA256_KAT_RECOVERY=y', 'CONFIG_CRYPTO=y', 'CONFIG_CRYPTO_HASH=y',
                'CONFIG_CRYPTO_SHA256=y', 'CONFIG_EXYNOS_REBOOT=y', 'CONFIG_SEC_REBOOT=y',
                'CONFIG_BLK_DEV_INITRD=y', 'CONFIG_RD_LZMA=y', 'CONFIG_ARM64_4K_PAGES=y',
                }
    if not builtin:
        required.add('CONFIG_INITRAMFS_SOURCE=""')
    lines = config.read_text().splitlines()
    if producing_sources is not None:
        require(not any(x in lines for x in ('CONFIG_NOTE10_OWNED_CONTIGUOUS_STAGING=y','CONFIG_NOTE10_CURRENT_OWNED_STAGING=y')),
                'historical reuse forbids early owned reservation')
    if stream:
        require('CONFIG_NOTE10_SHA256_STREAM_STATE=y' in lines and
                sha(ROOT/'note10/device_test/sha256_stream_vectors.json') ==
                result['source_sha256'].get('note10/device_test/sha256_stream_vectors.json'),
                'new stream option/vector source binding differs')
    require(required.issubset(lines) and (builtin or 'CONFIG_INITRAMFS_FORCE=y' not in lines) and
            'CONFIG_CMDLINE_FORCE=y' not in lines, 'external TWRP ramdisk/recovery configuration differs')
    policy_source = 'note10/device_test/build_sha256_kat_recovery.py'
    require(sha(ROOT/policy_source) == result['source_sha256'].get(policy_source),
            'live command-line policy helper differs from Image-producing source')
    if not builtin:
        from build_sha256_kat_recovery import bootloader_cmdline_policy
        bootloader_cmdline_policy('\n'.join(lines))
    extra = {}
    if builtin:
        from builtin_init_profile import input_binding
        extra = input_binding(root, result, image, lines, fdt_owned_route=fdt,native_memory_route=native,data_carrier_route=data,producing_sources=producing_sources,readonly_origin=readonly_origin)
    if affinity:
        from affinity_binding import input_binding as affinity_input_binding
        extra.update(affinity_input_binding(result, lines))
    if fdt:
        from early_fdt_binding import linked_footprint
        import struct
        measured_footprint = linked_footprint((root/'System.map').read_text(),
            (root/'new-object-symbols.log').read_text(), struct.unpack_from('<Q',image,16)[0],
            struct.unpack_from('<Q',image,8)[0],struct.unpack_from('<Q',image,24)[0])
        require(result.get('fdt_snapshot_footprint') == measured_footprint, 'linked FDT footprint changed')
    if native:
        from native_memory_observation import linked_footprint as native_footprint
        import struct
        measured=native_footprint((root/'System.map').read_text(),(root/'new-object-symbols.log').read_text(),
            struct.unpack_from('<Q',image,16)[0],struct.unpack_from('<Q',image,8)[0],struct.unpack_from('<Q',image,24)[0])
        require(result.get('native_memory_footprint')==measured,'native linked state/footprint changed')
    if data:
        from linux_data_carrier import linked_footprint as data_footprint, slot_metadata
        import struct
        map_text, object_text = (root/'System.map').read_text(), (root/'new-object-symbols.log').read_text()
        measured = data_footprint(map_text, object_text,
            struct.unpack_from('<Q',image,16)[0],struct.unpack_from('<Q',image,8)[0],struct.unpack_from('<Q',image,24)[0])
        require(measured == result.get('data_footprint'), 'DATA footprint differs')
        if type3:
            from kernel_readonly_span_candidate import slot_metadata as type3_slot,span_metadata
            require(type3_slot(image,map_text,object_text,(root/'new-object-sections.log').read_text(),
                (root/'new-object-symbol-table.log').read_text())==result.get('kernel_readonly3_slot') and
                span_metadata(map_text,measured,result['kernel_readonly3_slot'])==result.get('kernel_readonly3_span'),'native107 intrinsic class3 witnesses differ')
        elif kernel_ro:
            from kernel_readonly_input import slot_metadata as kernel_slot
            require(kernel_slot(image,map_text,object_text,(root/'new-object-sections.log').read_text(),
                (root/'new-object-symbol-table.log').read_text())==result.get('kernel_readonly_slot'),
                'original CI readonly class2 slot provenance differs')
        else:
            require(slot_metadata(image,map_text,object_text,(root/'new-object-sections.log').read_text()) == result.get('data_expectation_slot'), 'original CI Image slot provenance differs')
    return dict(device_profile=marker, **extra, accepted_result_sha256=expected_result,
                source_head=expected_source, image_sha256=result['image_sha256'], image_size=len(image),
                effective_config_sha256=sha(config), build_evidence_id=identity,
                kernel_banner=banners[0].decode('ascii'))


# Exact previously accepted host7: used only to validate the immutable v71
# current-BOOT pair after v72 changes. Never relabel it as current source.
V71_HOST_HEAD = '5e233aa5f08473d716ca2e9b3d8937c1821d513f'
V71_HOST_PINS = {'note10/device_test/sha256_kat_device_profile.py': '76111d416db9646271a7de9ae7ab55288e23aa5304ad6601b94bedc900832ea5', 'note10/device_test/test_sha256_kat_device_profile.py': 'c48400d5573695d217101806b8481e39aec38fd5382e64b85f999b4cee42c498', 'note10/device_test/materialize_auto_cycle.py': '87ef3da2e0ddbbb40b02bc9334c59deb8c590692352f099cb2b3ae99b749f960', 'note10/device_test/prepare_linux_boot.py': '4f599c7c667e3dc18a5afccfd682c47f705ed714daa916b4c0557db9f7f78c70', 'note10/device_test/build_boot_test_packages.py': 'afbf2d7352ce4722ce6d7cb6d2430bb06962f5a5b1fa570fbd68f182faf4fdda', 'note10/device_test/stage_phase2.py': '9e340ba0d6244ef5c2673317b01dfdec4433959241f6318669b8d27f01ce319b', 'note10/device_test/auto_cycle.py': '0118d152452434b76fc77ad6089165a601abca3838699c5dd7f28d8f371e3950'}


V72_HOST_HEAD = '149cb74c3f7640f2e26dfdcd1d775ec99f6c02ac'
V72_HOST_PINS = {'note10/device_test/auto_cycle.py': 'e69be83bf1ac709173679f0476de7ad84b17ea3b737e34f47223d974f4ea36ee', 'note10/device_test/build_boot_test_packages.py': 'f829b2c7482b76231bc19dcd6f383efca999147e2bfaedf7e5f89bd2dcea0c18', 'note10/device_test/builtin_init_profile.py': 'b9cb4ed6c9e7c555932392be5a95990db2b0d5a1d0b523be9c5c92a2ba454099', 'note10/device_test/builtin_init_route.py': '46b100dc95f11e344c11b8cb3fba5d34d17b2884385923426a42246699fda43d', 'note10/device_test/materialize_auto_cycle.py': '87ef3da2e0ddbbb40b02bc9334c59deb8c590692352f099cb2b3ae99b749f960', 'note10/device_test/prepare_linux_boot.py': '4f599c7c667e3dc18a5afccfd682c47f705ed714daa916b4c0557db9f7f78c70', 'note10/device_test/sha256_kat_device_profile.py': 'f18e6f159eb2f98e2fcf8340985c9c44923b0c6a6b028fe362258d9a49c2f80d', 'note10/device_test/stage_phase2.py': '1ecc741d7517fc15a6043b1329b726e420791f06e712bfd1aaf901a7747db433', 'note10/device_test/test_builtin_init_route.py': '9fa63dd55114472a748062447dd95c17bf4d4d7e743117f69f0bb6a7aca6ea42', 'note10/device_test/test_sha256_kat_device_profile.py': 'c48400d5573695d217101806b8481e39aec38fd5382e64b85f999b4cee42c498'}


# Exact accepted current-BOOT host closure; carried pins, never current source.
V73_HOST_HEAD = '7e4a8c992f95f01429e824404378fa9271c0eb8e'
V73_HOST_PINS = {'note10/device_test/auto_cycle.py': 'e69be83bf1ac709173679f0476de7ad84b17ea3b737e34f47223d974f4ea36ee', 'note10/device_test/build_boot_test_packages.py': '0d5b06bcf7d0cca1f2da2490cb283b7d191e5f8192fa8cef9eac557e47259396', 'note10/device_test/builtin_init_profile.py': 'bf411a8b2b58e9ba0c8e30aca44eef5952aea3137e288bf8927f2c6555e61809', 'note10/device_test/builtin_init_route.py': '46b100dc95f11e344c11b8cb3fba5d34d17b2884385923426a42246699fda43d', 'note10/device_test/materialize_auto_cycle.py': '87ef3da2e0ddbbb40b02bc9334c59deb8c590692352f099cb2b3ae99b749f960', 'note10/device_test/prepare_linux_boot.py': '4f599c7c667e3dc18a5afccfd682c47f705ed714daa916b4c0557db9f7f78c70', 'note10/device_test/sha256_kat_device_profile.py': 'fa8c2632cf8e3826925539a35b793c8f99e32e97dbd305822da6c32cce7c1d21', 'note10/device_test/sha256_stream_state.py': '55de2735fb830ae8047bb4a8fa74325f51b766b1e885c482dbbc5ebabe3ea437', 'note10/device_test/sha256_stream_vectors.json': '5c379d1ef41a40b9a1262c985476e9dc0ba88dae7b1586f949bbe79686f2165f', 'note10/device_test/stage_phase2.py': '1ecc741d7517fc15a6043b1329b726e420791f06e712bfd1aaf901a7747db433', 'note10/device_test/test_builtin_init_route.py': '9fa63dd55114472a748062447dd95c17bf4d4d7e743117f69f0bb6a7aca6ea42', 'note10/device_test/test_sha256_kat_device_profile.py': 'c48400d5573695d217101806b8481e39aec38fd5382e64b85f999b4cee42c498', 'note10/device_test/test_sha256_stream_state.py': '088881f92037a9895b7947eb44692f51ecba1eb602a02dacc02ff3b94a836db8'}


# Exact accepted v78 host closure; current package lineage must remain immutable.
V78_HOST_HEAD = 'a0674c29eaa2bc8938023fc2be590b9a4a84374e'
V78_HOST_PINS = {'note10/device_test/affinity_binding.py': '6d5b16d54a803c95bdd391a38efbd2bac5ef36baffe199f86cd83f878bf10678', 'note10/device_test/auto_cycle.py': 'e69be83bf1ac709173679f0476de7ad84b17ea3b737e34f47223d974f4ea36ee', 'note10/device_test/build_boot_test_packages.py': 'e7d34e08c15eed674af7d4467bb5b615ee3492f3798f4ebd7f0d21cc1c707b97', 'note10/device_test/builtin_init_profile.py': '6df07ee89a3dc7e46506a8dbec1013ea57511d72336c16daabbf9442e8aa2b62', 'note10/device_test/builtin_init_route.py': '46b100dc95f11e344c11b8cb3fba5d34d17b2884385923426a42246699fda43d', 'note10/device_test/materialize_auto_cycle.py': '87ef3da2e0ddbbb40b02bc9334c59deb8c590692352f099cb2b3ae99b749f960', 'note10/device_test/prepare_linux_boot.py': '4f599c7c667e3dc18a5afccfd682c47f705ed714daa916b4c0557db9f7f78c70', 'note10/device_test/sha256_kat_device_profile.py': '41a01209338e25ea72b8f2f8e9d07cd5900135fd7bd819346be5d1a4b979a3d1', 'note10/device_test/sha256_stream_state.py': '55de2735fb830ae8047bb4a8fa74325f51b766b1e885c482dbbc5ebabe3ea437', 'note10/device_test/sha256_stream_vectors.json': '5c379d1ef41a40b9a1262c985476e9dc0ba88dae7b1586f949bbe79686f2165f', 'note10/device_test/stage_phase2.py': '1ecc741d7517fc15a6043b1329b726e420791f06e712bfd1aaf901a7747db433', 'note10/device_test/test_affinity_binding.py': 'bf602887c4437e0096473392789da33e3ef502297d8c060faf7d9da9ecd3eb89', 'note10/device_test/test_affinity_ci_context.py': '71aad30ab105a45efe2703fd7b222233836d6e7514560834daa71bfdd351dea9', 'note10/device_test/test_builtin_init_route.py': '9fa63dd55114472a748062447dd95c17bf4d4d7e743117f69f0bb6a7aca6ea42', 'note10/device_test/test_sha256_kat_device_profile.py': 'c48400d5573695d217101806b8481e39aec38fd5382e64b85f999b4cee42c498', 'note10/device_test/test_sha256_stream_state.py': '088881f92037a9895b7947eb44692f51ecba1eb602a02dacc02ff3b94a836db8'}


# Frozen code-only a77 Image-era host closure; never relabelled as current host.
V81_IMAGE_HEAD = 'a77f1eca32d1888f3266f49412dda9f0129f8719'
V81_IMAGE_HOST_PINS = {'note10/device_test/sha256_kat_device_profile.py': 'a60c1cd0cfeaf89b21524d6b634f66fb3e9518184ea086938e4697866db18bc5', 'note10/device_test/test_sha256_kat_device_profile.py': 'c48400d5573695d217101806b8481e39aec38fd5382e64b85f999b4cee42c498', 'note10/device_test/materialize_auto_cycle.py': '87ef3da2e0ddbbb40b02bc9334c59deb8c590692352f099cb2b3ae99b749f960', 'note10/device_test/prepare_linux_boot.py': '4f599c7c667e3dc18a5afccfd682c47f705ed714daa916b4c0557db9f7f78c70', 'note10/device_test/build_boot_test_packages.py': '774d978651cbbc75a29e377860f0b100933137af217a81d301ce68bb33a6d3a4', 'note10/device_test/stage_phase2.py': '1ecc741d7517fc15a6043b1329b726e420791f06e712bfd1aaf901a7747db433', 'note10/device_test/auto_cycle.py': '36793ff1964331b3a77b530fc1be5923d1807a3752ab0f7d4f68a51adde12812', 'note10/device_test/builtin_init_profile.py': 'c9246e6acc22d6666109f90d17368c71e4c61273ebfd1f8bb11f93971119dfa9', 'note10/device_test/builtin_init_route.py': '46b100dc95f11e344c11b8cb3fba5d34d17b2884385923426a42246699fda43d', 'note10/device_test/test_builtin_init_route.py': '9fa63dd55114472a748062447dd95c17bf4d4d7e743117f69f0bb6a7aca6ea42', 'note10/device_test/sha256_stream_state.py': '55de2735fb830ae8047bb4a8fa74325f51b766b1e885c482dbbc5ebabe3ea437', 'note10/device_test/sha256_stream_vectors.json': '5c379d1ef41a40b9a1262c985476e9dc0ba88dae7b1586f949bbe79686f2165f', 'note10/device_test/test_sha256_stream_state.py': '088881f92037a9895b7947eb44692f51ecba1eb602a02dacc02ff3b94a836db8', 'note10/device_test/affinity_binding.py': '6d5b16d54a803c95bdd391a38efbd2bac5ef36baffe199f86cd83f878bf10678', 'note10/device_test/test_affinity_binding.py': 'bf602887c4437e0096473392789da33e3ef502297d8c060faf7d9da9ecd3eb89', 'note10/device_test/test_affinity_ci_context.py': '71aad30ab105a45efe2703fd7b222233836d6e7514560834daa71bfdd351dea9', 'note10/device_test/test_partition_gate_evidence.py': 'b7dd52aa5c7747489a2713f805dbe15a6318f3d3776a8043700549e9383bcc72', 'note10/device_test/early_fdt_binding.py': '51a3dce472787ffe739c2458ad0505bad0eb43964ef031e3ff78a0a70beec5f9', 'note10/device_test/test_early_fdt_binding.py': '2444d3d20b7cc42e705cb89c1d04de72599f7da2a5d1b9282636f3b9990ce1fa'}


# Actual consumed v81 accepted host closure, distinct from its a77 Image.
V81_HOST_HEAD = '7490b4286417a6581be292de0ac1a5c3a6a079aa'
V81_HOST_PINS = {'note10/device_test/affinity_binding.py': '6d5b16d54a803c95bdd391a38efbd2bac5ef36baffe199f86cd83f878bf10678', 'note10/device_test/auto_cycle.py': '36793ff1964331b3a77b530fc1be5923d1807a3752ab0f7d4f68a51adde12812', 'note10/device_test/build_boot_test_packages.py': '774d978651cbbc75a29e377860f0b100933137af217a81d301ce68bb33a6d3a4', 'note10/device_test/builtin_init_profile.py': 'fcedb2d8f4cc3350a6c4e30dbb99c9dac24119182df8f2d2a02bf2d8f77640b7', 'note10/device_test/builtin_init_route.py': '46b100dc95f11e344c11b8cb3fba5d34d17b2884385923426a42246699fda43d', 'note10/device_test/early_fdt_binding.py': 'd4f7099fb45eca31c83c9acd9fbfe0cd5c7ccc5c271c18180e3672e22f9a6b78', 'note10/device_test/materialize_auto_cycle.py': '87ef3da2e0ddbbb40b02bc9334c59deb8c590692352f099cb2b3ae99b749f960', 'note10/device_test/prepare_linux_boot.py': '4f599c7c667e3dc18a5afccfd682c47f705ed714daa916b4c0557db9f7f78c70', 'note10/device_test/sha256_kat_device_profile.py': 'ede9f06c4652a3366b535bad510fae99504ccef0f1dd9f45fbafd01bb579ef60', 'note10/device_test/sha256_stream_state.py': '55de2735fb830ae8047bb4a8fa74325f51b766b1e885c482dbbc5ebabe3ea437', 'note10/device_test/sha256_stream_vectors.json': '5c379d1ef41a40b9a1262c985476e9dc0ba88dae7b1586f949bbe79686f2165f', 'note10/device_test/stage_phase2.py': '1ecc741d7517fc15a6043b1329b726e420791f06e712bfd1aaf901a7747db433', 'note10/device_test/test_affinity_binding.py': 'bf602887c4437e0096473392789da33e3ef502297d8c060faf7d9da9ecd3eb89', 'note10/device_test/test_affinity_ci_context.py': '71aad30ab105a45efe2703fd7b222233836d6e7514560834daa71bfdd351dea9', 'note10/device_test/test_builtin_init_route.py': '9fa63dd55114472a748062447dd95c17bf4d4d7e743117f69f0bb6a7aca6ea42', 'note10/device_test/test_early_fdt_binding.py': '2444d3d20b7cc42e705cb89c1d04de72599f7da2a5d1b9282636f3b9990ce1fa', 'note10/device_test/test_early_fdt_host_route.py': '75992eb3e8b1228d0ae3916d47306f0329b7947cb0dfae234ec25c1e737fef6a', 'note10/device_test/test_partition_gate_evidence.py': 'b7dd52aa5c7747489a2713f805dbe15a6318f3d3776a8043700549e9383bcc72', 'note10/device_test/test_sha256_kat_device_profile.py': 'c48400d5573695d217101806b8481e39aec38fd5382e64b85f999b4cee42c498', 'note10/device_test/test_sha256_stream_state.py': '088881f92037a9895b7947eb44692f51ecba1eb602a02dacc02ff3b94a836db8'}


# Exact accepted v82 host22, frozen before DATA host changes.
V82_HOST_HEAD = 'b42228737b77f4ce1b24aa8333f03cf31190f026'
V82_HOST_PINS = {'note10/device_test/affinity_binding.py': '6d5b16d54a803c95bdd391a38efbd2bac5ef36baffe199f86cd83f878bf10678', 'note10/device_test/auto_cycle.py': '36793ff1964331b3a77b530fc1be5923d1807a3752ab0f7d4f68a51adde12812', 'note10/device_test/build_boot_test_packages.py': 'cce6403a24fbe38fb2d7b143ff441cd540177b59424cb1445940d2d94de90d5b', 'note10/device_test/builtin_init_profile.py': 'da6878e62f7dbce6fcd1d582efab2ab87cb16164cf8393c401ed0073e09155d4', 'note10/device_test/builtin_init_route.py': '46b100dc95f11e344c11b8cb3fba5d34d17b2884385923426a42246699fda43d', 'note10/device_test/early_fdt_binding.py': 'd4f7099fb45eca31c83c9acd9fbfe0cd5c7ccc5c271c18180e3672e22f9a6b78', 'note10/device_test/materialize_auto_cycle.py': '87ef3da2e0ddbbb40b02bc9334c59deb8c590692352f099cb2b3ae99b749f960', 'note10/device_test/native_memory_observation.py': 'f4acd0f310989bfcd1b0c2039fef6e429e8ec4d4f41ebdb94fc483538fa26663', 'note10/device_test/prepare_linux_boot.py': '4f599c7c667e3dc18a5afccfd682c47f705ed714daa916b4c0557db9f7f78c70', 'note10/device_test/sha256_kat_device_profile.py': '6136f0bb2fd2846091d321e71d71d9e9efc30717d5bb78f2bc2f1b7949334178', 'note10/device_test/sha256_stream_state.py': '55de2735fb830ae8047bb4a8fa74325f51b766b1e885c482dbbc5ebabe3ea437', 'note10/device_test/sha256_stream_vectors.json': '5c379d1ef41a40b9a1262c985476e9dc0ba88dae7b1586f949bbe79686f2165f', 'note10/device_test/stage_phase2.py': '1ecc741d7517fc15a6043b1329b726e420791f06e712bfd1aaf901a7747db433', 'note10/device_test/test_affinity_binding.py': 'bf602887c4437e0096473392789da33e3ef502297d8c060faf7d9da9ecd3eb89', 'note10/device_test/test_affinity_ci_context.py': '71aad30ab105a45efe2703fd7b222233836d6e7514560834daa71bfdd351dea9', 'note10/device_test/test_builtin_init_route.py': '9fa63dd55114472a748062447dd95c17bf4d4d7e743117f69f0bb6a7aca6ea42', 'note10/device_test/test_early_fdt_binding.py': '2444d3d20b7cc42e705cb89c1d04de72599f7da2a5d1b9282636f3b9990ce1fa', 'note10/device_test/test_early_fdt_host_route.py': '75992eb3e8b1228d0ae3916d47306f0329b7947cb0dfae234ec25c1e737fef6a', 'note10/device_test/test_native_memory_observation.py': 'd34e94fd5d964004c42dedd172ec07bd62826b675dcc9f4925ab4ac06c460599', 'note10/device_test/test_partition_gate_evidence.py': 'b7dd52aa5c7747489a2713f805dbe15a6318f3d3776a8043700549e9383bcc72', 'note10/device_test/test_sha256_kat_device_profile.py': 'c48400d5573695d217101806b8481e39aec38fd5382e64b85f999b4cee42c498', 'note10/device_test/test_sha256_stream_state.py': '088881f92037a9895b7947eb44692f51ecba1eb602a02dacc02ff3b94a836db8'}


# Exact accepted v88 DATA host29; current predecessor only, never replayed.
V88_HOST_HEAD = '1b18b5045c0e695e271329505634ccfdddfc808d'
V88_HOST_PINS = {'note10/device_test/affinity_binding.py': '6d5b16d54a803c95bdd391a38efbd2bac5ef36baffe199f86cd83f878bf10678', 'note10/device_test/auto_cycle.py': '36793ff1964331b3a77b530fc1be5923d1807a3752ab0f7d4f68a51adde12812', 'note10/device_test/build_boot_test_packages.py': '17b973f54185521be6685acb5e019f8bf8b5f10897d01c0167929c97859cddef', 'note10/device_test/builtin_init_profile.py': 'cfd39e4e5c548581ab824fd34c745fe64e68329d4c5c8b163ac442e20141f851', 'note10/device_test/builtin_init_route.py': '46b100dc95f11e344c11b8cb3fba5d34d17b2884385923426a42246699fda43d', 'note10/device_test/carrier_lzma.c': 'e204732754f15929f7134885ec2740e1ed26f0291dd64c7df7957a4aee7b987a', 'note10/device_test/carrier_lzma.h': '6790aa17da94025e0bab175377573edb8df3f503c8cde86f8c919e33ee742974', 'note10/device_test/early_fdt_binding.py': 'd4f7099fb45eca31c83c9acd9fbfe0cd5c7ccc5c271c18180e3672e22f9a6b78', 'note10/device_test/linux_data_carrier.c': '57115ab06acc11d43098b29e6ee37e4568dc21e720bd979923101598896c4bb0', 'note10/device_test/linux_data_carrier.py': '9da8ce25e1ff753a87ea9bbb8d42f3e99c832dd510869358ddebcb99820277fc', 'note10/device_test/linux_data_carrier_composition.c': '3d8bfdda62368e4ef4cf5461b5aa6a6bc1a6000aafa65edcadbd37f0723749c1', 'note10/device_test/linux_data_carrier_fixture.c': 'add9e91147ff149663f0aae819fb63aa3d59c343b21bdb934bee57684d81d2c2', 'note10/device_test/materialize_auto_cycle.py': '87ef3da2e0ddbbb40b02bc9334c59deb8c590692352f099cb2b3ae99b749f960', 'note10/device_test/native_memory_observation.py': 'f4acd0f310989bfcd1b0c2039fef6e429e8ec4d4f41ebdb94fc483538fa26663', 'note10/device_test/prepare_linux_boot.py': '53deae85bc3b3a4803d96fd02f346c5a386748b732d9844e89950fefac811128', 'note10/device_test/sha256_kat_device_profile.py': '23aacdb660db38d863d323c126736ac98be755e5b55aac62396af6b21d652927', 'note10/device_test/sha256_stream_state.py': '55de2735fb830ae8047bb4a8fa74325f51b766b1e885c482dbbc5ebabe3ea437', 'note10/device_test/sha256_stream_vectors.json': '5c379d1ef41a40b9a1262c985476e9dc0ba88dae7b1586f949bbe79686f2165f', 'note10/device_test/stage_phase2.py': '1ecc741d7517fc15a6043b1329b726e420791f06e712bfd1aaf901a7747db433', 'note10/device_test/test_affinity_binding.py': 'bf602887c4437e0096473392789da33e3ef502297d8c060faf7d9da9ecd3eb89', 'note10/device_test/test_affinity_ci_context.py': '71aad30ab105a45efe2703fd7b222233836d6e7514560834daa71bfdd351dea9', 'note10/device_test/test_builtin_init_route.py': '9fa63dd55114472a748062447dd95c17bf4d4d7e743117f69f0bb6a7aca6ea42', 'note10/device_test/test_early_fdt_binding.py': '2444d3d20b7cc42e705cb89c1d04de72599f7da2a5d1b9282636f3b9990ce1fa', 'note10/device_test/test_early_fdt_host_route.py': '75992eb3e8b1228d0ae3916d47306f0329b7947cb0dfae234ec25c1e737fef6a', 'note10/device_test/test_linux_data_carrier.py': '224cf5a878a755d9c547d6083aa2663dbb7c065af5188aebf7dc874bcc0d5a21', 'note10/device_test/test_native_memory_observation.py': 'd34e94fd5d964004c42dedd172ec07bd62826b675dcc9f4925ab4ac06c460599', 'note10/device_test/test_partition_gate_evidence.py': 'b7dd52aa5c7747489a2713f805dbe15a6318f3d3776a8043700549e9383bcc72', 'note10/device_test/test_sha256_kat_device_profile.py': 'c48400d5573695d217101806b8481e39aec38fd5382e64b85f999b4cee42c498', 'note10/device_test/test_sha256_stream_state.py': '088881f92037a9895b7947eb44692f51ecba1eb602a02dacc02ff3b94a836db8'}


# Exact accepted v89 DATA host closure, frozen before Image-slot mode.
V89_IMAGE_HEAD = 'aebe2bd4f683d9c4bc3d11892ce00fa100b4c22d'
V89_HOST_HEAD = 'aebe2bd4f683d9c4bc3d11892ce00fa100b4c22d'
V89_HOST_PINS = {'note10/device_test/affinity_binding.py': '6d5b16d54a803c95bdd391a38efbd2bac5ef36baffe199f86cd83f878bf10678', 'note10/device_test/auto_cycle.py': '36793ff1964331b3a77b530fc1be5923d1807a3752ab0f7d4f68a51adde12812', 'note10/device_test/build_boot_test_packages.py': '17b973f54185521be6685acb5e019f8bf8b5f10897d01c0167929c97859cddef', 'note10/device_test/builtin_init_profile.py': 'e3117fecc38b57827be1aea93e85f3226139f23a80a07ad2668d3a0431da7610', 'note10/device_test/builtin_init_route.py': '46b100dc95f11e344c11b8cb3fba5d34d17b2884385923426a42246699fda43d', 'note10/device_test/carrier_lzma.c': 'e204732754f15929f7134885ec2740e1ed26f0291dd64c7df7957a4aee7b987a', 'note10/device_test/carrier_lzma.h': '6790aa17da94025e0bab175377573edb8df3f503c8cde86f8c919e33ee742974', 'note10/device_test/early_fdt_binding.py': 'd4f7099fb45eca31c83c9acd9fbfe0cd5c7ccc5c271c18180e3672e22f9a6b78', 'note10/device_test/linux_data_carrier.c': '75bb02bb8ec1e2c5db6d74bb35ec94d29eb87711ae2362a38c3418169b382ce4', 'note10/device_test/linux_data_carrier.py': '015a1ad2ab475e3020ea1378d6cae9df7e5765ccc822701f09494970fea7804e', 'note10/device_test/linux_data_carrier_composition.c': '3d8bfdda62368e4ef4cf5461b5aa6a6bc1a6000aafa65edcadbd37f0723749c1', 'note10/device_test/linux_data_carrier_fixture.c': '963137346e2f02e9eb6c1379d22b7edd0cabe0b3c2a6e3f4b0cf3502353e2565', 'note10/device_test/materialize_auto_cycle.py': '87ef3da2e0ddbbb40b02bc9334c59deb8c590692352f099cb2b3ae99b749f960', 'note10/device_test/native_memory_observation.py': 'f4acd0f310989bfcd1b0c2039fef6e429e8ec4d4f41ebdb94fc483538fa26663', 'note10/device_test/prepare_linux_boot.py': '53deae85bc3b3a4803d96fd02f346c5a386748b732d9844e89950fefac811128', 'note10/device_test/sha256_kat_device_profile.py': '27f461e981fe8ff06a8550808c3bd94b04660f555c7a6fd2b1a2cf8742eaa4a7', 'note10/device_test/sha256_stream_state.py': '55de2735fb830ae8047bb4a8fa74325f51b766b1e885c482dbbc5ebabe3ea437', 'note10/device_test/sha256_stream_vectors.json': '5c379d1ef41a40b9a1262c985476e9dc0ba88dae7b1586f949bbe79686f2165f', 'note10/device_test/stage_phase2.py': '1ecc741d7517fc15a6043b1329b726e420791f06e712bfd1aaf901a7747db433', 'note10/device_test/test_affinity_binding.py': 'bf602887c4437e0096473392789da33e3ef502297d8c060faf7d9da9ecd3eb89', 'note10/device_test/test_affinity_ci_context.py': '71aad30ab105a45efe2703fd7b222233836d6e7514560834daa71bfdd351dea9', 'note10/device_test/test_builtin_init_route.py': '9fa63dd55114472a748062447dd95c17bf4d4d7e743117f69f0bb6a7aca6ea42', 'note10/device_test/test_early_fdt_binding.py': '2444d3d20b7cc42e705cb89c1d04de72599f7da2a5d1b9282636f3b9990ce1fa', 'note10/device_test/test_early_fdt_host_route.py': '75992eb3e8b1228d0ae3916d47306f0329b7947cb0dfae234ec25c1e737fef6a', 'note10/device_test/test_linux_data_carrier.py': '8b193fde3fd3bd63b4ed805ae6f2ab0359904c86d1e9f87c7efc6c73fb577de8', 'note10/device_test/test_native_memory_observation.py': 'd34e94fd5d964004c42dedd172ec07bd62826b675dcc9f4925ab4ac06c460599', 'note10/device_test/test_partition_gate_evidence.py': 'b7dd52aa5c7747489a2713f805dbe15a6318f3d3776a8043700549e9383bcc72', 'note10/device_test/test_sha256_kat_device_profile.py': 'c48400d5573695d217101806b8481e39aec38fd5382e64b85f999b4cee42c498', 'note10/device_test/test_sha256_stream_state.py': '088881f92037a9895b7947eb44692f51ecba1eb602a02dacc02ff3b94a836db8'}


V90_IMAGE_HEAD = '59bfd8d9f21047c9d943cd0dd4f4eb96fb5459e9'
V90_HOST_HEAD = '59bfd8d9f21047c9d943cd0dd4f4eb96fb5459e9'
V90_HOST_PINS = {'note10/device_test/affinity_binding.py': '6d5b16d54a803c95bdd391a38efbd2bac5ef36baffe199f86cd83f878bf10678', 'note10/device_test/auto_cycle.py': '36793ff1964331b3a77b530fc1be5923d1807a3752ab0f7d4f68a51adde12812', 'note10/device_test/build_boot_test_packages.py': '17b973f54185521be6685acb5e019f8bf8b5f10897d01c0167929c97859cddef', 'note10/device_test/builtin_init_profile.py': '824f2a5276644d93492cc11907780359bd03b6ff4bf2c6a91682b06b375ce683', 'note10/device_test/builtin_init_route.py': '46b100dc95f11e344c11b8cb3fba5d34d17b2884385923426a42246699fda43d', 'note10/device_test/carrier_lzma.c': 'e204732754f15929f7134885ec2740e1ed26f0291dd64c7df7957a4aee7b987a', 'note10/device_test/carrier_lzma.h': '6790aa17da94025e0bab175377573edb8df3f503c8cde86f8c919e33ee742974', 'note10/device_test/early_fdt_binding.py': 'd4f7099fb45eca31c83c9acd9fbfe0cd5c7ccc5c271c18180e3672e22f9a6b78', 'note10/device_test/linux_data_carrier.c': '4e149a7f35ab631cd467c4f1b0adfccfeea498ab5399bcaa8c3bf17b0b287238', 'note10/device_test/linux_data_carrier.py': 'dce66a8f94e583ffd1e0e3af4ae50cd3351563129e87a19a0121697f346dfbca', 'note10/device_test/linux_data_carrier_composition.c': '8fb8f040f1d003b96336f15f5adbab92d7ee0654276e00361f37b0d37036ec5d', 'note10/device_test/linux_data_carrier_fixture.c': '06dafec2839f03aec2b4b07a56f8a2462a982781385da32ef844c0cc0d7df8dd', 'note10/device_test/materialize_auto_cycle.py': 'ca9bb27f8cf08fc61d2a7ea677e63edb620a99119c2ead871ebae2c29ac8c289', 'note10/device_test/native_memory_observation.py': 'f4acd0f310989bfcd1b0c2039fef6e429e8ec4d4f41ebdb94fc483538fa26663', 'note10/device_test/prepare_linux_boot.py': '53deae85bc3b3a4803d96fd02f346c5a386748b732d9844e89950fefac811128', 'note10/device_test/sha256_kat_device_profile.py': 'a258270ff738fed28c6aff672ec3b89cfdbca0b7f362084afbafd177c8ddc077', 'note10/device_test/sha256_stream_state.py': '55de2735fb830ae8047bb4a8fa74325f51b766b1e885c482dbbc5ebabe3ea437', 'note10/device_test/sha256_stream_vectors.json': '5c379d1ef41a40b9a1262c985476e9dc0ba88dae7b1586f949bbe79686f2165f', 'note10/device_test/stage_phase2.py': '1ecc741d7517fc15a6043b1329b726e420791f06e712bfd1aaf901a7747db433', 'note10/device_test/test_affinity_binding.py': 'bf602887c4437e0096473392789da33e3ef502297d8c060faf7d9da9ecd3eb89', 'note10/device_test/test_affinity_ci_context.py': '71aad30ab105a45efe2703fd7b222233836d6e7514560834daa71bfdd351dea9', 'note10/device_test/test_builtin_init_route.py': '9fa63dd55114472a748062447dd95c17bf4d4d7e743117f69f0bb6a7aca6ea42', 'note10/device_test/test_early_fdt_binding.py': '2444d3d20b7cc42e705cb89c1d04de72599f7da2a5d1b9282636f3b9990ce1fa', 'note10/device_test/test_early_fdt_host_route.py': '75992eb3e8b1228d0ae3916d47306f0329b7947cb0dfae234ec25c1e737fef6a', 'note10/device_test/test_linux_data_carrier.py': '05d666305939a65d75a551957ca19a7961f39bfff044d81a26b6b7e410ea85df', 'note10/device_test/test_native_memory_observation.py': 'd34e94fd5d964004c42dedd172ec07bd62826b675dcc9f4925ab4ac06c460599', 'note10/device_test/test_partition_gate_evidence.py': 'b7dd52aa5c7747489a2713f805dbe15a6318f3d3776a8043700549e9383bcc72', 'note10/device_test/test_sha256_kat_device_profile.py': 'c48400d5573695d217101806b8481e39aec38fd5382e64b85f999b4cee42c498', 'note10/device_test/test_sha256_stream_state.py': '088881f92037a9895b7947eb44692f51ecba1eb602a02dacc02ff3b94a836db8'}


V91_IMAGE_HEAD = '0696b4dbf157a2d51b68b26e4a5237a7c51daa80'
V91_HOST_HEAD = '0696b4dbf157a2d51b68b26e4a5237a7c51daa80'
V91_HOST_PINS = {'note10/device_test/affinity_binding.py': '6d5b16d54a803c95bdd391a38efbd2bac5ef36baffe199f86cd83f878bf10678', 'note10/device_test/auto_cycle.py': '36793ff1964331b3a77b530fc1be5923d1807a3752ab0f7d4f68a51adde12812', 'note10/device_test/build_boot_test_packages.py': '17b973f54185521be6685acb5e019f8bf8b5f10897d01c0167929c97859cddef', 'note10/device_test/builtin_init_profile.py': '2f286f36b375a0a963c2cb892b6416df860598d9dc293391d124947e840cfc4f', 'note10/device_test/builtin_init_route.py': '46b100dc95f11e344c11b8cb3fba5d34d17b2884385923426a42246699fda43d', 'note10/device_test/carrier_lzma.c': 'e204732754f15929f7134885ec2740e1ed26f0291dd64c7df7957a4aee7b987a', 'note10/device_test/carrier_lzma.h': '6790aa17da94025e0bab175377573edb8df3f503c8cde86f8c919e33ee742974', 'note10/device_test/early_fdt_binding.py': 'd4f7099fb45eca31c83c9acd9fbfe0cd5c7ccc5c271c18180e3672e22f9a6b78', 'note10/device_test/linux_data_carrier.c': '06ef63a916cf1dc041668db83bc1bb8fce9dd8f73ad72e33be72b6ef10f9177a', 'note10/device_test/linux_data_carrier.py': 'ea3e57f7217494b641df7879c41d12d8e5b9bcbcf285f274c0fbc4855e7b3b4b', 'note10/device_test/linux_data_carrier_composition.c': '8fb8f040f1d003b96336f15f5adbab92d7ee0654276e00361f37b0d37036ec5d', 'note10/device_test/linux_data_carrier_fixture.c': '354bfeae658b89b079295bcc5e546bfac3e22503b50c1a8cf408c0005a109606', 'note10/device_test/materialize_auto_cycle.py': 'ca9bb27f8cf08fc61d2a7ea677e63edb620a99119c2ead871ebae2c29ac8c289', 'note10/device_test/native_memory_observation.py': 'f4acd0f310989bfcd1b0c2039fef6e429e8ec4d4f41ebdb94fc483538fa26663', 'note10/device_test/prepare_linux_boot.py': '2dc0ddd51a68f3da30f58df6243bbc33d441a296bd141cc6b9da5dc7fa10b604', 'note10/device_test/sha256_kat_device_profile.py': '9e859969d78fd2a9768996fef1b459463cf9a7e3abadcfe963eb9ac9ec0272f1', 'note10/device_test/sha256_stream_state.py': '55de2735fb830ae8047bb4a8fa74325f51b766b1e885c482dbbc5ebabe3ea437', 'note10/device_test/sha256_stream_vectors.json': '5c379d1ef41a40b9a1262c985476e9dc0ba88dae7b1586f949bbe79686f2165f', 'note10/device_test/stage_phase2.py': '1ecc741d7517fc15a6043b1329b726e420791f06e712bfd1aaf901a7747db433', 'note10/device_test/test_affinity_binding.py': 'bf602887c4437e0096473392789da33e3ef502297d8c060faf7d9da9ecd3eb89', 'note10/device_test/test_affinity_ci_context.py': '71aad30ab105a45efe2703fd7b222233836d6e7514560834daa71bfdd351dea9', 'note10/device_test/test_builtin_init_route.py': '9fa63dd55114472a748062447dd95c17bf4d4d7e743117f69f0bb6a7aca6ea42', 'note10/device_test/test_early_fdt_binding.py': '2444d3d20b7cc42e705cb89c1d04de72599f7da2a5d1b9282636f3b9990ce1fa', 'note10/device_test/test_early_fdt_host_route.py': '75992eb3e8b1228d0ae3916d47306f0329b7947cb0dfae234ec25c1e737fef6a', 'note10/device_test/test_linux_data_carrier.py': '550344e818b42f8147ea1f688929feda322c68173f79f6e72850053dbc2e1ca7', 'note10/device_test/test_native_memory_observation.py': 'd34e94fd5d964004c42dedd172ec07bd62826b675dcc9f4925ab4ac06c460599', 'note10/device_test/test_partition_gate_evidence.py': 'b7dd52aa5c7747489a2713f805dbe15a6318f3d3776a8043700549e9383bcc72', 'note10/device_test/test_sha256_kat_device_profile.py': 'c48400d5573695d217101806b8481e39aec38fd5382e64b85f999b4cee42c498', 'note10/device_test/test_sha256_stream_state.py': '088881f92037a9895b7947eb44692f51ecba1eb602a02dacc02ff3b94a836db8'}


# Published profile-origin snapshots. Read-side identity only; never executing-host claims.
V97_PROFILE_ORIGIN_HEAD = 'bdd56f101e3e9bb83ecbadad03be24473f143447'
V97_PROFILE_ORIGIN_PINS = MappingProxyType({
    "note10/device_test/affinity_binding.py": "6d5b16d54a803c95bdd391a38efbd2bac5ef36baffe199f86cd83f878bf10678",
    "note10/device_test/auto_cycle.py": "36793ff1964331b3a77b530fc1be5923d1807a3752ab0f7d4f68a51adde12812",
    "note10/device_test/build_boot_test_packages.py": "17b973f54185521be6685acb5e019f8bf8b5f10897d01c0167929c97859cddef",
    "note10/device_test/builtin_init_profile.py": "34cdd8e2c425140b738026ef44269f5b3c61f775df0f06e2af08b18b6a219286",
    "note10/device_test/builtin_init_route.py": "46b100dc95f11e344c11b8cb3fba5d34d17b2884385923426a42246699fda43d",
    "note10/device_test/carrier_lzma.c": "e204732754f15929f7134885ec2740e1ed26f0291dd64c7df7957a4aee7b987a",
    "note10/device_test/carrier_lzma.h": "6790aa17da94025e0bab175377573edb8df3f503c8cde86f8c919e33ee742974",
    "note10/device_test/current_data_reuse.py": "15c7a5a55e22f4445c216904769d7ba9b6367f792122e5b936305c95ae031129",
    "note10/device_test/early_fdt_binding.py": "d4f7099fb45eca31c83c9acd9fbfe0cd5c7ccc5c271c18180e3672e22f9a6b78",
    "note10/device_test/linux_data_carrier.c": "76fe40b296d68964d4585ee458b518a3ec7fdd512a7d9e15cfc4f2997a08d76f",
    "note10/device_test/linux_data_carrier.py": "916e2b54d7321229437d3fa53558babef60cd2f8be624c374ab39a15498b5fad",
    "note10/device_test/linux_data_carrier_composition.c": "8fb8f040f1d003b96336f15f5adbab92d7ee0654276e00361f37b0d37036ec5d",
    "note10/device_test/linux_data_carrier_fixture.c": "6b1b0e14184582c734a3154eeef6c0e2736fd1b8ef3491881b7decaacb5ecbe4",
    "note10/device_test/materialize_auto_cycle.py": "ca9bb27f8cf08fc61d2a7ea677e63edb620a99119c2ead871ebae2c29ac8c289",
    "note10/device_test/native_memory_observation.py": "f4acd0f310989bfcd1b0c2039fef6e429e8ec4d4f41ebdb94fc483538fa26663",
    "note10/device_test/prepare_linux_boot.py": "2dc0ddd51a68f3da30f58df6243bbc33d441a296bd141cc6b9da5dc7fa10b604",
    "note10/device_test/sha256_kat_device_profile.py": "134255db5e6ea2a4e53213b7ec6bb8bd72eb642309d98b322566a02e6c80ba9a",
    "note10/device_test/sha256_stream_state.py": "55de2735fb830ae8047bb4a8fa74325f51b766b1e885c482dbbc5ebabe3ea437",
    "note10/device_test/sha256_stream_vectors.json": "5c379d1ef41a40b9a1262c985476e9dc0ba88dae7b1586f949bbe79686f2165f",
    "note10/device_test/stage_phase2.py": "1ecc741d7517fc15a6043b1329b726e420791f06e712bfd1aaf901a7747db433",
    "note10/device_test/test_affinity_binding.py": "bf602887c4437e0096473392789da33e3ef502297d8c060faf7d9da9ecd3eb89",
    "note10/device_test/test_affinity_ci_context.py": "71aad30ab105a45efe2703fd7b222233836d6e7514560834daa71bfdd351dea9",
    "note10/device_test/test_builtin_init_route.py": "9fa63dd55114472a748062447dd95c17bf4d4d7e743117f69f0bb6a7aca6ea42",
    "note10/device_test/test_current_data_reuse.py": "c1a868d4f9669539aee3e4fca4868118db37071467325a85d73c279b2f1d29de",
    "note10/device_test/test_early_fdt_binding.py": "2444d3d20b7cc42e705cb89c1d04de72599f7da2a5d1b9282636f3b9990ce1fa",
    "note10/device_test/test_early_fdt_host_route.py": "75992eb3e8b1228d0ae3916d47306f0329b7947cb0dfae234ec25c1e737fef6a",
    "note10/device_test/test_linux_data_carrier.py": "550344e818b42f8147ea1f688929feda322c68173f79f6e72850053dbc2e1ca7",
    "note10/device_test/test_native_memory_observation.py": "d34e94fd5d964004c42dedd172ec07bd62826b675dcc9f4925ab4ac06c460599",
    "note10/device_test/test_partition_gate_evidence.py": "b7dd52aa5c7747489a2713f805dbe15a6318f3d3776a8043700549e9383bcc72",
    "note10/device_test/test_sha256_kat_device_profile.py": "c48400d5573695d217101806b8481e39aec38fd5382e64b85f999b4cee42c498",
    "note10/device_test/test_sha256_stream_state.py": "088881f92037a9895b7947eb44692f51ecba1eb602a02dacc02ff3b94a836db8"
})
V99_PROFILE_ORIGIN_HEAD = '4f9eb149bd116db77eaf3400a25f7454577268a9'
V99_PROFILE_ORIGIN_PINS = MappingProxyType({
    "note10/device_test/affinity_binding.py": "6d5b16d54a803c95bdd391a38efbd2bac5ef36baffe199f86cd83f878bf10678",
    "note10/device_test/auto_cycle.py": "36793ff1964331b3a77b530fc1be5923d1807a3752ab0f7d4f68a51adde12812",
    "note10/device_test/build_boot_test_packages.py": "17b973f54185521be6685acb5e019f8bf8b5f10897d01c0167929c97859cddef",
    "note10/device_test/builtin_init_profile.py": "96e54699f5dc7bf8e603e3f03854592b5c977e7e0d1ebc82fcebcb38ea132477",
    "note10/device_test/builtin_init_route.py": "46b100dc95f11e344c11b8cb3fba5d34d17b2884385923426a42246699fda43d",
    "note10/device_test/carrier_lzma.c": "e204732754f15929f7134885ec2740e1ed26f0291dd64c7df7957a4aee7b987a",
    "note10/device_test/carrier_lzma.h": "6790aa17da94025e0bab175377573edb8df3f503c8cde86f8c919e33ee742974",
    "note10/device_test/current_data_reuse.py": "15c7a5a55e22f4445c216904769d7ba9b6367f792122e5b936305c95ae031129",
    "note10/device_test/early_fdt_binding.py": "d4f7099fb45eca31c83c9acd9fbfe0cd5c7ccc5c271c18180e3672e22f9a6b78",
    "note10/device_test/linux_data_carrier.c": "e308ba2715d4295834bd8fa862cf2b7a1880b0a981e783063f3dd00ee947b900",
    "note10/device_test/linux_data_carrier.py": "57276d2e30761ff725e906b9dde47020c05a6dab52c32a928850fa5cbbb7e00f",
    "note10/device_test/linux_data_carrier_composition.c": "2eb666597983d3a2dfb0a4f98da26dc02dff287db49d39756ada6edc90e0c667",
    "note10/device_test/linux_data_carrier_fixture.c": "6b1b0e14184582c734a3154eeef6c0e2736fd1b8ef3491881b7decaacb5ecbe4",
    "note10/device_test/linux_data_compare_evidence.h": "6863c7ba8fad407d2b6e0323bb823084f4066f98f5265cbe25e728430417eef8",
    "note10/device_test/linux_data_compare_evidence_fixture.c": "45a0cdfd8d4bd8df5ffbbb0e370cd05f768d522e96208881a7f7a02ee02fadc3",
    "note10/device_test/materialize_auto_cycle.py": "ca9bb27f8cf08fc61d2a7ea677e63edb620a99119c2ead871ebae2c29ac8c289",
    "note10/device_test/native_memory_observation.py": "f4acd0f310989bfcd1b0c2039fef6e429e8ec4d4f41ebdb94fc483538fa26663",
    "note10/device_test/prepare_linux_boot.py": "2dc0ddd51a68f3da30f58df6243bbc33d441a296bd141cc6b9da5dc7fa10b604",
    "note10/device_test/sha256_kat_device_profile.py": "28aa67896a91b452b60d0c68902a906851f2253e4223db7d8a6537d657884965",
    "note10/device_test/sha256_stream_state.py": "55de2735fb830ae8047bb4a8fa74325f51b766b1e885c482dbbc5ebabe3ea437",
    "note10/device_test/sha256_stream_vectors.json": "5c379d1ef41a40b9a1262c985476e9dc0ba88dae7b1586f949bbe79686f2165f",
    "note10/device_test/stage_phase2.py": "1ecc741d7517fc15a6043b1329b726e420791f06e712bfd1aaf901a7747db433",
    "note10/device_test/test_affinity_binding.py": "bf602887c4437e0096473392789da33e3ef502297d8c060faf7d9da9ecd3eb89",
    "note10/device_test/test_affinity_ci_context.py": "71aad30ab105a45efe2703fd7b222233836d6e7514560834daa71bfdd351dea9",
    "note10/device_test/test_builtin_init_route.py": "9fa63dd55114472a748062447dd95c17bf4d4d7e743117f69f0bb6a7aca6ea42",
    "note10/device_test/test_current_data_reuse.py": "c1a868d4f9669539aee3e4fca4868118db37071467325a85d73c279b2f1d29de",
    "note10/device_test/test_early_fdt_binding.py": "2444d3d20b7cc42e705cb89c1d04de72599f7da2a5d1b9282636f3b9990ce1fa",
    "note10/device_test/test_early_fdt_host_route.py": "75992eb3e8b1228d0ae3916d47306f0329b7947cb0dfae234ec25c1e737fef6a",
    "note10/device_test/test_linux_data_carrier.py": "550344e818b42f8147ea1f688929feda322c68173f79f6e72850053dbc2e1ca7",
    "note10/device_test/test_native_memory_observation.py": "d34e94fd5d964004c42dedd172ec07bd62826b675dcc9f4925ab4ac06c460599",
    "note10/device_test/test_partition_gate_evidence.py": "b7dd52aa5c7747489a2713f805dbe15a6318f3d3776a8043700549e9383bcc72",
    "note10/device_test/test_sha256_kat_device_profile.py": "c48400d5573695d217101806b8481e39aec38fd5382e64b85f999b4cee42c498",
    "note10/device_test/test_sha256_stream_state.py": "088881f92037a9895b7947eb44692f51ecba1eb602a02dacc02ff3b94a836db8",
    "note10/device_test/test_v99_carrier_compare_evidence.py": "2b45c21197709706d3f3ffc23e1428084d5d50a93a1d9b5bd22c2693124cf20c"
})


V100_PROFILE_ORIGIN_HEAD = '566e0416fa0dcf87e70d556ba3c01e5c2f52b1df'
V100_PROFILE_ORIGIN_PINS = MappingProxyType({
    "note10/device_test/affinity_binding.py": "6d5b16d54a803c95bdd391a38efbd2bac5ef36baffe199f86cd83f878bf10678",
    "note10/device_test/auto_cycle.py": "36793ff1964331b3a77b530fc1be5923d1807a3752ab0f7d4f68a51adde12812",
    "note10/device_test/build_boot_test_packages.py": "17b973f54185521be6685acb5e019f8bf8b5f10897d01c0167929c97859cddef",
    "note10/device_test/builtin_init_profile.py": "74dbbb2941ba85fd755a0ff1c1e9f189e1732335a5db9b711e8121250c6c0b4c",
    "note10/device_test/builtin_init_route.py": "46b100dc95f11e344c11b8cb3fba5d34d17b2884385923426a42246699fda43d",
    "note10/device_test/carrier_lzma.c": "e204732754f15929f7134885ec2740e1ed26f0291dd64c7df7957a4aee7b987a",
    "note10/device_test/carrier_lzma.h": "6790aa17da94025e0bab175377573edb8df3f503c8cde86f8c919e33ee742974",
    "note10/device_test/current_data_reuse.py": "15c7a5a55e22f4445c216904769d7ba9b6367f792122e5b936305c95ae031129",
    "note10/device_test/early_fdt_binding.py": "d4f7099fb45eca31c83c9acd9fbfe0cd5c7ccc5c271c18180e3672e22f9a6b78",
    "note10/device_test/linux_data_carrier.c": "317347c3b8ebbb094a0094daf3b74fe6a4e1c3d284d32bed3fd67a8ef7ac61a5",
    "note10/device_test/linux_data_carrier.py": "d46c28de982baa9658b6e6955392f8492015d6d4f74b222ee5f1d4649742a601",
    "note10/device_test/linux_data_carrier_composition.c": "2eb666597983d3a2dfb0a4f98da26dc02dff287db49d39756ada6edc90e0c667",
    "note10/device_test/linux_data_carrier_fixture.c": "6b1b0e14184582c734a3154eeef6c0e2736fd1b8ef3491881b7decaacb5ecbe4",
    "note10/device_test/linux_data_compare_evidence.h": "3383823cf1fd56f688ad9d6823d965fdda270a08acede17f6df8d87fa6199438",
    "note10/device_test/linux_data_compare_evidence_fixture.c": "45a0cdfd8d4bd8df5ffbbb0e370cd05f768d522e96208881a7f7a02ee02fadc3",
    "note10/device_test/linux_data_input_probe_fixture.c": "c7192b0515eb7de9526291913ef97737207844a45d266a4e1287437f49b3e0b4",
    "note10/device_test/materialize_auto_cycle.py": "ca9bb27f8cf08fc61d2a7ea677e63edb620a99119c2ead871ebae2c29ac8c289",
    "note10/device_test/native_memory_observation.py": "f4acd0f310989bfcd1b0c2039fef6e429e8ec4d4f41ebdb94fc483538fa26663",
    "note10/device_test/prepare_linux_boot.py": "2dc0ddd51a68f3da30f58df6243bbc33d441a296bd141cc6b9da5dc7fa10b604",
    "note10/device_test/sha256_kat_device_profile.py": "c2e1a4b7eb6d003889648b1ec33f64052205ed59d616010aa67c5161f1de6d78",
    "note10/device_test/sha256_stream_state.py": "55de2735fb830ae8047bb4a8fa74325f51b766b1e885c482dbbc5ebabe3ea437",
    "note10/device_test/sha256_stream_vectors.json": "5c379d1ef41a40b9a1262c985476e9dc0ba88dae7b1586f949bbe79686f2165f",
    "note10/device_test/stage_phase2.py": "1ecc741d7517fc15a6043b1329b726e420791f06e712bfd1aaf901a7747db433",
    "note10/device_test/test_affinity_binding.py": "bf602887c4437e0096473392789da33e3ef502297d8c060faf7d9da9ecd3eb89",
    "note10/device_test/test_affinity_ci_context.py": "71aad30ab105a45efe2703fd7b222233836d6e7514560834daa71bfdd351dea9",
    "note10/device_test/test_builtin_init_route.py": "9fa63dd55114472a748062447dd95c17bf4d4d7e743117f69f0bb6a7aca6ea42",
    "note10/device_test/test_current_data_reuse.py": "c1a868d4f9669539aee3e4fca4868118db37071467325a85d73c279b2f1d29de",
    "note10/device_test/test_early_fdt_binding.py": "2444d3d20b7cc42e705cb89c1d04de72599f7da2a5d1b9282636f3b9990ce1fa",
    "note10/device_test/test_early_fdt_host_route.py": "75992eb3e8b1228d0ae3916d47306f0329b7947cb0dfae234ec25c1e737fef6a",
    "note10/device_test/test_linux_data_carrier.py": "550344e818b42f8147ea1f688929feda322c68173f79f6e72850053dbc2e1ca7",
    "note10/device_test/test_native_memory_observation.py": "d34e94fd5d964004c42dedd172ec07bd62826b675dcc9f4925ab4ac06c460599",
    "note10/device_test/test_partition_gate_evidence.py": "b7dd52aa5c7747489a2713f805dbe15a6318f3d3776a8043700549e9383bcc72",
    "note10/device_test/test_sha256_kat_device_profile.py": "c48400d5573695d217101806b8481e39aec38fd5382e64b85f999b4cee42c498",
    "note10/device_test/test_sha256_stream_state.py": "088881f92037a9895b7947eb44692f51ecba1eb602a02dacc02ff3b94a836db8",
    "note10/device_test/test_v100_carrier_input_probe.py": "f8e37cb2da1fc1efda5582079bb619d8853565d892a589872d0699277e8c4489",
    "note10/device_test/test_v99_carrier_compare_evidence.py": "2b45c21197709706d3f3ffc23e1428084d5d50a93a1d9b5bd22c2693124cf20c",
    "note10/device_test/test_v99_host_profile_origin.py": "fb4a1c349ca298b4f18ba64e0692c7a93e9f0877b2f7a7ec22fa2c8f29ac219a"
})


V101_PROFILE_ORIGIN_HEAD = '2c4ba27332fde3e0e8789911ca8b2edf9a75f51a'
V101_PROFILE_ORIGIN_PINS = MappingProxyType({
    "note10/device_test/affinity_binding.py": "6d5b16d54a803c95bdd391a38efbd2bac5ef36baffe199f86cd83f878bf10678",
    "note10/device_test/auto_cycle.py": "36793ff1964331b3a77b530fc1be5923d1807a3752ab0f7d4f68a51adde12812",
    "note10/device_test/build_boot_test_packages.py": "17b973f54185521be6685acb5e019f8bf8b5f10897d01c0167929c97859cddef",
    "note10/device_test/builtin_init_profile.py": "15c95c4ba10a19e9b8382d7f85dc12141584f9a1c946e727cffd448ca221b254",
    "note10/device_test/builtin_init_route.py": "46b100dc95f11e344c11b8cb3fba5d34d17b2884385923426a42246699fda43d",
    "note10/device_test/carrier_lzma.c": "e204732754f15929f7134885ec2740e1ed26f0291dd64c7df7957a4aee7b987a",
    "note10/device_test/carrier_lzma.h": "6790aa17da94025e0bab175377573edb8df3f503c8cde86f8c919e33ee742974",
    "note10/device_test/current_data_reuse.py": "15c7a5a55e22f4445c216904769d7ba9b6367f792122e5b936305c95ae031129",
    "note10/device_test/early_fdt_binding.py": "d4f7099fb45eca31c83c9acd9fbfe0cd5c7ccc5c271c18180e3672e22f9a6b78",
    "note10/device_test/linux_data_carrier.c": "e0ff70fca3282fdcb2f59422163f6948a3f233426c7de9108a4c245a508b875a",
    "note10/device_test/linux_data_carrier.py": "a94518ff4cea08464a5f1c0e11ea503c98f647e627693d41998276ceef98f8cd",
    "note10/device_test/linux_data_carrier_composition.c": "2eb666597983d3a2dfb0a4f98da26dc02dff287db49d39756ada6edc90e0c667",
    "note10/device_test/linux_data_carrier_fixture.c": "6b1b0e14184582c734a3154eeef6c0e2736fd1b8ef3491881b7decaacb5ecbe4",
    "note10/device_test/linux_data_compare_evidence.h": "3383823cf1fd56f688ad9d6823d965fdda270a08acede17f6df8d87fa6199438",
    "note10/device_test/linux_data_compare_evidence_fixture.c": "45a0cdfd8d4bd8df5ffbbb0e370cd05f768d522e96208881a7f7a02ee02fadc3",
    "note10/device_test/linux_data_input_probe_fixture.c": "c7192b0515eb7de9526291913ef97737207844a45d266a4e1287437f49b3e0b4",
    "note10/device_test/linux_data_input_range.h": "c53f208c886ba21af0f22d266a1edb1de0f42a3e40d5a68080a41fcf775d4dac",
    "note10/device_test/linux_data_input_range_fixture.c": "d3c7695b319963b9d6de679a5eadaf107c4dc667e610b892f2953a390854ecd5",
    "note10/device_test/materialize_auto_cycle.py": "ca9bb27f8cf08fc61d2a7ea677e63edb620a99119c2ead871ebae2c29ac8c289",
    "note10/device_test/native_memory_observation.py": "f4acd0f310989bfcd1b0c2039fef6e429e8ec4d4f41ebdb94fc483538fa26663",
    "note10/device_test/prepare_linux_boot.py": "2dc0ddd51a68f3da30f58df6243bbc33d441a296bd141cc6b9da5dc7fa10b604",
    "note10/device_test/sha256_kat_device_profile.py": "0a28a786b9872d940886827771e642a571346217a9c636e8be8e5efdc2e2fd1b",
    "note10/device_test/sha256_stream_state.py": "55de2735fb830ae8047bb4a8fa74325f51b766b1e885c482dbbc5ebabe3ea437",
    "note10/device_test/sha256_stream_vectors.json": "5c379d1ef41a40b9a1262c985476e9dc0ba88dae7b1586f949bbe79686f2165f",
    "note10/device_test/stage_phase2.py": "1ecc741d7517fc15a6043b1329b726e420791f06e712bfd1aaf901a7747db433",
    "note10/device_test/test_affinity_binding.py": "bf602887c4437e0096473392789da33e3ef502297d8c060faf7d9da9ecd3eb89",
    "note10/device_test/test_affinity_ci_context.py": "71aad30ab105a45efe2703fd7b222233836d6e7514560834daa71bfdd351dea9",
    "note10/device_test/test_builtin_init_route.py": "9fa63dd55114472a748062447dd95c17bf4d4d7e743117f69f0bb6a7aca6ea42",
    "note10/device_test/test_current_data_reuse.py": "c1a868d4f9669539aee3e4fca4868118db37071467325a85d73c279b2f1d29de",
    "note10/device_test/test_early_fdt_binding.py": "2444d3d20b7cc42e705cb89c1d04de72599f7da2a5d1b9282636f3b9990ce1fa",
    "note10/device_test/test_early_fdt_host_route.py": "75992eb3e8b1228d0ae3916d47306f0329b7947cb0dfae234ec25c1e737fef6a",
    "note10/device_test/test_linux_data_carrier.py": "550344e818b42f8147ea1f688929feda322c68173f79f6e72850053dbc2e1ca7",
    "note10/device_test/test_native_memory_observation.py": "d34e94fd5d964004c42dedd172ec07bd62826b675dcc9f4925ab4ac06c460599",
    "note10/device_test/test_partition_gate_evidence.py": "b7dd52aa5c7747489a2713f805dbe15a6318f3d3776a8043700549e9383bcc72",
    "note10/device_test/test_sha256_kat_device_profile.py": "c48400d5573695d217101806b8481e39aec38fd5382e64b85f999b4cee42c498",
    "note10/device_test/test_sha256_stream_state.py": "088881f92037a9895b7947eb44692f51ecba1eb602a02dacc02ff3b94a836db8",
    "note10/device_test/test_v100_carrier_input_probe.py": "f8e37cb2da1fc1efda5582079bb619d8853565d892a589872d0699277e8c4489",
    "note10/device_test/test_v101_live_input_range.py": "e4424b6128a18f4099b31ddc6dcf16ba6256749ba2a87f8bd565b68a1ef68183",
    "note10/device_test/test_v99_carrier_compare_evidence.py": "2b45c21197709706d3f3ffc23e1428084d5d50a93a1d9b5bd22c2693124cf20c",
    "note10/device_test/test_v99_host_profile_origin.py": "fb4a1c349ca298b4f18ba64e0692c7a93e9f0877b2f7a7ec22fa2c8f29ac219a"
})


V102_PROFILE_ORIGIN_HEAD = '27ae68950c208e4b9bafb7f12540a131dcabcccc'
V102_PROFILE_ORIGIN_PINS = MappingProxyType({
    "note10/device_test/affinity_binding.py": "6d5b16d54a803c95bdd391a38efbd2bac5ef36baffe199f86cd83f878bf10678",
    "note10/device_test/auto_cycle.py": "36793ff1964331b3a77b530fc1be5923d1807a3752ab0f7d4f68a51adde12812",
    "note10/device_test/build_boot_test_packages.py": "17b973f54185521be6685acb5e019f8bf8b5f10897d01c0167929c97859cddef",
    "note10/device_test/builtin_init_profile.py": "320d51ccf8062de6b97e7627297666a24535843e77b3ebf23619ae158672a5f2",
    "note10/device_test/builtin_init_route.py": "46b100dc95f11e344c11b8cb3fba5d34d17b2884385923426a42246699fda43d",
    "note10/device_test/carrier_lzma.c": "e204732754f15929f7134885ec2740e1ed26f0291dd64c7df7957a4aee7b987a",
    "note10/device_test/carrier_lzma.h": "6790aa17da94025e0bab175377573edb8df3f503c8cde86f8c919e33ee742974",
    "note10/device_test/current_data_reuse.py": "15c7a5a55e22f4445c216904769d7ba9b6367f792122e5b936305c95ae031129",
    "note10/device_test/early_fdt_binding.py": "d4f7099fb45eca31c83c9acd9fbfe0cd5c7ccc5c271c18180e3672e22f9a6b78",
    "note10/device_test/linux_data_carrier.c": "0df1b8e07e6d4058c17b656b3b481d1ea411ed6ee61647ce4ba0935b8243a836",
    "note10/device_test/linux_data_carrier.py": "da76dd7374a493926784942da4a3b2803722f97eb24242ab85b1dd0f1147107b",
    "note10/device_test/linux_data_carrier_composition.c": "2eb666597983d3a2dfb0a4f98da26dc02dff287db49d39756ada6edc90e0c667",
    "note10/device_test/linux_data_carrier_fixture.c": "6b1b0e14184582c734a3154eeef6c0e2736fd1b8ef3491881b7decaacb5ecbe4",
    "note10/device_test/linux_data_compare_evidence.h": "3383823cf1fd56f688ad9d6823d965fdda270a08acede17f6df8d87fa6199438",
    "note10/device_test/linux_data_compare_evidence_fixture.c": "45a0cdfd8d4bd8df5ffbbb0e370cd05f768d522e96208881a7f7a02ee02fadc3",
    "note10/device_test/linux_data_early_prefix.h": "60fb29d56be78212e04cc164938db4a25296fdea5250e372824b317127aaeb98",
    "note10/device_test/linux_data_early_prefix_fixture.c": "b058ccfa33fccadfa2547986a724b21dd7de0b781e003cd3ca1c71fddfe36f09",
    "note10/device_test/linux_data_input_probe_fixture.c": "c7192b0515eb7de9526291913ef97737207844a45d266a4e1287437f49b3e0b4",
    "note10/device_test/linux_data_input_range.h": "c53f208c886ba21af0f22d266a1edb1de0f42a3e40d5a68080a41fcf775d4dac",
    "note10/device_test/linux_data_input_range_fixture.c": "d3c7695b319963b9d6de679a5eadaf107c4dc667e610b892f2953a390854ecd5",
    "note10/device_test/materialize_auto_cycle.py": "ca9bb27f8cf08fc61d2a7ea677e63edb620a99119c2ead871ebae2c29ac8c289",
    "note10/device_test/native_memory_observation.py": "f4acd0f310989bfcd1b0c2039fef6e429e8ec4d4f41ebdb94fc483538fa26663",
    "note10/device_test/prepare_linux_boot.py": "2dc0ddd51a68f3da30f58df6243bbc33d441a296bd141cc6b9da5dc7fa10b604",
    "note10/device_test/sha256_kat_device_profile.py": "066bb54b8784ae1ec9390dd4f100a07581cf36c05b30d3708a4ee1e5054c5c40",
    "note10/device_test/sha256_stream_state.py": "55de2735fb830ae8047bb4a8fa74325f51b766b1e885c482dbbc5ebabe3ea437",
    "note10/device_test/sha256_stream_vectors.json": "5c379d1ef41a40b9a1262c985476e9dc0ba88dae7b1586f949bbe79686f2165f",
    "note10/device_test/stage_phase2.py": "1ecc741d7517fc15a6043b1329b726e420791f06e712bfd1aaf901a7747db433",
    "note10/device_test/test_affinity_binding.py": "bf602887c4437e0096473392789da33e3ef502297d8c060faf7d9da9ecd3eb89",
    "note10/device_test/test_affinity_ci_context.py": "71aad30ab105a45efe2703fd7b222233836d6e7514560834daa71bfdd351dea9",
    "note10/device_test/test_builtin_init_route.py": "9fa63dd55114472a748062447dd95c17bf4d4d7e743117f69f0bb6a7aca6ea42",
    "note10/device_test/test_current_data_reuse.py": "c1a868d4f9669539aee3e4fca4868118db37071467325a85d73c279b2f1d29de",
    "note10/device_test/test_early_fdt_binding.py": "2444d3d20b7cc42e705cb89c1d04de72599f7da2a5d1b9282636f3b9990ce1fa",
    "note10/device_test/test_early_fdt_host_route.py": "75992eb3e8b1228d0ae3916d47306f0329b7947cb0dfae234ec25c1e737fef6a",
    "note10/device_test/test_linux_data_carrier.py": "550344e818b42f8147ea1f688929feda322c68173f79f6e72850053dbc2e1ca7",
    "note10/device_test/test_native_memory_observation.py": "d34e94fd5d964004c42dedd172ec07bd62826b675dcc9f4925ab4ac06c460599",
    "note10/device_test/test_partition_gate_evidence.py": "b7dd52aa5c7747489a2713f805dbe15a6318f3d3776a8043700549e9383bcc72",
    "note10/device_test/test_sha256_kat_device_profile.py": "c48400d5573695d217101806b8481e39aec38fd5382e64b85f999b4cee42c498",
    "note10/device_test/test_sha256_stream_state.py": "088881f92037a9895b7947eb44692f51ecba1eb602a02dacc02ff3b94a836db8",
    "note10/device_test/test_v100_carrier_input_probe.py": "f8e37cb2da1fc1efda5582079bb619d8853565d892a589872d0699277e8c4489",
    "note10/device_test/test_v101_live_input_range.py": "e4424b6128a18f4099b31ddc6dcf16ba6256749ba2a87f8bd565b68a1ef68183",
    "note10/device_test/test_v102_input_lifetime.py": "29cdae5c4b8ace788ad84f529700d753bcb19c9d4a34697bddf8ca7dfa80bed1",
    "note10/device_test/test_v99_carrier_compare_evidence.py": "2b45c21197709706d3f3ffc23e1428084d5d50a93a1d9b5bd22c2693124cf20c",
    "note10/device_test/test_v99_host_profile_origin.py": "fb4a1c349ca298b4f18ba64e0692c7a93e9f0877b2f7a7ec22fa2c8f29ac219a"
})


V104_PROFILE_ORIGIN_HEAD = '392e0352715c60d96adc0ecbe860335547941dce'
V104_PROFILE_ORIGIN_PINS = MappingProxyType({
    "note10/device_test/affinity_binding.py": "6d5b16d54a803c95bdd391a38efbd2bac5ef36baffe199f86cd83f878bf10678",
    "note10/device_test/auto_cycle.py": "36793ff1964331b3a77b530fc1be5923d1807a3752ab0f7d4f68a51adde12812",
    "note10/device_test/build_boot_test_packages.py": "17b973f54185521be6685acb5e019f8bf8b5f10897d01c0167929c97859cddef",
    "note10/device_test/build_readonly_input_pc.py": "893698f6741fd178334777b4f96c98934d78b5a927fe4cf3d383d92e90557d9e",
    "note10/device_test/builtin_init_profile.py": "78dd3b93a3c1aaf3651a1b3efcf1568beb608dab0693721ec336dd8dc3c4b1a6",
    "note10/device_test/builtin_init_route.py": "46b100dc95f11e344c11b8cb3fba5d34d17b2884385923426a42246699fda43d",
    "note10/device_test/carrier_lzma.c": "e204732754f15929f7134885ec2740e1ed26f0291dd64c7df7957a4aee7b987a",
    "note10/device_test/carrier_lzma.h": "6790aa17da94025e0bab175377573edb8df3f503c8cde86f8c919e33ee742974",
    "note10/device_test/current_data_reuse.py": "15c7a5a55e22f4445c216904769d7ba9b6367f792122e5b936305c95ae031129",
    "note10/device_test/early_fdt_binding.py": "d4f7099fb45eca31c83c9acd9fbfe0cd5c7ccc5c271c18180e3672e22f9a6b78",
    "note10/device_test/linux_data_carrier.c": "25b219d04ebd391c160ad39c4ffed070a82104d4242eab4adad7a53dbdc66c9f",
    "note10/device_test/linux_data_carrier.py": "71b70fac5eb77fe55e6db2a0ab915ba3e1deeb723793e476488fb1f7b33652e3",
    "note10/device_test/linux_data_carrier_composition.c": "2eb666597983d3a2dfb0a4f98da26dc02dff287db49d39756ada6edc90e0c667",
    "note10/device_test/linux_data_carrier_fixture.c": "6b1b0e14184582c734a3154eeef6c0e2736fd1b8ef3491881b7decaacb5ecbe4",
    "note10/device_test/linux_data_compare_evidence.h": "3383823cf1fd56f688ad9d6823d965fdda270a08acede17f6df8d87fa6199438",
    "note10/device_test/linux_data_compare_evidence_fixture.c": "45a0cdfd8d4bd8df5ffbbb0e370cd05f768d522e96208881a7f7a02ee02fadc3",
    "note10/device_test/linux_data_early_prefix.h": "60fb29d56be78212e04cc164938db4a25296fdea5250e372824b317127aaeb98",
    "note10/device_test/linux_data_early_prefix_fixture.c": "b058ccfa33fccadfa2547986a724b21dd7de0b781e003cd3ca1c71fddfe36f09",
    "note10/device_test/linux_data_growth.h": "640ae63bd927d205ad8bc489c4c7b25935f1c4311332dce5d10821acf3ac0746",
    "note10/device_test/linux_data_growth_fixture.c": "d567edfc28efc1b258eff93a72dda94d8f24af00297b315b1f7d371c7d77066a",
    "note10/device_test/linux_data_input_probe_fixture.c": "c7192b0515eb7de9526291913ef97737207844a45d266a4e1287437f49b3e0b4",
    "note10/device_test/linux_data_input_range.h": "c53f208c886ba21af0f22d266a1edb1de0f42a3e40d5a68080a41fcf775d4dac",
    "note10/device_test/linux_data_input_range_fixture.c": "d3c7695b319963b9d6de679a5eadaf107c4dc667e610b892f2953a390854ecd5",
    "note10/device_test/materialize_auto_cycle.py": "ca9bb27f8cf08fc61d2a7ea677e63edb620a99119c2ead871ebae2c29ac8c289",
    "note10/device_test/native_memory_observation.py": "f4acd0f310989bfcd1b0c2039fef6e429e8ec4d4f41ebdb94fc483538fa26663",
    "note10/device_test/prepare_linux_boot.py": "2dc0ddd51a68f3da30f58df6243bbc33d441a296bd141cc6b9da5dc7fa10b604",
    "note10/device_test/readonly_input_pc.h": "01b18e5fddcd12fba45190baa337b47c3309f54cc7a448cd6d72209c5ba8a3f0",
    "note10/device_test/readonly_input_pc.py": "d7125058dc85a57eb4283fccf87bcb6af96c26de1363f81d1acb0999b94f1fc7",
    "note10/device_test/readonly_input_pc_fixture.c": "99f0e7eb9240b5c08314993a14dfcd9a532df0e24158679cdbed8b0c3c752730",
    "note10/device_test/sha256_kat_device_profile.py": "81843092a418cb04ed001882ca97ee0de158eac6d19496a2188e27441159908c",
    "note10/device_test/sha256_stream_state.py": "55de2735fb830ae8047bb4a8fa74325f51b766b1e885c482dbbc5ebabe3ea437",
    "note10/device_test/sha256_stream_vectors.json": "5c379d1ef41a40b9a1262c985476e9dc0ba88dae7b1586f949bbe79686f2165f",
    "note10/device_test/stage_phase2.py": "1ecc741d7517fc15a6043b1329b726e420791f06e712bfd1aaf901a7747db433",
    "note10/device_test/test_affinity_binding.py": "bf602887c4437e0096473392789da33e3ef502297d8c060faf7d9da9ecd3eb89",
    "note10/device_test/test_affinity_ci_context.py": "71aad30ab105a45efe2703fd7b222233836d6e7514560834daa71bfdd351dea9",
    "note10/device_test/test_builtin_init_route.py": "9fa63dd55114472a748062447dd95c17bf4d4d7e743117f69f0bb6a7aca6ea42",
    "note10/device_test/test_current_data_reuse.py": "c1a868d4f9669539aee3e4fca4868118db37071467325a85d73c279b2f1d29de",
    "note10/device_test/test_early_fdt_binding.py": "2444d3d20b7cc42e705cb89c1d04de72599f7da2a5d1b9282636f3b9990ce1fa",
    "note10/device_test/test_early_fdt_host_route.py": "75992eb3e8b1228d0ae3916d47306f0329b7947cb0dfae234ec25c1e737fef6a",
    "note10/device_test/test_linux_data_carrier.py": "550344e818b42f8147ea1f688929feda322c68173f79f6e72850053dbc2e1ca7",
    "note10/device_test/test_native_memory_observation.py": "d34e94fd5d964004c42dedd172ec07bd62826b675dcc9f4925ab4ac06c460599",
    "note10/device_test/test_partition_gate_evidence.py": "b7dd52aa5c7747489a2713f805dbe15a6318f3d3776a8043700549e9383bcc72",
    "note10/device_test/test_sha256_kat_device_profile.py": "c48400d5573695d217101806b8481e39aec38fd5382e64b85f999b4cee42c498",
    "note10/device_test/test_sha256_stream_state.py": "088881f92037a9895b7947eb44692f51ecba1eb602a02dacc02ff3b94a836db8",
    "note10/device_test/test_v100_carrier_input_probe.py": "f8e37cb2da1fc1efda5582079bb619d8853565d892a589872d0699277e8c4489",
    "note10/device_test/test_v101_live_input_range.py": "e4424b6128a18f4099b31ddc6dcf16ba6256749ba2a87f8bd565b68a1ef68183",
    "note10/device_test/test_v102_input_lifetime.py": "29cdae5c4b8ace788ad84f529700d753bcb19c9d4a34697bddf8ca7dfa80bed1",
    "note10/device_test/test_v103_readonly_input_pc.py": "cdce146aed40d9526eae04259e39896f629248f6b395ad8ceeec341cae5be9c5",
    "note10/device_test/test_v104_growth_region.py": "89ca671ca695b083ccf9cb58c6f474acfeadb9a67ff9747d640cc533dde40e7d",
    "note10/device_test/test_v99_carrier_compare_evidence.py": "2b45c21197709706d3f3ffc23e1428084d5d50a93a1d9b5bd22c2693124cf20c",
    "note10/device_test/test_v99_host_profile_origin.py": "fb4a1c349ca298b4f18ba64e0692c7a93e9f0877b2f7a7ec22fa2c8f29ac219a"
})


V105_CANDIDATE_ORIGIN_HEAD = 'e49ccf7fe46eb92b32c0b425a2e4da5fe667f9b4'
V105_CANDIDATE_ORIGIN_PINS = MappingProxyType({
    "note10/device_test/affinity_binding.py": "6d5b16d54a803c95bdd391a38efbd2bac5ef36baffe199f86cd83f878bf10678",
    "note10/device_test/auto_cycle.py": "f96796425bae2c1f1308ef4567edcd92b24eb0980ef3f6af2a1d44e6ccbf33a5",
    "note10/device_test/build_boot_test_packages.py": "17b973f54185521be6685acb5e019f8bf8b5f10897d01c0167929c97859cddef",
    "note10/device_test/build_kernel_readonly_input.py": "5391edfa477324dbdd5f4d9c6fb13deb5df8a66b2ed4df7d018213012b227000",
    "note10/device_test/build_readonly_input_pc.py": "893698f6741fd178334777b4f96c98934d78b5a927fe4cf3d383d92e90557d9e",
    "note10/device_test/builtin_init_profile.py": "97d8402ea4e351f6ccae24311fd85e5d27d92d235806449a11ddbb01ab794352",
    "note10/device_test/builtin_init_route.py": "46b100dc95f11e344c11b8cb3fba5d34d17b2884385923426a42246699fda43d",
    "note10/device_test/carrier_lzma.c": "e204732754f15929f7134885ec2740e1ed26f0291dd64c7df7957a4aee7b987a",
    "note10/device_test/carrier_lzma.h": "6790aa17da94025e0bab175377573edb8df3f503c8cde86f8c919e33ee742974",
    "note10/device_test/current_data_reuse.py": "15c7a5a55e22f4445c216904769d7ba9b6367f792122e5b936305c95ae031129",
    "note10/device_test/early_fdt_binding.py": "d4f7099fb45eca31c83c9acd9fbfe0cd5c7ccc5c271c18180e3672e22f9a6b78",
    "note10/device_test/kernel_readonly_input.h": "4aa99ff2ab756b854174eb2519af96e79669f82114293790a538ddd3025298ea",
    "note10/device_test/kernel_readonly_input.py": "2e3856095d7cffab144697f6a835945e5181c37335bb2032fa52be6ed18c0812",
    "note10/device_test/kernel_readonly_input_fixture.c": "6300f13ba284b4f42614a4c6cda8f09c6e6671e88d6e524ec24dacd3a7ab70e0",
    "note10/device_test/linux_data_carrier.c": "ab69b1c91364b8ad6643fe3c5065a9e8724f9acccd22f38049e6badf90a9484b",
    "note10/device_test/linux_data_carrier.py": "11ccb1033110df0bce0f896fe8e96f522724df0256d3aa963d36112b8df6afb5",
    "note10/device_test/linux_data_carrier_composition.c": "2eb666597983d3a2dfb0a4f98da26dc02dff287db49d39756ada6edc90e0c667",
    "note10/device_test/linux_data_carrier_fixture.c": "6b1b0e14184582c734a3154eeef6c0e2736fd1b8ef3491881b7decaacb5ecbe4",
    "note10/device_test/linux_data_compare_evidence.h": "3383823cf1fd56f688ad9d6823d965fdda270a08acede17f6df8d87fa6199438",
    "note10/device_test/linux_data_compare_evidence_fixture.c": "45a0cdfd8d4bd8df5ffbbb0e370cd05f768d522e96208881a7f7a02ee02fadc3",
    "note10/device_test/linux_data_early_prefix.h": "60fb29d56be78212e04cc164938db4a25296fdea5250e372824b317127aaeb98",
    "note10/device_test/linux_data_early_prefix_fixture.c": "b058ccfa33fccadfa2547986a724b21dd7de0b781e003cd3ca1c71fddfe36f09",
    "note10/device_test/linux_data_growth.h": "640ae63bd927d205ad8bc489c4c7b25935f1c4311332dce5d10821acf3ac0746",
    "note10/device_test/linux_data_growth_fixture.c": "d567edfc28efc1b258eff93a72dda94d8f24af00297b315b1f7d371c7d77066a",
    "note10/device_test/linux_data_input_probe_fixture.c": "c7192b0515eb7de9526291913ef97737207844a45d266a4e1287437f49b3e0b4",
    "note10/device_test/linux_data_input_range.h": "c53f208c886ba21af0f22d266a1edb1de0f42a3e40d5a68080a41fcf775d4dac",
    "note10/device_test/linux_data_input_range_fixture.c": "d3c7695b319963b9d6de679a5eadaf107c4dc667e610b892f2953a390854ecd5",
    "note10/device_test/materialize_auto_cycle.py": "3821c1069c5b0c8cef3ae19702525a5449f2763944da0affac00409b7219586e",
    "note10/device_test/native_memory_observation.py": "f4acd0f310989bfcd1b0c2039fef6e429e8ec4d4f41ebdb94fc483538fa26663",
    "note10/device_test/prepare_linux_boot.py": "3543131327e60553ef8708916cdb831aaa727230e664169a580cd018c3bac20f",
    "note10/device_test/readonly_input_pc.h": "01b18e5fddcd12fba45190baa337b47c3309f54cc7a448cd6d72209c5ba8a3f0",
    "note10/device_test/readonly_input_pc.py": "d7125058dc85a57eb4283fccf87bcb6af96c26de1363f81d1acb0999b94f1fc7",
    "note10/device_test/readonly_input_pc_fixture.c": "99f0e7eb9240b5c08314993a14dfcd9a532df0e24158679cdbed8b0c3c752730",
    "note10/device_test/sha256_kat_device_profile.py": "4193a30c66c8a9be97a7c4524ef20d9dc300c4ff3e764559966a3ffe37b4c4e9",
    "note10/device_test/sha256_stream_state.py": "55de2735fb830ae8047bb4a8fa74325f51b766b1e885c482dbbc5ebabe3ea437",
    "note10/device_test/sha256_stream_vectors.json": "5c379d1ef41a40b9a1262c985476e9dc0ba88dae7b1586f949bbe79686f2165f",
    "note10/device_test/stage_phase2.py": "fd95f75a0c204de6c66464dc2e25094c1f41d09ade11e21716155d0089e789ac",
    "note10/device_test/test_affinity_binding.py": "bf602887c4437e0096473392789da33e3ef502297d8c060faf7d9da9ecd3eb89",
    "note10/device_test/test_affinity_ci_context.py": "71aad30ab105a45efe2703fd7b222233836d6e7514560834daa71bfdd351dea9",
    "note10/device_test/test_builtin_init_route.py": "9fa63dd55114472a748062447dd95c17bf4d4d7e743117f69f0bb6a7aca6ea42",
    "note10/device_test/test_current_data_reuse.py": "c1a868d4f9669539aee3e4fca4868118db37071467325a85d73c279b2f1d29de",
    "note10/device_test/test_early_fdt_binding.py": "2444d3d20b7cc42e705cb89c1d04de72599f7da2a5d1b9282636f3b9990ce1fa",
    "note10/device_test/test_early_fdt_host_route.py": "75992eb3e8b1228d0ae3916d47306f0329b7947cb0dfae234ec25c1e737fef6a",
    "note10/device_test/test_linux_data_carrier.py": "550344e818b42f8147ea1f688929feda322c68173f79f6e72850053dbc2e1ca7",
    "note10/device_test/test_native_memory_observation.py": "d34e94fd5d964004c42dedd172ec07bd62826b675dcc9f4925ab4ac06c460599",
    "note10/device_test/test_partition_gate_evidence.py": "b7dd52aa5c7747489a2713f805dbe15a6318f3d3776a8043700549e9383bcc72",
    "note10/device_test/test_sha256_kat_device_profile.py": "c48400d5573695d217101806b8481e39aec38fd5382e64b85f999b4cee42c498",
    "note10/device_test/test_sha256_stream_state.py": "088881f92037a9895b7947eb44692f51ecba1eb602a02dacc02ff3b94a836db8",
    "note10/device_test/test_v100_carrier_input_probe.py": "f8e37cb2da1fc1efda5582079bb619d8853565d892a589872d0699277e8c4489",
    "note10/device_test/test_v101_live_input_range.py": "e4424b6128a18f4099b31ddc6dcf16ba6256749ba2a87f8bd565b68a1ef68183",
    "note10/device_test/test_v102_input_lifetime.py": "29cdae5c4b8ace788ad84f529700d753bcb19c9d4a34697bddf8ca7dfa80bed1",
    "note10/device_test/test_v103_readonly_input_pc.py": "cdce146aed40d9526eae04259e39896f629248f6b395ad8ceeec341cae5be9c5",
    "note10/device_test/test_v104_growth_region.py": "89ca671ca695b083ccf9cb58c6f474acfeadb9a67ff9747d640cc533dde40e7d",
    "note10/device_test/test_v105_kernel_readonly.py": "7c1cccbdda3e8df612a0fa7d52870e74d750385b85cff7b2965d236177bb23dd",
    "note10/device_test/test_v99_carrier_compare_evidence.py": "2b45c21197709706d3f3ffc23e1428084d5d50a93a1d9b5bd22c2693124cf20c",
    "note10/device_test/test_v99_host_profile_origin.py": "fb4a1c349ca298b4f18ba64e0692c7a93e9f0877b2f7a7ec22fa2c8f29ac219a"
})


V105_PACKING_ORIGIN_HEAD = 'a0d180974badaa339ee8463ca877ca737942eb2b'
V105_PACKING_ORIGIN_PINS = MappingProxyType({
    "note10/device_test/affinity_binding.py": "6d5b16d54a803c95bdd391a38efbd2bac5ef36baffe199f86cd83f878bf10678",
    "note10/device_test/auto_cycle.py": "f96796425bae2c1f1308ef4567edcd92b24eb0980ef3f6af2a1d44e6ccbf33a5",
    "note10/device_test/build_boot_test_packages.py": "17b973f54185521be6685acb5e019f8bf8b5f10897d01c0167929c97859cddef",
    "note10/device_test/build_kernel_readonly_input.py": "5391edfa477324dbdd5f4d9c6fb13deb5df8a66b2ed4df7d018213012b227000",
    "note10/device_test/build_readonly_input_pc.py": "893698f6741fd178334777b4f96c98934d78b5a927fe4cf3d383d92e90557d9e",
    "note10/device_test/builtin_init_profile.py": "81ee864aeecfec92f87c5704533b0b15423d21ea604565a1b121a4d338898248",
    "note10/device_test/builtin_init_route.py": "46b100dc95f11e344c11b8cb3fba5d34d17b2884385923426a42246699fda43d",
    "note10/device_test/carrier_lzma.c": "e204732754f15929f7134885ec2740e1ed26f0291dd64c7df7957a4aee7b987a",
    "note10/device_test/carrier_lzma.h": "6790aa17da94025e0bab175377573edb8df3f503c8cde86f8c919e33ee742974",
    "note10/device_test/current_data_reuse.py": "15c7a5a55e22f4445c216904769d7ba9b6367f792122e5b936305c95ae031129",
    "note10/device_test/early_fdt_binding.py": "d4f7099fb45eca31c83c9acd9fbfe0cd5c7ccc5c271c18180e3672e22f9a6b78",
    "note10/device_test/kernel_readonly_input.h": "4aa99ff2ab756b854174eb2519af96e79669f82114293790a538ddd3025298ea",
    "note10/device_test/kernel_readonly_input.py": "1160fa8a27461a4403f7fc1a176b5d9048ab10c5b906301d914232720cda4f5f",
    "note10/device_test/kernel_readonly_input_fixture.c": "6300f13ba284b4f42614a4c6cda8f09c6e6671e88d6e524ec24dacd3a7ab70e0",
    "note10/device_test/linux_data_carrier.c": "ab69b1c91364b8ad6643fe3c5065a9e8724f9acccd22f38049e6badf90a9484b",
    "note10/device_test/linux_data_carrier.py": "ac839c201b84e6ab27cd696b22a7f9260d53621cf4d754182e4da116568e9abf",
    "note10/device_test/linux_data_carrier_composition.c": "2eb666597983d3a2dfb0a4f98da26dc02dff287db49d39756ada6edc90e0c667",
    "note10/device_test/linux_data_carrier_fixture.c": "6b1b0e14184582c734a3154eeef6c0e2736fd1b8ef3491881b7decaacb5ecbe4",
    "note10/device_test/linux_data_compare_evidence.h": "3383823cf1fd56f688ad9d6823d965fdda270a08acede17f6df8d87fa6199438",
    "note10/device_test/linux_data_compare_evidence_fixture.c": "45a0cdfd8d4bd8df5ffbbb0e370cd05f768d522e96208881a7f7a02ee02fadc3",
    "note10/device_test/linux_data_early_prefix.h": "60fb29d56be78212e04cc164938db4a25296fdea5250e372824b317127aaeb98",
    "note10/device_test/linux_data_early_prefix_fixture.c": "b058ccfa33fccadfa2547986a724b21dd7de0b781e003cd3ca1c71fddfe36f09",
    "note10/device_test/linux_data_growth.h": "640ae63bd927d205ad8bc489c4c7b25935f1c4311332dce5d10821acf3ac0746",
    "note10/device_test/linux_data_growth_fixture.c": "d567edfc28efc1b258eff93a72dda94d8f24af00297b315b1f7d371c7d77066a",
    "note10/device_test/linux_data_input_probe_fixture.c": "c7192b0515eb7de9526291913ef97737207844a45d266a4e1287437f49b3e0b4",
    "note10/device_test/linux_data_input_range.h": "c53f208c886ba21af0f22d266a1edb1de0f42a3e40d5a68080a41fcf775d4dac",
    "note10/device_test/linux_data_input_range_fixture.c": "d3c7695b319963b9d6de679a5eadaf107c4dc667e610b892f2953a390854ecd5",
    "note10/device_test/materialize_auto_cycle.py": "65874b171f2d88a66f98df854a831e30bf6055a32c43903e82dfa92df13d39e8",
    "note10/device_test/native_memory_observation.py": "f4acd0f310989bfcd1b0c2039fef6e429e8ec4d4f41ebdb94fc483538fa26663",
    "note10/device_test/prepare_linux_boot.py": "9b41826b7b27dca4ff9078b5b78b30bb509b848535b597516354a5bb64038674",
    "note10/device_test/readonly_input_pc.h": "01b18e5fddcd12fba45190baa337b47c3309f54cc7a448cd6d72209c5ba8a3f0",
    "note10/device_test/readonly_input_pc.py": "d7125058dc85a57eb4283fccf87bcb6af96c26de1363f81d1acb0999b94f1fc7",
    "note10/device_test/readonly_input_pc_fixture.c": "99f0e7eb9240b5c08314993a14dfcd9a532df0e24158679cdbed8b0c3c752730",
    "note10/device_test/sha256_kat_device_profile.py": "255ebe4d879f415d10466fa8c85389a2cac7ac1b681f5028b4e7f3ce242145d5",
    "note10/device_test/sha256_stream_state.py": "55de2735fb830ae8047bb4a8fa74325f51b766b1e885c482dbbc5ebabe3ea437",
    "note10/device_test/sha256_stream_vectors.json": "5c379d1ef41a40b9a1262c985476e9dc0ba88dae7b1586f949bbe79686f2165f",
    "note10/device_test/stage_phase2.py": "fd95f75a0c204de6c66464dc2e25094c1f41d09ade11e21716155d0089e789ac",
    "note10/device_test/test_affinity_binding.py": "bf602887c4437e0096473392789da33e3ef502297d8c060faf7d9da9ecd3eb89",
    "note10/device_test/test_affinity_ci_context.py": "71aad30ab105a45efe2703fd7b222233836d6e7514560834daa71bfdd351dea9",
    "note10/device_test/test_builtin_init_route.py": "9fa63dd55114472a748062447dd95c17bf4d4d7e743117f69f0bb6a7aca6ea42",
    "note10/device_test/test_current_data_reuse.py": "c1a868d4f9669539aee3e4fca4868118db37071467325a85d73c279b2f1d29de",
    "note10/device_test/test_early_fdt_binding.py": "2444d3d20b7cc42e705cb89c1d04de72599f7da2a5d1b9282636f3b9990ce1fa",
    "note10/device_test/test_early_fdt_host_route.py": "75992eb3e8b1228d0ae3916d47306f0329b7947cb0dfae234ec25c1e737fef6a",
    "note10/device_test/test_linux_data_carrier.py": "550344e818b42f8147ea1f688929feda322c68173f79f6e72850053dbc2e1ca7",
    "note10/device_test/test_native_memory_observation.py": "d34e94fd5d964004c42dedd172ec07bd62826b675dcc9f4925ab4ac06c460599",
    "note10/device_test/test_partition_gate_evidence.py": "b7dd52aa5c7747489a2713f805dbe15a6318f3d3776a8043700549e9383bcc72",
    "note10/device_test/test_sha256_kat_device_profile.py": "c48400d5573695d217101806b8481e39aec38fd5382e64b85f999b4cee42c498",
    "note10/device_test/test_sha256_stream_state.py": "088881f92037a9895b7947eb44692f51ecba1eb602a02dacc02ff3b94a836db8",
    "note10/device_test/test_v100_carrier_input_probe.py": "f8e37cb2da1fc1efda5582079bb619d8853565d892a589872d0699277e8c4489",
    "note10/device_test/test_v101_live_input_range.py": "e4424b6128a18f4099b31ddc6dcf16ba6256749ba2a87f8bd565b68a1ef68183",
    "note10/device_test/test_v102_input_lifetime.py": "29cdae5c4b8ace788ad84f529700d753bcb19c9d4a34697bddf8ca7dfa80bed1",
    "note10/device_test/test_v103_readonly_input_pc.py": "cdce146aed40d9526eae04259e39896f629248f6b395ad8ceeec341cae5be9c5",
    "note10/device_test/test_v104_growth_region.py": "89ca671ca695b083ccf9cb58c6f474acfeadb9a67ff9747d640cc533dde40e7d",
    "note10/device_test/test_v105_kernel_readonly.py": "7c1cccbdda3e8df612a0fa7d52870e74d750385b85cff7b2965d236177bb23dd",
    "note10/device_test/test_v105_packing_rev1.py": "2402b70737ee2ec9c16fadd0a05b8837d68e5ae364cd1a468c4ac4471a75eabe",
    "note10/device_test/test_v99_carrier_compare_evidence.py": "2b45c21197709706d3f3ffc23e1428084d5d50a93a1d9b5bd22c2693124cf20c",
    "note10/device_test/test_v99_host_profile_origin.py": "fb4a1c349ca298b4f18ba64e0692c7a93e9f0877b2f7a7ec22fa2c8f29ac219a"
})


def host_binding(source_head):
    from retained_v108_origin import live
    live(source_head)
    require(re.fullmatch('[0-9a-f]{40}', source_head or ''), 'exact host-profile publication source pin required')
    require(source_head not in (V97_PROFILE_ORIGIN_HEAD, V99_PROFILE_ORIGIN_HEAD, V100_PROFILE_ORIGIN_HEAD, V101_PROFILE_ORIGIN_HEAD, V102_PROFILE_ORIGIN_HEAD, V104_PROFILE_ORIGIN_HEAD, V105_CANDIDATE_ORIGIN_HEAD, V105_PACKING_ORIGIN_HEAD, __import__('kernel_readonly_span_candidate').NATIVE_HEAD, 'e32ec501551b74b4cca5618ea25245f012656f29'),
            'retained host origin cannot construct current host')
    pins = V71_HOST_PINS if source_head == V71_HOST_HEAD else V72_HOST_PINS if source_head == V72_HOST_HEAD else V73_HOST_PINS if source_head == V73_HOST_HEAD else V78_HOST_PINS if source_head == V78_HOST_HEAD else V81_IMAGE_HOST_PINS if source_head == V81_IMAGE_HEAD else V81_HOST_PINS if source_head == V81_HOST_HEAD else V82_HOST_PINS if source_head == V82_HOST_HEAD else V88_HOST_PINS if source_head == V88_HOST_HEAD else V89_HOST_PINS if source_head == V89_HOST_HEAD else V90_HOST_PINS if source_head == V90_HOST_HEAD else V91_HOST_PINS if source_head == V91_HOST_HEAD else {
        'note10/device_test/'+name: sha(Path(__file__).parent/name)
        for name in (*HOST_SOURCES, 'builtin_init_profile.py', 'builtin_init_route.py', 'test_builtin_init_route.py',
                     'sha256_stream_state.py', 'sha256_stream_vectors.json', 'test_sha256_stream_state.py',
                     'affinity_binding.py', 'test_affinity_binding.py', 'test_affinity_ci_context.py',
                     'test_partition_gate_evidence.py', 'early_fdt_binding.py', 'test_early_fdt_binding.py', 'test_early_fdt_host_route.py', 'native_memory_observation.py', 'test_native_memory_observation.py',
                      'linux_data_carrier.py', 'linux_data_carrier.c', 'linux_data_carrier_composition.c',
                      'test_linux_data_carrier.py', 'linux_data_carrier_fixture.c', 'carrier_lzma.c', 'carrier_lzma.h',
                      'linux_data_compare_evidence.h', 'linux_data_compare_evidence_fixture.c', 'test_v99_carrier_compare_evidence.py',
                      'test_v99_host_profile_origin.py', 'linux_data_input_probe_fixture.c',
                      'test_v100_carrier_input_probe.py', 'linux_data_input_range.h',
                      'linux_data_input_range_fixture.c', 'test_v101_live_input_range.py',
                      'linux_data_early_prefix.h', 'linux_data_early_prefix_fixture.c', 'test_v102_input_lifetime.py',
                      'readonly_input_pc.py','readonly_input_pc.h','build_readonly_input_pc.py',
                      'readonly_input_pc_fixture.c','test_v103_readonly_input_pc.py',
                      'linux_data_growth.h','linux_data_growth_fixture.c','test_v104_growth_region.py',
                      'kernel_readonly_input.py','kernel_readonly_input.h','build_kernel_readonly_input.py',
                      'kernel_readonly_input_fixture.c','test_v105_kernel_readonly.py','test_v105_packing_rev1.py','precheck_window_access.py','test_v105_battery5_policy.py','kernel_readonly_span.h','kernel_readonly_span_fixture.c',
                      'test_v106_kernel_readonly_span.py','build_kernel_readonly_span_pc.py',
                      'kernel_readonly_span_candidate.py','kernel_readonly_span_candidate.h','kernel_readonly_span_candidate_fixture.c',
                      'test_v107_readonly_span_candidate.py','build_kernel_readonly_span_candidate.py',
                      'type3_admission.py','test_v108_type3_admission.py','retained_v108_origin.py',
                      'readonly_stage_witness.py','readonly_stage_witness.h','readonly_stage_witness_fixture.c','test_v109_readonly_stage_witness.py')}
    return dict(host_profile_source_head=source_head, host_profile_source_sha256=dict(pins))


def packing_host_origin(binding):
    require(type(binding) is dict and set(binding)=={'host_profile_source_head','host_profile_source_sha256'},
            'closed packing-host origin required')
    head=binding['host_profile_source_head']
    if head==V105_PACKING_ORIGIN_HEAD:
        require(binding['host_profile_source_sha256']==dict(V105_PACKING_ORIGIN_PINS),'retained packing57 identity differs')
        return dict(host_profile_source_head=head,host_profile_source_sha256=dict(V105_PACKING_ORIGIN_PINS))
    require(binding==host_binding(head),'live packing-host identity differs')
    return binding


def host_profile_origin(binding):
    """Validate a producing profile origin without relabeling the live host."""
    from retained_v108_origin import selected,origin
    if selected(binding):return origin(binding)
    head = binding.get('host_profile_source_head')
    require(re.fullmatch('[0-9a-f]{40}', head or '') and
            re.fullmatch('[0-9a-f]{40}', binding.get('source_head', '')),
            'host-profile code identity differs')
    if head == V97_PROFILE_ORIGIN_HEAD:
        require(binding.get('device_profile') == DATA_PROFILE and
                binding.get('source_head') == V91_IMAGE_HEAD and
                binding.get('data_host_experiment') == 'v97-current-data-reuse-v91' and
                re.fullmatch('[0-9a-f]{64}', binding.get('data_current_binding_sha256', '')) and
                'data_compare_schema' not in binding,
                'retained v97 host origin scope differs')
        pins = V97_PROFILE_ORIGIN_PINS
    elif head == V99_PROFILE_ORIGIN_HEAD:
        require(binding.get('device_profile') == DATA_PROFILE and
                binding.get('source_head') == V99_PROFILE_ORIGIN_HEAD and
                binding.get('data_compare_schema') == 'n10-data-compare-v1' and
                not any(key in binding for key in ('data_host_experiment', 'data_current_binding_sha256')),
                'retained v99 host origin scope differs')
        pins = V99_PROFILE_ORIGIN_PINS
    elif head == V100_PROFILE_ORIGIN_HEAD:
        require(binding.get('device_profile') == DATA_PROFILE and
                binding.get('source_head') == V100_PROFILE_ORIGIN_HEAD and
                binding.get('data_compare_schema') == 'n10-data-compare-v2' and
                not any(key in binding for key in ('data_host_experiment', 'data_current_binding_sha256',
                                                    'data_input_range_schema', 'data_linked_kernel_bytes')),
                'retained v100 host origin scope differs')
        pins = V100_PROFILE_ORIGIN_PINS
    elif head == V101_PROFILE_ORIGIN_HEAD:
        require(binding.get('device_profile') == DATA_PROFILE and binding.get('source_head') == V101_PROFILE_ORIGIN_HEAD and
                binding.get('data_compare_schema') == 'n10-data-compare-v2' and
                binding.get('data_input_range_schema') == 'n10-data-range-v1' and
                type(binding.get('data_linked_kernel_bytes')) is int and 0 < binding['data_linked_kernel_bytes'] < (1<<64) and
                not any(key in binding for key in ('data_host_experiment','data_current_binding_sha256','data_early_prefix_schema')),
                'retained v101 host origin scope differs')
        pins = V101_PROFILE_ORIGIN_PINS
    elif head == V102_PROFILE_ORIGIN_HEAD:
        require(binding.get('device_profile') == DATA_PROFILE and binding.get('source_head') == V102_PROFILE_ORIGIN_HEAD and
                binding.get('data_compare_schema') == 'n10-data-compare-v2' and
                binding.get('data_input_range_schema') == 'n10-data-range-v1' and
                binding.get('data_early_prefix_schema') == 'n10-data-early-prefix-v1' and
                type(binding.get('data_linked_kernel_bytes')) is int and 0 < binding['data_linked_kernel_bytes'] < (1<<64) and
                not any(key in binding for key in ('data_host_experiment','data_current_binding_sha256',
                                                    'readonly_input_schema','readonly_input_slot','readonly_pc_contract')),
                'retained v102 host origin scope differs')
        pins = V102_PROFILE_ORIGIN_PINS
    elif head == V104_PROFILE_ORIGIN_HEAD:
        require(binding.get('device_profile')==DATA_PROFILE and binding.get('source_head')==V104_PROFILE_ORIGIN_HEAD and
            binding.get('data_compare_schema')=='n10-data-compare-v2' and binding.get('data_input_range_schema')=='n10-data-range-v1' and
            binding.get('data_early_prefix_schema')=='n10-data-early-prefix-v1' and binding.get('data_growth_schema')=='n10-data-growth-v1' and
            binding.get('data_growth_target_source')=='e32ec501551b74b4cca5618ea25245f012656f29' and
            type(binding.get('data_growth_target_bytes')) is int and binding['data_growth_target_bytes']==59523072 and
            type(binding.get('data_growth_budget_bytes')) is int and binding['data_growth_budget_bytes']==59768832 and
            type(binding.get('data_linked_kernel_bytes')) is int and 0<binding['data_linked_kernel_bytes']<59523072 and
            not any(key in binding for key in ('data_host_experiment','data_current_binding_sha256','data_input_kind',
                'kernel_readonly_schema','kernel_readonly_slot','kernel_readonly_compact_sha256',
                'readonly_input_schema','readonly_input_slot','readonly_pc_contract')),'exact retained normal v104 origin required')
        pins = V104_PROFILE_ORIGIN_PINS
    elif head == V105_CANDIDATE_ORIGIN_HEAD:
        from kernel_readonly_input import candidate_scope
        require(binding.get('device_profile')==DATA_PROFILE and binding.get('source_head')==V105_CANDIDATE_ORIGIN_HEAD,
                'exact retained candidate native/profile origin required')
        candidate_scope(binding)
        pins=V105_CANDIDATE_ORIGIN_PINS
    else:
        pins = host_binding(head)['host_profile_source_sha256']
    require(binding.get('host_profile_source_sha256') == dict(pins), 'host-profile code identity differs')
    return dict(host_profile_source_head=head, host_profile_source_sha256=dict(pins))


def root_receipt_binding(root, receipt, expected_sha, binding):
    require(re.fullmatch('[0-9a-f]{64}', expected_sha or '') and sha(receipt) == expected_sha,
            'exact reviewed Image-root receipt SHA required')
    row = read(receipt)
    keys = {'schema', 'kind', 'accepted', 'root_reader_result_sha256', 'producer_source_head',
            'ci_result_sha256', 'image_sha256', 'image_bytes', 'effective_config_sha256',
            'build_evidence_id', 'kernel_banner', 'run_id', 'attempt', 'workflow_id', 'job_id',
            'artifact_id', 'artifact_zip_sha256', 'artifact_zip_bytes'}
    require(set(row) == keys and row['schema'] == 1 and row['kind'] == binding['device_profile']+'-accepted-image' and
            row['accepted'] is True, 'closed accepted Image-root receipt required')
    require(all(type(row[k]) is int and row[k] > 0 for k in
                ('image_bytes', 'run_id', 'attempt', 'workflow_id', 'job_id', 'artifact_id', 'artifact_zip_bytes')) and
            all(re.fullmatch('[0-9a-f]{64}', row[k] or '') for k in
                ('root_reader_result_sha256', 'ci_result_sha256', 'image_sha256',
                 'effective_config_sha256', 'artifact_zip_sha256')), 'root receipt pin types differ')
    actual = read(Path(root)/'result.json')
    require(row['producer_source_head'] == binding['source_head'] and
            row['ci_result_sha256'] == binding['accepted_result_sha256'] and
            row['image_sha256'] == binding['image_sha256'] and row['image_bytes'] == binding['image_size'] and
            row['effective_config_sha256'] == binding['effective_config_sha256'] and
            row['build_evidence_id'] == binding['build_evidence_id'] and row['kernel_banner'] == binding['kernel_banner'] and
            str(row['run_id']) == actual['ci_context']['GITHUB_RUN_ID'] and
            str(row['attempt']) == actual['ci_context']['GITHUB_RUN_ATTEMPT'], 'root receipt/Image/producer tuple differs')
    # Root supplies the CI-success/producing-byte receipt. The legacy
    # root_reader_result_sha256 field can name that success record; it does
    # not require or claim a separate postbuild reader.
    return dict(image_root_receipt_sha256=expected_sha, root_reader_result_sha256=row['root_reader_result_sha256'])


def ci_success_receipt(context, context_sha256, binding, producer):
    """Bind approved CI metadata to the banner already derived by packaging."""
    keys = {'schema', 'kind', 'accepted', 'producer_source_head', 'ci_result_sha256',
            'image_sha256', 'image_bytes', 'effective_config_sha256', 'build_evidence_id',
            'run_id', 'attempt', 'workflow_id', 'job_id', 'artifact_id',
            'artifact_zip_sha256', 'artifact_zip_bytes'}
    require(type(context) is dict and set(context) == keys and
            type(context['schema']) is int and context['schema'] == 1 and
            context['kind'] == binding.get('device_profile','')+'-ci-success-context' and
            context['accepted'] is True and binding.get('device_profile') in (AFFINITY_PROFILE, FDT_PROFILE, NATIVE_PROFILE, DATA_PROFILE),
            'closed accepted diagnostic CI-success context required')
    require(isinstance(context_sha256, str) and re.fullmatch('[0-9a-f]{64}', context_sha256) and
            all(type(context[k]) is int and context[k] > 0 for k in
                ('image_bytes', 'run_id', 'attempt', 'workflow_id', 'job_id', 'artifact_id', 'artifact_zip_bytes')) and
            all(isinstance(context[k], str) and re.fullmatch('[0-9a-f]{64}', context[k]) for k in
                ('ci_result_sha256', 'image_sha256', 'effective_config_sha256', 'artifact_zip_sha256')) and
            isinstance(context['producer_source_head'], str) and re.fullmatch('[0-9a-f]{40}', context['producer_source_head']) and
            isinstance(context['build_evidence_id'], str) and re.fullmatch('[0-9a-f]{32}', context['build_evidence_id']),
            'CI-success context types/pins differ')
    ci = producer.get('ci_context', {})
    require(producer.get('version') == ('v107' if binding.get('data_input_kind')=='kernel-readonly-span-candidate' else 'v105' if binding.get('data_input_kind')=='kernel-readonly-candidate' else 'v91' if binding['device_profile']==DATA_PROFILE else 'v82' if binding['device_profile']==NATIVE_PROFILE else 'v81' if binding['device_profile']==FDT_PROFILE else 'v78') and
            producer.get('diagnostic_kind') == ('kernel-readonly-span-candidate' if binding.get('data_input_kind')=='kernel-readonly-span-candidate' else 'kernel-readonly-candidate' if binding.get('data_input_kind')=='kernel-readonly-candidate' else 'linux-data-carrier' if binding['device_profile']==DATA_PROFILE else 'native-memory-observation' if binding['device_profile']==NATIVE_PROFILE else 'early-fdt-binding' if binding['device_profile']==FDT_PROFILE else 'cpu-affinity-binding') and
            producer.get('passed') is True and producer.get('Image_built') is True and
            context['producer_source_head'] == binding['source_head'] == ci.get('GITHUB_SHA') and
            str(context['run_id']) == ci.get('GITHUB_RUN_ID') and
            str(context['attempt']) == ci.get('GITHUB_RUN_ATTEMPT') and
            ci.get('GITHUB_JOB') == ('linux-data-carrier' if binding['device_profile']==DATA_PROFILE else 'native-memory-observation' if binding['device_profile']==NATIVE_PROFILE else 'early-fdt-binding' if binding['device_profile']==FDT_PROFILE else 'cpu-affinity-binding') and
            context['ci_result_sha256'] == binding['accepted_result_sha256'] and
            context['image_sha256'] == binding['image_sha256'] == producer.get('image_sha256') and
            context['image_bytes'] == binding['image_size'] == producer.get('image_bytes') and
            context['effective_config_sha256'] == binding['effective_config_sha256'] ==
                producer.get('files_sha256', {}).get('actual-effective.config') and
            context['build_evidence_id'] == binding['build_evidence_id'] == producer.get('build_evidence_id') and
            isinstance(binding.get('kernel_banner'), str) and
            binding['kernel_banner'].startswith('Linux version 4.14.113-v107-readonly-span-candidate ' if binding.get('data_input_kind')=='kernel-readonly-span-candidate' else 'Linux version 4.14.113-v105-kernel-readonly ' if binding.get('data_input_kind')=='kernel-readonly-candidate' else 'Linux version 4.14.113-v91-trusted-logical ' if binding['device_profile']==DATA_PROFILE else 'Linux version 4.14.113-v82-native-memory ' if binding['device_profile']==NATIVE_PROFILE else 'Linux version 4.14.113-v81-early-fdt ' if binding['device_profile']==FDT_PROFILE else 'Linux version 4.14.113-v78-cpu-affinity '),
            'CI-success context/producer/package tuple differs')
    # No banner is accepted from the context. Workflow/job/artifact IDs originate
    # in the explicitly hash-approved Root collection record, not Image guesses.
    return dict(schema=1, kind=binding['device_profile']+'-accepted-image', accepted=True,
                root_reader_result_sha256=context_sha256,
                producer_source_head=context['producer_source_head'],
                ci_result_sha256=context['ci_result_sha256'], image_sha256=context['image_sha256'],
                image_bytes=context['image_bytes'], effective_config_sha256=context['effective_config_sha256'],
                build_evidence_id=context['build_evidence_id'], kernel_banner=binding['kernel_banner'],
                **{k: context[k] for k in ('run_id', 'attempt', 'workflow_id', 'job_id', 'artifact_id',
                                         'artifact_zip_sha256', 'artifact_zip_bytes')})


def write_ci_success_receipt(output, receipt):
    """Exclusive atomic receipt publication inside the fresh private template."""
    output = private(output)
    require(output.is_dir(), 'private template directory required')
    target = output/'image-root-receipt.json'
    require(not target.exists() and not target.is_symlink(), 'fresh image receipt required')
    data = (json.dumps(receipt, indent=2, sort_keys=True)+'\n').encode('utf8')
    temporary = output/'.image-root-receipt.json.tmp'
    with temporary.open('xb') as stream:
        stream.write(data); stream.flush(); os.fsync(stream.fileno())
    try:
        os.link(temporary, target)
    finally:
        temporary.unlink()
    return dict(image_root_receipt_sha256=hashlib.sha256(data).hexdigest(),
                root_reader_result_sha256=receipt['root_reader_result_sha256'])


def common_report(binding, profile_sha):
    extra = dict(builtin_minimal_init_route=True, external_initrd_used_for_PID1=False) if binding['device_profile'] in (BUILTIN_PROFILE, STREAM_PROFILE, AFFINITY_PROFILE, FDT_PROFILE, NATIVE_PROFILE, DATA_PROFILE) else {}
    return dict(binding, **extra, profile_sha256=profile_sha, build_passed=True,
                auto_return_diagnostic=True, auto_return_evidence_version=1,
                auto_cycle_slot=SLOT.decode(), diagnostic_preserves_external_initramfs=binding['device_profile'] != DATA_PROFILE,
                source_commit='55f042627bb7030c93550faafa117674d32b21d1',
                public_defconfig='exynos9820-d2x_defconfig', deployment_ready=False,
                device_boot_tested=False)


def prepare_template(build, output, accepted_result_sha256, source_head, *, root_receipt=None,
                     root_receipt_sha256=None, host_source_head, ci_success_context=None,
                     ci_success_context_sha256=None, carrier_manifest=None, carrier_manifest_sha256=None, producing_sources=None, readonly_compact_manifest=None, readonly_compact_manifest_sha256=None):
    from retained_v108_origin import live
    live(host_source_head)
    build, output = private(build), private(output)
    require(not output.exists() and not output.is_relative_to(build) and not build.is_relative_to(output),
            'fresh disjoint template required')
    context_mode = ci_success_context is not None or ci_success_context_sha256 is not None
    context_bytes = generated_receipt = None
    if context_mode:
        require(root_receipt is None and root_receipt_sha256 is None and ci_success_context is not None and
                isinstance(ci_success_context_sha256, str) and re.fullmatch('[0-9a-f]{64}', ci_success_context_sha256),
                'exclusive CI-success context and exact SHA required')
        context_path = private(ci_success_context)
        require(context_path.is_file() and 0 < context_path.stat().st_size <= 65536, 'bounded CI-success context required')
        context_bytes = context_path.read_bytes()
        require(hashlib.sha256(context_bytes).hexdigest() == ci_success_context_sha256, 'approved CI-success context changed')
        context = json.loads(context_bytes.decode('utf-8-sig'))
    else:
        require(root_receipt is not None and root_receipt_sha256 is not None, 'reviewed root receipt and SHA required')
        root_receipt = private(root_receipt)
    binding = raw_binding(build, accepted_result_sha256, source_head,producing_sources=producing_sources)
    if context_mode:
        require(binding['device_profile'] in (AFFINITY_PROFILE,FDT_PROFILE,NATIVE_PROFILE,DATA_PROFILE) and
                (binding['device_profile'] in (NATIVE_PROFILE,DATA_PROFILE) or host_source_head != source_head),
                'CI-success integration requires a supported new diagnostic/host publication')
        generated_receipt = ci_success_receipt(context, ci_success_context_sha256, binding, read(build/'result.json'))
    else:
        binding.update(root_receipt_binding(build, root_receipt, root_receipt_sha256, binding))
    require(binding['device_profile'] not in (BUILTIN_PROFILE, STREAM_PROFILE, AFFINITY_PROFILE, FDT_PROFILE, NATIVE_PROFILE, DATA_PROFILE) or host_source_head != V71_HOST_HEAD,
            'new builtin profile requires its own host publication head')
    require(binding['device_profile'] != STREAM_PROFILE or host_source_head != V72_HOST_HEAD,
            'stream task requires a new host publication head')
    require(binding['device_profile'] != AFFINITY_PROFILE or host_source_head not in (V71_HOST_HEAD, V72_HOST_HEAD, V73_HOST_HEAD),
            'affinity requires its new host publication')
    require(binding['device_profile'] != FDT_PROFILE or host_source_head not in
            (V71_HOST_HEAD,V72_HOST_HEAD,V73_HOST_HEAD,V78_HOST_HEAD,V81_IMAGE_HEAD) and
            (binding['device_profile'] != FDT_PROFILE or host_source_head != source_head), 'FDT requires separate new host publication')
    require(binding['device_profile'] != NATIVE_PROFILE or host_source_head not in
            (V71_HOST_HEAD,V72_HOST_HEAD,V73_HOST_HEAD,V78_HOST_HEAD,V81_IMAGE_HEAD,V81_HOST_HEAD),
            'native task requires its own new host publication')
    require(binding['device_profile'] != DATA_PROFILE or host_source_head not in (V71_HOST_HEAD,V72_HOST_HEAD,V73_HOST_HEAD,V78_HOST_HEAD,V81_IMAGE_HEAD,V81_HOST_HEAD,V82_HOST_HEAD,V88_HOST_HEAD,V89_IMAGE_HEAD,V89_HOST_HEAD,V90_IMAGE_HEAD,V90_HOST_HEAD), 'DATA requires new host publication')
    require((binding['device_profile'] == DATA_PROFILE and carrier_manifest is not None and carrier_manifest_sha256 is not None) or
            (binding['device_profile'] != DATA_PROFILE and carrier_manifest is None and carrier_manifest_sha256 is None), 'DATA alone requires accepted private carrier input')
    candidate=binding.get('data_input_kind')=='kernel-readonly-candidate'
    require((candidate and readonly_compact_manifest is not None and readonly_compact_manifest_sha256 is not None) or
        (not candidate and readonly_compact_manifest is None and readonly_compact_manifest_sha256 is None),
        'readonly candidate alone requires approved compact manifest')
    binding.update(host_binding(host_source_head))
    shutil.copytree(build, output)
    if binding['device_profile'] == DATA_PROFILE:
        from linux_data_carrier import attach_carrier
        binding.update(attach_carrier(output, carrier_manifest, carrier_manifest_sha256))
        if candidate:
            from kernel_readonly_input import attach_compact
            binding.update(attach_compact(output,readonly_compact_manifest,readonly_compact_manifest_sha256,binding))
    if producing_sources is not None:
        from current_data_reuse import require_context
        context=require_context(producing_sources)
        context.check_carrier(binding)
        binding.update(context.write_record(output,host_source_head))
    if context_mode:
        binding.update(write_ci_success_receipt(output, generated_receipt))
        with (output/'ci-success-context.json').open('xb') as stream:
            stream.write(context_bytes)
    else:
        shutil.copyfile(root_receipt, output/'image-root-receipt.json')
    save(output/'device-profile.json', binding)
    save(output/'build-result.json', common_report(binding, sha(output/'device-profile.json')))
    shutil.copyfile(output/'prerequisites/objects/.config', output/'handoff.config')
    validate_template(output)
    return dict(template=str(output), profile=binding['device_profile'], build_result_sha256=sha(output/'build-result.json'),
                device_operations=[], deployment_ready=False,
                kernel_readonly_IO_events=list(__import__('kernel_readonly_input').IO_EVENTS) if candidate else [])


def validate_template(root):
    root = private(root)
    binding = read(root/'device-profile.json')
    if binding.get('data_input_kind')=='kernel-readonly-span-candidate':
        from type3_admission import validate_template as type3_template
        return type3_template(root)
    physical_input_scope(binding)
    require(selected(binding), 'closed KAT profile required')
    origin=host_profile_origin(binding)
    readonly_origin=V105_CANDIDATE_ORIGIN_HEAD if binding.get('host_profile_source_head')==V105_CANDIDATE_ORIGIN_HEAD else None
    context=None
    if 'data_current_binding_sha256' in binding or 'data_host_experiment' in binding:
        from current_data_reuse import load_record
        context=load_record(root,binding)
    measured = raw_binding(root, binding['accepted_result_sha256'], binding['source_head'],producing_sources=context,readonly_origin=readonly_origin)
    if binding['device_profile'] == DATA_PROFILE:
        from linux_data_carrier import carrier_fields
        measured.update(carrier_fields(root))
        if binding.get('data_input_kind')=='kernel-readonly-candidate':
            from kernel_readonly_input import compact_fields
            measured.update(compact_fields(root,measured))
    if context is not None:
        context.check_carrier(measured)
        measured.update(data_current_binding_sha256=binding['data_current_binding_sha256'],data_host_experiment=binding['data_host_experiment'])
    measured.update(root_receipt_binding(root, root/'image-root-receipt.json', binding['image_root_receipt_sha256'], measured))
    measured.update(origin)
    require(binding == measured and sha(root/'handoff.config') == binding['effective_config_sha256'],
            'template profile/config changed')
    report = read(root/'build-result.json')
    require(report == common_report(binding, sha(root/'device-profile.json')), 'truthful template report changed')
    return report


def variant(root, token):
    from materialize_auto_cycle import validate
    report = validate(private(root), token)
    require(selected(report), 'KAT variant required')
    no_legacy(report)
    return report


def fields(row):
    require(selected(row), 'closed KAT profile required')
    no_legacy(row)
    # New bindings are carried through every pair/record/meta comparison.
    from builtin_init_profile import EXTRA_FIELDS
    keys = (*FIELDS, *EXTRA_FIELDS) if row['device_profile'] in (BUILTIN_PROFILE, STREAM_PROFILE, AFFINITY_PROFILE, FDT_PROFILE, NATIVE_PROFILE, DATA_PROFILE) else FIELDS
    if row['device_profile'] == AFFINITY_PROFILE:
        from affinity_binding import EXTRA_FIELDS as affinity_fields
        keys = (*keys, *affinity_fields)
    if row['device_profile'] == FDT_PROFILE:
        from early_fdt_binding import FIELDS as fdt_fields
        keys = (*keys, *fdt_fields)
    if row['device_profile']==NATIVE_PROFILE:
        from native_memory_observation import FIELDS as native_fields
        keys=(*keys,*native_fields)
    if row['device_profile'] == DATA_PROFILE:
        from linux_data_carrier import FIELDS as data_fields, LEGACY_FIELDS, CARRIER_FIELDS
        keys = (*keys, *(LEGACY_FIELDS if row.get('source_head') in (V88_HOST_HEAD,V89_IMAGE_HEAD) else data_fields), *CARRIER_FIELDS)
    if 'data_current_binding_sha256' in row or 'data_host_experiment' in row:
        keys=(*keys,'data_current_binding_sha256','data_host_experiment')
    if 'data_compare_schema' in row:
        keys = (*keys, 'data_compare_schema')
    if 'data_input_range_schema' in row or 'data_linked_kernel_bytes' in row:
        keys = (*keys, 'data_input_range_schema', 'data_linked_kernel_bytes')
    if 'data_early_prefix_schema' in row:
        keys = (*keys, 'data_early_prefix_schema')
    from linux_data_carrier import GROWTH_FIELDS
    if any(key in row for key in GROWTH_FIELDS):
        keys=(*keys,*GROWTH_FIELDS)
    from kernel_readonly_input import FIELDS as kernel_fields, is_candidate
    if row.get('data_input_kind')=='kernel-readonly-span-candidate':
        from type3_admission import BINDING_FIELDS
        keys=(*keys,*BINDING_FIELDS,*(('type3_materialization',) if 'type3_materialization' in row else ()))
    elif is_candidate(row):keys=(*keys,*kernel_fields)
    from kernel_readonly_input import PACKING_FIELDS
    if any(key in row for key in PACKING_FIELDS):keys=(*keys,*PACKING_FIELDS)
    return {key: row[key] for key in keys}


def package_scope(row, mode=None):
    physical_input_scope(row)
    require(selected(row), 'KAT package profile missing')
    no_legacy(row)
    for key in ('profile_sha256', 'accepted_result_sha256', 'image_root_receipt_sha256', 'root_reader_result_sha256'):
        require(re.fullmatch('[0-9a-f]{64}', row.get(key, '')), 'KAT package result/profile pin missing')
    require(re.fullmatch('[0-9a-f]{32}', row.get('build_evidence_id', '')) and
            row.get('kernel_banner', '').startswith(('Linux version 4.14.113-v107-readonly-span-candidate ' if row.get('data_input_kind')=='kernel-readonly-span-candidate' else 'Linux version 4.14.113-v105-kernel-readonly ' if row.get('data_input_kind')=='kernel-readonly-candidate' else 'Linux version 4.14.113-v88-linux-data ' if row.get('source_head') == V88_HOST_HEAD else 'Linux version 4.14.113-v89-data-guard ' if row.get('source_head') == V89_IMAGE_HEAD else 'Linux version 4.14.113-v90-image-expectation ' if row.get('source_head') == V90_IMAGE_HEAD else 'Linux version 4.14.113-v91-trusted-logical ') if row['device_profile']==DATA_PROFILE else 'Linux version 4.14.113-v82-native-memory ' if row['device_profile']==NATIVE_PROFILE else 'Linux version 4.14.113-v81-early-fdt ' if row['device_profile'] == FDT_PROFILE else 'Linux version 4.14.113-v78-cpu-affinity ' if row['device_profile'] == AFFINITY_PROFILE else 'Linux version 4.14.113-v73-sha256-stream ' if row['device_profile'] == STREAM_PROFILE else 'Linux version 4.14.113-v72-builtin-init ' if row['device_profile'] == BUILTIN_PROFILE else 'Linux version 4.14.113-v71-sha256-recovery '),
            'KAT package identity missing')
    host_profile_origin(row)
    if row['device_profile'] in (BUILTIN_PROFILE, STREAM_PROFILE, AFFINITY_PROFILE, FDT_PROFILE, NATIVE_PROFILE, DATA_PROFILE):
        require(row.get('host_profile_source_head') != V71_HOST_HEAD, 'new profile cannot claim historical host head')
        require(row['device_profile'] != STREAM_PROFILE or row.get('host_profile_source_head') != V72_HOST_HEAD, 'stream task cannot claim old host publication')
        from builtin_init_profile import EXTRA_FIELDS
        require(all(re.fullmatch('[0-9a-f]{64}', row.get(k, '')) for k in EXTRA_FIELDS), 'minimal init pins missing')
    if row['device_profile'] == AFFINITY_PROFILE:
        require(row.get('host_profile_source_head') not in (V71_HOST_HEAD, V72_HOST_HEAD, V73_HOST_HEAD) and
                row.get('raw_input_binding') is False and row.get('original_fdt_digest_unavailable') is True,
                'affinity host/FDT non-claim binding differs')
    if row['device_profile'] == FDT_PROFILE:
        from early_fdt_binding import BOUNDARY, CAPACITY, REVISION, ALLOCATION
        require(row.get('host_profile_source_head') not in (V71_HOST_HEAD,V72_HOST_HEAD,V73_HOST_HEAD,V78_HOST_HEAD) and
                row.get('raw_input_binding') is False and row.get('fdt_capture_boundary') == BOUNDARY and
                type(row.get('fdt_snapshot_capacity_bytes')) is int and row['fdt_snapshot_capacity_bytes'] == CAPACITY and
                type(row.get('fdt_capture_revision')) is int and row['fdt_capture_revision'] == REVISION and
                row.get('fdt_allocation_form') == ALLOCATION and
                row.get('fdt_relative_placement_admitted') is True and row.get('source_head') == V81_IMAGE_HEAD and
                row.get('host_profile_source_head') not in (V81_IMAGE_HEAD,row.get('source_head')) and
                type(row.get('fdt_effective_host_admission')) is dict and
                row['fdt_effective_host_admission'].get('kind') == 'v81-revision2-effective-host-admission' and
                row['fdt_effective_host_admission'].get('eligible') is True and
                row['fdt_effective_host_admission'].get('producer_reported_eligible') is False and
                row['fdt_effective_host_admission'].get('image_source_head') == V81_IMAGE_HEAD,
                'FDT source/boundary/cap/nonclaim differs')
    if row['device_profile']==NATIVE_PROFILE:
        from native_memory_observation import STAGE,CAPACITY
        require(row.get('host_profile_source_head') not in (V71_HOST_HEAD,V72_HOST_HEAD,V73_HOST_HEAD,V78_HOST_HEAD,V81_IMAGE_HEAD,V81_HOST_HEAD) and
                row.get('raw_input_binding') is False and row.get('native_memory_stage')==STAGE and
                type(row.get('native_memory_capacity')) is int and row['native_memory_capacity']==CAPACITY and
                row.get('native_relative_placement_admitted') is True,'native stage/source/nonclaim binding differs')
    if row['device_profile'] == DATA_PROFILE:
        from kernel_readonly_input import is_candidate,candidate_scope
        if row.get('data_input_kind')=='kernel-readonly-span-candidate':
            from type3_admission import candidate_scope as type3_scope
            type3_scope(row,patched=True)
        elif is_candidate(row):
            candidate_scope(row)
            require(row.get('image_expectation_patched') is True and
                all(re.fullmatch('[0-9a-f]{64}',row.get(key,'')) for key in
                    ('data_manifest_sha256','data_carrier_sha256','data_payload_sha256')) and
                row.get('data_carrier_bytes')==10962166 and row.get('data_payload_bytes')==19136512,
                'readonly variant and unchanged external carrier binding required')
        else:
            from linux_data_carrier import STAGE, MODE, RANGE_SCHEMA, COMPARE_SCHEMA
            retained = (V97_PROFILE_ORIGIN_HEAD,V99_PROFILE_ORIGIN_HEAD,V100_PROFILE_ORIGIN_HEAD,
                        V88_HOST_HEAD,V89_IMAGE_HEAD,V89_HOST_HEAD,V90_IMAGE_HEAD,V90_HOST_HEAD,V91_IMAGE_HEAD)
            has_range = 'data_input_range_schema' in row or 'data_linked_kernel_bytes' in row
            if has_range:
                require(row.get('data_input_range_schema') == RANGE_SCHEMA and
                        row.get('data_compare_schema') == COMPARE_SCHEMA and
                        type(row.get('data_linked_kernel_bytes')) is int and 0 < row['data_linked_kernel_bytes'] < (1<<64) and
                        row.get('source_head') not in retained and row.get('host_profile_source_head') not in retained,
                        'new live range producer binding differs')
            else:
                require(row.get('host_profile_source_head') in retained, 'new DATA live range declaration missing')
            from linux_data_carrier import EARLY_SCHEMA
            early_retained=(*retained,V101_PROFILE_ORIGIN_HEAD)
            if 'data_early_prefix_schema' in row:
                require(row['data_early_prefix_schema']==EARLY_SCHEMA and has_range and
                        row.get('source_head') not in early_retained and row.get('host_profile_source_head') not in early_retained,
                        'new early prefix producer binding differs')
            else:
                require(row.get('host_profile_source_head') in early_retained, 'new DATA early prefix declaration missing')
            from linux_data_carrier import GROWTH_FIELDS, growth_declaration, growth_retained_heads
            growth_retained=growth_retained_heads()
            if any(key in row for key in GROWTH_FIELDS):
                growth_declaration(row)
                require(row.get('source_head') not in growth_retained and row.get('host_profile_source_head') not in growth_retained and
                        row.get('data_early_prefix_schema')==EARLY_SCHEMA and has_range,
                        'new normal growth producer binding differs')
            else:
                require(row.get('host_profile_source_head') in growth_retained,'new DATA growth declaration missing')
            if 'data_compare_schema' in row:
                from linux_data_carrier import COMPARE_SCHEMA, COMPARE_SCHEMA_V1
                if row['data_compare_schema'] == COMPARE_SCHEMA_V1:
                    require(row.get('source_head') == row.get('host_profile_source_head') == V99_PROFILE_ORIGIN_HEAD,
                            'v1 comparison requires exact retained v99 origin')
                else:
                    require(row['data_compare_schema'] == COMPARE_SCHEMA and
                            row.get('source_head') not in (V88_HOST_HEAD,V89_IMAGE_HEAD,V90_IMAGE_HEAD,V91_IMAGE_HEAD,V99_PROFILE_ORIGIN_HEAD),
                            'new DATA comparison producer binding differs')
            if row.get('source_head') == V90_IMAGE_HEAD:
                require(row.get('data_expectation_mode') == 'image-slot-v1' and row.get('image_expectation_patched') is True, 'historical Image expectation differs')
            elif row.get('source_head') not in (V88_HOST_HEAD,V89_IMAGE_HEAD):
                require(row.get('data_expectation_mode') == MODE and row.get('image_expectation_patched') is True and type(row.get('data_expectation_slot')) is dict, 'private Image expectation binding required')
            require(row.get('data_carrier_stage') == STAGE and row.get('data_relative_placement_admitted') is True and row.get('raw_input_binding') is False and
                all(re.fullmatch('[0-9a-f]{64}', row.get(k,'')) for k in ('data_manifest_sha256','data_carrier_sha256','data_payload_sha256')) and
                all(type(row.get(k)) is int and 0 < row[k] <= 64*1024*1024 for k in ('data_carrier_bytes','data_payload_bytes')), 'DATA package scope differs')
    if 'data_current_binding_sha256' in row or 'data_host_experiment' in row:
        from current_data_reuse import IMAGE_HEAD,MODE
        require(row['device_profile']==DATA_PROFILE and row.get('source_head')==IMAGE_HEAD and
            row.get('host_profile_source_head')!=IMAGE_HEAD and row.get('data_host_experiment')==MODE and
            re.fullmatch('[0-9a-f]{64}',row.get('data_current_binding_sha256','')), 'new current DATA host scope differs')
    if mode is None or mode in ('diagnostic', 'rollback'):
        diagnostic = mode in (None, 'diagnostic')
        require(row.get('auto_return_diagnostic') is diagnostic and
                (re.fullmatch('[0-9a-f]{32}', row.get('auto_cycle_token') or '') if diagnostic
                 else row.get('auto_cycle_token') is None), 'KAT package role/cycle differs')
        if 'mode' in row:
            require(row['mode'] == mode and row.get('test_purpose') ==
                    (('linux-data-carrier' if row['device_profile']==DATA_PROFILE else 'native-memory-observation' if row['device_profile']==NATIVE_PROFILE else 'early-fdt-binding' if row['device_profile'] == FDT_PROFILE else 'cpu-affinity-binding' if row['device_profile'] == AFFINITY_PROFILE else 'sha256-stream-state' if row['device_profile'] == STREAM_PROFILE else 'sha256-kat-builtin-init' if row['device_profile'] == BUILTIN_PROFILE else 'sha256-kat-recovery') if diagnostic else 'rollback'), 'KAT package purpose differs')
    else:
        raise ValueError('closed KAT package role required')


def pack(backup, kernel_build, official, mkbootimg, output, parts, token):
    from prepare_linux_boot import pack_verified
    build = variant(kernel_build, token)
    from retained_v108_origin import live
    live(build.get('host_profile_source_head'))
    return pack_verified(backup, kernel_build, official, mkbootimg, output, parts, build,
                         (kernel_build/'handoff.config').read_bytes(), token, kat_profile=True)


def prepare_plan(kernel_build, backup, twrp, mkbootimg, current_packages, output, cycles=1):
    from materialize_auto_cycle import materialize
    from prepare_linux_boot import prepare
    from build_boot_test_packages import build
    from stage_phase2 import verify_packages
    require(cycles == 1, 'KAT profile permits exactly one cycle')
    kernel_build, backup, output = private(kernel_build), private(backup), private(output)
    template = validate_template(kernel_build)
    from retained_v108_origin import live
    live(template.get('host_profile_source_head'))
    if template.get('data_input_kind')=='kernel-readonly-span-candidate':
        from type3_admission import require_plan_transaction
        require_plan_transaction(template,output)
    current_records = verify_packages(private(current_packages))
    current_diagnostic = next(r for r in current_records if r['mode'] == 'diagnostic')
    require(not output.exists(), 'fresh KAT plan required')
    output.mkdir(parents=True)
    cycle = uuid.uuid4().hex
    folder = output/'cycle-01'
    folder.mkdir()
    target = folder/'kernel-build'
    bound = materialize(kernel_build, target, cycle)
    boot = folder/'boot.img'
    prepare(backup, target, Path(twrp), Path(mkbootimg), boot, cycle)
    packages = folder/'packages'
    build(backup, boot, packages, private(current_packages))
    stage = dict(index=1, cycle=cycle, kernel_build=str(target), image_sha256=bound['image_sha256'],
                 build_result_sha256=sha(target/'build-result.json'), packages=str(packages),
                 package_result_sha256=sha(packages/'package-result.json'))
    plan = dict(schema=1, kind='note10-bounded-auto-cycle', device_profile=template['device_profile'],
                kernel_build=str(kernel_build), backup=str(backup),
                backup_manifest_sha256=sha(backup/'backup-manifest.json'),
                build_result_sha256=sha(kernel_build/'build-result.json'), image_sha256=template['image_sha256'],
                identity=template['build_evidence_id'], current_packages=str(private(current_packages)),
                current_package_result_sha256=sha(Path(current_packages)/'package-result.json'),
                reference_twrp=str(Path(twrp).resolve()), mkbootimg=str(Path(mkbootimg).resolve()), minimum_battery=10,
                return_timeout_seconds=240, stages=[stage])
    if template['device_profile'] in (BUILTIN_PROFILE, STREAM_PROFILE, AFFINITY_PROFILE, FDT_PROFILE, NATIVE_PROFILE, DATA_PROFILE):
        plan['current_boot_payload_sha256'] = current_diagnostic['payload_sha256']
    if template.get('data_input_kind')=='kernel-readonly-span-candidate':
        plan.update(execution_version=template['execution_version'],executing_host_source_head=template['host_profile_source_head'],type3_contract_sha256=template['type3_contract_sha256'])
    save(output/'plan.json', plan)
    validate_plan(output/'plan.json', sha(output/'plan.json'))
    return dict(plan=str(output/'plan.json'), plan_sha256=sha(output/'plan.json'), cycles=1, device_operations=[],
        kernel_readonly_IO_events=list(__import__('kernel_readonly_input').IO_EVENTS) if template.get('data_input_kind')=='kernel-readonly-candidate' else [])


def validate_plan(path, expected):
    from stage_phase2 import verify_packages
    from prepare_linux_boot import boot_header, read_verified_backup
    from prepare_linux_boot import TWRP_SHA256, MKBOOTIMG_SHA256
    from build_boot_test_packages import updater
    path = private(path)
    require(re.fullmatch('[0-9a-f]{64}', expected or '') and sha(path) == expected, 'reviewed KAT plan SHA required')
    plan = read(path)
    from kernel_readonly_input import PACKING_FIELDS
    packing_keys=set(PACKING_FIELDS) if any(key in plan for key in PACKING_FIELDS) else set()
    from type3_admission import PLAN_FIELDS
    type3_keys=set(PLAN_FIELDS) if any(key in plan for key in PLAN_FIELDS) else set()
    require(set(plan)-packing_keys-type3_keys == (PLAN_KEYS | {'current_boot_payload_sha256'} if plan.get('device_profile') in (BUILTIN_PROFILE, STREAM_PROFILE, AFFINITY_PROFILE, FDT_PROFILE, NATIVE_PROFILE, DATA_PROFILE) else PLAN_KEYS) and selected(plan) and plan.get('kind') == 'note10-bounded-auto-cycle' and
            type(plan.get('schema')) is int and plan['schema'] == 1 and
            type(plan.get('minimum_battery')) is int and type(plan.get('return_timeout_seconds')) is int and
            plan.get('minimum_battery') == 10 and plan.get('return_timeout_seconds') == 240 and
            len(plan.get('stages', [])) == 1, 'closed single-cycle KAT plan required')
    root, backup = private(plan['kernel_build']), private(plan['backup'])
    report = validate_template(root)
    if report.get('data_input_kind')=='kernel-readonly-span-candidate':
        require(type3_keys==set(PLAN_FIELDS) and plan['execution_version']==report['execution_version'] and
            plan['executing_host_source_head']==report['host_profile_source_head'] and plan['type3_contract_sha256']==report['type3_contract_sha256'],'type3 plan execution provenance differs')
    else:require(not type3_keys,'unrelated plan cannot claim type3 execution scope')
    require(sha(root/'build-result.json') == plan['build_result_sha256'] and
            report['image_sha256'] == plan['image_sha256'] and report['build_evidence_id'] == plan['identity'] and
            sha(backup/'backup-manifest.json') == plan['backup_manifest_sha256'], 'KAT plan template/backup changed')
    item = plan['stages'][0]
    require(set(item) == STAGE_KEYS and type(item.get('index')) is int, 'closed KAT stage schema required')
    bound = variant(private(item['kernel_build']), item['cycle'])
    require(all(plan.get(key)==bound.get(key) for key in PACKING_FIELDS) and
        bool(packing_keys)==any(key in bound for key in PACKING_FIELDS),'plan/resumed host packing binding differs')
    require(item['index'] == 1 and bound['auto_cycle_template'] == str(root) and
            sha(Path(item['kernel_build'])/'build-result.json') == item['build_result_sha256'] and
            bound['image_sha256'] == item['image_sha256'], 'KAT stage variant changed')
    packages = private(item['packages'])
    require(sha(packages/'package-result.json') == item['package_result_sha256'], 'KAT package manifest changed')
    records = verify_packages(packages)
    pair = read(packages/'package-result.json')
    package_scope(pair)
    require(all(pair.get(k) == bound[k] for k in fields(bound)) and pair['auto_cycle_token'] == item['cycle'] and
            pair['backup_manifest_sha256'] == plan['backup_manifest_sha256'] and
            pair['kernel_image_sha256'] == bound['image_sha256'], 'KAT pair/image/backup binding differs')
    previous = private(plan['current_packages'])
    require(sha(previous/'package-result.json') == plan['current_package_result_sha256'] and
            read(previous/'package-result.json')['backup_manifest_sha256'] == plan['backup_manifest_sha256'],
            'current BOOT package chain changed')
    previous_records = verify_packages(previous)
    prior = next(r for r in previous_records if r['mode'] == 'diagnostic')
    if plan['device_profile'] in (BUILTIN_PROFILE, STREAM_PROFILE, AFFINITY_PROFILE, FDT_PROFILE, NATIVE_PROFILE, DATA_PROFILE):
        prior_pair = read(previous/'package-result.json')
        from builtin_init_profile import current_boot_binding
        current_boot_binding(plan, prior_pair, prior)
    parts = read_verified_backup(backup)
    require(sha(plan['reference_twrp']) == TWRP_SHA256 and sha(plan['mkbootimg']) == MKBOOTIMG_SHA256,
            'private reference TWRP/mkbootimg input changed')
    official = Path(plan['reference_twrp']).read_bytes()
    require(parts['recovery'].startswith(official), 'paired recovery differs from reference')
    original_header, recovery_header = boot_header(parts['boot']), boot_header(official)
    rollback = next(r for r in records if r['mode'] == 'rollback')
    require(pair['expected_current_boot_sha256'] == prior['payload_sha256'] and
            prior['payload_size'] == len(parts['boot']) and
            rollback['payload_sha256'] == hashlib.sha256(parts['boot']).hexdigest() and
            rollback['payload_size'] == len(parts['boot']), 'paired rollback/current BOOT chain differs')
    import zipfile
    diagnostic = next(r for r in records if r['mode'] == 'diagnostic')
    baseline = read(backup/'backup-manifest.json')
    for record in records:
        require(record['payload_size'] == len(parts['boot']), 'full BOOT partition payload required')
        expected_writer = updater(mode=record['mode'], bootloader=baseline['bootloader'],
                                  partitions=baseline['partitions'], payload_sha=record['payload_sha256'],
                                  current_boot_sha=pair['expected_current_boot_sha256'],
                                  auto_return=record['mode'] == 'diagnostic', device_profile=plan['device_profile'])
        with zipfile.ZipFile(packages/record['file']) as archive:
            require(archive.read('META-INF/com/google/android/update-binary') == expected_writer,
                    'package differs from unchanged common BOOT writer')
            require(len(archive.read('boot.img')) == len(parts['boot']), 'actual padded BOOT size differs')
    with zipfile.ZipFile(packages/diagnostic['file']) as archive:
        payload = archive.read('boot.img')
        header = boot_header(payload)
    require(header['kernel_sha256'] == bound['image_sha256'] and 'n10.cycle=' not in header['cmdline'],
            'actual KAT BOOT kernel/cycle differs')
    expected_cmdline = recovery_header['cmdline']
    if plan['device_profile'] == DATA_PROFILE:
        from linux_data_carrier import data_cmdline, MODE, BOOT_PAGE
        if pair.get('data_expectation_mode') in (MODE,'kernel-readonly-candidate-v1','kernel-readonly-span-candidate-v1'):
            require(header['page_size'] == BOOT_PAGE and pair['data_expectation_slot'].get('boot_page') == BOOT_PAGE, 'trusted logical DATA BOOT-page policy differs')
        if pair.get('data_expectation_mode') not in (MODE,'image-slot-v1','kernel-readonly-candidate-v1','kernel-readonly-span-candidate-v1'):
            expected_cmdline = data_cmdline(expected_cmdline,pair['data_carrier_sha256'])
    require(all(header[k] == original_header[k] for k in
                ('name', 'os_version', 'security_patch_month', 'kernel_addr', 'tags_addr', 'page_size')) and
            header['header_version'] == recovery_header['header_version'] == 1 and
            header['recovery_dtbo_size'] == header['second_size'] == 0 and
            header['cmdline'] == expected_cmdline and
            header['ramdisk_addr'] == recovery_header['ramdisk_addr'] and
            header['arm64_text_offset'] == recovery_header['arm64_text_offset'],
            'actual BOOT metadata/bootloader command line differs')
    ramdisk = official[recovery_header['ramdisk_file_offset']:
                       recovery_header['ramdisk_file_offset']+recovery_header['ramdisk_size']]
    actual_ramdisk = payload[header['ramdisk_file_offset']:header['ramdisk_file_offset']+header['ramdisk_size']]
    if plan['device_profile'] == DATA_PROFILE:
        if pair.get('data_input_kind')=='kernel-readonly-span-candidate':
            from type3_admission import candidate_scope as type3_scope
            type3_scope(pair,patched=True)
            require(len(ramdisk)==pair['data_carrier_bytes']==10962166 and len(actual_ramdisk)==4440064 and
                hashlib.sha256(actual_ramdisk).hexdigest()==pair['type3_compact_sha256'],'actual typed class3 compact external carrier differs')
        elif pair.get('kernel_readonly_external_choice')=='compact-v1':
            from kernel_readonly_input import packing_scope, CAPACITY, OLD_BYTES
            packing_scope(pair)
            require(len(ramdisk)==pair['data_carrier_bytes']==OLD_BYTES and len(actual_ramdisk)==CAPACITY and
                hashlib.sha256(actual_ramdisk).hexdigest()==pair['kernel_readonly_compact_sha256'],
                'actual explicit compact external carrier differs')
        else:
            require(len(actual_ramdisk) == len(ramdisk) == pair['data_carrier_bytes'] and hashlib.sha256(actual_ramdisk).hexdigest() == pair['data_carrier_sha256'], 'actual fixed DATA carrier differs')
    else:
        require(ramdisk and actual_ramdisk == ramdisk, 'actual external TWRP ramdisk differs')
    end, trailer = header['second_file_offset'], b'SEANDROIDENFORCE'
    require(payload[end:end+len(trailer)] == trailer and not any(payload[end+len(trailer):]),
            'Samsung trailer/full-partition zero padding differs')
    return plan


def precheck(packages, kernel_build, backup, adb, staged, *, ack_kernel_readonly_growth=False,battery_policy=None,receipt_path=None,type3_context=None):
    from run_probe import preflight
    from stage_phase2 import verify_packages
    from prepare_linux_boot import read_verified_backup
    from precheck_window_access import require_install_battery,validate_install_battery_policy,require_battery_policy_scope
    from auto_cycle import verify_partitions
    from prepare_linux_boot import boot_header
    import zipfile
    packages, kernel_build, backup = private(packages), private(kernel_build), private(backup)
    battery_policy=validate_install_battery_policy(battery_policy)
    target=private(receipt_path) if receipt_path is not None else packages/'PREINSTALL-CHECK.json'
    if battery_policy['five_percent_exception']:
        require(receipt_path is not None and not target.exists() and not target.is_relative_to(packages),
            'temporary exception requires a fresh journal receipt; preserve stopped precheck')
    report = dict(ready_for_manual_access_test=False, device_profile=read(packages/'package-result.json').get('device_profile'),
                  partition_writes=False, rebooted=False,
                  partition_evidence=dict(phase='preinstall',status='not-started',node_size_rows=[]),
                  battery_policy=battery_policy,declared_minimum_battery=10,
                  effective_minimum_battery=battery_policy['effective_minimum_percent'])
    active_node=None
    save(target, report)
    try:
        records = verify_packages(packages)
        pair = read(packages/'package-result.json')
        package_scope(pair)
        from kernel_readonly_input import require_device_scope
        from type3_admission import require_context_directory
        require_context_directory(type3_context,packages)
        require_device_scope(pair,ack_kernel_readonly_growth,type3_context=type3_context)
        require_battery_policy_scope(battery_policy,pair,ack_kernel_readonly_growth)
        bound = variant(kernel_build, pair['auto_cycle_token'])
        require(all(pair.get(k) == bound[k] for k in fields(bound)) and
                pair['kernel_image_sha256'] == bound['image_sha256'] and
                pair['backup_manifest_sha256'] == sha(backup/'backup-manifest.json'), 'preinstall KAT binding differs')
        read_verified_backup(backup)
        state = preflight(adb)
        battery = int(adb.text('shell', 'cat', '/sys/class/power_supply/battery/capacity'))
        report['observed_battery_percent']=battery
        require_install_battery(battery,policy=battery_policy)
        require(staged.get('native_archive_read_verified') is True and
                staged.get('packages') == [r['file'] for r in records], 'current RAM stage binding missing')
        remote = staged['ram_directory']
        require(re.fullmatch('/tmp/note10-phase2-[0-9a-f]{8}', remote), 'bounded current RAM stage required')
        baseline = read(backup/'backup-manifest.json')
        for part in baseline['partitions']:
            active_node=dict(partition=part.get('partition'),expected_canonical_node=part.get('block_node'),
                expected_size_bytes=part.get('size'),observed_canonical_node=None,observed_size_bytes=None,
                observed_size_text=None,status='reading-node')
            report['partition_evidence']['node_size_rows'].append(active_node)
            observed_node=adb.text('shell', 'readlink', '-f', '/dev/block/by-name/'+part['partition'])
            active_node.update(observed_canonical_node=observed_node[:256],node_observation_complete=len(observed_node)<=256)
            matched=observed_node==part['block_node']
            if matched:
                active_node['status']='reading-size'
                observed_size=adb.text('shell', 'blockdev', '--getsize64', part['block_node'])
                active_node.update(observed_size_text=observed_size[:128],size_observation_complete=len(observed_size)<=128,
                    observed_size_bytes=int(observed_size) if observed_size.isascii() and observed_size.isdecimal() and len(observed_size)<=20 else None)
                matched=observed_size==str(part['size'])
            active_node['status']='passed' if matched else 'mismatch'
            require(matched, 'paired partition node/size changed')
            active_node=None
        verify_partitions(adb, backup, pair['expected_current_boot_sha256'],evidence=report['partition_evidence'])
        for record in records:
            with zipfile.ZipFile(packages/record['file']) as archive:
                script = archive.read('META-INF/com/google/android/update-binary')
                header = boot_header(archive.read('boot.img')) if record['mode'] == 'diagnostic' else None
            syntax = subprocess.run([adb.executable, '-s', adb.serial, 'shell', '-T', 'sh', '-n'],
                                    input=script, capture_output=True, timeout=30)
            require(syntax.returncode == 0 and
                    adb.text('shell', 'sha256sum', remote+'/'+record['file']).split()[0] == record['sha256'],
                    'native updater syntax/RAM ZIP binding failed')
            if header is not None:
                require(header['kernel_sha256'] == bound['image_sha256'], 'staged KAT BOOT kernel differs')
        report.update(ready_for_manual_access_test=True, current_device_checks_pending=False,
                      battery_percent=battery, twrp_version=state['twrp_version'], ram_directory=remote)
        return report
    except BaseException as error:
        if active_node is not None:
            if active_node['status']!='mismatch':active_node['status']='error'
            active_node['error_type']=type(error).__name__
            report['partition_evidence']['status']=active_node['status']
        report['partition_evidence']['precheck_error_type']=type(error).__name__
        raise
    finally:
        save(target, report)


def decode_selected(data, banner, identity, cycle, *, digest_decoder=None, component_evidence=None):
    from decode_auto_return import select_cycle_log, decode as decode_return
    if digest_decoder is None:
        from decode_sha256_runtime_kat import decode as digest_decoder
    starts = list(re.finditer(rb'(?m)^[ \t]*(?:<[0-9]+>)?\[\s*0\.000000\][^\r\n]*?(Linux version [^\r\n]*)', data))
    require(starts and starts[-1][1] == banner.encode('ascii'), 'latest self-contained boot banner required')
    selected_boot = data[starts[-1].start():]
    clipped, offset = select_cycle_log(selected_boot, identity, cycle)
    recovery = decode_return(clipped, identity, cycle)
    if component_evidence is not None:
        component_evidence['auto_return_records'] = recovery
        component_evidence['return_validation'] = 'validated_request_records'
    kat = digest_decoder(clipped.decode('ascii', errors='replace'), identity)
    require(kat['passed'], 'current-cycle KAT did not pass')
    return clipped, dict(kat=kat, auto_return=recovery, boot_byte_start=starts[-1].start(), cycle_byte_start=offset)


def log_probe_command(remote):
    require(remote in ('/proc/last_kmsg', '/sys/fs/pstore/console-ramoops-0',
                       '/sys/fs/pstore/dmesg-ramoops-0'), 'fixed log probe path required')
    # Only test status1 is definitive absent/unreadable. Status>1 remains a
    # failing remote command; transport errors are never converted to absence.
    return ("[ -r '"+remote+"' ]; n10_probe_status=$?; "
            'case "$n10_probe_status" in '
            "0) printf 'N10KAT_READABLE\\n';; "
            "1) printf 'N10KAT_ABSENT\\n';; "
            '*) exit "$n10_probe_status";; esac')


def collect(packages, kernel_build, adb, capture_parent=None, *, ack_kernel_readonly_growth=False,type3_context=None):
    # Return a failed observation after retaining raw logs, rather than raising
    # past run_plan's common post-return five-partition verification.
    from kernel_readonly_input import require_device_scope
    from type3_admission import require_context_directory
    require_context_directory(type3_context,packages)
    require_device_scope(read(Path(packages)/'package-result.json'),ack_kernel_readonly_growth,type3_context=type3_context)
    parent = private(capture_parent or ROOT/'note10/private/device-observations')
    out = private(parent/('kat-test-'+uuid.uuid4().hex[:12]))
    out.mkdir(parents=True)
    try:
        return _collect_into(packages, kernel_build, adb, out,ack_kernel_readonly_growth=ack_kernel_readonly_growth,type3_context=type3_context)
    except Exception as error:
        index = read(out/'capture-index.json') if (out/'capture-index.json').is_file() else {}
        failed = dict(directory=str(out), device_profile=read(Path(packages)/'package-result.json').get('device_profile'), diagnostic_passed=False,
                      log_selections={}, logs_sha256=index.get('logs_sha256', {}), error=str(error),
                      partition_writes=False, rebooted=False, xnu_executed=False,
                      legacy_evaluations_claimed=False, hardware_return_proven_by_frames=False)
        save(out/'result.json', failed)
        return failed


def _collect_into(packages, kernel_build, adb, out, *, ack_kernel_readonly_growth=False,type3_context=None):
    from run_probe import preflight
    from stage_phase2 import verify_packages
    verify_packages(private(packages))
    pair = read(Path(packages)/'package-result.json')
    from kernel_readonly_input import require_device_scope
    from type3_admission import require_context_directory
    require_context_directory(type3_context,packages)
    require_device_scope(pair,ack_kernel_readonly_growth,type3_context=type3_context)
    bound = variant(private(kernel_build), pair['auto_cycle_token'])
    require(all(pair.get(k) == bound[k] for k in fields(bound)), 'collection profile binding differs')
    preflight(adb)
    if bound['device_profile'] in (BUILTIN_PROFILE, STREAM_PROFILE, AFFINITY_PROFILE, FDT_PROFILE, NATIVE_PROFILE, DATA_PROFILE):
        from builtin_init_profile import snapshot
        decode_fn = None
        if bound['device_profile'] == STREAM_PROFILE:
            from sha256_stream_state import decode_selected as decode_fn
        elif bound['device_profile'] == DATA_PROFILE:
            if bound.get('data_input_kind')=='kernel-readonly-span-candidate':
                from kernel_readonly_span_candidate import decode_selected as data_decode
            elif bound.get('data_input_kind')=='kernel-readonly-candidate':
                from kernel_readonly_input import decode_selected as data_decode
            else:
                from linux_data_carrier import decode_selected as data_decode
            decode_fn = lambda *args: data_decode(*args, expected=bound)
        elif bound['device_profile'] == NATIVE_PROFILE:
            from native_memory_observation import decode_selected as decode_fn
        elif bound['device_profile'] == FDT_PROFILE:
            from early_fdt_binding import decode_selected as decode_fn
        elif bound['device_profile'] == AFFINITY_PROFILE:
            from affinity_binding import decode_selected as decode_fn
        return snapshot(adb, out, bound, pair['auto_cycle_token'], decode_fn=decode_fn)
    selections, observations, raw_hashes = {}, [], {}
    for name, remote in (('last_kmsg.txt', '/proc/last_kmsg'),
                         ('console-ramoops-0', '/sys/fs/pstore/console-ramoops-0'),
                         ('dmesg-ramoops-0', '/sys/fs/pstore/dmesg-ramoops-0')):
        probe = adb.call('shell', '-T', log_probe_command(remote))
        if probe == b'N10KAT_ABSENT\n':
            continue
        require(probe == b'N10KAT_READABLE\n', 'log probe did not return an explicit readable/absent result')
        # Any probe command/transport failure or cat failure propagates to the
        # failed-observation wrapper; no later passing source can hide it.
        data = adb.call('exec-out', 'cat', remote, timeout=60)
        require(0 < len(data) <= 16*1024*1024, 'raw log bound invalid')
        (out/name).write_bytes(data)
        raw_hashes[name] = hashlib.sha256(data).hexdigest()
        save(out/'capture-index.json', {'logs_sha256': raw_hashes, 'device_profile': PROFILE})
        # An unrelated stale file cannot supply evidence. Any current-token file
        # must pass in isolation; never hide its failure behind another log.
        if pair['auto_cycle_token'].encode() not in data:
            continue
        try:
            clipped, observation = decode_selected(data, bound['kernel_banner'], bound['build_evidence_id'], pair['auto_cycle_token'])
        except ValueError as error:
            save(out/'failure.json', {'diagnostic_passed': False, 'error': str(error), 'logs_sha256': raw_hashes})
            raise ValueError('current-cycle KAT evidence failed; capture='+str(out)) from error
        selected_file = 'selected-'+name
        (out/selected_file).write_bytes(clipped)
        selections[name] = dict(selected_file=selected_file, selected_sha256=hashlib.sha256(clipped).hexdigest())
        observations.append(observation)
    require(observations and all(o['kat'] == observations[0]['kat'] and o['auto_return'] == observations[0]['auto_return']
                                 for o in observations), 'no agreeing current-cycle KAT/recovery evidence')
    report = dict(directory=str(out), device_profile=PROFILE, diagnostic_passed=True,
                  log_selections=selections, logs_sha256=raw_hashes, observations=observations,
                  partition_writes=False, rebooted=False, xnu_executed=False,
                  legacy_evaluations_claimed=False, hardware_return_proven_by_frames=False)
    save(out/'result.json', report)
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--accepted-result-sha256', required=True)
    parser.add_argument('--source-head', required=True)
    receipt_mode = parser.add_mutually_exclusive_group(required=True)
    receipt_mode.add_argument('--root-receipt', type=Path)
    receipt_mode.add_argument('--ci-success-context', type=Path)
    parser.add_argument('--root-receipt-sha256')
    parser.add_argument('--ci-success-context-sha256')
    parser.add_argument('--host-source-head', required=True)
    parser.add_argument('--carrier-manifest', type=Path)
    parser.add_argument('--carrier-manifest-sha256')
    parser.add_argument('--readonly-compact-manifest',type=Path)
    parser.add_argument('--readonly-compact-manifest-sha256')
    args = parser.parse_args()
    print(json.dumps(prepare_template(args.build, args.output, args.accepted_result_sha256, args.source_head,
        root_receipt=args.root_receipt, root_receipt_sha256=args.root_receipt_sha256,
        host_source_head=args.host_source_head, ci_success_context=args.ci_success_context,
        ci_success_context_sha256=args.ci_success_context_sha256, carrier_manifest=args.carrier_manifest,
        carrier_manifest_sha256=args.carrier_manifest_sha256,readonly_compact_manifest=args.readonly_compact_manifest,
        readonly_compact_manifest_sha256=args.readonly_compact_manifest_sha256), indent=2))
