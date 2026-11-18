"""Only new diagnostic include mapping; previous guards/probes are not rerun."""
import v300_diagnostic_prepare as producer


def predicate(fixture_result):
    assert fixture_result==dict(passed=True,groups=1,variants=27,assertions=27)
    raw=b'/* synthetic source */\n#include "v299_wdt_eligible.inc"\n'
    changed=producer.diagnostic_overlay(raw)
    assert changed==raw.replace(b'v299_wdt_eligible.inc',b'v300_wdt_diagnostic.inc')
    try:producer.diagnostic_overlay(changed)
    except ValueError:pass
    else:raise AssertionError('diagnostic overlay repeated')
    return dict(passed=True,groups=2,variants=29,assertions=29)
