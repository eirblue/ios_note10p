"""Fresh recovery-only build: empty initramfs has no compression choice."""
import hashlib
from pathlib import Path
from types import FunctionType

HERE = Path(__file__).resolve().parent
if hashlib.sha256((HERE / 'v293_recovery_prepare.py').read_bytes()).hexdigest() != '1b414bde3719793ab06661f5ed0b859c23d75f15027166bf856da09aedc453c2':
    raise ValueError('immutable v293 producer')
import v293_recovery_prepare as retained

ROOT = HERE.parents[1]
WORKFLOW = '.github/workflows/note10-v294-recovery-only.yml'
JOB = 'v294-recovery-only'
OUTPUT = ROOT / 'note10/private/v294-ci-recovery-only'
SETTINGS = dict(retained.SETTINGS, INITRAMFS_COMPRESSION_NONE='n', LOCALVERSION='"-v294-recovery-only"')
CONTEXT_SCHEMA = 'note10-v294-recovery-only-public-input-v1'
require = retained.require
recipient = retained.recipient


def source_pins():
    pins = retained.source_pins()
    pins.pop(retained.WORKFLOW)
    for name in ('v294_recovery_prepare.py', 'test_v294_empty_initramfs.py'):
        path = 'note10/device_test/' + name
        pins[path] = retained.p.sha(retained.p.ordinary(ROOT / path))
    pins[WORKFLOW] = retained.p.sha(retained.p.ordinary(ROOT / WORKFLOW))
    return pins


def public_context(head, passed):
    retained.p.hexid(head, 40)
    require(set(passed) == {'passed', 'groups', 'variants', 'assertions', 'result_sha256'}
            and passed['passed'] is True
            and tuple(passed[k] for k in ('groups', 'variants', 'assertions')) == (1, 2, 2),
            'new empty-initramfs config cases only')
    retained.p.hexid(passed['result_sha256'])
    return dict(schema=CONTEXT_SCHEMA, source_head=head, source_sha256=source_pins(),
                new_fixture_PASS=passed, old_tests_replayed=False)


def metadata_code(function, replacements):
    # Only these outer identity literals differ; no recursive code rewriting.
    constants = function.__code__.co_consts
    require(all(constants.count(key) == 1 for key in replacements), 'exact inherited metadata literals')
    return function.__code__.replace(co_consts=tuple(replacements.get(value, value) if type(value) is str else value
                                                    for value in constants))


_ENV = dict(retained.__dict__, WORKFLOW=WORKFLOW, JOB=JOB, OUTPUT=OUTPUT,
            SETTINGS=SETTINGS, source_pins=source_pins, public_context=public_context,
            CONTEXT_SCHEMA=CONTEXT_SCHEMA, __doc__=__doc__)
run_build = FunctionType(metadata_code(retained.run_build, {
    'note10-v293-recovery-only-build-v1': 'note10-v294-recovery-only-build-v1',
    'v293': 'v294'}), _ENV, 'run_build', retained.run_build.__defaults__)
seal = FunctionType(metadata_code(retained.seal, {
    'note10-v293-recovery-only-sealed-members-v1': 'note10-v294-recovery-only-sealed-members-v1'}),
                    _ENV, 'seal', retained.seal.__defaults__)
_ENV.update(run_build=run_build, seal=seal)
main = FunctionType(retained.main.__code__, _ENV, 'main', retained.main.__defaults__)


if __name__ == '__main__':
    main()
