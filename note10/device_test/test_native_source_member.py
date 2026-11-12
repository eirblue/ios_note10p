"""New synthetic source-member cases only; no real native inputs."""
import gzip
import hashlib
import io
import native_source_member as member


def run():
    assertions=0;variants=0;productions=[]
    def check(ok):
        nonlocal assertions
        assertions+=1
        if not ok:raise AssertionError('source-member fixture assertion '+str(assertions))
    def sources():
        return {role:dict(stream=io.BytesIO(raw),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
                for role,raw in (('kernel.mem',b'synthetic-kernel'*17),('adapter.mem',b'a'*16384))}
    def denied(rows):
        sink=io.BytesIO();progress={}
        try:member.produce(rows,sink,progress)
        except ValueError:
            productions.append(progress);return sink,progress
        raise AssertionError('mutated input accepted')

    # Group1: the actual writer and exact newc frame, decoded only for synthetic data.
    variants+=1;rows=sources();out=io.BytesIO();progress={};result=member.produce(rows,out,progress)
    productions.append(progress)
    raw=out.getvalue();archive=gzip.decompress(raw);offset=0;files={}
    while True:
        check(archive[offset:offset+6]==b'070701')
        fields=[int(archive[offset+6+i*8:offset+14+i*8],16) for i in range(13)]
        size,namesize=fields[6],fields[11];start=offset+110
        name=archive[start:start+namesize-1].decode('ascii');data_at=(start+namesize+3)//4*4
        data=archive[data_at:data_at+size];offset=(data_at+size+3)//4*4
        if name=='TRAILER!!!':break
        files[name]=data
    check(set(files)=={'n10','n10/kernel.mem','n10/adapter.mem'})
    check(files['n10/kernel.mem']==b'synthetic-kernel'*17 and files['n10/adapter.mem']==b'a'*16384)
    check(result['completed']is True and result['member_hash_complete']is True and result['compressions']==1)
    check(result['member_sha256']==hashlib.sha256(raw).hexdigest() and result['member_bytes']==len(raw))
    check(all(row['EOF_verified']is True and row['hash_complete']is True and row['passes']==1 for row in result['inputs'].values()))
    check(len(archive)%512==0 and not any(archive[offset:]) and raw[:4]==b'\x1f\x8b\x08\x00' and raw[4:8]==bytes(4))

    # Group2: each independent input refusal uses a new synthetic invocation.
    for mutation in ('hash','short','extra'):
        variants+=1;rows=sources();row=rows['kernel.mem']
        if mutation=='hash':row['sha256']='0'*64
        elif mutation=='short':row['stream']=io.BytesIO(b'x')
        else:row['stream']=io.BytesIO(b'synthetic-kernel'*17+b'x')
        _,progress=denied(rows)
        check(progress['completed']is False and progress['member_hash_complete']is False)
        check(progress['compressions']==1 and 'adapter.mem' not in progress['inputs'])

    # Group3: pre-read admission errors must leave both streams untouched.
    for mutation in ('role','extent'):
        variants+=1;rows=sources();streams=[row['stream'] for row in rows.values()]
        if mutation=='role':rows['wrong']=rows.pop('kernel.mem')
        else:rows['adapter.mem']['bytes']=16383
        out,progress=denied(rows)
        check(not progress and out.getvalue()==b'')
        check(all(stream.tell()==0 for stream in streams))

    # Group4: exact production arithmetic, with alignment-sensitive overflow.
    variants+=1;exact=member.fit(member.MEMBER_BUDGET)
    check(exact['fit']is True and exact['aligned_required_bytes']==member.SLOT_BYTES and exact['excess_bytes']==0)
    variants+=1;overflow=member.fit(member.MEMBER_BUDGET+1)
    check(overflow['fit']is False and overflow['excess_bytes']==4)
    return dict(groups=4,variants=variants,assertions=assertions,real_native_source_reads=0,old_tests_replayed=0,
                synthetic_production_calls=len(productions),synthetic_compressions=sum(row.get('compressions',0) for row in productions),
                synthetic_completed_members=sum(row.get('completed')is True for row in productions),
                synthetic_input_passes={role:sum(row.get('inputs',{}).get(role,{}).get('passes',0) for row in productions) for role in member.ROLES})
