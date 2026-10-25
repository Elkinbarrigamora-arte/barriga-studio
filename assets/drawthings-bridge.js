/* Panel experimental. Solo funciona cuando lo sirve tools/puente_local.py. */
(() => {
  'use strict';
  const token = window.__BARRIGA_LOCAL_TOKEN__;
  const parent = document.querySelector('#crear .panel');
  if (!token || !parent) return;

  const create = (tag, text, parentNode) => {
    const element = document.createElement(tag);
    if (text !== undefined) element.textContent = text;
    if (parentNode) parentNode.appendChild(element);
    return element;
  };
  const box = create('section', undefined, parent);
  box.setAttribute('aria-label', 'Generador de imágenes Draw Things');
  box.style.cssText = 'margin:20px 0;padding:18px;border:1px solid #7769d5;border-radius:14px;background:#14122c';
  create('h3', '📷 Barriga IA · Imágenes con Draw Things', box);
  create('p', 'Genera y compara fotografías directamente desde tu Studio local. Las imágenes no se guardan en los proyectos ni se envían a GitHub.', box).className = 'muted';

  const makeField = (labelText, tag) => {
    const wrapper = create('div', undefined, box);
    wrapper.style.margin = '12px 0';
    const label = create('label', labelText, wrapper);
    const input = create(tag, undefined, wrapper);
    input.id = 'barriga-image-' + labelText.toLowerCase().replace(/[^a-z]/g, '-');
    label.htmlFor = input.id;
    input.style.cssText = 'display:block;width:100%;margin-top:6px';
    return input;
  };
  const preset = makeField('Perfil visual', 'select');
  const prompt = makeField('Descripción editable', 'textarea');
  prompt.rows = 5;
  const settings = create('div', undefined, box);
  settings.style.cssText = 'display:flex;flex-wrap:wrap;gap:12px';
  const numberInput = (label, value, min, max, step) => {
    const wrap = create('label', label, settings);
    wrap.style.flex = '1 1 90px';
    const input = create('input', undefined, wrap);
    input.type = 'number'; input.value = String(value);
    input.min = String(min); input.max = String(max); input.step = String(step);
    input.style.cssText = 'display:block;width:100%;margin-top:5px';
    return input;
  };
  const steps = numberInput('Pasos', 35, 20, 45, 1);
  const guidance = numberInput('Guía', 6, 3, 8, 0.5);
  const seed = numberInput('Semilla (-1 = nueva)', -1, -1, 2147483647, 1);

  const actions = create('div', undefined, box);
  actions.style.cssText = 'display:flex;flex-wrap:wrap;gap:9px;margin:12px 0';
  const check = create('button', 'Comprobar conexión', actions);
  const generate = create('button', 'Generar imagen', actions);
  const download = create('button', 'Descargar imagen', actions);
  const downloadPrevious = create('button', 'Descargar anterior', actions);
  check.type = generate.type = download.type = downloadPrevious.type = 'button';
  check.className = 'button ghost'; generate.className = download.className = 'button';
  downloadPrevious.className = 'button ghost';
  download.disabled = downloadPrevious.disabled = true;
  const status = create('p', 'Conecta Draw Things y comprueba su estado.', box);
  status.className = 'muted'; status.setAttribute('role', 'status');
  status.setAttribute('aria-live', 'polite');
  const comparison = create('div', undefined, box);
  comparison.style.cssText = 'display:flex;flex-wrap:wrap;gap:12px';
  const previousFrame = create('figure', undefined, comparison);
  const currentFrame = create('figure', undefined, comparison);
  for (const frame of [previousFrame, currentFrame]) {
    frame.style.cssText = 'flex:1 1 240px;min-width:0;margin:0';
  }
  create('figcaption', 'Versión anterior', previousFrame);
  create('figcaption', 'Versión actual', currentFrame);
  const previousImage = create('img', undefined, previousFrame);
  previousImage.alt = 'Imagen anterior de Draw Things';
  const image = create('img', undefined, currentFrame);
  image.alt = 'Última imagen generada por Draw Things';
  for (const photo of [previousImage, image]) {
    photo.style.cssText = 'display:none;max-width:100%;max-height:620px;object-fit:contain;border-radius:12px';
  }
  let previewUrl = null;
  let previousUrl = null;
  let imageType = 'image/png';
  let previousImageType = 'image/png';
  let profiles = {};

  const readJson = async (response) => {
    const body = await response.json();
    if (!response.ok) throw new Error(body.error || `HTTP ${response.status}`);
    return body;
  };
  const headers = () => ({'X-Barriga-Token': token});
  const setBusy = (busy) => {
    generate.disabled = busy; check.disabled = busy; preset.disabled = busy;
    steps.disabled = guidance.disabled = seed.disabled = busy;
    prompt.disabled = busy;
  };
  async function connect() {
    status.textContent = 'Comprobando Draw Things en tu Mac...';
    try {
      const response = await fetch('/api/drawthings/estado', {headers: headers()});
      const data = await readJson(response);
      status.textContent = 'Draw Things conectado · Modelo: ' + data.modelo;
    } catch (error) {
      status.textContent = error.message;
    }
  }

  preset.addEventListener('change', () => {
    prompt.value = profiles[preset.value]?.prompt || '';
  });
  check.addEventListener('click', connect);
  generate.addEventListener('click', async () => {
    setBusy(true);
    status.textContent = 'Generando una imagen de 1024 × 1024... Puede tardar varios minutos.';
    try {
      const response = await fetch('/api/drawthings/generar', {
        method: 'POST',
        headers: {...headers(), 'Content-Type': 'application/json'},
        body: JSON.stringify({
          preset: preset.value, prompt: prompt.value,
          steps: Number(steps.value), guidance_scale: Number(guidance.value),
          seed: Number(seed.value)
        })
      });
      if (!response.ok) throw new Error((await response.json()).error || `HTTP ${response.status}`);
      const data = await response.blob();
      if (data.type !== 'image/png' && data.type !== 'image/jpeg') throw new Error('Formato inesperado');
      const nextUrl = URL.createObjectURL(data);
      if (previousUrl) URL.revokeObjectURL(previousUrl);
      previousUrl = previewUrl;
      if (previousUrl) {
        previousImageType = imageType;
        previousImage.src = previousUrl;
        previousImage.style.display = 'block';
      }
      downloadPrevious.disabled = !previousUrl;
      previewUrl = nextUrl;
      imageType = data.type;
      image.src = nextUrl;
      image.style.display = 'block';
      download.disabled = false;
      status.textContent = 'Imagen lista. Compara ambas versiones, descarga la mejor o ajusta el prompt y repite.';
    } catch (error) {
      status.textContent = 'No se pudo generar: ' + error.message;
    } finally {
      setBusy(false);
    }
  });
  const downloadUrl = (url, mime, name) => {
    if (!url) return;
    const link = create('a');
    link.href = url;
    link.download = `barriga-${name}-${Date.now()}.${mime === 'image/png' ? 'png' : 'jpg'}`;
    link.click();
  };
  download.addEventListener('click', () => downloadUrl(previewUrl, imageType, 'actual'));
  downloadPrevious.addEventListener('click', () => downloadUrl(previousUrl, previousImageType, 'anterior'));
  window.addEventListener('pagehide', () => {
    if (previewUrl) URL.revokeObjectURL(previewUrl);
    if (previousUrl) URL.revokeObjectURL(previousUrl);
  });

  fetch('/api/drawthings/perfiles', {headers: headers()})
    .then(readJson)
    .then(data => {
      profiles = data.perfiles;
      Object.entries(profiles).forEach(([id, value]) => {
        const option = create('option', value.name, preset);
        option.value = id;
      });
      preset.value = 'planeta';
      prompt.value = profiles.planeta.prompt;
    })
    .catch(error => {status.textContent = 'No se cargaron los perfiles: ' + error.message;});
})();
