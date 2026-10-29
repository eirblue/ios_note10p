"""Focused checksum, pair, identity and admission decoder cases."""
import argparse
import hashlib
import json
from pathlib import Path

from decode_cpu_pm_roundtrip import SCHEMA, TAG, decode
from decode_reservation import checksum

HERE = Path(__file__).resolve().parent
CASES = ('valid-pair', 'missing-copy', 'duplicate-copy', 'copy-mismatch',
         'wrong-id', 'wrong-generation', 'bad-checksum', 'bad-prefix',
         'bad-schema', 'blocked-not-completed', 'blocked-with-api-counts',
         'enter-count-mismatch', 'exit-count-mismatch', 'failed-postcondition',
         'extra-frame', 'malformed-frame')
IDENTITY = 'a' * 32
GENERATION = 9
BASE = {
    'id': IDENTITY, 'copy': 0, 'generation': GENERATION, 'attempted': 1,
    'roster': 6, 'roster_valid': 1, 'pre': 1, 'post': 1,
    'enter_calls': 1, 'exit_calls': 1, 'enter_ok': 1, 'exit_ok': 1,
    'daif': 1, 'timer': 1, 'gic': 1, 'ehld_before': 1,
    'ehld_after': 1, 'context': 1, 'passed': 1, 'error': 0,
    'enter_error': 0, 'exit_error': 0,
}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def EXPECTED():
    outcomes = []
    for case in CASES:
        accepted = case == 'valid-pair'
        normalized = ({'generation': GENERATION, 'attempted': 1, 'roster_count': 6,
                       'enter_calls': 1, 'exit_calls': 1, 'postconditions_passed': True}
                      if accepted else None)
        outcomes.append({'case': case, 'accepted': accepted, 'normalized': normalized})
    return outcomes


def frame(row, corrupt=False, malformed=False):
    body = ' '.join(f'{key}={row[key]}' for key in SCHEMA)
    digest = checksum(body.encode('ascii'))
    if corrupt:
        digest ^= 1
    if malformed:
        return TAG + ' ' + body + ' checksum=bad'
    return f'{TAG} {body} checksum={digest:08x}'


def input_vector(case):
    rows = _rows(case)
    if case == 'bad-prefix':
        text = 'N10CPMRT1X ' + frame(rows[0])
    elif case == 'bad-schema':
        raw = frame(rows[0]).replace('copy=0', 'generation=9', 1)
        text = raw + '\n' + frame(rows[1])
    elif case == 'bad-checksum':
        text = frame(rows[0], corrupt=True) + '\n' + frame(rows[1])
    elif case == 'malformed-frame':
        text = frame(rows[0], malformed=True) + '\n' + frame(rows[1])
    else:
        text = '\n'.join(frame(row) for row in rows)
    return json.dumps({'case': case, 'text': text}, sort_keys=True,
                      separators=(',', ':')).encode() + b'\n'


def _rows(case):
    first, second = dict(BASE), dict(BASE)
    second['copy'] = 1
    if case == 'missing-copy': return [first]
    if case == 'duplicate-copy': second['copy'] = 0
    if case == 'copy-mismatch': second['gic'] = 0
    if case == 'wrong-id': first['id'] = 'b' * 32; second['id'] = 'b' * 32
    if case == 'wrong-generation': first['generation'] += 1; second['generation'] += 1
    if case == 'blocked-not-completed':
        for row in (first, second):
            row.update(attempted=0, enter_calls=0, exit_calls=0,
                       enter_ok=0, exit_ok=0, passed=0)
    if case == 'blocked-with-api-counts':
        for row in (first, second): row['attempted'] = 0
    if case == 'enter-count-mismatch':
        for row in (first, second): row['enter_calls'] = 0
    if case == 'exit-count-mismatch':
        for row in (first, second): row['exit_calls'] = 2
    if case == 'failed-postcondition':
        for row in (first, second): row['ehld_after'] = 0
    if case == 'extra-frame':
        third = dict(BASE); third['copy'] = 2
        return [first, second, third]
    return [first, second]


def run(output):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    outcomes, generated, logs, transcripts = [], {}, {}, {}
    for case in CASES:
        vector = input_vector(case)
        text = json.loads(vector)['text']
        expected = case == 'valid-pair'
        try:
            result = decode(text, IDENTITY, GENERATION)
            accepted = True
        except (ValueError, TypeError, KeyError):
            result, accepted = None, False
        if accepted is not expected:
            raise AssertionError('decoder outcome differs: ' + case)
        if expected and result != {'generation': GENERATION, 'attempted': 1,
                                  'roster_count': 6, 'enter_calls': 1,
                                  'exit_calls': 1, 'postconditions_passed': True}:
            raise AssertionError('decoder normalized result differs')
        transcript = ('PASS|' if accepted else 'REJECT|') + case
        generated_raw = vector
        code = output / (case + '.json'); code.write_bytes(generated_raw)
        log = output / (case + '.log'); log.write_text(transcript + '\n', encoding='utf8', newline='\n')
        generated[case], logs[case], transcripts[case] = sha(code.read_bytes()), sha(log.read_bytes()), transcript
        outcomes.append({'case': case, 'accepted': accepted,
                         'normalized': result if expected else None})
    proof = {'schema_version': 1, 'passed': True, 'hardware_verified': False,
             'cases': list(CASES), 'case_results': outcomes,
             'case_transcripts': transcripts, 'generated_sha256': generated,
             'logs_sha256': logs, 'decoder_sha256': sha((HERE / 'decode_cpu_pm_roundtrip.py').read_bytes()),
             'harness_sha256': sha(Path(__file__).read_bytes())}
    (output / 'result.json').write_text(json.dumps(proof, indent=2) + '\n', encoding='utf8', newline='\n')
    return proof


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(run(args.output), sort_keys=True))
