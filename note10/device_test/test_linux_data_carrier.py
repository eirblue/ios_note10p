"""One selected new wrapper/profile batch; never invokes earlier test suites."""
import argparse
import json
import lzma
import os
from pathlib import Path
import struct
import subprocess
import unittest
from unittest.mock import patch

import linux_data_carrier as data


class LinuxDataCarrierTests(unittest.TestCase):
    output = None
    fixture = None
    compiles = 0
    needs_fixture = True

    @classmethod
    def setUpClass(cls):
        if not cls.needs_fixture:
            return
        cls.fixture = cls.output/'linux-data-carrier-fixture'
        command = ['clang-14', '-std=gnu11', '-O2', '-Wall', '-Wextra', '-Werror',
                   str(data.HERE/'linux_data_carrier_fixture.c'), '-lcrypto', '-o', str(cls.fixture)]
        cls.compiles += 1
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=120)
        (cls.output/'fixture-compile.log').write_bytes(result.stdout)
        (cls.output/'fixture-command.json').write_text(json.dumps(command, indent=2)+'\n')
        if result.returncode:
            raise RuntimeError('new wrapper fixture compilation failed')
        cls.fixture_raw = cls.fixture.read_bytes()
        if cls.fixture_raw.count(data.SLOT_PREIMAGE) != 1:
            raise RuntimeError('one generic compiled readonly fixture slot required')
        cls.fixture_slot_offset = cls.fixture_raw.index(data.SLOT_PREIMAGE)

    def setUp(self):
        self.root = self.output/self._testMethodName
        self.root.mkdir()
        self.invocations = 0

    @staticmethod
    def sample():
        return bytes(range(128))*7+b'new-linux-DATA'*80

    def container(self, stream=None, payload=None):
        payload = self.sample() if payload is None else payload
        if stream is None:
            original = lzma.compress(payload, format=lzma.FORMAT_ALONE, preset=6)
            stream = original[:5]+len(payload).to_bytes(8,'little')+original[13:]
        header = struct.pack('<8sHHI4Q32s32s16s', b'N10DATA1',1,128,0,4096,128,len(stream),len(payload),
                             bytes.fromhex(data.sha(stream)),bytes.fromhex(data.sha(payload)),bytes(16))
        return header+stream+bytes(4096-128-len(stream))

    def invoke(self, raw=None, mode='good', slot_expectation=None, invalid_slot=False, slot_logical=None):
        raw = self.container() if raw is None else raw
        self.invocations += 1
        path = self.root/('synthetic-carrier-%02d.data' % self.invocations)
        path.write_bytes(raw)
        program = bytearray(self.fixture_raw)
        offset = self.fixture_slot_offset
        if slot_expectation is not None:
            expected = bytes.fromhex(slot_expectation)
            self.assertEqual(len(expected),32)
            program[offset+24:offset+56] = expected
            if slot_logical is None:
                slot_logical = len(raw)
        if slot_logical is not None:
            program[offset+56:offset+64] = slot_logical.to_bytes(8,'little')
        if invalid_slot:
            program[offset] ^= 1
        executable = self.root/('readonly-fixture-%02d' % self.invocations)
        executable.write_bytes(program)
        executable.chmod(self.fixture.stat().st_mode & 0o777)
        result = subprocess.run([str(executable),str(path),mode],
                                stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=30)
        path.with_suffix('.stdout').write_bytes(result.stdout)
        path.with_suffix('.stderr').write_bytes(result.stderr)
        self.assertEqual(result.returncode,0,result.stderr.decode(errors='replace'))
        return json.loads(result.stdout)

    def test_native_capture_and_private_parameter_refuse_ambiguity(self):
        for mode in ('missing_parameter','duplicate_parameter','reversed','nonlinear','repeat_capture','changed'):
            row = self.invoke(mode=mode)
            self.assertEqual(row['status'],'unavailable',mode)
            self.assertEqual(row['calls'],0)
            self.assertEqual(row['allocations'],0)
        for parameter in ('a'*63,'A'*64,'g'*64,'a'*65):
            self.assertEqual(self.invoke(parameter=parameter)['status'],'unavailable')
        for mode in ('unarmed','arm_fail'):
            row = self.invoke(mode=mode)
            self.assertEqual(row['status'],'skipped')
            self.assertEqual(row['calls'],0)

    def test_actual_wrapper_owned_decode_and_cleanup(self):
        row = self.invoke()
        self.assertEqual(row['status'],'ok')
        self.assertEqual(row['calls'],1)
        self.assertEqual(row['callbacks'],1)
        self.assertEqual(row['written'],len(self.sample()))
        self.assertEqual(row['digest'],data.sha(self.sample()))
        self.assertEqual((row['allocations'],row['frees'],row['cleared']),(2,2,1))
        repeat = self.invoke(mode='repeat_callback')
        self.assertEqual(repeat['status'],'unavailable')
        self.assertEqual(repeat['calls'],1)
        self.assertEqual(repeat['frees'],2)

    def test_actual_wrapper_hash_header_and_slice_refusals(self):
        raw = self.container()
        self.assertEqual(self.invoke(raw,parameter='0'*64)['status'],'carrier_hash')
        changes = ((0,b'X'),(8,b'\x02'),(10,b'\x7f'),(12,b'\x01'),(24,b'\x81'),
                   (32,b'\xff'*8),(112,b'X'),(len(raw)-1,b'X'),(128,b'\0'))
        for offset,value in changes:
            broken = raw[:offset]+value+raw[offset+len(value):]
            row = self.invoke(broken)
            self.assertEqual(row['status'],'header',offset)
            self.assertEqual(row['allocations'],0)
        broken = raw[:48]+bytes([raw[48]^1])+raw[49:]
        self.assertEqual(self.invoke(broken)['status'],'stream_hash')

    def test_actual_wrapper_allocation_and_decoder_failure_cleanup(self):
        for mode in ('alloc1','alloc2'):
            row = self.invoke(mode=mode)
            self.assertEqual(row['status'],'allocation')
            self.assertEqual((row['calls'],row['frees'],row['cleared']),(0,1,1))
        for mode,status,calls in (('hash1','carrier_hash',0),('hash2','stream_hash',0),('hash3','payload_hash',1)):
            row = self.invoke(mode=mode)
            self.assertEqual((row['status'],row['calls']),(status,calls))
            self.assertEqual(row['cleared'],1)
            if calls:
                self.assertEqual(row['frees'],2)
        original = lzma.compress(self.sample(),format=lzma.FORMAT_ALONE,preset=6)
        short = original[:5]+len(self.sample()).to_bytes(8,'little')+original[13:18]
        row = self.invoke(self.container(stream=short))
        self.assertEqual((row['status'],row['calls'],row['frees'],row['cleared']),('decode',1,2,1))

    def test_data_profile_private_input_and_cmdline_binding(self):
        raw = self.container()
        manifest = dict(purpose='fixed-data-carrier-host-preparation',accepted=True,decoder_calls=1,
            carrier_admitted=False,deployment_ready=False,device_operations=[],xnu_executed=False,
            carrier_bytes=len(raw),carrier_sha256=data.sha(raw),payload_bytes=len(self.sample()),
            decoded_bytes=len(self.sample()),payload_sha256=data.sha(self.sample()),decoded_sha256=data.sha(self.sample()),decode={'status':0})
        fields = data.private_input_record(json.dumps(manifest).encode(),raw)
        build = dict(device_profile=data.PROFILE,**fields)
        cmdline = data.package_data(build,b'R'*len(raw),'synthetic=only',raw)
        self.assertEqual(cmdline,'synthetic=only n10.data_sha='+data.sha(raw))
        for base in (cmdline,'n10.data_sha=bad','n10.data_sha'):
            with self.assertRaises(ValueError):
                data.data_cmdline(base,data.sha(raw))
        with self.assertRaises(ValueError):
            data.data_cmdline('x'*1500,data.sha(raw))
        for changed in (dict(build,device_profile='native-memory-observation-v1'),dict(build,data_carrier_bytes=len(raw)-1)):
            with self.assertRaises(ValueError):
                data.package_data(changed,b'R'*len(raw),'synthetic=only',raw)
        with self.assertRaises(ValueError):
            data.private_input_record(json.dumps(dict(manifest,decoded_sha256='f'*64)).encode(),raw)

    def test_new_package_label_and_nonclaim_fields(self):
        from build_boot_test_packages import updater
        names = ('boot','recovery','dtb','dtbo','vbmeta')
        partitions = [dict(partition=name,block_node='/dev/block/sdz'+str(i+1),size=4096,sha256='a'*64)
                      for i,name in enumerate(names)]
        result = updater(mode='diagnostic',bootloader='N976NTEST',partitions=partitions,
            payload_sha='b'*64,current_boot_sha='c'*64,auto_return=True,device_profile=data.PROFILE)
        self.assertIn(b'Temporary Linux DATA decode diagnostic; not iOS/XNU.',result)
        self.assertNotIn(b'Temporary Linux SHA256 diagnostic',result)
        from builtin_init_profile import current_boot_binding
        pair = dict(device_profile='native-memory-observation-v1',source_head='b42228737b77f4ce1b24aa8333f03cf31190f026',
                    host_profile_source_head='b42228737b77f4ce1b24aa8333f03cf31190f026')
        plan = dict(device_profile=data.PROFILE,current_boot_payload_sha256='d'*64)
        current_boot_binding(plan,pair,{'payload_sha256':'d'*64})
        with self.assertRaises(ValueError):
            current_boot_binding(plan,dict(pair,device_profile='early-fdt-binding-v1'),{'payload_sha256':'d'*64})

    def test_new_frame_identity_counts_and_relative_caps(self):
        from decode_reservation import checksum
        identity,cycle,boot = 'a'*32,'b'*32,'c'*32
        body = 'id='+identity+' cycle='+cycle+' kind=result status=ok carrier=4096 stream=200 payload=1000 consumed=193 written=1000 calls=1 digest='+'d'*64+' ownership=0 executed=0'
        line = 'N10BOOTLINK2 boot='+boot+' N10DATA1 '+body+' checksum=%08x' % checksum(body.encode())
        self.assertTrue(data.decode(line,identity,cycle)['passed'])
        with self.assertRaises(ValueError):
            data.decode(line,identity,'e'*32)
        with self.assertRaises(ValueError):
            data.decode(line+'\n'+line,identity,cycle)
        from early_fdt_binding import ACCEPTED_BASELINE
        result = dict(data_carrier_stage=data.STAGE,image_bytes=ACCEPTED_BASELINE['image_file_bytes'],
            source_sha256=ACCEPTED_BASELINE['route_sources'],guarded_init_main_sha256=ACCEPTED_BASELINE['route_artifacts']['guarded_init_main_sha256'])
        footprint = dict(data_state_bytes=80,linked_kernel_bytes=ACCEPTED_BASELINE['linked_kernel_bytes'],
                         image_text_offset=524288,image_flags=10)
        with patch('early_fdt_binding.fixed_route_relation',return_value={'kind':'controlled-new-gate'}), \
             patch('early_fdt_binding.placement_config_sha256',return_value=ACCEPTED_BASELINE['config_sha256']):
            self.assertTrue(data.relative_admission(result,['CONFIG_NOTE10_DATA_CARRIER=y'],footprint,
                elf=b'',archive=b'',raw_inputs={})['eligible'])
            bad = dict(footprint,linked_kernel_bytes=footprint['linked_kernel_bytes']+1)
            self.assertFalse(data.relative_admission(result,['CONFIG_NOTE10_DATA_CARRIER=y'],bad,
                elf=b'',archive=b'',raw_inputs={})['eligible'])

    def test_retained_pass_gate_fails_closed(self):
        plausible = dict(kind='linux-data-carrier-retained-pass',root_reviewed=True,source_commit='a'*40,
            run_id=123,attempt=1,result_sha256='b'*64,source_sha256=data.test_source_pins(),passed_case_ids=list(data.CASE_NAMES))
        for value in (plausible, {}, None):
            with self.assertRaisesRegex(ValueError,'retained PASS disabled'):
                data.retained_pass(value)



    def test_data_guard_reasons_and_parser_error_wire(self):
        from decode_reservation import checksum
        raw = self.container()
        cases = (
            ('missing_parameter',None,'parameter_missing'),
            ('good','g'*64,'parameter_invalid'),
            ('duplicate_parameter',None,'parameter_duplicate'),
            ('missing_capture',None,'capture_missing'),
            ('reversed',None,'capture_invalid'),
            ('repeat_capture',None,'capture_repeat'),
            ('changed',None,'global_mismatch'),
            ('repeat_refused_callback',None,'emit_repeat'),
        )
        identity,cycle,boot = 'a'*32,'b'*32,'c'*32
        def frame(row):
            keys = ('status','carrier','stream','payload','consumed','written','calls','digest',
                    'reasons','params','captures','retained')
            body = 'id='+identity+' cycle='+cycle+' kind=result '+ ' '.join(k+'='+str(row[k]) for k in keys)+' ownership=0 executed=0'
            return 'N10BOOTLINK2 boot='+boot+' N10DATA1 '+body+' checksum=%08x' % checksum(body.encode())
        masks = set()
        for mode,parameter,label in cases:
            row = self.invoke(raw,mode,parameter)
            self.assertEqual(row['status'],'unavailable',mode)
            self.assertEqual((row['hashes'],row['allocations'],row['calls']),(0,0,0),mode)
            self.assertIn(row['params'],(0,1,2))
            self.assertIn(row['captures'],(0,1,2))
            self.assertIn(row['retained'],(0,1))
            parsed = data.decode(frame(row),identity,cycle)
            self.assertFalse(parsed['passed'])
            self.assertIn(label,parsed['reason_labels'])
            masks.add(parsed['reasons'])
            with self.assertRaisesRegex(ValueError,'DATA functional decode failed status=unavailable reasons='+row['reasons']) as error:
                data.require_functional(parsed)
            self.assertIn(label,str(error.exception))
            self.assertIn('params='+str(row['params']),str(error.exception))
            self.assertIn('captures='+str(row['captures']),str(error.exception))
            self.assertIn('retained='+str(row['retained']),str(error.exception))
        self.assertEqual(len(masks),len(cases))
        for changes in ({'reasons':'00000400'},{'params':3},{'captures':3},{'retained':2}):
            with self.assertRaisesRegex(ValueError,'bounded DATA guard reasons'):
                data.decode(frame(dict(row,**changes)),identity,cycle)


    @staticmethod
    def synthetic_slot_inputs():
        from materialize_auto_cycle import SLOT
        raw = bytearray(4096)
        raw[64:97] = SLOT+b'\0'
        raw[256:320] = data.SLOT_PREIMAGE
        raw[400:407] = b'N10RET1'
        raw = bytes(raw)
        system = '100000 T _text\n100080 R __start_rodata\n100100 r n10_image_expectation_slot\n100800 T __init_begin\n'
        symbols = '0000000000000000 0000000000000040 r n10_image_expectation_slot\n'
        sections = '[ 3] .rodata.n10_expectation PROGBITS 0000000000000000 000080 000040 00 A 0 0 16\n'
        slot = data.slot_metadata(raw,system,symbols,sections)
        report = dict(data_expectation_mode=data.MODE,data_expectation_slot=slot,image_expectation_patched=False,
                      image_sha256=data.sha(raw),image_size=len(raw),data_carrier_sha256=data.sha(b'D'*4096),
                      data_carrier_bytes=4096,device_profile=data.PROFILE,build_passed=True,auto_return_diagnostic=True,
                      auto_cycle_slot=SLOT.decode(),accepted_result_sha256='a'*64,image_root_receipt_sha256='b'*64,
                      source_head='c'*40,ci_context={'synthetic':'only'})
        return raw,report,system,symbols,sections

    def test_private_slot_patch_preimage_bounds_and_exact_variant(self):
        from materialize_auto_cycle import SLOT
        raw,report,_,_,_ = self.synthetic_slot_inputs()
        original_report = json.loads(json.dumps(report))
        patched = data.patch_image(raw,report,'d'*32,SLOT)
        self.assertEqual(report,original_report)
        self.assertEqual(data.sha(raw),report['image_sha256'])
        self.assertNotEqual(data.sha(patched),report['image_sha256'])
        self.assertEqual(patched[280:312],bytes.fromhex(report['data_carrier_sha256']))
        allowed = set(range(64,96)) | set(range(280,312))
        self.assertTrue(all(i in allowed for i,(a,b) in enumerate(zip(raw,patched)) if a != b))
        self.assertEqual(patched[256:280],raw[256:280])
        self.assertEqual(patched[312:320],raw[312:320])
        variants = [dict(report,image_sha256='f'*64),dict(report,image_expectation_patched=True),
                    dict(report,data_carrier_sha256='0'*64),dict(report,data_expectation_mode='unknown')]
        for changes in ({'offset':64},{'expectation_offset':281},{'readonly_flags':'WA'},{'bytes':65}):
            variants.append(dict(report,data_expectation_slot=dict(report['data_expectation_slot'],**changes)))
        for invalid in variants:
            with self.assertRaises(ValueError):
                data.patch_image(raw,invalid,'d'*32,SLOT)
        duplicate = raw+data.SLOT_PREIMAGE
        with self.assertRaises(ValueError):
            data.patch_image(duplicate,dict(report,image_sha256=data.sha(duplicate)),'d'*32,SLOT)
        with self.assertRaises(ValueError):
            data.patch_image(patched,dict(report,image_sha256=data.sha(patched)),'d'*32,SLOT)

    def test_actual_loaded_readonly_slot_and_refusal_order(self):
        raw = self.container()
        unpatched = self.invoke(raw)
        self.assertEqual(unpatched['status'],'unavailable')
        self.assertEqual(int(unpatched['reasons'],16),1024)
        invalid = self.invoke(raw,slot_expectation=data.sha(raw),invalid_slot=True)
        self.assertEqual(invalid['status'],'unavailable')
        self.assertEqual(int(invalid['reasons'],16),2048)
        for row in (unpatched,invalid):
            self.assertEqual((row['hashes'],row['allocations'],row['calls'],row['expectations']),(0,0,0,0))
            self.assertEqual(row['source'],data.MODE)
            self.assertNotIn('params',row)
        expected = bytes.fromhex(data.sha(raw))
        wrong = bytes([expected[0]^1])+expected[1:]
        rejected = self.invoke(raw,slot_expectation=wrong.hex())
        self.assertEqual((rejected['status'],rejected['hashes'],rejected['allocations'],rejected['calls']),('carrier_hash',1,0,0))
        accepted = self.invoke(raw,slot_expectation=expected.hex())
        self.assertEqual((accepted['status'],accepted['expectations'],accepted['calls']),('ok',1,1))
        self.assertEqual(accepted['digest'],data.sha(self.sample()))
        self.assertEqual((accepted['allocations'],accepted['frees'],accepted['cleared']),(2,2,1))
        from decode_reservation import checksum
        body = 'id='+'a'*32+' cycle='+'b'*32+' kind=result source='+data.MODE+' '+ ' '.join(
            key+'='+str(accepted[key]) for key in ('status','carrier','stream','payload','consumed','written','calls','digest','reasons','expectations','captures','retained'))+' ownership=0 executed=0'
        frame = 'N10BOOTLINK2 boot='+'c'*32+' N10DATA1 '+body+' checksum=%08x' % checksum(body.encode())
        parsed = data.decode(frame,'a'*32,'b'*32)
        self.assertTrue(parsed['passed'])
        self.assertEqual(parsed['expectation_source'],data.MODE)
        self.assertEqual(parsed['expectations'],1)
        for key,value in (('expectations','0'),('reasons','00000400')):
            contradictory = body.replace(key+'='+str(accepted[key]),key+'='+value)
            refused = data.decode('N10BOOTLINK2 boot='+'c'*32+' N10DATA1 '+contradictory+' checksum=%08x' % checksum(contradictory.encode()),'a'*32,'b'*32)
            self.assertFalse(refused['passed'])

    def test_intrinsic_slot_profile_and_context_preservation(self):
        import materialize_auto_cycle as cycle
        raw,report,system,symbols,sections = self.synthetic_slot_inputs()
        for changed in (sections.replace('00 A ','00 WA '),sections.replace('00 A ','00 AX ')):
            with self.assertRaises(ValueError):
                data.slot_metadata(raw,system,symbols,changed)
        with self.assertRaises(ValueError):
            data.slot_metadata(raw,system.replace('100100 r','100101 r'),symbols,sections)
        with self.assertRaises(ValueError):
            data.slot_metadata(raw,system,symbols.replace('0040 r','0040 d'),sections)
        template,output = self.root/'generic-template',self.root/'private-variant'
        template.mkdir()
        (template/'Image').write_bytes(raw)
        (template/'build-result.json').write_text(json.dumps(report))
        with patch('sha256_kat_device_profile.validate_template',return_value=report):
            private = cycle.materialize(template,output,'d'*32)
            cycle.validate(output,'d'*32,template)
            self.assertEqual((template/'Image').read_bytes(),raw)
            self.assertEqual(private['auto_cycle_template_image_sha256'],report['image_sha256'])
            self.assertEqual(private['accepted_result_sha256'],report['accepted_result_sha256'])
            self.assertEqual(private['image_root_receipt_sha256'],report['image_root_receipt_sha256'])
            self.assertNotEqual(private['image_sha256'],report['image_sha256'])
            self.assertTrue(private['image_expectation_patched'])
            self.assertEqual(data.package_data(private,b'R'*4096,'synthetic-recovery=unchanged',b'D'*4096),'synthetic-recovery=unchanged')
            with self.assertRaises(ValueError):
                data.package_data(report,b'R'*4096,'synthetic-recovery=unchanged',b'D'*4096)
            bad = bytearray((output/'Image').read_bytes());bad[-1]^=1
            (output/'Image').write_bytes(bad)
            with self.assertRaises(ValueError):
                cycle.validate(output,'d'*32,template)


    def logical_container(self, length=4079):
        raw = bytearray(self.container()[:length])
        struct.pack_into('<Q',raw,16,length)
        return bytes(raw)

    def test_trusted_logical_native_extent_and_authenticated_header_bounds(self):
        logical = self.logical_container()
        native = logical+b'\xa5'*(4096-len(logical))
        for raw in (logical,native):
            row = self.invoke(raw,slot_expectation=data.sha(logical),slot_logical=len(logical))
            self.assertEqual((row['status'],row['logical'],row['carrier'],row['carrier_rc']),('ok',len(logical),len(raw),0))
            self.assertEqual((row['first_hash_bytes'],row['calls'],row['cleared']),(len(logical),1,1))
            self.assertEqual(row['digest'],data.sha(self.sample()))
        from decode_reservation import checksum
        keys=('status','carrier','logical','carrier_rc','stream','payload','consumed','written','calls','digest','reasons','expectations','captures','retained')
        body='id='+'a'*32+' cycle='+'b'*32+' kind=result source='+data.MODE+' '+' '.join(k+'='+str(row[k]) for k in keys)+' ownership=0 executed=0'
        decoded=data.decode('N10BOOTLINK2 boot='+'c'*32+' N10DATA1 '+body+' checksum=%08x'%checksum(body.encode()),'a'*32,'b'*32)
        self.assertTrue(decoded['passed'])
        self.assertEqual((decoded['logical'],decoded['carrier']),(len(logical),len(native)))
        for raw,size in ((native[:-1],len(logical)),(logical[:-1],len(logical)),(native,127),
                         (native,0),(native,64*1024*1024+1),(native,(1<<64)-1)):
            row = self.invoke(raw,slot_expectation=data.sha(logical),slot_logical=size)
            self.assertEqual((row['status'],row['hashes'],row['allocations'],row['calls']),('unavailable',0,0,0))
        for offset,value in ((16,len(logical)-1),(32,len(logical))):
            bad = bytearray(logical);struct.pack_into('<Q',bad,offset,value)
            row = self.invoke(bytes(bad),slot_expectation=data.sha(bad),slot_logical=len(bad))
            self.assertEqual((row['status'],row['hashes'],row['allocations'],row['calls']),('header',1,0,0))
        bad = bytearray(logical);bad[-1]=1
        row = self.invoke(bytes(bad),slot_expectation=data.sha(bad),slot_logical=len(bad))
        self.assertEqual((row['status'],row['allocations'],row['calls']),('header',0,0))
        minimum = bytearray(logical[:128]);struct.pack_into('<Q',minimum,16,128)
        row = self.invoke(bytes(minimum)+b'\x7e'*(2048-128),slot_expectation=data.sha(minimum),slot_logical=128)
        self.assertEqual((row['status'],row['first_hash_bytes'],row['allocations'],row['calls']),('header',128,0,0))

    def test_v2_exact_private_patch_and_current_producer_binding(self):
        import materialize_auto_cycle as cycle
        raw,report,system,symbols,sections = self.synthetic_slot_inputs()
        original = json.loads(json.dumps(report))
        private = data.patch_image(raw,report,'d'*32,cycle.SLOT)
        self.assertEqual(report,original)
        self.assertEqual(private[280:320],bytes.fromhex(report['data_carrier_sha256'])+report['data_carrier_bytes'].to_bytes(8,'little'))
        allowed = set(range(64,96))|set(range(280,320))
        self.assertTrue(all(i in allowed for i,(a,b) in enumerate(zip(raw,private)) if a!=b))
        for changed in (dict(report,data_expectation_mode='image-slot-v1'),dict(report,image_expectation_patched=True),
                        dict(report,image_sha256='f'*64),dict(report,data_carrier_bytes=127),
                        dict(report,data_carrier_bytes=64*1024*1024+1),dict(report,data_carrier_sha256='0'*64)):
            with self.assertRaises(ValueError):data.patch_image(raw,changed,'d'*32,cycle.SLOT)
        for changes in ({'expectation_bytes':32},{'logical_offset':313},{'boot_page':4096},{'offset':64},{'readonly_flags':'WA'}):
            with self.assertRaises(ValueError):
                data.patch_image(raw,dict(report,data_expectation_slot=dict(report['data_expectation_slot'],**changes)),'d'*32,cycle.SLOT)
        with self.assertRaises(ValueError):data.slot_metadata(raw+data.SLOT_PREIMAGE,system,symbols,sections)
        with self.assertRaises(ValueError):data.slot_metadata(raw,system,symbols,sections.replace('00 A ','00 AX '))
        template,variant = self.root/'generic',self.root/'variant'
        template.mkdir();(template/'Image').write_bytes(raw)
        (template/'build-result.json').write_text(json.dumps(report))
        with patch('sha256_kat_device_profile.validate_template',return_value=report):
            bound = cycle.materialize(template,variant,'d'*32)
            self.assertEqual((template/'Image').read_bytes(),raw)
            for key in ('accepted_result_sha256','image_root_receipt_sha256','source_head','ci_context'):
                self.assertEqual(bound[key],report[key])
            self.assertEqual(data.package_data(bound,b'R'*4096,'original-recovery',b'D'*4096),'original-recovery')
            edited = bytearray((variant/'Image').read_bytes());edited[-1]^=1;(variant/'Image').write_bytes(edited)
            with self.assertRaises(ValueError):cycle.validate(variant,'d'*32,template)

    def test_preload_sha_length_reads_and_carrier_error_wire(self):
        logical = self.logical_container();native=logical+b'\x91'*(4096-len(logical))
        generic = self.invoke(native)
        partial = self.invoke(native,slot_logical=len(logical))
        for row in (generic,partial):
            self.assertEqual((row['status'],row['hashes'],row['allocations'],row['calls']),('unavailable',0,0,0))
        self.assertEqual(int(generic['reasons'],16),1024)
        self.assertEqual(int(partial['reasons'],16),2048)
        shortened = self.invoke(native,slot_expectation=data.sha(logical[:-1]),slot_logical=len(logical)-1)
        self.assertEqual((shortened['logical'],shortened['first_hash_bytes'],shortened['status'],shortened['allocations']),(len(logical)-1,len(logical)-1,'header',0))
        mismatch = self.invoke(native,slot_expectation='a'*64,slot_logical=len(logical))
        api = self.invoke(native,mode='hash1',slot_expectation=data.sha(logical),slot_logical=len(logical))
        self.assertEqual((mismatch['status'],mismatch['carrier_rc']),('carrier_mismatch',0))
        self.assertEqual((api['status'],api['carrier_rc']),('carrier_crypto',-5))
        from decode_reservation import checksum
        for row in (mismatch,api):
            self.assertEqual((row['first_hash_bytes'],row['allocations'],row['calls']),(len(logical),0,0))
            keys=('status','carrier','logical','carrier_rc','stream','payload','consumed','written','calls','digest','reasons','expectations','captures','retained')
            body='id='+'a'*32+' cycle='+'b'*32+' kind=result source='+data.MODE+' '+' '.join(k+'='+str(row[k]) for k in keys)+' ownership=0 executed=0'
            self.assertLessEqual(len(body),447)
            parsed=data.decode('N10BOOTLINK2 boot='+'c'*32+' N10DATA1 '+body+' checksum=%08x'%checksum(body.encode()),'a'*32,'b'*32)
            self.assertFalse(parsed['passed'])
            self.assertEqual((parsed['status'],parsed['carrier_rc'],parsed['logical'],parsed['carrier']),(row['status'],row['carrier_rc'],len(logical),len(native)))
            with self.assertRaisesRegex(ValueError,'carrier_rc='+str(row['carrier_rc'])):data.require_functional(parsed)


class Recorded(unittest.TextTestResult):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.failed_methods,self.framework_errors = set(),[]
    def addFailure(self,test,error):
        self.failed_methods.add(test._testMethodName)
        super().addFailure(test,error)
    def addError(self,test,error):
        name = getattr(test,'_testMethodName',None)
        if name:
            self.failed_methods.add(name)
        else:
            self.framework_errors.append(test.id())
        super().addError(test,error)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--case',action='append',choices=data.CASE_NAMES)
    args = parser.parse_args()
    from sha256_kat_device_profile import private
    output = private(args.output)
    output.mkdir(parents=True,exist_ok=False)
    selected = args.case if args.case is not None else json.loads(os.environ.get('N10_NEW_CASES_JSON','[]'))
    if type(selected) is not list or any(n not in data.CASE_NAMES for n in selected) or len(selected) != len(set(selected)):
        parser.error('closed unique new case selection required')
    selected = selected or list(data.CASE_NAMES)
    LinuxDataCarrierTests.output = output
    LinuxDataCarrierTests.needs_fixture = any(n in selected for n in ('test_trusted_logical_native_extent_and_authenticated_header_bounds','test_preload_sha_length_reads_and_carrier_error_wire'))
    result = unittest.TextTestRunner(verbosity=2,resultclass=Recorded).run(unittest.TestSuite(LinuxDataCarrierTests(n) for n in selected))
    complete = result.testsRun == len(selected) and not result.framework_errors
    report = dict(kind='linux-data-carrier-new-tests',selected=selected,
        passed=[n for n in selected if n not in result.failed_methods] if complete else [],
        failed=sorted(result.failed_methods),tests_run=result.testsRun,framework_errors=result.framework_errors,
        success=result.wasSuccessful() and complete and not result.skipped,fixture_compiles=LinuxDataCarrierTests.compiles,
        source_sha256=data.test_source_pins(),
        ci_context={k:os.environ.get(k,'') for k in ('GITHUB_SHA','GITHUB_RUN_ID','GITHUB_RUN_ATTEMPT','GITHUB_JOB','GITHUB_WORKFLOW_REF','GITHUB_WORKFLOW_SHA')},
        synthetic=True,old_suites_executed=0,device_operations=[],xnu_executed=False)
    (output/'result.json').write_text(json.dumps(report,indent=2)+'\n')
    return 0 if report['success'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
