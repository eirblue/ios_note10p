"""Closed saved122-template tail and first remaining materialization; no prefix replay."""
import argparse
import copy
from contextlib import contextmanager
from contextvars import ContextVar
from functools import wraps
import json
from pathlib import Path
import re
import shutil
import linux_data_carrier as data
import native_prefree_output_admission as native
HEAD='162e8cb28cb2eaf49f2515f58720d082dd07af55'
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
 'note10/device_test/materialize_auto_cycle.py': '4b0b67be104a25c740f93a2ff3b4d57a859cf34006d0e43852a2e4cf6a4345de',
 'note10/device_test/native_memory_observation.py': 'f4acd0f310989bfcd1b0c2039fef6e429e8ec4d4f41ebdb94fc483538fa26663',
 'note10/device_test/native_prefree_output_admission.py': '49ca7389c90466f0a5170a261270a0651439a9bf6273d1b83f38f3f2ff8b774a',
 'note10/device_test/native_prefree_output_zero.py': 'cb580469be605f952bfa0e2b4a884bf9877edb70ebe48e25cf5f3fd5dc2c25f5',
 'note10/device_test/native_scoped_output.py': '28567462f0bcb45ba4ed94eb3736bf8ba28c22058262acee0b3f2ffc20496146',
 'note10/device_test/native_scoped_output_admission.py': 'b062cff7fedf1f252aaa9f2b89736c997602388ff9fdeb1921a0c3e7cd2f1073',
 'note10/device_test/precheck_window_access.py': '3ef3859ef2a4c154e93e5db7846bde78eb9061742243dba435187a9087226e28',
 'note10/device_test/prepare_linux_boot.py': '0499a630875cb4319e4bdfb33c02d0bac3e31538b24997bac794357b95a5298f',
 'note10/device_test/readonly_input_pc.h': '01b18e5fddcd12fba45190baa337b47c3309f54cc7a448cd6d72209c5ba8a3f0',
 'note10/device_test/readonly_input_pc.py': 'd7125058dc85a57eb4283fccf87bcb6af96c26de1363f81d1acb0999b94f1fc7',
 'note10/device_test/readonly_input_pc_fixture.c': '99f0e7eb9240b5c08314993a14dfcd9a532df0e24158679cdbed8b0c3c752730',
 'note10/device_test/readonly_stage_witness.h': '85851db4c9622842f4ccc547e7532139f306917d8674c0298529e5041fb08330',
 'note10/device_test/readonly_stage_witness.py': '2d8a4a6affa7e49459e92bd5b2b4ba3787177bf28786c13c3611d8b64f8653b8',
 'note10/device_test/readonly_stage_witness_fixture.c': '2513117dd52b2c8ef92a6f0c161af3a2e1fe6060e24dc9b166d187c5a3fd0cec',
 'note10/device_test/retained_v108_origin.py': '737e3de25884daee64e8dc4d938b81e5b2f328a5923a4b6cea0b2c92b0db24f7',
 'note10/device_test/sha256_kat_device_profile.py': '248d0d995257cc502ecf78abdb7199086da540c71d3167c3520b58aa23520b07',
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
 'note10/device_test/test_v99_carrier_compare_evidence.py': '2b45c21197709706d3f3ffc23e1428084d5d50a93a1d9b5bd22c2693124cf20c',
 'note10/device_test/test_v99_host_profile_origin.py': 'fb4a1c349ca298b4f18ba64e0692c7a93e9f0877b2f7a7ec22fa2c8f29ac219a',
 'note10/device_test/type3_admission.py': '538686fbdba11baa589d1c69d18b232c424a0273a5678aac1e45dcb918daf9a0',
 'note10/device_test/type3_remaining_pack.py': 'd39c393f9c421a59580df7f64a9cc3fe4fe333065d440e981316734030d97dce',
 'note10/device_test/type3_remaining_plan.py': '16a9fcbcba505d60731682bdd2704a8a0089dcf29c10bc352509b693f98e3ecc'})
SCHEMA='note10-native121-template-remaining-v123-v1'
FIELD='type3_remaining_template'
FIELD_SCHEMA='saved122-template-live123-v1'
DEVICE_SCHEMA='note10-type3-prefree-remaining-device-v123-v1'
CONTEXT_SCHEMA='type3-prefree-remaining-execution-v123-v1'
FILES=frozenset(('device-profile.json','build-result.json','image-root-receipt.json','ci-success-context.json','result.json','type3-contract.json','kernel-readonly-compact.json','handoff.config','actual-effective.config'))
BINARY_FILES=frozenset(('Image','kernel-readonly.data'))
KEYS=frozenset(('schema','status','execution_version','execution_host_source_head','execution_host_source_sha256','original_contract','failed_transaction','operator_failure','trace','template_root','template_files','output','caps'))
CAPS=dict(original_compact_attachments=0,compact_derivations=0,templates_created=0,standalone_Image_readers=0,generic_Image_copies=0,materializations=1,fixed_patch_transactions=1,new_variant_intrinsic_validations=1,generic_Image_intrinsic_reads=2,bound_Image_intrinsic_validation_reads=1,bound_Image_packer_reads=1,saved_template_compact_DATA_consumptions=3,saved_variant_compact_packer_consumptions=1,paired_BOOT_packs=1,plans=1,cycles=1,Image_builds=0,CI=0,decoder_or_MachO_replays=0,device_queries=0,BOOT_writes=0,reboots=0)
_ACTIVE=ContextVar('saved122_remaining_construct',default=None)
_READ=ContextVar('saved122_remaining_read',default=None)

def require(value,message):data.require(value,message)
def private(path):return __import__('type3_admission').private(path)
def read(path):return __import__('type3_admission').read(path)
def sha(path):
    path=private(path)
    require(path.name not in BINARY_FILES,'metadata-only loader cannot hash Image/DATA')
    return data.sha(data.bounded_private_read(path,4*1024*1024))
def selected(row):return FIELD in row

def _pin(item):
    require(type(item) is dict and set(item)=={'path','sha256'} and re.fullmatch('[0-9a-f]{64}',item['sha256'] or ''),'closed saved122 metadata pin required')
    p=private(item['path']);require(str(p)==item['path'] and sha(p)==item['sha256'],'saved122 metadata changed')
    return p

def load(path,expected):
    path=private(path);require(sha(path)==expected,'exact reviewed123 remaining contract SHA required')
    c=read(path)
    require(type(c) is dict and set(c)==KEYS and c['schema']==SCHEMA and c['status']=='reviewed_ready' and c['execution_version']=='v123' and c['caps']==CAPS and all(type(v) is int for v in c['caps'].values()),'closed123 remaining contract required')
    import sha256_kat_device_profile as profile
    host=profile.host_binding(c['execution_host_source_head'])
    require(host['host_profile_source_sha256']==c['execution_host_source_sha256'] and c['execution_host_source_head']!=HEAD,'distinct live123 source closure required')
    original=read(_pin(c['original_contract']));journal=read(_pin(c['failed_transaction']));failure=read(_pin(c['operator_failure']));trace=_pin(c['trace']).read_text(encoding='utf-8')
    import type3_admission as typed
    require(type(original) is dict and set(original)==typed.OFFLINE_KEYS and original.get('schema')==typed.OFFLINE_SCHEMA and original.get('status')=='reviewed_ready' and original.get('caps')==typed.OFFLINE_CAPS,'exact closed consumed122 offline contract required')
    require(original.get('host_source_head')==HEAD and original.get('execution_version')=='v122' and original.get('native_source_head')==native.record()['head'] and original.get('accepted_result_sha256')==native.record()['result'],'exact retained122/native121 origin required')
    require(journal.get('status')=='failed_no_restart' and journal.get('phase')=='template_reserved' and journal.get('contract_sha256')==c['original_contract']['sha256'] and journal.get('attempts')==dict(templates=1,materializations=0,plans=0) and [x.get('operation') for x in journal.get('IO_events',[])]==['attach_existing_compact_once','intrinsic_compact_copy_validation'],'exact completed122 prefix/zero remaining attempts required')
    require(failure.get('schema')=='v122-offline-operator-receipt-v1' and failure.get('native_source_head')==native.record()['head'] and failure.get('stderr_sha256')==c['trace']['sha256'] and private(failure.get('transaction_path',''))==private(c['failed_transaction']['path']) and private(failure.get('output',''))==private(original['output']) and failure.get('success') is False and failure.get('source_head')==HEAD and failure.get('invocation_attempts')==1 and failure.get('invocation_exit_code')==1 and failure.get('contract_sha256')==c['original_contract']['sha256'] and failure.get('transaction_sha256')==c['failed_transaction']['sha256'] and 'root_receipt_binding' in trace and 'closed accepted Image-root receipt required' in trace,'exact saved122 root-receipt failure lineage required')
    template=private(c['template_root']);require(template==private(original['output'])/'template' and set(c['template_files'])==FILES,'exact immutable122 template required')
    require(type(c['template_files']) is dict and all(re.fullmatch('[0-9a-f]{64}',c['template_files'][name] or '') and sha(template/name)==c['template_files'][name] for name in sorted(FILES)),'saved122 template metadata changed')
    require(all((template/n).is_file() and not (template/n).is_symlink() and (template/n).resolve()==template/n for n in ('Image','kernel-readonly.data')),'ordinary saved122 intrinsic byte inputs required')
    binding=read(template/'device-profile.json');report=read(template/'build-result.json')
    require(binding.get('host_profile_source_head')==HEAD and binding.get('host_profile_source_sha256')==dict(PINS) and binding.get('execution_version')==binding.get('version')=='v122' and binding.get('native_source_head')==binding.get('source_head')==native.record()['head'] and binding.get('image_sha256')==native.record()['image_sha256'] and binding.get('type3_contract_sha256')==c['original_contract']['sha256'] and read(template/'type3-contract.json')==original,'exact frozen122 binding/source89 required')
    require(sha(template/'result.json')==native.record()['result'] and c['template_files']['ci-success-context.json']==original['ci_success_context_sha256'] and c['template_files']['image-root-receipt.json']==binding.get('image_root_receipt_sha256') and c['template_files']['kernel-readonly-compact.json']==original['compact_manifest_sha256'],'exact carried native/context/receipt/compact metadata pins required')
    out=private(c['output'])
    require(all(not out.is_relative_to(private(original[k])) and not private(original[k]).is_relative_to(out) for k in ('producer_root','backup','current_packages')),'remaining123 output must be disjoint from original inputs')
    require(private(c['output'])!=template and not private(c['output']).is_relative_to(private(original['output'])) and not private(original['output']).is_relative_to(private(c['output'])),'fresh123 output must be disjoint from failed122 evidence')
    return dict(contract=c,path=str(path),sha256=expected,original=original,template=template,binding=binding,report=report,host=host,output=private(c['output']),variant=None)

def _context(row=None):
    ctx=_ACTIVE.get() or _READ.get()
    if ctx is not None:return ctx
    require(type(row) is dict and selected(row),'exact123 remaining scope required')
    f=row[FIELD];require(type(f) is dict and 'contract_path' in f and 'contract_sha256' in f,'closed123 lineage binding required')
    ctx=load(f['contract_path'],f['contract_sha256']);journal=read(ctx['output']/'transaction.json')
    require(journal.get('schema')=='saved122-template-remaining-journal-v1' and journal.get('status')==journal.get('phase')=='complete' and journal.get('contract_sha256')==ctx['sha256'] and journal.get('caps')==CAPS and journal.get('counts')==dict(template_tail=1,materializations=1,variant_validations=1,packs=1,plans=1),'completed123 remaining authority required for read only')
    return ctx

def marker(ctx):return dict(schema=FIELD_SCHEMA,contract_path=ctx['path'],contract_sha256=ctx['sha256'],composing_host=dict(host_profile_source_head=HEAD,host_profile_source_sha256=dict(PINS)),operation_host=copy.deepcopy(ctx['host']))
def project(row,ctx=None):
    ctx=ctx or _context(row);return dict(copy.deepcopy(row),**copy.deepcopy(ctx['host']),version='v123',execution_version='v123',**{FIELD:marker(ctx)})
def in_scope(root):
    ctx=_ACTIVE.get() or _READ.get()
    return ctx is not None and private(root) in (ctx['template'],ctx['output']/'plan/cycle-01/kernel-build')
def original_scope(row,path,expected):
    ctx=_ACTIVE.get() or _READ.get()
    return ctx is not None and private(path)==private(ctx['contract']['original_contract']['path']) and expected==ctx['contract']['original_contract']['sha256'] and row==ctx['original']
def applies(row):
    ctx=_ACTIVE.get() or _READ.get()
    return selected(row) or ctx is not None and row.get('host_profile_source_head')==HEAD and row.get('native_source_head')==native.record()['head']

def candidate(row,patched=None):
    import native_scoped_output_admission as shared
    ctx=_context(row);shared.no_pc(row)
    if not selected(row):require(row in (ctx['binding'],ctx['report']) and _ACTIVE.get() is not None,'retained122 origin is read-only in exact remaining transaction')
    else:
        require(row[FIELD]==marker(ctx) and row.get('host_profile_source_head')==ctx['host']['host_profile_source_head'] and row.get('host_profile_source_sha256')==ctx['host']['host_profile_source_sha256'] and row.get('version')==row.get('execution_version')=='v123','separate123 operation/source lineage differs')
    mutable={'host_profile_source_head','host_profile_source_sha256','version','execution_version','image_sha256','kernel_image_sha256','kernel_build_sha256','image_expectation_patched','auto_cycle_variant','auto_cycle_token','auto_return_diagnostic'}
    require(all(row.get(k)==v for k,v in ctx['binding'].items() if k not in mutable),'frozen122/native121 template fields differ')
    require(patched is None or row.get('image_expectation_patched') is patched,'remaining123 patch state differs')
    if row.get('image_expectation_patched'):
        require(all(row[k]==row['image_sha256'] for k in ('kernel_image_sha256','kernel_build_sha256') if k in row),'remaining123 bound image fields differ')
        w=row.get('type3_materialization',{});require(w.get('schema')=='type3-fixed-patch-v1' and w.get('generic_image_sha256')==ctx['binding']['image_sha256'] and w.get('bound_image_sha256')==row.get('image_sha256') and w.get('template_report_sha256')==ctx['contract']['template_files']['build-result.json'] and (w.get('cycle')==row.get('auto_cycle_token') or row.get('mode')=='rollback' and row.get('auto_cycle_token') is None) and re.fullmatch('[0-9a-f]{32}',w.get('cycle') or ''),'exact123 intrinsic materialization witness required')
    return dict(ctx['original'],host_source_head=ctx['host']['host_profile_source_head'],execution_version='v123',output=str(ctx['output']))

def transaction(row,phase):
    ctx=_ACTIVE.get();require(ctx is not None,'remaining123 construction scope required')
    journal=read(ctx['output']/'transaction.json');require(journal.get('status')=='started' and journal.get('phase')==phase and journal.get('contract_sha256')==ctx['sha256'],'remaining123 phase/reservation differs')
    return journal

def validate_tail(ctx):
    from sha256_kat_device_profile import root_receipt_binding,common_report
    b=ctx['binding'];root=ctx['template'];measured={k:v for k,v in b.items() if k not in ('image_root_receipt_sha256','root_reader_result_sha256')}
    measured.update(root_receipt_binding(root,root/'image-root-receipt.json',b['image_root_receipt_sha256'],measured))
    require(measured==b and sha(root/'handoff.config')==b['effective_config_sha256'],'remaining template provenance/config differs')
    require(ctx['report']==common_report(b,sha(root/'device-profile.json')),'remaining truthful template report differs')
    ctx['tail_validated']=True
    return project(ctx['report'],ctx)

def saved_template(root):
    ctx=_context();require(private(root)==ctx['template'] and ctx.get('tail_validated') is True,'only validated frozen122 template metadata available')
    require(all(sha(ctx['template']/name)==ctx['contract']['template_files'][name] for name in sorted(FILES)),'frozen122 metadata changed after tail')
    return project(ctx['report'],ctx)

def template_reader(function):
    @wraps(function)
    def checked(root,*args,**kwargs):
        if in_scope(root) and private(root)==_context()['template']:return saved_template(root)
        return function(root,*args,**kwargs)
    return checked

def variant_reader(function):
    @wraps(function)
    def checked(root,token,template=None):
        ctx=_ACTIVE.get() or _READ.get()
        if ctx is None or private(root)!=ctx['output']/'plan/cycle-01/kernel-build':return function(root,token,template)
        row=read(private(root)/'build-result.json');candidate(row,True)
        if ctx.get('variant') is not None:
            require(row==ctx['variant'] and sha(private(root)/'handoff.config')==row['effective_config_sha256'] and token==row['auto_cycle_token'] and (template is None or private(template)==ctx['template']),'validated123 variant metadata changed')
            return row
        require(_ACTIVE.get() is not None,'first123 variant validation requires construction scope')
        result=function(root,token,template);ctx['variant']=result
        j=transaction({},'plan_reserved');require(j['counts']['variant_validations']==0,'one new123 intrinsic variant validation only');j['counts']['variant_validations']=1;__import__('type3_admission').save(ctx['output']/'transaction.json',j)
        return result
    return checked

def require_materialization(output):
    ctx=_context();j=transaction({},'plan_reserved');require(private(output)==ctx['output']/'plan/cycle-01/kernel-build' and j['counts']['materializations']==0,'one fresh123 materialization only')
    j['counts']['materializations']=1;__import__('type3_admission').save(ctx['output']/'transaction.json',j)
def copy_variant(template,output):
    ctx=_context();require(private(template)==ctx['template'] and private(output)==ctx['output']/'plan/cycle-01/kernel-build','exact123 metadata copy route required')
    shutil.copytree(template,output,ignore=lambda directory,names:['Image'] if Path(directory)==ctx['template'] else [])
def require_pack(root,output,token):
    ctx=_ACTIVE.get();require(ctx is not None,'remaining123 read-only scope cannot pack')
    j=transaction({},'plan_reserved');row=read(private(root)/'build-result.json');candidate(row,True)
    require(ctx.get('variant')==row and private(output)==ctx['output']/'plan/cycle-01/boot.img' and not Path(output).exists() and token==row['auto_cycle_token'] and j['counts']['packs']==0,'one fresh123 pack only')
    j['counts']['packs']=1;__import__('type3_admission').save(ctx['output']/'transaction.json',j)

@contextmanager
def plan_scope(plan,path,expected):
    from native_prefree_output_admission import predecessor_scope
    ctx=_context(plan);require(sha(path)==expected and private(path)==ctx['output']/'plan/plan.json' and plan[FIELD]==marker(ctx),'exact123 remaining plan provenance required')
    if _ACTIVE.get() is None:
        ctx['tail_validated']=True;root=ctx['output']/'plan/cycle-01/kernel-build';ctx['variant']=read(root/'build-result.json')
    t=_READ.set(ctx)
    try:
        with predecessor_scope(ctx['original']):yield
    finally:_READ.reset(t)

def _start(path,expected):
    import type3_admission as typed
    ctx=load(path,expected);output=ctx['output'];require(not output.exists(),'fresh123 remaining output required; no restart')
    output.mkdir(parents=True)
    j=dict(schema='saved122-template-remaining-journal-v1',status='started',phase='template_tail',contract_sha256=expected,counts=dict(template_tail=1,materializations=0,variant_validations=0,packs=0,plans=0),caps=CAPS,device_operations=[])
    typed.save(output/'transaction.json',j);return ctx

def _ready(ctx):
    import type3_admission as typed
    validate_tail(ctx);j=transaction({},'template_tail');j.update(phase='plan_reserved');j['counts']['plans']=1;typed.save(ctx['output']/'transaction.json',j)

def _finish(ctx,result):
    import type3_admission as typed
    j=transaction({},'plan_reserved');require(j['counts']==dict(template_tail=1,materializations=1,variant_validations=1,packs=1,plans=1),'exact123 remaining counts incomplete')
    require(private(result['plan'])==ctx['output']/'plan/plan.json' and sha(result['plan'])==result['plan_sha256'] and read(result['plan']).get(FIELD)==marker(ctx),'completed123 plan/source lineage differs')
    j.update(status='complete',phase='complete',result=result,IO_events=list(typed.IO_EVENTS));typed.save(ctx['output']/'transaction.json',j);return result

def prepare(path,expected):
    import sha256_kat_device_profile as profile
    import type3_admission as typed
    from native_prefree_output_admission import predecessor_scope
    ctx=_start(path,expected);t=_ACTIVE.set(ctx)
    try:
        _ready(ctx);old=ctx['original']
        with predecessor_scope(old):result=profile.prepare_plan(ctx['template'],private(old['backup']),private(old['reference_twrp']),Path(old['mkbootimg']),private(old['current_packages']),ctx['output']/'plan',1)
        return _finish(ctx,result)
    except BaseException as error:
        j=read(ctx['output']/'transaction.json');j.update(status='failed_no_restart',error_type=type(error).__name__,IO_events=list(typed.IO_EVENTS));typed.save(ctx['output']/'transaction.json',j);raise
    finally:_ACTIVE.reset(t)

def main():
    p=argparse.ArgumentParser();p.add_argument('--contract',required=True,type=Path);p.add_argument('--contract-sha256',required=True);a=p.parse_args();print(json.dumps(prepare(a.contract,a.contract_sha256),indent=2))
if __name__=='__main__':
    # Preserve one canonical ContextVar instance across CLI and imported dispatch.
    import type3_remaining_template as canonical
    canonical.main()
