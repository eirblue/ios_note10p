"""Bounded transport for public synthetic PASS metadata, never private payloads."""
import base64
import binascii
import json
import zlib

PREFIX='n10-public-json-zlib-v1:'
MAX_ENCODED=65535
MAX_COMPRESSED=32768
MAX_JSON=131072


def encode_public(row):
    raw=json.dumps(row,sort_keys=True,separators=(',',':'),ensure_ascii=True).encode('ascii')
    if not 0<len(raw)<=MAX_JSON:raise ValueError('bounded public JSON required')
    compressed=zlib.compress(raw,9)
    if len(compressed)>MAX_COMPRESSED:raise ValueError('bounded compressed public metadata required')
    result=PREFIX+base64.b64encode(compressed).decode('ascii')
    if len(result)>MAX_ENCODED:raise ValueError('workflow public input bound exceeded')
    return result


def decode_public(encoded):
    if type(encoded) is not str or not encoded.startswith(PREFIX) or len(encoded)>MAX_ENCODED:raise ValueError('exact bounded public metadata envelope required')
    try:compressed=base64.b64decode(encoded[len(PREFIX):],validate=True)
    except (binascii.Error,ValueError) as error:raise ValueError('invalid public envelope base64') from error
    if not 0<len(compressed)<=MAX_COMPRESSED:raise ValueError('compressed public metadata bound exceeded')
    inflater=zlib.decompressobj()
    try:raw=inflater.decompress(compressed,MAX_JSON+1)
    except zlib.error as error:raise ValueError('invalid public zlib stream') from error
    if len(raw)>MAX_JSON or inflater.unconsumed_tail or inflater.unused_data or not inflater.eof:raise ValueError('public stream truncated, trailing or oversized')
    try:return json.loads(raw.decode('utf-8'))
    except (UnicodeDecodeError,json.JSONDecodeError) as error:raise ValueError('public UTF8 JSON required') from error
