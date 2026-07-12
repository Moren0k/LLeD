<template>
  <div ref="raiz" class="full">
    <VisualCanvas class="full-canvas" />

    <div
      v-if="ctrl.ajustes.visual_letra && lineasLetra.length"
      class="letra"
      :style="estiloLetra"
      @pointerdown="iniciarArrastreLetra"
    >
      <TransitionGroup name="carrusel" tag="div" class="letra-stack">
        <div v-for="l in lineasLetra" :key="l.key" class="letra-linea" :class="l.rol">{{ l.texto }}</div>
      </TransitionGroup>
    </div>

    <div
      v-if="mostrarTarjeta"
      class="tarjeta"
      :style="estiloTarjeta"
      @pointerdown="iniciarArrastre"
    >
      <template v-if="ctrl.timer.activo">
        <div class="t-nombre">{{ ctrl.timer.pausado ? 'PAUSADO' : 'TIMER' }}</div>
        <div class="t-artista">{{ tFocus }} restantes</div>
      </template>
      <template v-else>
        <img v-if="ctrl.ajustes.visual_portada && ctrl.portadaActual" class="t-portada" :src="ctrl.portadaActual" alt="" />
        <template v-if="ctrl.ajustes.visual_titulo">
          <div class="t-nombre">{{ ctrl.cancionActual }}</div>
          <div class="t-artista">{{ ctrl.artistaActual }}</div>
        </template>
      </template>
    </div>

    <button class="cerrar" title="Salir (Esc)" @click="cerrar">✕</button>
    <span class="pista">Arrastrá el título o la letra para moverlos · Esc para salir</span>
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

const mostrarTarjeta = computed(() => {
  if (ctrl.timer.activo) return ctrl.ajustes.visual_titulo
  const verNombre = ctrl.ajustes.visual_titulo && !!ctrl.cancionActual
  const verPortada = ctrl.ajustes.visual_portada && !!ctrl.portadaActual
  return verNombre || verPortada
})

const estiloTarjeta = computed(() => ({
  left: `${ctrl.ajustes.visual_titulo_x * 100}%`,
  top: `${ctrl.ajustes.visual_titulo_y * 100}%`,
  '--esc': ctrl.ajustes.visual_titulo_escala,
}))

const estiloLetra = computed(() => ({
  left: `${ctrl.ajustes.visual_letra_x * 100}%`,
  top: `${ctrl.ajustes.visual_letra_y * 100}%`,
  '--esc': ctrl.ajustes.visual_letra_escala,
}))

// Ventana de 3 líneas: anterior (arriba), actual (medio), siguiente (abajo).
// La clave es el índice de la línea en la canción para que TransitionGroup
// anime el desplazamiento (carrusel) al avanzar.
const lineasLetra = computed(() => {
  const i = ctrl.letraIndice
  if (i < 0 || !ctrl.letraActual) return []
  const arr = []
  if (ctrl.letraAnterior) arr.push({ key: i - 1, rol: 'ant', texto: ctrl.letraAnterior })
  arr.push({ key: i, rol: 'act', texto: ctrl.letraActual })
  if (ctrl.letraSiguiente) arr.push({ key: i + 1, rol: 'sig', texto: ctrl.letraSiguiente })
  return arr
})

// Arrastre genérico que persiste una posición (x, y) en dos ajustes.
function arrastrar(claveX, claveY) {
  const mover = (e) => {
    const x = Math.max(0.04, Math.min(0.96, e.clientX / window.innerWidth))
    const y = Math.max(0.06, Math.min(0.94, e.clientY / window.innerHeight))
    ctrl.ajustes[claveX] = x
    ctrl.ajustes[claveY] = y
    ctrl.setAjuste(claveX, x)
    ctrl.setAjuste(claveY, y)
  }
  const soltar = () => {
    window.removeEventListener('pointermove', mover)
    window.removeEventListener('pointerup', soltar)
    ctrl.setAjuste(claveX, ctrl.ajustes[claveX], true)
    ctrl.setAjuste(claveY, ctrl.ajustes[claveY], true)
  }
  window.addEventListener('pointermove', mover)
  window.addEventListener('pointerup', soltar)
}
function iniciarArrastreLetra() { arrastrar('visual_letra_x', 'visual_letra_y') }

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

.letra {
  position: absolute; transform: translate(-50%, -50%);
  width: min(92vw, 900px); text-align: center; z-index: 5;
  cursor: grab; user-select: none;
}
.letra:active { cursor: grabbing; }
.letra-stack {
  position: relative;
  display: flex; flex-direction: column; align-items: center; gap: 10px;
}
.letra-linea {
  text-align: center; line-height: 1.25; max-width: 100%;
  transition: opacity 0.5s ease, color 0.5s ease, font-size 0.5s ease;
}
.letra-linea.act {
  color: #fff; font-weight: 800; opacity: 1;
  font-size: calc(clamp(24px, 5.2vw, 52px) * var(--esc, 1));
  text-shadow: 0 2px 18px rgba(0, 0, 0, 0.6);
}
.letra-linea.ant, .letra-linea.sig {
  color: rgba(255, 255, 255, 0.5); font-weight: 600; opacity: 0.55;
  font-size: calc(clamp(16px, 3.4vw, 30px) * var(--esc, 1));
}
/* Carrusel: las líneas se desplazan (FLIP) y entran/salen con fundido. */
.carrusel-move { transition: transform 0.5s cubic-bezier(0.22, 0.61, 0.36, 1); }
.carrusel-enter-active { transition: opacity 0.5s ease, transform 0.5s ease; }
.carrusel-leave-active { transition: opacity 0.45s ease, transform 0.45s ease; position: absolute; left: 0; right: 0; }
.carrusel-enter-from { opacity: 0; transform: translateY(28px); }
.carrusel-leave-to { opacity: 0; transform: translateY(-28px); }

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
.t-portada { width: calc(140px * var(--esc, 1)); height: calc(140px * var(--esc, 1)); border-radius: 16px; object-fit: cover; display: block; margin: 0 auto 12px; box-shadow: 0 10px 30px rgba(0, 0, 0, 0.5); }
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
