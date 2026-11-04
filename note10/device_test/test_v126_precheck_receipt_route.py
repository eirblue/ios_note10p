"""One new receipt-route regression; no run_plan/preflight/old method execution."""
import argparse
import ast
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
import native_scoped_output_admission as shared
import v125_device_entry as device_entry

METHOD='test_actual_precheck_route_and_journal_use_fresh_execution_receipt'
SCOPE='v126-fresh-precheck-receipt-route'
RESULT_SCHEMA='v126-fresh-precheck-receipt-test-v1'
CAPS={'BOOT_writes': 0, 'CI': 0, 'Image_builds': 0, 'Linux_integration': 0, 'MachO': 0, 'device_queries': 0, 'kernel_builds': 0, 'local_C_compiles': 0, 'local_tests': 1, 'max_requested_PC_payload_bytes': 4096, 'native_target_builds': 0, 'new_fixture_compiles': 0, 'new_fixture_processes': 0, 'new_grouped_methods': 1, 'old_fixture_runs': 0, 'old_methods': 0, 'private_payload': 0, 'real_decoder': 0, 'reboots': 0, 'target_RAM_reservation': 0}
OUTPUT=None
ROOT=Path(__file__).resolve().parents[2]

def save(path,row):
    Path(path).parent.mkdir(parents=True,exist_ok=True)
    Path(path).write_text(json.dumps(row,indent=2)+'\n',encoding='utf-8')

def actual_receipt_expressions():
    path=Path(shared.__file__).with_name('auto_cycle.py')
    tree=ast.parse(path.read_text(encoding='utf-8-sig'))
    function=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='run_plan')
    def assignment(name,kind):
        return next(n.value for n in ast.walk(function) if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id==name for t in n.targets) and isinstance(n.value,kind))
    return path,assignment('precheck_receipt',ast.IfExp),assignment('preinstall_evidence',ast.Call)

class ReceiptRouteTests(unittest.TestCase):
    completed_sections=[]
    def test_actual_precheck_route_and_journal_use_fresh_execution_receipt(self):
        path,route,journal=actual_receipt_expressions()
        with tempfile.TemporaryDirectory(prefix='v126-new-receipt-',dir=OUTPUT) as tmp:
            root=Path(tmp);packages=root/'immutable124/packages';output=root/'fresh126'
            packages.mkdir(parents=True);output.mkdir()
            original=packages/'PREINSTALL-CHECK.json';original.write_bytes(b'{"historical":true}\n')
            before=hashlib.sha256(original.read_bytes()).hexdigest()
            context=dict(schema=device_entry.CONTEXT_SCHEMA,output=str(output),packages=str(packages))
            namespace=dict(output=output,packages=packages,item=dict(index=1,cycle='a'*32),battery_policy=dict(five_percent_exception=False),type3_context=context,str=str,dict=dict)
            # Evaluate the actual changed production expression; do not duplicate
            # its allowlist in the test or execute the passed run_plan body.
            safe_globals={'__builtins__':{'__import__':__import__}}
            receipt=eval(compile(ast.Expression(route),str(path),'eval'),safe_globals,namespace)
            self.assertEqual(receipt,output/'PREINSTALL-CHECK-01.json')
            namespace['precheck_receipt']=receipt
            evidence=eval(compile(ast.Expression(journal),str(path),'eval'),safe_globals,namespace)
            self.assertEqual(evidence['receipt_path'],str(receipt))
            # Inject only the existing validated-reader state needed by this
            # unchanged target guard; no origin/admission/device path is mocked.
            token=shared._DEVICE_READ.set(dict(context=context))
            try:
                self.assertEqual(shared.device_precheck_receipt(context,receipt),receipt)
                with self.assertRaises(ValueError):shared.device_precheck_receipt(context,original)
                with self.assertRaises(ValueError):shared.device_precheck_receipt(context,output/'wrong.json')
                receipt.write_bytes(b'{}\n')
                with self.assertRaises(ValueError):shared.device_precheck_receipt(context,receipt)
            finally:shared._DEVICE_READ.reset(token)
            self.assertEqual(hashlib.sha256(original.read_bytes()).hexdigest(),before)
            type(self).completed_sections.append('actual_route_journal_and_fresh_receipt_guard')
            save(OUTPUT/'progress.json',dict(schema=RESULT_SCHEMA,completed_sections=list(type(self).completed_sections)))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--scope',required=True,choices=(SCOPE,));p.add_argument('--output',required=True,type=Path);a=p.parse_args();OUTPUT=a.output.resolve()
    if not OUTPUT.is_relative_to(ROOT/'note10/private'):raise ValueError('fresh private synthetic output required')
    OUTPUT.mkdir(parents=True,exist_ok=False)
    result=unittest.TextTestRunner(verbosity=2).run(unittest.TestSuite([ReceiptRouteTests(METHOD)]))
    save(OUTPUT/'result.json',dict(schema=RESULT_SCHEMA,scope=SCOPE,selected=[METHOD],run=result.testsRun,errors=len(result.errors),failures=len(result.failures),passed=result.wasSuccessful(),completed_sections=ReceiptRouteTests.completed_sections,caps=CAPS,old_methods_run=0,fixture_compiles=0,fixture_processes=0,actual_private_inputs=0,actual_device_operations=[],Image_builds=0,error_tracebacks=[dict(test=t.id(),traceback=v) for t,v in result.errors],failure_tracebacks=[dict(test=t.id(),traceback=v) for t,v in result.failures]))
    raise SystemExit(0 if result.wasSuccessful() else 1)
