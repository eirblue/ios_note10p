"""Copy verified phase-2 ZIPs to a fresh TWRP RAM directory; never install."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import uuid
import zipfile
from run_probe import Adb,ROOT,preflight


def verify_packages(directory):
    result=json.loads((directory/'package-result.json').read_text())
    expected={'note10-phase2-diagnostic.zip','note10-phase2-rollback.zip'}
    records=result.get('packages',[])
    if len(records)!=2 or {r['file'] for r in records}!=expected:raise ValueError('Expected paired phase-2 packages')
    for record in records:
        path=directory/record['file']
        if path.is_symlink() or not 0<path.stat().st_size<=128*1024*1024:raise ValueError('Unsafe package file')
        if hashlib.sha256(path.read_bytes()).hexdigest()!=record['sha256']:raise ValueError('Package hash mismatch')
        with zipfile.ZipFile(path) as archive:
            if len(archive.namelist())!=len(set(archive.namelist())) or archive.testzip() is not None:
                raise ValueError('Invalid/duplicate archive members')
            meta=json.loads(archive.read('manifest.json'))
            if meta['writes']!=['boot'] or meta['automatic_reboot'] is not False:raise ValueError('Unexpected installer scope')
            if hashlib.sha256(archive.read('META-INF/com/google/android/update-binary')).hexdigest()!=meta['updater_sha256']:
                raise ValueError('Updater integrity mismatch')
            if hashlib.sha256(archive.read('boot.img')).hexdigest()!=meta['payload_sha256']:
                raise ValueError('Payload integrity mismatch')
    return records


def stage(directory,adb):
    records=verify_packages(directory)
    state=preflight(adb)
    bootloader=adb.text('shell','getprop','ro.bootloader')
    if not re.fullmatch(r'N976N[A-Z0-9]+',bootloader):raise ValueError('N976N bootloader required')
    if not adb.text('shell','ls','-ld','/tmp').startswith('d'):raise ValueError('Unexpected tmp path')
    mounts=adb.text('shell','cat','/proc/mounts')
    candidates=[line.split() for line in mounts.splitlines() if len(line.split())>=3 and line.split()[1] in ('/','/tmp')]
    if not candidates or max(candidates,key=lambda row:len(row[1]))[2] not in ('tmpfs','ramfs','rootfs'):
        raise ValueError('Memory-backed tmp required')
    tools=adb.text('shell','command','-v','sh','unzip','dd','sha256sum','blockdev','readlink','sync','awk')
    if len(tools.splitlines())!=8:raise ValueError('Required native TWRP utilities not all found')
    remote='/tmp/note10-phase2-'+uuid.uuid4().hex[:8]
    adb.call('shell','mkdir',remote)
    adb.call('shell','chmod','700',remote)
    for record in records:
        target=remote+'/'+record['file']
        adb.call('push',str(directory/record['file']),target,timeout=120)
        digest=adb.text('shell','sha256sum',target).split()[0]
        if digest!=record['sha256']:raise ValueError('RAM copy checksum mismatch')
        native_meta=json.loads(adb.text('shell','unzip','-p',target,'manifest.json'))
        if native_meta['payload_sha256']!=record['payload_sha256']:raise ValueError('Native ZIP manifest mismatch')
    report={'ram_directory':remote,'packages':[r['file'] for r in records],
            'model':state['model'],'twrp_version':state['twrp_version'],
            'native_archive_read_verified':True,'installed':False,'rebooted':False,
            'partition_writes':False,'xnu_executed':False,'deployment_ready':False,
            'scope':'TWRP RAM file staging only; paths disappear on reboot'}
    (directory/('ram-stage-'+remote.rsplit('-',1)[1]+'.json')).write_text(json.dumps(report,indent=2),encoding='utf-8')
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--packages',type=Path,required=True)
    report=stage(parser.parse_args().packages,Adb(ROOT/'host-tools/platform-tools/adb.exe'))
    print(json.dumps(report))
