"""Produce a new data-only finite relation from reviewed immutable records."""
import argparse
import os
from pathlib import Path
import re
import paired_layout_relation as relation
import paired_layout_input_contract as contract


def produce(control_sha256,output):
    output=Path(output).absolute(); contract.parent_identities(output)
    output.mkdir(); result={'schema':'paired-layout-result-v1','passed':False,'control_sha256':control_sha256,'input_ELF_DWARF_parses':0,'old_query_proof_helper_calls':0,'compiler_linker_make_calls':0,'fixture_calls':0}
    try:
        control,control_snap=contract.load_control(control_sha256); root=Path(__file__).resolve().parents[2]; sources=contract.source_closure(root)
        context={'repository':os.environ.get('GITHUB_REPOSITORY',''),'source_commit':os.environ.get('GITHUB_SHA',''),'run_id':int(os.environ.get('GITHUB_RUN_ID','0')),'run_attempt':int(os.environ.get('GITHUB_RUN_ATTEMPT','0')),'job':os.environ.get('GITHUB_JOB','')}
        contract.require(context['repository']==control['accepted_v67']['repository'] and re.fullmatch('[0-9a-f]{40}',context['source_commit']) is not None and context['run_id']>0 and context['run_attempt']==1 and context['job']=='paired-layout-relation','exact current producer CI context')
        result.update(ci_context=context,source_commit=context['source_commit'],nonclaims=control['nonclaims'])
        (output/'inputs').mkdir(); (output/'evidence').mkdir()
        original,ledger=contract.retrieve(control['accepted_v67'],output/'inputs'/'retrieval')
        files,buffers=contract.zip_snapshot(original,control['accepted_v67']['complete_member_map'])
        contract.write_json(output/'inputs'/'retrieval'/'retrieval.json',ledger); original_snap=contract.write_bytes(output/'inputs'/'v67.zip',original)
        accepted=control['accepted_v67']; object_snap=contract.write_bytes(output/'evidence'/'provider-core-pair.o',buffers[accepted['object']['member']])
        slices=contract.bind_object(control,object_snap['raw'])
        observed=relation.compare(control['finite_profile'],control['relation_policy'],control['caps'],control['nonclaims'])
        contract.unchanged(object_snap); contract.unchanged(original_snap); contract.unchanged(control_snap)
        contract.write_json(output/'relation.json',observed)
        for name,row in sources.items():
            snap=contract.snapshot(root/name,8*1024*1024,row); target=output/'source'/name; target.parent.mkdir(parents=True,exist_ok=True); contract.write_bytes(target,snap['raw']); contract.unchanged(snap)
        contract.require(contract.source_closure(root)==sources,'current source/control bytes stable through production')
        contract.write_json(output/'source-manifest.json',sources)
        result.update(passed=True,accepted_original_ZIP_sha256=accepted['ZIP']['sha256'],accepted_private_result_sha256=accepted['accepted_private_result_sha256'],accepted_producer_result_sha256=accepted['producer_result']['sha256'],raw_measurement_attribution=control['measurement_attribution'],raw_debug_slices=slices,source_sha256=sources,files=contract.inventory(output))
        contract.write_json(output/'result.json',result); return result
    except Exception as exc:
        result.update(passed=False,exception=contract.exception_record(exc),files=contract.inventory(output)); contract.write_json(output/'result.json',result); raise


def main():
    p=argparse.ArgumentParser(); p.add_argument('--control-sha256',required=True); p.add_argument('--output',required=True); a=p.parse_args(); produce(a.control_sha256,a.output)


if __name__=='__main__': main()
