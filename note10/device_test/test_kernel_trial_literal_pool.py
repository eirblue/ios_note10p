"""New bounded whole-pool/link-option/identity fixtures; no previous suite replay."""
import argparse
import copy
from pathlib import Path
from kernel_trial_object import (POOL,pool_attributes,pool_input_contract,pool_projection_contract,component_closure,
    projection_link_command,validate_projection_link)
from test_kernel_trial_component import synthetic_object
from relocation_trial_aarch64_model import private_path,sha,write

CASE_INVENTORY=('pool-exact-input','pool-whole-bytes-map','pool-renamed-rejected','pool-writable-rejected',
 'pool-executable-rejected','pool-size-change-rejected','pool-type-rejected','pool-alignment-rejected','pool-entrysize-rejected',
 'pool-byte-change-rejected','pool-offset-map-rejected','pool-reference-offset-rejected','pool-reference-out-of-range-rejected','pool-extra-reference-rejected',
 'pool-outgoing-relocation-rejected','extra-rodata-section-rejected','link-O0-exact','link-duplicate-O0-rejected',
 'link-conflicting-O1-rejected','link-relocatable-rejected','link-derived-object-rejected','link-other-LLD-rejected')

def pool_object():
    obj=synthetic_object();raw=bytearray(b'a'*1217)
    for offset in range(20,621,20):raw[offset]=0
    raw[736:741]=b'name\0';raw[-1]=0
    index=len(obj['sections']);obj['sections'].append({'index':index,'name':POOL,'type':1,'flags':0x32,'alignment':1,'stride':1,'address':0,'bytes':bytes(raw)})
    obj['sections'][6]['bytes']=b'\0'*0x240
    symbol={'name':'','section':index,'value':0,'info':3,'size':0}
    for offset,kind in ((0x234,275),(0x238,277)):obj['relocations'].append({'section':6,'offset':offset,'type':kind,'addend':736,'symbol':dict(symbol)})
    return obj

def run_cases():
    rows=[]
    def check(name,call,reject=False):
        try:call()
        except ValueError:
            if not reject:raise
        else:
            if reject:raise AssertionError('invalid literal/link fixture admitted: '+name)
        rows.append({'name':name,'passed':True})
    obj=pool_object();pool=obj['sections'][-1];selected={POOL,'.text.adt_node'}
    check('pool-exact-input',lambda:pool_input_contract(obj,selected))
    mapped=copy.deepcopy(pool);mapped['address']=0x10001000
    check('pool-whole-bytes-map',lambda:pool_projection_contract(pool,mapped,mapped))
    for name,field,value in (('pool-renamed-rejected','name','.rodata.str1.2'),('pool-writable-rejected','flags',0x33),
      ('pool-executable-rejected','flags',0x36),('pool-size-change-rejected','bytes',pool['bytes']+b'\0'),
      ('pool-type-rejected','type',8),('pool-alignment-rejected','alignment',2),('pool-entrysize-rejected','stride',2)):
        changed=copy.deepcopy(pool);changed[field]=value
        check(name,lambda changed=changed:pool_attributes(changed),True)
    changed=copy.deepcopy(mapped);changed['bytes']=b'b'+changed['bytes'][1:]
    check('pool-byte-change-rejected',lambda:pool_projection_contract(pool,changed,mapped),True)
    shifted=copy.deepcopy(mapped);shifted['address']+=1
    check('pool-offset-map-rejected',lambda:pool_projection_contract(pool,mapped,shifted),True)
    wrong=pool_object();wrong['relocations'][-1]['addend']=737
    check('pool-reference-offset-rejected',lambda:pool_input_contract(wrong,selected),True)
    outside=pool_object();outside['relocations'][-1]['addend']=1217
    check('pool-reference-out-of-range-rejected',lambda:pool_input_contract(outside,selected),True)
    extra=pool_object();extra['relocations'].append(copy.deepcopy(extra['relocations'][-1]));extra['relocations'][-1]['offset']=0x23c
    check('pool-extra-reference-rejected',lambda:pool_input_contract(extra,selected),True)
    outgoing=pool_object();outgoing['relocations'].append({'section':len(outgoing['sections'])-1,'offset':0,'type':257,'addend':0,'symbol':outgoing['symbols'][0]})
    check('pool-outgoing-relocation-rejected',lambda:pool_input_contract(outgoing,selected),True)
    unknown=pool_object();index=len(unknown['sections']);unknown['sections'].append({'index':index,'name':'.rodata.unreviewed','flags':2,'bytes':b'x'})
    unknown['relocations'].append({'section':6,'offset':0x23c,'type':275,'addend':0,'symbol':{'section':index,'name':'','value':0,'info':3,'size':0}})
    check('extra-rodata-section-rejected',lambda:component_closure(unknown),True)
    root='/recorded/output';command=projection_link_command(root)
    check('link-O0-exact',lambda:validate_projection_link(command,root))
    check('link-duplicate-O0-rejected',lambda:validate_projection_link(command+['-O0'],root),True)
    check('link-conflicting-O1-rejected',lambda:validate_projection_link(command+['-O1'],root),True)
    check('link-relocatable-rejected',lambda:validate_projection_link(command+['-r'],root),True)
    derived=list(command);derived[-3]='/recorded/output/derived.o'
    check('link-derived-object-rejected',lambda:validate_projection_link(derived,root),True)
    other=list(command);other[0]='ld.lld-15'
    check('link-other-LLD-rejected',lambda:validate_projection_link(other,root),True)
    return rows

if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--output',type=Path,required=True);a=ap.parse_args();out=private_path(a.output);out.mkdir(parents=True,exist_ok=False)
    write(out/'result.json',{'schema':1,'fixture_only':True,'synthetic_only':True,'hardware_verified':False,'whole_ci_accepted':False,
      'old35_public_or10_private_replayed':False,'cases':run_cases(),'source_sha256':{name:sha(Path(__file__).parent/name) for name in ('kernel_trial_object.py','test_kernel_trial_literal_pool.py','build_kernel_trial_component.py')}})
