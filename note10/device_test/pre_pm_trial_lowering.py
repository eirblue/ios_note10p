"""Finite static AAPCS64 dataflow for the observed full-prefix equality lowering."""
import re
from prepare_pre_pm_trial import require
from pre_pm_trial_decode import validate_word
AFFECTED=0x22b0000

def advance_obligation(state,event,obligations):
 require(type(state) is int and 0<=state<=len(obligations),'finite obligation state')
 return state+1 if state<len(obligations) and event is not None and event==obligations[state] else state

def operands(row):return row['operands'].split('//',1)[0].strip().lower()
def reg(name):
 name=name.strip()
 if name in ('xzr','wzr'):return 31
 m=re.fullmatch(r'[xw]([0-9]|[12][0-9]|30)',name);require(m is not None,'finite argument-flow register');return int(m[1])
def atom_union(a,b):
 def terms(x):return x[1] if isinstance(x,tuple) and x[0]=='or' else frozenset([x])
 return ('or',terms(a)|terms(b))
def restore_lowering(code,calls,trial):
 before=[o for o,r in code.items() if o<trial and (r['mnemonic']=='b' or r['mnemonic'].startswith('b.') or r['mnemonic'] in ('ret','cbz','cbnz','tbz','tbnz'))]
 start=max(before)+4 if before else min(code)
 registers={i:('entry-register',i) for i in range(31)};memory={};flags=None
 def low32(value):
  if isinstance(value,int):return value&0xffffffff
  return value if value[0] in ('return','not-equal','or','low32') else ('low32',value)
 def read(name):
  if name=='sp':return ('stack-pointer',0)
  i=reg(name);value=0 if i==31 else registers[i];return low32(value) if name.startswith('w') else value
 def put(name,value):
  i=reg(name)
  if i!=31:registers[i]=low32(value) if name.startswith('w') else value&0xffffffffffffffff if isinstance(value,int) else value
 def immediate(value):return int(value.removeprefix('#'),0)
 def location(text):
  m=re.fullmatch(r'\[(sp|x(?:[0-9]|[12][0-9]|30))(?:,\s*#(-?(?:0x[0-9a-f]+|[0-9]+)))?\]',text)
  require(m is not None,'finite tracked stack/frame load/store operand');return read(m[1]),int(m[2] or '0',0)
 window=backup=None;restore=None;comparison=None;barrier=None;hashes=[];guards=[];decision=None;comparison_boolean=None;word_checks=[]
 for off in range(start,max(code)+4,4):
  require(off in code,'contiguous observed argument-flow block');r=code[off];word_checks.append(validate_word(r));m=r['mnemonic'];text=operands(r);parts=[p.strip() for p in text.split(',')]
  if off>trial and (m.startswith('b.') or m in ('cbz','cbnz','tbz','tbnz','b','ret')):
   require(m=='cbnz' and parts[0].startswith('w'),'aggregate nonzero failure branch required')
   expected={('return',p) for p in hashes+guards}|{('not-equal',comparison)}
   value=read(parts[0]);require(value==('or',frozenset(expected)) and len(hashes)==2 and len(guards)==2 and comparison is not None and comparison_boolean is not None,'all full hash/byte/guard results feed unmasked nonzero rejection')
   decision=off;break
  if m=='bl':
   require(off in calls,'actual direct-call target required');target=calls[off]
   if off==trial:
    require(target=='n10_rt_trial','actual production trial target');window=read('x6');backup=memory.get((read('sp'),0));require(backup is not None and window!=backup and read('x7')==0x10000000 and memory.get((read('sp'),8))==AFFECTED,'actual trial window/backup ABI and bounded capacities')
   elif off>trial:
    if target in ('memcpy','__memcpy'):
     require(restore is None and read('x0')==window and read('x1')==backup and read('x2')==AFFECTED,'actual unconditional whole-prefix restore arguments');restore=off
    elif target=='n10_pre_pm_hash':
     require(restore is not None and barrier is not None and len(hashes)<2 and read('x1')==(backup if not hashes else window),'backup then window hash pointer dataflow');hashes.append(off)
    elif target in ('memcmp','bcmp'):
     require(comparison is None and len(hashes)==2 and read('x0')==window and read('x1')==backup and read('x2')==AFFECTED,'full-prefix equality arguments must match restore and trial ABI');comparison=off
    elif target=='n10_pre_pm_guard':
     require(comparison is not None and len(guards)<2 and read('w1')==(0xa5 if not guards else 0x5a),'both sequenced full-page guard calls');guards.append(off)
    else:raise ValueError('unexpected call before complete post-restore aggregate')
   for i in range(19):registers[i]=('return',off) if i==0 else ('call-clobbered',off,i)
   flags=None;continue
  if m in ('dsb','dmb'):
   require(off>trial and restore is not None and text in ('sy','ish'),'actual post-restore memory barrier');barrier=off;continue
  if m=='mov':put(parts[0],immediate(parts[1]) if parts[1].startswith('#') else read(parts[1]));continue
  if m=='movk':
   shift=int(parts[2].split('#')[1]) if len(parts)==3 else 0;old=read(parts[0]);require(isinstance(old,int),'known immediate MOVK chain');put(parts[0],(old&~(0xffff<<shift))|(immediate(parts[1])<<shift));continue
  if m=='add':
   a=read(parts[1]);b=immediate(parts[2]) if parts[2].startswith('#') else read(parts[2]);put(parts[0],('address-add',a,b));continue
  if m in ('ldr','ldur'):
   destination,address=text.split(',',1);loc=location(address.strip());put(destination.strip(),memory.get(loc,('memory',*loc)));continue
  if m in ('str','stur'):
   source,address=text.split(',',1);memory[location(address.strip())]=read(source.strip());continue
  if m=='stp':
   first,second,address=text.split(',',2);loc=location(address.strip());memory[loc]=read(first.strip());memory[loc[0],loc[1]+8]=read(second.strip());continue
  if m=='cmp':
   require(parts[1]=='#0','only observed zero comparison in postcheck block');flags=('zero-test',read(parts[0]));continue
  if m=='cset':
   require(parts[1]=='ne' and flags==('zero-test',('return',comparison)) and comparison is not None,'byte comparator only observed through zero/nonzero equality');comparison_boolean=off;put(parts[0],('not-equal',comparison));continue
  if m=='orr':put(parts[0],atom_union(read(parts[1]),read(parts[2])));continue
  raise ValueError('unsupported instruction in finite post-trial argument/aggregate proof: '+m)
 require(restore is not None and barrier is not None and comparison is not None and decision is not None,'complete actual lowering contract')
 return {'independent_word_fields_checked':True,'word_checked_instructions':word_checks,'trial_call_offset':trial,'restore_call_offset':restore,'comparison_call_offset':comparison,'comparison_target':calls[comparison],
 'compared_bytes':AFFECTED,'restore_and_compare_arguments_equal_trial_window_backup':True,'comparison_zero_only_use_offset':comparison_boolean,
 'hash_call_offsets':hashes,'guard_call_offsets':guards,'post_restore_barrier_offset':barrier,'unmasked_aggregate_nonzero_rejection_offset':decision,
 'source_expression':'memcmp(window, backup, N10_PRE_PM_AFFECTED) != 0','kernel_bcmp_semantics_required':calls[comparison]=='bcmp','execution_or_physical_safety_claim':False}

def bcmp_source_proof(header,source):
 # Both complete files are separately compared with the fixed kernel archive.
 def clean(raw):return re.sub(r'/\*.*?\*/|//[^\n]*','',raw.decode('utf8'),flags=re.S)
 declaration=clean(header);implementation=clean(source)
 require(len(re.findall(r'extern\s+int\s+bcmp\s*\(\s*const\s+void\s*\*\s*,\s*const\s+void\s*\*\s*,\s*__kernel_size_t\s*\)\s*;',declaration))==1,'real kernel bcmp declaration')
 body=re.findall(r'int\s+bcmp\s*\(\s*const\s+void\s*\*a\s*,\s*const\s+void\s*\*b\s*,\s*size_t\s+len\s*\)\s*\{([^{}]*)\}',implementation)
 require(len(body)==1 and re.sub(r'\s+','',body[0])=='returnmemcmp(a,b,len);','kernel bcmp fallback forwards exact complete spans to memcmp')
 require(len(re.findall(r'EXPORT_SYMBOL\s*\(\s*bcmp\s*\)\s*;',implementation))==1,'real bcmp export source')
 import hashlib
 return {'source_sha256':{'include/linux/string.h':hashlib.sha256(header).hexdigest(),'lib/string.c':hashlib.sha256(source).hexdigest()},
  'declaration':'int bcmp(const void *, const void *, __kernel_size_t)','fallback_body':'return memcmp(a, b, len);','zero_iff_equal_semantics':True,
  'scope':'pinned source declaration and fallback semantics only; provider object/link/runtime availability unproven','provider_object_built':False,'runtime_provider_availability_proven':False}
