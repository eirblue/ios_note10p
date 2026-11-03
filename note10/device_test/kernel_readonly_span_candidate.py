"""Distinct type3 readonly span candidate. This first-use revision is PC only."""
import re
import struct
from pathlib import Path
import linux_data_carrier as data
from retained_v108_origin import reader as retained_reader
import kernel_readonly_input as old

KIND='kernel-readonly-span-candidate'
SCHEMA='n10-kernel-readonly-span-candidate-v1'
MODE='kernel-readonly-span-candidate-v1'
CAPACITY=4440064
ALIGN=16
DESCRIPTOR_BYTES=80
BUDGET=59768832
MAGIC=b'N10KROINPUTV3!!!'
DESCRIPTOR=MAGIC+struct.pack('<IIQQ',3,80,CAPACITY,0)+bytes(40)
SLOT='n10_kernel_readonly3_input'
DESC='n10_kernel_readonly3_descriptor'
WORKFLOW=old.WORKFLOW
API_PINS=data.API_PINS
SOURCES=('kernel_readonly_span_candidate.py','kernel_readonly_span_candidate.h',
    'kernel_readonly_span_candidate_fixture.c','test_v107_readonly_span_candidate.py','build_kernel_readonly_span_candidate.py')
FIELDS=('kernel_readonly3_schema','kernel_readonly3_slot','kernel_readonly3_span_schema','kernel_readonly3_span',
    'kernel_readonly3_linked_bytes','kernel_readonly3_image_bytes','kernel_readonly3_requires_ack','kernel_readonly3_marker')


# Exact accepted native producer origin; never a historical host-profile identity.
NATIVE_HEAD='c41749e5a4b5179e46dbca6f66d0f473b7bc9529'
NATIVE_RESULT_SHA256='07ce90d75d33c7ed58102394c0999b5978f047fa0cf7e7955b5ff46baf492bcf'
NATIVE_PINS={'note10/device_test/build_builtin_init_image.py': '96ebb24f91f3358d0e586d71166bfa640d44abf600e01adf27717d94b07ca868', 'note10/device_test/build_kernel_readonly_span_candidate.py': '15db73e53be3c919e23dcff5368b0766d931607dec305a46950751c72976b282', 'note10/device_test/kernel_readonly_input.py': '46fdf3a5a85b98392cfbf1811f109c9421aa2f368d15f1ebfd10cae4b0a5931b', 'note10/device_test/kernel_readonly_span.h': 'dd0640b8322fb86c8baa29863a931ddb7d005dd589352ba4136c09bdb79de86d', 'note10/device_test/kernel_readonly_span_candidate.h': '8f8e8522a7b03413b3db59f21fca5cefa4b74fb9e63a412dfc9d6067beb5dec1', 'note10/device_test/kernel_readonly_span_candidate.py': '9bf08457a494075e49150f2a8e5b870bb307ba9138a37412a689adb722b0caf2', 'note10/device_test/kernel_readonly_span_candidate_fixture.c': 'b4d02ff71b82365915fca0c112170de9c44184dcce481656832e69e77dee9f29', 'note10/device_test/linux_data_carrier.c': '214523104e091eb4be28d67d5adb06b59864bfa5b589bde2ce92be56fba9aa80', 'note10/device_test/linux_data_carrier.py': '617f01bfd5ce8df5357a2080bc7b9b1a5badf44c247d6a6fce0c759450545a0b', 'note10/device_test/linux_data_carrier_composition.c': '2eb666597983d3a2dfb0a4f98da26dc02dff287db49d39756ada6edc90e0c667', 'note10/device_test/test_v107_readonly_span_candidate.py': '10a3f90b475eda8dcaace92cb1dd387ba0ba6198316773f0212b578d51a1d64c'}
NATIVE_SOURCE59={'.github/workflows/note10-builtin-init-route.yml': 'c135fb22c04e0fa085b3092c23af369f10070d6560e6ccaf0c005c71a1b134b6', '.github/workflows/note10-linux-data-carrier.yml': 'c4586cb80fb24c638c341c86b374849efee3a858c2154c15716001b1f0fdb7fa', 'note10/device_test/auto_cycle.py': 'f5c1efa4f248031e50d37728bca4fcf97cad6f02916572f1fb3ed72589ea085a', 'note10/device_test/auto_return.c': '9ec43d3d17f12fe90d2ab36e4712537b7f8275f6f27b6536bbef826f9692037d', 'note10/device_test/build_boot_test_packages.py': '17b973f54185521be6685acb5e019f8bf8b5f10897d01c0167929c97859cddef', 'note10/device_test/build_builtin_init_image.py': '96ebb24f91f3358d0e586d71166bfa640d44abf600e01adf27717d94b07ca868', 'note10/device_test/build_kernel_readonly_span_candidate.py': '15db73e53be3c919e23dcff5368b0766d931607dec305a46950751c72976b282', 'note10/device_test/build_linux_data_carrier.py': '44f083e2168716b33cea4111ab303c83f5fda5136dd99f54f32c2521a2f25d98', 'note10/device_test/build_sha256_kat_recovery.py': '2f84ba60d3b0a582d015c2d6c1955aae8a8a4e785b575da5d2af6ebf293ab123', 'note10/device_test/build_sha256_runtime_kat.py': 'd76c33333a67d6af4bc7c0d8caf0b0868f8e5d63e1c585f6def2860dfe4bbdff', 'note10/device_test/build_xnu_runtime_plan_component.py': '367f9147d50950dffb47bf83861787dce4a1be47225b11b070e2f60de45c6b6e', 'note10/device_test/builtin_init_profile.py': '81ee864aeecfec92f87c5704533b0b15423d21ea604565a1b121a4d338898248', 'note10/device_test/builtin_init_route.c': '2fb12577bfd332cd83c3e497aa5930c275983e0f9139d22f53b009b0a9249d74', 'note10/device_test/builtin_init_route.py': '46b100dc95f11e344c11b8cb3fba5d34d17b2884385923426a42246699fda43d', 'note10/device_test/builtin_init_route_fixture.c': 'e6c586d479175eae9ba2496b886ff504e584aadf53b2fb3816f64e839a2be6e7', 'note10/device_test/builtin_minimal_init.S': 'ca8ad494643331a3065b25f0e62330dce4c7385a354bac71e75a972627a6ad60', 'note10/device_test/bundle_affinity_evidence.py': 'b292f0cd45df8b8ef110146315520a857c388d52f9b2e69a0812a3ae8f4253dc', 'note10/device_test/carrier_lzma.c': 'e204732754f15929f7134885ec2740e1ed26f0291dd64c7df7957a4aee7b987a', 'note10/device_test/carrier_lzma.h': '6790aa17da94025e0bab175377573edb8df3f503c8cde86f8c919e33ee742974', 'note10/device_test/decode_reservation.py': 'c60e3f8cb399d6f62e61531ddf8c15aacbeaa87ea7d6c897e8953f3e62f1c971', 'note10/device_test/decode_sha256_runtime_kat.py': 'c83437aae48ee4f1d7400edf73933c8b0102291934648a30387100ef187f42b9', 'note10/device_test/early_fdt_binding.py': 'd4f7099fb45eca31c83c9acd9fbfe0cd5c7ccc5c271c18180e3672e22f9a6b78', 'note10/device_test/kernel_readonly_input.py': '46fdf3a5a85b98392cfbf1811f109c9421aa2f368d15f1ebfd10cae4b0a5931b', 'note10/device_test/kernel_readonly_span.h': 'dd0640b8322fb86c8baa29863a931ddb7d005dd589352ba4136c09bdb79de86d', 'note10/device_test/kernel_readonly_span_candidate.h': '8f8e8522a7b03413b3db59f21fca5cefa4b74fb9e63a412dfc9d6067beb5dec1', 'note10/device_test/kernel_readonly_span_candidate.py': '9bf08457a494075e49150f2a8e5b870bb307ba9138a37412a689adb722b0caf2', 'note10/device_test/kernel_readonly_span_candidate_fixture.c': 'b4d02ff71b82365915fca0c112170de9c44184dcce481656832e69e77dee9f29', 'note10/device_test/linux_data_carrier.c': '214523104e091eb4be28d67d5adb06b59864bfa5b589bde2ce92be56fba9aa80', 'note10/device_test/linux_data_carrier.py': '617f01bfd5ce8df5357a2080bc7b9b1a5badf44c247d6a6fce0c759450545a0b', 'note10/device_test/linux_data_carrier_composition.c': '2eb666597983d3a2dfb0a4f98da26dc02dff287db49d39756ada6edc90e0c667', 'note10/device_test/linux_data_carrier_fixture.c': '6b1b0e14184582c734a3154eeef6c0e2736fd1b8ef3491881b7decaacb5ecbe4', 'note10/device_test/linux_data_compare_evidence.h': '3383823cf1fd56f688ad9d6823d965fdda270a08acede17f6df8d87fa6199438', 'note10/device_test/linux_data_early_prefix.h': '60fb29d56be78212e04cc164938db4a25296fdea5250e372824b317127aaeb98', 'note10/device_test/linux_data_early_prefix_fixture.c': 'b058ccfa33fccadfa2547986a724b21dd7de0b781e003cd3ca1c71fddfe36f09', 'note10/device_test/linux_data_growth.h': '640ae63bd927d205ad8bc489c4c7b25935f1c4311332dce5d10821acf3ac0746', 'note10/device_test/linux_data_growth_fixture.c': 'd567edfc28efc1b258eff93a72dda94d8f24af00297b315b1f7d371c7d77066a', 'note10/device_test/linux_data_input_probe_fixture.c': 'c7192b0515eb7de9526291913ef97737207844a45d266a4e1287437f49b3e0b4', 'note10/device_test/linux_data_input_range.h': 'c53f208c886ba21af0f22d266a1edb1de0f42a3e40d5a68080a41fcf775d4dac', 'note10/device_test/linux_data_input_range_fixture.c': 'd3c7695b319963b9d6de679a5eadaf107c4dc667e610b892f2953a390854ecd5', 'note10/device_test/materialize_auto_cycle.py': '65874b171f2d88a66f98df854a831e30bf6055a32c43903e82dfa92df13d39e8', 'note10/device_test/pre_pm_archive_contract.py': '966a5b032e516ecc984defc9b0313192667d4f4585511fa232966ce79ac3b5c5', 'note10/device_test/prepare_linux_boot.py': '9b41826b7b27dca4ff9078b5b78b30bb509b848535b597516354a5bb64038674', 'note10/device_test/prepare_sha256_kat_recovery.py': '921dd3cade033e21e50994c1b8036d8067bb77c8f9372454c9290673aa7d4b91', 'note10/device_test/prepare_sha256_runtime_kat.py': '5f56dfb7d77acc2b998122022b65421a5e34f73d52be446a677ff333b5d5e5c2', 'note10/device_test/prepare_xnu_runtime_plan.py': '6b9b21ab93f3b49ef43e947a26ad1985d2f11bbd94002e30fcf6dcca875ac41c', 'note10/device_test/sealed_affinity_artifact.cjs': '08c17edb82357d5719fbccd2427fca1970c09f6b3ee7aef91d6034f7d12f70ec', 'note10/device_test/sha256_builtin_init.c': '11408b9dba36f56137f5d411d9a77eaf72db71cadfec9b406f85fcfc3d3cd6e4', 'note10/device_test/sha256_kat_device_profile.py': '9d86a519d98a0db3603a887c21c8d8a62e58f82e38bde8adb2c6d90c3c67e937', 'note10/device_test/sha256_kat_recovery.c': '5b26ec7dca0a936bcebf1860cddb42a0b24806b9f3a7c09bfdf06d8edf27d1bf', 'note10/device_test/sha256_kat_recovery_work.c': 'a39e955e0a104251434fed69e137687e0f24876f63e1f496f401d95acf119859', 'note10/device_test/sha256_runtime_kat.c': '58470621def88390f16d2608989bafac76ff6d502bb211d400d2b488ed5df5ca', 'note10/device_test/stage_phase2.py': 'fd95f75a0c204de6c66464dc2e25094c1f41d09ade11e21716155d0089e789ac', 'note10/device_test/test_builtin_init_route.py': '9fa63dd55114472a748062447dd95c17bf4d4d7e743117f69f0bb6a7aca6ea42', 'note10/device_test/test_linux_data_carrier.py': '550344e818b42f8147ea1f688929feda322c68173f79f6e72850053dbc2e1ca7', 'note10/device_test/test_v100_carrier_input_probe.py': 'f8e37cb2da1fc1efda5582079bb619d8853565d892a589872d0699277e8c4489', 'note10/device_test/test_v101_live_input_range.py': 'e4424b6128a18f4099b31ddc6dcf16ba6256749ba2a87f8bd565b68a1ef68183', 'note10/device_test/test_v102_input_lifetime.py': '29cdae5c4b8ace788ad84f529700d753bcb19c9d4a34697bddf8ca7dfa80bed1', 'note10/device_test/test_v104_growth_region.py': '89ca671ca695b083ccf9cb58c6f474acfeadb9a67ff9747d640cc533dde40e7d', 'note10/device_test/test_v107_readonly_span_candidate.py': '10a3f90b475eda8dcaace92cb1dd387ba0ba6198316773f0212b578d51a1d64c'}


def install(source,identity):
    source=Path(source);original=(source/'arch/arm64/kernel/setup.c').read_bytes()
    result=data.install(source,identity)
    (source/'arch/arm64/kernel/setup.c').write_bytes(original)
    result['arch/arm64/kernel/setup.c']=data.sha(original)
    composition=(data.HERE/'linux_data_carrier_composition.c').read_bytes()
    match=b'#define N10_DATA_COMPARE_EVIDENCE 1'
    data.require(composition.count(match)==1,'unique type3 late composition required')
    composition=composition.replace(match,b'#ifdef CONFIG_NOTE10_KERNEL_READONLY_SPAN_CANDIDATE\n#define N10_DATA_KERNEL_READONLY 1\n#define N10_DATA_KERNEL_READONLY_V3 1\n#else\n'+match+b'\n#endif',1)
    config=source/'drivers/misc/note10_sha256_kat.Kconfig'
    config.write_bytes(config.read_bytes()+b'\nconfig NOTE10_KERNEL_READONLY_SPAN_CANDIDATE\n\tbool "Note10 distinct type3 readonly span candidate"\n\tdepends on NOTE10_DATA_CARRIER\n\tdefault n\n')
    for name,raw in (('drivers/misc/note10_sha256_kat.c',composition),
        ('drivers/misc/kernel_readonly_span.h',(data.HERE/'kernel_readonly_span.h').read_bytes()),
        ('drivers/misc/kernel_readonly_span_candidate.h',(data.HERE/'kernel_readonly_span_candidate.h').read_bytes())):
        (source/name).write_bytes(raw);result[name]=data.sha(raw)
    result['drivers/misc/note10_sha256_kat.Kconfig']=data.sha(config.read_bytes())
    return result


def slot_metadata(raw,system_map,object_symbols,object_sections,object_table):
    data.require(not any(name in object_symbols or name in object_sections for name in
        ('n10_kernel_readonly_input','n10_kernel_readonly_descriptor','.rodata.n10_kernel_readonly_input','.rodata.n10_kernel_readonly_descriptor','n10_readonly_input','n10_readonly_descriptor')),
        'type3 must contain one slot/descriptor without class2 or PC storage')
    data.require(type(raw) is bytes and raw.count(DESCRIPTOR)==1,'one exact generic readonly descriptor required')
    names={'_text','_end','__start_rodata','__init_begin',SLOT,DESC}
    values={}
    for line in system_map.splitlines():
        row=line.split()
        if len(row)==3 and row[2] in names:
            data.require(row[2] not in values,'duplicate readonly linked symbol')
            values[row[2]]=int(row[0],16)
    data.require(set(values)==names,'readonly linked symbol bounds missing')
    records={}
    for symbol,section,size in ((SLOT,'.rodata.n10_kernel_readonly3_input',CAPACITY),
                                (DESC,'.rodata.n10_kernel_readonly3_descriptor',DESCRIPTOR_BYTES)):
        symbols=[row for line in object_symbols.splitlines() if len(row:=line.split())==4 and row[3]==symbol]
        sections=re.findall(r'\[\s*(\d+)\]\s+'+re.escape(section)+r'\s+PROGBITS\s+[0-9a-fA-F]+\s+[0-9a-fA-F]+\s+([0-9a-fA-F]+)\s+\S+\s+([A-Za-z]+)\s+\d+\s+\d+\s+(\d+)',object_sections)
        table=[row for line in object_table.splitlines() if len(row:=line.split())==8 and row[7]==symbol]
        data.require(len(symbols)==len(sections)==len(table)==1 and int(symbols[0][1],16)==size and
            int(symbols[0][0],16)==0 and symbols[0][2].lower()=='r' and
            int(sections[0][1],16)==size and 'A' in sections[0][2] and
            not {'W','X'} & set(sections[0][2]) and int(sections[0][3])>=ALIGN and
            table[0][3:6]==['OBJECT','LOCAL','DEFAULT'] and table[0][6]==sections[0][0] and
            int(table[0][1],16)==0 and
            int(table[0][2],16 if table[0][2].startswith('0x') else 10)==size,'actual readonly nonexecuting compiler section required')
        start=values[symbol];offset=start-values['_text']
        data.require(start%ALIGN==0 and values['_text']<values['__start_rodata']<=start and
            start+size<=values['__init_begin']<=values['_end'] and 0<=offset<=len(raw)-size,
            'readonly linked/file extent differs')
        want=bytes(CAPACITY) if symbol==SLOT else DESCRIPTOR
        data.require(raw[offset:offset+size]==want,'generic readonly file preimage differs')
        records[symbol]=dict(symbol=symbol,section=section,offset=offset,bytes=size,
            alignment=ALIGN,readonly_flags=sections[0][2],preimage_sha256=data.sha(want),
            object_section_index=int(sections[0][0]),object_symbol_offset=0)
    a,b=records[SLOT],records[DESC]
    data.require(a['offset']+a['bytes']<=b['offset'] or b['offset']+b['bytes']<=a['offset'],
        'readonly descriptor/input overlap')
    return dict(schema=SCHEMA,source=MODE,capacity=CAPACITY,descriptor_bytes=DESCRIPTOR_BYTES,
        slot=a,descriptor=b,generic=True,patched=False,permanent_input_bytes=CAPACITY,
        permanent_descriptor_bytes=DESCRIPTOR_BYTES,physical_ready=False,descriptor_class=3,boot_page=2048)


def metadata_contract(slot,image_bytes):
    keys={'schema','source','capacity','descriptor_bytes','slot','descriptor','generic','patched',
        'permanent_input_bytes','permanent_descriptor_bytes','physical_ready','descriptor_class','boot_page'}
    data.require(type(slot) is dict and set(slot)==keys and slot['schema']==SCHEMA and
        slot['source']==MODE and type(slot['descriptor_class']) is int and slot['descriptor_class']==3 and
        type(slot['boot_page']) is int and slot['boot_page']==2048 and type(slot['capacity']) is int and slot['capacity']==CAPACITY and
        type(slot['descriptor_bytes']) is int and slot['descriptor_bytes']==80 and
        slot['generic'] is True and slot['patched'] is False and slot['physical_ready'] is False and
        slot['permanent_input_bytes']==CAPACITY and slot['permanent_descriptor_bytes']==80 and
        type(image_bytes) is int and image_bytes>CAPACITY+80,'closed generic kernel readonly slot metadata required')
    for key,symbol,section,size,preimage in (
        ('slot',SLOT,'.rodata.n10_kernel_readonly3_input',CAPACITY,data.sha(bytes(CAPACITY))),
        ('descriptor',DESC,'.rodata.n10_kernel_readonly3_descriptor',80,data.sha(DESCRIPTOR))):
        row=slot[key]
        data.require(type(row) is dict and set(row)=={'symbol','section','offset','bytes','alignment','readonly_flags','preimage_sha256','object_section_index','object_symbol_offset'} and
            row['symbol']==symbol and row['section']==section and type(row['bytes']) is int and row['bytes']==size and
            type(row['offset']) is int and row['offset']>=0 and row['offset']%ALIGN==0 and
            row['offset']+size<=image_bytes and type(row['alignment']) is int and row['alignment']==ALIGN and
            type(row['readonly_flags']) is str and 'A' in row['readonly_flags'] and
            not {'W','X'} & set(row['readonly_flags']) and row['preimage_sha256']==preimage and
            type(row['object_section_index']) is int and row['object_section_index']>0 and
            type(row['object_symbol_offset']) is int and row['object_symbol_offset']==0,
            'closed candidate readonly extent provenance differs')
    a,b=slot['slot'],slot['descriptor']
    data.require(a['object_section_index']!=b['object_section_index'],'distinct type3 compiler sections required')
    data.require(a['offset']+a['bytes']<=b['offset'] or b['offset']+b['bytes']<=a['offset'],
        'candidate readonly metadata overlap')
    return True


def span_metadata(system_map,footprint,slot):
    return old.span_footprint(system_map,footprint,slot,slot_symbol=SLOT,descriptor_symbol=DESC)


def producer_contract(result,source,*,producing_sources=None,historical_origin=None):
    from readonly_stage_witness import KIND as STAGE_KIND,SCHEMA as STAGE_SCHEMA,SOURCES as STAGE_SOURCES
    from native_scoped_output import KIND as SCOPED_KIND,SCHEMA as SCOPED_SCHEMA,SOURCES as SCOPED_SOURCES,REFERENCE_LINKED_BYTES
    scoped=result.get('diagnostic_kind')==SCOPED_KIND
    witness=result.get('diagnostic_kind')==STAGE_KIND or scoped
    wanted_kind=SCOPED_KIND if scoped else STAGE_KIND if witness else KIND
    required=(*SOURCES,*(STAGE_SOURCES if witness else ()),*(SCOPED_SOURCES if scoped else ()),'kernel_readonly_input.py','kernel_readonly_span.h','linux_data_carrier.py',
        'linux_data_carrier.c','linux_data_carrier_composition.c','build_builtin_init_image.py')
    data.require(not witness or historical_origin is None and result.get('readonly_stage_schema')==STAGE_SCHEMA and
        result.get('readonly_stage_marker')=='N10DATASTAGE1' and result.get('operation_scope_PC_only') is True and
        result.get('admission_blocked') is True,'new witness producer cannot use native107 history')
    data.require(not scoped or historical_origin is None and result.get('scoped_output_schema')==SCOPED_SCHEMA and
        result.get('scoped_output_marker')=='N10OUTPUTLEASE1' and result.get('scoped_output_handle_bytes')==24 and
        result.get('scoped_output_payload_bytes')==old.PAYLOAD_BYTES and result.get('scoped_output_default_enabled') is False and
        result.get('scoped_output_reads_per_success')==2 and result.get('scoped_output_retained_after_emit') is False and
        result.get('scoped_output_reference_linked_bytes')==REFERENCE_LINKED_BYTES and
        result.get('scoped_output_linked_delta_bytes')==result.get('data_footprint',{}).get('linked_kernel_bytes',0)-REFERENCE_LINKED_BYTES and
        result.get('data_footprint',{}).get('data_state_bytes')==88 and result.get('settings',{}).get('NOTE10_SCOPED_OUTPUT_LEASE')=='y',
        'closed new native scoped-output producer required')
    if historical_origin is not None:
        data.require(historical_origin==source==NATIVE_HEAD and producing_sources is None and
            result.get('source_sha256')==NATIVE_SOURCE59,'exact retained native107 source59 required')
        producing_sources=NATIVE_PINS
    else:data.require(source!=NATIVE_HEAD,'retained native107 cannot construct a new producer')
    pins=producing_sources if producing_sources is not None else {
        'note10/device_test/'+name:data.sha((data.HERE/name).read_bytes()) for name in required}
    metadata_contract(result.get('kernel_readonly3_slot'),result.get('image_bytes'))
    span=result.get('kernel_readonly3_span',{});footprint=result.get('data_footprint',{});ci=result.get('ci_context',{})
    linked=footprint.get('linked_kernel_bytes')
    data.require(type(span) is dict and set(span)=={'schema','kernel_bytes','text_prefix_bytes','slot_contained','descriptor_contained',
        'disjoint','source','phase','hardware','ownership'} and span['schema']==old.SPAN_SCHEMA and
        type(span['kernel_bytes']) is int and 0<span['kernel_bytes']<=BUDGET and type(span['text_prefix_bytes']) is int and
        span['text_prefix_bytes']>=0 and span['kernel_bytes']+span['text_prefix_bytes']==linked and
        all(span[key] is True for key in ('slot_contained','descriptor_contained','disjoint')) and
        span['hardware'] is False and span['ownership'] is False and span['source']=='linked-kernel' and span['phase']=='pre_descriptor',
        'closed type3 linked span metadata required')
    data.require(result.get('version')==('v116' if scoped else 'v109' if witness else 'v107') and result.get('diagnostic_kind')==result.get('data_input_kind')==result.get('storage_input_kind')==wanted_kind and
        result.get('kernel_readonly3_marker')=='N10DATARO3' and result.get('kernel_readonly3_schema')==SCHEMA and result.get('kernel_readonly3_span_schema')==old.SPAN_SCHEMA and
        result.get('kernel_readonly3_default_enabled') is False and result.get('kernel_readonly3_requires_ack') is True and
        result.get('passed') is True and result.get('Image_built') is True and result.get('BOOT_built') is False and
        result.get('PC_only') is False and result.get('PC_first_use') is True and result.get('physical_ready') is False and result.get('deployment_ready') is False and
        result.get('device_authorized') is False and result.get('device_operations')==[] and
        result.get('data_expectation_mode')==MODE and result.get('data_expectation_slot')==result['kernel_readonly3_slot'] and
        result.get('image_expectation_patched') is False and result.get('external_initrd_capture') is False and
        result.get('input_capture_source')=='late-kernel-readonly-span-class3' and
        result.get('permanent_input_storage_bytes')==CAPACITY and result.get('permanent_descriptor_bytes')==80 and
        result.get('additional_linked_storage_bytes')==CAPACITY+80 and result.get('class2_PC_storage_absent') is True and
        type(linked) is int and 0<linked<=BUDGET and result.get('kernel_readonly3_linked_bytes')==linked and
        result.get('kernel_readonly3_image_bytes')==result.get('image_bytes') and
        type(footprint.get('data_state_bytes')) is int and 0<footprint['data_state_bytes']<=(88 if witness else 128) and
        result.get('settings',{}).get('NOTE10_KERNEL_READONLY_SPAN_CANDIDATE')=='y' and
        all(result.get('settings',{}).get(key)=='n' for key in ('NOTE10_KERNEL_READONLY_INPUT','NOTE10_KERNEL_READONLY_SPAN_PC',
            'NOTE10_READONLY_INPUT_PC','NOTE10_OWNED_CONTIGUOUS_STAGING','NOTE10_CURRENT_OWNED_STAGING')) and
        not any(key in result for key in (*old.FIELDS[1:],'kernel_readonly_span_schema','readonly_input_schema','readonly_input_slot',
            'readonly_pc_contract','data_compare_schema','data_input_range_schema','data_early_prefix_schema',*data.GROWTH_FIELDS)) and
        re.fullmatch('[0-9a-f]{40}',source or '') and source not in (old.HISTORICAL_HEAD,'1fb2be6472ffd7c1c1544caf005b4db55fb07f68') and
        ci.get('GITHUB_SHA')==ci.get('GITHUB_WORKFLOW_SHA')==source and ci.get('GITHUB_JOB')=='linux-data-carrier' and
        ci.get('GITHUB_REPOSITORY')=='eirblue/ios_note10p' and ci.get('GITHUB_WORKFLOW_REF')=='eirblue/ios_note10p/'+WORKFLOW+'@refs/heads/main' and
        all(re.fullmatch('[1-9][0-9]*',ci.get(key,'') or '') for key in ('GITHUB_RUN_ID','GITHUB_RUN_ATTEMPT')) and
        type(pins) is dict and all('note10/device_test/'+name in pins for name in required) and
        all(re.fullmatch('[0-9a-f]{64}',value or '') and result.get('source_sha256',{}).get(key)==value for key,value in pins.items()),
        'distinct type3 PC-first-use producer/source required')
    for key in ('slot','descriptor'):
        extent=result['kernel_readonly3_slot'][key]
        data.require(span['text_prefix_bytes']<=extent['offset'] and extent['offset']+extent['bytes']<=linked,'type3 span extent differs')
    return dict(candidate_kind=wanted_kind,storage_input_kind=wanted_kind,descriptor_class=3,PC_first_use=True,physical_ready=False,
        **(dict(PC_only=False,operation_scope_PC_only=True,admission_blocked=True,stage_witness_schema=STAGE_SCHEMA) if witness else {}),
        **(dict(scoped_output_schema=SCOPED_SCHEMA,caller_local_handle_bytes=24,reads_per_success=2,retained_after_emit=False,
            linked_reference_bytes=REFERENCE_LINKED_BYTES,actual_linked_extent_delta_bytes=linked-REFERENCE_LINKED_BYTES) if scoped else {}),
        slot_count=1,descriptor_count=1,additional_readonly_storage_bytes=CAPACITY+80,linked_budget=BUDGET,
        scalar_bytes=footprint['data_state_bytes'],range_scalar_bytes=16,temporary_outcome_bytes=128,
        hardware_mapping_attested=False,global_RAM_ownership=False,offline_composition_admitted=False)


def is_candidate(row):
    return row.get('diagnostic_kind')==KIND or row.get('data_input_kind')==KIND or row.get('data_expectation_mode')==MODE or any(key in row for key in FIELDS)


def physical_input_scope(row):
    from readonly_stage_witness import refuse
    refuse(row)
    if row.get('version')=='v107' and row.get('ci_context',{}).get('GITHUB_SHA')==NATIVE_HEAD:
        producer_contract(row,NATIVE_HEAD,historical_origin=NATIVE_HEAD)
        return True
    from type3_admission import candidate_scope
    candidate_scope(row)
    return True


def input_binding(result,lines,*,elf,archive,raw_inputs,historical_origin=None):
    from early_fdt_binding import fixed_route_relation
    from class3_native_origin import stage_selected,producer,stage_fields,_NATIVE109
    if stage_selected(result):
        data.require(historical_origin==_NATIVE109['head'],'native109 input binding is exact read-origin only')
        producer(result,historical_origin)
    else:producer_contract(result,result.get('ci_context',{}).get('GITHUB_SHA'),historical_origin=historical_origin)
    data.require('CONFIG_NOTE10_KERNEL_READONLY_SPAN_CANDIDATE=y' in lines and not
        {'CONFIG_NOTE10_KERNEL_READONLY_INPUT=y','CONFIG_NOTE10_KERNEL_READONLY_SPAN_PC=y','CONFIG_NOTE10_READONLY_INPUT_PC=y',
         'CONFIG_NOTE10_OWNED_CONTIGUOUS_STAGING=y','CONFIG_NOTE10_CURRENT_OWNED_STAGING=y'} & set(lines),'distinct native107 type3 configuration required')
    fixed_route_relation(elf,archive,result,raw_inputs)
    return dict(data_carrier_stage=data.STAGE,data_relative_placement_admitted=False,raw_input_binding=False,
        diagnostic_kind=result['diagnostic_kind'],data_input_kind=result['data_input_kind'],storage_input_kind=result['storage_input_kind'],data_expectation_mode=MODE,
        data_expectation_slot=result['kernel_readonly3_slot'],image_expectation_patched=False,
        **{key:result[key] for key in FIELDS},**(stage_fields() if stage_selected(result) else {}))


def require_device_scope(row,ack_kernel_readonly_growth=False,context=None):
    from type3_admission import require_device_scope as admitted
    return admitted(row,ack_kernel_readonly_growth,context)


@retained_reader
def decode_selected(raw,banner,identity,cycle,*,expected):
    from builtin_init_profile import decode as baseline_decode
    from class3_native_origin import stage_selected,producer
    witness=stage_selected(expected)
    materialized='execution_version' in expected
    if materialized:
        from type3_admission import candidate_scope
        candidate_scope(expected,patched=True)
    elif witness:producer(expected,expected.get('ci_context',{}).get('GITHUB_SHA'))
    else:producer_contract(expected,expected.get('ci_context',{}).get('GITHUB_SHA'),
        historical_origin=NATIVE_HEAD if expected.get('ci_context',{}).get('GITHUB_SHA')==NATIVE_HEAD else None)
    bound=expected['kernel_readonly3_span']['kernel_bytes']
    components=dict(pid1_validation='not_checked',return_validation='not_checked',return_boot_association='not_checked',
        functional_acceptance=False,hardware_return_proven_by_frames=False)
    def selected(text,rid):
        row=data.decode(text,rid,cycle,_source_class=MODE)
        components['kernel_readonly3_data']=row;components['data_phase']=data.functional_phase(row['status'])
        components['structural_presence']=data.structural_presence(text,rid,cycle,row['boot_identity'])
        data.require(not any(marker in text for marker in ('N10DATA1 ','N10DATARO1','N10DATAPC','N10DATACMP','N10DATARANGE','N10DATAEARLY','N10DATAGROWTH')),
            'type3 cannot claim class2, PC or external companions')
        components['kernel_readonly3_span']=old.decode_span(text,rid,cycle,row['boot_identity'],bound)
        if witness:
            from readonly_stage_witness import _decode_joined,SCHEMA as stage_schema
            try:components['readonly_stage_witness']=_decode_joined(text,rid,cycle,row,expected_schema=stage_schema)
            except ValueError as error:
                components['readonly_stage_witness']=dict(state='invalid_or_missing',error=str(error));raise
            data.require(components['readonly_stage_witness']['passed'],'native109 stage witness did not complete')
        data.require(row['carrier']==CAPACITY and row['logical'] in (0,CAPACITY),'type3 extent differs')
        data.require(materialized,'generic type3 PC observation cannot authorize functional or physical acceptance')
        data.require(components['kernel_readonly3_span']['state']=='checked','type3 pre-descriptor span was not checked')
        data.require_functional(row,report_phase=True)
        data.require(row['logical']==expected['type3_compact_bytes'] and row['payload']==row['written']==expected['data_payload_bytes'] and
            row['digest']==expected['data_payload_sha256'],'type3 decoded package identity differs')
        return row
    try:
        clipped,observed=baseline_decode(raw,banner,identity,cycle,digest_decoder=selected,digest_marker=b'N10DATARO3',component_evidence=components)
        data.require(observed['kat']['boot_identity']==observed['boot_identity'],'type3 PID1/recovery boot differs')
    except ValueError as error:raise data.ComponentObservationError(error,components) from error
    if witness:
        components['functional_acceptance']=True
        observed['component_evidence']=components
    return clipped,observed
