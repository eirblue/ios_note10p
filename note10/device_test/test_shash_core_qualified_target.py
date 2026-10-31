"""New synthetic single-const extraction/consumer cases; no old fixtures."""
import argparse,copy,hashlib,json
from pathlib import Path
from pre_pm_archive_contract import require
from shash_core_dwarf import qualified_member_type,bind_qualified_targets
from shash_core_preparation_cfg import preparation_type_target
from shash_core_qualified_target import canonical,layout_digest

PRODUCER_NEGATIVES=('pointer-ref-missing','pointer-ref-broken','pointer-ref-wrong-form','pointer-ref-wrong-value-type','pointer-ref-negative','wrapper-ref-missing','wrapper-ref-broken','pointer-cycle','wrapper-cycle','repeated-const','terminal-typedef','terminal-volatile','terminal-restrict','terminal-union','terminal-pointer','terminal-wrong-name','terminal-missing-name','terminal-missing-size','terminal-zero-size','terminal-negative-size','terminal-bool-size','terminal-float-size','terminal-declaration','pointer-width4','pointer-width0','pointer-CU-version','pointer-CU-address','wrapper-foreign-CU','terminal-foreign-CU','raw-target-name-mismatch','raw-pointer-name-mismatch','raw-alignment-mismatch','raw-width-mismatch','terminal-record-missing','terminal-record-duplicate','terminal-record-wrong-key','terminal-record-wrong-size','terminal-record-wrong-name','terminal-record-same-size-wrong-members','layout-same-size-wrong-members')
CONSUMER_NEGATIVES=('evidence-missing','evidence-extra-field','evidence-schema-mismatch','evidence-raw-pointer-mismatch','evidence-wrong-binding','evidence-qualifier-missing','evidence-qualifier-repeat','evidence-qualifier-typedef','evidence-qualifier-volatile','evidence-qualifier-restrict','evidence-qualifier-extra','evidence-terminal-extra','evidence-terminal-tag','evidence-terminal-name','evidence-terminal-size','evidence-terminal-bool-size','evidence-terminal-declaration','evidence-terminal-digest','consumer-layout-name','consumer-layout-size','consumer-layout-members','consumer-raw-width','consumer-raw-target-name','consumer-raw-extra-field')
EVIDENCE_KEYS=('schema','raw_pointer','qualifiers','terminal','binding')
TERMINAL_KEYS=('tag','name','byte_size','declaration','layout_sha256')
EXTRA_REFERENCE_CASES=('pointer-resolved-reference-mismatch','wrapper-resolved-reference-mismatch','longer-qualifier-chain-reject','consumer-raw-target-tag-mismatch','consumer-raw-kind-mismatch')
CASES=('single-const-extractor-to-consumer','raw-direct-target-fields-retained','complete-layout-digest-not-name-size','equivalent-layout-offsets-not-canonical','unrelated-owner-isolated','unrelated-member-isolated','direct-target-extractor-isolated')+PRODUCER_NEGATIVES+CONSUMER_NEGATIVES+tuple('missing-evidence-'+n for n in EVIDENCE_KEYS)+tuple('missing-terminal-'+n for n in TERMINAL_KEYS)+EXTRA_REFERENCE_CASES


class Attr:
 def __init__(self,value,form='DW_FORM_data4'):self.value=value;self.form=form


class CU:
 def __init__(self):self.cu_offset=0;self.header={'version':4,'address_size':8}
 def __getitem__(self,key):return self.header[key]


class DIE:
 def __init__(self,cu,offset,tag,**attrs):self.cu=cu;self.offset=offset;self.tag=tag;self.attributes={n:Attr(v) for n,v in attrs.items()};self.target=None;self.broken=False
 def get_DIE_from_attribute(self,key):
  if self.broken:raise ValueError('synthetic broken reference')
  return self.target


def fixture():
 cu=CU();pointer=DIE(cu,1,'DW_TAG_pointer_type');wrapper=DIE(cu,2,'DW_TAG_const_type');terminal=DIE(cu,3,'DW_TAG_structure_type',DW_AT_name=b'crypto_type',DW_AT_byte_size=32)
 for source,target in ((pointer,wrapper),(wrapper,terminal)):source.target=target;source.attributes['DW_AT_type']=Attr(target.offset,'DW_FORM_ref4')
 raw={'kind':'pointer','name':'','byte_size':8,'alignment':None,'target_tag':'DW_TAG_const_type','target_name':''}
 record={'name':'crypto_type','byte_size':32,'alignment':8,'members':[{'name':'synthetic_code','offset':0,'type':{'kind':'base','name':'unsigned','byte_size':4,'alignment':4},'member_alignment':None},{'name':'synthetic_pointer','offset':8,'type':{'kind':'pointer','name':'','byte_size':8,'alignment':8,'target_tag':'void','target_name':''},'member_alignment':None}],'die_offset':3,'CU_offset':0}
 return {'pointer':pointer,'wrapper':wrapper,'terminal':terminal,'raw':raw,'records':[record],'layouts':{'crypto_type':copy.deepcopy(canonical(record))}}


def extract(args,owner='crypto_alg',name='cra_type'):
 pending=[];descriptor=qualified_member_type(owner,name,args['pointer'],args['raw'],pending);bind_qualified_targets(pending,args['records'],args['layouts']);return descriptor


def integrate(args):
 descriptor=extract(args);preparation_type_target(descriptor,{'types':args['layouts']});return descriptor


def run_cases(completed=None):
 if completed is None:completed=[]
 def equal(a,b):require(a==b,'independent new qualified-target expectation')
 def check(name,action,reject=False):
  require(name==CASES[len(completed)],'frozen new-only qualified case order')
  try:action()
  except (ValueError,KeyError,TypeError,AttributeError):
   if not reject:raise
  else:require(not reject,'invalid qualified target accepted: '+name)
  completed.append(name)
 check(CASES[0],lambda:integrate(fixture()))
 def raw_retained():
  args=fixture();before=dict(args['raw']);typ=integrate(args);equal({k:v for k,v in typ.items() if k!='qualified_pointee'},before);equal(typ['target_tag'],'DW_TAG_const_type');equal(typ['target_name'],'')
 check(CASES[1],raw_retained)
 def full_digest():
  args=fixture();typ=integrate(args);other=copy.deepcopy(args['layouts']['crypto_type']);other['members'][0]['name']='different';require(typ['qualified_pointee']['terminal']['layout_sha256']!=layout_digest(other),'full extracted record identity, never size-only binding')
 check(CASES[2],full_digest)
 def equivalent_offsets():
  first=fixture();second=fixture();second['terminal'].offset=700;second['wrapper'].attributes['DW_AT_type'].value=700;second['records'][0]['die_offset']=700
  equal(integrate(first)['qualified_pointee'],integrate(second)['qualified_pointee'])
 check(CASES[3],equivalent_offsets)
 for case,owner,name in ((CASES[4],'unrelated_type','cra_type'),(CASES[5],'crypto_alg','another_member')):
  def isolated(o=owner,n=name):
   args=fixture();before=copy.deepcopy(args['raw']);args['pointer'].broken=True;equal(extract(args,o,n),before)
  check(case,isolated)
 def direct_isolated():
  args=fixture();args['raw'].update(target_tag='DW_TAG_structure_type',target_name='crypto_type');before=copy.deepcopy(args['raw']);args['pointer'].broken=True;equal(extract(args),before)
 check(CASES[6],direct_isolated)
 for name in PRODUCER_NEGATIVES:
  args=fixture();p=args['pointer'];w=args['wrapper'];t=args['terminal'];raw=args['raw'];record=args['records'][0]
  if name=='pointer-ref-missing':p.attributes.pop('DW_AT_type')
  elif name=='pointer-ref-broken':p.broken=True
  elif name=='pointer-ref-wrong-form':p.attributes['DW_AT_type'].form='DW_FORM_data4'
  elif name=='pointer-ref-wrong-value-type':p.attributes['DW_AT_type'].value='bad'
  elif name=='pointer-ref-negative':p.attributes['DW_AT_type'].value=-1
  elif name=='wrapper-ref-missing':w.attributes.pop('DW_AT_type')
  elif name=='wrapper-ref-broken':w.broken=True
  elif name=='pointer-cycle':p.target=p;p.attributes['DW_AT_type'].value=p.offset
  elif name=='wrapper-cycle':w.target=w;w.attributes['DW_AT_type'].value=w.offset
  elif name=='repeated-const':t.tag='DW_TAG_const_type'
  elif name.startswith('terminal-') and name in ('terminal-typedef','terminal-volatile','terminal-restrict','terminal-union','terminal-pointer'):t.tag={'terminal-typedef':'DW_TAG_typedef','terminal-volatile':'DW_TAG_volatile_type','terminal-restrict':'DW_TAG_restrict_type','terminal-union':'DW_TAG_union_type','terminal-pointer':'DW_TAG_pointer_type'}[name]
  elif name=='terminal-wrong-name':t.attributes['DW_AT_name'].value=b'other'
  elif name=='terminal-missing-name':t.attributes.pop('DW_AT_name')
  elif name=='terminal-missing-size':t.attributes.pop('DW_AT_byte_size')
  elif name=='terminal-zero-size':t.attributes['DW_AT_byte_size'].value=0
  elif name=='terminal-negative-size':t.attributes['DW_AT_byte_size'].value=-1
  elif name=='terminal-bool-size':t.attributes['DW_AT_byte_size'].value=True
  elif name=='terminal-float-size':t.attributes['DW_AT_byte_size'].value=32.0
  elif name=='terminal-declaration':t.attributes['DW_AT_declaration']=Attr(True,'DW_FORM_flag')
  elif name=='pointer-width4':p.attributes['DW_AT_byte_size']=Attr(4)
  elif name=='pointer-width0':p.attributes['DW_AT_byte_size']=Attr(0)
  elif name=='pointer-CU-version':p.cu.header['version']=5
  elif name=='pointer-CU-address':p.cu.header['address_size']=4
  elif name=='wrapper-foreign-CU':w.cu=CU()
  elif name=='terminal-foreign-CU':t.cu=CU()
  elif name=='raw-target-name-mismatch':raw['target_name']='not_empty'
  elif name=='raw-pointer-name-mismatch':raw['name']='other'
  elif name=='raw-alignment-mismatch':raw['alignment']=8
  elif name=='raw-width-mismatch':raw['byte_size']=4
  elif name=='terminal-record-missing':args['records']=[]
  elif name=='terminal-record-duplicate':args['records'].append(copy.deepcopy(record))
  elif name=='terminal-record-wrong-key':record['die_offset']=100
  elif name=='terminal-record-wrong-size':record['byte_size']=40
  elif name=='terminal-record-wrong-name':record['name']='other'
  elif name=='terminal-record-same-size-wrong-members':record['members'][0]['name']='different'
  elif name=='layout-same-size-wrong-members':args['layouts']['crypto_type']['members'][0]['name']='different'
  check(name,lambda a=args:integrate(a),True)
 for name in CONSUMER_NEGATIVES+tuple('missing-evidence-'+n for n in EVIDENCE_KEYS)+tuple('missing-terminal-'+n for n in TERMINAL_KEYS):
  args=fixture();typ=extract(args);e=typ['qualified_pointee'];terminal=e['terminal'];layout=args['layouts']['crypto_type']
  if name=='evidence-missing':typ.pop('qualified_pointee')
  elif name=='evidence-extra-field':e['extra']=1
  elif name=='evidence-schema-mismatch':e['schema']='other'
  elif name=='evidence-raw-pointer-mismatch':e['raw_pointer']['name']='other'
  elif name=='evidence-wrong-binding':e['binding']='name-and-size-only'
  elif name=='evidence-qualifier-missing':e['qualifiers']=[]
  elif name=='evidence-qualifier-repeat':e['qualifiers']*=2
  elif name in ('evidence-qualifier-typedef','evidence-qualifier-volatile','evidence-qualifier-restrict'):e['qualifiers'][0]['tag']={'evidence-qualifier-typedef':'DW_TAG_typedef','evidence-qualifier-volatile':'DW_TAG_volatile_type','evidence-qualifier-restrict':'DW_TAG_restrict_type'}[name]
  elif name=='evidence-qualifier-extra':e['qualifiers'][0]['extra']=1
  elif name=='evidence-terminal-extra':terminal['extra']=1
  elif name=='evidence-terminal-tag':terminal['tag']='DW_TAG_union_type'
  elif name=='evidence-terminal-name':terminal['name']='other'
  elif name=='evidence-terminal-size':terminal['byte_size']=40
  elif name=='evidence-terminal-bool-size':terminal['byte_size']=True
  elif name=='evidence-terminal-declaration':terminal['declaration']=True
  elif name=='evidence-terminal-digest':terminal['layout_sha256']='0'*64
  elif name=='consumer-layout-name':layout['name']='other'
  elif name=='consumer-layout-size':layout['byte_size']=40
  elif name=='consumer-layout-members':layout['members'][0]['name']='different'
  elif name=='consumer-raw-width':typ['byte_size']=4
  elif name=='consumer-raw-target-name':typ['target_name']='other'
  elif name=='consumer-raw-extra-field':typ['extra']=1
  elif name.startswith('missing-evidence-'):e.pop(name.removeprefix('missing-evidence-'))
  elif name.startswith('missing-terminal-'):terminal.pop(name.removeprefix('missing-terminal-'))
  check(name,lambda t=typ,a=args:preparation_type_target(t,{'types':a['layouts']}),True)
 for name in EXTRA_REFERENCE_CASES:
  args=fixture()
  if name=='pointer-resolved-reference-mismatch':args['pointer'].attributes['DW_AT_type'].value=99
  elif name=='wrapper-resolved-reference-mismatch':args['wrapper'].attributes['DW_AT_type'].value=99
  elif name=='longer-qualifier-chain-reject':
   args['terminal'].tag='DW_TAG_const_type';extra=DIE(args['terminal'].cu,4,'DW_TAG_structure_type',DW_AT_name=b'crypto_type',DW_AT_byte_size=32);args['terminal'].target=extra;args['terminal'].attributes['DW_AT_type']=Attr(4,'DW_FORM_ref4')
  else:
   typ=extract(args)
   if name=='consumer-raw-target-tag-mismatch':typ['target_tag']='DW_TAG_volatile_type'
   else:typ['kind']='base'
   check(name,lambda t=typ,a=args:preparation_type_target(t,{'types':a['layouts']}),True);continue
  check(name,lambda a=args:integrate(a),True)
 return {'passed':True,'cases':completed,'case_count':len(completed),'synthetic_only':True,'prior_fixture_import_or_replay':False,'actual_retained_object_checker_extractor_compiler_or_target_execution':False}


def main():
 p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--checkpoint',type=Path,required=True);p.add_argument('--checkpoint-sha256',required=True);p.add_argument('--inventory',type=Path,required=True);p.add_argument('--inventory-sha256',required=True);a=p.parse_args();out=a.output.absolute();require(out.is_relative_to(Path(__file__).resolve().parents[2]/'note10/private') and not out.exists(),'fresh private qualified fixture receipt')
 completed=[];phase='attribution';attribution={'checkpoint_path':str(a.checkpoint.absolute()),'inventory_path':str(a.inventory.absolute()),'expected_checkpoint_sha256':a.checkpoint_sha256,'expected_inventory_sha256':a.inventory_sha256}
 try:
  checkpoint_raw=a.checkpoint.read_bytes();inventory_raw=a.inventory.read_bytes();attribution.update(checkpoint_sha256=hashlib.sha256(checkpoint_raw).hexdigest(),inventory_sha256=hashlib.sha256(inventory_raw).hexdigest());require(attribution['checkpoint_sha256']==a.checkpoint_sha256 and attribution['inventory_sha256']==a.inventory_sha256,'exact independently pinned fixture attribution')
  cp=json.loads(checkpoint_raw);inventory=json.loads(inventory_raw);key='note10/device_test/'+Path(__file__).name;digest=hashlib.sha256(Path(__file__).read_bytes()).hexdigest();require(inventory['cases']==list(CASES) and inventory['case_count']==len(CASES) and inventory['fixture_sha256']==digest and cp['public_sources_sha256'][key]==digest and cp['new_revision8_fixture_inventory']==list(CASES),'exact frozen new-only qualified inventory')
  phase='synthetic_cases';result=run_cases(completed);result.update(attribution)
 except BaseException as error:
  result=dict(attribution,passed=False,cases=list(completed),case_count=len(completed),completed_case_names=list(completed),completed_case_count=len(completed),failing_next_case=CASES[len(completed)] if len(completed)<len(CASES) else None,failure_phase=phase,exception_type=type(error).__name__,exception_message=str(error),automatic_retry_performed=False,synthetic_only=True);out.parent.mkdir(parents=True,exist_ok=True)
  with out.open('x',encoding='utf8',newline='\n') as stream:stream.write(json.dumps(result,indent=2)+'\n')
  raise
 out.parent.mkdir(parents=True,exist_ok=True)
 with out.open('x',encoding='utf8',newline='\n') as stream:stream.write(json.dumps(result,indent=2)+'\n')
if __name__=='__main__':main()
