"""Stage a complete fresh pair artifact, retaining bounded failure evidence."""
import argparse
from pathlib import Path
import provider_core_pair_input_contract as contract


def stage(source, parent, receipt):
    source=Path(source); parent=Path(parent); parent.mkdir()
    rows=contract.inventory(source); result=contract.parse_json(contract.snapshot(source/'result.json',8*1024*1024)['raw'])
    contract.require(set(rows)==set(result['files'])|{'result.json'} and all(rows[k]==v for k,v in result['files'].items()), 'complete producer inventory, no leftovers')
    dest=parent/'v67-ci-pair'; dest.mkdir()
    for name,row in rows.items():
        snap=contract.snapshot(source/name,contract.CAP,row); target=dest/name; target.parent.mkdir(parents=True,exist_ok=True); contract.write_bytes(target,snap['raw']); contract.unchanged(snap)
    contract.require(contract.inventory(dest)==rows, 'same complete staged namespace')
    contract.write_json(receipt,{'schema':'pair-stage-v1','producer_passed':result['passed'],'files':rows})


def main():
    p=argparse.ArgumentParser(); p.add_argument('--source',required=True); p.add_argument('--staging-parent',required=True); p.add_argument('--receipt',required=True); a=p.parse_args(); stage(a.source,a.staging_parent,a.receipt)


if __name__=='__main__': main()
