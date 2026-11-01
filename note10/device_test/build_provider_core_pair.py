"""Produce one bounded GNU ET_REL pair link from immutable accepted objects."""
import argparse
import os
from pathlib import Path
import re
import time
import provider_core_pair as pair
import provider_core_pair_input_contract as contract


def produce(control_sha256, output, workspace, source_commit):
    c,control_snap=contract.load_control(control_sha256)
    contract.require(re.fullmatch('[0-9a-f]{40}',source_commit) is not None, 'exact current source commit')
    root=Path(__file__).resolve().parents[2]; sources=contract.source_closure(root)
    output=Path(output).absolute(); workspace=Path(workspace).absolute()
    contract.require(output!=workspace and output not in workspace.parents and workspace not in output.parents and output!=root and workspace!=root, 'disjoint fresh namespaces')
    output.mkdir(); workspace.mkdir()
    result={'schema':'provider-core-pair-result-v1','passed':False,'source_commit':source_commit,'control_sha256':control_sha256,'input_ELF_parses':0,'old_query_or_semantic_calls':0,'fixture_calls':0,'link_count':0,'version_count':0,'nonclaims':c['nonclaims']}
    try:
        context={'repository':os.environ.get('GITHUB_REPOSITORY',''),'run_id':int(os.environ.get('GITHUB_RUN_ID','0')),'run_attempt':int(os.environ.get('GITHUB_RUN_ATTEMPT','0')),'job':os.environ.get('GITHUB_JOB',''),'source_commit':source_commit}
        contract.require(context['repository']==c['accepted_v66']['repository'] and context['run_id']>0 and context['run_attempt']==1 and context['job']=='provider-core-pair','actual current CI context')
        result['ci_context']=context
        (output/'commands').mkdir(); (output/'inputs').mkdir(); (output/'evidence').mkdir()
        (workspace/'inputs').mkdir(); (workspace/'paired').mkdir()
        raw,buffers=contract.retrieve_old(c,output/'inputs'/'retrieval')
        contract.write_bytes(output/'inputs'/'v66.zip',raw)
        selected={}; copies=[]
        for role in ('provider','core'):
            rec=c['accepted_v66']['members'][role]; data=buffers[rec['member']]; selected[role]=data
            snap=contract.write_bytes(workspace/'inputs'/(role+'.o'),data); copies.append(snap)
            contract.write_bytes(output/'evidence'/(role+'.o'),data)
        tool=c['link_profile']['tool']; binary=contract.snapshot(tool['path'],c['caps']['tool_binary'])
        contract.require(binary['sha256']==tool['sha256'] and str(Path(tool['path']).resolve())==tool['path'], 'exact retained GNU executable')
        environment={'PATH':os.environ.get('PATH',''),'LC_ALL':'C','LANG':'C','TZ':'UTC'}
        result['version_count']=1
        version,version_receipt=contract.capture([tool['path'],'--version'],workspace,output/'commands','version',c['caps']['command_stdout'],180,environment)
        contract.require(version==tool['version'].encode(), 'exact full fresh GNU version')
        contract.unchanged(binary)
        argv=[tool['path']]+c['link_profile']['exact_argv'][1:]
        target=workspace/'paired'/'provider-core-pair.o'; contract.require(not target.exists(), 'fresh output absent')
        for snap in copies: contract.unchanged(snap)
        result['link_count']=1
        _,link_receipt=contract.capture(argv,workspace,output/'commands','link',c['caps']['command_stdout'],180,environment)
        linked=contract.snapshot(target,c['caps']['ELF'])
        contract.require(link_receipt['started_ns']<=linked['identity'][4]<=link_receipt['ended_ns'], 'fresh output within actual link interval')
        for snap in copies: contract.unchanged(snap)
        contract.unchanged(binary); contract.unchanged(control_snap)
        result.update(tool=tool,commands={'version':version_receipt,'link':link_receipt},link_environment=environment,output={'bytes':linked['bytes'],'sha256':linked['sha256']},accepted_v66_ZIP_sha256=c['accepted_v66']['ZIP']['sha256'],accepted_private_result_sha256=c['accepted_v66']['accepted_private_result']['sha256'],query_result_sha256=c['frozen_input_profile']['attribution']['accepted_query_result_sha256'])
        result['stable_capture']={}
        for role,snap in [('provider',copies[0]),('core',copies[1]),('linker',binary),('output',linked)]:
            contract.unchanged(snap); result['stable_capture'][role]={'bytes':snap['bytes'],'sha256':snap['sha256'],'before':list(snap['identity']),'after':list(contract.identity(contract.ordinary(snap['path'])))}
        contract.verify_stability(result,c)
        logs={}
        for label in ('version','link'):
            for suffix in ('stdout','stderr','receipt.json'):
                name='commands/'+label+'.'+suffix; logs[name]=contract.snapshot(output/name,8*1024*1024)['raw']
        contract.verify_command_evidence(c,result,logs)
        projection=pair.prove(c['frozen_input_profile'],selected,pair.parse_output(linked['raw']))
        contract.unchanged(linked)
        contract.write_bytes(output/'evidence'/'provider-core-pair.o',linked['raw'])
        contract.write_json(output/'projection.json',projection)
        for name,row in sources.items():
            snap=contract.snapshot(root/name,8*1024*1024,row)
            dest=output/'source'/name; dest.parent.mkdir(parents=True,exist_ok=True)
            contract.write_bytes(dest,snap['raw']); contract.unchanged(snap)
        contract.require(contract.source_closure(root)==sources, 'source closure unchanged through production')
        contract.write_json(output/'source-manifest.json',sources)
        result.update(passed=True,files=contract.inventory(output),completed_ns=time.time_ns())
        contract.write_json(output/'result.json',result)
        return result
    except Exception as exc:
        result.update(passed=False,exception=contract.exception_record(exc),files=contract.inventory(output))
        contract.write_json(output/'result.json',result)
        raise


def main():
    parser=argparse.ArgumentParser(); parser.add_argument('--control-sha256',required=True); parser.add_argument('--output',required=True); parser.add_argument('--workspace',required=True)
    args=parser.parse_args(); produce(args.control_sha256,args.output,args.workspace,os.environ.get('GITHUB_SHA',''))


if __name__=='__main__': main()
