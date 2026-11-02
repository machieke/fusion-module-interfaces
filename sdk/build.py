"""Build small separate wheels from explicit, byte-exact source lists.

No setuptools/build environment, network access or package-manager hook is used.
Provider and operator wheels are independently installable, not part of the kit.
"""
import argparse
import base64
import csv
import hashlib
import io
import json
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]
CLIENT = ('fusion/__init__.py', 'fusion/contracts.py', 'fusion/memory_types.py',
          'fusion/ports.py', 'fusion/registry.py', 'fusion/lookup_contracts.py',
          'fusion/responses.py', 'fusion/preview_client.py',
          'fusion/memory_contracts.py', 'fusion/preview_handles.py',
          'fusion/preview_tools.py')
PROVIDER_SHARED = ('fusion/adapters/__init__.py', 'fusion/adapters/fixture_feed.py',
                   'fusion/policy.py')
PROVIDER = ('__init__.py', 'server.py', 'conformance.py', 'caller.py')
OPERATOR = ('integration/single_node/__init__.py',
            'fusion/preview_deployment_contracts.py',
            'integration/single_node/reference_ops.py',
            'integration/single_node/reference_artifacts.py',
            'integration/single_node/preview_workbench.py',
            'integration/single_node/preview_secrets.py',
            'integration/single_node/preview_values.py',
            'integration/single_node/chain_address.py')
OPERATOR_RECIPES = ('create_secrets.py', 'import_workflow_images.py')
VERSION = '0.2.0'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def wheel(destination, name, files, requires=(), *, entries=None, extras=()):
    dist = name.replace('-', '_')
    info = f'{dist}-{VERSION}.dist-info'
    sources = {target: {'source': source, 'sha256': sha(raw), 'bytes': len(raw)}
               for target, (source, raw) in sorted(files.items())}
    payloads = {target: raw for target, (_, raw) in files.items()}
    payloads[info + '/source-manifest.json'] = json.dumps(
        {'schema': 'byte-exact-source-wheel/1', 'sources': sources}, sort_keys=True, indent=2).encode() + b'\n'
    metadata = (f'Metadata-Version: 2.1\nName: {name}\nVersion: {VERSION}\n'
                'Summary: Bounded Fusion preview contract/client example\n'
                'Requires-Python: >=3.12\n' + ''.join(f'Requires-Dist: {x}\n' for x in requires)
                + ''.join(f'Provides-Extra: {x}\n' for x in extras))
    payloads[info + '/METADATA'] = metadata.encode()
    if entries:
        payloads[info + '/entry_points.txt'] = ('[console_scripts]\n' + ''.join(
            f'{key} = {value}\n' for key, value in sorted(entries.items()))).encode()
    payloads[info + '/WHEEL'] = b'Wheel-Version: 1.0\nGenerator: fusion-byte-exact-builder\nRoot-Is-Purelib: true\nTag: py3-none-any\n'
    rows = []
    for path, data in sorted(payloads.items()):
        value = base64.urlsafe_b64encode(hashlib.sha256(data).digest()).decode().rstrip('=')
        rows.append([path, 'sha256=' + value, str(len(data))])
    rows.append([info + '/RECORD', '', ''])
    stream = io.StringIO(newline='')
    csv.writer(stream).writerows(rows)
    payloads[info + '/RECORD'] = stream.getvalue().encode()
    path = destination / f'{dist}-{VERSION}-py3-none-any.whl'
    with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED) as archive:
        for target, data in sorted(payloads.items()):
            item = zipfile.ZipInfo(target, date_time=(2026, 1, 1, 0, 0, 0))
            item.external_attr = 0o644 << 16
            item.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(item, data)
    return {'file': path.name, 'sha256': sha(path.read_bytes()), 'sources': sources}


def build(destination):
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=True)
    shared = {p: (p, (ROOT / p).read_bytes()) for p in CLIENT}
    shared['fusion_sdk/__init__.py'] = ('sdk/exports.py', (ROOT / 'sdk/exports.py').read_bytes())
    shared['fusion_sdk/public-api.json'] = ('sdk/public-api.json', (ROOT / 'sdk/public-api.json').read_bytes())
    provider = {p: (p, (ROOT / p).read_bytes()) for p in PROVIDER_SHARED}
    for p in PROVIDER:
        source = 'examples/phase2_provider/' + p
        provider['phase2_provider/' + p] = (source, (ROOT / source).read_bytes())
    operator = {p: (p, (ROOT / p).read_bytes()) for p in OPERATOR}
    operator['fusion_operator/cli.py'] = ('sdk/operator_cli.py', (ROOT / 'sdk/operator_cli.py').read_bytes())
    for name in OPERATOR_RECIPES:
        source = 'deploy/single-node/' + name
        operator['fusion_operator/recipes/' + name] = (source, (ROOT / source).read_bytes())
    result = {'schema': 'fusion-preview-sdk-build/1', 'live_generations': 0,
              'client': wheel(destination, 'fusion-module-client', shared),
              'provider': wheel(destination, 'fusion-file-feed-example', provider,
                                ('fusion-module-client>=0.1.0,<0.3.0',)),
              'operator': wheel(destination, 'fusion-preview-operator', operator,
                                ('fusion-module-client==0.2.0',
                                 'PyYAML==6.0.3; extra == "artifact-verification"',
                                 'PyYAML==6.0.3; extra == "preview-install"',
                                 'cryptography==50.0.2; extra == "chain-key-setup"',
                                 'pycryptodome==4.0.0; extra == "chain-key-setup"',
                                 'cffi==2.1.1; extra == "chain-key-setup"',
                                 'pycparser==3.12; extra == "chain-key-setup"'),
                                entries={'fusion-preview-workbench': 'integration.single_node.preview_workbench:main',
                                         'fusion-verify-artifacts': 'integration.single_node.reference_artifacts:main',
                                         'fusion-create-secrets': 'fusion_operator.cli:create_secrets',
                                         'fusion-preview-values': 'integration.single_node.preview_values:main',
                                         'fusion-import-images': 'fusion_operator.recipes.import_workflow_images:main'},
                                extras=('artifact-verification', 'preview-install', 'chain-key-setup'))}
    (destination / 'build-manifest.json').write_text(json.dumps(result, sort_keys=True, indent=2) + '\n')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True)
    print(json.dumps(build(parser.parse_args().output), sort_keys=True))
