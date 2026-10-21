"""Create private, non-bootable Mach-O BRK research copies and reversible site metadata."""
import hashlib
import json
from pathlib import Path
import struct
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'note10'))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from inspect_macho import inspect
from generate_pac_oracle import HINT
from capstone import Cs, CS_ARCH_ARM64, CS_MODE_LITTLE_ENDIAN
from active_inputs import userland_root, userland_reports

BRK = 0xd4200000 | (0x4e10 << 5)

def prepare(path):
    report = inspect(path)
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != report['sha256']:
        raise ValueError('Input changed during scan')
    executables, signatures = [], []
    off = 32
    for _ in range(struct.unpack_from('<I', raw, 16)[0]):
        cmd, size = struct.unpack_from('<II', raw, off)
        if cmd in (0x21, 0x2c):
            if size < 20 or struct.unpack_from('<I', raw, off + 16)[0]:
                raise ValueError('Encrypted or malformed image')
        if cmd == 0x19:
            va, vmsize, start, length = struct.unpack_from('<4Q', raw, off + 24)
            if struct.unpack_from('<I', raw, off + 60)[0] & 4:
                if start + length > len(raw): raise ValueError('Executable segment bounds')
                executables.append((start, length, va, vmsize))
        if cmd == 0x1d:
            if size < 16: raise ValueError('Signature command bounds')
            start, length = struct.unpack_from('<II', raw, off + 8)
            if start + length > len(raw): raise ValueError('Signature bounds')
            signatures.append({'offset': start, 'size': length})
        off += size
    md = Cs(CS_ARCH_ARM64, CS_MODE_LITTLE_ENDIAN)
    md.skipdata = True
    sites = []
    used = set()
    for section in report['code_sections']:
        start, length, va = section['offset'], section['size'], int(section['address'], 16)
        if start & 3 or va & 3 or not any(
                start >= p and start + length <= p + n and va == v + start - p and
                va + length <= v + vn for p, n, v, vn in executables):
            raise ValueError('Section outside executable file/VA mapping')
        for address, width, name, operands in md.disasm_lite(raw[start:start + length], va):
            if width != 4: raise ValueError('Unaligned decode')
            if name not in HINT: continue
            pos = start + address - va
            if pos in used: raise ValueError('Overlapping patch sites')
            used.add(pos)
            sites.append({'address': address, 'offset': pos,
                          'original_word': struct.unpack_from('<I', raw, pos)[0],
                          'replacement_word': BRK, 'mnemonic': name})
    sites.sort(key=lambda s: s['address'])
    if any(a['address'] >= b['address'] for a, b in zip(sites, sites[1:])):
        raise ValueError('Duplicate virtual sites')
    patched = bytearray(raw)
    for site in sites: struct.pack_into('<I', patched, site['offset'], BRK)
    restored = bytearray(patched)
    for site in sites: struct.pack_into('<I', restored, site['offset'], site['original_word'])
    if restored != raw: raise ValueError('Reversal failed')
    if path.read_bytes() != raw: raise ValueError('Source modified during preparation')
    return patched, {'source': report['file'], 'source_sha256': report['sha256'],
        'copy_sha256': hashlib.sha256(patched).hexdigest(), 'sites': sites,
        'code_signatures': signatures,
        'signature_status': 'invalidated_by_patch' if sites else 'unchanged_not_verified',
        'reversal_verified': True, 'bootable': False}

def main():
    reports = userland_reports()
    out = ROOT / 'note10/private/hint-copies'
    out.mkdir(parents=True, exist_ok=True)
    results = []
    for report in reports:
        path = (ROOT / report['file']).resolve()
        if not path.is_relative_to(userland_root().resolve()):
            raise ValueError('Unexpected source path')
        patched, manifest = prepare(path)
        if manifest['source_sha256'] != report['sha256']: raise ValueError('Source hash mismatch')
        target = out / (path.name + '.hint-brk.macho')
        target.write_bytes(patched)
        if hashlib.sha256(target.read_bytes()).hexdigest() != manifest['copy_sha256']:
            raise ValueError('Output verification failed')
        target.with_suffix('.json').write_text(json.dumps(manifest, indent=2))
        # Each image is a separate address space/table (dyld starts at VA zero).
        with target.with_suffix('.sites').open('wb') as f:
            f.write(struct.pack('<I', len(manifest['sites'])))
            for s in manifest['sites']: f.write(struct.pack('<QI', s['address'], s['original_word']))
        results.append({'image': path.name, 'sites': len(manifest['sites']),
                        'reversal_verified': True, 'source_unchanged': True})
    (out / 'summary.json').write_text(json.dumps(results, indent=2))
    print(json.dumps(results))

if __name__ == '__main__': main()
