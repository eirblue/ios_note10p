"""Eight new local ownership predicates; no old suite or external processes."""


def run(adapter,parser):
    instructions=[('mrs','x22, sp_el0'),('cbz','x0, 1054'),('ldr','w8, [x22, #16]'),('adrp','x23, 9000'),('add','x23, x23, #0x28'),('add','w8, w8, #0x1'),('str','w8, [x22, #16]'),
        ('bl','2000'),('bl','3000'),('ldr','w8, [x22, #16]'),('subs','w8, w8, #0x1'),('str','w8, [x22, #16]'),('bl','4000'),('ret',''),('ret','')]
    # Internal targets are hexadecimal instruction addresses, as in objdump.
    instructions[1]=('cbz','x0, 1038')
    rows=[(0x1000+4*i,op,args)for i,(op,args)in enumerate(instructions)]
    edges={0x101c:dict(names=['n231_capture_cpu_observation'],target=0x2000),0x1020:dict(names=['n233_capture_cpu_node_consistency'],target=0x3000),0x1030:dict(names=['preempt_schedule'],target=0x4000)}
    def changed(index,op,args):
        copy=list(rows);copy[index]=(copy[index][0],op,args);return copy
    cases=[('valid-early-reject-and-owned-release',rows,edges,True),
        ('capture-bypasses-acquisition',changed(1,'cbz','x0, 101c'),edges,False),
        ('owned-return-before-release',changed(8,'ret',''),{k:v for k,v in edges.items()if k!=0x1020},False),
        ('second-acquisition',changed(8,'b','1008'),{k:v for k,v in edges.items()if k!=0x1020},False),
        ('second-release',changed(12,'b','1024'),{k:v for k,v in edges.items()if k!=0x1030},False),
        ('scheduler-before-release',rows,{**edges,0x101c:dict(names=['preempt_schedule'],target=0x2000)},False),
        ('unrecognized-counter-write',changed(6,'str','w9, [x22, #16]'),edges,False),
        ('counter-base-clobber-before-access',changed(1,'mov','x22, xzr'),edges,False)]
    progress=dict(groups=1,variants=8,assertions=8,attempted_variants=0,completed_variants=0,completed_assertions=0,case_names=[],host_processes=0,old_tests_replayed=0)
    try:
        for index,(name,body,calls,accepted)in enumerate(cases,1):
            progress.update(attempted_variants=index,failing_case_index=index,failing_case_name=name)
            try:result=adapter.analyze(body,calls,parser)
            except ValueError:
                if accepted:raise
            else:
                if not accepted:raise AssertionError('invalid ownership CFG accepted')
                if not result['local_guard_ownership_proven']or result['whole_frontdoor_stack_bound_proven']:raise AssertionError('incorrect proof claims')
            progress['completed_variants']+=1;progress['completed_assertions']+=1;progress['case_names'].append(name)
        progress.update(failing_case_index=None,failing_case_name=None);return progress
    except BaseException as error:error.fixture_progress=progress;raise
