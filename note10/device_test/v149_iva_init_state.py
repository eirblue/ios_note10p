"""Roll back the native init bit when the existing clock-enable call fails."""
from hashlib import sha256

CTRL = 'drivers/vision/iva/iva_ctrl.c'
CTRL_SHA256 = 'c557c610a266d545c1cb38519612933208ac02d09f12e4c10b0a9d6b29634e82'
OLD = b'''\t\t\tdev_err(dev, "fail to enable iva_clk(%d)\\n", ret);
\t\t\treturn ret;'''
NEW = b'''\t\t\tdev_err(dev, "fail to enable iva_clk(%d)\\n", ret);
\t\t\tclear_bit(IVA_ST_INIT_DONE, &iva->state);
\t\t\treturn ret;'''


def patch_native(ctrl):
    if sha256(ctrl).hexdigest() != CTRL_SHA256:
        raise ValueError('actual148 exact composed native ctrl required')
    if ctrl.count(OLD) != 1:
        raise ValueError('exact native clock-enable failure anchor required')
    return {CTRL: ctrl.replace(OLD, NEW, 1)}
