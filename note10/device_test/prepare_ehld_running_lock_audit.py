"""Prepare the opt-in EHLD running-scalar ctrl-lock audit."""
import hashlib
import re
import shutil
from pathlib import Path

TARGET = 'drivers/soc/samsung/debug/exynos-ehld.c'
KCONFIG = 'kernel/power/Kconfig'
OPTION = 'CONFIG_NOTE10_EHLD_RUNNING_LOCK_AUDIT'
BLOCK = (b'\nconfig NOTE10_EHLD_RUNNING_LOCK_AUDIT\n'
         b'\tbool "EHLD running scalar lock audit"\n'
         b'\tdepends on NOTE10_EHLD_LOCK_AUDIT\n'
         b'\tdepends on NOTE10_EHLD_IRQSAVE_AUDIT\n'
         b'\tdefault n\n')
HELPER = (b'static void exynos_ehld_set_running(struct exynos_ehld_ctrl *ctrl, int running)\n'
          b'{\n'
          b'\tunsigned long flags;\n'
          b'\n'
          b'\traw_spin_lock_irqsave(&ctrl->lock, flags);\n'
          b'\tctrl->ehld_running = running;\n'
          b'\traw_spin_unlock_irqrestore(&ctrl->lock, flags);\n'
          b'}\n\n')


def sha(data):
    return hashlib.sha256(data).hexdigest()


def _replace_unique(raw, old, new, label):
    if raw.count(old) != 1:
        raise ValueError('expected exactly one ' + label)
    return raw.replace(old, new, 1)


def _function(raw, signature):
    if raw.count(signature) != 1:
        raise ValueError('function signature must be unique: ' + signature.decode())
    start = raw.index(signature)
    brace = raw.index(b'{', start)
    depth = 0
    for pos in range(brace, len(raw)):
        if raw[pos:pos + 1] == b'{':
            depth += 1
        elif raw[pos:pos + 1] == b'}':
            depth -= 1
            if depth == 0:
                return start, pos + 1, raw[start:pos + 1]
    raise ValueError('unterminated function: ' + signature.decode())


def transform(raw):
    start_signature = b'static int exynos_ehld_start_cpu(unsigned int cpu)'
    stop_signature = b'static int exynos_ehld_stop_cpu(unsigned int cpu)'
    start_at, start_end, start_fn = _function(raw, start_signature)
    stop_at, stop_end, stop_fn = _function(raw, stop_signature)
    if start_at >= stop_at:
        raise ValueError('start_cpu must precede stop_cpu in the pinned source')
    if start_fn.count(b'ctrl->ehld_running = 1;') != 1 or stop_fn.count(b'ctrl->ehld_running = 0;') != 1:
        raise ValueError('start/stop scalar stores must each occur once in their actual function')
    if b'exynos_ehld_set_running(' in raw:
        raise ValueError('running setter already exists')
    start_fn = _replace_unique(start_fn, b'ctrl->ehld_running = 1;', b'exynos_ehld_set_running(ctrl, 1);', 'start store')
    stop_fn = _replace_unique(stop_fn, b'ctrl->ehld_running = 0;', b'exynos_ehld_set_running(ctrl, 0);', 'stop store')
    return raw[:start_at] + HELPER + start_fn + raw[start_end:stop_at] + stop_fn + raw[stop_end:]


def validate_transform(baseline, prepared):
    """Fail closed unless prepared bytes are the exact approved production transform."""
    if not isinstance(baseline, bytes) or not isinstance(prepared, bytes):
        raise ValueError('EHLD source transform inputs must be bytes')
    if transform(baseline) != prepared:
        raise ValueError('prepared EHLD source differs from exact production transform')
    return True


def validate_map(source, baseline_map):
    source = Path(source)
    if not isinstance(baseline_map, dict) or len(baseline_map) != 78:
        raise ValueError('exact v46 78-source baseline map required')
    if TARGET not in baseline_map or KCONFIG not in baseline_map:
        raise ValueError('v46 baseline map lacks target pair')
    for name, digest in baseline_map.items():
        rel = Path(name)
        if rel.is_absolute() or rel.as_posix() != name or '..' in rel.parts or not re.fullmatch(r'[0-9a-f]{64}', digest):
            raise ValueError('invalid v46 source map entry')
        path = source / rel
        if path.is_symlink() or not path.is_file():
            raise ValueError('v46 source missing or unsafe: ' + name)
    actual = {name: sha((source / name).read_bytes()) for name in baseline_map}
    if actual != baseline_map:
        raise ValueError('v46 source baseline differs')
    return source


def prepare(source, enabled, baseline_map):
    if enabled is not True:
        raise ValueError('v47 preparation requires explicit opt-in')
    source = validate_map(source, baseline_map)
    target = source / TARGET
    kconfig = source / KCONFIG
    old_target = target.read_bytes()
    old_kconfig = kconfig.read_bytes()
    # Validate all inputs and transformations before either file is changed.
    if old_kconfig.count(b'config NOTE10_EHLD_RUNNING_LOCK_AUDIT') or BLOCK.strip() in old_kconfig:
        raise ValueError('running-lock option already exists')
    new_target = transform(old_target)
    validate_transform(old_target, new_target)
    new_kconfig = old_kconfig + BLOCK
    if new_target.count(b'exynos_ehld_set_running(ctrl, 1);') != 1 or new_target.count(b'exynos_ehld_set_running(ctrl, 0);') != 1:
        raise ValueError('running setter patch did not produce one start and one stop call')
    target.write_bytes(new_target)
    kconfig.write_bytes(new_kconfig)
    return {
        'ehld_running_lock_audit': True,
        'ehld_running_lock_audit_version': 1,
        'ehld_running_lock_baseline_sha256': {name: baseline_map[name] for name in (TARGET, KCONFIG)},
        'ehld_running_lock_prepared_sha256': {TARGET: sha(new_target), KCONFIG: sha(new_kconfig)},
    }


def snapshot(source, output, baseline_map):
    source = Path(source)
    output = Path(output)
    if output.exists() or output.is_symlink():
        raise ValueError('running-lock snapshot output already exists or unsafe')
    # Require the exact input set and ensure every entry remains a regular file.
    if not isinstance(baseline_map, dict) or len(baseline_map) != 78 or TARGET not in baseline_map or KCONFIG not in baseline_map:
        raise ValueError('exact v46 78-source map required')
    for name in baseline_map:
        rel = Path(name)
        path = source / rel
        if rel.is_absolute() or rel.as_posix() != name or '..' in rel.parts or path.is_symlink() or not path.is_file():
            raise ValueError('unsafe snapshot input: ' + name)
    expected = set(baseline_map)
    output.mkdir(parents=True)
    for name in sorted(expected):
        src = source / name
        dst = output / name
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dst)
    if {p.relative_to(output).as_posix() for p in output.rglob('*') if p.is_file()} != expected:
        raise ValueError('running-lock snapshot file set differs')
    actual = {name: sha((output / name).read_bytes()) for name in sorted(expected)}
    changed = {name for name in expected if actual[name] != baseline_map[name]}
    if changed != {TARGET, KCONFIG}:
        raise ValueError('running-lock snapshot must change exactly EHLD source and Kconfig')
    return actual
