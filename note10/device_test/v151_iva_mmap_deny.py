"""Deny future diagnostic IVA raw-SFR mappings in the exact composed149 ctrl."""
from hashlib import sha256

from v145_iva_sidecar import function_span

CTRL = 'drivers/vision/iva/iva_ctrl.c'
CTRL_SHA256 = '8fa6b9138fcfc5113169d818f3eddf6361229daf02c1abf3eb61c00fb53d1ba2'
SIGNATURE = b'static int n145_native_mmap(struct iva_proc *proc, struct vm_area_struct *vma)\n'
DENIED = SIGNATURE + b'{\n\t(void)proc;\n\t(void)vma;\n\treturn -EOPNOTSUPP;\n}'


def patch_native(ctrl):
    if sha256(ctrl).hexdigest() != CTRL_SHA256:
        raise ValueError('actual149 exact composed native ctrl required')
    start, end = function_span(ctrl, 'n145_native_mmap')
    if not ctrl[start:end].startswith(SIGNATURE + b'{\n'):
        raise ValueError('exact native proc/vma mmap signature required')
    return {CTRL: ctrl[:start] + DENIED + ctrl[end:]}
