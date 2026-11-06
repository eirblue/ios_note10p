"""Exact145 ->146 native get_user errno guards; bound to saved actual ROOT145 R2 PASS."""
from hashlib import sha256

CTRL = 'drivers/vision/iva/iva_ctrl.c'
CTRL_SHA256 = '378f40b4deec9dd129f5ce9aebd299bf4ed15159da8327c82e219ab8ce30d6c7'


def patch_native(ctrl):
    if not CTRL_SHA256 or sha256(ctrl).hexdigest() != CTRL_SHA256:
        raise ValueError('actual successful145 exact composed ctrl input required')
    for old, new in (
        (b'\tget_user(en_hwa, en_hwa_usr);',
         b'\tif (get_user(en_hwa, en_hwa_usr))\n\t\treturn -EFAULT;'),
        (b'\tget_user(usr_req, usr_clk_rate);',
         b'\tif (get_user(usr_req, usr_clk_rate))\n\t\treturn -EFAULT;'),
    ):
        if ctrl.count(old) != 1:
            raise ValueError('missing or ambiguous exact native get_user anchor')
        ctrl = ctrl.replace(old, new, 1)
    return {CTRL: ctrl}
