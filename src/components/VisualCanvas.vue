<template>
  <canvas ref="cv" class="cv"></canvas>
</template>

<script setup>
import { inject, ref, onMounted, onUnmounted, watch, computed } from 'vue'
import '../../motor_visual.js'

const ctrl = inject('ctrl')
const cv = ref(null)
let vis = null

// Tipo de visual EFECTIVO: si hay un timer activo y el usuario eligió su
// visual (Reloj/Tarjeta), gana ese; si no, el visual normal de Ajustes.
const tipoEfectivo = computed(() =>
  (ctrl.timer.activo && ctrl.timer.usarVisual) ? ctrl.timer.modoVisual : ctrl.ajustes.visual_tipo
)

onMounted(() => {
  vis = window.CrearVisual(cv.value, {
    r: ctrl.colorFondo.r, g: ctrl.colorFondo.g, b: ctrl.colorFondo.b,
    tipo: tipoEfectivo.value,
    movimiento: ctrl.ajustes.visual_movimiento,
    ritmo: ctrl.ritmoActivado,
  })

  // Alimenta los datos del timer al motor (los usan splitflap/colorcard).
  function alimentarTimer() {
    if (!vis) return
    vis.setTimerProgreso(ctrl.timer.progreso, ctrl.timer.tiempoRestante)
    vis.setTimerFondoColor(
      ctrl.timer.colorFondoVisual.r,
      ctrl.timer.colorFondoVisual.g,
      ctrl.timer.colorFondoVisual.b,
    )
  }

  watch(() => ({ ...ctrl.colorFondo }), (c) => vis && vis.setColor(c.r, c.g, c.b), { deep: true })
  watch(() => ctrl.ajustes.visual_movimiento, (v) => vis && vis.setMovimiento(v))
  watch(() => ctrl.ritmoActivado, (v) => vis && vis.setRitmo(v))
  watch(() => ctrl.beatTick, () => vis && vis.beat(ctrl.beatEnergia))

  // Un único punto de verdad para el tipo mostrado.
  watch(tipoEfectivo, (t) => {
    if (!vis) return
    if (ctrl.timer.activo && ctrl.timer.usarVisual) alimentarTimer()
    vis.setTipo(t)
  })

  // Datos del timer en vivo (progreso y color de la tarjeta).
  watch(() => ctrl.timer.progreso, (p) => {
    if (vis) vis.setTimerProgreso(p, ctrl.timer.tiempoRestante)
  })
  watch(() => ({ ...ctrl.timer.colorFondoVisual }), (c) => {
    if (vis) vis.setTimerFondoColor(c.r, c.g, c.b)
  }, { deep: true })

  // Estado inicial (p. ej. montar con timer ya activo en pantalla completa).
  if (ctrl.timer.activo && ctrl.timer.usarVisual) alimentarTimer()
})

onUnmounted(() => { if (vis) vis.destruir() })
</script>

<style scoped>
.cv { width: 100%; height: 100%; display: block; }
</style>
