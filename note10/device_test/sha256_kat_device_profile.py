"""Closed KAT-only bindings. Reuse existing packer/writer/journal; no new actuator."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
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
    require(result.get('PC_only') is not True and result.get('diagnostic_kind') not in ('owned-contiguous-staging-pc','current-owned-staging-pc'), 'PC-only owned staging cannot create a physical template/package')


def raw_binding(root, expected_result, expected_source, *, producing_sources=None):
    root = private(root)
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
    data = result.get('version') in ('v88','v89','v90','v91')
    native = result.get('version') == 'v82'
    builtin = result.get('version') in ('v72', 'v73', 'v78', 'v81', 'v82', 'v88', 'v89', 'v90', 'v91')
    marker = DATA_PROFILE if data else NATIVE_PROFILE if native else FDT_PROFILE if fdt else AFFINITY_PROFILE if affinity else STREAM_PROFILE if stream else BUILTIN_PROFILE if builtin else PROFILE
    require(result.get('version') in ('v71', 'v72', 'v73', 'v78', 'v81', 'v82', 'v88', 'v89', 'v90', 'v91') and result.get('passed') is True and
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
    require(not data or result.get('diagnostic_kind') == 'linux-data-carrier', 'new DATA task required')
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
            all(x in image for x in (b'N10RET1', b'N10DATA1' if data else b'N10MEMARGS1' if native else b'N10FDT1' if fdt else b'N10AFF1' if affinity else b'N10SHASTREAM1' if stream else b'N10SHA1')) and
            (not stream or b'N10SHA1' not in image) and
            (not (affinity or fdt) or not any(marker in image for marker in (b'N10SHA1', b'N10SHASTREAM1'))) and
            (not fdt or b'N10AFF1' not in image) and
            (not native or not any(x in image for x in (b'N10SHA1',b'N10SHASTREAM1',b'N10AFF1',b'N10FDT1'))) and
            (not data or not any(x in image for x in (b'N10SHA1',b'N10SHASTREAM1',b'N10AFF1',b'N10FDT1',b'N10MEMARGS1'))), 'Image evidence identity differs')
    banners = re.findall((rb'Linux version 4\.14\.113-v91-trusted-logical [^\x00\r\n]+' if result.get('version') == 'v91' else rb'Linux version 4\.14\.113-v90-image-expectation [^\x00\r\n]+' if result.get('version') == 'v90' else rb'Linux version 4\.14\.113-v89-data-guard [^\x00\r\n]+' if result.get('version') == 'v89' else rb'Linux version 4\.14\.113-v88-linux-data [^\x00\r\n]+' if data else rb'Linux version 4\.14\.113-v82-native-memory [^\x00\r\n]+' if native else rb'Linux version 4\.14\.113-v81-early-fdt [^\x00\r\n]+' if fdt else rb'Linux version 4\.14\.113-v78-cpu-affinity [^\x00\r\n]+' if affinity else rb'Linux version 4\.14\.113-v73-sha256-stream [^\x00\r\n]+' if stream else rb'Linux version 4\.14\.113-v72-builtin-init [^\x00\r\n]+' if builtin else rb'Linux version 4\.14\.113-v71-sha256-recovery [^\x00\r\n]+'), image)
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
        extra = input_binding(root, result, image, lines, fdt_owned_route=fdt,native_memory_route=native,data_carrier_route=data,producing_sources=producing_sources)
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


def host_binding(source_head):
    require(re.fullmatch('[0-9a-f]{40}', source_head or ''), 'exact host-profile publication source pin required')
    pins = V71_HOST_PINS if source_head == V71_HOST_HEAD else V72_HOST_PINS if source_head == V72_HOST_HEAD else V73_HOST_PINS if source_head == V73_HOST_HEAD else V78_HOST_PINS if source_head == V78_HOST_HEAD else V81_IMAGE_HOST_PINS if source_head == V81_IMAGE_HEAD else V81_HOST_PINS if source_head == V81_HOST_HEAD else V82_HOST_PINS if source_head == V82_HOST_HEAD else V88_HOST_PINS if source_head == V88_HOST_HEAD else V89_HOST_PINS if source_head == V89_HOST_HEAD else V90_HOST_PINS if source_head == V90_HOST_HEAD else V91_HOST_PINS if source_head == V91_HOST_HEAD else {
        'note10/device_test/'+name: sha(Path(__file__).parent/name)
        for name in (*HOST_SOURCES, 'builtin_init_profile.py', 'builtin_init_route.py', 'test_builtin_init_route.py',
                     'sha256_stream_state.py', 'sha256_stream_vectors.json', 'test_sha256_stream_state.py',
                     'affinity_binding.py', 'test_affinity_binding.py', 'test_affinity_ci_context.py',
                     'test_partition_gate_evidence.py', 'early_fdt_binding.py', 'test_early_fdt_binding.py', 'test_early_fdt_host_route.py', 'native_memory_observation.py', 'test_native_memory_observation.py',
                      'linux_data_carrier.py', 'linux_data_carrier.c', 'linux_data_carrier_composition.c',
                      'test_linux_data_carrier.py', 'linux_data_carrier_fixture.c', 'carrier_lzma.c', 'carrier_lzma.h',
                      'linux_data_compare_evidence.h', 'linux_data_compare_evidence_fixture.c', 'test_v99_carrier_compare_evidence.py')}
    return dict(host_profile_source_head=source_head, host_profile_source_sha256=dict(pins))


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
    require(producer.get('version') == ('v91' if binding['device_profile']==DATA_PROFILE else 'v82' if binding['device_profile']==NATIVE_PROFILE else 'v81' if binding['device_profile']==FDT_PROFILE else 'v78') and
            producer.get('diagnostic_kind') == ('linux-data-carrier' if binding['device_profile']==DATA_PROFILE else 'native-memory-observation' if binding['device_profile']==NATIVE_PROFILE else 'early-fdt-binding' if binding['device_profile']==FDT_PROFILE else 'cpu-affinity-binding') and
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
            binding['kernel_banner'].startswith('Linux version 4.14.113-v91-trusted-logical ' if binding['device_profile']==DATA_PROFILE else 'Linux version 4.14.113-v82-native-memory ' if binding['device_profile']==NATIVE_PROFILE else 'Linux version 4.14.113-v81-early-fdt ' if binding['device_profile']==FDT_PROFILE else 'Linux version 4.14.113-v78-cpu-affinity '),
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
                     ci_success_context_sha256=None, carrier_manifest=None, carrier_manifest_sha256=None, producing_sources=None):
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
    binding.update(host_binding(host_source_head))
    shutil.copytree(build, output)
    if binding['device_profile'] == DATA_PROFILE:
        from linux_data_carrier import attach_carrier
        binding.update(attach_carrier(output, carrier_manifest, carrier_manifest_sha256))
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
                device_operations=[], deployment_ready=False)


def validate_template(root):
    root = private(root)
    binding = read(root/'device-profile.json')
    require(selected(binding), 'closed KAT profile required')
    context=None
    if 'data_current_binding_sha256' in binding or 'data_host_experiment' in binding:
        from current_data_reuse import load_record
        context=load_record(root,binding)
    measured = raw_binding(root, binding['accepted_result_sha256'], binding['source_head'],producing_sources=context)
    if binding['device_profile'] == DATA_PROFILE:
        from linux_data_carrier import carrier_fields
        measured.update(carrier_fields(root))
    if context is not None:
        context.check_carrier(measured)
        measured.update(data_current_binding_sha256=binding['data_current_binding_sha256'],data_host_experiment=binding['data_host_experiment'])
    measured.update(root_receipt_binding(root, root/'image-root-receipt.json', binding['image_root_receipt_sha256'], measured))
    measured.update(host_binding(binding['host_profile_source_head']))
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
    return {key: row[key] for key in keys}


def package_scope(row, mode=None):
    require(selected(row), 'KAT package profile missing')
    no_legacy(row)
    for key in ('profile_sha256', 'accepted_result_sha256', 'image_root_receipt_sha256', 'root_reader_result_sha256'):
        require(re.fullmatch('[0-9a-f]{64}', row.get(key, '')), 'KAT package result/profile pin missing')
    require(re.fullmatch('[0-9a-f]{32}', row.get('build_evidence_id', '')) and
            row.get('kernel_banner', '').startswith(('Linux version 4.14.113-v88-linux-data ' if row.get('source_head') == V88_HOST_HEAD else 'Linux version 4.14.113-v89-data-guard ' if row.get('source_head') == V89_IMAGE_HEAD else 'Linux version 4.14.113-v90-image-expectation ' if row.get('source_head') == V90_IMAGE_HEAD else 'Linux version 4.14.113-v91-trusted-logical ') if row['device_profile']==DATA_PROFILE else 'Linux version 4.14.113-v82-native-memory ' if row['device_profile']==NATIVE_PROFILE else 'Linux version 4.14.113-v81-early-fdt ' if row['device_profile'] == FDT_PROFILE else 'Linux version 4.14.113-v78-cpu-affinity ' if row['device_profile'] == AFFINITY_PROFILE else 'Linux version 4.14.113-v73-sha256-stream ' if row['device_profile'] == STREAM_PROFILE else 'Linux version 4.14.113-v72-builtin-init ' if row['device_profile'] == BUILTIN_PROFILE else 'Linux version 4.14.113-v71-sha256-recovery '),
            'KAT package identity missing')
    require(re.fullmatch('[0-9a-f]{40}', row.get('source_head', '')) and
            re.fullmatch('[0-9a-f]{40}', row.get('host_profile_source_head', '')) and
            row.get('host_profile_source_sha256') == host_binding(row['host_profile_source_head'])['host_profile_source_sha256'],
            'host-profile code identity differs')
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
        from linux_data_carrier import STAGE, MODE
        if 'data_compare_schema' in row:
            from linux_data_carrier import COMPARE_SCHEMA
            require(row['data_compare_schema'] == COMPARE_SCHEMA and
                    row.get('source_head') not in (V88_HOST_HEAD,V89_IMAGE_HEAD,V90_IMAGE_HEAD,V91_IMAGE_HEAD),
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
    save(output/'plan.json', plan)
    validate_plan(output/'plan.json', sha(output/'plan.json'))
    return dict(plan=str(output/'plan.json'), plan_sha256=sha(output/'plan.json'), cycles=1, device_operations=[])


def validate_plan(path, expected):
    from stage_phase2 import verify_packages
    from prepare_linux_boot import boot_header, read_verified_backup
    from prepare_linux_boot import TWRP_SHA256, MKBOOTIMG_SHA256
    from build_boot_test_packages import updater
    path = private(path)
    require(re.fullmatch('[0-9a-f]{64}', expected or '') and sha(path) == expected, 'reviewed KAT plan SHA required')
    plan = read(path)
    require(set(plan) == (PLAN_KEYS | {'current_boot_payload_sha256'} if plan.get('device_profile') in (BUILTIN_PROFILE, STREAM_PROFILE, AFFINITY_PROFILE, FDT_PROFILE, NATIVE_PROFILE, DATA_PROFILE) else PLAN_KEYS) and selected(plan) and plan.get('kind') == 'note10-bounded-auto-cycle' and
            type(plan.get('schema')) is int and plan['schema'] == 1 and
            type(plan.get('minimum_battery')) is int and type(plan.get('return_timeout_seconds')) is int and
            plan.get('minimum_battery') == 10 and plan.get('return_timeout_seconds') == 240 and
            len(plan.get('stages', [])) == 1, 'closed single-cycle KAT plan required')
    root, backup = private(plan['kernel_build']), private(plan['backup'])
    report = validate_template(root)
    require(sha(root/'build-result.json') == plan['build_result_sha256'] and
            report['image_sha256'] == plan['image_sha256'] and report['build_evidence_id'] == plan['identity'] and
            sha(backup/'backup-manifest.json') == plan['backup_manifest_sha256'], 'KAT plan template/backup changed')
    item = plan['stages'][0]
    require(set(item) == STAGE_KEYS and type(item.get('index')) is int, 'closed KAT stage schema required')
    bound = variant(private(item['kernel_build']), item['cycle'])
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
        if pair.get('data_expectation_mode') == MODE:
            require(header['page_size'] == BOOT_PAGE and pair['data_expectation_slot'].get('boot_page') == BOOT_PAGE, 'trusted logical DATA BOOT-page policy differs')
        if pair.get('data_expectation_mode') not in (MODE,'image-slot-v1'):
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
        require(len(actual_ramdisk) == len(ramdisk) == pair['data_carrier_bytes'] and hashlib.sha256(actual_ramdisk).hexdigest() == pair['data_carrier_sha256'], 'actual fixed DATA carrier differs')
    else:
        require(ramdisk and actual_ramdisk == ramdisk, 'actual external TWRP ramdisk differs')
    end, trailer = header['second_file_offset'], b'SEANDROIDENFORCE'
    require(payload[end:end+len(trailer)] == trailer and not any(payload[end+len(trailer):]),
            'Samsung trailer/full-partition zero padding differs')
    return plan


def precheck(packages, kernel_build, backup, adb, staged):
    from run_probe import preflight
    from stage_phase2 import verify_packages
    from prepare_linux_boot import read_verified_backup
    from precheck_window_access import require_install_battery
    from auto_cycle import verify_partitions
    from prepare_linux_boot import boot_header
    import zipfile
    packages, kernel_build, backup = private(packages), private(kernel_build), private(backup)
    report = dict(ready_for_manual_access_test=False, device_profile=read(packages/'package-result.json').get('device_profile'),
                  partition_writes=False, rebooted=False,
                  partition_evidence=dict(phase='preinstall',status='not-started',node_size_rows=[]))
    active_node=None
    save(packages/'PREINSTALL-CHECK.json', report)
    try:
        records = verify_packages(packages)
        pair = read(packages/'package-result.json')
        package_scope(pair)
        bound = variant(kernel_build, pair['auto_cycle_token'])
        require(all(pair.get(k) == bound[k] for k in fields(bound)) and
                pair['kernel_image_sha256'] == bound['image_sha256'] and
                pair['backup_manifest_sha256'] == sha(backup/'backup-manifest.json'), 'preinstall KAT binding differs')
        read_verified_backup(backup)
        state = preflight(adb)
        battery = int(adb.text('shell', 'cat', '/sys/class/power_supply/battery/capacity'))
        require_install_battery(battery)
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
        save(packages/'PREINSTALL-CHECK.json', report)


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


def collect(packages, kernel_build, adb, capture_parent=None):
    # Return a failed observation after retaining raw logs, rather than raising
    # past run_plan's common post-return five-partition verification.
    parent = private(capture_parent or ROOT/'note10/private/device-observations')
    out = private(parent/('kat-test-'+uuid.uuid4().hex[:12]))
    out.mkdir(parents=True)
    try:
        return _collect_into(packages, kernel_build, adb, out)
    except Exception as error:
        index = read(out/'capture-index.json') if (out/'capture-index.json').is_file() else {}
        failed = dict(directory=str(out), device_profile=read(Path(packages)/'package-result.json').get('device_profile'), diagnostic_passed=False,
                      log_selections={}, logs_sha256=index.get('logs_sha256', {}), error=str(error),
                      partition_writes=False, rebooted=False, xnu_executed=False,
                      legacy_evaluations_claimed=False, hardware_return_proven_by_frames=False)
        save(out/'result.json', failed)
        return failed


def _collect_into(packages, kernel_build, adb, out):
    from run_probe import preflight
    from stage_phase2 import verify_packages
    verify_packages(private(packages))
    pair = read(Path(packages)/'package-result.json')
    bound = variant(private(kernel_build), pair['auto_cycle_token'])
    require(all(pair.get(k) == bound[k] for k in fields(bound)), 'collection profile binding differs')
    preflight(adb)
    if bound['device_profile'] in (BUILTIN_PROFILE, STREAM_PROFILE, AFFINITY_PROFILE, FDT_PROFILE, NATIVE_PROFILE, DATA_PROFILE):
        from builtin_init_profile import snapshot
        decode_fn = None
        if bound['device_profile'] == STREAM_PROFILE:
            from sha256_stream_state import decode_selected as decode_fn
        elif bound['device_profile'] == DATA_PROFILE:
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
    args = parser.parse_args()
    print(json.dumps(prepare_template(args.build, args.output, args.accepted_result_sha256, args.source_head,
        root_receipt=args.root_receipt, root_receipt_sha256=args.root_receipt_sha256,
        host_source_head=args.host_source_head, ci_success_context=args.ci_success_context,
        ci_success_context_sha256=args.ci_success_context_sha256, carrier_manifest=args.carrier_manifest,
        carrier_manifest_sha256=args.carrier_manifest_sha256), indent=2))
