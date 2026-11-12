"""New request-model fixtures only; no native buffers or old suites."""
import json
from native_source_request_budget import budget,CONFIG_KEYS,TYPE_KEYS


def run():
    config=dict(ARM64_4K_PAGES='y',SLUB='y',NR_CPUS='8',BASE_SMALL='0',FORCE_MAX_ZONEORDER='11',
        TRANSPARENT_HUGEPAGE='n',SLUB_DEBUG='y',SLUB_DEBUG_ON='n',MEMCG='y',TMPFS='y')
    sizes=dict(zip(TYPE_KEYS,(256,592,192,680,576,96,42312,112,328,32)))
    frames={k:128 for k in ('n219_sha256_transform','n219_sha256_init','n219_sha256_update','n219_sha256_final','n219_ingest_current')}
    frames['n219_sha256_init']=0
    source={'kernel.mem':16384*65,'adapter.mem':16384};assertions=0
    def check(ok):
        nonlocal assertions
        assertions+=1
        if not ok:raise AssertionError('new request-budget assertion '+str(assertions))
    def denied(fn):
        try:fn()
        except ValueError:return True
        return False
    # group1 two variants: phase max, no window/input duplication.
    result=budget(source,config,sizes,frames)
    check(all(row['named_phase_request_peak_bytes']==max(row['named_unpack_live_request_bytes'],row['named_ingest_live_request_bytes'])for row in result['branches'].values()))
    check(result['gunzip_raw_request_bytes']==75176 and result['gunzip_nominal_bucket_request_bytes']==98400 and result['compressed_member_added_again_bytes']==0 and result['workspace_includes_window'])
    # group2 two variants: both rootfs branches/counts, incompatible config denied.
    check(result['attached_radix_node_ceiling']==7 and result['preload_plus_inflight_node_ceiling']==169 and
          result['branches']['tmpfs']['named_persistent_payload_bytes']-result['branches']['ramfs']['named_persistent_payload_bytes']==3*(680-592))
    check(denied(lambda:budget(source,dict(config,TRANSPARENT_HUGEPAGE='y'),sizes,frames)))
    # group3 two variants: unknowns never authorize; malformed/missing costs denied.
    check(result['unknown_rows'] and result['resident_upper_bound_bytes']is None and result['whole_system_upper_bound_bytes']is None and
          all(result[k]is False for k in ('complete_numeric_peak','physical_scope_reviewable','device_authorized','global_destination_no_replay_proven')))
    missing=dict(sizes);del missing['sha_state']
    check(denied(lambda:budget(source,config,missing,frames)) and denied(lambda:budget(source,config,dict(sizes,file=True),frames)) and
          denied(lambda:budget(source,config,dict(sizes,file=1<<64),frames)))
    return dict(schema='note10-v219-request-budget-fixture-v1',passed=True,groups=3,variants=6,assertions=assertions)

if __name__=='__main__':print(json.dumps(run(),sort_keys=True))
