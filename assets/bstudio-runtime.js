/* B STUDIO: one local workspace for scripts and actual media. */
(()=>{
"use strict";
const config=window.__BSTUDIO_BRIDGE__;
if(!config || typeof config.token!=="string") return;
const token=config.token;
const knownId=config.taskId||"";
function mount(){
 if(document.getElementById("bstudio-integrado"))return;
 const host=document.createElement("section");
 host.id="bstudio-integrado";
 host.style.cssText="display:block;grid-column:1/-1;width:100%;margin:24px 0";
 const root=host.attachShadow({mode:"open"});
 root.innerHTML=`
 <style>
 :host{display:block;color:#f5f4ff;font:15px system-ui,-apple-system,sans-serif}
 *,*:before,*:after{box-sizing:border-box}
 .panel{background:linear-gradient(140deg,#121b30,#231435);border:1px solid #6e5da8;border-radius:18px;padding:20px;box-shadow:0 18px 45px #0003}
 h2{font-size:22px;margin:0 0 5px;color:#ffda66}h3{font-size:17px;margin:0 0 10px}
 p{font-size:13px;color:#d8d3e4;line-height:1.5;margin:5px 0 13px}
 .layout{display:grid;grid-template-columns:1fr 1fr;gap:20px}.wide{grid-column:1/-1}
 textarea,input{background:#070d20;border:1px solid #8b7bad;color:white;border-radius:10px;padding:11px;width:100%;font:inherit}
 textarea{min-height:90px;resize:vertical}
 button{background:#ffda4d;border:0;border-radius:8px;padding:10px 14px;font:700 13px system-ui;cursor:pointer;color:#181326}
 button.secondary{background:#353052;color:white;border:1px solid #968aba}button:disabled{opacity:.4;cursor:not-allowed}
 .actions{display:flex;flex-wrap:wrap;gap:8px;margin:10px 0}
 .status{font-size:13px;padding:8px 10px;background:#0b1122;border-radius:10px;min-height:32px;white-space:pre-wrap;overflow-wrap:anywhere}
 .engines{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px}
 .engine{border:1px solid #5e5578;padding:9px;border-radius:11px;background:#181c33}
 .engine strong{font-size:13px;display:block}.engine small{color:#c6bfd7;line-height:1.4}
 .engine em{font-style:normal;color:#ffda77;font-size:12px;display:block;margin:4px 0}
 .videos{display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:12px;margin-top:10px}
 .video-card{border:1px solid #7d7097;border-radius:12px;padding:9px;min-width:0}
 .video-card video{width:100%;border-radius:8px;aspect-ratio:9/16;max-height:310px;background:#070d20}
 .video-card strong{font-size:12px;overflow-wrap:anywhere;display:block}
 .video-card a{color:#ffe37a;display:inline-block;margin-top:7px;font-size:13px}
 #bst-output{min-height:100px}label{display:block;margin-bottom:6px;font-weight:600}
 @media(max-width:740px){.layout,.engines{grid-template-columns:1fr}.panel{padding:14px}}
 </style>
 <div class="panel">
 <h2>🎬 B STUDIO · Centro de producción local</h2>
 <p>Barriga IA, archivos MP4 existentes y registro de motores. Consultar videos anteriores no crea generaciones de pago.</p>
 <div class="layout">
 <div><h3>🧠 Barriga IA · Guiones</h3>
 <label for="bst-idea">Idea de tu historia</label>
 <textarea id="bst-idea" maxlength="2400" placeholder="Describe personajes, historia y final..."></textarea>
 <div class="actions"><button id="bst-script" disabled>Generar guion con Barriga IA</button>
 <button id="bst-check" class="secondary">Comprobar motores</button></div>
 <div class="status" id="bst-script-status" role="status">Verificando Ollama...</div>
 <label for="bst-output" style="margin-top:12px">Resultado del guion</label>
 <textarea id="bst-output" readonly placeholder="El guion generado aparecerá aquí."></textarea>
 </div>
 <div><h3>⚙️ Motores y voces</h3>
 <div id="bst-engines" class="engines" aria-live="polite">Comprobando los servicios conectados...</div></div>
 <div class="wide"><h3>🎙️ Biblioteca de voces existentes</h3>
 <p>Escucha y reutiliza tus archivos de audio originales, sin generar voces nuevas.</p>
 <div class="actions"><button id="bst-refresh-voices" class="secondary">Actualizar voces</button></div>
 <div class="status" id="bst-voices-status" role="status">Comprobando el banco de voces...</div>
 <div class="videos" id="bst-voices"></div></div>
 <div class="wide"><h3>🎞️ Videos generados · Galería MP4</h3>
 <p>Se muestran únicamente videos reales descargados a la carpeta de producciones de la Mac.</p>
 <div class="actions"><button id="bst-refresh" class="secondary">Actualizar galería</button></div>
 <label for="bst-upload">Importar MP4 existente desde mi Mac</label>
 <input id="bst-upload" type="file" accept="video/mp4,.mp4" />
 <div class="actions"><button id="bst-import">Importar video sin generar otro</button></div>
 <p>Se crea una copia en la galería local. Tu archivo original se conserva; máximo 250 MB.</p>
 <div class="status" id="bst-import-status" role="status">Selecciona un MP4 que ya tengas descargado.</div>
 <div class="status" id="bst-videos-status" role="status">Buscando MP4...</div>
 <div class="videos" id="bst-videos"></div></div>
 <div class="wide"><h3>☁️ Recuperar video existente de PoYo</h3>
 <label for="bst-task">Identificador de tarea PoYo</label>
 <input id="bst-task" maxlength="100" placeholder="ID de una tarea ya creada"/>
 <div class="actions"><button id="bst-recover">Consultar y recuperar MP4</button></div>
 <div class="status" id="bst-recovery-status" role="status">Nunca inicia una generación nueva.</div>
 </div></div></div>
 `;
 const target=document.querySelector("#crear")||document.querySelector("main")||document.body;
 target.appendChild(host);
 const el=id=>root.getElementById(id);
 const api=async(path,options={})=>{
   const resp=await fetch(path,{...options,
     headers:{"X-Barriga-Token":token,...(options.headers||{})}});
   const payload=await resp.json();
   if(!resp.ok)throw Error(payload.error||"HTTP "+resp.status);
   return payload;
 };
 const engines=el("bst-engines"),script=el("bst-script");
 const scriptStatus=el("bst-script-status"),recover=el("bst-recover");
 const recoveryStatus=el("bst-recovery-status");
 const task=el("bst-task");
 task.value=knownId||localStorage.getItem("bstudio-poyo-task-id")||"";
 async function updateEngines(){
  script.disabled=true;engines.textContent="Verificando motores...";
  try{
   const data=await api("/api/engines");
   engines.replaceChildren();
   for(const engine of data.engines){
    const block=document.createElement("div");block.className="engine";
    const name=document.createElement("strong");name.textContent=engine.name;
    const state=document.createElement("em");state.textContent=engine.state;
    const detail=document.createElement("small");detail.textContent=engine.detail||"";
    block.append(name,state,detail);engines.append(block);
    if(engine.id==="barriga-ia"){
      script.disabled=engine.state!=="ready";
      scriptStatus.textContent=engine.state==="ready"?
        "Ollama listo para generar guiones reales.":engine.detail+" Activa Ollama y comprueba de nuevo.";
    }
   }
  }catch(err){engines.textContent="No se pudo consultar motores: "+err.message;
    scriptStatus.textContent="Barriga IA sin conexión comprobada.";}
 }
 async function updateVideos(){
  const status=el("bst-videos-status"),gallery=el("bst-videos");
  status.textContent="Buscando videos existentes...";
  try{
   const data=await api("/api/videos");
   gallery.replaceChildren();
   status.textContent=data.videos.length?
    data.videos.length+" video(s) disponibles.":"No hay archivos MP4 en la carpeta de producción. El video remoto no se simula como descargado.";
   for(const vid of data.videos){
    const url="/media/"+encodeURIComponent(vid.filename)+"?token="+encodeURIComponent(token);
    const card=document.createElement("div");card.className="video-card";
    const player=document.createElement("video");
    player.controls=true;player.preload="metadata";player.playsInline=true;player.src=url;
    const title=document.createElement("strong");title.textContent=vid.filename;
    const download=document.createElement("a");
    download.href=url;download.download=vid.filename;download.textContent="Descargar video";
    card.append(player,title,download);gallery.append(card);
   }
  }catch(err){status.textContent="Error de galería: "+err.message;}
 }
 async function updateVoices(){
   const status=el("bst-voices-status"),library=el("bst-voices");
   status.textContent="Consultando archivos de voz existentes...";
   try{
     const data=await api("/api/voices");
     library.replaceChildren();
     if(!data.configured){
       status.textContent="La carpeta de voces aún no está configurada. Inicia el puente con --voices-dir RUTA.";
       return;
     }
     status.textContent=data.voices.length?
       data.voices.length+" archivo(s) de audio encontrados.":
       "No hay archivos compatibles en esa carpeta. No se crearon voces nuevas.";
     for(const voice of data.voices){
       const src="/voices/"+encodeURIComponent(voice.filename)+"?token="+encodeURIComponent(token);
       const card=document.createElement("div");card.className="video-card";
       const label=document.createElement("strong");label.textContent=voice.filename;
       const audio=document.createElement("audio");audio.controls=true;
       audio.preload="metadata";audio.src=src;audio.style.width="100%";
       const link=document.createElement("a");link.href=src;
       link.download=voice.filename;link.textContent="Descargar audio existente";
       card.append(label,audio,link);library.append(card);
     }
   }catch(err){status.textContent="No se pudo consultar las voces: "+err.message;}
 }
 script.addEventListener("click",async()=>{
  const idea=el("bst-idea").value.trim();
  if(idea.length<2){scriptStatus.textContent="Primero escribe una idea.";return;}
  script.disabled=true;scriptStatus.textContent="Generando guion real con Ollama...";
  try{
   const data=await api("/api/guion",{method:"POST",
    headers:{"Content-Type":"application/json"},body:JSON.stringify({idea})});
   const text="GANCHO\n"+data.gancho+"\n\nHISTORIA\n"+data.historia+
     "\n\nCIERRE\n"+data.oferta_cierre;
   el("bst-output").value=text;
   const field=document.querySelector("#script");
   if(field&&(!field.value.trim()||confirm("¿Reemplazar el guion del proyecto? Guarda una copia si es necesario."))){
    field.value=text;field.dispatchEvent(new Event("input",{bubbles:true}));
   }
   scriptStatus.textContent="Guion recibido de "+data.modelo+" en "+data.segundos+
     " s. Revisa y guarda el proyecto.";
  }catch(err){scriptStatus.textContent="No se pudo generar: "+err.message;}
  finally{script.disabled=false;}
 });
 recover.addEventListener("click",async()=>{
  const taskId=task.value.trim();
  if(!/^[A-Za-z0-9_-]{8,100}$/.test(taskId)){
   recoveryStatus.textContent="Indica un ID de tarea válido.";return;
  }
  localStorage.setItem("bstudio-poyo-task-id",taskId);
  recover.disabled=true;recoveryStatus.textContent="Consultando tarea existente de PoYo...";
  try{
   const data=await api("/api/recover",{method:"POST",
     headers:{"Content-Type":"application/json"},body:JSON.stringify({task_id:taskId})});
   recoveryStatus.textContent=(data.status==="downloaded"?"MP4 recuperado: ":"MP4 existente: ")+data.video;
   await updateVideos();
  }catch(err){
   recoveryStatus.textContent="No se recuperó: "+err.message+". No se generó otra tarea.";
  }finally{recover.disabled=false;}
 });
 el("bst-import").addEventListener("click",async()=>{
  const status=el("bst-import-status"),button=el("bst-import");
  const selected=el("bst-upload").files?.[0];
  if(!selected){status.textContent="Selecciona primero un archivo MP4.";return;}
  if(!/\.mp4$/i.test(selected.name)||selected.size<12||
     selected.size>250*1024*1024){
    status.textContent="Solo se admiten MP4 de hasta 250 MB.";return;
  }
  button.disabled=true;status.textContent="Copiando video a la galería local...";
  try{
    const result=await api("/api/import-video",{
      method:"POST",headers:{"Content-Type":"video/mp4",
       "X-Barriga-Filename":encodeURIComponent(selected.name)},
      body:selected
    });
    status.textContent="MP4 importado: "+result.video+
      ". Tu archivo original está intacto.";
    await updateVideos();
  }catch(err){status.textContent="No se pudo importar: "+err.message;}
  finally{button.disabled=false;}
 });
 el("bst-check").addEventListener("click",updateEngines);
 el("bst-refresh").addEventListener("click",updateVideos);
 el("bst-refresh-voices").addEventListener("click",updateVoices);
 updateEngines();updateVideos();updateVoices();
}
if(document.readyState==="loading")document.addEventListener("DOMContentLoaded",mount);
else mount();
})();