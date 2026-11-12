"""229 exact same-ELF address-range argv for the three bounded assembly leaves."""
from pathlib import PurePosixPath
CAP=65536


def command(vmlinux,symbol):
    image=str(vmlinux);path=PurePosixPath(image)
    if not path.is_absolute()or str(path)!=image or '..'in path.parts or path.name!='vmlinux':
        raise ValueError('canonical absolute same-vmlinux POSIX path required')
    if type(symbol)is not dict or set(symbol)!={'symbol','address','bytes','aliases'}or symbol['symbol']not in ('memcpy','memset','memcmp'):
        raise ValueError('one actual named assembly leaf symbol required')
    address,size,aliases=symbol['address'],symbol['bytes'],symbol['aliases']
    if type(address)is not int or type(size)is not int or not 0<address<1<<64 or not 0<size<=CAP or address%4 or size%4 or address+size>=1<<64:
        raise ValueError('bounded aligned actual64bit ELF leaf extent required')
    if type(aliases)is not list or not aliases or any(type(name)is not str or not name for name in aliases)or len(aliases)!=len(set(aliases))or symbol['symbol']not in aliases:
        raise ValueError('actual same-extent alias record required')
    return ['aarch64-linux-gnu-objdump','-d','--disassemble-zeroes','--start-address='+hex(address),'--stop-address='+hex(address+size),image]
