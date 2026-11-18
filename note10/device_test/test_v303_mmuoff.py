"""New owned-cursor/record ABI, source seams and physical-stub evidence only."""
import v303_mmuoff_prepare as producer


def predicate(fixture_result):
    assert fixture_result==dict(passed=True,groups=1,variants=10,assertions=10)
    def refused(call):
        try:call()
        except ValueError:return
        raise AssertionError('invalid new MMU-off source/evidence admitted')
    changed=producer.return_overlay(b'    n302_spin();\n')
    assert b'n303_enter(' in changed and b'atomic_cmpxchg(&n10_return_requested,1,0)' in changed
    refused(lambda:producer.return_overlay(changed))
    changed=producer.snapshot_overlay(b'/* synthetic owner */\n')
    assert changed.count(b'#include "n303_snapshot_claim.inc"')==1
    refused(lambda:producer.snapshot_overlay(changed))
    entry=dict(address=0x1000,bytes=36)
    good=('1000: 00000000 mrs x10, currentel\n1004: 00000000 cmp x10, #4\n'
          '1008: 00000000 b.ne 101c <synthetic>\n100c: 00000000 mrs x11, sctlr_el1\n'
          '1010: 00000000 dsb sy\n1014: 00000000 str w5, [x4]\n'
          '1018: 00000000 mov w9, #0x54\n101c: 00000000 yield\n1020: 00000000 b 101c <synthetic>\n')
    assert producer.stub_proof(good,entry)['no_external_calls'] is True
    refused(lambda:producer.stub_proof(good.replace('dsb sy','ret'),entry))
    refused(lambda:producer.stub_proof(good.replace('b.ne 101c','b.ne 2000'),entry))
    return dict(passed=True,groups=2,variants=17,assertions=17)
