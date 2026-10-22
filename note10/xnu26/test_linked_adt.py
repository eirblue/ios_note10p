"""Run the actual linked SecureDT functions against synthetic generated ADT.

Function-level Unicorn test only: no startup, hardware or driver handoff.
No implementation of strcmp, DT traversal or success returns is substituted.
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct
from boot_adt import encode
from test_boot_adt import fixture
from audit_kernel_instructions import image_layout
from verify_experimental_artifact import verify

ROOT = Path(__file__).resolve().parents[2]


def run(directory):
    from unicorn import Uc, UC_ARCH_ARM64, UC_MODE_ARM, UC_HOOK_CODE
    from unicorn import arm64_const as regs
    checked = verify(directory); raw = (directory / 'note10-experimental.macho').read_bytes()
    symbols = {name:address for address,name in image_layout(raw)[2]}
    engine = Uc(UC_ARCH_ARM64, UC_MODE_ARM)
    regions = [s for s in checked['segments'] if s['virtual_size']]
    start = min(s['virtual_address'] for s in regions)
    end = max(s['virtual_address'] + s['virtual_size'] for s in regions)
    # RWX is an emulator fixture convenience, not a proposed MMU policy.
    engine.mem_map(start, (end - start + 0xfff) & ~0xfff)
    for segment in regions:
        if segment['file_size']:
            engine.mem_write(segment['virtual_address'], raw[segment['file_offset']:segment['file_offset'] + segment['file_size']])
    data = 0x50000000; stack = 0x60000000; sentinel = 0x40000000
    for base in (data, stack, sentinel): engine.mem_map(base, 0x10000)
    adt = encode(fixture()); engine.mem_write(data, adt)
    panic_sites = {value for name,value in symbols.items() if name in ('_panic', '_panic_with_options', '___stack_chk_fail')}
    instructions = 0
    def step(uc, address, size, _):
        nonlocal instructions
        instructions += 1
        if address in panic_sites: raise ValueError('Real kernel DT parser panicked')
    engine.hook_add(UC_HOOK_CODE, step)
    calls = []
    def call(name, *values):
        for index in range(8): engine.reg_write(getattr(regs, 'UC_ARM64_REG_X' + str(index)), values[index] if index < len(values) else 0)
        engine.reg_write(regs.UC_ARM64_REG_SP, stack + 0xf000)
        engine.reg_write(regs.UC_ARM64_REG_LR, sentinel)
        before = instructions
        engine.emu_start(symbols[name], sentinel, count=100000)
        if engine.reg_read(regs.UC_ARM64_REG_PC) != sentinel: raise ValueError('DT function failed to return')
        result = engine.reg_read(regs.UC_ARM64_REG_X0) & 0xffffffff
        calls.append({'function':name, 'instructions':instructions-before, 'result_u32':result})
        return result
    call('_SecureDTInit', data, len(adt))
    path = data + 0x2000; found = data + 0x3000
    engine.mem_write(path, b'/chosen/note10-platform\0')
    if call('_SecureDTLookupEntry', 0, path, found) != 1: raise ValueError('Generated ADT node not found')
    entry = struct.unpack('<Q', engine.mem_read(found, 8))[0]
    if not data <= entry < data + len(adt): raise ValueError('DT parser returned pointer outside ADT')
    key = data + 0x2100; pointer = found + 8; length = found + 16
    for name, expected in (('version', struct.pack('<I',1)), ('test-marker', b'PC-only\0')):
        engine.mem_write(key, name.encode() + b'\0')
        if call('_SecureDTGetProperty', entry, key, pointer, length) != 1: raise ValueError('Generated property not found')
        address = struct.unpack('<Q', engine.mem_read(pointer,8))[0]
        size = struct.unpack('<I', engine.mem_read(length,4))[0]
        if size != len(expected) or not data <= address <= data + len(adt) - size:
            raise ValueError('DT parser returned bad property extent')
        if bytes(engine.mem_read(address, size)) != expected: raise ValueError('DT parser property bytes differ')
    # A test tree must not fabricate ownership of the recovery's GIC.
    engine.mem_write(key, b'gic-handoff\0')
    if call('_SecureDTGetProperty', entry, key, pointer, length) != 0xffffffff:
        raise ValueError('Unexpected fabricated GIC handoff')
    engine.mem_write(path, b'/chosen/missing-node\0')
    if call('_SecureDTLookupEntry', 0, path, found) != 0xffffffff:
        raise ValueError('Missing-node query unexpectedly succeeded')
    rejected = []
    for case in ('truncated-region', 'overflowing-property'):
        bad = bytearray(adt)
        if case == 'overflowing-property': struct.pack_into('<I',bad,40,0x7fffffff)
        engine.mem_write(data,bytes(bad))
        call('_SecureDTInit',data,1 if case == 'truncated-region' else len(bad))
        engine.mem_write(key,b'name\0')
        try: call('_SecureDTGetProperty',data,key,pointer,length)
        except ValueError as error:
            if str(error) != 'Real kernel DT parser panicked': raise
            rejected.append(case)
        else: raise ValueError('Real parser failed to reject invalid DT bounds')
    report = {'passed':True, 'calls':calls, 'instructions':instructions,
              'real_parser_bounds_panics_observed':rejected,
              'adt_bytes':len(adt), 'adt_sha256':hashlib.sha256(adt).hexdigest(),
              'kernel_sha256':hashlib.sha256(raw).hexdigest(),
              'scope':'Actual linked SecureDTInit/LookupEntry/GetProperty functions; synthetic RAM and test ADT',
              'hardware_verified':False, 'deployment_ready':False, 'device_operations':[]}
    output = ROOT / 'note10/private/boot-contract'; output.mkdir(exist_ok=True)
    (output / 'adt-parser-result.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps({key:report[key] for key in ('passed','instructions','adt_bytes','hardware_verified')}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('directory',type=Path)
    run(parser.parse_args().directory)
