"""New finite registration metadata edge; never executes old semantic proofs."""
from pathlib import Path
from crypto_hash_composite import parse_object,require,digest
from provider_core_input_contract import snapshot,json_bytes,validate_control,unchanged

PAIR='crypto_register_shashes'


def partial(actual,expected):return all(actual.get(key)==value for key,value in expected.items())


def unique_named(obj,name):
 rows=[s for s in obj['symbols'] if s['name']==name];require(len(rows)==1,'one exact named symbol');return rows[0]


def full_span(obj,symbol,kind):
 require(0<symbol['section']<len(obj['sections']) and symbol['info']&15==kind and symbol['value']==0 and symbol['size']>0,'owned positive full-span typed definition');section=obj['sections'][symbol['section']];require(section['type']==1 and section['size']==symbol['size'] and len(section['bytes'])==symbol['size'] and not section['flags']&(16|32|512),'complete unmerged owned section');require(bool(section['flags']&4)==(kind==2),'owned section execution flag')
 aliases=[s for s in obj['symbols'] if s['section']==symbol['section'] and s['info']&15==kind and s['size']>0];require(aliases==[symbol],'no ambiguous extent/alias');return section


def relocs(obj,section):
 rows=[r for r in obj['relocations'] if r['section']==section];require(len({r['offset'] for r in rows})==len(rows),'unique relocation place');return sorted(rows,key=lambda r:r['offset'])


def target_summary(obj,relocation):
 s=obj['symbols'][relocation['symbol']];return {'offset':s['value']+relocation['addend'],'section':s['section'],'symbol_name':s['name'],'symbol_info':s['info'],'symbol_value':s['value'],'symbol_size':s['size'],'addend':relocation['addend'],'relocation_type':relocation['type']}


def declared_profile(control,provider_root,core_root,provider_labels,core_labels):
 c=validate_control(control);profile=c['source_input_profile'];roots={'provider':Path(provider_root),'core':Path(core_root)};prefix={'provider':'evidence/dependency-files','core':'evidence/shash/dependency-files'};records=[];observed_headers={}
 for role,root in roots.items():
  report=json_bytes(snapshot(root/('evidence/dependencies.json' if role=='provider' else 'evidence/shash/prerequisites.json'))['raw']);headers={k:v for k,v in report['files_sha256'].items() if k.startswith('source/include/') and k.endswith('.h')};require(headers==profile['header_sets'][role],'exact declared per-role ABI header set');observed_headers[role]={}
  for name,sha in headers.items():
   record=snapshot(root/prefix[role]/name);require(record['sha256']==sha,'original declared ABI header full bytes');observed_headers[role][name]=record['raw'];records.append(record)
 for name,sha in profile['common_headers'].items():require(name in observed_headers['provider'] and name in observed_headers['core'] and observed_headers['provider'][name]==observed_headers['core'][name] and digest(observed_headers['provider'][name])==sha,'exact common declared header bytes')
 require(set(profile['common_headers'])==set(observed_headers['provider'])&set(observed_headers['core']),'no omitted common header')
 for header in profile['primary_headers']:
  for role in roots:require(digest(observed_headers[role][header['path']])==header['v63_sha256']==header['v65_sha256'] and len(observed_headers[role][header['path']])==header['bytes'],'frozen primary interface header')
 prototype=profile['prototype'].encode();require(prototype==b'int crypto_register_shashes(struct shash_alg *algs, int count);' and all(observed_headers[role]['source/include/crypto/internal/hash.h'].count(prototype)==1 for role in roots),'exact declared source prototype')
 for row in profile['generated_configs']:
  pair=[]
  for role,suffix in (('provider','v63'),('core','v65')):
   record=snapshot(roots[role]/prefix[role]/row['path']);require(record['sha256']==row['sha256_'+suffix] and record['bytes']==row['bytes_'+suffix],'full original generated config bytes');pair.append(record['raw'].splitlines(keepends=True));records.append(record)
  require(len(pair[0])==len(pair[1]),'same physical config line count');differences=[i for i,(a,b) in enumerate(zip(*pair)) if a!=b];require(len(differences)==1,'one finite LOCALVERSION line only');index=differences[0]
  for lines,suffix in zip(pair,('v63','v65')):
   expected=row['only_'+suffix+'_lines'];require(type(expected) is list and len(expected)==1 and lines[index].rstrip(b'\r\n')==expected[0].encode() and sum(line.lstrip().startswith((b'CONFIG_LOCALVERSION=',b'#define CONFIG_LOCALVERSION ')) for line in lines)==1,'exact one original LOCALVERSION physical line');require(lines[index].endswith(b'\n'),'complete config line')
  require(pair[0][index][len(row['only_v63_lines'][0].encode()):]==pair[1][index][len(row['only_v65_lines'][0].encode()):],'unchanged LOCALVERSION line terminator')
 args={'provider':provider_labels['command_origin']['args'],'core':json_bytes(snapshot(roots['core']/'evidence/shash/prerequisites.json')['raw'])['actual_CC_argv']};normalized={}
 for role,argv in args.items():
  primary='/crypto/'+('sha256_generic.c' if role=='provider' else 'shash.c');require(argv[-1].endswith(primary) and argv[-1].startswith('/'),'exact role primary C operand');source=argv[-1][:-len(primary)];result=[]
  for value in argv:
   candidates=[prefix+'@KERNEL_SRC@'+value[len(prefix+source):] for prefix in ('','-I') if value==prefix+source or value.startswith(prefix+source+'/')];require(len(candidates)<=1,'finite source-root mapping');result.append(candidates[0] if candidates else value)
  require(result==profile['normalized_argv']['v63_provider' if role=='provider' else 'v65_core_shash'],'full exact saved declared compiler argv');normalized[role]=result
 a,b=normalized['provider'],normalized['core'];require(len(a)==len(b)==89,'exact89-token recorded profile');allowed=set()
 for block in profile['allowed_role_blocks']:
  lo,hi=block['v63_argv_indices'];require(block['operation']=='replace' and block['v65_argv_indices']==[lo,hi] and a[lo:hi]==block['v63_tokens'] and b[lo:hi]==block['v65_tokens'],'exact finite role-specific argv block');allowed.update(range(lo,hi))
 require(len(allowed)==5 and sum(x==y for x,y in zip(a,b))==84 and all(a[i]==b[i] for i in range(89) if i not in allowed),'only three frozen role blocks differ')
 retained=retained_profile_records(profile,roots,provider_labels,core_labels,records)
 facts=c['provider_original_facts'];dw=provider_labels['proof']['DWARF'];require(dw['types']['shash_alg']['byte_size']==facts['accepted_layout_labels']['shash_alg']['byte_size']==facts['table_extent']['accepted_element_size'] and dw['types']['crypto_alg']['byte_size']==facts['accepted_layout_labels']['crypto_alg']['byte_size'],'original provider-only layout label provenance')
 for record in records:unchanged(record)
 return {'declared_input_profile_match':True,'prototype':profile['prototype'],'common_headers':len(profile['common_headers']),'normalized_argv_sha256':{role:digest(('\n'.join(values)+'\n').encode()) for role,values in normalized.items()},'generated_config_delta':'exact three frozen LOCALVERSION physical lines only','provider_layout_attribution':'original accepted v63 labels only','core_layout_measured':False,'binary_ABI_proven':False,'whole_toolchain_identity_proven':False,'runtime_compatibility_proven':False,'retained_record_checks':retained}


def join_parsed(provider,core,c,provider_labels,profile):
 validate_control(c);require(profile.get('declared_input_profile_match') is True and profile.get('core_layout_measured') is False and profile.get('binary_ABI_proven') is False,'new declared-profile evidence, no old pass substitution');roles=c['roles'];require(provider['sha256']==roles['provider']['selected_object']['sha256'] and core['sha256']==roles['core']['selected_object']['sha256'],'exact accepted whole object pair');pair=c['registration_pair'];u=unique_named(provider,PAIR);v=unique_named(core,PAIR);require(u==pair['provider_raw_symbol'] and v==pair['core_raw_symbol'] and (u['info'],u['other'],u['section'],u['value'],u['size'])==(16,0,0,0,0) and v['info']==18 and v['other']==0,'only exact contextual GLOBAL NOTYPE to FUNC registration pair');core_span=full_span(core,v,2);require(pair['accepted_core_origin']['origin']=='shash' and pair['accepted_core_origin']['output_symbol']==v,'accepted core origin label retained, not replayed')
 reg=provider_labels['proof']['registration'];table_labels=provider_labels['proof']['table'];facts=c['provider_original_facts'];require(reg['init_function']==pair['accepted_init_symbol']['record'] and reg['registration_external_symbol']==PAIR and reg['registration_call_offset']==pair['accepted_call_record']['accepted_call_offset'],'original accepted init/call labels');init=unique_named(provider,reg['init_function']['name']);require(partial(init,reg['init_function']),'original partial init record');init_span=full_span(provider,init,2)
 table=unique_named(provider,table_labels['symbol']['name']);require(table_labels['symbol']==facts['table_symbol']['record'] and partial(table,table_labels['symbol']),'original partial table label');table_span=full_span(provider,table,1);stride=facts['table_extent']['accepted_element_size'];count=facts['registration_count'];require(type(count) is int and count==reg['count']==len(facts['table_relocations']['accepted_entries']) and type(stride) is int and stride>0 and table['size']==count*stride==facts['table_extent']['accepted_size'] and table['value']==facts['table_extent']['accepted_value'],'complete table count/stride/extent')
 init_relocs=relocs(provider,init['section']);calls=[r for r in init_relocs if r['symbol']==u['index']];require(len(calls)==1,'unique owned registration reference');call=calls[0];require(call['type']==283 and call['offset']==reg['registration_call_offset'] and call['addend']==0 and init['value']<=call['offset'] and call['offset']+4<=init['value']+init['size'],'new observed direct CALL26 entry/addend/extent')
 array=reg['array_argument_relocations'];require(len(init_relocs)==len(array)+1,'complete init relocation inventory')
 for accepted in array:
  matches=[r for r in init_relocs if r['offset']==accepted['offset']];require(len(matches)==1,'one owned array relocation');r=matches[0];symbol=provider['symbols'][r['symbol']];require(r['type']==accepted['type'] and r['addend']==accepted['addend'] and partial(symbol,accepted['symbol']) and symbol['section']==table['section'] and symbol['value']+r['addend']==table['value'],'actual raw array target matches original source/table extent')
 require(table_labels['entries']==facts['table_relocations']['accepted_entries'],'original accepted callback labels');dw=provider_labels['proof']['DWARF']['types']['shash_alg'];offsets={m['name']:m['offset'] for m in dw['members']};expected={}
 for entry in facts['table_relocations']['accepted_entries']:
  require(type(entry['index']) is int and 0<=entry['index']<count,'original table entry index')
  for callback,accepted in entry['callbacks'].items():
   place=table['value']+entry['index']*stride+offsets[callback];require(place not in expected,'one accepted callback slot');expected[place]=accepted
 raw_table=relocs(provider,table['section']);require(set(expected)=={r['offset'] for r in raw_table},'complete table relocation set, no extra/missing slots');mapped=[]
 for r in raw_table:
  accepted=expected[r['offset']];require(r['type']==257 and r['offset']+8<=table['size'] and target_summary(provider,r)=={k:accepted[k] for k in ('offset','section','symbol_name','symbol_info','symbol_value','symbol_size','addend','relocation_type')},'new raw callback relocation binds accepted summary');target=unique_named(provider,accepted['target_name']);s=provider['symbols'][r['symbol']];require(target['section']==s['section'] and target['value']==s['value']+r['addend'] and target['info']&15==2,'callback section/coordinate-qualified target ownership');mapped.append({'relocation':r,'raw_target_symbol':s,'accepted_target_definition':target})
 return {'schema':'v66-new-registration-edge-v1','passed':True,'claim':'new raw metadata edge and declared input profile only','object_sha256':{'provider':provider['sha256'],'core':core['sha256']},'registration':{'provider_reference':u,'core_definition':v,'new_raw_CALL26':call,'accepted_core_origin':pair['accepted_core_origin']},'new_observations':{'attribution':'new metadata observations from whole accepted object, not invented accepted fields','init_symbol':init,'init_section':{k:value for k,value in init_span.items() if k!='bytes'},'init_bytes_sha256':digest(init_span['bytes']),'complete_init_RELA':init_relocs,'table_symbol':table,'table_section':{k:value for k,value in table_span.items() if k!='bytes'},'table_bytes_sha256':digest(table_span['bytes']),'complete_table_RELA':raw_table,'callback_coordinate_bindings':mapped,'core_bytes_sha256':digest(core_span['bytes'])},'original_provider_facts_attribution':{'accepted_result_sha256':facts['accepted_result_sha256'],'producer_result_sha256':facts['producer_result_sha256'],'registration_count':count,'provider_layout_labels':facts['accepted_layout_labels']},'declared_profile':profile,'unresolved_frontier':{'provider':[s for s in provider['symbols'] if s['section']==0 and s['name'] and s['name']!=PAIR],'core':[s for s in core['symbols'] if s['section']==0 and s['name']]},'nonclaims':c['nonclaims']}


def join_snapshots(provider,core,control,provider_labels,profile):
 result=join_parsed(parse_object(provider['raw']),parse_object(core['raw']),control,provider_labels,profile);unchanged(provider);unchanged(core);return result

def retained_profile_records(profile,roots,provider_labels,core_labels,records):
 tools=profile['retained_tool_records']
 for name,tool,oldlog,newlog in (('clang','clang-14','tools/clang-14.log','tools/clang-version.log'),('linker','aarch64-linux-gnu-ld','tools/aarch64-linux-gnu-ld.log','tools/linker-version.log'),('make','make','tools/make.log','tools/make-version.log')):
  expected=tools[name];old=provider_labels['toolchain'][tool];new=core_labels[{'clang':'compiler','linker':'linker','make':'make_tool'}[name]];require(old==expected['v63'] and new==expected['v65'],'all observed '+name+' path/role/binary/version fields, no inherited identity');left=snapshot(roots['provider']/oldlog);right=snapshot(roots['core']/newlog);records.extend((left,right));require(left['sha256']==expected['v63_version_log_sha256'] and right['sha256']==expected['v65_version_log_sha256'] and right['raw'].decode('utf8')==new['version'],'full observed '+name+' version byte binding');require(old['sha256']==new['sha256'],'reported observed binary equality')
  if name=='clang':require(old['path']==new['path'] and left['raw']==right['raw'],'reported Clang path/version equality')
 resource=tools['resource_directory'];left=snapshot(roots['provider']/'tools/include.log');right=snapshot(roots['core']/'tools/compiler-resource.log');records.extend((left,right));require(left['sha256']==resource['v63_record_sha256'] and right['sha256']==resource['v65_record_sha256'] and left['raw'].decode('utf8').strip()==resource['v63'] and right['raw'].decode('utf8').strip()==resource['v65'] and left['raw']==right['raw'] and resource['v63']==resource['v65'],'complete equal observed resource directory records')
 require(all('-no-integrated-as' in args for args in profile['normalized_argv'].values()),'declared external-assembler option, not observed assembler identity');cross=tools['cross_toolchain'];require(provider_labels['toolchain']['aarch64-linux-gnu-gcc']==cross['v63_aarch64_gcc'],'original observed cross-GCC path/hash, never inherited by core');version=snapshot(roots['provider']/'tools/aarch64-linux-gnu-gcc.log');records.append(version);require(version['sha256']==cross['v63_version_log_sha256'],'original GCC version record');require('aarch64-linux-gnu-gcc' not in core_labels.get('toolchain',{}) and not any(name in core_labels for name in ('cross_toolchain','assembler','gcc')),'core external GCC/as identity remains absent from accepted labels');require('aarch64-linux-gnu-as' not in provider_labels['toolchain'] and 'aarch64-linux-gnu-as' not in core_labels.get('toolchain',{}) and tools['external_assembler']['v63_identity'] is None and tools['external_assembler']['v65_identity'] is None and cross['v65_binary_sha_or_version_record'] is None,'missing assembler/cross-tool identity is an explicit record gap')
 commands={}
 for role in roots:
  record=snapshot(roots[role]/'commands.json');records.append(record);rows=json_bytes(record['raw']);target='crypto/sha256_generic.o' if role=='provider' else 'crypto/crypto_hash.o';matches=[row for row in rows if row['command'] and row['command'][0]=='make' and target in row['command']];require(len(matches)==1 and matches[0]['completed'] is True and matches[0]['returncode']==0,'one retained successful role build command');commands[role]=matches[0]
 provider=commands['provider']['command'];core=commands['core']['command'];kcflags='KCFLAGS=-gdwarf-4 -fstack-usage -ffunction-sections -fdata-sections -mllvm -enable-machine-outliner=never -fno-inline-functions'
 for args in (provider,core):require(args.count('ARCH=arm64')==1 and args.count('CC=clang-14')==1 and args.count(kcflags)==1 and args.count('-j2')==1,'same exact declared arm64/Clang/KCFLAGS inputs')
 require(provider[-2:]==['crypto/sha256_generic.o','crypto/n10_sha256_layout_oracle.o'] and 'V=1' in provider and '--trace' not in provider and not any(value.startswith('LDFLAGS=') for value in provider),'original standalone provider/oracle command and no LDFLAGS declaration');require(core==core_labels['composite_make_command'] and core[-1]=='crypto/crypto_hash.o' and core.count('--trace')==1 and core.count('V=0')==1 and core.count('LD=aarch64-linux-gnu-ld')==1 and core.count('LDFLAGS=-m aarch64linux --no-relax')==1 and core.count('CONFIG_THIN_ARCHIVES=')==1,'enumerated composite logging/link/effective config deltas only')
 packaging=core_labels['config_packaging'];require(packaging=={'source_CONFIG_THIN_ARCHIVES':'y','effective_make_CONFIG_THIN_ARCHIVES':'','declared_LDFLAGS':'-m aarch64linux --no-relax'},'honest source versus effective config declaration');require(commands['core']['make_environment']==core_labels['routing']['environment']=={'PLATFORM_VERSION':'11','ANDROID_MAJOR_VERSION':'r'},'observed core Android environment only, no inferred old environment equality')
 return {'checked_observed_records':['Clang','GNU linker','make','resource directory','original provider cross-GCC','all three declared build-delta records'],'unavailable_records':['v65 external GCC executable identity','provider and core external assembler identity'],'identity_scope':'retained observations only; complete toolchain and emitted ABI unproved'}
