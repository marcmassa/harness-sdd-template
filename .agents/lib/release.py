#!/usr/bin/env python3
"""Pilot report validation and offline release readiness. Standard library only.

`readiness` reads evidence already in the repository and reports what is
missing. It never tags, packages, publishes, or contacts a service. A result of
`ready` only means the evidence is complete: publication stays a separate step
that needs the maintainer's explicit authorization for the concrete artifacts.
"""
import argparse
import json
from pathlib import Path
import re
import sys

import capabilities
import git_state
import inventory

LIB = Path(__file__).resolve().parent
SCHEMA = LIB.parent / 'schemas/release-evidence.json'
PILOTS = 'docs/pilots'
VERSION = re.compile(r'^\d+\.\d+\.\d+$')
TASK = re.compile(r'^\s*-\s*\[(.?)\]\s*\*\*(T(\d+))\*\*')
SPEC_TASKS = 'specs/hybrid-team-stable-release/tasks.md'
# Evidence is recorded after the code it describes, so these paths may differ from the candidate.
EVIDENCE_PATHS = ('releases/', 'progress/', 'docs/pilots/', 'feature_list.json', SPEC_TASKS)
PUBLICATION = ('Publication is not part of readiness. Tagging, packaging, marketplace publication, '
               'and announcements need the maintainer\'s explicit authorization for these artifacts.')


def schema():
    data = json.loads(SCHEMA.read_text(encoding='utf-8'))
    if data.get('format_version') != 1:
        raise ValueError('unsupported release-evidence format_version')
    return data


def _text(value, label):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(label + ' is required')
    return value.strip()


def _load(path, label):
    try:
        return json.loads(Path(path).read_text(encoding='utf-8'))
    except OSError:
        raise ValueError(label + ' not found')
    except ValueError as error:
        raise ValueError('{} is not valid JSON: {}'.format(label, error))


def validate_pilot(report):
    """Raise ValueError unless the report is complete. Returns the report."""
    rules = schema()['pilot']
    if not isinstance(report, dict) or report.get('format_version') != 1:
        raise ValueError('pilot report must be an object with format_version 1')
    identifier = _text(report.get('id'), 'id')
    if not re.match(r'^[a-z0-9][a-z0-9-]{2,40}$', identifier):
        raise ValueError('id must be lowercase letters, digits, and hyphens')
    if report.get('kind') not in rules['kinds']:
        raise ValueError('kind must be real or synthetic')
    if report.get('context') not in rules['contexts']:
        raise ValueError('context must be small-team or team')
    dates = report.get('date_range') or {}
    for edge in ('from', 'to'):
        if not re.match(r'^\d{4}-\d{2}-\d{2}$', str(dates.get(edge))):
            raise ValueError('date_range.{} must be YYYY-MM-DD'.format(edge))
    if dates['from'] > dates['to']:
        raise ValueError('date_range ends before it starts')
    if not inventory.VERSION.match(str(report.get('framework_version'))):
        raise ValueError('framework_version must be MAJOR.MINOR.PATCH')
    _text(report.get('work_summary'), 'work_summary')
    _text(report.get('baseline'), 'baseline')
    _participants(report, rules)
    exercises = report.get('exercises') or {}
    for name in rules['exercises']:
        entry = exercises.get(name)
        if not isinstance(entry, dict) or entry.get('done') is not True:
            raise ValueError('exercise {} was not carried out'.format(name))
        _text(entry.get('notes'), 'exercise {} notes'.format(name))
    metrics = report.get('metrics') or {}
    for name in rules['metrics']:
        value = metrics.get(name)
        if isinstance(value, bool) or not isinstance(value, (int, float)) or value < 0:
            raise ValueError('metric {} must be a non-negative number'.format(name))
    issues = report.get('unresolved_issues')
    if not isinstance(issues, list):
        raise ValueError('unresolved_issues must be a list (empty if none)')
    for issue in issues:
        if not isinstance(issue, dict) or issue.get('severity') not in rules['issue_severities']:
            raise ValueError('each unresolved issue needs a severity')
        _text(issue.get('summary'), 'unresolved issue summary')
    review = report.get('human_review')
    if not isinstance(review, dict) or review.get('reviewed') is not True:
        raise ValueError('the report has not been reviewed by a human')
    _text(review.get('reviewer_role'), 'human_review.reviewer_role')
    _text(review.get('evidence_ref'), 'human_review.evidence_ref')
    return report


def _participants(report, rules):
    participants = report.get('participants')
    if not isinstance(participants, list) or not participants:
        raise ValueError('participants are required')
    humans, agents, tools = 0, 0, set()
    for person in participants:
        if not isinstance(person, dict) or person.get('kind') not in ('human', 'agent'):
            raise ValueError('each participant is a human or an agent')
        _text(person.get('role'), 'participant role')
        if person['kind'] == 'human':
            humans += 1
            if person.get('consent') is not True:
                raise ValueError('every human participant must have given consent')
        else:
            agents += 1
        if person.get('cli') is not None:
            if person['cli'] not in rules['clis']:
                raise ValueError('unknown CLI: {}'.format(person['cli']))
            tools.add(person['cli'])
    if report['context'] == 'small-team' and (humans < 1 or agents < 1):
        raise ValueError('a small-team pilot needs at least one human and one agent')
    if report['context'] == 'team' and (humans < 2 or len(tools) < 2):
        raise ValueError('a team pilot needs at least two humans and two supported CLIs')


def pilot_reports(root):
    """[(file name, report or None, error or None)] for every report file in docs/pilots."""
    folder = Path(root) / PILOTS
    found = []
    for path in sorted(folder.glob('*.json')) if folder.is_dir() else []:
        try:
            found.append((path.name, validate_pilot(_load(path, path.name)), None))
        except ValueError as error:
            found.append((path.name, None, str(error)))
    return found


def _pilot_gaps(root):
    gaps, real = [], {}
    for name, report, error in pilot_reports(root):
        if error:
            gaps.append('pilot report {} is invalid: {}'.format(name, error))
        elif report['kind'] == 'real':
            real.setdefault(report['context'], []).append(report)
    for context in schema()['pilot']['contexts']:
        if not real.get(context):
            gaps.append('no reviewed real pilot report for the {} context'.format(context))
    summaries = [report['work_summary'] for reports in real.values() for report in reports]
    if len(summaries) >= 2 and len(set(summaries)) < len(summaries):
        gaps.append('pilot reports must describe distinct work')
    blockers = ['pilot {}: {}'.format(report['id'], issue['summary'])
                for reports in real.values() for report in reports
                for issue in report['unresolved_issues'] if issue['severity'] == 'blocker']
    return gaps, blockers


def _task_gaps(root):
    path = Path(root) / SPEC_TASKS
    if not path.is_file():
        return ['{} not found'.format(SPEC_TASKS)]
    seen, unchecked = set(), []
    for line in path.read_text(encoding='utf-8').splitlines():
        match = TASK.match(line)
        if match and 1 <= int(match.group(3)) <= 27:
            seen.add(match.group(2))
            if match.group(1) not in ('x', 'X'):
                unchecked.append(match.group(2))
    missing = [task for task in ('T{}'.format(n) for n in range(1, 28)) if task not in seen]
    return ['milestone tasks not found in tasks.md: ' + ', '.join(missing)] if missing else (
        ['milestone tasks not checked: ' + ', '.join(unchecked)] if unchecked else [])


def _evidence(path):
    return any(path == prefix or (prefix.endswith('/') and path.startswith(prefix))
               for prefix in EVIDENCE_PATHS)


def _ci_gaps(root, version, candidate):
    try:
        record = _load(Path(root) / 'releases' / version / 'ci.json', 'releases/{}/ci.json'.format(version))
    except ValueError as error:
        return ['mandatory CI evidence: ' + str(error)]
    gaps = []
    revision = record.get('revision')
    try:
        git_state.require_commit(root, revision, 'CI revision')
        git_state.require_ancestor(root, revision, candidate, 'CI revision')
        later = [path for path in git_state.changed_paths(root, revision, candidate)
                 if not _evidence(path)]
        if later:
            gaps.append('code changed after the CI run ({}): {}'.format(
                revision[:12], ', '.join(sorted(later)[:5])))
    except ValueError as error:
        gaps.append('CI evidence: {}'.format(error))
    results = record.get('results') or {}
    for combination in schema()['release']['ci_matrix']:
        if results.get(combination) != 'success':
            gaps.append('CI did not succeed on ' + combination)
    if not str(record.get('run_reference') or '').strip():
        gaps.append('CI evidence names no run')
    return gaps


def _matrix_gaps(root):
    try:
        text = capabilities.render()
        path = Path(root) / capabilities.DOCUMENT
        if not path.is_file() or path.read_text(encoding='utf-8') != text:
            return ['compatibility matrix document is out of date']
    except (ValueError, OSError, KeyError) as error:
        return ['compatibility matrix is invalid: {}'.format(error)]
    return []


def _defect_blockers(root, version):
    """Open defects in a blocking category block the release, whatever severity they are given."""
    path = Path(root) / 'releases' / version / 'defects.json'
    if not path.is_file():
        return [], []
    rules = schema()['release']
    gaps, blockers = [], []
    defects = _load(path, 'releases/{}/defects.json'.format(version))
    for defect in defects if isinstance(defects, list) else [None]:
        if not isinstance(defect, dict) or defect.get('status') not in rules['defect_statuses'] \
                or not str(defect.get('summary') or '').strip() \
                or defect.get('category') not in list(rules['blocker_categories']) + ['other']:
            gaps.append('defects.json has a malformed entry')
            continue
        if defect['status'] == 'open' and defect['category'] != 'other':
            blockers.append('{} ({})'.format(defect['summary'], defect['category']))
        if defect['status'] == 'resolved' and not str(defect.get('disposition') or '').strip():
            gaps.append('resolved defect without a disposition: ' + defect['summary'])
    return gaps, blockers


def readiness(root, version):
    """Return the readiness report for a version. Reads only."""
    root = Path(root).resolve()
    if not VERSION.match(str(version)):
        raise ValueError('version must be MAJOR.MINOR.PATCH')
    candidate = git_state.head(root)
    missing = _task_gaps(root) + _ci_gaps(root, version, candidate) + _matrix_gaps(root)
    pilot_gaps, pilot_blockers = _pilot_gaps(root)
    defect_gaps, defect_blockers = _defect_blockers(root, version)
    missing += pilot_gaps + defect_gaps
    blockers = pilot_blockers + defect_blockers
    missing += ['unresolved release blocker: ' + item for item in blockers]
    dirty = [path for path in git_state.candidate_paths_dirty(root) if not _evidence(path)]
    if dirty:
        missing.append('uncommitted changes outside evidence paths: ' + ', '.join(sorted(dirty)[:5]))
    return {'format_version': 1, 'version': version, 'candidate': candidate,
            'framework_version': inventory.declared()['framework_version'],
            'status': 'ready' if not missing else 'release-candidate', 'missing': missing,
            'unresolved_blockers': len(blockers), 'publication': PUBLICATION}


def render(report):
    lines = ['release {} — {}'.format(report['version'], report['status']),
             'candidate {}'.format(report['candidate'])]
    lines += ['  missing: ' + item for item in report['missing']]
    lines.append(report['publication'])
    return '\n'.join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', default='.')
    sub = parser.add_subparsers(dest='command', required=True)
    pilot = sub.add_parser('pilot')
    pilot.add_argument('file')
    ready = sub.add_parser('readiness')
    ready.add_argument('version')
    ready.add_argument('--write', action='store_true', help='also write releases/<version>/readiness.json')
    args = parser.parse_args(argv)
    try:
        if args.command == 'pilot':
            report = validate_pilot(_load(args.file, args.file))
            counted = 'counts as a real pilot' if report['kind'] == 'real' else \
                'synthetic: valid, but never counts as a real pilot'
            print('pilot {} ({}): {}'.format(report['id'], report['context'], counted))
            return 0
        report = readiness(args.root, args.version)
        print(render(report))
        if args.write:
            target = Path(args.root) / 'releases' / args.version / 'readiness.json'
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(json.dumps(report, indent=2, sort_keys=True) + '\n', encoding='utf-8')
        return 0 if report['status'] == 'ready' else 1
    except (ValueError, OSError, KeyError) as error:
        print('[FAIL] release: {}'.format(error), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
