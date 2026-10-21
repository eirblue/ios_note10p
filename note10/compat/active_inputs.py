"""Select versioned userland inputs; never silently reuse an older IPSW corpus."""
import json
import hashlib
import plistlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

def userland_root():
    target = json.loads((ROOT / 'note10/target.json').read_text())
    return ROOT / target['research_directory'] / 'userland'

def userland_reports():
    directory = userland_root().parent
    report_path = directory / 'userland-report.json'
    if not report_path.is_file():
        raise FileNotFoundError('Active target userland has not been extracted/inspected: ' + str(report_path))
    reports = json.loads(report_path.read_text())
    target = json.loads((ROOT / 'note10/target.json').read_text())
    version = plistlib.loads((userland_root() / 'System/Library/CoreServices/SystemVersion.plist').read_bytes())
    if (version['ProductVersion'], version['ProductBuildVersion']) != (target['version'], target['build']):
        raise ValueError('Extracted userland does not match active target')
    for report in reports:
        path = (ROOT / report['file']).resolve()
        if not path.is_relative_to(userland_root().resolve()):
            raise ValueError('Report references a different target userland')
        if hashlib.sha256(path.read_bytes()).hexdigest() != report['sha256']:
            raise ValueError('Userland file changed since inspection')
    return reports
