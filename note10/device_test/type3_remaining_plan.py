"""One exact saved117 remaining-validation/read domain; never a construction grant."""
import argparse
from contextlib import contextmanager
from contextvars import ContextVar
from functools import wraps
import json
from pathlib import Path
import re
from types import MappingProxyType

HEAD='4afff621174cb489219cd054d72aa0bee6073bb6'
PINS=MappingProxyType({'note10/device_test/affinity_binding.py': '6d5b16d54a803c95bdd391a38efbd2bac5ef36baffe199f86cd83f878bf10678',
 'note10/device_test/auto_cycle.py': '622b4a4123c44618c7710ddeff8386848c43359c4a6ab0335efd4f168e626c47',
 'note10/device_test/build_boot_test_packages.py': '17b973f54185521be6685acb5e019f8bf8b5f10897d01c0167929c97859cddef',
 'note10/device_test/build_kernel_readonly_input.py': '5391edfa477324dbdd5f4d9c6fb13deb5df8a66b2ed4df7d018213012b227000',
 'note10/device_test/build_kernel_readonly_span_candidate.py': '1abba018c6ab5dd488a696c962bbd5437faacc70b9b035f7b876410b355839ec',
 'note10/device_test/build_kernel_readonly_span_pc.py': 'cd42e0dec6570bcc09c7a07695560eae13a62420d744e16035c4da3a57c588e9',
 'note10/device_test/build_readonly_input_pc.py': '893698f6741fd178334777b4f96c98934d78b5a927fe4cf3d383d92e90557d9e',
 'note10/device_test/builtin_init_profile.py': 'e196c7143cbd7aa55ded754a8381791efeff2974c03436e61c3f50454117e3bf',
 'note10/device_test/builtin_init_route.py': '46b100dc95f11e344c11b8cb3fba5d34d17b2884385923426a42246699fda43d',
 'note10/device_test/carrier_lzma.c': 'e204732754f15929f7134885ec2740e1ed26f0291dd64c7df7957a4aee7b987a',
 'note10/device_test/carrier_lzma.h': '6790aa17da94025e0bab175377573edb8df3f503c8cde86f8c919e33ee742974',
 'note10/device_test/class3_native_origin.py': 'cc929900eccfd900a3d5a82e0884ee515e5d9f7bb1e29c5d3cd22e6888ac8b6f',
 'note10/device_test/current_data_reuse.py': '15c7a5a55e22f4445c216904769d7ba9b6367f792122e5b936305c95ae031129',
 'note10/device_test/early_fdt_binding.py': 'd4f7099fb45eca31c83c9acd9fbfe0cd5c7ccc5c271c18180e3672e22f9a6b78',
 'note10/device_test/kernel_readonly_input.h': '4aa99ff2ab756b854174eb2519af96e79669f82114293790a538ddd3025298ea',
 'note10/device_test/kernel_readonly_input.py': 'bc6df2f0af0dc6912a94df120ccc9cd33d36b98f87a6b6f59fc23206cd557fb9',
 'note10/device_test/kernel_readonly_input_fixture.c': '6300f13ba284b4f42614a4c6cda8f09c6e6671e88d6e524ec24dacd3a7ab70e0',
 'note10/device_test/kernel_readonly_span.h': 'dd0640b8322fb86c8baa29863a931ddb7d005dd589352ba4136c09bdb79de86d',
 'note10/device_test/kernel_readonly_span_candidate.h': '8f8e8522a7b03413b3db59f21fca5cefa4b74fb9e63a412dfc9d6067beb5dec1',
 'note10/device_test/kernel_readonly_span_candidate.py': 'd5aeac7c00aa439cb68c57a9ef686d6c0b29832ed498305d4091ef1148629291',
 'note10/device_test/kernel_readonly_span_candidate_fixture.c': 'b4d02ff71b82365915fca0c112170de9c44184dcce481656832e69e77dee9f29',
 'note10/device_test/kernel_readonly_span_fixture.c': 'afbc9ae410e15bf7221e10a4cbcb325702a3a0235dec0fe585b836e7dae467c6',
 'note10/device_test/linux_data_carrier.c': 'e6e1c1fe04bc5f31cd430983663d8f150936ad3d258405546dbe0aed2bf91acf',
 'note10/device_test/linux_data_carrier.py': '29733dc57cd396a401ed344d7f4a33faed6c383a93c3889f61510a15fcce0ae7',
 'note10/device_test/linux_data_carrier_composition.c': '2eb666597983d3a2dfb0a4f98da26dc02dff287db49d39756ada6edc90e0c667',
 'note10/device_test/linux_data_carrier_fixture.c': '6b1b0e14184582c734a3154eeef6c0e2736fd1b8ef3491881b7decaacb5ecbe4',
 'note10/device_test/linux_data_compare_evidence.h': '3383823cf1fd56f688ad9d6823d965fdda270a08acede17f6df8d87fa6199438',
 'note10/device_test/linux_data_compare_evidence_fixture.c': '45a0cdfd8d4bd8df5ffbbb0e370cd05f768d522e96208881a7f7a02ee02fadc3',
 'note10/device_test/linux_data_early_prefix.h': '60fb29d56be78212e04cc164938db4a25296fdea5250e372824b317127aaeb98',
 'note10/device_test/linux_data_early_prefix_fixture.c': 'b058ccfa33fccadfa2547986a724b21dd7de0b781e003cd3ca1c71fddfe36f09',
 'note10/device_test/linux_data_growth.h': '640ae63bd927d205ad8bc489c4c7b25935f1c4311332dce5d10821acf3ac0746',
 'note10/device_test/linux_data_growth_fixture.c': 'd567edfc28efc1b258eff93a72dda94d8f24af00297b315b1f7d371c7d77066a',
 'note10/device_test/linux_data_input_probe_fixture.c': 'c7192b0515eb7de9526291913ef97737207844a45d266a4e1287437f49b3e0b4',
 'note10/device_test/linux_data_input_range.h': 'c53f208c886ba21af0f22d266a1edb1de0f42a3e40d5a68080a41fcf775d4dac',
 'note10/device_test/linux_data_input_range_fixture.c': 'd3c7695b319963b9d6de679a5eadaf107c4dc667e610b892f2953a390854ecd5',
 'note10/device_test/materialize_auto_cycle.py': '4b0b67be104a25c740f93a2ff3b4d57a859cf34006d0e43852a2e4cf6a4345de',
 'note10/device_test/native_memory_observation.py': 'f4acd0f310989bfcd1b0c2039fef6e429e8ec4d4f41ebdb94fc483538fa26663',
 'note10/device_test/native_scoped_output.py': '28567462f0bcb45ba4ed94eb3736bf8ba28c22058262acee0b3f2ffc20496146',
 'note10/device_test/native_scoped_output_admission.py': '2ca24169789996d6ea9d9cceb91c8c3ea2f65851935655685808bf7d57b76237',
 'note10/device_test/precheck_window_access.py': '3ef3859ef2a4c154e93e5db7846bde78eb9061742243dba435187a9087226e28',
 'note10/device_test/prepare_linux_boot.py': '0499a630875cb4319e4bdfb33c02d0bac3e31538b24997bac794357b95a5298f',
 'note10/device_test/readonly_input_pc.h': '01b18e5fddcd12fba45190baa337b47c3309f54cc7a448cd6d72209c5ba8a3f0',
 'note10/device_test/readonly_input_pc.py': 'd7125058dc85a57eb4283fccf87bcb6af96c26de1363f81d1acb0999b94f1fc7',
 'note10/device_test/readonly_input_pc_fixture.c': '99f0e7eb9240b5c08314993a14dfcd9a532df0e24158679cdbed8b0c3c752730',
 'note10/device_test/readonly_stage_witness.h': '85851db4c9622842f4ccc547e7532139f306917d8674c0298529e5041fb08330',
 'note10/device_test/readonly_stage_witness.py': 'eb50f90eb18b22e431b8a36890e700b4eddc0cbb36d1a49f686745fb18134495',
 'note10/device_test/readonly_stage_witness_fixture.c': '2513117dd52b2c8ef92a6f0c161af3a2e1fe6060e24dc9b166d187c5a3fd0cec',
 'note10/device_test/retained_v108_origin.py': '737e3de25884daee64e8dc4d938b81e5b2f328a5923a4b6cea0b2c92b0db24f7',
 'note10/device_test/sha256_kat_device_profile.py': 'ae26098d4505d4695978c2e1c67581406a46314c528ee7c9d2d4ba7e5e12c4a6',
 'note10/device_test/sha256_stream_state.py': '55de2735fb830ae8047bb4a8fa74325f51b766b1e885c482dbbc5ebabe3ea437',
 'note10/device_test/sha256_stream_vectors.json': '5c379d1ef41a40b9a1262c985476e9dc0ba88dae7b1586f949bbe79686f2165f',
 'note10/device_test/stage_phase2.py': '9df734fa4227bb2b9a34953ad286a24ca8ecb43d98fc7b5a79548cd3bd99cab1',
 'note10/device_test/test_affinity_binding.py': 'bf602887c4437e0096473392789da33e3ef502297d8c060faf7d9da9ecd3eb89',
 'note10/device_test/test_affinity_ci_context.py': '71aad30ab105a45efe2703fd7b222233836d6e7514560834daa71bfdd351dea9',
 'note10/device_test/test_builtin_init_route.py': '9fa63dd55114472a748062447dd95c17bf4d4d7e743117f69f0bb6a7aca6ea42',
 'note10/device_test/test_current_data_reuse.py': 'c1a868d4f9669539aee3e4fca4868118db37071467325a85d73c279b2f1d29de',
 'note10/device_test/test_early_fdt_binding.py': '2444d3d20b7cc42e705cb89c1d04de72599f7da2a5d1b9282636f3b9990ce1fa',
 'note10/device_test/test_early_fdt_host_route.py': '75992eb3e8b1228d0ae3916d47306f0329b7947cb0dfae234ec25c1e737fef6a',
 'note10/device_test/test_linux_data_carrier.py': '550344e818b42f8147ea1f688929feda322c68173f79f6e72850053dbc2e1ca7',
 'note10/device_test/test_native_memory_observation.py': 'd34e94fd5d964004c42dedd172ec07bd62826b675dcc9f4925ab4ac06c460599',
 'note10/device_test/test_partition_gate_evidence.py': 'b7dd52aa5c7747489a2713f805dbe15a6318f3d3776a8043700549e9383bcc72',
 'note10/device_test/test_sha256_kat_device_profile.py': 'c48400d5573695d217101806b8481e39aec38fd5382e64b85f999b4cee42c498',
 'note10/device_test/test_sha256_stream_state.py': '088881f92037a9895b7947eb44692f51ecba1eb602a02dacc02ff3b94a836db8',
 'note10/device_test/test_v100_carrier_input_probe.py': 'f8e37cb2da1fc1efda5582079bb619d8853565d892a589872d0699277e8c4489',
 'note10/device_test/test_v101_live_input_range.py': 'e4424b6128a18f4099b31ddc6dcf16ba6256749ba2a87f8bd565b68a1ef68183',
 'note10/device_test/test_v102_input_lifetime.py': '29cdae5c4b8ace788ad84f529700d753bcb19c9d4a34697bddf8ca7dfa80bed1',
 'note10/device_test/test_v103_readonly_input_pc.py': 'cdce146aed40d9526eae04259e39896f629248f6b395ad8ceeec341cae5be9c5',
 'note10/device_test/test_v104_growth_region.py': '89ca671ca695b083ccf9cb58c6f474acfeadb9a67ff9747d640cc533dde40e7d',
 'note10/device_test/test_v105_battery5_policy.py': '8871a297d549df482f8888cc53e392f4b5d659e8d93bfa1e3d16f25f9e4d2c0e',
 'note10/device_test/test_v105_kernel_readonly.py': '7c1cccbdda3e8df612a0fa7d52870e74d750385b85cff7b2965d236177bb23dd',
 'note10/device_test/test_v105_packing_rev1.py': '2402b70737ee2ec9c16fadd0a05b8837d68e5ae364cd1a468c4ac4471a75eabe',
 'note10/device_test/test_v106_kernel_readonly_span.py': '0a777ec820cdfb131f5dc725577e88ed8bffc73d1e951aecfa5671414eb1849c',
 'note10/device_test/test_v107_readonly_span_candidate.py': '10a3f90b475eda8dcaace92cb1dd387ba0ba6198316773f0212b578d51a1d64c',
 'note10/device_test/test_v108_type3_admission.py': '6c2e02ac70f187bd315f4f34dbb66266512c7cd5d07b765594079bafbc10cb30',
 'note10/device_test/test_v109_readonly_stage_witness.py': '33da915026b259cd267705a9a477ebbdf670581cbb8fed6fb604a1870c078684',
 'note10/device_test/test_v110_native109_admission.py': 'eb9b07328cef3bf3ef7a0c7461df1c89f0e8d3b448d440078df27edc69d0d485',
 'note10/device_test/test_v111_device_read_context.py': 'f812dfcfe13d3a75c1f79ac5e636584368aee5a13d894541cd0825ba664a613e',
 'note10/device_test/test_v116_native_scoped_output.py': '88ed04c1098e6c299d334bea64fdd40b7a9f691ddec3a9387792dc9045536cf9',
 'note10/device_test/test_v117_native_scoped_output_admission.py': '99c953b5f004de2491f448a84227f01af0b711482877796cd5a86c90d1df00c5',
 'note10/device_test/test_v99_carrier_compare_evidence.py': '2b45c21197709706d3f3ffc23e1428084d5d50a93a1d9b5bd22c2693124cf20c',
 'note10/device_test/test_v99_host_profile_origin.py': 'fb4a1c349ca298b4f18ba64e0692c7a93e9f0877b2f7a7ec22fa2c8f29ac219a',
 'note10/device_test/type3_admission.py': '2b5e896057e602ed027444b7f3efa405225cf58083091c89f5956917795231fa',
 'note10/device_test/type3_remaining_pack.py': 'd39c393f9c421a59580df7f64a9cc3fe4fe333065d440e981316734030d97dce'})
SCHEMA='note10-type3-saved117-remaining-plan-v1'
DEVICE_SCHEMA='note10-type3-saved117-device-v1'
CONTEXT_SCHEMA='type3-saved117-execution-v1'
KEYS=frozenset(('schema','status','execution_version','execution_host_source_head','execution_host_source_sha256',
    'producing_host_source_head','original_contract','failed_transaction','failure_receipt','failure_stderr','plan',
    'template_profile','template_report','variant_report','package_result','current_package_result','ci_success_context','output','caps'))
DEVICE_KEYS=frozenset(('schema','status','execution_version','producer_execution_version','producing_host_source_head',
    'execution_host_source_head','execution_host_source_sha256','plan','packages','package_result_sha256','bound_image_sha256',
    'remaining_acceptance','output','minimum_battery','BOOT_write_max','reboot_max','user_availability_record_sha256','linked_growth_ack'))
CONTEXT_KEYS=frozenset(('schema','declared_version','execution_host_source_head','execution_host_source_sha256','plan_sha256',
    'packages','output','contract_path','contract_sha256','remaining_acceptance','linked_growth_ack'))
CAPS=dict(remaining_validations=1,old_validation_prefix_runs=0,compact_source_consumptions=0,compact_copies=0,
    templates=0,materializations=0,BOOT_packings=0,plan_creations=0,cycle_generations=0,standalone_Image_reads=0,
    backup_manifest_reads=2,backup_component_reads=5,backup_component_hashes=5,reference_TWRP_stream_hashes=1,
    reference_TWRP_byte_reads=1,mkbootimg_stream_hashes=1,ZIP_opens=3,updater_member_reads=2,BOOT_member_reads=3,
    BOOT_member_bytes=3*57671680,boot_header_parses=3,header_kernel_hashes=3,rollback_backup_BOOT_hashes=1,
    compact_ramdisk_hashes=1,decoder_or_MachO_replays=0,Image_builds=0,CI=0,device_queries=0,BOOT_writes=0,reboots=0)
SECTIONS=('current111_binding_complete','backup_reference_complete','rollback_current_chain_complete',
    'package_writer_and_size_complete','diagnostic_BOOT_header_complete','compact_ramdisk_trailer_complete')
VALIDATION118_HEAD='f3d0008c62cdd017f71747e8555e6e3c33f93869'
VALIDATION118_PINS=MappingProxyType({'note10/device_test/affinity_binding.py': '6d5b16d54a803c95bdd391a38efbd2bac5ef36baffe199f86cd83f878bf10678',
 'note10/device_test/auto_cycle.py': '9c7ac95826164a7a90663aa08f91f3c556f53338ef331c0edaeccbb21534c8af',
 'note10/device_test/build_boot_test_packages.py': '17b973f54185521be6685acb5e019f8bf8b5f10897d01c0167929c97859cddef',
 'note10/device_test/build_kernel_readonly_input.py': '5391edfa477324dbdd5f4d9c6fb13deb5df8a66b2ed4df7d018213012b227000',
 'note10/device_test/build_kernel_readonly_span_candidate.py': '1abba018c6ab5dd488a696c962bbd5437faacc70b9b035f7b876410b355839ec',
 'note10/device_test/build_kernel_readonly_span_pc.py': 'cd42e0dec6570bcc09c7a07695560eae13a62420d744e16035c4da3a57c588e9',
 'note10/device_test/build_readonly_input_pc.py': '893698f6741fd178334777b4f96c98934d78b5a927fe4cf3d383d92e90557d9e',
 'note10/device_test/builtin_init_profile.py': 'bf9c4c21bbf7fb8b8086a9e8bfe1463aea1286879b566ec3d625a3dd695d6a9d',
 'note10/device_test/builtin_init_route.py': '46b100dc95f11e344c11b8cb3fba5d34d17b2884385923426a42246699fda43d',
 'note10/device_test/carrier_lzma.c': 'e204732754f15929f7134885ec2740e1ed26f0291dd64c7df7957a4aee7b987a',
 'note10/device_test/carrier_lzma.h': '6790aa17da94025e0bab175377573edb8df3f503c8cde86f8c919e33ee742974',
 'note10/device_test/class3_native_origin.py': 'cc929900eccfd900a3d5a82e0884ee515e5d9f7bb1e29c5d3cd22e6888ac8b6f',
 'note10/device_test/current_data_reuse.py': '15c7a5a55e22f4445c216904769d7ba9b6367f792122e5b936305c95ae031129',
 'note10/device_test/early_fdt_binding.py': 'd4f7099fb45eca31c83c9acd9fbfe0cd5c7ccc5c271c18180e3672e22f9a6b78',
 'note10/device_test/kernel_readonly_input.h': '4aa99ff2ab756b854174eb2519af96e79669f82114293790a538ddd3025298ea',
 'note10/device_test/kernel_readonly_input.py': 'bc6df2f0af0dc6912a94df120ccc9cd33d36b98f87a6b6f59fc23206cd557fb9',
 'note10/device_test/kernel_readonly_input_fixture.c': '6300f13ba284b4f42614a4c6cda8f09c6e6671e88d6e524ec24dacd3a7ab70e0',
 'note10/device_test/kernel_readonly_span.h': 'dd0640b8322fb86c8baa29863a931ddb7d005dd589352ba4136c09bdb79de86d',
 'note10/device_test/kernel_readonly_span_candidate.h': '8f8e8522a7b03413b3db59f21fca5cefa4b74fb9e63a412dfc9d6067beb5dec1',
 'note10/device_test/kernel_readonly_span_candidate.py': 'd5aeac7c00aa439cb68c57a9ef686d6c0b29832ed498305d4091ef1148629291',
 'note10/device_test/kernel_readonly_span_candidate_fixture.c': 'b4d02ff71b82365915fca0c112170de9c44184dcce481656832e69e77dee9f29',
 'note10/device_test/kernel_readonly_span_fixture.c': 'afbc9ae410e15bf7221e10a4cbcb325702a3a0235dec0fe585b836e7dae467c6',
 'note10/device_test/linux_data_carrier.c': 'e6e1c1fe04bc5f31cd430983663d8f150936ad3d258405546dbe0aed2bf91acf',
 'note10/device_test/linux_data_carrier.py': '29733dc57cd396a401ed344d7f4a33faed6c383a93c3889f61510a15fcce0ae7',
 'note10/device_test/linux_data_carrier_composition.c': '2eb666597983d3a2dfb0a4f98da26dc02dff287db49d39756ada6edc90e0c667',
 'note10/device_test/linux_data_carrier_fixture.c': '6b1b0e14184582c734a3154eeef6c0e2736fd1b8ef3491881b7decaacb5ecbe4',
 'note10/device_test/linux_data_compare_evidence.h': '3383823cf1fd56f688ad9d6823d965fdda270a08acede17f6df8d87fa6199438',
 'note10/device_test/linux_data_compare_evidence_fixture.c': '45a0cdfd8d4bd8df5ffbbb0e370cd05f768d522e96208881a7f7a02ee02fadc3',
 'note10/device_test/linux_data_early_prefix.h': '60fb29d56be78212e04cc164938db4a25296fdea5250e372824b317127aaeb98',
 'note10/device_test/linux_data_early_prefix_fixture.c': 'b058ccfa33fccadfa2547986a724b21dd7de0b781e003cd3ca1c71fddfe36f09',
 'note10/device_test/linux_data_growth.h': '640ae63bd927d205ad8bc489c4c7b25935f1c4311332dce5d10821acf3ac0746',
 'note10/device_test/linux_data_growth_fixture.c': 'd567edfc28efc1b258eff93a72dda94d8f24af00297b315b1f7d371c7d77066a',
 'note10/device_test/linux_data_input_probe_fixture.c': 'c7192b0515eb7de9526291913ef97737207844a45d266a4e1287437f49b3e0b4',
 'note10/device_test/linux_data_input_range.h': 'c53f208c886ba21af0f22d266a1edb1de0f42a3e40d5a68080a41fcf775d4dac',
 'note10/device_test/linux_data_input_range_fixture.c': 'd3c7695b319963b9d6de679a5eadaf107c4dc667e610b892f2953a390854ecd5',
 'note10/device_test/materialize_auto_cycle.py': '4b0b67be104a25c740f93a2ff3b4d57a859cf34006d0e43852a2e4cf6a4345de',
 'note10/device_test/native_memory_observation.py': 'f4acd0f310989bfcd1b0c2039fef6e429e8ec4d4f41ebdb94fc483538fa26663',
 'note10/device_test/native_scoped_output.py': '28567462f0bcb45ba4ed94eb3736bf8ba28c22058262acee0b3f2ffc20496146',
 'note10/device_test/native_scoped_output_admission.py': 'd9a043de9b709f0d47370bacf71b026b6dcbed43eedb368d50a0d87630e7b7e6',
 'note10/device_test/precheck_window_access.py': '3ef3859ef2a4c154e93e5db7846bde78eb9061742243dba435187a9087226e28',
 'note10/device_test/prepare_linux_boot.py': '0499a630875cb4319e4bdfb33c02d0bac3e31538b24997bac794357b95a5298f',
 'note10/device_test/readonly_input_pc.h': '01b18e5fddcd12fba45190baa337b47c3309f54cc7a448cd6d72209c5ba8a3f0',
 'note10/device_test/readonly_input_pc.py': 'd7125058dc85a57eb4283fccf87bcb6af96c26de1363f81d1acb0999b94f1fc7',
 'note10/device_test/readonly_input_pc_fixture.c': '99f0e7eb9240b5c08314993a14dfcd9a532df0e24158679cdbed8b0c3c752730',
 'note10/device_test/readonly_stage_witness.h': '85851db4c9622842f4ccc547e7532139f306917d8674c0298529e5041fb08330',
 'note10/device_test/readonly_stage_witness.py': 'eb50f90eb18b22e431b8a36890e700b4eddc0cbb36d1a49f686745fb18134495',
 'note10/device_test/readonly_stage_witness_fixture.c': '2513117dd52b2c8ef92a6f0c161af3a2e1fe6060e24dc9b166d187c5a3fd0cec',
 'note10/device_test/retained_v108_origin.py': '737e3de25884daee64e8dc4d938b81e5b2f328a5923a4b6cea0b2c92b0db24f7',
 'note10/device_test/sha256_kat_device_profile.py': '059dad7262a04c482d02fc72f06f72d9a80a55b22e75d029b1428a694d6fadfa',
 'note10/device_test/sha256_stream_state.py': '55de2735fb830ae8047bb4a8fa74325f51b766b1e885c482dbbc5ebabe3ea437',
 'note10/device_test/sha256_stream_vectors.json': '5c379d1ef41a40b9a1262c985476e9dc0ba88dae7b1586f949bbe79686f2165f',
 'note10/device_test/stage_phase2.py': '9df734fa4227bb2b9a34953ad286a24ca8ecb43d98fc7b5a79548cd3bd99cab1',
 'note10/device_test/test_affinity_binding.py': 'bf602887c4437e0096473392789da33e3ef502297d8c060faf7d9da9ecd3eb89',
 'note10/device_test/test_affinity_ci_context.py': '71aad30ab105a45efe2703fd7b222233836d6e7514560834daa71bfdd351dea9',
 'note10/device_test/test_builtin_init_route.py': '9fa63dd55114472a748062447dd95c17bf4d4d7e743117f69f0bb6a7aca6ea42',
 'note10/device_test/test_current_data_reuse.py': 'c1a868d4f9669539aee3e4fca4868118db37071467325a85d73c279b2f1d29de',
 'note10/device_test/test_early_fdt_binding.py': '2444d3d20b7cc42e705cb89c1d04de72599f7da2a5d1b9282636f3b9990ce1fa',
 'note10/device_test/test_early_fdt_host_route.py': '75992eb3e8b1228d0ae3916d47306f0329b7947cb0dfae234ec25c1e737fef6a',
 'note10/device_test/test_linux_data_carrier.py': '550344e818b42f8147ea1f688929feda322c68173f79f6e72850053dbc2e1ca7',
 'note10/device_test/test_native_memory_observation.py': 'd34e94fd5d964004c42dedd172ec07bd62826b675dcc9f4925ab4ac06c460599',
 'note10/device_test/test_partition_gate_evidence.py': 'b7dd52aa5c7747489a2713f805dbe15a6318f3d3776a8043700549e9383bcc72',
 'note10/device_test/test_sha256_kat_device_profile.py': 'c48400d5573695d217101806b8481e39aec38fd5382e64b85f999b4cee42c498',
 'note10/device_test/test_sha256_stream_state.py': '088881f92037a9895b7947eb44692f51ecba1eb602a02dacc02ff3b94a836db8',
 'note10/device_test/test_v100_carrier_input_probe.py': 'f8e37cb2da1fc1efda5582079bb619d8853565d892a589872d0699277e8c4489',
 'note10/device_test/test_v101_live_input_range.py': 'e4424b6128a18f4099b31ddc6dcf16ba6256749ba2a87f8bd565b68a1ef68183',
 'note10/device_test/test_v102_input_lifetime.py': '29cdae5c4b8ace788ad84f529700d753bcb19c9d4a34697bddf8ca7dfa80bed1',
 'note10/device_test/test_v103_readonly_input_pc.py': 'cdce146aed40d9526eae04259e39896f629248f6b395ad8ceeec341cae5be9c5',
 'note10/device_test/test_v104_growth_region.py': '89ca671ca695b083ccf9cb58c6f474acfeadb9a67ff9747d640cc533dde40e7d',
 'note10/device_test/test_v105_battery5_policy.py': '8871a297d549df482f8888cc53e392f4b5d659e8d93bfa1e3d16f25f9e4d2c0e',
 'note10/device_test/test_v105_kernel_readonly.py': '7c1cccbdda3e8df612a0fa7d52870e74d750385b85cff7b2965d236177bb23dd',
 'note10/device_test/test_v105_packing_rev1.py': '2402b70737ee2ec9c16fadd0a05b8837d68e5ae364cd1a468c4ac4471a75eabe',
 'note10/device_test/test_v106_kernel_readonly_span.py': '0a777ec820cdfb131f5dc725577e88ed8bffc73d1e951aecfa5671414eb1849c',
 'note10/device_test/test_v107_readonly_span_candidate.py': '10a3f90b475eda8dcaace92cb1dd387ba0ba6198316773f0212b578d51a1d64c',
 'note10/device_test/test_v108_type3_admission.py': '6c2e02ac70f187bd315f4f34dbb66266512c7cd5d07b765594079bafbc10cb30',
 'note10/device_test/test_v109_readonly_stage_witness.py': '33da915026b259cd267705a9a477ebbdf670581cbb8fed6fb604a1870c078684',
 'note10/device_test/test_v110_native109_admission.py': 'eb9b07328cef3bf3ef7a0c7461df1c89f0e8d3b448d440078df27edc69d0d485',
 'note10/device_test/test_v111_device_read_context.py': 'f812dfcfe13d3a75c1f79ac5e636584368aee5a13d894541cd0825ba664a613e',
 'note10/device_test/test_v116_native_scoped_output.py': '88ed04c1098e6c299d334bea64fdd40b7a9f691ddec3a9387792dc9045536cf9',
 'note10/device_test/test_v117_native_scoped_output_admission.py': '99c953b5f004de2491f448a84227f01af0b711482877796cd5a86c90d1df00c5',
 'note10/device_test/test_v118_saved117_remaining_plan.py': 'e24c8fa01cfc3ff1a41ba3f7b7d119c6b682b84e5ef27d56d10f5d9883397d17',
 'note10/device_test/test_v99_carrier_compare_evidence.py': '2b45c21197709706d3f3ffc23e1428084d5d50a93a1d9b5bd22c2693124cf20c',
 'note10/device_test/test_v99_host_profile_origin.py': 'fb4a1c349ca298b4f18ba64e0692c7a93e9f0877b2f7a7ec22fa2c8f29ac219a',
 'note10/device_test/type3_admission.py': 'f86388877ee19effa14eaec47a10d39f049c9159daeb3bf003020aac75139052',
 'note10/device_test/type3_remaining_pack.py': 'd39c393f9c421a59580df7f64a9cc3fe4fe333065d440e981316734030d97dce',
 'note10/device_test/type3_remaining_plan.py': '56a1d22c9eaa9025c5d585d57df5ff9cf993d58d77b29705931564c7e42c8cb2'})
DEVICE119_SCHEMA='note10-type3-saved118-device-v1'
CONTEXT119_SCHEMA='type3-saved118-execution-v1'
DEVICE119_KEYS=DEVICE_KEYS|{'validation_host_source_head','validation_host_source_sha256'}
CONTEXT119_KEYS=CONTEXT_KEYS|{'validation_host_source_head','validation_host_source_sha256'}
_VALIDATION118_READ=ContextVar('accepted118_validation_read',default=None)
_READ=ContextVar('saved117_read',default=None)


def require(value,message):
    from linux_data_carrier import require as checked
    checked(value,message)


def private(path):
    from type3_admission import private as checked
    return checked(path)


def sha(raw):
    from linux_data_carrier import sha as checked
    return checked(raw)


def read(path):return json.loads(Path(path).read_text(encoding='utf-8-sig'))
def save(path,row):Path(path).write_text(json.dumps(row,sort_keys=True,indent=2)+'\n',encoding='utf-8')
def selected(row):return row.get('host_profile_source_head')==HEAD


def _pin(value,*,JSON=True):
    from linux_data_carrier import bounded_private_read
    require(type(value) is dict and set(value)=={'path','sha256'} and type(value['path']) is str and
        re.fullmatch('[0-9a-f]{64}',value['sha256'] or ''),'closed private evidence pin required')
    path=private(value['path']);require(str(path)==value['path'],'canonical private evidence path required')
    raw=bounded_private_read(path,4*1024*1024 if JSON else 65536)
    require(sha(raw)==value['sha256'],'saved117 metadata/evidence pin changed')
    return json.loads(raw.decode('utf-8-sig')) if JSON else raw


def _host(head):
    import sha256_kat_device_profile as profile
    from native_scoped_output_admission import record
    require(head not in (HEAD,VALIDATION118_HEAD,record()['head'],'669f25ae9e164d6e079620d890e0b377fca75ce5'),
        'retained producing/validation/native hosts cannot be live119 executor')
    return profile.host_binding(head)


def _validation118_origin(c,path,expected):
    proof=_VALIDATION118_READ.get()
    origin=dict(host_profile_source_head=VALIDATION118_HEAD,host_profile_source_sha256=dict(VALIDATION118_PINS))
    require(proof is not None and proof['remaining_contract']==dict(path=str(path),sha256=expected) and
        proof['acceptance']['remaining_contract']==proof['remaining_contract'] and
        proof['acceptance']['validation_host']==origin and
        c['execution_host_source_head']==VALIDATION118_HEAD and c['execution_host_source_sha256']==dict(VALIDATION118_PINS),
        'exact accepted118 typed read authority and historical85 map required')
    return origin


def load(path,expected):
    from linux_data_carrier import bounded_private_read
    import native_scoped_output_admission as native
    path=private(path);raw=bounded_private_read(path,131072)
    require(re.fullmatch('[0-9a-f]{64}',expected or '') and sha(raw)==expected,'reviewed remaining-plan contract SHA required')
    c=json.loads(raw.decode('utf-8-sig'))
    require(type(c) is dict and set(c)==KEYS and c['schema']==SCHEMA and c['status']=='reviewed_ready' and
        c['execution_version']=='v118' and c['producing_host_source_head']==HEAD and c['caps']==CAPS and
        type(c['caps']) is dict and all(type(v) is int for v in c['caps'].values()),'closed one remaining validation required')
    host=_validation118_origin(c,path,expected)
    old=_pin(c['original_contract']);journal=_pin(c['failed_transaction']);receipt=_pin(c['failure_receipt'])
    trace=_pin(c['failure_stderr'],JSON=False).decode('utf-8')
    require(old.get('schema')=='note10-type3-offline-first-use-v1' and old.get('status')=='reviewed_ready' and
        old.get('host_source_head')==HEAD and old.get('execution_version')=='v117' and
        old.get('native_source_head')==native.record()['head'] and old.get('accepted_result_sha256')==native.record()['result'] and
        receipt.get('source_head')==HEAD and receipt.get('phase')=='offline' and receipt.get('invocation_attempts')==1 and
        receipt.get('invocation_retries')==0 and receipt.get('invocation_exit_code')==1 and receipt.get('success') is False and
        receipt.get('contract_sha256')==c['original_contract']['sha256'] and
        receipt.get('stderr_path')==c['failure_stderr']['path'] and receipt.get('stderr_sha256')==c['failure_stderr']['sha256'] and
        journal.get('status')=='failed_no_restart' and journal.get('phase')=='plan_reserved' and
        journal.get('attempts')==dict(templates=1,materializations=1,plans=1) and journal.get('device_operations')==[] and
        journal.get('contract_sha256')==c['original_contract']['sha256'] and journal.get('error_type')=='ValueError' and
        'line 1318, in validate_plan' in trace and 'current_boot_binding' in trace and
        trace.rstrip().endswith('ValueError: reviewed exact prior profile/source/current BOOT chain required'),
        'exact spent117 prefix/failure proof required')
    plan=_pin(c['plan']);profile_row=_pin(c['template_profile']);generic=_pin(c['template_report'])
    bound=_pin(c['variant_report']);pair=_pin(c['package_result']);prior_pair=_pin(c['current_package_result']);wrapper=_pin(c['ci_success_context'])
    base=private(old['output']);stage=plan.get('stages',[None])[0]
    require(type(stage) is dict and len(plan['stages'])==1 and stage['index']==1 and
        c['plan']['path']==str(base/'plan/plan.json') and c['failed_transaction']['path']==str(base/'transaction.json') and
        c['template_profile']['path']==str(base/'template/device-profile.json') and
        c['template_report']['path']==str(base/'template/build-result.json') and
        c['variant_report']['path']==str(private(stage['kernel_build'])/'build-result.json') and
        c['package_result']['path']==str(private(stage['packages'])/'package-result.json') and
        private(stage['kernel_build'])==base/'plan/cycle-01/kernel-build' and
        private(stage['packages'])==base/'plan/cycle-01/packages' and
        c['current_package_result']['path']==str(private(plan['current_packages'])/'package-result.json') and
        c['current_package_result']['sha256']==plan['current_package_result_sha256']==old['current_package_result_sha256'] and
        c['ci_success_context']==dict(path=old['ci_success_context'],sha256=old['ci_success_context_sha256']) and
        plan['execution_version']=='v117' and plan['executing_host_source_head']==HEAD and
        plan['type3_contract_sha256']==c['original_contract']['sha256'] and
        plan['kernel_build']==str(base/'template') and plan['build_result_sha256']==c['template_report']['sha256'] and
        stage['build_result_sha256']==c['variant_report']['sha256'] and stage['package_result_sha256']==c['package_result']['sha256'],
        'exact saved117 plan/template/variant/package pointers required')
    require(all(row.get('host_profile_source_head')==HEAD and row.get('host_profile_source_sha256')==dict(PINS) and
        row.get('version')==row.get('execution_version')=='v117' and row.get('native_source_head')==native.record()['head'] and
        row.get('source_head')==native.record()['head'] for row in (profile_row,generic,bound,pair)) and
        bound.get('auto_cycle_template')==str(base/'template') and bound.get('auto_cycle_token')==stage['cycle'] and
        bound.get('auto_cycle_template_report_sha256')==c['template_report']['sha256'] and
        bound.get('type3_materialization',{}).get('cycle')==stage['cycle'] and
        bound['image_sha256']==stage['image_sha256']==pair['kernel_image_sha256'] and
        pair['auto_cycle_token']==stage['cycle'] and
        pair['expected_current_boot_sha256']==plan['current_boot_payload_sha256']==old['current_boot_sha256'] and
        plan['backup_manifest_sha256']==pair['backup_manifest_sha256']==old['backup_manifest_sha256'] and
        len(pair['packages'])==2 and {r['mode'] for r in pair['packages']}=={'diagnostic','rollback'} and
        all(type(r['payload_size']) is int and r['payload_size']==57671680 for r in pair['packages']),
        'immutable producing117 source83/materialization/current bindings required')
    require(native.predecessor(old)==prior_pair and wrapper.get('current_predecessor',{}).get('boot_sha256')==old['current_boot_sha256'],
        'saved current111 private authority differs')
    output=private(c['output']);require(str(output)==c['output'] and all(not output.is_relative_to(private(pin['path']).parent) and
        not private(pin['path']).is_relative_to(output) for pin in (c['plan'],c['original_contract'],c['current_package_result'])),
        'fresh continuation output must be disjoint from saved evidence')
    return dict(contract=c,contract_path=str(path),contract_sha256=expected,host=host,old=old,plan=plan,profile=profile_row,
        generic=generic,bound=bound,pair=pair,prior_pair=prior_pair,wrapper=wrapper,template=base/'template',
        variant=base/'plan/cycle-01/kernel-build',packages=private(stage['packages']),output=output,purpose=None)


@contextmanager
def read_scope(context,purpose):
    require(purpose in ('remaining','device') and (purpose!='device' or
        context.get('device_context',{}).get('schema')==CONTEXT119_SCHEMA),'closed validated saved117 read purpose required')
    value=dict(context,purpose=purpose);token=_READ.set(value)
    try:yield value
    finally:_READ.reset(token)


def origin(row):
    from native_scoped_output_admission import no_pc
    no_pc(row)
    context=_READ.get()
    require(context is not None and selected(row) and row.get('host_profile_source_sha256')==dict(PINS) and
        row.get('source_head')==context['bound']['source_head'] and row.get('native_source_head')==context['bound']['native_source_head'] and
        row.get('version')==row.get('execution_version')=='v117','exact retained117 read context/source83 required')
    import sha256_kat_device_profile as profile
    base=context['bound'] if row.get('image_expectation_patched') else context['profile']
    require(all(row.get(k)==v for k,v in profile.fields(base).items()),'saved117 read metadata differs outside immutable binding')
    return dict(host_profile_source_head=HEAD,host_profile_source_sha256=dict(PINS))


def require_original_contract(row,path,expected):
    context=_READ.get()
    require(context is not None and row==context['old'] and str(private(path))==context['contract']['original_contract']['path'] and
        expected==context['contract']['original_contract']['sha256'],'spent117 contract is read-only in exact saved scope')


def saved_metadata(root,token=None,template=None):
    context=_READ.get();require(context is not None,'retained117 metadata requires exact remaining/device read context')
    root=private(root);generic=root==context['template'];require(generic or root==context['variant'],'only exact saved117 template/variant readable')
    row=context['generic'] if generic else context['bound'];key='template_report' if generic else 'variant_report'
    from sha256_kat_device_profile import sha as file_sha
    require(_pin(context['contract'][key])==row and file_sha(root/'handoff.config')==row['effective_config_sha256'],'saved117 report/config changed')
    require(generic or token==row['auto_cycle_token'] and (template is None or private(template)==context['template']),
        'saved117 cycle/template differs')
    return dict(row)


def current111_selected(pair):
    return pair.get('source_head')=='f20987a42249e61ef028c52099931f740d9a6cc5' and pair.get('host_profile_source_head')=='f39c0cdcb9c40a4c378ca2cff4afa94e9fa4d916'


def current_boot_binding(plan,pair,diagnostic):
    context=_READ.get();require(context is not None and plan==context['plan'] and pair==context['prior_pair'],
        'current111 binding requires exact saved117 remaining/read context')
    import native_scoped_output_admission as native
    from type3_remaining_pack import PINS as producer_pins,PACKAGING_PINS,PACKAGING_HEAD,FIELD
    authority=context['wrapper']['current_predecessor'];native._baseline_context(authority)
    prior=next(r for r in pair['packages'] if r['mode']=='diagnostic')
    require(current111_selected(pair) and pair.get('host_profile_source_sha256')==dict(producer_pins) and
        pair.get(FIELD,{}).get('packaging_host')==dict(host_profile_source_head=PACKAGING_HEAD,host_profile_source_sha256=dict(PACKAGING_PINS)) and
        diagnostic==prior and diagnostic['payload_sha256']==authority['boot_sha256']==plan['current_boot_payload_sha256'] and
        plan['current_package_result_sha256']==authority['package_result_sha256'] and plan['current_packages']==authority['packages'] and
        context['pair']['expected_current_boot_sha256']==authority['boot_sha256'] and pair['device_profile']==plan['device_profile']=='linux-data-carrier-v1',
        'exact current111 diagnostic/producing/packaging/executing provenance differs')


def report_section(name):
    context=_READ.get()
    if context is None or context['purpose']!='remaining':return
    require(name in SECTIONS and name not in context['journal']['completed_sections'],'one ordered remaining section required')
    index=len(context['journal']['completed_sections']);require(name==SECTIONS[index],'remaining section order differs')
    context['journal']['completed_sections'].append(name);save(context['output']/'journal.json',context['journal'])


def _acceptance(context):
    return dict(schema='note10-saved117-plan-acceptance-v1',status='remaining_validation_complete_not_device_authority',
        original_plan=context['contract']['plan'],producer_execution_version='v117',producing_host_source_head=HEAD,
        producing_host_source_sha256=dict(PINS),validation_host=context['host'],remaining_contract=dict(path=context['contract_path'],sha256=context['contract_sha256']),
        completed_sections=list(SECTIONS),caps=CAPS,native_source_head=context['bound']['native_source_head'],
        original_offline_contract=context['contract']['original_contract'],package_result=context['contract']['package_result'],
        variant_report=context['contract']['variant_report'],device_operations=[])


def prepare(path,expected):
    context=load(path,expected);output=context['output'];require(not output.exists(),'remaining validation already reserved; never restart')
    output.mkdir(parents=True);journal=dict(schema='type3-saved117-validation-journal-v1',status='started',attempts=dict(remaining_validations=1),
        contract_sha256=expected,completed_sections=[],declared_caps=CAPS,device_operations=[]);context['journal']=journal
    save(output/'journal.json',journal)
    try:
        with read_scope(context,'remaining') as active:
            from builtin_init_profile import current_boot_binding as bind
            prior=next(r for r in active['prior_pair']['packages'] if r['mode']=='diagnostic')
            bind(active['plan'],active['prior_pair'],prior);report_section('current111_binding_complete')
            from sha256_kat_device_profile import _validate_plan_tail
            _validate_plan_tail(active['plan'],active['bound'],active['pair'],active['pair']['packages'],prior,
                private(active['plan']['backup']),active['packages'])
            require(journal['completed_sections']==list(SECTIONS),'unreached validation suffix did not complete')
        receipt=_acceptance(context);target=output/'accepted-plan.json'
        with target.open('x',encoding='utf-8') as stream:stream.write(json.dumps(receipt,sort_keys=True,indent=2)+'\n')
        journal.update(status='complete',acceptance=dict(path=str(target),sha256=sha(target.read_bytes())))
        save(output/'journal.json',journal);return journal['acceptance']
    except BaseException as error:
        journal.update(status='failed_no_restart',error_type=type(error).__name__);save(output/'journal.json',journal);raise


def in_scope(root):
    context=_READ.get()
    return context is not None and private(root) in (context['template'],context['variant'])


def selected_plan(path):
    context=_READ.get()
    if context is not None and str(private(path))==context['contract']['plan']['path']:return True
    row=read(private(path));return row.get('execution_version')=='v117' and row.get('executing_host_source_head')==HEAD


def accepted_plan(path,expected):
    context=_READ.get();require(context is not None and context['purpose']=='device' and
        str(private(path))==context['contract']['plan']['path'] and expected==context['contract']['plan']['sha256'],
        'saved117 plan requires new accepted118 execution scope; prefix replay refused')
    require(_pin(context['contract']['plan'])==context['plan'],'accepted saved117 plan metadata changed')
    return dict(context['plan'])


def _device(path,expected,plan_path,plan_sha,packages,declared,head,output):
    from linux_data_carrier import bounded_private_read
    import native_scoped_output_admission as native
    path=private(path);raw=bounded_private_read(path,131072)
    require(re.fullmatch('[0-9a-f]{64}',expected or '') and sha(raw)==expected,'exact saved117 device contract SHA required')
    c=json.loads(raw.decode('utf-8-sig'))
    require(type(c) is dict and set(c)==DEVICE119_KEYS and c['schema']==DEVICE119_SCHEMA and c['status']=='reviewed_ready' and
        c['execution_version']==declared=='v119','closed119 execution contract required; stale118 is read-only')
    require(type(c['packages']) is str,'canonical closed119 packages path required')
    effective_packages=private(c['packages'])
    require(type(c['packages']) is str and str(effective_packages)==c['packages'] and
        (packages is None or private(packages)==effective_packages),'supplied packages contradict closed119 contract')
    host=_host(head)
    require(c['execution_version']==declared=='v119' and c['producer_execution_version']=='v117' and c['producing_host_source_head']==HEAD and
        c['validation_host_source_head']==VALIDATION118_HEAD and c['validation_host_source_sha256']==dict(VALIDATION118_PINS) and
        c['execution_host_source_head']==head and c['execution_host_source_sha256']==host['host_profile_source_sha256'] and
        c['plan']==dict(path=str(private(plan_path if plan_path is not None else c['plan']['path'])),sha256=plan_sha) and
        c['packages']==str(effective_packages) and
        c['output']==str(private(output)) and not private(output).is_relative_to(effective_packages) and
        c['linked_growth_ack']==native.growth_ack() and c['linked_growth_ack'].get('acknowledged') is True and
        all(type(c['linked_growth_ack'][k]) is int for k in ('reference_linked_bytes','accepted_linked_bytes','delta_bytes')) and
        all(type(c[k]) is int and c[k]==v for k,v in (('minimum_battery',10),('BOOT_write_max',1),('reboot_max',1))) and
        c['user_availability_record_sha256']=='4a639d278836af88256a339d199b9fbe53ad65d354db4b8c4401796522e758e9',
        'closed119 execution/retained118/producing117/device gates differ')
    acceptance=_pin(c['remaining_acceptance']);rp=acceptance.get('remaining_contract',{})
    retained=dict(host_profile_source_head=VALIDATION118_HEAD,host_profile_source_sha256=dict(VALIDATION118_PINS))
    require(type(rp) is dict and set(rp)=={'path','sha256'} and acceptance.get('validation_host')==retained,
        'accepted118 validation provenance/map changed')
    token=_VALIDATION118_READ.set(dict(remaining_contract=rp,acceptance=acceptance))
    try:context=load(rp['path'],rp['sha256'])
    finally:_VALIDATION118_READ.reset(token)
    journal=read(context['output']/'journal.json')
    require(acceptance==_acceptance(context) and c['remaining_acceptance']==journal.get('acceptance') and
        c['remaining_acceptance']['path']==str(context['output']/'accepted-plan.json') and journal.get('status')=='complete' and
        journal.get('attempts')==dict(remaining_validations=1) and type(journal['attempts']['remaining_validations']) is int and
        journal.get('declared_caps')==CAPS and journal.get('contract_sha256')==context['contract_sha256'] and
        journal.get('completed_sections')==list(SECTIONS) and journal.get('device_operations')==[] and
        c['plan']==context['contract']['plan'] and c['packages']==str(context['packages']) and
        c['package_result_sha256']==context['contract']['package_result']['sha256'] and
        c['bound_image_sha256']==context['bound']['image_sha256'] and context['host']==retained,
        'exact completed remaining acceptance/plan/packages/live execution lineage required')
    destination=private(output);spent_root=private(context['old']['output'])
    require(not destination.is_relative_to(spent_root) and not spent_root.is_relative_to(destination) and
        not destination.is_relative_to(context['output']) and not context['output'].is_relative_to(destination) and
        not private(context['plan']['current_packages']).is_relative_to(destination) and
        not destination.is_relative_to(private(context['plan']['current_packages'])),
        'fresh119 device output must preserve all saved117/current/acceptance evidence')
    execution=dict(schema=CONTEXT119_SCHEMA,declared_version='v119',execution_host_source_head=head,
        execution_host_source_sha256=host['host_profile_source_sha256'],validation_host_source_head=VALIDATION118_HEAD,
        validation_host_source_sha256=dict(VALIDATION118_PINS),plan_sha256=plan_sha,packages=c['packages'],output=c['output'],
        contract_path=str(path),contract_sha256=expected,remaining_acceptance=c['remaining_acceptance'],linked_growth_ack=c['linked_growth_ack'])
    context['device_context']=execution;return context


def execution_context(row,plan_sha,packages,declared,head,path,expected,output):
    require(selected(row),'saved117 execution requires producing117 tuple')
    active=_READ.get()
    if active is not None and active.get('purpose')=='device':
        c=active['device_context'];require(c['plan_sha256']==plan_sha and c['packages']==str(private(packages)) and
            c['declared_version']==declared and c['execution_host_source_head']==head and c['contract_path']==str(private(path)) and
            c['contract_sha256']==expected and c['output']==str(private(output)),'explicit saved117 execution context contradicts active scope')
        _execution_row(row,active)
        return dict(c)
    # The immutable producing row binds its plan through the reviewed device contract;
    # no row version/source field is rewritten to the live executor.
    context=_device(path,expected,None,plan_sha,packages,declared,head,output)
    _execution_row(row,context)
    return context['device_context']


def _execution_row(row,context):
    from native_scoped_output_admission import no_pc
    no_pc(row)
    import sha256_kat_device_profile as profile
    require(selected(row) and all(row.get(k)==v for k,v in profile.fields(context['bound']).items()),
        'saved117 actual row differs from accepted118 device lineage')


def require_device_scope(row,ack,context):
    require(ack is True and type(context) is dict and set(context)==CONTEXT119_KEYS and context.get('schema')==CONTEXT119_SCHEMA,
        'exact119 execution context and growth ACK required before transport')
    expected=execution_context(row,context['plan_sha256'],context['packages'],context['declared_version'],
        context['execution_host_source_head'],context['contract_path'],context['contract_sha256'],context['output'])
    require(context==expected,'saved117 explicit execution context differs');return True


def device_reader(function,packages,kernel_build,*args,**kwargs):
    import sha256_kat_device_profile as profile
    row=read(private(packages)/'package-result.json');execution=kwargs.get('type3_context')
    require_device_scope(row,kwargs.get('ack_kernel_readonly_growth',False),execution)
    context=_device(execution['contract_path'],execution['contract_sha256'],None,execution['plan_sha256'],packages,
        execution['declared_version'],execution['execution_host_source_head'],execution['output'])
    require(private(kernel_build)==context['variant'],'exact saved117 variant path required before transport')
    with read_scope(context,'device'):return function(packages,kernel_build,*args,**kwargs)


def precheck_receipt(context,path):
    active=_READ.get();require(active is not None and active['purpose']=='device' and context==active['device_context'],
        'validated saved117 device read scope required')
    target=private(context['output'])/'PREINSTALL-CHECK-01.json'
    require((path is None or private(path)==target) and not target.exists() and not target.is_relative_to(private(context['packages'])),
        'fresh118 precheck receipt required');return target


def device_plan_reader(function):
    @wraps(function)
    def checked(path,expected,output,**kwargs):
        require(kwargs.get('declared_test_version')!='v118','spent118 execution is read-only; distinct119 contract required')
        if kwargs.get('declared_test_version')!='v119':return function(path,expected,output,**kwargs)
        require(kwargs.get('execute') is True and kwargs.get('limit',1)==1 and kwargs.get('ack_kernel_readonly_growth') is True and
            kwargs.get('v105_battery_5pct_exception',False) is False,'one explicit119 execution with default battery10 and ACK required')
        context=_device(kwargs.get('type3_device_contract'),kwargs.get('type3_device_contract_sha256'),path,expected,None,
            'v119',kwargs.get('execution_host_source_head'),output)
        with read_scope(context,'device'):return function(path,expected,output,**kwargs)
    return checked


if __name__=='__main__':
    import type3_remaining_plan as canonical
    parser=argparse.ArgumentParser();parser.add_argument('--contract',required=True);parser.add_argument('--contract-sha256',required=True)
    args=parser.parse_args();print(json.dumps(canonical.prepare(args.contract,args.contract_sha256),indent=2))
