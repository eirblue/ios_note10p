"""Actual production init.o stack-usage and compiled THREAD_SIZE oracle."""
import json
import re
import shutil
import shlex
import struct
from pathlib import Path,PurePosixPath
from prepare_xnu_runtime_observation import sha

FOLDER='xnu-runtime-scratch-stack'
CAPTURE_MODEL=FOLDER+'/capture-model'
LEAF_MODEL=FOLDER+'/leaf-model'
KERNEL='android_kernel_samsung_universal9820-55f042627bb7030c93550faafa117674d32b21d1'
KBUILD_PINS={
 'scripts/Makefile.build':'b8eb9a53659f378ef1973889ae7e7a76aa3b043e83a7cce02e6a7588364f785c',
 'scripts/Kbuild.include':'a83d13d4a0574979dff3a9d6ffa9b686344a6c6ccc27e55ec18fb20bff999700',
 'scripts/Makefile.lib':'b5e800ad4a55bbcd7903052ab7c6cfff42cdd0d1d12a51377fed217ba1a34b57'}

def postprocess_provenance(config,scripts,final_object,target_make_succeeded):
    """Scoped source/final-section inference, not an observed shell trace."""
    if set(scripts)!=set(KBUILD_PINS) or {n:sha(raw) for n,raw in scripts.items()}!=KBUILD_PINS:
        raise ValueError('original pinned Kbuild scripts differ')
    lines=config.decode('ascii').splitlines()
    for name in ('MODVERSIONS','LTO','LTO_CLANG','FTRACE_MCOUNT_RECORD','STACK_VALIDATION'):
        key='CONFIG_'+name
        values=[line for line in lines if line.startswith(key+'=') or line=='# '+key+' is not set']
        allowed=([key+'=y'],) if name=='MODVERSIONS' else ([],[key+'=n'],['# '+key+' is not set'])
        if values not in allowed:raise ValueError('unsupported or ambiguous object transformation: '+name)
    if target_make_succeeded is not True:raise ValueError('actual target make success is required')
    raw=final_object
    if len(raw)<64 or raw[:6]!=b'\x7fELF\x02\x01' or struct.unpack_from('<HH',raw,16)!=(1,183):raise ValueError('final object must be AArch64 ELF64 relocatable')
    start=struct.unpack_from('<Q',raw,40)[0];size,count,names_index=struct.unpack_from('<HHH',raw,58)
    if size!=64 or not 1<=count<=4096 or names_index>=count or start>len(raw) or count*size>len(raw)-start:raise ValueError('final object section table invalid')
    sections=[struct.unpack_from('<IIQQQQIIQQ',raw,start+i*size) for i in range(count)]
    names_section=sections[names_index]
    if names_section[4]>len(raw) or names_section[5]>len(raw)-names_section[4]:raise ValueError('final object section names invalid')
    names=raw[names_section[4]:names_section[4]+names_section[5]];export_sections=[]
    for section in sections:
        at=section[0]
        if at>=len(names):raise ValueError('final object section name offset invalid')
        end=names.find(b'\0',at)
        if end<0:raise ValueError('final object section name unterminated')
        name=names[at:end].decode('ascii')
        if '__ksymtab' in name:export_sections.append(name)
    return {'classification':'pinned-source-and-final-section-inference','shell_branch_observed':False,
      'inferred_branch':'relocatable-crc-symbol-link' if export_sections else 'rename',
      'matching_final_sections':export_sections,'pinned_scripts_sha256':dict(KBUILD_PINS),
      'command_template_reference':'scripts/Makefile.build:230-240 (pinned source, not expanded shell command)',
      'target_make_succeeded':True,'compiler_output_object_sha256':None,
      'compiler_output_object_unavailable_reason':'temporary compiler object consumed by pinned Kbuild postprocess',
      'final_object_sha256':sha(raw),'raw_compiler_object_identity_claimed':False}

def command_origin(command,config):
    """Parse one pinned Kbuild compile assignment; never execute shell text."""
    if not isinstance(command,str) or len(command)>8*1024*1024:raise ValueError('recorded command invalid')
    prefix='cmd_arch/arm64/mm/init.o :='
    lines=[line for line in command.splitlines() if line.startswith('cmd_')]
    if len(lines)!=1 or not lines[0].startswith(prefix):raise ValueError('unique init compiler assignment required')
    stage=lines[0][len(prefix):].strip()
    if not stage or any(c in stage for c in ';|&<>`$\r\n') or stage.endswith('\\'):raise ValueError('untrusted/compound compiler stage')
    try:tokens=shlex.split(stage,posix=True)
    except ValueError as error:raise ValueError('compiler quoting invalid') from error
    if not tokens or tokens[0] not in ('clang-14','/usr/bin/clang-14'):raise ValueError('pinned clang-14 required')
    if tokens.count('-c')!=1 or tokens.count('-o')!=1 or tokens.count('-fstack-usage')!=1 or '--target=aarch64-linux-gnu' not in tokens:
        raise ValueError('unique actual ARM64 compile/stack output required')
    if any((t.startswith('-o') and t!='-o') or t.startswith(('--output','-stack-usage-file','-fstack-usage=','-fno-stack-usage')) for t in tokens):raise ValueError('alternate output option rejected')
    at=tokens.index('-o')
    if at+1>=len(tokens):raise ValueError('compiler output missing')
    output=PurePosixPath(tokens[at+1]);cfg=config.decode('ascii').splitlines()
    options=[line for line in cfg if line.startswith('CONFIG_MODVERSIONS=') or line=='# CONFIG_MODVERSIONS is not set']
    if options==['CONFIG_MODVERSIONS=y']:temporary=True
    elif options in (['# CONFIG_MODVERSIONS is not set'],['CONFIG_MODVERSIONS=n']):temporary=False
    else:raise ValueError('unique modversion config required')
    expected='arch/arm64/mm/'+('.tmp_init.o' if temporary else 'init.o')
    if tokens[at+1]!=expected or output.is_absolute() or '..' in output.parts:raise ValueError('compiler output escaped pinned object directory')
    sources=[t for t in tokens if t.endswith('/init.c')]
    suffix='/'+KERNEL+'/arch/arm64/mm/init.c'
    if len(sources)!=1 or tokens[-1]!=sources[0] or not sources[0].startswith('/') or not sources[0].endswith(suffix) or '..' in PurePosixPath(sources[0]).parts:
        raise ValueError('pinned final init source path differs')
    return {'compiler':tokens[0],'compiler_output':expected,'sidecar':str(output.with_suffix('.su')),
      'source':sources[0],'modversions':temporary,'command_stage_sha256':sha(stage.encode())}
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

PLANNER={'n10_observe_runtime_plan','n10_xnu_runtime_plan_check','n10_runtime_plan_report'}
RUNTIME={'n10_rt_validate_adt','n10_rt_plan','n10_rt_serialize_boot_args','n10_rt_serialize_record','n10_rt_build'}
SCRATCH={'n10_scratch_build','n10_scratch_check','n10_scratch_expected','n10_scratch_report','n10_observe_runtime_scratch'}

def calculate(usage,obj,sources=None,expected_id=None):
    rows={}
    for line in usage.decode().splitlines():
        fields=line.split('\t')
        if len(fields)!=3:raise ValueError('stack-usage syntax unsupported')
        name=fields[0].rsplit(':',1)[-1];base=name.split('.')[0]
        if base.startswith(('n10_rt_','n10_scratch_','n10_observe_runtime_scratch','n10_observe_runtime_plan','n10_xnu_runtime_plan','n10_runtime_plan')) and base not in RUNTIME|SCRATCH|PLANNER:raise ValueError('unknown relevant runtime/planner function')
        if base in RUNTIME|SCRATCH|PLANNER|HELPERS:
            if fields[2]!='static' or not fields[1].isdigit():raise ValueError('unbounded production stack')
            if name in rows:raise ValueError('duplicate stack function')
            rows[name]=int(fields[1])
    required={'n10_rt_build','n10_rt_plan','n10_rt_validate_adt','n10_rt_serialize_boot_args',
      'n10_rt_serialize_record','n10_scratch_build','n10_scratch_check','n10_scratch_report',
      'n10_observe_runtime_scratch','n10_scratch_expected','note10_check_xnu_window','adt_node'}|PLANNER
    if not required<={n.split('.')[0] for n in rows}:raise ValueError('production stack function missing; do not infer zero')
    leaf=None;levels=9
    if sources is not None or expected_id is not None:
        from xnu_runtime_leaf import prove
        leaf=prove(obj,sources,expected_id)
        leaf['usage_sha256']=sha(usage);levels=leaf['adt_levels']
    scratch_rows={n:v for n,v in rows.items() if n.split('.')[0] not in PLANNER}
    # Without the complete caller proof, assume no sequential exclusion and
    # charge every tracked caller frame together at generic depth9.
    path_rows={'generic':rows} if leaf is None else {'scratch':scratch_rows}
    if leaf is not None:
        if not PLANNER<={n.split('.')[0] for n in rows}:raise ValueError('proven sequential planner caller frames missing')
        # Exact reviewed sources prove the planner never calls build or either
        # serializer, and the two diagnostics are sequential sibling calls.
        planner_reachable=HELPERS|PLANNER|{'n10_rt_plan','n10_rt_validate_adt'}
        path_rows['planner']={n:v for n,v in rows.items() if n.split('.')[0] in planner_reachable}
    recursive=max(v for n,v in rows.items() if n.split('.')[0]=='adt_node')
    path_sums={name:sum(values.values())+(levels-1)*recursive for name,values in path_rows.items()}
    measured=max(path_sums.values())
    # External printk/scnprintf/initcall ancestors and interrupt headroom are
    # reserved independently; this is not a whole-kernel stack maximum claim.
    external=2048;bound=measured+external;thread=thread_size(obj)
    if bound>8192 or thread-bound<8192:raise ValueError('scratch stack budget/margin gate rejected')
    return dict(passed=True,frames=rows,adt_levels=levels,leaf_proof=leaf,path_frames=path_rows,path_frame_sums=path_sums,
      sequential_path_maximum=leaf is not None,conservative_function_sum=measured,
      external_reserve=external,cumulative_bound=bound,thread_size=thread,margin=thread-bound,
      maximum_bound=8192,minimum_margin=8192,scope='scoped compiler function-frame estimate',
      compiler_estimate_only=True,physical_stack_safety_proven=False,
      external_reserve_assumed=True,whole_OS_stack_bound_proven=False)

def _save(folder,name,value):
    path=folder/name
    path.write_text(json.dumps(value,indent=2)+'\n')

def _capture(objects,output,source,build,image=None,preliminary=False,target_make_succeeded=False):
    root=Path(output)/FOLDER
    folder=root/'preflight' if preliminary else root
    folder.mkdir(parents=True,exist_ok=not preliminary)
    if any((folder/n).exists() for n in ('result.json','FAILURE.json','evidence.json')):raise ValueError('stack capture already exists; preserve original')
    objects=Path(objects);directory=objects/'arch/arm64/mm'
    evidence={'phase':'standalone-init-object-preflight' if preliminary else 'completed-Image-final-object',
      'preliminary':preliminary,'accepted_full_build':False,'files_sha256':{},'sidecar_inventory':[],
      'copy_errors':[],'final_sources_sha256':build.get('xnu_runtime_scratch_prepared_sha256')}
    origin=None
    try:
        # Capture all available immutable production inputs before parsing or
        # asserting any stack path. Failures retain their evidence directory.
        inputs=[(directory/'init.o','init.o'),(directory/'.init.o.cmd','init.o.cmd'),
          (Path(output)/'handoff.config','handoff.config')]
        final=build.get('xnu_runtime_scratch_prepared_sha256',{})
        inputs += [(Path(source)/name,'source/'+name) for name in final]
        inputs += [(Path(source)/name,'kbuild/'+name) for name in KBUILD_PINS]
        for original,name in inputs:
            try:
                if original.is_symlink() or not original.is_file():raise ValueError('regular production input missing')
                raw=original.read_bytes();dest=folder/name;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(raw)
                evidence['files_sha256'][name]=sha(raw)
            except (OSError,ValueError) as error:evidence['copy_errors'].append({'input':str(original),'output':name,'error':str(error)})
        if directory.is_dir():
            for path in sorted(directory.iterdir(),key=lambda item:item.name):
                if path.name.endswith('.su'):
                    evidence['sidecar_inventory'].append({'name':path.name,'symlink':path.is_symlink(),
                      'size':path.lstat().st_size})
        _save(folder,'evidence.json',evidence)
        if evidence['copy_errors']:raise ValueError('production evidence incomplete; see evidence.json')
        if not final or any(evidence['files_sha256'].get('source/'+n)!=d for n,d in final.items()):raise ValueError('production final source hashes differ')
        provenance=postprocess_provenance((folder/'handoff.config').read_bytes(),
          {n:(folder/'kbuild'/n).read_bytes() for n in KBUILD_PINS},(folder/'init.o').read_bytes(),target_make_succeeded)
        evidence['postprocess_provenance']=provenance;_save(folder,'evidence.json',evidence)
        origin=command_origin((folder/'init.o.cmd').read_text(),(folder/'handoff.config').read_bytes())
        evidence['origin']=origin;_save(folder,'evidence.json',evidence)
        sidecar=objects/origin['sidecar']
        if sidecar.is_symlink() or not sidecar.is_file() or not sidecar.resolve().is_relative_to(directory.resolve()):raise ValueError('recorded compiler stack sidecar missing/unsafe')
        raw=sidecar.read_bytes();(folder/'init.su').write_bytes(raw)
        evidence['files_sha256']['init.su']=sha(raw);_save(folder,'evidence.json',evidence)
        source_bytes={n:(folder/'source'/n).read_bytes() for n in final}
        result=calculate(raw,(folder/'init.o').read_bytes(),source_bytes,build.get('reservation_evidence_id'))
        result['preliminary']=preliminary;result['accepted_full_build']=not preliminary
        result['files_sha256']={n:evidence['files_sha256'][n] for n in ('init.su','init.o')}
        result['production_binding']={'command_sha256':evidence['files_sha256']['init.o.cmd'],
          'config_sha256':evidence['files_sha256']['handoff.config'],
          'final_sources_sha256':final,'object_sha256':evidence['files_sha256']['init.o'],
          'origin':origin,'phase':evidence['phase'],'postprocess_provenance':provenance,
          'compiler_output_object_sha256':None,'final_object_sha256':evidence['files_sha256']['init.o']}
        if not preliminary:
            if image is None or Path(image).is_symlink() or not Path(image).is_file():raise ValueError('completed Image missing')
            result['production_binding']['image_sha256']=sha(Path(image).read_bytes())
            early=(root/'preflight/result.json').read_bytes();preflight_result=json.loads(early)
            if sha(early)!=build.get('xnu_runtime_scratch_stack_preflight_sha256') or preflight_result.get('preliminary') is not True or preflight_result.get('accepted_full_build') is not False:
                raise ValueError('standalone object preflight provenance missing/differs')
            result['production_binding']['preflight_sha256']=sha(early)
            result['production_binding']['preflight_object_changed']=preflight_result['files_sha256']['init.o']!=evidence['files_sha256']['init.o']
            result['production_binding']['leaf_model_input_phase']='standalone-init-object-preflight'
            result['production_binding']['final_estimate_phase']='independently-recomputed-final-object'
            leaf_model=Path(output)/LEAF_MODEL/'result.json'
            result['leaf_model_sha256']=sha(leaf_model.read_bytes())
            if result['leaf_model_sha256']!=build.get('xnu_runtime_scratch_leaf_model_sha256'):raise ValueError('fixed leaf fixture proof missing/differs')
            proof=Path(output)/CAPTURE_MODEL/'result.json'
            result['capture_model_sha256']=sha(proof.read_bytes())
            if result['capture_model_sha256']!=build.get('xnu_runtime_scratch_capture_model_sha256'):raise ValueError('capture fixture proof missing/differs')
        _save(folder,'result.json',result)
        return sha((folder/'result.json').read_bytes())
    except Exception as error:
        evidence['origin']=origin;_save(folder,'evidence.json',evidence)
        _save(folder,'FAILURE.json',{'passed':False,'phase':evidence['phase'],'preliminary':preliminary,
          'accepted_full_build':False,'error_type':type(error).__name__,'error':str(error),
          'evidence_sha256':sha((folder/'evidence.json').read_bytes())})
        raise

def preflight(objects,output,source,build,target_make_succeeded=False):
    return _capture(objects,output,source,build,preliminary=True,target_make_succeeded=target_make_succeeded)

def capture(objects,output,source,image,build,target_make_succeeded=False):
    return _capture(objects,output,source,build,image=image,preliminary=False,target_make_succeeded=target_make_succeeded)


def validate(root,build):
    folder=Path(root)/FOLDER;raw=(folder/'result.json').read_bytes();saved=json.loads(raw)
    if sha(raw)!=build.get('xnu_runtime_scratch_stack_sha256'):raise ValueError('stack evidence hash differs')
    files={n:(folder/n).read_bytes() for n in ('init.su','init.o')}
    if saved.get('files_sha256')!={n:sha(r) for n,r in files.items()}:raise ValueError('actual stack files differ')
    source_bytes={n:(folder/'source'/n).read_bytes() for n in build['xnu_runtime_scratch_prepared_sha256']}
    expected=calculate(files['init.su'],files['init.o'],source_bytes,build.get('reservation_evidence_id'))
    if any(saved.get(k)!=v for k,v in expected.items()):raise ValueError('stack derivation differs')
    if saved.get('preliminary') is not False or saved.get('accepted_full_build') is not True:raise ValueError('preliminary stack proof cannot accept Image')
    binding=saved.get('production_binding',{});command=(folder/'init.o.cmd').read_bytes()
    provenance=postprocess_provenance((folder/'handoff.config').read_bytes(),
      {n:(folder/'kbuild'/n).read_bytes() for n in KBUILD_PINS},files['init.o'],True)
    if (binding.get('postprocess_provenance')!=provenance or binding.get('compiler_output_object_sha256','missing') is not None or
        binding.get('final_object_sha256')!=sha(files['init.o'])):raise ValueError('compiler-estimate/final-object provenance differs')
    origin=command_origin(command.decode(),(folder/'handoff.config').read_bytes())
    if binding.get('origin')!=origin or binding.get('phase')!='completed-Image-final-object':raise ValueError('recorded production output origin differs')
    early=(folder/'preflight/result.json').read_bytes();preflight_result=json.loads(early)
    if (sha(early)!=build.get('xnu_runtime_scratch_stack_preflight_sha256') or sha(early)!=binding.get('preflight_sha256') or
        preflight_result.get('preliminary') is not True or preflight_result.get('accepted_full_build') is not False or
        binding.get('preflight_object_changed')!=(preflight_result['files_sha256']['init.o']!=sha(files['init.o']))):raise ValueError('early/final production object provenance differs')
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
    proof=(Path(root)/CAPTURE_MODEL/'result.json').read_bytes()
    if sha(proof)!=saved.get('capture_model_sha256') or sha(proof)!=build.get('xnu_runtime_scratch_capture_model_sha256'):raise ValueError('capture fixture proof hash differs')
    from test_xnu_runtime_scratch_stack import CASES
    model=json.loads(proof)
    if (model.get('passed') is not True or model.get('fixture_only') is not True or model.get('canonical_suite_complete') is not True or tuple(model.get('cases',{}))!=CASES or
        not all(model['cases'].values()) or model.get('source_sha256')!=sha(Path(__file__).read_bytes()) or
        model.get('test_source_sha256')!=sha((Path(__file__).parent/'test_xnu_runtime_scratch_stack.py').read_bytes())):raise ValueError('capture focused model differs')
    leaf_model=(Path(root)/LEAF_MODEL/'result.json').read_bytes()
    if sha(leaf_model)!=saved.get('leaf_model_sha256') or sha(leaf_model)!=build.get('xnu_runtime_scratch_leaf_model_sha256'):raise ValueError('fixed leaf model hash differs')
    from test_xnu_runtime_leaf import validate_result as validate_leaf_model
    leaf_analysis=json.loads(leaf_model)
    validate_leaf_model(leaf_analysis)
    # The hosted model analyzes the early object. Bind it to retained early
    # inputs and rederive its estimate separately from the final object above.
    from xnu_runtime_leaf import SOURCE_PINS as LEAF_SOURCES,RESERVE as LEAF_RESERVE
    early_folder=folder/'preflight'
    early_object=(early_folder/'init.o').read_bytes();early_usage=(early_folder/'init.su').read_bytes()
    early_sources={n:(early_folder/'source'/n).read_bytes() for n in (*LEAF_SOURCES,LEAF_RESERVE)}
    early_inputs={'object_sha256':sha(early_object),'usage_sha256':sha(early_usage),
      'source_sha256':{n:sha(raw) for n,raw in early_sources.items()}}
    if leaf_analysis.get('analysis_inputs')!=early_inputs:raise ValueError('leaf model is not bound to retained preliminary inputs')
    if (preflight_result['files_sha256'].get('init.o')!=early_inputs['object_sha256'] or
        preflight_result['files_sha256'].get('init.su')!=early_inputs['usage_sha256']):raise ValueError('preliminary object/usage bytes differ')
    early_estimate=calculate(early_usage,early_object,early_sources,build.get('reservation_evidence_id'))
    if (leaf_analysis.get('estimate')!=early_estimate or
        any(preflight_result.get(k)!=v for k,v in early_estimate.items())):raise ValueError('leaf model/preliminary estimate differs from actual early bytes')
    if (binding.get('leaf_model_input_phase')!='standalone-init-object-preflight' or
        binding.get('final_estimate_phase')!='independently-recomputed-final-object' or
        binding.get('preflight_object_changed')!=(early_inputs['object_sha256']!=sha(files['init.o']))):raise ValueError('early model/final independent proof phase differs')
    for name,digest in binding['final_sources_sha256'].items():
        if sha((folder/'source'/name).read_bytes())!=digest:raise ValueError('stack production source snapshot differs')
    return expected
