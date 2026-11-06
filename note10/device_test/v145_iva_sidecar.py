"""Exact144 ->145 native file-pointer sidecar overlay; bound to saved actual144 R2 PASS."""
from hashlib import sha256
import re

CTRL = 'drivers/vision/iva/iva_ctrl.c'
HELPER = 'drivers/vision/iva/v145_iva_sidecar.inc'
CTRL_SHA256 = 'f7f27fd884e3233bd85a9e23ebcbdb0b677a7bd1baad18cda8c5808e26de2f1b'
HELPER_SHA256 = '880e3a8f3a2c2e34adbc71faf3def748154db7eabf0d98270cec5c9be74f7377'
TOKENS = re.compile(rb'/\*.*?\*/|//[^\n]*|"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'|[{}]', re.S)


def once(raw, old, new):
    if raw.count(old) != 1:
        raise ValueError('missing or ambiguous exact native anchor')
    return raw.replace(old, new, 1)


def function_span(raw, name):
    matches = list(re.finditer(rb'^static\s+(?:long|int)\s+' + name.encode() + rb'\s*\(', raw, re.M))
    if len(matches) != 1:
        raise ValueError('exact native definition required: ' + name)
    start = matches[0].start()
    depth = 0
    for token in TOKENS.finditer(raw, raw.index(b'{', matches[0].end())):
        if token.group() == b'{':
            depth += 1
        elif token.group() == b'}':
            depth -= 1
            if depth == 0:
                return start, token.end()
    raise ValueError('unbalanced native body')


def patch_native(ctrl, helper):
    if not CTRL_SHA256 or not HELPER_SHA256:
        raise ValueError('await exact actual ROOT144 PASS before freeze/execution')
    if sha256(ctrl).hexdigest() != CTRL_SHA256 or sha256(helper).hexdigest() != HELPER_SHA256:
        raise ValueError('exact sequential native/helper pin mismatch')
    start, end = function_span(ctrl, 'iva_ctrl_ioctl')
    ctrl = ctrl[:start] + ctrl[end:]
    start, end = function_span(ctrl, 'iva_ctrl_mmap')
    body = ctrl[start:end]
    boundary = body.index(b'#ifdef ENABLE_MMAP_US')
    body = (b'static int n145_native_mmap(struct iva_proc *proc, struct vm_area_struct *vma)\n{\n'
            b'\tstruct iva_dev_data\t*iva = proc->iva_data;\n'
            b'\tstruct device\t\t*dev = iva->dev;\n\n' + body[boundary:])
    ctrl = ctrl[:start] + body + ctrl[end:]
    start, end = function_span(ctrl, 'iva_ctrl_open')
    body = ctrl[start:end]
    boundary = body.index(b'\tmutex_lock(&iva->proc_mutex);')
    body = (b'static int n145_native_open(struct iva_dev_data *iva, struct iva_proc **result)\n{\n'
            b'\tstruct device *dev = iva->dev;\n'
            b'\tstruct iva_proc *proc;\n\n' + body[boundary:])
    body = once(body, b'/* update file->private to hold struct iva_proc */',
                b'/* Return native proc to the stable file-context wrapper. */')
    body = once(body, b'filp->private_data = (void *) proc;', b'*result = proc;')
    ctrl = ctrl[:start] + body + ctrl[end:]
    start, end = function_span(ctrl, 'iva_ctrl_release')
    body = ctrl[start:end]
    body = once(body, b'static int iva_ctrl_release(struct inode *inode, struct file *filp)',
                b'static int n145_native_release(struct iva_proc *proc)')
    body = once(body, b'\tstruct iva_proc\t\t*proc;\n', b'')
    body = once(body, b'\tproc\t= (struct iva_proc *) filp->private_data;\n', b'')
    body = once(body, b'\tput_task_struct(proc->tsk);\n',
                b'\t/* Exact owned task put deferred by wrapper until device unlock. */\n')
    ctrl = ctrl[:start] + body + ctrl[end:]
    ctrl = once(ctrl, b'static const struct file_operations iva_ctl_fops = {',
                b'#include "v145_iva_sidecar.inc"\n\n'
                b'static const struct file_operations iva_ctl_fops = {')
    start, end = function_span(ctrl, 'iva_ctl_probe')
    body = ctrl[start:end]
    body = once(body, b'static int iva_ctl_probe(', b'static int n145_native_probe(')
    body = once(body, b'\tint\tret = 0;\n',
                b'\tint\tret = 0;\n\tbool misc_registered = false;\n')
    registration = b'''\tret = misc_register(&iva->misc);
\tif (ret) {
\t\tdev_err(dev, "%s() failed to register misc device\\n",
\t\t\t\t__func__);
\t\tgoto err_misc_reg;
\t}
'''
    body = once(body, registration, registration + b'\tmisc_registered = true;\n')
    body = once(body, b'err_misc_reg:\n\tiva_mcu_remove(iva);',
                b'err_misc_reg:\n\tif (misc_registered)\n\t\tmisc_deregister(&iva->misc);\n'
                b'\tiva_mcu_remove(iva);')
    ctrl = ctrl[:start] + body + ctrl[end:]
    ctrl = once(ctrl, b'static int iva_ctl_remove(struct platform_device *pdev)',
                b'static int n145_native_remove(struct platform_device *pdev)')
    return {CTRL: ctrl, HELPER: helper}
