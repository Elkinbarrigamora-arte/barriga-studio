"""Pruebas sin conexión del puente de colaboración."""
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import puente_colaboracion as bridge


class FakeHTTP:
    def __init__(self, data):
        self.data = data
    def __enter__(self):
        return io.BytesIO(self.data)
    def __exit__(self, *args):
        return None


class PuenteTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.root = self.base / 'studio'
        self.root.mkdir()
        (self.root / '.git').mkdir()
        (self.root / 'index.html').write_text(
            '<html><a href="#crear">Crear</a><a href="#inexistente">Inexistente</a>'
            '<div id="crear"></div><div id="crear"></div>'
            '<script>const KEY="barriga-studio-projects-v1";'
            'localStorage.setItem(KEY,[]);activeId=p.id;</script></html>', encoding='utf-8')
        self.state = self.base / 'private'

    def test_orders_allowlist(self):
        raw = json.dumps({'version': 1, 'ordenes': [
            {'id': 'BS-0001', 'accion': 'diagnostico'}]}).encode('utf-8')
        with patch.object(bridge, 'urlopen', return_value=FakeHTTP(raw)):
            self.assertEqual(bridge.load_orders()[0]['accion'], 'diagnostico')

    def test_invalid_commands_are_rejected(self):
        for orders in ([{'id': 'BS-0002', 'accion': 'borrar_disco'}],
                       [{'id': 'BS-0002', 'accion': 'diagnostico', 'shell': 'rm -rf /'}],
                       [{'id': 'BS-0002', 'accion': 'diagnostico'},
                        {'id': 'BS-0002', 'accion': 'diagnostico'}]):
            with self.subTest(orders=orders):
                raw = json.dumps({'version': 1, 'ordenes': orders}).encode('utf-8')
                with patch.object(bridge, 'urlopen', return_value=FakeHTTP(raw)):
                    with self.assertRaises(ValueError):
                        bridge.load_orders()

    def test_audit_counts_navigation_errors(self):
        a = bridge.do_action(self.root, 'auditoria_interfaz')
        self.assertEqual(a['enlaces_sin_destino'], 1)
        self.assertEqual(a['ids_duplicados'], 1)

    def test_jobs_are_not_executed_twice(self):
        orders = [{'id': 'BS-0001', 'accion': 'auditoria_interfaz'}]
        first = bridge.run_once(self.root, self.state, orders)
        second = bridge.run_once(self.root, self.state, orders)
        self.assertEqual(first['nuevas'], 1)
        self.assertEqual(second['nuevas'], 0)

    def test_errors_do_not_expose_private_content(self):
        orders = [{'id': 'BS-0003', 'accion': 'revision_proyectos'}]
        with patch.object(bridge, 'do_action', side_effect=RuntimeError('PASSWORD PRIVATE')) :
            result = bridge.run_once(self.root, self.state, orders)
        self.assertNotIn('PASSWORD PRIVATE', json.dumps(result))
        self.assertEqual(result['resultados'][0]['estado'], 'ERROR')

    def test_results_are_not_public_by_default(self):
        with patch.object(bridge, 'publish') as publisher:
            bridge.run_once(self.root, self.state, [
                {'id': 'BS-0004', 'accion': 'auditoria_interfaz'}])
            publisher.assert_not_called()


if __name__ == '__main__':
    unittest.main()
