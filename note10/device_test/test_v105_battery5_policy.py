"""One grouped v105 temporary5 host test; no actual candidate/device actions."""
import argparse
import ast
import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import kernel_readonly_input as kro
import precheck_window_access as battery
import sha256_kat_device_profile as profile

OUTPUT=None
METHOD='test_v105_only5_default10_forwarding_and_early_scope_refusal'


def actual_function(filename,name,namespace):
    tree=ast.parse((Path(__file__).parent/filename).read_text())
    node=next(node for node in tree.body if isinstance(node,ast.FunctionDef) and node.name==name)
    exec(compile(ast.Module(body=[node],type_ignores=[]),filename,'exec'),namespace)
    return namespace[name]


class TemporaryBatteryTests(unittest.TestCase):
    def test_v105_only5_default10_forwarding_and_early_scope_refusal(self):
        self.assertEqual(battery.MINIMUM_INSTALL_BATTERY,10)
        for value in (10,100):battery.require_install_battery(value)
        for value in (0,4,5,9,-1,101,True,False,5.0,'5'):
            with self.subTest(default=value),self.assertRaises(ValueError):battery.require_install_battery(value)
        retained=dict(host_profile_source_head=profile.V105_PACKING_ORIGIN_HEAD,host_profile_source_sha256=dict(profile.V105_PACKING_ORIGIN_PINS))
        self.assertEqual(len(profile.packing_host_origin(retained)['host_profile_source_sha256']),57)
        with self.assertRaises(ValueError):profile.host_binding(profile.V105_PACKING_ORIGIN_HEAD)
        bad=copy.deepcopy(retained);bad['host_profile_source_sha256']['note10/device_test/auto_cycle.py']='0'*64
        with self.assertRaises(ValueError):profile.packing_host_origin(bad)
        with tempfile.TemporaryDirectory(dir=OUTPUT) as temp:
            folder=Path(temp);packages=folder/'packages';packages.mkdir();backup=folder/'backup';backup.mkdir()
            row=dict(device_profile=profile.DATA_PROFILE,data_input_kind=kro.KIND,kernel_readonly_schema=kro.SCHEMA,
                kernel_readonly_requires_ack=True,kernel_readonly_slot=dict(schema=kro.SCHEMA,descriptor_class=2),data_expectation_mode=kro.MODE,
                source_head=kro.HISTORICAL_HEAD,host_profile_source_head=kro.HISTORICAL_HEAD,kernel_readonly_packing_revision=kro.PACKING_SCHEMA,
                kernel_readonly_external_choice='compact-v1',image_sha256='b'*64,kernel_image_sha256='b'*64,
                backup_manifest_sha256='c'*64,auto_cycle_token='d'*32)
            (folder/'build-result.json').write_text(json.dumps(row));(packages/'package-result.json').write_text(json.dumps(row))
            record=dict(schema='user-v105-only-temporary5percent-exception-v1',version_scope='v105',exception_applies_to_version='v105',
                native_v105_source_head=kro.HISTORICAL_HEAD,exception_minimum_percent=5,v106_and_later_minimum_percent=10,
                standing_5percent_exception=False,all_other_safety_gates_unchanged=True,must_transfer_daily=True,
                below5_action_current_v105='PC-only new builds/tests',exact_user_instruction='synthetic v105-only approval',exact_v105_plan_sha256='a'*64)
            approval=folder/'approval.json';approval.write_text(json.dumps(record));pin=hashlib.sha256(approval.read_bytes()).hexdigest()
            scope=dict(row,plan_declared_minimum_percent=10,plan_sha256='a'*64)
            arguments=dict(use_v105_5pct_exception=True,approval_path=approval,approval_sha256=pin,scope=scope,growth_ack=True,
                execution_host_source_head='9'*40,declared_test_version='v105')
            policy=battery.make_install_battery_policy(**arguments)
            self.assertEqual((policy['default_minimum_percent'],policy['effective_minimum_percent'],policy['plan_declared_minimum_percent']),(10,5,10))
            for value in (5,100):battery.require_install_battery(value,policy=policy)
            for value in (0,4,-1,101,True,False,5.0,'5'):
                with self.subTest(exception=value),self.assertRaises(ValueError):battery.require_install_battery(value,policy=policy)
            for changes in (dict(declared_test_version='v106'),dict(scope=dict(scope,source_head='6'*40)),
                dict(scope=dict(scope,version='v106')),dict(scope=dict(scope,plan_sha256='e'*64)),dict(scope=dict(scope,plan_declared_minimum_percent=5)),
                dict(scope=dict(scope,diagnostic_kind='readonly-input-pc',PC_only=False)),dict(growth_ack=False)):
                with self.subTest(changes=changes),self.assertRaises(ValueError):battery.make_install_battery_policy(**dict(arguments,**changes))
            default106=battery.make_install_battery_policy(declared_test_version='v106')
            self.assertEqual(default106['effective_minimum_percent'],10)
            with self.assertRaises(ValueError):battery.require_install_battery(5,policy=default106)
            battery.require_install_battery(10,policy=default106)
            fake=dict(policy,effective_minimum_percent=True)
            with self.assertRaises(ValueError):battery.require_install_battery(5,policy=fake)
            events=[]
            class MockTransport:
                serial='synthetic'
                def text(self,*args,**kwargs):
                    events.append(('battery-query',args));return '5'
                def call(self,*args,**kwargs):raise AssertionError('no actual device/installation path')
            records=[dict(mode='diagnostic',file='synthetic.zip')]
            save=lambda path,value:Path(path).write_text(json.dumps(value))
            read=lambda path:json.loads(Path(path).read_text())
            check=actual_function('sha256_kat_device_profile.py','precheck',dict(Path=Path,private=lambda path:Path(path),read=read,save=save,
                variant=lambda *args:row,fields=lambda bound:{},sha=lambda path:'c'*64,package_scope=lambda pair:None,require=profile.require))
            plan=dict(kernel_build=str(folder),device_profile=profile.DATA_PROFILE,minimum_battery=10,
                kernel_readonly_packing_revision=kro.PACKING_SCHEMA,kernel_readonly_external_choice='compact-v1',
                kernel_readonly_packing_host=retained,kernel_readonly_reused_variant={},image_sha256='b'*64,
                backup_manifest_sha256='c'*64,backup=str(backup),stages=[dict(index=1,cycle='d'*32,packages=str(packages),kernel_build=str(folder),image_sha256='b'*64)])
            def stage(*args,**kwargs):events.append(('stage',kwargs));return dict(native_archive_read_verified=False)
            run=actual_function('auto_cycle.py','run_plan',dict(Path=Path,hashlib=hashlib,validate_plan=lambda *args:plan,read=read,private=lambda path:Path(path),save=save,
                preflight=lambda adb:events.append(('run-preflight',None)) or dict(twrp_version='synthetic'),stage=stage,verify_packages=lambda path:records))
            fake_auto=SimpleNamespace(verify_partitions=lambda *args,**kwargs:None)
            with patch.object(profile,'precheck',side_effect=check),patch('run_probe.preflight',return_value={}),                patch('stage_phase2.verify_packages',return_value=records),patch('prepare_linux_boot.read_verified_backup',return_value={}),patch.dict(sys.modules,{'auto_cycle':fake_auto}):
                with self.assertRaisesRegex(ValueError,'at least 10'):run(folder/'unused','a'*64,folder/'default-run',execute=True,adb=MockTransport(),ack_kernel_readonly_growth=True)
                stopped=(packages/'PREINSTALL-CHECK.json').read_bytes()
                with self.assertRaisesRegex(ValueError,'current RAM stage binding missing'):
                    run(folder/'unused','a'*64,folder/'exception-run',execute=True,adb=MockTransport(),ack_kernel_readonly_growth=True,
                        v105_battery_5pct_exception=True,battery_exception_approval=approval,battery_exception_approval_sha256=pin,
                        execution_host_source_head='9'*40,declared_test_version='v105')
                self.assertEqual((packages/'PREINSTALL-CHECK.json').read_bytes(),stopped)
                receipt=json.loads((folder/'exception-run/PREINSTALL-CHECK-01.json').read_text())
                journal=json.loads((folder/'exception-run/journal.json').read_text())
                self.assertEqual((receipt['observed_battery_percent'],receipt['declared_minimum_battery'],receipt['effective_minimum_battery']),(5,10,5))
                self.assertEqual(journal['battery_policy']['approval_binding']['sha256'],pin)
                self.assertEqual(journal['battery_policy']['declared_test_version'],'v105')
                self.assertEqual(plan['minimum_battery'],10);self.assertFalse(journal['partition_writes_attempted']);self.assertFalse(journal['reboots_attempted'])
                for version,change in (('v106',{}),('v105',dict(source_head='6'*40)),('v105',dict(diagnostic_kind='readonly-input-pc',PC_only=False))):
                    events.clear();(folder/'build-result.json').write_text(json.dumps(dict(row,**change)))
                    with self.assertRaises(ValueError):run(folder/'unused','a'*64,folder/('refuse-'+version),execute=True,adb=MockTransport(),ack_kernel_readonly_growth=True,
                        v105_battery_5pct_exception=True,battery_exception_approval=approval,battery_exception_approval_sha256=pin,
                        execution_host_source_head='9'*40,declared_test_version=version)
                    self.assertEqual(events,[])


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();OUTPUT=args.output;OUTPUT.mkdir(parents=True,exist_ok=False)
    result=unittest.TextTestRunner(verbosity=2).run(unittest.TestSuite([TemporaryBatteryTests(METHOD)]))
    (OUTPUT/'result.json').write_text(json.dumps(dict(schema='v105-temporary5-new1-v1',selected=[METHOD],run=result.testsRun,
        failures=len(result.failures),errors=len(result.errors),passed=result.wasSuccessful(),old_methods=0,C_compiles=0,Image_builds=0,
        CI=0,actual_private_candidate_calls=0,device_actions=0,physical_admission_from_PC_PASS=False),indent=2)+'\n')
    raise SystemExit(0 if result.wasSuccessful() else 1)
