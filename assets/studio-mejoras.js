/* Barriga Studio — herramientas de conservación de borradores y revisión editorial.
   No invoca servidores ni crea videos. Compatible con la clave legacy de localStorage. */
(() => {
  "use strict";
  const KEY = "barriga-studio-projects-v1";
  const FORMAT = "barriga-studio-respaldo";
  const styles = [
    "Frutas dramáticas 3D",
    "Fotorrealismo cinematográfico",
    "Animación 3D de personajes humanos"
  ];
  const formats = ["Vertical 9:16", "Horizontal 16:9"];
  const durations = ["30 segundos", "60 segundos"];
  const voices = [
    "Español femenino",
    "Español masculino",
    "Voces por personaje (requiere motor)"
  ];
  const stamp = () => new Date().toLocaleString("es-CO");
  const uniqueId = () =>
    (globalThis.crypto && typeof crypto.randomUUID === "function") ?
      crypto.randomUUID() : "restaurado-" + Date.now() + "-" + Math.random().toString(36).slice(2);
  const projectList = () => {
    let projects;
    try { projects = JSON.parse(localStorage.getItem(KEY) || "[]"); }
    catch { throw new Error("Los datos guardados están dañados. No se modificaron. Descarga una copia o pide ayuda."); }
    if (!Array.isArray(projects)) throw new Error("Formato de datos inesperado. No se modificaron proyectos.");
    return projects;
  };
  const clean = (project) => {
    if (!project || typeof project !== "object" || Array.isArray(project)) return null;
    const name = String(project.name || "Proyecto sin título").slice(0, 150).trim();
    const script = String(project.script || "").slice(0, 30000);
    const style = styles.includes(project.style) ? project.style : styles[0];
    const format = formats.includes(project.format) ? project.format : formats[0];
    const duration = durations.includes(project.duration) ? project.duration : durations[0];
    const voice = voices.includes(project.voice) ? project.voice : voices[0];
    const date = String(project.date || stamp()).slice(0, 100);
    return { id: (typeof project.id === "number" || typeof project.id === "string") ?
      project.id : uniqueId(), name, script, style, format, duration, voice, date };
  };
  const fingerprint = (p) => JSON.stringify([
    p.name, p.script, p.style, p.format, p.duration, p.voice
  ]);
  const status = (message, error = false) => {
    const el = document.getElementById("respaldo-status");
    if (el) {
      el.textContent = message;
      el.style.color = error ? "#ffb5b5" : "#c9efd7";
    }
  };
  function downloadFile(data, filename, mime) {
    const file = new Blob([data], {type: mime});
    const url = URL.createObjectURL(file);
    const link = document.createElement("a");
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    link.remove();
    setTimeout(() => URL.revokeObjectURL(url), 3000);
  }
  function exportBackup() {
    try {
      const projects = projectList();
      const backup = {
        formato: FORMAT,
        version: 1,
        exportado: new Date().toISOString(),
        almacenamiento: "navegador-local",
        proyectos: projects
      };
      const date = new Date().toISOString().slice(0, 10);
      downloadFile(JSON.stringify(backup, null, 2),
        "barriga-studio-respaldo-" + date + ".json", "application/json;charset=utf-8");
      status("Respaldo preparado: " + projects.length + " proyecto(s). Conserva el JSON en un lugar seguro.");
    } catch (error) { status(error.message, true); }
  }
  async function importBackup(file) {
    if (!file) return;
    if (file.size > 4 * 1024 * 1024) return status("El archivo supera 4 MB; no se importó.", true);
    try {
      const parsed = JSON.parse(await file.text());
      if (!parsed || parsed.formato !== FORMAT || parsed.version !== 1 ||
          !Array.isArray(parsed.proyectos))
        throw new Error("El archivo no es un respaldo JSON compatible de Barriga Studio.");
      if (parsed.proyectos.length > 1000) throw new Error("El respaldo tiene demasiados proyectos.");
      const existing = projectList();
      const before = existing.length;
      const ids = new Set(existing.map(p => String(p.id)));
      const fp = new Set(existing.map(p => fingerprint(clean(p) || p)));
      let repeated = 0;
      for (const item of parsed.proyectos) {
        const project = clean(item);
        if (!project) { repeated++; continue; }
        const signature = fingerprint(project);
        if (fp.has(signature)) { repeated++; continue; }
        if (ids.has(String(project.id))) project.id = uniqueId();
        ids.add(String(project.id));
        fp.add(signature);
        existing.push(project);
      }
      /* Una sola escritura: si falta espacio, el almacenamiento previo sigue intacto. */
      if (existing.length !== before) localStorage.setItem(KEY, JSON.stringify(existing));
      if (typeof window.render === "function") window.render();
      status("Restauración: " + (existing.length - before) +
        " añadidos; " + repeated + " repetidos u omitidos. No se sobrescribió ninguno.");
    } catch (error) { status("No se pudo importar: " + error.message, true); }
  }
  function deleteProject(id) {
    try {
      const projects = projectList();
      const selected = projects.find(p => String(p.id) === String(id));
      if (!selected) return;
      if (!confirm("¿Eliminar «" + String(selected.name).slice(0, 80) +
          "» de este navegador? Descarga un respaldo antes de borrar.")) return;
      const remaining = projects.filter(p => String(p.id) !== String(id));
      localStorage.setItem(KEY, JSON.stringify(remaining));
      /* No se borra el contenido que el usuario esté editando. */
      if (typeof activeId !== "undefined" && String(activeId) === String(id)) activeId = null;
      window.render();
      status("Proyecto eliminado de este navegador.");
    } catch (error) { status(error.message, true); }
  }
  function cloneProject(id) {
    try {
      const projects = projectList();
      const selected = projects.find(p => String(p.id) === String(id));
      if (!selected) return;
      const copy = {...selected, id: uniqueId(),
        name: String(selected.name || "Proyecto") + " (copia)", date: stamp()};
      projects.unshift(copy);
      localStorage.setItem(KEY, JSON.stringify(projects));
      window.render();
      status("Copia creada sin cambiar el original.");
    } catch (error) { status(error.message, true); }
  }
  function upgradeRows() {
    const root = document.getElementById("projectList");
    if (!root) return;
    let projects;
    try { projects = projectList(); } catch { return; }
    const rows = [...root.children].filter(n => n.classList.contains("project"));
    rows.forEach((row, index) => {
      const item = projects[index];
      if (!item) return;
      const actions = document.createElement("div");
      actions.style.cssText = "display:flex;flex-wrap:wrap;gap:6px";
      const duplicate = document.createElement("button");
      duplicate.className = "button ghost";
      duplicate.type = "button";
      duplicate.textContent = "Duplicar";
      duplicate.addEventListener("click", () => cloneProject(item.id));
      const remove = document.createElement("button");
      remove.className = "button ghost";
      remove.type = "button";
      remove.textContent = "Eliminar";
      remove.addEventListener("click", () => deleteProject(item.id));
      actions.append(duplicate, remove);
      row.append(actions);
    });
  }
  function installBackup() {
    const container = document.querySelector("#proyectos .panel");
    if (!container || document.getElementById("respaldo-herramientas")) return;
    const box = document.createElement("div");
    box.id = "respaldo-herramientas";
    box.style.cssText = "border-top:1px solid #ffffff44;margin-top:20px;padding-top:18px";
    const title = document.createElement("h3");
    title.textContent = "💾 Respaldo y recuperación";
    const desc = document.createElement("p");
    desc.className = "muted";
    desc.textContent = "Descarga una copia de tus proyectos antes de cambiar de equipo o navegador. Importar añade sin sobrescribir.";
    const exportButton = document.createElement("button");
    exportButton.type = "button"; exportButton.className = "button";
    exportButton.textContent = "Descargar respaldo JSON";
    exportButton.addEventListener("click", exportBackup);
    const importButton = document.createElement("button");
    importButton.type = "button"; importButton.className = "button ghost";
    importButton.textContent = "Restaurar respaldo";
    importButton.style.marginLeft = "8px";
    const picker = document.createElement("input");
    picker.type = "file"; picker.accept = ".json,application/json";
    picker.setAttribute("aria-label", "Archivo de respaldo JSON");
    picker.style.display = "none";
    importButton.addEventListener("click", () => picker.click());
    picker.addEventListener("change", async () => {
      await importBackup(picker.files && picker.files[0]);
      picker.value = "";
    });
    const report = document.createElement("p");
    report.id = "respaldo-status";
    report.className = "muted"; report.setAttribute("role", "status");
    report.textContent = "Tus datos continúan guardados solo en este navegador hasta que descargues un respaldo.";
    box.append(title, desc, exportButton, importButton, picker, report);
    container.append(box);
  }
  function installScriptReview() {
    const textarea = document.getElementById("script");
    if (!textarea || document.getElementById("guion-analisis")) return;
    const box = document.createElement("p");
    box.className = "muted";
    box.id = "guion-analisis";
    box.setAttribute("role", "status");
    textarea.insertAdjacentElement("afterend", box);
    function check() {
      const value = textarea.value.trim();
      const words = value ? value.split(/\s+/u).filter(Boolean).length : 0;
      const sec = Math.round(words / 2.5);
      const flags = ["gancho","historia","cierre"].filter(x =>
        value.toLocaleLowerCase("es").includes(x));
      box.textContent = words + " palabras · narración estimada: " + sec +
        " s (a 150 palabras/min). " + (words === 0 ?
          "Escribe el guion para analizarlo." :
          flags.length === 3 ? "Contiene referencias a gancho, historia y cierre." :
          "Revisa gancho (0–4 s), historia (4–32 s) y cierre (32–40 s).") +
        " La duración real requiere medir la voz.";
    }
    textarea.addEventListener("input", check);
    check();
  }
  function init() {
    installBackup();
    installScriptReview();
    if (typeof window.render === "function") {
      const existingRender = window.render;
      window.render = function (...args) {
        const result = existingRender.apply(this, args);
        upgradeRows();
        return result;
      };
      upgradeRows();
    }
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
  else init();
})();