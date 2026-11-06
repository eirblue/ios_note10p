"""One NEW pure-Python batch for immutable133 PID1 compatibility only."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
sys.dont_write_bytecode = True
import v134_pid1_compat as compat

ROOT = Path(__file__).resolve().parents[2]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    out = args.output.resolve()
    if out.exists() or args.output.is_symlink():
        parser.error('fresh NEW-only output required')
    out.mkdir(parents=True)
    result = dict(schema='note10-v134-PID1-compat-NEW-test-v1', passed=False,
                  test_process_invocations=1, compiler_invocations=0,
                  old_tests_replayed=0, device_commands=0, cases=[])

    def case(name, condition):
        if not condition:
            raise AssertionError(name)
        result['cases'].append(name)

    def rejects(function, *values):
        try:
            function(*values)
        except ValueError:
            return True
        return False

    try:
        inputs = [(ROOT / ('note10/device_test/' + name)).read_bytes() for name in
                  ('v133_build.py', 'v130_loader.c', 'v133_cycle.py')]
        binding = compat.derive_binding(*inputs)
        case('actual-source-derived-PID1-132-native133-mismatch',
             binding['pid1_prefix'] == 'N10XNU132' and binding['native_prefix'] == 'N10XNU133')
        case('changed-producer-source-refused', rejects(compat.derive_binding, inputs[0] + b'\n', *inputs[1:]))
        case('changed-loader-source-refused', rejects(compat.derive_binding, inputs[0], inputs[1] + b'\n', inputs[2]))
        case('changed-consumer-source-refused', rejects(compat.derive_binding, *inputs[:2], inputs[2] + b'\n'))
        identity, cycle = 'a' * 32, 'b' * 32

        def pid(stage, tag='132', ident=identity, cyc=cycle):
            return '[ 1.000] N10XNU' + tag + ' id=' + ident + ' cycle=' + cyc + ' stage=' + stage + '\n'

        native = '[ 2.000] N10XNU133 id=' + identity + ' '
        text = pid('begin') + pid('kexec-load-once') + pid('kexec-reboot-once')
        text += native + 'stage=score-power errno=-16 owner=synthetic-master\n'
        text += native + 'score reason=pm-get item=0 state=0 value=-16 aux=0 owner=synthetic-master\n'
        text += native + 'iommu controller=synthetic-controller active=1 runtime=0 effective=0\n'
        text += native + 'final_qualified=1 EL1_preserved=1 actual_XNU_pending=1\n'
        observed = compat.decode(text.encode(), identity, cycle, binding)
        case('actual-mismatch-admits-exact-PID1-identity', observed['identity_bound_PID1_begin_observed'])
        case('PID1-counts-and-native133-remain-separate',
             observed['internal_kexec_load_attempts_observed'] == 1 and
             observed['internal_kexec_REBOOT_attempts_observed'] == 1 and
             len(observed['gate_refusals']) == len(observed['score_refusal_details']) == 1 and
             observed['iommu_refusal_states'][0]['effective'] == 0)
        case('final-hook-never-promotes-physical-entry-or-epoch',
             observed['final_hook_qualified_observed'] and not observed['physical_XNU_entry_established'] and
             not observed['full_XNU_boot_established'] and not observed['log_reboot_epoch_proven'])
        for name, wrong in [('wrong-identity', pid('begin', ident='c' * 32)),
                            ('wrong-cycle', pid('begin', cyc='d' * 32)),
                            ('wrong-producer', pid('begin', tag='133'))]:
            empty = compat.decode(wrong.encode(), identity, cycle, binding)
            case(name + '-not-admitted', not empty['identity_bound_PID1_begin_observed'] and
                 empty['internal_kexec_load_attempts_observed'] is None)
        mixed = compat.decode((pid('begin') + pid('kexec-load-once', tag='133')).encode(), identity, cycle, binding)
        case('native-tag-cannot-supply-PID1-load', mixed['internal_kexec_load_attempts_observed'] == 0 and
             'kexec-load-once' not in mixed['PID1_stages_observed'])
        wrong_native = text.replace('N10XNU133 id=', 'N10XNU132 id=')
        case('PID1-tag-cannot-supply-native-kernel-proof',
             not compat.decode(wrong_native.encode(), identity, cycle, binding)['gate_refusals'])
        case('another-begin-refuses-epoch-merge', compat.decode((text + pid('begin')).encode(), identity, cycle, binding)['ambiguous_begin'])
        case('later-other-identity-begin-refuses-merge', compat.decode((text + pid('begin', ident='e' * 32)).encode(), identity, cycle, binding)['ambiguous_begin'])
        bad = dict(binding, pid1_prefix='N10XNU131')
        case('wrong-source-binding-refused', rejects(compat.decode, text.encode(), identity, cycle, bad))
        case('malformed-identity-refused', rejects(compat.decode, text.encode(), 'bad', cycle, binding))
        case('empty-log-refused', rejects(compat.decode, b'', identity, cycle, binding))
        case('oversized-log-refused', rejects(compat.decode, b'x' * (compat.MAX_LOG_BYTES + 1), identity, cycle, binding))
        bounded = pid('begin') + ''.join(native + 'stage=score-power errno=-16 owner=synthetic-' + str(i) + '\n' for i in range(12))
        bounded += native + 'score reason=pm-get item=256 state=0 value=-16 aux=0 owner=synthetic-master\n'
        bounded += native + 'score reason=pm-get item=0 state=4294967296 value=-16 aux=0 owner=synthetic-master\n'
        bounded += native + 'score reason=pm-get item=0 state=0 value=2147483648 aux=0 owner=synthetic-master\n'
        bounded += native + 'score reason=pm-get item=0 state=0 value=-16 aux=4294967296 owner=synthetic-master\n'
        bounded += native + 'stage=score-power errno=-99999 owner=synthetic-master\n'
        limited = compat.decode(bounded.encode(), identity, cycle, binding)
        case('bounded-eight-refusals-and-native-numeric-widths', len(limited['gate_refusals']) == 8 and not limited['score_refusal_details'])
        case('same-input-deterministic-no-epoch-promotion', compat.decode(text.encode(), identity, cycle, binding) == observed)
        result.update(passed=True, binding=binding,
                      source_sha256={name: hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in
                                     ('note10/device_test/v134_pid1_compat.py', 'note10/device_test/test_v134_pid1_compat.py')})
    finally:
        (out/'result.json').write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8', newline='\n')
    print(json.dumps({'passed': result['passed'], 'NEW_cases': len(result['cases'])}))


if __name__ == '__main__':
    main()
