"""New fixed-profile metadata cases only; no compiler, crypto, object or kernel input."""
import copy
import hashlib
import json
from pathlib import Path, PurePosixPath

import current_native_kernel as native
import prepare_user_exception_fetch as fetch
import compact_native_receipts as compact
import native_handoff_artifact as artifact
from phase1_iostorage_kernel_link import storage_units


def model():
    inventory = [dict(source=fetch.REL, source_sha256=fetch.POSTIMAGE, component='osfmk', kind='C'),
                 dict(source=fetch.COPYIN_REL, source_sha256=fetch.COPYIN_SHA, component='osfmk', kind='C')]
    inventory += [dict(source='osfmk/synthetic/unit' + str(i) + '.c', source_sha256='a' * 64,
                       component='osfmk', kind='C') for i in range(1065)]
    producer = dict(source_commit='1' * 40, objects_root='/objects', user_exception_fetch=fetch.proof())
    bindings = dict(user_exception_fetch=native.digest(fetch.proof()))
    dependencies = {n: dict(path='/unused/source', source_sha256='b' * 64) for n in native.EXTRAS}
    dependencies[fetch.UNIT] = dict(path=str(fetch.ROOT / fetch.SOURCE), source_sha256=fetch.PINS[fetch.SOURCE])
    current = dict(kind='v84-current-native', producer=producer, producer_id=native.digest(producer),
                   bindings=bindings, input_binding=native.digest(bindings), inventory=inventory, dependencies=dependencies)
    rows = []
    for i, item in enumerate(inventory + [dict(source=n, **v) for n, v in dependencies.items()]):
        name = item['source']
        row = dict(source=name, source_sha256=item['source_sha256'], object_path='/objects/' + str(i) + '.o',
                   object_sha256='c' * 64, passed=True)
        native.stamp(current, row, 'native' if i < 1067 else 'port' if name == fetch.UNIT else native.EXTRAS[name])
        rows.append(row)
    source_rows = {r['source']: r for r in rows}
    defined = {name: [source_rows[src]['object_path']] for name, src in
               zip(fetch.LINK_SYMBOLS, (fetch.REL, fetch.UNIT, fetch.COPYIN_REL))}
    references = {fetch.LINK_SYMBOLS[1]: defined[fetch.LINK_SYMBOLS[0]].copy(),
                  fetch.LINK_SYMBOLS[2]: defined[fetch.LINK_SYMBOLS[1]].copy()}
    storage_proof = dict(producer_id=current['producer_id'], input_binding=current['input_binding'])
    binding = native.digest(storage_proof)
    storage = dict(binding=dict(proof=storage_proof, binding=binding), units=[])
    for source, _, source_sha in storage_units(PurePosixPath('/source-proof')):
        row = dict(source='@storage/' + source.name, source_sha256=source_sha,
                   object_path='/storage/' + source.stem + '.o', object_sha256='d' * 64, passed=True,
                   storage_binding=binding)
        native.stamp(current, row, 'storage')
        storage['units'].append(row)
    current['storage'] = storage['binding']
    filelist = ('\n'.join(r['object_path'] for r in rows + storage['units']) + '\n').encode()
    link = dict(producer_id=current['producer_id'], input_binding=current['input_binding'], link_succeeded=True,
                returncode=0, object_count=1078, filelist_sha256=hashlib.sha256(filelist).hexdigest())
    summary = dict(source_head='1' * 40, storage_binding_sha256=binding,
                   storage_object_sha256={r['source']: r['object_sha256'] for r in storage['units']},
                   memdev_integration=dict(native_manifest_sha256=native.digest([
                       {k: r[k] for k in ('source', 'component', 'kind', 'source_sha256')} for r in inventory])))
    return current, rows, defined, references, storage, link, filelist, summary


def run():
    groups = [0, 0, 0]
    def deny(group, call):
        try:
            call()
        except ValueError:
            groups[group] += 1
        else:
            raise ValueError('new fixed-profile denial accepted')
    current, rows, defined, references, storage, link, filelist, summary = model()
    observation = fetch.link_begin()
    fetch.bind_symbol_origins(current, rows, defined, references, {}, observation)
    groups[0] += 1
    for case in range(8):
        bad_rows, defs, refs, aliases = copy.deepcopy(rows), copy.deepcopy(defined), copy.deepcopy(references), {}
        if case == 0: defs['_copyin'] = []
        if case == 1: defs['_copyin'] *= 2
        if case == 2: defs['_copyin'] = defs['_n10_fetch_user_instruction'].copy()
        if case == 3: aliases['_copyin'] = '_shim'
        if case == 4: refs['_n10_fetch_user_instruction'] = []
        if case == 5: refs['_copyin'] = []
        if case == 6: bad_rows[0]['source_sha256'] = fetch.PREIMAGE
        if case == 7: bad_rows[1]['producer_id'] = '0' * 64
        deny(0, lambda: fetch.bind_symbol_origins(current, bad_rows, defs, refs, aliases, fetch.link_begin()))
    symbols = '\n'.join('00000001 T ' + n for n in fetch.LINK_SYMBOLS)
    fetch.final_symbols(symbols, link, current, observation)
    groups[0] += 1
    deny(0, lambda: fetch.final_symbols(symbols + '\n00000002 T _copyin', link, current, copy.deepcopy(observation)))
    deny(0, lambda: fetch.final_symbols(symbols.replace('_copyin', '_other'), link, current, copy.deepcopy(observation)))
    # This is newly constructed metadata, not a transformed historical producer or a kernel payload.
    portable = copy.deepcopy(current)
    portable['dependencies'][fetch.UNIT]['path'] = '/project/note10/xnu26/note10_user_instruction_fetch.c'
    compact.validate_rows(rows, portable, storage, link, filelist, summary, user_exception_fetch=True)
    packed_rows, raw = compact.project(json.dumps(rows).encode(), portable, storage, link, filelist, summary,
                                       user_exception_fetch=True)
    if packed_rows != [{k: r[k] for k in compact.CORE} for r in rows] or json.loads(raw)['schema'] != 'note10-v200-compact-native-object-receipts-v1':
        raise ValueError('new compact profile positive')
    groups[1] += 1
    for case in range(7):
        ctx, rs, linked = copy.deepcopy(portable), copy.deepcopy(rows), copy.deepcopy(link)
        if case == 0: rs = rs[:-1]
        if case == 1: linked['object_count'] = 1077
        if case == 2: ctx['producer']['user_exception_fetch']['header_sha256'] = '0' * 64
        if case == 3: ctx['dependencies'][fetch.UNIT]['path'] = '/project/evil.c'
        if case == 4: rs[-1]['category'] = 'metadata'
        if case == 5: rs[-1]['object_path'] = rs[0]['object_path']
        if case == 6: rs[-1]['input_binding'] = '0' * 64
        deny(1, lambda: compact.validate_rows(rs, ctx, storage, linked, filelist, summary, user_exception_fetch=True))
    deny(1, lambda: compact.validate_rows(rows, portable, storage, link, filelist, summary))
    deny(1, lambda: compact.project(b' ' * (compact.FETCH_RAW_MAX + 1), portable, storage, link, filelist, summary,
                                   user_exception_fetch=True))
    counts = dict(counts_complete=True, linked_unit_compile_attempts=1078, auxiliary_genassym_target_compiles=1,
                  total_target_driver_compile_jobs=1079, host_config_compiler_drivers=1, host_config_C_units=9,
                  host_config_links=1, bison=1, flex=1, IIG_attempts=4, IIG_successes=4,
                  MIG_attempts=2, MIG_successes=2, alias_map_generations=1, alias_assembler_invocations=0, nm_invocations=4)
    state = dict(user_exception_fetch_link=observation, user_exception_tool_counts=counts)
    summary.update(copy.deepcopy(state))
    artifact.verify_fetch_profile(portable, rows, state, summary, link)
    groups[2] += 1
    for case in range(4):
        bad = copy.deepcopy(state)
        if case == 0: bad['user_exception_fetch_link']['members']['_copyin']['source'] = 'bsd/stub.c'
        if case == 1: bad['user_exception_tool_counts']['total_target_driver_compile_jobs'] = 1078
        if case == 2: bad['user_exception_fetch_link']['runtime_task_map_observed'] = True
        if case == 3: bad['user_exception_fetch_link']['aliases_substituted'] = True
        mutated_summary = copy.deepcopy(summary)
        mutated_summary.update(copy.deepcopy(bad))
        deny(2, lambda: artifact.verify_fetch_profile(portable, rows, bad, mutated_summary, link))
    deny(2, lambda: artifact.success_payloads(Path('/not-read'), {}, '1' * 40, 1, 1,
                                            compact=False, user_exception_fetch=True))
    if groups != [12, 10, 6]:
        raise ValueError('new metadata case count')
    return dict(groups=3, cases=28, group_cases=groups, host_C_compiles=0, old_suites=0)
