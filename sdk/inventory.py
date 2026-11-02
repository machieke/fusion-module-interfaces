"""Inventory built wheel bytes and declared dependencies; never import packages.

This is an artifact inventory, not a vulnerability scan or license grant.
Absent license metadata remains NOASSERTION. Python/OS/native image inventories
remain separate because a wheel does not prove the complete installed platform.
"""
import argparse
from email.parser import BytesParser
import hashlib
import json
from pathlib import Path
import zipfile


def inventory(paths):
    packages = []
    for path in sorted(map(Path, paths)):
        raw = path.read_bytes()
        with zipfile.ZipFile(path) as wheel:
            metadata_paths = [p for p in wheel.namelist() if p.endswith('.dist-info/METADATA')]
            if len(metadata_paths) != 1:
                raise ValueError('one wheel metadata record required')
            metadata = BytesParser().parsebytes(wheel.read(metadata_paths[0]))
            files = [{'path': name, 'bytes': len(value), 'sha256': hashlib.sha256(value).hexdigest()}
                     for name in sorted(wheel.namelist()) if not name.endswith('/')
                     for value in [wheel.read(name)]]
        packages.append(dict(artifact=path.name, bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest(),
            name=metadata['Name'], version=metadata['Version'], requires_python=metadata['Requires-Python'],
            declared_dependencies=metadata.get_all('Requires-Dist', []),
            optional_extras=metadata.get_all('Provides-Extra', []),
            license_expression=metadata.get('License-Expression') or 'NOASSERTION',
            license_text=metadata.get('License') or None,
            license_files=metadata.get_all('License-File', []), files=files))
    return dict(schema='fusion-wheel-dependency-license-inventory/1', packages=packages,
                scope='exact built wheels; declared dependencies, not the full installed environment',
                vulnerability_scan='NOT_RUN', hosted_ci='NOT_OBSERVED',
                additional_live_generations=0)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('wheels', nargs='+')
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    Path(args.output).write_text(json.dumps(inventory(args.wheels), sort_keys=True, indent=2) + '\n')


if __name__ == '__main__':
    main()
