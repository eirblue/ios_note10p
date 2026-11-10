"""Pinned opt-in memdev patch and fixed scalar arithmetic projection."""
import difflib
import hashlib


REL = 'bsd/dev/memdev.c'
PATCH_NAME = '0014-memdev-wide-byte-extent.patch'
PATCH_SHA256 = '290d38e2fcbd45d7e3d626417e0fa1ba3b8d9b9528a5d511d7cadad9e985f0bc'
POSTIMAGE_SHA256 = '2287acde8a535955f5126b990ac1d0f0e22054b1251ce21c232599914b79195d'
REFERENCE_PINS = {
    REL: (29537, '4d50d2fb61096aca3ab354f402069c4ffea1f82d6b6be719518954588e97747a'),
    'bsd/sys/param.h': (10141, 'ee6024c8fee1eb9bcd280203532cba183fb015c5549eebcd8f45f4667529ad4a'),
    'bsd/arm/limits.h': (5958, '25601a7f5536e86447b47fb24dd5ea12310df2d7b0056f50db80f4c91de8c6b9'),
    'bsd/libkern/libkern.h': (9702, 'b5036cd85a9d75e56189d6f80336a818eab16e776cd3b854e494a1900f13cc3d'),
    'bsd/sys/buf.h': (59395, 'c30c605d4edd8b87d9e17b0ddee028ad4d4d4a7ad6db6149e05549f5fe28d1c7'),
    'bsd/sys/uio.h': (10212, 'f2e931597efe30d3f884e28d2a66374c14151ac04d637837deeb42e82cd68c14'),
}


def transformed(before):
    if hashlib.sha256(before).hexdigest() != REFERENCE_PINS[REL][1]:
        raise ValueError('exact memdev preimage required')
    text = before.decode('utf-8')
    old = 'mdev[devid].mdSize << 12'
    if text.count(old) != 8:
        raise ValueError('eight exact byte reconstruction seams required')
    text = text.replace(old, '(uint64_t)' + old)
    old_count = 'count = imin(uio_resid(uio), ((uint64_t)mdev[devid].mdSize << 12) - uio->uio_offset);'
    new_count = 'count = (int)MIN((uint64_t)INT_MAX, MIN((uint64_t)uio_resid(uio), ((uint64_t)mdev[devid].mdSize << 12) - (uint64_t)uio->uio_offset));'
    if text.count(old_count) != 1:
        raise ValueError('unique character count seam required')
    after = text.replace(old_count, new_count).encode('utf-8')
    if hashlib.sha256(after).hexdigest() != POSTIMAGE_SHA256:
        raise ValueError('reviewed memdev postimage differs')
    return after


def patch_bytes(before):
    after = transformed(before)
    raw = ''.join(difflib.unified_diff(before.decode().splitlines(True),
        after.decode().splitlines(True), fromfile='a/' + REL, tofile='b/' + REL)).encode()
    if hashlib.sha256(raw).hexdigest() != PATCH_SHA256:
        raise ValueError('reviewed literal memdev patch differs')
    return raw


def fixture_header(after, references):
    if set(references) != set(REFERENCE_PINS) or any(
        len(references[name]) != size or hashlib.sha256(references[name]).hexdigest() != digest
        for name, (size, digest) in REFERENCE_PINS.items()
    ) or hashlib.sha256(after).hexdigest() != POSTIMAGE_SHA256:
        raise ValueError('exact arithmetic source inputs required')
    text = after.decode()

    def line(prefix, source=text):
        matches = [s.split('/*', 1)[0].rstrip() for s in source.splitlines() if s.startswith(prefix)]
        if len(matches) != 1:
            raise ValueError('unique fixed arithmetic line required')
        return matches[0]

    start = text.index('struct mdev {\n')
    end_marker = '} mdev[NB_MAX_MDEVICES];'
    end = text.index(end_marker, start) + len(end_marker)
    declaration = 'static ' + text[start:end].replace(end_marker, '} mdev[1];')
    extent = line('\t*size = ').split(' = ', 1)[1].removesuffix(';')
    blocks = line('\t\t*o = (((uint64_t)').split(' = ', 1)[1].removesuffix(';')
    count = line('\t\tcount = (int)MIN(').split(' = ', 1)[1].removesuffix(';')
    count = count.replace('uio_resid(uio)', 'resid').replace('uio->uio_offset', 'offset')
    char_eof = line('\tif (uio->uio_offset > ').removeprefix('\tif (').removesuffix(') {')
    char_eof = char_eof.replace('uio->uio_offset', 'offset')
    eof = line('\tif (blkoff >= ').removeprefix('\tif (').removesuffix(') {')
    crossing = line('\tif ((blkoff + buf_count(bp)) > ').removeprefix('\tif (').removesuffix(') {')
    crossing = crossing.replace('buf_count(bp)', 'request')
    trim = line('\t\tbuf_setcount(bp, ').removeprefix('\t\tbuf_setcount(bp, ').removesuffix(');')
    minimum = line('#define MIN(a, b)', references['bsd/sys/param.h'].decode())
    maximum = line('#define INT_MAX ', references['bsd/arm/limits.h'].decode())
    maximum = maximum.replace('INT_MAX', 'N10_SOURCE_INT_MAX', 1)
    return ('''/* Fixed arithmetic copied from the pinned patched memdev; no kernel API stubs. */
#include <stdint.h>
#include <limits.h>
''' + minimum + '\n' + maximum + '\n' + '''
_Static_assert(UINT_MAX == UINT32_MAX, "actual source unsigned-int width");
_Static_assert(INT_MAX == N10_SOURCE_INT_MAX, "actual source int bound");
''' + declaration + f'''
static uint64_t n10_extent(uint32_t pages) {{
    const int devid = 0;
    mdev[devid].mdSize = pages;
    return {extent};
}}
static uint64_t n10_blocks(uint32_t pages, int sector) {{
    const int devid = 0;
    mdev[devid].mdSize = pages;
    mdev[devid].mdSecsize = sector;
    return {blocks};
}}
static int n10_char_count(uint32_t pages, int64_t resid, int64_t offset) {{
    const int devid = 0;
    mdev[devid].mdSize = pages;
    if ({char_eof}) return 0;
    return {count};
}}
static int n10_eof(uint32_t pages, uint64_t blkoff) {{
    const int devid = 0;
    mdev[devid].mdSize = pages;
    return {eof};
}}
static uint32_t n10_strategy_count(uint32_t pages, uint64_t blkoff, uint32_t request) {{
    const int devid = 0;
    mdev[devid].mdSize = pages;
    if ({crossing}) return {trim};
    return request;
}}
''').encode()
