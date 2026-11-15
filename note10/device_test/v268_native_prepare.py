"""New268 identity over the immutable267 carrier procedure; no old stage invocation."""
import hashlib
from pathlib import Path
from types import CodeType,FunctionType
HERE=Path(__file__).resolve().parent
LEGACY_SHA='b3ad459cda40b6c335fc87b695ec9241b3589e1b0898fd718612d1c554f3b0b8'
if hashlib.sha256((HERE/'v267_native_prepare.py').read_bytes()).hexdigest()!=LEGACY_SHA:raise ValueError('immutable267 producer source')
import v267_native_prepare as retained
WORKFLOW='.github/workflows/note10-v268-native-prepare.yml'
JOB='v268-native-prepare'
BUILD_SCHEMA='note10-v268-holder-carrier-build-v1'
CONTEXT_SCHEMA='note10-v268-holder-carrier-public-input-v1'
MANIFEST_SCHEMA='note10-v268-holder-carrier-sealed-members-v1'
SUCCESS_MEMBERS=retained.SUCCESS_MEMBERS
PUBLIC_NEW=('v265_carrier_capacity.py','v267_coupled_carrier_bounds.py','test_v267_coupled_bounds.py','v267_native_prepare.py','v268_coupled_bounds_fixture.c','v268_native_prepare.py')

def source_pins():
    pins=retained.original.source_pins()
    pins.update({'note10/device_test/'+n:retained.sha(retained.p.ordinary(HERE/n))for n in PUBLIC_NEW})
    pins[WORKFLOW]=retained.sha(retained.p.ordinary(retained.ROOT/WORKFLOW));return pins

def _bind(function,namespace,replacements):
    # Exact full-string constants only, each once, including nested code objects.
    # No substring rewriting, source eval, old module mutation or old CLI call.
    counts={key:0 for key in replacements}
    def changed(code):
        constants=[]
        for value in code.co_consts:
            if isinstance(value,CodeType):value=changed(value)
            elif isinstance(value,str)and value in replacements:
                counts[value]+=1;value=replacements[value]
            constants.append(value)
        return code.replace(co_consts=tuple(constants))
    code=changed(function.__code__)
    if any(count!=1 for count in counts.values()):raise ValueError('closed identity substitution count')
    return FunctionType(code,namespace,function.__name__,function.__defaults__,function.__closure__)

_ENV={**retained.__dict__,**{k:globals()[k]for k in ('WORKFLOW','JOB','BUILD_SCHEMA','CONTEXT_SCHEMA','MANIFEST_SCHEMA','SUCCESS_MEMBERS','source_pins')}}
public_context=_bind(retained.public_context,_ENV,{})
_ENV['public_context']=public_context
run_build=_bind(retained.run_build,_ENV,{'note10/private/v267-ci-native-prepare':'note10/private/v268-ci-native-prepare','v267':'v268','"-v267-coupled-reader-bounds"':'"-v268-coupled-reader-bounds"'})
seal=_bind(retained.seal,_ENV,{})
_ENV.update(run_build=run_build,seal=seal)
main=_bind(retained.main,_ENV,{})
if __name__=='__main__':main()
