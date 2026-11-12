"""228 exact section-attribute fix in a fresh kernel overlay only."""
import hashlib
from pathlib import Path
import v227_native_prepare as retained
SOURCE_SHA='375a8f329d1411b8a42d471354ccf7a0a8d46b68c745db69041bf3d63474ed8d'
POST_SHA='c7f5e0153af2d46d7a85d39e8383f2040b8b694d49347de022ceac1d2fab1328'
OLD=b'__section(".bss.n226_source_pool")'
NEW=b'__attribute__((__section__(".bss.n226_source_pool")))'


def prepare(raw):
    if type(raw)is not bytes or hashlib.sha256(raw).hexdigest()!=SOURCE_SHA or raw.count(OLD)!=1:
        raise ValueError('exact226 source pool declaration preimage required')
    changed=raw.replace(OLD,NEW,1)
    if hashlib.sha256(changed).hexdigest()!=POST_SHA:raise ValueError('exact228 explicit section postimage required')
    return changed


def install(source,identity,buffers,parser_sha):
    result=retained.install(source,identity,buffers,parser_sha)
    relative='arch/arm64/mm/v226_source_stream_kernel.c';target=Path(source)/relative
    before=retained.p.ordinary(target);after=prepare(before);target.write_bytes(after)
    result['source_pool_section_transform']=dict(path=relative,before_sha256=hashlib.sha256(before).hexdigest(),after_sha256=hashlib.sha256(after).hexdigest(),
        replacements=1,section='.bss.n226_source_pool',pool_bytes=49152,alignment=4096,NOBITS_required=True,public_source_mutated=False,fresh_overlay_transformed=True)
    return result
