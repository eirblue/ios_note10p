"""Private Linux-only BOOT/package producer; source-built cycle field mutation only."""
import argparse
import json
from pathlib import Path
import re
import struct
import subprocess
import sys
import uuid
import zipfile
import v154_linux_prepare as p

MKBOOTIMG_SHA = '2a8d05d34110f66c463668f43fc812ce2e46e66459c347eaadb080271df69aa8'
TWRP_SHA = 'e8de29b03fc3eab95f51663b08b2f848e168854a15f8a598a1f80d216f4794df'


def header(raw, *, reference=False, file_size=None):
    if len(raw) < 1660 or raw[:8] != b'ANDROID!':
        raise ValueError('Android BOOTv1 header required')
    keys = ('kernel_size', 'kernel_addr', 'ramdisk_size', 'ramdisk_addr', 'second_size',
            'second_addr', 'tags_addr', 'page_size', 'header_version', 'encoded_os')
    row = dict(zip(keys, struct.unpack_from('<10I', raw, 8)))
    page = row['page_size']
    if row['header_version'] != 1 or page not in (2048, 4096, 8192, 16384):
        raise ValueError('observed BOOTv1 geometry required')
    z = lambda value: value.split(b'\0', 1)[0].decode('ascii')
    row.update(name=z(raw[48:64]), cmdline=z(raw[64:576])+z(raw[608:1632]), kernel_offset=page)
    row['ramdisk_offset'] = page+(row['kernel_size']+page-1)//page*page
    row['payload_end'] = row['ramdisk_offset']+(row['ramdisk_size']+page-1)//page*page
    row['recovery_dtbo_size'], row['recovery_dtbo_offset'], row['header_size'] = struct.unpack_from('<IQI', raw, 1632)
    total = len(raw) if file_size is None else file_size
    if (type(total) is not int or not len(raw) <= total <= 128*1024*1024 or
        (not reference and total != len(raw)) or not row['kernel_size'] or row['second_size'] or
        row['header_size'] != 1648 or row['payload_end'] > total):
        raise ValueError('BOOT extent differs')
    if row['recovery_dtbo_size']:
        if not reference or row['recovery_dtbo_offset'] != row['payload_end'] or row['recovery_dtbo_offset'] % page or row['recovery_dtbo_offset']+row['recovery_dtbo_size'] > total:
            raise ValueError('reference recovery DTBO extent differs')
    elif row['recovery_dtbo_offset']:
        raise ValueError('empty recovery DTBO offset must be zero')
    return row


def patch_cycle(image, build, cycle):
    p.hexid(cycle, 32)
    offset = build['cycle_offset']
    if (type(offset) is not int or offset < 64 or offset+33 > len(image) or
        len(image) != build['Image_bytes'] or p.sha(image) != build['Image_sha256'] or
        len(image) > p.IMAGE_LIMIT or image[56:60] != b'ARM\x64' or
        image[offset:offset+33] != p.CYCLE_MARKER+b'\0' or image.count(p.CYCLE_MARKER+b'\0') != 1):
        raise ValueError('producer-bound cycle-only Image required')
    enabled = image[:offset]+cycle.encode()+image[offset+32:]
    if len(enabled) != len(image) or enabled[:offset] != image[:offset] or enabled[offset+32:] != image[offset+32:]:
        raise ValueError('out-of-cycle mutation')
    return enabled


def partition_rows(backup):
    rows = backup.get('partitions')
    if (backup.get('complete') is not True or backup.get('partition_writes') is not False or
        type(rows) is not list or len(rows) != 5 or {r['partition'] for r in rows} != p.PARTITIONS or
        len({r['block_node'] for r in rows}) != 5 or re.fullmatch('N976N[A-Z0-9]+', backup.get('bootloader', '')) is None):
        raise ValueError('paired complete five-partition backup required')
    for row in rows:
        if (row.get('file') != row['partition']+'.img' or row.get('remote_hash_before_and_after_match') is not True or
            type(row['size']) is not int or not 0 < row['size'] <= 128*1024*1024 or
            re.fullmatch('/dev/block/sd[a-z][0-9]+', row['block_node']) is None):
            raise ValueError('unsafe partition authority')
        p.hexid(row['sha256'])
    return rows


def current_and_restore(current, ledger, backup):
    rows = partition_rows(backup)
    if (current.get('schema') != 'note10-v141-private-xnu-package-v1' or current.get('version') != 'v141' or
        ledger.get('schema') != 'note10-v141-owned-XNU-ledger-v1' or ledger.get('recovery_returned') is not True or
        ledger.get('status') != 'cycle-complete-XNU-proof-limits-retained' or
        any(type(ledger.get(k)) is not int or ledger[k] != 1 for k in ('host_BOOT_write_attempts', 'host_reboot_attempts')) or
        any(ledger.get(k) != current.get(k) for k in ('cycle', 'build_evidence_id')) or
        current.get('bootloader') != backup['bootloader']):
        raise ValueError('accepted consumed141 TWRP baseline required')
    safe = next(row for row in rows if row['partition'] == 'boot')
    if safe['sha256'] != current['rollback_BOOT_sha256'] or safe['sha256'] == current['diagnostic_BOOT_sha256']:
        raise ValueError('paired rollback and installed141 baseline differ')
    for row in rows:
        prior = next(item for item in current['partitions'] if item['partition'] == row['partition'])
        if any(row[k] != prior[k] for k in ('size', 'block_node', 'sha256')):
            raise ValueError('current141 paired partition baseline differs')
    return p.hexid(current['diagnostic_BOOT_sha256']), safe


def updater(mode, package):
    if mode not in ('diagnostic', 'restore'):
        raise ValueError('exact BOOT-only package role required')
    rows = package['partitions']
    payload = package['diagnostic_BOOT_sha256'] if mode == 'diagnostic' else package['rollback_BOOT_sha256']
    script = '''#!/sbin/sh
set -eu
PATH=/sbin:/system/bin:/system/xbin:/vendor/bin:$PATH
export PATH
FD=${2:-}
ZIP=${3:-}
case "$FD" in ''|0|1|2|*[!0-9]*) exit 1 ;; esac
ui() { printf 'ui_print %s\\nui_print\\n' "$*" > "/proc/self/fd/$FD"; }
fail() { ui "$*"; exit 1; }
sum() { sha256sum "$1" | awk '{print $1}'; }
[ "$(id -u)" = 0 ] && [ "$(uname -m)" = aarch64 ] || fail "Root AArch64 required"
[ -n "$(getprop ro.twrp.version)" ] || fail "TWRP required"
case "$(getprop ro.product.device)" in d2x|d2xks) ;; *) fail "Device differs" ;; esac
'''
    script += '[ "$(getprop ro.bootloader)" = "'+package['bootloader']+'" ] || fail "Bootloader differs"\n'
    for row in rows:
        name, node = row['partition'], row['block_node']
        script += '[ "$(readlink -f /dev/block/by-name/'+name+')" = "'+node+'" ] || fail "Node differs"\n'
        script += '[ "$(blockdev --getsize64 '+node+')" = "'+str(row['size'])+'" ] || fail "Size differs"\n'
        if name != 'boot' or mode == 'diagnostic':
            expected = package['expected_current_BOOT_sha256'] if name == 'boot' else row['sha256']
            script += '[ "$(sum '+node+')" = "'+expected+'" ] || fail "Baseline differs"\n'
    script += '''[ ! -L /tmp ] || fail "RAM path differs"
awk '($2 == "/" || $2 == "/tmp") && length($2) > best {best=length($2);kind=$3} END {exit !(kind=="tmpfs" || kind=="ramfs" || kind=="rootfs")}' /proc/mounts || fail "RAM tmp required"
WORK=/tmp/n10-v154-$$
[ ! -e "$WORK" ] && [ ! -L "$WORK" ] || fail "Stale staging"
umask 077
mkdir "$WORK"
unzip -p "$ZIP" boot.img > "$WORK/boot.img" || fail "Extraction failed"
'''
    script += '[ "$(sum "$WORK/boot.img")" = "'+payload+'" ] || fail "Payload differs"\n'
    node = next(row['block_node'] for row in rows if row['partition'] == 'boot')
    script += 'dd if="$WORK/boot.img" of="'+node+'" bs=4096 || fail "BOOT write failed; stop"\nsync\n'
    script += '[ "$(sum '+node+')" = "'+payload+'" ] || fail "BOOT readback failed; stop"\n'
    script += 'ui "BOOT verified. No automatic reboot or restore."\nexit 0\n'
    return script.encode()


def zip_package(path, payload, mode, package):
    entries = {'boot.img': payload, 'META-INF/com/google/android/update-binary': updater(mode, package),
               'META-INF/com/google/android/updater-script': b'# Reviewed BOOT-only package\n'}
    with zipfile.ZipFile(path, 'x', compression=zipfile.ZIP_STORED) as bundle:
        for name, raw in entries.items():
            info = zipfile.ZipInfo(name)
            info.external_attr = (0o100755 if name.endswith('update-binary') else 0o100644) << 16
            bundle.writestr(info, raw)


def prepare(contract_path, contract_sha, output):
    _, contract_raw = p.pinned(dict(path=str(contract_path), sha256=contract_sha))
    spec = json.loads(contract_raw)
    roles = {'build_result', 'backup_manifest', 'current141_package', 'current141_ledger', 'mkbootimg', 'twrp', 'iva_resource_binding'}
    if set(spec) != {'schema', 'inputs'} or spec['schema'] != p.INPUTS_SCHEMA or set(spec['inputs']) != roles:
        raise ValueError('exact Linux package input roles required')
    pins = spec['inputs']
    inputs = {key: p.pinned(item) for key, item in pins.items() if key != 'twrp'}
    twrp = pins['twrp']
    if (set(twrp) != {'path', 'sha256', 'header_sha256', 'bytes'} or twrp['sha256'] != TWRP_SHA or
        pins['mkbootimg']['sha256'] != MKBOOTIMG_SHA):
        raise ValueError('official recovery/mkbootimg pin required')
    twrp_path = Path(twrp['path'])
    if twrp_path.is_symlink() or not twrp_path.is_file() or twrp_path.stat().st_size != twrp['bytes']:
        raise ValueError('official recovery bounded header reference differs')
    build = json.loads(inputs['build_result'][1])
    if (build.get('schema') != p.BUILD_SCHEMA or build.get('passed') is not True or build.get('version') != 'v154' or
        build.get('XNU_execution_allowed') is not False or build.get('internal_kexec_limit') != 0 or
        build.get('full_Image_build_attempts') != 1 or build.get('separate_native_object_builds') != 0 or
        build.get('native_output_sha256') != p.FINAL_NATIVE or build.get('source_sha256') != p.source_pins() or
        build.get('public_input', {}).get('source_sha256') != build.get('source_sha256') or
        type(build.get('linked_extent')) is not int or not 0 < build['linked_extent'] <= p.IMAGE_LIMIT):
        raise ValueError('accepted current full Linux Image/source proof required')
    backup = json.loads(inputs['backup_manifest'][1])
    current, ledger = (json.loads(inputs[key][1]) for key in ('current141_package', 'current141_ledger'))
    current_sha, safe = current_and_restore(current, ledger, backup)
    resource = json.loads(inputs['iva_resource_binding'][1])
    dtb = next(row for row in backup['partitions'] if row['partition'] == 'dtb')
    if (resource.get('schema') != 'note10-v154-private-iva-resource-binding-v1' or
        resource.get('resource_base') != 0x18200000 or resource.get('resource_size') != 0x200000 or
        resource.get('DTB_sha256') != dtb['sha256'] or resource.get('DTB_baseline_only_not_live_FDT_equality') is not True or
        resource.get('node_path') != '/iva@0x18200000' or resource.get('hardware_terminal_claimed') is not False or
        resource.get('baseline_package_sha256') != pins['current141_package']['sha256'] or resource.get('partition') != dtb):
        raise ValueError('selected unchanged physical IVA resource authority required')
    out = p.private(output)
    if out.exists():
        raise ValueError('fresh package output required')
    identity = p.hexid(build['build_evidence_id'], 32); cycle = uuid.uuid4().hex
    image = p.ordinary(inputs['build_result'][0].parent/'Image', p.IMAGE_LIMIT)
    enabled = patch_cycle(image, build, cycle)
    safe_raw = p.ordinary(inputs['backup_manifest'][0].parent/safe['file'], 128*1024*1024)
    if p.sha(safe_raw) != safe['sha256'] or len(safe_raw) != safe['size']:
        raise ValueError('paired restore BOOT differs')
    stock = header(safe_raw)
    with twrp_path.open('rb') as stream:
        reference_raw = stream.read(1660)
    if p.sha(reference_raw) != p.hexid(twrp['header_sha256']):
        raise ValueError('official header differs')
    reference = header(reference_raw, reference=True, file_size=twrp['bytes'])
    if any(stock[key] != reference[key] for key in ('kernel_addr', 'tags_addr', 'page_size')) or 'n10.cycle=' in reference['cmdline']:
        raise ValueError('unchanged official load geometry required')
    out.mkdir(parents=True); (out/'enabled-Image').write_bytes(enabled)
    encoded = stock['encoded_os']
    os_version = '.'.join(str((encoded >> bit) & 127) for bit in (25, 18, 11))
    month = f'{2000+((encoded >> 4) & 127):04d}-{encoded & 15:02d}'
    command = [sys.executable, '-B', str(inputs['mkbootimg'][0]), '--header_version', '1', '--kernel', str(out/'enabled-Image'),
               '--base', '0', '--kernel_offset', hex(stock['kernel_addr']), '--ramdisk_offset', hex(stock['ramdisk_addr']),
               '--tags_offset', hex(stock['tags_addr']), '--pagesize', str(stock['page_size']), '--board', stock['name'],
               '--cmdline', reference['cmdline'], '--os_version', os_version, '--os_patch_level', month, '--output', str(out/'packed-boot.img')]
    subprocess.run(command, check=True, capture_output=True, timeout=60, cwd=p.ROOT)
    raw = p.ordinary(out/'packed-boot.img', p.BOOT_LIMIT); geometry = header(raw); trailer = b'SEANDROIDENFORCE'
    if (geometry['ramdisk_size'] or geometry['recovery_dtbo_size'] or geometry['cmdline'] != reference['cmdline'] or
        any(geometry[key] != stock[key] for key in ('kernel_addr', 'tags_addr', 'page_size')) or
        raw[geometry['kernel_offset']:geometry['kernel_offset']+geometry['kernel_size']] != enabled or
        safe_raw[stock['payload_end']:stock['payload_end']+len(trailer)] != trailer or
        len(raw)+len(trailer) > min(p.BOOT_LIMIT, len(safe_raw))):
        raise ValueError('fresh no-external-ramdisk BOOT capacity/geometry differs')
    boot = (raw+trailer).ljust(len(safe_raw), b'\0'); (out/'boot.img').write_bytes(boot)
    package = dict(schema=p.PACKAGE_SCHEMA, version='v154', cycle=cycle, build_evidence_id=identity,
                   source_sha256=build['source_sha256'], build_result_sha256=pins['build_result']['sha256'],
                   input_contract_sha256=contract_sha, input_Image_sha256=p.sha(image), enabled_Image_sha256=p.sha(enabled),
                   diagnostic_BOOT_sha256=p.sha(boot), expected_current_BOOT_sha256=current_sha, rollback_BOOT_sha256=p.sha(safe_raw),
                   partitions=backup['partitions'], bootloader=backup['bootloader'], iva_resource_binding_sha256=pins['iva_resource_binding']['sha256'],
                   XNU_execution_allowed=False, internal_kexec_limit=0, automatic_restore=False, restore_available=True)
    zip_package(out/'diagnostic.zip', boot, 'diagnostic', package)
    zip_package(out/'restore.zip', safe_raw, 'restore', package)
    package.update(diagnostic_zip_sha256=p.sha(p.ordinary(out/'diagnostic.zip', 128*1024*1024)),
                   restore_zip_sha256=p.sha(p.ordinary(out/'restore.zip', 128*1024*1024)))
    p.save(out/'package-result.json', package)
    plan = dict(schema=p.PLAN_SCHEMA, version='v154', cycle=cycle, build_evidence_id=identity,
                packages=str(out), package_result_sha256=p.sha(p.ordinary(out/'package-result.json')),
                source_sha256=build['source_sha256'], XNU_execution_allowed=False, internal_kexec_limit=0,
                minimum_battery=10, return_timeout_seconds=240, host_BOOT_write_limit=1, host_reboot_limit=1,
                automatic_restore=False, mmap_attempt_limit=1, ioctl_limit=0)
    p.save(out/'plan.json', plan)
    return dict(plan=str(out/'plan.json'), plan_sha256=p.sha(p.ordinary(out/'plan.json')), device_operations=[])


def validate_plan(path, expected):
    _, raw = p.pinned(dict(path=str(path), sha256=expected)); plan = json.loads(raw)
    if (plan.get('schema') != p.PLAN_SCHEMA or plan.get('version') != 'v154' or
        plan.get('source_sha256') != p.source_pins() or plan.get('XNU_execution_allowed') is not False or
        plan.get('automatic_restore') is not False or any(type(plan.get(key)) is not int or plan[key] != value for key, value in
        (('internal_kexec_limit', 0), ('minimum_battery', 10), ('return_timeout_seconds', 240),
         ('host_BOOT_write_limit', 1), ('host_reboot_limit', 1), ('mmap_attempt_limit', 1), ('ioctl_limit', 0)))):
        raise ValueError('reviewed bounded Linux-only plan required')
    folder = p.private(plan['packages'])
    if p.sha(p.ordinary(folder/'package-result.json')) != plan['package_result_sha256']:
        raise ValueError('package receipt changed')
    package = p.read(folder/'package-result.json')
    if (package.get('schema') != p.PACKAGE_SCHEMA or package.get('restore_available') is not True or
        any(not p.same(package.get(key), plan[key]) for key in ('version', 'cycle', 'build_evidence_id', 'source_sha256', 'XNU_execution_allowed', 'internal_kexec_limit', 'automatic_restore'))):
        raise ValueError('package/plan metadata join differs')
    p.hexid(plan['cycle'], 32); p.hexid(plan['build_evidence_id'], 32)
    for name, key in (('boot.img', 'diagnostic_BOOT_sha256'), ('diagnostic.zip', 'diagnostic_zip_sha256'), ('restore.zip', 'restore_zip_sha256')):
        if p.sha(p.ordinary(folder/name, 128*1024*1024)) != package[key]:
            raise ValueError('bound package/available restore transport differs')
    return plan, package


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--contract', type=Path, required=True)
    parser.add_argument('--contract-sha256', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(prepare(args.contract, args.contract_sha256, args.output)))
