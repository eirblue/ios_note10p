"""Exact accepted native116 -> separately reviewed host117 admission.

Public constants bind accepted generic native source/CI/Image metadata and public
predecessor code lineage only. Device package/BOOT/terminal paths and hashes stay
in the byte-pinned private root context. No runtime origin setter or caller source
map override exists; no artifact reader or device query is added.
"""
from contextlib import contextmanager
from contextvars import ContextVar
from functools import wraps
import json
from pathlib import Path
import re

import linux_data_carrier as data
import native_scoped_output as scoped
import kernel_readonly_span_candidate as ro3

_NATIVE116 = {'artifact_id': 13285550652,
 'attempt': 1,
 'fixture_result_sha256': 'f745cd5693dc10185680c9aa8178a42689e690cb9f81ad2af5795f0b0eceb863',
 'head': '661dc45770efa46265b2856bb0ee42b7dd25f040',
 'image_bytes': 50870284,
 'image_sha256': '60884753e191546ecae8944aa9fb8a8f9433d2a7bbac120b6a1014abbee03c34',
 'job_id': 126294137720,
 'linked_bytes': 59588608,
 'outcome_bytes': 128,
 'pins': {'.github/workflows/note10-builtin-init-route.yml': 'c135fb22c04e0fa085b3092c23af369f10070d6560e6ccaf0c005c71a1b134b6',
          '.github/workflows/note10-linux-data-carrier.yml': '7eb419cd87a46eed0b82a96ba9bea6bb526ba1fa9d02099bcca5b53a1633cc42',
          'note10/device_test/auto_cycle.py': '357c0b4e372ebf1d3364ee33212f2c581c8810d08c21a327d0252bf410822936',
          'note10/device_test/auto_return.c': '9ec43d3d17f12fe90d2ab36e4712537b7f8275f6f27b6536bbef826f9692037d',
          'note10/device_test/build_boot_test_packages.py': '17b973f54185521be6685acb5e019f8bf8b5f10897d01c0167929c97859cddef',
          'note10/device_test/build_builtin_init_image.py': 'f562053636a71e07ac332ab1affcc8f409831144a3885bf56572e6f814c25e06',
          'note10/device_test/build_kernel_readonly_span_candidate.py': '1abba018c6ab5dd488a696c962bbd5437faacc70b9b035f7b876410b355839ec',
          'note10/device_test/build_linux_data_carrier.py': '44f083e2168716b33cea4111ab303c83f5fda5136dd99f54f32c2521a2f25d98',
          'note10/device_test/build_sha256_kat_recovery.py': '2f84ba60d3b0a582d015c2d6c1955aae8a8a4e785b575da5d2af6ebf293ab123',
          'note10/device_test/build_sha256_runtime_kat.py': 'd76c33333a67d6af4bc7c0d8caf0b0868f8e5d63e1c585f6def2860dfe4bbdff',
          'note10/device_test/build_xnu_runtime_plan_component.py': '367f9147d50950dffb47bf83861787dce4a1be47225b11b070e2f60de45c6b6e',
          'note10/device_test/builtin_init_profile.py': 'e196c7143cbd7aa55ded754a8381791efeff2974c03436e61c3f50454117e3bf',
          'note10/device_test/builtin_init_route.c': '2fb12577bfd332cd83c3e497aa5930c275983e0f9139d22f53b009b0a9249d74',
          'note10/device_test/builtin_init_route.py': '46b100dc95f11e344c11b8cb3fba5d34d17b2884385923426a42246699fda43d',
          'note10/device_test/builtin_init_route_fixture.c': 'e6c586d479175eae9ba2496b886ff504e584aadf53b2fb3816f64e839a2be6e7',
          'note10/device_test/builtin_minimal_init.S': 'ca8ad494643331a3065b25f0e62330dce4c7385a354bac71e75a972627a6ad60',
          'note10/device_test/bundle_affinity_evidence.py': 'b292f0cd45df8b8ef110146315520a857c388d52f9b2e69a0812a3ae8f4253dc',
          'note10/device_test/carrier_lzma.c': 'e204732754f15929f7134885ec2740e1ed26f0291dd64c7df7957a4aee7b987a',
          'note10/device_test/carrier_lzma.h': '6790aa17da94025e0bab175377573edb8df3f503c8cde86f8c919e33ee742974',
          'note10/device_test/decode_reservation.py': 'c60e3f8cb399d6f62e61531ddf8c15aacbeaa87ea7d6c897e8953f3e62f1c971',
          'note10/device_test/decode_sha256_runtime_kat.py': 'c83437aae48ee4f1d7400edf73933c8b0102291934648a30387100ef187f42b9',
          'note10/device_test/early_fdt_binding.py': 'd4f7099fb45eca31c83c9acd9fbfe0cd5c7ccc5c271c18180e3672e22f9a6b78',
          'note10/device_test/kernel_readonly_input.py': 'c936aed61b36eb51cf40c6922f595c7d586c1aa40179656faa8b6bfb03471203',
          'note10/device_test/kernel_readonly_span.h': 'dd0640b8322fb86c8baa29863a931ddb7d005dd589352ba4136c09bdb79de86d',
          'note10/device_test/kernel_readonly_span_candidate.h': '8f8e8522a7b03413b3db59f21fca5cefa4b74fb9e63a412dfc9d6067beb5dec1',
          'note10/device_test/kernel_readonly_span_candidate.py': 'a0fab6b0ab310ef5846583baf7a43c2a32646228082ea008625f0dfeca02f4f5',
          'note10/device_test/kernel_readonly_span_candidate_fixture.c': 'b4d02ff71b82365915fca0c112170de9c44184dcce481656832e69e77dee9f29',
          'note10/device_test/linux_data_carrier.c': 'e6e1c1fe04bc5f31cd430983663d8f150936ad3d258405546dbe0aed2bf91acf',
          'note10/device_test/linux_data_carrier.py': '29733dc57cd396a401ed344d7f4a33faed6c383a93c3889f61510a15fcce0ae7',
          'note10/device_test/linux_data_carrier_composition.c': '2eb666597983d3a2dfb0a4f98da26dc02dff287db49d39756ada6edc90e0c667',
          'note10/device_test/linux_data_carrier_fixture.c': '6b1b0e14184582c734a3154eeef6c0e2736fd1b8ef3491881b7decaacb5ecbe4',
          'note10/device_test/linux_data_compare_evidence.h': '3383823cf1fd56f688ad9d6823d965fdda270a08acede17f6df8d87fa6199438',
          'note10/device_test/linux_data_early_prefix.h': '60fb29d56be78212e04cc164938db4a25296fdea5250e372824b317127aaeb98',
          'note10/device_test/linux_data_early_prefix_fixture.c': 'b058ccfa33fccadfa2547986a724b21dd7de0b781e003cd3ca1c71fddfe36f09',
          'note10/device_test/linux_data_growth.h': '640ae63bd927d205ad8bc489c4c7b25935f1c4311332dce5d10821acf3ac0746',
          'note10/device_test/linux_data_growth_fixture.c': 'd567edfc28efc1b258eff93a72dda94d8f24af00297b315b1f7d371c7d77066a',
          'note10/device_test/linux_data_input_probe_fixture.c': 'c7192b0515eb7de9526291913ef97737207844a45d266a4e1287437f49b3e0b4',
          'note10/device_test/linux_data_input_range.h': 'c53f208c886ba21af0f22d266a1edb1de0f42a3e40d5a68080a41fcf775d4dac',
          'note10/device_test/linux_data_input_range_fixture.c': 'd3c7695b319963b9d6de679a5eadaf107c4dc667e610b892f2953a390854ecd5',
          'note10/device_test/materialize_auto_cycle.py': '4b0b67be104a25c740f93a2ff3b4d57a859cf34006d0e43852a2e4cf6a4345de',
          'note10/device_test/native_scoped_output.h': 'dd52afd255b685b7f8c0b769ca826defbff343e13d4020826ca7d6fcec0d907c',
          'note10/device_test/native_scoped_output.py': 'd758acc3d7c118970c90cd2f1cac64410004b234eb382cec628834291cdbc2e8',
          'note10/device_test/native_scoped_output_fixture.c': '0288c96ca301560ecf82cf14aee6fdd378e207278857969fd17e1ab84dacc880',
          'note10/device_test/pre_pm_archive_contract.py': '966a5b032e516ecc984defc9b0313192667d4f4585511fa232966ce79ac3b5c5',
          'note10/device_test/prepare_linux_boot.py': '0499a630875cb4319e4bdfb33c02d0bac3e31538b24997bac794357b95a5298f',
          'note10/device_test/prepare_sha256_kat_recovery.py': '921dd3cade033e21e50994c1b8036d8067bb77c8f9372454c9290673aa7d4b91',
          'note10/device_test/prepare_sha256_runtime_kat.py': '5f56dfb7d77acc2b998122022b65421a5e34f73d52be446a677ff333b5d5e5c2',
          'note10/device_test/prepare_xnu_runtime_plan.py': '6b9b21ab93f3b49ef43e947a26ad1985d2f11bbd94002e30fcf6dcca875ac41c',
          'note10/device_test/readonly_stage_witness.h': '85851db4c9622842f4ccc547e7532139f306917d8674c0298529e5041fb08330',
          'note10/device_test/readonly_stage_witness.py': '200ebe64a1095eca28edc312f897a8c98ee3113f449e47d87ba83a2292cf77ce',
          'note10/device_test/readonly_stage_witness_fixture.c': '2513117dd52b2c8ef92a6f0c161af3a2e1fe6060e24dc9b166d187c5a3fd0cec',
          'note10/device_test/retained_v108_origin.py': '737e3de25884daee64e8dc4d938b81e5b2f328a5923a4b6cea0b2c92b0db24f7',
          'note10/device_test/sealed_affinity_artifact.cjs': '08c17edb82357d5719fbccd2427fca1970c09f6b3ee7aef91d6034f7d12f70ec',
          'note10/device_test/sha256_builtin_init.c': '11408b9dba36f56137f5d411d9a77eaf72db71cadfec9b406f85fcfc3d3cd6e4',
          'note10/device_test/sha256_kat_device_profile.py': 'd1093c722c2a134b8198e65fa6395d3c62d9f2a4c0d39fa295868784e17bc1f9',
          'note10/device_test/sha256_kat_recovery.c': '5b26ec7dca0a936bcebf1860cddb42a0b24806b9f3a7c09bfdf06d8edf27d1bf',
          'note10/device_test/sha256_kat_recovery_work.c': 'a39e955e0a104251434fed69e137687e0f24876f63e1f496f401d95acf119859',
          'note10/device_test/sha256_runtime_kat.c': '58470621def88390f16d2608989bafac76ff6d502bb211d400d2b488ed5df5ca',
          'note10/device_test/stage_phase2.py': '9df734fa4227bb2b9a34953ad286a24ca8ecb43d98fc7b5a79548cd3bd99cab1',
          'note10/device_test/test_builtin_init_route.py': '9fa63dd55114472a748062447dd95c17bf4d4d7e743117f69f0bb6a7aca6ea42',
          'note10/device_test/test_linux_data_carrier.py': '550344e818b42f8147ea1f688929feda322c68173f79f6e72850053dbc2e1ca7',
          'note10/device_test/test_v100_carrier_input_probe.py': 'f8e37cb2da1fc1efda5582079bb619d8853565d892a589872d0699277e8c4489',
          'note10/device_test/test_v101_live_input_range.py': 'e4424b6128a18f4099b31ddc6dcf16ba6256749ba2a87f8bd565b68a1ef68183',
          'note10/device_test/test_v102_input_lifetime.py': '29cdae5c4b8ace788ad84f529700d753bcb19c9d4a34697bddf8ca7dfa80bed1',
          'note10/device_test/test_v104_growth_region.py': '89ca671ca695b083ccf9cb58c6f474acfeadb9a67ff9747d640cc533dde40e7d',
          'note10/device_test/test_v107_readonly_span_candidate.py': '10a3f90b475eda8dcaace92cb1dd387ba0ba6198316773f0212b578d51a1d64c',
          'note10/device_test/test_v108_type3_admission.py': '6c2e02ac70f187bd315f4f34dbb66266512c7cd5d07b765594079bafbc10cb30',
          'note10/device_test/test_v109_readonly_stage_witness.py': '33da915026b259cd267705a9a477ebbdf670581cbb8fed6fb604a1870c078684',
          'note10/device_test/test_v116_native_scoped_output.py': '88ed04c1098e6c299d334bea64fdd40b7a9f691ddec3a9387792dc9045536cf9',
          'note10/device_test/type3_admission.py': '18e650c3d4894ffa83ccbd68e823b58c81b6fc8c985f2ab1d17b4d05d00d6956'},
 'plaintext_zip_sha256': 'a8c443dcd17329a599387b434672300521e39ca8314be4618f7d1ace0c6f5dad',
 'producer_ci_context': {'GITHUB_JOB': 'linux-data-carrier',
                         'GITHUB_REPOSITORY': 'eirblue/ios_note10p',
                         'GITHUB_RUN_ATTEMPT': '1',
                         'GITHUB_RUN_ID': '41744539466',
                         'GITHUB_SHA': '661dc45770efa46265b2856bb0ee42b7dd25f040',
                         'GITHUB_WORKFLOW_REF': 'eirblue/ios_note10p/.github/workflows/note10-linux-data-carrier.yml@refs/heads/main',
                         'GITHUB_WORKFLOW_SHA': '661dc45770efa46265b2856bb0ee42b7dd25f040'},
 'result': '96f8e5300fe8299cb51b1ee490b4c504c74fb88f836bfe15d3c7def395254fd9',
 'run_id': 41744539466,
 'source_manifest_sha256': '6a6c4bd11c1879f559ae4656296a251cc05e6da7e7e8b938ceb47b078c95ee80',
 'state_bytes': 88,
 'test_result_sha256': '243b14f9481a29ea3c3de6dd34e37ee2fc04671be43e29125933d17bff5477e3',
 'workflow_id': 404040749}
_CURRENT111_LINEAGE = {'execution_host': '669f25ae9e164d6e079620d890e0b377fca75ce5',
 'execution_host_pins': {'note10/device_test/affinity_binding.py': '6d5b16d54a803c95bdd391a38efbd2bac5ef36baffe199f86cd83f878bf10678',
                         'note10/device_test/auto_cycle.py': '357c0b4e372ebf1d3364ee33212f2c581c8810d08c21a327d0252bf410822936',
                         'note10/device_test/build_boot_test_packages.py': '17b973f54185521be6685acb5e019f8bf8b5f10897d01c0167929c97859cddef',
                         'note10/device_test/build_kernel_readonly_input.py': '5391edfa477324dbdd5f4d9c6fb13deb5df8a66b2ed4df7d018213012b227000',
                         'note10/device_test/build_kernel_readonly_span_candidate.py': 'c9b44d314719e2f59e69541c2d6618777f616f468e9ca11b5f12d18dcec0f3a0',
                         'note10/device_test/build_kernel_readonly_span_pc.py': 'cd42e0dec6570bcc09c7a07695560eae13a62420d744e16035c4da3a57c588e9',
                         'note10/device_test/build_readonly_input_pc.py': '893698f6741fd178334777b4f96c98934d78b5a927fe4cf3d383d92e90557d9e',
                         'note10/device_test/builtin_init_profile.py': 'e196c7143cbd7aa55ded754a8381791efeff2974c03436e61c3f50454117e3bf',
                         'note10/device_test/builtin_init_route.py': '46b100dc95f11e344c11b8cb3fba5d34d17b2884385923426a42246699fda43d',
                         'note10/device_test/carrier_lzma.c': 'e204732754f15929f7134885ec2740e1ed26f0291dd64c7df7957a4aee7b987a',
                         'note10/device_test/carrier_lzma.h': '6790aa17da94025e0bab175377573edb8df3f503c8cde86f8c919e33ee742974',
                         'note10/device_test/class3_native_origin.py': 'ac977605af4f30679c60931ad99450af23e969b8426d20814664a2da4afae886',
                         'note10/device_test/current_data_reuse.py': '15c7a5a55e22f4445c216904769d7ba9b6367f792122e5b936305c95ae031129',
                         'note10/device_test/early_fdt_binding.py': 'd4f7099fb45eca31c83c9acd9fbfe0cd5c7ccc5c271c18180e3672e22f9a6b78',
                         'note10/device_test/kernel_readonly_input.h': '4aa99ff2ab756b854174eb2519af96e79669f82114293790a538ddd3025298ea',
                         'note10/device_test/kernel_readonly_input.py': '77dfaeea9c4c1b8c5626c637e1286c988e9257359ebf857f6a0c2f1789015a37',
                         'note10/device_test/kernel_readonly_input_fixture.c': '6300f13ba284b4f42614a4c6cda8f09c6e6671e88d6e524ec24dacd3a7ab70e0',
                         'note10/device_test/kernel_readonly_span.h': 'dd0640b8322fb86c8baa29863a931ddb7d005dd589352ba4136c09bdb79de86d',
                         'note10/device_test/kernel_readonly_span_candidate.h': '8f8e8522a7b03413b3db59f21fca5cefa4b74fb9e63a412dfc9d6067beb5dec1',
                         'note10/device_test/kernel_readonly_span_candidate.py': 'eaa6e94d44c1c05396741177d2571577293b032ac91d1931e3533bdace45641a',
                         'note10/device_test/kernel_readonly_span_candidate_fixture.c': 'b4d02ff71b82365915fca0c112170de9c44184dcce481656832e69e77dee9f29',
                         'note10/device_test/kernel_readonly_span_fixture.c': 'afbc9ae410e15bf7221e10a4cbcb325702a3a0235dec0fe585b836e7dae467c6',
                         'note10/device_test/linux_data_carrier.c': '53b29fb87158183a0911596820e2f768d15059a5908c7434fa2ca6796e8d0259',
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
                         'note10/device_test/precheck_window_access.py': '3ef3859ef2a4c154e93e5db7846bde78eb9061742243dba435187a9087226e28',
                         'note10/device_test/prepare_linux_boot.py': '0499a630875cb4319e4bdfb33c02d0bac3e31538b24997bac794357b95a5298f',
                         'note10/device_test/readonly_input_pc.h': '01b18e5fddcd12fba45190baa337b47c3309f54cc7a448cd6d72209c5ba8a3f0',
                         'note10/device_test/readonly_input_pc.py': 'd7125058dc85a57eb4283fccf87bcb6af96c26de1363f81d1acb0999b94f1fc7',
                         'note10/device_test/readonly_input_pc_fixture.c': '99f0e7eb9240b5c08314993a14dfcd9a532df0e24158679cdbed8b0c3c752730',
                         'note10/device_test/readonly_stage_witness.h': '85851db4c9622842f4ccc547e7532139f306917d8674c0298529e5041fb08330',
                         'note10/device_test/readonly_stage_witness.py': '200ebe64a1095eca28edc312f897a8c98ee3113f449e47d87ba83a2292cf77ce',
                         'note10/device_test/readonly_stage_witness_fixture.c': '2513117dd52b2c8ef92a6f0c161af3a2e1fe6060e24dc9b166d187c5a3fd0cec',
                         'note10/device_test/retained_v108_origin.py': '737e3de25884daee64e8dc4d938b81e5b2f328a5923a4b6cea0b2c92b0db24f7',
                         'note10/device_test/sha256_kat_device_profile.py': '616225a911c0656d913876015037286ee783d21873d0f735953a6c6033ae5506',
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
                         'note10/device_test/test_v99_carrier_compare_evidence.py': '2b45c21197709706d3f3ffc23e1428084d5d50a93a1d9b5bd22c2693124cf20c',
                         'note10/device_test/test_v99_host_profile_origin.py': 'fb4a1c349ca298b4f18ba64e0692c7a93e9f0877b2f7a7ec22fa2c8f29ac219a',
                         'note10/device_test/type3_admission.py': '18e650c3d4894ffa83ccbd68e823b58c81b6fc8c985f2ab1d17b4d05d00d6956',
                         'note10/device_test/type3_remaining_pack.py': 'd39c393f9c421a59580df7f64a9cc3fe4fe333065d440e981316734030d97dce'},
 'packaging_host': '6bf37bf61c01d8ba95f5439743f318a6e5118a45',
 'producer_host': 'f39c0cdcb9c40a4c378ca2cff4afa94e9fa4d916'}
ORIGIN_KEYS=frozenset(('head', 'result', 'pins', 'producer_ci_context', 'image_sha256', 'image_bytes', 'linked_bytes', 'source_manifest_sha256', 'run_id', 'attempt', 'job_id', 'artifact_id', 'workflow_id', 'state_bytes', 'outcome_bytes', 'test_result_sha256', 'fixture_result_sha256', 'plaintext_zip_sha256'))
CI_CONTEXT_KEYS=frozenset(('schema','native_version','native_source_head','accepted_result_sha256','source_sha256','source_manifest_sha256',
    'producer_ci_context','generic_image_sha256','Image_bytes','candidate_contract','new_grouped_method','new_fixture','artifact','current_predecessor'))
CURRENT_KEYS=frozenset(('packages','package_result_sha256','boot_sha256','backup_manifest_sha256',
    'plan_path','plan_sha256','execution_receipt_path','execution_receipt_sha256',
    'producer_host','packaging_host','execution_host','execution_host_pins'))
DEVICE_SCHEMA='note10-type3-scoped-output-device-v1'
CONTEXT_SCHEMA='type3-scoped-output-execution-v1'
DEVICE_KEYS=frozenset(('schema','status','execution_version','host_source_head','host_source_sha256','native_source_head','plan_sha256',
    'packages','package_result_sha256','bound_image_sha256','offline_contract_sha256','output','minimum_battery',
    'BOOT_write_max','reboot_max','user_availability_record_sha256','linked_growth_ack'))
SCOPED_FIELDS=('scoped_output_schema','scoped_output_marker','scoped_output_handle_bytes',
    'scoped_output_reads_per_success','scoped_output_retained_after_emit')
_DEVICE_READ=ContextVar('native116_device_read',default=None)


def require(value,message):data.require(value,message)


def record(head=None):
    from native_prefree_output_admission import is_head,record as prefree_record
    if is_head(head):return prefree_record()
    item=_NATIVE116
    require(type(item) is dict and set(item)==ORIGIN_KEYS,'native116 origin not bound by root acceptance')
    require(re.fullmatch('[0-9a-f]{40}',item['head'] or '') and
        all(re.fullmatch('[0-9a-f]{64}',item[key] or '') for key in
            ('result','image_sha256','source_manifest_sha256','test_result_sha256','fixture_result_sha256','plaintext_zip_sha256')) and
        type(item['pins']) is dict and len(item['pins'])==70 and
        all(type(k) is str and not Path(k).is_absolute() and '..' not in Path(k).parts and
            re.fullmatch('[0-9a-f]{64}',v or '') for k,v in item['pins'].items()) and
        type(item['producer_ci_context']) is dict and all(type(item[k]) is int and item[k]>0 for k in
            ('image_bytes','linked_bytes','run_id','attempt','job_id','artifact_id','workflow_id')) and
        item['linked_bytes']<=ro3.BUDGET and item['state_bytes']==88 and item['outcome_bytes']==128,
        'closed exact native116 accepted origin required')
    return dict(item,kind=scoped.KIND,version='v116',host_version='v117',witness_schema='n10-readonly-stage-witness-candidate-v1')


def is_head(head):
    from native_prefree_output_admission import is_head as prefree_head
    return prefree_head(head) or _NATIVE116 is not None and head==record()['head']


def provenance(head=None):
    return dict(version=record(head)['version'],PC_first_use=True,PC_only=False,operation_scope_PC_only=True,
        physical_ready=False,admission_blocked=True)


def stage_fields(head=None):
    from native_prefree_output_admission import is_head,fields
    return dict(**(fields() if is_head(head) else {}),readonly_stage_schema='n10-readonly-stage-witness-candidate-v1',readonly_stage_marker='N10DATASTAGE1',
        native_producer_provenance=provenance(head),scoped_output_schema=scoped.SCHEMA,
        scoped_output_marker='N10OUTPUTLEASE1',scoped_output_handle_bytes=24,
        scoped_output_reads_per_success=2,scoped_output_retained_after_emit=False)


def no_pc(row):
    require(row.get('schema') not in ('n10-output-lifetime-lease-pc-v1','n10-host-owned-output-adapter-pc-v1','n10-host-output-writer-pc-v1','n10-host-output-content-verification-pc-v1','n10-host-output-retirement-zero-pc-v1'),'PC schema permanently forbidden')
    require(row.get('PC_only') is not True and row.get('diagnostic_kind') not in
        ('output-lifetime-lease-pc','host-owned-output-adapter-pc','host-output-writer-pc','host-output-content-verification-pc','host-output-retirement-zero-pc',
         'readonly-input-pc','owned-contiguous-staging-pc','current-owned-staging-pc','kernel-readonly-span-pc') and
        not any(key in row for key in ('output_lease_schema','output_adapter_schema','output_writer_schema','output_verification_schema','output_retirement_schema',
            'readonly_input_schema','readonly_input_slot','readonly_pc_contract','kernel_readonly_span_schema')),
        'PC formats remain permanently forbidden for native116 admission')


def live_row(row):
    from type3_remaining_plan import selected as saved_selected,origin as saved_origin
    if saved_selected(row):
        no_pc(row);return saved_origin(row)
    no_pc(row)
    item=record(row.get('native_source_head'))
    require(row.get('source_head')==row.get('native_source_head')==item['head'] and
        row.get('native_producer_version')==item['version'] and row.get('execution_version')==row.get('version')==item['host_version'] and
        all(row.get(key)==item['kind'] for key in ('diagnostic_kind','data_input_kind','storage_input_kind')) and
        all(row.get(key)==value for key,value in stage_fields(item['head']).items()),'native116 requires separate exact live host117')
    from class3_native_origin import live_host
    live_host(row.get('host_profile_source_head'))
    require(row.get('host_profile_source_head') not in (item['head'],_NATIVE116['head'],'669f25ae9e164d6e079620d890e0b377fca75ce5'),
        'native producer/current111 host cannot become live host117')


def producer(result,head):
    no_pc(result)
    item=record(head)
    require(head==item['head'] and result.get('source_sha256')==item['pins'] and
        result.get('version')==item['version'] and result.get('diagnostic_kind')==item['kind'] and
        result.get('image_bytes')==item['image_bytes'] and result.get('image_sha256')==item['image_sha256'] and
        result.get('kernel_readonly3_linked_bytes')==item['linked_bytes'] and result.get('passed') is True and
        result.get('Image_built') is True and result.get('kernel_or_provider_executed') is False and
        result.get('ci_context',{}).get('GITHUB_SHA')==head and
        result.get('PC_only') is False and result.get('physical_ready') is False and
        result.get('operation_scope_PC_only') is True and result.get('admission_blocked') is True,
        'exact accepted native116 producing tuple required')
    accepted=ro3.producer_contract(result,head,producing_sources=item['pins'])
    require(result.get('kernel_readonly3_candidate_contract')==accepted and
        accepted['temporary_outcome_bytes']==128 and result.get('data_footprint',{}).get('data_state_bytes')==88,
        'accepted native116 compiler contract differs')
    return accepted


def ci_receipt(context,context_sha,binding,result):
    item=record(context.get('native_source_head') if type(context) is dict else None);producer(result,item['head'])
    keys=CI_CONTEXT_KEYS
    require(type(context) is dict and set(context)==keys and context['schema']==f"note10-root-native{item['version'][1:]}-ci-success-context-v1" and
        context['native_version']==item['version'] and context['native_source_head']==item['head'] and
        context['accepted_result_sha256']==item['result'] and context['source_sha256']==item['pins'] and
        context['source_manifest_sha256']==item['source_manifest_sha256'] and context['producer_ci_context']==item['producer_ci_context'] and
        context['generic_image_sha256']==item['image_sha256'] and context['Image_bytes']==item['image_bytes'] and
        context['candidate_contract']==result['kernel_readonly3_candidate_contract'] and
        re.fullmatch('[0-9a-f]{64}',context_sha or '') and
        binding.get('source_head')==item['head'] and binding.get('accepted_result_sha256')==item['result'] and
        binding.get('image_sha256')==item['image_sha256'] and binding.get('image_size')==item['image_bytes'] and
        binding.get('effective_config_sha256')==result.get('files_sha256',{}).get('actual-effective.config') and
        binding.get('build_evidence_id')==result.get('build_evidence_id') and
        binding.get('kernel_banner','').startswith(__import__('class3_native_origin').banner(binding)),
        'exact root native116 CI context/package binding differs')
    method=context['new_grouped_method'];fixture=context['new_fixture'];artifact=context['artifact']
    require(type(method) is dict and set(method)=={'source_head','result_sha256','selected','run','errors','failures','fixture_compiles','fixture_processes'} and
        method['source_head']==item['head'] and method['result_sha256']==item['test_result_sha256'] and
        method['selected']==(['test_actual_native_prefree_output_scan_and_cleanup'] if item['version']=='v121' else ['test_actual_native_scoped_output_transfer_emit_and_exact_cleanup']) and
        method['run']==1 and method['errors']==method['failures']==0 and method['fixture_compiles']==method['fixture_processes']==1 and
        (fixture==__import__('native_prefree_output_admission').FIXTURE_EVIDENCE if item['version']=='v121' else (
        type(fixture) is dict and set(fixture)=={'source_head','result_sha256','schema','cases','allocation_attempts','allocation_successes','free_calls','output_reads','hash_stub_calls','decoder_stub_calls','emit_frames'} and
        fixture==dict(source_head=item['head'],result_sha256=item['fixture_result_sha256'],schema='n10-native-scoped-output-fixture-v1',
            cases=6,allocation_attempts=12,allocation_successes=10,free_calls=10,output_reads=2,hash_stub_calls=16,decoder_stub_calls=4,emit_frames=16))) and
        type(artifact) is dict and artifact==dict(run_id=item['run_id'],attempt=item['attempt'],job_id=item['job_id'],
            workflow_id=item['workflow_id'],artifact_id=item['artifact_id'],plaintext_zip_sha256=item['plaintext_zip_sha256']),
        'native116 accepted single-source fixture/producer CI evidence differs')
    _baseline_context(context['current_predecessor'])
    from class3_native_origin import origin
    return dict(schema=f"native{item['version'][1:]}-root-ci-receipt-v1",kind=binding['device_profile']+'-accepted-image',accepted=True,
        root_reader_result_sha256=context_sha,producer_source_head=item['head'],ci_result_sha256=item['result'],
        image_sha256=item['image_sha256'],image_bytes=item['image_bytes'],
        effective_config_sha256=binding['effective_config_sha256'],build_evidence_id=binding['build_evidence_id'],
        kernel_banner=binding['kernel_banner'],native_origin=origin(item['head']),native_producer_provenance=provenance(item['head']),
        run_id=item['run_id'],attempt=item['attempt'],job_id=item['job_id'],workflow_id=item['workflow_id'],
        artifact_id=item['artifact_id'])


def receipt_binding(root,row,expected,binding):
    from sha256_kat_device_profile import read,sha
    root=Path(root);raw=data.bounded_private_read(root/'ci-success-context.json',65536)
    require(row==ci_receipt(json.loads(raw.decode('utf-8-sig')),data.sha(raw),binding,read(root/'result.json')),
        'native116 stored CI receipt differs')
    return dict(image_root_receipt_sha256=expected,root_reader_result_sha256=sha(root/'ci-success-context.json'))


def _baseline_context(item):
    require(type(item) is dict and set(item)==CURRENT_KEYS and
        all(item[key]==value for key,value in _CURRENT111_LINEAGE.items()),'exact private current111/code lineage context required')
    require(all(re.fullmatch('[0-9a-f]{64}',item[k] or '') for k in ('package_result_sha256','boot_sha256',
        'backup_manifest_sha256','plan_sha256','execution_receipt_sha256')),'private predecessor evidence pins required')
    from type3_admission import private
    require(all(type(item[k]) is str and str(private(item[k]))==item[k] for k in
        ('packages','plan_path','execution_receipt_path')),'canonical private predecessor paths required')
    return item


def _predecessor_context(contract):
    """Read private reviewed111 provenance; never acquire old execution privilege."""
    import type3_admission as typed
    raw=data.bounded_private_read(typed.private(contract['ci_success_context']),65536)
    require(data.sha(raw)==contract['ci_success_context_sha256'],'reviewed private native116 context changed')
    context=json.loads(raw.decode('utf-8-sig'));native=record(contract.get('native_source_head'))
    require(type(context) is dict and set(context)==CI_CONTEXT_KEYS and
        context['schema']==f"note10-root-native{native['version'][1:]}-ci-success-context-v1" and context['native_version']==native['version'] and
        context['native_source_head']==native['head'] and context['accepted_result_sha256']==native['result'] and
        context['source_sha256']==native['pins'] and context['source_manifest_sha256']==native['source_manifest_sha256'] and
        context['producer_ci_context']==native['producer_ci_context'] and context['generic_image_sha256']==native['image_sha256'] and
        context['Image_bytes']==native['image_bytes'],'exact private native116/predecessor context required before reservation')
    item=_baseline_context(context['current_predecessor'])
    from sha256_kat_device_profile import private,read,sha
    from type3_remaining_pack import HEAD,PINS,PACKAGING_HEAD,PACKAGING_PINS,FIELD
    require(item['producer_host']==HEAD and item['packaging_host']==PACKAGING_HEAD and
        item['execution_host']=='669f25ae9e164d6e079620d890e0b377fca75ce5' and
        type(item['execution_host_pins']) is dict and bool(item['execution_host_pins']) and
        all(contract[key]==item[other] for key,other in (
            ('current_packages','packages'),('current_package_result_sha256','package_result_sha256'),
            ('current_boot_sha256','boot_sha256'),('backup_manifest_sha256','backup_manifest_sha256'))),
        'exact current111 predecessor/contract differs')
    packages=private(item['packages']);row=read(packages/'package-result.json')
    require(sha(packages/'package-result.json')==item['package_result_sha256'] and
        sha(private(item['plan_path']))==item['plan_sha256'] and
        sha(private(item['execution_receipt_path']))==item['execution_receipt_sha256'] and
        row.get('host_profile_source_head')==HEAD and row.get('backup_manifest_sha256')==item['backup_manifest_sha256'] and
        row.get('host_profile_source_sha256')==dict(PINS) and
        row.get(FIELD,{}).get('packaging_host')==dict(host_profile_source_head=PACKAGING_HEAD,host_profile_source_sha256=dict(PACKAGING_PINS)) and
        any(p.get('mode')=='diagnostic' and p.get('payload_sha256')==item['boot_sha256'] for p in row.get('packages',[])),
        'saved current111 package/plan/terminal evidence differs')
    return row,item


def predecessor(contract):
    return _predecessor_context(contract)[0]


def growth_ack(head=None):
    item=record(head)
    return dict(reference_linked_bytes=scoped.REFERENCE_LINKED_BYTES,accepted_linked_bytes=item['linked_bytes'],
        delta_bytes=item['linked_bytes']-scoped.REFERENCE_LINKED_BYTES,acknowledged=True)


def execution_context(row,plan_sha,packages,declared_version,host_head,path,expected,execution_output):
    from type3_remaining_plan import selected as saved_selected,execution_context as saved_execution
    if saved_selected(row):return saved_execution(row,plan_sha,packages,declared_version,host_head,path,expected,execution_output)
    import type3_admission as typed
    from sha256_kat_device_profile import host_binding
    item=record(row.get('native_source_head'))
    live_row(row);offline=typed.candidate_scope(row,patched=True)
    completed=typed.read(Path(offline['output'])/'transaction.json')
    require(completed.get('status')=='complete' and completed.get('phase')=='complete' and
        completed.get('contract_sha256')==row['type3_contract_sha256'] and
        completed.get('result',{}).get('plan_sha256')==plan_sha,'complete fresh native116 offline transaction required')
    require(declared_version==item['host_version'] and host_head==row['host_profile_source_head'] and
        re.fullmatch('[0-9a-f]{64}',plan_sha or '') and path is not None and
        re.fullmatch('[0-9a-f]{64}',expected or ''),'explicit reviewed host117 device scope required')
    path=typed.private(path);raw=data.bounded_private_read(path,65536)
    require(data.sha(raw)==expected,'exact host117 device contract SHA required')
    contract=json.loads(raw.decode('utf-8-sig'))
    keys=DEVICE_KEYS
    from native_prefree_output_admission import device_schema,context_schema
    require(type(contract) is dict and set(contract)==keys,'closed native device object required')
    effective=typed.private(contract['packages'])
    require(packages is None or typed.private(packages)==effective,'explicit packages contradict closed device contract')
    packages=effective
    host=host_binding(host_head)
    require(type(contract) is dict and set(contract)==keys and contract['schema']==device_schema(item['head']) and
        contract['status']=='reviewed_ready' and contract['execution_version']==declared_version and
        contract['host_source_head']==host_head and contract['host_source_sha256']==host['host_profile_source_sha256'] and
        contract['native_source_head']==item['head'] and contract['plan_sha256']==plan_sha and
        contract['packages']==str(typed.private(packages)) and execution_output is not None and
        contract['output']==str(typed.private(execution_output)) and
        not typed.private(execution_output).is_relative_to(typed.private(packages)) and
        contract['bound_image_sha256']==row.get('image_sha256',row.get('kernel_image_sha256')) and
        contract['offline_contract_sha256']==row['type3_contract_sha256'] and
        contract['linked_growth_ack']==growth_ack(item['head']) and type(contract['linked_growth_ack']) is dict and
        contract['linked_growth_ack'].get('acknowledged') is True and
        all(type(contract['linked_growth_ack'][k]) is int for k in ('reference_linked_bytes','accepted_linked_bytes','delta_bytes')) and
        all(type(contract[k]) is int and contract[k]==v for k,v in
            (('minimum_battery',10),('BOOT_write_max',1),('reboot_max',1))) and
        contract['user_availability_record_sha256']=='4a639d278836af88256a339d199b9fbe53ad65d354db4b8c4401796522e758e9',
        'closed host117 device contract/plan/growth scope differs')
    require(data.sha(data.bounded_private_read(typed.private(packages)/'package-result.json',4*1024*1024))==
        contract['package_result_sha256'],'reviewed host117 package metadata changed')
    return dict(schema=context_schema(item['head']),declared_version=item['host_version'],host_source_head=host_head,
        host_source_sha256=host['host_profile_source_sha256'],plan_sha256=plan_sha,packages=str(typed.private(packages)),
        output=str(typed.private(execution_output)),contract_path=str(path),contract_sha256=expected,
        linked_growth_ack=contract['linked_growth_ack'])


def require_device_scope(row,ack,context):
    from type3_remaining_plan import selected as saved_selected,require_device_scope as saved_scope
    if saved_selected(row):return saved_scope(row,ack,context)
    require(ack is True,'host117 requires explicit measured growth ACK before device query')
    keys={'schema','declared_version','host_source_head','host_source_sha256','plan_sha256','packages','output',
        'contract_path','contract_sha256','linked_growth_ack'}
    from native_prefree_output_admission import context_schema
    require(type(context) is dict and set(context)==keys and context.get('schema')==context_schema(row.get('native_source_head')),
        'separate exact host117 execution context required before transport')
    expected=execution_context(row,context['plan_sha256'],context['packages'],context['declared_version'],
        context['host_source_head'],context['contract_path'],context['contract_sha256'],context['output'])
    require(context==expected,'host117 execution context differs')
    return True


def device_reader(function):
    """Validate direct precheck/collect entry before granting metadata-only scope."""
    @wraps(function)
    def checked(packages,kernel_build,*args,**kwargs):
        import type3_admission as typed
        import sha256_kat_device_profile as profile
        row=profile.read(profile.private(packages)/'package-result.json')
        if not scoped.selected(row):return function(packages,kernel_build,*args,**kwargs)
        from type3_remaining_plan import selected as saved_selected,device_reader as saved_reader
        if saved_selected(row):return saved_reader(function,packages,kernel_build,*args,**kwargs)
        context=kwargs.get('type3_context')
        typed.require_context_directory(context,packages)
        require_device_scope(row,kwargs.get('ack_kernel_readonly_growth',False),context)
        report=profile.read(profile.private(kernel_build)/'build-result.json')
        offline=typed.candidate_scope(report,patched=True)
        require(profile.private(kernel_build)==Path(offline['output'])/'plan/cycle-01/kernel-build',
            'host117 device read requires exact completed variant path')
        require(all(row.get(k)==v for k,v in profile.fields(report).items()) and
            profile.sha(profile.private(kernel_build)/'handoff.config')==report['effective_config_sha256'],
            'host117 package/variant metadata/config differs')
        token=_DEVICE_READ.set(dict(context=context,root=str(profile.private(kernel_build)),report=report))
        try:return function(packages,kernel_build,*args,**kwargs)
        finally:_DEVICE_READ.reset(token)
    return checked


def device_metadata(root,token=None,template=None):
    import type3_admission as typed
    scope=_DEVICE_READ.get()
    require(scope is not None and str(typed.private(root))==scope['root'],'exact host117 read-only variant scope required')
    report=typed.read(typed.private(root)/'build-result.json')
    from sha256_kat_device_profile import sha
    require(report==scope['report'] and sha(typed.private(root)/'handoff.config')==report['effective_config_sha256'] and token==report.get('auto_cycle_token') and
        (template is None or str(typed.private(template))==report.get('auto_cycle_template')),
        'host117 saved metadata/token changed')
    typed.candidate_scope(report,patched=True)
    return report


def device_precheck_receipt(context,path):
    from type3_remaining_plan import CONTEXT119_SCHEMA as saved_schema,precheck_receipt
    if context is not None and context.get('schema')==saved_schema:return precheck_receipt(context,path)
    import type3_admission as typed
    require(_DEVICE_READ.get() is not None and context is not None and context.get('schema') in (CONTEXT_SCHEMA,'type3-prefree-output-execution-v1'),
        'validated host117 read scope required before precheck output')
    target=typed.private(context['output'])/'PREINSTALL-CHECK-01.json'
    require((path is None or typed.private(path)==target) and not target.exists() and
        not target.is_relative_to(typed.private(context['packages'])),'fresh host117 precheck receipt required')
    return target


def decode_joined(text,identity,cycle,legacy,stages,*,producer_kind=None):
    from decode_reservation import checksum
    from native_prefree_output_zero import KIND as prefree_kind
    prefree=producer_kind==prefree_kind
    lines=[line for line in text.splitlines() if 'N10OUTPUTLEASE' in line]
    require(len(lines)==1,'one native116 output-scope companion required')
    match=re.search(r'N10BOOTLINK2 boot=([0-9a-f]{32}) N10OUTPUTLEASE1 ([^\r\n\x00]{1,447}) checksum=([0-9a-f]{8})$',lines[0])
    require(match is not None and match[1]==legacy['boot_identity'] and match[1]!='0'*32 and
        checksum(match[2].encode('ascii'))==int(match[3],16),'output-scope boot/checksum differs')
    prefix=f'id={identity} cycle={cycle} kind=output_scope schema={scoped.WIRE_SCHEMA} '
    require(match[2].startswith(prefix),'output-scope id/cycle/schema differs')
    fields=re.fullmatch(r'flags=([0-9a-f]{8}) reads=([012]) allocator=vmalloc retained_after_emit=0 lease_cleanup=(not_called|void_returned) ownership=0 hardware=0 executed=0',match[2][len(prefix):])
    require(fields is not None,'closed output-scope frame required')
    bits=int(fields[1],16);reads=int(fields[2]);require(not bits&~0x7ff,'unknown output-scope flags')
    names=('offered','borrowed','first_returned','last_returned','released','retired','clear_called','clear_returned','free_called','free_returned','refused')
    flags={name:bool(bits&(1<<i)) for i,name in enumerate(names)}
    require(reads==int(flags['first_returned'])+int(flags['last_returned']),'output-scope read count contradicts flags')
    for a,b in (('borrowed','offered'),('first_returned','borrowed'),('last_returned','first_returned'),
        ('released','last_returned'),('retired','offered'),('clear_called','retired'),('free_called','clear_returned')):
        require(prefree and a=='clear_called' and not flags['offered'] or not flags[a] or flags[b],'contradictory output-scope sequence')
    for op in ('clear','free'):
        require(flags[op+'_called']==flags[op+'_returned'],'incomplete output-scope cleanup return')
    require(flags['clear_called']==flags['free_called'] and fields[3]==('void_returned' if flags['free_returned'] else 'not_called'),
        'output-scope cleanup text contradicts flags')
    if flags['offered']:
        require(stages['events']['digest_ok'] and stages['events']['work_free_returned'] and
            flags['free_returned']==stages['events']['output_free_returned'] and flags['free_returned'],
            'output transfer/stage/cleanup differs')
    phase=legacy['status']
    if phase=='ok':require(legacy['passed'] and stages['passed'] and bits==0x3ff and reads==2,'successful output scope incomplete')
    elif phase=='output_consumer':require(flags['offered'] and flags['refused'] and flags['retired'] and
        flags['free_returned'] and not flags['released'] and reads==0 and not legacy['passed'],'consumer refusal scope differs')
    elif prefree and phase=='output_zero_observation' and flags['offered']:
        require(flags['free_returned'] and not legacy['passed'],'failed prefree observation cannot pass')
    else:require(bits in ((0,0x3c0) if prefree else (0,)) and reads==0 and
        (not prefree or flags['free_returned']==stages['events']['output_free_returned']),'unoffered output cannot claim scoped lifetime')
    return dict(schema=scoped.WIRE_SCHEMA,boot_identity=match[1],flags=bits,events=flags,reads=reads,
        passed=phase=='ok' and bits==0x3ff,cleanup_result=fields[3],cleanup_semantics='void_call_boundaries_only',
        retained_after_emit=False,global_RAM_ownership=False,hardware=False,xnu_executed=False)


def require_pack_transaction(root,output,token):
    """Device read scope cannot authorize a new packing operation."""
    import type3_admission as typed
    from type3_remaining_plan import selected as saved_selected
    require(not saved_selected(typed.read(typed.private(root)/'build-result.json')),'retained117 metadata is read-only; packing refused')
    require(_DEVICE_READ.get() is None,'host117 device metadata scope is read-only; packing refused')
    root=typed.private(root);row=typed.read(root/'build-result.json');contract=typed.candidate_scope(row,patched=True)
    typed.transaction(dict(contract,_contract_sha256=row['type3_contract_sha256']),'plan_reserved')
    require(root==Path(contract['output'])/'plan/cycle-01/kernel-build' and
        typed.private(output)==Path(contract['output'])/'plan/cycle-01/boot.img' and token==row['auto_cycle_token'] and
        not Path(output).exists(),'one fresh host117 intrinsic packing output required')
