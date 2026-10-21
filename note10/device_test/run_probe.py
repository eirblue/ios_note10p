"""Preflight a connected d2x TWRP; --run executes the RAM-only collector.

Does not unlock, reboot, mount, install a recovery, flash or load XNU.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess
import uuid

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent


class Adb:
    def __init__(self, executable, serial=None):
        self.executable = str(executable); self.serial = serial

    def call(self, *args, timeout=30, select=True):
        command = [self.executable]
        if select and self.serial:command += ['-s', self.serial]
        result = subprocess.run([*command, *args], capture_output=True, timeout=timeout)
        if result.returncode:
            # Never print an unfiltered device serial or arbitrary device data.
            raise RuntimeError('ADB command failed: ' + args[0])
        return result.stdout

    def text(self, *args, **kwargs):return self.call(*args, **kwargs).decode(errors='replace').strip()


def preflight(adb):
    rows = [s.split()[:2] for s in adb.text('devices', select=False).splitlines()[1:] if s.strip()]
    if adb.serial:rows = [r for r in rows if r[0] == adb.serial]
    if len(rows) != 1 or rows[0][1] not in ('device', 'recovery'):
        raise RuntimeError('Exactly one authorized normal ADB recovery transport required; sideload is not shell mode')
    adb.serial = rows[0][0]
    model = adb.text('shell', 'getprop', 'ro.product.model')
    device = adb.text('shell', 'getprop', 'ro.product.device')
    twrp = adb.text('shell', 'getprop', 'ro.twrp.version')
    if not twrp:raise RuntimeError('TWRP is not running; Android/stock recovery refused')
    if model != 'SM-N976N' and device not in ('d2x', 'd2xks'):
        raise RuntimeError('Connected device is not SM-N976N/d2x')
    if adb.text('shell', 'id', '-u') != '0':raise RuntimeError('Root TWRP shell required')
    if adb.text('shell', 'uname', '-m') != 'aarch64':raise RuntimeError('AArch64 recovery required')
    return {'model': model, 'device': device, 'twrp_version': twrp, 'root_shell': True,
            'xnu_executed': False, 'partition_writes': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--adb', type=Path, default=ROOT/'host-tools/platform-tools/adb.exe')
    parser.add_argument('--serial')
    parser.add_argument('--run', action='store_true', help='Push collector to RAM, execute and pull observations')
    parser.add_argument('--pull-only', metavar='SESSION', help='Pull a session produced by installing the probe ZIP')
    parser.add_argument('--out', type=Path, default=ROOT/'note10/private/device-observations')
    args = parser.parse_args()
    if args.run and args.pull_only:parser.error('--run and --pull-only are mutually exclusive')
    adb = Adb(args.adb, args.serial)
    state = preflight(adb)
    if not args.run and not args.pull_only:
        print(json.dumps({'preflight_passed': True, **state, 'next': 'Use --run to collect into RAM'}));return
    session = args.pull_only or 'session-' + uuid.uuid4().hex[:16]
    if not re.fullmatch(r'session-[A-Za-z0-9_-]+', session):raise RuntimeError('Invalid session name')
    remote = '/tmp/note10-probe/' + session
    local = args.out / session
    if local.exists():raise RuntimeError('Local session already exists; refusing mixed/stale captures')
    if args.run:
        script = HERE / 'collect.sh'
        # Fixed paths only. No shell interpolation of model strings or user data.
        adb.call('push', str(script), '/tmp/note10-probe-collect.sh')
        output = adb.text('shell', 'sh', '/tmp/note10-probe-collect.sh', remote)
        if 'NOTE10_PROBE_OUTPUT=' + remote not in output:
            raise RuntimeError('Collector did not confirm the requested session')
    if adb.text('shell', 'cat', remote + '/COMPLETE') != 'NOTE10_PROBE_COMPLETE':
        raise RuntimeError('Recovery capture incomplete')
    args.out.mkdir(parents=True, exist_ok=True)
    adb.call('pull', remote, str(local), timeout=120)
    if (local/'COMPLETE').read_text().strip() != 'NOTE10_PROBE_COMPLETE':
        raise RuntimeError('Downloaded completion marker is invalid')
    state.update({'captured_utc': datetime.now(timezone.utc).isoformat(),
                  'collector_sha256': hashlib.sha256((HERE/'collect.sh').read_bytes()).hexdigest(),
                  'method': 'RAM-only TWRP shell' if args.run else 'pull existing RAM-only ZIP capture'})
    (local/'host-result.json').write_text(json.dumps(state, indent=2))
    from analyze_capture import analyze
    result = analyze(local)
    (local/'analysis.json').write_text(json.dumps(result, indent=2))
    print(json.dumps({'capture_downloaded': True, 'directory': str(local),
                      'live_tree_observed': result['live_tree_observed'],
                      'boot_contract_verified': False, 'xnu_executed': False}))


if __name__ == '__main__':
    try:main()
    except (RuntimeError, OSError, subprocess.TimeoutExpired, ValueError) as error:
        raise SystemExit(str(error))
