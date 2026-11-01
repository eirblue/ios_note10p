"""Strict selected-boot KAT frames; checksum is damage detection, not identity proof."""
import re
from decode_reservation import checksum

ANSWER = 'ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad'
KEYS = ('id', 'copy', 'phase', 'status', 'driver_match', 'computed', 'digest')


def decode(text, identity):
    if not isinstance(identity, str) or not re.fullmatch('[0-9a-f]{32}', identity):
        raise ValueError('invalid expected build evidence ID')
    lines = [line[line.index('N10SHA1'):] for line in text.splitlines() if 'N10SHA1' in line]
    if len(lines) != 2:
        raise ValueError('exactly two current-boot KAT frames required')
    copies, facts = set(), None
    for line in lines:
        match = re.fullmatch(r'N10SHA1 ([^\r\n\x00]{1,319}) checksum=([0-9a-f]{8})', line)
        if not match or not match[1].isascii() or checksum(match[1].encode('ascii')) != int(match[2], 16):
            raise ValueError('KAT frame checksum/format invalid')
        pairs = [word.split('=') for word in match[1].split(' ')]
        if any(len(pair) != 2 for pair in pairs) or tuple(p[0] for p in pairs) != KEYS:
            raise ValueError('KAT schema/order differs')
        row = dict(pairs)
        if row['id'] != identity or row['phase'] != 'late-init':
            raise ValueError('KAT build/phase mismatch')
        if row['copy'] not in ('0', '1') or row['copy'] in copies:
            raise ValueError('KAT duplicate/invalid copy')
        if (not re.fullmatch(r'0|-[1-9][0-9]{0,3}', row['status']) or
                int(row['status']) < -4095 or row['driver_match'] not in ('0', '1') or
                row['computed'] not in ('0', '1') or not re.fullmatch('[0-9a-f]{64}', row['digest'])):
            raise ValueError('KAT values invalid')
        status, computed, driver = int(row['status']), row['computed'] == '1', row['driver_match'] == '1'
        if ((computed and not driver) or (status == 0 and (not computed or row['digest'] != ANSWER)) or
                (not computed and row['digest'] != '0'*64) or
                (computed and status != 0 and (status != -74 or row['digest'] == ANSWER))):
            raise ValueError('KAT contradictory facts')
        copies.add(row.pop('copy'))
        if facts is not None and row != facts:
            raise ValueError('KAT copies disagree')
        facts = row
    return dict(observed=True, passed=int(facts['status']) == 0,
                status=int(facts['status']), build_evidence_id=identity,
                driver='sha256-generic' if facts['driver_match'] == '1' else None,
                computed=facts['computed'] == '1', digest=facts['digest'],
                runtime_observation_scope='single selected-boot call',
                physical_safety_proven=False, xnu_executed=False)
