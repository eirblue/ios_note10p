"""Exact retained host110 materialization: one separately reviewed remaining packing transaction."""
import argparse
from contextlib import contextmanager
from contextvars import ContextVar
from functools import wraps
import json
from pathlib import Path
import re
from types import MappingProxyType

HEAD='f39c0cdcb9c40a4c378ca2cff4afa94e9fa4d916'
FIELD='type3_remaining_pack'
SCHEMA='note10-type3-remaining-pack-v1'
DEVICE_SCHEMA='note10-type3-remaining-pack-device-v1'
NATIVE='f20987a42249e61ef028c52099931f740d9a6cc5'
CONTEXT_SCHEMA='type3-remaining-pack-execution-v1'
PINS=MappingProxyType({
    "note10/device_test/affinity_binding.py": "6d5b16d54a803c95bdd391a38efbd2bac5ef36baffe199f86cd83f878bf10678",
    "note10/device_test/auto_cycle.py": "48d986be690da42d91d0934bab0bed261840c183aad8de5145baf13788aef483",
    "note10/device_test/build_boot_test_packages.py": "17b973f54185521be6685acb5e019f8bf8b5f10897d01c0167929c97859cddef",
    "note10/device_test/build_kernel_readonly_input.py": "5391edfa477324dbdd5f4d9c6fb13deb5df8a66b2ed4df7d018213012b227000",
    "note10/device_test/build_kernel_readonly_span_candidate.py": "c9b44d314719e2f59e69541c2d6618777f616f468e9ca11b5f12d18dcec0f3a0",
    "note10/device_test/build_kernel_readonly_span_pc.py": "cd42e0dec6570bcc09c7a07695560eae13a62420d744e16035c4da3a57c588e9",
    "note10/device_test/build_readonly_input_pc.py": "893698f6741fd178334777b4f96c98934d78b5a927fe4cf3d383d92e90557d9e",
    "note10/device_test/builtin_init_profile.py": "e196c7143cbd7aa55ded754a8381791efeff2974c03436e61c3f50454117e3bf",
    "note10/device_test/builtin_init_route.py": "46b100dc95f11e344c11b8cb3fba5d34d17b2884385923426a42246699fda43d",
    "note10/device_test/carrier_lzma.c": "e204732754f15929f7134885ec2740e1ed26f0291dd64c7df7957a4aee7b987a",
    "note10/device_test/carrier_lzma.h": "6790aa17da94025e0bab175377573edb8df3f503c8cde86f8c919e33ee742974",
    "note10/device_test/class3_native_origin.py": "afdf807d81bc89631776424cb8de25bb87930e74601505d8848ac2c9c70e57cc",
    "note10/device_test/current_data_reuse.py": "15c7a5a55e22f4445c216904769d7ba9b6367f792122e5b936305c95ae031129",
    "note10/device_test/early_fdt_binding.py": "d4f7099fb45eca31c83c9acd9fbfe0cd5c7ccc5c271c18180e3672e22f9a6b78",
    "note10/device_test/kernel_readonly_input.h": "4aa99ff2ab756b854174eb2519af96e79669f82114293790a538ddd3025298ea",
    "note10/device_test/kernel_readonly_input.py": "77dfaeea9c4c1b8c5626c637e1286c988e9257359ebf857f6a0c2f1789015a37",
    "note10/device_test/kernel_readonly_input_fixture.c": "6300f13ba284b4f42614a4c6cda8f09c6e6671e88d6e524ec24dacd3a7ab70e0",
    "note10/device_test/kernel_readonly_span.h": "dd0640b8322fb86c8baa29863a931ddb7d005dd589352ba4136c09bdb79de86d",
    "note10/device_test/kernel_readonly_span_candidate.h": "8f8e8522a7b03413b3db59f21fca5cefa4b74fb9e63a412dfc9d6067beb5dec1",
    "note10/device_test/kernel_readonly_span_candidate.py": "eaa6e94d44c1c05396741177d2571577293b032ac91d1931e3533bdace45641a",
    "note10/device_test/kernel_readonly_span_candidate_fixture.c": "b4d02ff71b82365915fca0c112170de9c44184dcce481656832e69e77dee9f29",
    "note10/device_test/kernel_readonly_span_fixture.c": "afbc9ae410e15bf7221e10a4cbcb325702a3a0235dec0fe585b836e7dae467c6",
    "note10/device_test/linux_data_carrier.c": "53b29fb87158183a0911596820e2f768d15059a5908c7434fa2ca6796e8d0259",
    "note10/device_test/linux_data_carrier.py": "29733dc57cd396a401ed344d7f4a33faed6c383a93c3889f61510a15fcce0ae7",
    "note10/device_test/linux_data_carrier_composition.c": "2eb666597983d3a2dfb0a4f98da26dc02dff287db49d39756ada6edc90e0c667",
    "note10/device_test/linux_data_carrier_fixture.c": "6b1b0e14184582c734a3154eeef6c0e2736fd1b8ef3491881b7decaacb5ecbe4",
    "note10/device_test/linux_data_compare_evidence.h": "3383823cf1fd56f688ad9d6823d965fdda270a08acede17f6df8d87fa6199438",
    "note10/device_test/linux_data_compare_evidence_fixture.c": "45a0cdfd8d4bd8df5ffbbb0e370cd05f768d522e96208881a7f7a02ee02fadc3",
    "note10/device_test/linux_data_early_prefix.h": "60fb29d56be78212e04cc164938db4a25296fdea5250e372824b317127aaeb98",
    "note10/device_test/linux_data_early_prefix_fixture.c": "b058ccfa33fccadfa2547986a724b21dd7de0b781e003cd3ca1c71fddfe36f09",
    "note10/device_test/linux_data_growth.h": "640ae63bd927d205ad8bc489c4c7b25935f1c4311332dce5d10821acf3ac0746",
    "note10/device_test/linux_data_growth_fixture.c": "d567edfc28efc1b258eff93a72dda94d8f24af00297b315b1f7d371c7d77066a",
    "note10/device_test/linux_data_input_probe_fixture.c": "c7192b0515eb7de9526291913ef97737207844a45d266a4e1287437f49b3e0b4",
    "note10/device_test/linux_data_input_range.h": "c53f208c886ba21af0f22d266a1edb1de0f42a3e40d5a68080a41fcf775d4dac",
    "note10/device_test/linux_data_input_range_fixture.c": "d3c7695b319963b9d6de679a5eadaf107c4dc667e610b892f2953a390854ecd5",
    "note10/device_test/materialize_auto_cycle.py": "4b0b67be104a25c740f93a2ff3b4d57a859cf34006d0e43852a2e4cf6a4345de",
    "note10/device_test/native_memory_observation.py": "f4acd0f310989bfcd1b0c2039fef6e429e8ec4d4f41ebdb94fc483538fa26663",
    "note10/device_test/precheck_window_access.py": "3ef3859ef2a4c154e93e5db7846bde78eb9061742243dba435187a9087226e28",
    "note10/device_test/prepare_linux_boot.py": "ae0f41cb5284110680e232a4a830415022a7cb6a1f10312be2dfb3bea0194772",
    "note10/device_test/readonly_input_pc.h": "01b18e5fddcd12fba45190baa337b47c3309f54cc7a448cd6d72209c5ba8a3f0",
    "note10/device_test/readonly_input_pc.py": "d7125058dc85a57eb4283fccf87bcb6af96c26de1363f81d1acb0999b94f1fc7",
    "note10/device_test/readonly_input_pc_fixture.c": "99f0e7eb9240b5c08314993a14dfcd9a532df0e24158679cdbed8b0c3c752730",
    "note10/device_test/readonly_stage_witness.h": "85851db4c9622842f4ccc547e7532139f306917d8674c0298529e5041fb08330",
    "note10/device_test/readonly_stage_witness.py": "200ebe64a1095eca28edc312f897a8c98ee3113f449e47d87ba83a2292cf77ce",
    "note10/device_test/readonly_stage_witness_fixture.c": "2513117dd52b2c8ef92a6f0c161af3a2e1fe6060e24dc9b166d187c5a3fd0cec",
    "note10/device_test/retained_v108_origin.py": "737e3de25884daee64e8dc4d938b81e5b2f328a5923a4b6cea0b2c92b0db24f7",
    "note10/device_test/sha256_kat_device_profile.py": "c0b616627eab344200e165497036cb7aa17b437d6b302da5b4a9ede1d1fe13c6",
    "note10/device_test/sha256_stream_state.py": "55de2735fb830ae8047bb4a8fa74325f51b766b1e885c482dbbc5ebabe3ea437",
    "note10/device_test/sha256_stream_vectors.json": "5c379d1ef41a40b9a1262c985476e9dc0ba88dae7b1586f949bbe79686f2165f",
    "note10/device_test/stage_phase2.py": "9df734fa4227bb2b9a34953ad286a24ca8ecb43d98fc7b5a79548cd3bd99cab1",
    "note10/device_test/test_affinity_binding.py": "bf602887c4437e0096473392789da33e3ef502297d8c060faf7d9da9ecd3eb89",
    "note10/device_test/test_affinity_ci_context.py": "71aad30ab105a45efe2703fd7b222233836d6e7514560834daa71bfdd351dea9",
    "note10/device_test/test_builtin_init_route.py": "9fa63dd55114472a748062447dd95c17bf4d4d7e743117f69f0bb6a7aca6ea42",
    "note10/device_test/test_current_data_reuse.py": "c1a868d4f9669539aee3e4fca4868118db37071467325a85d73c279b2f1d29de",
    "note10/device_test/test_early_fdt_binding.py": "2444d3d20b7cc42e705cb89c1d04de72599f7da2a5d1b9282636f3b9990ce1fa",
    "note10/device_test/test_early_fdt_host_route.py": "75992eb3e8b1228d0ae3916d47306f0329b7947cb0dfae234ec25c1e737fef6a",
    "note10/device_test/test_linux_data_carrier.py": "550344e818b42f8147ea1f688929feda322c68173f79f6e72850053dbc2e1ca7",
    "note10/device_test/test_native_memory_observation.py": "d34e94fd5d964004c42dedd172ec07bd62826b675dcc9f4925ab4ac06c460599",
    "note10/device_test/test_partition_gate_evidence.py": "b7dd52aa5c7747489a2713f805dbe15a6318f3d3776a8043700549e9383bcc72",
    "note10/device_test/test_sha256_kat_device_profile.py": "c48400d5573695d217101806b8481e39aec38fd5382e64b85f999b4cee42c498",
    "note10/device_test/test_sha256_stream_state.py": "088881f92037a9895b7947eb44692f51ecba1eb602a02dacc02ff3b94a836db8",
    "note10/device_test/test_v100_carrier_input_probe.py": "f8e37cb2da1fc1efda5582079bb619d8853565d892a589872d0699277e8c4489",
    "note10/device_test/test_v101_live_input_range.py": "e4424b6128a18f4099b31ddc6dcf16ba6256749ba2a87f8bd565b68a1ef68183",
    "note10/device_test/test_v102_input_lifetime.py": "29cdae5c4b8ace788ad84f529700d753bcb19c9d4a34697bddf8ca7dfa80bed1",
    "note10/device_test/test_v103_readonly_input_pc.py": "cdce146aed40d9526eae04259e39896f629248f6b395ad8ceeec341cae5be9c5",
    "note10/device_test/test_v104_growth_region.py": "89ca671ca695b083ccf9cb58c6f474acfeadb9a67ff9747d640cc533dde40e7d",
    "note10/device_test/test_v105_battery5_policy.py": "8871a297d549df482f8888cc53e392f4b5d659e8d93bfa1e3d16f25f9e4d2c0e",
    "note10/device_test/test_v105_kernel_readonly.py": "7c1cccbdda3e8df612a0fa7d52870e74d750385b85cff7b2965d236177bb23dd",
    "note10/device_test/test_v105_packing_rev1.py": "2402b70737ee2ec9c16fadd0a05b8837d68e5ae364cd1a468c4ac4471a75eabe",
    "note10/device_test/test_v106_kernel_readonly_span.py": "0a777ec820cdfb131f5dc725577e88ed8bffc73d1e951aecfa5671414eb1849c",
    "note10/device_test/test_v107_readonly_span_candidate.py": "10a3f90b475eda8dcaace92cb1dd387ba0ba6198316773f0212b578d51a1d64c",
    "note10/device_test/test_v108_type3_admission.py": "6c2e02ac70f187bd315f4f34dbb66266512c7cd5d07b765594079bafbc10cb30",
    "note10/device_test/test_v109_readonly_stage_witness.py": "33da915026b259cd267705a9a477ebbdf670581cbb8fed6fb604a1870c078684",
    "note10/device_test/test_v110_native109_admission.py": "fcd7b9cad4714a2644fa8601134f25f567ae85b1ea5a0b3a11c0f8c7fc89ff9d",
    "note10/device_test/test_v99_carrier_compare_evidence.py": "2b45c21197709706d3f3ffc23e1428084d5d50a93a1d9b5bd22c2693124cf20c",
    "note10/device_test/test_v99_host_profile_origin.py": "fb4a1c349ca298b4f18ba64e0692c7a93e9f0877b2f7a7ec22fa2c8f29ac219a",
    "note10/device_test/type3_admission.py": "c2bac10bd80ab2262bc6acf7b9c1d297217147b4a0e6c4e66020d7e36df225af"
})
CAPS=dict(compact_source_consumptions=0,compact_derivations=0,templates=0,materializations=0,repatches=0,
    intrinsic_variant_data_consumptions=1,intrinsic_packer_compact_validations=1,
    BOOT_packings=1,package_pair_builds=1,plans=1,new_cycles=0,Image_builds=0,CI=0,C_compiles=0,
    decoder_or_MachO_replays=0,device_queries=0,BOOT_writes=0,reboots=0)
KEYS={'schema','status','execution_version','packaging_host_source_head','retained_host_source_head','native_source_head',
    'accepted_result_sha256','original_contract','original_contract_sha256','original_transaction_sha256',
    'failure_projection','failure_projection_sha256','template_profile_sha256','template_report_sha256',
    'variant_report_sha256','variant_config_sha256','bound_image_sha256','cycle','output','caps'}
_ACTIVE=ContextVar('type3_remaining_pack',default=None)


def selected(row):return row.get('host_profile_source_head')==HEAD


def origin(row):
    import class3_native_origin as origins
    from linux_data_carrier import require
    require(selected(row) and row.get('host_profile_source_sha256')==dict(PINS) and
        row.get('native_source_head')==row.get('source_head')==origins.record(NATIVE)['head'] and
        row.get('version')==row.get('execution_version')=='v110' and origins.stage_selected(row),
        'exact retained f39 host110 read-origin required')
    return dict(host_profile_source_head=HEAD,host_profile_source_sha256=dict(PINS))


def load(path,expected):
    import type3_admission as typed
    import class3_native_origin as origins
    import sha256_kat_device_profile as profile
    path=typed.private(path);raw=typed.data.bounded_private_read(path,65536)
    typed.require(re.fullmatch('[0-9a-f]{64}',expected or '') and typed.sha(raw)==expected,'exact reviewed remaining-pack contract SHA required')
    row=json.loads(raw.decode('utf-8-sig'));item=origins.record(NATIVE)
    typed.require(type(row) is dict and set(row)==KEYS and row['schema']==SCHEMA and row['status']=='reviewed_ready' and
        row['execution_version']=='v110' and row['retained_host_source_head']==HEAD and row['native_source_head']==item['head'] and
        row['accepted_result_sha256']==item['result'] and row['caps']==CAPS and type(row['caps']) is dict and
        all(type(v) is int for v in row['caps'].values()),'closed native109 remaining-pack scope required')
    origins.live_host(row['packaging_host_source_head']);host=profile.host_binding(row['packaging_host_source_head'])
    typed.require(re.fullmatch('[0-9a-f]{32}',row['cycle'] or '') and all(re.fullmatch('[0-9a-f]{64}',row[key] or '') for key in
        ('original_contract_sha256','original_transaction_sha256','failure_projection_sha256','template_profile_sha256',
         'template_report_sha256','variant_report_sha256','variant_config_sha256','bound_image_sha256')),'closed remaining-pack metadata pins required')
    for key in ('original_contract','failure_projection','output'):
        typed.require(type(row[key]) is str and str(typed.private(row[key]))==row[key],'canonical private continuation path required')
    old=typed.load_offline(row['original_contract'],row['original_contract_sha256'])
    typed.require(old['host_source_head']==HEAD and old['native_source_head']==item['head'] and old['execution_version']=='v110',
        'only the exact stopped f39 native109 transaction may continue')
    saved=Path(old['output']);output=Path(row['output']);template=saved/'template';variant=saved/'plan/cycle-01/kernel-build'
    typed.require(all(not output.is_relative_to(Path(p)) and not Path(p).is_relative_to(output) for p in
        (saved,old['producer_root'],old['backup'],old['current_packages'])),'fresh disjoint remaining-pack output required')
    journal=profile.read(saved/'transaction.json');projection=profile.read(row['failure_projection'])
    typed.require(profile.sha(saved/'transaction.json')==row['original_transaction_sha256'] and
        profile.sha(row['failure_projection'])==row['failure_projection_sha256'] and
        journal.get('schema')=='type3-offline-journal-v1' and journal.get('status')=='failed_no_restart' and
        journal.get('phase')=='plan_reserved' and journal.get('error_type')=='ValueError' and journal.get('device_operations')==[] and
        journal.get('contract_sha256')==row['original_contract_sha256'] and journal.get('attempts')==dict(templates=1,plans=1,materializations=1) and
        all(type(v) is int for v in journal['attempts'].values()),
        'exact immutable failed offline journal required')
    counts=dict(cycles_prepared=0,materializations=1,decoder_calls=0,device_operations=0,plan_attempts=1,packages_created=0,
        compact_copy_operations=1,variants=1,compact_validation_operations=1,completed_plan=False,templates=1)
    typed.require(projection.get('schema')=='v110-offline-receipt-copy-rev1-failure-projection-v1' and
        projection.get('status')=='failed_no_restart' and projection.get('host_source_head')==HEAD and
        projection.get('native_source_head')==item['head'] and projection.get('native_result_sha256')==item['result'] and
        projection.get('offline_contract_sha256')==row['original_contract_sha256'] and
        projection.get('offline_transaction_sha256')==row['original_transaction_sha256'] and projection.get('phase')=='plan_reserved' and
        projection.get('error_type')=='ValueError' and
        projection.get('failure_diagnosis',{}).get('message')=='bounded private DATA input required' and
        projection.get('failure_diagnosis',{}).get('template_and_variant_completed_before_failure') is True and
        projection.get('operation_counts')==counts and all(type(projection['operation_counts'][key]) is type(value) for key,value in counts.items()),
        'exact completed-template/variant failed-packing projection required')
    projected=Path(projection.get('offline_transaction_path',''))
    if not projected.is_absolute():projected=Path(__file__).resolve().parents[2]/projected
    typed.require(typed.private(projected)==saved/'transaction.json','failure projection transaction path differs')
    typed.require(not (saved/'plan/plan.json').exists() and all(not (variant.parent/name).exists() for name in
        ('boot.img','boot.json','boot.partial','boot.ramdisk.lzma','packages')),'unfinished packing only; existing old outputs cannot resume')
    for folder,name,pin in ((template,'device-profile.json','template_profile_sha256'),(template,'build-result.json','template_report_sha256'),
        (variant,'build-result.json','variant_report_sha256'),(variant,'handoff.config','variant_config_sha256')):
        typed.require(profile.sha(folder/name)==row[pin],'saved metadata/config pin differs')
    generic=profile.read(template/'build-result.json');binding=profile.read(template/'device-profile.json');original=profile.read(variant/'build-result.json')
    origin(binding);origin(generic);origin(original)
    typed.candidate_scope(binding,patched=False);typed.candidate_scope(original,patched=True)
    typed.require(generic==profile.common_report(binding,row['template_profile_sha256']) and
        binding['type3_contract_sha256']==row['original_contract_sha256'] and binding['type3_contract_path']==row['original_contract'] and
        profile.sha(template/'type3-contract.json')==row['original_contract_sha256'] and
        profile.sha(template/'handoff.config')==row['variant_config_sha256']==binding['effective_config_sha256'] and
        profile.sha(template/'ci-success-context.json')==old['ci_success_context_sha256'] and
        profile.sha(template/'result.json')==item['result'],'saved template source/context/config differs')
    typed.require(profile.sha(template/'image-root-receipt.json')==binding['image_root_receipt_sha256'] and
        profile.sha(variant/'image-root-receipt.json')==binding['image_root_receipt_sha256'],
        'saved accepted receipt metadata changed')
    expected_report=dict(generic,auto_cycle_variant=True,auto_cycle_token=row['cycle'],auto_cycle_template=str(template),
        auto_cycle_template_report_sha256=row['template_report_sha256'],auto_cycle_template_image_sha256=generic['image_sha256'],
        image_sha256=row['bound_image_sha256'],image_expectation_patched=True)
    expected_report['type3_materialization']=typed.materialization(generic,row['cycle'],generic['image_sha256'],row['bound_image_sha256'],row['template_report_sha256'])
    typed.require(original==expected_report and profile.sha(variant/'device-profile.json')==row['template_profile_sha256'] and
        original['effective_config_sha256']==row['variant_config_sha256'] and
        profile.sha(variant/'kernel-readonly-compact.json')==old['compact_manifest_sha256'],
        'saved variant differs outside its already-completed fixed materialization')
    typed.require(profile.sha(Path(old['backup'])/'backup-manifest.json')==old['backup_manifest_sha256'] and
        profile.sha(Path(old['current_packages'])/'package-result.json')==old['current_package_result_sha256'],
        'saved backup/current predecessor metadata differs')
    pair=profile.read(Path(old['current_packages'])/'package-result.json')
    import retained_v108_origin as retained
    with retained.read_scope():retained.origin(pair)
    typed.require(pair.get('backup_manifest_sha256')==old['backup_manifest_sha256'] and
        any(p.get('mode')=='diagnostic' and p.get('payload_sha256')==old['current_boot_sha256'] for p in pair.get('packages',[])),
        'exact current v108 BOOT predecessor required')
    return dict(contract=row,old=old,template=template,variant=variant,generic=generic,report=original,host=host,
        binding=dict(schema=SCHEMA,contract_path=str(path),contract_sha256=expected,packaging_host=host))


def checked_binding(binding):
    from linux_data_carrier import require
    require(type(binding) is dict and set(binding)=={'schema','contract_path','contract_sha256','packaging_host'} and binding['schema']==SCHEMA,
        'closed separate packing provenance required')
    context=load(binding['contract_path'],binding['contract_sha256'])
    require(context['binding']==binding,'separate live packing-host closure differs')
    return context


@contextmanager
def _scope(context):
    token=_ACTIVE.set(context)
    try:yield context
    finally:_ACTIVE.reset(token)


def saved_metadata(root,token=None,template=None):
    import sha256_kat_device_profile as profile
    from linux_data_carrier import require
    context=_ACTIVE.get();require(context is not None,'retained f39 template/variant requires reviewed remaining-pack context')
    root=profile.private(root);generic=root==context['template'];row=context['generic'] if generic else context['report']
    require(generic or root==context['variant'],'remaining-pack may read only its exact saved template/variant')
    pin='template_report_sha256' if generic else 'variant_report_sha256'
    require(profile.sha(root/'build-result.json')==context['contract'][pin] and
        profile.sha(root/'handoff.config')==context['contract']['variant_config_sha256'],'retained saved metadata/config changed')
    if not generic:require(token==context['contract']['cycle'] and (template is None or profile.private(template)==context['template']),
        'retained materialized cycle/template differs')
    return dict(row)


def plan_reader(function):
    @wraps(function)
    def checked(path,expected,*args,**kwargs):
        import sha256_kat_device_profile as profile
        from linux_data_carrier import require
        path=profile.private(path)
        require(re.fullmatch('[0-9a-f]{64}',expected or '') and profile.sha(path)==expected,'reviewed KAT plan SHA required')
        plan=profile.read(path)
        if FIELD not in plan:return function(path,expected,*args,**kwargs)
        context=checked_binding(plan[FIELD])
        require(profile.private(path)==Path(context['contract']['output'])/'plan.json','remaining-pack plan path differs')
        with _scope(context):return function(path,expected,*args,**kwargs)
    return checked



def require_pack(root,output,cycle):
    import sha256_kat_device_profile as profile
    from linux_data_carrier import require
    context=_ACTIVE.get()
    require(context is not None,'retained f39 cannot pack outside its reviewed remaining-stage transaction')
    saved_metadata(root,cycle)
    destination=Path(context['contract']['output'])
    journal=profile.read(destination/'transaction.json')
    require(profile.private(output)==destination/'cycle-01/boot.img' and journal.get('schema')=='type3-remaining-pack-journal-v1' and
        journal.get('status')=='started' and journal.get('phase')=='pack_reserved' and
        journal.get('contract_sha256')==context['binding']['contract_sha256'] and
        journal.get('attempts')==dict(BOOT_packings=1,package_pair_builds=0,plans=0,intrinsic_variant_data_consumptions=1,intrinsic_packer_compact_validations=1) and journal.get('device_operations')==[],
        'one exact fresh remaining-pack reservation required')


def package_scope(row):
    import sha256_kat_device_profile as profile
    from linux_data_carrier import require
    require(FIELD in row,'retained f39 packages require separate reviewed live packing provenance')
    context=_ACTIVE.get()
    if context is None:context=checked_binding(row[FIELD])
    require(row[FIELD]==context['binding'] and all(row.get(key)==value for key,value in profile.fields(context['report']).items()),
        'remaining-pack package/retained variant provenance differs')


def plan_pair(plan,pair,bound,path):
    import sha256_kat_device_profile as profile
    from linux_data_carrier import require
    context=_ACTIVE.get()
    require(context is not None and plan[FIELD]==pair.get(FIELD)==context['binding'] and bound==context['report'] and
        profile.private(path)==Path(context['contract']['output'])/'plan.json' and plan['kernel_build']==str(context['template']) and
        plan['stages'][0]['kernel_build']==str(context['variant']) and plan['stages'][0]['cycle']==context['contract']['cycle'] and
        plan['backup']==context['old']['backup'] and plan['current_packages']==context['old']['current_packages'] and
        plan['current_package_result_sha256']==context['old']['current_package_result_sha256'] and
        plan['current_boot_payload_sha256']==context['old']['current_boot_sha256'],
        'remaining-pack plan must preserve exact saved template/variant/current lineage')


def prepare(path,expected):
    import sha256_kat_device_profile as profile
    import type3_admission as typed
    from prepare_linux_boot import prepare as pack
    from build_boot_test_packages import build
    from stage_phase2 import verify_packages
    context=load(path,expected);contract=context['contract'];old=context['old'];output=Path(contract['output'])
    typed.require(not output.exists(),'remaining-pack reservation already exists; cannot restart')
    output.mkdir(parents=True)
    # This reservation includes only the existing packer's saved-variant DATA read/validation.
    # It does not reopen/attach the original compact source or copy/materialize another variant.
    journal=dict(schema='type3-remaining-pack-journal-v1',status='started',phase='pack_reserved',contract_sha256=expected,
        attempts=dict(BOOT_packings=1,package_pair_builds=0,plans=0,intrinsic_variant_data_consumptions=1,intrinsic_packer_compact_validations=1),device_operations=[])
    profile.save(output/'transaction.json',journal)
    try:
        with _scope(context):
            boot=output/'cycle-01/boot.img';boot.parent.mkdir()
            report=pack(Path(old['backup']),context['variant'],Path(old['reference_twrp']),Path(old['mkbootimg']),boot,contract['cycle'])
            report[FIELD]=context['binding'];profile.save(boot.with_suffix('.json'),report)
            journal.update(phase='packages_reserved');journal['attempts']['package_pair_builds']=1;profile.save(output/'transaction.json',journal)
            packages=boot.parent/'packages';build(Path(old['backup']),boot,packages,Path(old['current_packages']))
            current=next(p for p in verify_packages(Path(old['current_packages'])) if p['mode']=='diagnostic')
            journal.update(phase='plan_reserved');journal['attempts']['plans']=1;profile.save(output/'transaction.json',journal)
            result=profile.finish_plan(context['template'],Path(old['backup']),Path(old['reference_twrp']),Path(old['mkbootimg']),
                Path(old['current_packages']),output,context['generic'],context['variant'],context['report'],contract['cycle'],packages,current,
                extra={FIELD:context['binding']})
        journal.update(status='complete',phase='complete',result=result);profile.save(output/'transaction.json',journal)
        return dict(result,transaction=str(output/'transaction.json'),native_version='v109',execution_version='v110',remaining_caps=CAPS,
            immutable_saved_variant=True,device_operations=[])
    except BaseException as error:
        journal.update(status='failed_no_restart',error_type=type(error).__name__);profile.save(output/'transaction.json',journal)
        raise


def execution_context(row,plan_sha,packages,declared_version,host_head,path,expected,execution_output):
    import type3_admission as typed
    import sha256_kat_device_profile as profile
    typed.require(FIELD in row,'retained f39 cannot stage without separate remaining-pack lineage')
    origin(row);typed.candidate_scope(row,patched=True)
    context=checked_binding(row[FIELD]);contract=context['contract'];old=context['old'];output=Path(contract['output'])
    completed=profile.read(output/'transaction.json');plan_path=output/'plan.json'
    typed.require(completed.get('schema')=='type3-remaining-pack-journal-v1' and completed.get('status')=='complete' and
        completed.get('phase')=='complete' and completed.get('contract_sha256')==row[FIELD]['contract_sha256'] and
        completed.get('attempts')==dict(BOOT_packings=1,package_pair_builds=1,plans=1,intrinsic_variant_data_consumptions=1,intrinsic_packer_compact_validations=1) and completed.get('device_operations')==[] and
        completed.get('result',{}).get('plan_sha256')==plan_sha and profile.sha(plan_path)==plan_sha,
        'exact remaining-pack transaction must complete before transport')
    plan=profile.read(plan_path);item=plan['stages'][0];saved=context['report']
    typed.require(plan.get(FIELD)==row[FIELD] and item['kernel_build']==str(context['variant']) and
        item['build_result_sha256']==contract['variant_report_sha256'] and item['image_sha256']==contract['bound_image_sha256'] and
        item['cycle']==contract['cycle'] and item['packages']==str(profile.private(packages)) and
        all(row.get(key)==value for key,value in profile.fields(saved).items()),'remaining plan/packages/immutable variant lineage differs')
    typed.require(path is not None and re.fullmatch('[0-9a-f]{64}',expected or ''),'explicit remaining-pack device contract required')
    path=profile.private(path);raw=typed.data.bounded_private_read(path,65536)
    typed.require(typed.sha(raw)==expected,'exact reviewed remaining-pack device contract SHA required')
    device=json.loads(raw.decode('utf-8-sig'))
    keys={'schema','status','execution_version','producer_host_source_head','packaging_host_source_head','native_source_head','plan_sha256',
        'packages','package_result_sha256','bound_image_sha256','offline_contract_sha256','remaining_contract_sha256','output',
        'minimum_battery','BOOT_write_max','reboot_max','user_availability_record_sha256'}
    typed.require(type(device) is dict and set(device)==keys and device['schema']==DEVICE_SCHEMA and device['status']=='reviewed_ready' and
        declared_version==device['execution_version']=='v110' and device['producer_host_source_head']==HEAD and
        device['packaging_host_source_head']==host_head==contract['packaging_host_source_head'] and
        device['native_source_head']==contract['native_source_head'] and device['plan_sha256']==plan_sha and
        device['packages']==str(profile.private(packages)) and execution_output is not None and
        device['output']==str(profile.private(execution_output)) and not profile.private(execution_output).is_relative_to(profile.private(packages)) and
        device['bound_image_sha256']==contract['bound_image_sha256'] and device['offline_contract_sha256']==contract['original_contract_sha256'] and
        device['remaining_contract_sha256']==row[FIELD]['contract_sha256'] and device['minimum_battery']==10 and type(device['minimum_battery']) is int and
        device['BOOT_write_max']==1 and type(device['BOOT_write_max']) is int and device['reboot_max']==1 and type(device['reboot_max']) is int and
        device['user_availability_record_sha256']=='4a639d278836af88256a339d199b9fbe53ad65d354db4b8c4401796522e758e9',
        'closed separate remaining-pack device/producer/live-host scope differs')
    typed.require(profile.sha(profile.private(packages)/'package-result.json')==device['package_result_sha256']==item['package_result_sha256'],
        'reviewed remaining-pack package manifest changed')
    return dict(schema=CONTEXT_SCHEMA,declared_version=declared_version,host_source_head=host_head,plan_sha256=plan_sha,
        packages=str(profile.private(packages)),output=str(profile.private(execution_output)),contract_path=str(path),contract_sha256=expected,
        remaining_pack=row[FIELD])


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--contract',type=Path,required=True);parser.add_argument('--contract-sha256',required=True)
    # Call the canonical module so downstream imports share its transaction ContextVar.
    from type3_remaining_pack import prepare as canonical_prepare
    args=parser.parse_args();print(json.dumps(canonical_prepare(args.contract,args.contract_sha256),indent=2))
