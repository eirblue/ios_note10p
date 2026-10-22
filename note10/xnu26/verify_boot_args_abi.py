"""Compile the pinned real XNU header and compare its layout and data bytes.

Uses the saved local Windows compile environment; does not run ARM code.
"""
import hashlib
import json
from pathlib import Path
import struct
import subprocess
from boot_contract import SIZE, OFFSETS, encode_boot_args

ROOT = Path(__file__).resolve().parents[2]


def symbol_bytes(raw, name, length):
    if struct.unpack_from('<4I', raw) != (0xfeedfacf, 0x100000c, 0, 1):
        raise ValueError('Expected arm64 Mach-O object')
    count, total = struct.unpack_from('<II', raw, 16)
    offset = 32; sections = []; symtab = None
    for _ in range(count):
        cmd, size = struct.unpack_from('<II', raw, offset)
        if size < 8 or offset + size > 32 + total: raise ValueError('Bad object command')
        if cmd == 0x19:
            nsects = struct.unpack_from('<I', raw, offset + 64)[0]
            if size != 72 + nsects * 80: raise ValueError('Bad section table')
            for index in range(nsects):
                at = offset + 72 + index * 80
                addr, extent, fileoff = struct.unpack_from('<QQI', raw, at + 32)
                nreloc = struct.unpack_from('<I', raw, at + 60)[0]
                sections.append((addr, extent, fileoff, nreloc))
        elif cmd == 2: symtab = struct.unpack_from('<4I', raw, offset + 8)
        offset += size
    if offset != 32 + total or symtab is None: raise ValueError('Missing object symbols')
    at, count, strings, extent = symtab
    if at + count * 16 > len(raw) or strings + extent > len(raw): raise ValueError('Bad symbol bounds')
    names = raw[strings:strings + extent]
    for index in range(count):
        key, kind, section, _, value = struct.unpack_from('<IBBHQ', raw, at + index * 16)
        end = names.find(b'\0', key)
        if end < 0: raise ValueError('Unterminated symbol')
        if names[key:end].decode() != name: continue
        if kind & 0xe0 or kind & 0xe != 0xe or not 0 < section <= len(sections):
            raise ValueError('Expected section-defined oracle symbol')
        addr, extent, fileoff, nreloc = sections[section - 1]
        position = fileoff + value - addr
        if nreloc or value < addr or value + length > addr + extent or position + length > len(raw):
            raise ValueError('Oracle bytes require relocation or exceed section')
        return raw[position:position + length]
    raise ValueError('Missing oracle symbol: ' + name)


def main():
    reference = json.loads((ROOT / 'research/ios26/xnu-reference.json').read_text())
    header = ROOT / reference['source_directory'] / 'pexpert/pexpert/arm64/boot.h'
    output = ROOT / 'note10/private/boot-contract'; output.mkdir(exist_ok=True)
    source = output / 'abi-oracle.c'; obj = output / 'abi-oracle.o'
    fields = ', '.join('__builtin_offsetof(boot_args, ' + field + ')' for field in OFFSETS)
    source.write_text('#include "' + header.as_posix() + '"\n'
        'const unsigned long long note10_layout[] = {sizeof(boot_args), ' + fields + '};\n'
        'const boot_args note10_fixture = {\n'
        '.Revision=2, .Version=2, .virtBase=0xfffffff000000000ULL, .physBase=0x80000000ULL,\n'
        '.memSize=0x40000000ULL, .topOfKernelData=0x88004000ULL,\n'
        '.Video={1,2,3,4,5,6}, .machineType=7,\n'
        '.deviceTreeP=(void*)0xfffffff006008000ULL, .deviceTreeLength=0x1234,\n'
        '.CommandLine="debug=0x14e", .bootFlags=0, .memSizeActual=0x40000000ULL};\n', encoding='utf-8')
    saved = json.loads((ROOT / 'note10/private/windows-xnu/objects/DEVELOPMENT/compile-result.json').read_text())
    command = list(next(u for u in saved['units'] if u['source'] == 'osfmk/arm64/machine_routines.c')['command'])
    command[command.index('-c') + 1] = str(source)
    command[command.index('-o') + 1] = str(obj)
    result = subprocess.run(command, capture_output=True, text=True, encoding='utf-8', errors='replace')
    (output / 'compile.log').write_text(result.stdout + result.stderr, encoding='utf-8')
    if result.returncode: raise RuntimeError('ABI oracle compilation failed; see private compile.log')
    raw = obj.read_bytes()
    layout = struct.unpack('<' + 'Q' * (len(OFFSETS) + 1), symbol_bytes(raw, '_note10_layout', 8 * (len(OFFSETS) + 1)))
    if layout != (SIZE, *OFFSETS.values()): raise ValueError('Boot arguments disagree with real header ABI')
    expected = encode_boot_args(virtual_base=0xfffffff000000000, physical_base=0x80000000,
        memory_size=0x40000000, top_of_kernel=0x88004000, video=(1,2,3,4,5,6), machine_type=7,
        device_tree_pointer=0xfffffff006008000, device_tree_length=0x1234, command_line='debug=0x14e')
    if symbol_bytes(raw, '_note10_fixture', SIZE) != expected:
        raise ValueError('Python serialization differs from actual C initializer')
    report = dict(passed=True, structure_size=SIZE, offsets=OFFSETS,
                  c_initializer_bytes_compared=SIZE, source_commit=reference['commit'],
                  header_sha256=hashlib.sha256(header.read_bytes()).hexdigest(),
                  object_sha256=hashlib.sha256(raw).hexdigest(), command=command,
                  scope='Real public XNU header ABI only; not proof of IPSW ABI or device boot',
                  hardware_verified=False, deployment_ready=False, device_operations=[])
    (output / 'abi-result.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps({key:report[key] for key in ('passed','structure_size','c_initializer_bytes_compared','source_commit')}))


if __name__ == '__main__': main()
