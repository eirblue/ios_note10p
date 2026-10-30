"""Focused collector tests for CPR/CPT generation lineage."""
import argparse
import json
import re
from pathlib import Path

from collect_reservation import (
    cpu_pm_transaction_predecessor,
    decode_cpu_pm_roundtrip_observation,
)
from decode_reservation import checksum


IDENTITY = 'a' * 32


def frame(tag, values):
    body = ' '.join(f'{key}={value}' for key, value in values.items())
    return f'{tag} {body} checksum={checksum(body.encode("ascii")):08x}'


def pair_log(generation, identity=IDENTITY):
    common = {
        'id': identity, 'copy': 0, 'generation': generation, 'attempted': 1,
        'roster': 6, 'roster_valid': 1, 'pre': 1, 'post': 1,
        'enter_calls': 1, 'exit_calls': 1, 'enter_ok': 1, 'exit_ok': 1,
        'daif': 1, 'timer': 1, 'gic': 1, 'ehld_before': 1,
        'ehld_after': 1, 'context': 1, 'passed': 1, 'error': 0,
        'enter_error': 0, 'exit_error': 0,
    }
    lines = []
    for copy in (0, 1):
        common['copy'] = copy
        lines.append(frame('N10CPR1', common))
    return '\n'.join(lines) + '\n'


def terminal_log(generation, identity=IDENTITY):
    common = {
        'id': identity, 'copy': 0, 'generation': generation,
        'attempted': 1, 'recorded': 1, 'completed': 1,
        'caller_invoked': 1, 'stage': 2, 'outer_error': 0,
        'helper_error': -16, 'probe_error': -16,
        'enter_calls': 0, 'exit_calls': 0,
        'enter_error': 0, 'exit_error': 0,
    }
    lines = []
    for copy in (0, 1):
        common['copy'] = copy
        lines.append(frame('N10CPT1', common))
    return '\n'.join(lines) + '\n'


def require_rejection(label, call):
    try:
        call()
    except ValueError:
        return {'case': label, 'accepted': False}
    raise AssertionError(f'{label} was accepted')


def run_cases():
    pair = decode_cpu_pm_roundtrip_observation(pair_log(1), IDENTITY, 2)
    if pair.get('pair_observed') is not True or pair.get('evaluation_item') != {
        'required': True, 'status': 'passed'
    }:
        raise AssertionError('completed generation 2 did not bind CPR generation 1')

    terminal = decode_cpu_pm_roundtrip_observation(terminal_log(7), IDENTITY, 8)
    if (terminal.get('terminal_failure_observed') is not True or
            terminal.get('pair_passed') is not False or
            terminal.get('evaluation_item') != {'required': True, 'status': 'failed'}):
        raise AssertionError('completed generation 8 did not preserve terminal generation 7')

    wrapped = decode_cpu_pm_roundtrip_observation(pair_log(0xffffffff), IDENTITY, 1)
    if wrapped.get('pair_observed') is not True:
        raise AssertionError('completed generation 1 did not wrap to predecessor UINT32_MAX')

    cases = [
        {'case': 'strict-success', 'accepted': True},
        {'case': 'terminal-failure', 'accepted': True},
        {'case': 'generation-wrap', 'accepted': True},
    ]
    for invalid in (0, True, -1, 0x100000000):
        cases.append(require_rejection(
            f'invalid-completed-{invalid!r}',
            lambda invalid=invalid: decode_cpu_pm_roundtrip_observation(
                pair_log(1), IDENTITY, invalid)))

    cases.append(require_rejection(
        'stale-transaction-generation',
        lambda: decode_cpu_pm_roundtrip_observation(pair_log(1), IDENTITY, 3)))
    cases.append(require_rejection(
        'identity-mismatch',
        lambda: decode_cpu_pm_roundtrip_observation(pair_log(1, 'b' * 32), IDENTITY, 2)))

    corrupt_lines = pair_log(1).splitlines()
    body, digest = corrupt_lines[0].rsplit('checksum=', 1)
    corrupt_lines[0] = body + 'checksum=' + ('0' if digest[0] != '0' else '1') + digest[1:]
    corrupt = '\n'.join(corrupt_lines) + '\n'
    cases.append(require_rejection(
        'checksum-mismatch',
        lambda: decode_cpu_pm_roundtrip_observation(corrupt, IDENTITY, 2)))
    return cases


def decode_saved_log(path, completed):
    text = Path(path).read_text(encoding='utf-8', errors='replace')
    matches = re.findall(r'\bN10CPR1 id=([0-9a-f]{32})\b', text)
    if len(matches) != 2 or matches[0] != matches[1]:
        raise AssertionError('saved log does not contain exactly two same-identity CPR frames')
    result = decode_cpu_pm_roundtrip_observation(text, matches[0], completed)
    if result.get('pair_observed') is not True:
        raise AssertionError('saved raw CPR pair was not strictly accepted')
    generation = cpu_pm_transaction_predecessor(completed)
    return {
        'decoded': True,
        'pair_observed': True,
        'frame_count': len(matches),
        'completed_generation': completed,
        'transaction_generation': generation,
        'hardware_operations': False,
        'v50_result_modified': False,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--saved-log', type=Path)
    parser.add_argument('--completed-generation', type=int, default=2)
    parser.add_argument('--proof-output', type=Path)
    args = parser.parse_args()

    result = {'passed': True, 'cases': run_cases(), 'saved_log_proof': None}
    if args.saved_log:
        result['saved_log_proof'] = decode_saved_log(args.saved_log, args.completed_generation)
    if args.proof_output:
        args.proof_output.parent.mkdir(parents=True, exist_ok=True)
        args.proof_output.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(result, sort_keys=True))


if __name__ == '__main__':
    main()
