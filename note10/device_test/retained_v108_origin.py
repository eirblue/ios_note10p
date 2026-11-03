"""Exact consumed v108 producing host origin, exclusively for retained reads."""
from contextlib import contextmanager
from contextvars import ContextVar
from functools import wraps
from types import MappingProxyType

HEAD='2a8e5541f8bf3b3ff7fe6a5819930f8cace9b11c'
STOPPED_HEAD='1af6cb1a66f3a20a9754b74427a7c645e0fe2b1a'
NATIVE='c41749e5a4b5179e46dbca6f66d0f473b7bc9529'
_READ=ContextVar('retained_v108_read',default=False)
PINS=MappingProxyType({
    "note10/device_test/affinity_binding.py": "6d5b16d54a803c95bdd391a38efbd2bac5ef36baffe199f86cd83f878bf10678",
    "note10/device_test/auto_cycle.py": "113c067e8b692b9c08108c08cc08c8b9da6c2c87b3672aca097b4b6f9f910e0d",
    "note10/device_test/build_boot_test_packages.py": "17b973f54185521be6685acb5e019f8bf8b5f10897d01c0167929c97859cddef",
    "note10/device_test/build_kernel_readonly_input.py": "5391edfa477324dbdd5f4d9c6fb13deb5df8a66b2ed4df7d018213012b227000",
    "note10/device_test/build_kernel_readonly_span_candidate.py": "15db73e53be3c919e23dcff5368b0766d931607dec305a46950751c72976b282",
    "note10/device_test/build_kernel_readonly_span_pc.py": "cd42e0dec6570bcc09c7a07695560eae13a62420d744e16035c4da3a57c588e9",
    "note10/device_test/build_readonly_input_pc.py": "893698f6741fd178334777b4f96c98934d78b5a927fe4cf3d383d92e90557d9e",
    "note10/device_test/builtin_init_profile.py": "81ee864aeecfec92f87c5704533b0b15423d21ea604565a1b121a4d338898248",
    "note10/device_test/builtin_init_route.py": "46b100dc95f11e344c11b8cb3fba5d34d17b2884385923426a42246699fda43d",
    "note10/device_test/carrier_lzma.c": "e204732754f15929f7134885ec2740e1ed26f0291dd64c7df7957a4aee7b987a",
    "note10/device_test/carrier_lzma.h": "6790aa17da94025e0bab175377573edb8df3f503c8cde86f8c919e33ee742974",
    "note10/device_test/current_data_reuse.py": "15c7a5a55e22f4445c216904769d7ba9b6367f792122e5b936305c95ae031129",
    "note10/device_test/early_fdt_binding.py": "d4f7099fb45eca31c83c9acd9fbfe0cd5c7ccc5c271c18180e3672e22f9a6b78",
    "note10/device_test/kernel_readonly_input.h": "4aa99ff2ab756b854174eb2519af96e79669f82114293790a538ddd3025298ea",
    "note10/device_test/kernel_readonly_input.py": "57922b4e8431762effa4a40adeed8a2e90950a0573361a966c6f6b64b5a71dc0",
    "note10/device_test/kernel_readonly_input_fixture.c": "6300f13ba284b4f42614a4c6cda8f09c6e6671e88d6e524ec24dacd3a7ab70e0",
    "note10/device_test/kernel_readonly_span.h": "dd0640b8322fb86c8baa29863a931ddb7d005dd589352ba4136c09bdb79de86d",
    "note10/device_test/kernel_readonly_span_candidate.h": "8f8e8522a7b03413b3db59f21fca5cefa4b74fb9e63a412dfc9d6067beb5dec1",
    "note10/device_test/kernel_readonly_span_candidate.py": "b0f93d5e5282410762887a13b90e1db719744b8a53eb8a6d8d1ff2f9db2794ab",
    "note10/device_test/kernel_readonly_span_candidate_fixture.c": "b4d02ff71b82365915fca0c112170de9c44184dcce481656832e69e77dee9f29",
    "note10/device_test/kernel_readonly_span_fixture.c": "afbc9ae410e15bf7221e10a4cbcb325702a3a0235dec0fe585b836e7dae467c6",
    "note10/device_test/linux_data_carrier.c": "214523104e091eb4be28d67d5adb06b59864bfa5b589bde2ce92be56fba9aa80",
    "note10/device_test/linux_data_carrier.py": "40a1713839994bf8c0a3fc6c81822775ea36476cfb56a1da300bf59aced8dc52",
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
    "note10/device_test/materialize_auto_cycle.py": "8bcbb1c8cb95a251653ee5df05a7f79fb0900d32c0e09a97a79ce7e5ed6866bd",
    "note10/device_test/native_memory_observation.py": "f4acd0f310989bfcd1b0c2039fef6e429e8ec4d4f41ebdb94fc483538fa26663",
    "note10/device_test/precheck_window_access.py": "3ef3859ef2a4c154e93e5db7846bde78eb9061742243dba435187a9087226e28",
    "note10/device_test/prepare_linux_boot.py": "ae0f41cb5284110680e232a4a830415022a7cb6a1f10312be2dfb3bea0194772",
    "note10/device_test/readonly_input_pc.h": "01b18e5fddcd12fba45190baa337b47c3309f54cc7a448cd6d72209c5ba8a3f0",
    "note10/device_test/readonly_input_pc.py": "d7125058dc85a57eb4283fccf87bcb6af96c26de1363f81d1acb0999b94f1fc7",
    "note10/device_test/readonly_input_pc_fixture.c": "99f0e7eb9240b5c08314993a14dfcd9a532df0e24158679cdbed8b0c3c752730",
    "note10/device_test/sha256_kat_device_profile.py": "ce05b04f0b0bb4cf5596bc128706b0da2919929ab16388d32097422317bf8bf3",
    "note10/device_test/sha256_stream_state.py": "55de2735fb830ae8047bb4a8fa74325f51b766b1e885c482dbbc5ebabe3ea437",
    "note10/device_test/sha256_stream_vectors.json": "5c379d1ef41a40b9a1262c985476e9dc0ba88dae7b1586f949bbe79686f2165f",
    "note10/device_test/stage_phase2.py": "3f8361ea504433c97e60e14d95684d922a90dda3d3cea571697814244b466927",
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
    "note10/device_test/test_v99_carrier_compare_evidence.py": "2b45c21197709706d3f3ffc23e1428084d5d50a93a1d9b5bd22c2693124cf20c",
    "note10/device_test/test_v99_host_profile_origin.py": "fb4a1c349ca298b4f18ba64e0692c7a93e9f0877b2f7a7ec22fa2c8f29ac219a",
    "note10/device_test/type3_admission.py": "786d9b07eb3ded94b0ca595a755fd04e76284ccd8be9a647be574c53038c9d1a"
} )

@contextmanager
def read_scope():
    token=_READ.set(True)
    try:yield
    finally:_READ.reset(token)

def reading():return _READ.get() is True

def reader(function):
    @wraps(function)
    def checked(*args,**kwargs):
        with read_scope():return function(*args,**kwargs)
    return checked

def selected(row):return row.get('host_profile_source_head')==HEAD

def origin(row):
    from linux_data_carrier import require
    require(reading(),'retained v108 origin is read-only')
    require(selected(row) and row.get('device_profile')=='linux-data-carrier-v1' and row.get('source_head')==row.get('native_source_head')==NATIVE and
        row.get('version')==row.get('execution_version')=='v108' and row.get('native_producer_version')=='v107' and
        row.get('diagnostic_kind')==row.get('data_input_kind')==row.get('storage_input_kind')=='kernel-readonly-span-candidate' and
        row.get('host_profile_source_sha256')==dict(PINS),'exact typed retained v108 host70 origin required')
    return dict(host_profile_source_head=HEAD,host_profile_source_sha256=dict(PINS))

def live(head):
    from linux_data_carrier import require
    require(head not in (HEAD,STOPPED_HEAD),'consumed/stopped v108 cannot construct or stage')
