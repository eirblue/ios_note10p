"""v262 real origin binding; unchanged compiled-carrier primitives are retained."""
import re
import native_payload_producer as core
from v261_current_native_parcel import require,sha,reader_fit,insert,battery,observation,journal_id,SOURCE_CAP,KERNEL_CAP,RAW_CAP,ADAPTER_BYTES,ADAPTER_SHA
STEM='note10-v262-owned-ram-attach-start'

def parcel(raw,producer,manifest,expected,materialize):
    keys={'source_head','run_id','run_attempt','kernel_sha256','kernel_bytes','producer_id','input_binding'}
    require(type(expected)is dict and set(expected)==keys and producer['schema']=='note10-v262-owned-ram-attach-start-build-v1'and manifest['schema']=='note10-v262-owned-ram-attach-start-native-handoff-build-v1','actual261 producer origin, no schema projection')
    require(producer['passed']is True and producer['consumer_invoked']is producer['runtime_executed']is producer['physical_ready']is producer['native_activation']is producer['factory_invoked']is producer['provider_started']is producer['provider_registered']is False and producer['final_object_count']==1079,'unexecuted complete native candidate')
    require(producer['owned_ram_factory']==manifest['owned_ram_factory']and producer['owned_ram_factory']['passed']is True and producer['owned_ram_factory']['external_consumer_callers']==0 and producer['owned_ram_factory']['consumer_retained']is True and producer['owned_ram_factory']['consumer_invoked']is False and producer['owned_ram_factory']['local_factory_source_consumer']=='note10_attach_owned_readonly_ram_nub'and producer['owned_ram_factory']['local_factory_source_calls']==1,'retained factory provenance')
    require(re.fullmatch('[0-9a-f]{40}',expected['source_head'])and type(expected['run_id'])is int and expected['run_id']>0 and expected['run_attempt']==1,'new native source/run identity')
    for key in ('kernel_sha256','producer_id','input_binding'):core.hexadecimal(expected[key])
    require(all(producer[k]==expected[k]for k in ('source_head','run_id','run_attempt','kernel_sha256','kernel_bytes'))and all(manifest[k]==expected[v]for k,v in dict(source_commit='source_head',run_id='run_id',run_attempt='run_attempt',output_sha256='kernel_sha256',output_size='kernel_bytes',producer_id='producer_id',input_binding='input_binding').items()),'exact new native producer/manifest expectation')
    require(type(raw)is bytes and len(raw)==expected['kernel_bytes']and sha(raw)==expected['kernel_sha256'],'new native input SHA/extent')
    geometry=core.parse_kernel(raw);require(0<geometry['kernel_span']<=KERNEL_CAP,'authenticated geometry must fit before materialization');base,memory=materialize(raw,geometry['segments'])
    require(base==geometry['virtual_base']and type(memory)is bytes and len(memory)==geometry['kernel_span']and 0<len(memory)<=KERNEL_CAP,'new materialization fits compiled carrier span')
    memory_sha=sha(memory)
    fields=[geometry[k]for k in ('virtual_base','kernel_span','kernel_entry_offset','entry_extent_offset','entry_extent_bytes','pool_offset','pool_bytes')]+[ADAPTER_BYTES,0,256]
    descriptor=core.WIRE.pack(b'N209PAY1',1,256,*fields,bytes.fromhex(expected['kernel_sha256']),bytes.fromhex(memory_sha),bytes.fromhex(ADAPTER_SHA),bytes.fromhex(expected['producer_id']),bytes.fromhex(expected['input_binding']))
    metadata=dict(schema=STEM+'-source-parcel-v1',purpose='current-native-source-candidate',**expected,kernel_materialized_bytes=len(memory),kernel_materialized_sha256=memory_sha,adapter_bytes=ADAPTER_BYTES,adapter_sha256=ADAPTER_SHA,adapter_entry_offset=0,adapter_record_offset=256,descriptor_sha256=sha(descriptor),geometry={k:v for k,v in geometry.items()if k!='segments'},native_activation=False,physical_ready=False)
    return memory,descriptor,metadata

def candidate_identity(native,carrier,cycle):
    require(type(cycle)is str and re.fullmatch('[0-9a-f]{32}',cycle)and cycle!='0'*32,'fresh candidate cycle')
    require(native['schema']==STEM+'-source-parcel-v1'and carrier['producer_revision']=='v241'and native['source_head']!=carrier['source_head'],'separate new native and retained241 carrier')
    return dict(version='v262',candidate_id=sha((native['kernel_sha256']+native['descriptor_sha256']+cycle).encode()),native_source_head=native['source_head'],native_run_id=native['run_id'],carrier_source_head=carrier['source_head'],carrier_build_evidence_id=carrier['build_evidence_id'],carrier_revision='v241',carrier_runtime_recompiled=False,cycle=cycle)
