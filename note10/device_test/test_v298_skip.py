"""Only new config/argument combinations and the guarded replacement seam."""
import v298_skip_prepare as producer


def predicate(fixture_result):
    assert fixture_result==dict(passed=True,groups=1,variants=8,assertions=16)
    raw=b'prefix\n'+producer.SKIP_HANDLER+b'\n__setup("skip_initramfs", skip_initramfs_param);\nsuffix'
    changed=producer.skip_overlay(raw)
    assert changed==raw.replace(producer.SKIP_HANDLER,b'#include "v298_skip_initramfs.inc"',1)
    try:producer.skip_overlay(changed)
    except ValueError:pass
    else:raise AssertionError('second handler overlay admitted')
    return dict(passed=True,groups=2,variants=10,assertions=18)
