"""Only new media dependency closure cases; no old profiles or native data."""
import hashlib
import native_media_dependency_profile as profile


def run():
    assertions=0;variants=0
    def check(ok):
        nonlocal assertions
        assertions+=1
        if not ok:raise AssertionError('media dependency assertion '+str(assertions))
    def rejected(call):
        try:call()
        except ValueError:return True
        return False
    critical=dict(profile.MANDATORY)
    values={**critical,**profile.DISPLAY,**profile.COMMON,**profile.REMOVED}
    # Group1: real shared provider requirements, including the failed214 interfaces.
    variants+=1;accepted=profile.effective(values,critical)
    check(accepted['retained_common']==profile.COMMON)
    check(accepted['display_reference']==profile.DISPLAY)
    variants+=1;changed=dict(values,VIDEO_V4L2='n')
    check(rejected(lambda:profile.effective(changed,critical)))
    variants+=1;changed=dict(values,VIDEOBUF2_DMA_SG='n')
    check(rejected(lambda:profile.effective(changed,critical)))
    # Group2: actual owner/consumer closure and unaffected safety requirements.
    variants+=1;changed=dict(values,LEDS_S2MPB02='y')
    check(rejected(lambda:profile.effective(changed,critical)))
    variants+=1;changed=dict(values,EXYNOS_REBOOT='n')
    check(rejected(lambda:profile.effective(changed,critical)))
    variants+=1;source=b'synthetic shared provider selector\n';expected=hashlib.sha256(source).hexdigest()
    check(rejected(lambda:profile.guard_source(source+b'mutated\n',expected)))
    return dict(groups=2,variants=variants,assertions=assertions,old_tests_replayed=0,host_compiles=0,native_input_reads=0)
