"""Run the installed directory outside the repository, using no model service."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
import zipfile
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
ABC = 'X:1\nT:中文旋律\nM:4/4\nL:1/4\nK:C\nC D E F | G A B c |\n'
LY = '\\version "2.26.0"\n\\score { \\new Staff { \\time 4/4 c\'4 d\' e\' f\' | g\' a\' b\' c\'\' | } \\layout {} \\midi {} }\n'


def binary(name):
    value = os.environ.get(name.upper() + '_PATH') or name
    return shutil.which(value)


class SkillTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Managed Windows sandboxes can deny writes and cleanup in the system
        # temp directory. Keep the test sandbox inside the writable checkout.
        cls.temp = tempfile.TemporaryDirectory(prefix='.opusloom-test-', dir=ROOT.parent)
        cls.outside = Path(cls.temp.name)
        cls.skill = cls.outside / '独立 skill'
        shutil.copytree(ROOT, cls.skill, ignore=shutil.ignore_patterns('__pycache__', '*.pyc', '.work', 'dist', '.git', '.obsidian'))
        cls.scripts = cls.skill / 'scripts'
        tools = ROOT.parent / '.tools' / 'lilypond-2.26.0' / 'lilypond-2.26.0' / 'bin'
        cls.env = os.environ.copy()
        if (tools / 'convert-ly.py').is_file() and (tools / 'lilypond.exe').is_file():
            cls.env['CONVERT_LY_PATH'] = str(tools / 'convert-ly.py')
            cls.env['LILYPOND_PATH'] = str(tools / 'lilypond.exe')

    @classmethod
    def tearDownClass(cls):
        for attempt in range(10):
            try:
                cls.temp.cleanup()
                break
            except PermissionError:
                if attempt == 9:
                    raise
                time.sleep(0.2)

    def setUp(self):
        self.workspace = Path(tempfile.mkdtemp(prefix='作品-', dir=self.outside))
        baseline = type(self).skill
        self.skill = self.workspace / 'isolated-skill'
        shutil.copytree(baseline, self.skill)
        self.scripts = self.skill / 'scripts'

    def call(self, script, *args, success=True, timeout=180):
        result = subprocess.run([sys.executable, '-B', str(self.scripts / script), *map(str, args)],
                                cwd=self.workspace, capture_output=True, timeout=timeout, env=self.env)
        try:
            data = json.loads(result.stdout)
        except ValueError:
            self.fail(f'not JSON: {result.stdout!r} {result.stderr!r}')
        self.assertEqual(result.returncode == 0, success, data)
        return data

    def compile(self, source=ABC, suffix='.abc', **kwargs):
        path = self.workspace / ('中文 乐谱' + suffix)
        path.write_text(source, encoding='utf-8')
        flags = []
        for key, value in kwargs.items():
            flags.extend(['--' + key.replace('_', '-'), str(value)])
        report = self.call('compile_score.py', '--source', path, '--output-dir', self.workspace / '输出', *flags)
        self.assertEqual(path.read_text(encoding='utf-8'), source)
        return path, report

    def analysis(self, path, report, *flags, success=True):
        return self.call('analyze_score.py', '--source', path, '--compile-report', report['report_path'],
                         '--meter', '4/4', '--first', 1, '--last', 2, *flags, success=success)

    def require_abc(self):
        if not binary('abc2midi') or not binary('abc2abc'):
            self.skipTest('real abc2midi and abc2abc required')

    def require_analysis(self):
        if not importlib.util.find_spec('music21'):
            self.skipTest('music21 required')

    def require_lily(self):
        if not binary('lilypond'):
            self.skipTest('real LilyPond required')

    def test_skill_metadata_links_and_no_framework_dependencies(self):
        body = (self.skill / 'SKILL.md').read_text(encoding='utf-8')
        self.assertRegex(body, r'\A---\nname: abc-lily-composer\ndescription: .+\n---')
        # Check the actual installed payload. Developer documentation such as
        # AGENT.md can intentionally link to research elsewhere in the repo.
        archive = self.workspace / 'runtime.zip'
        self.call('package_skill.py', '--output', archive)
        installed = self.workspace / 'installed'
        with zipfile.ZipFile(archive) as package:
            package.extractall(installed)
        runtime = installed / 'abc-lily-composer'
        self.assertFalse((runtime / 'AGENT.md').exists())
        self.assertFalse((runtime / 'references-origin').exists())
        for doc in runtime.rglob('*.md'):
            for target in re.findall(r'\]\(([^)]+)\)', doc.read_text(encoding='utf-8')):
                parsed = urlsplit(target)
                if not parsed.scheme and parsed.path:
                    self.assertTrue((doc.parent / unquote(parsed.path)).is_file(), (doc, target))
        for phrase in ('只读审稿', '重新编译', '待复核', '自审', 'diff'):
            self.assertIn(phrase, body)
        scripts = '\n'.join(p.read_text(encoding='utf-8') for p in self.scripts.glob('*.py'))
        self.assertNotIn('opusloom_agent', scripts)
        self.assertNotIn('pi-base-agent', scripts)
        self.assertNotIn('api_key', scripts)






    def test_help_outside_repository(self):
        for script in ('check_environment.py', 'compile_score.py', 'analyze_score.py'):
            result = subprocess.run([sys.executable, '-B', str(self.scripts / script), '--help'],
                                    cwd=self.workspace, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn(b'usage:', result.stdout)

    def test_environment_missing_explicit_tool(self):
        data = self.call('check_environment.py', '--format', 'lilypond', '--lilypond',
                         self.workspace / 'missing-executable', success=False)
        self.assertFalse(data['tools']['lilypond']['available'])
        self.assertEqual(data['status'], 'missing_dependencies')

    def test_missing_compiler_report(self):
        path = self.workspace / 'score.ly'
        path.write_text(LY, encoding='utf-8')
        data = self.call('compile_score.py', '--source', path, '--output-dir', self.workspace / 'out',
                         '--lilypond', self.workspace / 'missing', success=False)
        self.assertTrue(Path(data['report_path']).is_file())
        self.assertEqual(data['artifacts'], [])

    def test_invalid_source_and_timeout_input(self):
        path = self.workspace / 'score.abc'
        path.write_text('', encoding='utf-8')
        self.call('compile_score.py', '--source', path, '--output-dir', self.workspace / 'out', success=False)
        path.write_text(ABC, encoding='utf-8')
        data = self.call('compile_score.py', '--source', path, '--output-dir', self.workspace / 'out',
                         '--timeout', 'nan', success=False)
        self.assertIn('finite', str(data))

    def test_abc_unicode_multitune_and_selection(self):
        self.require_abc()
        path, report = self.compile(ABC + ABC.replace('X:1', 'X:2').replace('C D E F', 'G A B c'))
        self.assertEqual(len(report['artifacts']), 2)
        self.assertEqual(len(report['units']), 2)
        self.assertEqual(report['source_hash'], hashlib.sha256(path.read_bytes()).hexdigest())
        self.require_analysis()
        facts = self.analysis(path, report, '--movement', 2, '--kind', 'notes')
        self.assertEqual(facts['notes'][0]['pitch'], 67)

    def test_abc_analysis_paging_and_candidates(self):
        self.require_abc()
        self.require_analysis()
        path, report = self.compile()
        first = self.analysis(path, report, '--kind', 'notes', '--limit', 3)
        second = self.analysis(path, report, '--kind', 'notes', '--limit', 20, '--offset', first['next_offset'])
        self.assertEqual(len(first['notes']) + len(second['notes']), 8)
        self.assertEqual(first['notes'][0]['pitch'], 60)
        self.assertEqual(first['duration_quarters'], 8)
        self.assertIn('native_abc', first)
        for kind in ('overview', 'harmony', 'voice_leading'):
            facts = self.analysis(path, report, '--kind', kind)
            self.assertEqual(facts['status'], 'available')
            self.assertIn('limitations', facts)

    def test_stale_source_then_recompile(self):
        self.require_abc()
        self.require_analysis()
        path, report = self.compile()
        path.write_text(ABC.replace('C D E F', 'D E F G'), encoding='utf-8')
        data = self.analysis(path, report, success=False)
        self.assertIn('stale', data['error'])
        updated = self.call('compile_score.py', '--source', path, '--output-dir', self.workspace / '输出')
        self.assertNotEqual(report['report_path'], updated['report_path'])
        self.assertEqual(self.analysis(path, updated, '--kind', 'notes')['notes'][0]['pitch'], 62)

    def test_artifact_tamper_and_missing(self):
        self.require_abc()
        self.require_analysis()
        path, report = self.compile()
        artifact = Path(report['report_path']).parent / report['artifacts'][0]['name']
        original = artifact.read_bytes()
        artifact.write_bytes(original + b'bad')
        self.assertIn('hash mismatch', self.analysis(path, report, success=False)['error'])
        artifact.unlink()
        self.analysis(path, report, success=False)

    def test_abc_invalid_notation(self):
        self.require_abc()
        path = self.workspace / 'bad.abc'
        path.write_text('X:1\nM:4/4\nL:1/4\nK:C\nC D E F | C D E F G A B | C D E F |\n', encoding='utf-8')
        report = self.call('compile_score.py', '--source', path, '--output-dir', self.workspace / 'out', success=False)
        self.assertTrue(report['diagnostics'])

    def test_echoed_title_is_not_a_diagnostic(self):
        self.require_abc()
        _, report = self.compile(ABC.replace('中文旋律', 'An error and warning in the title'))
        self.assertEqual(report['diagnostics'], [])

    def test_multiple_lily_midi_selection(self):
        self.require_lily()
        self.require_analysis()
        path, report = self.compile(LY + LY.split('\n', 1)[1], '.ly')
        midis = [a['name'] for a in report['artifacts'] if Path(a['name']).suffix in {'.mid', '.midi'}]
        self.assertEqual(len(midis), 2)
        self.assertIn('select', self.analysis(path, report, success=False)['error'])
        for index, name in enumerate(midis, 1):
            facts = self.analysis(path, report, '--artifact', name, '--movement', index)
            self.assertEqual(facts['artifact'], name)

    def test_lily_pdf_midi_and_unknown_spelling(self):
        self.require_lily()
        path, report = self.compile(LY, '.ly', require='midi')
        suffixes = {Path(a['name']).suffix for a in report['artifacts']}
        self.assertIn('.pdf', suffixes)
        self.assertTrue(suffixes & {'.mid', '.midi'})
        self.require_analysis()
        facts = self.analysis(path, report, '--kind', 'notes')
        self.assertTrue(facts['pitch_spelling'].startswith('unknown'))
        self.assertTrue(all(n['spelling'] is None for n in facts['notes']))
        self.assertTrue(any('tracks' in s for s in facts['limitations']))

    def test_lily_invalid_and_no_stale_artifacts(self):
        self.require_lily()
        path, report = self.compile(LY, '.ly')
        path.write_text('\\version "2.26.0"\n\\score { \\undefinedMusic }', encoding='utf-8')
        failed = self.call('compile_score.py', '--source', path, '--output-dir', self.workspace / '输出', success=False)
        self.assertNotEqual(failed['report_path'], report['report_path'])
        self.assertTrue(any(d['severity'] == 'error' for d in failed['diagnostics']))

    def test_required_output_missing(self):
        self.require_abc()
        path = self.workspace / 'score.abc'
        path.write_text(ABC, encoding='utf-8')
        data = self.call('compile_score.py', '--source', path, '--output-dir', self.workspace / 'out',
                         '--require', 'pdf', success=False)
        self.assertIn('pdf', data['missing_artifacts'])

    def test_real_compiler_timeout(self):
        self.require_lily()
        path = self.workspace / 'score.ly'
        path.write_text(LY, encoding='utf-8')
        report = self.call('compile_score.py', '--source', path, '--output-dir', self.workspace / 'out',
                           '--timeout', '0.000001', success=False)
        self.assertIn('timed_out', str(report))

    def test_variable_meter_is_not_mislocated(self):
        self.require_lily()
        self.require_analysis()
        source = LY.replace("c'4 d' e' f' | g' a' b' c'' |", "c'1 | \\time 3/4 d'2. |")
        path, report = self.compile(source, '.ly')
        data = self.analysis(path, report, success=False)
        self.assertIn('meter', data['error'])

    def test_pickup_positions(self):
        self.require_abc()
        self.require_analysis()
        path, report = self.compile('X:1\nM:4/4\nL:1/4\nK:C\nG | C D E F | G A B c |\n')
        facts = self.analysis(path, report, '--first', 0, '--pickup', 1, '--kind', 'notes')
        self.assertEqual(facts['notes'][0]['measure'], 0)
        self.assertEqual(facts['notes'][1]['measure'], 1)


if __name__ == '__main__':
    unittest.main()
