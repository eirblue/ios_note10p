"""Release the existing mailbox writer lock on duplicate registration."""
from hashlib import sha256

MBOX = 'drivers/vision/iva/iva_mbox.c'
MBOX_SHA256 = '6c87f0b62bc762613279bb31b2b4151ba2512a8d726a5574aacc641a73ea1b24'
OLD_DUPLICATE = b'''\t\tif ((*cl) == cb)
\t\t\treturn 0;'''
NEW_DUPLICATE = b'''\t\tif ((*cl) == cb)
\t\t\tgoto out;'''
OLD_UNLOCK = b'''\trcu_assign_pointer(*cl, cb);
\tspin_unlock_irqrestore(&ch->lock, flags);'''
NEW_UNLOCK = b'''\trcu_assign_pointer(*cl, cb);
out:
\tspin_unlock_irqrestore(&ch->lock, flags);'''


def patch_native(mbox):
    if sha256(mbox).hexdigest() != MBOX_SHA256:
        raise ValueError('exact pinned native mailbox input required')
    if mbox.count(OLD_DUPLICATE) != 1 or mbox.count(OLD_UNLOCK) != 1:
        raise ValueError('exact duplicate and common-unlock anchors required')
    return {MBOX: mbox.replace(OLD_DUPLICATE, NEW_DUPLICATE, 1).replace(OLD_UNLOCK, NEW_UNLOCK, 1)}
