"""v73 bounded shash stream/state preparation and current-cycle frame decoder."""
import hashlib
import json
from pathlib import Path
import re

HERE = Path(__file__).resolve().parent
PROFILE = 'sha256-stream-state-v1'
API_PINS = {
    'include/crypto/hash.h': '4a094bf7b8059469306762a8e9c653cda9bf2bb84b2cd23f9a0fd912617520ec',
    'crypto/shash.c': '0f4c16dc648eedd16f8eadbbf6877d2b15c57d68d303e05d4859519d9e0ae8ea',
    'crypto/sha256_generic.c': 'c85f77c45bc469f402311c9bf2a0ea4c456c64675ecf60fafa0421db25cad96f',
}
SOURCES = ('sha256_stream_state.py', 'sha256_stream_state.c', 'sha256_stream_composition.c',
           'sha256_stream_vectors.json', 'build_sha256_stream_state.py',
           'test_sha256_stream_state.py', 'sha256_stream_fixture.c')
KEYS = ('id', 'cycle', 'case', 'copy', 'len', 'split', 'statesize', 'status', 'driver_match',
        'streamed', 'exported', 'imported', 'resumed', 'direct', 'restored')


def require(value, message):
    if not value: raise ValueError(message)


def vectors():
    value = json.loads((HERE/'sha256_stream_vectors.json').read_text(encoding='utf8'))
    require(set(value) == {'schema', 'recipe', 'vectors'} and value['schema'] == 1 and
            value['recipe'] == 'byte[i]=(37*i+11)&255', 'closed NEW vector recipe')
    rows = value['vectors']
    require(len(rows) == 6, 'six new vectors only')
    for i, (row, length) in enumerate(zip(rows, (55, 56, 63, 64, 65, 129))):
        require(set(row) == {'case', 'length', 'split', 'digest'} and
                all(type(row[k]) is int for k in ('case', 'length', 'split')) and
                (row['case'], row['length'], row['split']) == (i, length, 65 if length > 65 else 55) and
                re.fullmatch('[0-9a-f]{64}', row['digest']), 'exact bounded vector')
    return rows


def vector_header():
    rows = []
    for row in vectors():
        answer = ','.join('0x'+row['digest'][i:i+2] for i in range(0, 64, 2))
        rows.append('    {%d,%d,{%s}}' % (row['length'], row['split'], answer))
    return ('struct n10_stream_vector { unsigned int length, split; unsigned char answer[32]; };\n'
            'static const struct n10_stream_vector n10_stream_vectors[] = {\n'+',\n'.join(rows)+'\n};\n').encode('ascii')


def install(source, identity):
    from builtin_init_route import install as install_baseline
    for name, digest in API_PINS.items():
        require(hashlib.sha256((source/name).read_bytes()).hexdigest() == digest, 'pinned real shash API: '+name)
    result = install_baseline(source, identity)
    replacements = {
        'drivers/misc/note10_sha256_kat.c': (HERE/'sha256_stream_composition.c').read_bytes(),
        'drivers/misc/sha256_stream_state.c': (HERE/'sha256_stream_state.c').read_bytes(),
        'drivers/misc/sha256_stream_vectors.h': vector_header(),
    }
    kconfig = source/'drivers/misc/note10_sha256_kat.Kconfig'
    kconfig.write_bytes(kconfig.read_bytes()+b'''
config NOTE10_SHA256_STREAM_STATE
\tbool "Note10 bounded SHA256 incremental and opaque-state observation"
\tdepends on NOTE10_SHA256_KAT_RECOVERY && NOTE10_BUILTIN_INIT_ROUTE
\tdefault n
\thelp
\t  Six new messages, same-provider incremental and export/import state.
\t  Existing independent recovery worker; no portable state ABI claim.
''')
    for name, data in replacements.items(): (source/name).write_bytes(data)
    # Original abc source may exist as an inherited input file, but the new
    # composition never includes it. No canonical abc execution or new initcall.
    return {name: hashlib.sha256((source/name).read_bytes()).hexdigest() for name in (*result, *replacements)}


def decode(text, identity, cycle):
    from decode_reservation import checksum
    require(re.fullmatch('[0-9a-f]{32}', identity) and re.fullmatch('[0-9a-f]{32}', cycle), 'expected stream build/cycle')
    table = vectors()
    lines = [line for line in text.splitlines() if 'N10SHASTREAM1' in line]
    require(len(lines) == 12, 'exactly twelve current stream frames')
    rows, boots, order = {}, set(), []
    for line in lines:
        match = re.search(r'N10BOOTLINK2 boot=([0-9a-f]{32}) N10SHASTREAM1 ([^\r\n\x00]{1,511}) checksum=([0-9a-f]{8})$', line)
        require(match and checksum(match[2].encode('ascii')) == int(match[3], 16), 'stream frame format/checksum')
        pairs = [word.split('=') for word in match[2].split(' ')]
        require(all(len(x) == 2 for x in pairs) and tuple(x[0] for x in pairs) == KEYS, 'closed stream schema/order')
        row = dict(pairs); boots.add(match[1])
        require(row['id'] == identity and row['cycle'] == cycle, 'current stream build/cycle differs')
        for key in ('case', 'copy', 'len', 'split', 'statesize'):
            require(re.fullmatch('0|[1-9][0-9]{0,9}', row[key]), 'bounded numeric stream field')
            row[key] = int(row[key])
        require(0 <= row['case'] < 6 and row['copy'] in (0, 1) and row['statesize'] <= 0xffffffff and
                re.fullmatch('0|-[1-9][0-9]{0,3}', row['status']) and int(row['status']) >= -4095, 'stream status/index bounds')
        row['status'] = int(row['status'])
        for key in ('driver_match', 'streamed', 'exported', 'imported', 'resumed'):
            require(row[key] in ('0', '1'), 'stream boolean'); row[key] = int(row[key])
        v = table[row['case']]
        require((row['len'], row['split']) == (v['length'], v['split']) and
                all(re.fullmatch('[0-9a-f]{64}', row[k]) for k in ('direct', 'restored')), 'new message/digest shape')
        require(row['resumed'] <= row['imported'] <= row['exported'] <= row['streamed'] <= row['driver_match'], 'API progress order')
        require((row['streamed'] or row['direct'] == '0'*64) and (row['resumed'] or row['restored'] == '0'*64), 'uncomputed outputs must be zero')
        if row['streamed'] and row['direct'] != v['digest']:
            require(row['status'] == -74 and row['exported'] == 0, 'direct mismatch must stop this case')
        if row['resumed'] and row['status'] != 0:
            require(row['status'] == -74 and row['restored'] != v['digest'], 'completed resume error facts differ')
        if row['status'] == 0:
            require(row['resumed'] == 1 and 0 < row['statesize'] <= 4096 and
                    row['direct'] == row['restored'] == v['digest'], 'successful stream/state facts differ')
        key = (row['case'], row.pop('copy'))
        require(key not in rows, 'duplicate stream case/copy')
        rows[key] = row; order.append(key)
    require(order == [(i, j) for i in range(6) for j in (0, 1)], 'single ordered new batch')
    require(len(boots) == 1 and '0'*32 not in boots and all(rows[i, 0] == rows[i, 1] for i in range(6)), 'agreeing copies and single boot')
    require(len({r['statesize'] for r in rows.values()}) == 1, 'same transform state size across batch')
    return dict(observed=True, passed=all(rows[i, 0]['status'] == 0 for i in range(6)),
                boot_identity=next(iter(boots)), cases=[rows[i, 0] for i in range(6)],
                scope='new Linux same-provider incremental/export-import batch',
                portable_state_ABI_proven=False, xnu_executed=False)


def decode_selected(data, banner, identity, cycle):
    from builtin_init_profile import decode as baseline_decode
    observation_decoder = lambda text, rid: decode(text, rid, cycle)
    clipped, observation = baseline_decode(data, banner, identity, cycle, digest_decoder=observation_decoder, digest_marker=b'N10SHASTREAM1')
    require(observation['kat']['boot_identity'] == observation['boot_identity'], 'stream/route/recovery boot identity differs')
    return clipped, observation
