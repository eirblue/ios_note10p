"""Pure receipt-consumer fixtures. Never call the real receipt producer."""
import argparse
import copy
import json
from pathlib import Path
import tempfile
import ci_step_receipts as p

CASES=('baseline-document','material-document','schema','fixture','old-run','old-attempt','old-head','wrong-job',
 'wrong-step','wrong-input','extra-input','workflow-source','helper-source','command-hash','nonzero-exit','incomplete',
 'whole-CI-claim','baseline-output','material-snapshot','canonical-manifest','payload-input',
 'missing-pair','duplicate-pair','checkout-context','workflow-ref-context','boolean-run-context',
 'workflow-failfast','workflow-error-mask','workflow-postcommand','duplicate-JSON-field')

def reject(call,*args):
    try:call(*args)
    except (ValueError,OSError,KeyError):return True
    raise AssertionError('invalid new receipt/context fixture accepted')

def fixture(root,context,inputs,source):
    kernel=root/'handoff-kernel';kernel.mkdir()
    def save(name,raw):
        path=root/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw)
    collector=json.dumps({'passed':True,'fixture_only':True}).encode();save(p.COLLECTOR,collector)
    image=b'hosted synthetic bytes, not a kernel';config=b'fixture config\n';payload=b'synthetic payload'
    manifest=json.dumps({'build_completed':True,'identity':{'project_head':context['head'],'run_id':context['run_id'],
      'attempt':1,'kernel_source_commit':'55f042627bb7030c93550faafa117674d32b21d1'}}).encode()
    payload_manifest=json.dumps({'payload_sha256':p.sha(payload),'payload_size':len(payload)}).encode()
    report=json.dumps({'build_passed':True,'source_commit':'55f042627bb7030c93550faafa117674d32b21d1',
      'binding_validation_result_sha256':p.sha(manifest),'image_sha256':p.sha(image),
      'effective_config_sha256':p.sha(config),'xnu_payload_sha256':p.sha(payload),'xnu_payload_size':len(payload)}).encode()
    for name,raw in zip(p.MATERIAL,(report,manifest,image,config)):save(name,raw)
    documents={}
    for step,(identity,name) in p.STEPS.items():
        document={'schema':1,'kind':'post-command CI step evidence','step_id':identity,'step_name':name,
          'context':dict(context),'dispatch_inputs':dict(inputs),'source_sha256':{n:p.sha(source[n]) for n in (p.WORKFLOW,p.HELPER)},
          'command_block_sha256':p.command_block(source[p.WORKFLOW],step),'command_exit_code':0,
          'command_block_completed':True,'whole_CI_accepted':False,'fixture_only':False,'outputs':{},'input_evidence':{}}
        for output in p.output_names(step):
            raw=(root/output).read_bytes();snapshot=p.FOLDER+'/'+step+'/snapshots/'+Path(output).name if output.endswith('.json') else None
            if snapshot:save(snapshot,raw)
            document['outputs'][output]={'sha256':p.sha(raw),'size':len(raw),'snapshot':snapshot}
        if step=='materialization':
            snapshot=p.FOLDER+'/materialization/inputs/payload-manifest.json';save(snapshot,payload_manifest)
            document['input_evidence']={'payload_sha256':p.sha(payload),'payload_size':len(payload),
              'manifest_sha256':p.sha(payload_manifest),'manifest_snapshot':snapshot}
        documents[step]=document
    # Documents stay in memory. No completed receipt.json is emitted by tests.
    return documents

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    args.output.mkdir(parents=True,exist_ok=False);project=Path(__file__).resolve().parents[2]
    source={n:(project/n).read_bytes() for n in (p.WORKFLOW,p.HELPER)}
    context={'run_id':11,'attempt':1,'head':'a'*40,'repository':p.REPOSITORY,'workflow':p.WORKFLOW_NAME,
      'workflow_ref':p.REPOSITORY+'/'+p.WORKFLOW+'@refs/heads/main','workflow_sha':'a'*40,'job':'kernel',
      'event':'workflow_dispatch','ref':'refs/heads/main','checked_out_head':'a'*40}
    inputs={n:'false' if n=='screen_log' else 'true' for n in p.BOOL_INPUTS};inputs['xnu_artifact_run_id']='39560904016'
    results={}
    with tempfile.TemporaryDirectory(dir=args.output) as temp:
        root=Path(temp);documents=fixture(root,context,inputs,source)
        for step in p.STEPS:
            p.validate_document(documents[step],step,root,context,inputs,source.__getitem__)
            results['baseline-document' if step=='baseline' else 'material-document']=True
        for name in CASES[2:17]:
            bad=copy.deepcopy(documents['materialization'])
            if name=='schema':bad['schema']=True
            elif name=='fixture':bad['fixture_only']=True
            elif name=='old-run':bad['context']['run_id']=10
            elif name=='old-attempt':bad['context']['attempt']=2
            elif name=='old-head':bad['context']['head']='b'*40
            elif name=='wrong-job':bad['context']['job']='other'
            elif name=='wrong-step':bad['step_id']='baseline_checks'
            elif name=='wrong-input':bad['dispatch_inputs']['screen_log']='true'
            elif name=='extra-input':bad['dispatch_inputs']['unknown']='true'
            elif name=='workflow-source':bad['source_sha256'][p.WORKFLOW]='0'*64
            elif name=='helper-source':bad['source_sha256'][p.HELPER]='0'*64
            elif name=='command-hash':bad['command_block_sha256']='0'*64
            elif name=='nonzero-exit':bad['command_exit_code']=1
            elif name=='incomplete':bad['command_block_completed']=False
            else:bad['whole_CI_accepted']=True
            results[name]=reject(p.validate_document,bad,'materialization',root,context,inputs,source.__getitem__)
        for name,step,target in (('baseline-output','baseline',p.COLLECTOR),
          ('material-snapshot','materialization',p.FOLDER+'/materialization/snapshots/build-result.json'),
          ('canonical-manifest','materialization',p.MATERIAL[1]),
          ('payload-input','materialization',p.FOLDER+'/materialization/inputs/payload-manifest.json')):
            path=root/target;raw=path.read_bytes();path.write_bytes(b'changed fixture')
            results[name]=reject(p.validate_document,documents[step],step,root,context,inputs,source.__getitem__)
            path.write_bytes(raw)
        results['missing-pair']=reject(p.validate_pair,root,context,inputs,source.__getitem__)
        for step in p.STEPS:
            placeholder=root/p.FOLDER/step/'receipt.json';placeholder.write_text('{}')
        extra=root/p.FOLDER/'other/receipt.json';extra.parent.mkdir(parents=True);extra.write_text('{}')
        results['duplicate-pair']=reject(p.validate_pair,root,context,inputs,source.__getitem__)
        for name,key,value in (('checkout-context','checked_out_head','b'*40),('workflow-ref-context','workflow_ref','wrong'),('boolean-run-context','run_id',True)):
            bad=dict(context);bad[key]=value;results[name]=reject(p.context_valid,bad)
        text=source[p.WORKFLOW]
        results['workflow-failfast']=reject(p.command_block,text.replace(b'bash --noprofile --norc -euo pipefail {0}',b'bash {0}'),'baseline')
        results['workflow-error-mask']=reject(p.command_block,text+b'\n# continue-on-error: true\n','baseline')
        results['workflow-postcommand']=reject(p.command_block,text.replace(b'ci_step_receipts.py --step baseline',b'ci_step_receipts.py --step materialization'),'baseline')
        results['duplicate-JSON-field']=reject(p.decode_receipt,b'{"schema":1,"schema":1}')
    if set(results)!=set(CASES) or not all(results.values()):raise AssertionError('receipt fixture case inventory differs')
    (args.output/'result.json').write_text(json.dumps(dict(passed=True,fixture_only=True,real_receipt_producer_called=False,
      genuine_completed_receipts_emitted=False,GitHub_API_called=False,git_called=False,compiler_executed=False,
      device_operations=False,cases={n:results[n] for n in CASES},source_sha256={n:p.sha(raw) for n,raw in source.items()},
      test_source_sha256=p.sha(Path(__file__).read_bytes())),indent=2)+'\n')
if __name__=='__main__':main()
