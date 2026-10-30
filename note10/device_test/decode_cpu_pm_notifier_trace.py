"""Strict scalar N10CPD1 companion; independent of the existing CPR/CPN verdicts."""
import re
from decode_reservation import checksum

TAG = 'N10CPD1'
SCHEMA = ('id', 'copy', 'generation', 'transaction', 'version', 'roster', 'phases', 'conflict', 'valid',
          'en', 'er', 'ee', 're', 'xn', 'xr', 'xe', 'rx')
ORDER = 0x123456


def decode(text, identity, generation, pair=None, counts=None, terminal=None):
    if not isinstance(identity, str) or not re.fullmatch(r'[0-9a-f]{32}', identity):
        raise ValueError('invalid dispatch identity')
    if type(generation) is not int or not 0 < generation <= 0xffffffff:
        raise ValueError('invalid dispatch transaction generation')
    # Independently re-derive prerequisite evidence from the same raw text.
    # Caller-supplied objects must match; fabricated success objects cannot pass.
    from decode_cpu_pm_roundtrip import decode as decode_pair, decode_counts, decode_terminal
    if 'N10CPT' in text:
        if 'N10CPR' in text:
            raise ValueError('dispatch pair/terminal conflict')
        actual_terminal = decode_terminal(text, identity, generation)
        actual_pair = None
        actual_counts = decode_counts(text, identity, generation, terminal=actual_terminal)
    else:
        actual_pair = decode_pair(text, identity, generation)
        actual_terminal = None
        actual_counts = decode_counts(text, identity, generation, pair=actual_pair)
    for provided, actual in ((pair, actual_pair), (counts, actual_counts), (terminal, actual_terminal)):
        if provided is not None and provided != actual:
            raise ValueError('dispatch prerequisite object differs')
    for line in text.splitlines():
        for occurrence in re.finditer('N10CPD', line):
            if not re.match(TAG + r' ', line[occurrence.start():]):
                raise ValueError('malformed dispatch prefix')
    rows = []
    for match in re.finditer(TAG + r' ([^\r\n]*)', text):
        frame = re.fullmatch(r'(.*?) checksum=([0-9a-f]{8})', match.group(1))
        if not frame:
            raise ValueError('malformed dispatch frame')
        body, digest = frame.groups()
        fields = [field.split('=', 1) for field in body.split(' ')]
        if any(len(field) != 2 for field in fields) or tuple(key for key, _ in fields) != SCHEMA:
            raise ValueError('dispatch field order/schema differs')
        if fields[0][1] != identity or checksum(body.encode('ascii')) != int(digest, 16):
            raise ValueError('dispatch identity/checksum differs')
        row = {'id': identity}
        for key, value in fields[1:]:
            if not re.fullmatch(r'(?:0|[1-9][0-9]*)', value):
                raise ValueError('dispatch integer syntax')
            number = int(value)
            if number > 0xffffffff:
                raise ValueError('dispatch integer width')
            row[key] = number
        rows.append(row)
    if len(rows) != 2 or [row['copy'] for row in rows] != [0, 1]:
        raise ValueError('dispatch copy cardinality')
    first, second = rows
    if {k: v for k, v in first.items() if k != 'copy'} != {k: v for k, v in second.items() if k != 'copy'}:
        raise ValueError('dispatch copies conflict')
    if first['generation'] != generation or first['version'] != 1:
        raise ValueError('dispatch version/generation differs')
    bounds = {'roster': 6, 'phases': 3, 'conflict': 1, 'valid': 1,
              'en': 6, 'er': 6, 'xn': 6, 'xr': 6,
              'ee': 0xffffff, 're': 0xffffff, 'xe': 0xffffff, 'rx': 0xffffff}
    if any(first[key] > limit for key, limit in bounds.items()):
        raise ValueError('dispatch field outside domain')
    success = (actual_pair is not None and actual_terminal is None and
               actual_counts.get('counts_passed') is True and first['transaction'] == generation and first['roster'] == 6 and
               first['phases'] == 3 and first['conflict'] == 0 and first['valid'] == 1 and
               all(first[key] == 6 for key in ('en', 'er', 'xn', 'xr')) and
               all(first[key] == ORDER for key in ('ee', 're', 'xe', 'rx')))
    return {'generation': generation, 'companion_valid': True, 'trace_passed': bool(success),
            'enter_entry_order': first['ee'], 'enter_return_order': first['re'],
            'exit_entry_order': first['xe'], 'exit_return_order': first['rx'],
            'conflict': bool(first['conflict']), 'terminal': actual_terminal is not None,
            'semantics': 'block identity/order and separate callback-field snapshot equality'}
