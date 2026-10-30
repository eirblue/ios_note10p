"""New fixed-leaf proof mutations over saved object bytes; never compile/run C."""
import argparse
import json
from pathlib import Path
import struct
import xnu_runtime_leaf as leaf
import xnu_runtime_scratch_stack as stack
from prepare_xnu_runtime_observation import sha

SYMBOL_MUTATIONS=('missing','duplicate','global','weak','writable','executable','not-allocated',
 'wrong-size','wrong-type','wrong-bytes','child-depth','out-of-bounds')
SOURCE_CASES=tuple('source-'+Path(n).name for n in (*leaf.SOURCE_PINS,leaf.RESERVE))
CASES=('both-leaves','both-path-estimate','generic-default','wrong-id','invalid-id','reserve-first-line',
 'reserve-extra-byte','same-object-id','missing-source','metadata-cannot-force-depth','truncated-object',
 'missing-planner-frame','missing-scratch-frame','unknown-callee','duplicate-frame','generic-caller-coverage',
 'planner-observer-id-relocation','planner-report-id-relocation','scratch-report-id-relocation','duplicate-reporter',
 'reporter-identity-valid','reporter-id-wrong-kind','reporter-id-wrong-target','reporter-id-outside-function',
 'reporter-id-duplicate-relocation','reporter-id-writable-target')+SOURCE_CASES+tuple(
    ('scratch-' if i==0 else 'planner-')+kind for i in range(2) for kind in SYMBOL_MUTATIONS)

def reject(call,*args):
    try:call(*args)
    except (ValueError,OSError):return True
    raise AssertionError('invalid fixed leaf/caller proof accepted')

def symbol_locations(raw,name):
    at=struct.unpack_from('<Q',raw,40)[0];stride,count=struct.unpack_from('<HH',raw,58)
    sections=[struct.unpack_from('<IIQQQQIIQQ',raw,at+i*stride) for i in range(count)]
    matches=[]
    for table in sections:
        if table[1]!=2:continue
        strings=sections[table[6]];names=raw[strings[4]:strings[4]+strings[5]]
        for pos in range(table[4],table[4]+table[5],table[9]):
            n,info,other,index,value,size=struct.unpack_from('<IBBHQQ',raw,pos)
            if names[n:].split(b'\0',1)[0].decode()!=name:continue
            section=sections[index]
            matches.append({'symbol':pos,'null_symbol':table[4],'section':at+index*stride,
              'bytes':section[4]+value,'section_size':section[5]})
    if len(matches)!=1:raise AssertionError('analysis input symbol missing/ambiguous')
    return matches[0]

def mutate_symbol(raw,name,kind):
    where=symbol_locations(raw,name);out=bytearray(raw);pos=where['symbol']
    if kind=='missing':struct.pack_into('<I',out,pos,0)
    elif kind=='duplicate':out[where['null_symbol']:where['null_symbol']+24]=out[pos:pos+24]
    elif kind in ('global','weak'):out[pos+4]=17 if kind=='global' else 33
    elif kind=='wrong-type':out[pos+4]=2
    elif kind in ('writable','executable','not-allocated'):
        flags=struct.unpack_from('<Q',out,where['section']+8)[0]
        flags=flags|1 if kind=='writable' else flags|4 if kind=='executable' else flags&~2
        struct.pack_into('<Q',out,where['section']+8,flags)
    elif kind=='wrong-size':struct.pack_into('<Q',out,pos+16,55)
    elif kind=='out-of-bounds':struct.pack_into('<Q',out,pos+8,where['section_size'])
    elif kind=='child-depth':struct.pack_into('<I',out,where['bytes']+4,1)
    else:out[where['bytes']+44]^=1
    return bytes(out)

def alter_reporter_id_relocation(raw,name,identity,kind="missing"):
    out=bytearray(raw);at=struct.unpack_from('<Q',raw,40)[0];stride,count=struct.unpack_from('<HH',raw,58)
    sections=[struct.unpack_from('<IIQQQQIIQQ',raw,at+i*stride) for i in range(count)]
    table=next(s for s in sections if s[1]==2);strings_section=sections[table[6]]
    names=raw[strings_section[4]:strings_section[4]+strings_section[5]]
    symbols=[struct.unpack_from('<IBBHQQ',raw,pos) for pos in range(table[4],table[4]+table[5],24)]
    function=next(s for s in symbols if names[s[0]:].split(b'\0',1)[0].decode()==name)
    for reloc in sections:
        if reloc[1]!=4 or reloc[7]!=function[3]:continue
        for pos in range(reloc[4],reloc[4]+reloc[5],24):
            offset,info,addend=struct.unpack_from('<QQq',raw,pos)
            if info&0xffffffff!=275 or not function[4]<=offset<function[4]+function[5]:continue
            target=symbols[info>>32]
            if not 0<target[3]<len(sections):continue
            section=sections[target[3]];where=section[4]+target[4]+addend
            if raw[where:where+33]!=identity.encode()+b'\0':continue
            if kind=='missing':struct.pack_into('<Q',out,pos+8,info&~0xffffffff)
            elif kind=='wrong-kind':struct.pack_into('<Q',out,pos+8,(info&~0xffffffff)|276)
            elif kind=='wrong-target':struct.pack_into('<q',out,pos+16,addend+1)
            elif kind=='outside-function':struct.pack_into('<Q',out,pos,function[4]+function[5])
            elif kind=='duplicate-relocation':
                other=reloc[4] if pos!=reloc[4] else reloc[4]+24
                out[other:other+24]=out[pos:pos+24]
            elif kind=='writable-target':
                section_header=at+target[3]*stride
                flags=struct.unpack_from('<Q',out,section_header+8)[0]
                struct.pack_into('<Q',out,section_header+8,flags|1)
            else:raise AssertionError('unknown identity mutation')
            return bytes(out)
    raise AssertionError('analysis input reporter ID relocation missing')

def identity_cases(obj,usage,sources,expected_id):
    results={}
    proof=leaf.prove(obj,sources,expected_id)
    if set(proof['reporter_id_relocations'])!=set(leaf.REPORTERS):raise AssertionError('all actual reporter ID references missing')
    results['reporter-identity-valid']=True
    compact=b'\n'.join(line.split(b'\t')[0]+b'\t1\tstatic' for line in usage.splitlines())+b'\n'
    generic=stack.calculate(compact,obj)
    if (generic['adt_levels']!=9 or generic['sequential_path_maximum'] is not False or
        set(generic['path_frames'])!={'generic'} or set(generic['path_frames']['generic'])!=set(generic['frames']) or
        not stack.PLANNER<={n.split('.')[0] for n in generic['path_frames']['generic']}):raise AssertionError('generic caller frames omitted or sequentiality assumed')
    results['generic-caller-coverage']=True
    for name,function in zip(('planner-observer-id-relocation','planner-report-id-relocation','scratch-report-id-relocation'),leaf.REPORTERS):
        results[name]=reject(leaf.prove,alter_reporter_id_relocation(obj,function,expected_id),sources,expected_id)
    results['duplicate-reporter']=reject(leaf.prove,mutate_symbol(obj,leaf.REPORTERS[0],'duplicate'),sources,expected_id)
    for kind in ('wrong-kind','wrong-target','outside-function','duplicate-relocation','writable-target'):
        results['reporter-id-'+kind]=reject(leaf.prove,alter_reporter_id_relocation(obj,leaf.REPORTERS[0],expected_id,kind),sources,expected_id)
    return results

def run(preflight,expected_id):
    obj=(preflight/'init.o').read_bytes();usage=(preflight/'init.su').read_bytes()
    sources={n:(preflight/'source'/n).read_bytes() for n in (*leaf.SOURCE_PINS,leaf.RESERVE)}
    proof=leaf.prove(obj,sources,expected_id);result=stack.calculate(usage,obj,sources,expected_id)
    if proof['adt_levels']!=1 or tuple(s['symbol'] for s in proof['symbols'])!=leaf.SYMBOLS:raise AssertionError('both fixed leaves not proven')
    if (set(result['path_frame_sums'])!={'scratch','planner'} or result['adt_levels']!=1 or
        result['physical_stack_safety_proven'] is not False or result['maximum_bound']!=8192 or
        result['minimum_margin']!=8192 or result['external_reserve']!=2048):raise AssertionError('path estimate scope/threshold differs')
    results={'both-leaves':True,'both-path-estimate':True}
    try:generic=stack.calculate(usage,obj)
    except ValueError as error:
        if 'budget/margin' not in str(error):raise
    else:
        if generic['adt_levels']!=9 or generic['leaf_proof'] is not None:raise AssertionError('generic estimate specialized without proof')
    results['generic-default']=True
    other='0'*32 if expected_id!='0'*32 else '1'*32
    results['wrong-id']=reject(leaf.prove,obj,sources,other)
    results['invalid-id']=reject(leaf.prove,obj,sources,'invalid')
    bad=dict(sources);bad[leaf.RESERVE]=b' '+bad[leaf.RESERVE]
    results['reserve-first-line']=reject(leaf.prove,obj,bad,expected_id)
    bad=dict(sources);bad[leaf.RESERVE]+=b'\n'
    results['reserve-extra-byte']=reject(leaf.prove,obj,bad,expected_id)
    bad=dict(sources);bad[leaf.RESERVE]=bad[leaf.RESERVE].replace(expected_id.encode(),other.encode(),1)
    results['same-object-id']=reject(leaf.prove,obj,bad,other)
    bad=dict(sources);bad.pop(next(iter(leaf.SOURCE_PINS)))
    results['missing-source']=reject(leaf.prove,obj,bad,expected_id)
    results['metadata-cannot-force-depth']=reject(stack.calculate,usage,obj,{'adt_levels':1},expected_id)
    results['truncated-object']=reject(leaf.prove,obj[:100],sources,expected_id)
    for name,function in (('missing-planner-frame','n10_observe_runtime_plan'),('missing-scratch-frame','n10_scratch_build')):
        altered=b'\n'.join(line for line in usage.splitlines() if (':'+function+'\t').encode() not in line)+b'\n'
        results[name]=reject(stack.calculate,altered,obj,sources,expected_id)
    results['unknown-callee']=reject(stack.calculate,usage+b'fixture:1:n10_rt_unknown\t0\tstatic\n',obj,sources,expected_id)
    line=next(row for row in usage.splitlines() if b':adt_node\t' in row)
    results['duplicate-frame']=reject(stack.calculate,usage+line+b'\n',obj,sources,expected_id)
    results.update(identity_cases(obj,usage,sources,expected_id))
    for name,source in zip(SOURCE_CASES,(*leaf.SOURCE_PINS,leaf.RESERVE)):
        altered=dict(sources);altered[source]+=b' /* changed call closure */'
        results[name]=reject(leaf.prove,obj,altered,expected_id)
    for i,symbol in enumerate(leaf.SYMBOLS):
        for kind in SYMBOL_MUTATIONS:
            name=('scratch-' if i==0 else 'planner-')+kind
            results[name]=reject(leaf.prove,mutate_symbol(obj,symbol,kind),sources,expected_id)
    return {n:results[n] for n in CASES},result,{'object_sha256':sha(obj),'usage_sha256':sha(usage),
      'source_sha256':{n:sha(raw) for n,raw in sources.items()}}

def validate_result(result):
    if (result.get('passed') is not True or result.get('fixture_only') is not True or
        result.get('artifact_analysis_only') is not True or result.get('canonical_suite_complete') is not True or result.get('compiler_executed') is not False or
        result.get('device_operations') is not False or tuple(result.get('cases',{}))!=CASES or
        not all(result['cases'].values()) or result.get('implementation_sha256')!=implementation_hashes()):
        raise ValueError('fixed leaf focused proof/scope/source differs')

def implementation_hashes():
    return {n:sha((Path(__file__).parent/n).read_bytes()) for n in ('xnu_runtime_leaf.py','xnu_runtime_scratch_stack.py','test_xnu_runtime_leaf.py')}

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--preflight',type=Path,required=True);parser.add_argument('--expected-id',required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();args.output.mkdir(parents=True,exist_ok=False)
    cases,estimate,inputs=run(args.preflight,args.expected_id)
    result=dict(passed=True,fixture_only=True,artifact_analysis_only=True,compiler_executed=False,
      device_operations=False,new_CI_acceptance=False,canonical_suite_complete=True,cases=cases,estimate=estimate,analysis_inputs=inputs,
      implementation_sha256=implementation_hashes(),unchanged_prior_suites_replayed=False)
    (args.output/'result.json').write_text(json.dumps(result,indent=2)+'\n')
if __name__=='__main__':main()
