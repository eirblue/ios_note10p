"""New terminal guard/ACK, append seam and bounded spin-proof cases only."""
import v302_park_prepare as producer


def predicate(fixture_result):
    assert fixture_result==dict(passed=True,groups=1,variants=15,assertions=15)
    raw=b'/* synthetic return TU */\n';changed=producer.append_park(raw)
    assert changed.startswith(raw) and changed.count(b'#include "v302_park.inc"')==1
    def refused(call):
        try:call()
        except ValueError:return
        raise AssertionError('invalid new terminal evidence admitted')
    refused(lambda:producer.append_park(changed))
    entry=dict(address=0x1000,bytes=8)
    good='1000: 00000000 yield\n1004: 00000000 b 1000 <synthetic>\n'
    assert producer.spin_proof(good,entry)['no_return'] is True
    refused(lambda:producer.spin_proof(good.replace('yield','ret'),entry))
    refused(lambda:producer.spin_proof(good.replace('b 1000','b 2000'),entry))
    return dict(passed=True,groups=2,variants=20,assertions=20)
