"""Pinned Exynos-only native bootstrap selection, without modifying a reference tree."""
import argparse
import difflib
import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
COMMIT = 'ac9718fb1af618d5ce8678d0dc6e8a58f252216f'
OPTION = 'CONFIG_NOTE10_NATIVE_BOOTSTRAP'
PATCH_NAME = '0010-exynos9825-native-bootstrap-selection.patch'
SOURCES = ('osfmk/arm/pmap/pmap.c', 'osfmk/arm/pmap/pmap_cs.c', 'osfmk/arm/pmap/pmap_data.c', 'osfmk/arm/pmap/pmap_iommu.c', 'osfmk/arm/pmap/pmap_misc.c', 'osfmk/arm/pmap/pmap_ppl_interface.c', 'osfmk/arm/arm_init.c', 'osfmk/arm64/arm_vm_init.c', 'osfmk/arm64/pcb.c', 'osfmk/arm/machine_routines_apple.c', 'osfmk/arm64/caches_asm.s', 'osfmk/arm64/locore.s', 'osfmk/arm64/cswitch.s', 'osfmk/arm64/machine_routines_asm.s', 'osfmk/arm64/start.s')
PINS = {'config/MASTER.arm64.exynos9825': 'c6a49e32638777ede9e26113d4da4e0b804af40a67082aa736f5731a276b0ac8', 'osfmk/conf/files.arm64': '50baa4125c35578069773388c95aafbce60479a2c1ebf44b82c64db034fa51ad'}
PATCH_SHA256 = 'd7ee051dc1407ed0655841ba48ee4762d1c6f8063aa420656e915bcef002f264'


def transformed(before):
    if set(before) != set(PINS):
        raise ValueError('exact two source preimages required')
    for name, raw in before.items():
        if hashlib.sha256(raw).hexdigest() != PINS[name]:
            raise ValueError('pinned after-0009 source mismatch: ' + name)
    result = dict(before)
    name = 'config/MASTER.arm64.exynos9825'
    result[name] += b'\n# Project-only source selection; no PPL/SPTM or hardware enablement.\noptions CONFIG_NOTE10_NATIVE_BOOTSTRAP\n'
    name = 'osfmk/conf/files.arm64'
    result[name] += b'\n# Exynos-only alternative ownership; preserve all existing selectors above.\nOPTIONS/config_note10_native_bootstrap optional config_note10_native_bootstrap\n'
    result[name] += ''.join(n + ' optional config_note10_native_bootstrap\n' for n in SOURCES).encode()
    return result


def patch_bytes(before):
    after = transformed(before)
    raw = ''.join(''.join(difflib.unified_diff(before[n].decode().splitlines(True),
        after[n].decode().splitlines(True), fromfile='a/' + n, tofile='b/' + n)) for n in PINS).encode()
    if hashlib.sha256(raw).hexdigest() != PATCH_SHA256:
        raise ValueError('reviewed selection patch mismatch')
    return raw


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source', required=True, help='disposable after-0009 source input')
    p.add_argument('--output', required=True, help='fresh patch file; source is read-only')
    args = p.parse_args()
    source, output = Path(args.source), Path(args.output)
    raw = patch_bytes({n: (source / n).read_bytes() for n in PINS})
    with output.open('xb') as stream:
        stream.write(raw)


if __name__ == '__main__':
    main()
