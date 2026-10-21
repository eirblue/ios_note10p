#!/usr/bin/env python3
"""Read hardware facts over ADB. Never writes to or reboots the phone."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from datetime import datetime, timezone

PROPERTIES = (
    'ro.product.model', 'ro.product.device', 'ro.product.board',
    'ro.board.platform', 'ro.hardware', 'ro.soc.manufacturer', 'ro.soc.model',
    'ro.build.version.release', 'ro.build.version.security_patch',
    'ro.build.PDA', 'ro.bootloader', 'ro.boot.flash.locked',
    'ro.build.display.id', 'ro.build.version.incremental',
    'ro.boot.hw_rev', 'ro.revision', 'ro.boot.em.status',
    'ro.boot.vbmeta.device_state', 'ro.boot.verifiedbootstate',
    'ro.oem_unlock_supported', 'sys.oem_unlock_allowed',
)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    local_adb = Path(__file__).resolve().parents[1] / 'host-tools/platform-tools/adb.exe'
    parser.add_argument('--adb', default=str(local_adb) if local_adb.exists() else 'adb')
    parser.add_argument('--serial', help='Select device; serial is not saved in report')
    parser.add_argument('--out', type=Path, default=Path(__file__).resolve().parent / 'private')
    parser.add_argument('--fdt', action='store_true', help='Also read /sys/firmware/fdt if accessible; may contain device identifiers')
    args = parser.parse_args()

    def run(command, selected=True):
        prefix = [args.adb]
        if selected and args.serial:
            prefix += ['-s', args.serial]
        try:
            r = subprocess.run(prefix + command, capture_output=True, timeout=20)
            return r.returncode, r.stdout, r.stderr
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise RuntimeError(f'ADB unavailable: {exc}') from exc

    code, stdout, stderr = run(['devices'], selected=False)
    if code:
        raise RuntimeError('ADB server failed: ' + stderr.decode(errors='replace'))
    rows = [row.split()[:2] for row in stdout.decode(errors='replace').splitlines()[1:] if row.strip()]
    if args.serial:
        rows = [row for row in rows if row[0] == args.serial]
    if len(rows) != 1 or rows[0][1] != 'device':
        raise RuntimeError('Exactly one authorized device required. Connect USB, allow USB debugging; use --serial for multiple devices.')
    # Pin every subsequent command to the transport just inspected.
    args.serial = rows[0][0]
    report = {'collected_utc': datetime.now(timezone.utc).isoformat(),
              'properties': {}, 'observations': {}, 'limitations': [
                  'Properties are observations, not proof of bootloader unlock or native boot support.',
                  'No root escalation, partition reading, flashing, reboot or phone writes performed.']}
    for prop in PROPERTIES:
        code, stdout, stderr = run(['shell', 'getprop', prop])
        report['properties'][prop] = {'exit_code': code, 'value': stdout.decode(errors='replace').strip(),
                                      'error': stderr.decode(errors='replace').strip()}
    for label, command in {
        'kernel': ['uname', '-a'],
        'display_size': ['wm', 'size'],
        'display_density': ['wm', 'density'],
        'dt_compatible': ['cat', '/sys/firmware/devicetree/base/compatible'],
        'dt_model': ['cat', '/sys/firmware/devicetree/base/model'],
        'partition_names': ['ls', '-l', '/dev/block/by-name'],
    }.items():
        code, stdout, stderr = run(['shell'] + command)
        report['observations'][label] = {'exit_code': code, 'value': stdout.decode(errors='replace').replace('\x00', '\n').strip(),
                                         'error': stderr.decode(errors='replace').strip()}
    code, stdout, stderr = run(['shell', 'cat', '/proc/cpuinfo'])
    # Keep feature declarations without persisting hardware serial identifiers.
    cpu_lines = [line for line in stdout.decode(errors='replace').splitlines()
                 if line.split(':', 1)[0].strip().lower() != 'serial']
    report['observations']['cpuinfo'] = {'exit_code': code, 'value': '\n'.join(cpu_lines),
                                        'error': stderr.decode(errors='replace').strip()}
    args.out.mkdir(parents=True, exist_ok=True)
    if args.fdt:
        code, stdout, stderr = run(['exec-out', 'cat', '/sys/firmware/fdt'])
        valid = code == 0 and stdout[:4] == b'\xd0\x0d\xfe\xed'
        report['fdt'] = {'valid_header': valid, 'exit_code': code,
                         'error': stderr.decode(errors='replace').strip()}
        if valid:
            (args.out / 'live.dtb').write_bytes(stdout)
            report['fdt']['sha256'] = hashlib.sha256(stdout).hexdigest()
    target = args.out / 'device-report.json'
    target.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'Read-only collection saved: {target}')


if __name__ == '__main__':
    try:
        main()
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(2)
