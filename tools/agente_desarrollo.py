#!/usr/bin/env python3
"""Barriga IA: desarrollo local de Studio con Ollama, verificación y puntos de recuperación.

No expone puertos, no instala software, no envía código a proveedores externos.
Por seguridad, no ejecuta comandos producidos por el modelo ni publica en GitHub.
"""
import argparse
import ast
from datetime import datetime
from html.parser import HTMLParser
import json
from pathlib import Path
import shutil
import subprocess
import sys
from urllib.request import Request, urlopen
from urllib.error import HTTPError
import time

MODEL = 'qwen2.5-coder:14b'
OLLAMA = 'http://127.0.0.1:11434/api/generate'
MAX_NEW_SIZE = 110_000
MAX_CHANGES = 3

STAGES = [
    ('01_guion', 'Crear una experiencia editorial real: guiones con gancho, historia, cierre y escenas, '
     'incluyendo coherencia narrativa, sin confundir una oferta comercial con el final dramático. '
     'Mantener las tres plantillas existentes y los IDs HTML usados por el editor.'),
    ('02_escenas', 'Agregar un desglose editable en escenas con duración, personajes, diálogos y '
     'continuidad de ropa, cuerpo, rostros y objetos. No presentar imágenes como videos.'),
    ('03_proyectos', 'Mejorar guardado, reanudación y estado de producción por escena; '
     'respetar la clave barriga-studio-projects-v1 y la importación de respaldos existentes.'),
    ('04_motores', 'Agregar comprobación visual de capacidades reales, voz, imagen y video, '
     'mostrando explícitamente NO DISPONIBLE cuando no existe un motor comprobado. '
     'No inventar servidores ni servicios de pago.'),
    ('05_calidad', 'Agregar checklist de control de calidad: cuatro revisiones editoriales '
     'y cuatro verificaciones finales, con fallos legibles y sin resultados simulados.'),
]


def git(root, *args, check=True):
    proc = subprocess.run(['git', *args], cwd=root, text=True, capture_output=True,
                          timeout=35, check=False)
    if check and proc.returncode:
        raise RuntimeError('git ' + ' '.join(args) + ': ' + (proc.stderr or proc.stdout).strip())
    return proc.stdout.strip()


def guard_path(root, rel):
    if not isinstance(rel, str) or len(rel) > 150 or '\\' in rel or rel.startswith('/'):
        raise ValueError('Ruta inválida')
    parts = Path(rel).parts
    if not parts or any(p in ('..', '.', '.git', '__pycache__') for p in parts):
        raise ValueError('Ruta fuera del proyecto')
    allowed = (rel == 'index.html' or
               (rel.startswith('assets/') and rel.endswith(('.js', '.css'))) or
               (rel.startswith('docs/') and rel.endswith('.md')) or
               (rel.startswith('tests/') and rel.endswith('.py')))
    if not allowed:
        raise ValueError('Archivo no autorizado: ' + rel)
    path = (root / rel).resolve()
    if not path.is_relative_to(root.resolve()):
        raise ValueError('La ruta sale del repositorio')
    if path.exists() and not path.is_file():
        raise ValueError('La ruta no es un archivo')
    return path


def context(root, task):
    base = ['index.html', 'assets/studio-mejoras.js', 'tools/puente_local.py']
    existing = [p for p in sorted(root.glob('assets/*.js')) if p.name != 'studio-mejoras.js']
    files = [root / p for p in base] + existing[:3]
    sections = []
    for path in files:
        if path.is_file() and path.stat().st_size <= 50_000:
            s = path.read_text(encoding='utf-8')
            if path.name == 'index.html' and len(s) > 13_000:
                s = s[:2000] + '\n[CSS intermedio omitido]\n' + s[-11_500:]
            sections.append('ARCHIVO ' + str(path.relative_to(root)) + '\n' + s)
    return '\n\n'.join(sections)[:34_000]


def ask_model(task, current, model):
    system = (
        'Actúas como ingeniero senior de Barriga Studio, no como un chat. '
        'Debes IMPLEMENTAR una mejora concreta y mínima del objetivo, compatible con el código real. '
        'Devuelve SOLO JSON válido con forma '
        '{"resumen":"...","cambios":[{"ruta":"assets/modulo.js","contenido":"código completo"},'
        '{"ruta":"index.html","buscar":"texto literal único","reemplazar":"texto nuevo"}]}. '
        'REGLA CRÍTICA OBLIGATORIA: contenido SOLO para rutas que NO EXISTEN EN DISCO; '
        'NUNCA entregues contenido para assets/escenas.js, assets/editorial.js, index.html '
        'ni otro archivo existente. Para archivos existentes usa buscar/reemplazar literal exacto. '
        'Ejemplo de archivo existente: {"ruta":"assets/escenas.js",'
        '"buscar":"TEXTO EXACTO PRESENTE", "reemplazar":"TEXTO NUEVO"}. '
        'Ejemplo de archivo nuevo: {"ruta":"assets/proyectos-core.js",'
        '"contenido":"código JavaScript completo"}. '
        'Si quieres añadir una funcionalidad extensa, CREA un archivo JS nuevo y '
        'enlázalo desde index.html mediante un parche exacto en </body>. '
        'Puedes incluir varios buscar/reemplazar sobre UNA MISMA RUTA existente; '
        'se aplicarán EN ORDEN y cada buscar debe coincidir exactamente una vez '
        'en el resultado del cambio anterior. Nunca dupliques contenido para un archivo nuevo. '
        'Hasta TRES cambios por iteración. '
        'No inventes servicios de video, sincronización, voces ni funcionalidades no conectadas. '
        'Solo edita index.html, assets/, docs/ o tests/. '
        'NO propongas cambios de tools/puente_local.py ni de otros archivos tools/. '
        'Si usas buscar/reemplazar, copia exactamente un fragmento visible del archivo actual; '
        'no reescribas fragmentos supuestos, recortados u omitidos. '
        'Prioriza crear un módulo JS en assets/ y enlazarlo desde index.html. '
        'No toques datos privados, versiones históricas ni herramientas del agente. '
        'Conserva nombres de controles, IDs HTML y funciones existentes. '
        'Código ejecutable y profesional; evita funciones vacías, ejemplos falsos y promesas. '
        'Se verificará sintaxis JS con Node si está disponible. '
        'No generes comandos shell. Responde en español.'
    )
    prompt = (system + '\n\nOBJETIVO DE ESTA ITERACIÓN: ' + task +
              '\n\nCÓDIGO ACTUAL:\n' + current +
              '\n\nRECUERDA: antes de escribir JSON, distingue archivos EXISTENTES (buscar/reemplazar) '
              'de archivos NUEVOS (contenido). No uses contenido para assets/escenas.js.')
    payload = {'model': model, 'prompt': prompt, 'format': 'json', 'stream': False,
               'options': {'temperature': 0.2, 'num_ctx': 12288, 'num_predict': 3500}}
    request = Request(OLLAMA, data=json.dumps(payload).encode('utf-8'),
                      headers={'Content-Type': 'application/json'}, method='POST')
    raw = None
    for attempt in range(1, 4):
        try:
            with urlopen(request, timeout=360) as answer:
                raw = json.load(answer).get('response', '')
            break
        except HTTPError as exc:
            detail = exc.read(500).decode('utf-8', 'replace').strip()
            if exc.code not in (500, 502, 503, 504) or attempt == 3:
                raise RuntimeError('Ollama HTTP ' + str(exc.code) + ': ' + detail[:350]) from exc
            print('Ollama HTTP ' + str(exc.code) +
                  ': reintento controlado ' + str(attempt) + '/3', flush=True)
            time.sleep(attempt * 2)
        except (OSError, TimeoutError) as exc:
            if attempt == 3:
                raise RuntimeError('Ollama no disponible tras tres intentos: ' + str(exc)) from exc
            print('Ollama desconectado: reintento controlado ' +
                  str(attempt) + '/3', flush=True)
            time.sleep(attempt * 2)
    try:
        result = json.loads(raw)
    except (ValueError, TypeError) as exc:
        raise RuntimeError('Ollama no devolvió cambios JSON válidos: ' + str(exc)) from exc
    if not isinstance(result, dict) or not isinstance(result.get('cambios'), list):
        raise ValueError('Falta el arreglo cambios')
    if not 1 <= len(result['cambios']) <= MAX_CHANGES:
        raise ValueError('Se permiten de 1 a 3 cambios por ciclo')
    return result


def plan_changes(root, changes):
    planned = {}
    for change in changes:
        if not isinstance(change, dict):
            raise ValueError('Cambio sin formato válido')
        rel = change.get('ruta')
        target = guard_path(root, rel)
        if target.exists():
            if 'contenido' in change:
                raise ValueError('Para archivo existente usa buscar/reemplazar: ' + rel)
            # Parches sobre una misma ruta se aplican secuencialmente sin borrar cambios previos.
            old = planned[rel] if rel in planned else target.read_text(encoding='utf-8')
            find, replace = change.get('buscar'), change.get('reemplazar')
            if not isinstance(find, str) or not find or not isinstance(replace, str):
                raise ValueError('Parche de texto inválido: ' + rel)
            if old.count(find) != 1:
                raise ValueError('El parche no coincide exactamente una vez: ' + rel)
            new = old.replace(find, replace, 1)
        else:
            if rel in planned:
                raise ValueError('Archivo nuevo repetido: ' + rel)
            if 'buscar' in change or not isinstance(change.get('contenido'), str):
                raise ValueError('Para archivo nuevo usa contenido: ' + rel)
            new = change['contenido']
        if len(new.encode('utf-8')) > MAX_NEW_SIZE or not new.strip():
            raise ValueError('Archivo vacío o demasiado grande: ' + rel)
        planned[rel] = new
    return planned


class Scripts(HTMLParser):
    def __init__(self):
        super().__init__()
        self.refs, self.inline, self.in_script = [], [], False
    def handle_starttag(self, tag, attrs):
        if tag == 'script':
            attrs = dict(attrs)
            if attrs.get('src'):
                self.refs.append(attrs['src'])
                self.in_script = False
            else:
                self.in_script = True
    def handle_endtag(self, tag):
        if tag == 'script':
            self.in_script = False
    def handle_data(self, data):
        if self.in_script and data.strip():
            self.inline.append(data)


def node_check(code, name):
    node = shutil.which('node')
    if not node:
        raise RuntimeError('Node.js no está instalado: es necesario para validar los cambios JavaScript')
    result = subprocess.run([node, '--check', '-'], input=code, capture_output=True,
                            text=True, timeout=30)
    if result.returncode:
        raise RuntimeError('Sintaxis JS inválida en ' + name + ': ' + result.stderr.strip()[:1200])


def validate(root, changes):
    for rel, source in changes.items():
        if rel.endswith('.py'):
            ast.parse(source, filename=rel)
        elif rel.endswith('.js'):
            node_check(source, rel)
        elif rel == 'index.html':
            if not all(x in source for x in ('<html', '</html>', 'id="script"', 'id="projectList"')):
                raise ValueError('La estructura del editor quedó incompleta')
            parser = Scripts()
            parser.feed(source)
            for inline in parser.inline:
                node_check(inline, 'JavaScript inline de index.html')
    html = changes.get('index.html', (root / 'index.html').read_text(encoding='utf-8'))
    parser = Scripts()
    parser.feed(html)
    for ref in parser.refs:
        if ref.startswith(('https://', 'http://')):
            continue
        if not (root / ref).is_file() and ref not in changes:
            raise ValueError('Script enlazado que no existe: ' + ref)


def restore(root, previous):
    for rel, content in previous.items():
        path = root / rel
        if content is None:
            path.unlink(missing_ok=True)
        else:
            path.write_text(content, encoding='utf-8')


def run_stage(root, name, goal, model):
    if git(root, 'status', '--porcelain'):
        raise RuntimeError('Hay cambios locales sin guardar; no se tocará nada')
    backup = 'backup/barriga-ia-' + datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    git(root, 'branch', backup)
    print('Respaldo Git: ' + backup, flush=True)
    planned = None
    error_feedback = ''
    max_attempts = 5
    for attempt in range(1, max_attempts + 1):
        task = goal + error_feedback
        answer = ask_model(task, context(root, task), model)
        try:
            planned = plan_changes(root, answer['cambios'])
            break
        except ValueError as exc:
            if attempt == max_attempts:
                raise RuntimeError('Cinco propuestas no aplicables; no se editó ningún archivo: ' + str(exc)) from exc
            print('Parche rechazado (' + str(attempt) + '/' + str(max_attempts) + '): ' + str(exc) + '. Reintentando...', flush=True)
            message = str(exc)
            if message.startswith('Archivo nuevo repetido: '):
                advice = ('No crees dos veces un mismo archivo. Envía una única entrada contenido '
                          'para esa ruta y usa las otras entradas para otros archivos.')
            elif message.startswith('Para archivo existente usa buscar/reemplazar: '):
                rejected_path = message.split(': ', 1)[1]
                advice = ('La ruta ' + rejected_path + ' YA EXISTE. Está PROHIBIDO devolver contenido '
                          'para ella. Usa buscar/reemplazar exactos o crea un JS NUEVO '
                          'y agrégalo a index.html con otro parche.')
            elif message.startswith('El parche no coincide exactamente una vez: '):
                rejected_path = message.split(': ', 1)[1]
                advice = ('Tu campo buscar NO aparece exactamente una vez en ' + rejected_path +
                          '. Copia textualmente una cadena breve y ÚNICA del archivo mostrado, '
                          'o crea un JS NUEVO y enlázalo con un parche exacto a index.html.')
            else:
                advice = ('Usa rutas diferentes y los fragmentos literales presentes '
                          'en el código actual, sin modificar archivos protegidos.')
            error_feedback = ('\n\nCORRECCIÓN OBLIGATORIA DEL INTENTO ' + str(attempt) +
                              ': ' + message + '. ' + advice +
                              ' Rehaz TODOS los cambios en JSON válido, sin repetir el error.')
    previous = {rel: (root / rel).read_text(encoding='utf-8') if (root / rel).exists() else None
                for rel in planned}
    try:
        for rel, content in planned.items():
            target = root / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding='utf-8')
        validate(root, planned)
        git(root, 'add', '--', *planned)
        diff = subprocess.run(['git', 'diff', '--cached', '--check'], cwd=root,
                              text=True, capture_output=True, timeout=20)
        if diff.returncode:
            raise RuntimeError('git diff --check: ' + diff.stdout + diff.stderr)
        git(root, 'commit', '-m', 'Barriga IA: ' + name)
        sha = git(root, 'rev-parse', '--short', 'HEAD')
        print('APROBADO: ' + name + ' | commit ' + sha + ' | ' + ', '.join(planned), flush=True)
        print('Nota: pasó validación estructural y de sintaxis, no prueba funcional real.', flush=True)
        return True
    except Exception:
        git(root, 'reset', '-q', '--', *planned, check=False)
        restore(root, previous)
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--studio', type=Path, default=Path.cwd())
    parser.add_argument('--modelo', default=MODEL)
    parser.add_argument('--ciclos', type=int, default=1,
                        help='Máximo 5 fases secuenciales por ejecución (1-5)')
    args = parser.parse_args()
    if not 1 <= args.ciclos <= len(STAGES):
        parser.error('--ciclos debe estar entre 1 y ' + str(len(STAGES)))
    root = args.studio.expanduser().resolve()
    if not (root / '.git').exists() or not (root / 'index.html').is_file():
        parser.error('Abre la carpeta Git real de barriga-studio con index.html')
    if git(root, 'branch', '--show-current') != 'main':
        parser.error('Para evitar modificar otra rama, inicia desde main')
    if git(root, 'status', '--porcelain'):
        parser.error('Repositorio con cambios locales. Haz un respaldo/commit antes de iniciar.')
    print('Barriga IA | desarrollo local | sin publicación automática', flush=True)
    completed = set()
    history = git(root, 'log', '--format=%s', '-n', '100', check=False)
    for name, _ in STAGES:
        if 'Barriga IA: ' + name in history.splitlines():
            completed.add(name)
    pending = [(name, objective) for name, objective in STAGES if name not in completed]
    selection = pending[:args.ciclos]
    if not selection:
        print('No hay fases pendientes en el plan.', flush=True)
        return 0
    for index, (name, objective) in enumerate(selection, 1):
        print('FASE ' + str(index) + '/' + str(len(selection)) + ': ' + name, flush=True)
        try:
            run_stage(root, name, objective, args.modelo)
        except Exception as exc:
            print('DETENIDO EN ' + name + ': ' + str(exc), file=sys.stderr, flush=True)
            print('No se completarán más fases. Revisa el error y el respaldo.', flush=True)
            return 1
    print('Ciclos completados. Cambios guardados SOLO en el Git local. '
          'Verifica el Studio antes de publicar.', flush=True)
    return 0


if __name__ == '__main__':
    sys.exit(main())
