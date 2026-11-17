"""One new actual C collector/codec/owner conjunction, no old fixture invocation."""
import v291_native_prepare as producer

def predicate(fixture_result,golden_matches):
    producer.audit_api()
    raw=(producer.HERE/'v226_source_stream_kernel.c').read_bytes()
    signature=b'static N226_NOINLINE int n226_ingest_prepared_locked('
    source=raw.replace(signature,b'#include "v285_current_cpu_metadata.inc"\n'+signature,1)
    source=source.replace(b' done:\n',b' done:\n'+producer.metadata.AFTER_END,1)
    source=producer.retained.owner_overlay(source)
    changed=producer.owner_overlay(source)
    producer.require(changed.count(producer.DRAFT_CALL)==1 and changed.index(producer.retained.STORAGE_CALL)<changed.index(producer.DRAFT_CALL)<changed.index(b'stats->error='),'new real post-storage source caller')
    producer.require(fixture_result==dict(passed=True,groups=1,variants=1,assertions=1,negative_cases=6)and golden_matches is True,'new C conjunction plus immutable golden bytes')
    return dict(passed=True,groups=1,variants=1,assertions=1)
