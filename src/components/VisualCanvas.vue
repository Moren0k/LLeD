<template>
  <canvas ref="cv" class="cv"></canvas>
</template>

<script setup>
import { inject, ref, onMounted, onUnmounted, watch } from 'vue'
import '../../motor_visual.js'

const ctrl = inject('ctrl')
const cv = ref(null)
let vis = null

onMounted(() => {
  vis = window.CrearVisual(cv.value, {
    r: ctrl.colorFondo.r, g: ctrl.colorFondo.g, b: ctrl.colorFondo.b,
    tipo: ctrl.ajustes.visual_tipo,
    movimiento: ctrl.ajustes.visual_movimiento,
    ritmo: ctrl.ritmoActivado,
  })
  watch(() => ({ ...ctrl.colorFondo }), (c) => vis && vis.setColor(c.r, c.g, c.b), { deep: true })
  watch(() => ctrl.ajustes.visual_tipo, (v) => vis && vis.setTipo(v))
  watch(() => ctrl.ajustes.visual_movimiento, (v) => vis && vis.setMovimiento(v))
  watch(() => ctrl.ritmoActivado, (v) => vis && vis.setRitmo(v))
  watch(() => ctrl.beatTick, () => vis && vis.beat(ctrl.beatEnergia))
})

onUnmounted(() => { if (vis) vis.destruir() })
</script>

<style scoped>
.cv { width: 100%; height: 100%; display: block; }
</style>
