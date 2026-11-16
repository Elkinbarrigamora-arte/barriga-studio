const { test, expect } = require('@playwright/test');

const KEY = 'barriga-studio-projects-v1';
const FORMAT = 'barriga-studio-respaldo';
const templates = [
  'Frutas dramáticas 3D',
  'Fotorrealismo cinematográfico',
  'Animación 3D de personajes humanos'
];

async function saved(page) {
  return page.evaluate(k => JSON.parse(localStorage.getItem(k) || '[]'), KEY);
}
async function store(page, projects) {
  await page.evaluate(({k, projects}) => localStorage.setItem(k, JSON.stringify(projects)), {k: KEY, projects});
  await page.reload();
}
async function add(page, {name='Proyecto prueba', script='Gancho historia cierre', style=null, format=null, duration=null, voice=null}={}) {
  await page.locator('#name').fill(name);
  await page.locator('#script').fill(script);
  if (style) await page.locator('#style').selectOption({label:style});
  if (format) await page.locator('#format').selectOption({label:format});
  if (duration) await page.locator('#duration').selectOption({label:duration});
  if (voice) await page.locator('#voice').selectOption({label:voice});
  await page.getByRole('button', {name:'Guardar proyecto'}).click();
}
async function restore(page, data) {
  const picker = page.locator('#respaldo-herramientas input[type="file"]');
  await picker.setInputFiles({
    name:'backup.json', mimeType:'application/json',
    buffer: Buffer.from(typeof data === 'string' ? data : JSON.stringify(data))
  });
}
function backup(proyectos) {
  return {formato:FORMAT,version:1,proyectos};
}
function project(id,name,other={}) {
  return {id,name,script:'Gancho historia cierre',style:templates[0],
    format:'Vertical 9:16',duration:'30 segundos',voice:'Español masculino',
    date:'10/11/2026',...other};
}

test.beforeEach(async ({page}) => {
  await page.goto('/');
  await page.evaluate(k => localStorage.removeItem(k), KEY);
  await page.reload();
});

test.describe('Arranque, contrato visual y controles visibles', () => {
  test('01 título de página coherente', async ({page}) => {
    await expect(page).toHaveTitle(/Barriga Studio/i);
  });
  test('02 portada con marca', async ({page}) => {
    await expect(page.locator('#inicio h1')).toContainText('BARRIGA');
    await expect(page.locator('#inicio h1')).toContainText('STUDIO');
  });
  test('03 tres plantillas, no cuatro ni cero', async ({page}) => {
    await expect(page.locator('#plantillas article.card')).toHaveCount(3);
  });
  test('04 todos los botones tienen texto visible o accessible label', async ({page}) => {
    const buttons=await page.locator('button').all();
    for(const button of buttons) {
      const label = (await button.innerText()).trim() || await button.getAttribute('aria-label');
      expect(label, 'Un botón sin nombre accesible').toBeTruthy();
    }
  });
  test('05 todos los enlaces tienen destino', async ({page}) => {
    const hrefs=await page.locator('a').evaluateAll(els=>els.map(el=>el.getAttribute('href')));
    expect(hrefs.length).toBeGreaterThan(0);
    expect(hrefs.every(Boolean)).toBeTruthy();
  });
  test('06 todos los enlaces internos tienen sección destino', async ({page}) => {
    const errors=await page.locator('a[href^="#"]').evaluateAll(els=>
      els.map(a=>a.getAttribute('href')).filter(h=>!document.querySelector(h)));
    expect(errors).toEqual([]);
  });
  test('07 plantilla inicial seleccionada', async ({page}) => {
    await expect(page.locator('#style')).toHaveValue(templates[0]);
  });
  test('08 formato vertical inicial', async ({page}) => {
    await expect(page.locator('#format')).toHaveValue('Vertical 9:16');
  });
  test('09 selector de duración tiene opciones', async ({page}) => {
    await expect(page.locator('#duration option')).toHaveCount(2);
  });
  test('10 selector de voz muestra al usuario la limitación', async ({page}) => {
    await expect(page.locator('#voice option')).toHaveCount(3);
    await expect(page.locator('#voice')).toContainText('requiere motor');
  });
  test('11 vista previa no simula render neuronal', async ({page}) => {
    await expect(page.locator('.preview-frame')).toContainText('cuando se conecte un motor real');
  });
  test('12 contador editorial indica guion vacío', async ({page}) => {
    await expect(page.locator('#guion-analisis')).toContainText('0 palabras');
  });
  test('13 biblioteca vacía comunica estado', async ({page}) => {
    await expect(page.locator('#projectList')).toContainText('Todavía no hay proyectos');
  });
  test('14 herramientas respaldo existen', async ({page}) => {
    await expect(page.getByRole('button',{name:'Descargar respaldo JSON'})).toBeVisible();
    await expect(page.getByRole('button',{name:'Restaurar respaldo'})).toBeVisible();
  });
  test('15 título y guion tienen etiquetas vinculadas', async ({page}) => {
    await expect(page.locator('label[for="name"]')).toBeVisible();
    await expect(page.locator('label[for="script"]')).toBeVisible();
  });
});

test.describe('Navegación funcional', () => {
  for(const [idx,anchor] of ['#inicio','#plantillas','#crear','#proyectos'].entries()) {
    test(`navegación ${idx+1}: ${anchor} abre la sección real`, async ({page}) => {
      await page.locator(`nav a[href="${anchor}"]`).click();
      await expect(page).toHaveURL(new RegExp(anchor+'$'));
      await expect(page.locator(anchor)).toBeAttached();
    });
  }
  test('CTA principal abre creador', async ({page}) => {
    await page.locator('.hero a[href="#crear"]').first().click();
    await expect(page).toHaveURL(/#crear$/);
  });
  test('CTA de proyectos abre biblioteca', async ({page}) => {
    await page.locator('.hero a[href="#proyectos"]').click();
    await expect(page).toHaveURL(/#proyectos$/);
  });
});

test.describe('Plantillas, entradas y análisis editorial', () => {
  for(const [idx,template] of templates.entries()) {
    test(`plantilla ${idx+1}: elegir ${template}`, async ({page}) => {
      await page.locator('#plantillas .card').nth(idx).locator('button').click();
      await expect(page.locator('#style')).toHaveValue(template);
    });
  }
  for(const [idx,input] of [
    ['Gancho', '1 palabras'],
    ['Gancho historia cierre', '3 palabras'],
    ['Uno dos tres cuatro cinco seis', '6 palabras']
  ].entries()) {
    test(`análisis de texto ${idx+1}: ${input[0]}`, async ({page}) => {
      await page.locator('#script').fill(input[0]);
      await expect(page.locator('#guion-analisis')).toContainText(input[1]);
    });
  }
  test('guion completo reconoce estructura narrativa', async ({page}) => {
    await page.locator('#script').fill('GANCHO. HISTORIA. CIERRE.');
    await expect(page.locator('#guion-analisis')).toContainText('Contiene referencias');
  });
  test('guion parcial recomienda estructura', async ({page}) => {
    await page.locator('#script').fill('Historia');
    await expect(page.locator('#guion-analisis')).toContainText('Revisa gancho');
  });
  test('campo imagen acepta formatos de imagen', async ({page}) => {
    await expect(page.locator('#reference')).toHaveAttribute('accept','image/*');
  });
  test('selector cambia a horizontal', async ({page}) => {
    await page.locator('#format').selectOption({label:'Horizontal 16:9'});
    await expect(page.locator('#format')).toHaveValue('Horizontal 16:9');
  });
  test('selector cambia a 60 segundos', async ({page}) => {
    await page.locator('#duration').selectOption({label:'60 segundos'});
    await expect(page.locator('#duration')).toHaveValue('60 segundos');
  });
  test('selector cambia de voz', async ({page}) => {
    await page.locator('#voice').selectOption({label:'Español femenino'});
    await expect(page.locator('#voice')).toHaveValue('Español femenino');
  });
});

test.describe('Persistencia y edición de proyectos', () => {
  test('guarda un proyecto en localStorage', async ({page}) => {
    await add(page);
    expect(await saved(page)).toHaveLength(1);
  });
  test('conserva nombre y guion', async ({page}) => {
    await add(page,{name:'Viaje del vaquero',script:'El caballo corrió'});
    const rows=await saved(page);
    expect(rows[0]).toMatchObject({name:'Viaje del vaquero',script:'El caballo corrió'});
  });
  test('nombre vacío se convierte en título predeterminado', async ({page}) => {
    await add(page,{name:''});
    expect((await saved(page))[0].name).toBe('Proyecto sin título');
  });
  test('retiene registros al recargar el navegador', async ({page}) => {
    await add(page);
    await page.reload();
    await expect(page.locator('#projectList .project')).toHaveCount(1);
  });
  test('edición de proyecto abierto conserva mismo ID', async ({page}) => {
    await add(page);
    const id=(await saved(page))[0].id;
    await page.getByRole('button',{name:'Abrir'}).click();
    await page.locator('#script').fill('Nuevo guion corregido');
    await page.getByRole('button',{name:'Guardar proyecto'}).click();
    const stored=await saved(page);
    expect(stored).toHaveLength(1);
    expect(stored[0].id).toBe(id);
    expect(stored[0].script).toBe('Nuevo guion corregido');
  });
  test('guardar otro proyecto no elimina el anterior', async ({page}) => {
    await add(page,{name:'A'});
    await page.reload();
    await add(page,{name:'B'});
    expect((await saved(page)).map(p=>p.name).sort()).toEqual(['A','B']);
  });
  test('abrir proyecto restaura nombre y contenido', async ({page}) => {
    await add(page,{name:'Guardado',script:'Esta es una historia guardada'});
    await page.reload();
    await page.getByRole('button',{name:'Abrir'}).click();
    await expect(page.locator('#name')).toHaveValue('Guardado');
    await expect(page.locator('#script')).toHaveValue('Esta es una historia guardada');
  });
  test('abrir proyecto restaura plantilla, formato y voz', async ({page}) => {
    await add(page,{style:templates[2],format:'Horizontal 16:9',voice:'Español femenino'});
    await page.reload();
    await page.getByRole('button',{name:'Abrir'}).click();
    await expect(page.locator('#style')).toHaveValue(templates[2]);
    await expect(page.locator('#format')).toHaveValue('Horizontal 16:9');
    await expect(page.locator('#voice')).toHaveValue('Español femenino');
  });
  test('muestra la fecha del proyecto guardado', async ({page}) => {
    await add(page);
    await expect(page.locator('#projectList .project .muted')).not.toBeEmpty();
  });
  test('guardar informa el resultado', async ({page}) => {
    await add(page);
    await expect(page.locator('#notice')).toContainText('Proyecto guardado');
  });
});

test.describe('Duplicar, borrar y proteger contenido', () => {
  test('duplicar crea una nueva entrada', async ({page}) => {
    await add(page,{name:'Original'});
    await page.getByRole('button',{name:'Duplicar'}).first().click();
    expect(await saved(page)).toHaveLength(2);
  });
  test('duplicar conserva original y nombres diferenciados', async ({page}) => {
    await add(page,{name:'Original'});
    await page.getByRole('button',{name:'Duplicar'}).first().click();
    expect((await saved(page)).map(p=>p.name)).toEqual(['Original (copia)','Original']);
  });
  test('duplicar mantiene guion original', async ({page}) => {
    await add(page,{script:'Historia original'});
    await page.getByRole('button',{name:'Duplicar'}).first().click();
    expect((await saved(page)).map(p=>p.script)).toEqual(['Historia original','Historia original']);
  });
  test('duplicar asigna ID independiente', async ({page}) => {
    await add(page);
    await page.getByRole('button',{name:'Duplicar'}).first().click();
    const p=await saved(page);
    expect(String(p[0].id)).not.toBe(String(p[1].id));
  });
  test('cancelar eliminar conserva proyecto', async ({page}) => {
    await add(page);
    page.once('dialog',dialog=>dialog.dismiss());
    await page.getByRole('button',{name:'Eliminar'}).first().click();
    expect(await saved(page)).toHaveLength(1);
  });
  test('confirmar eliminar borra solo proyecto seleccionado', async ({page}) => {
    await add(page,{name:'A'});
    await page.reload();
    await add(page,{name:'B'});
    page.once('dialog',dialog=>dialog.accept());
    await page.getByRole('button',{name:'Eliminar'}).first().click();
    expect((await saved(page)).map(p=>p.name)).toEqual(['A']);
  });
  test('borrar actualiza lista', async ({page}) => {
    await add(page);
    page.once('dialog',dialog=>dialog.accept());
    await page.getByRole('button',{name:'Eliminar'}).first().click();
    await expect(page.locator('#projectList')).toContainText('Todavía no hay proyectos');
  });
});

test.describe('Respaldo exportación e importación sin pérdida', () => {
  test('descarga respaldo vacío válido', async ({page}) => {
    const pending=page.waitForEvent('download');
    await page.getByRole('button',{name:'Descargar respaldo JSON'}).click();
    const download=await pending;
    expect(download.suggestedFilename()).toMatch(/^barriga-studio-respaldo-.*\.json$/);
  });
  test('descarga respaldo sin borrar proyectos', async ({page}) => {
    await add(page);
    const pending=page.waitForEvent('download');
    await page.getByRole('button',{name:'Descargar respaldo JSON'}).click();
    await pending;
    expect(await saved(page)).toHaveLength(1);
  });
  test('descarga informa cantidad de proyectos', async ({page}) => {
    await add(page);
    await page.getByRole('button',{name:'Descargar respaldo JSON'}).click();
    await expect(page.locator('#respaldo-status')).toContainText('1 proyecto(s)');
  });
  test('restaurar añade proyectos', async ({page}) => {
    await restore(page,backup([project('r1','Restaurado')]));
    await expect(page.locator('#projectList')).toContainText('Restaurado');
    expect(await saved(page)).toHaveLength(1);
  });
  test('restaurar no elimina proyectos previos', async ({page}) => {
    await add(page,{name:'Anterior'});
    await restore(page,backup([project('r1','Importado')]));
    expect((await saved(page)).map(p=>p.name).sort()).toEqual(['Anterior','Importado']);
  });
  test('restaurar dos veces evita duplicados idénticos', async ({page}) => {
    await restore(page,backup([project('r1','Una vez')]));
    await restore(page,backup([project('r1','Una vez')]));
    expect(await saved(page)).toHaveLength(1);
  });
  test('colisión de ID importa sin sobrescribir', async ({page}) => {
    await store(page,[project('same','A')]);
    await restore(page,backup([project('same','B')]));
    const ps=await saved(page);
    expect(ps).toHaveLength(2);
    expect(new Set(ps.map(p=>String(p.id))).size).toBe(2);
  });
  test('JSON corrupto no modifica proyectos', async ({page}) => {
    await add(page);
    await restore(page,'{not json');
    await expect(page.locator('#respaldo-status')).toContainText('No se pudo importar');
    expect(await saved(page)).toHaveLength(1);
  });
  test('formato inválido no modifica proyectos', async ({page}) => {
    await add(page);
    await restore(page,{formato:'otro',version:1,proyectos:[]});
    await expect(page.locator('#respaldo-status')).toContainText('no es un respaldo JSON compatible');
    expect(await saved(page)).toHaveLength(1);
  });
  test('versión incompatible del backup es rechazada', async ({page}) => {
    await restore(page,{formato:FORMAT,version:99,proyectos:[]});
    await expect(page.locator('#respaldo-status')).toContainText('No se pudo importar');
  });
  test('carga con más de mil registros es rechazada', async ({page}) => {
    await restore(page,backup(Array.from({length:1001},(_,i)=>project('id'+i,'N'+i))));
    await expect(page.locator('#respaldo-status')).toContainText('demasiados proyectos');
    expect(await saved(page)).toHaveLength(0);
  });
  test('archivo mayor que 4 MB es rechazado', async ({page}) => {
    await restore(page,' '.repeat(4*1024*1024+1));
    await expect(page.locator('#respaldo-status')).toContainText('supera 4 MB');
  });
});

test.describe('Exportar guion y resistencia de la interfaz', () => {
  test('exporta archivo con extensión txt', async ({page}) => {
    const pending=page.waitForEvent('download');
    await page.getByRole('button',{name:'Exportar guion'}).click();
    const dl=await pending;
    expect(dl.suggestedFilename()).toBe('barriga-guion.txt');
  });
  test('exportar no modifica proyecto guardado', async ({page}) => {
    await add(page);
    const old=await saved(page);
    const pending=page.waitForEvent('download');
    await page.getByRole('button',{name:'Exportar guion'}).click();
    await pending;
    expect(await saved(page)).toEqual(old);
  });
  test('título con HTML se muestra como texto, no como elemento', async ({page}) => {
    await add(page,{name:'<img src=x onerror=alert(1)>'});
    await expect(page.locator('#projectList strong')).toContainText('<img src=x onerror=alert(1)>');
    await expect(page.locator('#projectList img')).toHaveCount(0);
  });
  test('guion con HTML no ejecuta etiquetas', async ({page}) => {
    await add(page,{script:'<script>alert(1)</script>'});
    await expect(page.locator('#projectList script')).toHaveCount(0);
  });
  test('localStorage corrupto no provoca página blanca', async ({page}) => {
    await page.evaluate(k=>localStorage.setItem(k,'{broken'), KEY);
    await page.reload();
    await expect(page.locator('#inicio h1')).toBeVisible();
  });
  test('campos funcionan después de recarga', async ({page}) => {
    await page.reload();
    await page.locator('#name').fill('Prueba posterior');
    await page.locator('#script').fill('Historia');
    await expect(page.locator('#name')).toHaveValue('Prueba posterior');
  });
  test('no hay error JS al cargar página nueva', async ({page}) => {
    const errors=[];
    page.on('pageerror',err=>errors.push(err.message));
    await page.reload();
    expect(errors).toEqual([]);
  });
});
