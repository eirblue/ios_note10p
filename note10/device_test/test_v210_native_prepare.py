"""Only two new packaging metadata variants, grouped with the new C core fixture."""
import hashlib
import struct


def run(profile):
    assertions=0
    def check(ok):
        nonlocal assertions
        assertions+=1
        if not ok:raise AssertionError('new packaging metadata assertion')
    elf=bytearray(128);elf[:6]=b'\x7fELF\x02\x01';elf[18:20]=b'\xb7\0'
    elf.extend(b'N10MININIT2:N210PREP')
    generic,prefix=profile.generic(bytes(elf))
    check(len(generic)-prefix==4096 and not any(generic[prefix:]))
    check(all(value is False or type(value)is int and value==0 for value in profile.FALSE_CLAIMS.values()))
    descriptor=struct.pack('<8sII10Q32s32s32s32s32s',b'N209PAY1',1,256,0xffff000001004000,49152,0,0,16,32768,16384,16384,0,256,
                           *[bytes([number])*32 for number in range(1,6)])
    member,binding=profile.private_member(descriptor,'1'*32,'2'*32)
    check(len(member)<=4096 and len(binding)==128 and binding[80:112]==hashlib.sha256(descriptor).digest())
    image=bytearray(4608);image[128:161]=profile.p.CYCLE_MARKER+b'\0'
    denied=False
    try:profile.insert(bytes(image),dict(slot_offset=512,slot_bytes=4096,cycle_offset=128),b'070701'+bytes(4091),'2'*32)
    except ValueError:denied=True
    check(denied)
    return dict(Python_variants=2,Python_assertions=assertions)
