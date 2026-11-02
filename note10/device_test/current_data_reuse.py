"""v97 host-only adapter: truthful old generic Linux evidence plus current DATA input.

No Image build, byte reader, actuator or payload transform. Root-selected receipt
SHA pins are offline trust anchors, not an independent CI verification.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re

ROOT=Path(__file__).resolve().parents[2]
IMAGE_HEAD='0696b4dbf157a2d51b68b26e4a5237a7c51daa80'
PAYLOAD_HEAD='ad4bc6b8f7cb1e7308de7e34474f25a0ec4bcf26'
MODE='v97-current-data-reuse-v91'
FIELD='data_current_binding_sha256'
MODE_FIELD='data_host_experiment'
RECORD='v97-current-data-reuse.json'


def require(condition,message):
    if not condition:raise ValueError(message)


def private(path):
    path=Path(path).absolute();root=(ROOT/'note10/private').resolve()
    require(path.resolve()==path and path!=root and path.is_relative_to(root) and
        not any(p.is_symlink() for p in (path,*path.parents)),'ordinary private path required')
    return path


def sha(raw):return hashlib.sha256(raw).hexdigest()


def pinned(path,expected):
    path=private(path)
    require(re.fullmatch('[0-9a-f]{64}',expected or '') and path.is_file() and
        0<path.stat().st_size<=2*1024*1024,'bounded pinned metadata required')
    raw=path.read_bytes();require(sha(raw)==expected,'accepted metadata pin differs')
    value=json.loads(raw.decode('utf-8-sig'));require(type(value) is dict,'metadata object required')
    return value


class ProducingSources:
    def __init__(self,linux_path,linux_sha,current_path,current_sha):
        self.linux_path=private(linux_path);self.linux_sha=linux_sha
        self.current_path=private(current_path);self.current_sha=current_sha
        self.receipt=pinned(self.linux_path,linux_sha)
        old=self.receipt
        require(old.get('schema')=='note10-v91-ci-operator-receipt-v1' and
            old['source'].get('commit')==IMAGE_HEAD and
            old['workflow'].get('head_sha')==IMAGE_HEAD and old['workflow'].get('run_id')==41404110966 and
            old['workflow'].get('attempt')==1 and old['workflow'].get('conclusion')=='success' and
            old['workflow'].get('job_name')=='linux-data-carrier', 'exact accepted historical Linux receipt required')
        original=private(old['original_artifact_and_extraction_directory'])
        require(original.name=='v91-linux-data-carrier-20261102','original historical evidence root required')
        self.producer=original/'evidence-v91-once/extracted-private-evidence/image-producer'
        accepted=old['image_producer'];self.result_sha=accepted['result_sha256']
        require(private(accepted['result_path'])==self.producer/'result.json','original producer location differs')
        result=pinned(self.producer/'result.json',self.result_sha)
        self.require_result(self.producer,self.result_sha,IMAGE_HEAD,result)
        self.pins=old['source']['observed_producer_source_sha256']
        from linux_data_carrier import SOURCES
        require(all(result['source_sha256'].get('note10/device_test/'+n)==self.pins.get('note10/device_test/'+n)
                    for n in SOURCES),'historical producing source record differs')
        self.carrier_path,self.carrier_sha,self.carrier_fields=self.current_carrier()
    def require_result(self,root,expected,source,result):
        accepted=self.receipt['image_producer'];ci=result.get('ci_context',{})
        require(expected==self.result_sha and source==IMAGE_HEAD and result.get('version')=='v91' and
            result.get('diagnostic_kind')=='linux-data-carrier' and result.get('passed') is True and
            result.get('Image_built') is True and result.get('BOOT_built') is False and
            result.get('PC_only') is not True and result.get('cycle_slot_patched') is False and
            result.get('image_expectation_patched') is False and
            result.get('data_expectation_mode')=='image-slot-logical-v2' and
            result.get('data_expectation_slot',{}).get('generic') is True and
            result.get('data_footprint',{}).get('data_state_bytes')==88 and
            ci.get('GITHUB_SHA')==IMAGE_HEAD and ci.get('GITHUB_RUN_ID')=='41404110966' and
            ci.get('GITHUB_RUN_ATTEMPT')=='1' and ci.get('GITHUB_JOB')=='linux-data-carrier' and
            result.get('image_sha256')==accepted.get('image_sha256') and
            result.get('image_bytes')==accepted.get('image_bytes') and
            result.get('build_evidence_id')==accepted.get('build_evidence_id'),
            'unmodified generic historical late-vmalloc Image required')
    def verify_sources(self,result,names):
        self.require_result(self.producer,self.result_sha,IMAGE_HEAD,result)
        for name in names:
            key='note10/device_test/'+name;path=private(self.producer/'source'/key)
            require(path.is_file() and 0<path.stat().st_size<=2*1024*1024 and
                result['source_sha256'].get(key)==self.pins.get(key)==sha(path.read_bytes()),
                'accepted historical producing source differs: '+name)
    def current_carrier(self):
        host=pinned(self.current_path,self.current_sha)
        require(host.get('schema')=='note10-v95-host-operator-receipt-v1','accepted current host receipt required')
        actual=host['actual_transform']
        require(actual.get('command_invocations')==1 and actual.get('exit_code')==0,'one accepted current transform required')
        made=pinned(actual['result_path'],actual['result_manifest_sha256'])
        fit=pinned(actual['fit_report_path'],actual['fit_report_sha256'])
        inputs=pinned(actual['input_binding_path'],actual['input_binding_sha256'])
        ctx=inputs['actual_producer_context'];producer=ctx['producer'];ci=fit.get('ci_context',{})
        require(made.get('kind')=='v95-fresh-current-payload-carrier-pc' and made.get('accepted') is True and
            made.get('decoder_calls')==1 and made.get('fits_budget') is True and fit.get('fits_budget') is True and
            made.get('payload_bytes')==fit.get('payload_bytes')==19136512 and
            made.get('payload_manifest_sha256')==actual['fit_report_sha256'] and
            made.get('input_binding_metadata_sha256')==actual['input_binding_sha256'] and
            fit.get('current_producer_kind')=='v94-exynos-checked-ptpage-pc' and
            ctx.get('kind')=='v84-current-native' and producer.get('candidate_kind')=='v94-exynos-checked-ptpage-pc' and
            ci==producer.get('ci_context') and ci.get('GITHUB_SHA')==producer.get('source_commit')==PAYLOAD_HEAD and
            fit.get('producer_id')==ctx.get('producer_id') and fit.get('input_binding')==ctx.get('input_binding') and
            fit.get('producer_context_sha256')==inputs.get('producer_context_sha256') and
            fit.get('producer_result_sha256')==inputs.get('producer_result_sha256_reused_from_accepted_receipt') and
            made.get('PC_only') is fit.get('PC_only') is True and
            made.get('physical_ready') is fit.get('physical_ready') is False,
            'accepted current payload subject/context differs')
        path=private(Path(actual['result_path']).parent/made['carrier_manifest'])
        require(path.name=='carrier-manifest.json','current carrier manifest path required')
        meta=pinned(path,made['carrier_manifest_sha256'])
        require(meta.get('purpose')=='fixed-data-carrier-host-preparation' and meta.get('accepted') is True and
            meta.get('decoder_calls')==1 and meta.get('payload_bytes')==19136512 and
            meta.get('payload_manifest_sha256')==actual['fit_report_sha256'] and
            meta.get('input_ci_context')==ci and meta.get('producer_id')==fit['producer_id'] and
            meta.get('input_binding')==fit['input_binding'] and meta.get('carrier_bytes')==10962166 and
            meta.get('carrier_admitted') is False and meta.get('deployment_ready') is False and
            meta.get('decoded_bytes')==meta['payload_bytes'] and meta.get('decode',{}).get('status')==0 and
            meta.get('decoded_sha256')==meta.get('payload_sha256')==fit.get('payload_sha256'),
            'current carrier proof differs')
        fields=dict(data_manifest_sha256=made['carrier_manifest_sha256'],data_carrier_sha256=meta['carrier_sha256'],
            data_carrier_bytes=meta['carrier_bytes'],data_payload_sha256=meta['payload_sha256'],data_payload_bytes=meta['payload_bytes'])
        return path,made['carrier_manifest_sha256'],fields
    def check_carrier(self,fields):
        require(all(fields.get(k)==v for k,v in self.carrier_fields.items()),'current carrier fields differ')
    def write_record(self,output,host_head):
        require(re.fullmatch('[0-9a-f]{40}',host_head or '') and host_head!=IMAGE_HEAD,
            'new host publication must remain distinct from old Linux producer')
        value=dict(schema=1,kind=MODE,host_source_head=host_head,
            linux_receipt=str(self.linux_path),linux_receipt_sha256=self.linux_sha,
            current_receipt=str(self.current_path),current_receipt_sha256=self.current_sha)
        raw=(json.dumps(value,sort_keys=True,indent=2)+'\n').encode()
        with (Path(output)/RECORD).open('xb') as target:target.write(raw)
        return {FIELD:sha(raw),MODE_FIELD:MODE}


def require_context(context):
    require(type(context) is ProducingSources,'exact historical producing-source adapter required')
    return context


def load_record(root,binding):
    require(binding.get(MODE_FIELD)==MODE and binding.get('source_head')==IMAGE_HEAD and
        binding.get('host_profile_source_head')!=IMAGE_HEAD,'closed new host experiment required')
    row=pinned(Path(root)/RECORD,binding[FIELD])
    require(set(row)=={'schema','kind','host_source_head','linux_receipt','linux_receipt_sha256',
        'current_receipt','current_receipt_sha256'} and row['schema']==1 and row['kind']==MODE and
        row['host_source_head']==binding['host_profile_source_head'],'current host receipt record differs')
    return ProducingSources(row['linux_receipt'],row['linux_receipt_sha256'],row['current_receipt'],row['current_receipt_sha256'])


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('build','output','linux-receipt','current-receipt','ci-success-context'):
        p.add_argument('--'+name,type=Path,required=True)
    for name in ('linux-receipt-sha256','current-receipt-sha256','ci-success-context-sha256','host-source-head'):
        p.add_argument('--'+name,required=True)
    a=p.parse_args();context=ProducingSources(a.linux_receipt,a.linux_receipt_sha256,a.current_receipt,a.current_receipt_sha256)
    require(private(a.build)==context.producer,'original generic producer is the only input route')
    from sha256_kat_device_profile import prepare_template
    report=prepare_template(a.build,a.output,context.result_sha,IMAGE_HEAD,
        host_source_head=a.host_source_head,ci_success_context=a.ci_success_context,
        ci_success_context_sha256=a.ci_success_context_sha256,carrier_manifest=context.carrier_path,
        carrier_manifest_sha256=context.carrier_sha,producing_sources=context)
    print(json.dumps(report,indent=2))
if __name__=='__main__':main()
