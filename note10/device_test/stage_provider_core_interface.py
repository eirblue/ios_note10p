"""Stage only the exact new interface evidence namespace, failure evidence separate."""
import argparse,shutil
from pathlib import Path
from provider_core_input_contract import ROOT,NAMESPACE,require,inventory,validate_namespace,write_json,disjoint


def main():
 p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--staging-parent',type=Path,required=True);p.add_argument('--receipt',type=Path,required=True);p.add_argument('--forensic-on-failure',action='store_true');a=p.parse_args();source=a.source.absolute();parent=a.staging_parent.absolute();receipt=a.receipt.absolute();require(source.name==NAMESPACE and source.is_relative_to(ROOT/'note10/private') and parent.is_relative_to(ROOT/'note10/private') and receipt.is_relative_to(ROOT/'note10/private') and not parent.exists() and not receipt.exists(),'fresh private staging and receipt');disjoint([source,parent,receipt]);failure=(source/'failure.json').exists();require(not failure or a.forensic_on_failure,'forensic preservation explicitly selected');actual=validate_namespace(source,forensic=failure);parent.mkdir(parents=True);target=parent/NAMESPACE;shutil.copytree(source,target,symlinks=False);require(inventory(target)==actual,'complete exact namespace staged');write_json(receipt,{'passed':not failure,'forensic_only':failure,'files':actual,'source_mutated':False,'automatic_retry':False})


if __name__=='__main__':main()
