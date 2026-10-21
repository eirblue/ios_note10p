"""Bundle a RAM-only probe, host scripts and the existing Windows ADB runtime."""
import hashlib
import json
from pathlib import Path
import zipfile
from build_package import ROOT, HERE, OUT, build


def main():
    probe = build()
    files = {'note10-phase1-probe.zip': probe.read_bytes(),
             'README.ko.md': (HERE/'README.ko.md').read_bytes()}
    for name in ('run_probe.py','run-probe.ps1','analyze_capture.py','collect.sh'):
        files['note10/device_test/'+name] = (HERE/name).read_bytes()
    files['note10/inspect_firmware.py'] = (ROOT/'note10/inspect_firmware.py').read_bytes()
    platform = ROOT/'host-tools/platform-tools'
    for name in ('adb.exe','AdbWinApi.dll','AdbWinUsbApi.dll','libwinpthread-1.dll','NOTICE.txt','source.properties'):
        files['host-tools/platform-tools/'+name] = (platform/name).read_bytes()
    manifest = {'schema': 1, 'phase': 'linux-recovery-observation', 'target': 'SM-N976N / d2x',
                'xnu_executed': False, 'partition_writes': False,
                'requires': ['working compatible TWRP', 'Windows Python 3', 'USB ADB connection'],
                'files': {n:hashlib.sha256(v).hexdigest() for n,v in files.items()}}
    files['bundle-manifest.json'] = json.dumps(manifest,indent=2).encode()
    result = OUT/'note10-phase1-windows-kit.zip'
    with zipfile.ZipFile(result,'w',zipfile.ZIP_DEFLATED) as archive:
        for name, data in sorted(files.items()):
            entry=zipfile.ZipInfo(name,(2026,1,1,0,0,0));entry.create_system=3
            entry.external_attr=0o100644<<16;entry.compress_type=zipfile.ZIP_DEFLATED
            archive.writestr(entry,data)
    report={'bundle':str(result.relative_to(ROOT)), 'size':result.stat().st_size,
            'sha256':hashlib.sha256(result.read_bytes()).hexdigest(),
            'probe_sha256':hashlib.sha256(probe.read_bytes()).hexdigest(),
            'file_count':len(files),'device_tested':False,'xnu_executed':False}
    (OUT/'bundle-result.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report))


if __name__=='__main__':main()
