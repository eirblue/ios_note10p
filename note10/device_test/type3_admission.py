"""Host108 typed admission for the exact retained native107 class3 Image."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import retained_v108_origin as retained
import class3_native_origin as origins

import kernel_readonly_span_candidate as ro3
import kernel_readonly_input as old
import linux_data_carrier as data

OFFLINE_SCHEMA='note10-type3-offline-first-use-v1'
DEVICE_SCHEMA='note10-type3-device-first-use-v1'
COMPACT_FIELDS=('type3_compact_sha256','type3_compact_bytes','type3_compact_manifest_sha256')
BINDING_FIELDS=(*ro3.FIELDS,'diagnostic_kind','data_input_kind','storage_input_kind','version','execution_version','native_producer_version',
    'native_source_head','native_producer_PC_first_use','type3_native_origin','type3_generic_image_sha256','type3_contract_path','type3_contract_sha256',
    'type3_external_choice',*COMPACT_FIELDS)
PLAN_FIELDS=('execution_version','executing_host_source_head','type3_contract_sha256')
OFFLINE_CAPS=dict(compact_source_consumptions=1,compact_derivations=0,templates=1,materializations=1,plans=1,cycles=1,
    Image_builds=0,CI=0,C_compiles=0,decoder_or_MachO_replays=0,device_queries=0,BOOT_writes=0,reboots=0)
OFFLINE_KEYS={'schema','status','execution_version','host_source_head','native_source_head','accepted_result_sha256',
    'producer_root','ci_success_context','ci_success_context_sha256','compact_manifest','compact_manifest_sha256',
    'backup','backup_manifest_sha256','current_packages','current_package_result_sha256','current_boot_sha256',
    'reference_twrp','mkbootimg','output','caps'}
# These events count named compact/variant operations; common source/artifact
# hashes, whole-tree template copy, BOOT wrapping and package I/O are additional.
IO_EVENTS=[]


def sha(raw):return hashlib.sha256(raw).hexdigest()
def read(path):return json.loads(Path(path).read_text(encoding='utf-8-sig'))
def save(path,row):Path(path).write_text(json.dumps(row,indent=2,sort_keys=True)+'\n',encoding='utf-8')
def require(value,message):data.require(value,message)
def private(path):
    from sha256_kat_device_profile import private as checked
    p=checked(path)
    require(not p.is_symlink(),'type3 symlink path refused')
    return p


def version(value):
    require(type(value) is str and re.fullmatch('v[1-9][0-9]*',value) and int(value[1:])>=108,'type3 execution version must be v108 or later')
    return value


def native_origin(head=None):
    return origins.origin(head or ro3.NATIVE_HEAD)


def load_offline(path,expected):
    path=private(path);raw=data.bounded_private_read(path,65536)
    require(re.fullmatch('[0-9a-f]{64}',expected or '') and sha(raw)==expected,'exact reviewed type3 offline contract SHA required')
    row=json.loads(raw.decode('utf-8-sig'))
    require(type(row) is dict,'closed type3 offline object required')
    item=origins.record(row.get('native_source_head'))
    require(type(row) is dict and set(row)==OFFLINE_KEYS and row['schema']==OFFLINE_SCHEMA and row['status']=='reviewed_ready' and
        row['native_source_head']==item['head'] and row['accepted_result_sha256']==item['result'] and
        type(row['caps']) is dict and row['caps']==OFFLINE_CAPS and all(type(v) is int for v in row['caps'].values()),'closed type3 single offline transaction required')
    version(row['execution_version'])
    from sha256_kat_device_profile import host_binding
    if item['version']=='v107':
        require(retained.reading() and row['host_source_head']==retained.HEAD and row['execution_version']=='v108','native107 contract is retained-read-only')
    else:
        require(row['execution_version']=='v110','native109 requires separately versioned host110')
        origins.live_host(row['host_source_head']);host_binding(row['host_source_head'])
    for key in ('producer_root','ci_success_context','compact_manifest','backup','current_packages','reference_twrp','output'):
        require(type(row[key]) is str and str(private(row[key]))==row[key],'canonical private type3 path required')
    # Only this repository tool crosses the private boundary; payload paths do not.
    from prepare_linux_boot import MKBOOTIMG_SHA256
    from sha256_kat_device_profile import sha as file_sha
    tool=Path(__file__).resolve().parents[2]/'research/twrp-d2x-reference/aosp-mkbootimg.py'
    require(type(row['mkbootimg']) is str and row['mkbootimg']==str(tool) and
        tool.is_file() and not tool.is_symlink() and tool.resolve()==tool,'exact canonical repository mkbootimg required')
    require(file_sha(tool)==MKBOOTIMG_SHA256,'expected pinned Android 12 AOSP mkbootimg script')
    require(all(re.fullmatch('[0-9a-f]{64}',row[key] or '') for key in
        ('ci_success_context_sha256','compact_manifest_sha256','backup_manifest_sha256','current_package_result_sha256','current_boot_sha256')),'type3 input metadata pins required')
    output=Path(row['output'])
    require(all(not output.is_relative_to(Path(row[key])) and not Path(row[key]).is_relative_to(output) for key in
        ('producer_root','backup','current_packages')),'type3 output and original inputs must be disjoint')
    return row


def contract_binding(row):
    contract=load_offline(row.get('type3_contract_path',''),row.get('type3_contract_sha256'))
    require(row.get('execution_version')==row.get('version')==contract['execution_version'] and
        row.get('host_profile_source_head')==contract['host_source_head'],'type3 execution host/version differs from reviewed contract')
    return contract


def candidate_scope(row,*,patched=None):
    item=origins.record(row.get('native_source_head'))
    if item['version']=='v109':
        origins.live_row(row)
        require(all(row.get(key)==value for key,value in origins.stage_fields().items()),'native109 stage provenance differs')
        require(row.get('kernel_readonly3_image_bytes')==item['image_bytes'] and
            row.get('kernel_readonly3_linked_bytes')==item['linked_bytes'],'accepted native109 dimensions differ')
    else:retained.origin(row)
    require(row.get('device_profile')==data.PROFILE and row.get('diagnostic_kind')==item['kind'] and
        row.get('data_input_kind')==row.get('storage_input_kind')==item['kind'] and row.get('kernel_readonly3_schema')==ro3.SCHEMA and
        row.get('data_expectation_mode')==ro3.MODE and row.get('kernel_readonly3_marker')=='N10DATARO3' and
        row.get('kernel_readonly3_span_schema')==old.SPAN_SCHEMA and row.get('kernel_readonly3_requires_ack') is True and
        row.get('source_head')==row.get('native_source_head')==item['head'] and row.get('native_producer_version')==item['version'] and
        row.get('type3_native_origin')==native_origin(item['head']) and row.get('native_producer_PC_first_use') is True and row.get('PC_only') is not True and
        not any(key in row for key in (*old.FIELDS[1:],'kernel_readonly_span_schema','readonly_input_schema','readonly_pc_contract')),
        'exact retained native class3 and separate new host identity required')
    version(row.get('execution_version'))
    from sha256_kat_device_profile import host_binding
    host=retained.origin(row) if retained.selected(row) else host_binding(row.get('host_profile_source_head'))
    require(row.get('host_profile_source_sha256')==host['host_profile_source_sha256'],'type3 current host closure differs')
    ro3.metadata_contract(row.get('kernel_readonly3_slot'),row.get('kernel_readonly3_image_bytes'))
    span=row.get('kernel_readonly3_span')
    require(type(span) is dict and set(span)=={'schema','kernel_bytes','text_prefix_bytes','slot_contained','descriptor_contained','disjoint','source','phase','hardware','ownership'} and
        type(span['kernel_bytes']) is int and 0<span['kernel_bytes']<=ro3.BUDGET and type(span['text_prefix_bytes']) is int and span['text_prefix_bytes']>=0 and
        all(span[key] is True for key in ('slot_contained','descriptor_contained','disjoint')) and span['hardware'] is False and span['ownership'] is False and
        span['source']=='linked-kernel' and span['phase']=='pre_descriptor','type3 closed native span metadata required')
    require(row.get('data_expectation_slot')==row['kernel_readonly3_slot'] and
        type(row.get('kernel_readonly3_linked_bytes')) is int and 0<row['kernel_readonly3_linked_bytes']<=ro3.BUDGET and
        row.get('image_size',row['kernel_readonly3_image_bytes'])==row['kernel_readonly3_image_bytes'] and
        row.get('kernel_readonly3_span',{}).get('schema')==old.SPAN_SCHEMA and
        row['kernel_readonly3_span']['kernel_bytes']+row['kernel_readonly3_span']['text_prefix_bytes']==row['kernel_readonly3_linked_bytes'] and
        row.get('data_carrier_stage')==data.STAGE and row.get('data_relative_placement_admitted') is False and row.get('raw_input_binding') is False and
        row.get('type3_external_choice')=='compact-v1' and row.get('type3_compact_bytes')==ro3.CAPACITY and
        row.get('data_carrier_bytes')==old.OLD_BYTES and row.get('data_payload_bytes')==old.PAYLOAD_BYTES and
        all(re.fullmatch('[0-9a-f]{64}',row.get(key,'') or '') for key in
            ('type3_generic_image_sha256','type3_compact_sha256','type3_compact_manifest_sha256','data_manifest_sha256','data_carrier_sha256','data_payload_sha256')) and
        type(row.get('image_expectation_patched')) is bool,'closed type3 Image/compact/source binding required')
    for extent in row['kernel_readonly3_slot']['slot'],row['kernel_readonly3_slot']['descriptor']:
        require(span['text_prefix_bytes']<=extent['offset'] and extent['offset']+extent['bytes']<=row['kernel_readonly3_linked_bytes'],'type3 complete linked extent differs')
    contract=contract_binding(row)
    require(row['type3_compact_manifest_sha256']==contract['compact_manifest_sha256'],'type3 compact manifest/contract differs')
    if patched is not None:require(row['image_expectation_patched'] is patched,'type3 patch state differs')
    if row['image_expectation_patched']:
        witness=row.get('type3_materialization',{})
        require(type(witness) is dict and set(witness)=={'schema','generic_image_sha256','bound_image_sha256','template_report_sha256','cycle'} and
            witness['schema']=='type3-fixed-patch-v1' and witness['generic_image_sha256']==row['type3_generic_image_sha256'] and
            all(row[key]==witness['bound_image_sha256'] for key in ('image_sha256','kernel_image_sha256','kernel_build_sha256') if key in row) and
            (witness['cycle']==row.get('auto_cycle_token') or row.get('mode')=='rollback' and row.get('auto_cycle_token') is None) and re.fullmatch('[0-9a-f]{32}',witness['cycle'] or '') and
            re.fullmatch('[0-9a-f]{64}',witness['template_report_sha256'] or ''),'intrinsic type3 materialization witness required')
    else:require('type3_materialization' not in row,'generic type3 cannot claim materialization')
    return contract


def compact_binding(raw,manifest_raw):
    fields=old.validate_compact(raw,manifest_raw)
    meta=json.loads(manifest_raw)
    return dict(data_manifest_sha256=meta['source_manifest_sha256'],data_carrier_sha256=meta['source_carrier_sha256'],
        data_carrier_bytes=old.OLD_BYTES,data_payload_sha256=meta['payload_sha256'],data_payload_bytes=old.PAYLOAD_BYTES,
        **dict(zip(COMPACT_FIELDS,(fields['kernel_readonly_compact_sha256'],fields['kernel_readonly_compact_bytes'],fields['kernel_readonly_compact_manifest_sha256']))))


def read_compact(root,row):
    meta=data.bounded_private_read(Path(root)/'kernel-readonly-compact.json',65536)
    raw=data.bounded_private_read(Path(root)/'kernel-readonly.data',ro3.CAPACITY)
    fields=compact_binding(raw,meta)
    require(all(row.get(key)==value for key,value in fields.items()),'type3 compact copy identity differs')
    IO_EVENTS.append(dict(operation='intrinsic_compact_copy_validation',file_reads=2,bytes_read=len(raw)+len(meta),compact_hashes=1,stream_hashes=1,manifest_hashes=1,decoder_calls=0))
    return raw,fields


def transaction(row,phase):
    output=Path(row['output']);journal=read(output/'transaction.json')
    require(journal.get('schema')=='type3-offline-journal-v1' and journal.get('status')=='started' and journal.get('phase')==phase and
        journal.get('contract_sha256')==row['_contract_sha256'],'unfinished exact type3 transaction reservation required')
    return journal


def _copy_ci_context(output,raw):
    output=private(output)
    require(output.is_dir() and type(raw) is bytes and 0<len(raw)<=65536,'bounded reviewed CI context copy required')
    # The receipt pins the reviewed bytes, including JSON ordering/whitespace.
    # A fresh copy must not reserialize or overwrite that evidence.
    with (output/'ci-success-context.json').open('xb') as stream:stream.write(raw)


def prepare_template(contract,path,expected):
    item=origins.record(contract.get('native_source_head'))
    require(item['version']=='v109' and contract.get('execution_version')=='v110','new templates require native109/host110')
    origins.live_host(contract.get('host_source_head'))
    from sha256_kat_device_profile import raw_binding,host_binding,ci_success_receipt,write_ci_success_receipt,common_report,sha as file_sha
    transaction(contract,'template_reserved')
    source=Path(contract['producer_root']);output=Path(contract['output'])/'template'
    require(not output.exists(),'fresh type3 template required')
    binding=raw_binding(source,item['result'],item['head'],readonly_origin=item['head'])
    context_raw=data.bounded_private_read(Path(contract['ci_success_context']),65536)
    require(sha(context_raw)==contract['ci_success_context_sha256'],'type3 Root CI context changed')
    receipt=ci_success_receipt(json.loads(context_raw.decode('utf-8-sig')),contract['ci_success_context_sha256'],binding,read(source/'result.json'))
    manifest=data.bounded_private_read(Path(contract['compact_manifest']),65536)
    require(sha(manifest)==contract['compact_manifest_sha256'],'approved existing compact manifest changed')
    compact=data.bounded_private_read(Path(contract['compact_manifest']).parent/'kernel-readonly.data',ro3.CAPACITY)
    fields=compact_binding(compact,manifest)
    binding.update(fields,**host_binding(contract['host_source_head']),version=contract['execution_version'],execution_version=contract['execution_version'],
        native_producer_version=item['version'],native_source_head=item['head'],native_producer_PC_first_use=True,type3_native_origin=native_origin(item['head']),
        type3_generic_image_sha256=binding['image_sha256'],type3_contract_path=str(path),type3_contract_sha256=expected,type3_external_choice='compact-v1')
    shutil.copytree(source,output)
    for name,raw in (('kernel-readonly.data',compact),('kernel-readonly-compact.json',manifest),('type3-contract.json',Path(path).read_bytes())):
        with (output/name).open('xb') as stream:stream.write(raw)
    IO_EVENTS.append(dict(operation='attach_existing_compact_once',source_file_reads=2,source_bytes_read=len(compact)+len(manifest),
        compact_hashes=1,stream_hashes=1,manifest_hashes=2,compact_files_written=1,compact_bytes_written=len(compact),
        metadata_copies=2,derivations=0,recompressions=0,decoder_calls=0))
    binding.update(write_ci_success_receipt(output,receipt))
    _copy_ci_context(output,context_raw)
    save(output/'device-profile.json',binding)
    save(output/'build-result.json',common_report(binding,file_sha(output/'device-profile.json')))
    shutil.copyfile(output/'prerequisites/objects/.config',output/'handoff.config')
    validate_template(output)
    return output


@retained.reader
def validate_template(root):
    from sha256_kat_device_profile import raw_binding,host_profile_origin,root_receipt_binding,common_report,ci_success_receipt,sha as file_sha
    root=private(root);binding=read(root/'device-profile.json')
    contract=candidate_scope(binding,patched=False);item=origins.record(binding['native_source_head'])
    measured=raw_binding(root,item['result'],item['head'],readonly_origin=item['head'])
    _,fields=read_compact(root,binding);measured.update(fields)
    measured.update(host_profile_origin(binding),version=binding['version'],execution_version=binding['execution_version'],
        native_producer_version=item['version'],native_source_head=item['head'],native_producer_PC_first_use=True,type3_native_origin=native_origin(item['head']),
        type3_generic_image_sha256=measured['image_sha256'],type3_contract_path=binding['type3_contract_path'],
        type3_contract_sha256=binding['type3_contract_sha256'],type3_external_choice='compact-v1')
    context_raw=data.bounded_private_read(Path(contract['ci_success_context']),65536)
    require(sha(context_raw)==contract['ci_success_context_sha256'] and file_sha(root/'type3-contract.json')==binding['type3_contract_sha256'],'type3 copied contract/Root CI context changed')
    expected_receipt=ci_success_receipt(json.loads(context_raw.decode('utf-8-sig')),contract['ci_success_context_sha256'],measured,read(root/'result.json'))
    require(read(root/'image-root-receipt.json')==expected_receipt,'type3 Root CI receipt differs')
    measured.update(root_receipt_binding(root,root/'image-root-receipt.json',binding['image_root_receipt_sha256'],measured))
    require(measured==binding and file_sha(root/'handoff.config')==binding['effective_config_sha256'],'type3 template provenance/config differs')
    report=read(root/'build-result.json')
    require(report==common_report(binding,file_sha(root/'device-profile.json')),'type3 truthful host108 template report differs')
    return report


def patch_image(raw,report,token,cycle_slot,compact):
    origins.live_row(report)
    contract=candidate_scope(report,patched=False)
    transaction(dict(contract,_contract_sha256=report['type3_contract_sha256']),'plan_reserved')
    record=report['kernel_readonly3_slot'];a=record['slot']['offset'];b=record['descriptor']['offset']
    require(len(raw)==report['kernel_readonly3_image_bytes'] and sha(raw)==report['type3_generic_image_sha256']==report['image_sha256'] and
        len(compact)==ro3.CAPACITY and sha(compact)==report['type3_compact_sha256'] and
        raw.count(ro3.DESCRIPTOR)==1 and raw[b:b+80]==ro3.DESCRIPTOR and raw[a:a+ro3.CAPACITY]==bytes(ro3.CAPACITY) and
        raw.count(cycle_slot+b'\0')==1 and re.fullmatch('[0-9a-f]{32}',token or ''),'exact type3 generic Image/compact/cycle preimages required')
    cycle=raw.index(cycle_slot+b'\0')
    require(all(cycle+32<=part['offset'] or part['offset']+part['bytes']<=cycle for part in (record['slot'],record['descriptor'])),
        'type3 slot/descriptor/cycle extents overlap')
    result=bytearray(raw);result[a:a+ro3.CAPACITY]=compact
    result[b+32:b+72]=ro3.CAPACITY.to_bytes(8,'little')+bytes.fromhex(report['type3_compact_sha256'])
    result[cycle:cycle+32]=token.encode('ascii')
    require(len(result)==len(raw),'type3 fixed Image length changed')
    IO_EVENTS.append(dict(operation='one_fixed_type3_variant_patch',slot_copy_bytes=ro3.CAPACITY,descriptor_logical_expected_bytes=40,cycle_bytes=32,
        generic_image_hashes=1,compact_hashes=1,derivations=0,decoder_calls=0))
    return bytes(result)


def materialization(report,token,generic_sha,bound_sha,template_report_sha):
    return dict(schema='type3-fixed-patch-v1',generic_image_sha256=generic_sha,bound_image_sha256=bound_sha,
        template_report_sha256=template_report_sha,cycle=token)


@retained.reader
def validate_variant(root,token,template=None):
    from materialize_auto_cycle import template_bytes,SLOT
    root=private(root);report=read(root/'build-result.json');candidate_scope(report,patched=True)
    require(report.get('auto_cycle_variant') is True and report.get('auto_cycle_token')==token,'type3 cycle differs')
    source=private(report['auto_cycle_template'])
    require(template is None or source==private(template),'type3 template path differs')
    original,generic=template_bytes(source);actual=data.bounded_private_read(root/'Image',report['image_size'])
    require(len(actual)==len(generic) and sha(actual)==report['image_sha256'] and
        sha((source/'build-result.json').read_bytes())==report['auto_cycle_template_report_sha256'] and
        sha(generic)==report['auto_cycle_template_image_sha256'],'type3 actual variant/template bytes differ')
    compact,_=read_compact(source,original);slot=original['kernel_readonly3_slot'];a=slot['slot']['offset'];b=slot['descriptor']['offset'];c=generic.index(SLOT+b'\0')
    regions=sorted(((a,a+ro3.CAPACITY,compact),(b+32,b+72,ro3.CAPACITY.to_bytes(8,'little')+bytes.fromhex(original['type3_compact_sha256'])),(c,c+32,token.encode('ascii'))))
    position=0
    for start,end,want in regions:
        require(position<=start<end<=len(actual) and actual[position:start]==generic[position:start] and actual[start:end]==want,'type3 fixed patch extent differs')
        position=end
    require(actual[position:]==generic[position:],'type3 bytes outside patch extents differ')
    allowed=dict(original,auto_cycle_variant=True,auto_cycle_token=token,auto_cycle_template=str(source),
        auto_cycle_template_report_sha256=report['auto_cycle_template_report_sha256'],auto_cycle_template_image_sha256=sha(generic),
        image_sha256=sha(actual),image_expectation_patched=True)
    allowed['type3_materialization']=materialization(original,token,sha(generic),sha(actual),report['auto_cycle_template_report_sha256'])
    require(report==allowed,'type3 variant report differs outside intrinsic binding')
    IO_EVENTS.append(dict(operation='validate_existing_variant_without_repatch',actual_Image_reads=1,generic_Image_reads='existing template_bytes',fixed_patch_transactions=0,decoder_calls=0))
    return report


def require_plan_transaction(template,output):
    origins.live_row(template)
    contract=candidate_scope(template,patched=False)
    contract=dict(contract,_contract_sha256=template['type3_contract_sha256'])
    require(private(output)==Path(contract['output'])/'plan','type3 one plan output differs')
    transaction(contract,'plan_reserved')


def require_materialization_transaction(template,output):
    origins.live_row(template)
    contract=candidate_scope(template,patched=False)
    require(private(output)==Path(contract['output'])/'plan/cycle-01/kernel-build','one reviewed class3 variant output required')
    transaction(dict(contract,_contract_sha256=template['type3_contract_sha256']),'plan_reserved')


def prepare_offline(path,expected):
    contract=load_offline(path,expected);item=origins.record(contract['native_source_head'])
    require(item['version']=='v109' and contract['execution_version']=='v110','only native109/host110 may start new offline work')
    origins.live_host(contract['host_source_head']);output=Path(contract['output'])
    require(not output.exists(),'type3 transaction already reserved; partial/completed transaction cannot restart')
    from sha256_kat_device_profile import sha as file_sha,prepare_plan
    require(file_sha(Path(contract['backup'])/'backup-manifest.json')==contract['backup_manifest_sha256'] and
        file_sha(Path(contract['current_packages'])/'package-result.json')==contract['current_package_result_sha256'],'type3 saved current/backup metadata changed')
    current=read(Path(contract['current_packages'])/'package-result.json')
    with retained.read_scope():retained.origin(current)
    require(current.get('backup_manifest_sha256')==contract['backup_manifest_sha256'] and
        any(record.get('mode')=='diagnostic' and record.get('payload_sha256')==contract['current_boot_sha256'] for record in current.get('packages',[])),
        'host110 requires the exact saved current v108 full BOOT/package/backup baseline')
    output.mkdir(parents=True)
    journal=dict(schema='type3-offline-journal-v1',status='started',phase='template_reserved',contract_sha256=expected,
        attempts=dict(templates=1,plans=0,materializations=0),device_operations=[])
    save(output/'transaction.json',journal);scoped=dict(contract,_contract_sha256=expected)
    try:
        template=prepare_template(scoped,private(path),expected)
        journal.update(phase='plan_reserved');journal['attempts'].update(plans=1,materializations=1);save(output/'transaction.json',journal)
        result=prepare_plan(template,Path(contract['backup']),Path(contract['reference_twrp']),Path(contract['mkbootimg']),
            Path(contract['current_packages']),output/'plan',1)
        plan=read(result['plan']);require(plan.get('current_boot_payload_sha256')==contract['current_boot_sha256'],'type3 saved current BOOT differs')
        journal.update(status='complete',phase='complete',result=result,IO_events=list(IO_EVENTS));save(output/'transaction.json',journal)
        return dict(result,transaction=str(output/'transaction.json'),native_version=item['version'],execution_version=contract['execution_version'],device_operations=[])
    except BaseException as error:
        journal.update(status='failed_no_restart',error_type=type(error).__name__,IO_events=list(IO_EVENTS));save(output/'transaction.json',journal)
        raise


def execution_context(row,plan_sha,packages,declared_version,host_head,path,expected,execution_output=None):
    origins.live_row(row)
    offline=candidate_scope(row,patched=True)
    completed=read(Path(offline['output'])/'transaction.json')
    require(completed.get('status')=='complete' and completed.get('phase')=='complete' and completed.get('contract_sha256')==row['type3_contract_sha256'] and
        completed.get('result',{}).get('plan_sha256')==plan_sha,'exact type3 offline transaction must complete before transport')
    require(version(declared_version)==row['execution_version'] and host_head==row['host_profile_source_head'],'declared execution host/version differs')
    require(re.fullmatch('[0-9a-f]{64}',plan_sha or ''),'exact type3 plan SHA required before transport')
    require(path is not None and re.fullmatch('[0-9a-f]{64}',expected or ''),'explicit type3 device contract path/SHA required')
    path=private(path);raw=data.bounded_private_read(path,65536)
    require(sha(raw)==expected,'exact reviewed type3 device contract required')
    contract=json.loads(raw.decode('utf-8-sig'))
    keys={'schema','status','execution_version','host_source_head','native_source_head','plan_sha256','packages','package_result_sha256',
        'bound_image_sha256','offline_contract_sha256','output','minimum_battery','BOOT_write_max','reboot_max','user_availability_record_sha256'}
    require(type(contract) is dict and set(contract)==keys and contract['schema']==DEVICE_SCHEMA and contract['status']=='reviewed_ready' and
        contract['execution_version']==declared_version and contract['host_source_head']==host_head and contract['native_source_head']==row['native_source_head'] and
        contract['plan_sha256']==plan_sha and contract['packages']==str(private(packages)) and
        execution_output is not None and contract['output']==str(private(execution_output)) and not private(execution_output).is_relative_to(private(packages)) and
        contract['bound_image_sha256']==row.get('image_sha256',row.get('kernel_image_sha256')) and contract['offline_contract_sha256']==row['type3_contract_sha256'] and
        type(contract['minimum_battery']) is int and contract['minimum_battery']==10 and
        type(contract['BOOT_write_max']) is int and contract['BOOT_write_max']==1 and type(contract['reboot_max']) is int and contract['reboot_max']==1 and
        contract['user_availability_record_sha256']=='4a639d278836af88256a339d199b9fbe53ad65d354db4b8c4401796522e758e9',
        'closed type3 reviewed device contract/plan/host scope differs')
    require(sha((private(packages)/'package-result.json').read_bytes())==contract['package_result_sha256'],'reviewed type3 package manifest changed')
    return dict(schema='type3-explicit-execution-v1',declared_version=declared_version,host_source_head=host_head,plan_sha256=plan_sha,
        packages=str(private(packages)),output=str(private(execution_output)),contract_path=str(path),contract_sha256=expected)



def require_context_directory(context,directory):
    if context is not None:
        require(type(context) is dict and context.get('packages')==str(private(directory)),'type3 actual package directory differs from reviewed execution context')

def require_device_scope(row,ack_kernel_readonly_growth=False,context=None):
    origins.live_row(row)
    require(ack_kernel_readonly_growth is True,'type3 requires explicit growth ACK before any device query')
    candidate_scope(row,patched=True)
    keys={'schema','declared_version','host_source_head','plan_sha256','packages','output','contract_path','contract_sha256'}
    require(type(context) is dict and set(context)==keys and context.get('schema')=='type3-explicit-execution-v1','explicit reviewed type3 execution context required before transport')
    expected=execution_context(row,context['plan_sha256'],context['packages'],context['declared_version'],context['host_source_head'],context['contract_path'],context['contract_sha256'],context['output'])
    require(expected==context,'type3 execution context differs')
    return True


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--contract',type=Path,required=True);parser.add_argument('--contract-sha256',required=True)
    args=parser.parse_args();print(json.dumps(prepare_offline(args.contract,args.contract_sha256),indent=2))
