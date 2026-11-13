"""240 guarded CPU/node compile candidate; no package or device executor."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import uuid
import zipfile
import v238_native_prepare as base
import v238_of_frame_property as of_calls
import v232_cpu_stack_provenance as cpu_provenance
import re
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
WORKFLOW='.github/workflows/note10-v240-native-prepare.yml'
JOB='v240-native-prepare'
BUILD_SCHEMA='note10-v240-current-metadata-prepare-build-v1'
CONTEXT_SCHEMA='note10-v240-current-metadata-prepare-public-input-v1'
MANIFEST_SCHEMA='note10-v240-current-metadata-prepare-sealed-members-v1'
FIXTURE_SCHEMA='note10-v240-guarded-query-fixture-result-v1'
PUBLIC_NEW=('v240_guarded_query.h','v240_guarded_query.c','v240_guarded_query_fixture.c','test_v240_guarded_query.py','v240_native_prepare.py')
FROZEN239_MAP_SHA256='bbec22047ec7d2828b2bdde0851d153bd8eb6fbdd398f88627a88db6495587da'
CARRIED239_FIXTURE_PASS={'schema': 'note10-v239-query-admission-fixture-result-v1', 'passed': True, 'groups': 1, 'variants': 38, 'assertions': 38, 'analysis_source_head': 'ea98e42dcd635b4d9473b9a36ef03ed15e03c519', 'target_source_head': 'ddeb90b4da7f5fb75a95ff44586f918bebc1a2d0', 'target_CI_run': 43389733142, 'result_sha256': '790f5691d4469255974960937f7a641baa9ccfa9c62cd32046a6a1a5ddae4eec'}
CARRIED239_CONDITIONAL_PROOF={'schema': 'note10-v239-conditional-query-proof-result-v1', 'passed': True, 'analysis_source_head': 'ea98e42dcd635b4d9473b9a36ef03ed15e03c519', 'target_source_head': 'ddeb90b4da7f5fb75a95ff44586f918bebc1a2d0', 'target_CI_run': 43389733142, 'conditional_node_query_bound_bytes': 576, 'result_sha256': 'b49dea00354d77ba27fff242854b856dcae46c3387cc7f5b7d6e6f250ecc68c9', 'runtime_hook_allowed': False, 'CI_dispatches': 0}
CARRIED237_FIXTURE_PASS={'schema': 'note10-v237-selected-OF-evidence-fixture-result-v1', 'passed': True, 'groups': 1, 'variants': 27, 'assertions': 27, 'source_head': '34077a5a6d950423e6da80a86aceb7b7110fe826', 'result_sha256': '856727f4d830581a018ad6b43629a4208a86e91a455dfb2dda8ed3b91a8d7745'}
CARRIED237_CI_PASS={'schema': 'note10-v237-carried-full-Image-CI-PASS-v1', 'source_head': '34077a5a6d950423e6da80a86aceb7b7110fe826', 'run_id': 43383243638, 'result_sha256': '92dc966892dfe11763bfa0970110649e44e57e1f3604fa113d07cd846f6c1a47', 'receive_sha256': 'f51dd4c80599dbe9bf6ce7767a38d5dca6b16be83fc64a7d8011c0a0dc5e60a9', 'full_Image_build_attempts': 1, 'target_PID1_compile_links': 1, 'hardware_authorized': False}
CARRIED236_FIXTURE_PASS={'schema': 'note10-v236-selected-OF-evidence-fixture-result-v1', 'passed': True, 'groups': 1, 'variants': 10, 'assertions': 10, 'source_head': 'f4d19c91f93a84b9cb8a117185ee048d70fc1978', 'result_sha256': 'a7df0ec950eba563ac747a499880adef5d9ce081ece87ef3a8efd34827e1d5c3'}
CARRIED236_CI_PASS={'schema': 'note10-v236-carried-full-Image-CI-PASS-v1', 'source_head': 'f4d19c91f93a84b9cb8a117185ee048d70fc1978', 'run_id': 43376405098, 'result_sha256': 'e19560659d20cf007989fd0fdd27ab70f76acf3c005ade6b2fe2154d4ea8b12b', 'receive_sha256': 'adbe368aed703d6de78b57a6cd5bb509564ff3dcbf9f310dddb1afa14319aafa', 'full_Image_build_attempts': 1, 'target_PID1_compile_links': 1, 'hardware_authorized': False}
CARRIED235_FIXTURE_PASS={'schema': 'note10-v235-selected-OF-evidence-fixture-result-v1', 'passed': True, 'groups': 1, 'variants': 29, 'assertions': 29, 'source_head': '37a5dd14faae708ed6de9ca232d93bcafcd43b6f', 'result_sha256': 'f8e4a8196a62a188e4bdbcd3de16f8316c7cec8bf6a2a22eb23f71946d10437e'}
CARRIED235_PRE_DISPATCH_HOLD={'schema': 'note10-v235-carried-pre-dispatch-hold-v1', 'source_head': '37a5dd14faae708ed6de9ca232d93bcafcd43b6f', 'terminal_sha256': '99db799eda8c64d0f173c7c346524703ef4319bd78ce171c9bff7b5ac650a82d', 'fixture_passed': True, 'fixture_assertions': 29, 'target_nm_parser_executed': False, 'source_publications': 0, 'CI_dispatches': 0, 'no_retry': True}
CARRIED234_FIXTURE_PASS={'schema': 'note10-v234-cpu-node-fixture-binding-result-v1', 'passed': True, 'groups': 1, 'variants': 41, 'assertions': 157, 'source_head': '45a3f6b59dbb4ecf8217abd0bf628f8b8a9e380b', 'result_sha256': 'ed695b1c9ddb7b7b59fc493ac00eb8ecc01ef06f2f8d73068b6733824fad7e65'}
CARRIED234_CI_PASS={'schema': 'note10-v234-carried-full-Image-CI-PASS-v1', 'source_head': '45a3f6b59dbb4ecf8217abd0bf628f8b8a9e380b', 'run_id': 43368238622, 'result_sha256': 'a3306c4d5175f18d5d35bd4273ce97c5363b0f86bfe32689451005eb4f5a1c45', 'receive_sha256': 'd0e0f39f01253f3d47eb1c9d7f641f6176f0c68e3ec2f92a5852b2aaca38ddf7', 'full_Image_build_attempts': 1, 'target_PID1_compile_links': 1, 'hardware_authorized': False}
CARRIED238_FIXTURE_PASS={'schema': 'note10-v238-selected-OF-evidence-fixture-result-v1', 'passed': True, 'groups': 1, 'variants': 38, 'assertions': 38, 'source_head': 'ddeb90b4da7f5fb75a95ff44586f918bebc1a2d0', 'result_sha256': 'f329f2c80739c8785178b1fd2b9fab68c76a73b0b5cf8537477a14f2e055016b'}
FAILED233_FIXTURE=base.FAILED233_FIXTURE
p=base.p
stream_candidate=base.stream_candidate
leaf_capture=base.leaf_capture
house=base.house
archive_helper=base.archive_helper
footprint=base.footprint
tcs_guard=base.tcs_guard
require=base.require
sha=base.sha
private_member=base.private_member
inspect_pid1=base.inspect_pid1
generic=base.generic
insert_private=base.insert_private
stack_sidecar_relative=base.stack_sidecar_relative
RETAINED211_PARSER_PASS=base.RETAINED211_PARSER_PASS
FALSE_CLAIMS=base.FALSE_CLAIMS
owner=base.owner
BASELINE212_IMAGE_BYTES=base.BASELINE212_IMAGE_BYTES
BASELINE212_LINKED_BYTES=base.BASELINE212_LINKED_BYTES
BASELINE208_IMAGE_BYTES=base.BASELINE208_IMAGE_BYTES
BASELINE208_LINKED_BYTES=base.BASELINE208_LINKED_BYTES
state_overlay=base.state_overlay
METADATA_OBJECTS=base.METADATA_OBJECTS
METADATA_ABS=base.METADATA_ABS
metadata_symbols=base.metadata_symbols
metadata_object_evidence=base.metadata_object_evidence
KERNEL_SOURCE_SHA=base.KERNEL_SOURCE_SHA
KERNEL_POST_SHA=base.KERNEL_POST_SHA
PREPARE_SOURCE_SHA=base.PREPARE_SOURCE_SHA
PREPARE_POST_SHA=base.PREPARE_POST_SHA
CPU_CONFIG=base.CPU_CONFIG
CPU_HEADERS=base.CPU_HEADERS
observation_target=base.observation_target
NODE_CONFIG=base.NODE_CONFIG
NODE_ABS=base.NODE_ABS
NODE_FUNCTIONS=base.NODE_FUNCTIONS
NODE_SOURCE_GUARDS=base.NODE_SOURCE_GUARDS
OWNER_PRE_SHA=base.OWNER_PRE_SHA
FROZEN232_MAP_SHA256=base.FROZEN232_MAP_SHA256
node_config=base.node_config
SLOT_BYTES=base.SLOT_BYTES
PID1_CAP=base.PID1_CAP
encode_context_wire=base.encode_context_wire
decode_context_wire=base.decode_context_wire
CARRIED220_FIXTURE_PASS=base.CARRIED220_FIXTURE_PASS
CARRIED221_FIXTURE_PASS=base.CARRIED221_FIXTURE_PASS
CARRIED222_FIXTURE_PASS=base.CARRIED222_FIXTURE_PASS
CARRIED223_FIXTURE_PASS=base.CARRIED223_FIXTURE_PASS
CARRIED224_FIXTURE_PASS=base.CARRIED224_FIXTURE_PASS
CARRIED225_FIXTURE_PASS=base.CARRIED225_FIXTURE_PASS
CARRIED227_FIXTURE_PASS=base.CARRIED227_FIXTURE_PASS
CARRIED228_FIXTURE_PASS=base.CARRIED228_FIXTURE_PASS
CARRIED229_FIXTURE_PASS=base.CARRIED229_FIXTURE_PASS
CARRIED230_FIXTURE_PASS=base.CARRIED230_FIXTURE_PASS
CARRIED231_FIXTURE_PASS=base.CARRIED231_FIXTURE_PASS
CARRIED232_FIXTURE_PASS=base.CARRIED232_FIXTURE_PASS
CARRIED226_PARTIAL_PYTHON=base.CARRIED226_PARTIAL_PYTHON
CARRIED230_CI_PASS=base.CARRIED230_CI_PASS
CARRIED232_CI_PASS=base.CARRIED232_CI_PASS
SUCCESS_MEMBERS=(*base.SUCCESS_MEMBERS,'guarded-query-evidence.json')



STREAM_BEFORE='1feb713fd9bcafd784a06d03859a6a5686c3adeeb5a4d5ed489c10cdcccaff4a'
STORE_BEFORE='5413f7953e04ccd996c2a4f47dddea241fef34f57e0e5dd7755cf9c16d3cc9e7'
MAIN_BEFORE='319ce4da8f622fe017b75f8381234d495487c13f2d59a1a6db0d633f020ba97b'
QUERY_FUNCTIONS=('n240_observe_current_cpu','n240_invalidate_observations','n240_clear_receipt','n240_room','n240_layout_witness')
QUERY_CAPTURE=(*QUERY_FUNCTIONS,'n231_capture_cpu_observation','n231_clear_observation','n226_ingest_prepared_locked','n226_stack_room','n210_write')
QUERY_ABS={'n240_size_query':56,'n240_align_query':8,'n240_pre_room_offset':40}


def prepare_stream(raw,expected=STREAM_BEFORE):
    require(type(raw)is bytes and sha(raw)==expected,'exact fresh231 stream preimage required')
    old=b'    error=n231_capture_cpu_observation((struct n231_cpu_observation *)(n226_source_pool+N231_POOL_OFFSET));\n    if(error)goto early;\n'
    new=b'    error=n240_observe_current_cpu((struct n231_cpu_observation *)(n226_source_pool+N231_POOL_OFFSET),\n        (struct n233_cpu_node_consistency *)(n226_source_pool+N233_POOL_OFFSET),\n        (struct n240_query_receipt *)(n226_source_pool+N240_POOL_OFFSET));\n    if(error)goto early;\n'
    header=b'#include "v231_cpu_observation.h"\n'
    clear=b'    if(error)memset(n226_source_pool+N231_POOL_OFFSET,0,sizeof(struct n231_cpu_observation));\n'
    replacement=b'    if(error)n240_invalidate_observations((struct n231_cpu_observation *)(n226_source_pool+N231_POOL_OFFSET),\n        (struct n233_cpu_node_consistency *)(n226_source_pool+N233_POOL_OFFSET),\n        (struct n240_query_receipt *)(n226_source_pool+N240_POOL_OFFSET),error);\n'
    require(raw.count(old)==raw.count(header)==raw.count(clear)==1 and b'n240_'not in raw,'one new caller and final-clear seam required')
    changed=raw.replace(header,header+b'#include "v240_guarded_query.h"\n',1).replace(old,new,1).replace(clear,replacement,1)
    return changed.replace(b'Capture/put_cpu and possible scheduling have returned',b'Guarded capture/query/outer put_cpu have returned',1)


def prepare_main(raw,expected=MAIN_BEFORE):
    anchor=b'#include "v233_cpu_node_consistency.c"\n'
    require(type(raw)is bytes and sha(raw)==expected and raw.count(anchor)==1 and b'v240_'not in raw,'exact fresh233 owner include boundary required')
    return raw.replace(anchor,anchor+b'#include "v240_guarded_query.c"\n',1)


def prepare_store(raw,expected=STORE_BEFORE):
    declaration=b'static __always_inline void n231_emit(int);\n';emit=b'n226_emit(error);n231_emit(error);'
    require(type(raw)is bytes and sha(raw)==expected and raw.count(declaration)==raw.count(emit)==1 and b'n240_'not in raw,'exact outer logger seam required')
    return raw.replace(declaration,declaration+b'static __always_inline void n240_emit(int);\n',1).replace(emit,emit+b'n240_emit(error);',1)


def install(source,identity,buffers,parser_sha):
    result=base.install(source,identity,buffers,parser_sha)
    records={}
    for name,transform in (('init.c',prepare_main),('v226_source_stream_kernel.c',prepare_stream),('v210_native_prepare_kernel.c',prepare_store)):
        path=source/'arch/arm64/mm'/name;before=p.ordinary(path);after=transform(before);path.write_bytes(after)
        require(p.ordinary(path)==after,'exact new compiler input write required');records[name]=dict(before_sha256=sha(before),after_sha256=sha(after))
    for name in ('v240_guarded_query.h','v240_guarded_query.c'):
        path=source/'arch/arm64/mm'/name;require(not path.exists(),'fresh guarded query source required');path.write_bytes(buffers['note10/device_test/'+name])
    result['guarded_query_overlay']=dict(schema='note10-v240-guarded-query-overlay-v1',source_sha256={name:sha(buffers['note10/device_test/'+name])for name in ('v240_guarded_query.h','v240_guarded_query.c')},
        compiler_inputs=records,compiled_capture_callers=1,compiled_node_callers=1,pool_offset=43608,record_bytes=56,new_pool_bytes=0,
        one_owned_get_put=True,both_records_cleared_on_later_failure=True,logger_after_provider_unwind=True,public_source_mutated=False,fresh_overlay_transformed=True,
        runtime_observed=False,hardware_authorized=False,requires_fresh_direct_physical_consent=True)
    return result


def fixture_command(output,compiler):
    return [compiler,'-std=c11','-O2','-Wall','-Wextra','-Werror','-DN240_HOST_FIXTURE','-I',str(HERE),str(HERE/'v240_guarded_query.c'),str(HERE/'v240_guarded_query_fixture.c'),'-o',str(Path(output)/'guarded-query-fixture.exe')]


def node_target(symbols,usage,sections,command):
    tu=cpu_provenance.owner_tu(command);rows=[x.split()for x in symbols.splitlines()if x.strip()]
    def one(name):
        found=[x for x in rows if x[0]==name];require(len(found)==1,'one actual233 symbol required: '+name);return found[0]
    for name,value in NODE_ABS.items():
        row=one(name);require(len(row)==3 and row[1]=='A'and int(row[2],16)==value,'computed233 ABS layout required')
    pool,slot=one('n226_source_pool'),one('n233_node_storage')
    require(len(pool)==len(slot)==4 and pool[1]in('b','B')and slot[1]=='B'and int(pool[3],16)==49152 and int(slot[3],16)==32 and
        int(slot[2],16)==int(pool[2],16)+43576,'new233 alias must fit unchanged existing pool')
    require({x[0]for x in rows if x[0].startswith('n233_')}==set(NODE_ABS)|set(NODE_FUNCTIONS)|{'n233_node_storage'},'no undeclared233 data/function symbols')
    frames=stream_candidate.frames(usage);require({k for k in frames if k.startswith('n233_')}==set(NODE_FUNCTIONS),'exact known233 frames required')
    selected={k:frames[k]for k in NODE_FUNCTIONS};require(all(v['source']==tu['translation_unit']and v['kind']=='static'for v in selected.values()),'same actual owner TU/static233 frames required')
    elf=[];objects=[]
    for line in sections.splitlines():
        match=re.match(r'^\s*\d+:\s+([0-9a-fA-F]+)\s+(\d+|0x[0-9a-fA-F]+)\s+(FUNC|OBJECT)\s+(LOCAL|GLOBAL)\s+DEFAULT\s+(\d+)\s+(\S+)\s*$',line)
        if match:elf.append(match.groups())
    provenance={}
    for name in NODE_FUNCTIONS:
        nm=one(name);binding='GLOBAL'if name=='n233_capture_cpu_node_consistency'else'LOCAL';found=[x for x in elf if x[-1]==name]
        require(len(found)==1 and len(nm)==4 and nm[1]==('T'if binding=='GLOBAL'else't'),'exact233 nm function binding required')
        address,size,kind,actual,index,_=found[0];size=int(size,16 if size.startswith('0x')else 10)
        require(kind=='FUNC'and actual==binding and int(address,16)==int(nm[2],16)and size==int(nm[3],16)>0,'same-owner233 nm/ELF function extent required')
        provenance[name]=dict(address=int(address,16),bytes=size,binding=actual,section_index=int(index))
    for name in ('n226_source_pool','n233_node_storage'):
        found=[x for x in elf if x[-1]==name];nm=one(name);require(len(found)==1,'one actual pool/alias ELF object required')
        address,size,kind,binding,index,_=found[0]
        require(kind=='OBJECT'and int(address,16)==int(nm[2],16)and int(size,16 if size.startswith('0x')else 10)==int(nm[3],16),'same pool/alias ELF object extent required');objects.append(index)
    require(objects[0]==objects[1],'233 alias must share actual pool section')
    return dict(schema='note10-v233-cpu-node-target-v1',ABS=NODE_ABS,pool_offset=43576,record_bytes=32,new_pool_bytes=0,
        named_new_storage_is_alias=True,new233_allocated_writable_bytes=0,whole_owner_writable_bytes_claimed=False,runtime_callers=1,runtime_observed=False,
        frames=selected,noninit_functions=stream_candidate.noninit_functions(sections,set(NODE_FUNCTIONS)),
        owner_TU_provenance=dict(**tu,symbol_provenance=provenance,nm_sha256=sha(symbols.encode()),ELF_sha256=sha(sections.encode()),SU_sha256=sha(usage.encode())),
        whole_OF_or_scheduler_stack_bound_proven=False,FDT_bound=False,authoritative_ADT=False,post_shutdown=False)



def query_target(symbols,usage,sections,command,linked):
    tu=cpu_provenance.owner_tu(command);rows=[line.split()for line in symbols.splitlines()if line.strip()]
    def one(name):
        found=[row for row in rows if row[0]==name];require(len(found)==1,'one new guarded-query symbol required: '+name);return found[0]
    for name,value in QUERY_ABS.items():
        row=one(name);require(len(row)==3 and row[1]=='A'and int(row[2],16)==value,'computed query56 ABI required')
    pool,slot=one('n226_source_pool'),one('n240_query_storage')
    require(len(pool)==len(slot)==4 and pool[1]in ('b','B')and slot[1]=='B'and int(pool[3],16)==49152 and int(slot[3],16)==56 and
        int(slot[2],16)==int(pool[2],16)+43608,'one56 alias inside existing pool required')
    require({row[0]for row in rows if row[0].startswith('n240_')}==set(QUERY_ABS)|set(QUERY_FUNCTIONS)|{'n240_query_storage'},'no undeclared query globals/functions')
    frames=stream_candidate.frames(usage);require({name for name in frames if name.startswith('n240_')}==set(QUERY_FUNCTIONS),'inline logger and exact query frame set required')
    table=of_calls.p.linked_symbols(linked);functions={};objects={}
    for line in sections.splitlines():
        match=re.match(r'^\s*\d+:\s+([0-9a-fA-F]+)\s+(\d+|0x[0-9a-fA-F]+)\s+(FUNC|OBJECT)\s+(LOCAL|GLOBAL)\s+DEFAULT\s+(\d+)\s+(\S+)\s*$',line)
        if match:
            address,size,kind,binding,index,name=match.groups()
            if name in (*QUERY_CAPTURE,'n226_source_pool','n240_query_storage'):
                target=functions if kind=='FUNC'else objects;require(name not in target,'one actual owner ELF query record required')
                target[name]=dict(address=int(address,16),bytes=int(size,16 if size.startswith('0x')else 10),binding=binding,section_index=index)
    selected={};provenance={}
    for name in QUERY_CAPTURE:
        row=one(name);require(name in frames and name in functions and name in table and len(table[name])==1,'actual owner/frame/linked query function required: '+name)
        frame=frames[name];elf=functions[name];link=table[name][0]
        require(frame['source']==tu['translation_unit']and frame['kind']=='static'and 0<=frame['bytes']<=8192 and len(row)==4 and row[1]in ('T','t')and
            elf['address']==int(row[2],16)and elf['bytes']==int(row[3],16)==link['bytes']>0 and elf['binding']==('GLOBAL'if row[1]=='T'else'LOCAL'),
            'literal owner TU/static frame and object/linked size binding required')
        selected[name]=frame;provenance[name]=dict(**elf,linked_address=link['address'],linked_kind=link['kind'])
    require(set(objects)=={'n226_source_pool','n240_query_storage'}and objects['n226_source_pool']['section_index']==objects['n240_query_storage']['section_index']and
        objects['n240_query_storage']['bytes']==56 and objects['n240_query_storage']['address']==objects['n226_source_pool']['address']+43608,'actual same-section query alias required')
    total=sum(row['bytes']for row in selected.values());require(0<total<=8192,'guard/capture/caller static inventory exceeds selected cap')
    return dict(schema='note10-v240-guarded-query-target-v1',ABS=QUERY_ABS,record_bytes=56,pool_offset=43608,new_pool_bytes=0,
        frames=selected,function_provenance=provenance,noninit_functions=stream_candidate.noninit_functions(sections,set(QUERY_CAPTURE)),
        owner_TU=tu,guard_capture_caller_frame_inventory_bytes=total,compiled_capture_callers=1,compiled_node_callers=1,
        conditional_runtime_admission_proven=False,runtime_observed=False,requires_fresh_direct_physical_consent=True,
        outer_put_scheduler_bound_proven=False,atomic_duration_measured=False,whole_frontdoor_stack_bound_proven=False)


def owner_local_records(stack_data,target,proofs):
    owner_item=stack_data['objects']['arch/arm64/mm/init.o'];frames=stream_candidate.frames(owner_item['stack_usage']);local={}
    for line in owner_item['elf_sections_and_symbols'].splitlines():
        m=re.match(r'^\s*\d+:\s+([0-9a-fA-F]+)\s+(\d+|0x[0-9a-fA-F]+)\s+FUNC\s+LOCAL\s+DEFAULT\s+(\d+)\s+(OUTLINED_FUNCTION_\d+)\s*$',line)
        if m:local.setdefault(m[4],[]).append(dict(address=int(m[1],16),bytes=int(m[2],16 if m[2].startswith('0x')else 10),section_index=m[3]))
    deltas={}
    for row in target['function_provenance'].values():
        index=row['section_index'];delta=row['linked_address']-row['address'];require(index not in deltas or deltas[index]==delta,'consistent owner input-section translation required');deltas[index]=delta
    helper_records={}
    for proof in proofs.values():
        for edge in proof['external_transfers']:
            for record in edge['resolved_records']:
                name=record['name']
                if not re.fullmatch(r'OUTLINED_FUNCTION_\d+',name):continue
                require(name in local and len(local[name])==1,'one selected owner-local ELF definition required')
                item=local[name][0]
                require(item['section_index']in deltas and record['offset']==0 and record['kind']=='t'and
                    item['address']+deltas[item['section_index']]==record['address']and item['bytes']==record['bytes']and record['bytes']<=256 and
                    name in frames and frames[name]['source']==target['owner_TU']['translation_unit']and frames[name]['kind']=='static','actual direct owner-local helper join required')
                key=(record['address'],record['bytes']);helper_records.setdefault(key,[]).append(record)
    require(len(helper_records)<=32,'bounded direct owner-local frontier required')
    return helper_records


def collect_guarded(objects,stack_data,nm,target,out):
    reader=of_calls.p;table=reader.linked_symbols(nm);raw=dict(schema='note10-v240-guarded-query-raw-v1',linked_nm_sha256=sha(nm.encode()),target=target,assembly={},symbols={},tools=[])
    def persist():
        encoded=(json.dumps(raw,indent=2,sort_keys=True)+'\n').encode();require(len(encoded)<=8388608,'bounded guarded raw evidence required');p.save(out/'guarded-query-evidence.json',raw)
    def symbol(name):
        require(name in table and len(table[name])==1,'unique actual named guarded function required');row=table[name][0]
        require(0<row['address']<1<<64 and 0<row['bytes']<=8192 and row['address']%4==row['bytes']%4==0,'bounded AArch64 guarded function extent required')
        return dict(symbol=name,address=row['address'],bytes=row['bytes'],aliases=sorted({n for n,rows in table.items()for v in rows if v['address']==row['address']and v['bytes']==row['bytes']}))
    def capture(key,item):
        require(1<=len(item['aliases'])<=32,'bounded guarded aliases required')
        argv=['aarch64-linux-gnu-objdump','-d','--disassemble-zeroes','--start-address='+hex(item['address']),'--stop-address='+hex(item['address']+item['bytes']),str(objects/'vmlinux')]
        done=subprocess.run(argv,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=120,check=False)
        require(len(done.stdout)<=2097152 and len(done.stderr)<=65536,'bounded guarded disassembly text required')
        raw['symbols'][key]=item;raw['assembly'][key]=done.stdout.decode();raw['tools'].append(dict(key=key,argv=argv,returncode=done.returncode,stdout_sha256=sha(done.stdout),stderr=done.stderr.decode(errors='replace')));persist()
        require(done.returncode==0,'guarded disassembly failed; raw retained');return reader.transfers(raw['assembly'][key],item,table)
    persist();proofs={name:capture(name,symbol(name))for name in QUERY_CAPTURE}
    # Additional owner-local outlined targets are captured once, never assumed frame0.
    helper_records=owner_local_records(stack_data,target,proofs)
    helper_proofs={}
    for(address,size),records in sorted(helper_records.items()):
        name=records[0]['name'];key='owner-outlined@'+format(address,'016x')+':'+str(size)
        item=dict(symbol=name,address=address,bytes=size,aliases=sorted({n for n,rows in table.items()for v in rows if v['address']==address and v['bytes']==size}))
        helper_proofs[key]=capture(key,item)
    return dict(schema='note10-v240-guarded-query-compile-graph-v1',named_bodies=proofs,direct_owner_local_bodies=helper_proofs,
        direct_owner_local_records={format(address,'016x')+':'+str(size):rows for(address,size),rows in helper_records.items()},
        raw_sha256=sha(p.ordinary(out/'guarded-query-evidence.json',8388608)),conditional_preemption_predicate_proven=False,
        selected_query_runtime_admission_proven=False,outer_release_scheduler_bound_proven=False,atomic_interval_duration_measured=False,
        requires_fresh_direct_physical_consent=True,hardware_authorized=False,physical_ready=False)



def verify_guarded(raw,target,nm,stack_data,expected_root):
    reader=of_calls.p;table=reader.linked_symbols(nm)
    require(set(raw)=={'schema','linked_nm_sha256','target','assembly','symbols','tools'}and raw['schema']=='note10-v240-guarded-query-raw-v1'and raw['target']==target and raw['linked_nm_sha256']==sha(nm.encode()),'exact fresh same-image guarded raw binding required')
    require(set(raw['assembly'])==set(raw['symbols'])and set(QUERY_CAPTURE)<=set(raw['assembly'])and len(raw['assembly'])<=len(QUERY_CAPTURE)+32,'bounded guarded body inventory required')
    require(len(raw['tools'])==len(raw['assembly']),'one capture per guarded body required');seen=set();proofs={}
    for tool in raw['tools']:
        require(set(tool)=={'key','argv','returncode','stdout_sha256','stderr'}and tool['key']in raw['assembly']and tool['key']not in seen,'exact unique guarded tool row required')
        key=tool['key'];seen.add(key);item=raw['symbols'][key];text=raw['assembly'][key]
        require(set(item)=={'symbol','address','bytes','aliases'}and item['symbol']in table and any(row['address']==item['address']and row['bytes']==item['bytes']for row in table[item['symbol']])and
            item['aliases']==sorted({n for n,rows in table.items()for row in rows if row['address']==item['address']and row['bytes']==item['bytes']}),'actual same-nm guarded extent/aliases required')
        if key in QUERY_CAPTURE:require(item['symbol']==key and len(table[key])==1,'unique named guarded definition required')
        else:require(key=='owner-outlined@'+format(item['address'],'016x')+':'+str(item['bytes'])and re.fullmatch(r'OUTLINED_FUNCTION_\d+',item['symbol'])and item['bytes']<=256,'only bounded direct owner local allowed')
        wanted=['aarch64-linux-gnu-objdump','-d','--disassemble-zeroes','--start-address='+hex(item['address']),'--stop-address='+hex(item['address']+item['bytes']),expected_root+'/vmlinux']
        require(tool['argv']==wanted and tool['returncode']==0 and type(tool['stderr'])is str and tool['stdout_sha256']==sha(text.encode()),'guarded tools must use validated retained same-Image root/text')
        proofs[key]=reader.transfers(text,item,table)
    required=set(QUERY_CAPTURE);direct=set()
    for key in QUERY_CAPTURE:
        for edge in proofs[key]['external_transfers']:
            for row in edge['resolved_records']:
                if re.fullmatch(r'OUTLINED_FUNCTION_\d+',row['name']):direct.add('owner-outlined@'+format(row['address'],'016x')+':'+str(row['bytes']))
    require(set(proofs)==required|direct,'exact actual direct-owner outlined frontier required')
    records=owner_local_records(stack_data,target,{key:proofs[key]for key in QUERY_CAPTURE})
    require(direct=={'owner-outlined@'+format(address,'016x')+':'+str(size)for address,size in records},'actual owner TU/ELF/SU helper closure required')
    return dict(named_bodies={key:proofs[key]for key in QUERY_CAPTURE},direct_owner_local_bodies={key:proofs[key]for key in sorted(direct)},
        direct_owner_local_records={format(address,'016x')+':'+str(size):rows for(address,size),rows in records.items()})


def source_pins():
    pins=base.source_pins()
    pins.update({name:sha(p.ordinary(ROOT/name))for name in ('note10/device_test/v239_query_admission.py','note10/device_test/test_v239_query_admission.py')})
    require(sha(json.dumps(pins,sort_keys=True,separators=(',',':')).encode())==FROZEN239_MAP_SHA256,'unchanged239 source closure required')
    pins.update({'note10/device_test/'+name:sha(p.ordinary(HERE/name))for name in PUBLIC_NEW})
    pins[WORKFLOW]=sha(p.ordinary(ROOT/WORKFLOW));return pins


def fixture_run(output,compiler_argv):
    import test_v240_guarded_query as body
    return body.run(output,compiler_argv)


def public_context(head,passed):
    p.hexid(head,40)
    require(type(passed)is dict and set(passed)=={'schema','passed','groups','variants','assertions','result_sha256'}and
        passed['schema']==FIXTURE_SCHEMA and passed['passed']is True and(passed['groups'],passed['variants'],passed['assertions'])==(1,31,150),'exact new-only selected OF evidence group required')
    p.hexid(passed['result_sha256'])
    return dict(schema=CONTEXT_SCHEMA,source_head=head,source_sha256=source_pins(),new_fixture_PASS=passed,
        carried234_fixture_PASS=CARRIED234_FIXTURE_PASS,carried234_CI_PASS=CARRIED234_CI_PASS,
        carried235_fixture_PASS=CARRIED235_FIXTURE_PASS,carried235_pre_dispatch_HOLD=CARRIED235_PRE_DISPATCH_HOLD,
        carried236_fixture_PASS=CARRIED236_FIXTURE_PASS,carried236_CI_PASS=CARRIED236_CI_PASS,
        carried237_fixture_PASS=CARRIED237_FIXTURE_PASS,carried237_CI_PASS=CARRIED237_CI_PASS,
        carried238_fixture_PASS=CARRIED238_FIXTURE_PASS,carried239_fixture_PASS=CARRIED239_FIXTURE_PASS,carried239_conditional_proof=CARRIED239_CONDITIONAL_PROOF,
        carried221_fixture_PASS=CARRIED221_FIXTURE_PASS,carried222_fixture_PASS=CARRIED222_FIXTURE_PASS,
        carried220_fixture_PASS=CARRIED220_FIXTURE_PASS,carried223_fixture_PASS=CARRIED223_FIXTURE_PASS,
        carried224_fixture_PASS=CARRIED224_FIXTURE_PASS,carried225_fixture_PASS=CARRIED225_FIXTURE_PASS,
        carried226_partial_python=CARRIED226_PARTIAL_PYTHON,carried227_fixture_PASS=CARRIED227_FIXTURE_PASS,
        carried228_fixture_PASS=CARRIED228_FIXTURE_PASS,carried229_fixture_PASS=CARRIED229_FIXTURE_PASS,
        carried230_fixture_PASS=CARRIED230_FIXTURE_PASS,carried230_CI_PASS=CARRIED230_CI_PASS,
        carried231_fixture_PASS=CARRIED231_FIXTURE_PASS,carried232_fixture_PASS=CARRIED232_FIXTURE_PASS,
        carried232_CI_PASS=CARRIED232_CI_PASS,failed233_fixture=FAILED233_FIXTURE,
        fixture_body_revision='v240',fixture_binding_revision='v240',kernel_provider_revision='v233',guarded_query_revision='v240')


def run_build(output,context,head):
    require(sys.platform=='linux' and context==public_context(head,context.get('new_fixture_PASS')),
            'exact new240 guarded-query context required')
    passed=context['new_fixture_PASS']
    p.hexid(passed['result_sha256']);p.hexid(head,40)
    require(all(os.environ.get(k)==v for k,v in {'GITHUB_SHA':head,'GITHUB_WORKFLOW_SHA':head,'GITHUB_REPOSITORY':'eirblue/ios_note10p',
            'GITHUB_JOB':JOB,'GITHUB_RUN_ATTEMPT':'1'}.items()) and os.environ.get('GITHUB_WORKFLOW_REF','').startswith('eirblue/ios_note10p/'+WORKFLOW+'@'),'exact fresh CI dispatch required')
    out=Path(output).resolve();require(out==ROOT/'note10/private/v240-ci-native-prepare','fixed CI output required')
    work=out.with_name(out.name+'-work');archive=out.with_name(out.name+'-source.tar.gz')
    require(not any(x.exists() for x in (out,work,archive)),'fresh one-use producer required')
    out.mkdir(parents=True);identity=uuid.uuid4().hex
    result=dict(schema=BUILD_SCHEMA,version='v240',producer_revision='v240',kernel_provider_revision='v233',guarded_query_revision='v240',host_fixture_binding_revision='v240',fixture_body_revision='v240',cpu_observation_revision='v231',cpu_stack_provenance_revision='v232',cpu_node_consistency_revision='v233',node_runtime_callers=1,node_runtime_observed=False,requires_fresh_direct_physical_consent=True,atomic_interval_duration_unmeasured=True,scheduler_release_stack_bound_proven=False,compiled_observation_callers=1,cpu_observation_runtime_observed=False,FDT_bound=False,handoff_cpu_selected=False,post_shutdown=False,metadata_projection_revision='v230',metadata_runtime_callers=0,metadata_destination_writes=False,metadata_physical_authority=False,integration_revision='v221',wire_revision='v222',stack_path_revision='v223',metadata_interval_revision='v224',owner_state_revision='v225',source_stream_revision='v226',pool_section_revision='v228',leaf_capture_revision='v229',consumer_revision='v226',PID1_revision='v226',ingest_core_revision='v217',ingest_backend_revision='v219',hash_revision='v219',attribute_revision='v220',compiled_ingestion_callers=1,native_source_allocation_bytes=6258688,native_source_allocation_observed=False,CI_native_source_input_bytes=0,hardware_authorized=False,requires_new_CPU_observation_scope=True,requires_new_native_RAM_approval=None,physical_scope_review_required=True,separate_owner_target_attempts=0,passed=False,source_head=head,
                source_sha256=context['source_sha256'],public_input=context,build_evidence_id=identity,
                run_id=int(os.environ['GITHUB_RUN_ID']),run_attempt=1,full_Image_build_attempts=0,target_PID1_compile_links=0,
                old_tests_replayed=0,execution_slot_enabled=False,native_kernel_bytes_in_Image=0,native_adapter_bytes_in_Image=0,
                reservation_bytes=33554432,reservation_delta_vs208=33554432,stages={},**FALSE_CLAIMS)
    def persist():p.save(out/'result.json',result)
    def run(argv,label,timeout=600):
        result['stages'][label]=dict(argv=list(map(str,argv)),status='started');persist()
        with (out/(label+'.log')).open('xb') as log:done=house.run_command(argv,log,timeout)
        result['stages'][label].update(status='completed',returncode=done.returncode);persist()
        if not (out/(label+'.log')).stat().st_size:(out/(label+'.log')).write_bytes(b'completed\n')
        require(done.returncode==0,'producer stage failed: '+label)
    persist()
    try:
        for name in ('clang-14','gcc','make','aarch64-linux-gnu-gcc','arm-linux-gnueabi-gcc','aarch64-linux-gnu-nm','aarch64-linux-gnu-readelf','aarch64-linux-gnu-objdump'):require(shutil.which(name)is not None,'required tool absent: '+name)
        archive_helper.acquire(archive)
        with archive.open('rb') as stream:archive_sha=hashlib.file_digest(stream,'sha256').hexdigest()
        require(archive.stat().st_size==p.ARCHIVE_BYTES and archive_sha==p.ARCHIVE_SHA,'exact stock source archive required')
        work.mkdir();source=archive_helper.extract(archive,work/'source');objects=work/'objects';objects.mkdir()
        result['stock_config_boundary_sha256']={}
        for name,expected in footprint.STOCK_GUARDS.items():
            original=p.ordinary(source/name);footprint.guard_source(original,expected);result['stock_config_boundary_sha256'][name]=sha(original)
        result['OF_call_source_sha256']={name:sha(p.ordinary(source/name))for name in of_calls.SOURCE_GUARDS}
        require(result['OF_call_source_sha256']==of_calls.SOURCE_GUARDS,'exact selected OF/string/locking sources required')
        result['node_API_source_sha256']={name:sha(p.ordinary(source/name))for name in NODE_SOURCE_GUARDS}
        require(result['node_API_source_sha256']==NODE_SOURCE_GUARDS,'exact pinned OF/map/lifetime source required')
        result['cpu_header_sha256']={name:sha(p.ordinary(source/name))for name in CPU_HEADERS}
        require(result['cpu_header_sha256']==CPU_HEADERS,'exact migration/register helper source required')
        buffers={name:p.ordinary(ROOT/name) for name in context['source_sha256']}
        result['preparation']=install(source,identity,buffers,RETAINED211_PARSER_PASS['parser_source_sha256']);persist()
        require({name:sha(p.ordinary(source/name))for name in NODE_SOURCE_GUARDS}==NODE_SOURCE_GUARDS,'compiled OF/map API sources must remain unchanged after overlay')
        require({name:sha(p.ordinary(source/name))for name in of_calls.SOURCE_GUARDS}==of_calls.SOURCE_GUARDS,'selected source guards must survive unchanged overlay')
        compile_sources=[HERE/n for n in ('v226_native_prepare_pid1.c','native_prepare_core.c','native_parcel_core.c')]
        result['target_PID1_compile_links']=1;persist()
        run(['aarch64-linux-gnu-gcc','-std=c11','-Os','-ffreestanding','-fno-builtin','-fno-tree-loop-distribute-patterns','-fno-stack-protector',
             '-fno-pie','-no-pie','-nostdlib','-nodefaultlibs','-static','-Wl,-e,_start','-Wl,--build-id=none','-Wl,-z,max-page-size=4096',
             '-Wall','-Wextra','-Werror','-I',HERE,'-DN212_BUILD_ID="'+identity+'"',*compile_sources,'-o',out/'minimal-init.elf'],'01-pid1')
        run(['aarch64-linux-gnu-nm','--format=posix',out/'minimal-init.elf'],'01-pid1-symbols')
        init=p.ordinary(out/'minimal-init.elf',PID1_CAP);result['PID1_linkage']=inspect_pid1(init,p.ordinary(out/'01-pid1-symbols.log').decode())
        cpio,prefix=generic(init);(out/'initramfs.cpio').write_bytes(cpio)
        make=['make','-C',str(source),'O='+str(objects),'ARCH=arm64','CC=clang-14','CROSS_COMPILE=aarch64-linux-gnu-',
              'CLANG_TRIPLE=aarch64-linux-gnu-','CROSS_COMPILE_ARM32=arm-linux-gnueabi-','GCC_TOOLCHAIN_DIR=/usr/aarch64-linux-gnu/bin/',
              'HOSTCC=gcc','HOSTCFLAGS=-Wno-error=deprecated-declarations','KCFLAGS=-gdwarf-4 -fstack-usage']
        run([*make,p.DEFCONFIG],'02-defconfig')
        baseline=house.config_values(p.ordinary(objects/'.config'))
        require(baseline.get('NOTE10_V210_NATIVE_PREPARE','n')=='n','new profile must be default off')
        settings=dict(house.SETTINGS,NOTE10_V210_NATIVE_PREPARE='y',KEXEC='n',KEXEC_FILE='n',CRYPTO_SHA256='y',
                      CRYPTO_USER_API_HASH='y',INITRAMFS_SOURCE='"'+str(out/'initramfs.cpio')+'"',LOCALVERSION='"-v240-current-metadata-prepare"',**footprint.SETTINGS)
        edits=[]
        for key,value in settings.items():edits.extend(['--enable' if value=='y' else '--disable',key] if value in ('y','n') else ['--set-str',key,value[1:-1]] if value.startswith('"') else ['--set-val',key,value])
        run([source/'scripts/config','--file',objects/'.config',*edits],'03-settings');run([*make,'olddefconfig'],'04-config')
        config=p.ordinary(objects/'.config');values=house.config_values(config)
        critical=dict(p.REQUIRED_CONFIG,**settings)
        result['effective_profile']=values;result['requested_settings']=settings;result['expected_critical']=critical
        result['configuration_mismatches']={k:dict(expected=v,actual=values.get(k,'n'))for k,v in critical.items()if values.get(k,'n')!=v}
        (out/'actual-effective.config').write_bytes(config);persist()
        for key,value in critical.items():require(values.get(key,'n')==value,'effective setting differs: '+key)
        require(not any(key.startswith('NOTE10_') and value!='n' and key not in settings for key,value in values.items()),'unselected profile forbidden')
        require(all(values.get(k,'n')==v for k,v in CPU_CONFIG.items()),'exact migration-safe CPU profile required')
        result['cpu_observation_config']={k:values.get(k,'n')for k in CPU_CONFIG}
        result['cpu_node_config']=node_config(values)
        result['OF_call_config']={k:values.get(k,'n')for k in of_calls.CONFIG}
        require(result['OF_call_config']==of_calls.CONFIG,'unchanged selected OF/locking config required; do not force settings')
        result['profile_guard']=footprint.effective(values,dict(p.REQUIRED_CONFIG,**settings))
        require(all(values.get(k,'n')==v for k,v in tcs_guard.REQUIRED_CONFIG.items()),'unchanged real sensor/PWM/flash profile required')
        result['tcs3407_config']={k:values.get(k,'n')for k in tcs_guard.REQUIRED_CONFIG}
        result['stock_effective_config_sha256']=sha(json.dumps(baseline,sort_keys=True,separators=(',',':')).encode())
        result['effective_delta_from_stock']={k:dict(before=baseline.get(k,'n'),after=values.get(k,'n')) for k in sorted(set(baseline)|set(values)) if baseline.get(k,'n')!=values.get(k,'n')}
        (out/'actual-effective.config').write_bytes(config);result['effective_profile']=values
        result['cmdline_policy']=sys.modules['builtin_init_route'].builtin_cmdline_policy(config.decode())
        result['full_Image_build_attempts']=1;persist();run([*make,'V=1','-j4','Image'],'05-Image',5400)
        raw=p.ordinary(objects/'arch/arm64/boot/Image',p.IMAGE_LIMIT);symbols=p.ordinary(objects/'System.map',16777216).decode()
        result.update(house.check_image(raw,cpio,identity,symbols,b'N226REQUEST'))
        result['profile_symbol_guard']=footprint.linked_symbols(symbols)
        table={row[2]:int(row[0],16) for line in symbols.splitlines() if len(row:=line.split())==3 and row[2] in ('_text','_end')}
        require(set(table)=={'_text','_end'} and 0<table['_end']-table['_text']<=p.IMAGE_LIMIT,'measured linked extent cap')
        result['linked_end_minus_text']=table['_end']-table['_text']
        result['Image_growth_vs212_bytes']=result['Image_bytes']-BASELINE212_IMAGE_BYTES
        result['linked_growth_vs212_bytes']=result['linked_extent']-BASELINE212_LINKED_BYTES
        result['Image_growth_vs208_bytes']=result['Image_bytes']-BASELINE208_IMAGE_BYTES
        result['linked_growth_vs208_bytes']=result['linked_extent']-BASELINE208_LINKED_BYTES
        result['slot_growth_vs212_bytes']=SLOT_BYTES-4096
        result['kernel_linked_reduction_vs212_bytes']=BASELINE212_LINKED_BYTES+(SLOT_BYTES-4096)-result['linked_extent']
        result['kernel_end_reduction_vs212_bytes']=BASELINE212_LINKED_BYTES+(SLOT_BYTES-4096)-result['linked_end_minus_text']
        result['slot_offset']=result['initramfs_offset']+prefix;result['slot_bytes']=SLOT_BYTES
        require(not any(raw[result['slot_offset']:result['slot_offset']+SLOT_BYTES]),'generic private slot must stay zero')
        result['object_evidence']={}
        for name in ('arch/arm64/mm/init.o','drivers/misc/v154_linux_return.o','init/initramfs.o','drivers/optics/tcs3407.o'):
            obj=p.ordinary(objects/name,67108864);cmdpath=Path(name).with_name('.'+Path(name).name+'.cmd');cmd=p.ordinary(objects/cmdpath)
            require(b'clang-14' in cmd and b'-DMODULE' not in cmd,'same Image builtin command required')
            result['object_evidence'][name]=dict(object_sha256=sha(obj),object_bytes=len(obj),command_sha256=sha(cmd))
            if name=='arch/arm64/mm/init.o':
                (out/'owner-init.o').write_bytes(obj);(out/'owner-init.cmd').write_bytes(cmd)
        owner_command=p.ordinary(out/'owner-init.cmd');stack_relative=stack_sidecar_relative(owner_command)
        stack=p.ordinary(objects/stack_relative);frames=owner.stack_frames(stack.decode());(out/'owner-init.su').write_bytes(stack)
        result['stack_sidecar']=dict(schema='note10-v223-owner-stack-sidecar-v1',relative_path=str(stack_relative),command_sha256=sha(owner_command),stack_sha256=sha(stack))
        run(['aarch64-linux-gnu-nm','--format=posix','--print-size',objects/'arch/arm64/mm/init.o'],'owner-symbols')
        sizes=owner.target_sizes(p.ordinary(out/'owner-symbols.log').decode())
        p.save(out/'target-sizes.json',dict(schema='note10-v240-target-type-sizes-v1',source_head=head,bytes=sizes,allocator_resident_sizes=False))
        p.save(out/'stack-frames.json',dict(schema='note10-v240-target-stack-frames-v1',source_head=head,bytes=frames,total_kernel_stack_bound=False))
        result['target_sizes']=sizes;result['stack_frames']=frames
        result['shared_owner_state']=state_overlay.shared_symbols(p.ordinary(out/'owner-symbols.log').decode(),sizes['state'])
        run(['aarch64-linux-gnu-readelf','--wide','--sections','--symbols',objects/'arch/arm64/mm/init.o'],'owner-sections')
        layout=stream_candidate.target_layout(p.ordinary(out/'owner-symbols.log').decode(),p.ordinary(out/'owner-sections.log').decode(),symbols,len(raw),len(cpio))
        result['source_stream_layout']=layout;result['source_holder_offset']=layout['source_holder_offset'];result['source_holder_bytes']=layout['source_holder_bytes']
        require(not any(raw[layout['source_holder_offset']:layout['source_holder_offset']+layout['source_holder_bytes']]),'public CI source holder must remain all zero')
        require(values.get('HIGHMEM','n')=='n' and values.get('THREAD_INFO_IN_TASK')=='y' and values.get('KASAN','n')=='n' and
            values.get('DEBUG_LOCK_ALLOC','n')=='n' and values.get('DEBUG_VM','n')=='n' and values.get('DEBUG_VIRTUAL','n')=='n' and values.get('UBSAN','n')=='n' and values.get('GCOV_KERNEL','n')=='n' and values.get('VMAP_STACK')=='y','reviewed VMAP-aware stack/direct-page configuration required')
        stack_data=dict(schema='note10-v226-selected-stack-evidence-v1',objects={},assembly={})
        for target in stream_candidate.STACK_TARGETS:
            if target=='arch/arm64/mm/init.o':
                command=owner_command;usage_relative=stream_candidate.compiler_stack_path(command,target);usage=stack.decode()
                elf_evidence=p.ordinary(out/'owner-sections.log').decode()
            else:
                relative=Path(target);cmdpath=relative.with_name('.'+relative.name+'.cmd');command=p.ordinary(objects/cmdpath)
                usage_relative=stream_candidate.compiler_stack_path(command,target);usage=p.ordinary(objects/usage_relative).decode()
                label='stack-object-'+target.replace('/','-')[:-2]
                run(['aarch64-linux-gnu-readelf','--wide','--sections','--symbols',objects/target],label)
                elf_evidence=p.ordinary(out/(label+'.log')).decode()
            stack_data['objects'][target]=dict(command=command.decode(),command_sha256=sha(command),stack_usage=usage,stack_sha256=sha(usage.encode()),stack_relative=str(usage_relative),
                elf_sections_and_symbols=elf_evidence,elf_evidence_sha256=sha(elf_evidence.encode()))
        run(['aarch64-linux-gnu-nm','--format=posix','--print-size','--defined-only',objects/'vmlinux'],'leaf-symbols')
        leaf_symbol_raw=p.ordinary(out/'leaf-symbols.log',16777216)
        stack_data['assembly_symbols']=stream_candidate.leaf_symbols(leaf_symbol_raw.decode())
        stack_data['assembly_symbol_table_sha256']=sha(leaf_symbol_raw)
        for name in ('memcpy','memset','memcmp'):
            run(leaf_capture.command(objects/'vmlinux',stack_data['assembly_symbols'][name]),name+'-disassembly')
            stack_data['assembly'][name]=p.ordinary(out/(name+'-disassembly.log')).decode()
        p.save(out/'stack-evidence.json',stack_data)
        metadata_objects={}
        for target,label in zip(METADATA_OBJECTS,('metadata-projection-elf','metadata-serializer-elf')):
            run(['aarch64-linux-gnu-readelf','--wide','--sections','--symbols',objects/target],label)
            evidence=p.ordinary(out/(label+'.log')).decode()
            relative=Path(target);cmdpath=relative.with_name('.'+relative.name+'.cmd');command=p.ordinary(objects/cmdpath)
            usage_relative=stream_candidate.compiler_stack_path(command,target);usage=p.ordinary(objects/usage_relative).decode()
            proof=metadata_object_evidence(evidence,usage)
            required={'n230_project_metadata'}if target.endswith('/v230_boot_metadata.o')else{'n10_rt_validate_adt','n10_rt_serialize_boot_args','n10_rt_serialize_record'}
            require(required<=set(proof['frames']),'actual metadata compiler frame evidence required')
            metadata_objects[target]=dict(command=command.decode(),command_sha256=sha(command),stack_relative=str(usage_relative),
                stack_usage=usage,stack_sha256=sha(usage.encode()),elf_evidence_sha256=sha(evidence.encode()),**proof)
        result['metadata_projection_compile']=dict(schema='note10-v230-metadata-compile-evidence-v1',
            ABS=metadata_symbols(leaf_symbol_raw.decode()),objects=metadata_objects,runtime_callers=0,destination_writes=False,
            new_writable_section_bytes=0,synthetic_metadata_only=True,complete_ADT=False,live_owner_verified=False)
        result['cpu_observation_target']=observation_target(p.ordinary(out/'owner-symbols.log').decode(),stack.decode(),p.ordinary(out/'owner-sections.log').decode(),owner_command)
        result['cpu_node_target']=node_target(p.ordinary(out/'owner-symbols.log').decode(),stack.decode(),p.ordinary(out/'owner-sections.log').decode(),owner_command)
        result['guarded_query_target']=query_target(p.ordinary(out/'owner-symbols.log').decode(),stack.decode(),p.ordinary(out/'owner-sections.log').decode(),owner_command,leaf_symbol_raw.decode())
        result['guarded_query_graph']=collect_guarded(objects,stack_data,leaf_symbol_raw.decode(),result['guarded_query_target'],out)
        result['node_runtime_callers']=1;result['node_runtime_observed']=False;result['package_stage_supported']=False
        def save_OF_raw(bundle):
            encoded=(json.dumps(bundle,indent=2,sort_keys=True)+'\n').encode('utf-8')
            require(len(encoded)<=of_calls.BUNDLE_CAP,'bounded selected OF raw bundle required')
            p.save(out/'of-call-evidence.json',bundle)
        result['of_call_evidence']=of_calls.collect(objects,stack_data,leaf_symbol_raw.decode(),save_OF_raw)
        result['selected_stack_bound']=stream_candidate.verify_stack_evidence(stack_data)
        result['provider_stack_headroom_runtime_observed']=False;result['physical_ready']=False
        result['Image_growth_vs225_bytes']=len(raw)-50466828;result['linked_growth_vs225_bytes']=result['linked_extent']-57114624
        result['PID1_mapped_span_growth_vs225_bytes']=result['PID1_linkage']['mapped_span_bytes']-8192
        result['linked_noninit_growth_vs225_bytes']=layout['linked_noninit_extent']-35422208
        result['linked_noninit_growth_vs229_bytes']=layout['linked_noninit_extent']-41697280
        result['standing60_growth_cap_fit']=result['linked_noninit_growth_vs225_bytes']<=6275072
        result['requires_new_native_RAM_approval']=not result['standing60_growth_cap_fit']
        result['physical_scope_review_required']=True;result['device_stage_supported']=False
        result['physical_ready']=False
        linked={row[2]for line in symbols.splitlines()if len(row:=line.split())==3 and row[1]in ('T','t')}
        require({'n217_consume','n217_ingest_current','n219_ingest_current','n219_sha256_init','n219_sha256_update','n219_sha256_final'}<=linked,'all reviewed owner/hash bodies must be linked, no runtime invocation claimed')
        require(source_pins()==context['source_sha256'],'source changed during build')
        (out/'Image').write_bytes(raw);(out/'System.map').write_text(symbols)
        result.update(passed=True,PID1_sha256=sha(init),PID1_bytes=len(init),effective_config_sha256=sha(config),
                      native_make_target='Image',native_link_validation_status='linked-in-this-Image')
        persist()
    except BaseException as error:
        result.update(error_type=type(error).__name__,error=str(error)[:1024]);persist();raise
    return result


def seal(out,head):
    files=sorted(x for x in out.iterdir() if x.is_file());sizes={x.name:x.stat().st_size for x in files}
    result=json.loads((out/'result.json').read_bytes())
    require(set(sizes)<=set(SUCCESS_MEMBERS)-{'members.json'} and (result['passed']is not True or set(sizes)==set(SUCCESS_MEMBERS)-{'members.json'}),'exact producer members required')
    require(len(files)<=40 and all(not x.is_symlink() and 0<x.stat().st_size<=67108864 for x in files) and sum(sizes.values())<=134217728,'bounded producer evidence required')
    manifest=dict(schema=MANIFEST_SCHEMA,source_head=head,member_bytes=sizes,member_sha256={x.name:sha(p.ordinary(x,67108864)) for x in files},manifest_self_excluded=True)
    p.save(out/'members.json',manifest)
    with zipfile.ZipFile(out.with_suffix('.zip'),'x',compression=zipfile.ZIP_DEFLATED) as bundle:
        for path in [*files,out/'members.json']:bundle.write(path,path.name)
    subprocess.run(['node',str(ROOT/'note10/device_test/sealed_affinity_artifact.cjs'),'seal',str(out.with_suffix('.zip')),
                    str(out.with_suffix('.n10sealed')),head],check=True,timeout=120)


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',required=True,type=Path)
    parser.add_argument('--expected-source-head',required=True);parser.add_argument('--passed-new-test-context',required=True)
    args=parser.parse_args();house.recipient(os.environ['N10_RECIPIENT_PUBLIC_KEY_B64'])
    context=decode_context_wire(args.passed_new_test_context)
    try:run_build(args.output,context,args.expected_source_head)
    finally:
        if args.output.is_dir():seal(args.output,args.expected_source_head)


if __name__=='__main__':main()
