"""Assemble an offline preview packet from explicit, already built artifacts.

This invokes only Helm packaging. It never runs Docker, Kubernetes, a provider,
model, image entrypoint, install hook or network request. Run from the source
checkout with ``python -m sdk.distribution`` after final source qualification.
"""
import argparse
import errno
import gzip
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import tarfile

from fusion.contracts import canonical, digest, require
from integration.single_node.preview_values import generate
from integration.single_node.reference_artifacts import sha, verify
from sdk.inventory import inventory

ROOT = Path(__file__).resolve().parents[1]
CHART_FILES = (
    'deploy/helm/omega-fusion/Chart.yaml',
    'deploy/helm/omega-fusion/values.yaml',
    'deploy/helm/omega-fusion/values.schema.json',
    'deploy/helm/omega-fusion/templates/components.yaml',
    'deploy/helm/omega-fusion/templates/network-policy.yaml',
)
# This list is intentionally not a recursive copy of the checkout or artifacts.
# Changes to the public packet require a reviewable change to this selection.
PUBLIC_FILES = CHART_FILES + (
    'sdk/README.md', 'sdk/OPERATOR.md', 'sdk/DISTRIBUTION_REVIEW.md',
    'sdk/DISTRIBUTION.md',
    'sdk/build.py', 'sdk/distribution.py', 'sdk/inventory.py',
    'sdk/image_inventory.py', 'sdk/test_image_inventory.py',
    'sdk/exports.py', 'sdk/public-api.json', 'sdk/operator_cli.py',
    'sdk/operator-wheel-inputs.json', 'sdk/test_operator_package.py',
    'sdk/test_operator_install.py', 'sdk/test_preview_distribution.py',
    'sdk/test_distribution.py', 'sdk/qualification.json',
    'sdk/qualification-02.json', 'sdk/operator-final-candidate-qualification-01.json',
    'sdk/operator-final-candidate-qualification-02.json',
    'sdk/operator-final-candidate-qualification-03.json',
    'sdk/operator-final-candidate-qualification-04.json',
    'sdk/distribution-verifier-development-01.json',
    'sdk/distribution-verifier-development-02.json',
    'sdk/distribution-assembly-qualification-01.json',
    'sdk/distribution-assembly-qualification-02.json',
    'sdk/distribution-assembly-qualification-03.json',
    'sdk/distribution-assembly-qualification-04.json',
    'sdk/compatibility/README.md',
    'sdk/compatibility/0.1.0/fusion_module_client-0.1.0-py3-none-any.whl',
    'sdk/compatibility/0.1.0/fusion_file_feed_example-0.1.0-py3-none-any.whl',
    'examples/phase2_provider/README.md', 'examples/phase2_provider/__init__.py',
    'examples/phase2_provider/server.py', 'examples/phase2_provider/caller.py',
    'examples/phase2_provider/conformance.py',
    'examples/preview_chain_observer.py',
    'examples/preview_single_agent_values.py',
    'examples/preview_single_agent_qualification.py',
    'examples/preview_restore_qualification.py',
    'examples/preview_shared_source_qualification.py',
    'examples/preview_storage_layout_qualification.py',
    'examples/preview_handoff_recovery.py',
    'examples/preview_combined_observations.py',
    'examples/preview_stage_observations.py',
    'tests/__init__.py', 'tests/test_phase2_sdk.py',
    'tests/test_phase2_sdk_contracts.py', 'tests/test_phase2_sdk_compatibility.py',
    'tests/test_reference_schema.py',
    'tests/test_phase2_single_agent_values.py', 'tests/test_phase2_operator_values.py',
    'tests/test_phase2_single_agent_qualification.py',
    'tests/test_phase2_combined_observations.py',
    'tests/test_phase2_stage_observations.py',
    'tests/test_phase2_history_projection.py',
    'tests/test_phase2_owner_races.py',
    'tests/test_phase2_restore_qualification.py',
    'tests/test_phase2_shared_source_qualification.py',
    'tests/test_phase2_chain_observer.py', 'tests/test_m4_chain.py',
    'docs/phase2/programme-report.md', 'docs/phase2/scenario-matrix.md',
    'docs/phase2/runbook.md', 'docs/phase2/storage-layout.md', 'docs/phase2/irc-regression-recipe.md',
    'docs/phase2/latency-diagnosis.md', 'docs/phase2/sdk-compatibility.md',
    'docs/phase2/private-scopes.md', 'docs/phase2/native-capability-matrix.md',
    'docs/phase2/cross-feature-evidence-review.md',
    'docs/reference-distribution/README.md',
    'deploy/single-node/README.md', 'deploy/single-node/Dockerfile',
    'deploy/single-node/create_secrets.py',
    'deploy/single-node/import_workflow_images.py',
    'deploy/single-node/package_image.py', 'deploy/single-node/package_memory.py',
    'deploy/single-node/package_workflow.py', 'deploy/single-node/package_reference.py',
    'deploy/single-node/operator-lock.txt',
    'deploy/single-node/operator-requirements.txt',
    'deploy/single-node/ci-requirements.txt',
    'deploy/single-node/preview-ci-requirements.txt',
    'deploy/single-node/native-asset-manifest.json',
    '.github/workflows/reference.yml',
    # Existing hosted fast/preview-fast lanes and their direct test helpers.
    # This remains an explicit list, not a recursive publication of tests/.
    'tests/m2_support.py', 'tests/m3_support.py', 'tests/m5_support.py',
    'tests/test_cognitive_services.py', 'tests/test_m5_boundaries.py',
    'tests/test_model_channel_services.py',
    'tests/test_phase2_active_memory_ports.py', 'tests/test_phase2_artifact_contracts.py',
    'tests/test_phase2_backup.py', 'tests/test_phase2_backup_boundary.py',
    'tests/test_phase2_bridge_timing.py', 'tests/test_phase2_catalogue_adversarial.py',
    'tests/test_phase2_chain.py', 'tests/test_phase2_cognitive_wiring.py',
    'tests/test_phase2_context_rendering.py',
    'tests/test_phase2_supersession_cognition.py',
    'tests/test_phase2_cross_feature_edges.py', 'tests/test_phase2_deploy.py',
    'tests/test_phase2_detta_layout.py',
    'tests/test_phase2_facet_ports.py', 'tests/test_phase2_fault_configuration.py',
    'tests/test_phase2_foundations.py', 'tests/test_phase2_handles.py',
    'tests/test_phase2_handoff_recovery.py',
    'tests/test_phase2_history_deadlines.py', 'tests/test_phase2_history_relations.py',
    'tests/test_phase2_inspect_ports.py', 'tests/test_phase2_lifecycle.py',
    'tests/test_phase2_memory_policy.py', 'tests/test_phase2_model.py',
    'tests/test_phase2_native_inspect.py', 'tests/test_phase2_native_relations.py',
    'tests/test_phase2_preview_diagnostics.py', 'tests/test_phase2_preview_wiring.py',
    'tests/test_phase2_private_scopes.py', 'tests/test_phase2_recorded_proposals.py',
    'tests/test_phase2_scope_qualification.py', 'tests/test_phase2_session_bounds.py',
    'tests/test_phase2_session_service.py', 'tests/test_phase2_storage_gate.py',
    'tests/test_phase2_tasks.py', 'tests/test_phase2_text_policy.py',
    'tests/test_phase2_work_budgets.py', 'tests/test_phase2_workbench.py',
    'tests/test_phase2_workspace.py',
    'tests/test_reference_boundaries.py', 'tests/test_reference_chain_services.py',
    'tests/test_reference_diagnostics.py', 'tests/test_reference_live.py',
    'tests/test_reference_ownership.py', 'tests/test_reference_restore.py',
    'deploy/single-node/values.yaml', 'deploy/single-node/memory-values.yaml',
    'deploy/single-node/workflow-values.yaml', 'deploy/single-node/cognitive-values.yaml',
    'deploy/single-node/chain-values.yaml',
    # Reviewed public evidence and the bounded relative-link closure. Keep this
    # literal: never copy owner state or recursively publish artifacts/. The
    # current evidence/phase2/artifacts.json is a detached post-assembly record
    # and must stay outside this hashed packet; the older A-N record is a leaf.
    'codex_omega_phase2_multi_agent_developer_preview.md',
    'docs/omega-adoption/mettaclaw-neoclaw/coverage.json',
    'docs/phase2/final-review-notes.md',
    'docs/reference-distribution/programme-report.md',
    'evidence/phase2/capabilities.json',
    'evidence/phase2/changed-files.json',
    'evidence/phase2/checkpoint-11.json',
    'evidence/phase2/development/final-dev17/combined-native.json',
    'evidence/phase2/development/final-dev17/combined-observations.json',
    'evidence/phase2/development/final-dev17/same-workflow-chain.json',
    'evidence/phase2/development/final-dev17/workbench.json',
    'evidence/phase2/development/recovery-r17b-summary.json',
    'evidence/phase2/development/protected-comparison-compact-serialization.json',
    'evidence/phase2/development/stage-observations-01.json',
    'evidence/phase2/development/stage-observations-01.log',
    'evidence/phase2/development/storage-layout-real-01.json',
    'evidence/phase2/development/storage-layout-real-02.json',
    'evidence/phase2/development/storage-layout-source-01.json',
    'evidence/phase2/development/storage-layout-source-02.json',
    'evidence/phase2/final/attention-comparison.json',
    'evidence/phase2/final/attention-file.json',
    'evidence/phase2/final/attention-sqlite.json',
    'evidence/phase2/final/bounded-workload.json',
    'evidence/phase2/final/capability-binding.json',
    'evidence/phase2/final/chart-equivalence.json',
    'evidence/phase2/final/checks.json',
    'evidence/phase2/final/checks/baseline-fast.log',
    'evidence/phase2/final/checks/cognitive-selection.log',
    'evidence/phase2/final/checks/distribution-allowlist-report.json',
    'evidence/phase2/final/checks/distribution-allowlist-operator.log',
    'evidence/phase2/final/checks/distribution-allowlist-schema.log',
    'evidence/phase2/final/checks/handoff-observer.log',
    'evidence/phase2/final/checks/historical-native-34.log',
    'evidence/phase2/final/checks/historical-native-denial-34.json',
    'evidence/phase2/final/checks/operator-artifact.log',
    'evidence/phase2/final/checks/owner-races.log',
    'evidence/phase2/final/checks/ownership-policy-focused.log',
    'evidence/phase2/final/checks/preview-fast.log',
    'evidence/phase2/final/checks/stage-observations.log',
    'evidence/phase2/final/cleanup.json',
    'evidence/phase2/final/combined-native.json',
    'evidence/phase2/final/combined-observations.json',
    'evidence/phase2/final/handoff-recovery.json',
    'evidence/phase2/final/handoff-setup.json',
    'evidence/phase2/final/irc-regressions.json',
    'evidence/phase2/final/irc/absent-fact.json',
    'evidence/phase2/final/irc/missing-payload.json',
    'evidence/phase2/final/irc/qualification.json',
    'evidence/phase2/final/irc/recorded.json',
    'evidence/phase2/final/irc/uncertain-send.json',
    'evidence/phase2/final/irc/unready-search.json',
    'evidence/phase2/final/irc/wrong-answer.json',
    'evidence/phase2/final/private-scopes-rotation.json',
    'evidence/phase2/final/protected-resources.json',
    'evidence/phase2/final/publication-safety.json',
    'evidence/phase2/final/recovery-setup.json',
    'evidence/phase2/final/recovery.json',
    'evidence/phase2/final/resources.json',
    'evidence/phase2/final/restore.json',
    'evidence/phase2/final/same-workflow-chain.json',
    'evidence/phase2/final/shared-source.json',
    'evidence/phase2/final/single-agent.json',
    'evidence/phase2/final/source-images.json',
    'evidence/phase2/final/stage-observations.json',
    'evidence/phase2/final/workbench.json',
    'evidence/phase2/final/workbench/04-closed-summary.png',
    'evidence/phase2/final/workbench/05-retained-native-results.png',
    'evidence/phase2/final/workbench/06-main-ready.png',
    'evidence/phase2/final/workbench/07-registered-artifact.png',
    'evidence/phase2/final/workbench/actual-chain-observation.png',
    'evidence/phase2/final/workbench/main-cleanup.json',
    'evidence/phase2/final/workbench/main-process-stop.json',
    'evidence/phase2/final/workbench/main-report.json',
    'evidence/phase2/final/workbench/native-context-consumed.png',
    'evidence/phase2/final/workbench/solo-cleanup.json',
    'evidence/phase2/final/workbench/solo-report.json',
    'evidence/phase2/final/workspace-mount-recovery.json',
    'evidence/phase2/image-dependencies-dev19.json',
    'evidence/phase2/progress.json',
    'evidence/reference-distribution/artifacts.json',
    'evidence/reference-distribution/campaign/denial.json',
    'evidence/reference-distribution/campaign/execution-ledger.json',
    'evidence/reference-distribution/campaign/plan.json',
    'evidence/reference-distribution/campaign/plan.sha256',
    'evidence/reference-distribution/cleanup.json',
    'evidence/reference-distribution/executions.json',
    'evidence/reference-distribution/progress.json',
    'evidence/reference-distribution/resources.json',
    'evidence/reference-distribution/restore.json',
    'evidence/reference-distribution/source-images.json',
    'evidence/single-node-model-channel/tests.json',
    'sdk/operator-install-qualification-01.json',
    # Direct historical deployment-document links are retained as published
    # leaves. Their JSON inventories do not recursively expand this selection.
    'adapters/detta/Cargo.lock',
    'adapters/detta/src/main.rs',
    'docs/deployment/single-node-memory.md',
    'docs/deployment/single-node.md',
    'evidence/single-node-memory/README.md',
    'evidence/single-node-memory/SHA256SUMS',
    'evidence/single-node-memory/changes.json',
    'evidence/single-node-memory/cleanup.json',
    'evidence/single-node-memory/final-a/baseline/report.json',
    'evidence/single-node-memory/final-source-manifest.json',
    'evidence/single-node-memory/gates.json',
    'evidence/single-node-memory/image-source-reconciliation.json',
    'evidence/single-node-memory/images.json',
    'evidence/single-node-memory/measurements.json',
    'evidence/single-node-memory/native-artifact-index.json',
    'evidence/single-node-memory/native-comparison-final.json',
    'evidence/single-node-memory/native-final-three-paths.json',
    'evidence/single-node-memory/packages/base-v3.json',
    'evidence/single-node-memory/packages/base-v5.json',
    'evidence/single-node-memory/packages/base-v6.json',
    'evidence/single-node-memory/packages/caller-v5.json',
    'evidence/single-node-memory/packages/caller-v6.json',
    'evidence/single-node-memory/packages/embedding-v5.json',
    'evidence/single-node-memory/packages/embedding-v6.json',
    'evidence/single-node-memory/publication-check.json',
    'evidence/single-node-memory/runs.json',
    'evidence/single-node-memory/sources.json',
    'evidence/single-node-memory/tests.json',
    'evidence/single-node-memory/workflow-original-native.json',
    'evidence/single-node/SHA256SUMS',
    'evidence/single-node/changed-files.txt',
    'evidence/single-node/cleanup.json',
    'evidence/single-node/final/digest-install.json',
    'evidence/single-node/gates.json',
    'evidence/single-node/native-regressions.log',
    'evidence/single-node/regressions.log',
    'evidence/single-node/run-index.json',
    'evidence/single-node/sources.json',
    'scripts/build_detta.py',
    'scripts/build_s01.py',
)
PREREQUISITES = (
    'Prebuilt installation needs the supplied images/chart/wheels plus an explicitly selected '
    'single-node k3s environment, kubectl, Helm, Docker import adapter, OpenSSL and CPython 3.12.',
    'Source-overlay rebuild requires each exact cached parent configuration in parent_images; '
    'parent images are not exported by this assembler. No empty-cache or air-gap rebuild is claimed.',
    'Recorded examples are disabled templates, not an approved campaign or reusable session '
    'authority. Generate fresh selections with the installed fusion-preview-values command.',
    'No generative image, model/projector assets, credentials, approvals, owner journals, '
    'private-state migration or live-generation authority is included.',
    'Wheel metadata is not a complete image/OS/native SBOM or vulnerability scan. '
    'Project license metadata remains NOASSERTION; original third-party notices still apply.',
)


def contained(root, name):
    require(type(name) is str and name and not Path(name).is_absolute()
            and '..' not in Path(name).parts, 'CONFLICT')
    path = root / name
    require(path.is_file() and not path.is_symlink()
            and path.resolve().is_relative_to(root), 'CONFLICT')
    return path


def assemble(build, wheelhouse, output, *, source_root=ROOT):
    """Copy only declared inputs; fail closed on source drift or extra wheels."""
    build, wheelhouse, output, source_root = map(lambda p: Path(p).resolve(),
                                               (build, wheelhouse, output, source_root))
    require(not output.exists(), 'CONFLICT')
    imported_path = contained(build, 'images.json')
    imported = json.loads(imported_path.read_bytes())
    require(imported.get('source_export_verification') == 'PASS', 'CONFLICT')
    entries = imported['images']
    kinds = {item['kind'] for item in entries}
    require(len(kinds) == len(entries) and {'base', 'caller', 'embedding'} <= kinds
            <= {'base', 'caller', 'embedding', 'chain'}, 'UNSUPPORTED_PROFILE')
    image_archive = contained(build, 'images.tar')
    require(image_archive.stat().st_size == imported['archive_bytes']
            and sha(image_archive) == imported['archive_sha256'], 'CONFLICT')

    packages, source_map, parents = {}, None, {}
    for entry in entries:
        package_path = contained(build, entry['source_package'])
        package = json.loads(package_path.read_bytes())
        require(package['kind'] == entry['kind'], 'CONFLICT')
        if source_map is None:
            source_map = package['source']
        require(source_map == package['source'] and type(source_map) is dict and source_map,
                'CONFLICT')
        require(type(package['parent']) is str and package['parent_config'].startswith('sha256:'),
                'CONFLICT')
        require(package['parent'] not in parents or parents[package['parent']] == package['parent_config'],
                'CONFLICT')
        parents[package['parent']] = package['parent_config']
        packages[entry['kind']] = (package_path, package)
    require(digest(canonical(source_map)) == imported['source_manifest_sha256'], 'CONFLICT')
    sources = {}
    for name, expected in source_map.items():
        require(name.startswith(('fusion/', 'integration/')), 'UNAUTHORIZED')
        path = contained(source_root, name)
        require(sha(path) == expected, 'CONFLICT')
        sources[name] = path
    for name in PUBLIC_FILES:
        sources[name] = contained(source_root, name)

    # The existing overlay recipe copies this already pinned public IRC binary.
    # Include its notice, but never walk the surrounding artifacts directory.
    irc_pins = {p['ngircd_sha256'] for _, p in packages.values() if 'ngircd_sha256' in p}
    require(len(irc_pins) <= 1, 'CONFLICT')
    if irc_pins:
        irc_name = 'artifacts/s06/ngircd/sbin/ngircd'
        binary = contained(source_root, irc_name)
        require(sha(binary) == next(iter(irc_pins)), 'CONFLICT')
        sources[irc_name] = binary
        notice = 'artifacts/s06/ngircd/share/doc/ngircd/COPYING'
        sources[notice] = contained(source_root, notice)
    chart_root = source_root / 'deploy/helm/omega-fusion'
    actual_chart = {str(p.relative_to(source_root)) for p in chart_root.rglob('*') if p.is_file()}
    require(actual_chart == set(CHART_FILES), 'CONFLICT')

    sdk_path = contained(wheelhouse, 'build-manifest.json')
    sdk_build = json.loads(sdk_path.read_bytes())
    require(sdk_build['schema'] == 'fusion-preview-sdk-build/1'
            and type(sdk_build['live_generations']) is int and sdk_build['live_generations'] == 0,
            'CONFLICT')
    pins = json.loads((source_root / 'sdk/operator-wheel-inputs.json').read_bytes())['files']
    selected_wheels = {sdk_build[role]['file'] for role in ('client', 'provider', 'operator')}
    selected_wheels.update(pin['file'] for pin in pins)
    require(len(selected_wheels) == 8
            and {p.name for p in wheelhouse.glob('*.whl')} == selected_wheels, 'CONFLICT')
    wheels = {name: contained(wheelhouse, name) for name in selected_wheels}
    for pin in pins:
        path = wheels[pin['file']]
        require(path.stat().st_size == pin['bytes'] and sha(path) == pin['sha256'], 'CONFLICT')
    for role in ('client', 'provider', 'operator'):
        record = sdk_build[role]
        require(sha(wheels[record['file']]) == record['sha256'], 'CONFLICT')
        for binding in record['sources'].values():
            path = contained(source_root, binding['source'])
            require(path.stat().st_size == binding['bytes'] and sha(path) == binding['sha256'], 'CONFLICT')
            if binding['source'].startswith(('fusion/', 'integration/')):
                require(source_map.get(binding['source']) == binding['sha256'], 'CONFLICT')
    inventory_path = contained(wheelhouse, 'dependency-inventory.json')
    require(json.loads(inventory_path.read_bytes()) == inventory(wheels.values()), 'CONFLICT')
    source_inventory = {name: dict(sha256=sha(path), bytes=path.stat().st_size,
                                  license='NOASSERTION') for name, path in sorted(sources.items())}

    output.mkdir(parents=True, exist_ok=False)
    registered = []

    def register(path, kind):
        registered.append(dict(path=str(path.relative_to(output)), bytes=path.stat().st_size,
                               sha256=sha(path), kind=kind))

    def copy(source, name, kind):
        target = output / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        register(target, kind)
        return target

    def write(name, value, kind):
        target = output / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(canonical(value))
        register(target, kind)
        return target

    copy(imported_path, 'images.json', 'verified image export manifest')
    target_archive = output / 'images.tar'
    archive_storage = 'same-filesystem hardlink; both names must remain immutable'
    try:
        os.link(image_archive, target_archive)
    except OSError as exc:
        if exc.errno != errno.EXDEV:
            raise
        shutil.copyfile(image_archive, target_archive)
        archive_storage = 'copied across filesystems'
    register(target_archive, 'immutable OCI image archive')
    image_map = {}
    for entry in entries:
        kind = entry['kind']
        package_path, package = packages[kind]
        name = 'image-sources/' + kind + '.json'
        copy(package_path, name, 'exact role source package')
        image_map[kind] = dict(repository=entry['repository'], tag=entry['local_tag'].rsplit(':', 1)[1],
                              manifest=entry['manifest_digest'], configuration=entry['configuration_digest'],
                              source_package=name, source_manifest_sha256=digest(canonical(package['source'])))
    for name, path in sorted(wheels.items()):
        copy(path, 'wheelhouse/' + name, 'exact wheel with original notices')
    copy(sdk_path, 'wheelhouse/build-manifest.json', 'exact SDK build bindings')
    copy(inventory_path, 'wheelhouse/dependency-inventory.json', 'actual wheel dependency/license inventory')

    # Loose docs/tooling are convenient for operators; the archive additionally
    # carries every exact image-declared source file, without a checkout mount.
    for name in PUBLIC_FILES:
        copy(sources[name], name, 'positive-list public source/documentation')
    with (output / 'source.tar.gz').open('wb') as raw:
        with gzip.GzipFile(filename='', mode='wb', fileobj=raw, mtime=0) as compressed:
            with tarfile.open(fileobj=compressed, mode='w') as archive:
                for name, path in sorted(sources.items()):
                    data = path.read_bytes()
                    require(digest(data) == source_inventory[name]['sha256'], 'CONFLICT')
                    record = tarfile.TarInfo(name)
                    record.size, record.mode = len(data), 0o755 if name.endswith('/sbin/ngircd') else 0o644
                    archive.addfile(record, io.BytesIO(data))
    register(output / 'source.tar.gz', 'positive-list source and pinned public IRC prerequisite')
    write('source-inventory.json', dict(schema='fusion-preview-public-source-inventory/1',
          files=source_inventory, project_license='NOASSERTION'), 'exact public source inventory')

    subprocess.run(['helm', 'package', str(chart_root), '--destination', str(output)],
                   check=True, capture_output=True, text=True)
    charts = list(output.glob('omega-fusion-*.tgz'))
    require(len(charts) == 1, 'CONFLICT')
    chart = charts[0]
    register(chart, 'Helm-packaged chart')
    profiles = []
    for mode in ('minimal', 'memory', 'combined'):
        values = generate(imported, 'synthetic-distribution-' + mode, mode=mode)
        for role in ('omega-agent', 'omega-agent-b'):
            values['components'][role].setdefault('config', {}).update(nativeEnabled=False, workerEnabled=False)
        profiles.append(str(write('profiles/' + mode + '.yaml', values,
                                  'recorded disabled example; generate fresh installation values').relative_to(output)))
    host_tools = {}
    for tool in ('python3.12', 'helm', 'kubectl', 'openssl', 'docker'):
        found = shutil.which(tool)
        path = Path(found).resolve() if found else None
        host_tools[tool] = (dict(availability='PATH_FILE_OBSERVED', sha256=sha(path),
                                execution='HELM_PACKAGE_ONLY' if tool == 'helm' else 'NOT_EXECUTED',
                                bytes=path.stat().st_size, license='NOASSERTION') if path and path.is_file()
                            else dict(availability='NOT_FOUND'))
    write('host-tooling.json', dict(schema='fusion-preview-host-tooling-inventory/1',
          tools=host_tools, helm_package='EXECUTED', vulnerability_scan='NOT_RUN',
          hosted_ci='NOT_OBSERVED', additional_live_generations=0), 'host executable identities and limits')
    # Detect concurrent source edits rather than silently combining snapshots.
    require(all(sha(sources[name]) == binding['sha256'] for name, binding in source_inventory.items()),
            'CONFLICT')
    manifest = dict(schema='omega-single-node-preview-distribution/1', tested_source=source_map,
        images=image_map, parent_images=parents, image_archive='images.tar',
        image_archive_storage=archive_storage, chart=chart.name, source_archive='source.tar.gz',
        source_inventory='source-inventory.json', host_tooling='host-tooling.json',
        profile_files=profiles, sdk_build_manifest='wheelhouse/build-manifest.json',
        wheel_inventory='wheelhouse/dependency-inventory.json',
        files=sorted(registered, key=lambda row: row['path']),
        model_boundary='RECORDED_FIXTURE', live_generation_authorization=0,
        generative_runtime_availability='NOT_CHECKED', project_license='NOASSERTION',
        distribution='local immutable artifact set; no registry publication',
        qualification='ASSEMBLY_INTEGRITY_ONLY_NOT_AN_EXECUTED_DEPLOYMENT',
        prerequisites=list(PREREQUISITES))
    manifest_path = output / 'distribution.json'
    manifest_path.write_bytes(canonical(manifest))
    manifest_path.with_suffix('.sha256').write_text(digest(manifest_path.read_bytes()) + '\n')
    result = verify(manifest_path)
    (output / 'assembly-verification.json').write_bytes(canonical(result))
    return dict(manifest=str(manifest_path), sha256=result['manifest_sha256'],
                status=result['status'], files=len(registered), additional_live_generations=0)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build', required=True, type=Path)
    parser.add_argument('--wheelhouse', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    print(json.dumps(assemble(args.build, args.wheelhouse, args.output), indent=2))


if __name__ == '__main__':
    main()
