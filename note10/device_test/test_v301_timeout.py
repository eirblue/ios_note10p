"""Only changed timeout-policy source seam; old probes/actor tests are not run."""
import v301_timeout_prepare as producer


def predicate(fixture_result):
    assert fixture_result==dict(passed=True,groups=1,variants=6,assertions=6)
    raw=producer.KERNEL_INCLUDE+b'\n'+producer.HOST_INCLUDE+b'\n'+producer.TIMEOUT_LINE+b'\n'
    changed=producer.timeout_overlay(raw)
    assert changed.count(b'n301_timeout_reason(s->timeout)')==1 and producer.TIMEOUT_LINE not in changed
    try:producer.timeout_overlay(changed)
    except ValueError:pass
    else:raise AssertionError('timeout policy reapplied')
    return dict(passed=True,groups=2,variants=8,assertions=8)
