"""New-only synthetic selected-OF evidence parser and bounded collector argv cases."""
from copy import deepcopy
import v235_of_call_evidence as p

COUNTS=dict(groups=1,variants=29,assertions=29)


def run():
    cases=[]
    def accepted(name,call):cases.append((name,call,True))
    def rejected(name,call):cases.append((name,call,False))
    target='arch/arm64/kernel/setup.o';source='/ci/work/source/arch/arm64/kernel/setup.c'
    cmd=('cmd_'+target+' := clang-14 -fstack-usage -fno-strict-aliasing -o arch/arm64/kernel/.tmp_setup.o -c '+source+'\nsource_'+target+' := '+source+'\n').encode()
    accepted('literal TU and actual tmp SU',lambda:p.translation_unit(cmd,target)['stack_relative']=='arch/arm64/kernel/.tmp_setup.su')
    rejected('source declaration mismatch',lambda:p.translation_unit(cmd.replace(b'source_arch/arm64/kernel/setup.o := /ci/work/source',b'source_arch/arm64/kernel/setup.o := /else/source'),target))
    rejected('relative remote TU',lambda:p.translation_unit(cmd.replace(b'/ci/work/source',b'work/source'),target))
    rejected('wrong compiler output',lambda:p.translation_unit(cmd.replace(b'.tmp_setup.o',b'other.o'),target))
    rejected('duplicate source declaration',lambda:p.translation_unit(cmd+('source_'+target+' := '+source+'\n').encode(),target))
    nm='arch_match_cpu_phys_id T 1000 8\nstrcmp T 2000 10\nstrcmp_alias T 2000 10\npreempt_schedule T 3000 8\n'
    table=p.linked_symbols(nm);symbol=p.extent(table,'strcmp')
    accepted('bounded range argv and bound aliases',lambda:p.command('/ci/work/objects/vmlinux',symbol)==['aarch64-linux-gnu-objdump','-d','--disassemble-zeroes','--start-address=0x2000','--stop-address=0x2010','/ci/work/objects/vmlinux'])
    rejected('relative ELF path',lambda:p.command('objects/vmlinux',symbol))
    rejected('unlisted symbol',lambda:p.command('/ci/work/objects/vmlinux',{**symbol,'symbol':'unknown'}))
    rejected('unaligned symbol extent',lambda:p.extent({'strcmp':dict(address=0x2000,bytes=7)},'strcmp'))
    rejected('duplicate linked symbol',lambda:p.linked_symbols(nm+'strcmp T 2000 10\n'))
    dis='0000000000002000 <strcmp_alias>:\n 2000: 14000001 b 2004 <strcmp+0x4>\n 2004: 54000020 b.eq 2008 <strcmp+0x8>\n 2008: b4000000 cbz x0, 2000 <strcmp>\n 200c: d65f03c0 ret\n'
    accepted('internal unconditional conditional and cbz',lambda:p.transfers(dis,symbol,table)['internal_branches']==3)
    external=dis.replace('b 2004 <strcmp+0x4>','b 3000 <preempt_schedule>')
    accepted('external tail scheduler edge retained',lambda:p.transfers(external,symbol,table)['external_transfers'][0]['scheduler_boundary']is True)
    accepted('external conditional edge retained',lambda:p.transfers(dis.replace('b.eq 2008 <strcmp+0x8>','b.eq 3000 <preempt_schedule>'),symbol,table)['external_transfers'][0]['mnemonic']=='b.eq')
    accepted('unresolved direct call explicit',lambda:p.transfers(dis.replace('b 2004 <strcmp+0x4>','bl 4000'),symbol,table)['external_transfers'][0]['unresolved']is True)
    accepted('indirect transfer unknown not leaf',lambda:len(p.transfers(dis.replace('b 2004 <strcmp+0x4>','blr x8'),symbol,table)['unknown_control_transfers'])==1)
    rejected('missing function label',lambda:p.transfers('\n'.join(dis.splitlines()[1:]),symbol,table))
    rejected('arbitrary alias label',lambda:p.transfers(dis.replace('<strcmp_alias>:','<not_bound>:'),symbol,table))
    rejected('incomplete extent',lambda:p.transfers(dis.replace(' 2008: b4000000 cbz x0, 2000 <strcmp>\n',''),symbol,table))
    rejected('outside instruction extent',lambda:p.transfers(dis+' 2010: d65f03c0 ret\n',symbol,table))
    rejected('interior target must hit an instruction',lambda:p.transfers(dis.replace('b 2004 <strcmp+0x4>','b 2002 <strcmp+0x2>'),symbol,table))
    usage=source+':141:arch_match_cpu_phys_id\t0\tstatic\n'
    elf='  [ 1] .text PROGBITS 0000000000000000 000040 000008 00 AX 0 0 4\n  1: 0000000000000000 8 FUNC GLOBAL DEFAULT 1 arch_match_cpu_phys_id\n'
    item=dict(command=cmd.decode(),command_sha256=p.sha(cmd),stack_usage=usage,stack_sha256=p.sha(usage.encode()),stack_relative='arch/arm64/kernel/.tmp_setup.su',elf_sections_and_symbols=elf,elf_evidence_sha256=p.sha(elf.encode()))
    accepted('strong ARM64 setup body not weak OF shadow',lambda:p.object_proof(target,item,('arch_match_cpu_phys_id',),table)['arch_match_cpu_phys_id']['binding']=='GLOBAL')
    def changed(field,before,after):
        copy=deepcopy(item);copy[field]=copy[field].replace(before,after)
        copy['stack_sha256'if field=='stack_usage'else'elf_evidence_sha256']=p.sha(copy[field].encode());return copy
    rejected('dynamic selected frame',lambda:p.object_proof(target,changed('stack_usage','static','dynamic'),('arch_match_cpu_phys_id',),table))
    rejected('wrong TU selected frame',lambda:p.object_proof(target,changed('stack_usage','/ci/work/source','/other/source'),('arch_match_cpu_phys_id',),table))
    rejected('weak fallback cannot prove strong setup',lambda:p.object_proof(target,changed('elf_sections_and_symbols','FUNC GLOBAL','FUNC WEAK'),('arch_match_cpu_phys_id',),table))
    rejected('init section cannot supply runtime body',lambda:p.object_proof(target,changed('elf_sections_and_symbols','.text ','.init.text '),('arch_match_cpu_phys_id',),table))
    # The fixed complete collection contract, synthetic only; no subprocess/object read.
    objects={};linked={};assembly={};tools=[]
    for index,name in enumerate(p.MANDATORY):
        linked[name]=dict(kind='W'if name=='arch_find_n_match_cpu_physical_id'else't'if name=='n233_clear_consistency'else'T',address=0x10000+index*16,bytes=8)
    for obj,names in {**p.NEW_OBJECTS,**p.REUSED_OBJECTS}.items():
        tu='/ci/work/source/'+obj[:-2]+'.c';out=obj[:-2]+'.o'
        command=('cmd_'+obj+' := clang-14 -fstack-usage -fno-strict-aliasing -o '+out+' -c '+tu+'\nsource_'+obj+' := '+tu+'\n').encode()
        su=''.join(tu+':1:'+name+'\t16\tstatic\n'for name in names)
        sections='  [ 1] .text PROGBITS 0000000000000000 000040 000800 00 AX 0 0 4\n'
        for i,name in enumerate(names):
            binding='WEAK'if linked[name]['kind']=='W'else'LOCAL'if linked[name]['kind']=='t'else'GLOBAL'
            sections+='  '+str(i+1)+': '+format(i*8,'016x')+' 8 FUNC '+binding+' DEFAULT 1 '+name+'\n'
        objects[obj]=dict(command=command.decode(),command_sha256=p.sha(command),stack_usage=su,stack_sha256=p.sha(su.encode()),
            stack_relative=obj[:-2]+'.su',elf_sections_and_symbols=sections,elf_evidence_sha256=p.sha(sections.encode()))
    for name,row in linked.items():
        address=row['address'];assembly[name]=format(address,'016x')+' <'+name+'>:\n '+format(address,'x')+': d503201f nop\n '+format(address+4,'x')+': d65f03c0 ret\n'
    for obj in p.NEW_OBJECTS:
        tools.append(dict(argv=['aarch64-linux-gnu-readelf','--wide','--sections','--symbols','/ci/work/objects/'+obj],returncode=0,
            stdout_sha256=p.sha(objects[obj]['elf_sections_and_symbols'].encode()),stderr=''))
    for name in p.MANDATORY:
        tools.append(dict(argv=p.command('/ci/work/objects/vmlinux',p.extent(linked,name)),returncode=0,stdout_sha256=p.sha(assembly[name].encode()),stderr=''))
    nm_full=''.join(name+' '+row['kind']+' '+format(row['address'],'x')+' 8\n'for name,row in linked.items())
    raw=dict(schema=p.RAW_SCHEMA,objects={obj:objects[obj]for obj in p.NEW_OBJECTS},linked_nm_sha256=p.sha(nm_full.encode()),assembly=assembly,tools=tools)
    stack=dict(objects={obj:objects[obj]for obj in p.REUSED_OBJECTS},linked_nm=nm_full)
    def full_inventory():
        proof=p.verify(raw,stack);return all(proof[k]==v for k,v in p.LIMITS.items())
    accepted('complete fixed inventory preserves every hard false scope flag',full_inventory)
    accepted('WEAK OF matcher joins correct object not strong ARM64 matcher',lambda:p.object_proof('drivers/of/base.o',objects['drivers/of/base.o'],('arch_find_n_match_cpu_physical_id',),linked)['arch_find_n_match_cpu_physical_id']['binding']=='WEAK')
    def incomplete():
        copy=deepcopy(raw);del copy['objects']['drivers/of/base.o'];return p.verify(copy,stack)
    rejected('missing required object text',incomplete)
    def wrong_argv():
        copy=deepcopy(raw);copy['tools'][-1]['argv'][-1]='/other/objects/vmlinux';return p.verify(copy,stack)
    rejected('disassembly from different ELF root',wrong_argv)
    for name,call,wanted in cases:
        try:result=call();actual=result is not False
        except (ValueError,KeyError,TypeError):actual=False
        if actual is not wanted:raise AssertionError(name)
    if len(cases)!=COUNTS['variants']:raise AssertionError('new evidence case count')
    return dict(COUNTS)
