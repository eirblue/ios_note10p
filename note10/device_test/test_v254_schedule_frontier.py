"""Five new extraction/provenance/switch-call predicates; synthetic bytes only."""
from copy import deepcopy
import struct


def run(helper):
    raw=bytearray(200);raw[:7]=b'\x7fELF\x02\x01\x01';struct.pack_into('<HH',raw,16,1,183);struct.pack_into('<Q',raw,40,64);struct.pack_into('<HH',raw,58,64,2)
    struct.pack_into('<IIQQQQIIQQ',raw,128,0,1,6,0,192,8,0,0,4,0);struct.pack_into('<II',raw,192,0x94000000,0xd65f03c0)
    text="""  [ 1] .sched.text PROGBITS 0000000000000000 0000c0 000008 00 AX 0 0 4
Relocation section '.rela.sched.text' at offset 0x100 contains 1 entries:
0000000000000000 000000030000011b R_AARCH64_CALL26 0000000000000000 __switch_to + 0
Symbol table '.symtab' contains 4 entries:
 0: 0000000000000000 0 NOTYPE LOCAL DEFAULT UND
 1: 0000000000000000 8 FUNC LOCAL DEFAULT 1 __schedule
 2: 0000000000000000 0 NOTYPE LOCAL DEFAULT 1 $x
 3: 0000000000000000 0 NOTYPE GLOBAL DEFAULT UND __switch_to
"""
    expected=dict(index=1,value=0,bytes=8,section=1,source_line=1,frame_bytes=16,switch_offset=0,switch_symbol_index=3);tu='/source/kernel/sched/core.c';usage=tu+':1:__schedule\t16\tstatic\n';source='static void __schedule(bool preempt)\n'
    def accepted():
        body,info=helper.extract(bytes(raw),text,expected);proof=helper.verify(body,info,usage,tu,source,expected)
        if not proof['context_switch_CALL26_boundary_proven']or proof['original_Image_schedule_body_equivalent']or proof['whole_scheduler_stack_bound_proven']:raise AssertionError('incorrect bounded proof labels')
    def rejected(change):
        body,info=helper.extract(bytes(raw),text,expected);body,info,changed_usage=change(body,deepcopy(info),usage)
        try:helper.verify(body,info,changed_usage,tu,source,expected)
        except ValueError:return
        raise AssertionError('unsupported evidence accepted')
    def data_mapping(body,info,usage):
        info['symbols'][4]=dict(index=4,value=4,bytes=0,type='NOTYPE',binding='LOCAL',visibility='DEFAULT',section=1,name='$d');return body,info,usage
    def wrong_index(body,info,usage):
        info['relocations'][0]['symbol_index']=2;return body,info,usage
    def dynamic(body,info,usage):return body,info,usage.replace('\tstatic','\tdynamic')
    def wrong_opcode(body,info,usage):return struct.pack('<I',0xd65f03c0)+body[4:],info,usage
    cases=[('valid-selected-body-static-SU-switch-call',accepted),('data-mapping-rejected',lambda:rejected(data_mapping)),('relocation-symbol-index-mismatch',lambda:rejected(wrong_index)),('dynamic-SU-rejected',lambda:rejected(dynamic)),('wrong-CALL26-opcode-rejected',lambda:rejected(wrong_opcode))]
    progress=dict(groups=1,variants=5,assertions=5,attempted_variants=0,completed_variants=0,completed_assertions=0,host_processes=0,fresh_object_reads=0,old_tests_replayed=0,case_names=[])
    try:
        for index,(name,case)in enumerate(cases,1):
            progress.update(attempted_variants=index,failing_case_index=index,failing_case_name=name);case();progress['completed_variants']+=1;progress['completed_assertions']+=1;progress['case_names'].append(name)
        progress.update(failing_case_index=None,failing_case_name=None);return progress
    except BaseException as error:error.fixture_progress=progress;raise
