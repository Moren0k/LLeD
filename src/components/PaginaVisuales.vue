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
          v-if="ctrl.ajustes.visual_titulo && ctrl.cancionActual"
          class="prev-tarjeta"
          :style="{ left: ctrl.ajustes.visual_titulo_x * 100 + '%', top: ctrl.ajustes.visual_titulo_y * 100 + '%' }"
        >{{ ctrl.cancionActual }}</div>
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
        <AyudaInfo>Elegí cómo se ve el fondo. <b>Aurora</b>: nubes de luz suaves. <b>Orbes</b>: bolitas que se mueven por la pantalla. <b>Ondas</b>: ondas que recorren de lado a lado.</AyudaInfo>
      </div>
      <div class="estilos">
        <button
          v-for="v in visuales"
          :key="v.id"
          class="estilo"
          :class="{ activo: ctrl.ajustes.visual_tipo === v.id }"
          @click="ctrl.setAjuste('visual_tipo', v.id, true)"
        >
          <span class="estilo-ico" v-html="v.ico"></span>
          <span class="estilo-lbl">{{ v.label }}</span>
        </button>
      </div>

      <label class="toggle mov">
        <input type="checkbox" :checked="ctrl.ajustes.visual_movimiento" @change="ctrl.setAjuste('visual_movimiento', $event.target.checked, true)" />
        <span class="track"><span class="thumb"></span></span>
        <span class="toggle-txt">Movimiento por la pantalla</span>
        <AyudaInfo>Con esto los elementos se desplazan por la pantalla. Sin esto, se quedan en su lugar y solo laten con la música.</AyudaInfo>
      </label>
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
            <span class="titulo">Visual remoto</span>
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
import { inject, ref } from 'vue'
import VisualCanvas from './VisualCanvas.vue'
import AyudaInfo from './AyudaInfo.vue'

const ctrl = inject('ctrl')
const copiado = ref(false)

const visuales = [
  { id: 'aurora', label: 'Aurora', ico: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6"><path d="M3 15c3-6 6-6 9 0s6 6 9 0"/><path d="M3 10c3-6 6-6 9 0s6 6 9 0" opacity=".5"/></svg>' },
  { id: 'orbes', label: 'Orbes', ico: '<svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor"><circle cx="7" cy="8" r="3"/><circle cx="16" cy="14" r="4"/><circle cx="17" cy="6" r="2"/></svg>' },
  { id: 'ondas', label: 'Ondas', ico: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6"><path d="M2 8c2-3 4-3 6 0s4 3 6 0 4-3 6 0"/><path d="M2 16c2-3 4-3 6 0s4 3 6 0 4-3 6 0"/></svg>' },
]

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
.pagina { display: flex; flex-direction: column; gap: 16px; }
.card { padding: 18px; display: flex; flex-direction: column; gap: 14px; }

.preview { position: relative; height: 190px; border-radius: 16px; overflow: hidden; background: #05060a; }
.preview-canvas { position: absolute; inset: 0; }
.prev-tarjeta {
  position: absolute; transform: translate(-50%, -50%);
  padding: 6px 12px; border-radius: 12px; font-size: 0.78rem; font-weight: 600; color: #fff;
  background: rgba(255,255,255,0.1); backdrop-filter: blur(10px);
  border: 1px solid rgba(255,255,255,0.16); max-width: 70%;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap; pointer-events: none;
}
.full { width: 100%; justify-content: center; }

.fila-titulo { display: flex; align-items: center; gap: 8px; }
.sub, .titulo { font-size: 0.95rem; font-weight: 600; }

.estilos { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; }
.estilo {
  display: flex; flex-direction: column; align-items: center; gap: 6px;
  padding: 14px 6px; border-radius: 14px; cursor: pointer; font-family: inherit;
  background: rgba(0,0,0,0.25); border: 1px solid var(--glass-border); color: var(--text2);
  transition: all 0.15s;
}
.estilo:hover { color: var(--text); border-color: var(--glass-border-strong); }
.estilo.activo { color: #fff; border-color: transparent; background: linear-gradient(135deg, var(--tint), var(--tint-2)); box-shadow: 0 4px 16px -6px var(--tint); }
.estilo-lbl { font-size: 0.74rem; font-weight: 600; }

.mov { margin-top: 2px; }
.toggle-txt { font-size: 0.88rem; }

.fila { display: flex; align-items: center; gap: 12px; }
.valor { font-size: 0.82rem; font-weight: 600; color: var(--text2); min-width: 36px; text-align: right; }
.nota { font-size: 0.76rem; color: var(--text3); line-height: 1.5; }

.posiciones { display: flex; gap: 6px; flex-wrap: wrap; }
.pos-btn { position: relative; width: 38px; height: 26px; border-radius: 7px; cursor: pointer; background: rgba(0,0,0,0.3); border: 1px solid var(--glass-border); padding: 0; transition: border-color 0.15s; }
.pos-btn:hover { border-color: var(--tint); }
.pos-dot { position: absolute; width: 6px; height: 6px; border-radius: 50%; background: var(--tint); transform: translate(-50%, -50%); }

.fila-top { display: flex; align-items: flex-start; justify-content: space-between; gap: 12px; }
.url-box { display: flex; flex-direction: column; gap: 6px; }
.url-fila { display: flex; align-items: center; gap: 8px; }
.url-txt { flex: 1; font-family: 'SF Mono', 'Consolas', monospace; font-size: 0.9rem; font-weight: 600; background: rgba(0,0,0,0.3); padding: 10px 12px; border-radius: 10px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.copiar { flex-shrink: 0; }
.hint { font-size: 0.74rem; color: var(--text3); }
</style>
