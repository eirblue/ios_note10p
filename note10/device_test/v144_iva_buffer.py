"""Exact sequential142 ->144 native ION-provider overlay. No runtime entry."""
from hashlib import sha256

CTRL = 'drivers/vision/iva/iva_ctrl.c'
MEM = 'drivers/vision/iva/iva_mem.c'
HEADER = 'drivers/vision/iva/iva_mem.h'
HELPER = 'drivers/vision/iva/v144_iva_buffer.h'
NATIVE_SHA256 = {'drivers/vision/iva/iva_mem.c': 'f1085466746c50e7fbb7d78f7d4e05c9c37d6ae10597cb22fe1f86648d657507', 'drivers/vision/iva/iva_mem.h': 'c9bf7fef55b12e4bf84ccf931941e71e8a45fc2afc6cfbfa191e3ee2927e7b83', 'drivers/vision/iva/iva_ctrl.c': 'b13aa35e80c528f2a1d87a4716166a0553cd6bc506974a710bc6ed8678767321'}
HELPER_SHA256 = 'ca9bc9f95a4828b6c12895c3e15d4d0818a92b01699084842e3efb60b7f62d30'


def once(raw, old, new):
    if raw.count(old) != 1:
        raise ValueError('native anchor missing or ambiguous')
    return raw.replace(old, new, 1)


def patch_native(inputs, helper):
    """Saved accepted142 ctrl.c, stock mem.c/h;143 leaves ctrl.c alone."""
    if set(inputs) != set(NATIVE_SHA256):
        raise ValueError('exact sequential overlay input set required')
    for name, expected in NATIVE_SHA256.items():
        if sha256(inputs[name]).hexdigest() != expected:
            raise ValueError('native input pin mismatch: ' + name)
    if sha256(helper).hexdigest() != HELPER_SHA256:
        raise ValueError('new helper pin mismatch')
    mem = inputs[MEM]
    mem = once(mem, b'int import_fd)\n{',
               b'int import_fd, struct n144_buffer_call *call)\n{')
    import_head = (b'static struct iva_mem_map *iva_mem_import_ion_buf(struct iva_proc *proc,\n'
                   b'\t\tint import_fd, struct n144_buffer_call *call)\n{\n'
                   b'\tstruct iva_dev_data\t*iva = proc->iva_data;\n'
                   b'\tstruct device\t\t*dev = iva->dev;\n'
                   b'\tstruct iva_mem_map\t*iva_map_node;\n'
                   b'\tstruct dma_buf\t\t*dmabuf;\n')
    mem = once(mem, import_head, import_head +
               b'\n\tif (!n144_buffer_call_ready(call))\n\t\treturn NULL;\n')
    mem = once(mem, b'\tiva_map_node->shared_fd\t\t= import_fd;',
               b'\t/* Validate exact owned get before storage/attach/priv casts. */\n'
               b'\tif (dmabuf->ops != &ion_dma_buf_ops) {\n'
               b'\t\tcall->foreign_put = dmabuf;\n'
               b'\t\tcall->refused_history = true;\n'
               b'\t\tgoto err_buf_get;\n\t}\n\n'
               b'\tiva_map_node->shared_fd\t\t= import_fd;')
    mem = once(mem, b'static int iva_mem_get_ion_iova_param(struct iva_proc *proc,\n\t\t\tstruct iva_ion_param *ion_param)',
               b'static int iva_mem_get_ion_iova_param(struct iva_proc *proc,\n'
               b'\t\t\tstruct iva_ion_param *ion_param,\n'
               b'\t\t\tstruct n144_buffer_call *call)')
    mem = once(mem, b'iva_mem_import_ion_buf(proc, ion_param->shared_fd)',
               b'iva_mem_import_ion_buf(proc, ion_param->shared_fd, call)')
    mem = once(mem, b'long iva_mem_ioctl(struct iva_proc *proc, unsigned int cmd, void __user *p)',
               b'long iva_mem_ioctl(struct iva_proc *proc, unsigned int cmd, void __user *p,\n'
               b'\t\tstruct n144_buffer_call *call)')
    mem = once(mem, b'iva_mem_get_ion_iova_param(proc, &iva_param)',
               b'iva_mem_get_ion_iova_param(proc, &iva_param, call)')
    hdr = once(inputs[HEADER], b'#include "iva_ctrl_ioctl.h"',
               b'#include "iva_ctrl_ioctl.h"\n#include "v144_iva_buffer.h"')
    hdr = once(hdr, b'unsigned int cmd, void __user *p);',
               b'unsigned int cmd, void __user *p,\n\t\t\tstruct n144_buffer_call *call);')
    ctrl = inputs[CTRL]
    start = ctrl.index(b'static long iva_ctrl_ioctl(')
    end = ctrl.index(b'static int iva_ctrl_mmap(', start)
    original = ctrl[start:end]
    inner = once(original, b'static long iva_ctrl_ioctl(struct file *filp, unsigned int cmd, unsigned long arg)',
                 b'static long n144_iva_ctrl_ioctl_body(struct iva_proc *proc, unsigned int cmd,\n'
                 b'\t\tunsigned long arg, struct n144_buffer_call *call)')
    inner = once(inner, b'\tstruct iva_proc\t\t*proc;\n', b'')
    inner = once(inner, b'\tproc\t= (struct iva_proc *) filp->private_data;\n', b'')
    inner = once(inner, b'iva_mem_ioctl(proc, cmd, p)', b'iva_mem_ioctl(proc, cmd, p, call)')
    wrapper = b'''
static long iva_ctrl_ioctl(struct file *filp, unsigned int cmd, unsigned long arg)
{
\tstruct n144_buffer_call call;
\tstruct iva_proc *proc = (struct iva_proc *)filp->private_data;
\tlong result;

\tn144_buffer_call_init(&call);
\tresult = n144_iva_ctrl_ioctl_body(proc, cmd, arg, &call);
\tn144_buffer_call_finish(&call);
\treturn result;
}

'''
    ctrl = ctrl[:start] + inner + wrapper + ctrl[end:]
    return {CTRL: ctrl, MEM: mem, HEADER: hdr, HELPER: helper}
