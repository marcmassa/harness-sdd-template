"""Documentation and authored-file contract (T23): size limit, links, and documented commands."""
from pathlib import Path
import re
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
COMMON = ROOT / '.agents/adapters/_common'
MAX_BYTES = 20000
LOCKFILES = ('.lock', 'package-lock.json')
LINK = re.compile(r'(?<!\!)\[[^\]]+\]\(([^)\s]+)\)')
COMMAND = re.compile(r'bootstrap\.sh\s+((?:--)?[a-z][a-z-]*)')


def tracked():
    names = subprocess.run(['git', '-C', str(ROOT), 'ls-files', '-z'], stdout=subprocess.PIPE,
                           check=True).stdout.decode('utf-8').split('\0')
    return [name for name in names if name]


def documents():
    return [name for name in tracked() if name.endswith('.md') and not name.startswith(
        ('progress/', 'specs/', 'examples/'))]


class AuthoredFileLimitTests(unittest.TestCase):
    def test_no_tracked_authored_file_exceeds_the_limit(self):
        oversized = [(name, (ROOT / name).stat().st_size) for name in tracked()
                     if (ROOT / name).is_file() and not name.endswith(LOCKFILES)
                     and (ROOT / name).stat().st_size > MAX_BYTES]
        self.assertEqual(oversized, [])

    def test_navigation_entry_stays_short(self):
        self.assertLessEqual(len((ROOT / 'AGENTS.md').read_text().splitlines()), 120)


class RendererStructureTests(unittest.TestCase):
    def test_entry_point_reexports_the_split_modules(self):
        sys.path.insert(0, str(COMMON))
        try:
            import render
            import render_adapters
            import render_core
        finally:
            sys.path.remove(str(COMMON))
        self.assertIs(render.RENDERERS, render_adapters.RENDERERS)
        self.assertIs(render.load_manifest, render_core.load_manifest)
        for name in ('build_context', 'validate_init', 'export_template', 'profile_project',
                     '_merge_unique_ordered', 'load_soul_content', 'main'):
            self.assertTrue(callable(getattr(render, name)), name)

    def test_modules_do_not_import_the_entry_point(self):
        for module in sorted(COMMON.glob('render_*.py')):
            text = module.read_text()
            self.assertNotRegex(text, r'(?m)^(?:from render import|import render$)', module.name)


class LinkTests(unittest.TestCase):
    def test_relative_links_resolve(self):
        broken = []
        for name in documents():
            base = (ROOT / name).parent
            for target in LINK.findall((ROOT / name).read_text(encoding='utf-8')):
                if re.match(r'^(?:[a-z]+:|#)', target):
                    continue
                path = target.split('#', 1)[0]
                if path and not (base / path).exists():
                    broken.append('{} -> {}'.format(name, target))
        self.assertEqual(broken, [])

    def test_anchors_into_other_documents_exist(self):
        def anchors(path):
            slugs = set()
            for line in path.read_text(encoding='utf-8').splitlines():
                if line.startswith('#'):
                    title = line.lstrip('#').strip().lower()
                    slugs.add(re.sub(r'[^a-z0-9 _-]', '', title).replace(' ', '-'))
            return slugs
        broken = []
        for name in documents():
            base = (ROOT / name).parent
            for target in LINK.findall((ROOT / name).read_text(encoding='utf-8')):
                if re.match(r'^[a-z]+:', target) or '#' not in target:
                    continue
                path, anchor = target.split('#', 1)
                document = (base / path) if path else (ROOT / name)
                if document.suffix == '.md' and document.is_file() and anchor not in anchors(document):
                    broken.append('{} -> {}'.format(name, target))
        self.assertEqual(broken, [])

    def test_contributing_covers_the_required_topics(self):
        text = (ROOT / 'CONTRIBUTING.md').read_text()
        for topic in ('core.hooksPath', 'docs/team-policy.md', 'docs/maintenance.md', 'rollback',
                      '## Releases', 'explicit authorization'):
            self.assertIn(topic, text)
        self.assertIn('CONTRIBUTING.md', (ROOT / 'README.md').read_text())


class DocumentedCommandTests(unittest.TestCase):
    def test_every_documented_bootstrap_command_exists(self):
        script = (ROOT / '.agents/bootstrap.sh').read_text()
        dispatch = script[script.index('case "${1:-help}" in'):]
        known = set(re.findall(r'(?m)^\s{4}([a-z|*-]+|--[a-z|-]+(?:\|[a-z|-]+)*)\)', dispatch))
        names = {part for pattern in known for part in pattern.split('|')}
        sys.path.insert(0, str(COMMON))
        try:
            import render
        finally:
            sys.path.remove(str(COMMON))
        names |= set(render.RENDERERS)
        missing = []
        for name in documents() + ['.agents/bootstrap.sh']:
            for command in COMMAND.findall((ROOT / name).read_text(encoding='utf-8')):
                if command.endswith('-'):
                    continue  # a shell variable completes it (usage text)
                if command in names or (command.startswith('workflow-') and 'workflow-*' in names):
                    continue
                missing.append('{}: {}'.format(name, command))
        self.assertEqual(sorted(set(missing)), [])

    def test_workflow_commands_named_in_docs_are_real(self):
        sys.path.insert(0, str(ROOT / '.agents/lib'))
        try:
            import workflow_cli
        finally:
            sys.path.remove(str(ROOT / '.agents/lib'))
        choices = set()
        for action in workflow_cli.parser()._actions:
            if getattr(action, 'choices', None):
                choices |= set(action.choices)
        named = set()
        for name in documents():
            named |= set(re.findall(r'(?<![\w/-])workflow-([a-z]+(?:-[a-z]+)*)(?![\w.-])',
                                    (ROOT / name).read_text()))
        self.assertTrue(named)
        self.assertEqual(sorted(named - choices), [])


if __name__ == '__main__':
    unittest.main()
