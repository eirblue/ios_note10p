"""Closed accepted native109 origin; native107 historical constants stay separate."""
from types import MappingProxyType
import re
import kernel_readonly_span_candidate as ro3
import linux_data_carrier as data

_NATIVE109=MappingProxyType({
    "artifact_id": 13253663808,
    "attempt": 1,
    "head": "f20987a42249e61ef028c52099931f740d9a6cc5",
    "image_bytes": 50870284,
    "job_id": 126071943919,
    "kind": "kernel-readonly-stage-witness-candidate",
    "linked_bytes": 59588608,
    "outcome_bytes": 128,
    "pins": {
        ".github/workflows/note10-builtin-init-route.yml": "c135fb22c04e0fa085b3092c23af369f10070d6560e6ccaf0c005c71a1b134b6",
        ".github/workflows/note10-linux-data-carrier.yml": "f01c86bdbd2f9f702465430a9ee8703177cfdda8e1076612b842f09fb6a210aa",
        "note10/device_test/auto_cycle.py": "113c067e8b692b9c08108c08cc08c8b9da6c2c87b3672aca097b4b6f9f910e0d",
        "note10/device_test/auto_return.c": "9ec43d3d17f12fe90d2ab36e4712537b7f8275f6f27b6536bbef826f9692037d",
        "note10/device_test/build_boot_test_packages.py": "17b973f54185521be6685acb5e019f8bf8b5f10897d01c0167929c97859cddef",
        "note10/device_test/build_builtin_init_image.py": "230bfad069d1c94ad4743649f198f670473f07944261bd7a05b73a30194ba84c",
        "note10/device_test/build_kernel_readonly_span_candidate.py": "c9b44d314719e2f59e69541c2d6618777f616f468e9ca11b5f12d18dcec0f3a0",
        "note10/device_test/build_linux_data_carrier.py": "44f083e2168716b33cea4111ab303c83f5fda5136dd99f54f32c2521a2f25d98",
        "note10/device_test/build_sha256_kat_recovery.py": "2f84ba60d3b0a582d015c2d6c1955aae8a8a4e785b575da5d2af6ebf293ab123",
        "note10/device_test/build_sha256_runtime_kat.py": "d76c33333a67d6af4bc7c0d8caf0b0868f8e5d63e1c585f6def2860dfe4bbdff",
        "note10/device_test/build_xnu_runtime_plan_component.py": "367f9147d50950dffb47bf83861787dce4a1be47225b11b070e2f60de45c6b6e",
        "note10/device_test/builtin_init_profile.py": "e196c7143cbd7aa55ded754a8381791efeff2974c03436e61c3f50454117e3bf",
        "note10/device_test/builtin_init_route.c": "2fb12577bfd332cd83c3e497aa5930c275983e0f9139d22f53b009b0a9249d74",
        "note10/device_test/builtin_init_route.py": "46b100dc95f11e344c11b8cb3fba5d34d17b2884385923426a42246699fda43d",
        "note10/device_test/builtin_init_route_fixture.c": "e6c586d479175eae9ba2496b886ff504e584aadf53b2fb3816f64e839a2be6e7",
        "note10/device_test/builtin_minimal_init.S": "ca8ad494643331a3065b25f0e62330dce4c7385a354bac71e75a972627a6ad60",
        "note10/device_test/bundle_affinity_evidence.py": "b292f0cd45df8b8ef110146315520a857c388d52f9b2e69a0812a3ae8f4253dc",
        "note10/device_test/carrier_lzma.c": "e204732754f15929f7134885ec2740e1ed26f0291dd64c7df7957a4aee7b987a",
        "note10/device_test/carrier_lzma.h": "6790aa17da94025e0bab175377573edb8df3f503c8cde86f8c919e33ee742974",
        "note10/device_test/decode_reservation.py": "c60e3f8cb399d6f62e61531ddf8c15aacbeaa87ea7d6c897e8953f3e62f1c971",
        "note10/device_test/decode_sha256_runtime_kat.py": "c83437aae48ee4f1d7400edf73933c8b0102291934648a30387100ef187f42b9",
        "note10/device_test/early_fdt_binding.py": "d4f7099fb45eca31c83c9acd9fbfe0cd5c7ccc5c271c18180e3672e22f9a6b78",
        "note10/device_test/kernel_readonly_input.py": "3c798d53cdea11c486c29287e407288708bb25b3aac3f148a6b4e67501062e73",
        "note10/device_test/kernel_readonly_span.h": "dd0640b8322fb86c8baa29863a931ddb7d005dd589352ba4136c09bdb79de86d",
        "note10/device_test/kernel_readonly_span_candidate.h": "8f8e8522a7b03413b3db59f21fca5cefa4b74fb9e63a412dfc9d6067beb5dec1",
        "note10/device_test/kernel_readonly_span_candidate.py": "f79f3c641682ac978a31c1862b4c66f8151e8fd14d1888c9f3992e4606e15ce6",
        "note10/device_test/kernel_readonly_span_candidate_fixture.c": "b4d02ff71b82365915fca0c112170de9c44184dcce481656832e69e77dee9f29",
        "note10/device_test/linux_data_carrier.c": "53b29fb87158183a0911596820e2f768d15059a5908c7434fa2ca6796e8d0259",
        "note10/device_test/linux_data_carrier.py": "40a1713839994bf8c0a3fc6c81822775ea36476cfb56a1da300bf59aced8dc52",
        "note10/device_test/linux_data_carrier_composition.c": "2eb666597983d3a2dfb0a4f98da26dc02dff287db49d39756ada6edc90e0c667",
        "note10/device_test/linux_data_carrier_fixture.c": "6b1b0e14184582c734a3154eeef6c0e2736fd1b8ef3491881b7decaacb5ecbe4",
        "note10/device_test/linux_data_compare_evidence.h": "3383823cf1fd56f688ad9d6823d965fdda270a08acede17f6df8d87fa6199438",
        "note10/device_test/linux_data_early_prefix.h": "60fb29d56be78212e04cc164938db4a25296fdea5250e372824b317127aaeb98",
        "note10/device_test/linux_data_early_prefix_fixture.c": "b058ccfa33fccadfa2547986a724b21dd7de0b781e003cd3ca1c71fddfe36f09",
        "note10/device_test/linux_data_growth.h": "640ae63bd927d205ad8bc489c4c7b25935f1c4311332dce5d10821acf3ac0746",
        "note10/device_test/linux_data_growth_fixture.c": "d567edfc28efc1b258eff93a72dda94d8f24af00297b315b1f7d371c7d77066a",
        "note10/device_test/linux_data_input_probe_fixture.c": "c7192b0515eb7de9526291913ef97737207844a45d266a4e1287437f49b3e0b4",
        "note10/device_test/linux_data_input_range.h": "c53f208c886ba21af0f22d266a1edb1de0f42a3e40d5a68080a41fcf775d4dac",
        "note10/device_test/linux_data_input_range_fixture.c": "d3c7695b319963b9d6de679a5eadaf107c4dc667e610b892f2953a390854ecd5",
        "note10/device_test/materialize_auto_cycle.py": "aab1e4e1560c43b2731f875067d5eddb8c43ee815a15b96e41ed83250c682e36",
        "note10/device_test/pre_pm_archive_contract.py": "966a5b032e516ecc984defc9b0313192667d4f4585511fa232966ce79ac3b5c5",
        "note10/device_test/prepare_linux_boot.py": "ae0f41cb5284110680e232a4a830415022a7cb6a1f10312be2dfb3bea0194772",
        "note10/device_test/prepare_sha256_kat_recovery.py": "921dd3cade033e21e50994c1b8036d8067bb77c8f9372454c9290673aa7d4b91",
        "note10/device_test/prepare_sha256_runtime_kat.py": "5f56dfb7d77acc2b998122022b65421a5e34f73d52be446a677ff333b5d5e5c2",
        "note10/device_test/prepare_xnu_runtime_plan.py": "6b9b21ab93f3b49ef43e947a26ad1985d2f11bbd94002e30fcf6dcca875ac41c",
        "note10/device_test/readonly_stage_witness.h": "85851db4c9622842f4ccc547e7532139f306917d8674c0298529e5041fb08330",
        "note10/device_test/readonly_stage_witness.py": "c0db55ec9bed5fa8803efd03fd05ecbe93f3cb97705ce83f66ea3161e3cb62f7",
        "note10/device_test/readonly_stage_witness_fixture.c": "2513117dd52b2c8ef92a6f0c161af3a2e1fe6060e24dc9b166d187c5a3fd0cec",
        "note10/device_test/retained_v108_origin.py": "737e3de25884daee64e8dc4d938b81e5b2f328a5923a4b6cea0b2c92b0db24f7",
        "note10/device_test/sealed_affinity_artifact.cjs": "08c17edb82357d5719fbccd2427fca1970c09f6b3ee7aef91d6034f7d12f70ec",
        "note10/device_test/sha256_builtin_init.c": "11408b9dba36f56137f5d411d9a77eaf72db71cadfec9b406f85fcfc3d3cd6e4",
        "note10/device_test/sha256_kat_device_profile.py": "8f6805cc558fdc54504e242e9db083efecfc226cbd758a7825e4d9a0256af777",
        "note10/device_test/sha256_kat_recovery.c": "5b26ec7dca0a936bcebf1860cddb42a0b24806b9f3a7c09bfdf06d8edf27d1bf",
        "note10/device_test/sha256_kat_recovery_work.c": "a39e955e0a104251434fed69e137687e0f24876f63e1f496f401d95acf119859",
        "note10/device_test/sha256_runtime_kat.c": "58470621def88390f16d2608989bafac76ff6d502bb211d400d2b488ed5df5ca",
        "note10/device_test/stage_phase2.py": "9df734fa4227bb2b9a34953ad286a24ca8ecb43d98fc7b5a79548cd3bd99cab1",
        "note10/device_test/test_builtin_init_route.py": "9fa63dd55114472a748062447dd95c17bf4d4d7e743117f69f0bb6a7aca6ea42",
        "note10/device_test/test_linux_data_carrier.py": "550344e818b42f8147ea1f688929feda322c68173f79f6e72850053dbc2e1ca7",
        "note10/device_test/test_v100_carrier_input_probe.py": "f8e37cb2da1fc1efda5582079bb619d8853565d892a589872d0699277e8c4489",
        "note10/device_test/test_v101_live_input_range.py": "e4424b6128a18f4099b31ddc6dcf16ba6256749ba2a87f8bd565b68a1ef68183",
        "note10/device_test/test_v102_input_lifetime.py": "29cdae5c4b8ace788ad84f529700d753bcb19c9d4a34697bddf8ca7dfa80bed1",
        "note10/device_test/test_v104_growth_region.py": "89ca671ca695b083ccf9cb58c6f474acfeadb9a67ff9747d640cc533dde40e7d",
        "note10/device_test/test_v107_readonly_span_candidate.py": "10a3f90b475eda8dcaace92cb1dd387ba0ba6198316773f0212b578d51a1d64c",
        "note10/device_test/test_v108_type3_admission.py": "6c2e02ac70f187bd315f4f34dbb66266512c7cd5d07b765594079bafbc10cb30",
        "note10/device_test/test_v109_readonly_stage_witness.py": "33da915026b259cd267705a9a477ebbdf670581cbb8fed6fb604a1870c078684",
        "note10/device_test/type3_admission.py": "0f1ebf8a395b339bf75b3b3459b8cae27a1fdb27b904d4f6c590c5217a75638e"
    },
    "result": "86e9d58a8700f47496ae5c333d7bffa0ccca4606e33eda09b1307dd92b709d74",
    "run_id": 41680318368,
    "state_bytes": 88,
    "version": "v109",
    "witness_schema": "n10-readonly-stage-witness-candidate-v1"
})
_NATIVE109=MappingProxyType(dict(_NATIVE109,pins=MappingProxyType(dict(_NATIVE109['pins']))))
_CONTEXT_KEYS=frozenset(('schema', 'native_version', 'native_source_head', 'accepted_result_sha256', 'source_sha256', 'source_manifest_sha256', 'run_id', 'run_attempt', 'job_id', 'workflow_id', 'repository', 'workflow_ref', 'run_conclusion', 'job_conclusion', 'artifact_id', 'authenticated_plaintext_zip_sha256', 'producer_result_file_sha256', 'generic_image_sha256', 'Image_bytes', 'candidate_contract', 'root_PC_acceptance_sha256', 'operator_metadata_sha256', 'operator_projection_sha256', 'current_host_method', 'carried_fixture', 'both_methods_executed_at_current_source', 'native_Image_executed', 'producer_physical_ready', 'producer_admission_blocked', 'global_RAM_ownership_or_hardware_mapping_attested'))


def new_kind():return _NATIVE109['kind']
def stage_selected(row):
    return any(row.get(key)==new_kind() for key in ('diagnostic_kind','data_input_kind','storage_input_kind')) or 'readonly_stage_schema' in row

def selected(row):return stage_selected(row) or row.get('data_input_kind')==ro3.KIND

def record(head):
    if head==_NATIVE109['head']:return _NATIVE109
    data.require(head==ro3.NATIVE_HEAD,'unaccepted native class3 source')
    return dict(head=ro3.NATIVE_HEAD,version='v107',result=ro3.NATIVE_RESULT_SHA256,pins=dict(ro3.NATIVE_PINS),kind=ro3.KIND)

def origin(head):
    item=record(head)
    return dict(source_head=item['head'],accepted_result_sha256=item['result'],source_sha256=dict(item['pins']),native_version=item['version'])

def provenance():
    return dict(version='v109',PC_first_use=True,PC_only=False,operation_scope_PC_only=True,physical_ready=False,admission_blocked=True)

def stage_fields():
    return dict(readonly_stage_schema=_NATIVE109['witness_schema'],readonly_stage_marker='N10DATASTAGE1',native_producer_provenance=provenance())

def live_host(head):
    from retained_v108_origin import live
    live(head)
    from type3_remaining_pack import HEAD as stopped_host
    data.require(head!=stopped_host,'stopped f39 host may only supply its reviewed saved read-origin')
    data.require(head not in (_NATIVE109['head'],ro3.NATIVE_HEAD),'native producer cannot be relabeled live host110')

def live_row(row):
    data.require(row.get('native_source_head')==_NATIVE109['head'] and row.get('source_head')==_NATIVE109['head'] and
        row.get('execution_version')==row.get('version')=='v110' and row.get('data_input_kind')==new_kind(),
        'live host110 requires the exact accepted native109 candidate')
    live_host(row.get('host_profile_source_head'))

def producer(result,head):
    item=record(head)
    data.require(head==_NATIVE109['head'] and result.get('source_sha256')==dict(item['pins']) and
        result.get('version')==item['version'] and result.get('diagnostic_kind')==item['kind'] and
        result.get('image_bytes')==item['image_bytes'] and result.get('kernel_readonly3_linked_bytes')==item['linked_bytes'] and
        result.get('data_footprint',{}).get('data_state_bytes')==item['state_bytes'],
        'exact accepted native109 producing tuple required')
    accepted=ro3.producer_contract(result,head,producing_sources=dict(item['pins']))
    data.require(accepted['temporary_outcome_bytes']==item['outcome_bytes'] and result.get('kernel_readonly3_candidate_contract')==accepted,
        'native109 accepted compiler contract differs')
    return accepted

def banner(row):
    return 'Linux version 4.14.113-v109-readonly-stage-witness-candidate ' if stage_selected(row) else 'Linux version 4.14.113-v107-readonly-span-candidate '

def ci_receipt(context,context_sha,binding,result):
    item=_NATIVE109;producer(result,item['head'])
    data.require(type(context) is dict and set(context)==_CONTEXT_KEYS and
        context['schema']=='note10-root-native109-ci-success-context-v1' and context['native_version']=='v109' and
        context['native_source_head']==binding['source_head']==item['head'] and
        context['accepted_result_sha256']==context['producer_result_file_sha256']==binding['accepted_result_sha256']==item['result'] and
        context['source_sha256']==dict(item['pins']) and context['run_id']==item['run_id'] and context['run_attempt']==item['attempt'] and
        context['job_id']==item['job_id'] and context['artifact_id']==item['artifact_id'] and context['workflow_id']==404040749 and
        context['repository']=='eirblue/ios_note10p' and context['workflow_ref']=='eirblue/ios_note10p/'+ro3.WORKFLOW+'@refs/heads/main' and
        context['run_conclusion']==context['job_conclusion']=='success' and context['Image_bytes']==binding['image_size']==item['image_bytes'] and
        context['generic_image_sha256']==binding['image_sha256']==result['image_sha256'] and
        binding['effective_config_sha256']==result.get('files_sha256',{}).get('actual-effective.config') and
        binding['build_evidence_id']==result.get('build_evidence_id') and
        binding['kernel_banner'].startswith(banner(binding)) and context['candidate_contract']==result['kernel_readonly3_candidate_contract'] and
        context['both_methods_executed_at_current_source'] is False and context['native_Image_executed'] is False and
        context['producer_physical_ready'] is False and context['producer_admission_blocked'] is True and
        context['global_RAM_ownership_or_hardware_mapping_attested'] is False and re.fullmatch('[0-9a-f]{64}',context_sha or ''),
        'closed native109 accepted CI context differs')
    data.require(all(type(context[key]) is int and context[key]>0 for key in ('run_id','run_attempt','job_id','artifact_id','workflow_id','Image_bytes')) and
        all(re.fullmatch('[0-9a-f]{64}',context.get(key,'') or '') for key in ('source_manifest_sha256','authenticated_plaintext_zip_sha256',
            'root_PC_acceptance_sha256','operator_metadata_sha256','operator_projection_sha256')),'native109 CI metadata types/pins differ')
    host=context['current_host_method'];fixture=context['carried_fixture']
    data.require(type(host) is dict and host.get('passed') is True and host.get('run')==1 and host.get('errors')==host.get('failures')==0 and
        host.get('selected')==['test_closed_witness_and_retained_v108_read_scope'] and
        host.get('fixture_compiles')==host.get('fixture_processes')==host.get('old_test_methods_run')==host.get('real_decoder_calls')==host.get('actual_private_input_reads')==0 and
        type(fixture) is dict and fixture.get('source_head')=='595bc927f39424bbe659deef2957b90ec4a13091' and
        fixture.get('run_id')==41676621074 and fixture.get('job_id')==126058869018 and fixture.get('cases')==12 and
        fixture.get('fixture_compiles')==fixture.get('fixture_processes')==1 and fixture.get('replayed_in_rev1') is False and
        fixture.get('overall_prior_CI_conclusion')=='failure' and fixture.get('specific_method_passed') is True and
        fixture.get('passed_method')=='test_actual_class3_stage_witness_and_existing_cleanup' and
        fixture.get('native_dependencies')=={name:item['pins']['note10/device_test/'+name] for name in
            ('linux_data_carrier.c','readonly_stage_witness.h','readonly_stage_witness_fixture.c')},'native109 distinct method provenance differs')
    return dict(schema='native109-root-ci-receipt-v1',kind=binding['device_profile']+'-accepted-image',accepted=True,
        root_reader_result_sha256=context_sha,producer_source_head=item['head'],ci_result_sha256=item['result'],
        image_sha256=binding['image_sha256'],image_bytes=binding['image_size'],effective_config_sha256=binding['effective_config_sha256'],
        build_evidence_id=binding['build_evidence_id'],kernel_banner=binding['kernel_banner'],native_origin=origin(item['head']),
        current_host_method=host,carried_fixture=fixture,run_id=item['run_id'],attempt=item['attempt'],job_id=item['job_id'],
        workflow_id=404040749,artifact_id=item['artifact_id'],authenticated_plaintext_zip_sha256=context['authenticated_plaintext_zip_sha256'])


def receipt_binding(root,row,expected,binding):
    from sha256_kat_device_profile import read,sha
    context=read(root/'ci-success-context.json');context_sha=sha(root/'ci-success-context.json')
    data.require(row==ci_receipt(context,context_sha,binding,read(root/'result.json')),'native109 stored CI receipt differs')
    return dict(image_root_receipt_sha256=expected,root_reader_result_sha256=context_sha)
