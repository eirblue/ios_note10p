"""Read only boot/recovery/DT/AVB partitions into a new private PC directory.

No restore, flash, mount, reboot, partition write or arbitrary partition option.
This is a boot-component backup, not a user-data or complete device backup.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import uuid
from run_probe import Adb, ROOT, preflight

PARTITIONS = ('boot', 'recovery', 'dtb', 'dtbo', 'vbmeta')
MAX_PARTITION = 128 * 1024 * 1024
MAX_TOTAL = 320 * 1024 * 1024


def remote_info(adb, name):
    if name not in PARTITIONS: raise ValueError('Partition is not in boot-component allowlist')
    remote = '/dev/block/by-name/' + name
    resolved = adb.text('shell', 'readlink', '-f', remote)
    if not re.fullmatch(r'/dev/block/sd[a-z][0-9]+', resolved):
        raise ValueError('Unexpected block node for ' + name)
    size_text = adb.text('shell', 'blockdev', '--getsize64', resolved)
    if not re.fullmatch(r'[0-9]+', size_text): raise ValueError('Invalid block size')
    size = int(size_text)
    if not 0 < size <= MAX_PARTITION or size % 512:
        raise ValueError('Unsupported boot-component size')
    return {'partition':name, 'block_node':resolved, 'size':size}


def remote_hash(adb, node):
    value = adb.text('shell', 'sha256sum', node).split()
    if not value or not re.fullmatch(r'[a-fA-F0-9]{64}', value[0]):
        raise ValueError('Invalid remote checksum')
    return value[0].lower()


def stream(adb, node, target, expected_size):
    # exec-out preserves raw bytes; shell redirection on Windows is avoided.
    command = [adb.executable, '-s', adb.serial, 'exec-out', 'cat', node]
    with target.open('xb') as output:
        result = subprocess.run(command, stdout=output, stderr=subprocess.PIPE, timeout=120)
    if result.returncode or target.stat().st_size != expected_size:
        raise ValueError('Partition transfer failed or size changed')


def backup(adb, output, transfer=stream):
    state = preflight(adb)
    bootloader = adb.text('shell', 'getprop', 'ro.bootloader')
    if not re.fullmatch(r'N976N[A-Z0-9]+', bootloader):
        raise ValueError('SM-N976N bootloader identity required')
    infos = [remote_info(adb, name) for name in PARTITIONS]
    if len({x['block_node'] for x in infos}) != len(infos):
        raise ValueError('Duplicate boot-component block nodes')
    if sum(x['size'] for x in infos) > MAX_TOTAL: raise ValueError('Backup exceeds PC size limit')
    output.mkdir(parents=True, exist_ok=False)
    records = []
    for info in infos:
        name = info['partition']; node = info['block_node']
        before = remote_hash(adb, node)
        partial = output / (name + '.img.partial')
        transfer(adb, node, partial, info['size'])
        actual = hashlib.sha256(partial.read_bytes()).hexdigest()
        after = remote_hash(adb, node)
        if partial.stat().st_size != info['size'] or before != actual or after != actual:
            raise ValueError('Backup does not match stable device contents: ' + name)
        final = output / (name + '.img')
        if final.exists(): raise ValueError('Refusing to overwrite verified backup')
        partial.rename(final)
        records.append({**info, 'file':final.name, 'sha256':actual,
                        'remote_hash_before_and_after_match':True})
    report = {'complete':True, 'scope':'Boot components only; not full device/user-data backup',
              'device':state['device'], 'twrp_version':state['twrp_version'],
              'bootloader':bootloader, 'partitions':records,
              'partition_writes':False, 'rebooted':False, 'xnu_executed':False,
              'restore_tested':False, 'files_are_private':True}
    (output / 'backup-manifest.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--read',action='store_true',help='Read the fixed allowlist of boot components to PC')
    args = parser.parse_args()
    adb = Adb(ROOT / 'host-tools/platform-tools/adb.exe')
    if not args.read:
        print(json.dumps({'preflight':preflight(adb), 'next':'--read for boot-component backup; no restore command'}))
    else:
        output = ROOT / 'note10/private/boot-backups' / ('session-' + uuid.uuid4().hex[:16])
        report = backup(adb, output)
        print(json.dumps({'complete':report['complete'],'directory':str(output),
                          'partitions':len(report['partitions']),'partition_writes':False,'restore_tested':False}))
