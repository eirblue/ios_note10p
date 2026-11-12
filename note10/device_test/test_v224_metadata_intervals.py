"""New metadata interval orders, touching endpoints, overlaps and bounds only."""
import struct
import v224_native_prepare as producer


def run():
    assertions=0
    size=producer.SLOT_BYTES;length=size+512;cycle='2'*32
    descriptor=b'N209PAY1'+struct.pack('<II',1,256)+bytes(240)
    def check(ok):
        nonlocal assertions
        assertions+=1
        if not ok:raise AssertionError('metadata interval assertion failed')
    def inputs(start,marker):
        image=bytearray(length)
        if 0<=marker<=length-33:image[marker:marker+33]=producer.p.CYCLE_MARKER+b'\0'
        return bytes(image),dict(build_evidence_id='1'*32,slot_offset=start,slot_bytes=size,cycle_offset=marker)
    def valid(start,marker):
        image,build=inputs(start,marker);changed,binding,row=producer.insert_metadata(image,build,descriptor,cycle)
        first,second=sorted(((start,start+size),(marker,marker+32)))
        unchanged=(changed[:first[0]]==image[:first[0]] and changed[first[1]:second[0]]==image[first[1]:second[0]] and changed[second[1]:]==image[second[1]:])
        member=changed[start:start+row['metadata_newc_bytes']]
        return (len(changed)==len(image) and unchanged and changed[marker:marker+33]==cycle.encode()+b'\0' and
            row['descriptor_bytes']==256 and row['binding_bytes']==len(binding)==128 and row['native_source_allocation_bytes']==0 and
            0<row['metadata_newc_bytes']<=4096 and descriptor in member and binding in member and
            not any(changed[start+row['metadata_newc_bytes']:start+size]))
    def denied(start,marker):
        image,build=inputs(start,marker)
        try:producer.insert_metadata(image,build,descriptor,cycle)
        except ValueError:return True
        return False
    check(valid(256,64))
    check(valid(256,size+384))
    check(valid(97,64))
    check(valid(256,size+256))
    check(denied(256,224))
    check(denied(256,size+255))
    check(denied(256,32))
    check(denied(256,length-32))
    check(denied(32,size+384))
    check(denied(513,64))
    return dict(groups=1,variants=10,assertions=assertions)
