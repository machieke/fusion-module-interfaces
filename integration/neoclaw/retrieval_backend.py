"""Explicit campaign composition of the existing X01 provider. Never a fallback."""
from dataclasses import asdict
import json
import os
from pathlib import Path
import sys
from fusion.contracts import ContractError, require
from . import retrieval_campaign as c


def install(selection):
    # Keep the real class before replacing the composition factory. No instance
    # or readiness call is made until separate authority has been validated.
    from fusion.adapters import ollama_completion as adapter
    original = adapter.OllamaCompletion
    recorded = selection['mode'] == 'recorded'
    require(selection['mode'] in ('recorded','live'), 'UNSUPPORTED_PROFILE')
    value, _ = c.approve(selection['manifest'], selection['approval'], recorded=recorded, assets=False)
    session = next(s for s in value['sessions'] if s['id'] == selection['session'])

    class SelectedBackend:
        def __init__(self, lock):
            try:
                c.approve(selection['manifest'], selection['approval'], recorded=recorded, assets=False)
                require(lock == session['runtime_lock'], 'CONFLICT')
                if recorded:
                    from .retrieval_fixture import AuthoredBackend
                    self.backend = AuthoredBackend(lock)
                else: self.backend = original(lock)
                self.port = self.backend.port
            except RuntimeError: raise ContractError('UNAUTHORIZED') from None

        def complete(self, accepted):
            try: c.claim(selection['manifest'], selection['approval'], asdict(accepted), recorded=recorded)
            except RuntimeError: raise ContractError('UNAUTHORIZED') from None
            return self.backend.complete(accepted)

    adapter.OllamaCompletion = SelectedBackend


def main():
    path, policy, port, ready = sys.argv[1:]; selection = c.read(path)
    # Gate precedes isolation, constructor and server startup, even if invoked
    # directly rather than through the operator runner.
    value, _ = c.approve(selection['manifest'], selection['approval'], recorded=selection['mode']=='recorded', assets=False)
    session = next(s for s in value['sessions'] if s['id'] == selection['session'])
    if os.environ.get('FUSION_CAMPAIGN_PROVIDER_ISOLATED') != '1':
        command = ['bwrap','--die-with-parent','--ro-bind','/','/', '--proc','/proc','--dev','/dev',
                   '--bind',session['completion_root'],session['completion_root'],
                   '--bind',value['execution_root'],value['execution_root']]
        for denied in session['provider_denied_paths']: command += ['--tmpfs',denied]
        for denied in session['provider_denied_files']: command += ['--ro-bind','/dev/null',denied]
        os.execvpe('bwrap', [*command,'--',sys.executable,'-m',__spec__.name,*sys.argv[1:]],
                   dict(os.environ,FUSION_CAMPAIGN_PROVIDER_ISOLATED='1'))
    install(selection)
    from .host import serve
    serve(policy,int(port),ready)


if __name__ == '__main__': main()
