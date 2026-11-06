"""PC-only IVA firmware-argument repair over two exact native source inputs.

This module only transforms supplied bytes.  It grants no DMA-owner witness or
physical execution authority and does not invoke retained render/build helpers.
"""
from hashlib import sha256

CTRL = 'drivers/vision/iva/iva_ctrl.c'
MCU = 'drivers/vision/iva/iva_mcu.c'
NATIVE_SHA256 = {
    CTRL: 'e7aa8f4369c4ae2c6be91cb4f53edb3b9f1cbf66475bd2f014d123a2f87c34c8',
    MCU: '0bf1bc903dcf14a3b5c413c43700bf337d559da3d9e93e6dc59712743b74ae6c',
}

_USER_OLD = b'''\tif (name_len <= 0) {
\t\tdev_err(dev, "%s() unexpected name_len(%d)\\n",
\t\t\t\t__func__, name_len);
\t\treturn name_len;
\t}

\t/* already boot_ref > 0 */'''
_USER_NEW = b'''\tif (name_len <= 0) {
\t\tdev_err(dev, "%s() unexpected name_len(%d)\\n",
\t\t\t\t__func__, name_len);
\t\treturn name_len < 0 ? name_len : -EINVAL;
\t}
\t/* Validate before native reference/QoS/firmware ownership changes. */
\tif (strncmp(mcu_file, IVA_MCU_FILE_PATH, sizeof(IVA_MCU_FILE_PATH)))
\t\treturn -EINVAL;

\t/* already boot_ref > 0 */'''
_NATIVE_OLD = b'''\tif (strncmp(mcu_file, IVA_MCU_FILE_PATH, sizeof(IVA_MCU_FILE_PATH))) {
\t\tdev_err(dev, "%s() mcu_file(%s) is wrong file path.\\n",
\t\t\t\t__func__, mcu_file);
\t\treturn 0;
\t}

'''
_NATIVE_ANCHOR = b'\tdev_dbg(dev, "%s() try to boot with %s", __func__, mcu_file);'
_NATIVE_NEW = b'''\t/* Invalid arguments never become success through an already-booted path. */
\tif (!mcu_file || strncmp(mcu_file, IVA_MCU_FILE_PATH,
\t\t\t\t sizeof(IVA_MCU_FILE_PATH)))
\t\treturn -EINVAL;

'''


def _once(raw, before, after):
    if raw.count(before) != 1:
        raise ValueError('exact selected native IVA boundary required')
    return raw.replace(before, after, 1)


def patch_native(stock):
    """Return only changed ctrl/MCU native bytes, refusing all other inputs."""
    if type(stock) is not dict or set(stock) != set(NATIVE_SHA256):
        raise ValueError('exact two native IVA source roles required')
    for name, pin in NATIVE_SHA256.items():
        raw = stock[name]
        if type(raw) is not bytes or sha256(raw).hexdigest() != pin:
            raise ValueError('exact pinned native IVA input bytes required: ' + name)
    ctrl = _once(stock[CTRL], _USER_OLD, _USER_NEW)
    mcu = _once(stock[MCU], _NATIVE_OLD, b'')
    mcu = _once(mcu, _NATIVE_ANCHOR, _NATIVE_NEW + _NATIVE_ANCHOR)
    return {CTRL: ctrl, MCU: mcu}
