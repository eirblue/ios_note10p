"""New6MiBmetadata compositor boundary only; no prior core/SHA suites."""
import struct
import v221_native_prepare as producer


def run():
    count=0
    def check(ok):
        nonlocal count
        count+=1
        if not ok:raise AssertionError('new221metadata assertion failed')
    def denied(image,build,descriptor):
        try:producer.insert_metadata(image,build,descriptor,'2'*32)
        except ValueError:return True
        return False
    descriptor=b'N209PAY1'+struct.pack('<II',1,256)+bytes(240)
    image=bytearray(512+producer.SLOT_BYTES);image[64:97]=producer.p.CYCLE_MARKER+b'\0';image=bytes(image)
    build=dict(build_evidence_id='1'*32,slot_offset=512,slot_bytes=producer.SLOT_BYTES,cycle_offset=64)
    changed,binding,row=producer.insert_metadata(image,build,descriptor,'2'*32)
    check(changed[:64]==image[:64] and changed[96:512]==image[96:512] and changed[64:96]==b'2'*32)
    check(row['descriptor_bytes']==256 and row['binding_bytes']==len(binding)==128 and row['native_source_allocation_bytes']==0 and row['metadata_newc_bytes']<=4096)
    check(descriptor in changed[512:512+row['metadata_newc_bytes']] and binding in changed[512:512+row['metadata_newc_bytes']] and not any(changed[512+row['metadata_newc_bytes']:]))
    check(denied(image,build,b'\x1f\x8b'+bytes(254)))
    check(denied(image,dict(build,slot_bytes=4096),descriptor))
    dirty=bytearray(image);dirty[512]=1;check(denied(bytes(dirty),build,descriptor))
    return dict(groups=2,variants=4,assertions=count)
