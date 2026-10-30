"""Actual production init.o stack-usage and compiled THREAD_SIZE oracle."""
import json
import re
import shutil
import struct
from pathlib import Path
from prepare_xnu_runtime_observation import sha

FOLDER='xnu-runtime-scratch-stack'
HELPERS={'zero_bytes','copy_bytes','add64','overlap','pointer_overlap','pointer_span','same','le32',
 'put16','put32','put64','name_byte','gic_name','take','adt_node','command_ok','adt_cursor',
 'n10_frame_checksum','note10_check_xnu_window'}

def thread_size(raw):
    if raw[:6]!=b'\x7fELF\x02\x01' or struct.unpack_from('<H',raw,18)[0]!=183:raise ValueError('stack oracle not AArch64 ELF64')
    at=struct.unpack_from('<Q',raw,40)[0];entry,count=struct.unpack_from('<HH',raw,58)
    sections=[struct.unpack_from('<IIQQQQIIQQ',raw,at+i*entry) for i in range(count)]
    found=[]
    for s in sections:
        if s[1]!=2:continue
        strings=sections[s[6]];names=raw[strings[4]:strings[4]+strings[5]]
        for offset in range(s[4],s[4]+s[5],s[9]):
            name,info,other,index,value,size=struct.unpack_from('<IBBHQQ',raw,offset)
            if names[name:].split(b'\0',1)[0]!=b'n10_scratch_thread_size':continue
            if index>=len(sections) or size!=8:raise ValueError('thread oracle malformed')
            data=sections[index];found.append(struct.unpack_from('<Q',raw,data[4]+value)[0])
    if len(found)!=1 or found[0] not in (16384,32768,65536):raise ValueError('compiled THREAD_SIZE missing/unsupported')
    return found[0]

def calculate(usage,obj):
    rows={}
    for line in usage.decode().splitlines():
        fields=line.split('\t')
        if len(fields)!=3:raise ValueError('stack-usage syntax unsupported')
        name=fields[0].rsplit(':',1)[-1];base=name.split('.')[0]
        if base.startswith(('n10_rt_','n10_scratch_','n10_observe_runtime_scratch')) or base in HELPERS:
            if fields[2]!='static' or not fields[1].isdigit():raise ValueError('unbounded production stack')
            if name in rows:raise ValueError('duplicate stack function')
            rows[name]=int(fields[1])
    required={'n10_rt_build','n10_rt_plan','n10_rt_validate_adt','n10_rt_serialize_boot_args',
      'n10_rt_serialize_record','n10_scratch_build','n10_scratch_check','n10_scratch_report',
      'n10_observe_runtime_scratch','n10_scratch_expected','note10_check_xnu_window','adt_node'}
    if not required<={n.split('.')[0] for n in rows}:raise ValueError('production stack function missing; do not infer zero')
    # Sum all emitted frames, even mutually exclusive build/check/report paths.
    # Inline code is charged to emitted callers; all nine bounded ADT levels
    # are charged even though this immutable synthetic fixture has one level.
    recursive=max(v for n,v in rows.items() if n.split('.')[0]=='adt_node')
    measured=sum(rows.values())+8*recursive
    # External printk/scnprintf/initcall ancestors and interrupt headroom are
    # reserved independently; this is not a whole-kernel stack maximum claim.
    external=2048;bound=measured+external;thread=thread_size(obj)
    if bound>8192 or thread-bound<8192:raise ValueError('scratch stack budget/margin gate rejected')
    return dict(passed=True,frames=rows,adt_levels=9,conservative_function_sum=measured,
      external_reserve=external,cumulative_bound=bound,thread_size=thread,margin=thread-bound,
      maximum_bound=8192,minimum_margin=8192,scope='scratch synchronous chain; external reserve explicit')

def capture(objects,output,source,image,build):
    folder=Path(output)/FOLDER;folder.mkdir(exist_ok=False)
    for name in ('init.su','init.o'):
        shutil.copyfile(Path(objects)/'arch/arm64/mm'/name,folder/name)
    shutil.copyfile(Path(objects)/'arch/arm64/mm/.init.o.cmd',folder/'init.o.cmd')
    shutil.copyfile(Path(output)/'handoff.config',folder/'handoff.config')
    command=(folder/'init.o.cmd').read_text()
    if '-fstack-usage' not in command or 'arch/arm64/mm/init.c' not in command or 'clang' not in command:raise ValueError('actual production stack compile command missing')
    final=build['xnu_runtime_scratch_prepared_sha256']
    for name,digest in final.items():
        raw=(Path(source)/name).read_bytes()
        if sha(raw)!=digest:raise ValueError('production stack final source differs')
        path=folder/'source'/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw)
    result=calculate((folder/'init.su').read_bytes(),(folder/'init.o').read_bytes())
    result['files_sha256']={n:sha((folder/n).read_bytes()) for n in ('init.su','init.o')}
    result['production_binding']={'command_sha256':sha((folder/'init.o.cmd').read_bytes()),
      'config_sha256':sha((folder/'handoff.config').read_bytes()),'image_sha256':sha(Path(image).read_bytes()),
      'final_sources_sha256':final,'object_sha256':sha((folder/'init.o').read_bytes()),
      'origin':'actual completed Image build arch/arm64/mm/init.o'}
    (folder/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    return sha((folder/'result.json').read_bytes())

def validate(root,build):
    folder=Path(root)/FOLDER;raw=(folder/'result.json').read_bytes();saved=json.loads(raw)
    if sha(raw)!=build.get('xnu_runtime_scratch_stack_sha256'):raise ValueError('stack evidence hash differs')
    files={n:(folder/n).read_bytes() for n in ('init.su','init.o')}
    if saved.get('files_sha256')!={n:sha(r) for n,r in files.items()}:raise ValueError('actual stack files differ')
    expected=calculate(files['init.su'],files['init.o'])
    if any(saved.get(k)!=v for k,v in expected.items()):raise ValueError('stack derivation differs')
    binding=saved.get('production_binding',{});command=(folder/'init.o.cmd').read_bytes()
    image=(Path(root)/'Image').read_bytes()
    if build.get('auto_cycle_variant') is True:
        from materialize_auto_cycle import validate as validate_cycle,SLOT
        validate_cycle(root,build.get('auto_cycle_token'))
        image=image.replace(build['auto_cycle_token'].encode(),SLOT,1)
    if ('-fstack-usage' not in command.decode() or 'arch/arm64/mm/init.c' not in command.decode() or
        binding.get('command_sha256')!=sha(command) or binding.get('config_sha256')!=sha((Path(root)/'handoff.config').read_bytes()) or
        binding.get('config_sha256')!=sha((folder/'handoff.config').read_bytes()) or
        binding.get('image_sha256')!=sha(image) or
        binding.get('object_sha256')!=sha(files['init.o']) or
        binding.get('final_sources_sha256')!=build['xnu_runtime_scratch_prepared_sha256']):raise ValueError('stack actual production binding differs')
    for name,digest in binding['final_sources_sha256'].items():
        if sha((folder/'source'/name).read_bytes())!=digest:raise ValueError('stack production source snapshot differs')
    return expected
