"""Finite independent A64 word-field cross-check for the observed restore block."""
import re
from prepare_pre_pm_trial import require

def register(index,width,sp=False):
 return ('sp' if width==64 else 'wsp') if index==31 and sp else ('xzr' if width==64 else 'wzr') if index==31 else ('x' if width==64 else 'w')+str(index)
def signed(value,bits):return value-(1<<bits) if value&(1<<(bits-1)) else value
def number(text):
 require(re.fullmatch(r'#?-?(?:0x[0-9a-f]+|[0-9]+)',text) is not None,'canonical numeric decoded operand');return int(text.removeprefix('#'),0)
def validate_word(row):
 word=row['word'];require(type(word) is int and 0<=word<1<<32,'actual 32-bit instruction word')
 mnemonic=row['mnemonic'];text=row['operands'].split('//',1)[0].strip().lower();text=re.sub(r'<[^<>]*>','',text)
 require('<' not in text and '>' not in text,'malformed disassembly annotation');text=re.sub(r'\s+','',text);parts=text.split(',') if text else []
 sf=word>>31;width=64 if sf else 32;rd=word&31;rn=(word>>5)&31;rm=(word>>16)&31
 def exact(name,expected):require(mnemonic==name and parts==expected,'word/decoded operand mismatch: '+name)
 def memory(name,regs,base,offset):
  require(mnemonic==name,'word/mnemonic mismatch: '+name)
  prefix=','.join(regs)+',';require(text.startswith(prefix),'word/load-store register mismatch')
  match=re.fullmatch(r'\[(sp|x(?:[0-9]|[12][0-9]|30))(?:,(#-?(?:0x[0-9a-f]+|[0-9]+)))?\]',text[len(prefix):])
  require(match is not None and match[1]==base and (number(match[2]) if match[2] else 0)==offset,'word/load-store address mismatch')
 if word&0x1f800000==0x12800000:
  opc=(word>>29)&3;shift=((word>>21)&3)*16;imm=(word>>5)&0xffff;require(opc in (0,2,3) and shift<width and rd!=31,'finite wide move fields');dest=register(rd,width)
  if opc==3:
   require(mnemonic=='movk' and len(parts) in (2,3) and parts[0]==dest and number(parts[1])==imm,'word/MOVK fields')
   actual_shift=0 if len(parts)==2 else number(parts[2].removeprefix('lsl'));require(actual_shift==shift,'word/MOVK shift')
  else:
   value=(imm<<shift) if opc==2 else ~(imm<<shift);require(mnemonic=='mov' and len(parts)==2 and parts[0]==dest and number(parts[1])&((1<<width)-1)==value&((1<<width)-1),'word/wide MOV immediate')
 elif word&0x7f200000==0x2a000000:
  require((word>>22)&3==0 and (word>>10)&63==0,'only observed unshifted ORR/MOV')
  exact('mov',[register(rd,width),register(rm,width)]) if rn==31 else exact('orr',[register(rd,width),register(rn,width),register(rm,width)])
 elif word&0x7f800000==0x11000000:
  require(not word&(1<<22) and rd!=31,'only observed unshifted ADD immediate');require(mnemonic=='add' and len(parts)==3 and parts[:2]==[register(rd,width),register(rn,width,True)] and number(parts[2])==(word>>10)&0xfff,'word/ADD immediate fields')
 elif word&0x7f200000==0x0b000000:
  require((word>>22)&3==0 and (word>>10)&63==0,'only observed unshifted ADD registers');exact('add',[register(rd,width),register(rn,width),register(rm,width)])
 elif word&0xffc00000 in (0xf9400000,0xb9400000,0xf9000000,0xb9000000):
  base=word&0xffc00000;bits=64 if base in (0xf9400000,0xf9000000) else 32;name='ldr' if base in (0xf9400000,0xb9400000) else 'str';memory(name,[register(rd,bits)],register(rn,64,True),((word>>10)&0xfff)*(bits//8))
 elif word&0xffe00c00 in (0xf8400000,0xb8400000,0xf8000000,0xb8000000):
  base=word&0xffe00c00;bits=64 if base in (0xf8400000,0xf8000000) else 32;name='ldur' if base in (0xf8400000,0xb8400000) else 'stur';memory(name,[register(rd,bits)],register(rn,64,True),signed((word>>12)&0x1ff,9))
 elif word&0xffc00000==0xa9000000:
  memory('stp',[register(rd,64),register((word>>10)&31,64)],register(rn,64,True),signed((word>>15)&0x7f,7)*8)
 elif word&0xfffffc1f==0x7100001f:
  exact('cmp',[register(rn,32),'#0'])
 elif word&0xffff0fe0==0x1a9f07e0:
  condition=(word>>12)&15;require(condition in (0,1),'only observed equality/inequality CSET fields');exact('cset',[register(rd,32),'ne' if condition==0 else 'eq'])
 elif word>>26==37:
  require(mnemonic=='bl' and len(parts)==1 and number(parts[0])==row['offset']+4*signed(word&0x3ffffff,26),'word/BL target fields')
 elif word&0xff000000 in (0x34000000,0x35000000):
  require(mnemonic==('cbnz' if word&(1<<24) else 'cbz') and len(parts)==2 and parts[0]==register(rd,32) and number(parts[1])==row['offset']+4*signed((word>>5)&0x7ffff,19),'word/conditional branch fields')
 elif word==0xd5033f9f:exact('dsb',['sy'])
 elif word==0xd503201f:exact('nop',[])
 elif word&0xfffffc00==0x12000000:exact('and',[register(rd,32),register(rn,32),'#1'])
 else:raise ValueError('unreviewed word in finite restore-block decoder')
 return {'offset':row['offset'],'word':word,'mnemonic':mnemonic}
