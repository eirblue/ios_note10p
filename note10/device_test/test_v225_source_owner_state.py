"""New shared state source/symbol boundary only; no old core/SHA fixture replay."""
from pathlib import Path
import v225_source_owner_state as owner_state


def run():
    assertions=0
    def check(ok):
        nonlocal assertions
        assertions+=1
        if not ok:raise AssertionError('shared state assertion failed')
    def denied(call):
        try:call()
        except ValueError:return True
        return False
    original=Path(__file__).with_name('v219_source_owner_kernel.c').read_bytes()
    transformed=owner_state.prepare(original)
    symbols='n217_ingest_current T 10 20\nn219_ingest_current T 40 10\nn217_kernel_state b 80 188\n'
    check(b'n219_kernel_state' not in transformed and transformed.count(b'n217_kernel_state')==11 and
        b'if(n217_kernel_state.spent)' in transformed and b'&n217_kernel_state,&io,&ctx,stage,N217_CHUNK' in transformed and
        b'memcpy(result,&n217_kernel_state.result,sizeof(*result));' in transformed)
    check(owner_state.shared_symbols(symbols,392)==dict(schema='note10-v225-compiled-shared-owner-state-v1',state_symbol='n217_kernel_state',state_bytes=392,
        state_count=1,legacy_state_count=0,entry_symbols=['n217_ingest_current','n219_ingest_current'],compiled_only=True,runtime_no_replay_proven=False))
    check(denied(lambda:owner_state.prepare(original+b' ')))
    check(denied(lambda:owner_state.shared_symbols(symbols+'n219_kernel_state b 208 188\n',392)))
    check(denied(lambda:owner_state.prepare(transformed)))
    check(denied(lambda:owner_state.shared_symbols('n217_ingest_current T 10 20\nn219_ingest_current T 40 10\n',392)))
    return dict(groups=1,variants=3,assertions=assertions)
