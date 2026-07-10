<template>
  <span class="wrap">
    <button class="i" :class="{ activo: abierto }" @click.stop="toggle" aria-label="Información">i</button>
    <transition name="pop">
      <div v-if="abierto" class="globo glass" @click.stop>
        <slot />
      </div>
    </transition>
  </span>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
const abierto = ref(false)
function toggle() { abierto.value = !abierto.value }
function cerrar() { abierto.value = false }
onMounted(() => document.addEventListener('click', cerrar))
onUnmounted(() => document.removeEventListener('click', cerrar))
</script>

<style scoped>
.wrap { position: relative; display: inline-flex; }
.i {
  width: 18px; height: 18px; border-radius: 50%;
  border: 1px solid var(--glass-border); background: rgba(255, 255, 255, 0.06);
  color: var(--text2); font-size: 0.7rem; font-weight: 700; font-style: italic;
  cursor: pointer; font-family: Georgia, serif; line-height: 1; padding: 0;
  display: inline-flex; align-items: center; justify-content: center;
  transition: all 0.15s;
}
.i:hover { color: var(--text); border-color: var(--glass-border-strong); }
.i.activo { color: #fff; background: linear-gradient(135deg, var(--tint), var(--tint-2)); border-color: transparent; }

.globo {
  position: absolute; top: 26px; right: 0; z-index: 50;
  width: 240px; padding: 12px 14px;
  font-size: 0.76rem; line-height: 1.5; color: var(--text2);
  font-weight: 400; text-align: left; font-style: normal;
}

.pop-enter-active, .pop-leave-active { transition: opacity 0.15s, transform 0.15s; }
.pop-enter-from, .pop-leave-to { opacity: 0; transform: translateY(-4px); }
</style>
