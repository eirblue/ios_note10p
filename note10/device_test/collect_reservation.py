"""Read previous reservation-test boot logs from TWRP; never change a phone."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import uuid
from decode_reservation import decode
from decode_linux_caps import decode as decode_caps
from run_probe import ROOT,Adb,preflight
from stage_phase2 import verify_packages


def collect(packages,kernel_build,adb):
    records=verify_packages(packages)
    if {r['file'] for r in records}!={'note10-reservation-diagnostic.zip','note10-reservation-rollback.zip'}:
        raise ValueError('Reservation package pair required')
    result=json.loads((kernel_build/'build-result.json').read_text())
    image=(kernel_build/'Image').read_bytes()
    if result.get('build_passed') is not True or result.get('early_xnu_reservation') is not True:
        raise ValueError('Successful reservation kernel build required')
    digest=hashlib.sha256(image).hexdigest()
    if digest!=result['image_sha256'] or digest!=json.loads((packages/'package-result.json').read_text())['kernel_image_sha256']:
        raise ValueError('Kernel source artifact and package differ')
    banners=re.findall(rb'Linux version 4\.14\.113-note10-reserve-pc [^\x00\r\n]+',image)
    if len(banners)!=1:raise ValueError('Expected unique source kernel banner')
    banner=banners[0].decode('ascii')
    state=preflight(adb)
    if not adb.text('shell','getprop','ro.bootloader').startswith('N976N'):raise ValueError('N976N required')
    out=ROOT/'note10/private/device-observations'/('reservation-test-'+uuid.uuid4().hex[:12]);out.mkdir(parents=True)
    logs={}
    for name,remote in (('last_kmsg.txt','/proc/last_kmsg'),('console-ramoops-0','/sys/fs/pstore/console-ramoops-0'),
                        ('dmesg-ramoops-0','/sys/fs/pstore/dmesg-ramoops-0')):
        try:data=adb.call('exec-out','cat',remote,timeout=60)
        except RuntimeError:continue
        if not 0<len(data)<=16*1024*1024:continue
        (out/name).write_bytes(data);logs[name]=data
    report={'directory':str(out),'twrp_version':state['twrp_version'],'kernel_image_sha256':digest,
            'partition_writes':False,'rebooted':False,'xnu_executed':False,
            'previous_boot_reservation_observed':False,
            'logs_sha256':{n:hashlib.sha256(d).hexdigest() for n,d in logs.items()},'decode_failures':{}}
    for name,data in logs.items():
        text=data.decode(errors='replace')
        if banner not in text:
            report['decode_failures'][name]='Exact source build banner not observed';continue
        try:observation=decode(text)
        except ValueError as error:
            report['decode_failures'][name]=str(error);continue
        (out/'reservation-observation.json').write_text(json.dumps(observation,indent=2),encoding='utf-8')
        report.update(previous_boot_reservation_observed=True,evidence_file=name,
                      idle_init_marker_observed='N10INIT1 IDLE ' in text,
                      android_root_mount_message_observed='VFS: Mounted root' in text,
                      kernel_panic_observed='Kernel panic' in text,
                      init_execution_failure_observed='Failed to execute /init' in text or 'No working init found' in text)
        try:
            caps=decode_caps(text)
            (out/'cpu-capabilities.json').write_text(json.dumps(caps,indent=2),encoding='utf-8')
            report['observed_cpus']=caps['observed_cpus']
        except ValueError as error:report['cpu_decode_failure']=str(error)
        break
    (out/'capture-result.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--packages',type=Path,required=True);parser.add_argument('--kernel-build',type=Path,required=True)
    args=parser.parse_args();r=collect(args.packages,args.kernel_build,Adb(ROOT/'host-tools/platform-tools/adb.exe'))
    print(json.dumps({'directory':r['directory'],'previous_boot_reservation_observed':r['previous_boot_reservation_observed'],
                      'partition_writes':False,'xnu_executed':False}))
    if not r['previous_boot_reservation_observed']:raise SystemExit(1)
