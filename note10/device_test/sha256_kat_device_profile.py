"""Closed KAT-only bindings. Reuse existing packer/writer/journal; no new actuator."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import uuid

PROFILE = 'sha256-kat-recovery-v1'
BUILTIN_PROFILE = 'sha256-kat-builtin-init-v2'
ROOT = Path(__file__).resolve().parents[2]
SLOT = b'N10_CYCLE_SLOT_UNSET_0123456789A'
FIELDS = ('device_profile', 'profile_sha256', 'build_evidence_id', 'kernel_banner', 'accepted_result_sha256',
          'source_head', 'image_root_receipt_sha256', 'root_reader_result_sha256',
          'host_profile_source_head', 'host_profile_source_sha256')
HOST_SOURCES = ('sha256_kat_device_profile.py', 'test_sha256_kat_device_profile.py',
                'materialize_auto_cycle.py', 'prepare_linux_boot.py', 'build_boot_test_packages.py',
                'stage_phase2.py', 'auto_cycle.py')
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
    require(marker in (None, PROFILE, BUILTIN_PROFILE), 'unknown device profile')
    return marker in (PROFILE, BUILTIN_PROFILE)


def no_legacy(row):
    require(not any(row.get(k) for k in LEGACY), 'KAT profile cannot claim legacy evaluations')
    for key, value in row.items():
        if key.endswith(('_diagnostic', '_audit', '_restore')) and key != 'auto_return_diagnostic':
            require(not value, 'KAT profile contains unrelated diagnostic scope: '+key)


def raw_binding(root, expected_result, expected_source):
    root = private(root)
    require(re.fullmatch('[0-9a-f]{64}', expected_result or '') and
            re.fullmatch('[0-9a-f]{40}', expected_source or ''), 'exact accepted result/source pins required')
    require(sha(root/'result.json') == expected_result, 'accepted CI result changed')
    result = read(root/'result.json')
    builtin = result.get('version') == 'v72'
    marker = BUILTIN_PROFILE if builtin else PROFILE
    require(result.get('version') in ('v71', 'v72') and result.get('passed') is True and
            result.get('Image_built') is True and result.get('BOOT_built') is False and
            result.get('cycle_slot_patched') is False and result.get('kernel_or_provider_executed') is False and
            result.get('ci_context', {}).get('GITHUB_SHA') == expected_source and
            result.get('kernel_commit') == '55f042627bb7030c93550faafa117674d32b21d1' and
            result.get('make_target') == 'Image' and
            result.get('integration_object') == 'drivers/misc/note10_sha256_kat.o',
            'accepted new Image result scope differs')
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
            all(x in image for x in (b'N10RET1', b'N10SHA1')), 'Image evidence identity differs')
    banners = re.findall((rb'Linux version 4\.14\.113-v72-builtin-init [^\x00\r\n]+' if builtin else rb'Linux version 4\.14\.113-v71-sha256-recovery [^\x00\r\n]+'), image)
    require(len(banners) == 1, 'unique actual profile kernel banner required')
    config = root/'prerequisites/objects/.config'
    required = {'CONFIG_NOTE10_SHA256_KAT_RECOVERY=y', 'CONFIG_CRYPTO=y', 'CONFIG_CRYPTO_HASH=y',
                'CONFIG_CRYPTO_SHA256=y', 'CONFIG_EXYNOS_REBOOT=y', 'CONFIG_SEC_REBOOT=y',
                'CONFIG_BLK_DEV_INITRD=y', 'CONFIG_RD_LZMA=y', 'CONFIG_ARM64_4K_PAGES=y',
                }
    if not builtin:
        required.add('CONFIG_INITRAMFS_SOURCE=""')
    lines = config.read_text().splitlines()
    require(required.issubset(lines) and (builtin or 'CONFIG_INITRAMFS_FORCE=y' not in lines) and
            'CONFIG_CMDLINE_FORCE=y' not in lines, 'external TWRP ramdisk/recovery configuration differs')
    policy_source = 'note10/device_test/build_sha256_kat_recovery.py'
    require(sha(ROOT/policy_source) == result['source_sha256'].get(policy_source),
            'live command-line policy helper differs from Image-producing source')
    from build_sha256_kat_recovery import bootloader_cmdline_policy
    bootloader_cmdline_policy('\n'.join(lines))
    extra = {}
    if builtin:
        from builtin_init_profile import input_binding
        extra = input_binding(root, result, image, lines)
    return dict(device_profile=marker, **extra, accepted_result_sha256=expected_result,
                source_head=expected_source, image_sha256=result['image_sha256'], image_size=len(image),
                effective_config_sha256=sha(config), build_evidence_id=identity,
                kernel_banner=banners[0].decode('ascii'))


# Exact previously accepted host7: used only to validate the immutable v71
# current-BOOT pair after v72 changes. Never relabel it as current source.
V71_HOST_HEAD = '5e233aa5f08473d716ca2e9b3d8937c1821d513f'
V71_HOST_PINS = {'note10/device_test/sha256_kat_device_profile.py': '76111d416db9646271a7de9ae7ab55288e23aa5304ad6601b94bedc900832ea5', 'note10/device_test/test_sha256_kat_device_profile.py': 'c48400d5573695d217101806b8481e39aec38fd5382e64b85f999b4cee42c498', 'note10/device_test/materialize_auto_cycle.py': '87ef3da2e0ddbbb40b02bc9334c59deb8c590692352f099cb2b3ae99b749f960', 'note10/device_test/prepare_linux_boot.py': '4f599c7c667e3dc18a5afccfd682c47f705ed714daa916b4c0557db9f7f78c70', 'note10/device_test/build_boot_test_packages.py': 'afbf2d7352ce4722ce6d7cb6d2430bb06962f5a5b1fa570fbd68f182faf4fdda', 'note10/device_test/stage_phase2.py': '9e340ba0d6244ef5c2673317b01dfdec4433959241f6318669b8d27f01ce319b', 'note10/device_test/auto_cycle.py': '0118d152452434b76fc77ad6089165a601abca3838699c5dd7f28d8f371e3950'}


def host_binding(source_head):
    require(re.fullmatch('[0-9a-f]{40}', source_head or ''), 'exact host-profile publication source pin required')
    pins = V71_HOST_PINS if source_head == V71_HOST_HEAD else {
        'note10/device_test/'+name: sha(Path(__file__).parent/name)
        for name in (*HOST_SOURCES, 'builtin_init_profile.py', 'builtin_init_route.py', 'test_builtin_init_route.py')}
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
    # Root supplies and reviews this receipt from its actual independent reader.
    # Hash/type binding is not a replay of that reader or API authentication.
    return dict(image_root_receipt_sha256=expected_sha, root_reader_result_sha256=row['root_reader_result_sha256'])


def common_report(binding, profile_sha):
    extra = dict(builtin_minimal_init_route=True, external_initrd_used_for_PID1=False) if binding['device_profile'] == BUILTIN_PROFILE else {}
    return dict(binding, **extra, profile_sha256=profile_sha, build_passed=True,
                auto_return_diagnostic=True, auto_return_evidence_version=1,
                auto_cycle_slot=SLOT.decode(), diagnostic_preserves_external_initramfs=True,
                source_commit='55f042627bb7030c93550faafa117674d32b21d1',
                public_defconfig='exynos9820-d2x_defconfig', deployment_ready=False,
                device_boot_tested=False)


def prepare_template(build, output, accepted_result_sha256, source_head, *, root_receipt,
                     root_receipt_sha256, host_source_head):
    build, output = private(build), private(output)
    require(not output.exists() and not output.is_relative_to(build) and not build.is_relative_to(output),
            'fresh disjoint template required')
    root_receipt = private(root_receipt)
    binding = raw_binding(build, accepted_result_sha256, source_head)
    binding.update(root_receipt_binding(build, root_receipt, root_receipt_sha256, binding))
    require(binding['device_profile'] != BUILTIN_PROFILE or host_source_head != V71_HOST_HEAD,
            'new builtin profile requires its own host publication head')
    binding.update(host_binding(host_source_head))
    shutil.copytree(build, output)
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
    measured = raw_binding(root, binding['accepted_result_sha256'], binding['source_head'])
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
    keys = (*FIELDS, *EXTRA_FIELDS) if row['device_profile'] == BUILTIN_PROFILE else FIELDS
    return {key: row[key] for key in keys}


def package_scope(row, mode=None):
    require(selected(row), 'KAT package profile missing')
    no_legacy(row)
    for key in ('profile_sha256', 'accepted_result_sha256', 'image_root_receipt_sha256', 'root_reader_result_sha256'):
        require(re.fullmatch('[0-9a-f]{64}', row.get(key, '')), 'KAT package result/profile pin missing')
    require(re.fullmatch('[0-9a-f]{32}', row.get('build_evidence_id', '')) and
            row.get('kernel_banner', '').startswith('Linux version 4.14.113-v72-builtin-init ' if row['device_profile'] == BUILTIN_PROFILE else 'Linux version 4.14.113-v71-sha256-recovery '),
            'KAT package identity missing')
    require(re.fullmatch('[0-9a-f]{40}', row.get('source_head', '')) and
            re.fullmatch('[0-9a-f]{40}', row.get('host_profile_source_head', '')) and
            row.get('host_profile_source_sha256') == host_binding(row['host_profile_source_head'])['host_profile_source_sha256'],
            'host-profile code identity differs')
    if row['device_profile'] == BUILTIN_PROFILE:
        require(row.get('host_profile_source_head') != V71_HOST_HEAD, 'new profile cannot claim historical host head')
        from builtin_init_profile import EXTRA_FIELDS
        require(all(re.fullmatch('[0-9a-f]{64}', row.get(k, '')) for k in EXTRA_FIELDS), 'minimal init pins missing')
    if mode is None or mode in ('diagnostic', 'rollback'):
        diagnostic = mode in (None, 'diagnostic')
        require(row.get('auto_return_diagnostic') is diagnostic and
                (re.fullmatch('[0-9a-f]{32}', row.get('auto_cycle_token') or '') if diagnostic
                 else row.get('auto_cycle_token') is None), 'KAT package role/cycle differs')
        if 'mode' in row:
            require(row['mode'] == mode and row.get('test_purpose') ==
                    (('sha256-kat-builtin-init' if row['device_profile'] == BUILTIN_PROFILE else 'sha256-kat-recovery') if diagnostic else 'rollback'), 'KAT package purpose differs')
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
    if template['device_profile'] == BUILTIN_PROFILE:
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
    require(set(plan) == (PLAN_KEYS | {'current_boot_payload_sha256'} if plan.get('device_profile') == BUILTIN_PROFILE else PLAN_KEYS) and selected(plan) and plan.get('kind') == 'note10-bounded-auto-cycle' and
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
    if plan['device_profile'] == BUILTIN_PROFILE:
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
    require(all(header[k] == original_header[k] for k in
                ('name', 'os_version', 'security_patch_month', 'kernel_addr', 'tags_addr', 'page_size')) and
            header['header_version'] == recovery_header['header_version'] == 1 and
            header['recovery_dtbo_size'] == header['second_size'] == 0 and
            header['cmdline'] == recovery_header['cmdline'] and
            header['ramdisk_addr'] == recovery_header['ramdisk_addr'] and
            header['arm64_text_offset'] == recovery_header['arm64_text_offset'],
            'actual BOOT metadata/bootloader command line differs')
    ramdisk = official[recovery_header['ramdisk_file_offset']:
                       recovery_header['ramdisk_file_offset']+recovery_header['ramdisk_size']]
    require(ramdisk and payload[header['ramdisk_file_offset']:header['ramdisk_file_offset']+header['ramdisk_size']] == ramdisk,
            'actual external TWRP ramdisk differs')
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
                  partition_writes=False, rebooted=False)
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
            require(adb.text('shell', 'readlink', '-f', '/dev/block/by-name/'+part['partition']) == part['block_node'] and
                    adb.text('shell', 'blockdev', '--getsize64', part['block_node']) == str(part['size']),
                    'paired partition node/size changed')
        verify_partitions(adb, backup, pair['expected_current_boot_sha256'])
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
    finally:
        save(packages/'PREINSTALL-CHECK.json', report)


def decode_selected(data, banner, identity, cycle):
    from decode_auto_return import select_cycle_log, decode as decode_return
    from decode_sha256_runtime_kat import decode as decode_kat
    starts = list(re.finditer(rb'(?m)^[ \t]*(?:<[0-9]+>)?\[\s*0\.000000\][^\r\n]*?(Linux version [^\r\n]*)', data))
    require(starts and starts[-1][1] == banner.encode('ascii'), 'latest self-contained boot banner required')
    selected_boot = data[starts[-1].start():]
    clipped, offset = select_cycle_log(selected_boot, identity, cycle)
    recovery = decode_return(clipped, identity, cycle)
    kat = decode_kat(clipped.decode('ascii', errors='replace'), identity)
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
    if bound['device_profile'] == BUILTIN_PROFILE:
        from builtin_init_profile import snapshot
        return snapshot(adb, out, bound, pair['auto_cycle_token'])
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
    parser.add_argument('--root-receipt', type=Path, required=True)
    parser.add_argument('--root-receipt-sha256', required=True)
    parser.add_argument('--host-source-head', required=True)
    args = parser.parse_args()
    print(json.dumps(prepare_template(args.build, args.output, args.accepted_result_sha256, args.source_head,
        root_receipt=args.root_receipt, root_receipt_sha256=args.root_receipt_sha256,
        host_source_head=args.host_source_head), indent=2))
