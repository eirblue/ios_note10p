"""One new actual data-only provider/core interface evidence producer; no fixtures."""
import argparse,os,shutil,time
from pathlib import Path
from provider_core_input_contract import ROOT,PUBLIC,CONTROL,CAP,NAMESPACE,require,digest,load_control,source_map,write_json,write_bytes,snapshot,unchanged,disjoint,retrieve,zip_inventory,old_labels,inventory,redact,current_int5
from provider_core_interface import declared_profile,join_snapshots


def main():
 parser=argparse.ArgumentParser();parser.add_argument('--control-sha256',required=True);parser.add_argument('--output',type=Path,required=True);parser.add_argument('--workspace',type=Path,required=True);args=parser.parse_args();out=args.output.absolute();workspace=args.workspace.absolute();require(out.name==NAMESPACE and out.is_relative_to(ROOT/'note10/private') and workspace.is_relative_to(ROOT/'note10/private') and not out.exists() and not workspace.exists(),'fresh private evidence/workspace');disjoint([out,workspace]);out.mkdir(parents=True);workspace.mkdir(parents=True);phase='fixed_control';inputs={};snapshots=[]
 try:
  control,control_record=load_control(args.control_sha256);snapshots.append(control_record);sources=source_map();write_json(out/'source-manifest.json',sources)
  for name in PUBLIC:record=snapshot(ROOT/name);require(record['sha256']==sources[name],'captured exact source closure');write_bytes(out/'source'/name,record['raw']);snapshots.append(record)
  require(shutil.disk_usage(workspace).free>=4*CAP,'bounded input/extraction/output disk budget');phase='two_authenticated_inputs';require(not (out/'inputs').exists(),'fresh role evidence parent');(out/'inputs').mkdir();deadline=time.monotonic()+120
  for role,label in control['roles'].items():
   record=retrieve(label,workspace/(role+'-retrieval'),out/'inputs'/role,deadline=deadline);snapshots.append(record);extraction=workspace/(role+'-extraction');binding=zip_inventory(record,label,extraction,original=True);prod=old_labels(extraction,label,binding);root=extraction/label['ZIP']['root'];obj=snapshot(extraction/label['selected_object']['member'],16*1024*1024,label['selected_object']);snapshots.append(obj);write_bytes(out/'evidence'/(role+'.o'),obj['raw']);inputs[role]={'ZIP':record,'object':obj,'root':root,'producer':prod}
  disjoint([inputs['provider']['ZIP']['path'],inputs['core']['ZIP']['path']],[inputs['provider']['ZIP']['int5'],inputs['core']['ZIP']['int5']]);phase='declared_source_input_profile';profile=declared_profile(control,inputs['provider']['root'],inputs['core']['root'],inputs['provider']['producer'],inputs['core']['producer']);phase='new_finite_metadata_edge';proof=join_snapshots(inputs['provider']['object'],inputs['core']['object'],control,inputs['provider']['producer'],profile);write_json(out/'join.json',proof)
  for record in snapshots:unchanged(record)
  result={'schema':'v66-interface-producer-v1','version':'v66','passed':True,'control_sha256':control_record['sha256'],'control_bytes':control_record['bytes'],'source_sha256':sources,'ci_context':{name:os.environ.get(name) for name in ('GITHUB_SHA','GITHUB_RUN_ID','GITHUB_RUN_ATTEMPT','GITHUB_JOB')},'protected_inputs':{role:{'profile':control['roles'][role]['profile'],'bytes':info['ZIP']['bytes'],'sha256':info['ZIP']['sha256'],'producer_local_int5_before':info['ZIP']['int5'],'producer_local_int5_after':current_int5(info['ZIP'])} for role,info in inputs.items()},'join_sha256':digest(snapshot(out/'join.json')['raw']),'new_observation_scope':'raw metadata edge and source/prototype/declared input facts only','executed_fixture_commands':0,'compiler_linker_model_or_oldchecker_commands':0,'nonclaims':control['nonclaims']};result['files']=inventory(out);write_json(out/'result.json',result)
 except BaseException as error:
  write_json(out/'failure.json',{'schema':'v66-interface-failure-v1','version':'v66','passed':False,'failure_phase':phase,'exception_type':type(error).__name__,'exception_message':redact(str(error).encode(),os.environ.get('GH_TOKEN','')).decode(errors='replace'),'automatic_retry':False,'executed_fixture_commands':0});raise


if __name__=='__main__':main()
