"""Unchanged pinned Reachability guards, injected revision-only native runtime.

There is no Python revision arithmetic and no import of admission or projection.
The 10.1.14 profile explicitly rebaselines the original guarded 10.0.1 runtime.
"""
import hashlib
import importlib
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile

from ..contracts import ContractError, canonical, digest, require
from .. import memory_contracts as c

PINS = json.loads((Path(__file__).resolve().parents[2] / 'integration/pln/sources.json').read_text())


def run(args, *, timeout=10, env=None):
    try:
        value = subprocess.run(list(map(str, args)), capture_output=True, text=True, timeout=timeout,
                               env=env, check=True)
        require(not value.stderr.strip(), 'NOT_AVAILABLE')
        return value.stdout
    except (OSError, subprocess.SubprocessError):
        raise ContractError('NOT_AVAILABLE') from None


def verify_source(name, path):
    pin = PINS['sources'][name]
    require(run(['git', '-C', path, 'rev-parse', 'HEAD']).strip() == pin['commit'], 'UNSUPPORTED_PROFILE')
    require(not run(['git', '-C', path, 'status', '--porcelain']).strip(), 'UNSUPPORTED_PROFILE')
    for file, expected in pin.get('files', {}).items():
        require(hashlib.sha256((Path(path) / file).read_bytes()).hexdigest() == expected, 'UNSUPPORTED_PROFILE')


def reuse(path):
    """Load the exact package under a private namespace; do not shadow other installs."""
    verify_source('reachability', path)
    name = '_fusion_reachability_dd56f3f'
    package = Path(path) / 'reachability'
    if name in sys.modules:
        require(Path(sys.modules[name].__file__).resolve() == (package / '__init__.py').resolve(), 'UNSUPPORTED_PROFILE')
    else:
        spec = importlib.util.spec_from_file_location(name, package / '__init__.py', submodule_search_locations=[str(package)])
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
    return importlib.import_module(name + '.pln_adapter')


class RevisionRuntime:
    def __init__(self, config, upstream, *, timeout=10):
        self.config, self.upstream, self.timeout = config, upstream, timeout

    def check(self):
        require(self.config['runtime_profile'] == c.RUNTIME, 'UNSUPPORTED_PROFILE')
        for name in ('reachability', 'pln', 'petta'):
            verify_source(name, self.config[name])
        binary = Path(self.config['swipl']).resolve()
        require(hashlib.sha256(binary.read_bytes()).hexdigest() == self.config['swipl_sha256'], 'UNSUPPORTED_PROFILE')
        version = run([binary, '--version'])
        require(version.startswith('SWI-Prolog version 10.1.14 '), 'UNSUPPORTED_PROFILE')

    def evaluate(self, formula, truths):
        require(formula == 'Truth_Revision' and type(truths) is tuple and len(truths) == 2)
        require(all(type(t) is self.upstream.TruthValue for t in truths))
        self.check()
        library = str(Path(self.config['pln']) / 'lib_pln.metta')
        require(not any(c in library for c in ('"', '\\', '\n', '\r')), 'UNSUPPORTED_PROFILE')
        # Only validated numerical literals enter the executable expression.
        program = f'!(import! &self "{library}")\n!(Truth_Revision {truths[0].metta()} {truths[1].metta()})\n'
        with tempfile.TemporaryDirectory(prefix='fusion-private-pln-') as directory:
            path = Path(directory) / 'revision.metta'
            path.write_text(program)
            output = run([self.config['swipl'], '-q', '-s', str(Path(self.config['petta']) / 'src/main.pl'),
                          '--', path, '--silent'], timeout=self.timeout,
                         env=dict(os.environ, **self.config.get('environment', {})))
        return self.parse(output)

    def parse(self, output):
        lines = output.strip().splitlines()
        require(len(lines) == 2 and lines[0] == 'true', 'NOT_AVAILABLE')
        matched = re.fullmatch(r'\(stv ([^\s()]+) ([^\s()]+)\)', lines[1])
        require(matched is not None, 'NOT_AVAILABLE')
        try:
            return self.upstream.TruthValue(float(matched[1]), float(matched[2]))
        except (ValueError, OverflowError):
            raise ContractError('NOT_AVAILABLE') from None


class GuardedRevision:
    def __init__(self, environment, *, runtime_fixture=None, timeout=10):
        self.config = json.loads(Path(environment).read_text())
        self.upstream = reuse(self.config['reachability'])
        self.native = RevisionRuntime(self.config, self.upstream, timeout=timeout)
        self.native.check()
        self.fixture = runtime_fixture is not None
        self.adapter = self.upstream.PLNAdapter(runtime_fixture or self.native)

    def profile(self):
        self.native.check()
        return {'model': c.MODEL, 'runtime_profile': c.RUNTIME,
                'provider': 'recording-runtime-fixture' if self.fixture else 'real-petta-pln',
                'reachability': PINS['sources']['reachability']['commit'],
                'pln': PINS['sources']['pln']['commit'],
                'formula_sha256': PINS['sources']['pln']['files']['lib_pln.metta'],
                'petta': PINS['sources']['petta']['commit'],
                'swipl': PINS['swipl_version'], 'binary_sha256': self.config['swipl_sha256']}

    def _support(self, value):
        c.support(value, value['claim']['scope_ref'])
        # Exact immutable claim identity. No labels are interpolated into MeTTa.
        conclusion = self.upstream.proposition(digest(canonical(value['claim'])))
        return self.upstream.ProbabilisticSupport(value['id'], value['context'], conclusion,
            self.upstream.TruthValue(c.decimal(value['truth']['strength']), c.decimal(value['truth']['confidence'], True)),
            tuple(value['evidence_ids']), tuple(value['lineage_roots']))

    def revise(self, existing, incoming, revision, independence):
        self.profile()
        c.integer(revision)
        a, b = self._support(existing), self._support(incoming)
        require(existing['claim'] == incoming['claim'] and existing['context'] == incoming['context'], 'CONFLICT')
        declaration = None
        if independence is not None:
            c.independence(independence)
            require(set(independence['supports']) == {existing['id'], incoming['id']}, 'CONFLICT')
            declaration = self.upstream.IndependenceDeclaration(independence['model_id'], (a, b))
        result = self.adapter.revise(a, b, revision, declaration)
        proposal = None
        if result.proposal is not None:
            p = result.proposal
            proposal = {'id': p.support.support_id, 'claim': existing['claim'], 'context': existing['context'],
                'truth': {'model': c.MODEL, 'strength': repr(p.support.truth.strength),
                          'confidence': repr(p.support.truth.confidence), 'evidence_count': None},
                'evidence_ids': list(p.support.evidence_ids), 'lineage_roots': list(p.support.lineage_roots),
                'coverage': sorted(set(existing['coverage']) | set(incoming['coverage'])),
                'premises': list(p.premise_ids), 'formula': p.formula_id, 'assumptions': list(p.assumptions)}
            c.response(c.support, proposal, existing['claim']['scope_ref'])
        return {'status': result.status.value, 'detail': result.detail, 'proposal': proposal}
