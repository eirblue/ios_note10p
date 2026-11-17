"""New builtin-TWRP route, config and slot mapping; synthetic bytes only."""
import struct
import v296_twrp_prepare as producer


def predicate():
    seam=b'n154_require_return_armed();\n'+producer.ARGUMENT+b'\nargv_init[2] = NULL;\nrun_init_process("/init");'
    changed=producer.main_overlay(seam)
    assert producer.NORMAL_ARGUMENT in changed and changed.index(b'n154_require_return_armed();')<changed.index(producer.NORMAL_ARGUMENT)
    def refused(call):
        try:call()
        except ValueError:return
        raise AssertionError('invalid builtin route/slot accepted')
    refused(lambda:producer.main_overlay(seam+producer.ARGUMENT))
    settings=dict(producer.p.REQUIRED_CONFIG,**producer.SETTINGS)
    raw='\n'.join('CONFIG_'+k+'='+v for k,v in settings.items()).encode()
    assert producer.check_config(raw,producer.SETTINGS)['INITRAMFS_FORCE']=='y'
    refused(lambda:producer.check_config(raw.replace(b'CONFIG_INITRAMFS_FORCE=y',b'CONFIG_INITRAMFS_FORCE=n'),producer.SETTINGS))
    # Synthetic Image layout with the production-length inert slot and size cell.
    offset=64;size_offset=(offset+producer.SLOT_BYTES+7)&~7
    image=bytearray(size_offset+8);image[offset:offset+len(producer.SLOT_MARKER)]=producer.SLOT_MARKER
    struct.pack_into('<Q',image,size_offset,producer.SLOT_BYTES)
    table={k:[dict(address=v)] for k,v in {'_text':0x1000,'__initramfs_start':0x1000+offset,'__initramfs_size':0x1000+size_offset}.items()}
    proof=producer.initramfs_slot_proof(image,table)
    assert proof['offset']==offset and proof['bytes']==producer.SLOT_BYTES and proof['unpatched_Image_eligible'] is False
    struct.pack_into('<Q',image,size_offset,producer.SLOT_BYTES-1)
    refused(lambda:producer.initramfs_slot_proof(image,table))
    struct.pack_into('<Q',image,size_offset,producer.SLOT_BYTES)
    image[offset]=0
    refused(lambda:producer.initramfs_slot_proof(image,table))
    return dict(passed=True,groups=1,variants=7,assertions=7)
