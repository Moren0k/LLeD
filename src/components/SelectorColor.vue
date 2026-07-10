<template>
  <div class="selector">
    <!-- Cuadro Saturación / Brillo -->
    <div
      ref="cuadro"
      class="sv-box"
      :style="{ backgroundColor: `hsl(${h}, 100%, 50%)` }"
      @pointerdown="iniciarSV"
    >
      <div class="sv-white"></div>
      <div class="sv-black"></div>
      <div
        class="sv-handle"
        :style="{ left: `${s * 100}%`, top: `${(1 - v) * 100}%`, background: hex }"
      ></div>
    </div>

    <!-- Barra de matiz -->
    <div ref="barra" class="hue-bar" @pointerdown="iniciarHue">
      <div class="hue-handle" :style="{ left: `${(h / 360) * 100}%` }"></div>
    </div>

    <!-- Vista previa + hex -->
    <div class="preview-row">
      <div class="preview-swatch" :style="{ background: hex }"></div>
      <input class="hex-input" type="text" :value="hex" @change="desdeHex($event.target.value)" spellcheck="false" />
    </div>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'

const props = defineProps({
  modelValue: { type: Object, default: () => ({ r: 255, g: 0, b: 0 }) },
})
const emit = defineEmits(['update:modelValue'])

const h = ref(0)   // 0-360
const s = ref(1)   // 0-1
const v = ref(1)   // 0-1
const hex = ref('#ff0000')

const cuadro = ref(null)
const barra = ref(null)

let interno = false // evita bucle con el watch del prop

// ── Conversiones ──
function rgbAHsv(r, g, b) {
  r /= 255; g /= 255; b /= 255
  const mx = Math.max(r, g, b), mn = Math.min(r, g, b), d = mx - mn
  let hh = 0
  if (d !== 0) {
    if (mx === r) hh = ((g - b) / d) % 6
    else if (mx === g) hh = (b - r) / d + 2
    else hh = (r - g) / d + 4
    hh *= 60
    if (hh < 0) hh += 360
  }
  return { h: hh, s: mx === 0 ? 0 : d / mx, v: mx }
}

function hsvARgb(hh, ss, vv) {
  const c = vv * ss
  const x = c * (1 - Math.abs(((hh / 60) % 2) - 1))
  const m = vv - c
  let r = 0, g = 0, b = 0
  if (hh < 60) { r = c; g = x } else if (hh < 120) { r = x; g = c }
  else if (hh < 180) { g = c; b = x } else if (hh < 240) { g = x; b = c }
  else if (hh < 300) { r = x; b = c } else { r = c; b = x }
  return {
    r: Math.round((r + m) * 255),
    g: Math.round((g + m) * 255),
    b: Math.round((b + m) * 255),
  }
}

function aHex(r, g, b) {
  const t = (n) => Math.max(0, Math.min(255, n | 0)).toString(16).padStart(2, '0')
  return `#${t(r)}${t(g)}${t(b)}`
}

// ── Emisión (con throttle para no saturar el BLE al arrastrar) ──
let ultimoEmit = 0
let timerTrailing = null

function emitirAhora() {
  const { r, g, b } = hsvARgb(h.value, s.value, v.value)
  interno = true
  emit('update:modelValue', { r, g, b })
}

function emitir() {
  // La vista previa (hex) se actualiza al instante para que se sienta fluido.
  const { r, g, b } = hsvARgb(h.value, s.value, v.value)
  hex.value = aHex(r, g, b)

  const ahora = performance.now()
  if (ahora - ultimoEmit >= 45) {
    ultimoEmit = ahora
    if (timerTrailing) { clearTimeout(timerTrailing); timerTrailing = null }
    emitirAhora()
  } else if (!timerTrailing) {
    // Garantiza que el último valor arrastrado sí se envíe.
    timerTrailing = setTimeout(() => {
      ultimoEmit = performance.now()
      timerTrailing = null
      emitirAhora()
    }, 45)
  }
}

// ── Interacción con el cuadro S/V ──
function actualizarSV(e) {
  const rect = cuadro.value.getBoundingClientRect()
  const x = Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width))
  const y = Math.max(0, Math.min(1, (e.clientY - rect.top) / rect.height))
  s.value = x
  v.value = 1 - y
  emitir()
}
function iniciarSV(e) {
  actualizarSV(e)
  const mover = (ev) => actualizarSV(ev)
  const soltar = () => {
    window.removeEventListener('pointermove', mover)
    window.removeEventListener('pointerup', soltar)
  }
  window.addEventListener('pointermove', mover)
  window.addEventListener('pointerup', soltar)
}

// ── Interacción con la barra de matiz ──
function actualizarHue(e) {
  const rect = barra.value.getBoundingClientRect()
  const x = Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width))
  h.value = x * 360
  emitir()
}
function iniciarHue(e) {
  actualizarHue(e)
  const mover = (ev) => actualizarHue(ev)
  const soltar = () => {
    window.removeEventListener('pointermove', mover)
    window.removeEventListener('pointerup', soltar)
  }
  window.addEventListener('pointermove', mover)
  window.addEventListener('pointerup', soltar)
}

// ── Entrada manual por HEX ──
function desdeHex(valor) {
  const m = /^#?([0-9a-fA-F]{6})$/.exec(valor.trim())
  if (!m) return
  const n = parseInt(m[1], 16)
  const r = (n >> 16) & 255, g = (n >> 8) & 255, b = n & 255
  const hsv = rgbAHsv(r, g, b)
  h.value = hsv.h; s.value = hsv.s; v.value = hsv.v
  emitir()
}

// ── Sincroniza cuando el color llega desde afuera (p. ej. Spotify) ──
function sincronizarDesdeProp(rgb) {
  if (interno) { interno = false; return }
  const hsv = rgbAHsv(rgb.r, rgb.g, rgb.b)
  h.value = hsv.h; s.value = hsv.s; v.value = hsv.v
  hex.value = aHex(rgb.r, rgb.g, rgb.b)
}

watch(() => ({ ...props.modelValue }), sincronizarDesdeProp, { immediate: true, deep: true })
</script>

<style scoped>
.selector {
  display: flex;
  flex-direction: column;
  gap: 14px;
  user-select: none;
}

.sv-box {
  position: relative;
  width: 100%;
  height: 180px;
  border-radius: 16px;
  overflow: hidden;
  cursor: crosshair;
  touch-action: none;
  box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.14);
}
.sv-white, .sv-black {
  position: absolute;
  inset: 0;
}
.sv-white { background: linear-gradient(to right, #fff, rgba(255, 255, 255, 0)); }
.sv-black { background: linear-gradient(to top, #000, rgba(0, 0, 0, 0)); }

.sv-handle {
  position: absolute;
  width: 18px;
  height: 18px;
  border-radius: 50%;
  transform: translate(-50%, -50%);
  border: 2px solid #fff;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.5);
  pointer-events: none;
}

.hue-bar {
  position: relative;
  height: 16px;
  border-radius: 8px;
  cursor: pointer;
  touch-action: none;
  background: linear-gradient(to right,
    #f00 0%, #ff0 17%, #0f0 33%, #0ff 50%, #00f 67%, #f0f 83%, #f00 100%);
  box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.14);
}
.hue-handle {
  position: absolute;
  top: 50%;
  width: 16px;
  height: 16px;
  border-radius: 50%;
  transform: translate(-50%, -50%);
  background: #fff;
  border: 2px solid rgba(0, 0, 0, 0.25);
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.4);
  pointer-events: none;
}

.preview-row {
  display: flex;
  align-items: center;
  gap: 10px;
}
.preview-swatch {
  width: 36px;
  height: 36px;
  border-radius: 10px;
  flex-shrink: 0;
  box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.14);
}
.hex-input {
  flex: 1;
  background: rgba(255, 255, 255, 0.06);
  border: 1px solid rgba(255, 255, 255, 0.12);
  color: #fff;
  border-radius: 10px;
  padding: 9px 12px;
  font-family: 'SF Mono', 'Consolas', monospace;
  font-size: 0.85rem;
  outline: none;
  text-transform: uppercase;
}
.hex-input:focus { border-color: rgba(255, 255, 255, 0.3); }
</style>
