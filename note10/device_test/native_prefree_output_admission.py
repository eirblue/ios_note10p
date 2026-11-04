"""Exact native121 origin and bounded prefree companion; no PC format promotion."""
from contextlib import contextmanager
from contextvars import ContextVar
from types import MappingProxyType
from collections.abc import Mapping
import re
import native_prefree_output_zero as native
import linux_data_carrier as data
def _freeze(value):
    if isinstance(value,Mapping):return MappingProxyType({k:_freeze(v) for k,v in value.items()})
    if isinstance(value,(list,tuple)):return tuple(_freeze(v) for v in value)
    return value

def _record_copy(value):
    if isinstance(value,Mapping):return {k:_record_copy(v) for k,v in value.items()}
    if isinstance(value,tuple):return tuple(_record_copy(v) for v in value)
    return value

_NATIVE121=_freeze({'artifact_id': 13302224230,
 'attempt': 1,
 'fixture_result_sha256': 'ef759132a61daf006905c45519e3f6075f2878dccef906e9e7e7b24e1dc7a6e6',
 'head': 'd1dd52d08e06d13ac553c0420960560f6fd4944f',
 'image_bytes': 50870284,
 'image_sha256': '052c987498e07bc5f4c72fdd6de6d34497297ba8be1d8b35d20c3e6bdead2393',
 'job_id': 126431889321,
 'linked_bytes': 59588608,
 'outcome_bytes': 128,
 'pins': {'.github/workflows/note10-builtin-init-route.yml': 'c135fb22c04e0fa085b3092c23af369f10070d6560e6ccaf0c005c71a1b134b6',
          '.github/workflows/note10-linux-data-carrier.yml': '0337aac1ac7134d42a423f645dacb817f7ed350f6e535475404aeffc4d80dd2b',
          'note10/device_test/auto_cycle.py': '64cd356b88e828a516edf049f93e40ee283e1cd8bec2e575fe77baadc4aafa20',
          'note10/device_test/auto_return.c': '9ec43d3d17f12fe90d2ab36e4712537b7f8275f6f27b6536bbef826f9692037d',
          'note10/device_test/build_boot_test_packages.py': '17b973f54185521be6685acb5e019f8bf8b5f10897d01c0167929c97859cddef',
          'note10/device_test/build_builtin_init_image.py': '297a599f79c5d70ec5404836fd0962be3b338837371a94fe9aa2ee48a64082aa',
          'note10/device_test/build_kernel_readonly_span_candidate.py': '7ebcce1d50932d59d431f4be417c3637d18570b19b7b735f9543af2f9e1b2b75',
          'note10/device_test/build_linux_data_carrier.py': '44f083e2168716b33cea4111ab303c83f5fda5136dd99f54f32c2521a2f25d98',
          'note10/device_test/build_sha256_kat_recovery.py': '2f84ba60d3b0a582d015c2d6c1955aae8a8a4e785b575da5d2af6ebf293ab123',
          'note10/device_test/build_sha256_runtime_kat.py': 'd76c33333a67d6af4bc7c0d8caf0b0868f8e5d63e1c585f6def2860dfe4bbdff',
          'note10/device_test/build_xnu_runtime_plan_component.py': '367f9147d50950dffb47bf83861787dce4a1be47225b11b070e2f60de45c6b6e',
          'note10/device_test/builtin_init_profile.py': 'bf9c4c21bbf7fb8b8086a9e8bfe1463aea1286879b566ec3d625a3dd695d6a9d',
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
          'note10/device_test/kernel_readonly_input.py': '63377517fce79b95498af936ef0877c83889d4ef6ce31facb6013d2a2f5181b7',
          'note10/device_test/kernel_readonly_span.h': 'dd0640b8322fb86c8baa29863a931ddb7d005dd589352ba4136c09bdb79de86d',
          'note10/device_test/kernel_readonly_span_candidate.h': '8f8e8522a7b03413b3db59f21fca5cefa4b74fb9e63a412dfc9d6067beb5dec1',
          'note10/device_test/kernel_readonly_span_candidate.py': 'b77c2d328b4a97b09c7085ebc50e66b42186c6c882f9b977a6a33f3fd0358eb3',
          'note10/device_test/kernel_readonly_span_candidate_fixture.c': 'b4d02ff71b82365915fca0c112170de9c44184dcce481656832e69e77dee9f29',
          'note10/device_test/linux_data_carrier.c': 'a9fd626d384ac6b3fd3d8d705debdc3a1daa34ac1886a51ef8788f57e408c53d',
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
          'note10/device_test/native_prefree_output_zero.h': 'c51428279ba02d44169993417874251b6a6c888e1c8874eabcb6cdfacafb1516',
          'note10/device_test/native_prefree_output_zero.py': 'cb580469be605f952bfa0e2b4a884bf9877edb70ebe48e25cf5f3fd5dc2c25f5',
          'note10/device_test/native_prefree_output_zero_fixture.c': '6e7089a2a68b419b2f5712c0dd99197d14bd7f22f7a260ddf4fe39a66710cfd6',
          'note10/device_test/native_scoped_output.h': 'dd52afd255b685b7f8c0b769ca826defbff343e13d4020826ca7d6fcec0d907c',
          'note10/device_test/native_scoped_output.py': '28567462f0bcb45ba4ed94eb3736bf8ba28c22058262acee0b3f2ffc20496146',
          'note10/device_test/native_scoped_output_fixture.c': '0288c96ca301560ecf82cf14aee6fdd378e207278857969fd17e1ab84dacc880',
          'note10/device_test/pre_pm_archive_contract.py': '966a5b032e516ecc984defc9b0313192667d4f4585511fa232966ce79ac3b5c5',
          'note10/device_test/prepare_linux_boot.py': '0499a630875cb4319e4bdfb33c02d0bac3e31538b24997bac794357b95a5298f',
          'note10/device_test/prepare_sha256_kat_recovery.py': '921dd3cade033e21e50994c1b8036d8067bb77c8f9372454c9290673aa7d4b91',
          'note10/device_test/prepare_sha256_runtime_kat.py': '5f56dfb7d77acc2b998122022b65421a5e34f73d52be446a677ff333b5d5e5c2',
          'note10/device_test/prepare_xnu_runtime_plan.py': '6b9b21ab93f3b49ef43e947a26ad1985d2f11bbd94002e30fcf6dcca875ac41c',
          'note10/device_test/readonly_stage_witness.h': '85851db4c9622842f4ccc547e7532139f306917d8674c0298529e5041fb08330',
          'note10/device_test/readonly_stage_witness.py': 'eb50f90eb18b22e431b8a36890e700b4eddc0cbb36d1a49f686745fb18134495',
          'note10/device_test/readonly_stage_witness_fixture.c': '2513117dd52b2c8ef92a6f0c161af3a2e1fe6060e24dc9b166d187c5a3fd0cec',
          'note10/device_test/retained_v108_origin.py': '737e3de25884daee64e8dc4d938b81e5b2f328a5923a4b6cea0b2c92b0db24f7',
          'note10/device_test/sealed_affinity_artifact.cjs': '08c17edb82357d5719fbccd2427fca1970c09f6b3ee7aef91d6034f7d12f70ec',
          'note10/device_test/sha256_builtin_init.c': '11408b9dba36f56137f5d411d9a77eaf72db71cadfec9b406f85fcfc3d3cd6e4',
          'note10/device_test/sha256_kat_device_profile.py': 'f1ee77c1619ee11e07a8521ddd302dda11eb00f92a95fecea6a78d8ca1ebf307',
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
          'note10/device_test/test_v121_native_prefree_output_zero.py': 'c71c4754ebd279bd8285f2ae548ea0a3b98c35f97f4d1ca448e2b8c7bfbd9281',
          'note10/device_test/type3_admission.py': 'f86388877ee19effa14eaec47a10d39f049c9159daeb3bf003020aac75139052'},
 'plaintext_zip_sha256': 'd433243d1d8b136647acabcd16b6282ce41d2ef86ed0328def0f6909592bbda0',
 'producer_ci_context': {'GITHUB_JOB': 'linux-data-carrier',
                         'GITHUB_REPOSITORY': 'eirblue/ios_note10p',
                         'GITHUB_RUN_ATTEMPT': '1',
                         'GITHUB_RUN_ID': '41787180784',
                         'GITHUB_SHA': 'd1dd52d08e06d13ac553c0420960560f6fd4944f',
                         'GITHUB_WORKFLOW_REF': 'eirblue/ios_note10p/.github/workflows/note10-linux-data-carrier.yml@refs/heads/main',
                         'GITHUB_WORKFLOW_SHA': 'd1dd52d08e06d13ac553c0420960560f6fd4944f'},
 'result': '1a3a30c5c563dcb4ecc616f6a97b8faa25e427244bb1854c7f53ad4dfea2a391',
 'run_id': 41787180784,
 'source_manifest_sha256': '18941ae986b6368750541af7e506e33ecca6194c9c60a8b3867598b7f4908524',
 'state_bytes': 88,
 'test_result_sha256': '7c35bca2d839c46afc5fa2258da6812dd452c568945049202b286fb765ee9a38',
 'workflow_id': 404040749})
FIXTURE_EVIDENCE={'allocation_attempts': 10,
 'allocation_successes': 9,
 'cases': 5,
 'emit_frames': 20,
 'free_calls': 9,
 'independent_free_boundary_reads': 128,
 'nonzero_bytes_negative_case': 2,
 'partial_allocated_capacity': 32,
 'partial_decode_written': 7,
 'result_sha256': 'ef759132a61daf006905c45519e3f6075f2878dccef906e9e7e7b24e1dc7a6e6',
 'scan_reads': 128,
 'schema': 'n10-native-prefree-output-zero-fixture-v1',
 'source_head': 'd1dd52d08e06d13ac553c0420960560f6fd4944f'}
FIELDS=('prefree_output_schema','prefree_output_marker','prefree_output_handle_bytes','prefree_output_capacity_source','prefree_output_scan_phase','prefree_output_retained_after_emit')
_CURRENT_READ=ContextVar('native121_current111_read',default=None)

def record():
    data.require(len(_NATIVE121['pins'])==74 and _NATIVE121['linked_bytes']<=59768832 and
        all(re.fullmatch('[0-9a-f]{64}',v) for v in _NATIVE121['pins'].values()),'exact accepted native121 origin74 required')
    return dict(_record_copy(_NATIVE121),kind=native.KIND,version='v121',host_version='v122',witness_schema='n10-readonly-stage-witness-candidate-v1')

def selected(row):return native.selected(row)
def is_head(head):return head==_NATIVE121['head']
def context_schema(head):return 'type3-prefree-output-execution-v1' if is_head(head) else 'type3-scoped-output-execution-v1'
def device_schema(head):return 'note10-type3-prefree-output-device-v1' if is_head(head) else 'note10-type3-scoped-output-device-v1'
def fields():
    return dict(zip(FIELDS,(native.SCHEMA,'N10OUTPUTZERO1',24,'actual-output-allocation','after-clear-before-free',False)))

def decode_joined(text,identity,cycle,legacy,stages,lease):
    from decode_reservation import checksum
    require=data.require
    lines=[line for line in text.splitlines() if 'N10OUTPUTZERO' in line]
    require(len(lines)==1,'one native121 prefree companion required')
    m=re.search(r'N10BOOTLINK2 boot=([0-9a-f]{32}) N10OUTPUTZERO1 ([^\r\n\x00]{1,447}) checksum=([0-9a-f]{8})$',lines[0])
    require(m is not None and m[1]==legacy['boot_identity']==lease['boot_identity'] and m[1]!='0'*32 and
        checksum(m[2].encode('ascii'))==int(m[3],16),'prefree boot/checksum differs')
    prefix=f'id={identity} cycle={cycle} kind=prefree_zero schema={native.WIRE_SCHEMA} '
    require(m[2].startswith(prefix),'prefree id/cycle/schema differs')
    f=re.fullmatch(r'capacity=(0|[1-9][0-9]*) reads=(0|[1-9][0-9]*) nonzero=(0|[1-9][0-9]*) scan_called=([01]) scan_returned=([01]) observed_zero=([01]) free_called=([01]) free_returned=([01]) free_result=(not_called|void_returned) ownership=0 hardware=0 executed=0',m[2][len(prefix):])
    require(f is not None,'closed native121 prefree frame required')
    capacity,reads,nonzero,called,returned,zero,freed,free_returned=map(int,f.groups()[:8])
    require(0<=nonzero<=reads<=capacity<=64*1024*1024 and returned<=called and free_returned<=freed,'prefree bounded counts/sequence differ')
    require(called or reads==nonzero==zero==0,'uncalled prefree scan has observations')
    require(not returned or capacity>0 and reads==capacity,'returned prefree scan must cover actual allocation')
    require(zero==int(bool(returned and reads==capacity and capacity and not nonzero)),'prefree zero/count contradiction')
    events=stages['events'];scope=lease['events']
    require(not called or events['output_clear_returned'],'prefree scan precedes existing clear')
    require(bool(freed)==events['output_free_called']==scope['free_called'] and
        bool(free_returned)==events['output_free_returned']==scope['free_returned'] and
        f[9]==('void_returned' if free_returned else 'not_called'),'prefree free call/return text contradicts witnesses')
    require(not capacity or capacity==legacy['payload'],'prefree capacity differs from actual requested allocation')
    passed=bool(legacy['passed'] and stages['passed'] and lease['passed'] and capacity and reads==capacity and zero and freed and free_returned)
    require(legacy['status']!='ok' or passed,'native121 success requires complete prefree observation')
    return dict(schema=native.WIRE_SCHEMA,boot_identity=m[1],capacity=capacity,reads=reads,nonzero=nonzero,
        scan_called=bool(called),scan_returned=bool(returned),observed_zero=bool(zero),free_called=bool(freed),
        free_returned=bool(free_returned),free_result=f[9],passed=passed,capacity_source='actual-output-allocation',
        observation_phase='before-free',after_free_observation=False,secure_erasure_attested=False,
        free_reclamation_attested=False,global_RAM_ownership=False,hardware=False,xnu_executed=False)

@contextmanager
def predecessor_scope(contract):
    import native_scoped_output_admission as shared
    import type3_admission as typed
    _,context=shared._predecessor_context(contract)
    token=_CURRENT_READ.set(context)
    try:yield
    finally:_CURRENT_READ.reset(token)

def current_boot_binding(plan,pair,diagnostic):
    from type3_remaining_pack import HEAD,PINS,PACKAGING_HEAD,PACKAGING_PINS,FIELD
    from native_scoped_output_admission import _baseline_context
    context=_CURRENT_READ.get();data.require(context is not None,'native122 current111 typed read scope required')
    _baseline_context(context)
    data.require(pair.get('source_head')=='f20987a42249e61ef028c52099931f740d9a6cc5' and
        pair.get('host_profile_source_head')==HEAD and pair.get('host_profile_source_sha256')==dict(PINS) and
        pair.get(FIELD,{}).get('packaging_host')==dict(host_profile_source_head=PACKAGING_HEAD,host_profile_source_sha256=dict(PACKAGING_PINS)) and
        pair.get('backup_manifest_sha256')==context['backup_manifest_sha256'] and
        diagnostic in pair.get('packages',[]) and diagnostic.get('mode')=='diagnostic' and
        diagnostic.get('payload_sha256')==context['boot_sha256']==plan.get('current_boot_payload_sha256') and
        plan.get('current_packages')==context['packages'] and plan.get('current_package_result_sha256')==context['package_result_sha256'] and
        pair.get('device_profile')==plan.get('device_profile')=='linux-data-carrier-v1','exact native122/current111 producing/packaging/terminal chain differs')

# Scope admits immutable generic Image metadata/normal intrinsic template reads,
# never transport or arbitrary caller source-map authority.
_COMPOSE=ContextVar('native121_closed_composition',default=None)

def composition_template(function):
    from functools import wraps
    @wraps(function)
    def checked(contract,path,expected):
        import type3_admission as typed
        if not is_head(contract.get('native_source_head')):return function(contract,path,expected)
        approved=typed.load_offline(path,expected)
        data.require({k:v for k,v in contract.items() if k!='_contract_sha256'}==approved,'exact closed122 template contract required')
        token=_COMPOSE.set(approved)
        try:return function(contract,path,expected)
        finally:_COMPOSE.reset(token)
    return checked

def composition_reader(function):
    from functools import wraps
    @wraps(function)
    def checked(root,*args,**kwargs):
        import type3_admission as typed
        root=typed.private(root)
        meta=root/'device-profile.json' if (root/'device-profile.json').is_file() else root/'build-result.json'
        row=typed.read(meta)
        if not selected(row):return function(root,*args,**kwargs)
        contract=typed.load_offline(row.get('type3_contract_path',''),row.get('type3_contract_sha256'))
        data.require(row.get('native_source_head')==record()['head'] and row.get('execution_version')=='v122' and
            row.get('host_profile_source_head')==contract['host_source_head'] and
            root in (typed.private(contract['output'])/'template',typed.private(contract['output'])/'plan/cycle-01/kernel-build'),
            'exact new122 template/variant composition metadata required')
        token=_COMPOSE.set(contract)
        try:return function(root,*args,**kwargs)
        finally:_COMPOSE.reset(token)
    return checked

def require_composition():
    data.require(_COMPOSE.get() is not None,'native121 generic read requires exact closed122 offline composition proof')

def plan_reader(function):
    from functools import wraps
    @wraps(function)
    def checked(path,expected):
        import type3_admission as typed
        plan=typed.read(typed.private(path));row=typed.read(typed.private(plan['kernel_build'])/'build-result.json')
        if not selected(row):return function(path,expected)
        data.require(data.sha(data.bounded_private_read(typed.private(path),4*1024*1024))==expected,'exact122 plan SHA before predecessor read scope')
        contract=typed.load_offline(row['type3_contract_path'],row['type3_contract_sha256'])
        data.require(typed.private(path)==typed.private(contract['output'])/'plan/plan.json' and
            plan.get('execution_version')=='v122' and plan.get('executing_host_source_head')==contract['host_source_head'],
            'exact122 plan/live producing lineage required')
        with predecessor_scope(contract):return function(path,expected)
    return checked
