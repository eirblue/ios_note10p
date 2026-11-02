"""One NEW production-routine compile and bounded AArch64 ordinary-memory execution."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import struct
import subprocess
import unittest
from unicorn import Uc, UC_ARCH_ARM64, UC_MODE_ARM
from unicorn.arm64_const import UC_ARM64_REG_X0, UC_ARM64_REG_X1, UC_ARM64_REG_X2, UC_ARM64_REG_X3, UC_ARM64_REG_X4, UC_ARM64_REG_X18, UC_ARM64_REG_X19, UC_ARM64_REG_X20, UC_ARM64_REG_X21, UC_ARM64_REG_X22, UC_ARM64_REG_X23, UC_ARM64_REG_X24, UC_ARM64_REG_X25, UC_ARM64_REG_X26, UC_ARM64_REG_X27, UC_ARM64_REG_X28, UC_ARM64_REG_X29, UC_ARM64_REG_X30, UC_ARM64_REG_SP, UC_ARM64_REG_PC

ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
PAGE=16384
POOL=10*PAGE
MAX=32*1024*1024
CODE=0x20000000000
STOP=CODE+0x10000
VA=0xfffffff007004000
MASK=0x0000ffffffffc000
LEAF=0x0040000000000603
CASE_IDS=('test_exact_owned_leaf_translations_and_boundary_crossings',
          'test_refusal_preflight_before_any_table_write',
          'test_callee_abi_root_layout_and_pool_capacity')
SOURCES=('exynos_leaf_mapper.S','exynos_leaf_mapper.h','prepare_exynos_leaf_mapper.py','test_exynos_leaf_mapper.py')

def sha(raw):return hashlib.sha256(raw).hexdigest()

def produced_text(raw):
    # Only this newly compiled one-routine MH_OBJECT; never a kernel reader.
    if not 32<=len(raw)<=1024*1024:raise ValueError('bounded new fixture object required')
    h=struct.unpack_from('<8I',raw)
    if h[:4]!=(0xfeedfacf,0x100000c,0,1) or h[4]>16 or h[5]>len(raw)-32:raise ValueError('plain ARM64 fixture object required')
    offset=32;selected=[];symbol_table=None;section_index=0
    for _ in range(h[4]):
        if offset+8>32+h[5]:raise ValueError('fixture command bounds')
        cmd,size=struct.unpack_from('<II',raw,offset)
        if size<8 or offset+size>32+h[5]:raise ValueError('fixture command extent')
        if cmd==0x19:
            count=struct.unpack_from('<I',raw,offset+64)[0]
            if size!=72+count*80:raise ValueError('fixture section table bounds')
            for i in range(count):
                at=offset+72+i*80;section_index+=1
                name,segment,addr,length,start,align,reloff,nreloc,flags,*_=struct.unpack_from('<16s16sQQ8I',raw,at)
                if name.rstrip(b'\0')==b'__text' and segment.rstrip(b'\0')==b'__TEXT':
                    if not 0<length<=PAGE or start+length>len(raw) or nreloc or align<2:raise ValueError('self-contained fixture text required')
                    selected.append((addr,raw[start:start+length],section_index))
        elif cmd==2:
            if size!=24 or symbol_table is not None:raise ValueError('one fixture symbol table required')
            symbol_table=struct.unpack_from('<4I',raw,offset+8)
        offset+=size
    if offset!=32+h[5] or len(selected)!=1 or symbol_table is None:raise ValueError('exact fixture text required')
    symoff,count,stroff,strsize=symbol_table
    if count>4096 or symoff+16*count>len(raw) or stroff+strsize>len(raw):raise ValueError('fixture symbol bounds')
    entries=[]
    for i in range(count):
        index,kind,section,desc,value=struct.unpack_from('<IBBHQ',raw,symoff+i*16)
        if index>=strsize:raise ValueError('fixture symbol name bounds')
        end=raw.find(b'\0',stroff+index,stroff+strsize)
        if end<0:raise ValueError('fixture symbol terminator')
        if raw[stroff+index:end]==b'_n10_exynos_bootstrap_map':entries.append((kind,section,value))
    addr,code,section=selected[0]
    if len(entries)!=1 or entries[0][1:]!=(section,addr):raise ValueError('fixture entry at first instruction required')
    return code

class MapperTests(unittest.TestCase):
    output=None
    compiles=0
    completed_calls=0
    @classmethod
    def setUpClass(cls):
        compiler=subprocess.check_output(['xcrun','--find','clang'],text=True).strip()
        obj=cls.output/'new-mapper.o'
        command=[compiler,'--target=arm64-apple-darwin','-march=armv8.2-a+crypto','-x','assembler-with-cpp',
                 '-DN10_MAPPER_FIXTURE=1','-I',str(HERE),'-c',str(HERE/'exynos_leaf_mapper.S'),'-o',str(obj)]
        cls.compiles+=1
        result=subprocess.run(command,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=120)
        (cls.output/'fixture-compile.log').write_bytes(result.stdout)
        (cls.output/'fixture-command.json').write_text(json.dumps(command,indent=2)+'\n')
        if result.returncode:raise RuntimeError('new production mapper fixture compilation failed')
        cls.code=produced_text(obj.read_bytes())
        cls.preserved=(UC_ARM64_REG_X18,UC_ARM64_REG_X19,UC_ARM64_REG_X20,UC_ARM64_REG_X21,UC_ARM64_REG_X22,UC_ARM64_REG_X23,UC_ARM64_REG_X24,UC_ARM64_REG_X25,UC_ARM64_REG_X26,UC_ARM64_REG_X27,UC_ARM64_REG_X28,UC_ARM64_REG_X29,UC_ARM64_REG_X30,UC_ARM64_REG_SP)
    def run_mapper(self,va,pa,size,pool=None,capacity=POOL):
        pool=pa+PAGE if pool is None else pool
        arena=(pool&~(PAGE-1))-PAGE
        cpu=Uc(UC_ARCH_ARM64,UC_MODE_ARM)
        cpu.mem_map(CODE,PAGE);cpu.mem_write(CODE,self.code)
        cpu.mem_map(arena,POOL+3*PAGE);cpu.mem_write(arena,b'\xa5'*(POOL+3*PAGE))
        stamps={reg:0x1122330000000000+i*0x100 for i,reg in enumerate(self.preserved)}
        stamps[UC_ARM64_REG_X30]=STOP;stamps[UC_ARM64_REG_SP]=0x30000000000
        for reg,value in stamps.items():cpu.reg_write(reg,value)
        for reg,value in zip((UC_ARM64_REG_X0,UC_ARM64_REG_X1,UC_ARM64_REG_X2,UC_ARM64_REG_X3,UC_ARM64_REG_X4),(va,pa,size,pool,capacity)):cpu.reg_write(reg,value)
        cpu.emu_start(CODE,STOP,count=1000000)
        self.assertEqual(cpu.reg_read(UC_ARM64_REG_PC),STOP)
        type(self).completed_calls+=1
        self.assertTrue(all(cpu.reg_read(reg)==value for reg,value in stamps.items()))
        memory=bytes(cpu.mem_read(arena,POOL+3*PAGE))
        return cpu.reg_read(UC_ARM64_REG_X0),cpu.reg_read(UC_ARM64_REG_X1),memory,arena,pool
    def lookup(self,memory,arena,root,va):
        def word(address):
            self.assertTrue(arena<=address<=arena+len(memory)-8)
            return struct.unpack_from('<Q',memory,address-arena)[0]
        e1=word(root+((va>>36)&2047)*8)
        if e1&3!=3:return None
        e2=word((e1&MASK)+((va>>25)&2047)*8)
        if e2&3!=3:return None
        leaf=word((e2&MASK)+((va>>14)&2047)*8)
        if leaf&3!=3:return None
        return leaf
    def test_exact_owned_leaf_translations_and_boundary_crossings(self):
        for va,pa,size in ((VA,0x80004000,2*1024*1024),(VA,0x81ffc000,20*1024*1024)):
            status,used,memory,arena,pool=self.run_mapper(va,pa,size)
            self.assertEqual(status,0)
            self.assertTrue(2*PAGE<used<=POOL and used%PAGE==0)
            for root,start in ((pool,pa),(pool+PAGE,va)):
                for displacement in range(0,size,PAGE):
                    self.assertEqual(self.lookup(memory,arena,root,start+displacement),(pa+displacement)|LEAF)
                self.assertIsNone(self.lookup(memory,arena,root,start-PAGE))
                self.assertIsNone(self.lookup(memory,arena,root,start+size))
            self.assertEqual(memory[:PAGE],b'\xa5'*PAGE)
            self.assertEqual(memory[PAGE+POOL:],b'\xa5'*(2*PAGE))
    def test_refusal_preflight_before_any_table_write(self):
        pa=0x80000000;pool=pa+PAGE;size=2*1024*1024
        cases=((VA,pa,0,pool,POOL),(VA,pa,MAX+PAGE,pool,POOL),(VA+1,pa,size,pool,POOL),
            (VA,pa+1,size,pool,POOL),(VA,pa,size-1,pool,POOL),(VA,pa,size,pool+1,POOL),
            (0x800000000000,pa,size,pool,POOL),((1<<64)-PAGE,pa,2*PAGE,pool,POOL),
            ((1<<64)-MAX,pa,MAX,pool,POOL),
            (VA,(1<<40)-PAGE,2*PAGE,pool,POOL),(VA,pa,size,pa-PAGE,POOL),
            (VA,pa,PAGE,pool,POOL),(VA,pa,size,pool,POOL-PAGE))
        for args in cases:
            status,used,memory,_,_=self.run_mapper(*args)
            self.assertNotEqual(status,0)
            self.assertEqual(used,0)
            self.assertEqual(memory,b'\xa5'*len(memory))
    def test_callee_abi_root_layout_and_pool_capacity(self):
        va=(1<<64)-(1<<36)-4*PAGE;pa=(1<<36)-4*PAGE
        status,used,memory,arena,pool=self.run_mapper(va,pa,MAX)
        self.assertEqual((status,used),(0,POOL))
        for root,start in ((pool,pa),(pool+PAGE,va)):
            self.assertEqual(self.lookup(memory,arena,root,start),pa|LEAF)
            self.assertEqual(self.lookup(memory,arena,root,start+MAX-PAGE),(pa+MAX-PAGE)|LEAF)
            self.assertIsNone(self.lookup(memory,arena,root,start+MAX))
        self.assertEqual(memory[:PAGE],b'\xa5'*PAGE)
        self.assertEqual(memory[PAGE+POOL:],b'\xa5'*(2*PAGE))

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--case',action='append',choices=CASE_IDS);args=parser.parse_args()
    out=args.output.resolve();private=(ROOT/'note10/private').resolve()
    if out==private or not out.is_relative_to(private) or out.exists():parser.error('fresh private output required')
    selected=args.case if args.case is not None else json.loads(os.environ.get('N10_CI_CASE_JSON','[]'))
    if type(selected) is not list or len(selected)!=len(set(selected)) or any(n not in CASE_IDS for n in selected):parser.error('closed new case selection required')
    selected=selected or list(CASE_IDS);out.mkdir(parents=True);MapperTests.output=out
    result=unittest.TextTestRunner(verbosity=2).run(unittest.TestSuite(MapperTests(n) for n in selected))
    failed={t._testMethodName for t,_ in result.failures+result.errors if hasattr(t,'_testMethodName')}
    complete=result.testsRun==len(selected)
    report=dict(kind='v93-new-production-leaf-mapper',selected=selected,passed=[n for n in selected if n not in failed] if complete else [],
        tests_run=result.testsRun,failed=sorted(failed),fixture_compiles=MapperTests.compiles,success=result.wasSuccessful() and complete and not result.skipped,
        source_sha256={n:sha((HERE/n).read_bytes()) for n in SOURCES},
        ci_context={k:os.environ.get(k,'') for k in ('GITHUB_SHA','GITHUB_RUN_ID','GITHUB_RUN_ATTEMPT','GITHUB_JOB','GITHUB_WORKFLOW_REF','GITHUB_WORKFLOW_SHA')},
        PC_only=True,physical_ready=False,old_tests_executed=0,device_operations=[],new_mapper_instructions_executed=MapperTests.completed_calls>0,completed_mapper_calls=MapperTests.completed_calls,whole_XNU_kernel_entry_executed=False,hardware_XNU_executed=False,old_whole_entry_emulator_replay=False,fixture_backend='Unicorn2.1.4 actual new routine only')
    (out/'result.json').write_text(json.dumps(report,indent=2)+'\n')
    return 0 if report['success'] else 1
if __name__=='__main__':raise SystemExit(main())
