<template>
  <div class="pagina">
    <div class="head">
      <div>
        <h1 class="page-title">
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="3" width="20" height="14" rx="2"/><path d="M8 21h8M12 17v4"/></svg>
          Visuales
        </h1>
        <p class="page-subtitle">Un fondo animado que sigue el color de la música y el ritmo.</p>
      </div>
    </div>

    <!-- Preview -->
    <div class="glass card">
      <div class="preview">
        <VisualCanvas class="preview-canvas" />
        <div
          v-if="ctrl.ajustes.visual_titulo && (ctrl.cancionActual || ctrl.timer.activo)"
          class="prev-tarjeta"
          :style="{ left: ctrl.ajustes.visual_titulo_x * 100 + '%', top: ctrl.ajustes.visual_titulo_y * 100 + '%' }"
        >{{ ctrl.timer.activo ? 'TIMER' : ctrl.cancionActual }}</div>
      </div>
      <button class="btn btn-tint full" @click="ctrl.abrirVisualFull">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M8 3H5a2 2 0 0 0-2 2v3m18 0V5a2 2 0 0 0-2-2h-3m0 18h3a2 2 0 0 0 2-2v-3M3 16v3a2 2 0 0 0 2 2h3"/></svg>
        Pantalla completa
      </button>
    </div>

    <!-- Tipo de visual -->
    <div class="glass card">
      <div class="fila-titulo">
        <span class="sub">Estilo</span>
        <AyudaInfo>Elegí cómo se ve el fondo. <b>Aurora</b>: nubes de luz suaves. <b>Orbes</b>: bolitas que se mueven por la pantalla. <b>Ondas</b>: ondas que recorren de lado a lado. <b>Portada</b>: muestra la carátula del álbum que suena en Spotify.</AyudaInfo>
      </div>

      <div v-if="ctrl.timer.activo" class="timer-hint">
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
        Timer activo: elegí <b>Reloj</b> o <b>Tarjeta</b>, o dejá un visual normal.
      </div>

      <div class="estilos">
        <button
          v-for="v in visuales"
          :key="v.id"
          class="estilo"
          :class="{ activo: baseActivo(v.id) }"
          @click="elegirBase(v.id)"
        >
          <span class="estilo-ico" v-html="v.ico"></span>
          <span class="estilo-lbl">{{ v.label }}</span>
        </button>
        <template v-if="ctrl.timer.activo">
          <button
            v-for="v in ctrl.visualesTimer"
            :key="v.id"
            class="estilo estilo-timer"
            :class="{ activo: timerSel(v.id) }"
            @click="elegirTimer(v.id)"
          >
            <span class="estilo-ico" v-html="v.ico"></span>
            <span class="estilo-lbl">{{ v.label }}</span>
          </button>
        </template>
      </div>

      <label class="toggle mov">
        <input type="checkbox" :checked="ctrl.ajustes.visual_movimiento" @change="ctrl.setAjuste('visual_movimiento', $event.target.checked, true)" />
        <span class="track"><span class="thumb"></span></span>
        <span class="toggle-txt">Movimiento por la pantalla</span>
        <AyudaInfo>Con esto los elementos se desplazan por la pantalla. Sin esto, se quedan en su lugar y solo laten con la música.</AyudaInfo>
      </label>
    </div>

    <!-- Color de la tarjeta (solo con timer + visual Tarjeta) -->
    <div v-if="mostrarFondoCard" class="glass card">
      <div class="fila-titulo">
        <span class="sub">Color de la tarjeta</span>
        <AyudaInfo>Fondo sólido de la tarjeta del timer. El texto del tiempo se vuelve claro u oscuro automáticamente según el contraste.</AyudaInfo>
      </div>
      <div class="swatches">
        <button
          v-for="c in ctrl.fondosCard"
          :key="c.nombre"
          class="swatch"
          :class="{ selected: ctrl.timer.colorFondoVisual.r === c.r && ctrl.timer.colorFondoVisual.g === c.g && ctrl.timer.colorFondoVisual.b === c.b }"
          :style="{ background: `rgb(${c.r},${c.g},${c.b})` }"
          :title="c.nombre"
          @click="elegirFondo(c)"
        ></button>
      </div>
      <input class="input hex" type="text" maxlength="7" :value="hexFondo" @input="onHexFondo" placeholder="#0a0a1e" />
    </div>

    <!-- Carátula (visual Portada) -->
    <div v-if="mostrarPortadaCard" class="glass card">
      <div class="fila-titulo">
        <span class="sub">Carátula</span>
        <AyudaInfo>Muestra la carátula del álbum que suena en Spotify. Podés difuminar el fondo detrás y ubicar la carátula donde prefieras.</AyudaInfo>
      </div>
      <label class="toggle">
        <input type="checkbox" :checked="ctrl.ajustes.visual_portada_difuminado" @change="ctrl.setAjuste('visual_portada_difuminado', $event.target.checked, true)" />
        <span class="track"><span class="thumb"></span></span>
        <span class="toggle-txt">Difuminar el fondo</span>
      </label>
      <div class="fila">
        <span class="field-label">Posición</span>
        <div class="posiciones">
          <button v-for="p in posicionesPortada" :key="p.nombre" class="pos-btn" :class="{ activo: portadaPosSel(p) }" :title="p.nombre" @click="ponerPosicionPortada(p.x, p.y)">
            <span class="pos-dot" :style="dotStyle(p)"></span>
          </button>
        </div>
      </div>
      <p class="nota" v-if="!ctrl.cancionActual">Se verá cuando esté sonando una canción en Spotify.</p>
    </div>

    <!-- Título de la canción -->
    <div class="glass card">
      <div class="fila-titulo">
        <span class="sub">Nombre de la canción</span>
        <AyudaInfo>Muestra el título de la canción actual como una tarjeta sobre el visual. Podés cambiar su tamaño y posición, o arrastrarla libre en pantalla completa.</AyudaInfo>
      </div>

      <label class="toggle">
        <input type="checkbox" :checked="ctrl.ajustes.visual_titulo" @change="ctrl.setAjuste('visual_titulo', $event.target.checked, true)" />
        <span class="track"><span class="thumb"></span></span>
        <span class="toggle-txt">Mostrar el título</span>
      </label>

      <label class="toggle">
        <input type="checkbox" :checked="ctrl.ajustes.visual_portada" @change="ctrl.setAjuste('visual_portada', $event.target.checked, true)" />
        <span class="track"><span class="thumb"></span></span>
        <span class="toggle-txt">Mostrar la carátula en la tarjeta</span>
        <AyudaInfo>Agrega la carátula del álbum dentro de la tarjeta, junto al nombre y el artista.</AyudaInfo>
      </label>

      <template v-if="ctrl.ajustes.visual_titulo">
        <div class="fila">
          <span class="field-label">Tamaño</span>
          <input class="slider" type="range" min="0.5" max="2.5" step="0.1"
            :value="ctrl.ajustes.visual_titulo_escala"
            @input="ctrl.setAjuste('visual_titulo_escala', Number($event.target.value))" />
          <span class="valor">{{ Number(ctrl.ajustes.visual_titulo_escala).toFixed(1) }}×</span>
        </div>
        <div class="fila">
          <span class="field-label">Posición</span>
          <div class="posiciones">
            <button v-for="p in posiciones" :key="p.nombre" class="pos-btn" :title="p.nombre" @click="ponerPosicion(p.x, p.y)">
              <span class="pos-dot" :style="dotStyle(p)"></span>
            </button>
          </div>
        </div>
        <p class="nota">O arrastrá el título libremente en pantalla completa.</p>
      </template>
    </div>

    <!-- Visual remoto -->
    <div class="glass card">
      <div class="fila-top">
        <div>
          <div class="fila-titulo">
            <span class="sub">Visual remoto</span>
            <AyudaInfo>Abre una página web en tu red local con este mismo visual. Copiá la dirección y abrila en otro dispositivo (celular, TV, laptop) conectado al mismo WiFi.</AyudaInfo>
          </div>
          <p class="nota">Verlo en otra pantalla, sincronizado en vivo.</p>
        </div>
        <button class="btn" :class="ctrl.visual.activo ? 'btn-tint peligro' : 'btn-tint'" @click="ctrl.visual.activo ? ctrl.detenerVisual() : ctrl.iniciarVisual()">
          {{ ctrl.visual.activo ? 'Detener' : 'Activar' }}
        </button>
      </div>

      <div v-if="ctrl.visual.activo && ctrl.visual.url" class="url-box">
        <div class="url-fila">
          <span class="url-txt">{{ ctrl.visual.url }}</span>
          <button class="btn btn-glass copiar" @click="copiar(ctrl.visual.url)">{{ copiado ? 'Copiado' : 'Copiar' }}</button>
        </div>
        <p class="hint">Abrila en otro dispositivo de la misma red / WiFi.</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { inject, ref, computed } from 'vue'
import VisualCanvas from './VisualCanvas.vue'
import AyudaInfo from './AyudaInfo.vue'

const ctrl = inject('ctrl')
const copiado = ref(false)

// ── Selección de visual (base vs. visual del timer) ──
// El timer solo aporta estado; acá se decide QUÉ se muestra.
function usandoTimer() { return ctrl.timer.activo && ctrl.timer.usarVisual }
function baseActivo(id) { return !usandoTimer() && ctrl.ajustes.visual_tipo === id }
function timerSel(id) { return usandoTimer() && ctrl.timer.modoVisual === id }

function elegirBase(id) {
  ctrl.setAjuste('visual_tipo', id, true)
  if (ctrl.timer.activo) { ctrl.timer.usarVisual = false; ctrl.timerVisual() }
}
function elegirTimer(id) {
  ctrl.timer.modoVisual = id
  ctrl.timer.usarVisual = true
  ctrl.timerVisual()
}

const mostrarFondoCard = computed(() =>
  ctrl.timer.activo && ctrl.timer.usarVisual && ctrl.timer.modoVisual === 'colorcard'
)

const hexFondo = computed(() => {
  const { r, g, b } = ctrl.timer.colorFondoVisual
  return '#' + [r, g, b].map(x => x.toString(16).padStart(2, '0')).join('')
})
function onHexFondo(e) {
  let h = e.target.value.replace(/[^0-9a-fA-F]/g, '')
  if (h.length >= 6) {
    h = h.substring(0, 6)
    ctrl.timer.colorFondoVisual.r = parseInt(h.substring(0, 2), 16)
    ctrl.timer.colorFondoVisual.g = parseInt(h.substring(2, 4), 16)
    ctrl.timer.colorFondoVisual.b = parseInt(h.substring(4, 6), 16)
    ctrl.timerVisual()
  }
}
function elegirFondo(c) {
  ctrl.timer.colorFondoVisual.r = c.r
  ctrl.timer.colorFondoVisual.g = c.g
  ctrl.timer.colorFondoVisual.b = c.b
  ctrl.timerVisual()
}

const visuales = [
  { id: 'aurora', label: 'Aurora', ico: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6"><path d="M3 15c3-6 6-6 9 0s6 6 9 0"/><path d="M3 10c3-6 6-6 9 0s6 6 9 0" opacity=".5"/></svg>' },
  { id: 'orbes', label: 'Orbes', ico: '<svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor"><circle cx="7" cy="8" r="3"/><circle cx="16" cy="14" r="4"/><circle cx="17" cy="6" r="2"/></svg>' },
  { id: 'ondas', label: 'Ondas', ico: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6"><path d="M2 8c2-3 4-3 6 0s4 3 6 0 4-3 6 0"/><path d="M2 16c2-3 4-3 6 0s4 3 6 0 4-3 6 0"/></svg>' },
  { id: 'portada', label: 'Portada', ico: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="8.5" cy="8.5" r="1.6"/><path d="M21 15l-5-5L5 21"/></svg>' },
]

const mostrarPortadaCard = computed(() => ctrl.ajustes.visual_tipo === 'portada' && !usandoTimer())

const posicionesPortada = [
  { nombre: 'Arriba', x: 0.5, y: 0.28 },
  { nombre: 'Centro', x: 0.5, y: 0.42 },
  { nombre: 'Izquierda', x: 0.3, y: 0.42 },
  { nombre: 'Derecha', x: 0.7, y: 0.42 },
]
function ponerPosicionPortada(x, y) {
  ctrl.setAjuste('visual_portada_x', x, true)
  ctrl.setAjuste('visual_portada_y', y, true)
}
function portadaPosSel(p) {
  return Math.abs(ctrl.ajustes.visual_portada_x - p.x) < 0.02 && Math.abs(ctrl.ajustes.visual_portada_y - p.y) < 0.02
}

const posiciones = [
  { nombre: 'Arriba izq.', x: 0.16, y: 0.14 },
  { nombre: 'Arriba centro', x: 0.5, y: 0.14 },
  { nombre: 'Arriba der.', x: 0.84, y: 0.14 },
  { nombre: 'Centro', x: 0.5, y: 0.5 },
  { nombre: 'Abajo izq.', x: 0.16, y: 0.86 },
  { nombre: 'Abajo centro', x: 0.5, y: 0.86 },
  { nombre: 'Abajo der.', x: 0.84, y: 0.86 },
]

function ponerPosicion(x, y) {
  ctrl.setAjuste('visual_titulo_x', x, true)
  ctrl.setAjuste('visual_titulo_y', y, true)
}
function dotStyle(p) { return { left: p.x * 100 + '%', top: p.y * 100 + '%' } }

function copiar(texto) {
  try { navigator.clipboard.writeText(texto) } catch (e) { /* noop */ }
  copiado.value = true
  setTimeout(() => { copiado.value = false }, 1500)
}
</script>

<style scoped>
/* Estilos propios de la página; el resto viene del sistema (styles.css). */
.preview { position: relative; height: 190px; border-radius: var(--radius-sm); overflow: hidden; background: #05060a; }
.preview-canvas { position: absolute; inset: 0; }
.prev-tarjeta {
  position: absolute; transform: translate(-50%, -50%);
  padding: 6px 12px; border-radius: 12px; font-size: 0.78rem; font-weight: 600; color: #fff;
  background: rgba(255, 255, 255, 0.1); backdrop-filter: blur(10px);
  border: 1px solid rgba(255, 255, 255, 0.16); max-width: 70%;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap; pointer-events: none;
}
.full { width: 100%; justify-content: center; }

.estilos { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; }
.estilo {
  display: flex; flex-direction: column; align-items: center; gap: 6px;
  padding: 14px 6px; border-radius: var(--radius-sm); cursor: pointer; font-family: inherit;
  background: rgba(0, 0, 0, 0.25); border: 1px solid var(--glass-border); color: var(--text2);
  transition: all 0.15s;
}
.estilo:hover { color: var(--text); border-color: var(--glass-border-strong); }
.estilo.activo { color: #fff; border-color: transparent; background: linear-gradient(135deg, var(--tint), var(--tint-2)); box-shadow: 0 4px 16px -6px var(--tint); }
.estilo-lbl { font-size: 0.74rem; font-weight: 600; }
.estilo-timer { border-style: dashed; }
.estilo-timer.activo { border-style: solid; }

.timer-hint {
  display: flex; align-items: center; gap: 8px;
  font-size: 0.78rem; color: var(--text2); line-height: 1.4;
  padding: 8px 12px; border-radius: var(--radius-sm);
  background: rgba(255, 255, 255, 0.04); border: 1px solid var(--glass-border);
}
.timer-hint svg { flex-shrink: 0; color: var(--tint); }

.hex { max-width: 140px; font-family: 'SF Mono', 'Consolas', monospace; text-transform: uppercase; }

.mov { margin-top: 2px; }

.posiciones { display: flex; gap: 6px; flex-wrap: wrap; }
.pos-btn { position: relative; width: 38px; height: 26px; border-radius: 7px; cursor: pointer; background: rgba(0, 0, 0, 0.3); border: 1px solid var(--glass-border); padding: 0; transition: border-color 0.15s; }
.pos-btn:hover { border-color: var(--tint); }
.pos-btn.activo { border-color: var(--tint); background: rgba(125, 75, 255, 0.14); }
.pos-dot { position: absolute; width: 6px; height: 6px; border-radius: 50%; background: var(--tint); transform: translate(-50%, -50%); }

.fila-top { display: flex; align-items: flex-start; justify-content: space-between; gap: 12px; }
.url-box { display: flex; flex-direction: column; gap: 6px; }
.url-fila { display: flex; align-items: center; gap: 8px; }
.url-txt { flex: 1; min-width: 0; font-family: 'SF Mono', 'Consolas', monospace; font-size: 0.9rem; font-weight: 600; background: rgba(0, 0, 0, 0.3); padding: 10px 12px; border-radius: var(--radius-sm); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.copiar { flex-shrink: 0; }
.hint { font-size: 0.74rem; color: var(--text3); }
</style>
