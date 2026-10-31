"""Stage only the exact new bounded composite evidence namespace."""
import argparse,json,shutil
from pathlib import Path
from crypto_hash_composite import require
from crypto_hash_input_contract import NEW_ROOT,tree_inventory,write


def stage(source,parent,receipt,forensic_on_failure=False):
 source=Path(source).resolve();parent=Path(parent).resolve();receipt=Path(receipt).resolve();require(source.name==NEW_ROOT and source.is_dir() and not parent.exists() and not receipt.exists() and not source.is_relative_to(parent) and not parent.is_relative_to(source) and not receipt.is_relative_to(parent),'fresh disjoint staging and external receipt');before=tree_inventory(source);result=json.loads((source/'result.json').read_text()) if (source/'result.json').exists() else None;success=result is not None and result.get('passed') is True
 if success:require(result['version']=='v65' and result['executed_fixture_commands']==0 and set(before)==set(result['files'])|{'result.json'} and all(before[k]==v for k,v in result['files'].items()),'exact complete successful new namespace before staging')
 else:require(forensic_on_failure,'failure evidence requires explicit forensic staging; no acceptance')
 require(not any(name.endswith(('.zip','.tar.gz')) for name in before),'external raw protected inputs excluded');parent.mkdir(parents=True);shutil.copytree(source,parent/NEW_ROOT);after=tree_inventory(parent);expected={NEW_ROOT+'/'+name:value for name,value in before.items()};require(after==expected,'one exact complete staged root');write(receipt,{'namespace':NEW_ROOT,'files':after,'complete':True,'protected_inputs_uploaded':False,'forensic_only':not success,'actual_success_accepted':False});return after


def main():
 p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--staging-parent',type=Path,required=True);p.add_argument('--receipt',type=Path,required=True);p.add_argument('--forensic-on-failure',action='store_true');a=p.parse_args();stage(a.source,a.staging_parent,a.receipt,a.forensic_on_failure)
if __name__=='__main__':main()
