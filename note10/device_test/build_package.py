"""Build a deterministic TWRP diagnostic ZIP containing scripts only."""
import hashlib
import json
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
OUT = ROOT / 'note10/private/device-test'


def build():
    OUT.mkdir(parents=True, exist_ok=True)
    collector = (HERE / 'collect.sh').read_text(encoding='utf-8').replace('\r\n', '\n')
    # This is a RAM-only probe. TWRP install executes this updater; it does not
    # contain a partition-writing installer or firmware image.
    prelude = '''#!/sbin/sh
FD=$2
case "$FD" in ''|*[!0-9]*) exit 1 ;; esac
ui_print() { printf 'ui_print %s\\nui_print\\n' "$*" > "/proc/self/fd/$FD"; }
ui_print "Note10 phase-1 hardware probe; XNU is not executed."
trap 'RC=$?; if [ "$RC" = 0 ]; then ui_print "Probe complete. Pull /tmp/note10-probe before reboot."; else ui_print "Probe failed; inspect recovery log."; fi' EXIT
set -- "/tmp/note10-probe/session-$$"
'''
    files = {
        'META-INF/com/google/android/update-binary': (prelude + collector.split('\n', 1)[1]).encode(),
        'META-INF/com/google/android/updater-script': b'# RAM-only diagnostic updater; no partition writes.\n',
        'collect.sh': collector.encode(),
    }
    manifest = {'schema': 1, 'phase': 'linux-recovery-observation',
                'target': 'SM-N976N / d2x', 'requires': ['unlocked bootloader', 'working compatible TWRP'],
                'xnu_executed': False, 'partition_writes': False, 'automatic_reboot': False,
                'outputs': '/tmp/note10-probe/session-* (RAM; pull before reboot)',
                'files': {n: hashlib.sha256(b).hexdigest() for n,b in files.items()}}
    files['probe-manifest.json'] = json.dumps(manifest, indent=2).encode()
    path = OUT / 'note10-phase1-probe.zip'
    with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED) as archive:
        for name, data in sorted(files.items()):
            entry = zipfile.ZipInfo(name, (2026, 1, 1, 0, 0, 0))
            entry.create_system = 3
            entry.external_attr = (0o100755 if name.endswith(('update-binary', '.sh')) else 0o100644) << 16
            entry.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(entry, data)
    result = {'package': str(path.relative_to(ROOT)), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
              'size': path.stat().st_size, **manifest}
    (OUT / 'package-result.json').write_text(json.dumps(result, indent=2))
    print(json.dumps({k:result[k] for k in ('package','size','sha256','xnu_executed')}))
    return path


if __name__ == '__main__':build()
