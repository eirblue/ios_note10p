"""Complete exclusive public evidence staging, including bounded failures."""
import argparse
from pathlib import Path
import paired_layout_input_contract as contract


def stage(source,parent,receipt):
    source=Path(source); parent=Path(parent); contract.parent_identities(parent); parent.mkdir()
    rows=contract.inventory(source); record=contract.parse_json(contract.snapshot(source/'result.json',8*1024*1024)['raw'])
    contract.require(set(rows)==set(record['files'])|{'result.json'} and all(rows[k]==v for k,v in record['files'].items()),'same complete producer evidence map')
    dest=parent/'v68-ci-layout'; dest.mkdir()
    for name,row in rows.items():
        snap=contract.snapshot(source/name,contract.CAP,row); target=dest/name; target.parent.mkdir(parents=True,exist_ok=True); contract.write_bytes(target,snap['raw']); contract.unchanged(snap)
    contract.require(contract.inventory(dest)==rows,'complete staged bytes/SHA, no subset')
    contract.write_json(receipt,{'schema':'layout-stage-v1','producer_passed':record['passed'],'files':rows})


def main():
    p=argparse.ArgumentParser(); p.add_argument('--source',required=True); p.add_argument('--staging-parent',required=True); p.add_argument('--receipt',required=True); a=p.parse_args(); stage(a.source,a.staging_parent,a.receipt)


if __name__=='__main__': main()
