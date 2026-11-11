"""Exact, default-off real USER64 exception read overlay and one genuine provider."""
import difflib
import hashlib
import json
from pathlib import Path
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


def read(path):
    require(path.resolve() == path and not path.is_symlink() and path.is_file() and
            0 < path.stat().st_size <= CAP, 'ordinary bounded source required')
    with path.open('rb') as stream:
        raw = stream.read(CAP + 1)
    require(len(raw) == path.stat().st_size <= CAP, 'source extent differs')
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


def admit_binding(current):
    observation = current['producer'].get('user_exception_fetch')
    require(observation == proof() and current['bindings'].get('user_exception_fetch') ==
            hashlib.sha256(json.dumps(observation, sort_keys=True, separators=(',', ':')).encode()).hexdigest(),
            'exact opt-in caller/header/provider binding required')
    rows = [r for r in current['inventory'] if r['source'] == REL]
    require(len(rows) == 1 and rows[0]['source_sha256'] == POSTIMAGE and rows[0]['component'] == 'osfmk' and
            rows[0]['kind'] == 'C', 'one new caller inventory owner required')
    provider = current['dependencies'].get(UNIT)
    require(provider == dict(path=str(ROOT / SOURCE), source_sha256=PINS[SOURCE]), 'genuine current provider identity required')


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
