"""New scoped cost/lifetime denials only; synthetic metadata, no binary input."""
import native_source_accounting as accounting


def run():
    assertions=0;variants=0
    def check(ok):
        nonlocal assertions
        assertions+=1
        if not ok:raise AssertionError('accounting assertion '+str(assertions))
    def spec():return dict(source_bytes={'kernel.mem':65536,'adapter.mem':16384},reference_linked_bytes=1048576,
                           reservation_bytes=33554432,initramfs_bytes=6291456,deferred_initcalls=True,rootfs_kind='unknown')
    sizes={name:128 for name in accounting.SIZE_NAMES};sizes['inflate_workspace']=40000
    def denied(value):
        try:accounting.account(value,sizes)
        except ValueError:return True
        return False
    variants+=1;result=accounting.account(spec(),sizes)
    check(result['source_file_pages']==20)
    check(result['source_plus_destination_data_bytes']==33554432+81920)
    check(result['reference_linked_reserved_source_lower_bound']==1048576+33554432+81920)
    variants+=1;check(result['gunzip_requested_bytes']==32768+128+40000)
    check(result['workspace_includes_window']is True and result['compressed_member_added_again_bytes']==0)
    variants+=1;check(result['deferred_initcalls']is True and result['initmem_credit_bytes']==0)
    check(result['unchanged_global_runtime_baseline']['bytes']is None)
    variants+=1;unknown=accounting.account(spec(),{})
    check(bool(unknown['missing_target_sizes']) and unknown['gunzip_requested_bytes']is None)
    check(unknown['upper_bound_bytes']is None and unknown['complete_numeric_peak']is False and unknown['device_authorized']is False)
    variants+=1;value=spec();value['source_bytes']['kernel.mem']=1<<63;check(denied(value))
    variants+=1;value=spec();value['reservation_bytes']=True;check(denied(value))
    return dict(groups=4,variants=variants,assertions=assertions,old_tests_replayed=0,native_input_reads=0)
