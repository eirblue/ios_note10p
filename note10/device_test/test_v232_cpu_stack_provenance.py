"""New232 evidence parser only. All paths/addresses synthetic; no old C replay."""
import v232_cpu_stack_provenance as proof


def sample():
    tu='/ci/work/source/arch/arm64/mm/init.c'
    command=('cmd_arch/arm64/mm/init.o := clang-14 -fstack-usage -fno-strict-aliasing -c -o arch/arm64/mm/.tmp_init.o '+tu+'\nsource_arch/arm64/mm/init.o := '+tu+'\n').encode()
    usage='\n'.join(tu+':'+str(line)+':'+name+'\t'+str(size)+'\tstatic'for line,name,size in ((26,proof.FUNCTIONS[0],32),(21,proof.FUNCTIONS[1],0),(47,proof.FUNCTIONS[2],0)))+'\n'
    symbols='n226_source_pool b 1000 c000\nn231_observation_storage B '+format(0x1000+43544,'x')+' 20\n'
    symbols+='n231_size_observation A 20\nn231_align_observation A 8\nn231_status_offset A 18\n'
    symbols+='n231_capture_cpu_observation T 2000 c8\nn231_clear_observation t 20c8 1c\nn231_layout_witness t 20e4 4\n'
    sections='  [ 1] .text PROGBITS 0000000000000000 000040 003000 00 AX 0 0 4\n'
    sections+='  1: 0000000000002000 200 FUNC GLOBAL DEFAULT 1 n231_capture_cpu_observation\n'
    sections+='  2: 00000000000020c8 28 FUNC LOCAL DEFAULT 1 n231_clear_observation\n'
    sections+='  3: 00000000000020e4 4 FUNC LOCAL DEFAULT 1 n231_layout_witness\n'
    return symbols,usage,sections,command


def run():
    symbols,usage,sections,command=sample();actual=proof.observation_target(symbols,usage,sections,command)
    if actual['capture_static_frames'][proof.FUNCTIONS[0]]['bytes']!=32 or actual['owner_TU_provenance']['translation_unit']!='/ci/work/source/arch/arm64/mm/init.c' or actual['capture_scheduler_chain_bound']is not False:
        raise AssertionError('actual included-TU static attribution/provenance required')
    first=usage.splitlines(True)[0]
    mutations=[(symbols,usage.replace(first,''),sections,command),(symbols,usage+first,sections,command),
        (symbols,usage.replace('32\tstatic','32\tdynamic'),sections,command),
        (symbols,usage.replace('/ci/work/','/ci/other/'),sections,command),
        (symbols,usage.replace('/init.c','/v231_cpu_observation.c'),sections,command),
        (symbols,usage,sections,command.split(b'\nsource_',1)[0]+b'\n'),
        (symbols,usage,sections,command+command.splitlines(True)[1]),
        (symbols,usage,sections,command.replace(b'\nsource_arch/arm64/mm/init.o := /ci/work/',b'\nsource_arch/arm64/mm/init.o := /ci/other/')),
        (symbols,usage,sections.replace('200 FUNC','204 FUNC'),command),
        (symbols,usage,sections.replace('.text PROGBITS','.init.text PROGBITS'),command),
        (symbols,usage,'\n'.join(line for line in sections.splitlines()if not line.endswith('n231_clear_observation'))+'\n',command),
        (symbols+'n231_unreviewed t 2100 4\n',usage,sections,command),
        (symbols,usage,sections,command.replace(b'cmd_arch/arm64/mm/init.o :=',b'cmd_arch/arm64/mm/other.o :=')),
        (symbols,'\n'.join(line for line in usage.splitlines()if 'n231_clear_observation'not in line)+'\n',sections,command)]
    for args in mutations:
        try:proof.observation_target(*args)
        except ValueError:pass
        else:raise AssertionError('invalid/missing/duplicate/dynamic/wrong-owner evidence must reject')
    return dict(groups=1,variants=1+len(mutations),assertions=1+len(mutations))
