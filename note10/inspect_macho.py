#!/usr/bin/env python3
"""Read-only thin ARM64 Mach-O metadata and static authentication instruction scan."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import struct
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'host-tools/python-packages'))
import capstone


def inspect(path):
    raw = path.read_bytes()

    def check(ok, reason):
        if not ok:
            raise ValueError(f'{path}: {reason}')

    def text(b):
        return b.split(b'\0', 1)[0].decode('utf-8', errors='replace')

    check(len(raw) >= 32 and raw[:4] == b'\xcf\xfa\xed\xfe', 'Expected thin little-endian Mach-O 64')
    _, cpu, subtype, kind, ncmds, sizeofcmds, flags, _ = struct.unpack_from('<8I', raw)
    check(cpu == 0x0100000c, 'Expected ARM64')
    check(32 + sizeofcmds <= len(raw) and ncmds <= sizeofcmds // 8, 'Load command bounds')
    report = {'file': str(path.relative_to(ROOT)), 'size': len(raw), 'sha256': hashlib.sha256(raw).hexdigest(),
              'cpu_type': hex(cpu), 'cpu_subtype': hex(subtype), 'filetype': kind, 'flags': hex(flags),
              'capstone_version': capstone.__version__, 'libraries': [], 'code_sections': [],
              'chained_fixup_pointer_formats': [],
              'limits': ['Static scan only; no execution or control-flow reachability proof.',
                         'Decoder may not recognize newer instructions; unknown words are reported.',
                         'Counts cover instruction-marked sections, not all libraries or dyld caches.']}
    off = 32
    decoder = capstone.Cs(capstone.CS_ARCH_ARM64, capstone.CS_MODE_LITTLE_ENDIAN)
    decoder.skipdata = True
    counts, examples, unknown = Counter(), {}, 0
    for _ in range(ncmds):
        check(off + 8 <= 32 + sizeofcmds, 'Command header bounds')
        cmd, size = struct.unpack_from('<II', raw, off)
        check(size >= 8 and off + size <= 32 + sizeofcmds, 'Command bounds')
        if cmd == 0x19:
            check(size >= 72, 'Segment header bounds')
            seg = text(raw[off + 8:off + 24])
            nsections = struct.unpack_from('<I', raw, off + 64)[0]
            check(72 + nsections * 80 <= size, 'Section bounds')
            for i in range(nsections):
                s = off + 72 + 80 * i
                name = text(raw[s:s + 16])
                addr, length, fileoff = struct.unpack_from('<QQI', raw, s + 32)
                secflags = struct.unpack_from('<I', raw, s + 64)[0]
                if secflags & (0x80000000 | 0x400):
                    check(fileoff + length <= len(raw) and length % 4 == 0, 'Code section bounds/alignment')
                    report['code_sections'].append({'segment': seg, 'section': name, 'offset': fileoff,
                                                    'address': hex(addr), 'size': length})
                    for va, ilen, mnemonic, operands in decoder.disasm_lite(raw[fileoff:fileoff + length], addr):
                        if mnemonic == '.byte':
                            unknown += ilen
                        elif mnemonic.startswith(('pac', 'aut', 'xpac', 'braa', 'brab', 'blraa', 'blrab', 'retaa', 'retab')):
                            counts[mnemonic] += 1
                            if len(examples.setdefault(mnemonic, [])) < 3:
                                examples[mnemonic].append({'address': hex(va), 'operands': operands})
        elif cmd in (0xc, 0x80000018, 0x8000001f, 0x80000023):
            check(size >= 24, 'Dylib header bounds')
            nameoff = struct.unpack_from('<I', raw, off + 8)[0]
            check(24 <= nameoff < size, 'Dylib name bounds')
            report['libraries'].append(text(raw[off + nameoff:off + size]))
        elif cmd == 0x32:
            check(size >= 24, 'Build version bounds')
            platform, minimum, sdk, _ = struct.unpack_from('<4I', raw, off + 8)
            ver = lambda v: f'{v >> 16}.{(v >> 8) & 255}.{v & 255}'
            report['build_version'] = {'platform': platform, 'minimum': ver(minimum), 'sdk': ver(sdk)}
        elif cmd == 0x80000034:
            check(size >= 16, 'Fixup command bounds')
            start, length = struct.unpack_from('<II', raw, off + 8)
            check(start + length <= len(raw) and length >= 28, 'Fixup data bounds')
            fix = raw[start:start + length]
            starts = struct.unpack_from('<I', fix, 4)[0]
            check(starts + 4 <= len(fix), 'Fixup starts bounds')
            count = struct.unpack_from('<I', fix, starts)[0]
            check(starts + 4 + count * 4 <= len(fix), 'Fixup segment table bounds')
            for i in range(count):
                rel = struct.unpack_from('<I', fix, starts + 4 + 4 * i)[0]
                if rel:
                    pos = starts + rel
                    check(pos + 8 <= len(fix), 'Fixup segment header bounds')
                    fmt = struct.unpack_from('<H', fix, pos + 6)[0]
                    report['chained_fixup_pointer_formats'].append(fmt)
        off += size
    check(off == 32 + sizeofcmds, 'Load command size mismatch')
    report['authentication_instruction_counts'] = dict(sorted(counts.items()))
    report['examples'] = examples
    report['undecoded_bytes'] = unknown
    return report


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('files', nargs='+', type=Path)
    target = json.loads((ROOT / 'note10/target.json').read_text())
    p.add_argument('--out', type=Path, default=ROOT / target['research_directory'] / 'userland-report.json')
    a = p.parse_args()
    reports = [inspect(f.resolve()) for f in a.files]
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(reports, indent=2), encoding='utf-8')
    for r in reports:
        print(Path(r['file']).name, r['cpu_subtype'], r.get('build_version'),
              'auth=', r['authentication_instruction_counts'], 'unknown bytes=', r['undecoded_bytes'])


if __name__ == '__main__':
    main()
