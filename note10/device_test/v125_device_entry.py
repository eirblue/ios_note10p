"""Exact completed124 metadata is read-only; live126 execution is separate."""
from contextlib import contextmanager
from contextvars import ContextVar
from functools import wraps
from pathlib import Path
from types import MappingProxyType
import copy
import json
import re
import linux_data_carrier as data
HEAD='bb8f7b65e6b08b07caff750fdb154a2619099230'
PINS=MappingProxyType({'note10/device_test/affinity_binding.py': '6d5b16d54a803c95bdd391a38efbd2bac5ef36baffe199f86cd83f878bf10678', 'note10/device_test/auto_cycle.py': '67dea1c955df86da0c0e9aa8790e91f486fbc001b32c0e070c96e454aa50b5c5', 'note10/device_test/build_boot_test_packages.py': '5a6401feb0418e6bab6859dca20cfe36c644277ad4fc65e9cc5a8448e1037d64', 'note10/device_test/build_kernel_readonly_input.py': '5391edfa477324dbdd5f4d9c6fb13deb5df8a66b2ed4df7d018213012b227000', 'note10/device_test/build_kernel_readonly_span_candidate.py': '7ebcce1d50932d59d431f4be417c3637d18570b19b7b735f9543af2f9e1b2b75', 'note10/device_test/build_kernel_readonly_span_pc.py': 'cd42e0dec6570bcc09c7a07695560eae13a62420d744e16035c4da3a57c588e9', 'note10/device_test/build_readonly_input_pc.py': '893698f6741fd178334777b4f96c98934d78b5a927fe4cf3d383d92e90557d9e', 'note10/device_test/builtin_init_profile.py': '88b655785cd5cbc88265d003d829639ca63be4c0f20dad687e930f6981b38af3', 'note10/device_test/builtin_init_route.py': '46b100dc95f11e344c11b8cb3fba5d34d17b2884385923426a42246699fda43d', 'note10/device_test/carrier_lzma.c': 'e204732754f15929f7134885ec2740e1ed26f0291dd64c7df7957a4aee7b987a', 'note10/device_test/carrier_lzma.h': '6790aa17da94025e0bab175377573edb8df3f503c8cde86f8c919e33ee742974', 'note10/device_test/class3_native_origin.py': 'c739ce85dd586b959d74156a1005cd15ec6419ae3d29d7ed9b0ee98d3b2e334a', 'note10/device_test/current_data_reuse.py': '15c7a5a55e22f4445c216904769d7ba9b6367f792122e5b936305c95ae031129', 'note10/device_test/early_fdt_binding.py': 'd4f7099fb45eca31c83c9acd9fbfe0cd5c7ccc5c271c18180e3672e22f9a6b78', 'note10/device_test/kernel_readonly_input.h': '4aa99ff2ab756b854174eb2519af96e79669f82114293790a538ddd3025298ea', 'note10/device_test/kernel_readonly_input.py': '8920a316c0ce45b5ab5989e239cfa79282f3afc78ce63e320ade82676f081f83', 'note10/device_test/kernel_readonly_input_fixture.c': '6300f13ba284b4f42614a4c6cda8f09c6e6671e88d6e524ec24dacd3a7ab70e0', 'note10/device_test/kernel_readonly_span.h': 'dd0640b8322fb86c8baa29863a931ddb7d005dd589352ba4136c09bdb79de86d', 'note10/device_test/kernel_readonly_span_candidate.h': '8f8e8522a7b03413b3db59f21fca5cefa4b74fb9e63a412dfc9d6067beb5dec1', 'note10/device_test/kernel_readonly_span_candidate.py': 'f4ed3e0f81d9b3d1dafdcf2fdcfa416d1abb54df8dbd4765a989df1c5e0150f8', 'note10/device_test/kernel_readonly_span_candidate_fixture.c': 'b4d02ff71b82365915fca0c112170de9c44184dcce481656832e69e77dee9f29', 'note10/device_test/kernel_readonly_span_fixture.c': 'afbc9ae410e15bf7221e10a4cbcb325702a3a0235dec0fe585b836e7dae467c6', 'note10/device_test/linux_data_carrier.c': 'a9fd626d384ac6b3fd3d8d705debdc3a1daa34ac1886a51ef8788f57e408c53d', 'note10/device_test/linux_data_carrier.py': '29733dc57cd396a401ed344d7f4a33faed6c383a93c3889f61510a15fcce0ae7', 'note10/device_test/linux_data_carrier_composition.c': '2eb666597983d3a2dfb0a4f98da26dc02dff287db49d39756ada6edc90e0c667', 'note10/device_test/linux_data_carrier_fixture.c': '6b1b0e14184582c734a3154eeef6c0e2736fd1b8ef3491881b7decaacb5ecbe4', 'note10/device_test/linux_data_compare_evidence.h': '3383823cf1fd56f688ad9d6823d965fdda270a08acede17f6df8d87fa6199438', 'note10/device_test/linux_data_compare_evidence_fixture.c': '45a0cdfd8d4bd8df5ffbbb0e370cd05f768d522e96208881a7f7a02ee02fadc3', 'note10/device_test/linux_data_early_prefix.h': '60fb29d56be78212e04cc164938db4a25296fdea5250e372824b317127aaeb98', 'note10/device_test/linux_data_early_prefix_fixture.c': 'b058ccfa33fccadfa2547986a724b21dd7de0b781e003cd3ca1c71fddfe36f09', 'note10/device_test/linux_data_growth.h': '640ae63bd927d205ad8bc489c4c7b25935f1c4311332dce5d10821acf3ac0746', 'note10/device_test/linux_data_growth_fixture.c': 'd567edfc28efc1b258eff93a72dda94d8f24af00297b315b1f7d371c7d77066a', 'note10/device_test/linux_data_input_probe_fixture.c': 'c7192b0515eb7de9526291913ef97737207844a45d266a4e1287437f49b3e0b4', 'note10/device_test/linux_data_input_range.h': 'c53f208c886ba21af0f22d266a1edb1de0f42a3e40d5a68080a41fcf775d4dac', 'note10/device_test/linux_data_input_range_fixture.c': 'd3c7695b319963b9d6de679a5eadaf107c4dc667e610b892f2953a390854ecd5', 'note10/device_test/materialize_auto_cycle.py': 'fc05e3161f13831106e8c75cc5529a1d9ffbc8dab55151f416b0fa184d543b97', 'note10/device_test/native_memory_observation.py': 'f4acd0f310989bfcd1b0c2039fef6e429e8ec4d4f41ebdb94fc483538fa26663', 'note10/device_test/native_prefree_output_admission.py': '9ec5b29bae78e6ebd9d72316aed3e953510df90e55edd7c7e9f5c6168191c5e5', 'note10/device_test/native_prefree_output_zero.py': 'cb580469be605f952bfa0e2b4a884bf9877edb70ebe48e25cf5f3fd5dc2c25f5', 'note10/device_test/native_scoped_output.py': '28567462f0bcb45ba4ed94eb3736bf8ba28c22058262acee0b3f2ffc20496146', 'note10/device_test/native_scoped_output_admission.py': '975564957bba0e5221ae01a7603116d50751861335cb7e3c82455b011cf836bc', 'note10/device_test/precheck_window_access.py': '3ef3859ef2a4c154e93e5db7846bde78eb9061742243dba435187a9087226e28', 'note10/device_test/prepare_linux_boot.py': '0499a630875cb4319e4bdfb33c02d0bac3e31538b24997bac794357b95a5298f', 'note10/device_test/readonly_input_pc.h': '01b18e5fddcd12fba45190baa337b47c3309f54cc7a448cd6d72209c5ba8a3f0', 'note10/device_test/readonly_input_pc.py': 'd7125058dc85a57eb4283fccf87bcb6af96c26de1363f81d1acb0999b94f1fc7', 'note10/device_test/readonly_input_pc_fixture.c': '99f0e7eb9240b5c08314993a14dfcd9a532df0e24158679cdbed8b0c3c752730', 'note10/device_test/readonly_stage_witness.h': '85851db4c9622842f4ccc547e7532139f306917d8674c0298529e5041fb08330', 'note10/device_test/readonly_stage_witness.py': '2d8a4a6affa7e49459e92bd5b2b4ba3787177bf28786c13c3611d8b64f8653b8', 'note10/device_test/readonly_stage_witness_fixture.c': '2513117dd52b2c8ef92a6f0c161af3a2e1fe6060e24dc9b166d187c5a3fd0cec', 'note10/device_test/retained_v108_origin.py': '737e3de25884daee64e8dc4d938b81e5b2f328a5923a4b6cea0b2c92b0db24f7', 'note10/device_test/sha256_kat_device_profile.py': 'e254f3780dca3003c576e0161bf538a6f81d914f0536f151f78eee1bb1e3fc8a', 'note10/device_test/sha256_stream_state.py': '55de2735fb830ae8047bb4a8fa74325f51b766b1e885c482dbbc5ebabe3ea437', 'note10/device_test/sha256_stream_vectors.json': '5c379d1ef41a40b9a1262c985476e9dc0ba88dae7b1586f949bbe79686f2165f', 'note10/device_test/stage_phase2.py': '9df734fa4227bb2b9a34953ad286a24ca8ecb43d98fc7b5a79548cd3bd99cab1', 'note10/device_test/test_affinity_binding.py': 'bf602887c4437e0096473392789da33e3ef502297d8c060faf7d9da9ecd3eb89', 'note10/device_test/test_affinity_ci_context.py': '71aad30ab105a45efe2703fd7b222233836d6e7514560834daa71bfdd351dea9', 'note10/device_test/test_builtin_init_route.py': '9fa63dd55114472a748062447dd95c17bf4d4d7e743117f69f0bb6a7aca6ea42', 'note10/device_test/test_current_data_reuse.py': 'c1a868d4f9669539aee3e4fca4868118db37071467325a85d73c279b2f1d29de', 'note10/device_test/test_early_fdt_binding.py': '2444d3d20b7cc42e705cb89c1d04de72599f7da2a5d1b9282636f3b9990ce1fa', 'note10/device_test/test_early_fdt_host_route.py': '75992eb3e8b1228d0ae3916d47306f0329b7947cb0dfae234ec25c1e737fef6a', 'note10/device_test/test_linux_data_carrier.py': '550344e818b42f8147ea1f688929feda322c68173f79f6e72850053dbc2e1ca7', 'note10/device_test/test_native_memory_observation.py': 'd34e94fd5d964004c42dedd172ec07bd62826b675dcc9f4925ab4ac06c460599', 'note10/device_test/test_partition_gate_evidence.py': 'b7dd52aa5c7747489a2713f805dbe15a6318f3d3776a8043700549e9383bcc72', 'note10/device_test/test_sha256_kat_device_profile.py': 'c48400d5573695d217101806b8481e39aec38fd5382e64b85f999b4cee42c498', 'note10/device_test/test_sha256_stream_state.py': '088881f92037a9895b7947eb44692f51ecba1eb602a02dacc02ff3b94a836db8', 'note10/device_test/test_v100_carrier_input_probe.py': 'f8e37cb2da1fc1efda5582079bb619d8853565d892a589872d0699277e8c4489', 'note10/device_test/test_v101_live_input_range.py': 'e4424b6128a18f4099b31ddc6dcf16ba6256749ba2a87f8bd565b68a1ef68183', 'note10/device_test/test_v102_input_lifetime.py': '29cdae5c4b8ace788ad84f529700d753bcb19c9d4a34697bddf8ca7dfa80bed1', 'note10/device_test/test_v103_readonly_input_pc.py': 'cdce146aed40d9526eae04259e39896f629248f6b395ad8ceeec341cae5be9c5', 'note10/device_test/test_v104_growth_region.py': '89ca671ca695b083ccf9cb58c6f474acfeadb9a67ff9747d640cc533dde40e7d', 'note10/device_test/test_v105_battery5_policy.py': '8871a297d549df482f8888cc53e392f4b5d659e8d93bfa1e3d16f25f9e4d2c0e', 'note10/device_test/test_v105_kernel_readonly.py': '7c1cccbdda3e8df612a0fa7d52870e74d750385b85cff7b2965d236177bb23dd', 'note10/device_test/test_v105_packing_rev1.py': '2402b70737ee2ec9c16fadd0a05b8837d68e5ae364cd1a468c4ac4471a75eabe', 'note10/device_test/test_v106_kernel_readonly_span.py': '0a777ec820cdfb131f5dc725577e88ed8bffc73d1e951aecfa5671414eb1849c', 'note10/device_test/test_v107_readonly_span_candidate.py': '10a3f90b475eda8dcaace92cb1dd387ba0ba6198316773f0212b578d51a1d64c', 'note10/device_test/test_v108_type3_admission.py': '6c2e02ac70f187bd315f4f34dbb66266512c7cd5d07b765594079bafbc10cb30', 'note10/device_test/test_v109_readonly_stage_witness.py': '33da915026b259cd267705a9a477ebbdf670581cbb8fed6fb604a1870c078684', 'note10/device_test/test_v110_native109_admission.py': 'eb9b07328cef3bf3ef7a0c7461df1c89f0e8d3b448d440078df27edc69d0d485', 'note10/device_test/test_v111_device_read_context.py': 'f812dfcfe13d3a75c1f79ac5e636584368aee5a13d894541cd0825ba664a613e', 'note10/device_test/test_v116_native_scoped_output.py': '88ed04c1098e6c299d334bea64fdd40b7a9f691ddec3a9387792dc9045536cf9', 'note10/device_test/test_v117_native_scoped_output_admission.py': '99c953b5f004de2491f448a84227f01af0b711482877796cd5a86c90d1df00c5', 'note10/device_test/test_v118_saved117_remaining_plan.py': 'e24c8fa01cfc3ff1a41ba3f7b7d119c6b682b84e5ef27d56d10f5d9883397d17', 'note10/device_test/test_v119_saved118_device_entry.py': '31bb6bb79189c9bf18bdad7ab5b040d94888fdbed8c4785ae6335ac4810c6dce', 'note10/device_test/test_v122_native_prefree_output_admission.py': '61a619e7188b39daca018655374625d33e25921000349bbc694924f2e0473d0c', 'note10/device_test/test_v123_native121_remaining_template.py': '4a50d09e40c09a9d2fb7bc2599f910bd6e3373d5b53a923569baff5642fbc45d', 'note10/device_test/test_v124_saved123_package_tail.py': '3db145690d28c30a18094db6e5ac62f7553c758473ae3a59b941618f743e6eda', 'note10/device_test/test_v99_carrier_compare_evidence.py': '2b45c21197709706d3f3ffc23e1428084d5d50a93a1d9b5bd22c2693124cf20c', 'note10/device_test/test_v99_host_profile_origin.py': 'fb4a1c349ca298b4f18ba64e0692c7a93e9f0877b2f7a7ec22fa2c8f29ac219a', 'note10/device_test/type3_admission.py': 'd4dbacbe36f6037ba3653ed51ae818557c829ebbb268566720b36d76ed5d66ba', 'note10/device_test/type3_remaining_pack.py': 'd39c393f9c421a59580df7f64a9cc3fe4fe333065d440e981316734030d97dce', 'note10/device_test/type3_remaining_packages.py': 'dba2055a1b493aa20868e531213334804d496f5cd38b34d3cec5bd3ba5aefe4f', 'note10/device_test/type3_remaining_plan.py': '16a9fcbcba505d60731682bdd2704a8a0089dcf29c10bc352509b693f98e3ecc', 'note10/device_test/type3_remaining_template.py': '9b1f8c8e3829d7ff37d825ebda6490eb9e53e81c8a90d5987924537eeb08adcf'})
DEVICE_SCHEMA='note10-native121-saved124-device-v126-v1'
CONTEXT_SCHEMA='native121-saved124-execution-v126-v1'
EXTRA_KEYS=frozenset(('packaging_host_source_head','producer_transaction_sha256','user_availability_record'))
_READ=ContextVar('saved124_device125_read',default=None)
_AUTH=ContextVar('saved124_device125_authority',default=None)

def require(value,message):data.require(value,message)
def private(path):return __import__('type3_admission').private(path)
def read(path):return __import__('type3_admission').read(path)
def sha(path):
    path=private(path)
    require(path.suffix in ('.json','.config','.txt'),'125 metadata reader forbids binary inputs')
    return data.sha(data.bounded_private_read(path,4*1024*1024))

def retained_binding(contract):
    # Only this local loader branch recognizes completed124; global host_binding is unchanged.
    authority=_AUTH.get()
    require(authority is not None and authority['contract']==contract and
        contract['execution_host_source_head']==HEAD and contract['execution_host_source_sha256']==dict(PINS),
        'exact retained124 read-only authority required')
    return dict(host_profile_source_head=HEAD,host_profile_source_sha256=dict(PINS))

def _readiness(c):
    pin=c['user_availability_record']
    require(type(pin) is dict and set(pin)=={'path','sha256'} and pin['sha256']==c['user_availability_record_sha256'] and sha(pin['path'])==pin['sha256'],'reviewed126 user availability record changed')
    r=read(pin['path'])
    required=dict(schema='user-device-ready-from-v125-v1',interpreted_next_diagnostic_version='v125',device_available_from_version=125,current_v124_device_authorized=False,timing_readiness_only_not_battery_override=True,minimum_fresh_battery_percent=10,v105_only_5percent_exception_not_carried=True,fresh_device_identity_five_partition_hashes_paired_restore_and_TWRP_return240_required=True,per_diagnostic_BOOT_write_max=1,per_diagnostic_reboot_max=1,all_spent_cycles_and_journals_no_replay=True,native_Image_template_variant_BOOT_and_package_producing_sources_must_remain_truthful=True)
    require(all(type(r.get(k)) is type(v) and r[k]==v for k,v in required.items()),'user availability125 is not a battery or replay override')

def _load(path,expected,plan_sha,packages,declared,head,output):
    import native_scoped_output_admission as shared
    import native_prefree_output_admission as native
    import type3_remaining_packages as tail
    import sha256_kat_device_profile as profile
    require(declared=='v126' and path is not None and output is not None and re.fullmatch('[0-9a-f]{64}',expected or '') and re.fullmatch('[0-9a-f]{64}',plan_sha or ''),'explicit126 contract/plan/output required')
    path=private(path);require(sha(path)==expected,'reviewed126 device contract SHA differs');c=read(path)
    require(type(c) is dict and set(c)==shared.DEVICE_KEYS|EXTRA_KEYS and c['schema']==DEVICE_SCHEMA and c['status']=='reviewed_ready' and c['execution_version']=='v126','closed126 device contract required')
    effective=private(c['packages'])
    require(packages is None or private(packages)==effective,'supplied packages contradict closed126 contract')
    host=profile.host_binding(head)
    require(head!=HEAD and c['host_source_head']==head and c['host_source_sha256']==host['host_profile_source_sha256'] and c['packaging_host_source_head']==HEAD and c['native_source_head']==native.record()['head'] and c['plan_sha256']==plan_sha and c['packages']==str(effective) and c['output']==str(private(output)),'separate live126/retained124/native121 lineage required')
    require(c['linked_growth_ack']==shared.growth_ack(native.record()['head']) and c['linked_growth_ack'].get('acknowledged') is True and all(type(c['linked_growth_ack'][k]) is int for k in ('reference_linked_bytes','accepted_linked_bytes','delta_bytes')) and all(type(c[k]) is int and c[k]==v for k,v in (('minimum_battery',10),('BOOT_write_max',1),('reboot_max',1))),'126 bounded growth/battery/cycle gates required')
    _readiness(c)
    destination=private(output);producer=effective.parent
    require(not destination.is_relative_to(producer) and not producer.is_relative_to(destination),'fresh126 output must preserve completed124 evidence')
    planpath=producer/'plan.json';require(sha(planpath)==plan_sha,'exact completed124 plan pin required');plan=read(planpath)
    require(plan.get('minimum_battery')==10 and type(plan.get('minimum_battery')) is int and plan.get('return_timeout_seconds')==240 and type(plan.get('return_timeout_seconds')) is int and plan.get('execution_version')=='v124' and plan.get('executing_host_source_head')==HEAD and len(plan.get('stages',[]))==1 and private(plan['stages'][0]['packages'])==effective and plan.get(tail.FIELD,{}).get('operation_host')==dict(host_profile_source_head=HEAD,host_profile_source_sha256=dict(PINS)),'immutable124 producing plan labels required')
    marker=plan[tail.FIELD];contractpath=private(marker['contract_path'])
    require(sha(contractpath)==marker['contract_sha256']==c['offline_contract_sha256'],'completed124 contract pin differs');old=read(contractpath)
    require(private(old['output'])==producer and old.get('execution_host_source_head')==HEAD and old.get('execution_host_source_sha256')==dict(PINS),'exact retained124 contract/map93 required')
    token=_AUTH.set(dict(contract=old))
    try:ctx=tail.load(contractpath,marker['contract_sha256'])
    finally:_AUTH.reset(token)
    jpath=producer/'transaction.json';require(sha(jpath)==c['producer_transaction_sha256'],'completed124 transaction changed');j=read(jpath)
    require(j.get('schema')=='saved123-package-tail-journal-v1' and j.get('status')==j.get('phase')=='complete' and j.get('contract_sha256')==ctx['sha256'] and j.get('caps')==tail.CAPS and j.get('attempts')==j.get('completed')==dict(pairs=1,plans=1) and j.get('device_operations')==[] and j.get('result',{}).get('plan_sha256')==plan_sha and private(j['result']['plan'])==planpath,'completed124 intrinsic plan proof required; no old validation replay')
    pairpath=effective/'package-result.json'
    require(j.get('package_result')==dict(path=str(pairpath),sha256=c['package_result_sha256']) and sha(pairpath)==c['package_result_sha256'],'completed124 paired metadata changed')
    pair=read(pairpath);ctx['pair']=pair;ctx['role_digests']={p['mode']:(p['payload_sha256'],p['payload_size']) for p in pair['packages']}
    stage=plan['stages'][0];template=ctx['old'];bound=ctx['bound']
    require(type(stage) is dict and set(stage)=={'index','cycle','kernel_build','build_result_sha256','image_sha256','packages','package_result_sha256'} and
        type(stage['index']) is int and stage['index']==1 and stage['cycle']==bound['auto_cycle_token'] and
        private(stage['kernel_build'])==ctx['variant_root'] and stage['build_result_sha256']==ctx['contract']['variant_report']['sha256'] and
        stage['package_result_sha256']==c['package_result_sha256'] and
        stage['image_sha256']==c['bound_image_sha256']==bound['image_sha256']==pair.get('kernel_image_sha256') and
        {p['mode'] for p in pair['packages']}=={'diagnostic','rollback'},'exact saved124 stage/pair/variant witness required')
    require(private(plan['kernel_build'])==template['template'] and plan['image_sha256']==template['binding']['image_sha256'] and
        plan['build_result_sha256']==template['contract']['template_files']['build-result.json'] and
        private(bound['auto_cycle_template'])==template['template'] and
        bound['auto_cycle_template_image_sha256']==plan['image_sha256'] and
        bound['auto_cycle_template_report_sha256']==plan['build_result_sha256'] and
        bound['effective_config_sha256']==ctx['contract']['variant_config']['sha256'],
        'exact saved124 generic template and separate bound-stage roles required')
    with tail.read_scope(ctx):tail.candidate(pair,True);tail.plan_binding(plan,ctx['bound'])
    require(sha(ctx['old']['original']['ci_success_context'])==ctx['old']['original']['ci_success_context_sha256'],'reviewed private native121 context changed')
    predecessor=shared._baseline_context(read(ctx['old']['original']['ci_success_context'])['current_predecessor'])
    require(plan.get('current_package_result_sha256')==predecessor['package_result_sha256'] and plan.get('current_boot_payload_sha256')==predecessor['boot_sha256'] and private(plan['current_packages'])==private(predecessor['packages']) and pair.get('expected_current_boot_sha256')==predecessor['boot_sha256'],'private actual current111 predecessor differs')
    require(not destination.is_relative_to(private(predecessor['packages'])) and not private(predecessor['packages']).is_relative_to(destination),'current111 evidence must remain immutable')
    execution=dict(schema=CONTEXT_SCHEMA,declared_version='v126',producer_execution_version='v124',host_source_head=head,host_source_sha256=host['host_profile_source_sha256'],packaging_host_source_head=HEAD,packaging_host_source_sha256=dict(PINS),producer_transaction_sha256=c['producer_transaction_sha256'],plan_sha256=plan_sha,packages=str(effective),output=str(destination),contract_path=str(path),contract_sha256=expected,linked_growth_ack=c['linked_growth_ack'],user_availability_record_sha256=c['user_availability_record_sha256'])
    return dict(producer=ctx,plan=plan,plan_path=planpath,execution=execution,predecessor=predecessor)

def _row(row,state):
    import type3_remaining_packages as tail
    ctx=state['producer']
    with tail.read_scope(ctx):tail.candidate(row,True)

def execution_context(row,plan_sha,packages,declared,head,path,expected,output):
    state=_load(path,expected,plan_sha,packages,declared,head,output);_row(row,state);return copy.deepcopy(state['execution'])

def require_scope(row,ack,context):
    require(ack is True and type(context) is dict and context.get('schema')==CONTEXT_SCHEMA,'explicit126 context and growth ACK required before transport')
    expected=execution_context(row,context.get('plan_sha256'),context.get('packages'),context.get('declared_version'),context.get('host_source_head'),context.get('contract_path'),context.get('contract_sha256'),context.get('output'))
    require(context==expected,'exact126 execution context differs');return True

@contextmanager
def reader_scope(row,ack,context):
    require_scope(row,ack,context)
    state=_load(context['contract_path'],context['contract_sha256'],context['plan_sha256'],context['packages'],'v126',context['host_source_head'],context['output']);_row(row,state)
    import type3_remaining_packages as tail
    import native_prefree_output_admission as native
    token=_READ.set(state);current=native._CURRENT_READ.set(state['predecessor'])
    try:
        with tail.read_scope(state['producer']):yield
    finally:native._CURRENT_READ.reset(current);_READ.reset(token)

def accepted_plan(path,expected):
    state=_READ.get()
    if state is None:return None
    require(private(path)==state['plan_path'] and sha(path)==expected==state['execution']['plan_sha256'],'exact126 accepted plan reader required')
    return copy.deepcopy(state['plan'])

def saved_variant(root,token):
    """Exact accepted124 metadata under the new device-only read scope."""
    state=_READ.get()
    if state is None:return None
    import type3_remaining_packages as tail
    ctx=state['producer'];root=private(root)
    require(root==ctx['variant_root'] and token==ctx['bound']['auto_cycle_token'] and
        sha(root/'build-result.json')==ctx['contract']['variant_report']['sha256'] and
        sha(root/'handoff.config')==ctx['contract']['variant_config']['sha256'],
        'exact126 retained variant metadata/token/config required')
    report=read(root/'build-result.json')
    require(report==ctx['bound'],'saved123 variant metadata changed')
    with tail.read_scope(ctx):tail.candidate(dict(report,**{tail.FIELD:tail.marker(ctx)}),True)
    return copy.deepcopy(report)


def handles(row):
    state=_READ.get()
    if state is None:return False
    import type3_remaining_packages as tail
    return row.get('native_source_head')==state['producer']['bound']['native_source_head'] or tail.FIELD in row

def candidate(row,patched=None):
    """Read-only accepted variant/role dispatch before legacy template fallback."""
    state=_READ.get();require(state is not None and handles(row),'validated126 read context required')
    import type3_remaining_packages as tail
    ctx=state['producer']
    # Raw retained variant metadata has no package marker. Its exact accepted
    # bytes receive only an in-memory role projection; the saved row is unchanged.
    projected=dict(row,**{tail.FIELD:tail.marker(ctx)}) if row==ctx['bound'] else row
    with tail.read_scope(ctx):return tail.candidate(projected,patched)


def device_plan_reader(function):
    @wraps(function)
    def checked(path,expected,output,*args,**kwargs):
        if kwargs.get('declared_test_version') not in ('v125','v126'):return function(path,expected,output,*args,**kwargs)
        require(kwargs.get('declared_test_version')=='v126' and kwargs.get('execute') is True and kwargs.get('limit',1)==1 and kwargs.get('ack_kernel_readonly_growth') is True and not kwargs.get('v105_battery_5pct_exception') and not private(output).exists(),'fresh126 one-cycle execution and growth ACK required before query')
        state=_load(kwargs.get('type3_device_contract'),kwargs.get('type3_device_contract_sha256'),expected,None,'v126',kwargs.get('execution_host_source_head'),output)
        row=state['producer']['pair']
        with reader_scope(row,True,state['execution']):return function(path,expected,output,*args,**kwargs)
    return checked
