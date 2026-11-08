"""One Linux mmap-denial BOOT cycle; no retries, transfer, or automatic restore."""
import argparse
import json
from pathlib import Path
import re
import subprocess
import time
import v154_linux_prepare as p
from v154_linux_package import validate_plan

LEDGER_SCHEMA = 'note10-v154-linux-cycle-ledger-v1'
APPROVAL_SCHEMA = 'note10-v154-linux-physical-approval-v1'
LOGS = (('last_kmsg.txt', '/proc/last_kmsg'), ('console-ramoops-0', '/sys/fs/pstore/console-ramoops-0'),
        ('dmesg-ramoops-0', '/sys/fs/pstore/dmesg-ramoops-0'))


class Adb:
    def __init__(self,path,serial):self.path=str(path);self.serial=serial;self.deadline=None
    def call(self,*args,timeout=30):
        import queue,threading
        if self.deadline is not None:
            remaining=self.deadline-time.monotonic()
            if remaining<=0:raise subprocess.TimeoutExpired('bounded recovery wait',timeout)
            timeout=min(timeout,remaining,3)
        cap=16*1024*1024 if args[:2]==('exec-out','cat') else 65536
        process=subprocess.Popen([self.path,'-s',self.serial,*args],cwd=p.ROOT,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL)
        chunks=queue.Queue(maxsize=4);stop=threading.Event();data=bytearray();deadline=time.monotonic()+timeout
        def reader():
            try:
                while not stop.is_set():
                    block=process.stdout.read(65536)
                    if not block:break
                    while not stop.is_set():
                        try:chunks.put(block,timeout=.1);break
                        except queue.Full:pass
            finally:
                while not stop.is_set():
                    try:chunks.put(None,timeout=.1);break
                    except queue.Full:pass
        worker=threading.Thread(target=reader,daemon=True);worker.start()
        try:
            while True:
                remaining=deadline-time.monotonic()
                if remaining<=0:raise subprocess.TimeoutExpired('bounded ADB',timeout)
                try:block=chunks.get(timeout=min(.1,remaining))
                except queue.Empty:continue
                if block is None:break
                if len(data)+len(block)>cap:raise ValueError('bounded ADB output exceeded; no retry')
                data.extend(block)
            status=process.wait(timeout=max(.01,deadline-time.monotonic()))
            if status:raise RuntimeError('ADB '+args[0]+' failed; no retry')
            return bytes(data)
        finally:
            stop.set()
            if process.poll() is None:process.kill()
            process.wait();worker.join(timeout=1);process.stdout.close()
    def text(self,*args,**kwargs):return self.call(*args,**kwargs).decode('utf-8',errors='strict').strip()

def preflight(adb,package,expected_boot,*,check_battery=True):
    if (not adb.text('shell','getprop','ro.twrp.version') or adb.text('shell','id','-u')!='0' or
        adb.text('shell','uname','-m')!='aarch64' or adb.text('shell','getprop','ro.product.device') not in ('d2x','d2xks') or
        adb.text('shell','getprop','ro.bootloader')!=package['bootloader']):raise ValueError('paired root d2x TWRP required')
    if check_battery:
        battery=adb.text('shell','cat','/sys/class/power_supply/battery/capacity')
        if re.fullmatch('[0-9]{1,3}',battery) is None or not 10<=int(battery)<=100:raise ValueError('battery10 gate failed')
    for row in package['partitions']:
        name=row['partition'];node=row['block_node']
        if adb.text('shell','readlink','-f','/dev/block/by-name/'+name)!=node or adb.text('shell','blockdev','--getsize64',node)!=str(row['size']):
            raise ValueError('live partition canonical node/size differs: '+name)
        observed=adb.text('shell','sha256sum',node).split()
        expected=expected_boot if name=='boot' else row['sha256']
        if not observed or observed[0]!=expected:raise ValueError('live partition digest differs: '+name)
    value=adb.text('shell','cat','/proc/sys/kernel/random/boot_id')
    if re.fullmatch('[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}',value) is None:raise ValueError('boot ID unavailable')
    return value


def transport(path, serial):
    if re.fullmatch('[A-Za-z0-9._:-]{1,128}', serial) is None:
        raise ValueError('reviewed ADB transport identity required')
    call = subprocess.run([str(path), 'devices'], capture_output=True, timeout=15, check=True)
    if len(call.stdout) > 65536:
        raise ValueError('ADB inventory exceeds bound')
    rows = [line.split() for line in call.stdout.decode().splitlines()[1:] if line.strip()]
    if len(rows) != 1 or rows[0] != [serial, 'device'] and rows[0] != [serial, 'recovery']:
        raise ValueError('exactly one paired normal recovery transport required')


class ReturnAdb(Adb):
    def __init__(self, path, serial):
        super().__init__(path, serial)
        self.return_deadline = None

    def call(self, *args, timeout=30):
        if self.deadline is not None:
            raise ValueError('legacy3s deadline must remain unset')
        if self.return_deadline is not None:
            remaining = self.return_deadline-time.monotonic()
            if remaining <= 0:
                raise subprocess.TimeoutExpired('fresh TWRP return budget', timeout)
            timeout = min(timeout, remaining, 30)
        return super().call(*args, timeout=timeout)


def wait_return(adb, package, old_id, deadline, *, clock=None, sleep=None, preflight_fn=None):
    clock = clock or time.monotonic; sleep = sleep or time.sleep
    preflight_fn = preflight_fn or preflight
    adb.return_deadline = deadline
    try:
        while clock() < deadline:
            try:
                if adb.text('shell', 'getprop', 'ro.twrp.version'):
                    candidate = adb.text('shell', 'cat', '/proc/sys/kernel/random/boot_id')
                    if re.fullmatch('[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}', candidate) and candidate != old_id:
                        verified = preflight_fn(adb, package, package['diagnostic_BOOT_sha256'], check_battery=False)
                        if verified != candidate or clock() > deadline:
                            raise ValueError('same-epoch postreturn integrity required')
                        return verified
            except (RuntimeError, subprocess.TimeoutExpired):
                pass
            sleep(min(2, max(0, deadline-clock())))
        raise TimeoutError('no fresh TWRP return; spent, no second reboot/write')
    finally:
        adb.return_deadline = None


def decode(raw, identity, cycle):
    p.hexid(identity, 32); p.hexid(cycle, 32)
    text = raw.decode('utf-8', errors='replace')
    probe = list(re.finditer(r'N154IVA id='+identity+r' boot=([0-9a-f]{32}) cycle='+cycle+r' stage=pass errno=([0-9]+)\r?$', text, re.M))
    if len(probe) != 1 or probe[0].group(2) != '95':
        raise ValueError('one actual Linux EOPNOTSUPP probe PASS required')
    boot = probe[0].group(1)
    events = list(re.finditer(r'N154IVA id='+identity+' boot='+boot+' cycle='+cycle+r' stage=([a-z-]+) errno=(-?[0-9]+)\r?$', text, re.M))
    if [(event.group(1), event.group(2)) for event in events] != [('armed', '0'), ('pass', '95')]:
        raise ValueError('same-boot probe failure or duplicate event')
    frames = {}
    pattern = r'N10BOOTLINK2 boot='+boot+r' N10RET1 (id='+identity+r' cycle='+cycle+r' phase=([0-3]) seq=([0-9]+) delay_ms=90000 status=([0-9]+)) checksum=([0-9a-f]{8})\r?$'
    for match in re.finditer(pattern, text, re.M):
        body, phase, seq, status, expected = match.groups()
        checksum = 2166136261
        for byte in body.encode():
            checksum = ((checksum ^ byte)*16777619) & 0xffffffff
        if checksum != int(expected, 16):
            continue
        key = (int(phase), int(seq))
        if key in frames or key[1] >= 16 or int(status) or key[0] not in (0, 1):
            raise ValueError('duplicate/failed recovery frame')
        frames[key] = match.start()
    if any(sum(key[0] == phase for key in frames) < 2 for phase in (0, 1)):
        raise ValueError('two intact armed/request frames required')
    if not max(pos for key, pos in frames.items() if key[0] == 0) < events[0].start() < probe[0].start() < min(pos for key, pos in frames.items() if key[0] == 1):
        raise ValueError('arm/probe/request order differs')
    return dict(probe_pass=True, auto_recovery_request_observed=True, boot=boot,
                XNU_executed=False, DMA_terminal_proven=False, hardware_reset_cause_proven=False)


def admit(plan_path, expected, approval_path, approval_sha):
    plan, package = validate_plan(plan_path, expected)
    _, raw = p.pinned(dict(path=str(approval_path), sha256=approval_sha))
    review = json.loads(raw)
    expected_fields = dict(schema=APPROVAL_SCHEMA, decision='approve', version='v154',
                           plan_sha256=expected, cycle=plan['cycle'], build_evidence_id=plan['build_evidence_id'],
                           source_sha256=plan['source_sha256'], XNU_execution_allowed=False,
                           automatic_restore=False, battery_minimum=10, host_BOOT_writes=1,
                           host_reboots=1, internal_kexecs=0, ioctl_limit=0,
                           diagnostic_BOOT_sha256=package['diagnostic_BOOT_sha256'],
                           restore_zip_sha256=package['restore_zip_sha256'])
    if any(type(review.get(key)) is not type(value) or review[key] != value for key, value in expected_fields.items()):
        raise ValueError('exact new bounded Linux physical review required')
    evidence = review.get('reviewed_restore_evidence')
    if type(evidence) is not list or not evidence:
        raise ValueError('bound restore/TWRP evidence required')
    for item in evidence:
        p.pinned(item)
    p.hexid(review.get('adb_sha256'))
    return plan, package, review


def consume(plan, expected):
    folder = p.private(p.ROOT/'note10/private/device-test/v154-consumed-builds')
    folder.mkdir(parents=True, exist_ok=True)
    path = folder/(p.hexid(plan['build_evidence_id'], 32)+'.json')
    with path.open('xb') as stream:
        stream.write((json.dumps(dict(schema=LEDGER_SCHEMA, cycle=plan['cycle'], plan_sha256=expected,
                                     status='reserved-before-mutation', no_replay=True))+'\n').encode())
    return path


def collect(adb, out, identity, cycle):
    accepted = None; pins = {}
    for name, remote in LOGS:
        try:
            raw = adb.call('exec-out', 'cat', remote, timeout=30)
        except (RuntimeError, subprocess.TimeoutExpired, ValueError):
            continue
        if not 0 < len(raw) <= 16*1024*1024:
            continue
        (out/name).write_bytes(raw); pins[name] = p.sha(raw)
        try:
            candidate = decode(raw, identity, cycle)
        except ValueError:
            continue
        if accepted is not None and candidate != accepted:
            raise ValueError('conflicting same-cycle probe evidence')
        accepted = candidate
    if accepted is None:
        raise ValueError('same-build/cycle arm+probe+request evidence absent; return alone is insufficient')
    accepted['log_sha256'] = pins
    p.save(out/'observation.json', accepted)
    return accepted


def run(plan_path, expected, approval_path, approval_sha, output, adb, *, execute=False):
    if not execute:
        raise ValueError('explicit --execute required')
    plan, package, review = admit(plan_path, expected, approval_path, approval_sha)
    if str(Path(adb.path).resolve()) != review.get('adb_path') or adb.serial != review.get('serial') or p.sha(p.ordinary(adb.path, 64*1024*1024)) != review['adb_sha256']:
        raise ValueError('reviewed actual ADB/transport differs')
    out = p.private(output)
    if out.exists():
        raise ValueError('fresh physical output required')
    transport(adb.path, adb.serial)
    old_id = preflight(adb, package, package['expected_current_BOOT_sha256'])
    journal = consume(plan, expected)
    out.mkdir(parents=True)
    ledger = dict(schema=LEDGER_SCHEMA, build_evidence_id=plan['build_evidence_id'], cycle=plan['cycle'],
                  plan_sha256=expected, consumed_build_journal=str(journal), status='consumed',
                  host_BOOT_write_attempts=0, host_reboot_attempts=0, internal_kexecs=0,
                  recovery_returned=False, old_recovery_boot_id=old_id, automatic_restore=False, XNU_executed=False)
    def record():
        p.save(out/'ledger.json', ledger)
    record()
    try:
        mounts = [line.split() for line in adb.text('shell', 'cat', '/proc/mounts').splitlines()]
        rows = [row for row in mounts if len(row) >= 3 and row[1] in ('/', '/tmp')]
        if max(rows, key=lambda row: len(row[1]), default=['', '', ''])[2] not in ('tmpfs', 'ramfs', 'rootfs'):
            raise ValueError('RAM staging required')
        adb.call('shell', 'test', '!', '-L', '/tmp')
        remote = '/tmp/n10-v154-'+plan['cycle']+'.zip'
        adb.call('shell', 'test', '!', '-e', remote)
        adb.call('push', str(Path(plan['packages'])/'diagnostic.zip'), remote, timeout=120)
        observed = adb.text('shell', 'sha256sum', remote).split()
        if not observed or observed[0] != package['diagnostic_zip_sha256']:
            raise ValueError('RAM package staging differs')
        if preflight(adb, package, package['expected_current_BOOT_sha256']) != old_id:
            raise ValueError('recovery epoch changed before write')
        ledger['host_BOOT_write_attempts'] = 1; record()
        # The package updater contains the only BOOT write and verifies readback.
        adb.call('shell', 'twrp', 'install', remote, timeout=120)
        if preflight(adb, package, package['diagnostic_BOOT_sha256']) != old_id:
            raise ValueError('recovery epoch changed during installation')
        ledger['host_reboot_attempts'] = 1; record()
        deadline = time.monotonic()+240
        adb.return_deadline = deadline
        try:
            adb.call('reboot', timeout=15)
            new_id = wait_return(adb, package, old_id, deadline)
        finally:
            adb.return_deadline = None
        ledger.update(recovery_returned=True, new_recovery_boot_id=new_id,
                      status='returned-integrity-verified-probe-pending'); record()
        ledger['observation'] = collect(adb, out, plan['build_evidence_id'], plan['cycle'])
        ledger['status'] = 'cycle-complete-linux-mmap-denied'; record()
    except BaseException as error:
        ledger.update(status='failed-spent-no-retry', error_type=type(error).__name__, error=str(error)[:512]); record()
        raise
    return ledger


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('plan', 'approval', 'output', 'adb'):
        parser.add_argument('--'+name, type=Path, required=True)
    for name in ('plan-sha256', 'approval-sha256', 'serial'):
        parser.add_argument('--'+name, required=True)
    parser.add_argument('--execute', action='store_true')
    args = parser.parse_args()
    print(json.dumps(run(args.plan, args.plan_sha256, args.approval, args.approval_sha256,
                         args.output, ReturnAdb(args.adb, args.serial), execute=args.execute)))
