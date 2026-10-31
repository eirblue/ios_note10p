"""New v66 synthetic interface cases; actual committed control is preflight-hashed only."""
import argparse,copy,io,json,tempfile,zipfile
from pathlib import Path
from crypto_hash_composite import require,digest
from provider_core_input_contract import PUBLIC,snapshot,write_json,write_bytes,SCHEMA_MARKERS,BUILD_PROFILE_DELTAS,NONCLAIMS,validate_control,zip_inventory,old_labels
from provider_core_interface import declared_profile,join_parsed

HISTORICAL_CP2_CASES=('unique-provider-core-join-positive', 'original-input-facts-attributed-positive', 'provider-complete-init-span-positive', 'provider-complete-table-span-positive', 'registration-raw-relocation-binding-positive', 'source-prototype-declared-input-profile-positive', 'unresolved-frontier-carried-positive', 'missing-registration-reference-reject', 'duplicate-registration-reference-reject', 'wrong-registration-name-reject', 'wrong-provider-object-reject', 'wrong-core-object-reject', 'wrong-accepted-result-label-reject', 'weak-reference-reject', 'weak-definition-reject', 'common-or-absolute-definition-reject', 'duplicate-core-definition-reject', 'wrong-definition-section-reject', 'wrong-definition-coordinate-reject', 'definition-not-function-reject', 'unsupported-reference-type-pair-reject', 'visibility-drift-reject', 'wrong-call-relocation-kind-reject', 'wrong-call-addend-reject', 'relocation-outside-init-span-reject', 'truncated-init-span-reject', 'ambiguous-init-alias-reject', 'partial-table-span-reject', 'extra-table-relocation-reject', 'missing-table-relocation-reject', 'table-count-stride-disagreement-reject', 'wrong-table-target-ownership-reject', 'ABI-header-byte-drift-reject', 'generated-config-drift-reject', 'registration-prototype-drift-reject', 'declared-nested-type-header-drift-reject', 'provider-original-layout-provenance-drift-reject', 'declared-target-option-drift-reject', 'unapproved-CC-ABI-delta-reject', 'missing-layout-provenance-reject', 'old-proof-result-presented-as-new-pass-reject', 'new-join-nonclaims-preserved')
HISTORICAL_CP3_CASES=('primary-header-approved-byte-identical-true-positive', 'primary-header-missing-byte-identical-reject', 'primary-header-false-or-nonbool-byte-identical-reject')
CASES=('provider-opaque-member-whole-inventory-bound-positive', 'core-producer-plus-result-whole-inventory-bound-positive', 'provider-required-opaque-member-missing-reject', 'provider-opaque-size-or-digest-drift-reject', 'provider-unlisted-extra-member-reject', 'core-provider-only-opaque-crosswire-reject', 'original-namespace-inventory-binding-missing-reject', 'original-namespace-wrong-role-inventory-reject', 'declared-row-versus-bound-inventory-drift-reject', 'source-manifest-must-remain-declared-reject')


def synthetic(tmp):
 roots={'provider':Path(tmp)/'provider','core':Path(tmp)/'core'};hkeys=('source/include/crypto/hash.h','source/include/crypto/algapi.h','source/include/crypto/internal/hash.h','source/include/linux/crypto.h');header_bytes={k:('/* SYNTHETIC '+k+' */\n').encode() for k in hkeys};header_bytes[hkeys[2]]+=b'int crypto_register_shashes(struct shash_alg *algs, int count);\n';header_map={k:digest(v) for k,v in header_bytes.items()};normalized={};args={}
 for role in roots:
  a=['clang-14']+['-DSYNTHETIC_'+str(i)+'=1' for i in range(1,89)];a[1]='-I@KERNEL_SRC@/include';a[20]='-no-integrated-as';a[2]='-MD-SYNTHETIC-'+role;a[7]='-DBASENAME_SYNTHETIC='+role;a[8]='-DMODNAME_SYNTHETIC='+role;a[85]='-c';a[86]='-o';a[87]='crypto/.tmp_'+role+'.o';a[88]='@KERNEL_SRC@/crypto/'+('sha256_generic.c' if role=='provider' else 'shash.c');normalized[role]=a;args[role]=[x.replace('@KERNEL_SRC@','/synthetic/'+role+'/kernel') for x in a]
 blocks=[{'operation':'replace','v63_argv_indices':[lo,hi],'v65_argv_indices':[lo,hi],'v63_tokens':normalized['provider'][lo:hi],'v65_tokens':normalized['core'][lo:hi],'classification':'synthetic role output'} for lo,hi in ((2,3),(7,9),(87,89))];configs=[]
 for name in ('objects/.config','objects/include/config/auto.conf','objects/include/generated/autoconf.h'):
  definition='#define CONFIG_LOCALVERSION ' if name.endswith('autoconf.h') else 'CONFIG_LOCALVERSION=';rows={role:(b'CONFIG_SYNTHETIC=y\n'+(definition+'"-synthetic-'+role+'"\n').encode()) for role in roots};configs.append({'path':name,'bytes_v63':len(rows['provider']),'bytes_v65':len(rows['core']),'sha256_v63':digest(rows['provider']),'sha256_v65':digest(rows['core']),'only_v63_lines':[definition+'"-synthetic-provider"'],'only_v65_lines':[definition+'"-synthetic-core"']})
  for role in roots:write_bytes(roots[role]/('evidence/dependency-files' if role=='provider' else 'evidence/shash/dependency-files')/name,rows[role])
 for role in roots:
  prefix=roots[role]/('evidence/dependency-files' if role=='provider' else 'evidence/shash/dependency-files')
  for key,raw in header_bytes.items():write_bytes(prefix/key,raw)
  write_json(roots[role]/('evidence/dependencies.json' if role=='provider' else 'evidence/shash/prerequisites.json'),{'files_sha256':header_map,'actual_CC_argv':args[role]})
 def symbol(index,name,info,section,size=0):return {'index':index,'name':name,'info':info,'other':0,'section':section,'value':0,'size':size}
 def section(index,name,size,flags):return {'index':index,'name':name,'type':1,'flags':flags,'size':size,'bytes':bytes([65+index])*size}
 def relocation(section,offset,kind,target,addend=0):return {'section':section,'offset':offset,'type':kind,'symbol':target,'addend':addend,'entry':offset,'relocation_section':section+10}
 null=symbol(0,'',0,0);u=symbol(1,'crypto_register_shashes',16,0);init=symbol(2,'synthetic_init',2,1,48);table=symbol(3,'synthetic_table',1,2,96);section_symbol=symbol(4,'',3,2);callback=symbol(5,'synthetic_callback',18,3,16);provider={'sha256':digest(b'SYNTHETIC PROVIDER OBJECT'),'sections':[section(0,'',0,0),section(1,'.init.synthetic',48,6),section(2,'.data.synthetic',96,3),section(3,'.text.synthetic_callback',16,6)],'symbols':[null,u,init,table,section_symbol,callback],'relocations':[relocation(1,4,275,4),relocation(1,12,277,4),relocation(1,28,283,1)]+[relocation(2,i*32+offset,257,5) for i in range(3) for offset in (0,8,16,24)]};v=symbol(1,'crypto_register_shashes',18,1,72);core={'sha256':digest(b'SYNTHETIC CORE OBJECT'),'sections':[section(0,'',0,0),section(1,'.text.synthetic_register',72,6)],'symbols':[null.copy(),v],'relocations':[]}
 summary={'offset':0,'section':3,'symbol_name':callback['name'],'symbol_info':18,'symbol_value':0,'symbol_size':16,'addend':0,'relocation_type':257,'target_name':callback['name']};entries=[{'index':i,'callbacks':{name:dict(summary) for name in ('init','update','final','finup')},'cra_blocksize':16,'cra_driver_name':'synthetic-driver-'+str(i),'cra_flags':1,'cra_name':'synthetic-alg-'+str(i),'descsize':16,'digestsize':8} for i in range(3)];label=lambda s:{k:s[k] for k in ('name','info','section','size','value')};reg={'init_function':label(init),'registration_external_symbol':u['name'],'registration_call_offset':28,'count':3,'array_argument_relocations':[{'offset':off,'type':kind,'addend':0,'symbol':label(section_symbol)} for off,kind in ((4,275),(12,277))]};table_label={'symbol':label(table),'entries':entries};clang=digest(b'synthetic clang');ld=digest(b'synthetic ld');producer={'command_origin':{'args':args['provider']},'toolchain':{'clang-14':{'sha256':clang},'aarch64-linux-gnu-ld':{'sha256':ld}},'proof':{'registration':reg,'table':table_label,'DWARF':{'types':{'shash_alg':{'byte_size':32,'members':[{'name':name,'offset':offset} for name,offset in (('init',0),('update',8),('final',16),('finup',24))]},'crypto_alg':{'byte_size':24}}}}};core_labels={'compiler':{'sha256':clang},'linker':{'sha256':ld}}
 roles={}
 for i,role in enumerate(roots):
  root='synthetic-'+role;roles[role]={'profile':'accepted-v63-provider-ZIP-v1' if role=='provider' else 'accepted-v65-core-ZIP-v1','repository':'synthetic/repository','source_commit':('a' if role=='provider' else 'b')*40,'run_id':101+i,'run_attempt':1,'workflow_id':201+i,'job_id':301+i,'artifact_id':401+i,'artifact_name':root,'required_successful_steps':['synthetic success'],'ZIP':{'sha256':digest(root.encode()),'bytes':100+i,'root':root,'ordinary_members':3,'ordinary_expanded_bytes':200+i},'selected_object':{'member':root+'/object.o','bytes':10+i,'sha256':(provider if role=='provider' else core)['sha256']},'producer_result':{'member':root+'/result.json','bytes':10,'sha256':digest((role+' producer').encode())},'source_manifest':{'member':root+'/manifest.json','bytes':10,'sha256':digest((role+' manifest').encode())},'accepted_private_result_sha256':digest((role+' private accepted').encode()),'accepted_collector_sha256':digest((role+' collector').encode())}
 c={'schema':'note10-v66-provider-core-control-v1','version':'v66','roles':roles,'registration_pair':{'name':u['name'],'provider_raw_symbol':dict(u),'core_raw_symbol':dict(v),'accepted_call_record':{'accepted_call_offset':28},'accepted_init_symbol':{'record':label(init)},'accepted_core_origin':{'origin':'shash','input_symbol':dict(v),'output_symbol':dict(v)},'provider_object_sha256':provider['sha256'],'core_object_sha256':core['sha256']},'source_input_profile':{'header_sets':{'provider':dict(header_map),'core':dict(header_map)},'common_headers':dict(header_map),'primary_headers':[{'path':k,'byte_identical':True,'bytes':len(header_bytes[k]),'v63_sha256':header_map[k],'v65_sha256':header_map[k]} for k in hkeys],'prototype':'int crypto_register_shashes(struct shash_alg *algs, int count);','generated_configs':configs,'normalized_argv':{'v63_provider':normalized['provider'],'v65_core_shash':normalized['core']},'allowed_role_blocks':blocks,'build_profile_deltas':['synthetic role fields only'],'retained_tool_records':{'clang':{'v63':{'sha256':clang},'v65':{'sha256':clang}},'linker':{'v63':{'sha256':ld},'v65':{'sha256':ld}}},'limitations':['synthetic declared inputs only']},'provider_original_facts':{'accepted_result_sha256':roles['provider']['accepted_private_result_sha256'],'producer_result_sha256':roles['provider']['producer_result']['sha256'],'table_symbol':{'record':label(table)},'table_extent':{'accepted_element_size':32,'accepted_size':96,'accepted_value':0},'table_relocations':{'accepted_entries':copy.deepcopy(entries)},'registration_count':3,'accepted_layout_labels':{'shash_alg':{'byte_size':32},'crypto_alg':{'byte_size':24}}},'review_bindings':{k:digest(k.encode()) for k in ('survey_sha256','cc_profile_addendum_sha256','cc_profile_review_sha256','provider_query_result_sha256','provider_query_review_sha256','final_design_review_sha256')},'nonclaims':{'independent_core_layout_measured':False,'paired_DIE_equivalence':False,'generated_code_ABI_proven':False,'whole_binary_ABI_proven':False,'whole_toolchain_identity_proven':False,'runtime_compatibility_proven':False,'physical_BOOT_reboot':0}}
 complete_synthetic(c,producer,core_labels,roots)
 return provider,core,c,producer,core_labels,roots


def historical_run_cases_CP2(completed=None):
 raise ValueError('consumed CP2 historical cases must never execute')
 if completed is None:completed=[]
 def rejected(fn):
  try:fn()
  except (ValueError,KeyError,TypeError,IndexError):return
  raise ValueError('invalid new synthetic interface accepted')
 positives=set(HISTORICAL_CP2_CASES[:7])|{'new-join-nonclaims-preserved'}
 for name in HISTORICAL_CP2_CASES:
  with tempfile.TemporaryDirectory() as tmp:
   p,k,c,labels,core_labels,roots=synthetic(tmp);profile_override=None
   if name=='wrong-accepted-result-label-reject':
    defects=[(('provider_original_facts','accepted_result_sha256'),digest(b'wrong accepted label')),(('registration_pair','accepted_call_record','unreviewed'),True),(('registration_pair','accepted_call_record','evidence_status'),'verified'),(('registration_pair','accepted_init_symbol','new_raw_fields_required'),[]),(('registration_pair','accepted_core_origin','unreviewed'),True),(('provider_original_facts','table_extent','full_section_metadata_bytes_SHA'),digest(b'pretend observed table')),(('provider_original_facts','table_relocations','complete_raw_RELA'),'verified'),(('provider_original_facts','accepted_layout_labels','crypto_alg','unreviewed'),False),(('source_input_profile','generated_configs',0,'unreviewed'),True),(('nonclaims','unreviewed'),False)]
    for path,value in defects:
     mutant=copy.deepcopy(c);node=mutant
     for key in path[:-1]:node=node[key]
     node[path[-1]]=value;rejected(lambda:declared_profile(mutant,roots['provider'],roots['core'],labels,core_labels))
    completed.append(name);continue
   if name=='unapproved-CC-ABI-delta-reject':
    defects=[(('build_profile_deltas',),['unreviewed delta']),(('retained_tool_records','make','v63','sha256'),digest(b'unknown make')),(('retained_tool_records','make','v63_version_log_sha256'),digest(b'unknown make version')),(('retained_tool_records','resource_directory','v63'),'/synthetic/changed/resource'),(('retained_tool_records','resource_directory','v65_record_sha256'),digest(b'unknown resource record')),(('retained_tool_records','cross_toolchain','v63_aarch64_gcc','sha256'),digest(b'unknown cross gcc')),(('retained_tool_records','cross_toolchain','v65_binary_sha_or_version_record'),{'sha256':digest(b'inherited GCC')}),(('retained_tool_records','external_assembler','v65_identity'),{'sha256':digest(b'inherited assembler')}),(('retained_tool_records','clang','v65','version'),'SYNTHETIC unknown version\n'),(('retained_tool_records','linker','v63','path'),'/synthetic/unknown/linker')]
    for path,value in defects:
     mutant=copy.deepcopy(c);node=mutant['source_input_profile']
     for key in path[:-1]:node=node[key]
     node[path[-1]]=value;rejected(lambda:declared_profile(mutant,roots['provider'],roots['core'],labels,core_labels))

   if name not in positives:
    if name=='missing-registration-reference-reject':p['symbols'][1]['name']='synthetic_absent'
    elif name=='duplicate-registration-reference-reject':p['symbols'].append(dict(p['symbols'][1],index=6))
    elif name=='wrong-registration-name-reject':c['registration_pair']['name']='synthetic_wrong'
    elif name=='wrong-provider-object-reject':p['sha256']=digest(b'wrong synthetic provider')
    elif name=='wrong-core-object-reject':k['sha256']=digest(b'wrong synthetic core')
    elif name=='wrong-accepted-result-label-reject':c['provider_original_facts']['accepted_result_sha256']=digest(b'wrong accepted label')
    elif name=='weak-reference-reject':p['symbols'][1]['info']=32
    elif name=='weak-definition-reject':k['symbols'][1]['info']=34
    elif name=='common-or-absolute-definition-reject':k['symbols'][1]['section']=0xfff2
    elif name=='duplicate-core-definition-reject':k['symbols'].append(dict(k['symbols'][1],index=2))
    elif name=='wrong-definition-section-reject':k['symbols'][1]['section']=0
    elif name=='wrong-definition-coordinate-reject':k['symbols'][1]['value']=4
    elif name=='definition-not-function-reject':k['symbols'][1]['info']=17
    elif name=='unsupported-reference-type-pair-reject':p['symbols'][1]['info']=18;c['registration_pair']['provider_raw_symbol']['info']=18
    elif name=='visibility-drift-reject':p['symbols'][1]['other']=2;c['registration_pair']['provider_raw_symbol']['other']=2
    elif name=='wrong-call-relocation-kind-reject':p['relocations'][2]['type']=282
    elif name=='wrong-call-addend-reject':p['relocations'][2]['addend']=4
    elif name=='relocation-outside-init-span-reject':p['relocations'][2]['offset']=52
    elif name=='truncated-init-span-reject':p['sections'][1]['size']-=1
    elif name=='ambiguous-init-alias-reject':p['symbols'].append(dict(p['symbols'][2],index=6,name='synthetic_alias'))
    elif name=='partial-table-span-reject':p['sections'][2]['size']-=1
    elif name=='extra-table-relocation-reject':p['relocations'].append(dict(p['relocations'][3],offset=8,entry=99))
    elif name=='missing-table-relocation-reject':p['relocations'].pop()
    elif name=='table-count-stride-disagreement-reject':c['provider_original_facts']['registration_count']+=1
    elif name=='wrong-table-target-ownership-reject':p['symbols'][5]['section']=2
    elif name in ('ABI-header-byte-drift-reject','declared-nested-type-header-drift-reject'):(roots['core']/'evidence/shash/dependency-files/source/include/linux/crypto.h').write_bytes(b'changed SYNTHETIC header')
    elif name=='generated-config-drift-reject':(roots['core']/'evidence/shash/dependency-files/objects/.config').write_bytes(b'CONFIG_FOREIGN=y\n')
    elif name=='registration-prototype-drift-reject':c['source_input_profile']['prototype']='int synthetic_wrong(void);'
    elif name=='provider-original-layout-provenance-drift-reject':c['provider_original_facts']['accepted_layout_labels']['crypto_alg']['byte_size']+=1
    elif name=='declared-target-option-drift-reject':
     path=roots['core']/'evidence/shash/prerequisites.json';report=json.loads(path.read_text());report['actual_CC_argv'][30]='-DWRONG_TARGET=1';path.write_text(json.dumps(report))
    elif name=='unapproved-CC-ABI-delta-reject':
     path=roots['core']/'evidence/shash/prerequisites.json';report=json.loads(path.read_text());report['actual_CC_argv'][30]='-DUNAPPROVED=1';c['source_input_profile']['normalized_argv']['v65_core_shash'][30]='-DUNAPPROVED=1';path.write_text(json.dumps(report))
    elif name=='missing-layout-provenance-reject':del labels['proof']['DWARF']['types']['crypto_alg']
    elif name=='old-proof-result-presented-as-new-pass-reject':profile_override={'passed':True,'old_proof':True}
    else:raise ValueError('undefined frozen public case '+name)
   def action():
    profile=declared_profile(c,roots['provider'],roots['core'],labels,core_labels);return join_parsed(p,k,c,labels,profile_override if profile_override is not None else profile)
   if name in positives:
    result=action();require(result['passed'] is True and len(result['new_observations']['complete_init_RELA'])==3 and len(result['new_observations']['complete_table_RELA'])==12,'synthetic complete new raw observations');require(result['nonclaims']==c['nonclaims'] and all(v is False or type(v) is int and v==0 for v in result['nonclaims'].values()),'no stronger claims');require(result['original_provider_facts_attribution']['accepted_result_sha256']==c['roles']['provider']['accepted_private_result_sha256'],'original input facts not relabelled new proof')
   else:rejected(action)
   completed.append(name)
 return {'passed':True,'cases':completed,'case_count':len(completed),'synthetic_only':True,'actual_control_loaded_for_cases':False,'old_fixture_or_checker_replayed':False}


def main():
 p=argparse.ArgumentParser();p.add_argument('--checkpoint',type=Path,required=True);p.add_argument('--checkpoint-sha256',required=True);p.add_argument('--inventory',type=Path,required=True);p.add_argument('--inventory-sha256',required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();root=Path(__file__).resolve().parents[2];require(a.output.absolute().is_relative_to(root/'note10/private') and not a.output.exists(),'fresh private public-case receipt');completed=[];phase='attribution';attribution={'checkpoint_path':str(a.checkpoint.absolute()),'inventory_path':str(a.inventory.absolute()),'checkpoint_sha256':a.checkpoint_sha256,'inventory_sha256':a.inventory_sha256}
 try:
  cpraw=snapshot(a.checkpoint);invraw=snapshot(a.inventory);require(cpraw['sha256']==a.checkpoint_sha256 and invraw['sha256']==a.inventory_sha256,'exact checkpoint/inventory bytes');cp=json.loads(cpraw['raw']);inv=json.loads(invraw['raw']);require(cp['version']=='v66' and cp['checkpoint']==4 and cp['new_private_case_count']==0 and cp['new_private_fixture_inventory']==[] and inv['private_count']==0 and inv['public_cases']==list(CASES) and cp['new_public_fixture_inventory']==list(CASES) and inv['public_count']==len(CASES),'exact frozen public inventory')
  for group in ('public_sources_sha256','private_sources_sha256','shared_sources_sha256'):
   for name,expected in cp[group].items():require(snapshot(root/name)['sha256']==expected,'frozen source/control/import preflight hash only')
  phase='new_public_cases';result=run_cases(completed);result.update(attribution)
 except BaseException as error:
  write_json(a.output,dict(attribution,passed=False,cases=completed,case_count=len(completed),completed_case_names=completed,completed_case_count=len(completed),failing_next_case=CASES[len(completed)] if len(completed)<len(CASES) else None,failure_phase=phase,exception_type=type(error).__name__,exception_message=str(error),automatic_retry=False));raise
 write_json(a.output,result)


def complete_synthetic(c,producer,core,roots):
 """Complete schema vocabulary with invented records, never actual control data."""
 marker=SCHEMA_MARKERS;pair=c['registration_pair'];facts=c['provider_original_facts'];profile=c['source_input_profile'];pair['accepted_call_record'].update(evidence_status=marker['call_status'],producer_member=c['roles']['provider']['producer_result']['member'],producer_json_pointer='/proof/registration',accepted_external_name=pair['name'],survey_relocation_type=283,survey_sha256=c['review_bindings']['survey_sha256'],new_observation_required=list(marker['call_observations']),rule=marker['call_rule']);pair['accepted_init_symbol'].update(evidence_status=marker['init_status'],producer_json_pointer='/proof/registration/init_function',new_raw_fields_required=['index','other']);facts['table_symbol'].update(evidence_status=marker['table_status'],producer_json_pointer='/proof/table/symbol',new_raw_fields_required=['index','other']);facts['table_extent'].update(registered_array_mutable_data=True,full_section_metadata_bytes_SHA=marker['extent_marker']);facts['table_relocations'].update(evidence_status=marker['relocs_status'],producer_json_pointer='/proof/table/entries',complete_raw_RELA=marker['relocs_complete']);facts['accepted_layout_labels']={'crypto_alg':{'byte_size':24,'alignment':8,'alignment_source':marker['layout_sources'][0]},'shash_alg':{'byte_size':32,'alignment':8,'alignment_source':marker['layout_sources'][1]},'shash_desc':{'byte_size':16,'alignment':8,'alignment_source':marker['layout_sources'][1]},'sha256_state':{'byte_size':8,'alignment':8,'alignment_source':marker['layout_sources'][1]}};c['nonclaims']=dict(NONCLAIMS);profile['limitations']=list(marker['limitations']);profile['build_profile_deltas']=list(BUILD_PROFILE_DELTAS)
 for index,block in enumerate(profile['allowed_role_blocks']):block['classification']=marker['classifications'][index]
 tools={}
 for name,role,oldlog,newlog in (('clang','clang-14','tools/clang-14.log','tools/clang-version.log'),('linker','aarch64-linux-gnu-ld','tools/aarch64-linux-gnu-ld.log','tools/linker-version.log'),('make','make','tools/make.log','tools/make-version.log')):
  raw=('SYNTHETIC '+name+' version\n').encode();old={'path':'/synthetic/bin/'+name,'sha256':digest(('synthetic '+name).encode())};new=dict(old,role=role,version=raw.decode());row={'v63':old,'v65':new,'v63_version_log_sha256':digest(raw),'v65_version_log_sha256':digest(raw)};row.update({'same_path_sha256':True,'version_text_equal':True} if name=='clang' else {'same_sha256':True});tools[name]=row;producer['toolchain'][role]=dict(old);core[{'clang':'compiler','linker':'linker','make':'make_tool'}[name]]=dict(new);write_bytes(roots['provider']/oldlog,raw);write_bytes(roots['core']/newlog,raw)
 raw=b'/synthetic/clang/include\n';tools['resource_directory']={'equal':True,'v63':raw.decode().strip(),'v65':raw.decode().strip(),'v63_record_sha256':digest(raw),'v65_record_sha256':digest(raw)};write_bytes(roots['provider']/'tools/include.log',raw);write_bytes(roots['core']/'tools/compiler-resource.log',raw);gcc={'path':'/synthetic/bin/cross-gcc','sha256':digest(b'synthetic cross gcc')};producer['toolchain']['aarch64-linux-gnu-gcc']=dict(gcc);raw=b'SYNTHETIC cross GCC version\n';write_bytes(roots['provider']/'tools/aarch64-linux-gnu-gcc.log',raw);tools['cross_toolchain']={'gap':marker['cross_gap'],'v63_aarch64_gcc':gcc,'v63_version_log_sha256':digest(raw),'v65_binary_sha_or_version_record':None};tools['external_assembler']={'gap':marker['assembler_gap'],'v63_identity':None,'v65_identity':None};profile['retained_tool_records']=tools
 flags='KCFLAGS=-gdwarf-4 -fstack-usage -ffunction-sections -fdata-sections -mllvm -enable-machine-outliner=never -fno-inline-functions';old_args=['make','ARCH=arm64','CC=clang-14',flags,'V=1','-j2','crypto/sha256_generic.o','crypto/n10_sha256_layout_oracle.o'];new_args=['make','--trace','ARCH=arm64','CC=clang-14',flags,'LD=aarch64-linux-gnu-ld','LDFLAGS=-m aarch64linux --no-relax','CONFIG_THIN_ARCHIVES=','V=0','-j2','crypto/crypto_hash.o'];environment={'PLATFORM_VERSION':'11','ANDROID_MAJOR_VERSION':'r'};write_json(roots['provider']/'commands.json',[{'command':old_args,'completed':True,'returncode':0}]);write_json(roots['core']/'commands.json',[{'command':new_args,'completed':True,'returncode':0,'make_environment':environment}]);core['composite_make_command']=list(new_args);core['config_packaging']={'source_CONFIG_THIN_ARCHIVES':'y','effective_make_CONFIG_THIN_ARCHIVES':'','declared_LDFLAGS':'-m aarch64linux --no-relax'};core['routing']={'environment':dict(environment)}


def historical_run_cases_CP3(completed=None):
 raise ValueError('consumed CP3 cases must never execute')
 if completed is None:completed=[]
 require(not completed,'fresh new3-only run; no prefix replay')
 for name in HISTORICAL_CP3_CASES:
  with tempfile.TemporaryDirectory() as tmp:
   _,_,control,_,_,_=synthetic(tmp)
   if name==HISTORICAL_CP3_CASES[0]:
    require(all(row['byte_identical'] is True for row in control['source_input_profile']['primary_headers']),'approved synthetic five-key shape');validate_control(control)
   elif name==HISTORICAL_CP3_CASES[1]:
    del control['source_input_profile']['primary_headers'][0]['byte_identical']
    try:validate_control(control)
    except (ValueError,KeyError,TypeError):pass
    else:raise ValueError('missing mandatory primary flag accepted')
   elif name==HISTORICAL_CP3_CASES[2]:
    for value in (False,0,1,'true',None):
     mutant=copy.deepcopy(control);mutant['source_input_profile']['primary_headers'][0]['byte_identical']=value
     try:validate_control(mutant)
     except (ValueError,KeyError,TypeError):pass
     else:raise ValueError('non-literal-true primary flag accepted')
   else:raise ValueError('unfrozen CP3 case')
   completed.append(name)
 return {'passed':True,'cases':completed,'case_count':len(completed),'private_case_count':0,'synthetic_only':True,'actual_control_loaded_for_cases':False,'old54_replayed':False,'semantic_or_object_work':False}


def namespace_fixture(tmp,kind='provider',defect=None):
 """Invented tiny original ZIPs; opaque data is deliberately not JSON."""
 tmp=Path(tmp);tmp.mkdir(parents=True,exist_ok=True);prefix='synthetic-'+kind+'-original';head=('e' if kind=='provider' else 'f')*40;run=1901 if kind=='provider' else 1902;source=b'# SYNTHETIC original namespace source\n';manifest={'synthetic.py':digest(source)};encode=lambda data:(json.dumps(data,sort_keys=True)+'\n').encode();files={'source/synthetic.py':source,'source-manifest.json':encode(manifest),'evidence/object.o':b'SYNTHETIC bytes, not ELF'};declared={name:digest(raw) for name,raw in files.items()}
 if defect=='declared-row-drift':declared['source/synthetic.py']=digest(b'wrong synthetic declared row')
 if defect=='manifest-undeclared':del declared['source-manifest.json']
 prod={'passed':True,'ci_context':{'GITHUB_SHA':head,'GITHUB_RUN_ID':str(run),'GITHUB_RUN_ATTEMPT':'1'},'source_sha256':manifest,'files_sha256':declared};files['result.json']=encode(prod)
 if kind=='provider' and defect!='missing-opaque' or kind=='core' and defect=='core-opaque':files['independent-verification.json']=b'SYNTHETIC opaque, not JSON:\xff'
 if defect=='extra-member':files['unexpected.json']=b'{}'
 stream=io.BytesIO()
 with zipfile.ZipFile(stream,'w',compression=zipfile.ZIP_DEFLATED) as archive:
  for name,raw in files.items():archive.writestr(prefix+'/'+name,raw)
 raw=stream.getvalue();archive_path=tmp/'input.zip';write_bytes(archive_path,raw);member=lambda name:{'member':prefix+'/'+name,'bytes':len(files[name]),'sha256':digest(files[name])};role={'profile':'accepted-v63-provider-ZIP-v1' if kind=='provider' else 'accepted-v65-core-ZIP-v1','source_commit':head,'run_id':run,'run_attempt':1,'ZIP':{'root':prefix,'bytes':len(raw),'sha256':digest(raw),'ordinary_members':len(files),'ordinary_expanded_bytes':sum(len(value) for value in files.values())},'selected_object':member('evidence/object.o'),'producer_result':member('result.json'),'source_manifest':member('source-manifest.json')};record=snapshot(archive_path,16*1024*1024,role['ZIP']);extraction=tmp/'extracted';binding=zip_inventory(record,role,extraction,original=True);return role,record,extraction,binding,prod


def run_cases(completed=None):
 if completed is None:completed=[]
 require(not completed,'fresh CP4 new10-only run, no prefix replay')
 def rejected(fn):
  try:fn()
  except (ValueError,TypeError,KeyError,AttributeError):return
  raise ValueError('invalid new original inventory path accepted')
 for name in CASES:
  with tempfile.TemporaryDirectory() as tmp:
   if name in CASES[:2]:
    role,record,extraction,binding,prod=namespace_fixture(tmp,'provider' if name==CASES[0] else 'core');require(old_labels(extraction,role,binding)==prod,'original producer return shape, complete role namespace');require(type(binding.rows) is tuple and all(type(row) is tuple and all(type(value) in (str,int) for value in row) for row in binding.rows),'deeply immutable scalar inventory rows');copy_map=binding.members();key=next(iter(copy_map));copy_map[key]['sha256']=digest(b'copy mutation');require(binding.members()[key]['sha256']!=copy_map[key]['sha256'],'returned map copies cannot mutate binding');rejected(lambda:setattr(binding,'_profile','foreign'))
    try:binding.rows[0][1]=999
    except TypeError:pass
    else:raise ValueError('nested binding row was mutable')
   elif name=='provider-opaque-size-or-digest-drift-reject':
    for defect in ('size','digest'):
     role,record,extraction,binding,_=namespace_fixture(Path(tmp)/defect);opaque=extraction/role['ZIP']['root']/'independent-verification.json';raw=opaque.read_bytes();opaque.write_bytes(raw+b'x' if defect=='size' else b'X'+raw[1:]);rejected(lambda:old_labels(extraction,role,binding))
   elif name=='original-namespace-inventory-binding-missing-reject':
    role,record,extraction,binding,_=namespace_fixture(tmp)
    for missing in (None,binding.members(),binding.rows):rejected(lambda:old_labels(extraction,role,missing))
    rejected(lambda:type(binding)(record,role,binding.members()))
   elif name=='original-namespace-wrong-role-inventory-reject':
    role,_,extraction,_,_=namespace_fixture(Path(tmp)/'provider');_,_,_,other,_=namespace_fixture(Path(tmp)/'core','core');rejected(lambda:old_labels(extraction,role,other))
   else:
    kind='core' if name=='core-provider-only-opaque-crosswire-reject' else 'provider';defect={'provider-required-opaque-member-missing-reject':'missing-opaque','provider-unlisted-extra-member-reject':'extra-member','core-provider-only-opaque-crosswire-reject':'core-opaque','declared-row-versus-bound-inventory-drift-reject':'declared-row-drift','source-manifest-must-remain-declared-reject':'manifest-undeclared'}.get(name);require(defect is not None,'frozen CP4 case definition');role,_,extraction,binding,_=namespace_fixture(tmp,kind,defect);rejected(lambda:old_labels(extraction,role,binding))
   completed.append(name)
 return {'passed':True,'cases':completed,'case_count':len(completed),'private_case_count':0,'synthetic_only':True,'actual_control_loaded_for_cases':False,'old57_or_CP3_schema_audit_replayed':False,'ELF_semantic_API_compiler_work':False}


if __name__=='__main__':main()
