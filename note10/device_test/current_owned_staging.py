"""Default-off exact-current owned output; PC-only and metadata-only host join."""
import json
from pathlib import Path
import re
import owned_contiguous_staging as legacy
import linux_data_carrier as data

KIND='current-owned-staging-pc'
BYTES=19136512
ALIGN=16384
API_PINS=legacy.API_PINS
WORKFLOW='.github/workflows/note10-current-owned-staging-pc.yml'
SOURCES=('current_owned_staging.py','current_owned_capacity.h','current_owned_staging_composition.c',
    'current_owned_staging_fixture.c','test_current_owned_staging.py','build_current_owned_staging.py')
CASE_NAMES=('test_current_capacity_direct_output_and_old_span_refusal',
    'test_current_capacity_cleanup_and_canaries',
    'test_closed_current_profile_defaults_and_receipt_join')
footprint=legacy.footprint


def install(source,identity):
    source=Path(source);result=legacy.install(source,identity)
    config=source/'drivers/misc/note10_sha256_kat.Kconfig'
    config.write_bytes(config.read_bytes()+b'\nconfig NOTE10_CURRENT_OWNED_STAGING\n\tbool "Note10 PC-only exact current owned capacity"\n\tdepends on NOTE10_OWNED_CONTIGUOUS_STAGING\n\tdefault n\n')
    for target,name in (('drivers/misc/current_owned_capacity.h','current_owned_capacity.h'),
        ('drivers/misc/owned_contiguous_staging_composition.c','owned_contiguous_staging_composition.c'),
        ('drivers/misc/note10_sha256_kat.c','current_owned_staging_composition.c')):
        p=source/target;p.write_bytes((data.HERE/name).read_bytes());result[target]=data.sha(p.read_bytes())
    result['drivers/misc/note10_sha256_kat.Kconfig']=data.sha(config.read_bytes())
    return result


def relative(result,config,record,*,elf,archive,raw_inputs):
    filtered=[x for x in config if x not in ('CONFIG_NOTE10_CURRENT_OWNED_STAGING=y',
        '# CONFIG_NOTE10_CURRENT_OWNED_STAGING is not set')]
    previous=legacy.relative(result,filtered,record,elf=elf,archive=archive,raw_inputs=raw_inputs)
    checks=dict(previous['checks'],current_owned_enabled='CONFIG_NOTE10_CURRENT_OWNED_STAGING=y' in config)
    return dict(checks=checks,relative_eligible=all(checks.values()),PC_only=True,physical_ready=False,
        route_relation=previous['route_relation'],global_RAM_ownership=False)


def pc_contract(result,source):
    ci=result.get('ci_context',{})
    data.require(result.get('passed') is True and result.get('Image_built') is True and
        result.get('BOOT_built') is False and result.get('version')=='v96' and
        result.get('diagnostic_kind')==KIND and result.get('PC_only') is True and
        result.get('physical_ready') is False and result.get('owned_capacity_bytes')==BYTES and
        result.get('owned_alignment_bytes')==ALIGN and result.get('owned_default_enabled') is False and
        result.get('current_owned_default_enabled') is False and
        result.get('owned_capacity_source')=='current_owned_capacity.h' and
        result.get('data_expectation_mode')==data.MODE and re.fullmatch('[0-9a-f]{40}',source or '') and
        ci.get('GITHUB_SHA')==ci.get('GITHUB_WORKFLOW_SHA')==source and
        ci.get('GITHUB_JOB')==KIND and ci.get('GITHUB_REPOSITORY')=='eirblue/ios_note10p' and
        ci.get('GITHUB_WORKFLOW_REF')=='eirblue/ios_note10p/'+WORKFLOW+'@refs/heads/main' and
        all(re.fullmatch('[1-9][0-9]*',ci.get(k,'') or '') for k in ('GITHUB_RUN_ID','GITHUB_RUN_ATTEMPT')),
        'closed current PC-only owned producer differs')
    return dict(PC_only=True,physical_ready=False,owned_capacity_bytes=BYTES,
        global_RAM_ownership=False,whole_XNU_kernel_entry_executed=False,hardware_XNU_executed=False)


def pinned_metadata(path,expected):
    p=Path(path).absolute();root=(data.HERE.parent/'private').resolve()
    data.require(p.resolve()==p and p!=root and p.is_relative_to(root) and
        not any(q.is_symlink() for q in (p,*p.parents)) and p.is_file() and
        0<p.stat().st_size<=2*1024*1024 and re.fullmatch('[0-9a-f]{64}',expected or ''),
        'bounded pinned private metadata required')
    raw=p.read_bytes();data.require(data.sha(raw)==expected,'metadata pin differs')
    value=json.loads(raw);data.require(type(value) is dict,'metadata object required');return value


def join_host_payload(producer_result,producer_sha256,source,*,host_receipt,host_receipt_sha256):
    # Root supplies hashes from authenticated collection/accepted host transaction.
    result=pinned_metadata(producer_result,producer_sha256);pc_contract(result,source)
    host=pinned_metadata(host_receipt,host_receipt_sha256)
    data.require(host.get('schema')=='note10-v95-host-operator-receipt-v1','accepted current host receipt required')
    actual=host['actual_transform']
    data.require(actual.get('command_invocations')==1 and actual.get('exit_code')==0,'one accepted host transform required')
    made=pinned_metadata(actual['result_path'],actual['result_manifest_sha256'])
    fit=pinned_metadata(actual['fit_report_path'],actual['fit_report_sha256'])
    inputs=pinned_metadata(actual['input_binding_path'],actual['input_binding_sha256'])
    context=inputs['actual_producer_context'];ci=fit.get('ci_context',{});current=context['producer']
    data.require(made.get('kind')=='v95-fresh-current-payload-carrier-pc' and made.get('accepted') is True and
        made.get('decoder_calls')==1 and made.get('fits_budget') is True and
        made.get('payload_manifest_sha256')==actual['fit_report_sha256'] and
        made.get('input_binding_metadata_sha256')==actual['input_binding_sha256'] and
        fit.get('current_producer_kind')=='v94-exynos-checked-ptpage-pc' and
        context.get('kind')=='v84-current-native' and current.get('candidate_kind')=='v94-exynos-checked-ptpage-pc' and
        ci==current.get('ci_context') and current.get('source_commit')==ci.get('GITHUB_SHA') and
        ci.get('GITHUB_WORKFLOW_REF')=='eirblue/ios_note10p/.github/workflows/note10-exynos-checked-ptpage-pc.yml@refs/heads/main' and
        fit.get('producer_id')==context.get('producer_id') and fit.get('input_binding')==context.get('input_binding') and
        fit.get('producer_context_sha256')==inputs.get('producer_context_sha256') and
        fit.get('producer_result_sha256')==inputs.get('producer_result_sha256_reused_from_accepted_receipt') and
        made.get('payload_bytes')==fit.get('payload_bytes')==BYTES and
        made.get('PC_only') is fit.get('PC_only') is True and
        made.get('physical_ready') is fit.get('physical_ready') is False and
        made.get('carrier_admitted') is fit.get('carrier_admitted') is False,
        'accepted current payload/context does not match new owned capacity')
    return dict(payload_bytes=BYTES,new_owned_capacity_match=True,
        legacy_owned_capacity_match=BYTES==legacy.BYTES,PC_only=True,physical_ready=False,
        global_RAM_ownership=False,whole_XNU_kernel_entry_executed=False,hardware_XNU_executed=False)
