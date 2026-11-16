"""Only the new metadata owner seam, target refusals and48-member coupling."""
import v285_native_prepare as producer


def predicate():
    p=producer
    p.audit_api()
    source=(p.HERE/'v226_source_stream_kernel.c').read_bytes()
    # Actual retained owner structure is setup, not an old proof invocation.
    source=source.replace(b'static N226_NOINLINE int n226_ingest_prepared_locked(',
        b'#include "v279_current_owner_seal.inc"\nstatic N226_NOINLINE int n226_ingest_prepared_locked(',1)
    source=source.replace(b'    goto done;\n',p.seal_base.CALL+b'    goto done;\n',1)
    changed=p.owner_overlay(source)
    assert changed.count(b'n278_seal_once(')==1
    assert changed.index(b'n226_codec_end(ctx);')<changed.index(b'error=n285_snapshot_of_locked(')<\
        changed.index(b'error=n285_prepare_metadata(')<changed.index(b'error=n278_seal_once(')<changed.index(b'stats->error=')
    assert changed.index(b'if(n217_kernel_state.spent)')<changed.index(b'memset(n226_source_pool,0,sizeof(n226_source_pool))')
    assert b'if(error&&N279_SEAL->phase==N278_EMPTY)N279_SEAL->phase=N278_REFUSED;'in changed
    assert b'memzero_explicit(n226_source_pool,N226_WORKSPACE_BYTES)'in changed
    assert b'memzero_explicit(n226_source_pool+N226_STAGE_OFFSET,N217_CHUNK)'in changed
    for bad in (source.replace(p.seal_base.CALL,b''),source+p.DONE,source+b'n285_unknown'):
        try:p.owner_overlay(bad)
        except ValueError:pass
        else:raise AssertionError('ambiguous owner seam accepted')
    entries=[dict(name=name,bytes=1,regular=True,symlink=False)for name in p.SUCCESS_MEMBERS if name!='members.json']
    assert len(p.inventory_metadata(entries,True))==47
    try:p.inventory_metadata(entries[:-1],True)
    except ValueError:pass
    else:raise AssertionError('new member absent from success')
    try:p.verify_metadata(dict(schema='note10-v285-CPU-metadata-raw-v1',complete=False),'')
    except ValueError:pass
    else:raise AssertionError('incomplete target capture accepted')
    assert len(p.NAMED)==p.NAMED_CAP==49 and p.EXTENT_CAP==79 and p.OUTLINED_CAP==30
    assert p.CAPTURE_SCHEMA==p.watchdog.CAPTURE_SCHEMA
    return dict(passed=True,groups=1,variants=1,assertions=1)
