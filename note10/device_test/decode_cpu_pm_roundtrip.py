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

COUNTS_TAG = 'N10CPN1'
COUNTS_SCHEMA = ('id','copy','generation','attempted','roster','roster_valid',
                 'enter_calls','exit_calls','enter_nr_calls','exit_nr_calls',
                 'enter_seen','exit_seen','capture_valid','conflict','enter_error',
                 'exit_error','error','caller_invoked','terminal_stage',
                 'terminal_helper_error','terminal_probe_error','terminal_outer_error')
SIGNED_COUNTS = {'enter_error','exit_error','error','terminal_helper_error',
                 'terminal_probe_error','terminal_outer_error'}


def decode_counts(text, identity, generation, pair=None, terminal=None):
    """Decode the versioned count companion independently from the CPR row."""
    if not isinstance(identity, str) or not re.fullmatch(r'[0-9a-f]{32}', identity):
        raise ValueError('invalid CPU_PM count identity')
    if type(generation) is not int or not 0 < generation <= 0xffffffff:
        raise ValueError('invalid completed CPU_PM generation')
    for line in text.splitlines():
        for match in re.finditer(COUNTS_TAG, line):
            if not re.match(COUNTS_TAG + r' ', line[match.start():]):
                raise ValueError('malformed CPU_PM count prefix')
    rows=[]
    for match in re.finditer(COUNTS_TAG + r' ([^\r\n]*)', text):
        framed=re.fullmatch(r'(.*?) checksum=([0-9a-f]{8})',match.group(1))
        if not framed: raise ValueError('malformed CPU_PM count frame')
        body,digest=framed.groups()
        pairs=[part.split('=',1) for part in body.split(' ')]
        if any(len(item)!=2 for item in pairs) or tuple(item[0] for item in pairs)!=COUNTS_SCHEMA:
            raise ValueError('CPU_PM count schema differs')
        if pairs[0][1]!=identity or checksum(body.encode('ascii'))!=int(digest,16):
            raise ValueError('CPU_PM count identity/checksum differs')
        row={'id':identity}
        for key,value in pairs[1:]:
            pattern=r'(?:0|-?[1-9][0-9]*)' if key in SIGNED_COUNTS else r'(?:0|[1-9][0-9]*)'
            if not re.fullmatch(pattern,value): raise ValueError('CPU_PM count numeric syntax')
            number=int(value)
            if key in SIGNED_COUNTS:
                if not -(1<<31)<=number<(1<<31): raise ValueError('CPU_PM count signed width')
            elif number>0xffffffff: raise ValueError('CPU_PM count integer width')
            row[key]=number
        if row['copy'] not in (0,1): raise ValueError('CPU_PM count copy index')
        rows.append(row)
    if len(rows)!=2 or [row['copy'] for row in rows]!=[0,1]:
        raise ValueError('CPU_PM count frame cardinality')
    first,second=rows
    if {k:v for k,v in first.items() if k!='copy'}!={k:v for k,v in second.items() if k!='copy'}:
        raise ValueError('CPU_PM count copies differ')
    if first['generation']!=generation: raise ValueError('CPU_PM count generation differs')
    bounded={
        'attempted':(0,1),'roster':(0,6),'roster_valid':(0,1),
        'enter_calls':(0,1),'exit_calls':(0,1),'enter_nr_calls':(0,6),
        'exit_nr_calls':(0,6),'enter_seen':(0,1),'exit_seen':(0,1),
        'capture_valid':(0,1),'conflict':(0,1),'caller_invoked':(0,1),
        'terminal_stage':(0,5),
    }
    if any(not lo<=first[key]<=hi for key,(lo,hi) in bounded.items()):
        raise ValueError('CPU_PM count value outside field domain')
    if pair is not None:
        pair_map={'generation':'generation','attempted':'attempted','roster':'roster_count',
                  'enter_calls':'enter_calls','exit_calls':'exit_calls'}
        if any(first[companion]!=pair[pair_key] for companion,pair_key in pair_map.items()):
            raise ValueError('CPU_PM companion differs from successful CPR frame')
        if first['roster_valid']!=1:raise ValueError('CPU_PM companion roster validity differs from CPR')
        if terminal is not None: raise ValueError('CPU_PM pair and terminal state conflict')
    if terminal is not None:
        for key in ('generation','attempted','caller_invoked','stage','helper_error',
                    'probe_error','outer_error','enter_calls','exit_calls','enter_error','exit_error'):
            companion_key={'stage':'terminal_stage','helper_error':'terminal_helper_error',
                           'probe_error':'terminal_probe_error','outer_error':'terminal_outer_error'}.get(key,key)
            if first[companion_key]!=terminal[key]:
                raise ValueError('CPU_PM companion differs from terminal frame')
    success=(pair is not None and first['attempted']==1 and first['roster']==6 and
             first['roster_valid']==1 and first['enter_calls']==1 and first['exit_calls']==1 and
             first['enter_nr_calls']==6 and first['exit_nr_calls']==6 and
             first['enter_seen']==1 and first['exit_seen']==1 and first['capture_valid']==1 and
             first['conflict']==0 and all(first[k]==0 for k in ('enter_error','exit_error','error',
                 'terminal_helper_error','terminal_probe_error','terminal_outer_error')) and
             first['caller_invoked']==1 and first['terminal_stage']==0)
    return {'generation':generation,'companion_valid':True,'counts_passed':bool(success),
            'enter_nr_calls':first['enter_nr_calls'],'exit_nr_calls':first['exit_nr_calls'],
            'roster_count':first['roster'],'conflict':bool(first['conflict']),
            'terminal':terminal is not None}


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
