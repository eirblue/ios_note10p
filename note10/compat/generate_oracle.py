"""Generate an independent Capstone oracle, including actual IPSW code sections."""
import json
from pathlib import Path
import random
import struct
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'host-tools/python-packages'))
from capstone import Cs, CS_ARCH_ARM64, CS_MODE_LITTLE_ENDIAN
from active_inputs import userland_reports

OPS = {
    'braa': (0, 0, False), 'brab': (0, 1, False),
    'blraa': (1, 0, False), 'blrab': (1, 1, False),
    'braaz': (0, 0, True), 'brabz': (0, 1, True),
    'blraaz': (1, 0, True), 'blrabz': (1, 1, True),
    'retaa': (2, 0, False), 'retab': (2, 1, False),
}


def expected(mnemonic, operands):
    if mnemonic not in OPS:
        return (0, 0, 0, 0, 0, 0)
    kind, key, zero = OPS[mnemonic]
    if kind == 2:
        return (1, kind, key, 30, 31, 1)
    regs = [x.strip() for x in operands.split(',')]
    number = lambda name: 31 if name in ('sp', 'xzr') else int(name[1:])
    rn = number(regs[0])
    rm = 31 if zero else number(regs[1])
    mod = 2 if zero else (1 if regs[1] == 'sp' else 0)
    return (1, kind, key, rn, rm, mod)


def main():
    reports = userland_reports()
    out = ROOT / 'note10/private/auth-branch-oracle.bin'
    md = Cs(CS_ARCH_ARM64, CS_MODE_LITTLE_ENDIAN)
    words = set()
    for base in (0xd71f0800, 0xd71f0c00, 0xd73f0800, 0xd73f0c00):
        words.update(base | rn << 5 | rm for rn in range(32) for rm in range(32))
    for base in (0xd61f081f, 0xd61f0c1f, 0xd63f081f, 0xd63f0c1f):
        words.update(base | rn << 5 for rn in range(32))
    words.update((0xd65f0bff, 0xd65f0fff))
    for word in tuple(sorted(words))[::8]:
        words.update(word ^ (1 << bit) for bit in range(32))
    rng = random.Random(976)
    words.update(rng.getrandbits(32) for _ in range(20000))
    count = supported = actual = 0
    with out.open('wb') as stream:
        def emit(word, mnemonic, operands):
            nonlocal count, supported
            fields = expected(mnemonic, operands)
            stream.write(struct.pack('<I6B2x', word, *fields))
            count += 1
            supported += fields[0]
        for word in sorted(words):
            ins = next(iter(md.disasm_lite(word.to_bytes(4, 'little'), 0)), None)
            emit(word, ins[2] if ins else '', ins[3] if ins else '')
        # Instruction-marked sections, independently decoded from original bytes.
        for report in reports:
            raw = (ROOT / report['file']).read_bytes()
            md.skipdata = True
            for section in report['code_sections']:
                offset, size = section['offset'], section['size']
                code = raw[offset:offset + size]
                for address, length, mnemonic, operands in md.disasm_lite(code, 0):
                    if length != 4:
                        raise ValueError('Unexpected AArch64 instruction width')
                    emit(int.from_bytes(code[address:address + 4], 'little'), mnemonic, operands)
                    actual += 1
    metadata = {'oracle': 'Capstone', 'records': count, 'supported_records': supported,
                'actual_ipsw_instruction_words': actual, 'record_size': 12,
                'random_seed': 976, 'limits': 'Only ten authentication branch/return forms; no PAC implementation.'}
    out.with_suffix('.json').write_text(json.dumps(metadata, indent=2))
    print(json.dumps(metadata))


if __name__ == '__main__':
    main()
