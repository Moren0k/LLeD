<template>
  <div class="app" :style="tintStyle">
    <!-- Fondo ambiental (visual en canvas) -->
    <div class="fondo">
      <VisualCanvas />
    </div>

    <!-- Barra superior -->
    <header class="topbar glass">
      <div class="topbar-left">
        <span class="marca">LLeD</span>
        <span class="con-dot" :class="{ on: ctrl.conectadoLed }"></span>
        <span class="con-txt">{{ ctrl.conectadoLed ? 'Conectado' : 'Desconectado' }}</span>
      </div>
      <button
        class="power"
        :class="{ off: !ctrl.ledEncendido }"
        :disabled="!ctrl.conectadoLed"
        :title="ctrl.ledEncendido ? 'Apagar tira' : 'Encender tira'"
        @click="ctrl.togglePower"
      >
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
          <path d="M12 2v10"/><path d="M18.4 6.6a9 9 0 1 1-12.77 0"/>
        </svg>
      </button>
    </header>

    <!-- Página activa -->
    <main class="contenido">
      <transition name="fade" mode="out-in">
        <component :is="paginaComp" :key="paginaActiva" />
      </transition>
    </main>

    <!-- Barra de pestañas -->
    <nav class="tabbar glass">
      <button
        v-for="p in paginas"
        :key="p.id"
        class="tab"
        :class="{ active: paginaActiva === p.id }"
        @click="paginaActiva = p.id"
      >
        <span class="tab-ico" v-html="p.icono"></span>
        <span class="tab-lbl">{{ p.label }}</span>
      </button>
    </nav>

    <VisualFullscreen v-if="ctrl.mostrarFull" />
  </div>
</template>

<script setup>
import { ref, computed, provide } from 'vue'
import { useControlador } from './composables/useControlador.js'
import PaginaColor from './components/PaginaColor.vue'
import PaginaSpotify from './components/PaginaSpotify.vue'
import PaginaRitmo from './components/PaginaRitmo.vue'
import PaginaVisuales from './components/PaginaVisuales.vue'
import PaginaBiblioteca from './components/PaginaBiblioteca.vue'
import PaginaAjustes from './components/PaginaAjustes.vue'
import VisualFullscreen from './components/VisualFullscreen.vue'
import VisualCanvas from './components/VisualCanvas.vue'

const ctrl = useControlador()
provide('ctrl', ctrl)

const paginaActiva = ref('color')

const paginas = [
  { id: 'color', label: 'Color', comp: PaginaColor, icono: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="13.5" cy="6.5" r=".5" fill="currentColor"/><circle cx="17.5" cy="10.5" r=".5" fill="currentColor"/><circle cx="8.5" cy="7.5" r=".5" fill="currentColor"/><circle cx="6.5" cy="12.5" r=".5" fill="currentColor"/><path d="M12 2C6.5 2 2 6.5 2 12s4.5 10 10 10c.926 0 1.648-.746 1.648-1.688 0-.437-.18-.835-.437-1.125-.29-.289-.438-.652-.438-1.125a1.64 1.64 0 0 1 1.668-1.668h1.996c3.051 0 5.555-2.503 5.555-5.554C21.965 6.012 17.461 2 12 2z"/></svg>' },
  { id: 'spotify', label: 'Spotify', comp: PaginaSpotify, icono: '<svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor"><path d="M12 0C5.4 0 0 5.4 0 12s5.4 12 12 12 12-5.4 12-12S18.66 0 12 0zm5.521 17.34c-.24.359-.66.48-1.021.24-2.82-1.74-6.36-2.101-10.561-1.141-.418.122-.779-.179-.899-.539-.12-.421.18-.78.54-.9 4.56-1.021 8.52-.6 11.64 1.32.42.18.479.659.301 1.02zm1.44-3.3c-.301.42-.841.6-1.262.3-3.239-1.98-8.159-2.58-11.939-1.38-.479.12-1.02-.12-1.14-.6-.12-.48.12-1.021.6-1.141C9.6 9.9 15 10.561 18.72 12.84c.361.181.54.78.241 1.2zm.12-3.36C15.24 8.4 8.82 8.16 5.16 9.301c-.6.179-1.2-.181-1.38-.721-.18-.601.18-1.2.72-1.381 4.26-1.26 11.28-1.02 15.721 1.621.539.3.719 1.02.419 1.56-.299.421-1.02.599-1.559.3z"/></svg>' },
  { id: 'ritmo', label: 'Ritmo', comp: PaginaRitmo, icono: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M9 18V5l12-2v13"/><circle cx="6" cy="18" r="3"/><circle cx="18" cy="16" r="3"/></svg>' },
  { id: 'visuales', label: 'Visuales', comp: PaginaVisuales, icono: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="3" width="20" height="14" rx="2"/><path d="M8 21h8M12 17v4"/></svg>' },
  { id: 'biblioteca', label: 'Biblioteca', comp: PaginaBiblioteca, icono: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/></svg>' },
  { id: 'ajustes', label: 'Ajustes', comp: PaginaAjustes, icono: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/></svg>' },
]

const paginaComp = computed(() => paginas.find((p) => p.id === paginaActiva.value).comp)

// El acento de toda la interfaz sigue el color del fondo (transición fluida).
const tintStyle = computed(() => {
  const { r, g, b } = ctrl.colorFondo
  const mezcla = (a, x) => Math.round(a * 0.55 + x * 0.45)
  const t2 = `rgb(${mezcla(r, 125)}, ${mezcla(g, 75)}, ${mezcla(b, 255)})`
  return {
    '--tint': `rgb(${r}, ${g}, ${b})`,
    '--tint-2': t2,
  }
})
</script>

<style scoped>
.app {
  position: relative;
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 0 16px 110px;
  overflow: hidden;
}

/* ── Fondo ambiental (canvas) ── */
.fondo {
  position: fixed;
  inset: 0;
  z-index: -1;
  overflow: hidden;
  background: #05060a;
}

/* ── Barra superior ── */
.topbar {
  width: 100%;
  max-width: 480px;
  margin-top: 16px;
  padding: 12px 18px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  position: sticky;
  top: 16px;
  z-index: 20;
}
.topbar-left { display: flex; align-items: center; gap: 10px; }
.marca { font-size: 1.1rem; font-weight: 800; letter-spacing: -0.02em; }
.con-dot { width: 8px; height: 8px; border-radius: 50%; background: var(--red); }
.con-dot.on { background: var(--green); box-shadow: 0 0 8px var(--green); }
.con-txt { font-size: 0.75rem; color: var(--text2); }

.power {
  width: 38px; height: 38px;
  border-radius: 12px;
  border: 1px solid var(--glass-border);
  background: linear-gradient(135deg, var(--tint), var(--tint-2));
  color: #fff;
  display: flex; align-items: center; justify-content: center;
  cursor: pointer;
  transition: all 0.2s;
  box-shadow: 0 4px 16px -4px var(--tint);
}
.power.off {
  background: rgba(255, 255, 255, 0.06);
  color: var(--text3);
  box-shadow: none;
}
.power:disabled { opacity: 0.4; cursor: default; }

/* ── Contenido ── */
.contenido {
  width: 100%;
  max-width: 480px;
  margin-top: 18px;
  flex: 1;
}

/* ── Barra de pestañas ── */
.tabbar {
  position: fixed;
  bottom: 18px;
  left: 50%;
  transform: translateX(-50%);
  width: calc(100% - 32px);
  max-width: 480px;
  padding: 8px;
  display: flex;
  gap: 4px;
  z-index: 30;
}
.tab {
  flex: 1;
  background: none;
  border: none;
  color: var(--text3);
  cursor: pointer;
  font-family: inherit;
  padding: 8px 4px;
  border-radius: 14px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  transition: all 0.18s;
}
.tab:hover { color: var(--text2); }
.tab.active {
  color: #fff;
  background: linear-gradient(135deg, var(--tint), var(--tint-2));
  box-shadow: 0 4px 16px -4px var(--tint);
}
.tab-ico { display: flex; }
.tab-lbl { font-size: 0.62rem; font-weight: 600; }

/* ── Transición de página ── */
.fade-enter-active, .fade-leave-active { transition: opacity 0.2s ease, transform 0.2s ease; }
.fade-enter-from { opacity: 0; transform: translateY(8px); }
.fade-leave-to { opacity: 0; transform: translateY(-8px); }

@media (max-width: 380px) {
  .tab-lbl { display: none; }
}
</style>
