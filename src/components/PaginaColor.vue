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
      <span class="field-label bloque">Paleta rápida</span>
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
  </div>
</template>

<script setup>
import { inject } from 'vue'
import SelectorColor from './SelectorColor.vue'
import AyudaInfo from './AyudaInfo.vue'

const ctrl = inject('ctrl')

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
.pagina { display: flex; flex-direction: column; gap: 16px; }
.head { margin-bottom: 2px; }
.card { padding: 18px; display: flex; flex-direction: column; gap: 14px; }
.bloque { display: block; }

.paleta {
  display: grid;
  grid-template-columns: repeat(6, 1fr);
  gap: 8px;
}
.paleta .swatch { width: 100%; aspect-ratio: 1; }

.fila { display: flex; align-items: center; gap: 12px; }
.valor {
  font-size: 0.85rem;
  font-weight: 600;
  color: var(--text2);
  min-width: 30px;
  text-align: right;
}
.acciones { display: flex; gap: 8px; flex-wrap: wrap; }
.acciones .btn { flex: 1; min-width: 90px; }
</style>
