"""Private fresh v94 payload/carrier transform; host only, no binary parser or device route.

Root-selected JSON SHA pins are offline trust anchors from authenticated collection,
not producer self-approval or an independent GitHub verification.
"""
import argparse
import json
import lzma
from pathlib import Path
import re

import current_data_carrier as carrier
from handoff_bundle import materialize_kernel
from prepare_current_payload import bounded_read, digest, geometry, pinned_json, private, require, sha

BUDGET = 10962166
OLD_LINUX_CAPACITY = 19546112
PAGE = 16384
KIND = 'v94-exynos-checked-ptpage-pc'
WORKFLOW = '.github/workflows/note10-exynos-checked-ptpage-pc.yml'
BINDING_SCHEMA = 'note10-v94-current-payload-host-transform-input-binding-v1'
RECEIPT_SCHEMA = 'note10-v94-revision1-ci-operator-receipt-v1'


def write_json(path, value):
    raw = (json.dumps(value, indent=2) + '\n').encode()
    with path.open('xb') as target:
        target.write(raw)
    return sha(raw)


def current_inputs(binding_path, binding_sha256):
    binding = pinned_json(binding_path, binding_sha256)
    require(binding.get('schema') == BINDING_SCHEMA, 'closed current input binding required')
    receipt = pinned_json(binding['accepted_ci_receipt_path'], binding['accepted_ci_receipt_sha256'])
    require(receipt.get('schema') == RECEIPT_SCHEMA, 'accepted v94 collection receipt required')
    workflow, accepted = receipt['workflow'], receipt['new_xnu_producer']
    source = receipt['source_binding']['project_source_commit']
    require(re.fullmatch('[0-9a-f]{40}', source or '') and
            workflow.get('head_sha') == source and workflow.get('conclusion') == 'success' and
            workflow.get('event') == 'workflow_dispatch' and workflow.get('workflow_path') == WORKFLOW and
            workflow.get('job_name') == 'current-native-selected-link' and
            all(type(workflow.get(k)) is int and workflow[k] > 0 for k in ('run_id', 'attempt')),
            'accepted current CI tuple differs')
    result_path = private(binding['producer_result_path'])
    require(result_path.name == 'result.json' and result_path == private(accepted['result_path']) and
            binding['producer_result_sha256_reused_from_accepted_receipt'] == accepted['result_sha256'],
            'current result path or receipt pin differs')
    context_path = result_path.parent / 'producer-context.json'
    require(context_path == private(binding['producer_context_path']), 'current context path differs')
    result = pinned_json(result_path, accepted['result_sha256'])
    context = pinned_json(context_path, binding['producer_context_sha256'])
    ci = dict(GITHUB_SHA=source, GITHUB_RUN_ID=str(workflow['run_id']),
        GITHUB_RUN_ATTEMPT=str(workflow['attempt']), GITHUB_JOB=workflow['job_name'],
        GITHUB_WORKFLOW_REF='eirblue/ios_note10p/' + WORKFLOW + '@refs/heads/main',
        GITHUB_WORKFLOW_SHA=source, GITHUB_REPOSITORY='eirblue/ios_note10p')
    producer, bindings = context['producer'], context['bindings']
    require(context.get('kind') == 'v84-current-native' and producer.get('candidate_kind') == KIND and
            result.get('kind') == KIND and accepted.get('kind') == KIND and
            result.get('phase') == accepted.get('phase') == 'complete' and
            result.get('passed') is accepted.get('passed') is True,
            'fresh v94 producer completion required')
    require(result.get('ci_context') == producer.get('ci_context') == ci and
            producer.get('source_commit') == source and
            result.get('public_source_commit') == producer.get('public_source_commit') ==
            receipt['source_binding']['underlying_public_xnu_commit'] and
            producer.get('configuration') == 'DEVELOPMENT_ARM64_EXYNOS9825' and
            type(producer.get('fresh_work_root')) is str and bool(producer['fresh_work_root']),
            'current source/run/configuration mismatch')
    require(context.get('producer_id') == result.get('producer_id') == accepted.get('producer_id') == digest(producer) and
            context.get('input_binding') == result.get('input_binding') == accepted.get('input_binding') == digest(bindings),
            'current producer/configuration binding differs')
    link = result['link']
    require(link.get('producer_id') == result['producer_id'] and link.get('input_binding') == result['input_binding'] and
            link.get('attempted') is True and link.get('link_succeeded') is True and
            type(link.get('returncode')) is int and link['returncode'] == 0 and
            link.get('candidate_archive_used') is result.get('candidate_archive_used') is False and
            not any(k in context for k in ('candidate_archive', 'historical_objects', 'platform_reports')),
            'successful direct current link required')
    require(result.get('architecture') == 'arm64' and result.get('mach_o_type') == 'MH_EXECUTE' and
            result.get('undefined_symbols') == [] and result.get('old_suites_executed') == 0 and
            result.get('PC_only') is True and result.get('physical_ready') is False and
            result.get('deployment_ready') is False and result.get('hardware_verified') is False and
            result.get('whole_XNU_kernel_entry_executed') is False and
            result.get('hardware_XNU_executed') is False and result.get('device_operations') == [],
            'host-only current intrinsic output required')
    require(result.get('output_bytes') == accepted.get('producer_declared_output_bytes') and
            result.get('output_sha256') == accepted.get('producer_declared_output_sha256') and
            all(result.get(k) == accepted.get(k) for k in ('memory_image_virtual_base',
                'memory_image_span_bytes', 'entry_virtual_address', 'entry_offset',
                'bootstrap_pool_relative_offset', 'bootstrap_pool')),
            'accepted intrinsic geometry differs')
    pins = receipt['source_binding']['test_source_component_pins']
    require(all(producer['recipe_sha256'].get(n) == pins[n] for n in
            ('exynos_checked_ptpage.c', 'prepare_exynos_checked_ptpage.py')) and
            producer['patch_sha256'].get('0013-exynos9825-checked-dynamic-ptpage.patch') ==
            pins['patches/0013-exynos9825-checked-dynamic-ptpage.patch'],
            'new allocator source recipe differs')
    return binding, receipt, result, context, result_path.parent / 'current-native.macho'


def pool_geometry(result):
    base, span = geometry(result)
    pool = result['bootstrap_pool']
    start, size = pool['address'], pool['bytes']
    data = [row for row in result['segments'] if row['name'] == '__DATA']
    require(len(data) == 1, 'one current DATA segment required')
    data = data[0]
    require(span <= 32 * 1024 * 1024 and base == int(result['memory_image_virtual_base'], 16) and
            span == result['memory_image_span_bytes'] and
            int(result['entry_virtual_address'], 16) - base == result['entry_offset'],
            'fresh aligned span or entry differs')
    require(all(type(v) is int for v in (start, size, pool['alignment_log2'], pool['flags'])) and
            pool['segment'] == '__DATA' and size == 10 * PAGE and start % PAGE == 0 and
            pool['alignment_log2'] >= 14 and pool['flags'] & 255 == 1 and
            pool['segment_protection'] == data['initial_protection'] == 3 and
            pool['segment_maximum_protection'] & 3 == 3 and
            pool['segment_start'] == data['virtual_address'] and
            pool['segment_end'] == data['virtual_address'] + data['virtual_size'] and
            data['virtual_address'] + data['file_size'] <= start < start + size <= pool['segment_end'] and
            base <= start < start + size <= base + span and
            start - base == result['bootstrap_pool_relative_offset'],
            'current pool is not wholly in declared DATA zero tail')
    return base, span, start - base, size


def historical_decoder(receipt_path, receipt_sha256):
    receipt_path = private(receipt_path)
    receipt = pinned_json(receipt_path, receipt_sha256)
    require(receipt.get('schema') == 'v87-host-operator-receipt-v1', 'accepted historical decoder receipt required')
    batch = receipt['selected_batch']
    test_path = private(receipt_path.parent / batch['result_path'])
    require(test_path.name == 'result.json', 'fixed historical test receipt required')
    tests = pinned_json(test_path, batch['result_sha256'])
    names = ['CurrentDataCarrierTests.' + n for n in carrier.CASE_NAMES]
    require(batch.get('selected_method_ids') == batch.get('passed_method_ids') == names and
            batch.get('failed_count') == 0 and batch.get('tests_run') == len(names) and
            tests.get('kind') == 'current-data-carrier-new-tests' and tests.get('success') is True and
            tests.get('selected') == tests.get('passed') == list(carrier.CASE_NAMES) and
            tests.get('failed') == [] and tests.get('tests_run') == len(names) and
            tests.get('fixture_compiles') == 1 and tests.get('source_sha256') == receipt['source_pins'],
            'historical accepted compile/source closure differs')
    compiled = tests['compiled']
    require(compiled.get('returncode') == 0 and compiled.get('dll_file') == 'carrier_lzma.dll' and
            compiled.get('dll_sha256') == receipt['compiler']['corrected_attempt']['dll_sha256'] and
            receipt['compiler'].get('successful_C_compilations') == 1,
            'accepted immutable DLL binding differs')
    # Old DLL/old source closure explicitly retained; do not claim the live kernel header was its input.
    decoder = carrier.Decoder(test_path.parent / compiled['dll_file'], compiled['dll_sha256'])
    return decoder, dict(kind='accepted-historical-v87-DLL',operator_receipt_sha256=receipt_sha256,
        test_result_sha256=batch['result_sha256'],source_sha256=receipt['source_pins'],compiled=compiled,
        live_header_is_not_compiled_input=True,old_tests_replayed=0,new_compiles=0)


def prepare(input_binding, *, input_binding_sha256, decoder_receipt, decoder_receipt_sha256, output):
    output = private(output)
    require(not output.exists(), 'fresh private output required')
    binding, receipt, result, context, kernel = current_inputs(input_binding, input_binding_sha256)
    require(not any(private(p).is_relative_to(output) for p in
        (input_binding, binding['accepted_ci_receipt_path'], binding['producer_result_path'],
         binding['producer_context_path'], kernel, decoder_receipt)), 'output must not contain inputs')
    base, span, pool, pool_bytes = pool_geometry(result)
    raw = bounded_read(kernel, carrier.MAX_BYTES)
    require(len(raw) == result['output_bytes'] and sha(raw) == result['output_sha256'],
            'fresh kernel bytes differ')
    actual_base, payload = materialize_kernel(raw, result['segments'])
    require(actual_base == base and len(payload) == span and not any(payload[pool:pool+pool_bytes]),
            'fresh load extent or zero-fill pool differs')
    compressed = lzma.compress(payload, format=lzma.FORMAT_ALONE, preset=6)
    require(0 < len(compressed) <= carrier.MAX_BYTES + 1024 * 1024, 'compressed output bound exceeded')
    fits = len(compressed) <= BUDGET - 128
    manifest = dict(schema=1, purpose='current-source-payload-preparation',
        current_producer_kind=KIND, producer_result_sha256=receipt['new_xnu_producer']['result_sha256'],
        producer_context_sha256=binding['producer_context_sha256'],ci_context=result['ci_context'],
        public_source_commit=result['public_source_commit'], producer_id=result['producer_id'],
        input_binding=result['input_binding'],source_macho_sha256=result['output_sha256'],source_macho_bytes=len(raw),
        virtual_base=hex(base),entry_virtual_address=result['entry_virtual_address'],entry_offset=result['entry_offset'],
        bootstrap_pool_relative_offset=pool,bootstrap_pool_bytes=pool_bytes,
        payload_file='kernel.mem',payload_bytes=len(payload),payload_sha256=sha(payload),
        compressed_file='kernel.mem.lzma',compressed_bytes=len(compressed),compressed_sha256=sha(compressed),
        compression=dict(format='LZMA_ALONE',preset=6,streams=1,padding_bytes=0),
        carrier_budget_bytes=BUDGET,fits_budget=fits,budget_delta_bytes=BUDGET-128-len(compressed),
        carrier_admitted=False,physical_reservation_verified=False,device_operations=[],xnu_executed=False,
        deployment_ready=False,PC_only=True,physical_ready=False,
        linux_current_capacity_bytes=OLD_LINUX_CAPACITY,linux_current_capacity_match=span==OLD_LINUX_CAPACITY)
    output.mkdir(parents=True,exist_ok=False)
    for name,data in (('kernel.mem',payload),('kernel.mem.lzma',compressed)):
        with (output/name).open('xb') as target:target.write(data)
    manifest_sha = write_json(output/'payload-fit.json',manifest)
    report = dict(kind='v95-fresh-current-payload-carrier-pc',accepted=False,
        input_binding_metadata_sha256=input_binding_sha256,payload_manifest_sha256=manifest_sha,
        payload_bytes=span,compressed_bytes=len(compressed),carrier_budget_bytes=BUDGET,fits_budget=fits,
        decoder_calls=0,PC_only=True,physical_ready=False,carrier_admitted=False,
        linux_current_capacity_match=span==OLD_LINUX_CAPACITY,
        whole_XNU_kernel_entry_executed=False,hardware_XNU_executed=False,device_operations=[])
    if fits:
        decoder = None
        try:
            decoder, compile_binding = historical_decoder(decoder_receipt, decoder_receipt_sha256)
            made = carrier.produce(output/'payload-fit.json',payload_manifest_sha256=manifest_sha,
                budget=BUDGET,output=output/'carrier',decoder=decoder,compile_binding=compile_binding)
            require(made['decoder_calls'] == 1 and made['decoded_bytes'] == span and
                    made['decoded_sha256'] == manifest['payload_sha256'], 'new functional decode differs')
            report.update(accepted=True,decoder_calls=made['decoder_calls'],
                carrier_bytes=made['carrier_bytes'],carrier_manifest='carrier/carrier-manifest.json',
                carrier_manifest_sha256=sha((json.dumps(made,indent=2)+'\n').encode()))
        except (ValueError, OSError, MemoryError) as error:
            report['decoder_calls'] = decoder.calls if decoder is not None else 0
            report['error'] = str(error)
            write_json(output/'fresh-payload-carrier.json',report)
            raise
    write_json(output/'fresh-payload-carrier.json',report)
    return report


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--input-binding',type=Path,required=True)
    p.add_argument('--input-binding-sha256',required=True)
    p.add_argument('--decoder-receipt',type=Path,required=True)
    p.add_argument('--decoder-receipt-sha256',required=True)
    p.add_argument('--output',type=Path,required=True)
    try:
        report=prepare(**vars(p.parse_args()))
    except (ValueError,OSError,MemoryError,KeyError,TypeError):
        print('fresh host payload production refused; private evidence retained')
        return 1
    print(json.dumps({k:report[k] for k in ('payload_bytes','compressed_bytes','carrier_budget_bytes',
        'fits_budget','decoder_calls','accepted','linux_current_capacity_match','physical_ready')}))
    return 0 if report['accepted'] else 2
if __name__=='__main__':raise SystemExit(main())
