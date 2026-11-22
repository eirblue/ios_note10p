#!/usr/bin/env python3
"""Print the public input JSON for the v331 workflow dispatch. Read-only; no side effects."""
import argparse
import json
import v331_prepare as v

ap = argparse.ArgumentParser()
ap.add_argument('--head', required=True, help='40-hex commit SHA that will be dispatched')
ap.add_argument('--groups', type=int, required=True)
ap.add_argument('--variants', type=int, required=True)
ap.add_argument('--assertions', type=int, required=True)
ap.add_argument('--result-sha256', required=True, help='sha256 of the host fixture result log')
a = ap.parse_args()
passed = dict(passed=True, groups=a.groups, variants=a.variants,
              assertions=a.assertions, result_sha256=a.result_sha256)
print(json.dumps(v.public_context(a.head, passed), sort_keys=True, separators=(',', ':')))
