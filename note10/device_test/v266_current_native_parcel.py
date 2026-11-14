"""New266 native origin/one PC measurement; unchanged265 reader fit stays strict."""
import re
import native_payload_producer as core
from v261_current_native_parcel import require,sha,battery,observation,journal_id,ADAPTER_BYTES,ADAPTER_SHA
from v265_carrier_capacity import reader_fit,insert,SOURCE_CAP,KERNEL_CAP,RAW_CAP
STEM='note10-v266-genuine-block-driver'
def parcel(raw,producer,manifest,expected,materialize):
    keys={'source_head','run_id','run_attempt','kernel_sha256','kernel_bytes','producer_id','input_binding'}
    require(type(expected)is dict and set(expected)==keys and producer['schema']=='note10-v266-genuine-block-driver-build-v1'and manifest['schema']=='note10-v266-genuine-block-driver-native-handoff-build-v1','actual266 producer origin, no schema projection')
    require(producer['passed']is True and producer['media_instantiated']is producer['media_started']is producer['consumer_invoked']is producer['runtime_executed']is producer['physical_ready']is producer['native_activation']is producer['factory_invoked']is producer['provider_started']is producer['provider_registered']is False and producer['final_object_count']==1085,'unexecuted complete native candidate')
    require(producer['owned_ram_factory']==manifest['owned_ram_factory']and producer['owned_ram_factory']['passed']is True and producer['owned_ram_factory']['external_consumer_callers']==0 and producer['owned_ram_factory']['consumer_retained']is True and producer['owned_ram_factory']['consumer_invoked']is False and producer['owned_ram_factory']['local_factory_source_consumer']=='note10_attach_owned_readonly_ram_nub'and producer['owned_ram_factory']['local_factory_source_calls']==1,'retained factory provenance')
    media=producer['owned_ram_factory']['media'];require(media['object_provenance_verified']is media['class_retained']is True and media['instantiated']is media['started']is False and media['row']['source']=='@storage/IOMedia.cpp'and media['row']['source_sha256']=='38de6ac74dab48808261eed136137107a30a826e0845c9c5c6d039b53141da30','actual uninstantiated retained media origin')
    driver=producer['owned_ram_factory']['driver'];require(driver['passed']is driver['object_provenance_verified']is driver['retained_lock_export_addresses_verified']is True and driver['runtime_invoked']is False and len(driver['rows'])==5 and len(driver['roots'])==2,'genuine inert five-unit driver closure')
    require(re.fullmatch('[0-9a-f]{40}',expected['source_head'])and type(expected['run_id'])is int and expected['run_id']>0 and expected['run_attempt']==1,'new native source/run identity')
    for key in ('kernel_sha256','producer_id','input_binding'):core.hexadecimal(expected[key])
    require(all(producer[k]==expected[k]for k in ('source_head','run_id','run_attempt','kernel_sha256','kernel_bytes'))and all(manifest[k]==expected[v]for k,v in dict(source_commit='source_head',run_id='run_id',run_attempt='run_attempt',output_sha256='kernel_sha256',output_size='kernel_bytes',producer_id='producer_id',input_binding='input_binding').items()),'exact new native producer/manifest expectation')
    require(type(raw)is bytes and len(raw)==expected['kernel_bytes']and sha(raw)==expected['kernel_sha256'],'new native input SHA/extent')
    geometry=core.parse_kernel(raw);require(0<geometry['kernel_span']<=33554432,'bounded32MiB PC geometry before materialization');base,memory=materialize(raw,geometry['segments'])
    require(base==geometry['virtual_base']and type(memory)is bytes and len(memory)==geometry['kernel_span']and 0<len(memory)<=33554432,'new32MiB PC materialization; physical fit remains separate')
    memory_sha=sha(memory)
    fields=[geometry[k]for k in ('virtual_base','kernel_span','kernel_entry_offset','entry_extent_offset','entry_extent_bytes','pool_offset','pool_bytes')]+[ADAPTER_BYTES,0,256]
    descriptor=core.WIRE.pack(b'N209PAY1',1,256,*fields,bytes.fromhex(expected['kernel_sha256']),bytes.fromhex(memory_sha),bytes.fromhex(ADAPTER_SHA),bytes.fromhex(expected['producer_id']),bytes.fromhex(expected['input_binding']))
    metadata=dict(schema=STEM+'-source-parcel-v1',purpose='current-native-source-candidate',**expected,kernel_materialized_bytes=len(memory),kernel_materialized_sha256=memory_sha,adapter_bytes=ADAPTER_BYTES,adapter_sha256=ADAPTER_SHA,adapter_entry_offset=0,adapter_record_offset=256,descriptor_sha256=sha(descriptor),geometry={k:v for k,v in geometry.items()if k!='segments'},native_activation=False,physical_ready=False)
    return memory,descriptor,metadata


def retained_binding(received,progress,parcel,expected):
    require(all(received[k]is True for k in ('passed','authenticated','producer_passed','capture_passed','final_passed','candidate_usable'))and parcel['schema']==STEM+'-source-parcel-v1','actual new266 authenticated measurement')
    require(progress['completed']is progress['member_hash_complete']is True and progress['compressions']==1 and progress['member_bytes']==expected['member_bytes']and progress['member_sha256']==expected['member_sha256']and parcel['descriptor_sha256']==expected['descriptor_sha256']and parcel['kernel_materialized_bytes']==expected['kernel_span']and progress['uncompressed_newc_bytes']==expected['raw_newc_bytes'],'exact single completed new measurement')
    require(parcel['kernel_sha256']==received['members']['kernel/note10-experimental.macho']['sha256']and all(progress['inputs'][n]['EOF_verified']is progress['inputs'][n]['hash_complete']is True for n in ('kernel.mem','adapter.mem'))and progress['inputs']['kernel.mem']['sha256']==parcel['kernel_materialized_sha256'],'actual native/member/descriptor input join')
    return reader_fit(expected['kernel_span'],expected['member_bytes'],expected['raw_newc_bytes'])
