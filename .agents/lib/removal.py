#!/usr/bin/env python3
"""Remove the framework from an installed project, by inventory.

Only framework-owned files that still equal their installed baseline are
removed. A file the project changed, a project-owned (seed) file, and anything
the inventory does not list are kept and reported. Git configuration, hooks
configuration, and generated adapters are not touched: remove adapters first
with `bootstrap.sh clean --all`. Every removed file is backed up, and
`update-restore` puts it back. Standard library only.
"""
import hashlib
import json
from pathlib import Path
import shutil

import inventory
from inventory import INVENTORY
from update import BACKUPS, _blocked, _copy, _journal_state, _state, _write_json


def plan_removal(root):
    """What a removal would do. Reads only."""
    root = Path(root).resolve()
    document = inventory.load(root)
    if document is None:
        raise ValueError('the project has no {}; nothing is known to be framework-owned'
                         .format(INVENTORY))
    base = root / BACKUPS
    if base.is_dir() and not base.is_symlink() and any(
            _journal_state(folder) == 'started' for folder in base.iterdir()):
        raise ValueError('an interrupted update must be restored first (update-restore)')
    actions = []
    for relative, entry in sorted(document['files'].items()):
        current, blocked = _state(root, relative)
        if blocked:
            action, reason = 'keep', blocked
        elif entry['ownership'] == 'seed':
            action, reason = 'keep', 'project-owned'
        elif current is None:
            action, reason = 'gone', 'already absent'
        elif entry['sha256'] is None:
            action, reason = 'keep', 'uncertain baseline (legacy adoption)'
        elif current != entry['sha256']:
            action, reason = 'keep', 'changed locally'
        else:
            action, reason = 'remove', 'unchanged since install'
        actions.append({'path': relative, 'action': action, 'reason': reason, 'current': current})
    body = {'framework_version': document['framework_version'], 'actions': actions}
    body['plan_digest'] = hashlib.sha256(
        json.dumps(body, sort_keys=True).encode('utf-8')).hexdigest()
    return body


def apply_removal(root, plan_digest):
    """Remove exactly what the reviewed plan listed, after backing it up."""
    root = Path(root).resolve()
    plan = plan_removal(root)
    if plan['plan_digest'] != plan_digest:
        raise ValueError('the project changed since the removal plan was reviewed; run '
                         'update-remove again')
    if _blocked(root, BACKUPS + '/x'):
        raise ValueError('.harness must not contain symlinks')
    identifier = 'remove-' + plan_digest[:12]
    folder = root / BACKUPS / identifier
    if folder.exists():
        raise ValueError('removal {} was already applied'.format(identifier))
    work = [item for item in plan['actions'] if item['action'] == 'remove']
    folder.mkdir(parents=True)
    shutil.copy2(str(root / INVENTORY), str(folder / 'installed.json'))
    for item in work:
        _copy(root / item['path'], folder / 'before' / item['path'])
    journal = {'id': identifier, 'state': 'started', 'from': plan['framework_version'],
               'to': 'removed', 'conflicts': [],
               'actions': [{'path': item['path'], 'action': 'remove', 'before': item['current'],
                            'after': None} for item in work]}
    _write_json(folder / 'journal.json', journal)
    document = inventory.load(root)
    for item in work:
        current, blocked = _state(root, item['path'])
        if blocked or current != item['current']:
            raise ValueError('{} changed after planning; nothing more was removed'.format(item['path']))
        (root / item['path']).unlink()
        document['files'].pop(item['path'], None)
        _prune_empty_parents(root, item['path'])
    for item in plan['actions']:
        if item['action'] == 'gone':
            document['files'].pop(item['path'], None)
    document['removed'] = identifier
    _write_json(root / INVENTORY, document)
    journal['state'] = 'complete'
    _write_json(folder / 'journal.json', journal)
    kept = [item for item in plan['actions'] if item['action'] == 'keep']
    return {'removed': len(work), 'kept': [{'path': item['path'], 'reason': item['reason']}
                                           for item in kept],
            'backup': '{}/{}'.format(BACKUPS, identifier)}


def _prune_empty_parents(root, relative):
    """Remove directories the removal left empty, never the root or .harness."""
    folder = (root / relative).parent
    while folder != root and root in folder.parents and folder.name != '.harness':
        cache = folder / '__pycache__'
        # An interpreter cache is the only thing the framework leaves behind at run time.
        if cache.is_dir() and not cache.is_symlink() and [p.name for p in folder.iterdir()] == ['__pycache__']:
            shutil.rmtree(str(cache), ignore_errors=True)
        try:
            folder.rmdir()
        except OSError:
            return
        folder = folder.parent


def render_plan(plan):
    counts = {}
    lines = ['remove framework {}'.format(plan['framework_version'])]
    for item in plan['actions']:
        counts[item['action']] = counts.get(item['action'], 0) + 1
        if item['action'] == 'keep' and item['reason'] != 'project-owned':
            lines.append('  keep     {}  ({})'.format(item['path'], item['reason']))
    lines.append('summary: ' + ', '.join('{} {}'.format(counts[name], name) for name in sorted(counts)))
    lines.append('Project-owned files, files changed locally, and anything outside the inventory stay.')
    lines.append('plan digest: ' + plan['plan_digest'])
    return '\n'.join(lines)
