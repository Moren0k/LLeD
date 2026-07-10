<template>
  <div class="pagina">
    <div class="head">
      <div>
        <h1 class="page-title">
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="2" width="20" height="20" rx="2.18" ry="2.18"/><line x1="7" y1="2" x2="7" y2="22"/><line x1="17" y1="2" x2="17" y2="22"/><line x1="2" y1="12" x2="22" y2="12"/><line x1="2" y1="7" x2="7" y2="7"/><line x1="2" y1="17" x2="7" y2="17"/><line x1="17" y1="17" x2="22" y2="17"/><line x1="17" y1="7" x2="22" y2="7"/></svg>
          Cine Mode
          <AyudaInfo>La tira toma el color de lo que se ve en ESTA PC (tipo Ambilight), con la intensidad según la escena, y se complementa con el audio (destellos en golpes fuertes). Es un solo color para toda la tira. Función local.</AyudaInfo>
        </h1>
        <p class="page-subtitle">Ambiente inmersivo para películas y series, guiado por pantalla + sonido.</p>
      </div>
    </div>

    <!-- Aviso Netflix / DRM -->
    <div class="glass aviso">
      <span class="aviso-ico">ⓘ</span>
      <div>
        <b>YouTube funciona directo.</b> Para <b>Netflix</b> (y otros con DRM), si ves la tira apagada,
        desactivá la <b>aceleración por hardware</b> del navegador (Configuración → Sistema). Si la
        pantalla sale negra por DRM, Cine Mode sigue reaccionando <b>solo con el audio</b>.
      </div>
    </div>

    <!-- Activar -->
    <div class="glass card">
      <div class="fila-activar">
        <div class="estado">
          <span class="dot" :class="{ on: ctrl.ambilightActivado }"></span>
          <span>{{ ctrl.ambilightActivado ? 'Activo' : (ctrl.ambilightDisponible ? 'Listo' : 'Captura no disponible') }}</span>
        </div>
        <button
          class="btn"
          :class="ctrl.ambilightActivado ? 'btn-tint activo' : 'btn-tint'"
          :disabled="!ctrl.ambilightDisponible && !ctrl.ambilightActivado"
          @click="ctrl.toggleAmbilight"
        >{{ ctrl.ambilightActivado ? 'Detener' : 'Iniciar' }}</button>
      </div>

      <div class="fila">
        <span class="field-label">Monitor</span>
        <div class="segmented" v-if="ctrl.monitores.length">
          <button
            v-for="m in ctrl.monitores"
            :key="m.indice"
            :class="{ active: ctrl.ajustes.ambilight_monitor === m.indice }"
            @click="ctrl.setAmbilight('ambilight_monitor', m.indice, true)"
          >{{ m.nombre }}</button>
        </div>
        <button v-else class="btn btn-glass" @click="ctrl.cargarMonitores">Buscar monitores</button>
      </div>

      <label class="toggle">
        <input type="checkbox" :checked="ctrl.ajustes.ambilight_reactivo_audio" @change="ctrl.setAmbilight('ambilight_reactivo_audio', $event.target.checked, true)" />
        <span class="track"><span class="thumb"></span></span>
        <span class="toggle-txt">Reactivo al audio</span>
        <AyudaInfo>Usa el sonido del sistema para modular la intensidad y disparar destellos en golpes fuertes (explosiones, pasos, screamers). Necesita "Stereo Mix" activado.</AyudaInfo>
      </label>
    </div>

    <!-- Ajustes finos -->
    <div class="glass card">
      <span class="sub">Ajuste fino</span>
      <div class="fila" v-for="s in sliders" :key="s.clave">
        <span class="field-label">{{ s.label }}</span>
        <input class="slider" type="range" :min="s.min" :max="s.max" :step="s.step"
          :value="ctrl.ajustes[s.clave]"
          @input="ctrl.setAmbilight(s.clave, Number($event.target.value))" />
        <span class="valor">{{ formatear(s, ctrl.ajustes[s.clave]) }}</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { inject, onMounted } from 'vue'
import AyudaInfo from './AyudaInfo.vue'

const ctrl = inject('ctrl')

const sliders = [
  { clave: 'ambilight_suavizado', label: 'Suavidad', min: 0, max: 0.95, step: 0.05, tipo: 'x' },
  { clave: 'ambilight_saturacion', label: 'Saturación', min: 1, max: 2.5, step: 0.1, tipo: 'x' },
  { clave: 'ambilight_intensidad_min', label: 'Intensidad mín', min: 0, max: 1, step: 0.02, tipo: 'pct' },
  { clave: 'ambilight_intensidad_max', label: 'Intensidad máx', min: 0, max: 1, step: 0.02, tipo: 'pct' },
  { clave: 'ambilight_peso_bordes', label: 'Peso bordes', min: 0, max: 1, step: 0.05, tipo: 'pct' },
  { clave: 'ambilight_peso_dominante', label: 'Peso dominante', min: 0, max: 1, step: 0.05, tipo: 'pct' },
  { clave: 'ambilight_fps', label: 'FPS', min: 10, max: 30, step: 1, tipo: 'int' },
]

function formatear(s, v) {
  if (s.tipo === 'pct') return Math.round(v * 100) + '%'
  if (s.tipo === 'int') return String(v)
  return Number(v).toFixed(2)
}

onMounted(() => ctrl.cargarMonitores())
</script>

<style scoped>
.pagina { display: flex; flex-direction: column; gap: 16px; }
.card { padding: 18px; display: flex; flex-direction: column; gap: 14px; }

.aviso { display: flex; gap: 10px; padding: 14px 16px; font-size: 0.8rem; line-height: 1.5; color: var(--text2); }
.aviso-ico { color: var(--tint); font-weight: 700; flex-shrink: 0; }
.aviso b { color: var(--text); font-weight: 600; }

.fila-activar { display: flex; align-items: center; justify-content: space-between; }
.estado { display: flex; align-items: center; gap: 10px; font-size: 0.9rem; font-weight: 500; }
.dot { width: 9px; height: 9px; border-radius: 50%; background: var(--text3); }
.dot.on { background: var(--green); box-shadow: 0 0 8px var(--green); }

.fila { display: flex; align-items: center; gap: 12px; }
.sub { font-size: 0.95rem; font-weight: 600; }
.toggle-txt { font-size: 0.88rem; }
.valor { font-size: 0.8rem; font-weight: 600; color: var(--text2); min-width: 42px; text-align: right; }
</style>
