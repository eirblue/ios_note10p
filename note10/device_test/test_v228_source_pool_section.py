"""One new228 section-transform fixture; ROOT runs it once, without old subgroup replay."""
import hashlib
from pathlib import Path
import v228_source_pool_section as section_fix
HERE=Path(__file__).resolve().parent


def run():
    raw=(HERE/'v226_source_stream_kernel.c').read_bytes();changed=section_fix.prepare(raw)
    if hashlib.sha256(changed).hexdigest()!=section_fix.POST_SHA or changed!=raw.replace(section_fix.OLD,section_fix.NEW,1)or changed.count(section_fix.NEW)!=1 or section_fix.OLD in changed:
        raise AssertionError('one exact fresh-overlay builtin section attribute replacement required')
    try:section_fix.prepare(raw+b'\n')
    except ValueError:pass
    else:raise AssertionError('mutated section-transform preimage must be rejected')
    return dict(groups=1,variants=2,assertions=2)
