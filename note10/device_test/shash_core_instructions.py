"""Finite word-derived GPR facts for the new shash object; no target execution."""
from pre_pm_archive_contract import require

def signed(value,bits):return value-(1<<bits) if value>>(bits-1) else value

def logical_mask(word,width):
 n=(word>>22)&1;imms=(word>>10)&63;immr=(word>>16)&63;length=((n<<6)|(~imms&63)).bit_length()-1
 require(length>=1,'logical immediate encoding');esize=1<<length;levels=esize-1;s=imms&levels;r=immr&levels
 require(s!=levels and esize<=width,'reserved logical immediate');element=(1<<(s+1))-1;element=((element>>r)|(element<<(esize-r)))&((1<<esize)-1)
 return sum(element<<i for i in range(0,width,esize))

def decode(word):
 require(type(word) is int and 0<=word<1<<32,'finite instruction word');rd=word&31;rn=(word>>5)&31;rm=(word>>16)&31;width=64 if word>>31 else 32
 if word==0xd503201f:return {'op':'nop'}
 if word==0xd65f03c0:return {'op':'ret'}
 if word&0xfffffc1f in (0xd63f0000,0xd61f0000):return {'op':'blr' if word&0xfffffc1f==0xd63f0000 else 'br','rn':rn}
 if word>>26 in (5,37):return {'op':'bl' if word>>26==37 else 'b','delta':signed(word&0x3ffffff,26)*4}
 if word&0xff000010==0x54000000:return {'op':'cond','delta':signed((word>>5)&0x7ffff,19)*4,'condition':word&15}
 if word&0x7e000000==0x34000000:return {'op':'cb','rn':rd,'delta':signed((word>>5)&0x7ffff,19)*4,'nonzero':bool(word&(1<<24)),'width':width}
 if word&0x7e000000==0x36000000:return {'op':'tb','rn':rd,'delta':signed((word>>5)&0x3fff,14)*4,'bit':((word>>26)&32)|((word>>19)&31),'nonzero':bool(word&(1<<24))}
 if word&0x9f000000==0x90000000:return {'op':'adrp','rd':rd}
 if word&0x1f000000==0x11000000:return {'op':'sub' if word&(1<<30) else 'add','rd':rd,'rn':rn,'imm':((word>>10)&4095)<<(12 if word&(1<<22) else 0),'flags':bool(word&(1<<29)),'width':width}
 if word&0x7fe0ffe0==0x2a0003e0:return {'op':'mov','rd':rd,'rn':rm,'width':width}
 if word&0x1f800000==0x12800000:
  opc=(word>>29)&3;require(opc in (0,2,3),'reserved wide move');return {'op':('movn','invalid','movz','movk')[opc],'rd':rd,'imm':((word>>5)&65535)<<(((word>>21)&3)*16),'shift':((word>>21)&3)*16,'width':width}
 if word&0x1f800000==0x12000000:return {'op':('and','orr','eor','ands')[(word>>29)&3],'rd':rd,'rn':rn,'imm':logical_mask(word,width),'width':width}
 if word&0x3b000000==0x39000000 and not word&(1<<26):
  opc=(word>>22)&3
  if opc in (0,1):return {'op':'load' if opc else 'store','rd':rd,'rn':rn,'offset':((word>>10)&4095)*(1<<((word>>30)&3)),'size':1<<((word>>30)&3)}
 if word&0x3b200c00==0x38000000 and not word&(1<<26):
  opc=(word>>22)&3
  if opc in (0,1):return {'op':'load' if opc else 'store','rd':rd,'rn':rn,'offset':signed((word>>12)&511,9),'size':1<<((word>>30)&3)}
 if word&0x3a000000==0x28000000 and not word&(1<<26):return {'op':'pair-load' if word&(1<<22) else 'pair-store','rd':rd,'rt2':(word>>10)&31,'rn':rn}
 return {'op':'unknown','word':word}

def add(base,offset):
 if base is None:return None
 if not offset:return base
 if isinstance(base,int):return base+offset
 if isinstance(base,tuple) and base[0]=='add':return add(base[1],base[2]+offset)
 return ('add',base,offset)

def load(base,offset,size):return None if base is None else ('load',add(base,offset),size)

def bitop(op,value,constant,width):
 if value is None:return None
 if isinstance(value,int):return {'and':value&constant,'ands':value&constant,'orr':value|constant,'eor':value^constant}[op]&((1<<width)-1)
 return (op,value,constant,width)

def narrow(value,width):
 if width==64 or value is None:return value
 if isinstance(value,int):return value&0xffffffff
 if isinstance(value,tuple) and (value[0]=='load' and value[2]<=4 or value[0]=='return' or value==('arg',1)):return value
 # A W-register write must not silently preserve a symbolic 64-bit pointer.
 return None

def trace(words,relocations,call_targets):
 """Conservative finite CFG join. Unknown word destroys tracked values, never asserts preservation."""
 require(words and all(off%4==0 for off in words),'finite aligned function words');start=min(words);end=max(words)+4;states={start:{i:('arg',i) for i in range(8)}};pending=[start];events={};steps=0
 while pending:
  off=pending.pop();steps+=1;require(steps<=len(words)*128,'bounded static dataflow convergence');regs=dict(states[off]);d=decode(words[off]);op=d['op'];event={'offset':off,'decoded':d};rel=relocations.get(off)
  def get(r):return 0 if r==31 else regs.get(r)
  def put(r,value):
   if r!=31:
    if value is None:regs.pop(r,None)
    else:regs[r]=value
  if op in ('add','sub'):
   event['source_value']=get(d['rn'])
   if rel is not None:require(op=='add' and rel['type']==277 and regs.get(d['rn'])==('address',rel['identity']),'actual ADRP/ADD exact relocation pair');value=('address',rel['identity'])
   else:value=add(narrow(get(d['rn']),d['width']),d['imm']*(-1 if op=='sub' else 1))
   put(d['rd'],value)
  elif op=='adrp':require(rel is not None and rel['type']==275,'actual typed ADRP relocation');put(d['rd'],('address',rel['identity']))
  elif op=='mov':event['source_value']=get(d['rn']);put(d['rd'],narrow(get(d['rn']),d['width']))
  elif op in ('movz','movn'):put(d['rd'],d['imm'] if op=='movz' else (~d['imm'])&((1<<d['width'])-1))
  elif op=='movk':
   old=get(d['rd']);put(d['rd'],((old&~(65535<<d['shift']))|d['imm']) if isinstance(old,int) else None)
  elif op in ('and','ands','orr','eor'):put(d['rd'],bitop(op,get(d['rn']),d['imm'],d['width']))
  elif op=='load':event['address']=add(get(d['rn']),d['offset']);put(d['rd'],load(get(d['rn']),d['offset'],d['size']))
  elif op=='store':event.update(address=add(get(d['rn']),d['offset']),value=get(d['rd']),size=d['size'])
  elif op=='pair-load':
   if d['rn']!=31:regs={}
   else:put(d['rd'],None);put(d['rt2'],None)
  elif op=='pair-store':
   if d['rn']!=31:regs={}
  elif op in ('bl','blr','br') or op=='b' and off in call_targets:
   event.update(arguments=[get(i) for i in range(8)],target=call_targets.get(off) if op in ('bl','b') else get(d['rn']))
   if op not in ('br','b'):
    for i in range(19):regs.pop(i,None)
    put(0,('return',off,call_targets.get(off)))
  elif op in ('cb','tb'):event['condition_value']=get(d['rn'])
  elif op=='unknown':regs={}
  events[off]=event
  successors=[] if op in ('ret','br') else [off+4]
  if op=='b':successors=[off+d['delta']] if off not in call_targets else []
  elif op in ('cond','cb','tb'):successors.append(off+d['delta'])
  for target in successors:
   require(target in words,'actual function CFG does not escape or fall off')
   if target not in states:states[target]=dict(regs);pending.append(target)
   else:
    joined={r:v for r,v in states[target].items() if r in regs and regs[r]==v}
    if joined!=states[target]:states[target]=joined;pending.append(target)
 return [events[n] for n in sorted(events)]
