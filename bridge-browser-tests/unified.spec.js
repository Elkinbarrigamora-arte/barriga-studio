const {test, expect} = require("@playwright/test");
const pane = p => p.locator("#bstudio-integrado");
test("01 abre el puente en una sola página", async ({page})=>{
  await page.goto("/");
  await expect(pane(page)).toBeVisible();
  await expect(page).toHaveTitle(/Barriga Studio/i);
});
test("02 conserva el editor y las tres plantillas existentes", async ({page})=>{
  await page.goto("/");
  await expect(page.locator("#script")).toBeAttached();
  await expect(page.locator("#plantillas .card")).toHaveCount(3);
});
test("03 añade Barriga IA sin eliminar guardado", async ({page})=>{
  await page.goto("/");
  await expect(pane(page).getByRole("button",{name:"Generar guion con Barriga IA"})).toBeAttached();
  await expect(page.getByRole("button",{name:"Guardar proyecto"})).toBeAttached();
});
test("04 Ollama offline no se representa como listo", async ({page})=>{
  await page.goto("/");
  await expect(pane(page).locator("#bst-engines")).toContainText("Barriga IA");
  await expect(pane(page).locator("#bst-script")).toBeDisabled();
});
test("05 se informa cuando la carpeta no tiene MP4", async ({page})=>{
  await page.goto("/");
  await expect(pane(page).locator("#bst-videos-status")).toContainText("No hay archivos MP4");
});
test("06 botón actualizar galería ejecuta consulta", async ({page})=>{
  await page.goto("/");
  const response = page.waitForResponse(r=>r.url().endsWith("/api/videos"));
  await pane(page).getByRole("button",{name:"Actualizar galería"}).click();
  expect((await response).status()).toBe(200);
});
test("07 consulta motores actualiza estado", async ({page})=>{
  await page.goto("/");
  const response = page.waitForResponse(r=>r.url().endsWith("/api/engines"));
  await pane(page).getByRole("button",{name:"Comprobar motores"}).click();
  expect((await response).status()).toBe(200);
});
test("08 recuperación rechaza identificador inválido sin llamar proveedor", async ({page})=>{
  await page.goto("/");
  await pane(page).locator("#bst-task").fill("no");
  await pane(page).getByRole("button",{name:"Consultar y recuperar MP4"}).click();
  await expect(pane(page).locator("#bst-recovery-status")).toContainText("válido");
});
test("09 el error de PoYo se presenta sin fingir una recuperación", async ({page})=>{
  await page.route("**/api/recover",async route=>route.fulfill({
    status:502,contentType:"application/json",
    body:JSON.stringify({error:"PoYo HTTP 403"})
  }));
  await page.goto("/");
  await pane(page).locator("#bst-task").fill("0AHQMX2G2T4ZZE6O");
  await pane(page).getByRole("button",{name:"Consultar y recuperar MP4"}).click();
  await expect(pane(page).locator("#bst-recovery-status")).toContainText("HTTP 403");
  await expect(pane(page).locator("#bst-recovery-status")).toContainText("No se generó otra tarea");
});
test("10 galería renderiza un video solo cuando recibe archivo listado", async ({page})=>{
  await page.route("**/api/videos", async route=>route.fulfill({
    status:200,contentType:"application/json",
    body:JSON.stringify({videos:[{filename:"video-real.mp4",bytes:30000,modified:1,type:"video"}]})
  }));
  await page.goto("/");
  await expect(pane(page).locator("video")).toHaveCount(1);
  await expect(pane(page).getByRole("link",{name:"Descargar video"})).toBeVisible();
});
test("11 medios usan sesión privada al construir la URL", async ({page})=>{
  await page.route("**/api/videos",async route=>route.fulfill({
    status:200,contentType:"application/json",
    body:JSON.stringify({videos:[{filename:"escena uno.mp4",bytes:30000,modified:1,type:"video"}]})
  }));
  await page.goto("/");
  const href=await pane(page).getByRole("link",{name:"Descargar video"}).getAttribute("href");
  expect(href).toContain("/media/escena%20uno.mp4?token=");
  expect(href).not.toContain("POYO_API_KEY");
});
test("12 no se añade botón de generación de pago ficticio",async ({page})=>{
  await page.goto("/");
  await expect(pane(page)).not.toContainText("Generar pagando");
});
test("13 la aplicación usa una sola instancia del panel",async ({page})=>{
  await page.goto("/");
  await expect(page.locator("#bstudio-integrado")).toHaveCount(1);
  await page.reload();
  await expect(page.locator("#bstudio-integrado")).toHaveCount(1);
});
test("14 guion generado actualiza el editor solo tras respuesta real",async ({page})=>{
  await page.route("**/api/engines",async route=>route.fulfill({
    status:200,contentType:"application/json",
    body:JSON.stringify({engines:[{id:"barriga-ia",name:"Barriga IA · Ollama",
      state:"ready",detail:"Modelo disponible"}]})
  }));
  await page.route("**/api/guion",async route=>route.fulfill({
    status:200,contentType:"application/json",
    body:JSON.stringify({gancho:"Gancho verdadero",historia:"Historia completa",
      oferta_cierre:"Cierre emotivo",modelo:"qwen2.5-coder:14b",segundos:1.2})
  }));
  await page.goto("/");
  await pane(page).locator("#bst-idea").fill("Historia del oeste");
  await pane(page).locator("#bst-script").click();
  await expect(pane(page).locator("#bst-output")).toHaveValue(/Historia completa/);
  await expect(page.locator("#script")).toHaveValue(/Gancho verdadero/);
});
