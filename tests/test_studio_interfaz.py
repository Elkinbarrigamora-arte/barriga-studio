"""Auditoría estática del Studio: conserva esquema legacy y evita capacidades falsas.

Estas pruebas NO sustituyen una inspección visual con navegador real.
"""
from pathlib import Path
import re
import shutil
import subprocess
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
INDEX = (ROOT / "index.html").read_text(encoding="utf-8")
JS = (ROOT / "assets/studio-interfaz.js").read_text(encoding="utf-8")
CSS = (ROOT / "assets/studio-interfaz.css").read_text(encoding="utf-8")
MEJORAS = (ROOT / "assets/studio-mejoras.js").read_text(encoding="utf-8")


class StudioVisualStructureTest(unittest.TestCase):
    def test_modules_loaded_without_removing_legacy_features(self):
        self.assertIn('href="assets/studio-interfaz.css"', INDEX)
        self.assertIn('src="assets/studio-interfaz.js"', INDEX)
        self.assertIn('src="assets/studio-mejoras.js"', INDEX)
        for ident in ("script", "reference", "style", "voice", "format",
                      "duration", "projectList", "proyectos"):
            self.assertIn('id="' + ident + '"', INDEX)
        self.assertIn("barriga-studio-projects-v1", INDEX)
        self.assertIn("barriga-studio-projects-v1", MEJORAS)
        self.assertIn("barriga-studio-projects-v1", JS)

    def test_critical_functions_remain_real(self):
        for action in ("function save()", "function render()",
                       "function exportDraft()", "function choose("):
            self.assertIn(action, INDEX)
        for action in ("function exportBackup()", "async function importBackup(",
                       "function deleteProject(", "function cloneProject("):
            self.assertIn(action, MEJORAS)
        self.assertNotIn("localStorage.clear(", JS)
        self.assertNotIn("localStorage.removeItem(KEY)", JS)

    def test_respaldo_preserva_idea_original_y_guion_previo(self):
        self.assertIn('const ideaOriginal = String(project.ideaOriginal', MEJORAS)
        self.assertIn('const ultimoGuion = String(project.ultimoGuion', MEJORAS)
        self.assertIn('name, script, ideaOriginal, ultimoGuion', MEJORAS)
        self.assertIn('p.ideaOriginal, p.ultimoGuion', MEJORAS)
        self.assertNotIn('.slice(0, 30000)', MEJORAS)

    def test_four_columns_and_responsive_breakpoints(self):
        self.assertIn("grid-template-columns:minmax(0,27fr) minmax(0,40fr) minmax(0,16fr) minmax(0,17fr)", CSS)
        for bound in ("1070px", "680px"):
            self.assertIn(bound, CSS)
        for color in ("#030B20", "#08152E", "#FFD21A",
                      "#8B35FF", "#E000F5", "#1675FF"):
            self.assertIn(color, CSS)
        for anchor in ('"#crear"', '"#plantillas"', '"#voz"', '"#vista-previa"'):
            self.assertIn(anchor, JS)
        self.assertIn("min-height:44px", CSS)

    def test_media_behaviour_does_not_claim_fictional_generation(self):
        self.assertIn("player.controls = true", JS)
        self.assertIn("URL.createObjectURL(file)", JS)
        self.assertIn('generate.disabled = true', JS)
        self.assertIn('download.disabled = true', JS)
        self.assertIn('accept = "video/mp4,video/webm"', JS)
        self.assertIn("No fue generado por Barriga IA", JS)
        self.assertIn("motor de generación de video real", JS)

    def test_project_filters_and_additive_metadata(self):
        for name in ("Todos", "En proceso", "Completados", "Favoritos",
                     "Buscar proyectos", "Nuevo proyecto", "Restaurar respaldo"):
            self.assertTrue(name in JS or name in MEJORAS, name)
        self.assertIn("barriga-studio-favorites-v1", JS)
        self.assertIn("studio-project-menu", JS)
        self.assertIn("typeof activeId !==", JS)
        self.assertIn("if (script && script.value.trim() && !confirm", JS)

    def test_ilustracion_vectorial_integrada_y_valida(self):
        image = ROOT / "assets/banner-personajes.svg"
        self.assertTrue(image.is_file())
        root = ET.parse(image).getroot()
        self.assertEqual(root.tag, "{http://www.w3.org/2000/svg}svg")
        self.assertIn("banner-personajes.svg", CSS)
        self.assertIn("No fue generado por Barriga IA", JS)

    def test_javascript_syntax_if_node_available(self):
        node = shutil.which("node")
        if not node:
            self.skipTest("Node.js no disponible en el entorno")
        for file in (ROOT / "assets/studio-interfaz.js",
                     ROOT / "assets/studio-mejoras.js"):
            with self.subTest(file=file.name):
                proc = subprocess.run([node, "--check", str(file)],
                                      capture_output=True, text=True, timeout=20)
                self.assertEqual(proc.returncode, 0, proc.stderr)


if __name__ == "__main__":
    unittest.main()
