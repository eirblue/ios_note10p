"""Strict paired CPU_PM enter/exit diagnostic frame decoder."""
import re

from decode_reservation import checksum

TAG = 'N10CPR1'
SCHEMA = ('id', 'copy', 'generation', 'attempted', 'roster', 'roster_valid',
          'pre', 'post', 'enter_calls', 'exit_calls', 'enter_ok', 'exit_ok',
          'daif', 'timer', 'gic', 'ehld_before', 'ehld_after', 'context',
          'passed', 'error', 'enter_error', 'exit_error')
SUCCESS = ('attempted', 'roster_valid', 'pre', 'post', 'enter_calls',
           'exit_calls', 'enter_ok', 'exit_ok', 'daif', 'timer', 'gic',
           'ehld_before', 'ehld_after', 'context', 'passed')


def decode(text, identity, generation):
    if not isinstance(identity, str) or not re.fullmatch(r'[0-9a-f]{32}', identity):
        raise ValueError('invalid CPU_PM evidence identity')
    if type(generation) is not int or not 0 < generation <= 0xffffffff:
        raise ValueError('invalid completed CPU_PM generation')
    for line in text.splitlines():
        for match in re.finditer(TAG, line):
            if not re.match(TAG + r' ', line[match.start():]):
                raise ValueError('malformed CPU_PM roundtrip prefix')
    frames = []
    for match in re.finditer(TAG + r' ([^\r\n]*)', text):
        tail = match.group(1)
        frame = re.fullmatch(r'(.*?) checksum=([0-9a-f]{8})', tail)
        if not frame:
            raise ValueError('malformed CPU_PM roundtrip frame')
        body, digest = frame.groups()
        pairs = [part.split('=', 1) for part in body.split(' ')]
        if any(len(pair) != 2 for pair in pairs) or tuple(pair[0] for pair in pairs) != SCHEMA:
            raise ValueError('CPU_PM roundtrip frame schema differs')
        if pairs[0][1] != identity or checksum(body.encode('ascii')) != int(digest, 16):
            raise ValueError('CPU_PM roundtrip identity/checksum differs')
        row = {'id': identity}
        for key, value in pairs[1:]:
            if not re.fullmatch(r'(?:0|[1-9][0-9]*)', value):
                raise ValueError('CPU_PM roundtrip numeric syntax')
            number = int(value)
            if number > 0xffffffff:
                raise ValueError('CPU_PM roundtrip integer width')
            row[key] = number
        if row['copy'] not in (0, 1):
            raise ValueError('CPU_PM roundtrip copy index')
        frames.append(row)
    if len(frames) != 2 or [row['copy'] for row in frames] != [0, 1]:
        raise ValueError('CPU_PM roundtrip frame cardinality')
    first, second = frames
    if {key: value for key, value in first.items() if key != 'copy'} != {
            key: value for key, value in second.items() if key != 'copy'}:
        raise ValueError('CPU_PM roundtrip copies differ')
    if first['generation'] != generation:
        raise ValueError('CPU_PM roundtrip generation differs')
    # A blocked admission is not an executed pair and can never pass this row.
    if any(first[key] != 1 for key in SUCCESS):
        raise ValueError('CPU_PM pair was not admitted and completed successfully')
    if first['roster'] != 6 or any(first[key] != 0 for key in ('error', 'enter_error', 'exit_error')):
        raise ValueError('CPU_PM roundtrip postconditions failed')
    return {'generation': generation, 'attempted': 1, 'roster_count': 6,
            'enter_calls': 1, 'exit_calls': 1, 'postconditions_passed': True}
