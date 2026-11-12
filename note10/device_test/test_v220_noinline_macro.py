"""Only the new closed attribute transform; no SHA vectors or old fixtures."""
import v220_native_source_prepare as producer


def run(original):
    assertions=0
    def check(ok):
        nonlocal assertions
        assertions+=1
        if not ok:raise AssertionError('closed macro transform assertion failed')
    def denied(raw):
        try:producer.patch_noinline(raw)
        except ValueError:return True
        return False
    changed=producer.patch_noinline(original)
    check(changed==original.replace(producer.BEFORE,producer.AFTER) and changed.count(producer.AFTER)==4 and
          changed.replace(producer.AFTER,producer.BEFORE)==original)
    check(denied(original+b'\n'))
    check(denied(changed))
    return dict(groups=1,variants=3,assertions=assertions),changed
