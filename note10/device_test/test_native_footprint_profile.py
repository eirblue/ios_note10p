"""Only the new fixed configuration admission cases; no compiler or native data."""
import hashlib
import native_footprint_profile as profile


def run():
    assertions=0;variants=0
    def check(ok):
        nonlocal assertions
        assertions+=1
        if not ok:raise AssertionError('footprint profile assertion '+str(assertions))
    def rejected(call):
        try:call()
        except ValueError:return True
        return False
    # Group1: actual production critical/media configuration guard.
    critical=dict(profile.MANDATORY);values=dict(critical,**{k:'n' for k in profile.MEDIA_OFF})
    variants+=1;accepted=profile.effective(values,critical)
    check(accepted['selected_config']=={'MEDIA_SUPPORT':'n'})
    check(accepted['retained_critical']==critical)
    variants+=1;changed=dict(values,MEDIA_SUPPORT='y')
    check(rejected(lambda:profile.effective(changed,critical)))
    variants+=1;changed=dict(values,EXYNOS_REBOOT='n')
    check(rejected(lambda:profile.effective(changed,critical)))
    # Group2: source mutation uses synthetic bytes; no old source parser suite.
    variants+=1;raw=b'synthetic stock boundary\n';expected=hashlib.sha256(raw).hexdigest()
    check(rejected(lambda:profile.guard_source(raw+b'mutated\n',expected)))
    return dict(groups=2,variants=variants,assertions=assertions,old_tests_replayed=0,host_compiles=0,native_input_reads=0)
