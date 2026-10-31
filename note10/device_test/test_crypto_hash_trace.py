"""New CP5 SYNTHETIC trace fixtures only; no make, shell or prior fixture imports."""
import argparse,builtins,copy,json,stat,tempfile
from types import SimpleNamespace
from unittest.mock import patch
from pathlib import Path
from crypto_hash_trace import parse_trace,selected_recipe,lex,make_profile,MAKE_PATH,MAKE_SHA,MAKE_VERSION,sha,TARGETS
from build_crypto_hash_composite import postprocess_commands,make_command,routing_evidence,verify_routing_evidence,ROUTING_WRAPPER,MAKE_ENVIRONMENT,PUBLIC,trace_log_bytes,trace_tree_inventory,trace_snapshot,check_trace_snapshot,bind_trace_snapshot

CASES=('owned-three-frame-positive','missing-target-header-form-positive','resolved-linker-role-positive','raw-byte-and-line-spans-positive','ordinary-CC-capture-binding-positive','opaque-quoted-semicolon-positive','opaque-fake-header-text-positive','physical-continuation-positive','caller-dispatch-positive','five-command-reader-binding-positive','exact-make-profile-positive','trace-V0-j2-argv-positive','new-public-helper-fixture-closure','missing-ahash-frame-reject','missing-shash-frame-reject','missing-composite-frame-reject','duplicate-stock-frame-reject','unframed-linker-reject','wrong-stock-file-reject','wrong-stock-line-reject','cross-target-body-reject','missing-wrapper-frame-reject','wrong-wrapper-line-reject','wrong-wrapper-target-reject','runtime-echo-only-reject','printf-linker-only-reject','fixdep-linker-only-reject','interleaved-selected-line-reject','truncated-quote-reject','truncated-continuation-reject','missing-final-newline-reject','unknown-header-form-reject','shell-substitution-reject','backtick-substitution-reject','unknown-command-role-reject','unknown-control-operator-reject','wrong-leaf-flag-reject','wrong-temp-input-reject','wrong-version-script-reject','wrong-composite-order-reject','extra-composite-input-reject','missing-genksyms-reject','wrong-genksyms-role-reject','missing-guard-reject','wrong-guard-symbol-reject','missing-cleanup-reject','missing-else-move-reject','wrong-CC-command-reject','wrong-fixdep-capture-reject','missing-composite-capture-reject','extra-trailing-command-reject','unsupported-make-version-reject','wrong-make-binary-reject','wrong-make-path-reject','wrong-baseline-make-reject','fresh-version-mismatch-reject','missing-make-probe-reject','duplicate-build-command-reject','wrong-probe-argv-reject','V1-route-reject','missing-trace-route-reject','unsupported-debug-substitute-reject','branch-execution-claim-remains-false','bounded-log-exact-cap-positive','bounded-log-one-byte-over-cap-reject','bounded-log-default-64MiB-stat-reject','bounded-log-growth-before-open-reject','bounded-log-growth-during-read-reject','bounded-log-directory-reject','bounded-log-symlink-stat-reject','bounded-log-reparse-stat-reject','bounded-log-empty-positive','bounded-log-raised-cap-reject','trace-inventory-complete-byte-hash-positive','trace-inventory-oversized-log-reject','trace-inventory-aggregate-cap-reject','trace-inventory-unsafe-entry-reject','snapshot-single-read-reuse-positive','snapshot-parser-inventory-command-positive','snapshot-inventory-sha-tamper-reject','snapshot-inventory-size-tamper-reject','snapshot-command-sha-tamper-reject','snapshot-command-size-tamper-reject','snapshot-parser-sha-tamper-reject','snapshot-parser-size-tamper-reject','snapshot-file-growth-reject','snapshot-buffer-tamper-reject','snapshot-metadata-tamper-reject','snapshot-missing-inventory-entry-reject')
SOURCE='/synthetic/source/kernel'
OBJECTS='/synthetic/work/objects'
WRAPPER='/synthetic/work/routing/composite.mk'
LINKER={'path':'/synthetic/tools/aarch64-linux-gnu-ld'}


def q(value):return "'"+value.replace("'","'\\''")+"'"


def synthetic():
 """Invented stock-shaped examples; these are never actual trace evidence."""
 cc={};saved={};blocks={}
 for stem in ('ahash','shash'):
  target='crypto/'+stem+'.o';tmp='crypto/.tmp_'+stem+'.o';ver='crypto/.tmp_'+stem+'.ver';base='crypto/.'+stem+'.o';dep=base+'.d';args=['clang-14','-DSYNTHETIC=1','-c','-o',tmp,SOURCE+'/crypto/'+stem+'.c'];text=' '.join(args);cc[target]={'args':args,'text':text};saved[stem]='cmd_'+target+' := '+text+'\n';cpp=' '.join([args[0],'-E','-D__GENKSYMS__',*args[1:-4],args[-1]])
  recipe='set -e; echo '+q('  CC      '+target)+'; '+text+'; scripts/basic/fixdep '+dep+' '+target+' '+q(text)+' > '+base+'.tmp; rm -f '+dep+'; mv -f '+base+'.tmp '+base+'.cmd; if aarch64-linux-gnu-objdump -h '+tmp+' | grep -q __ksymtab; then '+cpp+' | scripts/genksyms/genksyms -r /dev/null > '+ver+'; aarch64-linux-gnu-ld -m aarch64linux --no-relax -r -o '+target+' '+tmp+' -T '+ver+'; rm -f '+tmp+' '+ver+'; else mv -f '+tmp+' '+target+'; fi;\n'
  blocks[target]=SOURCE+"/scripts/Makefile.build:357: update target '"+target+"' due to: SYNTHETIC.c FORCE\n"+recipe+'  CC      '+target+'\n'
 target=TARGETS[2];args=['aarch64-linux-gnu-ld','-m','aarch64linux','--no-relax','-r','-o',target,*TARGETS[:2]];text=' '.join(args);recipe='set -e; echo '+q('  LD      '+target)+'; '+text+"; printf '%s\\n' "+q('cmd_'+target+' := '+text)+' > crypto/.crypto_hash.o.cmd\n';blocks[target]=SOURCE+"/scripts/Makefile.build:653: update target '"+target+"' due to: crypto/ahash.o crypto/shash.o FORCE\n"+recipe+'  LD      '+target+'\n'
 route=WRAPPER+":2: update target 'crypto/crypto_hash.o' due to: prepare scripts FORCE\nmake -f "+SOURCE+'/scripts/Makefile.build obj=crypto crypto/crypto_hash.o\n'
 return route+''.join(blocks.values()),cc,saved,blocks,route


def run_cases(completed=None):
 if completed is None:completed=[]
 def reject(fn):
  try:fn()
  except (ValueError,KeyError,TypeError,IndexError,UnicodeError):return
  raise ValueError('invalid new synthetic trace accepted')
 for name in CASES:
  text,cc,saved,blocks,route=synthetic();raw=text.encode();args=make_command(SOURCE,OBJECTS,WRAPPER);profile={'role':'make','path':MAKE_PATH,'sha256':MAKE_SHA,'version':MAKE_VERSION};baseline={'path':MAKE_PATH,'sha256':MAKE_SHA}
  require=lambda ok,msg:(_ for _ in ()).throw(ValueError(msg)) if not ok else None
  if name.startswith('snapshot-'):
   with tempfile.TemporaryDirectory() as tmp:
    root=Path(tmp);(root/'build').mkdir();path=root/'build/composite.log';path.write_bytes(raw);snapshot=trace_snapshot(path);parsed=parse_trace(snapshot['raw'],LINKER,SOURCE,WRAPPER,cc);inventory={'build/composite.log':{'bytes':len(raw),'sha256':sha(raw)}};command={'log':'build/composite.log','log_bytes':len(raw),'log_sha256':sha(raw)}
    if name=='snapshot-single-read-reuse-positive':
     with patch.object(Path,'open',side_effect=AssertionError('trace snapshot must never reopen for inventory/parser/hash')):
      inventory=trace_tree_inventory(root,snapshot);parsed=parse_trace(snapshot['raw'],LINKER,SOURCE,WRAPPER,cc);bind_trace_snapshot(root,snapshot,parsed,inventory,command)
    elif name=='snapshot-parser-inventory-command-positive':require(bind_trace_snapshot(root,snapshot,parsed,trace_tree_inventory(root,snapshot),command)=={'bytes':len(raw),'sha256':sha(raw)},'all three explicit size/SHA bindings reuse exact buffer')
    else:
     if name=='snapshot-inventory-sha-tamper-reject':inventory['build/composite.log']['sha256']='0'*64
     elif name=='snapshot-inventory-size-tamper-reject':inventory['build/composite.log']['bytes']+=1
     elif name=='snapshot-command-sha-tamper-reject':command['log_sha256']='0'*64
     elif name=='snapshot-command-size-tamper-reject':command['log_bytes']+=1
     elif name=='snapshot-parser-sha-tamper-reject':parsed['log_sha256']='0'*64
     elif name=='snapshot-parser-size-tamper-reject':parsed['log_bytes']+=1
     elif name=='snapshot-file-growth-reject':
      with path.open('ab') as writer:writer.write(b'changed')
     elif name=='snapshot-buffer-tamper-reject':snapshot['raw']=snapshot['raw']+b'changed'
     elif name=='snapshot-metadata-tamper-reject':snapshot['sha256']='0'*64
     elif name=='snapshot-missing-inventory-entry-reject':inventory={}
     else:raise ValueError('undefined snapshot case '+name)
     reject(lambda:bind_trace_snapshot(root,snapshot,parsed,inventory,command))
  elif name.startswith('trace-inventory-'):
   with tempfile.TemporaryDirectory() as tmp:
    root=Path(tmp);(root/'build').mkdir();path=root/'build/composite.log';path.write_bytes(b'SYNTHETIC');(root/'other.json').write_bytes(b'{}');snapshot=trace_snapshot(path)
    if name=='trace-inventory-complete-byte-hash-positive':require(trace_tree_inventory(root,snapshot,11)=={'build/composite.log':{'bytes':9,'sha256':sha(b'SYNTHETIC')},'other.json':{'bytes':2,'sha256':sha(b'{}')}},'complete trace and ordinary entries preserved with exact total boundary')
    elif name=='trace-inventory-oversized-log-reject':
     with path.open('wb') as stream:stream.truncate(64*1024*1024+1)
     with patch.object(Path,'open',side_effect=AssertionError('adapter must reject oversized trace before open')):reject(lambda:trace_tree_inventory(root,snapshot))
    elif name=='trace-inventory-aggregate-cap-reject':reject(lambda:trace_tree_inventory(root,snapshot,10))
    elif name=='trace-inventory-unsafe-entry-reject':
     original=Path.lstat
     def unsafe(candidate,*args,**kwargs):
      st=original(candidate,*args,**kwargs)
      return SimpleNamespace(st_file_attributes=1024,st_mode=st.st_mode) if candidate==root/'other.json' else st
     with patch.object(Path,'lstat',unsafe):reject(lambda:trace_tree_inventory(root,snapshot))
    else:raise ValueError('undefined adapter case '+name)
  elif name.startswith('bounded-log-'):
   with tempfile.TemporaryDirectory() as tmp:
    path=Path(tmp)/'trace.log';path.write_bytes(b'x'*32)
    if name=='bounded-log-exact-cap-positive':require(trace_log_bytes(path,32)==b'x'*32,'bounded exact cap retained')
    elif name=='bounded-log-one-byte-over-cap-reject':reject(lambda:trace_log_bytes(path,31))
    elif name=='bounded-log-default-64MiB-stat-reject':
     with path.open('wb') as stream:stream.truncate(64*1024*1024+1)
     with patch.object(Path,'open',side_effect=AssertionError('oversized log must reject before open')):reject(lambda:trace_log_bytes(path))
    elif name in ('bounded-log-growth-before-open-reject','bounded-log-growth-during-read-reject'):
     original_open=Path.open
     class GrowingStream:
      def __init__(self,stream):self.stream=stream
      def __enter__(self):return self
      def __exit__(self,*args):return self.stream.__exit__(*args)
      def fileno(self):return self.stream.fileno()
      def read(self,count):
       require(count==33,'growth fixture observes bounded cap-plus-one read')
       raw=self.stream.read(count)
       with builtins.open(path,'ab') as writer:writer.write(b'g')
       return raw
     def growing_open(candidate,*args,**kwargs):
      if name=='bounded-log-growth-before-open-reject':
       with builtins.open(path,'ab') as writer:writer.write(b'g')
       return original_open(candidate,*args,**kwargs)
      return GrowingStream(original_open(candidate,*args,**kwargs))
     with patch.object(Path,'open',growing_open):reject(lambda:trace_log_bytes(path,32))
    elif name=='bounded-log-directory-reject':reject(lambda:trace_log_bytes(Path(tmp),32))
    elif name in ('bounded-log-symlink-stat-reject','bounded-log-reparse-stat-reject'):
     st=path.lstat();fake=SimpleNamespace(st_mode=stat.S_IFLNK if name=='bounded-log-symlink-stat-reject' else st.st_mode,st_file_attributes=1024 if name=='bounded-log-reparse-stat-reject' else 0,st_size=st.st_size)
     with patch.object(Path,'lstat',return_value=fake):reject(lambda:trace_log_bytes(path,32))
    elif name=='bounded-log-empty-positive':path.write_bytes(b'');require(trace_log_bytes(path)==b'','empty bounded raw log materialization only; parser still independently requires complete frames')
    elif name=='bounded-log-raised-cap-reject':reject(lambda:trace_log_bytes(path,64*1024*1024+1))
    else:raise ValueError('undefined bounded-read case '+name)
  elif name=='owned-three-frame-positive':require(set(parse_trace(raw,LINKER,SOURCE,WRAPPER,cc)['selected'])==set(TARGETS),'all owned synthetic targets')
  elif name=='missing-target-header-form-positive':parse_trace(text.replace("update target 'crypto/ahash.o' due to: SYNTHETIC.c FORCE","target 'crypto/ahash.o' does not exist").encode(),LINKER,SOURCE,WRAPPER,cc)
  elif name=='resolved-linker-role-positive':parse_trace(text.replace('aarch64-linux-gnu-ld -m',LINKER['path']+' -m').encode(),LINKER,SOURCE,WRAPPER,cc)
  elif name=='raw-byte-and-line-spans-positive':
   result=parse_trace(raw,LINKER,SOURCE,WRAPPER,cc)
   for row in result['selected'].values():
    start,end=row['recipe_byte_span'];require(raw[start:end].decode()==row['raw_recipe'] and sha(raw[start:end])==row['raw_recipe_sha256'] and row['recipe_line_span'][0]<=row['recipe_line_span'][1],'raw exact recipe span/hash')
  elif name=='ordinary-CC-capture-binding-positive':
   result=parse_trace(raw,LINKER,SOURCE,WRAPPER,cc);require(result['selected'][TARGETS[0]]['commands'][1]['args']==cc[TARGETS[0]]['args'],'actual executable CC equals saved command')
  elif name in ('opaque-quoted-semicolon-positive','opaque-fake-header-text-positive'):
   payload='quoted; linker aarch64-linux-gnu-ld ;' if name=='opaque-quoted-semicolon-positive' else "file:357: update target 'crypto/shash.o' due to: fake"
   tokens=lex('echo '+q(payload));require(len(tokens)==2 and tokens[1][0]==payload and tokens[1][3],'one opaque quoted argument')
  elif name=='physical-continuation-positive':parse_trace(text.replace('; if ','; \\\nif ',1).encode(),LINKER,SOURCE,WRAPPER,cc)
  elif name=='caller-dispatch-positive':require(postprocess_commands(raw,LINKER,SOURCE,WRAPPER,saved)==parse_trace(raw,LINKER,SOURCE,WRAPPER,cc),'caller delegates exact data-only evidence')
  elif name in ('five-command-reader-binding-positive','missing-make-probe-reject','duplicate-build-command-reject','wrong-probe-argv-reject','V1-route-reject','missing-trace-route-reject','unsupported-debug-substitute-reject'):
   with tempfile.TemporaryDirectory() as tmp:
    root=Path(tmp);(root/'routing').mkdir();(root/'routing/composite.mk').write_bytes(ROUTING_WRAPPER);evidence=routing_evidence(SOURCE,OBJECTS,WRAPPER);commands=[{'command':['clang-14','--version']},{'command':['aarch64-linux-gnu-ld','--version']},{'command':['clang-14','-print-file-name=include']},{'command':['make','--version']},{'command':list(args),'make_environment':dict(MAKE_ENVIRONMENT)}]
    if name=='five-command-reader-binding-positive':verify_routing_evidence(root,evidence,SOURCE,OBJECTS,commands)
    else:
     if name=='missing-make-probe-reject':commands.pop(3)
     elif name=='duplicate-build-command-reject':commands.append(copy.deepcopy(commands[-1]))
     elif name=='wrong-probe-argv-reject':commands[3]['command']=['make','-v']
     else:
      if name=='V1-route-reject':commands[-1]['command'][commands[-1]['command'].index('V=0')]='V=1'
      elif name=='missing-trace-route-reject':commands[-1]['command'].remove('--trace')
      else:commands[-1]['command'][1]='--debug=print,why'
     reject(lambda:verify_routing_evidence(root,evidence,SOURCE,OBJECTS,commands))
  elif name in ('exact-make-profile-positive','unsupported-make-version-reject','wrong-make-binary-reject','wrong-make-path-reject','wrong-baseline-make-reject','fresh-version-mismatch-reject'):
   if name=='exact-make-profile-positive':make_profile(profile,baseline,MAKE_VERSION)
   else:
    version=MAKE_VERSION
    if name=='unsupported-make-version-reject':profile['version']=MAKE_VERSION.replace('4.3','4.4')
    elif name=='wrong-make-binary-reject':profile['sha256']='0'*64
    elif name=='wrong-make-path-reject':profile['path']='/synthetic/other/make'
    elif name=='wrong-baseline-make-reject':baseline['sha256']='0'*64
    else:version=MAKE_VERSION+'extra\n'
    reject(lambda:make_profile(profile,baseline,version))
  elif name=='trace-V0-j2-argv-positive':require(args[:3]==['make','--trace','-C'] and 'V=0' in args and '-j2' in args and 'V=1' not in args,'only reviewed trace/verbosity delta')
  elif name=='new-public-helper-fixture-closure':require(all('note10/device_test/'+n in PUBLIC for n in ('crypto_hash_trace.py','test_crypto_hash_trace.py')),'exact new public files')
  elif name=='branch-execution-claim-remains-false':
   result=parse_trace(raw,LINKER,SOURCE,WRAPPER,cc);require(result['conditional_branch_execution_observed'] is False and all(r['conditional_branch_execution_observed'] is False for r in result['selected'].values()),'expanded clauses never branch execution proof')
  else:
   if name.startswith('missing-') and name.endswith('-frame-reject') and name!='missing-wrapper-frame-reject':text=text.replace(blocks['crypto/'+name.split('-')[1]+'.o' if 'composite' not in name else TARGETS[2]],'')
   elif name=='duplicate-stock-frame-reject':text+=blocks[TARGETS[0]]
   elif name=='unframed-linker-reject':text='\n'.join(line for line in text.splitlines() if ': update target ' not in line)+'\n'
   elif name=='wrong-stock-file-reject':text=text.replace('/scripts/Makefile.build:357','/scripts/other.mk:357',1)
   elif name=='wrong-stock-line-reject':text=text.replace('Makefile.build:357','Makefile.build:999',1)
   elif name=='cross-target-body-reject':text=text.replace("target 'crypto/ahash.o'", "target 'crypto/shash.o'",1)
   elif name=='missing-wrapper-frame-reject':text=text.replace(route,'')
   elif name=='wrong-wrapper-line-reject':text=text.replace('composite.mk:2','composite.mk:3')
   elif name=='wrong-wrapper-target-reject':text=text.replace("composite.mk:2: update target 'crypto/crypto_hash.o'","composite.mk:2: update target 'crypto/ahash.o'")
   elif name in ('runtime-echo-only-reject','printf-linker-only-reject','fixdep-linker-only-reject'):
    recipe=blocks[TARGETS[0]].splitlines()[1];payload='aarch64-linux-gnu-ld -m aarch64linux --no-relax -r -o crypto/ahash.o crypto/.tmp_ahash.o -T crypto/.tmp_ahash.ver';replacement={'runtime-echo-only-reject':'echo '+q(payload),'printf-linker-only-reject':"printf '%s\\n' "+q(payload),'fixdep-linker-only-reject':'scripts/basic/fixdep dep target '+q(payload)}[name];text=text.replace(recipe,'set -e; '+replacement+';')
   elif name=='interleaved-selected-line-reject':text=text.replace('  CC      crypto/ahash.o\n','compiler diagnostic from foreign task\n',1)
   elif name=='truncated-quote-reject':text=text.replace("echo '  CC      crypto/ahash.o'", "echo '  CC      crypto/ahash.o",1)
   elif name=='truncated-continuation-reject':text=text[:text.index('set -e;')]+'set -e; \\\n'
   elif name=='missing-final-newline-reject':text=text[:-1]
   elif name=='unknown-header-form-reject':text=text.replace("update target 'crypto/ahash.o' due to:","unsupported 'crypto/ahash.o':",1)
   elif name=='shell-substitution-reject':text=text.replace('set -e;','set -e; $(unknown);',1)
   elif name=='backtick-substitution-reject':text=text.replace('set -e;','set -e; `unknown`;',1)
   elif name=='unknown-command-role-reject':text=text.replace('scripts/basic/fixdep ','unknown/fixdep ',1)
   elif name=='unknown-control-operator-reject':text=text.replace('; if ',' && if ',1)
   elif name=='wrong-leaf-flag-reject':text=text.replace('--no-relax -r -o crypto/ahash.o','--relax -r -o crypto/ahash.o',1)
   elif name=='wrong-temp-input-reject':text=text.replace('crypto/ahash.o crypto/.tmp_ahash.o -T','crypto/ahash.o crypto/wrong.o -T',1)
   elif name=='wrong-version-script-reject':text=text.replace('-T crypto/.tmp_ahash.ver','-T crypto/wrong.ver',1)
   elif name=='wrong-composite-order-reject':text=text.replace('-o crypto/crypto_hash.o crypto/ahash.o crypto/shash.o','-o crypto/crypto_hash.o crypto/shash.o crypto/ahash.o')
   elif name=='extra-composite-input-reject':text=text.replace('-o crypto/crypto_hash.o crypto/ahash.o crypto/shash.o','-o crypto/crypto_hash.o crypto/ahash.o crypto/shash.o crypto/extra.o')
   elif name=='missing-genksyms-reject':text=text.replace(' | scripts/genksyms/genksyms -r /dev/null','',1)
   elif name=='wrong-genksyms-role-reject':text=text.replace('scripts/genksyms/genksyms','unknown/genksyms',1)
   elif name=='missing-guard-reject':text=text.replace('if aarch64-linux-gnu-objdump -h crypto/.tmp_ahash.o | grep -q __ksymtab; then ','',1)
   elif name=='wrong-guard-symbol-reject':text=text.replace('grep -q __ksymtab','grep -q wrong',1)
   elif name=='missing-cleanup-reject':text=text.replace('rm -f crypto/.tmp_ahash.o crypto/.tmp_ahash.ver; ','',1)
   elif name=='missing-else-move-reject':text=text.replace('else mv -f crypto/.tmp_ahash.o crypto/ahash.o; ','',1)
   elif name=='wrong-CC-command-reject':text=text.replace('; clang-14 -DSYNTHETIC=1','; clang-14 -DSYNTHETIC=2',1)
   elif name=='wrong-fixdep-capture-reject':text=text.replace(q(cc[TARGETS[0]]['text']),q('foreign command'),1)
   elif name=='missing-composite-capture-reject':text=text.replace("; printf '%s\\n' "+q('cmd_'+TARGETS[2]+' := '+' '.join(['aarch64-linux-gnu-ld','-m','aarch64linux','--no-relax','-r','-o',TARGETS[2],*TARGETS[:2]]))+' > crypto/.crypto_hash.o.cmd','')
   elif name=='extra-trailing-command-reject':text=text.replace('; fi;','; fi; unknown;',1)
   else:raise ValueError('undefined new trace case '+name)
   reject(lambda:parse_trace(text.encode(),LINKER,SOURCE,WRAPPER,cc))
  completed.append(name)
 return {'passed':True,'cases':completed,'case_count':len(completed),'synthetic_only':True,'conditional_branch_execution_observed':False,'prior120_42_53_58_16_import_or_replay':False,'make_shell_dryrun_compiler_object_parse_network_API_device_execution':False}


def main():
 p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--checkpoint',type=Path,required=True);p.add_argument('--checkpoint-sha256',required=True);p.add_argument('--inventory',type=Path,required=True);p.add_argument('--inventory-sha256',required=True);a=p.parse_args();root=Path(__file__).resolve().parents[2];require=lambda ok,msg:(_ for _ in ()).throw(ValueError(msg)) if not ok else None;require(not a.output.exists() and a.output.absolute().is_relative_to(root/'note10/private'),'fresh private CP5 result');completed=[];phase='attribution';attribution={'checkpoint_path':str(a.checkpoint.absolute()),'inventory_path':str(a.inventory.absolute())}
 try:
  cpraw=a.checkpoint.read_bytes();invraw=a.inventory.read_bytes();require(sha(cpraw)==a.checkpoint_sha256 and sha(invraw)==a.inventory_sha256,'exact frozen CP5 checkpoint/inventory SHA256');cp=json.loads(cpraw);inventory=json.loads(invraw);attribution.update(checkpoint_sha256=sha(cpraw),inventory_sha256=sha(invraw));require(cp['version']=='v65' and cp['checkpoint']==5 and cp['new_trace_fixture_inventory']==list(CASES) and inventory['cases']==list(CASES) and inventory['case_count']==len(CASES) and inventory['fixture_sha256']==sha(Path(__file__).read_bytes()),'exact new-only CP5 ordered inventory')
  for group in ('public_sources_sha256','private_sources_sha256','shared_sources_sha256'):
   for name,expected in cp[group].items():require(sha((root/name).read_bytes())==expected,'current frozen source/import closure')
  phase='new_trace_cases';result=run_cases(completed);result.update(attribution)
 except BaseException as error:
  a.output.parent.mkdir(parents=True,exist_ok=True)
  with a.output.open('x',encoding='utf8',newline='\n') as stream:stream.write(json.dumps(dict(attribution,passed=False,cases=completed,case_count=len(completed),completed_case_names=completed,completed_case_count=len(completed),failing_next_case=CASES[len(completed)] if len(completed)<len(CASES) else None,failure_phase=phase,exception_type=type(error).__name__,exception_message=str(error),automatic_retry=False),indent=2)+'\n')
  raise
 a.output.parent.mkdir(parents=True,exist_ok=True)
 with a.output.open('x',encoding='utf8',newline='\n') as stream:stream.write(json.dumps(result,indent=2)+'\n')
if __name__=='__main__':main()
