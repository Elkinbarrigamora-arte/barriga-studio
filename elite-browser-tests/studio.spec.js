const {test,expect}=require("@playwright/test");
const pane=page=>page.locator("#bstudio-integrado");

test("01 se usa la única dirección oficial /studio y no un segundo frontend",async({page})=>{
 await page.goto("/studio");
 await expect(page).toHaveTitle("B STUDIOS ÉLITE — Producción activa");
 await expect(page.locator("h1")).toHaveText("B STUDIOS ÉLITE");
 await expect(pane(page)).toBeVisible();
});
test("02 permanece el editor original y el botón previo de guardar",async({page})=>{
 await page.goto("/studio");
 await expect(page.locator("#script")).toBeAttached();
 await page.locator("#old-save").click();
 await expect(page.locator("#old-status")).toHaveText("Proyecto original conservado");
});
test("03 el estado previo conserva su origen y persiste tras recargar",async({page})=>{
 await page.goto("/studio");
 await page.locator("#old-save").click();
 await page.reload();
 expect(await page.evaluate(()=>localStorage.getItem("original-demo"))).toBe("OK");
 await expect(pane(page)).toHaveCount(1);
});
test("04 los endpoints originales no son interceptados por el nuevo puente",async({page})=>{
 await page.goto("/studio");
 const data=await page.evaluate(async()=>{
  const r=await fetch("/api/legacy-health");
  return r.json();
 });
 expect(data.legacy).toBe(true);
});
test("05 el nuevo panel usa prefijo reservado y no reemplaza rutas antiguas",async({page})=>{
 await page.goto("/studio");
 const endpoints=await page.evaluate(async()=>{
  const old=await fetch("/api/projects");
  const script=document.querySelector('script[src="/_bstudio/assets/bstudio-runtime.js"]');
  return {old:old.status,prefix:script?.dataset.apiBase}
 });
 expect(endpoints).toEqual({old:200,prefix:"/_bstudio"});
});
test("06 generador de guiones no se habilita si Ollama está desconectado",async({page})=>{
 await page.goto("/studio");
 await expect(pane(page).locator("#bst-script")).toBeDisabled();
 await expect(pane(page).locator("#bst-engines")).toContainText("Barriga IA");
});
test("07 no inventar videos si la galería no tiene archivos",async({page})=>{
 await page.route("**/_bstudio/api/videos",async route=>route.fulfill({
  status:200,contentType:"application/json",body:JSON.stringify({videos:[]})
 }));
 await page.goto("/studio");
 await expect(pane(page).locator("#bst-videos-status")).toContainText("No hay archivos MP4");
});
test("08 botón de importar enlaza con backend y crea copia visible",async({page})=>{
 await page.goto("/studio");
 const filename="video-intacto-"+Math.floor(Math.random()*1e9)+".mp4";
 const bytes=Buffer.concat([Buffer.from([0,0,0,24]),Buffer.from("ftypisom"),Buffer.alloc(65,15)]);
 await pane(page).locator("#bst-upload").setInputFiles({name:filename,mimeType:"video/mp4",buffer:bytes});
 await pane(page).getByRole("button",{name:"Importar video sin generar otro"}).click();
 await expect(pane(page).locator("#bst-import-status")).toContainText("MP4 importado");
 await expect(pane(page).locator(".video-card strong",{hasText:filename})).toBeVisible();
});
test("09 no presentar como conectado el banco de voces sin ruta",async({page})=>{
 await page.goto("/studio");
 await expect(pane(page).locator("#bst-voices-status")).toContainText("aún no está configurada");
});
test("10 recuperación PoYo muestra el error remoto sin reenvíos",async({page})=>{
 await page.route("**/_bstudio/api/recover",async route=>route.fulfill({
  status:502,contentType:"application/json",body:JSON.stringify({error:"PoYo 401/403"})
 }));
 await page.goto("/studio");
 await pane(page).locator("#bst-task").fill("0AHQMX2G2T4ZZE6O");
 await pane(page).getByRole("button",{name:"Consultar y recuperar MP4"}).click();
 await expect(pane(page).locator("#bst-recovery-status")).toContainText("401/403");
 await expect(pane(page).locator("#bst-recovery-status")).toContainText("No se generó otra tarea");
});
test("11 no hay iframe ni sustitución completa de la plataforma",async({page})=>{
 await page.goto("/studio");
 await expect(page.locator("iframe")).toHaveCount(0);
 await expect(page.locator("#crear")).toBeVisible();
 await expect(page.getByRole("heading",{name:"Estudio central original"})).toBeVisible();
});
test("12 la API nueva requiere sesión autorizada",async({page})=>{
 await page.goto("/studio");
 const status=await page.evaluate(async()=>(
  await fetch("/_bstudio/api/videos",{credentials:"omit"})
 ).status);
 expect(status).toBe(403);
});
