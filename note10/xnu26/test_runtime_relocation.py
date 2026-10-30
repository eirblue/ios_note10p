"""v54 focused PC proof: native C outputs, fresh ARM64 objects, ONE entry case.

No old entry/VM/seed/PM suites, real-header oracle recompilation, phone workflow,
physical memory inference or hardware transfer is performed by this driver.
"""
import argparse
import copy
import hashlib
import json
from importlib.metadata import version
import os
from pathlib import Path
import struct
import subprocess
import sys
sys.dont_write_bytecode = True
from boot_contract import encode_boot_args, SIZE, OFFSETS
from boot_adt import Node, encode as encode_adt, decode as decode_adt
from handoff_bundle import materialize_kernel, materialize_adapter, load
from verify_experimental_artifact import verify
from verify_boot_args_abi import symbol_bytes

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
MACHO_SHA = 'b2c80dea6762dc8a388563a099810b48a9157533c6b9c9db8889c29bdddf8d3f'
MEM_SHA = '7a573eb6d2f5efc87bd5c85af130ea854eb4bad8370d17a4247e54f9593a836a'
ASM_SHA = '317c8c7da5d7d99a620702a462ef156e0e72285be8f2dd643b4e0cd471d335bf'
LINK_SHA = 'f438985b1f9bb7f72d896bb22589dfdc80d725dbd70bfa585384bc98b9a7ba74'
ORACLE_OBJECT_SHA = 'b62eef73301a72110c93291ee5288e93b380c772690478b35952f0d78dd0cd85'
ORACLE_REPORT_SHA = '2422662da3d95bd5272be7ac03101b734da7f689d926753a4dba2775f3e2b08e'
PROVENANCE_SHA = '4e74f12e0c610e659a4ce7826ed470c975dd1e79683760320231f20ee50ae9dc'
SAVED_ADAPTER_SHA = 'ff3039f7e4333cffbad4fc513a98def759afcdd63de177b0f55163899193bf63'
PAGE = 0x4000
WINDOW = 0x10000000
SOURCES = ('runtime_relocation.h','runtime_relocation.c','runtime_relocation_host.c',
           'runtime_relocation_abi.c','runtime_relocation_abi.json','test_runtime_relocation.py',
           'test_linked_entry.py','boot_contract.py','boot_adt.py','handoff_bundle.py',
           'verify_experimental_artifact.py','verify_boot_args_abi.py','audit_kernel_instructions.py')


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def regular(path):
    path = Path(path)
    if path.is_symlink() or not path.is_file():raise ValueError('input/proof file missing or unsafe')
    return path.read_bytes()


def private_output(output, inputs):
    private = ROOT/'note10/private'
    if private.is_symlink() or not private.is_dir():raise ValueError('project private root missing/unsafe')
    resolved = output.resolve()
    if output.is_symlink() or output.exists() or resolved==private.resolve() or not resolved.is_relative_to(private.resolve()):
        raise ValueError('fresh project-private output required')
    for source in inputs:
        source=Path(source).resolve()
        if source.is_relative_to(resolved) or resolved.is_relative_to(source):
            raise ValueError('test output and input artifacts must be disjoint')
    output.mkdir(parents=True,exist_ok=False)
    temporary=output/'tmp';temporary.mkdir()
    return dict(os.environ,TMP=str(temporary.resolve()),TEMP=str(temporary.resolve()),TMPDIR=str(temporary.resolve()),
                PYTHONDONTWRITEBYTECODE='1')


def run(command, log, environment):
    completed=subprocess.run([str(arg) for arg in command],capture_output=True,env=environment,timeout=180)
    log.write_bytes(completed.stdout+completed.stderr)
    if completed.returncode:raise ValueError('new focused component command failed; inspect private log '+log.name)
    return completed.stdout


def check_adt(raw):
    if not raw or len(raw)>PAGE:raise ValueError('nonempty bounded synthetic ADT required')
    tree=decode_adt(raw)
    def visit(node):
        if node.name=='gic-handoff' or 'gic-handoff' in node.properties:
            raise ValueError('synthetic ADT cannot declare GIC handoff')
        for child in node.children:visit(child)
    visit(tree)
    if encode_adt(tree)!=raw:raise ValueError('ADT fixture is not canonical codec output')
    return tree


def inspect_codegen(raw):
    from capstone import Cs, CS_ARCH_ARM64, CS_MODE_LITTLE_ENDIAN
    if len(raw)<64 or raw[:7]!=b'\x7fELF\x02\x01\x01':raise ValueError('fresh codegen must be ELF64')
    kind,machine=struct.unpack_from('<HH',raw,16)
    if kind!=1 or machine!=183:raise ValueError('fresh codegen must be relocatable AArch64')
    shoff=struct.unpack_from('<Q',raw,40)[0];shsize,count=struct.unpack_from('<HH',raw,58)
    if shsize!=64 or not count or shoff+count*shsize>len(raw):raise ValueError('codegen section bounds')
    sections=[struct.unpack_from('<IIQQQQIIQQ',raw,shoff+i*64) for i in range(count)]
    undefined=[];functions=[];instruction_count=0
    forbidden={'mrs','msr','dc','ic','tlbi','smc','hvc','svc','eret','wfe','wfi'}
    md=Cs(CS_ARCH_ARM64,CS_MODE_LITTLE_ENDIAN)
    for section in sections:
        _,typ,flags,address,offset,size,link,_,_,entry_size=section
        if typ!=8 and offset+size>len(raw):raise ValueError('codegen section outside object')
        if flags&1 and size:raise ValueError('production C object has mutable global state')
        if flags&4 and size:
            instructions=list(md.disasm(raw[offset:offset+size],address))
            if sum(ins.size for ins in instructions)!=size:raise ValueError('undecodable production C text')
            if any(ins.mnemonic in forbidden for ins in instructions):raise ValueError('privileged operation in production C')
            instruction_count+=len(instructions)
        if typ==2:
            if entry_size!=24 or link>=count or size%24:raise ValueError('codegen symbol table malformed')
            strings_section=sections[link];strings=raw[strings_section[4]:strings_section[4]+strings_section[5]]
            for at in range(offset,offset+size,24):
                name,info,_,index,_,_=struct.unpack_from('<IBBHQQ',raw,at)
                if name>=len(strings):raise ValueError('codegen symbol name outside strings')
                end=strings.find(b'\0',name)
                if end<0:raise ValueError('unterminated codegen symbol')
                value=strings[name:end].decode('ascii')
                if value and index==0:undefined.append(value)
                if info&15==2 and value:functions.append(value)
    required={'n10_rt_validate_adt','n10_rt_plan','n10_rt_serialize_boot_args','n10_rt_serialize_record','n10_rt_build'}
    if undefined or not required<=set(functions) or not instruction_count:
        raise ValueError('freestanding codegen has unresolved dependencies or missing functions')
    return {'aarch64_object':True,'undefined_symbols':undefined,'public_functions':sorted(required),
            'instructions_decoded':instruction_count,'mutable_global_state':False,
            'privileged_instructions':False,'object_executed':False}


def abi_proof(output,host_bytes,saved_directory):
    oracle=json.loads(regular(HERE/'runtime_relocation_abi.json'))
    if oracle['structure_size']!=SIZE or oracle['offsets']!=OFFSETS:raise ValueError('saved numeric oracle differs')
    raw=regular(output/'layout-arm64.o')
    expected=(SIZE,*OFFSETS.values())
    layout=struct.unpack('<14Q',symbol_bytes(raw,'_n10_runtime_layout',14*8))
    fixture=symbol_bytes(raw,'_n10_runtime_fixture',SIZE)
    independent=encode_boot_args(virtual_base=0xfffffff000000000,physical_base=0x80000000,
        memory_size=0x40000000,top_of_kernel=0x88004000,video=(1,2,3,4,5,6),machine_type=7,
        device_tree_pointer=0xfffffff006008000,device_tree_length=0x1234,command_line='debug=0x14e')
    if layout!=expected or fixture!=host_bytes or host_bytes!=independent:
        raise ValueError('fresh ARM64 layout/1152 initializer/C serializer/Python codec differ')
    provenance={'numeric_oracle_sha256':sha(regular(HERE/'runtime_relocation_abi.json')),
                'real_header_sha256':oracle['header_sha256'],'real_source_commit':oracle['source_commit'],
                'saved_real_header_recompiled':False,'saved_private_oracle_available':saved_directory is not None}
    if saved_directory is not None:
        copied=json.loads(regular(saved_directory/'COPY-PROVENANCE.json'))
        if sha(regular(saved_directory/'COPY-PROVENANCE.json'))!=PROVENANCE_SHA:raise ValueError('saved input copy provenance differs')
        for name in ('abi-result.json','abi-oracle.c','abi-oracle.o','transfer.elf'):
            if sha(regular(saved_directory/name))!=copied[name]['sha256']:raise ValueError('saved ABI/adapter input changed')
        saved_raw=regular(saved_directory/'abi-oracle.o');saved_report=json.loads(regular(saved_directory/'abi-result.json'))
        if (sha(saved_raw)!=ORACLE_OBJECT_SHA or sha(regular(saved_directory/'abi-result.json'))!=ORACLE_REPORT_SHA or
                sha(regular(saved_directory/'transfer.elf'))!=SAVED_ADAPTER_SHA or
                saved_report['structure_size']!=SIZE or saved_report['offsets']!=OFFSETS or
                saved_report['header_sha256']!=oracle['header_sha256'] or saved_report['source_commit']!=oracle['source_commit'] or
                struct.unpack('<14Q',symbol_bytes(saved_raw,'_note10_layout',112))!=expected or
                symbol_bytes(saved_raw,'_note10_fixture',SIZE)!=fixture):
            raise ValueError('fresh data differs from saved real-header ABI oracle')
        provenance.update(copy_provenance_sha256=PROVENANCE_SHA,saved_oracle_object_sha256=ORACLE_OBJECT_SHA,
                          saved_oracle_report_sha256=ORACLE_REPORT_SHA,saved_adapter_sha256=SAVED_ADAPTER_SHA)
    return dict(provenance,passed=True,offsets_compared=13,serialized_bytes_compared=1152)


def write_bundle(output,checked,kernel,adapter_raw,adt,c_directory):
    values=json.loads(regular(c_directory/'plan.json'))
    virtual=int(values['virtual_ram_base'],16);base=values['physical_base']
    if (virtual!=0xfffffff006000000 or values['window_size']!=WINDOW or
        values['kernel_physical']-base!=0x1004000 or values['entry_physical']-base!=0x1340490 or
        values['kernel_end']-base!=0x22b0000 or values['mapping_blocks']!=7 or values['kernel_blocks']!=2 or
        [values[key]-base for key in ('arguments_physical','device_tree_physical','adapter_physical')]!=[0,0x4000,0x8000]):
        raise ValueError('actual image C relocation geometry differs')
    args=regular(c_directory/'boot-args.bin');record=regular(c_directory/'transfer-record.bin')
    if len(args)!=1152 or len(record)!=64:raise ValueError('C output sizes differ')
    independent=encode_boot_args(virtual_base=virtual,physical_base=base,memory_size=WINDOW,
        top_of_kernel=values['kernel_end'],device_tree_pointer=int(values['device_tree_virtual'],16),
        device_tree_length=len(adt),command_line='debug=0x14e')
    if args!=independent:raise ValueError('runtime C boot_args disagree with independent codec')
    if record!=struct.pack('<8sII6Q',b'N10XFER1',1,64,values['arguments_physical'],values['entry_physical'],0,0,0,0):
        raise ValueError('C original transfer record differs')
    adapter,entry,slot=materialize_adapter(adapter_raw);patched=bytearray(adapter)
    # These are the C-produced 64 bytes; no Python descriptor producer is used.
    patched[slot:slot+64]=record
    plan={'schema':1,'purpose':'synthetic-pc-model','physical_reservation_verified':False,
          'ram':{'start':base,'size':values['window_size']},'virtual_base':virtual,
          'reserved':[],'occupied':[],'arguments_address':values['arguments_physical'],
          'device_tree_address':values['device_tree_physical'],'adapter_address':values['adapter_physical'],
          'top_of_kernel':values['kernel_end'],'command_line':'debug=0x14e'}
    files={'kernel.mem':kernel,'boot-args.mem':args+bytes(PAGE-len(args)),
           'device-tree.mem':adt+bytes(PAGE-len(adt)),'adapter.mem':bytes(patched)}
    addresses={'kernel.mem':values['kernel_physical'],'boot-args.mem':values['arguments_physical'],
               'device-tree.mem':values['device_tree_physical'],'adapter.mem':values['adapter_physical']}
    manifest={'schema':1,'purpose':'synthetic-pc-model','plan':plan,'kernel_sha256':checked['sha256'],
        'adapter_elf_sha256':sha(adapter_raw),'adapter_entry_physical':values['adapter_physical']+entry,
        'adapter_record_physical':values['adapter_physical']+slot,'xnu_entry_physical':values['entry_physical'],
        'boot_args_physical':values['arguments_physical'],'device_tree_length':len(adt),
        'buffers':[{'file':name,'physical_address':addresses[name],'size':len(data),'sha256':sha(data)} for name,data in files.items()],
        'physical_reservation_verified':False,'device_operations':[],'deployment_ready':False,
        'scope':'C-produced relocation metadata in synthetic PC RAM only; no hardware transfer authorization'}
    output.mkdir()
    for name,data in files.items():(output/name).write_bytes(data)
    (output/'handoff.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf8')
    load(output,kernel_sha256=MACHO_SHA)
    return manifest,files,values,slot


def bundle_negative_cases(directory,manifest,files,slot):
    results={}
    original=(directory/'handoff.json').read_bytes()
    for name in ('descriptor-flags','descriptor-entry','boot-args-padding','false-deployment','source-hash','adt-gic-scope'):
        changed=copy.deepcopy(manifest)
        if name in ('descriptor-flags','descriptor-entry'):
            data=bytearray(files['adapter.mem']);at=slot+(32 if name=='descriptor-flags' else 24)
            data[at]^=1;data=bytes(data);(directory/'adapter.mem').write_bytes(data)
            next(row for row in changed['buffers'] if row['file']=='adapter.mem')['sha256']=sha(data)
        elif name=='boot-args-padding':
            data=bytearray(files['boot-args.mem']);data[4]=1;data=bytes(data);(directory/'boot-args.mem').write_bytes(data)
            next(row for row in changed['buffers'] if row['file']=='boot-args.mem')['sha256']=sha(data)
        elif name=='false-deployment':changed['deployment_ready']=True
        elif name=='source-hash':changed['kernel_sha256']='0'*64
        else:
            try:check_adt(encode_adt(Node('device-tree',{'gic-handoff':b'not-authorized'})))
            except ValueError:results[name]=True;continue
            raise AssertionError('false GIC handoff declaration accepted')
        (directory/'handoff.json').write_text(json.dumps(changed),encoding='utf8')
        try:load(directory,kernel_sha256=MACHO_SHA)
        except ValueError:results[name]=True
        else:raise AssertionError('mutated C bundle accepted: '+name)
        finally:
            (directory/'handoff.json').write_bytes(original)
            (directory/'adapter.mem').write_bytes(files['adapter.mem'])
            (directory/'boot-args.mem').write_bytes(files['boot-args.mem'])
    return results


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('kernel-build','adapter','output'):parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--saved-oracle',type=Path)
    parser.add_argument('--kernel-mem',type=Path)
    parser.add_argument('--base',type=lambda value:int(value,0),default=0x100000000)
    parser.add_argument('--host-cc',default='clang');parser.add_argument('--cross-cc',default='clang')
    args=parser.parse_args()
    dependency_versions={'unicorn':version('unicorn'),'capstone':version('capstone')}
    if dependency_versions!={'unicorn':'2.1.4','capstone':'5.0.9'}:
        raise ValueError('installed instruction-model distribution versions differ')
    import unicorn,capstone
    module_versions={'unicorn':getattr(unicorn,'__version__',None),
                     'capstone':getattr(capstone,'__version__',None)}
    inputs=[args.kernel_build,args.adapter.parent]
    if args.saved_oracle:inputs.append(args.saved_oracle)
    if args.kernel_mem:inputs.append(args.kernel_mem.parent)
    environment=private_output(args.output,inputs)
    checked=verify(args.kernel_build);raw=regular(args.kernel_build/'note10-experimental.macho')
    if checked['sha256']!=MACHO_SHA or len(raw)!=18522008:raise ValueError('required actual native XNU artifact differs')
    image_va,kernel=materialize_kernel(raw,checked['segments'])
    if sha(kernel)!=MEM_SHA or len(kernel)!=19578880:raise ValueError('required actual kernel.mem materialization differs')
    if args.kernel_mem and regular(args.kernel_mem)!=kernel:raise ValueError('saved kernel.mem differs from actual segment materialization')
    if sha(regular(ROOT/'note10/shim/xnu_transfer.S'))!=ASM_SHA or sha(regular(ROOT/'note10/shim/cap_link.ld'))!=LINK_SHA:
        raise ValueError('actual adapter source/linker-script provenance differs')
    adapter=regular(args.adapter);materialize_adapter(adapter)
    native=args.output/'native';native.mkdir()
    executable=native/('runtime-host.exe' if os.name=='nt' else 'runtime-host')
    run([args.host_cc,'-std=c11','-O2','-Wall','-Wextra','-Werror',HERE/'runtime_relocation.c',HERE/'runtime_relocation_host.c','-o',executable],native/'compile.log',environment)
    native_log=run([executable.resolve(),'--selftest'],native/'native.log',environment)
    cases=native_log.decode('ascii').splitlines()
    if not cases or len(cases)!=len(set(cases)) or any(not case.startswith('PASS|') for case in cases):raise ValueError('new native case transcript differs')
    adt=encode_adt(Node('device-tree',children=[Node('chosen',{'boot-args':b'debug=0x14e\0'})]));check_adt(adt)
    adt_path=args.output/'synthetic.adt';adt_path.write_bytes(adt)
    emitted=args.output/'c-output';emitted.mkdir()
    run([executable.resolve(),'--emit',hex(args.base),hex(image_va),hex(len(kernel)),checked['entry_virtual_address'],adt_path.resolve(),emitted.resolve()],emitted/'emit.log',environment)
    run([args.cross_cc,'--target=arm64-apple-macos11','-ffreestanding','-fno-builtin','-std=c11','-O2','-Wall','-Wextra','-Werror','-c',HERE/'runtime_relocation_abi.c','-o',args.output/'layout-arm64.o'],args.output/'layout-compile.log',environment)
    run([args.cross_cc,'--target=aarch64-none-elf','-ffreestanding','-fno-builtin','-std=c11','-O2','-Wall','-Wextra','-Werror','-c',HERE/'runtime_relocation.c','-o',args.output/'runtime-arm64.o'],args.output/'codegen-compile.log',environment)
    abi=abi_proof(args.output,regular(emitted/'oracle-serialized.bin'),args.saved_oracle)
    codegen=inspect_codegen(regular(args.output/'runtime-arm64.o'))
    bundle=args.output/'bundle';manifest,files,values,slot=write_bundle(bundle,checked,kernel,adapter,adt,emitted)
    negatives=bundle_negative_cases(bundle,manifest,files,slot)
    # Exactly one new linked-entry model invocation. Never call any old suite.
    from test_linked_entry import run_case
    entry=run_case(args.kernel_build,args.base,transfer_elf=args.adapter,handoff_bundle=bundle,
                   ram_size=values['window_size'],virtual_ram_base=int(values['virtual_ram_base'],16))
    if entry.get('passed') is not True or entry.get('stop',{}).get('reason')!='before_mmu_enable' or entry.get('modeled_daif_before_mmu')!=0x3c0:
        raise ValueError('new C-buffer entry case did not reach its strict pre-MMU/DAIF boundary')
    result={'version':'v54','passed':True,'pc_only':True,'native_cases':cases,'bundle_mutations':negatives,
        'abi':abi,'codegen':codegen,'entry_cases':[entry],'new_entry_case_count':1,
        'source_sha256':{name:sha(regular(HERE/name)) for name in SOURCES},
        'kernel_macho_sha256':MACHO_SHA,'kernel_mem_sha256':MEM_SHA,'adapter_sha256':sha(adapter),
        'adapter_source_sha256':ASM_SHA,'adapter_linker_sha256':LINK_SHA,
        'c_boot_args_sha256':sha(regular(emitted/'boot-args.bin')),'c_record_sha256':sha(regular(emitted/'transfer-record.bin')),
        'c_plan':values,'bundle_manifest_sha256':sha(regular(bundle/'handoff.json')),
        'host_executable_sha256':sha(regular(executable)),'fresh_arm64_layout_sha256':sha(regular(args.output/'layout-arm64.o')),
        'fresh_arm64_codegen_sha256':sha(regular(args.output/'runtime-arm64.o')),
        'unicorn_version':dependency_versions['unicorn'],'capstone_version':dependency_versions['capstone'],
        'unicorn_module_version':module_versions['unicorn'],'capstone_module_version':module_versions['capstone'],
        'saved_abi_recompiled':False,'old_entry_vm_seed_pm_suites_executed':False,
        'c_produced_buffers_used_directly':True,'synthetic_adt_only':True,'gic_handoff_declared':False,
        'physical_reservation_verified':False,'hardware_verified':False,'deployment_ready':False,
        'device_operations':[],'phone_xnu_executed':False,'scope':'Real XNU/adapter instructions in synthetic RAM; stops before MMU enable'}
    (args.output/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8')
    print(json.dumps({'passed':True,'native_cases':len(cases),'new_entry_cases':1,'stop':'before_mmu_enable','hardware_verified':False}))


if __name__=='__main__':main()
