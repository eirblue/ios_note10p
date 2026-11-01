"""Pinned Exynos-only early-clock patch; source input is never modified here."""
import argparse
import difflib
import hashlib
from pathlib import Path
import re
from prepare_native_bootstrap_selection import ROOT

PATCH_NAME = '0011-exynos9825-early-counter-clock.patch'
REL = 'pexpert/arm/pe_identify_machine.c'
KERNEL_COMPONENT = 'pexpert/arm/note10/early_clock.c'
SOURCE_PIN = 'f6d325385d7948e5df7549f8564fe7cea994fe144a8c9f03eff94f5f76cc6e95'
COMPONENT_SHA256 = '95670dd17837380c83aa20e8972ab8b0eb7e786ad6949c7d528991bf5aba0620'
PATCH_SHA256 = 'b686155a549e5249c8d7031f8827b6970067de759bf610461354b0118c4bf0f6'
HERE = Path(__file__).resolve().parent


def patch_bytes(before, component):
    if hashlib.sha256(before).hexdigest() != SOURCE_PIN or hashlib.sha256(component).hexdigest() != COMPONENT_SHA256:
        raise ValueError('pinned source and exact tested clock component required')
    text = before.decode()
    replacements = [
        ('#include <kern/locks.h>\n', '#include <kern/locks.h>\n\n#if defined(ARM64_BOARD_CONFIG_EXYNOS9825)\n#include "note10/early_clock.c"\n#endif\n'),
        ('pe_identify_machine(boot_args * bootArgs)\n{\n', 'pe_identify_machine(boot_args * bootArgs)\n{\n#if defined(ARM64_BOARD_CONFIG_EXYNOS9825)\n\t(void)bootArgs;\n\tpe_note10_early_clock_init();\n\treturn;\n#else\n'),
        ('\t    gPEClockFrequencyInfo.bus_clock_rate_hz / gPEClockFrequencyInfo.dec_clock_rate_hz;\n}\n', '\t    gPEClockFrequencyInfo.bus_clock_rate_hz / gPEClockFrequencyInfo.dec_clock_rate_hz;\n#endif\n}\n'),
    ]
    for old, new in replacements:
        if text.count(old) != 1:
            raise ValueError('exact early-clock insertion context required')
        text = text.replace(old, new, 1)
    raw = (''.join(difflib.unified_diff(before.decode().splitlines(True), text.splitlines(True), fromfile='a/' + REL, tofile='b/' + REL)) +
           ''.join(difflib.unified_diff([], component.decode().splitlines(True), fromfile='/dev/null', tofile='b/' + KERNEL_COMPONENT))).encode()
    if hashlib.sha256(raw).hexdigest() != PATCH_SHA256:
        raise ValueError('reviewed literal clock patch required')
    return raw


def embedded_component(patch):
    """Read only this added-file hunk, to bind kernel source to the tested C bytes."""
    marker = ('--- /dev/null\n+++ b/' + KERNEL_COMPONENT + '\n').encode()
    if patch.count(marker) != 1:
        raise ValueError('one exact added clock component required')
    block = patch.split(marker, 1)[1]
    hunk, _, body = block.partition(b'\n')
    match = re.fullmatch(rb'@@ -0,0 \+1,([0-9]+) @@', hunk)
    lines = body.splitlines(keepends=True)
    if not match or len(lines) != int(match[1]) or any(not line.startswith(b'+') for line in lines):
        raise ValueError('exact complete added-file hunk required')
    raw = b''.join(line[1:] for line in lines)
    if hashlib.sha256(raw).hexdigest() != COMPONENT_SHA256:
        raise ValueError('kernel component differs from the reviewed/tested C file')
    return raw


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', required=True, help='read-only disposable after-0010 source')
    parser.add_argument('--output', required=True, help='fresh patch output')
    args = parser.parse_args()
    component = (HERE / 'exynos_early_clock.c').read_bytes()
    raw = patch_bytes((Path(args.source) / REL).read_bytes(), component)
    with Path(args.output).open('xb') as stream:
        stream.write(raw)


if __name__ == '__main__':
    main()
