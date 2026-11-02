"""Closed PC-only contiguous owned-output candidate; no package/device admission."""
from pathlib import Path
import re
import linux_data_carrier as data

KIND='owned-contiguous-staging-pc'
BYTES=19546112
ALIGN=16384
API_PINS={'arch/arm64/kernel/setup.c': 'f80fd02832b12c48eba11b3e3148c59c6ad87d9ea2328c8c37492d107fd141d7', 'mm/memblock.c': '4f0bf30f9b0f81ff7e13446454d8a8f35e25129012b4fa63725c0f8b6f5c2c2f', 'include/linux/memblock.h': '04c5a23d41fa1adea1a955f832eca9412bd99cd43bbc84f2188559fb220f87fc', 'arch/arm64/mm/init.c': 'cc990de7d8222f56fd71519c8b5dbf87a50abd4131e9eeb49ba78c04e3b6e3f3', 'arch/arm64/mm/mmu.c': '18bb3b58865215b834e86aa8e44bf8f3c7f40c53428183351120958e25c43541'}
SOURCES=('owned_contiguous_staging.py','owned_contiguous_staging.c',
    'owned_contiguous_staging_composition.c','build_owned_contiguous_staging.py',
    'test_owned_contiguous_staging.py','linux_data_carrier.py','linux_data_carrier.c',
    'linux_data_carrier_fixture.c','test_linux_data_carrier.py','carrier_lzma.c','carrier_lzma.h')
CASE_NAMES=('test_reserve_failure_repeat_and_no_early_touch',
    'test_direct_owned_output_exact_capacity_cleanup_and_refusals',
    'test_closed_pc_producer_context_default_and_relative_caps')

def install(source,identity):
    source=Path(source)
    result=data.install(source,identity)
    setup=source/'arch/arm64/kernel/setup.c'
    raw=setup.read_bytes()
    prototype=b'extern void __init n10_data_capture(unsigned long start, unsigned long end);'
    hook=b'\tn10_data_capture(initrd_start, initrd_end);\n#endif\n'
    data.require(raw.count(prototype)==raw.count(hook)==1,'exact inherited DATA capture seam required')
    raw=raw.replace(prototype,prototype+b'\n#ifdef CONFIG_NOTE10_OWNED_CONTIGUOUS_STAGING\nextern void __init n10_owned_capture(void);\n#endif',1)
    raw=raw.replace(hook,hook+b'#ifdef CONFIG_NOTE10_OWNED_CONTIGUOUS_STAGING\n\tn10_owned_capture();\n#endif\n',1)
    setup.write_bytes(raw)
    config=source/'drivers/misc/note10_sha256_kat.Kconfig'
    config.write_bytes(config.read_bytes()+b'\nconfig NOTE10_OWNED_CONTIGUOUS_STAGING\n\tbool "Note10 PC-only owned contiguous DATA candidate"\n\tdepends on NOTE10_DATA_CARRIER && HAVE_MEMBLOCK && NO_BOOTMEM\n\tdefault n\n')
    for target,name in (('drivers/misc/owned_contiguous_staging.c','owned_contiguous_staging.c'),
                        ('drivers/misc/note10_sha256_kat.c','owned_contiguous_staging_composition.c')):
        path=source/target;path.write_bytes((data.HERE/name).read_bytes());result[target]=data.sha(path.read_bytes())
    result['arch/arm64/kernel/setup.c']=data.sha(raw)
    result['drivers/misc/note10_sha256_kat.Kconfig']=data.sha(config.read_bytes())
    return result


def footprint(system,symbols,size,offset,flags):
    record=data.linked_footprint(system,symbols,size,offset,flags)
    addresses=[int(p[0],16) for line in system.splitlines() if len(p:=line.split())==3 and p[2]=='n10_owned']
    own=[int(p[1],16) for line in symbols.splitlines() if len(p:=line.split())==4 and p[3]=='n10_owned' and p[2].lower()=='b']
    bounds={p[2]:int(p[0],16) for line in system.splitlines() if len(p:=line.split())==3 and p[2] in ('__bss_start','__bss_stop')}
    data.require(len(addresses)==len(own)==1 and 0<own[0]<=40 and
        bounds['__bss_start']<=addresses[0] and addresses[0]+own[0]<=bounds['__bss_stop'] and
        record['data_state_bytes']+own[0]<=128,'combined owned/DATA permanent state bound required')
    return dict(record,owned_state_bytes=own[0],combined_state_bytes=record['data_state_bytes']+own[0])


def relative(result,config,record,*,elf,archive,raw_inputs):
    filtered=[x for x in config if x not in ('CONFIG_NOTE10_OWNED_CONTIGUOUS_STAGING=y','# CONFIG_NOTE10_OWNED_CONTIGUOUS_STAGING is not set')]
    baseline=data.relative_admission(result,filtered,record,elf=elf,archive=archive,raw_inputs=raw_inputs)
    checks=dict(baseline['checks'],owned_enabled='CONFIG_NOTE10_OWNED_CONTIGUOUS_STAGING=y' in config,
        combined_bounded=0<record['combined_state_bytes']<=128)
    return dict(checks=checks,relative_eligible=all(checks.values()),physical_ready=False,PC_only=True,
        observed_runtime_base=False,global_RAM_ownership=False,route_relation=baseline['route_relation'])


def pc_contract(result,source):
    ci=result.get('ci_context',{})
    data.require(result.get('passed') is True and result.get('Image_built') is True and result.get('BOOT_built') is False and
        result.get('version')=='v92' and result.get('diagnostic_kind')==KIND and
        result.get('PC_only') is True and result.get('physical_ready') is False and
        result.get('owned_capacity_bytes')==BYTES and result.get('owned_alignment_bytes')==ALIGN and
        result.get('owned_default_enabled') is False and result.get('data_expectation_mode')==data.MODE and
        re.fullmatch('[0-9a-f]{40}',source or '') and ci.get('GITHUB_SHA')==source and
        ci.get('GITHUB_JOB')=='owned-contiguous-staging-pc' and
        re.fullmatch('[1-9][0-9]*',ci.get('GITHUB_RUN_ID','')) and
        re.fullmatch('[1-9][0-9]*',ci.get('GITHUB_RUN_ATTEMPT','')),
        'closed PC-only owned producer/context differs')
    return dict(PC_only=True,physical_ready=False,global_RAM_ownership=False,xnu_executed=False)
