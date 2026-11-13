"""New-only nm multiplicity/selected admission/address-resolution regression cases."""
import v236_nm_multiplicity as p

COUNTS=dict(groups=1,variants=10,assertions=10)


def run():
    cases=[]
    def accepted(name,call):cases.append((name,call,True))
    def rejected(name,call):cases.append((name,call,False))
    nm='strcmp T 1000 10\nstrcmp_alias T 1000 10\nOUTLINED_FUNCTION_0 t 3000 8\nOUTLINED_FUNCTION_0 t 4000 c\n'
    table=p.linked_symbols(nm);symbol=p.extent(table,'strcmp')
    accepted('all duplicate unselected rows survive with original identity',lambda:[(r['kind'],r['address'],r['bytes'],r['ordinal'])for r in table['OUTLINED_FUNCTION_0']]==[('t',0x3000,8,2),('t',0x4000,12,3)])
    accepted('selected extent keeps bound same-extent aliases',lambda:symbol==dict(symbol='strcmp',address=0x1000,bytes=16,aliases=['strcmp','strcmp_alias']))
    dis='0000000000001000 <strcmp>:\n 1000: 94000000 bl 3004 <OUTLINED_FUNCTION_0+0x4>\n 1004: 54000000 b.eq 4008 <OUTLINED_FUNCTION_0+0x8>\n 1008: b4000000 cbz x0, 5000\n 100c: d65f03c0 ret\n'
    def addresses():
        proof=p.transfers(dis,symbol,table);edges=proof['external_transfers']
        return [[(r['name'],r['address'],r['offset'])for r in row['resolved_records']]for row in edges]==[
            [('OUTLINED_FUNCTION_0',0x3000,4)],[('OUTLINED_FUNCTION_0',0x4000,8)],[]]and edges[2]['unresolved']is True
    accepted('both local definitions resolve at their own addresses',addresses)
    def identical_rows():
        duplicates=p.linked_symbols(nm+'OUTLINED_FUNCTION_0 t 3000 8\n')
        records=p.transfers(dis,symbol,duplicates)['external_transfers'][0]['resolved_records']
        return len(records)==2 and [r['ordinal']for r in records]==[2,4]
    accepted('even identical duplicate records are not overwritten',identical_rows)
    rejected('ambiguous selected symbol rejected',lambda:p.extent(p.linked_symbols(nm+'strcmp T 6000 10\n'),'strcmp'))
    rejected('missing selected symbol rejected',lambda:p.extent(p.linked_symbols('other t 3000 8\n'),'strcmp'))
    rejected('present optional selected symbol must also be unique',lambda:p.extent(p.linked_symbols('__of_find_property t 3000 8\n__of_find_property t 4000 8\n'),'__of_find_property'))
    def ambiguous_admission():
        linked=''.join(name+' T '+format(0x10000+i*16,'x')+' 8\n'for i,name in enumerate(p.MANDATORY))+'of_get_cpu_node T 90000 8\n'
        raw=dict(schema=p.RAW_SCHEMA,objects={name:{}for name in p.NEW_OBJECTS},linked_nm_sha256=p.sha(linked.encode()),assembly={},tools=[])
        return p.verify(raw,dict(objects={name:{}for name in p.REUSED_OBJECTS},linked_nm=linked))
    rejected('full reader rejects selected ambiguity before object join',ambiguous_admission)
    def aliases():
        duplicates=p.linked_symbols(nm+'strcmp_alias t 7000 8\n')
        return p.extent(duplicates,'strcmp')['aliases']==['strcmp','strcmp_alias']and len(duplicates['strcmp_alias'])==2
    accepted('alias label binding does not discard its other local definition',aliases)
    def selected_join():
        obj='arch/arm64/kernel/setup.o';tu='/ci/work/source/arch/arm64/kernel/setup.c'
        cmd=('cmd_'+obj+' := clang-14 -fstack-usage -fno-strict-aliasing -o '+obj+' -c '+tu+'\nsource_'+obj+' := '+tu+'\n').encode()
        su=tu+':1:arch_match_cpu_phys_id\t0\tstatic\n'
        elf=' [ 1] .text PROGBITS 0000000000000000 000040 000008 00 AX 0 0 4\n 1: 0000000000000000 8 FUNC GLOBAL DEFAULT 1 arch_match_cpu_phys_id\n'
        item=dict(command=cmd.decode(),command_sha256=p.sha(cmd),stack_usage=su,stack_sha256=p.sha(su.encode()),stack_relative='arch/arm64/kernel/setup.su',elf_sections_and_symbols=elf,elf_evidence_sha256=p.sha(elf.encode()))
        multi=p.linked_symbols(nm+'arch_match_cpu_phys_id T 8000 8\n')
        selected={'arch_match_cpu_phys_id':p.selected_symbol(multi,'arch_match_cpu_phys_id')}
        return p.object_proof(obj,item,('arch_match_cpu_phys_id',),selected)['arch_match_cpu_phys_id']['linked_address']==0x8000
    accepted('unique selected view joins unchanged ELF and SU proof API',selected_join)
    for name,call,wanted in cases:
        try:actual=call()is not False
        except(ValueError,KeyError,TypeError):actual=False
        if actual is not wanted:raise AssertionError(name)
    if len(cases)!=COUNTS['variants']:raise AssertionError('new multiplicity case count')
    return dict(COUNTS)
