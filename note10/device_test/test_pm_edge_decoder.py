"""Validate actual producer frames independently, including corruption and conflicts."""
import argparse, hashlib, json, re
from pathlib import Path
from decode_pm_edge import decode
from decode_reservation import checksum
from run_probe import ROOT
HERE=Path(__file__).resolve().parent
ID='0123456789abcdef0123456789abcdef'

def rewrite(line,old,new):
    tag,rest=line.split(' ',1);body,digest=rest.rsplit(' checksum=',1)
    if old not in body:raise ValueError('mutation anchor missing')
    body=body.replace(old,new,1)
    return tag+' '+body+' checksum='+format(checksum(body.encode()),'08x')

def run(output,producer_dir):
    output=Path(output).resolve();producer_dir=Path(producer_dir)
    if not output.is_relative_to((ROOT/'note10/private').resolve()) or output.exists():raise ValueError('fresh private model directory required')
    output.mkdir(parents=True)
    base=(producer_dir/'producer-0.log').read_text();runtime=(producer_dir/'producer-8.log').read_text()
    old_dma={'phases':{p:{'snapshot':{'total':1,'dma':1,'names_xor':7,'names_sum':7}} for p in (0,2)}}
    old_iommu={'phases':{p:{'snapshot':{'total':1,'names_xor':9,'names_sum':9,'syscore':0}} for p in (0,2)},'controller_details':{p:{'controllers':[]} for p in (0,2)}}
    lines=base.splitlines();find=lambda tag:next(i for i,line in enumerate(lines) if line.startswith(tag+' '))
    def mutate(tag,old,new):
        out=lines.copy();i=find(tag);out[i]=rewrite(out[i],old,new);return '\n'.join(out)+'\n'
    def remove(tag):
        out=lines.copy();out.pop(find(tag));return '\n'.join(out)+'\n'
    def bad_checksum(tag):
        out=lines.copy();i=find(tag);out[i]=out[i][:-8]+'00000000';return '\n'.join(out)+'\n'
    cases=[('baseline',base,True),('runtime_change',runtime,True),
       ('missing_dma',remove('N10EDG1'),False),('bad_checksum',bad_checksum('N10EIM1'),False),
       ('missing_identity',remove('N10EID1'),False),('missing_callback',remove('N10ESC1'),False),
       ('missing_status',remove('N10EOK1'),False),('duplicate',base+lines[find('N10ESC1')]+'\n',False),
       ('dma_conflict',mutate('N10EDG1','uncovered=1','uncovered=0'),False),
       ('iommu_conflict',mutate('N10EIM1','total=1','total=2'),False),
       ('callback_conflict',mutate('N10ESC1','sname=b','sname=c'),False),
       ('callback_mask',mutate('N10ESC1','mask=7','mask=0'),False),
       ('bad_phase',mutate('N10EDG1','phase=0','phase=3'),False),
       ('wrong_generation',mutate('N10EIM1','generation=1','generation=2'),False),
       ('bad_sentinel',mutate('N10EID1','name=-','name=00'),False),
       ('bad_status',mutate('N10EOK1','status=0','status=1'),False),
       ('failure_bitmask',base+'N10EER1 id='+ID+' failures=1\n',False)]
    for mode in range(1,8):cases.append(('producer_failure_'+str(mode),(producer_dir/('producer-'+str(mode)+'.log')).read_text(),False))
    outcomes=[]
    for name,text,expected in cases:
        try:decode(text,ID,2,old_dma,old_iommu);accepted=True
        except ValueError:accepted=False
        if accepted!=expected:raise ValueError('Unexpected PM edge decoder outcome: '+name)
        outcomes.append({'case':name,'accepted':accepted,'passed':True})
    result={'passed':True,'cases':len(outcomes),'outcomes':outcomes,'harness_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'decoder_sha256':hashlib.sha256((HERE/'decode_pm_edge.py').read_bytes()).hexdigest(),'actual_producer_frames_decoded':True,'producer_log_sha256':{f'producer-{i}.log':hashlib.sha256((producer_dir/f'producer-{i}.log').read_bytes()).hexdigest() for i in range(9)}}
    (output/'result.json').write_text(json.dumps(result,indent=2)+'\n');return result
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--producer-dir',type=Path,required=True);a=p.parse_args();r=run(a.output,a.producer_dir);print(json.dumps({'passed':r['passed'],'cases':r['cases']}))
