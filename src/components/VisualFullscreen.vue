<template>
  <div ref="raiz" class="full">
    <VisualCanvas class="full-canvas" />

    <div
      v-if="ctrl.ajustes.visual_titulo && (ctrl.cancionActual || ctrl.timer.activo)"
      class="tarjeta"
      :style="estiloTarjeta"
      @pointerdown="iniciarArrastre"
    >
      <template v-if="ctrl.timer.activo">
        <div class="t-nombre">{{ ctrl.timer.pausado ? 'PAUSADO' : 'TIMER' }}</div>
        <div class="t-artista">{{ tFocus }} restantes</div>
      </template>
      <template v-else>
        <div class="t-nombre">{{ ctrl.cancionActual }}</div>
        <div class="t-artista">{{ ctrl.artistaActual }}</div>
      </template>
    </div>

    <button class="cerrar" title="Salir (Esc)" @click="cerrar">✕</button>
    <span class="pista">Arrastrá el título para moverlo · Esc para salir</span>
  </div>
</template>

<script setup>
import { inject, ref, computed, onMounted, onUnmounted } from 'vue'
import VisualCanvas from './VisualCanvas.vue'
const ctrl = inject('ctrl')
const raiz = ref(null)

const tFocus = computed(() => {
  const t = ctrl.timer.activo ? ctrl.timer.tiempoRestante : 0
  const m = Math.floor(Math.max(0, t) / 60)
  const s = Math.floor(Math.max(0, t) % 60)
  return (m < 10 ? '0' : '') + m + ':' + (s < 10 ? '0' : '') + s
})

const estiloTarjeta = computed(() => ({
  left: `${ctrl.ajustes.visual_titulo_x * 100}%`,
  top: `${ctrl.ajustes.visual_titulo_y * 100}%`,
  '--esc': ctrl.ajustes.visual_titulo_escala,
}))

function iniciarArrastre() {
  const mover = (e) => {
    const x = Math.max(0.04, Math.min(0.96, e.clientX / window.innerWidth))
    const y = Math.max(0.06, Math.min(0.94, e.clientY / window.innerHeight))
    ctrl.ajustes.visual_titulo_x = x
    ctrl.ajustes.visual_titulo_y = y
    ctrl.setAjuste('visual_titulo_x', x)
    ctrl.setAjuste('visual_titulo_y', y)
  }
  const soltar = () => {
    window.removeEventListener('pointermove', mover)
    window.removeEventListener('pointerup', soltar)
    // Persiste la posición final de inmediato.
    ctrl.setAjuste('visual_titulo_x', ctrl.ajustes.visual_titulo_x, true)
    ctrl.setAjuste('visual_titulo_y', ctrl.ajustes.visual_titulo_y, true)
  }
  window.addEventListener('pointermove', mover)
  window.addEventListener('pointerup', soltar)
}

function cerrar() { ctrl.cerrarVisualFull() }

function onKey(e) { if (e.key === 'Escape') cerrar() }
function onFsChange() {
  if (!document.fullscreenElement) ctrl.cerrarVisualFull()
}

onMounted(async () => {
  window.addEventListener('keydown', onKey)
  document.addEventListener('fullscreenchange', onFsChange)
  try { await raiz.value.requestFullscreen() } catch (e) { /* sin fullscreen nativo: overlay igual */ }
})
onUnmounted(() => {
  window.removeEventListener('keydown', onKey)
  document.removeEventListener('fullscreenchange', onFsChange)
  if (document.fullscreenElement) { document.exitFullscreen().catch(() => {}) }
})
</script>

<style scoped>
.full {
  position: fixed;
  inset: 0;
  z-index: 1000;
  overflow: hidden;
  background: #05060a;
}
.full-canvas { position: absolute; inset: 0; }

.tarjeta {
  position: absolute;
  transform: translate(-50%, -50%);
  text-align: center;
  padding: calc(18px * var(--esc, 1)) calc(30px * var(--esc, 1));
  border-radius: 24px;
  cursor: grab;
  max-width: 82vw;
  background: rgba(255, 255, 255, 0.07);
  backdrop-filter: blur(26px) saturate(180%);
  -webkit-backdrop-filter: blur(26px) saturate(180%);
  border: 1px solid rgba(255, 255, 255, 0.14);
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.35), inset 0 1px 0 rgba(255, 255, 255, 0.14);
  user-select: none;
}
.tarjeta:active { cursor: grabbing; }
.t-nombre { color: #fff; font-weight: 700; font-size: calc(30px * var(--esc, 1)); line-height: 1.15; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 80vw; }
.t-artista { color: rgba(255, 255, 255, 0.62); font-weight: 500; font-size: calc(17px * var(--esc, 1)); margin-top: 4px; }

.cerrar {
  position: absolute; top: 20px; right: 20px;
  width: 40px; height: 40px; border-radius: 12px;
  background: rgba(255, 255, 255, 0.08); border: 1px solid rgba(255, 255, 255, 0.14);
  color: #fff; font-size: 1rem; cursor: pointer; backdrop-filter: blur(10px);
}
.cerrar:hover { background: rgba(255, 255, 255, 0.16); }
.pista {
  position: absolute; bottom: 18px; left: 50%; transform: translateX(-50%);
  font-size: 0.72rem; color: rgba(255, 255, 255, 0.35); letter-spacing: 0.04em;
}
</style>
