"""Strict additional identity for the opt-in, finite SDK leaf remediation."""
import json
from pathlib import Path
from fusion.contracts import digest,require

LOCK=Path(__file__).with_name('pilot-leaf-remediation.json')


def validate(runtime):
    if 'remediation' not in runtime:return
    layer=runtime['remediation'];lock=json.loads(LOCK.read_bytes())
    expected={x['name']:x['version'] for x in lock['packages'] if x['name']!='pip'}
    require(type(layer) is dict and set(layer)=={'profile','lock_sha256','prior_runtime_sha256','changed_packages','historical_lock_preserved'},'UNSUPPORTED_PROFILE')
    require(layer['profile']==lock['profile'] and layer['lock_sha256']==digest(LOCK.read_bytes()) and layer['changed_packages']==expected and
            layer['historical_lock_preserved']==runtime['lock_sha256'],'UNSUPPORTED_PROFILE')
    prior_path=Path('/opt/pilot-prior-memory-runtime.json')
    require(prior_path.is_file() and digest(prior_path.read_bytes())==layer['prior_runtime_sha256'],'UNSUPPORTED_PROFILE')
    prior=json.loads(prior_path.read_bytes())
    require(prior['lock_sha256']==runtime['lock_sha256'] and 'remediation' not in prior,'UNSUPPORTED_PROFILE')
    packages={key.lower().replace('_','-'):value for key,value in runtime['packages'].items()}
    require(all(packages.get(name)==version for name,version in expected.items()),'UNSUPPORTED_PROFILE')
    for name,version in prior['packages'].items():
        if name.lower().replace('_','-') not in expected:require(runtime['packages'].get(name)==version,'UNSUPPORTED_PROFILE')
    for key in ('model','model_spec','helper','helper_sha256','python','python_sha256','absent','profile'):
        require(runtime.get(key)==prior.get(key),'UNSUPPORTED_PROFILE')
