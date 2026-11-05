"""Fresh captured FDT -> real platform facts and canonical bounded AppleDT.

The result is a prospective single-CPU handoff contract. Native OF/probe and
final-state comparison remains mandatory; FDT is never relabelled as AppleDT.
"""
import argparse
import json
from pathlib import Path
import struct
import sys
from v130_slot import metadata
from v130_contract import ROOT,ordinary,private,sha,hexid,read,save,digest

sys.path.insert(0,str(ROOT/'note10/xnu26'))
from boot_adt import Node,encode,decode

SCHEMA='note10-v130-real-platform-derivation-v1'
MAX=2097152


def be(raw):
    if not raw or len(raw)%4:raise ValueError('FDT cell width differs')
    return int.from_bytes(raw,'big')


def parse(raw):
    if not 40<=len(raw)<=MAX:raise ValueError('bounded complete FDT required')
    magic,total,start,strings,reserve,version,compatible,bootcpu,nstrings,nstruct=struct.unpack_from('>10I',raw)
    if magic!=0xd00dfeed or total!=len(raw) or version!=17 or compatible>17 or start%4 or reserve%8:
        raise ValueError('FDT header differs')
    if start<40 or strings<40 or start+nstruct>total or strings+nstrings>total:
        raise ValueError('FDT blocks outside input')
    if start<strings+nstrings and strings<start+nstruct:raise ValueError('FDT blocks overlap')
    names=raw[strings:strings+nstrings];position=start;end=start+nstruct;stack=[];nodes={};props=0
    def string(buf,offset,limit):
        if not 0<=offset<limit:raise ValueError('FDT string offset differs')
        stop=buf.find(b'\0',offset,limit)
        if stop<0:raise ValueError('FDT unterminated string')
        return buf[offset:stop].decode('ascii'),stop
    while position+4<=end:
        token=struct.unpack_from('>I',raw,position)[0];position+=4
        if token==1:
            name,stop=string(raw,position,end);position=(stop+4)&~3
            if '/' in name or len(stack)>=64:raise ValueError('FDT path/depth differs')
            stack.append(name);path='/'+'/'.join(stack[1:])
            if path in nodes or len(nodes)>=4096:raise ValueError('FDT duplicate/node bound')
            nodes[path]={}
        elif token==2:
            if not stack:raise ValueError('FDT unbalanced end')
            stack.pop()
        elif token==3:
            if not stack or position+8>end:raise ValueError('FDT property outside node')
            size,index=struct.unpack_from('>II',raw,position);position+=8
            if position+size>end or props>=32768:raise ValueError('FDT property extent/count differs')
            key,_=string(names,index,len(names));path='/'+'/'.join(stack[1:])
            if not key or key in nodes[path]:raise ValueError('FDT duplicate/empty property')
            nodes[path][key]=raw[position:position+size];position=(position+size+3)&~3;props+=1
        elif token==4:continue
        elif token==9:
            if stack or '/' not in nodes:raise ValueError('FDT root not closed')
            return nodes,bootcpu
        else:raise ValueError('FDT token differs')
    raise ValueError('FDT END missing')


def strings(raw):return raw.rstrip(b'\0').split(b'\0')
def unique(nodes,compatible):
    found=[(path,p) for path,p in nodes.items() if compatible in strings(p.get('compatible',b'')) and p.get('status',b'okay\0') not in (b'disabled\0',b'fail\0')]
    if len(found)!=1:raise ValueError('one actual active '+compatible.decode()+' node required')
    return found[0]
def regs(nodes,path):
    parent=path.rsplit('/',1)[0] or '/';p=nodes[parent]
    ac=be(p.get('#address-cells',b'\0\0\0\2'));sc=be(p.get('#size-cells',b'\0\0\0\1'))
    if ac not in (1,2) or sc not in (1,2):raise ValueError('unsupported actual address/size cells')
    raw=nodes[path]['reg'];width=(ac+sc)*4
    if not raw or len(raw)%width:raise ValueError('FDT reg tuple width differs')
    return [(be(raw[i:i+ac*4]),be(raw[i+ac*4:i+width])) for i in range(0,len(raw),width)]


def derive(raw):
    nodes,bootcpu=parse(raw)
    gpath,gic=unique(nodes,b'arm,cortex-a15-gic');tpath,timer=unique(nodes,b'arm,armv8-timer')
    if gpath.count('/')!=1 or tpath.count('/')!=1:raise ValueError('translated/nested controller buses require a new audited profile')
    greg=regs(nodes,gpath)
    if len(greg)<2:raise ValueError('actual distributor/CPU interface ranges required')
    frequency=be(timer['clock-frequency'])
    interrupts=timer['interrupts']
    # Binding/source enum order: secure physical, nonsecure physical, virtual, hyp.
    if len(interrupts)!=48:raise ValueError('four actual timer PPI triples required')
    kind,index,flags=struct.unpack_from('>III',interrupts,12)
    if kind!=1 or index>=16:raise ValueError('actual nonsecure physical PPI differs')
    timer_intid=16+index
    cpus=nodes.get('/cpus');selected=[]
    if cpus is None:raise ValueError('actual CPU nodes required')
    ac=be(cpus.get('#address-cells',b'\0\0\0\2'))
    for path,p in nodes.items():
        if path.startswith('/cpus/') and p.get('device_type')==b'cpu\0' and len(p.get('reg',b''))==ac*4:
            if be(p['reg'])==bootcpu:selected.append((path,p))
    if len(selected)!=1:raise ValueError('actual FDT boot CPU selection ambiguous')
    cpath,cpu=selected[0]
    # These are accepted target-source constraints, not inferred hardware values.
    # The source snapshot supplies the actual compared numbers; mismatch refuses.
    if greg[:2]!=[(0x10101000,0x1000),(0x10102000,0x1000)] or timer_intid!=30 or frequency!=26000000:
        raise ValueError('actual board differs from the unchanged current94 target contract')
    memories=[]
    for path,p in nodes.items():
        if p.get('device_type')==b'memory\0':memories.extend(regs(nodes,path))
    if not memories or any(not size or base+size>1<<64 for base,size in memories):raise ValueError('actual memory map invalid')
    ordered=sorted(memories)
    if any(a+size>b for (a,size),(b,_) in zip(ordered,ordered[1:])):raise ValueError('actual DRAM extents overlap')
    facts=dict(gic_path=gpath,timer_path=tpath,cpu_path=cpath,boot_mpidr=bootcpu,frequency=frequency,
        gic_reg=greg,timer_intid=timer_intid,timer_interrupt_cells=[kind,index,flags],memory=ordered,
        source_properties={gpath:{k:v.hex() for k,v in gic.items() if k in ('compatible','reg','#interrupt-cells')},
                           tpath:{k:v.hex() for k,v in timer.items() if k in ('compatible','clock-frequency','interrupts')},
                           cpath:{k:v.hex() for k,v in cpu.items() if k in ('device_type','compatible','reg')},
                           '/':{k:v.hex() for k,v in nodes['/'].items() if k in ('compatible','#address-cells','#size-cells')}})
    target=Node('device-tree',properties={'compatible':nodes['/'].get('compatible',b'')},children=[
        Node('cpus',children=[Node('cpu0',properties={'state':b'running\0','reg':struct.pack('<I',bootcpu),
            'timebase-frequency':struct.pack('<I',frequency),'compatible':cpu['compatible']})]),
        Node('chosen',properties={'boot-args':b'cpus=1\0','dram-base':struct.pack('<Q',ordered[0][0]),
            'dram-size':struct.pack('<Q',33554432)},children=[Node('note10-platform',properties={
            'compatible':b'samsung,exynos9825-note10\0','version':struct.pack('<I',1),'gic-handoff':struct.pack('<I',1),
            'gic-reg':struct.pack('<4Q',*greg[0],*greg[1]),'timer-intid':struct.pack('<I',timer_intid),
            'timebase-frequency':struct.pack('<I',frequency)})])])
    tree=encode(target);decode(tree)
    # This catalog/expected descriptor is compared against the future kernel's
    # actual OF/probe/MPIDR/counter producer, never against bootargs text/hash.
    platform=struct.pack('<8sII6QII56s',b'N10PLAT1',1,128,bootcpu,frequency,*greg[0],*greg[1],timer_intid,1,bytes(56))
    return tree,platform,facts


def produce(capture,expected,output):
    capture=ordinary(capture);output=private(output)
    if sha(capture)!=hexid(expected) or output.exists():raise ValueError('exact fresh captured source receipt and output required')
    receipt=read(capture)
    if (receipt.get('schema')!='note10-v130-current-fdt-capture-v1' or receipt.get('status')!='captured-source-bound' or
        receipt.get('source_binding_passed') is not True or receipt.get('fdt_reads')!=1 or
        receipt.get('remote_hash_before')!=receipt.get('fdt_sha256') or receipt.get('remote_hash_after')!=receipt.get('fdt_sha256') or
        receipt.get('boot_id_before')!=receipt.get('source_boot_id') or receipt.get('boot_id_after')!=receipt.get('source_boot_id')):
        raise ValueError('real current-boot source capture join required; no historical fixture promotion')
    path=ordinary(capture.parent/receipt['fdt_file']);raw=path.read_bytes()
    if len(raw)!=receipt['fdt_bytes'] or digest(raw)!=hexid(receipt['fdt_sha256']):raise ValueError('captured FDT input bytes differ')
    tree,platform,facts=derive(raw)
    output.mkdir();(output/'platform.adt').write_bytes(tree);(output/'platform.contract').write_bytes(platform)
    save(output/'result.json',dict(schema=SCHEMA,passed=True,source_capture=str(capture),source_capture_sha256=expected,
        source_fdt_sha256=digest(raw),source_fdt_bytes=len(raw),source_boot_id=receipt['source_boot_id'],
        platform_adt_sha256=digest(tree),platform_adt_bytes=len(tree),platform_contract_sha256=digest(platform),
        activation_member_bytes=len(metadata(tree,platform,expected)),
        facts=facts,ADT_role='prospective source-derived single-CPU target; final runtime OF/probe/MPIDR/counter and shutdown-state gates mandatory',
        owned_DRAM_finalization_required='CI-built PID1 must replace chosen dram-base with this boot checked reserved base and dram-size with owned32MiB; current94 arm_init requires these fields. Template is not directly bootable.',
        memSize=33554432,memSizeActual=33554432,full_device_RAM_claimed=False,physical_ready=False,
        old_FDT_fixture_used=False,device_operations=[]))
    return output/'result.json'


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--capture-receipt',required=True,type=Path)
    p.add_argument('--capture-sha256',required=True);p.add_argument('--output',required=True,type=Path);a=p.parse_args()
    print(produce(a.capture_receipt,a.capture_sha256,a.output))
