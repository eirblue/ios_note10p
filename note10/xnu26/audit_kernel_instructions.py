"""Inspect actual executable sections without executing the kernel.

Findings are static candidates, not proof that an instruction is reachable or
that an otherwise clean binary can boot on the target hardware.
"""
import argparse
from bisect import bisect_right
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import re
import struct
from verify_experimental_artifact import verify

ROOT = Path(__file__).resolve().parents[2]


def image_layout(raw):
    count = struct.unpack_from('<I', raw, 16)[0]
    offset = 32; sections = []; data_ranges = []; symtab = None
    for _ in range(count):
        cmd, size = struct.unpack_from('<II', raw, offset)
        if cmd == 0x19:
            nsects = struct.unpack_from('<I', raw, offset+64)[0]
            for i in range(nsects):
                at = offset+72+i*80
                section = raw[at:at+16].split(b'\0')[0].decode()
                segment = raw[at+16:at+32].split(b'\0')[0].decode()
                address, length, fileoff, align, reloff, nreloc, flags = struct.unpack_from('<QQ5I', raw, at+32)
                if flags & 0x80000400 or flags & 0xff == 8:
                    if fileoff+length > len(raw):raise ValueError('Executable section exceeds file')
                    sections.append({'segment':segment,'section':section,'address':address,
                                     'size':length,'file_offset':fileoff,'flags':flags})
        elif cmd == 0x29:
            start, length = struct.unpack_from('<II', raw, offset+8)
            if length % 8 or start+length > len(raw):raise ValueError('Invalid LC_DATA_IN_CODE')
            for i in range(start,start+length,8):
                position, width, kind = struct.unpack_from('<IHH', raw, i)
                data_ranges.append((position,position+width))
        elif cmd == 2:symtab = struct.unpack_from('<4I',raw,offset+8)
        offset += size
    symbols = []
    if symtab:
        at, count, strings, length = symtab
        names = raw[strings:strings+length]
        for i in range(count):
            index, kind, section, desc, value = struct.unpack_from('<IBBHQ',raw,at+i*16)
            if kind & 0xe0 or kind & 0xe != 0xe:continue
            end = names.find(b'\0',index)
            if end < 0:raise ValueError('Unterminated symbol')
            symbols.append((value,names[index:end].decode(errors='replace')))
    return sections, sorted(data_ranges), sorted(symbols)


def code_chunks(section, data_ranges):
    start = section['file_offset']; end = start+section['size']; cursor = start
    for first,last in data_ranges:
        if last <= cursor or first >= end:continue
        if first > cursor:yield cursor,min(first,end)
        cursor = min(end,max(cursor,last))
    if cursor < end:yield cursor,end


def category(mnemonic, operands):
    if mnemonic.startswith(('pac','aut','xpac')) or mnemonic in (
        'braa','braaz','brab','brabz','blraa','blraaz','blrab','blrabz','retaa','retab','eretaa','eretab'):
        return 'pointer_authentication'
    if mnemonic == 'bti':return 'bti_hint'
    if mnemonic in ('irg','gmi','addg','subg','subp','subps','ldg','stg','st2g','stzg','stz2g','ldgm','stgm','stzgm'):
        return 'memory_tagging_candidate'
    if re.search(r'\b[zp]\d+\b', operands):return 'scalable_vector_candidate'
    if mnemonic in ('mrs','msr') and re.search(r'\bs[123]_[0-7]_c15_', operands):
        return 'implementation_defined_system_register'
    if mnemonic == '.byte':return 'undecoded_word_or_unmarked_data'
    return None


def audit(directory):
    import capstone
    verified = verify(directory)
    raw = (directory/'note10-experimental.macho').read_bytes()
    sections, data_ranges, symbols = image_layout(raw)
    addresses = [s[0] for s in symbols]
    disassembler = capstone.Cs(capstone.CS_ARCH_ARM64,capstone.CS_MODE_LITTLE_ENDIAN)
    disassembler.skipdata = True
    counts = Counter(); candidates = defaultdict(list); entry = []; instructions = 0
    section_reports = []
    start_pc = int(verified['entry_virtual_address'],16)
    for section in sections:
        checked = 0; scanned = 0
        for first,last in code_chunks(section,data_ranges):
            aligned = first + (-(section['address']+first-section['file_offset'])%4)
            final = last - ((last-aligned)%4)
            if final <= aligned:continue
            pc = section['address']+aligned-section['file_offset']
            for address,size,mnemonic,operands in disassembler.disasm_lite(raw[aligned:final],pc):
                instructions += 1; checked += 1; scanned += size
                kind = category(mnemonic,operands)
                if kind:
                    counts[kind] += 1
                    if len(candidates[kind]) < 256:
                        index = bisect_right(addresses,address)-1
                        near = symbols[index][1] if index >= 0 else None
                        candidates[kind].append({'address':hex(address),'mnemonic':mnemonic,'operands':operands,
                                                 'nearest_preceding_symbol':near,'section':section['section']})
                if start_pc <= address < start_pc+64*4:
                    entry.append({'address':hex(address),'mnemonic':mnemonic,'operands':operands})
        section_reports.append({**section,'instructions_or_skipdata_records':checked,'scanned_bytes':scanned})
    return {'kernel_sha256':hashlib.sha256(raw).hexdigest(),'capstone_version':capstone.__version__,
            'executable_sections':section_reports,'data_in_code_entries_excluded':len(data_ranges),
            'instructions_or_skipdata_records':instructions,'candidate_counts':dict(counts),
            'candidate_samples':dict(candidates),'entry_first_64_instructions':entry,
            'device_executed':False,'cpu_compatibility_proven':False,'deployment_ready':False,
            'limitations':['Static scan does not establish reachability or complete ISA compatibility.',
                           'Unknown encodings may be unsupported instructions or data without LC_DATA_IN_CODE.',
                           'Implementation-defined register semantics require individual source review.',
                           'BTI/PAuth hint encodings require separate analysis from trapping instruction forms.']}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory',type=Path)
    parser.add_argument('--report',type=Path,default=ROOT/'note10/private/kernel-instruction-audit.json')
    args = parser.parse_args();result = audit(args.directory)
    args.report.write_text(json.dumps(result,indent=2))
    print(json.dumps({k:result[k] for k in ('instructions_or_skipdata_records','data_in_code_entries_excluded','candidate_counts','cpu_compatibility_proven')}))
