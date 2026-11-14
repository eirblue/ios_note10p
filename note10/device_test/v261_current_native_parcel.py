"""New native origin and the unchanged241 compiled-reader boundary, no device I/O."""
import hashlib
import re
import struct
import native_payload_producer as core

STEM='note10-v261-owned-ram-integrated'
SOURCE_CAP=6209536
KERNEL_CAP=19169280
RAW_CAP=19186176
ADAPTER_BYTES=16384
ADAPTER_SHA='7489548da8b08b5846b5baa5f77fc5857b9bd5661cc33b17a2c7e064618872a8'


def require(ok,message):
    if not ok:raise ValueError(message)


def sha(raw):return hashlib.sha256(raw).hexdigest()


def reader_fit(kernel_span,member_bytes,raw_bytes):
    require(all(type(x)is int for x in (kernel_span,member_bytes,raw_bytes))and 0<kernel_span<=KERNEL_CAP and kernel_span%16384==0 and 18<=member_bytes<=SOURCE_CAP-96 and raw_bytes==((kernel_span+ADAPTER_BYTES+496+511)&~511)and raw_bytes<=RAW_CAP,'actual241 compiled native stream limits')
    return dict(kernel_span=kernel_span,adapter_bytes=ADAPTER_BYTES,member_bytes=member_bytes,raw_newc_bytes=raw_bytes,source_holder_bytes=SOURCE_CAP,source_zero_tail_bytes=SOURCE_CAP-96-member_bytes,compiled_reader_fit=True)


def parcel(raw,producer,manifest,expected,materialize):
    keys={'source_head','run_id','run_attempt','kernel_sha256','kernel_bytes','producer_id','input_binding'}
    require(type(expected)is dict and set(expected)==keys and producer['schema']=='note10-v261-owned-ram-integrated-build-v1'and manifest['schema']=='note10-v261-owned-ram-factory-native-handoff-build-v1','actual261 producer origin, no schema projection')
    require(producer['passed']is True and producer['runtime_executed']is producer['physical_ready']is producer['native_activation']is producer['factory_invoked']is producer['provider_started']is producer['provider_registered']is False and producer['final_object_count']==1079,'unexecuted complete native candidate')
    require(producer['owned_ram_factory']==manifest['owned_ram_factory']and producer['owned_ram_factory']['passed']is True and producer['owned_ram_factory']['compiled_callers']==0,'retained factory provenance')
    require(re.fullmatch('[0-9a-f]{40}',expected['source_head'])and type(expected['run_id'])is int and expected['run_id']>0 and expected['run_attempt']==1,'new native source/run identity')
    for key in ('kernel_sha256','producer_id','input_binding'):core.hexadecimal(expected[key])
    require(all(producer[k]==expected[k]for k in ('source_head','run_id','run_attempt','kernel_sha256','kernel_bytes'))and all(manifest[k]==expected[v]for k,v in dict(source_commit='source_head',run_id='run_id',run_attempt='run_attempt',output_sha256='kernel_sha256',output_size='kernel_bytes',producer_id='producer_id',input_binding='input_binding').items()),'exact new native producer/manifest expectation')
    require(type(raw)is bytes and len(raw)==expected['kernel_bytes']and sha(raw)==expected['kernel_sha256'],'new native input SHA/extent')
    geometry=core.parse_kernel(raw);base,memory=materialize(raw,geometry['segments'])
    require(base==geometry['virtual_base']and type(memory)is bytes and len(memory)==geometry['kernel_span']and 0<len(memory)<=KERNEL_CAP,'new materialization fits compiled carrier span')
    memory_sha=sha(memory)
    fields=[geometry[k]for k in ('virtual_base','kernel_span','kernel_entry_offset','entry_extent_offset','entry_extent_bytes','pool_offset','pool_bytes')]+[ADAPTER_BYTES,0,256]
    descriptor=core.WIRE.pack(b'N209PAY1',1,256,*fields,bytes.fromhex(expected['kernel_sha256']),bytes.fromhex(memory_sha),bytes.fromhex(ADAPTER_SHA),bytes.fromhex(expected['producer_id']),bytes.fromhex(expected['input_binding']))
    metadata=dict(schema=STEM+'-source-parcel-v1',purpose='current-native-source-candidate',**expected,kernel_materialized_bytes=len(memory),kernel_materialized_sha256=memory_sha,adapter_bytes=ADAPTER_BYTES,adapter_sha256=ADAPTER_SHA,adapter_entry_offset=0,adapter_record_offset=256,descriptor_sha256=sha(descriptor),geometry={k:v for k,v in geometry.items()if k!='segments'},native_activation=False,physical_ready=False)
    return memory,descriptor,metadata


def candidate_identity(native,carrier,cycle):
    require(type(cycle)is str and re.fullmatch('[0-9a-f]{32}',cycle)and cycle!='0'*32,'fresh candidate cycle')
    require(native['schema']==STEM+'-source-parcel-v1'and carrier['producer_revision']=='v241'and native['source_head']!=carrier['source_head'],'separate new native and retained241 carrier')
    return dict(version='v261',candidate_id=sha((native['kernel_sha256']+native['descriptor_sha256']+cycle).encode()),native_source_head=native['source_head'],native_run_id=native['run_id'],carrier_source_head=carrier['source_head'],carrier_build_evidence_id=carrier['build_evidence_id'],carrier_revision='v241',carrier_runtime_recompiled=False,cycle=cycle)


def insert(image,build,descriptor,member,member_sha,cycle,fit,private_member):
    require(type(image)is bytes and type(descriptor)is bytes and len(descriptor)==256 and type(member)is bytes and member[:4]==b'\x1f\x8b\x08\x00'and sha(member)==member_sha,'actual new descriptor/member')
    span=struct.unpack_from('<Q',descriptor,24)[0]
    require(reader_fit(span,len(member),fit['raw_newc_bytes'])==fit,'measured current member fit')
    meta,size,marker,source,capacity=(build[k]for k in ('slot_offset','slot_bytes','cycle_offset','source_holder_offset','source_holder_bytes'))
    require(all(type(x)is int for x in (meta,size,marker,source,capacity))and size==4096 and capacity==SOURCE_CAP and all(64<=a and a+z<=len(image)for a,z in ((meta,size),(marker,33),(source,capacity))),'fixed241 insertion geometry')
    intervals=sorted(((meta,meta+size),(source,source+capacity),(marker,marker+33)))
    require(all(a[1]<=b[0]for a,b in zip(intervals,intervals[1:]))and not any(image[meta:meta+size])and not any(image[source:source+capacity]),'disjoint original zero carrier slots')
    require(re.fullmatch('[0-9a-f]{32}',cycle)and image[marker:marker+33]==b'N10_CYCLE_SLOT_UNSET_0123456789A'+b'\0'and image.count(b'N10_CYCLE_SLOT_UNSET_0123456789A'+b'\0')==1,'original cycle placeholder')
    metadata,binding=private_member(descriptor,build['build_evidence_id'],cycle)
    require(len(metadata)<=4096 and len(binding)==128,'existing metadata/binding ABI')
    header=struct.pack('<8sIIQQ32s32s',b'N226SRC1',1,96,len(member),fit['raw_newc_bytes'],bytes.fromhex(member_sha),bytes.fromhex(sha(descriptor)))
    changed=bytearray(image);changed[meta:meta+size]=metadata+bytes(size-len(metadata));changed[source:source+capacity]=header+member+bytes(capacity-96-len(member));changed[marker:marker+32]=cycle.encode()
    return bytes(changed),binding


def battery(raw):
    require(type(raw)is bytes and len(raw)<=128,'bounded raw battery value');working=raw.replace(b'\r\n',b'\n').strip();require(re.fullmatch(rb'[0-9]{1,3}',working),'raw capacity integer');value=int(working);require(10<=value<=100,'fresh battery10 gate');return value


def observation(row,identity,metadata):
    require(metadata['descriptor_sha256']==identity['descriptor_sha256']and metadata['kernel_materialized_sha256']==identity['materialized_sha256']and row['build']==identity['carrier_build_evidence_id']and row['cycle']==identity['cycle']and row['copied_kernel']==metadata['kernel_materialized_bytes']and row['copied_adapter']==ADAPTER_BYTES and row['native_source']==row['destination_hash_verified']==1 and row['XNU']==0,'fresh261 dynamic inert source observation')
    return dict(ingested_new_native_data=True,factory_invoked=False,native_activation=False,physical_ready=False)


def journal_id(identity):
    value=identity['build_evidence_id']
    require(type(value)is str and re.fullmatch('[0-9a-f]{32}',value)and value==identity['candidate_id'][:32]and value!=identity['carrier_build_evidence_id'],'new261 candidate journal, never reused carrier journal')
    return value
