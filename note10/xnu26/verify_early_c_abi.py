"""Compile actual configured XNU types for early-C state inspection."""
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import sys
from verify_boot_args_abi import symbol_bytes

ROOT=Path(__file__).resolve().parents[2]
EXPRESSIONS={
 'static_entry_size':'sizeof(struct static_if_entry)',
 'static_key_size':'sizeof(struct static_if_key)',
 'static_count_offset':'__builtin_offsetof(struct static_if_key,sik_entries_count)',
 'static_head_offset':'__builtin_offsetof(struct static_if_key,sik_entries_head)',
 'timebase_offset':'__builtin_offsetof(clock_frequency_info_t,timebase_frequency_hz)',
 'topology_prefix_size':'__builtin_offsetof(ml_topology_info_t,chip_revision)',
 'cpu_mmio_offset':'__builtin_offsetof(ml_topology_cpu_t,cpu_IMPL_regs)',
 'cluster_mmio_offset':'__builtin_offsetof(ml_topology_cluster_t,acc_IMPL_regs)',
 'thread_size':'sizeof(struct thread)',
 'thread_ctid_offset':'__builtin_offsetof(struct thread,ctid)',
 'thread_ctid_size':'sizeof(((struct thread*)0)->ctid)',
 'thread_priority_offset':'__builtin_offsetof(struct thread,sched_pri)',
 'thread_priority_size':'sizeof(((struct thread*)0)->sched_pri)',
 'thread_cpu_data_offset':'__builtin_offsetof(struct thread,machine.CpuDatap)',
 'thread_preemption_offset':'__builtin_offsetof(struct thread,machine.preemption_count)',
 'cpu_active_thread_offset':'__builtin_offsetof(cpu_data_t,cpu_active_thread)',
 'cpu_type_offset':'__builtin_offsetof(cpu_data_t,cpu_type)',
 'cpu_subtype_offset':'__builtin_offsetof(cpu_data_t,cpu_subtype)',
 'cpu_running_offset':'__builtin_offsetof(cpu_data_t,cpu_running)',
 'cpu_rtclock_deadline_offset':'__builtin_offsetof(cpu_data_t,rtclock_timer.deadline)',
 'cache_valid_offset':'__builtin_offsetof(cache_info_t,c_valid)',
 'cache_line_offset':'__builtin_offsetof(cache_info_t,c_linesz)',
 'cache_isize_offset':'__builtin_offsetof(cache_info_t,c_isize)',
 'cache_dsize_offset':'__builtin_offsetof(cache_info_t,c_dsize)',
 'cache_l2size_offset':'__builtin_offsetof(cache_info_t,c_l2size)',
 'rtc_timebase_offset':'__builtin_offsetof(rtclock_data_t,rtc_timebase_const)',
 'startup_entry_size':'sizeof(struct startup_entry)',
 'startup_func_offset':'__builtin_offsetof(struct startup_entry,func)',
 'startup_arg_offset':'__builtin_offsetof(struct startup_entry,arg)',
 'startup_locks_phase':'STARTUP_SUB_LOCKS',
 'ctid_mask':'((1U<<CTID_SIZE_BIT)-1)',
 'maxpri_kernel':'MAXPRI_KERNEL',
}


def main():
    output=ROOT/'note10/private/early-c-abi';output.mkdir(exist_ok=True)
    source=output/'oracle.c';obj=output/'oracle.o'
    source.write_text('#include <machine/static_if.h>\n#include <pexpert/pexpert.h>\n'
                      '#include <kern/thread.h>\n#include <machine/machine_routines.h>\n'
                      '#include <arm/cpu_topology.h>\n#include <kern/sched.h>\n'
                      '#include <arm/cpu_data_internal.h>\n#include <arm/rtclock.h>\n#include <arm/cpuid.h>\n'
                      'const unsigned long long note10_early_layout[] = {'+', '.join(EXPRESSIONS.values())+'};\n'
                      'const struct thread note10_active_bit = {.active=1};\n')
    saved=json.loads((ROOT/'note10/private/windows-xnu/objects/DEVELOPMENT/compile-result.json').read_text())
    command=list(next(u['command'] for u in saved['units'] if u['source']=='osfmk/arm64/machine_routines.c'))
    command[command.index('-c')+1]=str(source);command[command.index('-o')+1]=str(obj)
    if '-MF' in command:command[command.index('-MF')+1]=str(output/'oracle.d')
    result=subprocess.run(command,capture_output=True,text=True,encoding='utf-8',errors='replace')
    (output/'compile.log').write_text(result.stdout+result.stderr)
    if result.returncode:raise RuntimeError('Early C ABI compilation failed; see private compile.log')
    raw=obj.read_bytes();values=struct.unpack('<'+'Q'*len(EXPRESSIONS),
                                           symbol_bytes(raw,'_note10_early_layout',8*len(EXPRESSIONS)))
    layout=dict(zip(EXPRESSIONS,values))
    bitfield=symbol_bytes(raw,'_note10_active_bit',layout['thread_size'])
    nonzero=[(index,value) for index,value in enumerate(bitfield) if value]
    if len(nonzero)!=1 or nonzero[0][1]&(nonzero[0][1]-1):raise ValueError('Active bit-field oracle is not one bit')
    layout['thread_active_offset'],layout['thread_active_mask']=nonzero[0]
    expected={'static_entry_size':16,'static_key_size':24,'static_count_offset':4,'static_head_offset':8,
              'timebase_offset':72,'topology_prefix_size':56,'cpu_mmio_offset':40,'cluster_mmio_offset':32}
    if any(layout[key]!=value for key,value in expected.items()):raise ValueError('State checker ABI assumptions differ')
    report={'passed':True,'layout':layout,'object_sha256':hashlib.sha256(raw).hexdigest(),
            'scope':'Actual configured ARM64 C types compiled with saved local flags; not IPSW ABI or hardware boot',
            'command':command,'device_operations':[]}
    (output/'result.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    reference=ROOT/'note10/xnu26/early_c_abi.json'
    if '--write-reference' in sys.argv:
        reference.write_text(json.dumps({'schema':1,'layout':layout,
            'kernel_sha256':'8584aec16c94eeb16b078cb18807f5b93b923c989c19afd78a778745d851454b',
            'oracle_object_sha256':report['object_sha256'],
            'scope':report['scope']},indent=2)+'\n',encoding='utf-8')
    elif reference.exists() and json.loads(reference.read_text())['layout']!=layout:
        raise ValueError('Configured types differ from reviewed state-inspection ABI')
    print(json.dumps({'passed':True,'layout':layout}))


if __name__=='__main__':main()
