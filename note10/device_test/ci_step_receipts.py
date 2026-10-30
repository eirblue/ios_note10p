"""Post-command evidence, never a substitute for authentic CI/job success."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess

WORKFLOW='.github/workflows/note10-handoff-kernel.yml'
HELPER='note10/device_test/ci_step_receipts.py'
WORKFLOW_NAME='Note10 temporary handoff kernel build'
REPOSITORY='eirblue/ios_note10p'
FOLDER='ci-step-receipts'
STEPS={'baseline':('baseline_checks','Build the pinned public d2x source with legacy kexec'),
 'materialization':('integrated_diagnostics','Materialize XNU data and build integrated diagnostics')}
COLLECTOR='handoff-kernel/collector-generation-binding-proof.json'
MATERIAL=('handoff-kernel/build-result.json','handoff-kernel/binding-validation-result.json',
 'handoff-kernel/Image','handoff-kernel/handoff.config')
BOOL_INPUTS=('caps','reserve','window_access','xnu_stage','cpu_cache','pm_timer','screen_log','gic_roundtrip',
 'dma_pm_audit','ufs_pm_audit','ehld_lock_audit','ehld_irqsave_audit','ehld_running_lock_audit',
 'cpu_pm_roundtrip','cpu_pm_notifier_counts','cpu_pm_notifier_trace','xnu_runtime_observation','xnu_runtime_scratch','auto_return')
CONTEXT_KEYS=('run_id','attempt','head','repository','workflow','workflow_ref','workflow_sha','job','event','ref','checked_out_head')

def sha(raw):return hashlib.sha256(raw).hexdigest()

def decode_receipt(raw):
    def unique(pairs):
        result={}
        for name,value in pairs:
            if name in result:raise ValueError('duplicate receipt JSON field')
            result[name]=value
        return result
    return json.loads(raw,object_pairs_hook=unique)

def regular(root,name):
    root=Path(root);relative=Path(name)
    if root.is_symlink() or not isinstance(name,str) or relative.is_absolute() or '..' in relative.parts or relative.as_posix()!=name:raise ValueError('unsafe receipt evidence path')
    path=root
    for part in relative.parts:
        path=path/part
        if path.is_symlink():raise ValueError('receipt evidence symlink')
    if not path.is_file() or not path.resolve().is_relative_to(root.resolve()):raise ValueError('receipt evidence missing/escaped')
    return path

def file_hash(path):
    with Path(path).open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()

def inputs_valid(inputs):
    if not isinstance(inputs,dict) or set(inputs)!=set(BOOL_INPUTS)|{'xnu_artifact_run_id'}:raise ValueError('exact original dispatch input set required')
    if any(type(inputs[n]) is not str or inputs[n] not in ('true','false') for n in BOOL_INPUTS):raise ValueError('dispatch booleans must retain original event strings')
    if not isinstance(inputs['xnu_artifact_run_id'],str) or re.fullmatch('[1-9][0-9]*',inputs['xnu_artifact_run_id']) is None:raise ValueError('upstream artifact input invalid')
    if any(inputs[n]!='true' for n in BOOL_INPUTS if n!='screen_log') or inputs['screen_log']!='false':raise ValueError('receipts require exact full headless scratch diagnostic mode')

def context_valid(context):
    if not isinstance(context,dict) or set(context)!=set(CONTEXT_KEYS):raise ValueError('CI receipt context schema differs')
    if type(context['run_id']) is not int or context['run_id']<=0 or type(context['attempt']) is not int or context['attempt']!=1:raise ValueError('fresh exact run/attempt required')
    head=context['head']
    if not isinstance(head,str) or re.fullmatch('[0-9a-f]{40}',head) is None:raise ValueError('receipt head invalid')
    expected={'repository':REPOSITORY,'workflow':WORKFLOW_NAME,'workflow_ref':REPOSITORY+'/'+WORKFLOW+'@refs/heads/main',
      'workflow_sha':head,'job':'kernel','event':'workflow_dispatch','ref':'refs/heads/main','checked_out_head':head}
    if any(context[n]!=value for n,value in expected.items()):raise ValueError('actual CI workflow/job/checkout context differs')

def command_block(workflow,step):
    try:text=workflow.decode('utf8')
    except UnicodeError as error:raise ValueError('workflow encoding invalid') from error
    if 'continue-on-error:' in text or 'set +e' in text:raise ValueError('required workflow failure chain weakened')
    identity,name=STEPS[step];lines=text.splitlines(keepends=True)
    starts=[i for i,line in enumerate(lines) if line.rstrip('\r\n')=='      - name: '+name]
    if len(starts)!=1:raise ValueError('unique required workflow step missing')
    start=starts[0];end=next((i for i in range(start+1,len(lines)) if lines[i].startswith('      - ')),len(lines))
    block=''.join(lines[start:end])
    if block.count('        id: '+identity+'\n')!=1 or block.count('        shell: bash --noprofile --norc -euo pipefail {0}\n')!=1:raise ValueError('fixed step ID/explicit fail-fast shell missing')
    tail=('          if [ "$NOTE10_XNU_RUNTIME_SCRATCH" = true ]; then\n'
      '            python note10/device_test/ci_step_receipts.py --step '+step+'\n          fi\n')
    if not block.endswith(tail) or block.count('ci_step_receipts.py --step ')!=1:raise ValueError('receipt is not the final post-command action')
    condition='        if: inputs.xnu_stage\n'
    if (step=='materialization' and block.count(condition)!=1) or (step=='baseline' and '        if:' in block):raise ValueError('required step condition differs')
    return sha(block.encode())

def output_names(step):return (COLLECTOR,) if step=='baseline' else MATERIAL

def validate_document(document,step,artifact,context,inputs,source_loader):
    context_valid(context);inputs_valid(inputs)
    keys={'schema','kind','step_id','step_name','context','dispatch_inputs','source_sha256','command_block_sha256',
      'command_exit_code','command_block_completed','whole_CI_accepted','fixture_only','outputs','input_evidence'}
    if not isinstance(document,dict) or set(document)!=keys or type(document['schema']) is not int or document['schema']!=1:raise ValueError('step receipt schema differs')
    if (document['kind']!='post-command CI step evidence' or document['step_id']!=STEPS[step][0] or document['step_name']!=STEPS[step][1] or
        document['context']!=context or document['dispatch_inputs']!=inputs or type(document['command_exit_code']) is not int or
        document['command_exit_code']!=0 or document['command_block_completed'] is not True or
        document['whole_CI_accepted'] is not False or document['fixture_only'] is not False):raise ValueError('step completion/context/input/fixture facts differ')
    source={n:sha(source_loader(n)) for n in (WORKFLOW,HELPER)}
    if document['source_sha256']!=source or document['command_block_sha256']!=command_block(source_loader(WORKFLOW),step):raise ValueError('exact workflow/helper/command identity differs')
    if set(document['outputs'])!=set(output_names(step)):raise ValueError('step output inventory differs')
    members={}
    for name,item in document['outputs'].items():
        if not isinstance(item,dict) or set(item)!={'sha256','size','snapshot'}:raise ValueError('output evidence shape differs')
        current=regular(artifact,name)
        if type(item['size']) is not int or item['size']!=current.stat().st_size or item['sha256']!=file_hash(current):raise ValueError('actual artifact output differs')
        members[name]=item['sha256']
        should_snapshot=name.endswith('.json')
        snapshot=FOLDER+'/'+step+'/snapshots/'+Path(name).name if should_snapshot else None
        if item['snapshot']!=snapshot:raise ValueError('fixed output snapshot path differs')
        if snapshot:
            saved=regular(artifact,snapshot)
            if saved.stat().st_size!=item['size'] or file_hash(saved)!=item['sha256']:raise ValueError('retained step output snapshot differs')
            members[snapshot]=item['sha256']
    if step=='baseline':
        if json.loads(regular(artifact,COLLECTOR).read_bytes()).get('passed') is not True or document['input_evidence']!={}:raise ValueError('baseline source-test proof differs')
    else:
        report=json.loads(regular(artifact,MATERIAL[0]).read_bytes());manifest_raw=regular(artifact,MATERIAL[1]).read_bytes();manifest=json.loads(manifest_raw)
        if (report.get('build_passed') is not True or report.get('failure') is not None or manifest.get('build_completed') is not True or
            manifest.get('identity')!={'project_head':context['head'],'run_id':context['run_id'],'attempt':context['attempt'],'kernel_source_commit':report.get('source_commit')} or
            report.get('binding_validation_result_sha256')!=sha(manifest_raw) or
            report.get('image_sha256')!=document['outputs'][MATERIAL[2]]['sha256'] or report.get('effective_config_sha256')!=document['outputs'][MATERIAL[3]]['sha256']):raise ValueError('final report/canonical manifest/Image/config binding differs')
        evidence=document['input_evidence'];snapshot=FOLDER+'/materialization/inputs/payload-manifest.json'
        if not isinstance(evidence,dict) or set(evidence)!={'payload_sha256','payload_size','manifest_sha256','manifest_snapshot'} or evidence['manifest_snapshot']!=snapshot:raise ValueError('material input evidence shape differs')
        raw=regular(artifact,snapshot).read_bytes();payload_manifest=json.loads(raw)
        if (sha(raw)!=evidence['manifest_sha256'] or evidence['payload_sha256']!=report.get('xnu_payload_sha256') or
            type(evidence['payload_size']) is not int or evidence['payload_size']!=report.get('xnu_payload_size') or
            payload_manifest.get('payload_sha256')!=evidence['payload_sha256'] or payload_manifest.get('payload_size')!=evidence['payload_size']):raise ValueError('actual staged payload input binding differs')
        members[snapshot]=sha(raw)
    return members

def validate_pair(artifact,context,inputs,source_loader):
    artifact=Path(artifact);folder=artifact/FOLDER
    if folder.is_symlink() or not folder.is_dir():raise ValueError('fresh post-command receipts missing')
    receipts=[p.relative_to(artifact).as_posix() for p in folder.rglob('receipt.json')]
    expected=[FOLDER+'/'+step+'/receipt.json' for step in STEPS]
    if set(receipts)!=set(expected) or len(receipts)!=2:raise ValueError('missing/duplicate/conflicting step receipts')
    members={}
    for step,path in zip(STEPS,expected):
        raw=regular(artifact,path).read_bytes();members[path]=sha(raw)
        members.update(validate_document(decode_receipt(raw),step,artifact,context,inputs,source_loader))
    return {'receipt_sha256':{n:members[n] for n in expected},'artifact_members_sha256':members,
      'whole_CI_acceptance_claimed_by_receipts':False}

def produce(step,root,environment):
    root=Path(root);event=json.loads(Path(environment['GITHUB_EVENT_PATH']).read_bytes());inputs=event.get('inputs')
    inputs_valid(inputs)
    context={'run_id':int(environment['GITHUB_RUN_ID']),'attempt':int(environment['GITHUB_RUN_ATTEMPT']),
      'head':environment['GITHUB_SHA'],'repository':environment['GITHUB_REPOSITORY'],'workflow':environment['GITHUB_WORKFLOW'],
      'workflow_ref':environment['GITHUB_WORKFLOW_REF'],'workflow_sha':environment['GITHUB_WORKFLOW_SHA'],
      'job':environment['GITHUB_JOB'],'event':environment['GITHUB_EVENT_NAME'],'ref':environment['GITHUB_REF'],
      'checked_out_head':subprocess.check_output(['git','-C',str(root),'rev-parse','HEAD'],text=True).strip()}
    context_valid(context)
    if event.get('repository',{}).get('full_name')!=context['repository']:raise ValueError('event repository differs')
    artifact=root/'note10/private';destination=artifact/FOLDER/step
    if destination.exists() or destination.is_symlink():raise ValueError('step receipt already exists; no replay')
    destination.mkdir(parents=True)
    source={n:sha(regular(root,n).read_bytes()) for n in (WORKFLOW,HELPER)}
    document={'schema':1,'kind':'post-command CI step evidence','step_id':STEPS[step][0],'step_name':STEPS[step][1],
      'context':context,'dispatch_inputs':inputs,'source_sha256':source,
      'command_block_sha256':command_block(regular(root,WORKFLOW).read_bytes(),step),
      'command_exit_code':0,'command_block_completed':True,'whole_CI_accepted':False,'fixture_only':False,
      'outputs':{},'input_evidence':{}}
    for name in output_names(step):
        path=regular(artifact,name);snapshot=FOLDER+'/'+step+'/snapshots/'+path.name if name.endswith('.json') else None
        if snapshot:
            target=artifact/snapshot;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(path.read_bytes())
        document['outputs'][name]={'sha256':file_hash(path),'size':path.stat().st_size,'snapshot':snapshot}
    if step=='materialization':
        payload=regular(artifact,'xnu-stage-payload/kernel.mem');manifest=regular(artifact,'xnu-stage-payload/payload-manifest.json')
        snapshot=FOLDER+'/materialization/inputs/payload-manifest.json';target=artifact/snapshot;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(manifest.read_bytes())
        document['input_evidence']={'payload_sha256':file_hash(payload),'payload_size':payload.stat().st_size,'manifest_sha256':file_hash(manifest),'manifest_snapshot':snapshot}
    validate_document(document,step,artifact,context,inputs,lambda name:regular(root,name).read_bytes())
    with (destination/'receipt.json').open('x',encoding='utf8',newline='\n') as stream:json.dump(document,stream,indent=2);stream.write('\n')

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--step',choices=tuple(STEPS),required=True);args=parser.parse_args()
    produce(args.step,Path(__file__).resolve().parents[2],os.environ)
if __name__=='__main__':main()
