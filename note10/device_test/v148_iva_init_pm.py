"""Exact147 ->148 failed get_sync usage accounting, without idle callbacks."""
from hashlib import sha256

CTRL = 'drivers/vision/iva/iva_ctrl.c'
CTRL_SHA256 = 'e49a3d744d35fa9f79211ed83e74123e0abdd077f5cd06a8c54801799dc45125'
OLD = b'''\tif (ret < 0) {
\t\tdev_err(dev, "%s() fail to enable iva clk/pwr. ret(%d)\\n",'''
NEW = b'''\tif (ret < 0) {
#ifdef CONFIG_PM
\t\tpm_runtime_put_noidle(dev);
#endif
\t\tdev_err(dev, "%s() fail to enable iva clk/pwr. ret(%d)\\n",'''


def patch_native(ctrl):
    if sha256(ctrl).hexdigest() != CTRL_SHA256:
        raise ValueError('actual147 exact composed native ctrl required')
    if ctrl.count(OLD) != 1:
        raise ValueError('exact first-global init failure anchor required')
    return {CTRL: ctrl.replace(OLD, NEW, 1)}
