"""Match static vector candidates against exact data literals in pinned source."""
import ast
import hashlib
import json
from pathlib import Path
import re
import struct
from audit_kernel_instructions import ROOT, image_layout


def main():
    directory = ROOT/'note10/private/cloud-runs/39560904016/note10-experimental-native-build'
    raw = (directory/'note10-experimental.macho').read_bytes()
    audit = json.loads((ROOT/'note10/private/kernel-instruction-audit.json').read_text())
    if hashlib.sha256(raw).hexdigest() != audit['kernel_sha256']:raise ValueError('Kernel audit does not match executable')
    reference = json.loads((ROOT/'research/ios26/xnu-reference.json').read_text())
    source = ROOT/reference['source_directory']
    sections, _, _ = image_layout(raw)
    evidence = []; hashes = {}
    def original(name):
        p=source/name;data=p.read_bytes();hashes[name]=hashlib.sha256(data).hexdigest();return data.decode()
    def match(data,name,label):
        if len(data) < 8:raise ValueError('Literal too small for exact source-data review')
        found = False
        for section in sections:
            start=section['file_offset'];end=start+section['size'];at=raw.find(data,start,end)
            while at >= 0:
                va=section['address']+at-start
                evidence.append({'source':name,'label':label,'start':va,'end':va+len(data),
                                 'data_sha256':hashlib.sha256(data).hexdigest()})
                found=True;at=raw.find(data,at+1,end)
        return found
    for name in ('osfmk/arm64/locore.s','osfmk/arm64/machine_routines_asm.s'):
        for literal in re.findall(r'^\s*\.asciz\s+("(?:\\.|[^"\\])*")',original(name),re.M):
            match(ast.literal_eval(literal).encode()+b'\0',name,'.asciz '+literal)
    def numeric_table(text,label,directive,width,constants=None):
        values=[]
        for line in text.split(label+':',1)[1].splitlines():
            line=line.split('//',1)[0].strip()
            if not line:continue
            if not line.startswith('.'+directive):break
            for token in line.split(None,1)[1].split(','):
                token=token.strip();value=(constants or {}).get(token)
                values.append(int(token,0) if value is None else value)
        return b''.join(v.to_bytes(width,'little') for v in values)
    name='osfmk/arm64/corecrypto/sha256_compress_arm64.s'
    data=numeric_table(original(name),'K256','long',4)
    if len(data)!=256 or not match(data,name,'K256'):raise ValueError('SHA256 source table mismatch')
    name='osfmk/arm64/lz4_decode_arm64.s'
    data=numeric_table(original(name),'L_match_permtable','byte',1)
    if len(data)!=512 or not match(data,name,'L_match_permtable'):raise ValueError('LZ4 source table mismatch')
    constants=original('osfmk/vm/lz4_constants.h')
    multiplier=int(re.search(r'^#define LZ4_COMPRESS_HASH_MULTIPLY (\d+)U',constants,re.M)[1])
    name='osfmk/arm64/lz4_encode_arm64.s'
    data=numeric_table(original(name),'L_constant','long',4,{'LZ4_COMPRESS_HASH_MULTIPLY':multiplier})
    if len(data)!=8 or not match(data,name,'L_constant'):raise ValueError('LZ4 encoder source literal mismatch')
    reviewed=[]
    for candidate in audit['candidate_samples'].get('scalable_vector_candidate',[]):
        address=int(candidate['address'],16)
        matches=[e for e in evidence if e['start']<=address and address+4<=e['end']]
        reviewed.append({**candidate,'exact_source_data_matches':matches})
    debug=original('osfmk/kern/debug.c')
    if 'awl_scratch_reg_supported = false' not in debug or '"awl-scratch-supported"' not in debug:
        raise ValueError('AWL source guard changed')
    report={'kernel_sha256':audit['kernel_sha256'],'source_sha256':hashes,
            'vector_candidates_reviewed':len(reviewed),
            'vector_candidates_matching_source_data':sum(bool(x['exact_source_data_matches']) for x in reviewed),
            'vector_candidate_review':reviewed,
            'awl_register_access_count':audit['candidate_counts'].get('implementation_defined_system_register',0),
            'awl_review':'Apple WatchdogDiag0 accesses remain in the binary. Upstream default support is false; /arm-io/wdt awl-scratch-supported enables the path. An Exynos handoff must not enable this Apple hardware feature.',
            'complete_isa_compatibility_proven':False,'hardware_verified':False}
    (ROOT/'note10/private/kernel-instruction-review.json').write_text(json.dumps(report,indent=2))
    print(json.dumps({k:report[k] for k in ('vector_candidates_reviewed','vector_candidates_matching_source_data','awl_register_access_count','complete_isa_compatibility_proven')}))


if __name__=='__main__':main()
