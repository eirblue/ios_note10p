"""New SYSTEM_RUNNING seam and park behavior only; old worker is not executed."""
import v293_recovery_prepare as producer


def predicate(fixture_result):
    raw = producer.DECLARATION + b'\n' + producer.ENTRY
    changed = producer.main_overlay(raw)
    assert changed.count(b'schedule_work(&deferred_initcall_work);') == 1
    guard = changed.index(b'n154_require_return_armed();')
    deferred = changed.index(b'schedule_work(&deferred_initcall_work);')
    park = changed.index(b'n293_recovery_only();')
    assert guard < deferred < park < changed.index(b'argv_init[1]')
    assert b'extern void __noreturn n293_recovery_only(void);' in changed
    try:
        producer.main_overlay(changed)
    except ValueError:
        pass
    else:
        raise AssertionError('already changed init route was admitted')
    assert fixture_result == dict(passed=True, groups=1, variants=2, assertions=8)
    return dict(passed=True, groups=2, variants=3, assertions=12)


def recipient_predicate(encoded):
    """New recipient binding only; do not call the spent park/seam predicate."""
    value = producer.recipient(encoded)
    assert value == dict(public_PEM_sha256=producer.PUBLIC_PEM_SHA256,
                         public_SPKI_sha256=producer.PUBLIC_SPKI_SHA256)
    raw = bytearray(producer.base64.b64decode(encoded, validate=True))
    raw[100] = ord('B') if raw[100] != ord('B') else ord('C')
    wrong = producer.base64.b64encode(raw).decode('ascii')
    for invalid in (encoded + '\n', wrong):
        try:
            producer.recipient(invalid)
        except ValueError:
            pass
        else:
            raise AssertionError('noncanonical or different recipient admitted')
    return dict(passed=True, groups=1, variants=3, assertions=3)
