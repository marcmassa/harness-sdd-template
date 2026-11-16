#!/usr/bin/env python3
"""Adapter capability matrix: one data file, one generated document.

`.agents/schemas/capabilities.json` states, per CLI adapter, how each framework
element reaches the CLI and how strongly it is enforced. This module renders
it as docs/compatibility.md and checks that the document has not drifted.
Tests render the adapters and verify the claims. Standard library only.
"""
import argparse
import json
from pathlib import Path
import sys

LIB = Path(__file__).resolve().parent
SOURCE = LIB.parent / 'schemas/capabilities.json'
DOCUMENT = 'docs/compatibility.md'
TITLES = {'instructions': 'Instructions', 'roles': 'Roles', 'commands': 'Commands',
          'edit_permissions': 'Edit permissions', 'lifecycle_hooks': 'Lifecycle hooks',
          'skills': 'Skills'}


def load():
    data = json.loads(SOURCE.read_text(encoding='utf-8'))
    if data.get('format_version') != 1:
        raise ValueError('unsupported capabilities format_version')
    for name, adapter in data['adapters'].items():
        for aspect in data['aspects']:
            entry = adapter.get(aspect)
            if not isinstance(entry, dict) or entry.get('level') not in data['levels'] \
                    or not str(entry.get('detail') or '').strip():
                raise ValueError('{}: {} needs a known level and a detail'.format(name, aspect))
        if not adapter.get('evidence') or not isinstance(adapter.get('unsupported'), list):
            raise ValueError('{}: evidence and unsupported are required'.format(name))
    return data


def render(data=None):
    data = data or load()
    names = list(data['adapters'])
    lines = ['# Adapter compatibility', '',
             '> Generated from `.agents/schemas/capabilities.json` by',
             '> `./.agents/bootstrap.sh capabilities --write`. Edit the JSON, not this file.', '',
             'What each CLI adapter delivers, and how strongly. The matrix separates what a',
             'CLI is configured to do from what an agent is only asked to do.', '',
             '## Enforcement levels', '']
    lines += ['- **{}**: {}'.format(level, text) for level, text in data['levels'].items()]
    lines += ['', '## Matrix', '', '| | ' + ' | '.join('`{}`'.format(name) for name in names) + ' |',
              '|---|' + '---|' * len(names)]
    for aspect in data['aspects']:
        lines.append('| {} | {} |'.format(TITLES[aspect], ' | '.join(
            data['adapters'][name][aspect]['level'] for name in names)))
    for name in names:
        adapter = data['adapters'][name]
        generated = ', '.join('`{}`'.format(path) for path in adapter['generates']) or 'nothing'
        lines += ['', '## `{}`'.format(name), '', 'Generates: {}.'.format(generated), '',
                  '| Element | Level | How |', '|---|---|---|']
        lines += ['| {} | {} | {} |'.format(TITLES[aspect], adapter[aspect]['level'],
                                            adapter[aspect]['detail']) for aspect in data['aspects']]
        lines += ['', 'Not supported: {}.'.format('; '.join(adapter['unsupported'])), '',
                  'Evidence: {}.'.format(', '.join('`{}`'.format(item) for item in adapter['evidence']))]
    lines += ['', '## Controls that do not depend on the CLI', '',
              'These hold for any agent, because a tool applies them rather than the model.', '',
              '| Control | Enforced by | Evidence |', '|---|---|---|']
    lines += ['| {} | {} | `{}` |'.format(item['control'], item['enforced_by'], item['evidence'])
              for item in data['cli_independent_controls']]
    lines += ['', '## Native plugin packaging', '', data['native_plugin_packaging'], '']
    return '\n'.join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', default='.')
    parser.add_argument('--write', action='store_true', help='regenerate docs/compatibility.md')
    parser.add_argument('--check', action='store_true', help='fail if the document has drifted')
    args = parser.parse_args(argv)
    try:
        text = render()
        target = Path(args.root) / DOCUMENT
        if args.write:
            target.write_text(text, encoding='utf-8')
            print('wrote ' + DOCUMENT)
        elif args.check:
            if not target.is_file() or target.read_text(encoding='utf-8') != text:
                raise ValueError('{} is out of date; run ./.agents/bootstrap.sh capabilities --write'
                                 .format(DOCUMENT))
        else:
            print(text)
    except (ValueError, OSError, KeyError) as error:
        print('[FAIL] capabilities: {}'.format(error), file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
