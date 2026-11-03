"""Bind a cycle by changing only the fixed data slot in a compiled template."""
import hashlib
import json
from pathlib import Path
import re
import shutil

SLOT = b'N10_CYCLE_SLOT_UNSET_0123456789A'
assert len(SLOT) == 32

def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))

def sha(data):
    return hashlib.sha256(data).hexdigest()

def template_bytes(root):
    report=read(root/'build-result.json');data=(root/'Image').read_bytes()
    if report.get('device_profile') is not None:
        from sha256_kat_device_profile import validate_template
        validate_template(root)
    if report.get('build_passed') is not True or report.get('auto_return_diagnostic') is not True or report.get('auto_cycle_variant'):
        raise ValueError('Successful unmodified auto-return template required')
    if sha(data)!=report['image_sha256'] or len(data)!=report['image_size'] or data.count(SLOT+b'\0')!=1 or b'N10RET1' not in data:
        raise ValueError('Template Image/hash/unique cycle slot differs')
    if report.get('auto_cycle_slot')!=SLOT.decode():raise ValueError('Template slot metadata differs')
    return report,data

def bound_image(data, report, token, *, template_root=None):
    mode = report.get('data_expectation_mode')
    if mode=='kernel-readonly-span-candidate-v1':
        from type3_admission import read_compact,patch_image
        if template_root is None:raise ValueError('typed type3 template context required')
        compact,_=read_compact(template_root,report)
        return patch_image(data,report,token,SLOT,compact)
    if mode=='kernel-readonly-candidate-v1':
        from kernel_readonly_input import read_compact, patch_image, COMPACT_FIELDS
        if template_root is None:raise ValueError('readonly template source context required')
        compact,fields=read_compact(template_root,report)
        if fields!={key:report[key] for key in COMPACT_FIELDS}:
            raise ValueError('readonly compact binding changed')
        return patch_image(data,report,token,SLOT,compact)
    if mode is not None:
        from linux_data_carrier import MODE, patch_image
        if mode != MODE:
            raise ValueError('closed Image expectation mode required')
        return patch_image(data,report,token,SLOT)
    return data.replace(SLOT,token.encode(),1)


def materialize(template,output,token):
    template=Path(template).resolve();output=Path(output).resolve()
    if not re.fullmatch('[0-9a-f]{32}',token) or output.exists():raise ValueError('Fresh variant and valid token required')
    report,data=template_bytes(template)
    shutil.copytree(template,output)
    patched=bound_image(data,report,token,template_root=template)
    (output/'Image').write_bytes(patched)
    report.update(auto_cycle_variant=True,auto_cycle_token=token,auto_cycle_template=str(template),
        auto_cycle_template_report_sha256=sha((template/'build-result.json').read_bytes()),
        auto_cycle_template_image_sha256=sha(data),image_sha256=sha(patched))
    if report.get('data_expectation_mode') is not None:
        report['image_expectation_patched'] = True
    if report.get('data_expectation_mode')=='kernel-readonly-span-candidate-v1':
        from type3_admission import materialization
        report['type3_materialization']=materialization(report,token,sha(data),sha(patched),report['auto_cycle_template_report_sha256'])
    (output/'build-result.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    validate(output,token,template)
    return report

def validate(root,token,template=None):
    root=Path(root);report=read(root/'build-result.json')
    if report.get('data_expectation_mode')=='kernel-readonly-span-candidate-v1':
        from type3_admission import validate_variant
        return validate_variant(root,token,template)
    if 'kernel_readonly_packing_revision' in report:
        from kernel_readonly_input import validate_resumed_variant
        return validate_resumed_variant(root,token,template)
    if report.get('auto_cycle_variant') is not True or report.get('auto_cycle_token')!=token or not re.fullmatch('[0-9a-f]{32}',token or ''):
        raise ValueError('Cycle data binding differs')
    source=Path(report['auto_cycle_template']).resolve()
    if template is not None and source!=Path(template).resolve():raise ValueError('Cycle template path differs')
    original,data=template_bytes(source)
    if sha((source/'build-result.json').read_bytes())!=report['auto_cycle_template_report_sha256'] or sha(data)!=report['auto_cycle_template_image_sha256']:
        raise ValueError('Compiled template changed')
    expected=bound_image(data,original,token,template_root=source)
    allowed=dict(original)
    allowed.update(auto_cycle_variant=True,auto_cycle_token=token,auto_cycle_template=str(source),
        auto_cycle_template_report_sha256=report['auto_cycle_template_report_sha256'],
        auto_cycle_template_image_sha256=sha(data),image_sha256=sha(expected))
    if original.get('data_expectation_mode') is not None:
        allowed['image_expectation_patched'] = True
    if report!=allowed or (root/'Image').read_bytes()!=expected:raise ValueError('Variant differs outside its closed data-slot patches')
    return report
