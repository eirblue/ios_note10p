"""Typed generated-BOOT role and saved123 package/plan tail; no BOOT/Image regeneration."""
import argparse
import copy
from contextlib import contextmanager
from contextvars import ContextVar
import json
from pathlib import Path
import re
import linux_data_carrier as data
import native_prefree_output_admission as native
import type3_remaining_template as prior
HEAD='022da24ead8561aded6c96b00777e821fc8aa4ce'
PINS=native._freeze({'note10/device_test/affinity_binding.py': '6d5b16d54a803c95bdd391a38efbd2bac5ef36baffe199f86cd83f878bf10678',
 'note10/device_test/auto_cycle.py': '64cd356b88e828a516edf049f93e40ee283e1cd8bec2e575fe77baadc4aafa20',
 'note10/device_test/build_boot_test_packages.py': '17b973f54185521be6685acb5e019f8bf8b5f10897d01c0167929c97859cddef',
 'note10/device_test/build_kernel_readonly_input.py': '5391edfa477324dbdd5f4d9c6fb13deb5df8a66b2ed4df7d018213012b227000',
 'note10/device_test/build_kernel_readonly_span_candidate.py': '7ebcce1d50932d59d431f4be417c3637d18570b19b7b735f9543af2f9e1b2b75',
 'note10/device_test/build_kernel_readonly_span_pc.py': 'cd42e0dec6570bcc09c7a07695560eae13a62420d744e16035c4da3a57c588e9',
 'note10/device_test/build_readonly_input_pc.py': '893698f6741fd178334777b4f96c98934d78b5a927fe4cf3d383d92e90557d9e',
 'note10/device_test/builtin_init_profile.py': '88b655785cd5cbc88265d003d829639ca63be4c0f20dad687e930f6981b38af3',
 'note10/device_test/builtin_init_route.py': '46b100dc95f11e344c11b8cb3fba5d34d17b2884385923426a42246699fda43d',
 'note10/device_test/carrier_lzma.c': 'e204732754f15929f7134885ec2740e1ed26f0291dd64c7df7957a4aee7b987a',
 'note10/device_test/carrier_lzma.h': '6790aa17da94025e0bab175377573edb8df3f503c8cde86f8c919e33ee742974',
 'note10/device_test/class3_native_origin.py': 'c739ce85dd586b959d74156a1005cd15ec6419ae3d29d7ed9b0ee98d3b2e334a',
 'note10/device_test/current_data_reuse.py': '15c7a5a55e22f4445c216904769d7ba9b6367f792122e5b936305c95ae031129',
 'note10/device_test/early_fdt_binding.py': 'd4f7099fb45eca31c83c9acd9fbfe0cd5c7ccc5c271c18180e3672e22f9a6b78',
 'note10/device_test/kernel_readonly_input.h': '4aa99ff2ab756b854174eb2519af96e79669f82114293790a538ddd3025298ea',
 'note10/device_test/kernel_readonly_input.py': '8920a316c0ce45b5ab5989e239cfa79282f3afc78ce63e320ade82676f081f83',
 'note10/device_test/kernel_readonly_input_fixture.c': '6300f13ba284b4f42614a4c6cda8f09c6e6671e88d6e524ec24dacd3a7ab70e0',
 'note10/device_test/kernel_readonly_span.h': 'dd0640b8322fb86c8baa29863a931ddb7d005dd589352ba4136c09bdb79de86d',
 'note10/device_test/kernel_readonly_span_candidate.h': '8f8e8522a7b03413b3db59f21fca5cefa4b74fb9e63a412dfc9d6067beb5dec1',
 'note10/device_test/kernel_readonly_span_candidate.py': 'f4ed3e0f81d9b3d1dafdcf2fdcfa416d1abb54df8dbd4765a989df1c5e0150f8',
 'note10/device_test/kernel_readonly_span_candidate_fixture.c': 'b4d02ff71b82365915fca0c112170de9c44184dcce481656832e69e77dee9f29',
 'note10/device_test/kernel_readonly_span_fixture.c': 'afbc9ae410e15bf7221e10a4cbcb325702a3a0235dec0fe585b836e7dae467c6',
 'note10/device_test/linux_data_carrier.c': 'a9fd626d384ac6b3fd3d8d705debdc3a1daa34ac1886a51ef8788f57e408c53d',
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
 'note10/device_test/materialize_auto_cycle.py': 'fc05e3161f13831106e8c75cc5529a1d9ffbc8dab55151f416b0fa184d543b97',
 'note10/device_test/native_memory_observation.py': 'f4acd0f310989bfcd1b0c2039fef6e429e8ec4d4f41ebdb94fc483538fa26663',
 'note10/device_test/native_prefree_output_admission.py': 'e0b450442414f6418d31508aab3c3ba07a42a11ed16bc928a16060a34c69d817',
 'note10/device_test/native_prefree_output_zero.py': 'cb580469be605f952bfa0e2b4a884bf9877edb70ebe48e25cf5f3fd5dc2c25f5',
 'note10/device_test/native_scoped_output.py': '28567462f0bcb45ba4ed94eb3736bf8ba28c22058262acee0b3f2ffc20496146',
 'note10/device_test/native_scoped_output_admission.py': '77ae3256efeba42d9c9f0b836a4c09bcc2eb9816be5f4b3c59b42526db67dd6f',
 'note10/device_test/precheck_window_access.py': '3ef3859ef2a4c154e93e5db7846bde78eb9061742243dba435187a9087226e28',
 'note10/device_test/prepare_linux_boot.py': '0499a630875cb4319e4bdfb33c02d0bac3e31538b24997bac794357b95a5298f',
 'note10/device_test/readonly_input_pc.h': '01b18e5fddcd12fba45190baa337b47c3309f54cc7a448cd6d72209c5ba8a3f0',
 'note10/device_test/readonly_input_pc.py': 'd7125058dc85a57eb4283fccf87bcb6af96c26de1363f81d1acb0999b94f1fc7',
 'note10/device_test/readonly_input_pc_fixture.c': '99f0e7eb9240b5c08314993a14dfcd9a532df0e24158679cdbed8b0c3c752730',
 'note10/device_test/readonly_stage_witness.h': '85851db4c9622842f4ccc547e7532139f306917d8674c0298529e5041fb08330',
 'note10/device_test/readonly_stage_witness.py': '2d8a4a6affa7e49459e92bd5b2b4ba3787177bf28786c13c3611d8b64f8653b8',
 'note10/device_test/readonly_stage_witness_fixture.c': '2513117dd52b2c8ef92a6f0c161af3a2e1fe6060e24dc9b166d187c5a3fd0cec',
 'note10/device_test/retained_v108_origin.py': '737e3de25884daee64e8dc4d938b81e5b2f328a5923a4b6cea0b2c92b0db24f7',
 'note10/device_test/sha256_kat_device_profile.py': 'ad435f487275260eea0e77bc73152631a8513826cc661083a89809815e08ce9b',
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
 'note10/device_test/test_v119_saved118_device_entry.py': '31bb6bb79189c9bf18bdad7ab5b040d94888fdbed8c4785ae6335ac4810c6dce',
 'note10/device_test/test_v122_native_prefree_output_admission.py': '61a619e7188b39daca018655374625d33e25921000349bbc694924f2e0473d0c',
 'note10/device_test/test_v123_native121_remaining_template.py': '4a50d09e40c09a9d2fb7bc2599f910bd6e3373d5b53a923569baff5642fbc45d',
 'note10/device_test/test_v99_carrier_compare_evidence.py': '2b45c21197709706d3f3ffc23e1428084d5d50a93a1d9b5bd22c2693124cf20c',
 'note10/device_test/test_v99_host_profile_origin.py': 'fb4a1c349ca298b4f18ba64e0692c7a93e9f0877b2f7a7ec22fa2c8f29ac219a',
 'note10/device_test/type3_admission.py': 'd4dbacbe36f6037ba3653ed51ae818557c829ebbb268566720b36d76ed5d66ba',
 'note10/device_test/type3_remaining_pack.py': 'd39c393f9c421a59580df7f64a9cc3fe4fe333065d440e981316734030d97dce',
 'note10/device_test/type3_remaining_plan.py': '16a9fcbcba505d60731682bdd2704a8a0089dcf29c10bc352509b693f98e3ecc',
 'note10/device_test/type3_remaining_template.py': '7bbdd29576314dc7e579584fb71390017ff31ee96f2581e6da1d737513712b73'})
BOOT_KEYS=frozenset(('abox_failed_fw_resume_guard',
 'abox_pm_audit_diagnostic',
 'abox_pm_audit_evidence_version',
 'abox_pmu_audit_diagnostic',
 'abox_pmu_audit_evidence_version',
 'accepted_result_sha256',
 'aosp_mkbootimg_sha256',
 'auto_cycle_token',
 'auto_return_diagnostic',
 'backup_manifest_sha256',
 'boot_partition_size',
 'build_evidence_id',
 'builtin_idle_init',
 'builtin_init_manifest_sha256',
 'command',
 'cpu_cache_roundtrip_diagnostic',
 'cpu_pm_notifier_counts',
 'cpu_pm_notifier_counts_version',
 'cpu_pm_notifier_trace',
 'cpu_pm_notifier_trace_version',
 'cpu_pm_roundtrip',
 'cpu_pm_roundtrip_version',
 'data_carrier_bytes',
 'data_carrier_sha256',
 'data_carrier_stage',
 'data_expectation_mode',
 'data_expectation_slot',
 'data_input_kind',
 'data_manifest_sha256',
 'data_payload_bytes',
 'data_payload_sha256',
 'data_relative_placement_admitted',
 'deployment_ready',
 'device_boot_tested',
 'device_operations',
 'device_profile',
 'diagnostic_kind',
 'dma_pm_audit_diagnostic',
 'dma_pm_audit_evidence_version',
 'early_xnu_reservation',
 'ehld_irqsave_audit',
 'ehld_irqsave_audit_version',
 'ehld_lock_audit',
 'ehld_lock_audit_version',
 'ehld_running_lock_audit',
 'ehld_running_lock_audit_version',
 'embedded_initramfs_check',
 'embedded_recovery_dtbo',
 'execution_version',
 'existing_recovery_partition_sha256',
 'external_ramdisk_included',
 'file',
 'fpsimd_reference_audit',
 'fpsimd_reference_audit_version',
 'gic_priority_restore',
 'gic_priority_restore_version',
 'gic_roundtrip_diagnostic',
 'gic_roundtrip_evidence_version',
 'guarded_init_main_sha256',
 'host_profile_source_head',
 'host_profile_source_sha256',
 'image_expectation_patched',
 'image_root_receipt_sha256',
 'initramfs_cpio_sha256',
 'iommu_pm_audit_diagnostic',
 'iommu_pm_audit_evidence_version',
 'kernel_banner',
 'kernel_build_sha256',
 'kernel_readonly3_image_bytes',
 'kernel_readonly3_linked_bytes',
 'kernel_readonly3_marker',
 'kernel_readonly3_requires_ack',
 'kernel_readonly3_schema',
 'kernel_readonly3_slot',
 'kernel_readonly3_span',
 'kernel_readonly3_span_schema',
 'kind',
 'minimal_init_elf_sha256',
 'native_producer_PC_first_use',
 'native_producer_provenance',
 'native_producer_version',
 'native_source_head',
 'original_avb_footer_copied',
 'original_boot_sha256',
 'partition_writes',
 'pm_branch_diagnostic',
 'pm_branch_version',
 'pm_callbacks_diagnostic',
 'pm_callbacks_evidence_version',
 'pm_cpus_diagnostic',
 'pm_cpus_evidence_version',
 'pm_edge_inventory_diagnostic',
 'pm_edge_inventory_evidence_version',
 'pm_irq_diagnostic',
 'pm_irq_evidence_version',
 'pm_noirq_diagnostic',
 'pm_noirq_evidence_version',
 'pm_post_arch_diagnostic',
 'pm_post_arch_evidence_version',
 'pm_preconditions_diagnostic',
 'pm_preconditions_version',
 'pm_quiesce_diagnostic',
 'pm_quiesce_evidence_version',
 'pm_timer_diagnostic',
 'pmu_control_audit',
 'pmu_control_audit_version',
 'pmu_failure_restore',
 'pmu_failure_restore_version',
 'pmu_settle_diagnostic',
 'pmu_settle_evidence_version',
 'pmu_state_audit',
 'pmu_state_audit_version',
 'prefree_output_capacity_source',
 'prefree_output_handle_bytes',
 'prefree_output_marker',
 'prefree_output_retained_after_emit',
 'prefree_output_scan_phase',
 'prefree_output_schema',
 'preserved_boot_os_version',
 'preserved_boot_security_patch_month',
 'profile_sha256',
 'prototype_created',
 'raw_input_binding',
 'rcu_context_audit',
 'rcu_context_audit_version',
 'readonly_stage_marker',
 'readonly_stage_schema',
 'recovery_reentry_verified_after_install',
 'reference_ramdisk_sha256',
 'requires_existing_dtb_dtbo_partitions',
 'root_reader_result_sha256',
 'samsung_boot_trailer_preserved',
 'scope',
 'scoped_output_handle_bytes',
 'scoped_output_marker',
 'scoped_output_reads_per_success',
 'scoped_output_retained_after_emit',
 'scoped_output_schema',
 'screen_log_diagnostic',
 'sha256',
 'size',
 'source_head',
 'storage_input_kind',
 'type3_compact_bytes',
 'type3_compact_manifest_sha256',
 'type3_compact_sha256',
 'type3_contract_path',
 'type3_contract_sha256',
 'type3_external_choice',
 'type3_generic_image_sha256',
 'type3_materialization',
 'type3_native_origin',
 'type3_remaining_template',
 'ufs_pm_audit_diagnostic',
 'ufs_pm_audit_evidence_version',
 'version',
 'window_access_diagnostic',
 'xnu_payload_sha256',
 'xnu_payload_size',
 'xnu_payload_stage_diagnostic'))
MANIFEST_KEYS=frozenset(('abox_failed_fw_resume_guard',
 'abox_pm_audit_diagnostic',
 'abox_pm_audit_evidence_version',
 'abox_pmu_audit_diagnostic',
 'abox_pmu_audit_evidence_version',
 'auto_cycle_token',
 'auto_return_diagnostic',
 'automatic_reboot',
 'cpu_cache_roundtrip_diagnostic',
 'cpu_pm_notifier_counts',
 'cpu_pm_notifier_counts_version',
 'cpu_pm_notifier_trace',
 'cpu_pm_notifier_trace_version',
 'cpu_pm_roundtrip',
 'cpu_pm_roundtrip_version',
 'dma_pm_audit_diagnostic',
 'dma_pm_audit_evidence_version',
 'ehld_irqsave_audit',
 'ehld_irqsave_audit_version',
 'ehld_lock_audit',
 'ehld_lock_audit_version',
 'ehld_running_lock_audit',
 'ehld_running_lock_audit_version',
 'fpsimd_reference_audit',
 'fpsimd_reference_audit_version',
 'gic_priority_restore',
 'gic_priority_restore_version',
 'gic_roundtrip_diagnostic',
 'gic_roundtrip_evidence_version',
 'iommu_pm_audit_diagnostic',
 'iommu_pm_audit_evidence_version',
 'mode',
 'payload_sha256',
 'payload_size',
 'pm_branch_diagnostic',
 'pm_branch_version',
 'pm_callbacks_diagnostic',
 'pm_callbacks_evidence_version',
 'pm_cpus_diagnostic',
 'pm_cpus_evidence_version',
 'pm_edge_inventory_diagnostic',
 'pm_edge_inventory_evidence_version',
 'pm_irq_diagnostic',
 'pm_irq_evidence_version',
 'pm_noirq_diagnostic',
 'pm_noirq_evidence_version',
 'pm_post_arch_diagnostic',
 'pm_post_arch_evidence_version',
 'pm_preconditions_diagnostic',
 'pm_preconditions_version',
 'pm_quiesce_diagnostic',
 'pm_quiesce_evidence_version',
 'pm_timer_diagnostic',
 'pmu_control_audit',
 'pmu_control_audit_version',
 'pmu_failure_restore',
 'pmu_failure_restore_version',
 'pmu_settle_diagnostic',
 'pmu_settle_evidence_version',
 'pmu_state_audit',
 'pmu_state_audit_version',
 'preserves_on_disk',
 'rcu_context_audit',
 'rcu_context_audit_version',
 'recovery_reentry_guaranteed',
 'scope',
 'screen_log_diagnostic',
 'test_purpose',
 'ufs_pm_audit_diagnostic',
 'ufs_pm_audit_evidence_version',
 'updater_sha256',
 'window_access_diagnostic',
 'writes',
 'xnu_payload_sha256',
 'xnu_payload_size',
 'xnu_payload_stage_diagnostic'))
PAIR_KEYS=frozenset(('abox_failed_fw_resume_guard',
 'abox_pm_audit_diagnostic',
 'abox_pm_audit_evidence_version',
 'abox_pmu_audit_diagnostic',
 'abox_pmu_audit_evidence_version',
 'auto_cycle_token',
 'auto_return_diagnostic',
 'backup_manifest_sha256',
 'builder_device_operations',
 'cpu_cache_roundtrip_diagnostic',
 'cpu_pm_notifier_counts',
 'cpu_pm_notifier_counts_version',
 'cpu_pm_notifier_trace',
 'cpu_pm_notifier_trace_version',
 'cpu_pm_roundtrip',
 'cpu_pm_roundtrip_version',
 'deployment_ready',
 'device_boot_tested',
 'dma_pm_audit_diagnostic',
 'dma_pm_audit_evidence_version',
 'ehld_irqsave_audit',
 'ehld_irqsave_audit_version',
 'ehld_lock_audit',
 'ehld_lock_audit_version',
 'ehld_running_lock_audit',
 'ehld_running_lock_audit_version',
 'expected_current_boot_sha256',
 'fpsimd_reference_audit',
 'fpsimd_reference_audit_version',
 'gic_priority_restore',
 'gic_priority_restore_version',
 'gic_roundtrip_diagnostic',
 'gic_roundtrip_evidence_version',
 'iommu_pm_audit_diagnostic',
 'iommu_pm_audit_evidence_version',
 'kernel_image_sha256',
 'manual_test_packages_created',
 'packages',
 'pm_branch_diagnostic',
 'pm_branch_version',
 'pm_callbacks_diagnostic',
 'pm_callbacks_evidence_version',
 'pm_cpus_diagnostic',
 'pm_cpus_evidence_version',
 'pm_edge_inventory_diagnostic',
 'pm_edge_inventory_evidence_version',
 'pm_irq_diagnostic',
 'pm_irq_evidence_version',
 'pm_noirq_diagnostic',
 'pm_noirq_evidence_version',
 'pm_post_arch_diagnostic',
 'pm_post_arch_evidence_version',
 'pm_preconditions_diagnostic',
 'pm_preconditions_version',
 'pm_quiesce_diagnostic',
 'pm_quiesce_evidence_version',
 'pm_timer_diagnostic',
 'pmu_control_audit',
 'pmu_control_audit_version',
 'pmu_failure_restore',
 'pmu_failure_restore_version',
 'pmu_settle_diagnostic',
 'pmu_settle_evidence_version',
 'pmu_state_audit',
 'pmu_state_audit_version',
 'prototype_sha256',
 'rcu_context_audit',
 'rcu_context_audit_version',
 'scope',
 'screen_log_diagnostic',
 'ufs_pm_audit_diagnostic',
 'ufs_pm_audit_evidence_version',
 'window_access_diagnostic',
 'xnu_payload_sha256',
 'xnu_payload_size',
 'xnu_payload_stage_diagnostic'))
SCHEMA='note10-native121-saved123-package-tail-v124-v1'
FIELD='type3_remaining_packages'
FIELD_SCHEMA='saved123-boot-live124-packages-v1'
DEVICE_SCHEMA='note10-native121-package-tail-device-v124-v1'
CONTEXT_SCHEMA='native121-package-tail-execution-v124-v1'
KEYS=frozenset(('schema','status','execution_version','execution_host_source_head','execution_host_source_sha256','prior_contract','prior_transaction','prior_operator','prior_trace','variant_report','variant_config','boot_metadata','boot_path','boot_stat','output','caps'))
CAPS=dict(template_tail_replays=0,templates=0,compact_attachments=0,materializations=0,variant_validations=0,BOOT_regenerations=0,mkbootimg=0,Image_reads=0,decoder_or_MachO_replays=0,paired_packages=1,plans=1,cycles_generated=0,saved_BOOT_intrinsic_packager_reads=1,Image_builds=0,CI=0,device_queries=0,BOOT_writes=0,reboots=0)
_SCOPE=ContextVar('saved123_boot_package124',default=None)

def require(v,m):data.require(v,m)
def private(p):return __import__('type3_admission').private(p)
def read(p):return __import__('type3_admission').read(p)
def save(p,v):return __import__('type3_admission').save(p,v)
def sha(p):
    p=private(p);require(p.name not in ('Image','kernel-readonly.data','boot.img'),'package-tail metadata loader cannot read binary inputs')
    return data.sha(data.bounded_private_read(p,4*1024*1024))
def _pin(v):
    require(type(v) is dict and set(v)=={'path','sha256'} and re.fullmatch('[0-9a-f]{64}',v['sha256'] or ''),'closed124 metadata pin required')
    p=private(v['path']);require(str(p)==v['path'] and sha(p)==v['sha256'],'saved123 metadata pin changed');return p

def selected(row):return FIELD in row

def load(path,expected):
    import sha256_kat_device_profile as profile
    path=private(path);require(sha(path)==expected,'exact reviewed124 package-tail contract SHA required');c=read(path)
    require(type(c) is dict and set(c)==KEYS and c['schema']==SCHEMA and c['status']=='reviewed_ready' and c['execution_version']=='v124' and c['caps']==CAPS and all(type(x) is int for x in c['caps'].values()),'closed124 package-tail contract required')
    host=profile.host_binding(c['execution_host_source_head']);require(host['host_profile_source_sha256']==c['execution_host_source_sha256'] and host['host_profile_source_head']!=HEAD,'separate live124 code closure required')
    old=read(_pin(c['prior_contract']));j=read(_pin(c['prior_transaction']));operator=read(_pin(c['prior_operator']));trace=_pin(c['prior_trace']).read_text(encoding='utf-8')
    require(set(old)==prior.KEYS and old.get('schema')==prior.SCHEMA and old.get('status')=='reviewed_ready' and old.get('execution_version')=='v123' and old.get('execution_host_source_head')==HEAD and old.get('execution_host_source_sha256')==dict(PINS) and old.get('caps')==prior.CAPS,'exact retained123 composing/materializing origin91 required')
    require(j.get('schema')=='saved122-template-remaining-journal-v1' and j.get('status')=='failed_no_restart' and j.get('phase')=='plan_reserved' and j.get('contract_sha256')==c['prior_contract']['sha256'] and j.get('counts')==dict(template_tail=1,materializations=1,variant_validations=1,packs=1,plans=1),'exact spent123 attempt counters required; not completed pairs/plan')
    require(operator.get('schema')=='v123-remaining-template-operator-receipt-v1' and operator.get('success') is False and operator.get('invocation_attempts')==1 and operator.get('invocation_exit_code')==1 and operator.get('contract_sha256')==c['prior_contract']['sha256'] and operator.get('transaction_sha256')==c['prior_transaction']['sha256'] and operator.get('stderr_sha256')==c['prior_trace']['sha256'] and 'package_scope' in trace and 'frozen122/native121 template fields differ' in trace,'exact saved123 package-entry failure required')
    original=read(_pin(old['original_contract']));template=private(old['template_root']);require(set(old['template_files'])==prior.FILES and all(sha(template/n)==old['template_files'][n] for n in prior.FILES),'immutable122 carried metadata differs')
    binding=read(template/'device-profile.json');report=read(template/'build-result.json')
    import type3_admission as typed
    import class3_native_origin as origins
    import native_scoped_output_admission as shared
    require(set(original)==typed.OFFLINE_KEYS and original.get('schema')==typed.OFFLINE_SCHEMA and original.get('status')=='reviewed_ready' and original.get('caps')==typed.OFFLINE_CAPS and original.get('execution_version')=='v122' and original.get('host_source_head')==prior.HEAD and original.get('native_source_head')==native.record()['head'] and original.get('accepted_result_sha256')==native.record()['result'],'closed original122/native121 composition required')
    require(binding.get('version')==binding.get('execution_version')=='v122' and binding.get('source_head')==native.record()['head'] and all(binding.get(k)==native.record()['kind'] for k in ('diagnostic_kind','data_input_kind','storage_input_kind')) and binding.get('native_producer_version')=='v121' and binding.get('type3_native_origin')==origins.origin(native.record()['head']) and binding.get('image_sha256')==native.record()['image_sha256'] and binding.get('image_size')==native.record()['image_bytes'] and all(binding.get(k)==v for k,v in shared.stage_fields(native.record()['head']).items()),'exact122/native121 immutable producer tuple required')
    require(binding.get('host_profile_source_head')==prior.HEAD and binding.get('host_profile_source_sha256')==dict(prior.PINS) and binding.get('native_source_head')==native.record()['head'] and binding.get('type3_contract_sha256')==old['original_contract']['sha256'] and sha(template/'result.json')==native.record()['result'],'exact native121/template122 origin required')
    oldctx=dict(contract=old,path=c['prior_contract']['path'],sha256=c['prior_contract']['sha256'],original=original,template=template,binding=binding,report=report,host=dict(host_profile_source_head=HEAD,host_profile_source_sha256=dict(PINS)),output=private(old['output']),tail_validated=True)
    variant=private(old['output'])/'plan/cycle-01/kernel-build';require(_pin(c['variant_report'])==variant/'build-result.json' and _pin(c['variant_config'])==variant/'handoff.config','exact saved123 variant metadata required')
    bound=read(variant/'build-result.json');require(bound.get(prior.FIELD)==prior.marker(oldctx) and bound.get('host_profile_source_head')==HEAD and bound.get('host_profile_source_sha256')==dict(PINS) and bound.get('version')==bound.get('execution_version')=='v123' and bound.get('effective_config_sha256')==c['variant_config']['sha256'] and bound.get('native_source_head')==native.record()['head'],'saved123 variant/config/producer lineage differs')
    witness=bound.get('type3_materialization',{})
    require(bound.get('source_head')==bound.get('native_source_head')==native.record()['head'] and bound.get('type3_native_origin')==binding['type3_native_origin'] and bound.get('image_size')==binding['image_size'] and bound.get('type3_generic_image_sha256')==binding['image_sha256'] and witness==dict(schema='type3-fixed-patch-v1',generic_image_sha256=binding['image_sha256'],bound_image_sha256=bound['image_sha256'],template_report_sha256=old['template_files']['build-result.json'],cycle=bound.get('auto_cycle_token')) and re.fullmatch('[0-9a-f]{32}',bound.get('auto_cycle_token') or ''),'exact saved123 validated materialization metadata required')
    oldctx['variant']=bound
    proto=private(c['boot_path']);require(proto==private(old['output'])/'plan/cycle-01/boot.img' and _pin(c['boot_metadata'])==proto.with_suffix('.json'),'exact saved123 BOOT metadata path required')
    metadata=read(proto.with_suffix('.json'));info=proto.stat();require(proto.is_file() and not proto.is_symlink() and proto.resolve()==proto and c['boot_stat']==dict(device=info.st_dev,inode=info.st_ino,size=info.st_size,mtime_ns=info.st_mtime_ns,ctime_ns=info.st_ctime_ns) and info.st_size==metadata.get('size'),'saved BOOT stat identity differs')
    require(set(metadata)==BOOT_KEYS and metadata.get('prototype_created') is True and metadata.get('kind')=='temporary Linux diagnostic boot; not XNU/iOS' and metadata.get('file')==str(proto) and metadata.get(prior.FIELD)==prior.marker(oldctx) and metadata.get('kernel_build_sha256')==bound.get('image_sha256') and metadata.get('kernel_readonly3_image_bytes')==bound.get('image_size') and profile.fields(metadata)==profile.fields(bound),'exact generated123 BOOT role/projection differs')
    output=private(c['output']);require(all(not output.is_relative_to(private(p)) and not private(p).is_relative_to(output) for p in (old['output'],original['output'],original['backup'],original['current_packages'])),'fresh124 output disjointness required')
    return dict(contract=c,path=str(path),sha256=expected,old=oldctx,variant_root=variant,bound=bound,boot=proto,boot_metadata=metadata,host=host,output=output,role_digests={},construct=False,pair=None)

def marker(ctx):return dict(schema=FIELD_SCHEMA,contract_path=ctx['path'],contract_sha256=ctx['sha256'],variant_BOOT_producer=dict(host_profile_source_head=HEAD,host_profile_source_sha256=dict(PINS)),operation_host=copy.deepcopy(ctx['host']))
def _context(row=None):
    ctx=_SCOPE.get()
    if ctx is not None:return ctx
    require(type(row) is dict and selected(row),'closed124 package/read scope required');f=row[FIELD];ctx=load(f['contract_path'],f['contract_sha256']);j=read(ctx['output']/'transaction.json')
    require(j.get('schema')=='saved123-package-tail-journal-v1' and j.get('status')==j.get('phase')=='complete' and j.get('contract_sha256')==ctx['sha256'] and j.get('caps')==CAPS and j.get('attempts')==dict(pairs=1,plans=1) and j.get('completed')==dict(pairs=1,plans=1),'completed124 package/plan authority required')
    pairpath=private(j['package_result']['path']);require(pairpath==ctx['output']/'packages/package-result.json' and sha(pairpath)==j['package_result']['sha256'],'completed124 package metadata changed');ctx['pair']=read(pairpath)
    ctx['role_digests']={p['mode']:(p['payload_sha256'],p['payload_size']) for p in ctx['pair']['packages']};return ctx

def handles(row):
    ctx=_SCOPE.get()
    return selected(row) or ctx is not None and row.get('file')==str(ctx['boot'])
def _profile_fields(ctx):return __import__('sha256_kat_device_profile').fields(ctx['boot_metadata'])

def candidate(row,patched=None):
    import native_scoped_output_admission as shared
    ctx=_context(row);shared.no_pc(row)
    if not selected(row):
        require(_SCOPE.get() is not None and row==ctx['boot_metadata'] and set(row)==BOOT_KEYS,'exact generated BOOT role required')
    else:
        require(row[FIELD]==marker(ctx),'closed124 package operation marker differs')
        base={k:v for k,v in row.items() if k!=FIELD}
        if base==ctx['bound']:pass # immutable variant plus in-memory execution marker
        elif 'packages' in row:
            require(set(row)==PAIR_KEYS|set(_profile_fields(ctx))|{FIELD} and row.get('prototype_sha256')==ctx['boot_metadata']['sha256'] and row.get('kernel_image_sha256')==ctx['bound']['image_sha256'] and row.get('expected_current_boot_sha256')==ctx['old']['original']['current_boot_sha256'] and len(row['packages'])==2,'exact124 paired-package metadata role differs')
        else:
            role=row.get('mode');extra={'file','sha256'} if 'file' in row or 'sha256' in row else set()
            require(role in ('diagnostic','rollback') and set(row)==MANIFEST_KEYS|set(_profile_fields(ctx))|{FIELD}|extra and role in ctx['role_digests'] and (row.get('payload_sha256'),row.get('payload_size'))==ctx['role_digests'][role] and row.get('writes')==['boot'] and row.get('auto_return_diagnostic') is (role=='diagnostic') and row.get('auto_cycle_token')==(ctx['bound']['auto_cycle_token'] if role=='diagnostic' else None),'exact124 diagnostic/rollback package role differs')
        require(all(row.get(k)==v for k,v in _profile_fields(ctx).items()),'saved123 BOOT package projection/source differs')
    require(patched is None or row.get('image_expectation_patched') is patched,'saved123 package patch state differs')
    return dict(ctx['old']['original'],execution_version='v124',host_source_head=ctx['host']['host_profile_source_head'],output=str(ctx['output']))

@contextmanager
def read_scope(ctx):
    t=_SCOPE.set(ctx);old=prior._READ.set(ctx['old'])
    try:yield
    finally:prior._READ.reset(old);_SCOPE.reset(t)

def builder_entry(backup,prototype,output,current_packages):
    metadata=read(Path(prototype).with_suffix('.json'))
    if prior.FIELD not in metadata:return
    ctx=_SCOPE.get();require(ctx is not None and ctx['construct'],'saved123 BOOT packaging requires fresh124 construction scope')
    require(private(prototype)==ctx['boot'] and sha(Path(prototype).with_suffix('.json'))==ctx['contract']['boot_metadata']['sha256'] and private(backup)==private(ctx['old']['original']['backup']) and private(current_packages)==private(ctx['old']['original']['current_packages']) and private(output)==ctx['output']/'packages' and not Path(output).exists(),'exact124 saved BOOT/package inputs required')
    candidate(metadata,True);j=read(ctx['output']/'transaction.json');require(j['attempts']['pairs']==0 and j['completed']['pairs']==0,'one new124 package pair only')
    j['attempts']['pairs']=1;save(ctx['output']/'transaction.json',j)

def package_fields(metadata,fields):
    ctx=_SCOPE.get()
    return dict(copy.deepcopy(fields),**{FIELD:marker(ctx)}) if ctx is not None and metadata==ctx['boot_metadata'] else fields

def note_payload(mode,digest,size):
    ctx=_SCOPE.get()
    if ctx is None:return
    require(ctx['construct'] and mode in ('diagnostic','rollback') and mode not in ctx['role_digests'],'one observed124 writer digest per role required')
    ctx['role_digests'][mode]=(digest,size)

def record_pair(ctx,pair):
    require(_SCOPE.get() is ctx and ctx['construct'] and private(ctx['output']/'packages/package-result.json').is_file(),'actual124 paired result required')
    candidate(pair,True);require({p['mode'] for p in pair['packages']}=={'diagnostic','rollback'},'one diagnostic/rollback pair required')
    for p in pair['packages']:candidate(p,True)
    ctx['pair']=copy.deepcopy(pair);j=read(ctx['output']/'transaction.json');j['completed']['pairs']=1;j['package_result']=dict(path=str(ctx['output']/'packages/package-result.json'),sha256=sha(ctx['output']/'packages/package-result.json'));save(ctx['output']/'transaction.json',j)

def require_finish(ctx):
    j=read(ctx['output']/'transaction.json');require(ctx['construct'] and j['completed']['pairs']==1 and ctx['pair'] is not None and sha(j['package_result']['path'])==j['package_result']['sha256'] and j['attempts']['plans']==0,'new124 plan only after completed pair')
    j['attempts']['plans']=1;j['phase']='plan_reserved';save(ctx['output']/'transaction.json',j)

def plan_binding(plan,report):
    ctx=_context(plan);require(plan[FIELD]==marker(ctx) and plan.get('execution_version')=='v124' and plan.get('executing_host_source_head')==ctx['host']['host_profile_source_head'] and report.get('execution_version')=='v123' and report.get('host_profile_source_head')==HEAD and plan.get(prior.FIELD)==prior.marker(ctx['old']) and plan.get('type3_contract_sha256')==ctx['old']['binding']['type3_contract_sha256'],'separate124 executor/123 BOOT/122 template plan lineage differs')

@contextmanager
def plan_scope(plan,path,expected):
    ctx=_context(plan);require(private(path)==ctx['output']/'plan.json' and sha(path)==expected,'exact124 plan pin required')
    from native_prefree_output_admission import predecessor_scope
    with read_scope(ctx),predecessor_scope(ctx['old']['original']):yield

def variant_root(row):return _context(row)['variant_root']
def execution_host(row):return _context(row)['host']['host_profile_source_head']

@contextmanager
def device_scope(row,ack,context):
    from native_scoped_output_admission import require_device_scope
    require_device_scope(row,ack,context);ctx=_context(row)
    with read_scope(ctx):yield

def _start(path,expected):
    ctx=load(path,expected);require(not ctx['output'].exists(),'fresh124 output required; no retry');ctx['output'].mkdir(parents=True);ctx['construct']=True
    save(ctx['output']/'transaction.json',dict(schema='saved123-package-tail-journal-v1',status='started',phase='packages_reserved',contract_sha256=expected,attempts=dict(pairs=0,plans=0),completed=dict(pairs=0,plans=0),caps=CAPS,device_operations=[]));return ctx

def prepare(path,expected):
    import sha256_kat_device_profile as profile
    from build_boot_test_packages import build
    from stage_phase2 import verify_packages
    from native_prefree_output_admission import predecessor_scope
    ctx=_start(path,expected)
    try:
        with read_scope(ctx):
            old=ctx['old']['original'];backup=private(old['backup']);current=private(old['current_packages'])
            pair=build(backup,ctx['boot'],ctx['output']/'packages',current);record_pair(ctx,pair);require_finish(ctx)
            prior_boot=next(x for x in verify_packages(current) if x['mode']=='diagnostic')
            template=prior.saved_template(ctx['old']['template'])
            with predecessor_scope(old):result=profile.finish_plan(ctx['old']['template'],backup,Path(old['reference_twrp']),Path(old['mkbootimg']),current,ctx['output'],template,ctx['variant_root'],ctx['bound'],ctx['bound']['auto_cycle_token'],ctx['output']/'packages',prior_boot,extra=dict(execution_version='v124',executing_host_source_head=ctx['host']['host_profile_source_head'],**{FIELD:marker(ctx)}))
            require(read(result['plan']).get(FIELD)==marker(ctx),'new124 plan marker missing');j=read(ctx['output']/'transaction.json');j['completed']['plans']=1;j.update(status='complete',phase='complete',result=result);save(ctx['output']/'transaction.json',j);return result
    except BaseException as e:
        j=read(ctx['output']/'transaction.json');j.update(status='failed_no_restart',error_type=type(e).__name__);save(ctx['output']/'transaction.json',j);raise

def main():
    p=argparse.ArgumentParser();p.add_argument('--contract',required=True,type=Path);p.add_argument('--contract-sha256',required=True);a=p.parse_args();print(json.dumps(prepare(a.contract,a.contract_sha256),indent=2))
if __name__=='__main__':
    import type3_remaining_packages as canonical
    canonical.main()
