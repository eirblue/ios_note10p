"""Independent Capstone oracle for PAC/AUT/XPAC register, zero and hint forms."""
import json
from pathlib import Path
import random
import struct
import sys
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'host-tools/python-packages'))
from capstone import Cs, CS_ARCH_ARM64, CS_MODE_LITTLE_ENDIAN
from active_inputs import userland_reports

REG = {name: (op, key) for op, stem in enumerate(('pac', 'aut'))
       for key, suffix in enumerate(('ia', 'ib', 'da', 'db')) for name in (stem + suffix,)}
ZERO = {name: (op, key) for op, stem in enumerate(('pac', 'aut'))
        for key, suffix in enumerate(('iza', 'izb', 'dza', 'dzb')) for name in (stem + suffix,)}
HINT = {
    'pacia1716': (0,0,17,0,16), 'pacib1716': (0,1,17,0,16),
    'autia1716': (1,0,17,0,16), 'autib1716': (1,1,17,0,16),
    'paciaz': (0,0,30,2,31), 'pacibz': (0,1,30,2,31),
    'autiaz': (1,0,30,2,31), 'autibz': (1,1,30,2,31),
    'paciasp': (0,0,30,1,31), 'pacibsp': (0,1,30,1,31),
    'autiasp': (1,0,30,1,31), 'autibsp': (1,1,30,1,31),
    'xpaclri': (2,0,30,2,31),
}

def expected(name, operands):
    reg = lambda x: 31 if x in ('xzr', 'sp') else int(x[1:])
    parts = [p.strip() for p in operands.split(',')]
    if name in REG:
        op, key = REG[name]
        return (1, op, key, reg(parts[0]), 1 if parts[1] == 'sp' else 0, reg(parts[1]), 0, 0)
    if name in ZERO:
        op, key = ZERO[name]
        return (1, op, key, reg(parts[0]), 2, 31, 0, 0)
    if name in ('xpaci', 'xpacd'):
        return (1, 2, 0 if name == 'xpaci' else 2, reg(parts[0]), 2, 31, 0, 0)
    if name in HINT:
        return (1, *HINT[name], 1, 0)
    return (0,) * 8

def main():
    reports = userland_reports()
    md = Cs(CS_ARCH_ARM64, CS_MODE_LITTLE_ENDIAN)
    words = {0xdac10000 | group << 10 | rn << 5 | rd for group in range(8) for rn in range(32) for rd in range(32)}
    for base in (0xdac123e0,0xdac127e0,0xdac12be0,0xdac12fe0,0xdac133e0,0xdac137e0,0xdac13be0,0xdac13fe0,0xdac143e0,0xdac147e0):
        words.update(base | rd for rd in range(32))
    words.update((0xd503211f,0xd503215f,0xd503219f,0xd50321df,0xd503231f,0xd503233f,0xd503235f,0xd503237f,0xd503239f,0xd50323bf,0xd50323df,0xd50323ff,0xd50320ff))
    for word in tuple(sorted(words))[::16]:
        words.update(word ^ (1 << bit) for bit in range(32))
    rng = random.Random(976)
    words.update(rng.getrandbits(32) for _ in range(20000))
    out = ROOT / 'note10/private/pac-instruction-oracle.bin'
    count = supported = actual = hints = 0
    with out.open('wb') as f:
        def emit(word, name, operands, original=False):
            nonlocal count, supported, actual, hints
            fields = expected(name, operands)
            f.write(struct.pack('<I8B', word, *fields))
            count += 1; supported += fields[0]
            if original and fields[0]:
                actual += 1; hints += fields[6]
        for word in sorted(words):
            ins = next(iter(md.disasm_lite(word.to_bytes(4, 'little'), 0)), None)
            emit(word, ins[2] if ins else '', ins[3] if ins else '')
        md.skipdata = True
        for report in reports:
            raw = (ROOT / report['file']).read_bytes()
            for section in report['code_sections']:
                data = raw[section['offset']:section['offset'] + section['size']]
                for address, length, name, operands in md.disasm_lite(data, 0):
                    if length != 4: raise ValueError('Unexpected instruction width')
                    emit(int.from_bytes(data[address:address+4], 'little'), name, operands, True)
    meta = {'records': count, 'supported_records': supported, 'actual_supported_instructions': actual,
            'actual_hint_instructions': hints, 'oracle': 'Capstone mnemonic/operand decode',
            'limits': '31 legacy forms; newer undecoded instructions remain unsupported.'}
    out.with_suffix('.json').write_text(json.dumps(meta, indent=2))
    print(json.dumps(meta))
if __name__ == '__main__': main()
