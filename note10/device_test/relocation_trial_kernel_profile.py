"""Source-pinned kernel-option subset and decoded GPR-only instruction gate."""
import hashlib
import json
from pathlib import Path
import re
from relocation_trial_instructions import classify,ROW

PROFILE_ID='kernel-init-subset-v1'
PROFILE_FILE=Path(__file__).with_suffix('.json')
FLAGS=('-mlittle-endian','-fno-common','-march=armv8-a+lse','-fno-PIE','-mno-implicit-float','-fno-pic','-Oz','-fno-stack-protector','-mno-global-merge')
PROFILE_SOURCE_SHA='d7cebe509d2ca93ce46404a13f46a67fd728f7a969d4f3aa47fa3c51989a920c'
GPR_MNEMONICS=frozenset('''adc adcs add adds adr adrp and ands asr asrv b b.eq b.ne
b.cs b.hs b.cc b.lo b.mi b.pl b.vs b.vc b.hi b.ls b.ge b.lt b.gt b.le
bic bics bl cbnz cbz ccmn ccmp cinc cinv cls clz cmn cmp cneg csel cset
csetm csinc csinv csneg eon eor extr ldp ldpsw ldr ldrb ldrh ldrsb ldrsh
ldrsw ldur ldurb ldurh ldursb ldursh ldursw lsl lslv lsr lsrv madd mneg
mov movk movn movz msub mul mvn neg negs nop orn orr rbit ret rev rev16
rev32 ror rorv sbc sbcs sbfiz sbfx sdiv smaddl smnegl smsubl smulh smull
stp str strb strh stur sturb sturh sub subs sxtb sxth sxtw tbnz tbz tst
ubfiz ubfx udiv umaddl umnegl umsubl umulh umull uxtb uxth bfi'''.split())
OPERAND_WORDS=frozenset('sp wsp xzr wzr eq ne cs hs cc lo mi pl vs vc hi ls ge lt gt le al nv lsl lsr asr ror msl uxtb uxth uxtw uxtx sxtb sxth sxtw sxtx'.split())

def require(ok,message):
    if not ok:raise ValueError(message)

def kernel_profile(expected_profile):
    require(expected_profile==PROFILE_ID,'explicit supported kernel profile required')
    raw=PROFILE_FILE.read_bytes();require(hashlib.sha256(raw).hexdigest()==PROFILE_SOURCE_SHA,'source-pinned profile JSON')
    value=json.loads(raw);require(value['profile_id']==PROFILE_ID and value['selected_flags']==list(FLAGS),'canonical selected kernel option subset')
    return {'profile_id':PROFILE_ID,'selected_flags':list(FLAGS),'flags_sha256':hashlib.sha256(json.dumps(list(FLAGS),separators=(',',':')).encode()).hexdigest(),
      'profile_source_sha256':PROFILE_SOURCE_SHA,'origin':value['origin'],'subset_only':True,'actual_kernel_integration':False}

def verify_profile_report(report,expected_profile):
    settings=kernel_profile(expected_profile)
    require(report['codegen_profile']==settings,'expected caller/source profile binding')
    emulator=report['emulator']
    require(emulator['fp_advsimd_setting']=={'register':'CPACR_EL1','value':0,'model_assumption_only':True} and
      type(emulator['cpacr_before']) is int and type(emulator['cpacr_after']) is int and
      emulator['cpacr_before']==0 and emulator['cpacr_after']==0,'actual model FP-disabled readback before/after')

def gpr_only(text):
    ordinary=classify(text);count=0;mnemonics=set()
    for line in text.splitlines():
        match=ROW.fullmatch(line)
        if not match:continue
        mnemonic=match[3];require(mnemonic in GPR_MNEMONICS,'FP/SIMD or unsupported GPR opcode: '+mnemonic)
        operands=match[4].split('//',1)[0].split(';',1)[0]
        operands=re.sub(r'<[^<>]*>','',operands)
        require('<' not in operands and '>' not in operands,'malformed symbol annotation')
        tokens=re.findall(r'(?<![A-Za-z0-9_])([A-Za-z_][A-Za-z0-9_.]*)(?![A-Za-z0-9_])',operands)
        for token in tokens:
            token=token.lower()
            require(token in OPERAND_WORDS or re.fullmatch(r'[xw](?:[0-9]|[12][0-9]|30)',token),'FP/SIMD or malformed operand register/token: '+token)
        count+=1;mnemonics.add(mnemonic)
    require(count==ordinary['instruction_count'],'every decoded instruction checked for GPR profile')
    return {'instruction_count':count,'mnemonics':sorted(mnemonics),'policy':'decoded-mnemonic-and-operand-GPR-only','fp_simd_instructions_or_registers':False,'hardware_FP_permission_claim':False}
