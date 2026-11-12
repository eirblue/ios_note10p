"""Only the new empty-initramfs object-profile boundary; no old host fixtures."""
import v218_native_source_prepare as profile


def run():
    assertions=0;variants=0
    def check(ok):
        nonlocal assertions
        assertions+=1
        if not ok:raise AssertionError('empty object profile assertion '+str(assertions))
    def rejected(values,critical):
        try:profile.object_profile(values,critical)
        except ValueError:return True
        return False
    critical=profile.critical_settings()
    values={**critical,**profile.prepared.footprint.COMMON,**profile.prepared.footprint.DISPLAY,**profile.prepared.footprint.REMOVED}
    values.pop('INITRAMFS_COMPRESSION_NONE')
    # Group1: inactive choice is n/absent; the old contradictory positive fails.
    variants+=1;accepted=profile.object_profile(values,critical)
    check(critical['INITRAMFS_COMPRESSION_NONE']=='n' and profile.house.SETTINGS['INITRAMFS_COMPRESSION_NONE']=='y')
    check(accepted['object_profile']['kind']=='empty-initramfs-owner-object')
    check(accepted['retained_critical']==critical)
    variants+=1;check(rejected(dict(values,INITRAMFS_COMPRESSION_NONE='y'),critical))
    # Group2: this correction cannot weaken a real gate or accept a payload profile.
    variants+=1;check(rejected(dict(values,EXYNOS_REBOOT='n'),critical))
    variants+=1;check(rejected(dict(values,INITRAMFS_SOURCE='"synthetic.cpio"'),critical))
    return dict(groups=2,variants=variants,assertions=assertions,old_tests_replayed=0,host_compiles=0,native_input_reads=0)
