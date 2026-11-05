"""Opt-in bounded reclamation inside the existing Chroma Search owner.

Only expired, unpublished native index generations qualify. Published generations
are permanent implicit pins under historical view retention; their indexes and
all maintenance/source/manifest records remain. New policy never frees replay
identities or refunds the generation count. The owner lock serializes publication
and plan application. Reclamation after interruption observes exact removed files.
"""
import json
import os
from pathlib import Path
import time
import uuid
from .contracts import canonical, digest, require, label, ContractError
from .adapters.chroma_vector import publish

PROFILE = 'expired-unpublished-search-reclamation/1'
LIMITS = dict(plans=32, generations=16, files=256, bytes=64 * 1024 * 1024)


def tree(root):
    require(root.is_dir() and not root.is_symlink(), 'NOT_AVAILABLE')
    files = {}; count = 0
    for p in sorted(root.rglob('*')):
        require(not p.is_symlink(), 'UNAUTHORIZED')
        require(p.is_file() or p.is_dir(), 'UNAUTHORIZED')
        if p.is_file():
            count += p.stat().st_size
            require(count <= LIMITS['bytes'] and len(files) < LIMITS['files'], 'OVERLOADED')
            files[str(p.relative_to(root))] = dict(bytes=p.stat().st_size, sha256=digest(p.read_bytes()),
                                                   blocks=p.stat().st_blocks * 512, links=p.stat().st_nlink)
    return files


class Cleanup:
    def __init__(self, search, *, clock=lambda: time.time_ns() // 1000000):
        self.search = search
        self.clock = clock

    def _publication(self):
        p = self.search.root / 'published.json'
        require(not p.is_symlink() and p.is_file() and p.stat().st_size <= 131072, 'NOT_AVAILABLE')
        raw = p.read_bytes(); value = json.loads(raw)
        require(set(value) == {'current', 'generations'} and type(value['generations']) is dict, 'CONFLICT')
        require(value['current'] is not None and value['generations'].get(value['current']['generation']) == value['current'], 'CONFLICT')
        return digest(raw), value

    def _candidate(self, generation, now, published):
        require(str(uuid.UUID(generation)) == generation, 'INVALID_ARGUMENT')
        require(generation not in published['generations'], 'CONFLICT')
        directory = self.search.root / generation
        require(directory.is_dir() and not directory.is_symlink(), 'NOT_AVAILABLE')
        p = directory / 'maintenance.json'
        require(not p.is_symlink() and p.is_file() and p.stat().st_size <= 32768, 'NOT_AVAILABLE')
        raw = p.read_bytes(); record = json.loads(raw); intent = record['intent']
        require(set(record) == {'intent', 'attempts'} and type(record['attempts']) is int and 0 <= record['attempts'] <= 3, 'CONFLICT')
        require(intent['scope'] == self.search.scope and intent['profile'] == self.search.c.PROFILE and
                intent['corpus'] == self.search.corpus and intent['embedding'] == self.search.embedding, 'CONFLICT')
        named, expected = self.search._named(self.search.scope, intent['through'], intent['key'], intent['principal'])
        require(named == generation and intent == dict(expected, deadline_ms=intent['deadline_ms']), 'CONFLICT')
        require(type(intent['deadline_ms']) is int and intent['deadline_ms'] < now, 'DEADLINE_EXCEEDED')
        # The immutable authoritative ports, rather than a cache, establish
        # reconstructibility. An unavailable/mismatched source refuses cleanup.
        self.search._head(self.search.scope, intent['through'])
        index = directory / 'index'
        files = tree(index)
        require(files, 'NOT_AVAILABLE')
        return dict(generation=generation, maintenance_sha256=digest(raw), source_head=intent['through'],
                    original_deadline_ms=intent['deadline_ms'], attempts_spent=record['attempts'], files=files)

    def _plan_locked(self, generations):
        owner = self.search
        owner.access.authorize(owner.scope, 'maintenance.planCleanup')
        require(type(generations) is list and 1 <= len(generations) <= LIMITS['generations'] and
                len(set(generations)) == len(generations), 'INVALID_ARGUMENT')
        head, published = self._publication(); now = self.clock()
        candidates = [self._candidate(g, now, published) for g in sorted(generations)]
        require(sum(len(x['files']) for x in candidates) <= LIMITS['files'], 'OVERLOADED')
        require(sum(f['bytes'] for x in candidates for f in x['files'].values()) <= LIMITS['bytes'], 'OVERLOADED')
        plan = dict(profile=PROFILE, scope=owner.scope, projection=owner._snapshot_extension(), publication_sha256=head, candidates=candidates,
                    dependency_rule='all-published-generations-pinned; expired-unpublished-index-only',
                    limits=LIMITS, authoritative_deletion=False, replay_record_deletion=False, capacity_refund=False)
        owner.access.authorize(owner.scope, 'maintenance.planCleanup')
        require(len(canonical(plan)) <= 60000, 'OVERLOADED')
        return dict(plan=plan, plan_sha256=digest(canonical(plan)))

    def plan(self, generations):
        with self.search._lock(): return self._plan_locked(generations)

    def _validate(self, plan):
        require(type(plan) is dict and set(plan) == {'plan', 'plan_sha256'}, 'INVALID_ARGUMENT')
        p = plan['plan']
        require(set(p) == {'profile', 'scope', 'projection', 'publication_sha256', 'candidates', 'dependency_rule', 'limits',
                           'authoritative_deletion', 'replay_record_deletion', 'capacity_refund'}, 'INVALID_ARGUMENT')
        require(p['profile'] == PROFILE and p['scope'] == self.search.scope and p['limits'] == LIMITS, 'UNSUPPORTED_PROFILE')
        require(p['projection'] == self.search._snapshot_extension(), 'CONFLICT')
        require(plan['plan_sha256'] == digest(canonical(p)), 'CONFLICT')
        require(p['authoritative_deletion'] is False and p['replay_record_deletion'] is False and p['capacity_refund'] is False,
                'UNAUTHORIZED')
        return p

    def _path(self, principal, identity):
        require(label(identity), 'INVALID_ARGUMENT')
        key = str(uuid.uuid5(uuid.NAMESPACE_URL, canonical([PROFILE, self.search.scope, principal, identity]).decode()))
        path = self.search.root / ('reclaim-' + key + '.json')
        require(not path.is_symlink(), 'UNAUTHORIZED')
        return path

    def observe(self, plan, identity):
        owner = self.search; self._validate(plan)
        principal = owner.access.authorize(owner.scope, 'maintenance.observeCleanup')
        path = self._path(principal, identity)
        if not path.exists(): return dict(state='absent', identity=identity, plan_sha256=plan['plan_sha256'])
        require(path.stat().st_size <= 1024 * 1024, 'OVERLOADED')
        record = json.loads(path.read_bytes())
        require(record['plan'] == plan and record['principal'] == principal and record['identity'] == identity, 'CONFLICT')
        owner.access.authorize(owner.scope, 'maintenance.observeCleanup')
        return record

    def apply(self, plan, identity):
        owner = self.search; p = self._validate(plan)
        principal = owner.access.authorize(owner.scope, 'maintenance.applyCleanup'); path = self._path(principal, identity)
        with owner._lock():
            if path.exists():
                record = self.observe(plan, identity)
                if record['state'] == 'complete': return record
            else:
                require(len(list(owner.root.glob('reclaim-*.json'))) < LIMITS['plans'], 'OVERLOADED')
                require(self._plan_locked([x['generation'] for x in p['candidates']]) == plan, 'CONFLICT')
                record = dict(profile=PROFILE, principal=principal, identity=identity, plan=plan, state='applying',
                              removed={}, unlink_intent=None, removed_logical_bytes=0, unlinked_allocated_bytes=0,
                              physical_freed_bytes='NOT_ESTABLISHED_WHILE_EXTERNAL_HANDLES_MAY_EXIST',
                              uncertain_unlink_bytes=0, capacity_refund=False)
                publish(path, record); owner.hook('after_cleanup_acceptance')
            for candidate in p['candidates']:
                generation = candidate['generation']
                require(str(uuid.UUID(generation)) == generation, 'INVALID_ARGUMENT')
                directory = owner.root / generation; index = directory / 'index'
                for name, expected in candidate['files'].items():
                    # Names originate from the owner plan and are revalidated even
                    # for a tampered replay. No arbitrary caller path is accepted.
                    relative = Path(name)
                    require(not relative.is_absolute() and '..' not in relative.parts, 'UNAUTHORIZED')
                    owner.access.authorize(owner.scope, 'maintenance.applyCleanup')
                    current, published = self._publication()
                    require(current == p['publication_sha256'] and generation not in published['generations'], 'CONFLICT')
                    require(not directory.is_symlink() and not index.is_symlink(), 'UNAUTHORIZED')
                    require(digest((directory / 'maintenance.json').read_bytes()) == candidate['maintenance_sha256'], 'CONFLICT')
                    require(candidate['original_deadline_ms'] < self.clock(), 'DEADLINE_EXCEEDED')
                    owner._head(owner.scope, candidate['source_head'])
                    key = generation + '/' + name; target = index / relative
                    for parent in target.parents:
                        if parent == owner.root: break
                        require(not parent.is_symlink(), 'UNAUTHORIZED')
                    require(not target.is_symlink(), 'UNAUTHORIZED')
                    if key in record['removed']:
                        require(not target.exists(), 'CONFLICT'); continue
                    if not target.exists():
                        require(record['unlink_intent'] == key, 'CONFLICT')
                        record['uncertain_unlink_bytes'] += expected['bytes']
                        record['removed'][key] = 'ABSENT_AFTER_DURABLE_UNLINK_INTENT'
                    else:
                        require(target.is_file() and target.stat().st_size == expected['bytes'] and
                                digest(target.read_bytes()) == expected['sha256'], 'CONFLICT')
                        record['unlink_intent'] = key; publish(path, record)
                        owner.hook('before_derived_unlink')
                        stat = target.stat(); target.unlink()
                        fd = os.open(target.parent, os.O_DIRECTORY)
                        try: os.fsync(fd)
                        finally: os.close(fd)
                        owner.hook('after_derived_unlink')
                        record['removed'][key] = 'UNLINK_OBSERVED'
                        record['removed_logical_bytes'] += expected['bytes']
                        if stat.st_nlink == 1: record['unlinked_allocated_bytes'] += stat.st_blocks * 512
                    record['unlink_intent'] = None; publish(path, record)
            record['state'] = 'complete'; publish(path, record)
            owner.hook('after_cleanup_capture')
            return self.observe(plan, identity)
