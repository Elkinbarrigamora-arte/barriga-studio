#!/usr/bin/env python3
"""Barriga Studio: puente de tareas permitidas por GitHub, sin exponer la Mac.

Las órdenes públicas son DATOS NO CONFIABLES, nunca comandos shell.
Publica únicamente resultados técnicos normalizados, jamás logs o proyectos.
"""
import argparse
import fcntl
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import plistlib
import re
import shutil
import socket
import subprocess
import sys
import tempfile
from urllib.request import Request, urlopen

REPO = 'Elkinbarrigamora-arte/barriga-studio'
SOURCE = 'https://raw.githubusercontent.com/' + REPO + '/main/bridge/ordenes.json'
REPO_URL = 'https://github.com/' + REPO + '.git'
AGENT_ID = 'com.barriga.studio.puente'
ACTIONS = frozenset({'diagnostico', 'auditoria_interfaz', 'pruebas_agente', 'revision_proyectos'})
ID_PATTERN = re.compile(r'^BS-[0-9]{4,8}$')


class Elements(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = []
        self.links = []

    def handle_starttag(self, tag, attrs):
        data = dict(attrs)
        if data.get('id'):
            self.ids.append(data['id'])
        if tag == 'a' and data.get('href', '').startswith('#'):
            self.links.append(data['href'][1:])


def command(*argv, cwd=None, timeout=25):
    env = os.environ.copy()
    env["GIT_TERMINAL_PROMPT"] = "0"
    return subprocess.run(argv, cwd=cwd, timeout=timeout, text=True,
                          capture_output=True, check=False, env=env)


def reachable(port):
    try:
        with socket.create_connection(('127.0.0.1', port), timeout=0.75):
            return True
    except OSError:
        return False


def do_action(root, action):
    if action == 'diagnostico':
        status = command('git', 'status', '--porcelain', cwd=root)
        return {'git_disponible': status.returncode == 0,
                'cambios_locales': bool(status.stdout.strip()),
                'ollama_conectado': reachable(11434),
                'drawthings_conectado': reachable(7860),
                'node_disponible': bool(shutil.which('node'))}
    if action == 'auditoria_interfaz':
        html = (root / 'index.html').read_text(encoding='utf-8')
        parser = Elements()
        parser.feed(html)
        ids = set(parser.ids)
        missing = sorted(set(parser.links) - ids - {''})
        duplicates = len(parser.ids) - len(ids)
        old_grid = '.workspace{display:grid;grid-template-columns:repeat(2' in html
        return {'enlaces_sin_destino': len(missing),
                'ids_duplicados': duplicates,
                'editor_en_dos_columnas': old_grid,
                'navegacion_requiere_revision': old_grid or bool(missing or duplicates)}
    if action == 'revision_proyectos':
        html = (root / 'index.html').read_text(encoding='utf-8')
        mejoras = (root / 'assets/studio-mejoras.js')
        contenido = mejoras.read_text(encoding='utf-8') if mejoras.is_file() else ''
        return {'guardado_local': 'localStorage.setItem(KEY' in html,
                'abre_proyecto': 'activeId=p.id' in html,
                'respaldo_json': 'function exportBackup()' in contenido,
                'guarda_escenas_en_proyecto': bool(re.search(r'\bscenes\s*:', html))}
    if action == 'pruebas_agente':
        target = root / 'tests' / 'test_agente_desarrollo.py'
        if not target.is_file():
            return {'pruebas_disponibles': False, 'pruebas_pasadas': False}
        proc = command(sys.executable, '-m', 'unittest', 'discover', '-s', 'tests',
                       '-p', 'test_agente_desarrollo.py', cwd=root, timeout=120)
        found = re.search(r'Ran (\d+) tests?', proc.stderr + proc.stdout)
        return {'pruebas_disponibles': True, 'pruebas_pasadas': proc.returncode == 0,
                'total_pruebas': int(found.group(1)) if found else 0}
    raise ValueError('Acción no autorizada')


def load_orders(url=SOURCE):
    request = Request(url, headers={'User-Agent': 'Barriga-Studio-Bridge/1.0',
                                    'Accept': 'application/json'})
    with urlopen(request, timeout=15) as response:
        raw = response.read(32769)
    if len(raw) > 32768:
        raise ValueError('Órdenes demasiado grandes')
    payload = json.loads(raw)
    if not isinstance(payload, dict) or payload.get('version') != 1:
        raise ValueError('Versión desconocida')
    orders = payload.get('ordenes')
    if not isinstance(orders, list) or len(orders) > 20:
        raise ValueError('Lista de órdenes inválida')
    approved = []
    ids = set()
    for order in orders:
        if (not isinstance(order, dict) or not isinstance(order.get('id'), str) or
            not ID_PATTERN.fullmatch(order['id']) or order['id'] in ids or
            order.get('accion') not in ACTIONS or
            set(order) - {'id', 'accion'}):
            raise ValueError('Orden no autorizada o repetida')
        ids.add(order['id'])
        approved.append(order)
    return approved


def private_dir():
    base = Path.home() / 'Library' / 'Application Support' / 'BarrigaStudio' / 'Puente'
    base.mkdir(parents=True, exist_ok=True, mode=0o700)
    return base


def read_json(path, default):
    if not path.is_file():
        return default
    return json.loads(path.read_text(encoding='utf-8'))


def atomic_json(path, payload):
    fd, name = tempfile.mkstemp(prefix='.' + path.name, dir=path.parent)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as output:
            json.dump(payload, output, ensure_ascii=False, indent=2)
            output.write('\n')
        os.chmod(name, 0o600)
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def publish(repo_dir, results):
    """Usa CLON APARTE: jamás hace reset/push del repositorio de trabajo."""
    if not results:
        return 'SIN_RESULTADOS'
    if not (repo_dir / '.git').exists():
        repo_dir.parent.mkdir(parents=True, exist_ok=True)
        p = command('git', 'clone', '--depth', '1', '--branch', 'main', REPO_URL,
                    str(repo_dir), timeout=120)
        if p.returncode:
            return 'SIN_PERMISOS_GITHUB'
    for attempt in range(2):
        fetched = command('git', 'fetch', 'origin', 'main', cwd=repo_dir, timeout=60)
        if fetched.returncode:
            return 'SIN_CONEXION_GITHUB'
        # Solo se descartan cambios en esta copia aislada, nunca en ~/barriga-studio.
        reset = command('git', 'reset', '--hard', 'origin/main', cwd=repo_dir)
        if reset.returncode:
            return 'ERROR_COPIA_AISLADA'
        target = repo_dir / 'bridge' / 'estado.json'
        target.parent.mkdir(parents=True, exist_ok=True)
        # INFORMACIÓN PÚBLICA: solo códigos y campos booleanos/números aprobados.
        target.write_text(json.dumps({'version': 1, 'resultados': results[-20:]},
                                     ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        command('git', 'config', 'user.name', 'Barriga Bridge', cwd=repo_dir)
        command('git', 'config', 'user.email',
                'barriga-bridge@users.noreply.github.com', cwd=repo_dir)
        add = command('git', 'add', '--', 'bridge/estado.json', cwd=repo_dir)
        if add.returncode:
            return 'ERROR_PREPARACION'
        commit = command('git', 'commit', '-m', 'bridge: resultados tecnicos verificados', cwd=repo_dir)
        if commit.returncode and 'nothing to commit' not in commit.stdout:
            return 'ERROR_PUBLICACION'
        if 'nothing to commit' in commit.stdout:
            return 'AL_DIA'
        push = command('git', 'push', 'origin', 'HEAD:main', cwd=repo_dir, timeout=65)
        if push.returncode == 0:
            return 'PUBLICADO'
    return 'SIN_PERMISOS_O_CONFLICTO'


def run_once(root, state_dir, orders=None):
    if not (root / 'index.html').is_file() or not (root / '.git').exists():
        raise ValueError('No es la carpeta real de Barriga Studio')
    state_dir.mkdir(parents=True, exist_ok=True)
    lock_path = state_dir / 'puente.lock'
    with lock_path.open('a+') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return {'estado': 'OCUPADO'}
        state_path = state_dir / 'procesados.json'
        state = read_json(state_path, {'ids': [], 'resultados': [], 'publicar': False})
        incoming = load_orders() if orders is None else orders
        completed = set(state.get('ids', []))
        new = []
        for order in incoming:
            if order['id'] in completed:
                continue
            try:
                detail = do_action(root, order['accion'])
                result = {'id': order['id'], 'accion': order['accion'],
                          'estado': 'OK', 'datos': detail}
            except Exception:
                result = {'id': order['id'], 'accion': order['accion'],
                          'estado': 'ERROR'}
            new.append(result)
            state.setdefault('ids', []).append(order['id'])
            state.setdefault('resultados', []).append(result)
            atomic_json(state_path, state)
        publication = 'DESACTIVADA'
        if state.get('publicar') and state.get('resultados'):
            publication = publish(state_dir / 'copia_publica', state.get('resultados', []))
        return {'estado': 'OK', 'nuevas': len(new), 'publicacion': publication,
                'resultados': new}


def install(root, state_dir, public):
    state_dir.mkdir(parents=True, exist_ok=True)
    config = state_dir / 'procesados.json'
    state = read_json(config, {'ids': [], 'resultados': [], 'publicar': False})
    # Publicar datos genéricos solo tras consentimiento explícito --publicar.
    state['publicar'] = public or state.get('publicar', False)
    atomic_json(config, state)
    agents = Path.home() / 'Library' / 'LaunchAgents'
    agents.mkdir(parents=True, exist_ok=True)
    plist = agents / (AGENT_ID + '.plist')
    payload = {'Label': AGENT_ID,
               'ProgramArguments': [sys.executable, str(Path(__file__).resolve()),
                                    '--una-vez', '--studio', str(root)],
               'RunAtLoad': True, 'StartInterval': 180,
               'StandardOutPath': str(state_dir / 'salida.log'),
               'StandardErrorPath': str(state_dir / 'errores.log')}
    with plist.open('wb') as output:
        plistlib.dump(payload, output)
    mode = 'gui/' + str(os.getuid())
    # Idempotente: un servicio anterior puede estar instalado.
    command('launchctl', 'bootout', mode + '/' + AGENT_ID, timeout=10)
    started = command('launchctl', 'bootstrap', mode, str(plist), timeout=15)
    if started.returncode:
        return {'instalado': False, 'plist': str(plist),
                'motivo': 'launchctl no pudo iniciar el servicio'}
    return {'instalado': True, 'cada_segundos': 180,
            'publicacion_publica': bool(state['publicar'])}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--studio', type=Path, default=Path(__file__).resolve().parents[1])
    actions = ap.add_mutually_exclusive_group(required=True)
    actions.add_argument('--instalar', action='store_true')
    actions.add_argument('--una-vez', action='store_true')
    actions.add_argument('--estado', action='store_true')
    ap.add_argument('--publicar', action='store_true',
                    help='Autoriza publicar exclusivamente resultados técnicos genéricos '
                         'en el repositorio GitHub PUBLICO')
    args = ap.parse_args()
    root = args.studio.expanduser().resolve()
    state_dir = private_dir()
    if args.instalar:
        result = install(root, state_dir, args.publicar)
    elif args.estado:
        status = read_json(state_dir / 'procesados.json', {})
        result = {'instalado': (Path.home() / 'Library' / 'LaunchAgents' /
                               (AGENT_ID + '.plist')).is_file(),
                  'procesadas': len(status.get('ids', [])),
                  'publicacion_publica': bool(status.get('publicar', False))}
    else:
        result = run_once(root, state_dir)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except Exception as error:
        print('Puente detenido: ' + type(error).__name__ + ': ' + str(error)[:150],
              file=sys.stderr)
        sys.exit(1)
