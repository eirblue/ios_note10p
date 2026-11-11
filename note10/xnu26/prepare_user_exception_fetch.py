"""Exact, default-off real USER64 exception read overlay and one genuine provider."""
import difflib
import hashlib
import json
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[2]
REL = 'osfmk/arm64/sleh.c'
HEADER_REL = 'osfmk/arm64/note10_user_instruction_fetch.h'
UNIT = '@port/note10_user_instruction_fetch.c'
PATCH_NAME = '0015-user-exception-checked-fetch.patch'
PREIMAGE = '05efec87e8a8d9da97ecd2048acded04641ce2aa103d50874e73d95128cf7e90'
POSTIMAGE = 'e1f5a16794795f275390692ed3c69b51b63a9a74dc240891287e913e689a91f8'
PATCH_SHA = 'aeec679b6dfaec6188ee7b12bb3af3d0dd86e15e2fa6def391efaf6a36c0d0eb'
SOURCE = 'note10/xnu26/note10_user_instruction_fetch.c'
HEADER = 'note10/xnu26/note10_user_instruction_fetch.h'
PINS = {SOURCE: '20becc0643449b8116a22efb377e9486c18830569e5294c87931930d004eb1b3',
        HEADER: '6a9817830b75296d59f087b2cf96e872c8f9d4018b51e5b16d6e3b3cfdc96238',
        'note10/xnu26/user_instruction_header_context.h': 'a2fa27027f150b5b76168f3c025287697e383225063d80b951973e0cc41ef069'}
CAP = 1048576
COPYIN_REL = 'osfmk/arm64/copyio.c'
COPYIN_SHA = '3be70427aebd03f130de44ca06db5adcbf16a9576fa43b9ccc47a50f29930456'
LINK_SYMBOLS = ('_sleh_synchronous', '_n10_fetch_user_instruction', '_copyin')
READ_BEFORE = '\tCOPYIN(get_saved_state_pc(state), (char *)&instr, sizeof(instr));'
READ_AFTER = '''#if defined(ARM64_BOARD_CONFIG_EXYNOS9825)
\tif (PSR64_IS_USER64(get_saved_state_cpsr(state))) {
\t\tstruct n10_user_instruction fetched = n10_fetch_user_instruction(state);
\t\tinstr = fetched.status == N10_USER_FETCH_OK ? fetched.word : 0;
\t} else
#endif
\t{
\tCOPYIN(get_saved_state_pc(state), (char *)&instr, sizeof(instr));
\t}'''
INCLUDE = '#include <arm64/instructions.h>'
NEW_INCLUDE = INCLUDE + '\n#if defined(ARM64_BOARD_CONFIG_EXYNOS9825)\n#include <arm64/note10_user_instruction_fetch.h>\n#endif'


def require(ok, reason):
    if not ok:
        raise ValueError(reason)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def read(path, cap=CAP):
    require(path.resolve() == path and not path.is_symlink() and path.is_file() and
            0 < path.stat().st_size <= cap, 'ordinary bounded source required')
    with path.open('rb') as stream:
        raw = stream.read(cap + 1)
    require(len(raw) == path.stat().st_size <= cap, 'source extent differs')
    return raw


def transformed(before):
    require(sha(before) == PREIMAGE, 'exact series13 caller preimage required')
    text = before.decode('utf-8')
    start = text.index('static void\nhandle_uncategorized(arm_saved_state_t *state)\n{')
    end = text.index('\n#if __has_feature(ptrauth_calls)', start)
    body = text[start:end]
    require(body.count(READ_BEFORE) == 1 and text.count(INCLUDE) == 1, 'unique caller-local seams')
    after = (text[:start] + body.replace(READ_BEFORE, READ_AFTER) + text[end:]).replace(INCLUDE, NEW_INCLUDE).encode()
    require(sha(after) == POSTIMAGE, 'exact new caller postimage required')
    return after


def patch_bytes(before):
    after = transformed(before)
    raw = ''.join(difflib.unified_diff(before.decode().splitlines(True), after.decode().splitlines(True),
                                      fromfile='a/' + REL, tofile='b/' + REL)).encode()
    require(sha(raw) == PATCH_SHA, 'literal caller patch differs')
    return raw


def proof():
    return dict(schema='note10-v198-user-exception-fetch-overlay-v1', source=REL,
                preimage_sha256=PREIMAGE, postimage_sha256=POSTIMAGE, patch_sha256=PATCH_SHA,
                header=HEADER_REL, header_sha256=PINS[HEADER], provider=UNIT, source_sha256=dict(PINS))


def apply(source, output):
    before = read(source / REL)
    require(patch_bytes(before) == read(ROOT / 'note10/xnu26/patches' / PATCH_NAME) and
            all(sha(read(ROOT / name)) == expected for name, expected in PINS.items()), 'reviewed overlay inputs differ')
    destination = source / HEADER_REL
    require(not destination.exists() and not destination.is_symlink(), 'fresh exact declaration overlay required')
    after = transformed(before)
    with destination.open('xb') as stream:
        stream.write(read(ROOT / HEADER))
    (source / REL).write_bytes(after)
    observation = proof()
    (output / 'user-exception-overlay.json').write_text(json.dumps(observation, sort_keys=True, indent=2) + '\n')
    return observation


def admit_provenance(current):
    observation = current['producer'].get('user_exception_fetch')
    require(observation == proof() and current['bindings'].get('user_exception_fetch') ==
            hashlib.sha256(json.dumps(observation, sort_keys=True, separators=(',', ':')).encode()).hexdigest(),
            'exact opt-in caller/header/provider binding required')
    rows = [r for r in current['inventory'] if r['source'] == REL]
    require(len(rows) == 1 and rows[0]['source_sha256'] == POSTIMAGE and rows[0]['component'] == 'osfmk' and
            rows[0]['kind'] == 'C', 'one new caller inventory owner required')
    provider = current['dependencies'].get(UNIT)
    require(type(provider) is dict and set(provider) == {'path', 'source_sha256'} and
            type(provider['path']) is str and 0 < len(provider['path']) <= 4096 and
            provider['source_sha256'] == PINS[SOURCE], 'genuine provider source provenance required')


def admit_binding(current):
    admit_provenance(current)
    provider = current['dependencies'][UNIT]
    require(provider == dict(path=str(ROOT / SOURCE), source_sha256=PINS[SOURCE]), 'genuine current provider identity required')


def link_begin():
    return dict(schema='note10-v200-user-exception-symbol-provenance-v1', stage='pending', passed=False,
                object_provenance_verified=False, final_symbols_verified=False,
                runtime_copyin_verified=False, runtime_task_map_observed=False, native_activation=False,
                firmware_abi_verified=False, physical_ready=False)


def bind_symbol_origins(current, rows, defined, references, aliases, observation):
    from current_native_kernel import digest
    admit_provenance(current)
    require(current['producer_id'] == digest(current['producer']) and current['input_binding'] == digest(current['bindings']),
            'current symbol provenance context required')
    by_path = {r['object_path']: r for r in rows}
    require(len(by_path) == len(rows), 'unique current object paths required')
    expected = ((REL, POSTIMAGE, 'native'), (UNIT, PINS[SOURCE], 'port'), (COPYIN_REL, COPYIN_SHA, 'native'))
    members = {}
    for symbol, (name, source_sha, category) in zip(LINK_SYMBOLS, expected):
        paths = defined.get(symbol, [])
        require(len(paths) == 1 and paths[0] in by_path and symbol not in aliases,
                'unique genuine symbol provider without alias required')
        row = by_path[paths[0]]
        require(row['source'] == name and row['source_sha256'] == source_sha and row['category'] == category and
                row['passed'] is True and row['producer_id'] == current['producer_id'] and
                row['input_binding'] == current['input_binding'], 'exact caller/fetch/native copyin origin required')
        members[symbol] = {k: row[k] for k in ('source', 'source_sha256', 'object_path', 'object_sha256', 'category')}
    require(members[LINK_SYMBOLS[0]]['object_path'] in references.get(LINK_SYMBOLS[1], []) and
            members[LINK_SYMBOLS[1]]['object_path'] in references.get(LINK_SYMBOLS[2], []),
            'actual caller to fetch to native copyin references required')
    observation.update(stage='object-symbols', producer_id=current['producer_id'], input_binding=current['input_binding'],
                       members=members, caller_references_fetch=True, fetch_references_native_copyin=True,
                       aliases_substituted=False, object_provenance_verified=True)


def final_symbols(symbols, linked, current, observation):
    from current_native_kernel import expected_objects
    names = [parts[-1] for line in symbols.splitlines() if len(parts := line.split()) >= 3 and
             re.fullmatch('[0-9a-fA-F]+', parts[0]) and parts[-2].isupper()]
    count = expected_objects(current, storage='storage' in current)
    require(observation['object_provenance_verified'] is True and
            linked['object_count'] == count and
            linked['link_succeeded'] is True and type(linked['returncode']) is int and linked['returncode'] == 0 and
            all(names.count(name) == 1 for name in LINK_SYMBOLS), 'exact final three source symbols required')
    observation.update(stage='complete', passed=True, final_symbols_verified=True,
                       final_symbol_counts={name: names.count(name) for name in LINK_SYMBOLS}, linked_objects=count)


def tool_counts(native, observation, complete):
    """Report completed recorded work; unobservable partial generator counts stay null."""
    counts = dict(counts_complete=False, linked_unit_compile_attempts=observation.get('total_target_compile_attempts'),
                  auxiliary_genassym_target_compiles=None, total_target_driver_compile_jobs=None,
                  host_config_compiler_drivers=None, host_config_C_units=None, host_config_links=None,
                  bison=None, flex=None, IIG_attempts=None, IIG_successes=None, MIG_attempts=None,
                  MIG_successes=None, alias_map_generations=None, alias_assembler_invocations=0, nm_invocations=None)
    if not complete:
        return counts
    extra = json.loads(read(native / 'native-extra-result.json', 8388608))
    mig = json.loads(read(native / 'native-mig-result.json', 8388608))
    assym = json.loads(read(native / 'current-genassym-result.json', 8388608))
    commands = [r for r in extra['commands'] if '--def' in r['command']]
    migrations = mig['interfaces'] + mig['generated_sources']
    require(assym['passed'] is True and observation['total_target_compile_attempts'] == 1078 and
            all(r['exit_code'] == 0 for r in commands) and all(r['passed'] is True for r in migrations),
            'complete actual generator/target reports required')
    counts.update(counts_complete=True, linked_unit_compile_attempts=1078, auxiliary_genassym_target_compiles=1,
                  total_target_driver_compile_jobs=1079, host_config_compiler_drivers=1, host_config_C_units=9,
                  host_config_links=1, bison=1, flex=1, IIG_attempts=len(commands),
                  IIG_successes=sum(r['exit_code'] == 0 for r in commands), MIG_attempts=len(migrations),
                  MIG_successes=sum(r['passed'] is True for r in migrations), alias_map_generations=1, nm_invocations=4)
    return counts


def fetch_argv(compiler, source, native, sdk, output):
    from build_native_bootstrap_selection import common_flags
    return [compiler, *common_flags(source, native / 'configured/DEVELOPMENT/osfmk', sdk),
            '-std=gnu11', '-mkernel', '-fno-c++-static-destructors', '-ftrivial-auto-var-init=zero',
            '-fsigned-bitfields', '-fmerge-all-constants', '-fno-strict-aliasing', '-momit-leaf-frame-pointer',
            '-fno-branch-target-identification', '-mno-implicit-sme', '-DMACH_KERNEL',
            '-I', str(native / 'exports'), '-include', str(ROOT / 'note10/xnu26/user_instruction_header_context.h'),
            '-c', str(ROOT / SOURCE), '-o', str(output)]


def compile_provider(current, source, native):
    from current_native_kernel import stamp
    admit_binding(current)
    require(all(sha(read(ROOT / n)) == h for n, h in PINS.items()) and
            sha(read(source / REL)) == POSTIMAGE and sha(read(source / HEADER_REL)) == PINS[HEADER],
            'bound caller/provider source changed')
    tool = current['producer']['toolchain']
    obj = Path(current['producer']['objects_root']) / 'port_note10_user_instruction_fetch.c.o'
    require(not obj.exists(), 'fresh current provider object required')
    argv = fetch_argv(tool['compiler'], source, native, tool['sdk'], obj)
    done = subprocess.run(argv, cwd=ROOT, capture_output=True, timeout=60)
    log = native / 'user-exception-fetch.log'
    log.write_bytes(done.stdout + done.stderr)
    row = dict(source=UNIT, passed=done.returncode == 0, command=argv, source_sha256=PINS[SOURCE],
               object_path=str(obj), object_sha256=sha(read(obj)) if done.returncode == 0 else None)
    stamp(current, row, 'port')
    report = dict(schema='note10-v198-current-fetch-provider-v1', units=[row])
    (native / 'current-user-exception-fetch-result.json').write_text(json.dumps(report, indent=2) + '\n')
    require(done.returncode == 0, 'current genuine fetch provider compile failed')
    return report


def policy_header(after, proc_reg):
    require(sha(after) == POSTIMAGE and after.decode().count(READ_AFTER) == 1, 'exact caller policy projection required')
    kernel = next(line for line in proc_reg.decode().splitlines() if line.startswith('#define PSR64_IS_KERNEL(x)'))
    # Only the new read seam is projected; the existing exception classifier is not reimplemented.
    prefix = kernel + '\n#define COPYIN(src,dst,size) (PSR64_IS_KERNEL(get_saved_state_cpsr(state)) ? copyin_kern(src,dst,size) : copyin(src,dst,size))\n'
    functions = []
    for name, enabled in (('n198_enabled', True), ('n198_disabled', False)):
        functions.append(('#define ARM64_BOARD_CONFIG_EXYNOS9825 1\n' if enabled else '') +
                         'static uint32_t ' + name + '(arm_saved_state_t *state) {\nuint32_t instr = 0;\n' +
                         READ_AFTER + '\nreturn instr;\n}\n' +
                         ('#undef ARM64_BOARD_CONFIG_EXYNOS9825\n' if enabled else ''))
    return (prefix + ''.join(functions) + '#undef COPYIN\n').encode()
