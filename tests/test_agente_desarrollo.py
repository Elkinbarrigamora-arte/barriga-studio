"""Pruebas del coordinador local; no requiere ejecutar un modelo ni conectarse a Internet."""
from pathlib import Path
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
