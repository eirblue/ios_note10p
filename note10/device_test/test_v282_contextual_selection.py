"""One private-input regression of the complete changed selection interface."""
import copy
import re
import v282_native_prepare as p

def refused(raw,table):
    try:p.restore_inputs(raw,table)
    except (ValueError,KeyError):return True
    return False

def predicate(raw,linked):
    assert type(raw)is dict and type(linked)is str and raw['schema']=='note10-v281-seal-raw-v1'and raw['complete']is False and raw['rejection']=='unique exact contextual function'
    assert p.sha(linked.encode())==raw['linked_nm_sha256']
    original=p.sha(repr(raw).encode());table=p.scoped.reader.linked_symbols(linked)
    assert len(table[p.RESTORE])==494 and len(table[p.CALLER])==1 and len(raw['bodies'])==21
    caller=table[p.CALLER][0];caller_id=format(caller['address'],'016x')+':'+str(caller['bytes'])
    words=p.instruction_words(raw['bodies'][caller_id]);call=max(words)-8;word=words[call];offset=word&0x3ffffff
    if offset&0x2000000:offset-=0x4000000
    target=call+4*offset
    expected=[row for row in table[p.RESTORE]if row['address']==target]
    assert len(expected)==1 and expected[0]['bytes']==12 and expected[0]['kind']=='t'
    expected=expected[0];helper_id=format(target,'016x')+':12'
    context=p.restore_inputs(raw,table);joined=context['provenance']
    assert context['call']==call and context['helper_address']==target and joined['linked_address']==target and joined['ordinal']==expected['ordinal']and joined['object']==p.OWNER_TARGET and joined['binding']=='LOCAL'and joined['frame']['bytes']==0
    assert context['caller_rows'][-3][0]==call and len(context['helper_rows'])==3 and all(type(k)is type(v)is int for k,v in context['words'].items())
    # Unrelated local definitions stay in the full table; no name/first/size fallback.
    bad=dict(table);bad[p.RESTORE]=[row for row in table[p.RESTORE]if row is not expected]
    assert refused(raw,bad)
    bad=dict(table);bad[p.RESTORE]=table[p.RESTORE]+[dict(expected)]
    assert refused(raw,bad)
    for size in (12,16):
        bad=dict(table);bad['unrelated_same_entry']=[dict(expected,bytes=size)]
        assert refused(raw,bad)
    bad=dict(table);bad[p.RESTORE]=[dict(row,address=target-4,bytes=16)if row is expected else row for row in table[p.RESTORE]]
    assert refused(raw,bad)
    bad=copy.deepcopy(raw);del bad['bodies'][helper_id];assert refused(bad,table)
    item=raw['objects'][p.OWNER_TARGET]
    for key,alter in [('nm',lambda text:re.sub(r'(?m)^'+p.RESTORE+r' t ([0-9a-f]+) c$',lambda m:p.RESTORE+' t '+format(int(m[1],16)+4,'x')+' c',text)),('usage',lambda text:re.sub(r'(?m)^([^\n]*:'+p.RESTORE+r'\t)0\tstatic$',r'\g<1>16\tstatic',text)),('usage',lambda text:re.sub(r'(?m)^([^\n]*init\.c)(:[^\n]*:'+p.RESTORE+r'\t0\tstatic)$',r'\g<1>.wrong\g<2>',text)),('elf',lambda text:re.sub(r'(?m)(DEFAULT\s+)1(\s+'+p.RESTORE+r'\s*)$',r'\g<1>2\g<2>',text))]:
        bad=copy.deepcopy(raw);changed=alter(item[key]);assert changed!=item[key]
        bad['objects'][p.OWNER_TARGET][key]=changed;assert refused(bad,table)
    bad=copy.deepcopy(raw)
    bad['bodies'][caller_id]=re.sub(r'(?m)(^\s*'+format(call,'x')+r':\s+[0-9a-f]{8}\s+)bl\b',r'\g<1>b',bad['bodies'][caller_id])
    assert bad['bodies'][caller_id]!=raw['bodies'][caller_id]and refused(bad,table)
    owner=table[p.OWNER][0];owner_id=format(owner['address'],'016x')+':'+str(owner['bytes'])
    bad=copy.deepcopy(raw)
    def second_caller(match):
        address=int(match[1],16);encoding=0x94000000+(((target-address)//4)&0x3ffffff)
        return match[1]+': '+format(encoding,'08x')+' bl '+format(target,'x')+' <'+p.RESTORE+'>'
    bad['bodies'][owner_id]=re.sub(r'(?m)^\s*([0-9a-f]+):\s+[0-9a-f]{8}\s+bl\s+[^\n]+',second_caller,bad['bodies'][owner_id],count=1)
    assert bad['bodies'][owner_id]!=raw['bodies'][owner_id]and refused(bad,table)
    assert raw['complete']is False and p.sha(repr(raw).encode())==original
    return dict(passed=True,groups=1,variants=1,assertions=1)
