"""Only the new storage conjunction and its actual generated-owner seam."""
import v290_native_prepare as producer


def predicate(fixture_result):
    producer.audit_api()
    # Exact retained AFTER_END is input setup, never an old test invocation.
    raw=(producer.HERE/'v226_source_stream_kernel.c').read_bytes()
    signature=b'static N226_NOINLINE int n226_ingest_prepared_locked('
    source=raw.replace(signature,b'#include "v285_current_cpu_metadata.inc"\n'+signature,1)
    source=source.replace(b' done:\n',b' done:\n'+producer.metadata.AFTER_END,1)
    changed=producer.owner_overlay(source)
    producer.require(changed.count(producer.STORAGE_CALL)==1 and changed.index(producer.SEAL_CALL)<changed.index(producer.STORAGE_CALL)<changed.index(b'stats->error='), 'new source-owned post-seal storage caller')
    producer.require(fixture_result==dict(passed=True,groups=1,variants=1,assertions=1,negative_cases=4),'new actual C storage conjunction only')
    return dict(passed=True,groups=1,variants=1,assertions=1)
