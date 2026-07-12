<template>
  <div class="pagina">
    <div class="head">
      <div>
        <h1 class="page-title">Color <AyudaInfo>Pintá la tira del color que quieras: tocá el cuadro y arrastrá, o usá la paleta. El brillo y los botones de encender/probar están más abajo.</AyudaInfo></h1>
        <p class="page-subtitle">Elegí cualquier color para tu tira LED.</p>
      </div>
    </div>

    <div class="glass card">
      <SelectorColor :model-value="ctrl.colorActual" @update:model-value="ctrl.aplicarColor" />
    </div>

    <div class="glass card">
      <span class="sub">Paleta rápida</span>
      <div class="paleta">
        <button
          v-for="c in swatches"
          :key="c.nombre"
          class="swatch"
          :style="{ background: `rgb(${c.r},${c.g},${c.b})` }"
          :title="c.nombre"
          @click="ctrl.aplicarColor(c)"
        ></button>
      </div>
    </div>

    <div class="glass card">
      <div class="fila">
        <span class="field-label">Brillo</span>
        <input
          class="slider"
          type="range"
          min="0"
          max="255"
          :value="ctrl.brilloActual"
          @input="ctrl.aplicarBrillo(Number($event.target.value))"
        />
        <span class="valor">{{ ctrl.brilloActual }}</span>
      </div>

      <div class="acciones">
        <button class="btn btn-glass" @click="ctrl.encender">Encender</button>
        <button class="btn btn-glass" @click="ctrl.apagar">Apagar</button>
        <button class="btn btn-glass" @click="ctrl.probar">Probar</button>
        <button class="btn btn-glass" @click="ctrl.arcoiris">Arcoíris</button>
      </div>
    </div>

    <div class="glass card">
      <div class="fila-titulo">
        <span class="sub">Efectos de ambiente</span>
        <AyudaInfo>Efectos suaves para cuando no hay música: <b>Respiración</b> y <b>Pulso</b> laten con el color actual; <b>Vela</b> y <b>Fuego</b> titilan cálidos; <b>Ciclo</b> recorre los colores. Tocá uno para activarlo y de nuevo para apagarlo.</AyudaInfo>
      </div>
      <div class="efectos">
        <button
          v-for="e in ctrl.efectosAmbiente"
          :key="e.id"
          class="efecto"
          :class="{ activo: ctrl.ambienteActivado && ctrl.ambienteEfecto === e.id }"
          @click="ctrl.toggleEfectoAmbiente(e.id)"
        >
          <span class="efecto-ico" v-html="e.ico"></span>
          <span class="efecto-lbl">{{ e.label }}</span>
        </button>
      </div>
      <button v-if="ctrl.ambienteActivado" class="btn btn-tint peligro full" @click="ctrl.detenerAmbiente">Detener efecto</button>
    </div>

    <div class="glass card">
      <div class="fila-titulo">
        <span class="sub">Blanco cálido / frío</span>
        <AyudaInfo>Luz blanca ajustable, de cálida (amarillenta) a fría (azulada). Reemplaza el color actual hasta que elijas otro color de la paleta.</AyudaInfo>
      </div>
      <div class="fila">
        <span class="field-label">Temperatura</span>
        <input class="slider temp" type="range" min="0" max="100"
          v-model.number="temp" @input="ctrl.aplicarTemperatura(temp)" />
      </div>
      <div class="temp-labels">
        <span>Frío</span>
        <span>Cálido</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { inject, ref } from 'vue'
import SelectorColor from './SelectorColor.vue'
import AyudaInfo from './AyudaInfo.vue'

const ctrl = inject('ctrl')
const temp = ref(50) // 0 = frío, 100 = cálido

const swatches = [
  { nombre: 'Rojo', r: 255, g: 0, b: 0 },
  { nombre: 'Naranja', r: 255, g: 128, b: 0 },
  { nombre: 'Amarillo', r: 255, g: 255, b: 0 },
  { nombre: 'Verde', r: 0, g: 255, b: 0 },
  { nombre: 'Lima', r: 50, g: 205, b: 50 },
  { nombre: 'Cian', r: 0, g: 255, b: 255 },
  { nombre: 'Azul', r: 0, g: 0, b: 255 },
  { nombre: 'Turquesa', r: 64, g: 224, b: 208 },
  { nombre: 'Morado', r: 128, g: 0, b: 255 },
  { nombre: 'Rosa', r: 255, g: 0, b: 255 },
  { nombre: 'Blanco', r: 255, g: 255, b: 255 },
  { nombre: 'Cálido', r: 255, g: 180, b: 107 },
]
</script>

<style scoped>
/* Estilos propios de la página; el resto viene del sistema (styles.css). */
.paleta {
  display: grid;
  grid-template-columns: repeat(6, 1fr);
  gap: 8px;
}
.paleta .swatch { width: 100%; height: auto; aspect-ratio: 1; }

.acciones .btn { flex: 1; min-width: 90px; }

.slider.temp {
  background: linear-gradient(90deg, #7ab8ff 0%, #ffffff 50%, #ffb457 100%);
}
.temp-labels { display: flex; justify-content: space-between; font-size: 0.74rem; color: var(--text3); margin-top: -6px; }

.efectos { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; }
.efecto {
  display: flex; flex-direction: column; align-items: center; gap: 6px;
  padding: 14px 6px; border-radius: var(--radius-sm); cursor: pointer; font-family: inherit;
  background: rgba(0, 0, 0, 0.25); border: 1px solid var(--glass-border); color: var(--text2);
  transition: all 0.15s;
}
.efecto:hover { color: var(--text); border-color: var(--glass-border-strong); }
.efecto.activo { color: #fff; border-color: transparent; background: linear-gradient(135deg, var(--tint), var(--tint-2)); box-shadow: 0 4px 16px -6px var(--tint); }
.efecto-lbl { font-size: 0.72rem; font-weight: 600; }
</style>
