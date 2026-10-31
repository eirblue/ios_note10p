"""Closed positive AArch64 mnemonic policy for the PC trial component.

Parse instruction fields only. Addresses, bytes, symbols and paths never classify
as instructions. This inspects compiler output; it does not execute AArch64.
"""
import re

PERMITTED=frozenset('''adc adcs add adds adr adrp and ands asr asrv b b.eq b.ne
b.cs b.hs b.cc b.lo b.mi b.pl b.vs b.vc b.hi b.ls b.ge b.lt b.gt b.le
bic bics bl cbnz cbz ccmn ccmp cinc cinv cls clz cmn cmp cneg csel cset
csetm csinc csinv csneg eon eor extr ldp ldpsw ldr ldrb ldrh ldrsb ldrsh
ldrsw ldur ldurb ldurh ldursb ldursh ldursw lsl lslv lsr lsrv madd mneg
mov movk movn movz msub mul mvn neg negs nop orn orr rbit ret rev rev16
rev32 ror rorv sbc sbcs sbfiz sbfx sdiv smaddl smnegl smsubl smulh smull
stp str strb strh stur sturb sturh sub subs sxtb sxth sxtw tbnz tbz tst
ubfiz ubfx udiv umaddl umnegl umsubl umulh umull uxtb uxth
addp cmeq cmge cmgt cmhi cmhs cmle cmlt cmtst cnt dup ext fmov ins
ld1 ld2 ld3 ld4 movi mvni not orn orr rev64 shl shrn sli sqxtn srshr
sshr st1 st2 st3 st4 tbl tbx trn1 trn2 uaddlv uaddlp uaddw uaddl
umaxv uminv urshr ushr uzp1 uzp2 xtn zip1 zip2'''.split())
ROW=re.compile(r'^\s*([0-9a-fA-F]+):\s+((?:[0-9a-fA-F]{2}\s+){3}[0-9a-fA-F]{2}|[0-9a-fA-F]{8})\s+([a-z][a-z0-9.]*)\s*(.*?)\s*$')
LABEL=re.compile(r'^\s*[0-9a-fA-F]+ <[^<>]+>:\s*$')

def classify(text):
    rows=[];seen=set();section=None
    for line in text.splitlines():
        if not line.strip():continue
        if re.fullmatch(r'.+:\s+file format elf64-littleaarch64\s*',line):continue
        if re.fullmatch(r'Disassembly of section [A-Za-z0-9_.$]+:',line):
            section=line;continue
        if LABEL.fullmatch(line):continue
        match=ROW.fullmatch(line)
        if not match or section is None:raise ValueError('malformed AArch64 disassembly row')
        address,encoding,mnemonic,operands=match.groups();address=int(address,16)
        if address%4 or (section,address) in seen:raise ValueError('unaligned/duplicate instruction address')
        if mnemonic not in PERMITTED or (not operands and mnemonic not in {'ret','nop'}):raise ValueError('unapproved instruction mnemonic/operands: '+mnemonic)
        if '<unknown>' in operands or '.word' in operands:raise ValueError('unknown instruction')
        seen.add((section,address));rows.append({'address':address,'encoding':encoding,'mnemonic':mnemonic})
    if not rows:raise ValueError('no decoded production instructions')
    return {'instruction_count':len(rows),'mnemonics':sorted({r['mnemonic'] for r in rows}),'policy':'positive-mnemonic-fields-only'}
