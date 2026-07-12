<template>
  <div class="pagina">
    <div class="head">
      <div>
        <h1 class="page-title">
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
          Timer
          <AyudaInfo>Temporizador de concentración. Corre sobre cualquier modo activo sin interrumpirlo. Al terminar, los LEDs harán una alerta con el color que elijas. El visual del reloj se elige en la sección <b>Visuales</b>.</AyudaInfo>
        </h1>
        <p class="page-subtitle">Los LEDs te avisarán al finalizar con el color que prefieras.</p>
      </div>
    </div>

    <template v-if="!ctrl.timer.activo">
      <div class="glass card">
        <div class="fila-titulo">
          <span class="sub">Cuándo avisar</span>
          <AyudaInfo>Elegí una <b>duración</b> (cuenta regresiva) o una <b>hora del día</b>. Al cumplirse, los LEDs te avisarán. Si la hora ya pasó hoy, será mañana.</AyudaInfo>
        </div>
        <div class="segmented">
          <button :class="{ active: modoTiempo === 'duracion' }" @click="modoTiempo = 'duracion'">Duración</button>
          <button :class="{ active: modoTiempo === 'hora' }" @click="modoTiempo = 'hora'">Hora del día</button>
        </div>

        <template v-if="modoTiempo === 'duracion'">
          <div class="presets">
            <button
              v-for="p in presets"
              :key="p.seconds"
              class="preset-btn"
              :class="{ selected: !personalizado && tiempoPreset === p.seconds }"
              @click="seleccionarPreset(p.seconds)"
            >{{ p.label }}</button>
          </div>

          <div class="custom" :class="{ activo: personalizado }" @click="personalizado = true">
            <span class="custom-lbl">Personalizado</span>
            <div class="hm">
              <div class="hm-campo">
                <input class="num" type="text" inputmode="numeric" maxlength="2"
                  :value="horas" placeholder="0" @input="onHoras" @focus="personalizado = true" />
                <span class="u">h</span>
              </div>
              <div class="hm-campo">
                <input class="num" type="text" inputmode="numeric" maxlength="3"
                  :value="minutos" placeholder="00" @input="onMinutos" @focus="personalizado = true" />
                <span class="u">min</span>
              </div>
            </div>
          </div>
        </template>

        <template v-else>
          <div class="custom activo">
            <span class="custom-lbl">Hora</span>
            <div class="hm">
              <div class="hm-campo">
                <input class="num" type="text" inputmode="numeric" maxlength="2"
                  :value="horaDia" placeholder="00" @input="onHoraDia" />
                <span class="u">h</span>
              </div>
              <div class="hm-campo">
                <input class="num" type="text" inputmode="numeric" maxlength="2"
                  :value="minDia" placeholder="00" @input="onMinDia" />
                <span class="u">m</span>
              </div>
            </div>
          </div>
          <p class="pista-hora" v-if="segundosElegidos >= 1">
            Sonará {{ esManana ? 'mañana' : 'hoy' }} a las {{ etiquetaHora }} · faltan {{ faltanTexto }}
          </p>
        </template>
      </div>

      <div class="glass card">
        <span class="sub">Color de alerta</span>
        <div class="swatches">
          <button
            v-for="c in ctrl.coloresAlerta"
            :key="c.nombre"
            class="swatch"
            :class="{ selected: ctrl.timer.colorAlerta.r === c.r && ctrl.timer.colorAlerta.g === c.g && ctrl.timer.colorAlerta.b === c.b }"
            :style="{ background: `rgb(${c.r},${c.g},${c.b})` }"
            :title="c.nombre"
            @click="ctrl.timer.colorAlerta.r = c.r; ctrl.timer.colorAlerta.g = c.g; ctrl.timer.colorAlerta.b = c.b"
          ></button>
        </div>
      </div>

      <div class="glass card">
        <div class="fila-titulo">
          <span class="sub">Acción al finalizar</span>
          <AyudaInfo><b>Destello:</b> el color aparece un instante y se apaga. <b>Titileo:</b> parpadea varias veces. <b>Fundido:</b> aparece y desaparece de forma suave.</AyudaInfo>
        </div>
        <div class="segmented">
          <button
            v-for="a in ctrl.accionesAlerta"
            :key="a.id"
            :class="{ active: ctrl.timer.accionAlerta === a.id }"
            @click="ctrl.timer.accionAlerta = a.id"
          >{{ a.label }}</button>
        </div>
      </div>

      <button class="btn btn-tint full" :disabled="segundosElegidos < 1" @click="iniciar">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polygon points="5 3 19 12 5 21 5 3"/></svg>
        Iniciar {{ etiquetaTiempo }}
      </button>
    </template>

    <template v-else>
      <div class="glass card timer-card">
        <div class="timer-display">
          <div class="timer-time">{{ tiempoFormateado }}</div>
          <div class="timer-bar-track">
            <div class="timer-bar-fill" :style="{ width: displayProgress + '%' }"></div>
          </div>
          <div class="timer-info">
            <span>{{ ctrl.timer.pausado ? 'PAUSADO' : 'TIMER' }}</span>
            <span>{{ displayProgress }}%</span>
          </div>
        </div>
      </div>

      <p class="pista-visual">
        Elegí el visual del reloj (Reloj / Tarjeta) en la sección <b>Visuales</b>.
      </p>

      <div class="timer-acciones">
        <button v-if="!ctrl.timer.pausado" class="btn btn-tint" @click="ctrl.timerPausar()">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><rect x="6" y="4" width="4" height="16"/><rect x="14" y="4" width="4" height="16"/></svg>
          Pausar
        </button>
        <button v-else class="btn btn-tint" @click="ctrl.timerReanudar()">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><polygon points="5 3 19 12 5 21 5 3"/></svg>
          Reanudar
        </button>
        <button class="btn btn-tint peligro" @click="detener">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><rect x="6" y="6" width="12" height="12"/></svg>
          Detener
        </button>
      </div>
    </template>
  </div>
</template>

<script setup>
import { inject, ref, computed } from 'vue'
import AyudaInfo from './AyudaInfo.vue'

const ctrl = inject('ctrl')

const presets = [
  { label: '5 min', seconds: 300 },
  { label: '15 min', seconds: 900 },
  { label: '25 min', seconds: 1500 },
  { label: '30 min', seconds: 1800 },
  { label: '45 min', seconds: 2700 },
  { label: '1 h', seconds: 3600 },
]

const modoTiempo = ref('duracion') // 'duracion' | 'hora'
const tiempoPreset = ref(1500)     // segundos del preset elegido
const horas = ref('')
const minutos = ref('')
const personalizado = ref(false)
const horaDia = ref('')            // hora del día 0-23
const minDia = ref('')             // minuto del día 0-59

function seleccionarPreset(seg) {
  tiempoPreset.value = seg
  personalizado.value = false
}

function soloDigitos(v) { return String(v).replace(/[^0-9]/g, '') }

function onHoras(e) {
  personalizado.value = true
  const d = soloDigitos(e.target.value)
  horas.value = d === '' ? '' : Math.min(99, parseInt(d, 10))
}
function onMinutos(e) {
  personalizado.value = true
  const d = soloDigitos(e.target.value)
  minutos.value = d === '' ? '' : Math.min(999, parseInt(d, 10))
}
function onHoraDia(e) {
  const d = soloDigitos(e.target.value)
  horaDia.value = d === '' ? '' : Math.min(23, parseInt(d, 10))
}
function onMinDia(e) {
  const d = soloDigitos(e.target.value)
  minDia.value = d === '' ? '' : Math.min(59, parseInt(d, 10))
}

const horaValida = computed(() => horaDia.value !== '' && minDia.value !== '')

// Segundos desde ahora hasta la hora del día elegida (mañana si ya pasó hoy).
function segundosHastaHora() {
  if (!horaValida.value) return 0
  const ahora = new Date()
  const objetivo = new Date()
  objetivo.setHours(parseInt(horaDia.value, 10), parseInt(minDia.value, 10), 0, 0)
  let diff = Math.round((objetivo.getTime() - ahora.getTime()) / 1000)
  if (diff <= 0) diff += 86400
  return diff
}

// Segundos finales según el modo elegido.
const segundosElegidos = computed(() => {
  if (modoTiempo.value === 'hora') return segundosHastaHora()
  if (personalizado.value) {
    const h = parseInt(horas.value, 10) || 0
    const m = parseInt(minutos.value, 10) || 0
    return h * 3600 + m * 60
  }
  return tiempoPreset.value
})

function formatoDuracion(s) {
  const h = Math.floor(s / 3600)
  const m = Math.floor((s % 3600) / 60)
  if (h > 0) return h + ' h' + (m ? ' ' + m + ' min' : '')
  return m + ' min'
}

const esManana = computed(() => {
  if (!horaValida.value) return false
  const ahora = new Date()
  const objetivo = new Date()
  objetivo.setHours(parseInt(horaDia.value, 10), parseInt(minDia.value, 10), 0, 0)
  return objetivo.getTime() <= ahora.getTime()
})
const etiquetaHora = computed(() => {
  const hh = String(parseInt(horaDia.value, 10) || 0).padStart(2, '0')
  const mm = String(parseInt(minDia.value, 10) || 0).padStart(2, '0')
  return `${hh}:${mm}`
})
const faltanTexto = computed(() => formatoDuracion(segundosElegidos.value))

const etiquetaTiempo = computed(() => {
  const s = segundosElegidos.value
  if (s < 1) return ''
  if (modoTiempo.value === 'hora') return '· ' + etiquetaHora.value
  return '· ' + formatoDuracion(s)
})

function iniciar() {
  // En modo hora se recalcula al instante para máxima precisión.
  const seg = modoTiempo.value === 'hora' ? segundosHastaHora() : segundosElegidos.value
  if (seg < 1) return
  ctrl.timerIniciar(seg, { ...ctrl.timer.colorAlerta }, ctrl.timer.accionAlerta)
}

function detener() {
  ctrl.timerDetener()
  ctrl.timer.progreso = 0
}

const tiempoFormateado = computed(() => {
  const t = ctrl.timer.activo ? ctrl.timer.tiempoRestante : ctrl.timer.tiempoTotal
  const total = Math.floor(Math.max(0, t))
  const h = Math.floor(total / 3600)
  const m = Math.floor((total % 3600) / 60)
  const s = total % 60
  const mm = (m < 10 ? '0' : '') + m
  const ss = (s < 10 ? '0' : '') + s
  return h > 0 ? h + ':' + mm + ':' + ss : mm + ':' + ss
})

const displayProgress = computed(() => {
  return Math.round(Math.min(1, ctrl.timer.progreso) * 100)
})
</script>

<style scoped>
/* Estilos propios de la página; el resto viene del sistema (styles.css). */
.presets { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; }
.preset-btn {
  padding: 10px 8px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--glass-border);
  background: rgba(255, 255, 255, 0.04);
  color: var(--text2);
  font-size: 0.85rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.15s;
  font-family: inherit;
}
.preset-btn:hover { background: rgba(255, 255, 255, 0.08); color: #fff; }
.preset-btn.selected {
  background: linear-gradient(135deg, var(--tint), var(--tint-2));
  color: #fff;
  border-color: transparent;
  box-shadow: 0 4px 16px -4px var(--tint);
}

/* Personalizado (horas + minutos, sin flechas) */
.custom {
  display: flex; align-items: center; justify-content: space-between;
  gap: 12px; padding: 12px 14px; border-radius: var(--radius-sm);
  border: 1px solid var(--glass-border); background: rgba(255, 255, 255, 0.03);
  cursor: text; transition: all 0.15s;
}
.custom.activo { border-color: var(--tint); background: rgba(255, 255, 255, 0.06); }
.custom-lbl { font-size: 0.85rem; font-weight: 600; color: var(--text2); }
.hm { display: flex; align-items: center; gap: 10px; }
.hm-campo { display: flex; align-items: baseline; gap: 4px; }
.num {
  width: 56px; text-align: center;
  padding: 8px 6px; border-radius: 10px;
  border: 1px solid var(--glass-border); background: rgba(0, 0, 0, 0.25);
  color: #fff; font-size: 1.2rem; font-weight: 700; font-family: 'Courier New', monospace;
  outline: none; transition: border 0.15s;
  -moz-appearance: textfield; appearance: textfield;
}
.num::-webkit-outer-spin-button,
.num::-webkit-inner-spin-button { -webkit-appearance: none; margin: 0; }
.num:focus { border-color: var(--tint); }
.u { font-size: 0.78rem; font-weight: 600; color: var(--text3); }
.pista-hora { font-size: 0.8rem; color: var(--text2); line-height: 1.5; margin: -2px 2px 0; }

.timer-card { align-items: center; padding: 32px 18px; }
.timer-display { text-align: center; width: 100%; }
.timer-time {
  font-size: 3.2rem;
  font-weight: 800;
  font-family: 'Courier New', monospace;
  color: #fff;
  letter-spacing: 0.04em;
  line-height: 1;
  margin-bottom: 20px;
}
.timer-bar-track {
  width: 100%;
  height: 6px;
  border-radius: 3px;
  background: rgba(255, 255, 255, 0.1);
  overflow: hidden;
}
.timer-bar-fill {
  height: 100%;
  border-radius: 3px;
  background: linear-gradient(90deg, var(--tint), var(--tint-2));
  transition: width 0.3s ease;
}
.timer-info {
  display: flex;
  justify-content: space-between;
  margin-top: 10px;
  font-size: 0.82rem;
  color: var(--text3);
}
.pista-visual {
  font-size: 0.78rem; color: var(--text3); text-align: center; line-height: 1.5;
  margin: -4px 0 0;
}

.timer-acciones {
  display: flex;
  gap: 12px;
  justify-content: center;
}
</style>
