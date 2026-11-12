"""227 host-copy-only ABI adaptation for pinned Linux rawinflate; target source is untouched."""
import hashlib
INPUT_SHA='c0e6fa1dc4087e19160312bff51f56bff32917eb6e10ed9a6fb7eb518a1bee8a'
POST_SHA='2de33eee5109dbb985f479654429d72674a4824e19078bbd0242f3b6c56858a8'
PREFIX=b'#include <stdint.h>\n_Static_assert(sizeof(uintptr_t)==sizeof(void *),"host pointer-width alignment");\n'
OLD=b'(long)(out - 1 + OFF)'
NEW=b'(uintptr_t)(out - 1 + OFF)'


def adapt(raw):
    if type(raw)is not bytes or hashlib.sha256(raw).hexdigest()!=INPUT_SHA or raw.count(OLD)!=1:
        raise ValueError('exact stock inffast host-copy preimage required')
    changed=PREFIX+raw.replace(OLD,NEW,1)
    if hashlib.sha256(changed).hexdigest()!=POST_SHA:raise ValueError('exact pointer-width host-copy postimage required')
    return changed


def regression(raw):
    changed=adapt(raw)
    if changed!=PREFIX+raw.replace(OLD,NEW,1)or OLD in changed or changed.count(NEW)!=1:
        raise AssertionError('one host-only pointer-width alignment edit required')
    try:adapt(raw+b'\n')
    except ValueError:pass
    else:raise AssertionError('mutated host-copy preimage must be rejected')
    return changed,dict(groups=1,variants=1,assertions=2)
