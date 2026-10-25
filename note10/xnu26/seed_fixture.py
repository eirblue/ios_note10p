"""PC-only deterministic seed fixture and exact canonical ADT property bounds."""
import struct
from boot_adt import decode,encode

# Public, predictable bytes. Never use as entropy in a hardware handoff.
PC_SEED=bytes(index%255+1 for index in range(256))


class SeedResultError(ValueError):
    def __init__(self,request,returned):
        self.report={'request':request,'returned':returned,'hardware_verified':False}
        super().__init__('Seed callback did not return declared byte count')


def property_spans(raw):
    root=decode(raw)
    if encode(root)!=raw:raise ValueError('Canonical producer ADT required for mutation bounds')
    spans={};cursor=0
    def visit(node,path):
        nonlocal cursor
        path=path+'/'+node.name;cursor+=8
        for key,value in [('name',node.name.encode()+b'\0'),*node.properties.items()]:
            cursor+=36;spans[(path,key)]=(cursor,len(value));cursor+=(len(value)+3)&~3
        for child in node.children:visit(child,path)
    visit(root,'')
    if cursor!=len(raw):raise ValueError('ADT extent accounting mismatch')
    return spans


def locate(uc,boot_args):
    pointer=struct.unpack_from('<Q',boot_args,96)[0]
    size=struct.unpack_from('<I',boot_args,104)[0]
    if not 0<size<=0x4000:raise ValueError('Seed fixture requires one-page ADT')
    raw=bytes(uc.mem_read(pointer,size))
    span=property_spans(raw).get(('/device-tree/chosen','random-seed'))
    if span is None:return None
    offset,length=span
    if not 0<length<=4096:raise ValueError('Unsupported seed property bounds')
    return {'address':pointer+offset,'length':length,'tree_address':pointer,'original_tree':raw,'offset':offset}


def inspect(uc,region,destination,request,returned):
    if region is None or request!=256 or returned!=256 or region['length']!=256:
        raise SeedResultError(request,returned)
    original=region['original_tree'];offset=region['offset']
    if bytes(uc.mem_read(destination,256))!=original[offset:offset+256]:
        raise ValueError('Actual seed destination differs from ADT input')
    expected=original[:offset]+bytes(256)+original[offset+256:]
    if bytes(uc.mem_read(region['tree_address'],len(original)))!=expected:
        raise ValueError('Seed was not erased exactly or unrelated ADT bytes changed')
    return {'bytes_copied':256,'adt_seed_erased':True,'other_adt_bytes_unchanged':True,
            'predictable_pc_fixture':True,'entropy_quality_verified':False,'hardware_seed_ready':False}
