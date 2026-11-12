"""New229 bounded range-argv regression only; no old fixture replay."""
import v229_leaf_capture as capture


def run():
    image='/synthetic/objects/vmlinux';symbol=dict(symbol='memcpy',address=0x1000,bytes=16,aliases=['memcpy','__memcpy'])
    if capture.command(image,symbol)!=['aarch64-linux-gnu-objdump','-d','--disassemble-zeroes','--start-address=0x1000','--stop-address=0x1010',image]:
        raise AssertionError('exact zero-preserving ELF address-range argv required')
    try:capture.command(image,dict(symbol,address=(1<<64)-4,bytes=8))
    except ValueError:pass
    else:raise AssertionError('overflowing ELF range must be rejected')
    return dict(groups=1,variants=2,assertions=2)
