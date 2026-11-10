"""New actual-shape oversized receipt regression and compact provenance tampering."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

import compact_native_receipts as compact
import native_handoff_artifact as artifact
from phase1_iostorage_kernel_link import storage_units

HEAD = '1'*40
KERNEL = b'new synthetic compact staging input'


def fixture():
    inventory = []
    for index in range(1067):
        name = 'bsd/dev/memdev.c' if index == 0 else ('synthetic/assembly.s' if index == 1 else f'synthetic/unit{index}.c')
        inventory.append(dict(source=name, component='bsd' if index == 0 else 'osfmk',
                              kind='assembly' if index == 1 else 'C',
                              source_sha256=artifact.POSTIMAGE_SHA256 if index == 0 else artifact.sha(name.encode())))
    current = dict(kind='v84-current-native', producer=dict(source_commit=HEAD, objects_root='/synthetic/current-objects',
        ci_context=dict(GITHUB_SHA=HEAD,GITHUB_RUN_ID='1',GITHUB_RUN_ATTEMPT='1')), bindings={'synthetic':True},
        inventory=inventory, assembly_input='a'*64,
        dependencies={name:{'source_sha256':artifact.sha(name.encode())} for name in compact.EXTRAS})
    current.update(producer_id=artifact.digest(current['producer']),input_binding=artifact.digest(current['bindings']))
    rows = []
    for index, name in enumerate([row['source'] for row in inventory] + list(compact.EXTRAS)):
        row = dict(source=name, component='osfmk', category=compact.EXTRAS.get(name,'native'), passed=True,
                   source_sha256=inventory[index]['source_sha256'] if index < 1067 else current['dependencies'][name]['source_sha256'],
                   object_path=f'/synthetic/current-objects/unit{index}.o', object_sha256=artifact.sha(str(index).encode()),
                   producer_id=current['producer_id'], input_binding=current['input_binding'], diagnostics='',
                   command=['clang','-D'+'X'*8192,'-I/synthetic/private/exports','-c',name,'-o',f'/synthetic/current-objects/unit{index}.o'])
        if index == 1:
            row['assembly_input'] = current['assembly_input']
        rows.append(row)
    proof = dict(producer_id=current['producer_id'],input_binding=current['input_binding'])
    binding = dict(proof=proof,binding=artifact.digest(proof))
    source_pins = {source.name: source_sha for source, _, source_sha in storage_units(Path('/source-proof'))}
    units = [dict(source='@storage/'+name,category='storage',passed=True,source_sha256=source_pins[name],
                  object_path='/synthetic/storage/'+Path(name).stem+'.o',object_sha256=artifact.sha((name+'object').encode()),
                  producer_id=current['producer_id'],input_binding=current['input_binding'],storage_binding=binding['binding'])
             for name in compact.STORAGE]
    storage = dict(binding=binding,units=units)
    filelist = ''.join(row['object_path']+'\n' for row in rows+units).encode()
    link = dict(producer_id=current['producer_id'],input_binding=current['input_binding'],link_succeeded=True,
                returncode=0,object_count=1077,filelist_sha256=artifact.sha(filelist))
    memdev = dict(kernel_link_verified=True,provider_binding_verified=True,
        extra_patch=dict(postimage_sha256=artifact.POSTIMAGE_SHA256,patch_sha256=artifact.PATCH_SHA256),
        memdev_member=dict(source_sha256=artifact.POSTIMAGE_SHA256),native_manifest_sha256=artifact.digest(inventory))
    producer = dict(schema='note10-v174-native-kernel-artifact-result-v1',source_head=HEAD,run_id=1,run_attempt=1,
        passed=True,final_object_count=1077,kernel_sha256=artifact.sha(KERNEL),kernel_bytes=len(KERNEL),
        memdev_integration=memdev,storage_binding_sha256=binding['binding'],
        storage_object_sha256={row['source']:row['object_sha256'] for row in units})
    state = dict(passed=True,phase='complete',producer_id=current['producer_id'],input_binding=current['input_binding'],
                 output_sha256=artifact.sha(KERNEL),output_bytes=len(KERNEL),memdev=memdev)
    return rows,current,storage,link,filelist,producer,state


def write_inputs(name, values):
    rows,current,storage,link,filelist,producer,state = values
    parent = OUTPUT/name
    build = parent/'build'
    build.mkdir(parents=True)
    records = {'producer-context.json':current,'current-object-receipts.json':rows,
               'storage-receipts.json':storage,'link-result.json':link,'result.json':state}
    for filename,value in records.items():
        (build/filename).write_bytes(artifact.encoded(value))
    (build/'native-objects.filelist').write_bytes(filelist)
    (build/'current-native.macho').write_bytes(KERNEL)
    summary = parent/'summary.json'
    summary.write_bytes(artifact.encoded(producer))
    return build,summary,parent/'stage'


class CompactReceiptTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.values = fixture()

    def test_1_actual_shape_large_input_compacts_through_stage(self):
        data = write_inputs('large',self.values)
        raw = (data[0]/'current-object-receipts.json').read_bytes()
        self.assertGreater(len(raw),artifact.META_MAX)
        self.assertLessEqual(len(raw),compact.RAW_MAX)
        record = artifact.stage(*data,head=HEAD,run_id=1,attempt=1,compact=True)
        self.assertTrue(record['kernel_retained'])
        encoded = (data[2]/'ownership/current-object-receipts.json').read_bytes()
        self.assertLessEqual(len(encoded),artifact.META_MAX)
        value = json.loads(encoded)
        self.assertEqual((value['raw_bytes'],value['raw_sha256']),(len(raw),hashlib.sha256(raw).hexdigest()))
        self.assertEqual(len(value['units']),1071)
        for before,after in zip(self.values[0],value['units']):
            expected = {key:before[key] for key in compact.CORE}
            if 'assembly_input' in before:
                expected['assembly_input'] = before['assembly_input']
            self.assertEqual(after,expected)
        self.assertNotIn(b'"command"',encoded)
        self.assertNotIn(b'"diagnostics"',encoded)
        manifest = json.loads((data[2]/'kernel/build-manifest.json').read_bytes())
        retained = next(row for row in manifest['ownership'] if row['file']=='ownership/current-object-receipts.json')
        self.assertEqual((retained['bytes'],retained['sha256']),(len(encoded),hashlib.sha256(encoded).hexdigest()))

    def test_2_core_and_coherent_filelist_tampering(self):
        for change,code in [('source','compact_source_binding'),('duplicate','compact_duplicate_receipt'),
                            ('assembly','compact_assembly_binding'),('owner','compact_object_owner'),
                            ('storage','compact_storage_binding'),('storage-source','compact_storage_binding'),
                            ('filelist','compact_filelist_binding')]:
            rows,current,storage,link,filelist,producer,_ = copy.deepcopy(self.values)
            if change=='source':rows[0]['source_sha256']='0'*64
            elif change=='duplicate':rows[2]['source']=rows[0]['source']
            elif change=='assembly':rows[1]['assembly_input']='0'*64
            elif change=='owner':rows[0]['object_path']='/different-owner/unit0.o'
            elif change=='storage':storage['units'][0]['input_binding']='0'*64
            elif change=='storage-source':storage['units'][0]['source_sha256']='0'*64
            else:
                paths=filelist.decode().splitlines();paths[0],paths[1]=paths[1],paths[0]
                filelist=('\n'.join(paths)+'\n').encode();link['filelist_sha256']=artifact.sha(filelist)
            with self.subTest(change=change),self.assertRaisesRegex(ValueError,code):
                compact.project(artifact.encoded(rows),current,storage,link,filelist,producer)
        values=copy.deepcopy(self.values)
        values[0][0]['source_sha256']='0'*64
        data=write_inputs('tampered',values)
        record=artifact.stage(*data,head=HEAD,run_id=1,attempt=1,compact=True)
        self.assertEqual(record['packaging_failure_code'],'compact_source_binding')
        self.assertFalse(record['kernel_retained'])
        self.assertFalse((data[2]/'kernel').exists())

    def test_3_member_size_observation_precedes_rejection(self):
        self.assertEqual((compact.RAW_MAX,compact.COMPACT_MAX,artifact.META_MAX,artifact.TOTAL_MAX),
                         (32*1024*1024,8*1024*1024,8*1024*1024,64*1024*1024))
        data = write_inputs('bounded',self.values)
        observed=(data[0]/'current-object-receipts.json').stat().st_size
        with patch.object(compact,'RAW_MAX',observed-1):
            record=artifact.stage(*data,head=HEAD,run_id=1,attempt=1,compact=True)
        self.assertFalse(record['kernel_retained'])
        self.assertEqual(record['packaging_failure_code'],'input_size_limit')
        self.assertEqual(record['failure_input'],dict(member='ownership/current-object-receipts.json',
                                                    observed_bytes=observed,limit_bytes=observed-1))
        self.assertFalse((data[2]/'kernel').exists())


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();OUTPUT=args.output.resolve()
    if not OUTPUT.is_relative_to(artifact.PRIVATE.resolve()) or OUTPUT.exists():
        raise ValueError('Fresh private fixture output required')
    OUTPUT.mkdir(parents=True,exist_ok=False)
    unittest.main(argv=[sys.argv[0]])
