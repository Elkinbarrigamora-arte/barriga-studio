"""Pruebas del coordinador local; no requiere ejecutar un modelo ni conectarse a Internet."""
from pathlib import Path
from io import BytesIO
import json
from urllib.error import HTTPError
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import agente_desarrollo as agent


class AgenteDesarrolloTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / 'index.html').write_text(
            '<html><body><textarea id="script"></textarea>'
            '<div id="projectList"></div></body></html>', encoding='utf-8')
        self.git('init', '-b', 'main')
        self.git('config', 'user.name', 'Barriga Test')
        self.git('config', 'user.email', 'test@example.invalid')
        self.git('add', '.')
        self.git('commit', '-m', 'test base')

    def git(self, *args):
        p = subprocess.run(['git', *args], cwd=self.root,
                           capture_output=True, text=True, check=True)
        return p.stdout.strip()

    def test_denies_escape_and_protected_agent(self):
        for path in ('../secreto.txt', '/tmp/secreto', 'tools/agente_desarrollo.py',
                     '.git/config', 'borradores/privado.json'):
            with self.subTest(path=path):
                with self.assertRaises(ValueError):
                    agent.guard_path(self.root, path)

    def test_patch_must_match_once(self):
        (self.root / 'assets').mkdir()
        (self.root / 'assets' / 'a.js').write_text('let a=1; let a=1;')
        with self.assertRaises(ValueError):
            agent.plan_changes(self.root, [
                {'ruta': 'assets/a.js', 'buscar': 'let a=1', 'reemplazar': 'let a=2'}])

    def test_sequential_patches_to_same_existing_file(self):
        before = (self.root / 'index.html').read_text(encoding='utf-8')
        changes = [
            {'ruta': 'index.html', 'buscar': '</body>',
             'reemplazar': '<script src="assets/proyectos.js"></script></body>'},
            {'ruta': 'index.html', 'buscar': '<textarea id="script"></textarea>',
             'reemplazar': '<textarea id="script" data-autosave="1"></textarea>'}
        ]
        planned = agent.plan_changes(self.root, changes)
        self.assertIn('data-autosave="1"', planned['index.html'])
        self.assertIn('src="assets/proyectos.js"', planned['index.html'])
        self.assertEqual((self.root / 'index.html').read_text(encoding='utf-8'), before)

    def test_repeated_new_file_is_rejected(self):
        changes = [
            {'ruta': 'assets/proyectos.js', 'contenido': 'let a = 1;'},
            {'ruta': 'assets/proyectos.js', 'contenido': 'let b = 2;'}
        ]
        with self.assertRaisesRegex(ValueError, 'Archivo nuevo repetido'):
            agent.plan_changes(self.root, changes)

    def test_repeated_patch_requires_exact_match_after_previous_patch(self):
        changes = [
            {'ruta': 'index.html', 'buscar': '</body>', 'reemplazar': '</main></body>'},
            {'ruta': 'index.html', 'buscar': '</body>', 'reemplazar': '</footer></body>'},
        ]
        planned = agent.plan_changes(self.root, changes)
        self.assertIn('</main></footer></body>', planned['index.html'])

    def test_ollama_http_500_retries_before_succeeding(self):
        first_error = HTTPError('http://127.0.0.1:11434/api/generate',
                                500, 'Internal Server Error', {}, BytesIO(b'overloaded'))
        model_response = {'response': json.dumps({
            'resumen': 'ok',
            'cambios': [{'ruta': 'assets/nuevo.js', 'contenido': 'console.log(1);'}]
        })}
        successful_response = BytesIO(json.dumps(model_response).encode('utf-8'))
        with patch.object(agent, 'urlopen',
                          side_effect=[first_error, successful_response]) as mocked, \
             patch.object(agent.time, 'sleep') as waiting:
            result = agent.ask_model('crear modulo', 'ARCHIVO index.html', 'modelo-local')
        self.assertEqual(result['resumen'], 'ok')
        self.assertEqual(mocked.call_count, 2)
        waiting.assert_called_once_with(2)

    @unittest.skipUnless(__import__('shutil').which('node'), 'Node.js necesario para validar JS')
    def test_success_creates_backup_and_commit(self):
        output = {'cambios': [
            {'ruta': 'assets/editorial.js', 'contenido': 'console.log("hola");'},
            {'ruta': 'index.html', 'buscar': '</body>',
             'reemplazar': '<script src="assets/editorial.js"></script></body>'}]}
        with patch.object(agent, 'ask_model', return_value=output):
            agent.run_stage(self.root, '01_guion', 'editorial', 'modelo-local')
        self.assertEqual(self.git('log', '-1', '--format=%s'), 'Barriga IA: 01_guion')
        self.assertIn('assets/editorial.js', (self.root / 'index.html').read_text())
        self.assertTrue(any(b.startswith('backup/barriga-ia-') for b in
                            self.git('branch', '--list').replace('* ', '').splitlines()))

    @unittest.skipUnless(__import__('shutil').which('node'), 'Node.js necesario para validar JS')
    def test_retries_invalid_js_then_commits_valid_patch(self):
        bad = {'cambios': [
            {'ruta': 'assets/proyectos-core.js', 'contenido': 'const x = `<div class='},
            {'ruta': 'index.html', 'buscar': '</body>',
             'reemplazar': '<script src="assets/proyectos-core.js"></script></body>'}
        ]}
        good = {'cambios': [
            {'ruta': 'assets/proyectos-core.js', 'contenido': 'window.BarrigaProyectos = {};'},
            {'ruta': 'index.html', 'buscar': '</body>',
             'reemplazar': '<script src="assets/proyectos-core.js"></script></body>'}
        ]}
        with patch.object(agent, 'ask_model', side_effect=[bad, good]) as mocked:
            self.assertTrue(agent.run_stage(self.root, '03_proyectos',
                                            'guardar proyectos', 'modelo-local'))
        self.assertEqual(mocked.call_count, 2)
        self.assertEqual(self.git('status', '--porcelain'), '')
        self.assertEqual(self.git('log', '-1', '--format=%s'),
                         'Barriga IA: 03_proyectos')
        self.assertEqual((self.root / 'assets/proyectos-core.js').read_text(),
                         'window.BarrigaProyectos = {};')

    @unittest.skipUnless(__import__('shutil').which('node'), 'Node.js necesario para validar JS')
    def test_failed_js_does_not_modify_existing_files(self):
        before = (self.root / 'index.html').read_text(encoding='utf-8')
        output = {'cambios': [
            {'ruta': 'assets/defectuoso.js', 'contenido': 'function x( {'},
            {'ruta': 'index.html', 'buscar': '</body>',
             'reemplazar': '<script src="assets/defectuoso.js"></script></body>'}]}
        with patch.object(agent, 'ask_model', return_value=output):
            with self.assertRaises(RuntimeError):
                agent.run_stage(self.root, '01_guion', 'editorial', 'modelo-local')
        self.assertEqual(before, (self.root / 'index.html').read_text(encoding='utf-8'))
        self.assertFalse((self.root / 'assets/defectuoso.js').exists())
        self.assertEqual(self.git('status', '--porcelain'), '')


if __name__ == '__main__':
    unittest.main()
