"""Read a manually booted diagnostic kernel; never install or reboot."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import uuid
from decode_linux_caps import decode
from run_probe import Adb, ROOT, preflight


def collect(adb):
    state=preflight(adb)
    bootloader=adb.text('shell','getprop','ro.bootloader')
    if not bootloader.startswith('N976N'):raise ValueError('N976N required')
    release=adb.text('shell','uname','-r')
    if release!='4.14.113-note10-handoff-pc':
        raise ValueError('Diagnostic BOOT kernel is not running; use manual Reboot > System after installation')
    output=ROOT/'note10/private/device-observations'/('phase2-'+uuid.uuid4().hex[:16])
    output.mkdir(parents=True,exist_ok=False)
    records={}
    for name,args in (('dmesg.txt',('shell','dmesg')),('config.gz',('exec-out','cat','/proc/config.gz')),
                      ('live.dtb',('exec-out','cat','/sys/firmware/fdt'))):
        data=adb.call(*args,timeout=60)
        if not 0<len(data)<=16*1024*1024:raise ValueError('Missing or oversized capture: '+name)
        (output/name).write_bytes(data)
        records[name]=hashlib.sha256(data).hexdigest()
    report={'kernel_release':release,'model':state['model'],'twrp_version':state['twrp_version'],
            'files_sha256':records,'partition_writes':False,'rebooted':False,'xnu_executed':False,
            'capture_verified':False,'deployment_ready':False}
    try:
        config=gzip.decompress((output/'config.gz').read_bytes()).decode().splitlines()
        if not {'CONFIG_KEXEC=y','CONFIG_KEXEC_CORE=y'}.issubset(config):
            raise ValueError('Expected kexec configuration missing')
        caps=decode((output/'dmesg.txt').read_text(encoding='utf-8',errors='replace'))
        (output/'cpu-capabilities.json').write_text(json.dumps(caps,indent=2),encoding='utf-8')
        report['capture_verified']=True
        report['observed_cpus']=caps['observed_cpus']
    except (ValueError,OSError) as error:
        report['failure']=str(error)
        raise
    finally:
        (output/'capture-result.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    return {'capture_verified':True,'directory':str(output),'observed_cpus':report['observed_cpus'],
            'partition_writes':False,'xnu_executed':False}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--serial')
    args=parser.parse_args()
    print(json.dumps(collect(Adb(ROOT/'host-tools/platform-tools/adb.exe',args.serial))))
