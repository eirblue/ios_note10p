"""Only the new299 source-append boundary; old probes/parsers are not run."""
import v299_watchdog_prepare as producer


def predicate(fixture_result):
    assert fixture_result==dict(passed=True,groups=1,variants=15,assertions=15)
    raw=b'/* synthetic source */\n';name='synthetic.inc'
    changed=producer.append_guarded(raw,name)
    assert changed.startswith(raw) and changed.count(b'#include "synthetic.inc"')==1
    try:producer.append_guarded(changed,name)
    except ValueError:pass
    else:raise AssertionError('duplicate bridge admitted')
    return dict(passed=True,groups=2,variants=17,assertions=17)
