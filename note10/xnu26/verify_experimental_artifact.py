"""Read-only validation of a downloaded source-built kernel; never executes it."""
import argparse
import hashlib
import json
from pathlib import Path
import struct


def verify(directory):
    manifest = json.loads((directory / 'build-manifest.json').read_text())
    binary = directory / 'note10-experimental.macho'
    raw = binary.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    if digest != manifest['output_sha256'] or len(raw) != manifest['output_size']:
        raise ValueError('Downloaded executable differs from build manifest')
    magic, cpu, subtype, kind, count, size, flags, reserved = struct.unpack_from('<8I', raw)
    if (magic, cpu, subtype, kind) != (0xfeedfacf, 0x100000c, 0, 2):
        raise ValueError('Expected plain arm64 MH_EXECUTE')
    if 32 + size > len(raw):raise ValueError('Load command table exceeds file')
    offset = 32; segments = []; entry = None; symtab = None
    for _ in range(count):
        cmd, length = struct.unpack_from('<II', raw, offset)
        if length < 8 or length % 8 or offset + length > 32 + size:
            raise ValueError('Invalid load command bounds')
        if cmd in (0xc, 0x18 | 0x80000000, 0x1f | 0x80000000, 0x20, 0x23 | 0x80000000):
            raise ValueError('Unexpected dynamic library load command')
        if cmd == 0x19:
            name = raw[offset+8:offset+24].split(b'\0')[0].decode()
            vm, vsize, fileoff, filesize, maximum, initial, nsects, _ = struct.unpack_from('<4Q4I', raw, offset+24)
            if length != 72 + nsects * 80 or fileoff + filesize > len(raw) or filesize > vsize:
                raise ValueError('Invalid segment extent: ' + name)
            if initial & 7 == 7:raise ValueError('Writable executable segment: ' + name)
            segments.append({'name': name, 'virtual_address': vm, 'virtual_size': vsize,
                             'file_offset': fileoff, 'file_size': filesize, 'initial_protection': initial})
        elif cmd == 0x5:
            flavor, state_count = struct.unpack_from('<II', raw, offset+8)
            if flavor != 6 or state_count != 68 or length != 288:
                raise ValueError('Unexpected ARM64 thread entry format')
            entry = struct.unpack_from('<Q', raw, offset+16+256)[0]
        elif cmd == 0x2:
            symtab = struct.unpack_from('<4I', raw, offset+8)
        offset += length
    if offset != 32 + size:raise ValueError('Incorrect load command table size')
    ordered = sorted((s for s in segments if s['virtual_size']), key=lambda s:s['virtual_address'])
    for left, right in zip(ordered, ordered[1:]):
        if left['virtual_address'] + left['virtual_size'] > right['virtual_address']:
            raise ValueError('Overlapping virtual segments')
    if entry is None or not any(s['initial_protection'] & 4 and
                               s['virtual_address'] <= entry < s['virtual_address'] + s['file_size'] for s in segments):
        raise ValueError('Entry is not in a file-backed executable segment')
    if symtab is None:raise ValueError('Missing kernel symbol table')
    symoff, nsyms, stroff, strsize = symtab
    if symoff + nsyms * 16 > len(raw) or stroff + strsize > len(raw):
        raise ValueError('Symbol table exceeds file')
    strings = raw[stroff:stroff+strsize]; symbols = {}; undefined = []
    for i in range(nsyms):
        index, stype, section, desc, value = struct.unpack_from('<IBBHQ', raw, symoff + i*16)
        if stype & 0xe0:continue  # STAB debugging records do not define ABI symbols.
        if index >= len(strings):raise ValueError('Invalid symbol string index')
        end = strings.find(b'\0', index)
        if end < 0:raise ValueError('Unterminated symbol name')
        name = strings[index:end].decode()
        if stype & 0xe == 0 and name:undefined.append(name)
        else:symbols[name] = value
    if undefined:raise ValueError('Undefined symbols in executable: ' + ', '.join(undefined[:8]))
    required = ('__start', '_start_first_cpu', '_arm_init', '_arm_vm_init', '_pmap_bootstrap', '_PE_init_platform')
    if not all(n in symbols for n in required):raise ValueError('Missing architecture entry symbol')
    if symbols['__start'] != entry:raise ValueError('Thread PC differs from __start')
    return {'structure_verified': True, 'sha256': digest, 'size': len(raw),
            'entry_virtual_address': hex(entry), 'entry_matches_start': True,
            'architecture_symbols': {n: hex(symbols[n]) for n in required},
            'segments': segments, 'undefined_symbols': [], 'deployment_ready': False,
            'hardware_verified': False, 'device_operations': []}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', type=Path)
    parser.add_argument('--report', type=Path)
    args = parser.parse_args()
    result = verify(args.directory)
    if args.report:args.report.write_text(json.dumps(result, indent=2))
    print(json.dumps({k: result[k] for k in ('structure_verified', 'size', 'entry_virtual_address', 'deployment_ready')}))


if __name__ == '__main__':main()
