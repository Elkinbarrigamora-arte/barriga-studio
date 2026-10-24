/* Barriga Studio: capa de interfaz, sin migrar ni borrar proyectos existentes.
 * Reutiliza IDs y acciones legacy, no inventa generación de video ni voz. */
(() => {
  "use strict";
  const KEY = "barriga-studio-projects-v1";
  const FAVORITES = "barriga-studio-favorites-v1";
  const PREFS = "barriga-studio-ui-preferences-v1";
  const state = { filter: "todos", query: "", view: "list", mediaUrl: "", mediaName: "" };
  const $ = (s, root = document) => root.querySelector(s);
  const create = (tag, cls, label) => {
    const el = document.createElement(tag);
    if (cls) el.className = cls;
    if (label !== undefined) el.textContent = label;
    return el;
  };
  const read = (key, fallback) => {
    try {
      const value = JSON.parse(localStorage.getItem(key) || "null");
      return value && typeof value === "object" ? value : fallback;
    } catch { return fallback; }
  };
  const write = (key, value) => {
    try { localStorage.setItem(key, JSON.stringify(value)); return true; }
    catch { return false; }
  };
  const projects = () => {
    const arr = read(KEY, []);
    return Array.isArray(arr) ? arr : [];
  };
  const notify = (message) => {
    const el = $("#studio-ui-status");
    if (el) el.textContent = message;
  };
  const button = (label, className, handler) => {
    const b = create("button", className, label);
    b.type = "button";
    b.addEventListener("click", handler);
    return b;
  };

  function installHeader() {
    const header = $("header");
    if (!header || $(".studio-header-tools", header)) return;
    header.classList.add("studio-header");
    const tools = create("div", "studio-header-tools");
    const language = create("select", "studio-language");
    language.setAttribute("aria-label", "Idioma de la interfaz");
    [["es", "ES · Español"], ["en", "EN · English (pendiente)"]].forEach(([value, label]) => {
      const option = new Option(label, value);
      if (value === "en") option.disabled = true;
      language.add(option);
    });
    language.value = "es";
    const profile = button("Perfil", "studio-profile", () =>
      notify("El perfil de usuario requiere autenticación; los proyectos siguen siendo locales."));
    profile.setAttribute("aria-label", "Estado del perfil: acceso no disponible");
    tools.append(language, profile);
    header.append(tools);
  }

  function installHero() {
    const hero = $("#inicio");
    if (!hero) return;
    hero.classList.add("studio-cinematic");
    const stage = create("div", "studio-scene");
    stage.setAttribute("aria-label", "Decoración de frutas sobre una ciudad al atardecer");
    const city = create("div", "studio-city");
    city.setAttribute("aria-hidden", "true");
    stage.append(city);
    const sceneFruits = create("div", "studio-scene-fruits");
    [["🍓", "Fresa animada"], ["🍍", "Piña cinematográfica"], ["🍌", "Banano expresivo"]]
      .forEach(([emoji, name]) => {
        const figure = create("span", "studio-scene-fruit", emoji);
        figure.title = name;
        figure.setAttribute("role", "img");
        figure.setAttribute("aria-label", name);
        sceneFruits.append(figure);
      });
    stage.append(sceneFruits);
    hero.append(stage);
    const action = $(".hero > a.button:not(.ghost)", document);
    if (action) action.textContent = "Crear video con IA";
  }

  function installSteps() {
    const flow = $(".workflow");
    if (!flow) return;
    const steps = [
      ["Guion", "#crear"], ["Plantilla", "#plantillas"], ["Voz", "#voz"],
      ["Generar", "#vista-previa"], ["Descargar", "#vista-previa"]
    ];
    flow.replaceChildren();
    steps.forEach(([name, anchor], i) => {
      const link = create("a", "studio-step");
      link.href = anchor;
      link.textContent = String(i + 1).padStart(2, "0") + "  " + name;
      flow.append(link);
    });
    flow.setAttribute("aria-label", "Etapas de creación");
  }

  function installWorkspace() {
    const workspace = $(".workspace");
    const creator = $("#crear");
    const templates = $("#plantillas");
    if (!workspace || !creator || !templates) return;
    workspace.classList.add("studio-workspace");
    creator.classList.add("studio-col", "studio-script");
    templates.classList.add("studio-col", "studio-templates");
    const templateTitle = $("h2", templates);
    if (templateTitle) templateTitle.textContent = "Plantillas";
    const templateIntro = $("p", templates);
    if (templateIntro) templateIntro.textContent = "Selecciona una estética para el proyecto";
    creator.insertBefore(create("p", "studio-section-sub", "Idea, formato y referencias"), $(".panel", creator));
    const panel = $(".panel", creator);
    const fields = $(".fields", panel);
    if (!panel || !fields) return;
    const mainTitle = $("h2", creator);
    if (mainTitle) mainTitle.textContent = "Guion";
    const move = (id, target) => {
      const input = document.getElementById(id);
      const group = input && input.parentElement;
      if (group) target.append(group);
      return input;
    };
    workspace.insertBefore(creator, templates);

    const voice = create("section", "studio-col studio-voice");
    voice.id = "voz";
    voice.append(create("h2", "", "Voz y música"));
    voice.append(create("p", "studio-section-sub", "Preferencias para el futuro motor de audio"));
    const voicePanel = create("div", "panel studio-voice-panel");
    voice.append(voicePanel);

    const preview = create("section", "studio-col studio-preview");
    preview.id = "vista-previa";
    preview.append(create("h2", "", "Vista previa"));
    preview.append(create("p", "studio-section-sub", "Reproductor de archivos reales"));
    const previewPanel = create("div", "panel studio-preview-panel");
    preview.append(previewPanel);
    workspace.append(voice, preview);

    const oldStyle = move("style", templates);
    if (oldStyle) oldStyle.parentElement.classList.add("studio-style-select");
    const oldVoice = move("voice", voicePanel);
    if (oldVoice) oldVoice.parentElement.classList.add("studio-voice-select");

    // Evitar controles duplicados: reutilizar el reproductor y botones originales.
    const frame = $(".preview-frame", panel);
    if (frame) {
      frame.classList.add("studio-preview-placeholder");
      previewPanel.append(frame);
    }
    [...panel.querySelectorAll(":scope > p")].forEach((p) => previewPanel.append(p));
    const saveButton = [...previewPanel.querySelectorAll('button')].find(b => b.textContent.trim() === 'Guardar proyecto');
    if (saveButton) saveButton.textContent = 'Guardar en Mis proyectos';
    const header = create("div", "studio-panel-top");
    header.append(create("span", "", "Historia"));
    const chars = create("span", "studio-char-count", "0 caracteres");
    chars.id = "studio-char-count";
    header.append(chars);
    const scriptGroup = $("#script") && $("#script").parentElement;
    if (scriptGroup) scriptGroup.prepend(header);
    const script = $("#script");
    if (script) {
      const counter = () => { chars.textContent = script.value.length + " caracteres"; };
      script.addEventListener("input", counter);
      counter();
    }

    const ai = button("✦ Completar con IA", "studio-ai-btn", () => {
      const bridge = [...document.querySelectorAll("button")].find(b =>
        b !== ai && b.textContent.includes("Generar y validar guion"));
      if (!bridge) return notify("Completar con IA requiere iniciar el puente local con Ollama. No se generó texto.");
      bridge.scrollIntoView({behavior: "smooth", block: "center"});
      bridge.click();
    });
    ai.id = "studio-completar-ia";
    if (scriptGroup) scriptGroup.append(ai);

    const upload = $("#reference");
    if (upload) {
      upload.setAttribute("accept", "image/png,image/jpeg,image/webp");
      upload.setAttribute("aria-label", "Seleccionar imagen de referencia PNG, JPG o WebP");
      const thumb = create("div", "studio-ref-preview");
      thumb.setAttribute("role", "status");
      upload.parentElement.append(thumb);
      let lastUrl = null;
      upload.addEventListener("change", () => {
        if (lastUrl) { URL.revokeObjectURL(lastUrl); lastUrl = null; }
        thumb.replaceChildren();
        const file = upload.files && upload.files[0];
        if (!file) return;
        if (!["image/png", "image/jpeg", "image/webp"].includes(file.type) ||
            file.size > 5 * 1024 * 1024) {
          upload.value = "";
          return notify("La referencia debe ser PNG, JPG o WebP y pesar como máximo 5 MB.");
        }
        lastUrl = URL.createObjectURL(file);
        const img = create("img", "studio-ref-thumbnail");
        img.src = lastUrl;
        img.alt = "Miniatura de referencia seleccionada";
        thumb.append(img, create("span", "studio-ref-name", file.name + " · referencia local, no subida"));
        notify("Referencia cargada solo para visualización local. El motor de imagen todavía no está conectado.");
      });
    }

    // Plantillas reales: selección funcional, sin fingir que existe un motor 3D.
    const cards = [...templates.querySelectorAll(".card")];
    function highlightCards() {
      const selected = $("#style")?.value;
      cards.forEach((card, i) => {
        const options = ["Frutas dramáticas 3D", "Fotorrealismo cinematográfico",
          "Animación 3D de personajes humanos"];
        const active = selected === options[i];
        card.classList.toggle("studio-active", active);
        card.setAttribute("aria-selected", String(active));
        card.setAttribute("aria-label", options[i] + " — motor de video no disponible");
      });
    }
    cards.forEach(card => {
      card.classList.add("studio-template-card");
      const badge = create("span", "studio-engine-state", "Motor de video pendiente");
      card.append(badge);
      card.addEventListener("click", e => {
        if (e.target.closest("button")) return;
        const index = cards.indexOf(card);
        const sel = $("#style");
        if (sel) {
          sel.selectedIndex = index;
          sel.dispatchEvent(new Event("change", {bubbles: true}));
        }
      });
    });
    if (oldStyle) oldStyle.addEventListener("change", highlightCards);
    cards.forEach(card => {
      const b = $("button", card);
      if (b) b.addEventListener("click", () => setTimeout(highlightCards, 0));
    });
    highlightCards();

    const prefs = read(PREFS, {});
    const language = create("div", "studio-preference");
    const languageLabel = create("label", "", "Idioma de narración");
    languageLabel.htmlFor = "studio-narration-language";
    const languageSelect = create("select", "");
    languageSelect.id = "studio-narration-language";
    [["es-CO", "Español · Colombia"], ["es-419", "Español · Latinoamérica"]]
      .forEach(([value, label]) => languageSelect.add(new Option(label, value)));
    languageSelect.value = prefs.language === "es-419" ? "es-419" : "es-CO";
    language.append(languageLabel, languageSelect);
    voicePanel.prepend(language);

    const musicGroup = create("div", "studio-preference");
    const musicLabel = create("label", "", "Música de fondo");
    musicLabel.htmlFor = "studio-music";
    const musicSelect = create("select", "");
    musicSelect.id = "studio-music";
    [["none", "Sin música"], ["cinematic", "Cinemática (preferencia)"],
      ["soft", "Suave (preferencia)"]].forEach(([value, label]) =>
        musicSelect.add(new Option(label, value)));
    musicSelect.value = ["cinematic", "soft"].includes(prefs.music) ? prefs.music : "none";
    musicGroup.append(musicLabel, musicSelect);
    voicePanel.append(musicGroup);
    const persistence = () => {
      const ok = write(PREFS, {language: languageSelect.value, music: musicSelect.value});
      if (!ok) notify("No fue posible conservar las preferencias de narración.");
    };
    languageSelect.addEventListener("change", persistence);
    musicSelect.addEventListener("change", persistence);
    voicePanel.append(create("p", "studio-capability-note",
      "Voz y música: configuración de proyecto. La síntesis y la mezcla de audio no están verificadas."));

    const player = create("video", "studio-video");
    player.id = "studio-video";
    player.controls = true;
    player.playsInline = true;
    player.preload = "metadata";
    player.setAttribute("aria-label", "Reproductor de video local");
    player.style.display = "none";
    previewPanel.prepend(player);

    const openMedia = create("label", "studio-media-picker", "Abrir video existente");
    const picker = create("input", "");
    picker.type = "file";
    picker.accept = "video/mp4,video/webm";
    picker.id = "studio-local-video";
    openMedia.htmlFor = picker.id;
    const mediaHint = create("p", "studio-capability-note", "Sin archivo de video generado. Puedes revisar un MP4 o WebM local.");
    previewPanel.append(openMedia, picker, mediaHint);
    const download = button("Descargar video", "studio-download", () => {
      if (!state.mediaUrl) return;
      const a = create("a");
      a.href = state.mediaUrl;
      a.download = state.mediaName || "barriga-video.mp4";
      a.click();
    });
    download.disabled = true;
    previewPanel.append(download);
    const generate = button("Generar video", "studio-generate", () =>
      notify("No hay motor de generación de video real conectado. Se conservará el guion sin simular archivos."));
    generate.disabled = true;
    generate.title = "Pendiente: motor de video real verificado";
    previewPanel.append(generate);
    picker.addEventListener("change", () => {
      if (state.mediaUrl) URL.revokeObjectURL(state.mediaUrl);
      state.mediaUrl = "";
      download.disabled = true;
      player.removeAttribute("src");
      player.load();
      player.style.display = "none";
      if (frame) frame.style.display = "";
      const file = picker.files && picker.files[0];
      if (!file) return;
      if (!["video/mp4", "video/webm"].includes(file.type) || file.size > 200 * 1024 * 1024) {
        picker.value = "";
        return notify("El video debe ser MP4 o WebM y pesar menos de 200 MB.");
      }
      state.mediaUrl = URL.createObjectURL(file);
      state.mediaName = file.name;
      player.src = state.mediaUrl;
      player.style.display = "block";
      if (frame) frame.style.display = "none";
      download.disabled = false;
      mediaHint.textContent = "Archivo local abierto: " + file.name + ". No fue generado por Barriga IA.";
      notify("Video local listo para reproducción y descarga. No se guardó ni generó en el servidor.");
    });
  }

  function installProjects() {
    const root = $("#projectList");
    const section = $("#proyectos");
    if (!root || !section || $("#studio-project-tools")) return;
    section.classList.add("studio-project-section");
    const panel = $(".panel", section);
    const tools = create("div", "studio-project-tools");
    tools.id = "studio-project-tools";
    const filters = create("div", "studio-project-filters");
    [["todos", "Todos"], ["proceso", "En proceso"],
      ["completados", "Completados"], ["favoritos", "Favoritos"]].forEach(([id, name]) => {
      const item = button(name, "studio-filter", () => {
        state.filter = id;
        decorate();
      });
      item.dataset.filter = id;
      filters.append(item);
    });
    const search = create("input", "studio-project-search");
    search.id = "studio-project-search";
    search.type = "search";
    search.placeholder = "Buscar proyectos";
    search.setAttribute("aria-label", "Buscar por nombre de proyecto");
    search.addEventListener("input", () => { state.query = search.value.toLocaleLowerCase("es").trim(); decorate(); });
    const views = create("div", "studio-project-view");
    const listView = button("☷ Lista", "studio-view-btn", () => { state.view = "list"; decorate(); });
    const gridView = button("▦ Cuadrícula", "studio-view-btn", () => { state.view = "grid"; decorate(); });
    views.append(listView, gridView);
    const newProject = button("+ Nuevo proyecto", "studio-new-project", () => {
      const script = $("#script");
      if (script && script.value.trim() && !confirm(
        "¿Crear un nuevo proyecto? Guarda primero los cambios actuales que quieras conservar.")) return;
      if (typeof activeId !== "undefined") activeId = null;
      ["name", "script", "reference"].forEach(id => {
        const input = document.getElementById(id);
        if (input) input.value = "";
      });
      if (script) {
        script.dataset.ideaOriginal = "";
        script.dataset.ultimoGuion = "";
        script.dispatchEvent(new Event("input", {bubbles: true}));
      }
      const name = $("#name");
      if (name) name.focus();
      $("#crear")?.scrollIntoView({behavior: "smooth"});
      notify("Nuevo borrador. Los proyectos ya guardados permanecen intactos.");
    });
    tools.append(filters, search, views, newProject);
    panel.insertBefore(tools, root);

    function decorate() {
      const favorites = read(FAVORITES, {});
      const list = projects();
      const rows = [...root.children].filter(n => n.classList.contains("project"));
      const grid = state.view === "grid";
      root.classList.toggle("studio-project-grid", grid);
      views.querySelectorAll("button").forEach((el, i) =>
        el.setAttribute("aria-pressed", String((i === 0) === !grid)));
      filters.querySelectorAll("button").forEach(b =>
        b.setAttribute("aria-pressed", String(b.dataset.filter === state.filter)));
      rows.forEach((row, idx) => {
        const p = list[idx];
        if (!p) return;
        const id = String(p.id);
        const trueState = (p.status === "en_proceso" || p.status === "procesando") ?
          "En proceso" : p.status === "completado" && p.videoFile ? "Completado" : "Borrador";
        const starred = !!favorites[id];
        const match = (state.filter === "todos" ||
          (state.filter === "proceso" && trueState === "En proceso") ||
          (state.filter === "completados" && trueState === "Completado") ||
          (state.filter === "favoritos" && starred));
        const found = String(p.name || "").toLocaleLowerCase("es").includes(state.query);
        row.hidden = !(match && found);
        row.classList.add("studio-project-card");
        if (!$(".studio-project-thumb", row)) {
          const thumb = create("div", "studio-project-thumb",
            p.style === "Fotorrealismo cinematográfico" ? "🎬" :
            p.style === "Animación 3D de personajes humanos" ? "🎭" : "🍌");
          thumb.setAttribute("aria-label", "Ilustración de plantilla, no miniatura de video generado");
          row.prepend(thumb);
        }
        const info = row.querySelector("div:not(.studio-project-thumb):not(.studio-project-actions)");
        let meta = $(".studio-project-meta", row);
        if (!meta) {
          meta = create("span", "studio-project-meta");
          if (info) info.append(meta);
        }
        meta.textContent = (p.duration || "Duración no definida") + " · " + trueState;
        let star = $(".studio-project-star", row);
        if (!star) {
          star = button("☆", "studio-project-star", () => {
            const current = read(FAVORITES, {});
            if (current[id]) delete current[id];
            else current[id] = true;
            if (write(FAVORITES, current)) decorate();
            else notify("No se pudo guardar el favorito.");
          });
          row.append(star);
        }
        star.textContent = starred ? "★ Favorito" : "☆ Favorito";
        star.setAttribute("aria-pressed", String(starred));
        let actions = $(".studio-project-menu", row);
        if (!actions) {
          actions = create("details", "studio-project-menu");
          const summary = create("summary", "", "···");
          summary.setAttribute("aria-label", "Acciones del proyecto");
          actions.append(summary);
          // Se reutilizan los botones de abrir, duplicar y eliminar ya existentes.
          const buttons = [...row.querySelectorAll(":scope > button, :scope > div > button")];
          buttons.filter(b => b !== star).forEach(b => actions.append(b));
          const originalActions = row.querySelector(".studio-project-actions");
          if (originalActions && !originalActions.children.length) originalActions.remove();
          row.append(actions);
        }
      });
      let empty = $("#studio-project-empty");
      if (!empty) {
        empty = create("p", "studio-project-empty");
        empty.id = "studio-project-empty";
        root.after(empty);
      }
      const matching = rows.filter(row => !row.hidden).length;
      empty.textContent = matching ? "" : "No hay proyectos para este filtro. Los borradores existentes no se han modificado.";
    }

    if (typeof window.render === "function") {
      const original = window.render;
      window.render = function (...args) {
        const output = original.apply(this, args);
        decorate();
        return output;
      };
    }
    decorate();
  }

  function init() {
    if ($("#studio-project-tools")) return;
    const status = create("p", "studio-ui-status");
    status.id = "studio-ui-status";
    status.setAttribute("role", "status");
    const main = $("main");
    if (main) main.append(status);
    installHeader();
    installHero();
    installSteps();
    installWorkspace();
    installProjects();
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
  else init();
})();
