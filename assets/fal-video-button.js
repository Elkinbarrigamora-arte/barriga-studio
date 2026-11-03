/* B STUDIO: fal.ai video button for the local-only test bridge. */
(() => {
  "use strict";
  function start() {
    const editor = document.getElementById("crear");
    const script = document.getElementById("script");
    if (!editor || !script || document.getElementById("bstudio-fal-panel")) return;
    const panel = document.createElement("div");
    panel.id = "bstudio-fal-panel";
    panel.className = "panel";
    panel.style.cssText = "margin-top:16px;border:1px solid #c9a4ff";
    const header = document.createElement("h3");
    header.textContent = "🎬 Generar video neuronal · fal.ai (prueba)";
    const description = document.createElement("p");
    description.className = "muted";
    description.textContent = "Wan 2.2: imagen pública HTTPS + movimiento. Una solicitud puede costar aprox. US$0,15. No incluye voz ni montaje.";
    const imageLabel = document.createElement("label");
    imageLabel.textContent = "URL HTTPS de la imagen de referencia";
    const image = document.createElement("input");
    image.type = "url";
    image.placeholder = "https://.../personaje.png";
    image.autocomplete = "off";
    const promptLabel = document.createElement("label");
    promptLabel.textContent = "Movimiento de la escena";
    const prompt = document.createElement("textarea");
    prompt.rows = 3;
    prompt.placeholder = "El personaje camina y mueve los brazos, manteniendo su identidad...";
    const button = document.createElement("button");
    button.type = "button";
    button.className = "button";
    button.textContent = "Generar video (con confirmación de costo)";
    const status = document.createElement("p");
    status.className = "muted";
    status.setAttribute("role", "status");
    status.textContent = "Sin generación iniciada.";
    const video = document.createElement("video");
    video.controls = true;
    video.playsInline = true;
    video.style.cssText = "display:none;width:100%;margin-top:12px;border-radius:12px";
    const link = document.createElement("a");
    link.className = "button ghost";
    link.style.cssText = "display:none;margin-top:10px";
    link.textContent = "Abrir MP4 / Guardar como";
    link.rel = "noopener noreferrer";
    link.target = "_blank";
    button.addEventListener("click", async () => {
      const url = image.value.trim();
      const motion = prompt.value.trim();
      if (!/^https:\/\/[^\s]+$/i.test(url) || motion.length < 8) {
        status.textContent = "Escribe una URL HTTPS pública y una instrucción de movimiento.";
        return;
      }
      if (!confirm("Se enviará UNA generación de Wan 2.2 a fal.ai. Costo estimado: US$0,15. ¿Confirmas este gasto?")) return;
      button.disabled = true;
      status.textContent = "Generando en la nube. No cierres esta ventana ni envíes otra solicitud...";
      try {
        const response = await fetch("/api/fal/generate", {
          method: "POST",
          headers: {"Content-Type": "application/json", "X-Barriga-Fal-Token": window.BSTUDIO_FAL_TOKEN},
          body: JSON.stringify({image_url: url, prompt: motion, confirm_charge: true})
        });
        const result = await response.json();
        if (!response.ok) throw Error(result.error || ("HTTP " + response.status));
        video.src = result.video_url;
        video.style.display = "block";
        link.href = result.video_url;
        link.style.display = "inline-block";
        status.textContent = "Video recibido de " + result.model + ". Revisa y guarda el MP4; este prototipo aún no persiste el archivo.";
      } catch (err) {
        status.textContent = "Error: " + err.message + " No reintentes sin revisar primero los cargos en fal.";
      } finally {
        button.disabled = false;
      }
    });
    panel.append(header, description, imageLabel, image, promptLabel, prompt, button, status, video, link);
    editor.append(panel);
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start);
  else start();
})();
