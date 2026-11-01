"""New synthetic pair-only cases; no accepted control/object proof fixtures."""
import argparse
import json
from pathlib import Path
import tempfile
import build_provider_core_pair as builder
import provider_core_pair as pair
import provider_core_pair_input_contract as contract

CASES = ('pair-link-normal-origin-positive', 'pair-registration-reference-defined-positive', 'pair-selected-input-bytes-preserved-positive', 'pair-anonymous-array-rebase-positive', 'pair-callback-target-origin-positive', 'pair-current-unresolved-frontier-positive', 'pair-missing-output-target-reject', 'pair-remains-undefined-reject', 'pair-wrong-strong-origin-reject', 'pair-duplicate-strong-target-reject', 'pair-weak-common-absolute-target-reject', 'pair-visibility-info-drift-reject', 'pair-selected-input-collision-reject', 'pair-selected-section-concatenation-reject', 'pair-selected-byte-rewrite-reject', 'pair-section-flags-align-extent-drift-reject', 'pair-init-relocation-missing-extra-reject', 'pair-call-kind-place-drift-reject', 'pair-call-addend-coordinate-drift-reject', 'pair-call-target-name-only-match-reject', 'pair-unapproved-symbol-rebase-reject', 'pair-array-target-other-input-reject', 'pair-table-relocation-drift-reject', 'pair-callback-output-owner-ambiguity-reject', 'pair-reference-target-section-merge-reject', 'pair-output-not-supported-ET_REL-reject', 'pair-input-reused-or-modified-during-link-reject', 'pair-command-input-order-or-extra-arg-reject', 'pair-second-link-receipt-reject', 'pair-linker-path-binary-version-drift-reject', 'pair-unsupported-prelink-origin-inventory-reject', 'pair-old-proof-accepted-as-new-result-reject', 'pair-recompiled-input-substitution-reject', 'pair-new-boundary-nonclaims-preserved')


def synthetic():
    inputs={'provider':b'','core':b''}; spans=[]; definitions={}; out_sections=[{'index':0,'name':'','bytes':b'','size':0}]; out_symbols=[dict(index=0,name='',info=0,other=0,section=0,value=0,size=0)]; mapped={}
    names=['.text.fixture_start','.data.fixture_table','.text.fixture_a','.text.fixture_b','.text.fixture_c','.text.fixture_d','.text.fixture_e','.text.fixture_register','.text.fixture_sub_a','.text.fixture_sub_b']
    symnames=['fixture_start','fixture_table','fixture_a','fixture_b','fixture_c','fixture_d','fixture_e','crypto_register_shashes','fixture_sub_a','fixture_sub_b']
    for i,name in enumerate(names):
        role='provider' if i<7 else 'core'; idx=101+i; size=160; data=bytes([30+i])*size; offset=len(inputs[role]); inputs[role]+=data
        section=dict(index=idx,name=name,name_offset=0,type=1,flags=3 if i==1 else 6,offset=offset,size=size,link=0,info=0,alignment=8,entsize=0)
        row={'role':role,'object_sha256':'','section':section,'section_bytes_sha256':pair.digest(data),'reasons':['invented fixture span'],'all_same_name_contributions':[]}; spans.append(row)
        info=1 if i==1 else (2 if i in (0,2,4,6) else 18)
        sym=dict(index=201+i,name=symnames[i],info=info,other=0,section=idx,value=0,size=size); definitions[i]=sym
        out=dict(section,index=i+1,offset=0,bytes=data); out_sections.append(out); mapped[i]=i+1
        out_symbols.append(dict(sym,index=len(out_symbols),section=i+1))
    records={role:{'bytes':len(raw),'sha256':pair.digest(raw),'member':'invented/'+role+'.o'} for role,raw in inputs.items()}
    for row in spans:
        row['object_sha256']=records[row['role']]['sha256']; row['all_same_name_contributions']=[dict(row['section'],role=row['role'],object_sha256=row['object_sha256'])]
    groups=[]; refs=[]; output_rela=[]
    plan=[(0,'init',[(16,275,1),(32,277,1),(48,283,7)]),(1,'table',[(i*8,257,target) for i,target in enumerate((2,3,4,5,6,3,4,5))]),(7,'registration_target',[(24,283,8),(72,283,9)])]
    for source,purpose,rows in plan:
        role=spans[source]['role']; old=[]
        for entry,(place,typ,target) in enumerate(rows):
            target_role=spans[target]['role']; defined=definitions[target]
            undefined=source==0 and target==7
            anonymous=not undefined and defined['info'] in (1,2)
            raw=dict(index=401+len(refs),name='',info=3,other=0,section=defined['section'],value=0,size=0) if anonymous else dict(defined)
            if undefined: raw=dict(index=501,name='crypto_register_shashes',info=16,other=0,section=0,value=0,size=0)
            rr=dict(section=definitions[source]['section'],offset=place,type=typ,symbol=raw['index'],addend=0,relocation_section=601+source,entry=entry); old.append(rr)
            ref={'origin_role':role,'selected_purpose':purpose,'relocation':rr,'raw_target_symbol':raw,'destination_role':target_role,'destination_section_name':spans[target]['section']['name'],'destination_coordinate':0}
            if undefined: ref.update(required_definition=defined,allowed_output_forms=['named_defined_registration_target_only']); output_symbol=next(x for x in out_symbols if x['name']=='crypto_register_shashes')
            else:
                ref.update(target_coordinate=0,coordinate_definition_candidates=[defined],allowed_output_forms=['anonymous_local_section_symbol_only'] if anonymous else ['same_named_definition','anonymous_local_section_symbol_with_exact_coordinate_rebase'])
                if anonymous:
                    output_symbol=dict(index=len(out_symbols),name='',info=3,other=0,section=mapped[target],value=0,size=0); out_symbols.append(output_symbol)
                else: output_symbol=next(x for x in out_symbols if x['name']==defined['name'])
            refs.append(ref); output_rela.append(dict(rr,section=mapped[source],symbol=output_symbol['index'],relocation_section=701+source))
        groups.append(dict(role=role,purpose=purpose,raw_symbol=definitions[source],accepted_label=definitions[source],full_section_extent=True,raw_complete_section_RELA=old))
    candidates=[{'name':definitions[i]['name'],'definitions':[{'role':spans[i]['role'],'object_sha256':records[spans[i]['role']]['sha256'],'raw_symbol':definitions[i],'eligible_strong_normal_definition':True}]} for i in (3,5,7,8,9)]
    profile={'object_records':records,'selected_direct_spans':spans,'selected_complete_RELA':groups,'direct_named_definition_candidates':candidates,'relocation_destinations_and_allowed_forms':refs,'selected_RELA_width_bytes':{'257':8,'275':4,'277':4,'283':4},'selected_RELA_count':13,'global_same_name_group_count':21}
    out_symbols.append(dict(index=len(out_symbols),name='fixture_unresolved_service',info=16,other=0,section=0,value=0,size=0))
    output={'sha256':pair.digest(b'invented output fixture'),'bytes':640,'sections':out_sections,'symbols':out_symbols,'relocations':output_rela}
    return profile,inputs,output


def commands():
    tool={'path':'/invented/ld','role':'aarch64-linux-gnu-ld','sha256':contract.digest(b'invented tool'),'version':'invented full version\n'}
    argv=['<pinned-resolved-GNU-ld>','-m','aarch64linux','--no-relax','-r','-o','paired/provider-core-pair.o','inputs/provider.o','inputs/core.o']
    control={'link_profile':{'tool':tool,'exact_argv':argv}}
    result={'tool':tool,'link_count':1,'version_count':1,'link_environment':{'PATH':'/invented','LC_ALL':'C','LANG':'C','TZ':'UTC'},'commands':{}}; buffers={}
    for label in ('version','link'):
        stdout=tool['version'].encode() if label=='version' else b''; stderr=b''
        row={'label':label,'argv':[tool['path'],'--version'] if label=='version' else [tool['path']]+argv[1:],'returncode':0,'started_ns':1 if label=='version' else 3,'ended_ns':2 if label=='version' else 4,'stdout':{'bytes':len(stdout),'sha256':contract.digest(stdout)},'stderr':{'bytes':0,'sha256':contract.digest(stderr)},'failure':None,'reaped':True}
        result['commands'][label]=row
        for suffix,data in (('stdout',stdout),('stderr',stderr),('receipt.json',contract.json_bytes(row))): buffers['commands/'+label+'.'+suffix]=data
    return control,result,buffers


def rejects(call):
    try: call()
    except (ValueError,KeyError,IndexError): return
    raise AssertionError('required rejection did not occur')


def run_case(name):
    p,inputs,out=synthetic(); proof=lambda:pair.prove(p,inputs,out); i=CASES.index(name)
    if i in (0,1,2,3,4,5,33):
        projection=proof()
        if i==1: contract.require(any(x['output_target']['name']=='crypto_register_shashes' and x['output_target']['section']>0 for x in projection['selected_RELA']),'registration defined')
        if i==2: contract.require(len(projection['finite_spans'])==10,'all full spans')
        if i==3: contract.require(any(x['output_target']['info']==3 for x in projection['selected_RELA']),'anonymous coordinate form')
        if i==4: contract.require(len(projection['selected_RELA'])==13,'complete table/core callback rows')
        if i==5: contract.require([x['name'] for x in projection['unresolved_raw']]==['','fixture_unresolved_service'],'complete unresolved including null')
        if i==33: contract.require(projection['input_ELF_parses']==projection['old_query_or_semantic_calls']==0 and projection['binary_ABI_proven'] is False and projection['registration_execution_proven'] is False and projection['global_input_same_name_groups_outside_claim']==21,'finite nonclaims')
        return
    if i==6: out['symbols']=[x for x in out['symbols'] if x['name']!='crypto_register_shashes']
    elif i==7: next(x for x in out['symbols'] if x['name']=='crypto_register_shashes')['section']=0
    elif i==8: next(x for x in out['symbols'] if x['name']=='crypto_register_shashes')['section']=3
    elif i==9: out['symbols'].append(dict(next(x for x in out['symbols'] if x['name']=='crypto_register_shashes'),index=999))
    elif i==10:
        for change in ({'info':34},{'section':65521},{'section':65522}):
            pp,ii,oo=synthetic(); next(x for x in oo['symbols'] if x['name']=='crypto_register_shashes').update(change); rejects(lambda:pair.prove(pp,ii,oo))
        return
    elif i==11: next(x for x in out['symbols'] if x['name']=='crypto_register_shashes')['other']=2
    elif i==12: p['selected_direct_spans'][0]['all_same_name_contributions'].append(dict(p['selected_direct_spans'][0]['all_same_name_contributions'][0]))
    elif i==13: out['sections'][1]['bytes']+=b'x'; out['sections'][1]['size']+=1
    elif i==14: out['sections'][2]['bytes']=b'!'+out['sections'][2]['bytes'][1:]
    elif i==15: out['sections'][4]['alignment']=16
    elif i==16: out['relocations'].pop(0)
    elif i==17: out['relocations'][2]['type']=282
    elif i==18: out['relocations'][2]['addend']=8
    elif i==19: next(x for x in out['symbols'] if x['name']=='crypto_register_shashes')['value']=8
    elif i==20: out['symbols'][out['relocations'][0]['symbol']]['info']=19
    elif i==21: out['symbols'][out['relocations'][0]['symbol']]['section']=9
    elif i==22: out['relocations'][4]['offset']+=8
    elif i==23: out['sections'].append(dict(out['sections'][3],index=len(out['sections'])))
    elif i==24: out['sections'][9]['size']+=8
    elif i==25: rejects(lambda:pair.parse_output(b'invented non-ELF output')); return
    elif i==26:
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'fresh'; snap=contract.write_bytes(path,b'invented first bytes'); path.write_bytes(b'invented changed bytes'); rejects(lambda:contract.unchanged(snap))
        return
    elif i in (27,28,29,31):
        c,result,buffers=commands()
        if i==27: result['commands']['link']['argv'][-2:]=list(reversed(result['commands']['link']['argv'][-2:]))
        elif i==28: result['link_count']=2
        elif i==29: result['tool']=dict(result['tool'],sha256=contract.digest(b'other invented tool'))
        else: result={'passed':True,'proof':'invented historical result'}
        rejects(lambda:contract.verify_command_evidence(c,result,buffers)); return
    elif i==30: p['selected_direct_spans'][0]['object_sha256']=contract.digest(b'other invented source')
    elif i==32: inputs['provider']=b'?'+inputs['provider'][1:]
    else: raise AssertionError('unassigned new case')
    rejects(proof)


def main():
    parser=argparse.ArgumentParser()
    for arg in ('checkpoint','checkpoint-sha256','inventory','inventory-sha256','output'): parser.add_argument('--'+arg,required=True)
    a=parser.parse_args(); completed=[]; current=None; attribution={'checkpoint_sha256':a.checkpoint_sha256,'inventory_sha256':a.inventory_sha256,'role':'public'}
    contract.require(not Path(a.output).exists(),'fresh exclusive case receipt')
    try:
        checkpoint=contract.snapshot(a.checkpoint,8*1024*1024); cp=contract.parse_json(checkpoint['raw']); contract.require(checkpoint['sha256']==a.checkpoint_sha256,'checkpoint SHA')
        inventory=contract.snapshot(a.inventory,8*1024*1024); contract.require(inventory['sha256']==a.inventory_sha256==cp['inventory']['sha256'],'frozen inventory SHA')
        ids=contract.parse_json(inventory['raw']); contract.require(tuple(ids['public'])==CASES and len(CASES)==34 and ids['private_count']==8,'ordered42 new-only inventory')
        root=Path(__file__).resolve().parents[2]
        for name,row in cp['production_sources'].items(): contract.snapshot(root/name,8*1024*1024,row)
        contract.require(cp['control']==cp['production_sources']['note10/device_test/provider_core_pair_control.json'],'actual blob hash preflight only; never fixture proof input')
        for current in CASES: run_case(current); completed.append(current)
        contract.write_json(a.output,dict(attribution,passed=True,completed=completed,completed_count=len(completed),next_case=None))
    except Exception as exc:
        contract.write_json(a.output,dict(attribution,passed=False,completed=completed,completed_count=len(completed),next_case=current,exception=contract.exception_record(exc))); raise


if __name__=='__main__': main()
