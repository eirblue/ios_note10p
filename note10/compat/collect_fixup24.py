"""Walk original Mach-O format-12 chains with bounds checks; no image modification."""
from pathlib import Path
import hashlib
import json
import random
import struct
from active_inputs import userland_root, userland_reports

ROOT = Path(__file__).resolve().parents[2]


def collect(path):
    b = path.read_bytes()
    def need(ok, why):
        if not ok:
            raise ValueError(f'{path}: {why}')
    need(b[:4] == b'\xcf\xfa\xed\xfe', 'Expected Mach-O64 LE')
    n, total = struct.unpack_from('<II', b, 16)
    need(32 + total <= len(b), 'Commands exceed file')
    pos, segments, chain = 32, [], None
    for _ in range(n):
        need(pos + 8 <= 32 + total, 'Short command')
        cmd, size = struct.unpack_from('<II', b, pos)
        need(size >= 8 and pos + size <= 32 + total, 'Bad command size')
        if cmd == 0x19:
            need(size >= 72, 'Short segment')
            name = b[pos + 8:pos + 24].split(b'\0')[0].decode()
            vm, vmsize, off, length = struct.unpack_from('<QQQQ', b, pos + 24)
            need(off + length <= len(b), 'Segment exceeds file')
            segments.append((name, vm, vmsize, off, length))
        elif cmd == 0x80000034:
            need(size >= 16 and chain is None, 'Bad/duplicate fixup command')
            off, length = struct.unpack_from('<II', b, pos + 8)
            need(off + length <= len(b) and length >= 28, 'Fixup bounds')
            chain = b[off:off + length]
        pos += size
    need(pos == 32 + total and chain is not None, 'Missing fixups')
    version, starts, _, _, imports, _, _ = struct.unpack_from('<7I', chain)
    need(version == 0 and starts + 4 <= len(chain), 'Fixup header')
    (ROOT / 'note10/private' / (path.name + '-fixups.bin')).write_bytes(chain)
    count = struct.unpack_from('<I', chain, starts)[0]
    need(count <= len(segments) and starts + 4 + count * 4 <= len(chain), 'Segment starts bounds')
    base = next(s[1] for s in segments if s[0] == '__TEXT')
    words, pages, page_data, kinds = [], [], [], {'auth_bind': 0, 'auth_rebase': 0, 'bind': 0, 'rebase': 0}
    for i in range(count):
        rel = struct.unpack_from('<I', chain, starts + 4 + i * 4)[0]
        if not rel:
            continue
        p = starts + rel
        need(p + 22 <= len(chain), 'Short starts segment')
        size, page_size, fmt, seg_off, _, page_count = struct.unpack_from('<IHHQIH', chain, p)
        need(fmt == 12, 'Unsupported pointer format')
        need(page_size in (4096, 16384), 'Unsupported page size')
        need(size >= 22 + page_count * 2 and p + size <= len(chain), 'Page starts bounds')
        seg = segments[i]
        need(seg[1] - base == seg_off, 'Segment VM offset mismatch')
        for page in range(page_count):
            start = struct.unpack_from('<H', chain, p + 22 + page * 2)[0]
            if start == 0xffff:
                continue
            need(start < 0x8000, 'Unsupported multiple starts')
            page_off = page * page_size
            need(page_off < seg[4], 'Page outside file-backed segment')
            remaining = min(page_size, seg[4] - page_off)
            local, offsets = start, []
            while True:
                need(local + 8 <= remaining, 'Chain crosses page/file boundary')
                slot = seg[3] + page_off + local
                raw = struct.unpack_from('<Q', b, slot)[0]
                auth, bind = raw >> 63, (raw >> 62) & 1
                if bind:
                    need((raw >> 24) & 255 == 0, 'Nonzero reserved bind bits')
                    need((raw & 0xffffff) < imports, 'Bind ordinal out of import range')
                kinds[('auth_' if auth else '') + ('bind' if bind else 'rebase')] += 1
                words.append(raw)
                offsets.append(local)
                step = ((raw >> 51) & 0x7ff) * 8
                if not step:
                    break
                local += step
            pages.append({'segment': seg[0], 'page': page, 'size': page_size, 'start': start, 'slots': len(offsets)})
            content = b[seg[3] + page_off:seg[3] + page_off + remaining]
            page_data.append((page_size, start, len(offsets), content.ljust(page_size, b'\0')))
    return words, {'file': str(path.relative_to(ROOT)), 'sha256': hashlib.sha256(b).hexdigest(),
                   'fixups': len(words), 'counts': kinds, 'pages': pages}, page_data


def main():
    userland_reports()  # Fail before corpus writes if the active target is not inspected.
    root = userland_root()
    files = [root / 'sbin/launchd', root / 'usr/lib/dyld',
             root / 'System/Library/CoreServices/SpringBoard.app/SpringBoard']
    words, reports, page_data = [], [], []
    for path in files:
        data, report, fixtures = collect(path)
        words.extend(data); reports.append(report)
        page_data.extend(fixtures)
        print(path.name, report['fixups'], report['counts'])
    actual_count = len(words)
    rng = random.Random(976)
    words.extend(rng.getrandbits(64) for _ in range(20000))
    # Boundary values for all fields and signed addends; bits interpreted by the
    # independent Apple bitfield header in the native test, not Python expected data.
    words.extend((0, (1 << 64) - 1, 1 << 63, 1 << 62, 3 << 62))
    for auth in (0, 1):
        for addend in (0, 1, 0x3ffff, 0x40000, 0x7ffff):
            words.append((auth << 63) | (1 << 62) | (addend << 32) | 0xffffff)
    out = ROOT / 'note10/private/fixup24-corpus.bin'
    out.write_bytes(b''.join(struct.pack('<Q', w) for w in words))
    with out.with_suffix('.pages').open('wb') as f:
        f.write(struct.pack('<I', len(page_data)))
        for size, start, count, content in page_data:
            f.write(struct.pack('<IHHI', size, start, 0, count))
            f.write(content)
    result = {'actual_fixups': actual_count, 'records': len(words), 'actual_pages': len(page_data), 'files': reports}
    out.with_suffix('.json').write_text(json.dumps(result, indent=2))
    print('Total actual fixups:', actual_count, 'test records:', len(words))


if __name__ == '__main__':
    main()
