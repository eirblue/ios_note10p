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
 if word&0xffe00c00==0x1a800000 and (word>>12)&15==12:return {'op':'csel32gt','rd':rd,'rn':rn,'rm':rm,'condition':12,'width':32}
 if word&0xffe0fc1f==0xeb00001f:return {'op':'cmpreg64','rn':rn,'rm':rm,'width':64,'flags':True}
 if word&0xffe08000==0x9ba00000:return {'op':'umaddl','rd':rd,'rn':rn,'rm':rm,'ra':(word>>10)&31,'input_width':32,'accumulator_width':64,'width':64}
 if word&0xffe00c00==0xb8000c00 and rn!=31 and rn!=rd:return {'op':'store','rd':rd,'rn':rn,'offset':signed((word>>12)&511,9),'size':4,'mode':'preindex','writeback':True,'base_width':64}
 if word&0xffe0fc1f==0xea00001f:return {'op':'tst64','rn':rn,'rm':rm,'width':64,'flags':True}
 if word&0xffe0fc00==0x2a000000:return {'op':'orr32reg','rd':rd,'rn':rn,'rm':rm,'width':32}
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

def compare_provenance(left,right,width,origin):
 return {'operation':'subtract','left':left,'right':right,'width':width,'origin':origin}

def compare_nzcv(left,right,width):
 if width not in (32,64) or type(left) is not int or type(right) is not int:return None
 mask=(1<<width)-1;a=left&mask;b=right&mask;result=(a-b)&mask;sign=1<<(width-1)
 return {'N':bool(result&sign),'Z':result==0,'C':a>=b,'V':bool((a^b)&(a^result)&sign)}

def csel32_gt(left,right,flags):
 if not isinstance(flags,dict) or flags.get('operation')!='subtract' or type(flags.get('origin')) is not int:return None
 actual=compare_nzcv(flags.get('left'),flags.get('right'),flags.get('width',0))
 if actual is not None:
  chosen=left if not actual['Z'] and actual['N']==actual['V'] else right
  return chosen&0xffffffff if type(chosen) is int else None
 if flags.get('width')==32 and flags.get('left')==left==('arg',1) and flags.get('right')==0 and right==0:return ('zero_extended_signed_positive_clamp32',('arg',1))
 return None

def umaddl_value(left,right,accumulator):
 if not all(type(value) is int for value in (left,right,accumulator)):return None
 return ((left&0xffffffff)*(right&0xffffffff)+(accumulator&0xffffffffffffffff))&0xffffffffffffffff

def orr32_value(left,right):
 if left is None or right is None:return None
 if type(left) is int and type(right) is int:return (left|right)&0xffffffff
 # Bit provenance only. In particular, an argument/pointer is never retained as itself.
 a=left&0xffffffff if type(left) is int else ('low32',left)
 b=right&0xffffffff if type(right) is int else ('low32',right)
 return ('zero_extend32',('or32',a,b))

def and64_flags(left,right,origin):
 result=(left&right)&0xffffffffffffffff if type(left) is int and type(right) is int else None
 return {'operation':'and','left':left,'right':right,'width':64,'origin':origin,'N':None if result is None else bool(result&(1<<63)),'Z':None if result is None else result==0,'C':False,'V':False}

def preindex_address(base,offset):
 if base is None:return None
 if type(base) is int:return (base+offset)&0xffffffffffffffff
 return add(base,offset)

def store_word32(value):
 if value is None:return None
 if type(value) is int:return value&0xffffffff
 if isinstance(value,tuple) and value[0]=='load' and value[2]<=4:return value
 return ('low32',value)

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
   if d['flags']:
    if op=='sub' and d['rd']==31:regs['NZCV']=compare_provenance(event['source_value'],d['imm'],d['width'],off)
    else:regs.pop('NZCV',None)
  elif op=='adrp':require(rel is not None and rel['type']==275,'actual typed ADRP relocation');put(d['rd'],('address',rel['identity']))
  elif op=='mov':event['source_value']=get(d['rn']);put(d['rd'],narrow(get(d['rn']),d['width']))
  elif op in ('movz','movn'):put(d['rd'],d['imm'] if op=='movz' else (~d['imm'])&((1<<d['width'])-1))
  elif op=='movk':
   old=get(d['rd']);put(d['rd'],((old&~(65535<<d['shift']))|d['imm']) if isinstance(old,int) else None)
  elif op in ('and','ands','orr','eor'):
   put(d['rd'],bitop(op,get(d['rn']),d['imm'],d['width']))
   if op=='ands':regs.pop('NZCV',None)
  elif op=='csel32gt':
   event['NZCV_source']=regs.get('NZCV');put(d['rd'],csel32_gt(get(d['rn']),get(d['rm']),regs.get('NZCV')))
  elif op=='cmpreg64':regs['NZCV']=compare_provenance(get(d['rn']),get(d['rm']),64,off)
  elif op=='umaddl':put(d['rd'],umaddl_value(get(d['rn']),get(d['rm']),get(d['ra'])))
  elif op=='orr32reg':put(d['rd'],orr32_value(get(d['rn']),get(d['rm'])))
  elif op=='tst64':
   regs['NZCV']=and64_flags(get(d['rn']),get(d['rm']),off);event['NZCV_result']=regs['NZCV']
  elif op=='load':event['address']=add(get(d['rn']),d['offset']);put(d['rd'],load(get(d['rn']),d['offset'],d['size']))
  elif op=='store':
   if d.get('mode')=='preindex':
    old_base=get(d['rn']);old_data=get(d['rd']);address=preindex_address(old_base,d['offset'])
    event.update(address=address,value=store_word32(old_data),size=4,mode='preindex',writeback=True,base_register=d['rn'],old_base=old_base,new_base=address,address_width=64,address_modulo=True,source_width=32)
    put(d['rn'],address)
   else:event.update(address=add(get(d['rn']),d['offset']),value=get(d['rd']),size=d['size'])
  elif op=='pair-load':
   if d['rn']!=31:regs={}
   else:put(d['rd'],None);put(d['rt2'],None)
  elif op=='pair-store':
   if d['rn']!=31:regs={}
  elif op in ('bl','blr','br') or op=='b' and off in call_targets:
   event.update(arguments=[get(i) for i in range(8)],target=call_targets.get(off) if op in ('bl','b') else get(d['rn']))
   if op not in ('br','b'):
    for i in range(19):regs.pop(i,None)
    regs.pop('NZCV',None)
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
