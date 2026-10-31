"""Bounded GNU Make 4.3 trace data parsing; never executes captured text."""
import hashlib,re

LOG_CAP=64*1024*1024
RECIPE_CAP=2*1024*1024
TOKEN_CAP=65536
TARGETS=('crypto/ahash.o','crypto/shash.o','crypto/crypto_hash.o')
MAKE_PATH='/usr/bin/make'
MAKE_SHA='92f646030615cd98490a68a94c0aefd87b552be3158b941c02e43b0bfdb576db'
MAKE_VERSION='GNU Make 4.3\nBuilt for x86_64-pc-linux-gnu\nCopyright (C) 1988-2020 Free Software Foundation, Inc.\nLicense GPLv3+: GNU GPL version 3 or later <http://gnu.org/licenses/gpl.html>\nThis is free software: you are free to change and redistribute it.\nThere is NO WARRANTY, to the extent permitted by law.\n'


def need(ok,message):
 if not ok:raise ValueError(message)


def sha(raw):return hashlib.sha256(raw).hexdigest()


def make_profile(profile,baseline,version):
 need(profile=={'role':'make','path':MAKE_PATH,'sha256':MAKE_SHA,'version':MAKE_VERSION},'exact supported GNU Make 4.3 executable/full version profile')
 need(baseline['path']==MAKE_PATH and baseline['sha256']==MAKE_SHA and version==MAKE_VERSION,'same protected baseline make binary and fresh full version output')
 return profile


def lex(text):
 """Finite shell words/operators with raw spans; quoted payloads stay opaque."""
 need(len(text.encode())<=RECIPE_CAP,'bounded selected logical recipe');out=[];i=0
 while i<len(text):
  if text[i].isspace():i+=1;continue
  start=i
  if text[i] in ';|<>':
   value=text[i];i+=1;need(i==len(text) or text[i]!=value,'no unsupported doubled shell operator');out.append((value,start,i,False));continue
  need(text[i] not in '&(){}#`$','unsupported shell operator/substitution');value='';quoted=False
  while i<len(text) and not text[i].isspace() and text[i] not in ';|<>':
   ch=text[i]
   if ch in "'\"":
    quote=ch;quoted=True;i+=1
    while i<len(text) and text[i]!=quote:
     if quote=='"':need(text[i] not in '$`\\','no dynamic double quoted payload')
     value+=text[i];i+=1
    need(i<len(text),'complete shell quote');i+=1
   elif ch=='\\':
    i+=1;need(i<len(text),'complete shell escape');value+=text[i];i+=1
   else:need(ch not in '&(){}#`$','no dynamic shell syntax');value+=ch;i+=1
  out.append((value,start,i,quoted));need(len(out)<=TOKEN_CAP,'bounded token count')
 return out


class Recipe:
 def __init__(self,text):self.text=text;self.tokens=lex(text);self.i=0;self.commands=[]
 def literal(self,*values):
  for value in values:
   need(self.i<len(self.tokens) and self.tokens[self.i][0]==value and not self.tokens[self.i][3],'exact stock shell control/operator '+value);self.i+=1
 def command(self,expected,redirect=None):
  begin=self.i
  while self.i<len(self.tokens) and self.tokens[self.i][0] not in (';','|','>','<'):self.i+=1
  selected=self.tokens[begin:self.i];args=[t[0] for t in selected]
  need(args==expected and selected and not selected[0][3],'exact owned executable command position')
  self.commands.append({'args':args,'character_span':[selected[0][1],selected[-1][2]]})
  if redirect is not None:self.literal('>',redirect)
 def echo(self,label):self.command(['echo',label]);self.literal(';')
 def end(self):need(self.i==len(self.tokens),'no unknown or trailing executable recipe syntax')


def selected_recipe(text,target,linker,cc=None):
 r=Recipe(text);r.literal('set','-e',';')
 if target==TARGETS[2]:
  r.echo('  LD      '+target);args=['aarch64-linux-gnu-ld','-m','aarch64linux','--no-relax','-r','-o',target,*TARGETS[:2]]
  if r.tokens[r.i][0]==linker['path']:args[0]=linker['path']
  r.command(args);r.literal(';');need(r.i+2<len(r.tokens),'complete composite capture');payload=r.tokens[r.i+2][0];need(r.tokens[r.i+2][3] and payload.split()==['cmd_'+target,':=',*args],'opaque composite saved command data');r.command(['printf','%s\\n',payload],'crypto/.crypto_hash.o.cmd');r.end()
 else:
  saved_text=cc['text'];cc=cc['args'];stem=target.split('/')[-1][:-2];tmp='crypto/.tmp_'+stem+'.o';ver='crypto/.tmp_'+stem+'.ver';dep='crypto/.'+stem+'.o.d';saved='crypto/.'+stem+'.o';need(type(cc) is list and cc and cc[0]=='clang-14' and cc[-4:-1]==['-c','-o',tmp] and cc[-1].endswith('/crypto/'+stem+'.c'),'owned complete saved compiler argv')
  r.echo('  CC      '+target);r.command(cc);r.literal(';')
  # fixdep receives the complete command as one opaque argument, never reparsed.
  need(r.i+3<len(r.tokens),'complete fixdep');payload=r.tokens[r.i+3][0]
  need(r.tokens[r.i+3][3] and payload.strip()==saved_text.strip(),'quoted fixdep capture binds saved compiler command')
  r.command(['scripts/basic/fixdep',dep,target,payload],saved+'.tmp');r.literal(';');r.command(['rm','-f',dep]);r.literal(';');r.command(['mv','-f',saved+'.tmp',saved+'.cmd']);r.literal(';','if')
  r.command(['aarch64-linux-gnu-objdump','-h',tmp]);r.literal('|');r.command(['grep','-q','__ksymtab']);r.literal(';','then')
  cpp=[cc[0],'-E','-D__GENKSYMS__',*cc[1:-4],cc[-1]];r.command(cpp);r.literal('|');r.command(['scripts/genksyms/genksyms','-r','/dev/null'],ver);r.literal(';')
  args=['aarch64-linux-gnu-ld','-m','aarch64linux','--no-relax','-r','-o',target,tmp,'-T',ver]
  if r.tokens[r.i][0]==linker['path']:args[0]=linker['path']
  r.command(args);r.literal(';');r.command(['rm','-f',tmp,ver]);r.literal(';','else');r.command(['mv','-f',tmp,target]);r.literal(';','fi',';');r.end()
 return {'args':args,'commands':r.commands,'conditional_branch_execution_observed':False}


HEADER=re.compile(r"^(?P<file>.+):(?P<line>[1-9][0-9]*): (?:(?:update target '(?P<update>[^']+)' due to: (?P<reason>.*))|(?:target '(?P<missing>[^']+)' does not exist))$")


def parse_trace(raw,linker,source,wrapper,cc_commands):
 need(type(raw) is bytes and len(raw)<=LOG_CAP and b'\x00' not in raw,'bounded complete trace bytes');text=raw.decode('utf8',errors='strict');need(text.endswith('\n'),'complete trace final line');need(source.startswith('/') and wrapper.startswith('/') and set(cc_commands)==set(TARGETS[:2]),'exact mapped source/wrapper and two saved CC commands');lines=text.splitlines(keepends=True);frames=[];offset=0;current=None
 for number,line in enumerate(lines,1):
  body=line.rstrip('\n');m=HEADER.fullmatch(body)
  if m:
   current={'file':m['file'],'line':int(m['line']),'target':m['update'] or m['missing'],'reason':m['reason'],'header':body,'header_byte_span':[offset,offset+len(line.encode())],'header_line':number,'lines':[]};frames.append(current)
  elif current is not None:current['lines'].append((number,offset,line))
  offset+=len(line.encode())
 need(len(frames)<=100000,'bounded trace frame count');result={};route=[]
 for frame in frames:
  target=frame['target']
  if target not in TARGETS:continue
  if frame['file']==wrapper:
   need(target==TARGETS[2] and frame['line']==2,'exact wrapper delegation ownership');route.append(frame);continue
  need(frame['file']==source+'/scripts/Makefile.build' and frame['line'] in ((355,356,357) if target in TARGETS[:2] else (652,653)),'exact owned stock target/file/line');need(target not in result,'unique selected stock frame')
  candidates=[];i=0;items=frame['lines']
  while i<len(items):
   n,start,physical=items[i];logical=physical;last=n;i+=1
   while logical.endswith('\\\n'):
    need(i<len(items),'complete recipe continuation');nextn,_,more=items[i];logical=logical[:-2]+' '+more;last=nextn;i+=1
   stripped=logical.strip()
   if stripped.startswith('set -e;'):
    need(len(logical.encode())<=RECIPE_CAP,'bounded recipe');candidates.append((n,last,start,items[i-1][1]+len(items[i-1][2].encode()),logical.rstrip('\n')))
   else:need(not stripped or stripped==':' or stripped in ('CC      '+target,'LD      '+target) or re.fullmatch(r"make(?:\[[0-9]+\])?: (?:Entering|Leaving) directory '.*'",stripped),'no interleaved/unowned selected frame output')
  need(len(candidates)==1,'one full actual expanded selected recipe');first,last,start,end,recipe=candidates[0];parsed=selected_recipe(recipe,target,linker,cc_commands.get(target));parsed.update(frame={k:v for k,v in frame.items() if k!='lines'},recipe_byte_span=[start,end],recipe_line_span=[first,last],raw_recipe_sha256=sha(raw[start:end]),raw_recipe=raw[start:end].decode(),expanded_Kbuild_recipe_line=recipe);result[target]=parsed
 need(set(result)==set(TARGETS) and len(route)==1,'all three unique stock frames and one wrapper delegation');return {'schema':1,'make_trace_scope':'selected_and_expanded_recipe_only','conditional_branch_execution_observed':False,'log_sha256':sha(raw),'log_bytes':len(raw),'wrapper_frame':{k:v for k,v in route[0].items() if k!='lines'},'selected':result}
