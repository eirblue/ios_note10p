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
TERMINAL_TAG = 'N10CPT1'
TERMINAL_SCHEMA = ('id','copy','generation','attempted','recorded','completed',
                   'caller_invoked','stage','outer_error','helper_error','probe_error',
                   'enter_calls','exit_calls','enter_error','exit_error')
SIGNED_TERMINAL = {'outer_error','helper_error','probe_error','enter_error','exit_error'}


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


def decode_terminal(text, identity, generation):
    """Decode failure-only terminal state; never satisfy the paired-call pass row."""
    if not isinstance(identity,str) or not re.fullmatch(r'[0-9a-f]{32}',identity):
        raise ValueError('invalid CPU_PM terminal identity')
    if type(generation) is not int or not 0<generation<=0xffffffff:
        raise ValueError('invalid CPU_PM terminal generation')
    for line in text.splitlines():
        for match in re.finditer(TERMINAL_TAG,line):
            if not re.match(TERMINAL_TAG+r' ',line[match.start():]):
                raise ValueError('malformed CPU_PM terminal prefix')
    rows=[]
    for match in re.finditer(TERMINAL_TAG+r' ([^\r\n]*)',text):
        framed=re.fullmatch(r'(.*?) checksum=([0-9a-f]{8})',match.group(1))
        if not framed: raise ValueError('malformed CPU_PM terminal frame')
        body,digest=framed.groups()
        pairs=[part.split('=',1) for part in body.split(' ')]
        if any(len(pair)!=2 for pair in pairs) or tuple(pair[0] for pair in pairs)!=TERMINAL_SCHEMA:
            raise ValueError('CPU_PM terminal schema differs')
        if pairs[0][1]!=identity or checksum(body.encode('ascii'))!=int(digest,16):
            raise ValueError('CPU_PM terminal identity/checksum differs')
        row={'id':identity}
        for key,value in pairs[1:]:
            pattern=r'-?(?:0|[1-9][0-9]*)' if key in SIGNED_TERMINAL else r'(?:0|[1-9][0-9]*)'
            if not re.fullmatch(pattern,value): raise ValueError('CPU_PM terminal numeric syntax')
            number=int(value)
            if key in SIGNED_TERMINAL:
                if not -(1<<31)<=number<(1<<31): raise ValueError('CPU_PM terminal signed width')
            elif number>0xffffffff: raise ValueError('CPU_PM terminal integer width')
            row[key]=number
        if row['copy'] not in (0,1): raise ValueError('CPU_PM terminal copy index')
        rows.append(row)
    if len(rows)!=2 or [row['copy'] for row in rows]!=[0,1]:
        raise ValueError('CPU_PM terminal frame cardinality')
    first,second=rows
    if {k:v for k,v in first.items() if k!='copy'}!={k:v for k,v in second.items() if k!='copy'}:
        raise ValueError('CPU_PM terminal copies differ')
    if first['generation']!=generation: raise ValueError('CPU_PM terminal generation differs')
    if any(first[k]!=1 for k in ('recorded','completed')):
        raise ValueError('CPU_PM terminal record is incomplete')
    stage=first['stage']; called=first['caller_invoked']
    if stage not in range(6) or called not in (0,1): raise ValueError('CPU_PM terminal stage/caller invalid')
    if stage in (0,1):
        if (first['attempted'] or called or first['helper_error'] or first['enter_calls'] or
            first['exit_calls'] or first['enter_error'] or first['exit_error'] or
            not (first['outer_error'] or first['probe_error'])):
            raise ValueError('CPU_PM pre-helper terminal state differs')
    elif stage==2:
        if (first['attempted'] not in (0,1) or not called or first['enter_calls'] or first['exit_calls'] or
            first['enter_error'] or first['exit_error'] or not first['helper_error'] or
            (first['attempted']==0 and first['helper_error'] not in (-103,-114))):
            raise ValueError('CPU_PM admission terminal state differs')
    elif stage==3:
        if first['attempted']!=1 or not called or first['enter_calls']!=1 or first['exit_calls'] or not first['enter_error'] or first['exit_error'] or not first['helper_error']:
            raise ValueError('CPU_PM enter-failure terminal state differs')
    elif stage==4:
        if first['attempted']!=1 or not called or first['enter_calls']!=1 or first['exit_calls']!=1 or first['enter_error'] or not first['exit_error'] or not first['helper_error']:
            raise ValueError('CPU_PM exit-failure terminal state differs')
    else:
        if (first['attempted']!=1 or not called or first['enter_calls']!=1 or first['exit_calls']!=1 or
            first['enter_error'] or first['exit_error'] or
            not (first['helper_error'] or first['outer_error'] or first['probe_error'])):
            raise ValueError('CPU_PM postcondition terminal state differs')
    return {'generation':generation,'attempted':first['attempted'],'recorded':True,'completed':True,
            'caller_invoked':bool(called),'stage':stage,'pair_passed':False,
            'outer_error':first['outer_error'],'helper_error':first['helper_error'],
            'probe_error':first['probe_error'],
            'enter_calls':first['enter_calls'],'exit_calls':first['exit_calls'],
            'enter_error':first['enter_error'],'exit_error':first['exit_error']}
