"""Work ownership rules: claims, dependencies, and handoff integrity. Read-only.

A work record names one owner, through a claim with its own identifier. Tracked
records make conflicting ownership visible in Git when clones meet; they are
not a distributed lock, and nothing here prevents two clones from working
offline on the same feature. This module only validates; handoffs.py changes
state.
"""
import hashlib
import os
import re

import git_state
import safe_fs
from workflow_store import read_state_json

WORK = 'progress/work'
HANDOFFS = 'progress/handoffs'
ACTIVE = ('spec_ready', 'in_progress', 'blocked')
CLAIM_ID = re.compile(r'^[0-9a-f]{16}$')
DIGEST = re.compile(r'^[0-9a-f]{64}$')
HANDOFF_KINDS = ('handoff', 'migrated-session')


def new_claim(owner, revision):
    return {'id': os.urandom(8).hex(), 'owner': owner, 'revision': revision}


def load_records(root):
    """{feature_id: record} for every regular record file; malformed ones are refused."""
    records = {}
    for name, kind in safe_fs.list_directory(root, WORK):
        if name.startswith('.') or not name.endswith('.json'):
            continue
        if kind != 'file':
            raise ValueError('{}/{} must be a regular file'.format(WORK, name))
        _text, record = read_state_json(root, '{}/{}'.format(WORK, name))
        if not isinstance(record, dict) or not isinstance(record.get('feature_id'), str):
            raise ValueError('{}/{} is not a work record'.format(WORK, name))
        if record['feature_id'] in records:
            raise ValueError('two work records claim ' + record['feature_id'])
        records[record['feature_id']] = record
    return records


def check_dependencies(feature_ids, feature_id, dependencies):
    if not isinstance(dependencies, list) or not all(isinstance(item, str) for item in dependencies):
        raise ValueError('{}: dependencies must be a list of feature ids'.format(feature_id))
    if len(set(dependencies)) != len(dependencies):
        raise ValueError('{}: a dependency is listed twice'.format(feature_id))
    for dependency in dependencies:
        if dependency == feature_id:
            raise ValueError('{} cannot depend on itself'.format(feature_id))
        if dependency not in feature_ids:
            raise ValueError('{} depends on unknown feature {}'.format(feature_id, dependency))


def check_cycles(records):
    """Refuse a dependency cycle among recorded features, naming the path."""
    state = {}

    def visit(feature_id, path):
        if state.get(feature_id) == 'done':
            return
        if state.get(feature_id) == 'open':
            cycle = path[path.index(feature_id):] + [feature_id]
            raise ValueError('dependency cycle: ' + ' -> '.join(cycle))
        state[feature_id] = 'open'
        for dependency in records.get(feature_id, {}).get('dependencies') or []:
            if dependency in records:
                visit(dependency, path + [feature_id])
        state[feature_id] = 'done'

    for feature_id in sorted(records):
        visit(feature_id, [])


def check_workspace_conflicts(records):
    """Two features in progress must not share a branch or a worktree."""
    for field in ('branch', 'worktree'):
        seen = {}
        for feature_id in sorted(records):
            record = records[feature_id]
            value = record.get(field)
            if record.get('status') != 'in_progress' or not value:
                continue
            if value in seen:
                raise ValueError('{} and {} are both in progress on {} {!r}; concurrent work needs '
                                 'separate branches or worktrees'.format(seen[value], feature_id,
                                                                         field, value))
            seen[value] = feature_id


def check_start(root, feature, record, feature_data):
    """Gate for moving one feature to in_progress, against the other records on disk."""
    records = load_records(root)
    records[feature['id']] = dict(record, status='in_progress')
    feature_ids = {item.get('id') for item in (feature_data or {}).get('features', [])}
    check_dependencies(feature_ids, feature['id'], record.get('dependencies'))
    check_cycles(records)
    check_workspace_conflicts(records)


def _check_claim(feature_id, record):
    claim = record.get('claim')
    if claim is None:
        return None  # a record created before claims existed: the owner field alone stands
    if not isinstance(claim, dict) or not CLAIM_ID.match(str(claim.get('id'))):
        raise ValueError('{}: claim is malformed'.format(feature_id))
    if claim.get('owner') != record.get('owner'):
        raise ValueError('{}: claim owner {!r} differs from record owner {!r}; ownership changes '
                         'only through a handoff or an authorized reassignment'.format(
                             feature_id, claim.get('owner'), record.get('owner')))
    for event in record.get('claim_history') or []:
        if not isinstance(event, dict) or event.get('event') not in ('reassigned', 'handoff-resumed') \
                or not isinstance(event.get('previous'), dict):
            raise ValueError('{}: claim_history entry is malformed'.format(feature_id))
    return claim['id']


def handoff_pointers(record):
    """Latest pointer first, then history; a legacy string pointer is ignored."""
    pointers = [record['handoff']] if isinstance(record.get('handoff'), dict) else []
    return pointers + [item for item in record.get('handoff_history') or []]


def verify_handoff(root, feature_name, pointer):
    """A handoff file is immutable: it must still hash to what its pointer recorded."""
    if not isinstance(pointer, dict) or pointer.get('kind') not in HANDOFF_KINDS \
            or not DIGEST.match(str(pointer.get('sha256'))) \
            or not git_state.OBJECT_ID.match(str(pointer.get('revision'))):
        raise ValueError('{}: handoff pointer is malformed'.format(feature_name))
    expected = '{}/{}/{}.md'.format(HANDOFFS, feature_name, pointer.get('id'))
    if pointer.get('path') != expected or not re.match(r'^\d{3}$', str(pointer.get('id'))):
        raise ValueError('{}: handoff path must be {}'.format(feature_name, expected))
    content = safe_fs.read_bytes(root, expected)
    if content is None:
        raise ValueError('{}: handoff {} is missing; handoffs are immutable records'.format(
            feature_name, expected))
    if hashlib.sha256(content).hexdigest() != pointer['sha256']:
        raise ValueError('{}: handoff {} was modified after it was recorded'.format(
            feature_name, expected))
    return content


def validate_repository(root, data, records):
    """Merge-time validation over every record: run by check.sh through workflow-check."""
    features = {item.get('id'): item for item in data.get('features', [])}
    claims = {}
    for feature_id in sorted(records):
        record = records[feature_id]
        claim_id = _check_claim(feature_id, record)
        if claim_id in claims:
            raise ValueError('{} and {} carry the same claim id; one record was copied'.format(
                claims[claim_id], feature_id))
        if claim_id:
            claims[claim_id] = feature_id
        check_dependencies(set(features), feature_id, record.get('dependencies'))
        name = features[feature_id].get('name') if feature_id in features else None
        referenced = set()
        for pointer in handoff_pointers(record):
            verify_handoff(root, name, pointer)
            referenced.add(pointer['id'] + '.md')
        for entry, kind in safe_fs.list_directory(root, '{}/{}'.format(HANDOFFS, name)):
            if kind != 'file' or entry not in referenced:
                raise ValueError('{}: {}/{}/{} is not referenced by the work record'.format(
                    feature_id, HANDOFFS, name, entry))
    check_cycles(records)
    check_workspace_conflicts(records)
