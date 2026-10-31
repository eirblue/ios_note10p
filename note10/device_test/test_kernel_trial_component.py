"""Only new source/entry/dependency/relocation/component-stack gate fixtures."""
import argparse
import copy
from pathlib import Path
import struct
from relocation_trial_aarch64_model import entry_contract,report_entry_contract,private_path,sha,write
from prepare_kernel_trial_component import render,ENTRY
from kernel_trial_object import component_closure,relocate,stack_estimate,usage_frames
import prepare_xnu_runtime_plan as canonical

CASE_INVENTORY=('source-default-off','source-enabled-uninvoked','source-duplicate-rejected','source-nonboolean-rejected',
 'entry-default','entry-explicit-adapter','entry-without-optin-rejected','entry-unreviewed-rejected','report-selected-entry-rejected',
 'component-leaf-stack','generic-counts-rejecting-tenth-frame','missing-frame-rejected','stack-margin-rejected','duplicate-SU-row-rejected',
 'CALL26-resynthesizes-opcode-and-bits','ADRP-resynthesizes-page-bits','unknown-relocation-rejected',
 'disabled-object','disabled-component-rejected','closed-uninvoked-object','boot-reference-rejected','OS-provider-rejected',
 'dependency-canonical-key','dependency-escape-rejected')

def synthetic_object():
    sections=[{'index':0,'name':'','flags':0,'bytes':b''}]
    for name,flags,size in (('.n10_abi',2,8),('.n10_stack',2,16),('.text.'+ENTRY,6,4),('.text.n10_rt_trial',6,4),('.text.n10_rt_plan',6,4),('.text.adt_node',6,4),('.init.text',6,4)):
        sections.append({'index':len(sections),'name':name,'flags':flags,'bytes':b'\0'*size})
    symbols=[{'name':name,'section':index,'value':0,'size':4,'info':18 if name!='adt_node' else 2} for name,index in ((ENTRY,3),('n10_rt_trial',4),('n10_rt_plan',5),('adt_node',6))]
    rels=[{'section':index,'offset':0,'type':283,'addend':0,'symbol':symbols[target]} for index,target in ((3,1),(4,2),(5,3))]
    return {'sections':sections,'symbols':symbols,'relocations':rels}

def run_cases(key_helper):
    rows=[]
    def check(name,call,reject=False):
        try:call()
        except ValueError:
            if not reject:raise
        else:
            if reject:raise AssertionError('invalid new component fixture admitted: '+name)
        rows.append({'name':name,'passed':True})
    init=b'prefix\n'+canonical.CANON_INCLUDE+b'\nbody';config=b'config ARM64\n'
    def off():
        if render(init,config,False)!=(init,config):raise AssertionError('default modified sources')
    def on():
        a,b=render(init,config,True)
        if b'default n' not in b or a.count(b'#include "kernel_trial_adapter.c"')!=1 or b'n10_kernel_trial_adapter(' in a:raise AssertionError('active adapter hook')
    check('source-default-off',off);check('source-enabled-uninvoked',on)
    check('source-duplicate-rejected',lambda:render(init+b'CONFIG_NOTE10_KERNEL_TRIAL_COMPONENT',config,True),True)
    check('source-nonboolean-rejected',lambda:render(init,config,1),True)
    symbols={'n10_rt_trial':{'info':18,'flags':6,'size':64,'value':0x10000000},ENTRY:{'info':18,'flags':6,'size':16,'value':0x10000100}}
    check('entry-default',lambda:entry_contract(symbols,0x10000000))
    check('entry-explicit-adapter',lambda:entry_contract(symbols,0x10000100,ENTRY))
    check('entry-without-optin-rejected',lambda:entry_contract(symbols,0x10000100),True)
    check('entry-unreviewed-rejected',lambda:entry_contract(symbols,0x10000100,'other'),True)
    check('report-selected-entry-rejected',lambda:report_entry_contract({'entry_symbol':ENTRY}),True)
    frames={ENTRY:16,'n10_rt_trial':128,'n10_rt_plan':256,'adt_node':800};functions=set(frames)
    check('component-leaf-stack',lambda:stack_estimate(frames,functions,16384))
    def generic():
        proof=stack_estimate(frames,functions,16384)
        if proof['generic_ADT_frames_including_rejecting_depth9']!=10 or proof['generic_component_bound']!=32+sum(frames.values())+9*800 or proof['generic_budget_passed']:raise AssertionError('rejecting recursion frame omitted')
    check('generic-counts-rejecting-tenth-frame',generic)
    check('missing-frame-rejected',lambda:stack_estimate({ENTRY:16},functions,16384),True)
    check('stack-margin-rejected',lambda:stack_estimate(frames,functions,8192),True)
    check('duplicate-SU-row-rejected',lambda:usage_frames('a.c:1:1:copy\t16\tstatic\na.c:2:1:copy\t16\tstatic\n'),True)
    def call26():
        if struct.unpack('<I',relocate(struct.pack('<I',0x94000000),0,283,0x1010,0,0x1000))[0]!=0x94000004:raise AssertionError('wrong CALL26 original opcode/value')
    def adrp():
        if struct.unpack('<I',relocate(struct.pack('<I',0x90000000),0,275,0x2000,0,0x1000))[0]!=0xb0000000:raise AssertionError('wrong ADRP page/value')
    check('CALL26-resynthesizes-opcode-and-bits',call26);check('ADRP-resynthesizes-page-bits',adrp)
    check('unknown-relocation-rejected',lambda:relocate(b'\0'*4,0,999,0,0,0),True)
    check('disabled-object',lambda:component_closure({'symbols':[]},False))
    check('disabled-component-rejected',lambda:component_closure(synthetic_object(),False),True)
    check('closed-uninvoked-object',lambda:component_closure(synthetic_object()))
    boot=synthetic_object();boot['relocations'].append({'section':7,'offset':0,'type':283,'addend':0,'symbol':boot['symbols'][0]})
    check('boot-reference-rejected',lambda:component_closure(boot),True)
    os=synthetic_object();os['relocations'].append({'section':4,'offset':0,'type':283,'addend':0,'symbol':{'name':'kmalloc','section':0,'value':0,'info':18,'size':0}})
    check('OS-provider-rejected',lambda:component_closure(os),True)
    roots={'source':'/source','objects':'/objects'}
    def key():
        if key_helper('/source/include/a.h',roots)!='source/include/a.h':raise AssertionError('canonical dependency key differs')
    check('dependency-canonical-key',key)
    check('dependency-escape-rejected',lambda:key_helper('/escape/a.h',roots),True)
    return rows

if __name__=='__main__':
    from build_kernel_trial_component import canonical_key
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--output',type=Path,required=True);a=ap.parse_args();out=private_path(a.output);out.mkdir(parents=True,exist_ok=False)
    write(out/'result.json',{'schema':1,'fixture_only':True,'synthetic_only':True,'hardware_verified':False,'whole_ci_accepted':False,'cases':run_cases(canonical_key),
      'compiler_model_API_executed':False,'source_sha256':{n:sha(Path(__file__).parent/n) for n in ('test_kernel_trial_component.py','kernel_trial_object.py','prepare_kernel_trial_component.py','build_kernel_trial_component.py','relocation_trial_aarch64_model.py')}})
