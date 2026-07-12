<template>
  <div class="pagina">
    <div class="head">
      <div>
        <h1 class="page-title">
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M9 18V5l12-2v13"/><circle cx="6" cy="18" r="3"/><circle cx="18" cy="16" r="3"/></svg>
          Ritmo
          <AyudaInfo>Detecta la música que suena en la PC y hace destellar la tira con cada golpe. Necesita tener activado el "Stereo Mix" en Windows y música sonando.</AyudaInfo>
        </h1>
        <p class="page-subtitle">Los LEDs destellan al compás de la música del sistema.</p>
      </div>
    </div>

    <div class="glass card">
      <div class="fila-activar">
        <div class="estado">
          <span class="dot" :class="{ on: ctrl.ritmoActivado }"></span>
          <span>{{ ctrl.ritmoActivado ? 'Detectando ritmo' : (ctrl.ritmoDisponible ? 'Listo' : 'Audio no disponible') }}</span>
        </div>
        <button
          class="btn"
          :class="ctrl.ritmoActivado ? 'btn-tint activo' : 'btn-tint'"
          :disabled="!ctrl.ritmoDisponible && !ctrl.ritmoActivado"
          @click="ctrl.toggleRitmo"
        >{{ ctrl.ritmoActivado ? 'Activo' : (ctrl.ritmoDisponible ? 'Iniciar' : 'No disponible') }}</button>
      </div>
    </div>

    <template v-if="ctrl.ritmoActivado">
      <!-- Color del flash -->
      <div class="glass card">
        <span class="sub">Color del flash</span>
        <div class="swatches">
          <button
            v-for="c in ctrl.coloresFlash"
            :key="c.nombre"
            class="swatch"
            :class="{ selected: !ctrl.flashDeCancion && ctrl.flashColor.r === c.r && ctrl.flashColor.g === c.g && ctrl.flashColor.b === c.b }"
            :style="{ background: `rgb(${c.r},${c.g},${c.b})` }"
            :title="c.nombre"
            @click="ctrl.cambiarFlashColor(c.r, c.g, c.b)"
          ></button>
          <button
            class="swatch swatch-song"
            :class="{ selected: ctrl.flashDeCancion }"
            title="Color de la canción actual"
            @click="ctrl.flashColorCancion"
          >
            <svg width="15" height="15" viewBox="0 0 24 24" fill="currentColor"><path d="M12 0C5.4 0 0 5.4 0 12s5.4 12 12 12 12-5.4 12-12S18.66 0 12 0zm5.521 17.34c-.24.359-.66.48-1.021.24-2.82-1.74-6.36-2.101-10.561-1.141-.418.122-.779-.179-.899-.539-.12-.421.18-.78.54-.9 4.56-1.021 8.52-.6 11.64 1.32.42.18.479.659.301 1.02z"/></svg>
          </button>
        </div>
      </div>

      <!-- Detección -->
      <div class="glass card">
        <div class="fila">
          <span class="field-label">Detectar</span>
          <AyudaInfo><b>Kicks</b>: solo el bombo. <b>Bajos</b>: las frecuencias graves. <b>Ambos</b>: kicks y bajos juntos (más reactivo).</AyudaInfo>
          <div class="segmented">
            <button
              v-for="d in ctrl.modosDeteccion"
              :key="d.modo"
              :class="{ active: ctrl.modoDeteccion === d.modo }"
              @click="ctrl.cambiarModoDeteccion(d.modo)"
            >{{ d.label }}</button>
          </div>
        </div>

        <label class="toggle">
          <input type="checkbox" v-model="ctrl.flashOnly" @change="ctrl.toggleFlashOnly" />
          <span class="track"><span class="thumb"></span></span>
          <span class="toggle-txt">Solo flash</span>
        </label>
        <p class="nota">El LED se mantiene tenue entre golpes y destella al máximo en cada beat.</p>
      </div>
    </template>
  </div>
</template>

<script setup>
import { inject } from 'vue'
import AyudaInfo from './AyudaInfo.vue'
const ctrl = inject('ctrl')
</script>

<style scoped>
/* Estilos propios de la página; el resto viene del sistema (styles.css). */
.swatch-song {
  background: rgba(255, 255, 255, 0.08);
  display: flex; align-items: center; justify-content: center;
  color: var(--text2); border-color: var(--glass-border);
}
.swatch-song.selected { border-color: var(--tint); color: var(--tint); }
</style>
